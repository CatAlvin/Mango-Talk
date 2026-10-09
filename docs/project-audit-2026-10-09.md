# Mango Talk 项目审查与成熟路线

> 本报告记录 `1a71659` 开发基线。消息可靠性、附件权限、登录入口、演示和发布流程已在 1.0 版本集中修复；当前验收结果见 [1.0 验收记录](releases/2026-10-09/validation.md)。下文保留原始问题和复现证据。

Mango Talk 已形成可运行的聊天产品原型，私聊、群聊、文字、附件、回复、撤回已有实现。下一步应先解决消息可靠性与附件权限，再完善用户入口和移动端，最后进入可运维的小规模上线。当前 README 将头像与资料系统放在下一阶段，建议先插入一轮基础修复。

审查日期为 2026 年 10 月 9 日，代码基线为 `1a71659`。本次只增加审查文档、截图与复现脚本，未修改业务代码。页面来自实际前端生产构建，后端使用隔离的 SQLite 内存库和虚构用户；线上 MySQL、Nginx、HTTPS、真实用户与负载未验证。下文的“已复现”指本地隔离环境，“代码确认”指实现直接支持该结论，“待验证”指需要目标部署环境或真实设备。

## 文件结构和现有能力

| 范围 | 职责 | 当前判断 |
| --- | --- | --- |
| `frontend/src/views/LoginView.vue` | 登录界面 | 主流程可用，缺少新用户入口，仍保留过时开发文案 |
| `frontend/src/views/ChatView.vue` | 消息展示、上传、发送、连接、回复、撤回 | 2566 行，业务状态与样式集中，存在异步竞态和发送边界问题 |
| `frontend/src/components` | 私聊和群聊创建 | 已有搜索、选人、创建逻辑，短屏群聊面板会裁切 |
| `frontend/src/stores` | 身份、房间、消息缓存 | 分层清楚，缺少请求取消、恢复策略和统一错误状态 |
| `backend/app/api` | HTTP 和 WebSocket 接口 | 主要功能齐备，消息验证和序列化在两个通道重复实现 |
| `backend/app/models` 和 `schemas` | 数据模型和接口契约 | 房间成员唯一约束已建立；缺少附件归属、发送幂等、已读游标等模型 |
| `backend/app/core` 和 `db` | 配置、认证、数据库 | 使用 JWT 与密码哈希；配置校验、数据库迁移与时区约定不足 |
| `scripts/ws_*` | 手动实时通信验证 | 可以调试，连接 URL 会打印令牌，应脱敏 |
| `docs/development-log.md` | 开发记录 | 记录完整，但部分“完成”结论与当前源码不一致 |
| `codesort` | 合并导出代码 | 脚本固定 Linux 路径，导出副本与源码双份维护；应以源码为唯一依据 |
| `logs` 和 `backups` | 目录占位 | 没有相应备份恢复、日志轮转和运维脚本 |

已有可保留的基础：Vue、Pinia、API、模型的目录分层；房间成员权限检查；消息落库后广播；附件随机存储名和大小限制；回复状态、加载状态、撤回占位和滚动提示。后端探针确认非房间成员读取历史、发送消息均返回 403，正常 WebSocket 发送返回 `new_message`。这些基础可以逐步补强，无需重写整个项目。

## 修复优先级

P0 表示真实用户试用前应解决的权限或内容误发问题；P1 表示影响核心聊天或用户完成任务的问题；P2 表示后续维护、性能和体验改进。优先级不等同于漏洞公告评级。

### 附件与身份边界

| 编号 | 优先级和证据 | 问题与影响 | 建议和验收 |
| --- | --- | --- | --- |
| S1 | P0，已复现 | 上传目录由 `StaticFiles` 直接公开。匿名 GET 文件链接返回 200，私聊文件的访问没有房间权限边界。随机 URL 不能替代权限校验。 | 附件用受控下载接口或短期授权 URL；房间成员可以读取，匿名用户和非成员被拒绝。 |
| S2 | P0，已复现及风险推断 | 上传处理器接受 HTML，匿名下载返回 `text/html`；只使用客户端 MIME 黑名单，定义的图片白名单没有被使用。同源主动内容可能执行脚本，进而接触 localStorage 中的令牌。本次只测试无脚本 HTML，没有执行窃取行为。 | 校验允许的文件类别、扩展名和实际内容；普通文件强制下载，主动内容隔离域名或严格拒绝；验证 HTML、SVG、伪造 MIME 的行为。 |
| S3 | P0，已复现 | 消息发送接受客户端提交的 `storage_path` 等元数据，仅核对路径和大小，不验证上传者。其他用户拿到元数据后，可将 Alice 的附件绑定到自己所在的房间，返回 201。 | 建立上传记录，客户端只提交 `upload_id`；服务端验证所有者、状态和目标房间，再生成文件元数据。 |
| S4 | P0，受控函数复现 | A 房间开始上传，完成前切到 B，发送阶段读取新的 `wsRef`，最终把附件发送给 B。 | 上传任务绑定发起时的房间 ID、回复目标和任务 ID；切房间取消或保留到原房间，绝不发送到新房间。 |
| S5 | P1，已复现 | 用户禁用只在建立 WebSocket 时验证；已有连接继续发送，禁用后仍得到 `new_message`。令牌有效期也只在握手校验。 | 发消息重新检查有效身份；禁用、过期与撤销时关闭连接，并让前端正确进入重新登录状态。 |
| S6 | P1，代码确认 | `JWT_SECRET_KEY` 默认空字符串，启动时不校验；令牌默认有效 7 天，退出只清除客户端状态。 | 非开发环境缺少强密钥时拒绝启动；明确会话有效期、刷新和撤销策略；令牌从日志中脱敏。线上密钥是否配置正确尚未验证。 |
| S7 | P1，已复现 | 登录用 username 或 phone 的 OR 查询，再要求最多一条结果。用户名等于另一用户手机号时，两条记录触发 `MultipleResultsFound`，登录变成 500。 | 定义一致的身份命名空间，例如禁止手机号形态用户名或显式区分登录类型；冲突注册被拒绝，登录返回确定的业务结果。 |
| S8 | P1，已复现 | 密码允许 128 个字符，但现有 bcrypt 实现忽略超过 72 字节的后缀；两串前 72 字节相同、最后一字节不同的密码都能验证通过。 | 采用支持长密码的哈希方案并设计旧密码迁移，或明确按字节限制；同时验证中文密码，避免仅用字符数判断。 |

S1、S2 的代码入口是 [main.py](D:/Programming/CodeX/Mango-Talk/backend/app/main.py:24) 和 [uploads.py](D:/Programming/CodeX/Mango-Talk/backend/app/api/uploads.py:46)；S3 在 [messages.py](D:/Programming/CodeX/Mango-Talk/backend/app/api/messages.py:103) 与 WebSocket 的附件校验中；S4 在 [ChatView.vue](D:/Programming/CodeX/Mango-Talk/frontend/src/views/ChatView.vue:1104)。S5 在 [ws.py](D:/Programming/CodeX/Mango-Talk/backend/app/api/ws.py:196)，S6 在 [config.py](D:/Programming/CodeX/Mango-Talk/backend/app/core/config.py:19)，S7 在 [auth.py](D:/Programming/CodeX/Mango-Talk/backend/app/api/auth.py:45)，S8 在 [security.py](D:/Programming/CodeX/Mango-Talk/backend/app/core/security.py:6) 和 [user.py](D:/Programming/CodeX/Mango-Talk/backend/app/schemas/user.py:4)。

附件的类型校验、存储隔离和访问控制建议参考 [OWASP 文件上传指南](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)。

### 消息可靠性

| 编号 | 优先级和证据 | 问题与影响 | 建议和验收 |
| --- | --- | --- | --- |
| M1 | P1，已复现 | 历史接口按时间升序直接取 50 条。61 条消息的测试房间返回 ID 1 到 50，后来的消息刷新后看不到。 | 首屏取最新 50 条，再正序展示；添加 `before_id` 游标分页，验证至少 120 条消息的连续性与去重。 |
| M2 | P1，页面及代码确认 | 后端已有 `replied_message`，前端却只从 `currentMessages` 查原消息。摘要明明存在仍显示“原消息暂未加载”，与 README 的完成说明不一致。 | 展示优先使用有效的后端摘要；定位单独判断是否加载，可再增加定位接口。 |
| M3 | P1，受控函数复现 | 发送按钮虽然禁用，Enter 处理却直接调用发送；发送函数不检查 `sending`、`uploading`。两次调用实际发送两次。输入法候选确认 Enter 也会触发发送。 | 发送动作自身校验可发送状态；检查 `isComposing` 和输入法边界；连续按 Enter、上传中按 Enter 不重复发送。 |
| M4 | P1，代码确认 | 服务器确认通过文本或附件名匹配，没有 `client_message_id`。超时重试可能重复入库，同内容的其他端消息也可能被误认为确认；收到确认时无条件清空当前草稿。 | 为每次发送生成稳定 ID，服务端建立幂等约束；确认关联任务；允许用户编辑下一条草稿，不能被上一条确认删除。 |
| M5 | P1，代码确认 | 重连只打开 WebSocket，不补取断线期间消息；没有客户端心跳与自动恢复。只订阅当前房间，其他房间无未读和新会话通知。 | 重连后按最后消息 ID 补齐并去重；添加心跳和退避重连；再加入用户级会话事件与未读游标。 |
| M6 | P1，代码确认 | 切房间先等待 HTTP，再连接新 WebSocket；旧连接仍可能工作。多个快速切换的请求完成顺序可能覆盖当前连接；初次挂载与 watcher 都加载和连接，存在重复初始化。 | 房间切换绑定请求代次并取消旧请求；连接回调确认仍属当前任务；慢网络 A→B→C 后应始终留在 C。 |
| M7 | P1，已复现及代码确认 | 撤回只标记 `is_recalled`，历史响应仍返回原文，附件仍可访问。前端撤回动作忽略 HTTP 返回值，依赖广播；广播丢失时本端界面也可能不更新。 | 普通客户端响应不再携带撤回正文和附件；明确保留策略；撤回 HTTP 成功立即更新本端，再用事件同步其他端。 |
| M8 | P1，已复现 | WebSocket 接收到数组或数字 content 时抛 `AttributeError`；安全发送包装忽略内层 False，失败仍返回 True、连接仍保留。 | 使用类型化事件模型，拒绝错误输入并返回可识别错误；数据库错误回滚并记录；正确透传发送结果、清除失效连接。 |
| M9 | P1，代码确认 | HTTP `POST /messages` 落库后直接返回，不发送实时事件；与 WebSocket 发送行为不一致。 | 两个通道共享消息服务和发布流程；用 HTTP 发消息时，在线房间参与者也应立刻收到事件。 |

M1 见 [messages.py](D:/Programming/CodeX/Mango-Talk/backend/app/api/messages.py:290)，M2 见 [ChatView.vue](D:/Programming/CodeX/Mango-Talk/frontend/src/views/ChatView.vue:684)，M3 见 [键盘入口](D:/Programming/CodeX/Mango-Talk/frontend/src/views/ChatView.vue:1045) 和 [发送动作](D:/Programming/CodeX/Mango-Talk/frontend/src/views/ChatView.vue:1163)，M4 见 [确认匹配](D:/Programming/CodeX/Mango-Talk/frontend/src/views/ChatView.vue:810) 和 [草稿清理](D:/Programming/CodeX/Mango-Talk/frontend/src/views/ChatView.vue:962)。M5、M6 见 [连接与重连](D:/Programming/CodeX/Mango-Talk/frontend/src/views/ChatView.vue:892) 和 [房间监听](D:/Programming/CodeX/Mango-Talk/frontend/src/views/ChatView.vue:1233)。M7 见 [序列化](D:/Programming/CodeX/Mango-Talk/backend/app/api/messages.py:84) 和 [撤回动作](D:/Programming/CodeX/Mango-Talk/frontend/src/views/ChatView.vue:1210)。M8 见 [ws.py](D:/Programming/CodeX/Mango-Talk/backend/app/api/ws.py:243)、[安全发送](D:/Programming/CodeX/Mango-Talk/backend/app/api/ws.py:36) 和 [ws_manager.py](D:/Programming/CodeX/Mango-Talk/backend/app/services/ws_manager.py:22)。M9 见 [HTTP 创建消息](D:/Programming/CodeX/Mango-Talk/backend/app/api/messages.py:258)。

### 展示和用户流程

| 编号 | 优先级和证据 | 问题 | 建议和验收 |
| --- | --- | --- | --- |
| U1 | P1，页面复现 | 390×640 下选中群成员后，创建按钮顶部约 739px、底部约 777px，落到屏幕外。侧栏和面板均限制溢出，操作被裁切。 | 移动端使用可滚动全屏面板或弹层，底部主按钮固定；覆盖 320×568、390×640、横屏和键盘弹出。 |
| U2 | P2，页面及 DOM 确认 | 默认 body margin 为 8px，聊天文档高 736px、视口高 720px，外层出现滚动条；登录页同样有白边。布局只在组件中定义，没有全局 reset。 | 统一 `box-sizing`、清除 body margin，使用动态视口高度与 safe-area；聊天只在消息区域滚动。 |
| U3 | P2，页面确认 | 登录页仍写“下一步再接 /users/me 与房间列表”；侧栏写 v0.5，README 写 v0.6，package 写 0.0.0；`user/member/owner` 直接展示内部枚举。 | 换成产品文案，角色中文化；版本集中定义，开发记录移出用户界面。 |
| U4 | P1 至 P2，代码确认 | 没有注册、资料编辑、找回密码入口；房间和历史获取失败主要写 console，用户会看到空列表或无消息，难以区分失败和空状态。 | 首先确定邀请制或开放注册；为每个请求提供加载、空、失败、重试状态；会话过期统一处理，网络错误不要直接抹掉有效登录状态。 |
| U5 | P2，页面及代码确认 | 房间卡片只有成员数和角色，无最后消息、活动时间、未读；后端按 room.updated_at 排序，而发送消息不更新房间。用户难以找到最新会话。 | 加入最后消息摘要、最后活动时间和未读标记；新会话和其他房间事件更新列表。 |
| U6 | P2，可访问性风险 | 空 `html lang`；刷新、关闭、菜单等图标按钮缺少明确名称；群聊 label 没关联 input，回复定位是点击 div；辅助文字较小且很浅，缺少 reduced-motion 分支。 | 补语义、标签和焦点；回复定位使用按钮；测试键盘访问和错误播报，测量文字对比度；支持减少动画。截图不能证明整体 WCAG 合规。 |

U1 见 [GroupRoomCreator.vue](D:/Programming/CodeX/Mango-Talk/frontend/src/components/GroupRoomCreator.vue:386) 和 [ChatView.vue](D:/Programming/CodeX/Mango-Talk/frontend/src/views/ChatView.vue:1312)，U2 见 [布局](D:/Programming/CodeX/Mango-Talk/frontend/src/views/ChatView.vue:1303)，U3 见 [LoginView.vue](D:/Programming/CodeX/Mango-Talk/frontend/src/views/LoginView.vue:72) 和 [版本展示](D:/Programming/CodeX/Mango-Talk/frontend/src/views/ChatView.vue:25)，U4 见 [错误处理](D:/Programming/CodeX/Mango-Talk/frontend/src/views/ChatView.vue:986) 与 [身份恢复](D:/Programming/CodeX/Mango-Talk/frontend/src/stores/auth.js:78)，U5 见 [房间列表接口](D:/Programming/CodeX/Mango-Talk/backend/app/api/rooms.py:179)，U6 见 [index.html](D:/Programming/CodeX/Mango-Talk/frontend/index.html:2)。

## 技术和上线准备

1. **新检出项目无法直接启动后端，已复现。** `uploads` 根目录不存在，导入 `app.main` 时 `StaticFiles` 抛 RuntimeError。应在初始化流程创建存储目录，提供配置模板、数据库初始化步骤和完整本地运行说明。当前 Vite 没有 API 和 WebSocket 本地代理；同源请求依赖外部反向代理。验收应从干净检出开始，而不是只验证已经配置好的服务器。
2. **依赖扫描需要处理。** 按 `package-lock.json` 安装后构建成功，npm audit 报告 13 个受影响包项，其中 10 high、2 moderate、1 low。这不代表 13 个可利用的线上漏洞，部分是 Node 适配器、SSR 或构建工具链条件。锁定 Vite 8.0.3 命中官方开发服务器文件读取公告；若仍通过公网代理开发服务器，应优先停止该部署方式，并升级到覆盖当前公告的补丁版本。不能仅因为某一公告在 8.0.5 修复，就认为全部公告已经解决。[Vite 官方公告](https://github.com/vitejs/vite/security/advisories/GHSA-p9ff-h696-f583)
3. **连接管理器只适用于单进程，代码确认。** 内存字典不会跨 Uvicorn workers 共享；撤回 HTTP 请求与 WebSocket 被分配到不同 worker 时，实时广播可能缺失。短期明确单 worker 部署和容量边界；需要扩容时再引入 Redis 等跨进程事件通道。[FastAPI 官方说明](https://fastapi.tiangolo.com/advanced/websockets/)
4. **性能应先减少重复查询和阻塞。** 探针取 61 条历史消息执行 40 次 SQL，序列化发送者和回复产生额外查询。建议批量加载用户与回复，添加符合游标查询的复合索引。异步 WebSocket 中运行同步 PyMySQL/SQLAlchemy、同步文件写入会阻塞事件循环；广播逐个 await 也会受慢客户端影响。先测目标规模，再采用线程隔离或异步数据访问、广播超时与队列。
5. **数据库演进缺少迁移。** `create_all` 不负责修改已有表结构；没有 Alembic 迁移、数据库备份恢复演练。私聊靠先查后建，没有用户对的唯一约束，并发创建可能重复；注册的预查也不能替代唯一冲突处理。时间使用无时区 DateTime、数据库 now、Python 本地时间和 UTC 混合，前端直接 new Date，应统一 UTC 带时区协议。
6. **上传生命周期未闭合。** 全局 HTTP 超时 10 秒却允许 50MB 文件，弱网容易中断；上传后发送失败无法直接复用重试，留下孤儿文件。零字节上传可成功，但消息附件要求大小大于零。应增加上传进度、取消、任务复用、大小提示、配额和定期清理。
7. **安全与运维配置需要收敛。** CORS 当前为所有来源且允许凭据，WebSocket 没有来源白名单；登录、注册、搜索、上传和发消息缺少业务限流，内容长度和附件数量边界不足。用户搜索可以空关键词枚举用户并返回完整手机号，应按产品需要脱敏和限制。没有可复用 Nginx/systemd 配置、结构化业务日志、告警和恢复流程；服务器现状需要另行核实。
8. **维护与验证门槛尚未建立。** package 脚本只有 dev/build/preview，没有自动化测试、lint 或 CI。`ChatView.vue` 应在修复过程中逐步抽出连接、上传和发送任务逻辑，HTTP/WS 后端共享验证与序列化。`uvloop` 无条件固定在 requirements 中，Windows 复现需跳过；Passlib 与 bcrypt 当前组合会打印版本探测警告，但本次密码哈希和登录可用，不能据此判定登录已坏。

## 页面证据和流程结果

以下均使用虚构审查账号。浏览器设置桌面默认尺寸，移动端分别为 390×844 和 390×640；截图实际像素尺寸由内嵌浏览器内容区决定。

1. **登录和退出后返回登录页：可用，展示需要整理。** 输入标签和自动填充属性已具备；文案过时、没有新用户路径、外层白边和滚动条明显。

![登录页](D:/Programming/CodeX/Mango-Talk/docs/audit/2026-10-09/09-login-verified.png)

2. **进入群聊和读取消息：主界面可用。** 房间与消息层次清楚，连接状态可见；角色枚举、低对比辅助信息和外层滚动需要调整。用户卡片绿点是固定展示，不能据此声称已实现在线状态。

![群聊页面](D:/Programming/CodeX/Mango-Talk/docs/audit/2026-10-09/02-chat-desktop.png)

3. **查看私聊历史和缺失原消息的回复：异常。** 61 条消息只展示最早 50 条；用专门构造的“回复目标不在当前窗口”数据验证时，后端摘要存在，界面仍显示未加载。该数据用于隔离显示与定位逻辑，不用于模拟自然产生的消息时间顺序。

![回复摘要缺失](D:/Programming/CodeX/Mango-Talk/docs/audit/2026-10-09/03-reply-missing.png)

4. **桌面打开创建群聊面板：可见，空间偏窄。** 选人流程有提示；关闭按钮和输入语义需要补齐。此步骤检查面板，不代表完成了真实多人创建与邀请验证。

![桌面创建群聊](D:/Programming/CodeX/Mango-Talk/docs/audit/2026-10-09/04-group-desktop.png)

5. **高屏手机打开侧栏和群聊面板：基本可见。** 抽屉能展开，但创建表单挤在固定侧栏内，字号较小。

![移动端创建群聊](D:/Programming/CodeX/Mango-Talk/docs/audit/2026-10-09/05-group-mobile.png)

6. **短屏手机搜索并选择群成员：流程被阻断。** 两个搜索结果、一个已选成员就把主按钮推到视口下方，当前裁切布局无法完成创建。

![短屏创建按钮被裁切](D:/Programming/CodeX/Mango-Talk/docs/audit/2026-10-09/06-group-short-screen.png)

7. **发送文本回复并点击已加载原消息：可用。** 回复摘要显示正确，定位处理可执行。输入法、重复发送和弱网仍需按 M3 至 M6 验收。

![回复发送成功](D:/Programming/CodeX/Mango-Talk/docs/audit/2026-10-09/07-reply-sent.png)

8. **撤回本人消息：本地实时界面可用，数据边界不足。** 页面变成撤回占位，但历史响应仍带原文，参见 M7。

![撤回消息](D:/Programming/CodeX/Mango-Talk/docs/audit/2026-10-09/08-recalled.png)

## 按顺序推进的成熟路线

每一步作为一个独立迭代，通过验收后再进入下一步。下面是建议顺序，不是未经估算的日期承诺。

| 阶段 | 工作范围 | 进入下一阶段的条件 |
| --- | --- | --- |
| 第一步 权限与误发修复 | S1 至 S4；强配置校验；移除公网开发服务器部署方式；补启动说明 | 匿名和非成员不能下载；其他用户不能复用上传；HTML 不以主站主动内容执行；上传切房间不误发；干净检出可复现运行 |
| 第二步 可靠消息主链路 | M1 至 M9；S5 至 S8；发送幂等、重连补取、回复摘要、输入法、统一错误处理 | 120 条历史可连续浏览；连续 Enter 不重复；断线期间消息恢复；A→B→C 不串连接；禁用与会话到期生效；撤回正文不再提供给普通客户端 |
| 第三步 用户流程和移动端 | U1 至 U6；明确邀请或注册；错误和空状态；会话摘要与未读；按需增加头像和资料 | 新用户无需开发者协助完成进入、建会话、聊天；短屏与软键盘下按钮可达；网络失败可重试；键盘能完成核心流程 |
| 第四步 生产运行和回归检查 | Nginx 静态构建、HTTPS/WSS、systemd、迁移、限流、日志、备份恢复、CI；单 worker 容量测量 | 服务重启可恢复；HTTPS 和刷新子路由正常；告警能定位问题；从备份恢复到新环境成功；CI 执行核心权限与消息回归 |
| 第五步 小范围试用和迭代 | 邀请 5 至 10 位目标用户持续试用，收集任务失败与高频需求 | 每个严重问题都有复现与回归；明确发送失败率、重连恢复情况、接口延迟和存储增长；试用者能自行完成主要任务 |

默认以 README 中的小团队或校园社群为首批使用场景。第一批用户的真实反馈应决定是否追加搜索、管理、通知和成员管理等功能。头像可以放在第三步，输入中状态和复杂在线系统可排在核心可靠性之后。

## 第一轮具体任务清单

- [ ] 为附件建立上传记录与所有权校验，客户端发送 `upload_id`。
- [ ] 将私聊附件从公开静态目录读取改为授权下载；定义 HTML、SVG 与普通文件处理规则。
- [ ] 上传绑定原房间，切换房间时取消或回到原任务，不使用新的连接发送。
- [ ] 首屏读取最新 50 条，增加历史游标和分页去重。
- [ ] 发送函数检查发送状态，输入法 Enter 不发送；给发送任务增加稳定 ID。
- [ ] 回复展示消费 `replied_message`，与“原消息能否定位”分开判断。
- [ ] 补权限、消息历史、串房间和重复发送的自动化回归。
- [ ] 修复缺少 uploads 目录的启动失败，提供本地代理、配置模板和运行说明。
- [ ] 核实公网部署方式，生产切换静态构建和 HTTPS/WSS；处理依赖公告。

## 复现材料和边界

后端结果保存在 [results.json](D:/Programming/CodeX/Mango-Talk/docs/audit/2026-10-09/results.json)，前端受控函数结果保存在 [frontend-results.json](D:/Programming/CodeX/Mango-Talk/docs/audit/2026-10-09/frontend-results.json)，依赖扫描保存在 [npm-audit.json](D:/Programming/CodeX/Mango-Talk/docs/audit/2026-10-09/npm-audit.json)，默认启动失败保存在 [startup-check.txt](D:/Programming/CodeX/Mango-Talk/docs/audit/2026-10-09/startup-check.txt)。

Windows 审查环境使用 Node 24.19.0、Python 3.12；后端对齐 requirements，跳过不支持 Windows 的 uvloop，并额外安装测试客户端 httpx。前端按 npm 锁文件安装，实际执行 Vite 8.0.3 生产构建成功，输出 JS 179.08kB、CSS 41.71kB；Python 依赖一致性检查通过。安装的 Vue Devtools 传递依赖出现 Vite peer 版本警告，插件未在 vite.config 中启用，应清理或对齐。

从项目根目录执行：

```powershell
& backend/.venv/Scripts/python.exe docs/audit/2026-10-09/probe.py
node docs/audit/2026-10-09/frontend-probe.mjs
```

后端探针覆盖隔离的有效发送、权限拒绝、历史顺序、上传、撤回内容、身份冲突、长密码、禁用后的已有连接、错误 WebSocket 输入和失效连接清理；前端探针直接提取未修改的组件函数，使用受控 Promise 和键盘事件复现串房间、重复发送和输入法问题。它们是本次审查证据，后续应转换为项目正式测试。

截图预览使用 [preview.mjs](D:/Programming/CodeX/Mango-Talk/docs/audit/2026-10-09/preview.mjs) 和探针的 `--serve` 模式，在 127.0.0.1 的独立端口运行。该预览仅用于审查数据，不是生产代理配置。尚需验证 MySQL 实际迁移和并发约束、跨进程广播、线上配置、真实移动设备软键盘、完整辅助技术支持，以及目标用户规模的性能。
