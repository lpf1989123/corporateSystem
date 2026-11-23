# 鲁信环境 · 企业制度门户

拆成 **2 个文件夹**：后端启动后提供 API；前端文件夹只放前端代码，通过 AJAX 调接口。

```
corporateSystem/
├── backend/      后端服务（启动后提供 /api）
└── frontend/     仅前端代码（HTML/CSS/JS）
```

---

## 一、快速启动

**1. 启动后端（提供接口）**

```bash
cd backend
python3 server.py
```

| 项 | 地址 |
| --- | --- |
| API | http://127.0.0.1:8080/api/ |
| 健康检查 | http://127.0.0.1:8080/api/health |
| 上传文件 | http://127.0.0.1:8080/uploads/ |

Windows 可双击 `backend/启动后端.bat`。

**2. 打开前端（仅静态文件）**

`frontend/` 内只有前端代码，不含服务端。用任意静态方式托管即可，例如：

```bash
cd frontend
python3 -m http.server 3000
```

| 入口 | 地址 |
| --- | --- |
| 前台门户 | http://127.0.0.1:3000 |
| 管理后台 | http://127.0.0.1:3000/#/admin |

**默认管理员：`admin` / `admin888`**（首次登录后请修改）

前端通过 `frontend/config.js` 的 `API_BASE` 指向后端；跨域由后端 CORS 处理。

---

## 二、两个文件夹各自职责

| 文件夹 | 内容 | 职责 |
| --- | --- | --- |
| [backend](./backend/README.md) | `server.py`、数据库、上传目录 | 启动服务，对外提供 API |
| [frontend](./frontend/README.md) | `index.html` / JS / CSS / 图片 | 页面展示，AJAX 请求后端 |

---

## 三、功能概要

**前台**：首页概览、分类浏览、制度阅读、全文检索、打印导出  

**后台**：数据概览、制度 CRUD、Markdown 编辑与上传、账号与设置、操作日志  

---

## 四、部署建议

1. **后端**：服务器上运行 `python3 server.py`（或注册为服务）。可用环境变量 `HOST` / `PORT` / `CORS_ORIGIN`。
2. **前端**：用 Nginx / IIS 托管 `frontend/`；修改 `config.js` 的 `API_BASE` 为后端实际地址。
3. **备份**：备份 `backend/data/portal.db` 与 `backend/uploads/`。

---

## 五、常见问题

**Q：前端提示无法连接后端？**  
确认后端已启动，且 `frontend/config.js` 的 `API_BASE` 与后端地址一致。

**Q：端口被占用？**  
`PORT=8090 python3 server.py`（后端）；前端换端口时同步检查 CORS / `API_BASE`。

**Q：忘记管理员密码？**  
在 `backend` 目录执行：

```python
import sqlite3, hashlib, secrets
c = sqlite3.connect('data/portal.db')
salt = secrets.token_hex(8)
c.execute("UPDATE users SET password=?, salt=? WHERE username='admin'",
          (hashlib.sha256(('新密码' + salt).encode()).hexdigest(), salt))
c.commit()
```
