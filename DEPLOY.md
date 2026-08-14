# 部署教程 - 迅鲨云导航站

本教程覆盖三种部署方式：**Windows 本机**、**Linux 服务器（systemd）**、**Docker**。

---

## 方式一：Windows 本机部署

### 1. 安装 Python

1. 前往 https://www.python.org/downloads/ 下载 Python 3.11+（64位）
2. 安装时 **务必勾选** `Add Python to PATH`
3. 验证：
   ```powershell
   python --version
   ```

### 2. 获取代码

```powershell
git clone https://github.com/<你的用户名>/nav_site.git
cd nav_site
```

> 没有 Git？直接下载 ZIP 解压也可以。

### 3. 创建虚拟环境（推荐）

```powershell
python -m venv venv
venv\Scripts\activate
```

激活成功后，命令行前缀会出现 `(venv)`。

### 4. 安装依赖

```powershell
pip install -r requirements.txt
```

### 5. 配置密钥（可选但推荐）

```powershell
$env:NAV_SECRET = "换成你的随机字符串"
```

### 6. 启动

```powershell
python backend.py
```

看到以下输出即成功：

```
[OK] admin created        # 首次启动自动创建管理员
INFO: Uvicorn running on http://0.0.0.0:8766
```

### 7. 访问

- 本机：http://localhost:8766
- 局域网其他设备：`http://<你的IP>:8766`（需防火墙放行 8766 端口）

> **防火墙放行（Windows）**：
> 1. 设置 → 网络和 Internet → Windows 防火墙 → 高级设置
> 2. 入站规则 → 新建规则 → 端口 → TCP 8766 → 允许连接

### 8. 开机自启（可选）

1. `Win + R` 输入 `shell:startup` 回车
2. 新建 `start_nav.bat`：
   ```bat
   @echo off
   cd /d C:\path\to\nav_site
   venv\Scripts\python backend.py
   ```
3. 双击运行一次测试，之后开机自动启动

---

## 方式二：Linux 服务器部署（systemd）

### 1. 安装 Python 与依赖

```bash
# Debian/Ubuntu
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git

# CentOS/RHEL
sudo yum install -y python3 python3-pip git
```

### 2. 获取代码

```bash
sudo mkdir -p /opt/nav_site
sudo chown $USER:$USER /opt/nav_site
git clone https://github.com/<你的用户名>/nav_site.git /opt/nav_site
cd /opt/nav_site
```

### 3. 虚拟环境与依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 先手动跑通

```bash
export NAV_SECRET="你的随机字符串"
python backend.py
```

浏览器访问 `http://<服务器IP>:8766` 确认正常，然后 `Ctrl+C` 停止。

### 5. 创建 systemd 服务

```bash
sudo tee /etc/systemd/system/nav_site.service > /dev/null <<'EOF'
[Unit]
Description=Nav Site (收藏导航站)
After=network.target

[Service]
WorkingDirectory=/opt/nav_site
ExecStart=/opt/nav_site/venv/bin/python -m uvicorn backend:app --host 0.0.0.0 --port 8766
Restart=always
RestartSec=3
Environment=NAV_SECRET=你的随机字符串

[Install]
WantedBy=multi-user.target
EOF
```

### 6. 启动与开机自启

```bash
sudo systemctl daemon-reload
sudo systemctl enable nav_site
sudo systemctl start nav_site
sudo systemctl status nav_site   # 查看状态
journalctl -u nav_site -f        # 查看日志
```

### 7. 防火墙

```bash
# Ubuntu（ufw）
sudo ufw allow 8766/tcp

# CentOS（firewalld）
sudo firewall-cmd --permanent --add-port=8766/tcp
sudo firewall-cmd --reload
```

---

## 方式三：Docker 部署

### 1. Dockerfile

在项目根目录创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend.py .
COPY static/ static/

ENV NAV_SECRET=change-me-in-production

EXPOSE 8766

CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8766"]
```

### 2. 构建与运行

```bash
docker build -t nav_site .

# 数据持久化到宿主机 ./data
mkdir -p data
docker run -d \
  --name nav_site \
  -p 8766:8766 \
  -v $(pwd)/data:/app \
  -e NAV_SECRET=你的随机字符串 \
  --restart unless-stopped \
  nav_site
```

> 注意：`-v $(pwd)/data:/app` 挂载整个 /app 目录，保证 `nav.db` 持久化在宿主机。

### 3. 验证

```bash
docker logs -f nav_site
curl http://localhost:8766/api/links
```

---

## 常见问题（FAQ）

### Q1: 复制账号密码失败，提示 `Cannot read properties of undefined (reading 'writeText')`

**原因**：浏览器剪贴板 API 需要 HTTPS 安全上下文，局域网 HTTP 下不可用。

**解决**：前端已内置降级方案（自动使用 `execCommand('copy')`），无需处理。若仍失败，请强制刷新（Ctrl+F5）清除缓存。

### Q2: 刷新页面后自动退出登录

**原因**：旧版本 token 存内存，后端重启即失效。

**解决**：当前版本已改为无状态 JWT，后端重启不影响已登录用户。请更新代码并重启后端。

### Q3: 注册后无法登录？

注册采用**管理员审核制**。需要管理员登录后在「管理 → 待审核用户」中点击「通过」，才能登录。

### Q4: 如何修改默认管理员密码？

登录默认管理员（`971954959@qq.com` / `admin123`）→ 右上角「修改密码」。

### Q5: 数据库在哪里？如何备份？

数据库是项目目录下的 `nav.db` 单文件。直接复制该文件即可备份/迁移，新环境启动时自动读取。

### Q6: 端口被占用怎么办？

```bash
# 改用其他端口（如 9000）
uvicorn backend:app --host 0.0.0.0 --port 9000
```

### Q7: 修改代码后不生效？

开发模式使用 `python backend.py` 启动时带 `--reload`，修改 `backend.py` 自动生效（前端 HTML 直接刷新即可）。生产环境建议关闭 reload。

### Q8: 如何让网站通过 HTTPS 访问？

推荐使用 Caddy（自动 HTTPS）：

```bash
# Caddyfile
nav.example.com {
    reverse_proxy 127.0.0.1:8766
}
```

```bash
caddy run
```

---

## 安全清单

- [ ] 修改默认管理员密码
- [ ] 设置强随机 `NAV_SECRET`
- [ ] 生产环境关闭 reload（使用 `uvicorn` 直接启动）
- [ ] 配置 HTTPS（推荐）
- [ ] 定期备份 `nav.db`
- [ ] 如需公网访问，建议加认证（如 Nginx basic auth 或 VPN）
