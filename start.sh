#!/bin/bash
# 一键启动辑佚史智能体（基于 tmux）
# 流程：构建前端 → 启动后端（FastAPI 同时托管 API 与前端 dist/）
set -u

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$PROJECT_DIR/.env"

# 从 .env 读取单个键（忽略注释、剥离引号；后端启动时也会用 python-dotenv 自行加载 .env）
env_get() {
  grep -E "^$1=" "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'"
}

echo "=== 启动辑佚史智能体 ==="

# 0. 前置检查
if ! command -v python >/dev/null 2>&1; then
  echo "[错误] 未找到 python，请先安装 Python 3.9+"
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "[错误] 未找到 npm，请先安装 Node.js 18+"
  exit 1
fi
if ! command -v tmux >/dev/null 2>&1; then
  echo "[错误] 未找到 tmux，请先安装：apt install tmux / brew install tmux"
  exit 1
fi
if [ ! -f "$ENV_FILE" ]; then
  echo "[错误] 未找到 .env，请先执行：cp .env.example .env 并填入配置"
  exit 1
fi
if [ ! -d "$PROJECT_DIR/src/frontend/node_modules" ]; then
  echo "[提示] 前端依赖未安装，先执行 npm install ..."
  (cd "$PROJECT_DIR/src/frontend" && npm install) || { echo "[错误] npm install 失败"; exit 1; }
fi

API_HOST=$(env_get API_HOST); API_HOST=${API_HOST:-127.0.0.1}
API_PORT=$(env_get API_PORT); API_PORT=${API_PORT:-8000}

# 1. 构建前端生产产物
echo "构建前端（npm run build）..."
(cd "$PROJECT_DIR/src/frontend" && npm run build) || {
  echo "[错误] 前端构建失败，请检查 src/frontend 依赖是否完整"
  exit 1
}

# 2. 重启后端（先杀旧会话，幂等）
tmux kill-session -t jys-api 2>/dev/null
echo "启动后端 API ..."
tmux new-session -d -s jys-api "cd '$PROJECT_DIR' && python src/model/api_server.py"

# 3. 等待并健康检查
sleep 3
if curl -sf "http://${API_HOST}:${API_PORT}/health" >/dev/null 2>&1; then
  echo "[成功] 后端已就绪"
else
  echo "[提示] 健康检查未通过，请用 ./status.sh 或 tmux attach -t jys-api 查看日志"
fi

echo ""
echo "=== 启动完成 ==="
echo "访问地址: http://${API_HOST}:${API_PORT}"
echo ""
echo "查看日志: tmux attach -t jys-api   （退出按 Ctrl+B 再 D）"
echo "查看状态: ./status.sh"
echo "停止服务: ./stop.sh"
echo ""
