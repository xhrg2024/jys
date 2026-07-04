# 文件说明

## 当前状态
- **推理模式**: 基础 Qwen2.5-7B-Instruct (bf16) + RACE 规划层，不含 LoRA
- **服务器**: Ubuntu 24.04, RTX 5090 32GB, Neo4j 5.26.5, API :8000, 前端 :5173
- **访问**: SSH 隧道 `ssh -L 5173:localhost:5173 -L 8000:localhost:8000 -L 7474:localhost:7474 wj@162.105.19.120`

## 数据文件 (data/)
| 文件 | 说明 |
|---|---|
| data.json | 原始辑佚史实体与关系数据（208 实体，169 条 object_properties） |
| sft_alpaca(1).json | 19 条问答数据（含部分占位符答案） |
| sft_alpaca_cleaned.json | 清洗后的 sft_alpaca，答案已回填 |
| sharegpt_toolcall(1).json | 295 条 ShareGPT 格式工具调用数据 |
| entity_dict.json | Neo4j 导出的实体词典 |
| test_set.json | 评估测试集（待编写） |
| extraction_*.json | 三元组抽取训练/验证/测试数据（自动生成） |
| race_*.json | RACE 问答训练数据（自动生成） |

## 记忆层 (src/memory/)
| 文件 | 说明 |
|---|---|
| build_graph.py | 将 data.json 导入 Neo4j：创建实体节点、关系边、索引、导出 entity_dict |
| build_vector_index.py | bge-large-zh-v1.5 向量化实体文本 → Neo4j 向量索引 |
| build_extraction_data.py | 构造三元组抽取训练数据 |

## 模型层 (src/model/)
| 文件 | 说明 |
|---|---|
| model_loader.py | 模型加载器（单例，常驻显存） |
| generator.py | 推理接口：感知→规划→检索→生成 全链路 |
| api_server.py | FastAPI 服务（POST /chat），包装 generator |
| train_extraction_lora.py | 第一阶段 LoRA 训练（三元组抽取） |
| train_race_lora.py | 第二阶段 LoRA 训练（RACE 问答） |
| eval_extraction.py | 三元组抽取量化评估 |
| build_race_data.py | 构造 RACE 格式训练数据（sft + sharegpt + data.json 增强） |
| clean_sft_alpaca.py | 清洗 sft_alpaca，回填真实答案 |
| test_base_inference.py | 纯基础模型 + RACE 规划层测试 |
| test_race_inference.py | LoRA 模型端到端推理测试 |
| compare_extraction.py | 基础模型 vs LoRA 三元组抽取对比 |

## 感知层 (src/perception/)
| 文件 | 说明 |
|---|---|
| entity_linker.py | 精确匹配 + jieba 分词模糊匹配 |
| intent_recognizer.py | 关键词规则 5 分类 |
| question_parser.py | 整合实体链接 + 意图识别 + 结构要素提取 |

## 工具层 (src/tools/)
| 文件 | 说明 |
|---|---|
| graph_tools.py | Cypher 图查询 + 结构化邻居查询（多跳用） |
| vector_tools.py | Neo4j 向量索引语义检索 |
| tool_registry.py | 5 个 tool schema + 调度执行器 |

## 规划层 (src/planning/)
| 文件 | 说明 |
|---|---|
| planner.py | 检索策略选择、多跳查询(≤2)、结果融合、RACE Prompt 构建、后处理 |

## 测试脚本
| 文件 | 说明 |
|---|---|
| test_perception.py | 感知层独立测试 |
| test_tools.py | 工具层独立测试 |
| test_planner.py | 规划层端到端测试 |

## 前端 (src/frontend/)
| 文件 | 说明 |
|---|---|
| App.jsx | 主入口，路由导航 |
| main.jsx | React 挂载点 |
| pages/ResearchSection.jsx | 智能问答页：对话界面，调 API |
| pages/DataOverviewPage.jsx | 数据概览 |
| pages/EntityExplorePage.jsx | 实体探索 |
| pages/PathQueryPage.jsx | 路径查询 |
| pages/EntityListPage.jsx | 辑佚者列表 |
| pages/GlobalBrowsePage.jsx | 全局浏览 |
| pages/DataDownloadPage.jsx | 数据下载 |
| components/KnowledgeGraph.jsx | 知识图谱 SVG |
| components/EntityCard.jsx | 实体详情卡片 |
| components/TopNav.jsx | 顶部导航栏 |
| components/ResourceSidebar.jsx | 资源浏览侧边栏 |
| constants/colors.js | 设计 Token |
| constants/graphData.js | 图谱节点与边数据 |

## 文档
| 文件 | 说明 |
|---|---|
| jys-agent.md | 智能体构建方案（技术细节） |
| project.md | 项目详细说明（领域 Schema、工作流） |
| requirements.txt | Python 依赖 |
| README.md | 服务器连接与启动说明 |

## 已知问题
- **繁体字/错字**: 4-bit 量化偶尔导致字符替换（辑佚→辑遗），已切换 bf16 全精度，待验证
- **第一阶段 LoRA**: 训练完成但效果与基础模型差异不大（数据偏简单）
- **第二阶段 LoRA**: 多次尝试效果不佳，暂时搁置，待积累高质量训练数据后重训
- **63 条无效关系**: data.json 中 source/target 指向不存在的 entity ID，导入时已跳过
