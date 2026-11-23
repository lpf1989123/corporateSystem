# 前端 · 企业制度门户

本目录**仅含前端代码**（HTML / CSS / JS / 图片）。数据一律通过 AJAX 请求后端 API。

## 目录

```
frontend/
├── index.html      入口页
├── config.js       后端 API 地址（API_BASE）
├── app.js          前台：路由 / 首页 / 阅读 / 检索
├── admin.js        管理后台页面逻辑
├── style.css       前台样式
├── admin.css       后台样式
└── logo*.png / ka.png
```

## 配置后端地址

编辑 `config.js`：

```js
window.API_BASE = 'http://127.0.0.1:8080';
```

先启动 `backend` 服务，再将本目录部署到任意静态站点即可。

## 本地预览（任选其一）

本目录不含服务端代码。可用系统自带静态服务临时打开：

```bash
# 先启动后端
cd ../backend && python3 server.py

# 另开终端，在 frontend 目录用任意静态服务器托管
cd ../frontend
python3 -m http.server 3000
```

- 门户：http://127.0.0.1:3000  
- 后台：http://127.0.0.1:3000/#/admin  

生产环境用 Nginx / IIS 等托管本目录静态文件即可，无需 Node 构建。
