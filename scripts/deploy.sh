#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p /home/ubuntu/proCreate/data
sudo docker compose up -d --build
sudo docker compose ps
echo "本机访问: http://127.0.0.1:8096"
echo "健康检查: curl http://127.0.0.1:8096/api/health"
