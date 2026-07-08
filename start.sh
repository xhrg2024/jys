#!/bin/bash
# 一键启动辑佚史智能体（基于tmux）

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== 启动辑佚史智能体 ==="

# 杀掉旧的会话（如果存在）
tmux kill-session -t jys-api 2>/dev/null
tmux kill-session -t jys-frontend 2>/dev/null

# 1. 启动后端
echo "启动后端API..."
tmux new-session -d -s jys-api "cd $PROJECT_DIR && python src/model/api_server.py"

# 2. 启动前端
echo "启动前端..."
tmux new-session -d -s jys-frontend "cd $PROJECT_DIR/src/frontend && npm run dev -- --host 0.0.0.0 --port 15173"

# 等待启动
sleep 2

echo ""
echo "=== 启动完成 ==="
echo "后端: http://localhost:8000"
echo "前端: http://localhost:15173"
echo ""
echo "查看后端日志: tmux attach -t jys-api"
echo "查看前端日志: tmux attach -t jys-frontend"
echo "停止所有服务: ./stop.sh"
echo ""
