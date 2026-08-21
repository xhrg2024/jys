#!/bin/bash
# 一键停止辑佚史智能体

echo "=== 停止辑佚史智能体 ==="

tmux kill-session -t jys-api 2>/dev/null && echo "后端已停止（含前端托管）" || echo "后端未运行"

echo "=== 停止完成 ==="
