#!/bin/bash
set -e

cd "$(dirname "$0")/../docker"

echo "=== TLS 星群論壇部署腳本 ==="
echo ""

# Generate password
PG_PASSWORD=$(openssl rand -base64 24)
export PG_PASSWORD

# Create ssl directory
mkdir -p nginx/ssl

# Pull images first
echo "[1/5] 拉取 Docker 映像..."
docker compose -f docker-compose.forum.yml pull

# Start services
echo "[2/5] 啟動服務..."
PG_PASSWORD=$PG_PASSWORD docker compose -f docker-compose.forum.yml up -d

# Wait for PostgreSQL
echo "[3/5] 等待 PostgreSQL 就緒..."
for i in {1..30}; do
    if docker exec nodebb_postgres pg_isready -U nodebb > /dev/null 2>&1; then
        echo "  PostgreSQL 就緒"
        break
    fi
    echo "  等待中... ($i/30)"
    sleep 2
done

# Wait for NodeBB
echo "[4/5] 等待 NodeBB 就緒..."
for i in {1..30}; do
    if curl -sf http://localhost:4567/api/health > /dev/null 2>&1; then
        echo "  NodeBB 就緒"
        break
    fi
    echo "  等待中... ($i/30)"
    sleep 2
done

# Check status
echo "[5/5] 健康檢查..."
docker compose -f docker-compose.forum.yml ps

echo ""
echo "=== 部署完成 ==="
echo "論壇地址：http://localhost:4567"
echo "Nginx 反向代理：http://localhost:80"
echo ""
echo "管理員初始化：請存取 http://localhost:4567 完成設定"
