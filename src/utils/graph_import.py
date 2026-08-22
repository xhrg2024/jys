"""
JSON 知识图谱增量导入：写入 Neo4j + 语义更新（为涉及实体重算 embedding）。

JSON 格式与 data/data.json 一致：
{
  "entities":  [{"id", "text", "label", "properties": {...}}, ...],
  "relations": [{"source", "target", "type", "description"}, ...]
}

- 增量合并：按 id MERGE 去重，已存在则更新属性，不删除现有数据；
- 语义更新：为本次涉及的实体重新生成 embedding 写回 e.embedding，
  向量索引（entity_vector_index）为 schema 级，已建立即持续生效，无需重建。
"""
import re

from tools.graph_tools import _get_driver
from tools.vector_tools import _get_model

# Neo4j 标签合法标识符（防 Cypher 注入：label 直接拼进动态标签语法）
_LABEL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_label(label):
    """校验业务 label，非法则回退 Entity。"""
    if label and _LABEL_RE.match(str(label)):
        return str(label)
    return "Entity"


def import_graph_incremental(entities, relations):
    """增量导入 entities/relations 到 Neo4j，并为涉及实体重算 embedding。

    返回统计 dict（entities_total/created、relations_total/created/skipped、embeddings）。
    语义更新失败不阻断图数据导入，只在统计里附 embeddings_error。
    """
    entities = [e for e in (entities or []) if isinstance(e, dict)]
    relations = [r for r in (relations or []) if isinstance(r, dict)]

    # 实体 id 集合（用于关系有效性校验）
    entity_ids = {str(e["id"]) for e in entities if e.get("id") is not None}

    stats = {
        "entities_total": len(entities),
        "entities_created": 0,
        "relations_total": len(relations),
        "relations_created": 0,
        "relations_skipped": 0,
        "embeddings": 0,
    }

    driver = _get_driver()

    # ── 1. 实体 upsert ──
    with driver.session() as session:
        for e in entities:
            eid = e.get("id")
            if eid is None:
                continue
            label = _safe_label(e.get("label"))
            props = dict(e.get("properties") or {})
            # 内部字段由本模块显式维护，避免 JSON 里同名字段覆盖/污染
            for k in ("id", "name", "embedding"):
                props.pop(k, None)
            cypher = (
                f"MERGE (n:Entity {{id: $id}}) "
                f"SET n:{label} SET n.name = $text, n += $props"
            )
            counters = session.run(
                cypher,  # type: ignore[arg-type]  # label 经 _safe_label 校验，无注入风险
                id=str(eid), text=e.get("text", ""), props=props,
            ).consume().counters
            stats["entities_created"] += counters.nodes_created

        # ── 2. 关系 upsert ──
        for r in relations:
            src = r.get("source")
            tgt = r.get("target")
            if src is None or tgt is None:
                stats["relations_skipped"] += 1
                continue
            if str(src) not in entity_ids or str(tgt) not in entity_ids:
                stats["relations_skipped"] += 1
                continue
            counters = session.run(
                "MATCH (a {id: $src}), (b {id: $tgt}) "
                "MERGE (a)-[r:RELATES {type: $type}]->(b) "
                "SET r.description = $desc",
                src=str(src), tgt=str(tgt),
                type=str(r.get("type", "")),
                desc=r.get("description", ""),
            ).consume().counters
            stats["relations_created"] += counters.relationships_created

    # ── 3. 语义更新：为涉及实体重算 embedding ──
    if entity_ids:
        try:
            model = _get_model()
            with driver.session() as session:
                rows = list(session.run(
                    "MATCH (e:Entity) WHERE e.id IN $ids "
                    "RETURN e.id AS id, e.name AS name, properties(e) AS props",
                    ids=list(entity_ids),
                ))
            ids, texts = [], []
            for row in rows:
                props = dict(row["props"] or {})
                props.pop("id", None)
                props.pop("name", None)
                props.pop("embedding", None)
                prop_text = "，".join(str(v) for v in props.values() if v)
                ids.append(row["id"])
                texts.append(f"{row['name']}：{prop_text}")

            if texts:
                embeddings = model.encode(texts, normalize_embeddings=True)
                with driver.session() as session:
                    for eid, emb in zip(ids, embeddings):
                        session.run(
                            "MATCH (e:Entity {id: $id}) SET e.embedding = $emb",
                            id=eid, emb=emb.tolist(),
                        )
                stats["embeddings"] = len(texts)
        except Exception as e:  # 语义失败不阻断图数据导入
            print(f"[Import] 语义更新失败: {e}")
            stats["embeddings_error"] = str(e)

    return stats
