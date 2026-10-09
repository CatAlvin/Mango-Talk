# Mango Talk

一个用于团队日常沟通的实时聊天应用。支持私聊、群聊、图片与文件、消息回复和撤回，提供可直接体验的演示空间。

[打开 Mango Talk](https://mango-talk.chenglan.tech) · [体验演示](https://mango-talk.chenglan.tech/demo) · [发布与恢复](docs/deployment.md)

## 体验

在登录页选择「进入演示空间」，无需注册即可体验聊天、回复、附件和创建会话。演示数据保存在当前浏览器，刷新后继续使用，也可以随时重置。真实账号的聊天使用独立的服务端数据。

注册账号后可以搜索用户，开始私聊或邀请成员创建群聊。消息通过 HTTP 确认发送，WebSocket 同步新消息、撤回和会话变化；断线重连后按消息游标补齐记录。

## 功能与实现

| 功能 | 实现 |
| --- | --- |
| 账号 | 注册、用户名或手机号登录、退出时撤销令牌；scrypt 密码散列，旧 bcrypt 登录后升级 |
| 会话 | 私聊唯一约束、群聊、最近消息摘要、未读数和已读游标 |
| 消息 | 历史分页、引用预览、定位原消息、撤回；按发送编号去重，失败可重试 |
| 附件 | 服务端记录所有权，发送时校验；下载验证会话权限，短期签名链接，撤回后失效 |
| 交互 | 手机与桌面布局、中文输入法支持、可滚动弹窗、加载和错误反馈 |
| 演示 | 共用正式聊天界面，通过独立本地数据服务运行，支持刷新保存、重置和退出 |
| 发布 | 提交对应独立构建与虚拟环境，部署前回归、数据库备份、迁移、健康验证和应用恢复 |

## 技术

前端使用 Vue 3、Pinia、Vue Router、Vite 和 Axios。后端使用 FastAPI、SQLAlchemy 和 MySQL；图片校验使用 Pillow。Nginx 提供 HTTPS 与静态构建，systemd 管理 Uvicorn。

WebSocket 连接由单个 API 进程管理，生产服务固定为一个 worker。数据库调用在工作线程执行，消息和引用批量加载。扩展到多个实例时需要接入共享消息分发。

```text
backend/app/       API、权限、消息服务和数据库迁移
backend/tests/     独立 SQLite 回归测试
frontend/src/      界面、状态管理、网络与演示数据服务
frontend/public/  演示资源
deploy/           服务器发布、快照和恢复
scripts/          本机发布入口
docs/             审查证据、开发记录和运维说明
```

## 本地运行

需要 Python 3.10+、Node 22.22.2 或 24.15+ 和 MySQL 8。后端也支持通过 `DATABASE_URL` 使用 SQLite 进行本地体验。

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
# 编辑数据库连接与 JWT_SECRET_KEY
python -m app.db.migrate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm ci
npm run dev
```

开发前端通过 Vite 代理连接 `127.0.0.1:8000`。演示空间可以独立于后端运行。生产环境使用强随机密钥、明确的 CORS 来源和共享附件目录；配置见 [环境示例](backend/.env.example) 与 [部署说明](docs/deployment.md)。

## 验证与发布

```bash
cd backend
python -m pytest -q
cd ../frontend
npm test
npm run build
```

测试使用临时数据库和附件目录，不读取真实聊天记录。CI 检查后端权限、历史分页、幂等发送、撤回、WebSocket 与前端演示数据、消息状态和构建。

发布前提交并推送至 `main`，在 PowerShell 运行 `./scripts/deploy.ps1`。脚本会再次构建、测试、备份和核对线上提交；详情见 [发布与恢复](docs/deployment.md)。密钥、数据库快照和用户附件不进入仓库。
