# 迅鲨云 - 收藏链接导航站

一个极简风格的收藏链接导航站，支持多用户、权限分级、管理员审核，适合家庭/团队内部使用。

![深蓝黑极简界面](https://img.shields.io/badge/style-minimal-0f172a)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)
![SQLite](https://img.shields.io/badge/db-SQLite-003B57)
![零构建](https://img.shields.io/badge/frontend-zero--build-38bdf8)

---

## ✨ 功能特性

- 🔍 **实时搜索**：300ms 防抖，匹配标题/描述/URL
- 👥 **多用户体系**：邮箱注册 + 管理员审核
- 🛡️ **三级权限**：游客 / 用户 / 管理员，按角色展示链接
- 🔐 **仅管理员可发布**：普通用户只能浏览，管理员负责内容管理
- 📋 **账号密码凭据**：链接可附带账号/密码，一键复制（仅管理员与创建者可见）
- 🔑 **密码管理**：用户可自助修改密码，管理员可重置任意用户密码
- 🔢 **自定义排序**：管理员可置顶/下移链接，或直接编辑排序值，重要链接放前面
- 🏷️ **分类标签**：链接支持分类，自动聚合
- 📱 **响应式**：桌面/移动端自适应

## 🧱 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.10+ / FastAPI / Uvicorn |
| 数据库 | SQLite（零配置，单文件） |
| 认证 | 无状态 JWT（HMAC-SHA256，标准库实现，无第三方依赖） |
| 前端 | 原生 HTML + CSS + JS（单文件，零构建） |

## 🚀 快速开始

### 环境要求

- Python 3.10+（推荐 3.11）
- 无需 Node.js / 无需数据库服务

### 安装与启动

```bash
# 1. 克隆仓库
git clone https://github.com/<你的用户名>/nav_site.git
cd nav_site

# 2. （可选）创建虚拟环境
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动（默认端口 8766）
python backend.py
# 或指定端口
uvicorn backend:app --host 0.0.0.0 --port 8766
```

浏览器访问 **http://localhost:8766**

### 默认管理员

| 项 | 值 |
|---|---|
| 邮箱 | `971954959@qq.com` |
| 密码 | `admin123` |

> ⚠️ **首次登录后请立即修改密码**（右上角 → 修改密码）。

### 局域网访问

```bash
uvicorn backend:app --host 0.0.0.0 --port 8766
```

然后用 `http://<你的局域网IP>:8766` 访问（防火墙需放行 8766 端口）。

---

## 📖 使用指南

### 角色与权限

| 角色 | 浏览 | 发布/编辑/删除链接 | 查看凭据 | 用户管理 |
|---|---|---|---|---|
| 游客（未登录） | ✅ 仅 guest 级 | ❌ | ❌ | ❌ |
| 用户 | ✅ guest + user 级 | ❌ | ❌ | ❌ |
| 管理员 | ✅ 全部 | ✅ | ✅ | ✅ |

### 注册流程

1. 点击右上角「注册」，填写邮箱和密码
2. 提交后账号状态为 **待审核（pending）**，无法登录
3. 管理员在「管理 → 待审核用户」中点「通过」，即可登录

### 链接可见性

发布链接时选择可见范围：

- **游客可见**：所有人（含未登录）可见
- **用户可见**：仅登录用户可见
- **管理员可见**：仅管理员可见

### 账号密码凭据

发布链接时可附带账号/密码（可选）。卡片会显示凭据区域，点击复制按钮一键复制。

> 凭据以明文存储于数据库，**仅管理员和链接创建者可见**，请勿存放高敏感信息。

---

## 🔌 API 文档

基础地址：`http://<host>:8766`

### 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/auth/register` | 注册（邮箱+密码，进入待审核） |
| POST | `/api/auth/login` | 登录，返回 JWT token |
| GET | `/api/auth/me` | 当前用户信息 |
| POST | `/api/auth/logout` | 退出（客户端删除 token 即可） |

### 链接

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/links?q=&category=` | 链接列表（按角色过滤） | 所有人 |
| GET | `/api/links/categories` | 分类列表 | 所有人 |
| POST | `/api/links` | 发布链接 | 仅管理员 |
| PUT | `/api/links/reorder` | 批量设置排序（ids 顺序即展示顺序） | 仅管理员 |
| PUT | `/api/links/{lid}` | 编辑链接 | 仅管理员 |
| DELETE | `/api/links/{lid}` | 删除链接 | 仅管理员 |

### 个人

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/me/password` | 修改自己的密码（需旧密码） |

### 管理员

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/admin/users` | 用户列表 |
| GET | `/api/admin/pending-users` | 待审核用户列表 |
| POST | `/api/admin/users/{uid}/approve` | 通过/拒绝审核（`{"action":"approve"}`） |
| PUT | `/api/admin/users/{uid}/role` | 修改角色 |
| POST | `/api/admin/users` | 创建用户 |
| POST | `/api/admin/users/{uid}/reset-password` | 重置用户密码 |
| DELETE | `/api/admin/users/{uid}` | 删除用户 |

### 认证方式

所有需要登录的接口，请求头携带：

```
Authorization: Bearer <token>
```

Token 为无状态 JWT（HMAC-SHA256 签名），有效期 7 天，**后端重启后依然有效**。

### 链接数据模型

```json
{
  "id": 1,
  "title": "GitHub",
  "url": "https://github.com",
  "description": "代码托管平台",
  "category": "开发",
  "favicon": "https://github.com/favicon.ico",
  "visibility": "guest",        // guest | user | admin
  "created_by": 1,
  "created_at": "2026-08-13T18:00:00",
  "can_edit": true,
  "username": "my_account",      // 凭据，非管理员/创建者为空
  "password": "secret",          // 凭据，非管理员/创建者为空
  "has_credentials": true
}
```

---

## 🗂️ 项目结构

```
nav_site/
├── backend.py            # FastAPI 后端（单文件，含数据库初始化）
├── requirements.txt      # Python 依赖
├── Dockerfile            # Docker 镜像定义（python:3.11-slim）
├── docker-compose.yml    # Docker Compose 编排
├── static/
│   └── index.html        # 前端（单文件，零构建）
├── data/                 # 数据目录（Docker 挂载卷，含 nav.db）
├── nav.db                # SQLite 数据库（源码部署时生成于当前目录）
└── SPEC.md               # 设计规格文档
```

## ⚙️ 配置项

| 环境变量 | 说明 | 默认值 |
|---|---|---|
| `NAV_SECRET` | JWT 签名密钥（生产环境务必修改） | `nav-site-secret-change-me` |
| `NAV_DB_PATH` | SQLite 数据库文件路径 | `nav.db`（当前目录） |

```bash
# Linux/macOS
export NAV_SECRET="your-strong-random-secret"
export NAV_DB_PATH="/data/nav.db"

# Windows PowerShell
$env:NAV_SECRET = "your-strong-random-secret"
$env:NAV_DB_PATH = "D:\\data\\nav.db"
```

## 🐳 Docker 部署（推荐）

> 项目已包含 `Dockerfile` 与 `docker-compose.yml`，支持直接构建或镜像导入两种方式。

### 方式一：源码构建（可自定义代码）

```bash
git clone https://github.com/<你的用户名>/nav_site.git
cd nav_site

# 构建并启动
docker compose up -d --build
```

### 方式二：镜像导入（无需源码/构建）

```bash
# 1. 加载镜像（tar 文件已随发布包提供，或自行导出）
docker load -i nav_site-image.tar

# 2. 验证
docker images | grep nav_site
# → nav_site-nav_site   latest   ...   172MB
```

`docker-compose.yml` 完整内容：

```yaml
services:
  nav_site:
    # 方式一：源码构建
    build: .
    # 方式二：镜像导入（先 docker load 再启用）
    # image: nav_site-nav_site:latest
    container_name: nav_site
    restart: unless-stopped
    ports:
      - "8766:8766"
    environment:
      - NAV_SECRET=${NAV_SECRET:-nav-site-secret-change-me}
      - NAV_DB_PATH=/app/data/nav.db
    volumes:
      - ./data:/app/data
```

启动：

```bash
docker compose up -d
# 访问 http://<主机IP>:8766
```

数据保存在宿主机 `./data/nav.db`，容器删除/重建不丢失。

### 导出镜像（跨平台移植）

```bash
# 在已构建的机器上
docker save nav_site-nav_site:latest -o nav_site-image.tar

# 在目标机器上（无源码也可）
docker load -i nav_site-image.tar
docker run -d \
  --name nav_site \
  -p 8766:8766 \
  -e NAV_SECRET=your-secret \
  -e NAV_DB_PATH=/app/data/nav.db \
  -v $(pwd)/data:/app/data \
  nav_site-nav_site:latest
```

> 镜像基于 `python:3.11-slim`（约 172MB），容器内以非 root 用户运行。

## 🖥️ 源码部署（无 Docker）

```bash
# 1. 克隆仓库
git clone https://github.com/<你的用户名>/nav_site.git
cd nav_site

# 2. （可选）创建虚拟环境
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动（默认端口 8766）
python backend.py
# 或指定端口
uvicorn backend:app --host 0.0.0.0 --port 8766
```

浏览器访问 **http://localhost:8766**

### 局域网访问

```bash
uvicorn backend:app --host 0.0.0.0 --port 8766
```

然后用 `http://<你的局域网IP>:8766` 访问（防火墙需放行 8766 端口）。

## 🛠️ 生产部署建议

- 推荐使用 Docker 方式（自愈重启、数据卷持久化）
- 反向代理 Nginx/Caddy 并配置 HTTPS（复制功能依赖安全上下文）
- 建议定期备份数据（Docker 方式备份 `./data/nav.db`）
- 修改默认管理员密码与 `NAV_SECRET`

### 示例：Nginx 反向代理

```nginx
server {
    listen 80;
    server_name nav.example.com;

    location / {
        proxy_pass http://127.0.0.1:8766;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 示例：systemd 服务（Linux 源码部署）

```ini
[Unit]
Description=Nav Site
After=network.target

[Service]
WorkingDirectory=/opt/nav_site
ExecStart=/usr/bin/python3 -m uvicorn backend:app --host 0.0.0.0 --port 8766
Restart=always
Environment=NAV_SECRET=your-strong-random-secret

[Install]
WantedBy=multi-user.target
```

---

## 📄 License

MIT
