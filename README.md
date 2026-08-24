# 辑佚史智能体（jys-agent）

基于 Neo4j 知识图谱 + 大模型的辑佚学问答智能体。后端 FastAPI 同时托管 API 与前端静态资源，单进程即可部署。

## 环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.9+ | 后端 |
| Node.js | 18+ | 前端构建 |
| Neo4j | 5.x | 图数据库（本地 7687 端口） |
| MySQL | 5.7+ | 可选，用于 SQL 工具检索 |
| tmux | 任意 | 后台运行脚本依赖 |

## 安装

```bash
# 1. 后端依赖
pip install -r requirements.txt

# 2. 前端依赖
cd src/frontend && npm install && cd ../..
```

## 配置

```bash
cp .env.example .env
# 编辑 .env，至少填入：
#   NEO4J_PASSWORD    Neo4j 密码（必填）
#   API_PORT / API_HOST  服务端口与监听地址（对外访问改为 0.0.0.0）
#   需要外部模型时填入对应厂商的 *_API_KEY
```

## 启动 / 停止

```bash
bash start.sh    # 构建前端 + 启动后端（后台 tmux 会话 jys-api）
bash status.sh   # 查看运行状态
bash stop.sh     # 停止服务
```

启动后访问 `http://<API_HOST>:<API_PORT>`（默认 `http://127.0.0.1:8000`）。

> 前端生产构建产物为 `src/frontend/dist/`，由后端 `StaticFiles` 托管，无需单独启动前端。开发调试前端可 `cd src/frontend && npm run dev`（走 vite 代理）。

## 数据初始化

首次部署需准备 embedding 模型、导入图谱数据并建立向量索引：

```bash
# 0. 下载本地 embedding 模型（约 1.3GB，未纳入 git，首次部署必须下载）
python scripts/download_embedding_model.py

# 1. 导入 data/data.json 到 Neo4j（清空重建，仅初始化用）
python src/memory/build_graph.py

# 2. 为实体生成 embedding 并建立向量索引
python src/memory/build_vector_index.py
```

> `embeddings/bge-large-zh-v1.5/` 已被 `.gitignore` 忽略（大体积权重不进版本库），部署时用 `scripts/download_embedding_model.py` 从 ModelScope / HuggingFace 下载，或手动放置该目录。

运行中的增量更新走前端「图谱导入」页或 `POST /import/graph`（按 id MERGE 合并，并重算 embedding），不会清空现有数据。

## 目录结构

```
src/
├── model/          # 后端：api_server.py（FastAPI 入口）、generator.py（推理链路）
├── tools/          # 工具层：图查询 / 向量检索 / SQL 检索 / 工具调度
├── utils/          # 报告生成、图谱导入、会话日志等
├── memory/         # 数据构建：build_graph.py、build_vector_index.py
├── planning/       # 规划
├── perception/     # 感知
├── evaluation/     # 评测
└── frontend/       # React + Vite 前端
data/data.json      # 知识图谱源数据
reports/            # 生成的报告（运行时自动创建）
logs/               # 日志（运行时自动创建）
```

## 常用命令

```bash
tmux attach -t jys-api        # 查看后端日志（退出按 Ctrl+B 再 D）
tmux kill-session -t jys-api  # 强制关闭

# 健康检查
curl http://127.0.0.1:8000/health

# 问答接口
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"《玉函山房辑佚书》有多少卷？"}'
```

## 注意事项

- `API_TOKEN` 留空时普通接口开放、评测页 `/eval/*` 禁用；设置后需在请求头带 `Authorization: Bearer <token>`。
- 默认监听 `127.0.0.1`（仅本机）；需局域网/服务器外部访问时把 `API_HOST` 改为 `0.0.0.0`，或通过 SSH 隧道转发。
