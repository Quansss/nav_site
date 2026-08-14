# 迅鲨云导航站 - Docker 镜像
FROM python:3.11-slim

LABEL maintainer="nav_site" \
      description="迅鲨云 - 收藏链接导航站"

WORKDIR /app

# 安装依赖（利用层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY backend.py .
COPY static/ static/

# 数据目录（挂载卷，持久化 nav.db）
VOLUME ["/app/data"]

# 默认密钥（生产环境务必通过环境变量覆盖）
ENV NAV_SECRET=nav-site-secret-change-me \
    NAV_DB_PATH=/app/data/nav.db \
    PYTHONUNBUFFERED=1

EXPOSE 8766

# 非 root 运行（更安全）
RUN useradd -m -u 1000 navuser && \
    mkdir -p /app/data && \
    chown -R navuser:navuser /app
USER navuser

CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8766"]
