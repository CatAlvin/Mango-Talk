# Mango Talk 发布与恢复

正式站点是 [mango-talk.chenglan.tech](https://mango-talk.chenglan.tech)。登录、实时聊天和演示入口使用同一个生产构建。每次发布对应 GitHub `main` 的一个完整提交，网页的 `/release.json` 可用于核对线上版本。

## 生产环境

| 项目 | 配置 |
| --- | --- |
| SSH | 本机 SSH config 中的 `ChengLanServer`，使用已有密钥 |
| 项目目录 | `/home/projects/mango-talk` |
| Git | `git@github.com:CatAlvin/mango-talk.git`，`main` |
| 后端 | `mango-talk-api.service`，`127.0.0.1:8000` |
| 前端 | Nginx 读取 `.deploy/current/frontend/dist` |
| Nginx 站点文件 | `/etc/nginx/sites-available/mango-talk` |
| MySQL | 配置读取 `backend/.env`，发布前创建一致性快照 |
| 附件与日志 | 项目根目录下的 `uploads/`、`logs/` |
| 历史版本 | `.deploy/releases/` |
| 恢复检查点 | `.deploy/backups/`，仅 root 可读 |

API 使用 `mango-talk` 系统用户和一个 Uvicorn worker。当前 WebSocket 连接与在线状态保存在进程内，扩展 worker 数量前需要共享消息分发。服务由 systemd 负责重启，警告与异常可通过 `journalctl -u mango-talk-api.service` 查看；请求日志由 Nginx 统一记录，Uvicorn 不记录访问行和 WebSocket 连接中的查询令牌。

Nginx 只代理 Mango Talk 的 API 和 WebSocket 路径，不使用公开附件目录 alias。附件请求必须经过后端权限检查。本站访问日志记录路径，不记录查询参数和 Referer，避免将 WebSocket 与附件访问令牌写入 access log。TLS 证书沿用本站已有配置，发布脚本不会改动 Certbot 或同服务器其他站点的配置。

登录和注册共享每 IP 每分钟 10 次的请求配额，允许 10 次突发请求；超额返回 `429` 和可直接显示的中文提示。该限制只作用于认证端点，演示入口和演示交互无需认证请求。HTTPS 响应启用一年 HSTS，仅限 Mango Talk 当前主机，不包含其他子域；CSP 限制脚本为本站生产资源，保留 Vue 所需的内联样式、图片 data/blob 和本站 WebSocket 连接。HTML、静态资源与构建清单的独立 location 均保留安全响应头，避免缓存设置覆盖 Nginx 的响应头继承。

2026-10-09 的服务器调查确认：线上已经使用静态构建和 HTTPS；MySQL、API、Nginx 正常。现有证书同时包含 Mango Talk 和图像处理站点，当前有效期至 2026-11-09，续期由服务器现有 Certbot 配置负责。服务器 Node 通过 nvm 安装，本脚本在本机构建前端以避免非交互 SSH 的 PATH 差异。

## 发布

本机需要 Git、Node 22.22.2 或 24.15+、OpenSSH 和 Windows `tar`。使用 npm 构建；只有 pnpm 的环境会通过 `pnpm --package=npm@11.6.2 dlx npm` 运行同一套 npm 命令。服务器需要 Git、Python 3.10、venv、MySQL 客户端、Nginx、systemd、`flock`，并能下载 Python 依赖。

1. 完成代码审查、前后端回归和浏览器检查，将代码、测试、迁移及发布脚本一起提交。
2. 推送该提交至 GitHub `main`。本机和服务器的工作区都应无未提交的业务改动。
3. 在项目根目录运行：

```powershell
git push origin main
./scripts/deploy.ps1
```

脚本不创建提交、不推送代码。它检查本机 HEAD 与 GitHub `main` 一致，重新执行 `npm ci` 和生产构建，将构建及该提交内的发布工具上传到服务器的独立临时目录。服务器再从 GitHub 拉取同一提交。

服务器按以下顺序发布：

1. 获取部署锁，检查目录、分支、工作区和提交，导出独立版本目录。
2. 创建该版本的 Python 虚拟环境，安装正式及测试依赖，运行 `pytest` 和语法检查。
3. 读取当前 TLS 文件路径，保存此前的站点配置、systemd unit、环境文件、Git 提交及版本链接。
4. 停止 Mango Talk API，将 MySQL 快照写入仅 root 可读的压缩文件，并验证压缩文件可完整读取。
5. 执行 `python -m app.db.migrate`。迁移必须可重复执行，并与此前的应用版本兼容。
6. 原子切换 `.deploy/current`，安装本站 Nginx 和服务配置，通过 `nginx -t` 后启动 API。
7. 验证本地与 HTTPS 数据库健康、构建提交和演示路由，再将服务器 Git 工作区快进到发布提交。

安装依赖和运行测试发生在停服前；备份、迁移及重启期间聊天连接会短暂断开。新旧版本保留各自的依赖环境，恢复时可以直接切换。

生产环境文件不会写入 Git，也不会打印到控制台。至少配置 `JWT_SECRET_KEY`（32 字符以上）、MySQL 连接参数或 `DATABASE_URL`。正式服务、数据库快照和迁移显式设置 `APP_ENV=production`、`CORS_ORIGINS=https://mango-talk.chenglan.tech` 和共享 `UPLOAD_ROOT`，保证历史附件始终映射到项目根目录的存储。备份程序从实际 `DATABASE_URL` 解析连接，不在命令行参数中暴露数据库密码。现行环境文件权限为 `root:mango-talk` 的 `0640`（仅 root 与服务组可读），部署前验证服务用户确实可读；检查点内的副本为 root 独占的 `0600`。

systemd 仍从现有 `.env` 读取密钥与数据库连接；`ExecStart` 通过 `/usr/bin/env` 在启动 Uvicorn 时覆盖生产环境、本站 CORS、共享上传目录和 Python 运行参数。因此历史 `.env` 中同名配置无法覆盖正式运行值，也无需改写密钥文件。

## 发布后检查

```powershell
ssh ChengLanServer "systemctl is-active mango-talk-api.service; nginx -t; curl -fsS https://mango-talk.chenglan.tech/health/db; curl -fsS https://mango-talk.chenglan.tech/release.json"
ssh ChengLanServer "journalctl -u mango-talk-api.service -n 50 --no-pager"
```

还需用浏览器核对登录、登录页演示入口、移动端布局、双账号实时消息、重连、回复、撤回和成员附件访问。公开演示的发送行为应只改变当前观看者的本地会话。匿名附件请求、非成员请求和身份过期请求应无法读取私聊附件。

## 应用恢复

测试、备份和配置验证失败时，脚本会停止发布。开始切换后的异常会恢复此前的应用链接与配置，并重启此前的服务。快照路径保留在输出中；成功部署的最近恢复检查点还保存于 `.deploy/latest-backup`。

上线后需要主动撤回版本时，先读取该路径并核对检查点，再执行：

```bash
cat /home/projects/mango-talk/.deploy/latest-backup
bash /home/projects/mango-talk/.deploy/current/deploy/rollback.sh /home/projects/mango-talk/.deploy/backups/检查点目录
```

恢复脚本只接受 Mango Talk 备份目录，并要求服务器仍在对应发布提交且无业务修改。它会恢复此前的应用和本站配置，同时将服务器 Git 工作区恢复到此前提交。GitHub `main` 保留发布记录；修复后提交新版本再发布。

应用恢复保留数据库中的新消息和兼容迁移。它不会用旧快照覆盖上线后的数据，也不会覆盖可能已经轮换的环境文件。

## 数据库恢复

只有数据库确实需要恢复、且已经确认恢复点之后的数据处理方案时，才使用此流程。SQL 快照会覆盖其中的表数据，应在 API 停止且没有其他写入者的情况下执行。

```bash
systemctl stop mango-talk-api.service
cd /home/projects/mango-talk/.deploy/current/backend
.venv/bin/python ../deploy/database_snapshot.py restore \
  --backend /home/projects/mango-talk/.deploy/current/backend \
  --snapshot /home/projects/mango-talk/.deploy/backups/检查点目录/database.sql.gz \
  --confirm-database-restore
# 根据恢复点选择对应应用版本；检查数据库健康后再开放 API。
```

备份目录包含生产环境文件与数据库，禁止对外下载或打包到作品仓库。定期将快照复制到受控的异机备份位置，并以独立数据库演练恢复。发布脚本保留历史版本和检查点，由维护者根据空间和恢复需求清理；不会自动删除可恢复版本。
