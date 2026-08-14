"""
FastAPI 服务：把 generator 包装成 HTTP API。
启动：python src/model/api_server.py
"""
import sys, os
# Windows GBK 控制台 UTF-8 兼容
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json

from model.generator import Generator, list_providers
from tools import graph_tools, vector_tools, sql_tools

app = FastAPI(title="辑佚史智能体")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "辑佚史智能体 API", "docs": "/docs"}


generator = Generator()


# ========== 问答接口 ==========

class ChatRequest(BaseModel):
    question: str
    use_api: Optional[bool] = None   # None=默认, True=API, False=本地
    model: Optional[str] = None      # 指定 API 模型，如 "deepseek-chat", "glm-4-plus"


class ChatResponse(BaseModel):
    answer: str
    plan_log: Optional[dict] = None
    mode: str = "default"  # "api" | "local" | "default"
    model: Optional[str] = None     # 实际使用的模型 ID
    thinking: Optional[str] = None  # CoT 前置分析（两段式推理的第一轮输出）


@app.get("/models")
def get_models():
    """返回供应商+模型层级列表（供前端两级下拉菜单）"""
    return {"providers": list_providers()}


@app.post("/chat")
def chat(req: ChatRequest):
    try:
        answer, plan_log = generator.answer(
            req.question, use_api=req.use_api, model_id=req.model
        )
        effective = generator.use_api if req.use_api is None else req.use_api
        mode = "api" if effective else "local"
        thinking = getattr(generator, 'last_thinking', None)
        return ChatResponse(
            answer=answer, plan_log=plan_log, mode=mode,
            model=generator.model_id, thinking=thinking,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推理失败: {str(e)}")


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """SSE 流式问答接口：逐 token 推送思考过程和回答"""
    def event_stream():
        for event in generator.answer_stream(req.question, model_id=req.model):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ========== 实体接口 ==========

@app.get("/entities")
def get_entities(label: Optional[str] = None):
    """获取所有实体，可按类型筛选"""
    try:
        if label:
            results = graph_tools._run(
                "MATCH (e:Entity) WHERE $label IN labels(e) "
                "RETURN e.id AS id, e.name AS name, labels(e) AS labels, properties(e) AS props",
                label=label
            )
        else:
            results = graph_tools._run(
                "MATCH (e:Entity) RETURN e.id AS id, e.name AS name, labels(e) AS labels, properties(e) AS props"
            )
        entities = []
        for r in results:
            props = dict(r["props"])
            props.pop("embedding", None)
            entities.append({
                "id": r["id"],
                "name": r["name"],
                "labels": [l for l in r["labels"] if l != "Entity"],
                "properties": props,
            })
        return {"entities": entities, "count": len(entities)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/entity/{name}")
def get_entity(name: str):
    """按名称获取单个实体详情"""
    try:
        result = graph_tools.query_entity_by_name(name)
        return {"name": name, "info": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/entity/{name}/relations")
def get_entity_relations(name: str):
    """获取实体的所有关系"""
    try:
        # 先获取实体ID
        results = graph_tools._run("MATCH (e {name: $name}) RETURN e.id AS id", name=name)
        if not results:
            return {"relations": [], "message": f"未找到实体: {name}"}
        entity_id = results[0]["id"]
        result = graph_tools.query_entity_relations(entity_id)
        return {"entity": name, "relations": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 路径查询接口 ==========

@app.get("/path")
def find_path(source: str, target: str):
    """查询两个实体间的最短路径"""
    try:
        result = graph_tools.query_relation_between(source, target)
        return {"source": source, "target": target, "path": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 搜索接口 ==========

@app.get("/search")
def search_entities(q: str, limit: int = 10):
    """搜索实体（精确+模糊匹配）"""
    try:
        # 精确匹配
        exact_results = graph_tools._run(
            "MATCH (e:Entity) WHERE e.name CONTAINS $q "
            "RETURN e.id AS id, e.name AS name, labels(e) AS labels LIMIT $limit",
            q=q, limit=limit
        )
        entities = []
        for r in exact_results:
            entities.append({
                "id": r["id"],
                "name": r["name"],
                "labels": [l for l in r["labels"] if l != "Entity"],
            })
        return {"query": q, "results": entities, "count": len(entities)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 向量搜索接口 ==========

@app.get("/vector_search")
def vector_search_api(q: str, k: int = 5):
    """语义搜索实体"""
    try:
        result = vector_tools.vector_search(q, k=k)
        return {"query": q, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 统计接口 ==========

@app.get("/stats")
def get_stats():
    """获取知识图谱统计信息"""
    try:
        entity_count = graph_tools._run("MATCH (e:Entity) RETURN count(e) AS count")[0]["count"]
        relation_count = graph_tools._run("MATCH ()-[r]->() RETURN count(r) AS count")[0]["count"]

        # 按类型统计
        type_stats = graph_tools._run(
            "MATCH (e:Entity) UNWIND labels(e) AS label "
            "WITH label WHERE label <> 'Entity' "
            "RETURN label, count(*) AS count ORDER BY count DESC"
        )
        types = {r["label"]: r["count"] for r in type_stats}

        return {
            "entity_count": entity_count,
            "relation_count": relation_count,
            "entity_types": types,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 图谱数据接口 ==========

@app.get("/graph")
def get_graph(name: Optional[str] = None, depth: int = 1, limit: int = 50):
    """
    获取知识图谱数据
    - name: 中心节点名称（不传则返回随机子图）
    - depth: 展开深度（1-3跳）
    """
    try:
        if name:
            # 以指定节点为中心查询
            # 第一步：找到中心节点
            center_result = graph_tools._run(
                "MATCH (e:Entity {name: $name}) RETURN e.id AS id, e.name AS name, labels(e) AS labels",
                name=name
            )
            if not center_result:
                return {"nodes": [], "edges": [], "center": None}

            center_id = center_result[0]["id"]
            all_node_ids = {center_id}

            # 第二步：多跳扩展
            current_ids = {center_id}
            for _ in range(depth):
                if not current_ids:
                    break
                neighbor_result = graph_tools._run(
                    "MATCH (a)-[r]-(b) WHERE a.id IN $ids "
                    "RETURN DISTINCT b.id AS id",
                    ids=list(current_ids)
                )
                new_ids = set()
                for r in neighbor_result:
                    if r["id"] not in all_node_ids:
                        new_ids.add(r["id"])
                        all_node_ids.add(r["id"])
                current_ids = new_ids

                # 限制节点总数
                if len(all_node_ids) > limit:
                    break
        else:
            # 没有指定中心，返回随机子图
            nodes_result = graph_tools._run(
                "MATCH (e:Entity) WITH e, rand() AS r ORDER BY r "
                "RETURN e.id AS id, e.name AS name, labels(e) AS labels LIMIT $limit",
                limit=min(limit, 30)
            )
            all_node_ids = {r["id"] for r in nodes_result}

        # 第三步：获取所有节点信息
        nodes = []
        if all_node_ids:
            nodes_result = graph_tools._run(
                "MATCH (e:Entity) WHERE e.id IN $ids "
                "RETURN e.id AS id, e.name AS name, labels(e) AS labels",
                ids=list(all_node_ids)
            )
            for r in nodes_result:
                nodes.append({
                    "id": r["id"],
                    "name": r["name"],
                    "label": [l for l in r["labels"] if l != "Entity"][0] if len(r["labels"]) > 1 else "Entity",
                    "is_center": r["id"] == (center_id if name else None),
                })

        # 第四步：获取所有边
        edges = []
        if all_node_ids:
            edges_result = graph_tools._run(
                "MATCH (a)-[r]->(b) WHERE a.id IN $ids AND b.id IN $ids "
                "RETURN a.id AS source, b.id AS target, type(r) AS type, "
                "r.description AS desc",
                ids=list(all_node_ids)
            )
            for r in edges_result:
                edges.append({
                    "source": r["source"],
                    "target": r["target"],
                    "type": r["type"],
                    "description": r["desc"] or "",
                })

        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== SQL 查询接口 ==========

@app.get("/sql/document")
def sql_search_document(title: str):
    """按标题搜索文献"""
    try:
        result = sql_tools.query_document_by_title(title)
        return {"query": title, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sql/author")
def sql_search_author(name: str):
    """按姓名搜索作者"""
    try:
        result = sql_tools.query_author_by_name(name)
        return {"query": name, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sql/document_detail")
def sql_document_detail(title: str):
    """查询文献详情（含作者）"""
    try:
        result = sql_tools.query_document_with_authors(title)
        return {"query": title, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sql/text_search")
def sql_text_search(keyword: str, limit: int = 10):
    """全文关键词搜索"""
    try:
        result = sql_tools.query_full_text_by_keyword(keyword, limit=limit)
        return {"query": keyword, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sql/stats")
def sql_stats():
    """获取 MySQL 数据库统计信息"""
    try:
        stats = sql_tools.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


# ========== 参考资料接口 ==========

@app.get("/reference/graph")
def reference_graph(entity_name: Optional[str] = None, entity_id: Optional[str] = None, depth: int = 2):
    """获取图谱实体的参考资料：完整属性 + 多跳邻居图数据。
    返回结构化 JSON 供前端右侧栏可视化。
    优先按 entity_id 精确定位；仅给 entity_name 时若存在同名实体，取邻居最多的那个。
    """
    try:
        # 实体详情（结构化属性列表）
        from tools.graph_tools import _run, _format_entity, KEY_CN
        if entity_id:
            recs = _run("MATCH (e:Entity {id: $id}) RETURN e", id=entity_id)
        elif entity_name:
            recs = _run("MATCH (e:Entity {name: $name}) RETURN e", name=entity_name)
            # 重名消歧：同名实体取关系数最多的那个（如"永乐大典"类书版 vs 辑本版）
            if len(recs) > 1:
                def _degree(nid):
                    d = _run("MATCH (a {id: $id})-[r]-(b) RETURN count(DISTINCT b) AS c", id=nid)
                    return d[0]["c"] if d else 0
                recs = [max(recs, key=lambda r: _degree(r["e"].get("id", "")))]
        else:
            raise HTTPException(status_code=400, detail="需要提供 entity_name 或 entity_id")

        if not recs:
            raise HTTPException(status_code=404, detail=f"未找到实体: {entity_name or entity_id}")

        entity_node = recs[0]["e"]
        entity_id = entity_node.get("id", "")
        biz_label = [l for l in entity_node.labels if l != "Entity"]
        entity_type = biz_label[0] if biz_label else "Entity"

        # 提取属性列表（中文key）
        props = []
        d = dict(entity_node)
        d.pop("id", None)
        name = d.pop("name", "")
        d.pop("embedding", None)
        # 噪音字段
        noise = {"mergedFromIds", "allDescriptions", "allCompilers",
                 "allCompilationPeriods", "allLabels", "allPeriodValues",
                 "allCompletionPeriods", "allEditionInfo"}
        for k, v in d.items():
            if not v or k in noise:
                continue
            zh = graph_tools.KEY_CN.get(k, k) if hasattr(graph_tools, 'KEY_CN') else k
            props.append({"key": zh, "value": str(v)})

        # 图谱数据（多跳邻居）：BFS 标记 hop 层级，并限制每节点邻居数，避免"线缠在一起"
        import random
        MAX_TOTAL_NODES = 40          # 总节点上限
        MAX_NEIGHBORS_PER_NODE = 6    # 每个节点最多展开的邻居数（随机抽样）

        hop_of = {entity_id: 0}
        all_node_ids = {entity_id}
        current_ids = {entity_id}

        for hop in range(1, depth + 1):
            if not current_ids or len(all_node_ids) >= MAX_TOTAL_NODES:
                break
            next_ids = set()
            for nid in current_ids:
                neighbor_result = _run(
                    "MATCH (a {id: $id})-[r]-(b) RETURN DISTINCT b.id AS id",
                    id=nid
                )
                candidates = [nr["id"] for nr in neighbor_result if nr["id"] not in all_node_ids]
                # 邻居过多时随机抽样，避免图谱线纠缠不清
                if len(candidates) > MAX_NEIGHBORS_PER_NODE:
                    candidates = random.sample(candidates, MAX_NEIGHBORS_PER_NODE)
                for cid in candidates:
                    hop_of[cid] = hop
                    all_node_ids.add(cid)
                    next_ids.add(cid)
                    if len(all_node_ids) >= MAX_TOTAL_NODES:
                        break
                if len(all_node_ids) >= MAX_TOTAL_NODES:
                    break
            current_ids = next_ids

        # 获取节点信息
        nodes = []
        if all_node_ids:
            nodes_result = _run(
                "MATCH (e:Entity) WHERE e.id IN $ids "
                "RETURN e.id AS id, e.name AS name, labels(e) AS labels",
                ids=list(all_node_ids)
            )
            for nr in nodes_result:
                nlabels = [l for l in nr["labels"] if l != "Entity"]
                nodes.append({
                    "id": nr["id"],
                    "name": nr["name"],
                    "label": nlabels[0] if nlabels else "Entity",
                    "is_center": nr["id"] == entity_id,
                    "hop": hop_of.get(nr["id"], 0),
                })

        # 获取边
        edges = []
        if all_node_ids:
            edges_result = _run(
                "MATCH (a)-[r]->(b) WHERE a.id IN $ids AND b.id IN $ids "
                "RETURN a.id AS source, b.id AS target, type(r) AS type, "
                "r.description AS desc",
                ids=list(all_node_ids)
            )
            for er in edges_result:
                edges.append({
                    "source": er["source"],
                    "target": er["target"],
                    "type": er["type"],
                    "description": er.get("desc") or "",
                })

        return {
            "entity_name": name,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "properties": props,
            "graph": {"nodes": nodes, "edges": edges},
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reference/sql")
def reference_sql(title: Optional[str] = None, author_name: Optional[str] = None):
    """获取 SQL 文献参考资料：结构化元数据 + 正文预览。
    返回结构化 JSON 供前端右侧栏表格展示。
    """
    try:
        if title:
            # 调用 sql_tools 内部函数获取结构化数据
            from tools.sql_tools import _search_variants, _fetchall, _get_conn
            clean = title.strip('《》').replace(' ', '')
            prefix = clean[:6] if len(clean) >= 3 else clean

            # 查询文献元数据
            def _do_query(search_term):
                return _fetchall(
                    """SELECT d.doc_id, d.doc_title, d.doc_specific_category, d.doc_style,
                              d.dynasty, d.compilation_time, d.completeness, d.doc_theme,
                              GROUP_CONCAT(CONCAT(a.author_name, '(', dal.role, ')')
                                           ORDER BY dal.da_id SEPARATOR '、') AS authors
                       FROM documents d
                       LEFT JOIN document_author_links dal ON d.doc_id = dal.doc_id
                       LEFT JOIN authors a ON dal.author_id = a.author_id
                       WHERE d.doc_title LIKE %s
                       GROUP BY d.doc_id
                       ORDER BY d.doc_id
                       LIMIT 5""",
                    (f"%{search_term}%",)
                )

            variants = _search_variants(prefix)
            merged = {}
            for v in variants:
                for row in _do_query(v):
                    merged[row['doc_id']] = row
            rows = list(merged.values())

            if not rows:
                return {"found": False, "message": f"未找到文献「{title}」"}

            doc = rows[0]
            # DB 中的标题自带书名号《》，统一剥离，避免前端再套一层出现《《》》
            doc["doc_title"] = (doc.get("doc_title") or title).strip("《》")
            # 格式化元数据为 key-value 列表
            fields = []
            field_map = {
                "doc_title": "书名", "doc_specific_category": "类别",
                "dynasty": "朝代", "doc_style": "体例",
                "compilation_time": "编纂时间", "completeness": "完整性",
                "doc_theme": "主题", "authors": "编者",
            }
            for en, zh in field_map.items():
                val = doc.get(en)
                if val:
                    fields.append({"key": zh, "value": str(val)})

            # 获取正文预览
            from tools.sql_tools import query_full_text_by_doc
            content = query_full_text_by_doc(title, limit=8)
            has_content = content and "未找到" not in content

            return {
                "found": True,
                "source_type": "sql",
                "doc_title": doc.get("doc_title", title),
                "fields": fields,
                "content_preview": content if has_content else None,
            }

        elif author_name:
            from tools.sql_tools import _search_variants, _fetchall
            variants = _search_variants(author_name)
            merged = {}
            for v in variants:
                for row in _fetchall(
                    """SELECT a.author_name, a.author_org, d.doc_title, dal.role
                       FROM authors a
                       LEFT JOIN document_author_links dal ON a.author_id = dal.author_id
                       LEFT JOIN documents d ON dal.doc_id = d.doc_id
                       WHERE a.author_name LIKE %s""",
                    (f"%{v}%",)
                ):
                    key = f"{row['author_name']}_{row.get('doc_title', '')}"
                    if key not in merged:
                        merged[key] = row
            rows = list(merged.values())
            if not rows:
                return {"found": False, "message": f"未找到作者「{author_name}」"}

            works = []
            for r in rows:
                works.append({
                    "author": r["author_name"],
                    "org": r.get("author_org", ""),
                    "doc": r.get("doc_title", ""),
                    "role": r.get("role", ""),
                })
            return {
                "found": True,
                "source_type": "sql",
                "author_name": author_name,
                "works": works,
            }

        else:
            raise HTTPException(status_code=400, detail="需要 title 或 author_name 参数")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 评估接口 ==========

import re
import uuid
from datetime import datetime

EVAL_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
EVAL_RESULTS_FILE = EVAL_DATA_DIR / "eval_results_manual.json"
EVAL_QUESTIONS_FILE = EVAL_DATA_DIR / "test_questions.md"


def _load_eval_results():
    if EVAL_RESULTS_FILE.exists():
        with open(EVAL_RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"results": [], "custom_questions": []}


def _save_eval_results(data):
    with open(EVAL_RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _parse_questions_from_md():
    """从 test_questions.md 解析题目列表"""
    questions = []
    if not EVAL_QUESTIONS_FILE.exists():
        return questions
    with open(EVAL_QUESTIONS_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    # 解析形如 "### N. 问题内容" 的标题
    pattern = r'###\s+(\d+)\.\s+(.+?)(?=\n-|\n\n|$)'
    matches = re.findall(pattern, content)
    for num, text in matches:
        questions.append({
            "id": f"q{num}",
            "question": text.strip(),
        })
    return questions


@app.get("/eval/questions")
def get_eval_questions():
    """获取所有评估题目（预设 + 自定义）"""
    preset = _parse_questions_from_md()
    data = _load_eval_results()
    custom = data.get("custom_questions", [])
    return {"questions": preset + custom}


@app.post("/eval/questions")
def add_eval_question(body: dict):
    """添加自定义题目 {question: str}"""
    data = _load_eval_results()
    custom = data.get("custom_questions", [])
    new_q = {
        "id": f"custom_{uuid.uuid4().hex[:6]}",
        "question": body.get("question", "").strip(),
    }
    custom.append(new_q)
    data["custom_questions"] = custom
    _save_eval_results(data)
    return {"ok": True, "question": new_q}


@app.delete("/eval/questions/{qid}")
def delete_eval_question(qid: str):
    """删除自定义题目及关联结果"""
    data = _load_eval_results()
    data["custom_questions"] = [q for q in data.get("custom_questions", []) if q["id"] != qid]
    data["results"] = [r for r in data.get("results", []) if r.get("question_id") != qid]
    _save_eval_results(data)
    return {"ok": True}


@app.post("/eval/run")
def eval_run(body: dict):
    """对指定题目调用 API 并返回结果 {question_id, question, model}"""
    question = body.get("question", "")
    model_id = body.get("model")
    try:
        answer, plan_log = generator.answer(question, use_api=True, model_id=model_id)
        thinking = getattr(generator, 'last_thinking', None)
        return {
            "answer": answer,
            "plan_log": plan_log,
            "model": generator.model_id,
            "thinking": thinking,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"调用失败: {str(e)}")


@app.post("/eval/save")
def eval_save(body: dict):
    """保存评分结果"""
    data = _load_eval_results()
    entry = {
        "id": uuid.uuid4().hex[:8],
        "question_id": body.get("question_id", ""),
        "question": body.get("question", ""),
        "model": body.get("model", ""),
        "answer": body.get("answer", ""),
        "plan_log": body.get("plan_log", {}),
        "thinking": body.get("thinking", ""),
        "scores": body.get("scores", {}),   # {C: int, D: int, A: int, B: int}
        "notes": body.get("notes", ""),
        "timestamp": datetime.now().isoformat(),
    }
    data.setdefault("results", []).append(entry)
    _save_eval_results(data)
    return {"ok": True, "id": entry["id"]}


@app.get("/eval/results")
def get_eval_results():
    """获取所有评分结果"""
    data = _load_eval_results()
    return {"results": data.get("results", [])}


@app.delete("/eval/results/{qid}")
def reset_eval_result(qid: str, model: Optional[str] = None):
    """重置某题的评分结果，可指定模型"""
    data = _load_eval_results()
    if model:
        data["results"] = [r for r in data.get("results", [])
                           if not (r.get("question_id") == qid and r.get("model") == model)]
    else:
        data["results"] = [r for r in data.get("results", []) if r.get("question_id") != qid]
    _save_eval_results(data)
    return {"ok": True}


@app.get("/eval/summary")
def get_eval_summary():
    """获取汇总统计（按模型分组）"""
    data = _load_eval_results()
    results = data.get("results", [])
    # 按模型分组
    models = {}
    for r in results:
        m = r.get("model", "unknown")
        if m not in models:
            models[m] = {"count": 0, "C": [], "D": [], "A": [], "B": [], "results": []}
        s = r.get("scores", {})
        models[m]["count"] += 1
        for k in ["C", "D", "A", "B"]:
            if k in s:
                models[m][k].append(s[k])
        models[m]["results"].append(r)
    # 算均分
    summary = {}
    for m, v in models.items():
        avg = {}
        for k in ["C", "D", "A", "B"]:
            vals = v[k]
            avg[k] = round(sum(vals) / len(vals), 2) if vals else 0
        summary[m] = {"count": v["count"], "avg_scores": avg, "results": v["results"]}
    return {"summary": summary, "total_results": len(results)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("API_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
