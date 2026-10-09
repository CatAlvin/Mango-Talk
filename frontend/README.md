# Mango Talk 前端

Vue 3、Pinia、Vue Router 与 Vite 构建的即时聊天界面。正式账号和演示空间使用相同的组件与交互流程。

## 本地运行

使用 Node.js 24.15+，或 Node.js 22.22.2+。

```sh
npm ci
npm run dev
```

开发地址为 `http://127.0.0.1:5173`，API 与 WebSocket 代理到 `127.0.0.1:8000`。生产环境部署 `npm run build` 生成的 `dist`，由同源反向代理提供 API 和 WebSocket。

`VITE_API_BASE_URL` 默认为 `/`；WebSocket 始终使用页面所在域名。配置参考 `.env.example`。

## 演示空间

登录页可直接进入，也可访问 `/demo`。包含群聊、私聊、回复、图片与文件，可发送和撤回消息、创建会话、加载历史、重置或退出。

演示会话的开关使用 `sessionStorage`，数据保存到独立的 `localStorage` 键。`lib/api.js` 将演示请求全部交给 `lib/demo.js`，未知请求同样不会进入真实网络。真实账号的认证信息不被演示读写；演示页面不建立 WebSocket。

## 验证

```sh
npm test
npm run build
```

Vitest 覆盖发送任务幂等重试、输入法、上传取消、草稿保存、历史与实时消息竞态、窗口连续性、离线撤回、重连游标与心跳，以及演示隔离和主要界面流程。

## 代码结构

- `views`：登录、注册与聊天页面。
- `components`：群聊和私聊创建对话框。
- `composables`：发送任务、实时连接、页面协调与对话框焦点管理。
- `stores`：身份、会话与消息状态。
- `lib`：HTTP、本地演示、请求路由及消息工具。

每次发送生成稳定的 `client_message_id`，HTTP 响应确认提交结果，WebSocket 同步其他参与者。上传任务绑定原会话，切换会话即取消。历史以游标分页，重连从连接前快照补齐新消息，并按已加载 ID 刷新撤回状态。
