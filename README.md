# jys-agent — 辑佚史智能体

## 依赖

- Python 3.10+
- Neo4j 5.x
- PyTorch 2.x + CUDA 12.x
- 模型：Qwen2.5-7B-Instruct

## 安装

```bash
pip install -r requirements.txt
```

## 启动

```bash
# 1. 启动 Neo4j
cd neo4j-community-5.26.5 && ./bin/neo4j start

neo4j密码 jys123456

查看状态
~/jys-agent/neo4j/neo4j-community-5.26.5/bin/neo4j status

本地ssh隧道
ssh -L 7474:localhost:7474 -L 7687:localhost:7687 wj@162.105.19.120

服务器
 ./bin/cypher-shell -u neo4j -p neo4j

# 2. 导入数据
python src/memory/build_graph.py

# 3. 启动推理服务
python src/model/generator.py
```


工具层
图查询  Cypher 查询 Neo4j，结果转为自然语言   graph_tools.py
向量检索工具  将问句向量化，在 Neo4j 向量索引中检索相似实体。 vector_tools.py
工具调用机制  定义 tool schemas，调度执行，结果回传。 tool_registry.py

推理接口封装
model_loader.py  单例加载 Qwen + QA LoRA，常驻显存   //暂时ban掉loRA
generator.py    全链路：感知→规划→检索→模型生成→后处理



前端

src/
├── App.jsx                        # 主入口，路由/导航逻辑
│
├── constants/
│   ├── colors.js                  # 设计 Token（C 对象）
│   └── graphData.js               # 知识图谱节点 & 边数据（NODES, EDGES）
│
├── components/                    # 可复用共享组件
│   ├── TopNav.jsx                 # 顶部导航栏
│   ├── ResourceSidebar.jsx        # 资源浏览左侧边栏
│   ├── KnowledgeGraph.jsx         # 知识图谱 SVG（多页复用）
│   └── EntityCard.jsx             # 实体详情卡片（多页复用）
│
└── pages/                         # 各页面
    ├── DataOverviewPage.jsx        # 数据概览
    ├── EntityListPage.jsx          # 辑佚者列表
    ├── EntityExplorePage.jsx       # 实体探索
    ├── PathQueryPage.jsx           # 路径查询
    ├── GlobalBrowsePage.jsx        # 全局浏览
    ├── ResearchSection.jsx         # 智能研究（Landing + Chat + Report）
    └── DataDownloadPage.jsx        # 数据下载
拆分原则说明：

constants/ 将全局共享的颜色 token 和图数据从组件中分离，避免重复定义
components/ 收录在多个页面中复用的 KnowledgeGraph、EntityCard、TopNav、ResourceSidebar
pages/ 每个页面对应一个文件，职责清晰
App.jsx 仅保留路由状态和渲染逻辑，不含任何 UI 细节


npm run dev

npm install

npm run dev -- --host 0.0.0.0

2. 启动 API（tmux 保持后台运行）

tmux new -s jys-api  创建jys-api会话

# 如果之前用 tmux new -s jys-api 创建过，重新进入：
tmux attach -t jys-api

python src/model/api_server.py
Ctrl+B 然后 D 退出 tmux，服务继续跑。

Ctrl+B 然后 D — 退出但保持后台运行
tmux ls — 查看当前有哪些会话
tmux kill-session -t jys-api — 彻底关闭某个会话

3. 测试

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"《玉函山房辑佚书》有多少卷？"}'


# tmux挂后台
# API 后台（已有的）
tmux new -d -s jys-api
tmux send-keys -t jys-api "cd ~/jys-agent && python src/model/api_server.py" Enter

# 前端后台
tmux new -d -s jys-frontend

tmux send-keys -t jys-frontend "cd ~/jys-agent/src/frontend && npm run dev -- --host 0.0.0.0" Enter

# 查看状态
tmux ls

# 随时看日志
tmux attach -t jys-api      # Ctrl+B D 退出
tmux attach -t jys-frontend

服务	端口	管理
Neo4j	7474/7687	手动启动
API	8000	tmux attach -t jys-api
前端	5173	tmux attach -t jys-frontend


# SSH 隧道一行连所有：
ssh -L 5173:localhost:5173 -L 8000:localhost:8000 -L 7474:localhost:7474 wj@162.105.19.120


高位端口启动
npx vite --port 15173 --host 0.0.0.0
ssh -L 15173:localhost:15173 wj@162.105.19.120

纯Qwen,无LoRA
训练阶段做的事：喂给模型几百条"RACE 格式输入 → 带来源标注的专业答案"的数据对，让模型学会：

看到 【参考信息】 就知道从这里找证据
自动生成 （来源：XXX） 格式的标注
稳定输出学术中文，不乱编、不串字

deepseek生成问答对
事实问答：约 500 条（覆盖所有实体）
关系问答：200 条
脉络问答：约 20 条
方法问答：约 30 条
总计约 750 条