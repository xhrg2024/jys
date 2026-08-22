#!/bin/bash
# 一键停止辑佚史智能体（后端含前端托管，仅一个 tmux 会话）
set -u

echo "=== 停止辑佚史智能体 ==="

if tmux has-session -t jys-api 2>/dev/null; then
  tmux kill-session -t jys-api
  echo "后端已停止（含前端托管）"
else
  echo "后端未在运行"
fi

echo "=== 停止完成 ==="
