# 开发环境一键启动脚本

## 脚本列表

- `scripts/start-dev.sh`：检查依赖、清理端口、并行启动 backend/agents/frontend、健康检查、写入 PID。
- `scripts/stop-dev.sh`：读取 `pids/` 中 PID，先 `kill -15`，超时后 `kill -9`。
- `scripts/status.sh`：查看进程状态与端口占用。

## 使用方式

```bash
chmod +x scripts/start-dev.sh scripts/stop-dev.sh scripts/status.sh
scripts/start-dev.sh
```

可选参数：

- `--help`：查看帮助。
- `--skip-ports`：跳过端口占用检测和清理。

## `.env` 配置

脚本会读取项目根目录 `.env`，默认值如下：

```bash
BACKEND_PORT=8000
AGENT_PORT=8001
FRONTEND_PORT=3000

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
MINIO_HOST=127.0.0.1
MINIO_PORT=9000
```

可选自定义启动命令：

```bash
BACKEND_START_CMD="uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT} --reload"
AGENT_START_CMD="python -m agents.main"
FRONTEND_START_CMD="pnpm --dir frontend run dev -- --port ${FRONTEND_PORT}"
```

## 日志与 PID

- 运行日志：`logs/backend.log`、`logs/agents.log`、`logs/frontend.log`。
- 进程 PID：`pids/backend.pid`、`pids/agents.pid`、`pids/frontend.pid`。
- 启动时终端会实时彩色输出日志，同时写入文件。

## 健康检查

启动后 30 秒内需要以下接口全部返回 200：

- `http://127.0.0.1:${BACKEND_PORT}/health`
- `http://127.0.0.1:${AGENT_PORT}/health`
- `http://127.0.0.1:${FRONTEND_PORT}/frontend/health`

若失败，会自动停止已启动进程并输出最近日志。

## 故障排查

1. 先执行 `scripts/status.sh` 查看 PID 与端口状态。
2. 查看 `logs/*.log` 中报错信息。
3. 确认 MySQL/Redis/MinIO 可连通。
4. 若 PID 文件存在但进程已不存在，执行一次 `scripts/stop-dev.sh` 清理后重试。
