# 前端 · 企业制度门户

纯静态页面，通过 AJAX（`fetch`）请求后端 API 获取数据。

## 启动

先启动后端（默认 `http://127.0.0.1:8080`），再：

```bash
cd frontend
python3 serve.py
```

Windows 也可双击 `启动前端.bat`。

| 入口 | 地址 |
| --- | --- |
| 前台门户 | http://127.0.0.1:3000 |
| 管理后台 | http://127.0.0.1:3000/#/admin |

## 配置后端地址

编辑 `config.js`：

```js
window.API_BASE = 'http://127.0.0.1:8080';
```

若后端部署在其他机器或端口，改成实际地址即可。上传附件、制度内图片也会自动拼到该基址下的 `/uploads/`。

## 环境变量（静态服务）

| 变量 | 说明 | 默认 |
| --- | --- | --- |
| `HOST` | 监听地址 | `127.0.0.1` |
| `PORT` | 端口 | `3000` |

## 目录

```
frontend/
├── index.html      入口
├── config.js       后端 API_BASE
├── app.js          前台：路由 / 首页 / 阅读 / 检索
├── admin.js        后台
├── style.css / admin.css
├── logo*.png / ka.png
├── serve.py        本地静态服务
└── 启动前端.bat
```

生产环境可将本目录部署到 Nginx / IIS 等任意静态站点，无需 Node 构建。
