# 后端 · 企业制度门户 API

独立部署的 Python 后端，提供 REST 接口与上传文件访问。纯标准库，零第三方依赖。

## 启动

```bash
cd backend
python3 server.py
```

Windows 也可双击 `启动后端.bat`。

| 项 | 默认 |
| --- | --- |
| 地址 | http://127.0.0.1:8080 |
| 健康检查 | GET `/api/health` |
| 上传资源 | `/uploads/...` |
| 管理员 | `admin` / `admin888` |

## 环境变量

| 变量 | 说明 | 默认 |
| --- | --- | --- |
| `HOST` | 监听地址 | `0.0.0.0` |
| `PORT` | 端口 | `8080` |
| `CORS_ORIGIN` | 允许的前端 Origin，多个用逗号分隔 | `*` |

示例：

```bash
set PORT=8090
set CORS_ORIGIN=http://127.0.0.1:3000,http://192.168.1.10:3000
python3 server.py
```

## 主要接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| GET | `/api/settings` | 门户设置 |
| GET | `/api/stats` | 统计概览 |
| GET | `/api/categories` | 分类列表 |
| GET/POST | `/api/policies` | 制度列表 / 新增 |
| GET/PUT/DELETE | `/api/policies/:id` | 制度详情 / 改 / 删 |
| GET | `/api/search?q=` | 全文检索 |
| POST | `/api/login` | 登录，返回 token |
| GET | `/api/me` | 当前用户（需 `X-Token`） |
| POST | `/api/upload` | 附件上传（multipart） |

鉴权：请求头 `X-Token: <登录返回的 token>`。

## 目录

```
backend/
├── server.py           API 服务
├── 启动后端.bat
├── data/portal.db      SQLite（自动创建）
├── data/handbook_doc.json
├── uploads/            上传附件
├── import_handbook.py  手册导入脚本
└── import_pdf_policy.py
```

## 备份

备份 `data/portal.db` 与 `uploads/` 即可。
