# 鲁信环境 · 企业制度门户

把公司内部制度做成网页：**美观、可搜索、带管理后台**。

本仓库已拆分为 **前端** 与 **后端** 两个独立项目：后端单独部署提供 API，前端通过 AJAX 请求接口获取数据。

```
corporateSystem/
├── backend/     Python API（SQLite + http.server）
└── frontend/    静态门户（HTML/CSS/JS）
```

---

## 一、快速启动

需要两个终端（或两个窗口）：

**1. 启动后端**

```bash
cd backend
python3 server.py
```

默认接口：http://127.0.0.1:8080  

**2. 启动前端**

```bash
cd frontend
python3 serve.py
```

| 入口 | 地址 | 说明 |
| --- | --- | --- |
| 前台门户 | http://127.0.0.1:3000 | 员工查阅、搜索 |
| 管理后台 | http://127.0.0.1:3000/#/admin | 管理员维护制度 |

**默认管理员：`admin` / `admin888`**（首次登录后请立即修改）

Windows 也可分别双击 `backend/启动后端.bat`、`frontend/启动前端.bat`。

前端通过 `frontend/config.js` 中的 `API_BASE` 指向后端；跨域由后端 CORS 处理。

---

## 二、功能清单

### 前台门户（员工使用）

- **首页** —— 英雄区 + 数据概览、核心制度推荐、全库分类浏览
- **全部制度** —— 按分类筛选
- **制度阅读** —— 章节目录、进度条、元信息、打印 / 导出 PDF、复制链接
- **全文检索** —— 关键词精确到条款，命中高亮
- **使用说明** —— 门户定位、使用方法、效力顺序、反馈渠道

### 管理后台（管理员使用）

| 模块 | 能力 |
| --- | --- |
| 数据概览 | KPI、查阅量排行、制度清单 |
| 制度管理 | 新增 / 编辑 / 删除、分类与版本、发布状态 |
| 内容编辑器 | Markdown 编辑 + 实时预览 + 文件上传 |
| 账号管理 | 新增管理员、修改密码、删除账号 |
| 系统设置 | 门户名称与标语、修改自身密码 |
| 系统日志 | 登录与制度变更等操作留痕 |

---

## 三、预置数据

系统首次启动自动导入三部制度：

1. **员工手册**（人力资源）—— 11 章 54 条
2. **差旅费报销管理办法**（财务制度）
3. **信息安全管理规定**（信息技术）

---

## 四、分项目说明

| 项目 | 文档 | 职责 |
| --- | --- | --- |
| [backend](./backend/README.md) | 后端 API | 鉴权、SQLite、上传、CORS |
| [frontend](./frontend/README.md) | 前端静态站 | 页面与 AJAX 调用 |

### 典型部署

1. **后端**：内网服务器上运行 `python server.py`（或注册为服务）。可用 `PORT`、`HOST`、`CORS_ORIGIN` 调整。
2. **前端**：用 Nginx / IIS 托管 `frontend/` 静态文件；修改 `config.js` 的 `API_BASE` 为后端地址。
3. **备份**：备份 `backend/data/portal.db` 与 `backend/uploads/`。

---

## 五、常见问题

**Q：前端提示无法连接后端？**  
确认后端已启动，且 `frontend/config.js` 的 `API_BASE` 与后端实际地址一致（含协议与端口）。

**Q：端口被占用？**  
后端：`set PORT=8090 && python3 server.py`  
前端：`set PORT=3001 && python3 serve.py`，并同步改 `API_BASE` / `CORS_ORIGIN`（如需要）。

**Q：忘记管理员密码？**  
删除 `backend/data/portal.db` 会重置全部数据。若只想重置密码，在 `backend` 目录执行：

```python
import sqlite3, hashlib, secrets
c = sqlite3.connect('data/portal.db')
salt = secrets.token_hex(8)
c.execute("UPDATE users SET password=?, salt=? WHERE username='admin'",
          (hashlib.sha256(('新密码' + salt).encode()).hexdigest(), salt))
c.commit()
```

**Q：如何把 Word/PDF 制度快速录入？**  
后台「新增制度」→ 上传原件存档，再把正文粘贴为 Markdown（`## 第一章`、`### 第一条`、`| 表格 |`）。
