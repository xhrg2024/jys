#!/bin/bash
# 一键停止辑佚史智能体

echo "=== 停止辑佚史智能体 ==="

tmux kill-session -t jys-api 2>/dev/null && echo "后端已停止" || echo "后端未运行"
tmux kill-session -t jys-frontend 2>/dev/null && echo "前端已停止" || echo "前端未运行"

echo "=== 停止完成 ==="
