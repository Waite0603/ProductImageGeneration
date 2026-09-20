# 产品展示图

Vue 画板 + FastAPI 历史记录。本地前后端分开跑；线上用 Docker Compose，对外只暴露 `8096`。

## 目录

```
frontend/          Vue + Vite
backend/           FastAPI + SQLite
data/              本地数据库目录（showcase.db）
docker-compose.yml 线上编排
scripts/           本地启动 / 线上部署
```

## 环境

- Node 22+（前端）
- Python 3.12+（本地后端）
- Docker + Docker Compose（线上）

## 本地运行

需要两个进程：后端 `8000`，前端 Vite 默认 `5173`。前端把 `/api` 代理到 `http://127.0.0.1:8000`。

数据库默认写到项目根目录 `data/showcase.db`。

### Windows（PowerShell）

在项目根目录：

```powershell
.\scripts\dev-backend.ps1
```

另开一个终端：

```powershell
.\scripts\dev-frontend.ps1
```

浏览器打开脚本输出的 Local 地址（一般是 `http://localhost:5173/`）。

手动命令：

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

```powershell
cd frontend
npm install
npm run dev
```

### macOS / Linux

```bash
chmod +x scripts/*.sh
./scripts/dev-backend.sh
```

另开一个终端：

```bash
./scripts/dev-frontend.sh
```

手动命令：

```bash
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

```bash
cd frontend
npm install
npm run dev
```

后端起来后可检查：`http://127.0.0.1:8000/api/health`

## 线上部署

服务器目录按当前 compose 约定是 `/home/ubuntu/proCreate`，SQLite 落在 `/home/ubuntu/proCreate/data`。如果路径不同，改 `docker-compose.yml` 里 backend 的 volumes。

在服务器项目根目录：

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

等价于：

```bash
mkdir -p /home/ubuntu/proCreate/data
sudo docker compose up -d --build
```

访问：

- 本机：`http://127.0.0.1:8096`
- 宝塔：站点反向代理到 `http://127.0.0.1:8096`（根路径 `/` 即可，`/api` 由容器内 Nginx 转到 backend）

改代码后重新构建：

```bash
sudo docker compose up -d --build
```

看日志 / 健康检查：

```bash
sudo docker compose ps
sudo docker compose logs web --tail 80
sudo docker compose logs backend --tail 80
curl -I http://127.0.0.1:8096
curl http://127.0.0.1:8096/api/health
```

停掉：

```bash
sudo docker compose down
```

`down` 不会删 `/home/ubuntu/proCreate/data` 里的库文件。

## 常见问题

- 前端能开、历史保存失败：本地后端没在 `8000`，或线上 `backend` 不健康。
- 宝塔 502：先 `curl -I http://127.0.0.1:8096`。本机不通就重建 compose；本机通再查反向代理是否指到 `8096`。
- 历史图片：上传图以 data URL 写进 SQLite；默认配色图走前端静态资源地址。
