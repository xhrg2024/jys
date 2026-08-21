#!/bin/bash
# 一键启动辑佚史智能体（基于tmux）
# 流程：构建前端 → 启动后端（FastAPI 同时托管 API 与前端 dist/）

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 从 .env 读取配置（如果存在）
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

API_PORT=${API_PORT:-8000}

echo "=== 启动辑佚史智能体 ==="
echo "访问端口: $API_PORT（前端已由后端托管）"

# 1. 构建前端生产产物
echo "构建前端（npm run build）..."
(cd "$PROJECT_DIR/src/frontend" && npm run build) || {
    echo "前端构建失败：请先 cd src/frontend && npm install 安装依赖"
    exit 1
}

# 杀掉旧的会话（如果存在）
tmux kill-session -t jys-api 2>/dev/null

# 2. 启动后端（FastAPI 托管 API + 前端静态资源）
echo "启动后端API..."
tmux new-session -d -s jys-api "cd $PROJECT_DIR && python src/model/api_server.py"

# 等待启动
sleep 2

echo ""
echo "=== 启动完成 ==="
echo "访问地址: http://localhost:$API_PORT"
echo ""
echo "查看日志: tmux attach -t jys-api"
echo "停止服务: ./stop.sh"
echo ""
