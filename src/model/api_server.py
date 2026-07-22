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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("API_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
