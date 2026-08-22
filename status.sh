#!/bin/bash
# 查看辑佚史智能体状态（后端托管前端，仅一个 tmux 会话）
set -u

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== 辑佚史智能体状态 ==="
echo ""

echo "运行中的会话:"
tmux ls 2>/dev/null || echo "  没有运行中的会话"

echo ""
echo "健康检查:"
if [ -f "$PROJECT_DIR/.env" ]; then
  API_HOST=$(grep -E '^API_HOST=' "$PROJECT_DIR/.env" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
  API_PORT=$(grep -E '^API_PORT=' "$PROJECT_DIR/.env" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
fi
API_HOST=${API_HOST:-127.0.0.1}; API_PORT=${API_PORT:-8000}
curl -sf "http://${API_HOST}:${API_PORT}/health" >/dev/null 2>&1 \
  && echo "  服务正常: http://${API_HOST}:${API_PORT}" \
  || echo "  服务未响应"

echo ""
echo "常用命令:"
echo "  查看后端: tmux attach -t jys-api"
echo "  退出 tmux: Ctrl+B 然后 D"
echo "  停止服务: ./stop.sh"
echo "  启动服务: ./start.sh"
