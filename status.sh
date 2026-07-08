#!/bin/bash
# 查看辑佚史智能体状态

echo "=== 辑佚史智能体状态 ==="
echo ""
echo "运行中的会话:"
tmux ls 2>/dev/null || echo "没有运行中的会话"
echo ""
echo "常用命令:"
echo "  查看后端: tmux attach -t jys-api"
echo "  查看前端: tmux attach -t jys-frontend"
echo "  退出tmux: Ctrl+B 然后 D"
echo "  停止服务: ./stop.sh"
