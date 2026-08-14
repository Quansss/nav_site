# 导航站 - SPEC.md

## 1. Concept & Vision

一个极简风格的收藏链接导航站。主页中央一个搜索框，下方展示收藏链接。支持按权限分级展示（游客/用户/管理员），管理员可发布/管理所有链接，普通用户可发布用户级链接。无过度装饰，干净利落。

## 2. Design Language

**Aesthetic**: 极简工具风格，类似简化版 Chrome 新标签页 + 一点点的卡片感
**Colors**:
- Background: `#0f172a` (深蓝黑)
- Surface: `#1e293b` (卡片背景)
- Border: `#334155`
- Primary: `#38bdf8` (亮蓝)
- Text: `#f1f5f9`
- Muted: `#64748b`
- Admin badge: `#f59e0b` (橙)
- User badge: `#34d399` (绿)
- Guest badge: `#94a3b8` (灰)

**Typography**: 系统字体栈，标题用 medium weight
**Motion**: 卡片 hover 微微上浮 + 边框发光过渡 (200ms ease)

## 3. Layout & Structure

```
┌──────────────────────────────────────────┐
│  [Logo/标题]          [登录/管理入口]      │  ← 顶栏
├──────────────────────────────────────────┤
│                                          │
│           ┌──────────────────┐            │
│           │  🔍  搜索框      │            │  ← 搜索区
│           └──────────────────┘            │
│                                          │
│  [全部] [游客可见] [用户可见] [管理员可见]  │  ← 筛选标签
│                                          │
│  ┌────────┐  ┌────────┐  ┌────────┐    │
│  │  卡片   │  │  卡片   │  │  卡片   │    │  ← 链接卡片网格
│  │  图标   │  │  图标   │  │  图标   │    │
│  │  标题   │  │  标题   │  │  标题   │    │
│  │  描述   │  │  描述   │  │  描述   │    │
│  └────────┘  └────────┘  └────────┘    │
│                                          │
└──────────────────────────────────────────┘
```

## 4. Features & Interactions

### 搜索
- 实时搜索（300ms 防抖），匹配标题/描述/URL
- 支持站内搜索（数据库已有链接）+ 站外搜索（百度/Google 转发）

### 链接展示
- 游客：看到 `guest_visible=true` 的链接
- 登录用户：看到 `guest_visible OR user_visible` 的链接
- 管理员：看到所有链接

### 发布链接（需登录）
- 点击「+」或「发布链接」按钮
- 填写：标题、URL、描述（可选）、分类（可选）、可见权限
- URL 自动获取网站 favicon

### 管理（仅管理员）
- 编辑 / 删除任意链接
- 用户管理（查看/修改用户角色）

### 登录
- 用户名 + 密码
- 默认管理员：admin / admin123（首次登录后应修改）

### 空状态
- 无链接时显示「暂无收藏链接，快去发布吧」

## 5. Component Inventory

### SearchBar
- 圆角输入框，左侧搜索图标
- focus 时边框高亮 (#38bdf8)
- 支持回车搜索 / 实时搜索切换

### LinkCard
- 左侧：favicon 图标（32x32）
- 中间：标题（可点击）+ 描述（单行截断）
- 右上角：可见性标签（游客/用户/管理员，彩色小标签）
- 悬停：上浮 + 边框亮蓝 + 出现编辑/删除按钮（管理员可见）

### VisibilityBadge
- 小圆角 pill，彩色背景
- 游客=灰 / 用户=绿 / 管理员=橙

### AddLinkModal
- 居中弹窗，遮罩层
- 表单：标题*、URL*、描述、分类、可见权限下拉

### AdminPanel
- 侧边抽屉或独立页面
- 链接列表 + 编辑表单
- 用户列表 + 角色切换

## 6. Technical Approach

### 后端：FastAPI + SQLite
- 零依赖部署，单文件数据库
- JWT Token 认证

### 数据模型
```
User:
  id, username, password_hash, role(admin/user), created_at

Link:
  id, title, url, description, category, favicon,
  visibility(guest/user/admin), created_by, created_at, updated_at
```

### API 设计
```
GET    /api/links                    # 按权限返回链接列表（游客/用户/管理员）
GET    /api/links/categories         # 返回已有分类列表
POST   /api/links                    # 发布链接（需登录 user/admin）
PUT    /api/links/{id}               # 编辑（需本人或管理员）
DELETE /api/links/{id}               # 删除（需本人或管理员）

POST   /api/auth/login               # 登录，返回 JWT token
GET    /api/auth/me                  # 当前用户信息
POST   /api/auth/logout              # 退出

GET    /api/admin/users              # 用户列表（需 admin）
POST   /api/admin/users              # 创建用户（需 admin）
PUT    /api/admin/users/{id}/role    # 修改角色（需 admin）
DELETE /api/admin/users/{id}          # 删除用户（需 admin）
```

**认证方式**：Bearer Token。登录成功后 header 携带 `Authorization: Bearer <token>`
**默认账号**：admin / admin123（admin 角色）
**后端端口**：8766
**Token 有效期**：7 天（in-memory，服务器重启后需重新登录）

### 前端
- 单 HTML + 内联 CSS/JS（零构建）
- Fetch API 调用后端
- 无框架，原生 JS
