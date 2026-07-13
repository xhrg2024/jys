#!/bin/bash
# 一键启动辑佚史智能体（基于tmux）

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 从 .env 读取端口配置（如果存在）
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

API_PORT=${API_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-15173}

echo "=== 启动辑佚史智能体 ==="
echo "后端端口: $API_PORT"
echo "前端端口: $FRONTEND_PORT"

# 杀掉旧的会话（如果存在）
tmux kill-session -t jys-api 2>/dev/null
tmux kill-session -t jys-frontend 2>/dev/null

# 1. 启动后端
echo "启动后端API..."
tmux new-session -d -s jys-api "cd $PROJECT_DIR && python src/model/api_server.py"

# 2. 启动前端
echo "启动前端..."
tmux new-session -d -s jys-frontend "cd $PROJECT_DIR/src/frontend && npm run dev -- --host 0.0.0.0 --port $FRONTEND_PORT"

# 等待启动
sleep 2

echo ""
echo "=== 启动完成 ==="
echo "后端: http://localhost:$API_PORT"
echo "前端: http://localhost:$FRONTEND_PORT"
echo ""
echo "查看后端日志: tmux attach -t jys-api"
echo "查看前端日志: tmux attach -t jys-frontend"
echo "停止所有服务: ./stop.sh"
echo ""
