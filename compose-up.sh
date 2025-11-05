#!/usr/bin/env bash
set -euo pipefail

# 用 docker-compose 一键构建并运行
# 可覆盖变量：MONGODB_URI

echo "[compose] building images..."
docker-compose build

echo "[compose] starting containers..."
docker-compose up -d

echo "[compose] services started:"
echo "- Frontend: http://localhost:3051"
echo "- Backend:  http://localhost:8009/api/health"

