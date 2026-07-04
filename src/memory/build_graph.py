"""
将 data.json 导入 Neo4j 知识图谱。
用法：python src/memory/build_graph.py
"""
import json
import os
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "52LiWenJing")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def load_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_graph(session):
    """清空原有数据（仅首次导入时使用）"""
    session.run("MATCH (n) DETACH DELETE n")
    session.run("DROP INDEX entity_name_index IF EXISTS")
    session.run("DROP INDEX entity_id_index IF EXISTS")
    print("已清空旧数据")


def create_indexes(session):
    session.run("CREATE INDEX entity_id_index FOR (e:Entity) ON (e.id)")
    session.run("CREATE INDEX entity_name_index FOR (e:Entity) ON (e.name)")
    print("索引已创建")


def import_entities(session, entities):
    count = 0
    for e in entities:
        props = dict(e.get("properties", {}))
        props["id"] = e["id"]
        props["name"] = e["text"]
        session.run(
            """
            CREATE (n:Entity:%s)
            SET n += $props
            """ % e["label"],
            props=props
        )
        count += 1
        if count % 100 == 0:
            print(f"  已导入 {count} 个实体...")
    print(f"实体导入完成，共 {count} 个")


def import_relationships(session, relationships, entity_ids):
    valid = 0
    skipped = 0
    for r in relationships:
        src = r["source"]
        tgt = r["target"]
        if src not in entity_ids or tgt not in entity_ids:
            skipped += 1
            continue
        session.run(
            """
            MATCH (a {id: $src}), (b {id: $tgt})
            CREATE (a)-[:RELATES {type: $type, description: $desc}]->(b)
            """,
            src=src, tgt=tgt, type=r["type"],
            desc=r.get("description", "")
        )
        valid += 1
        if valid % 100 == 0:
            print(f"  已导入 {valid} 个关系...")
    print(f"关系导入完成，有效 {valid} 个，跳过 {skipped} 个无效关系")


def export_entity_dict(session, output_path):
    result = session.run("MATCH (e:Entity) RETURN e.name, e.id, labels(e) AS lbls")
    records = []
    for r in result:
        # labels(e) 返回 ['Entity', 'Compilation'] 之类，取第二个作为业务标签
        lbls = r["lbls"]
        biz_label = [l for l in lbls if l != "Entity"][0] if lbls else ""
        records.append({"name": r["e.name"], "id": r["e.id"], "label": biz_label})
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"实体词典已导出，共 {len(records)} 条 → {output_path}")


def main():
    data = load_data(os.path.join(DATA_DIR, "data.json"))
    entities = data["entities"]
    relationships = data["object_properties"]
    entity_ids = {e["id"] for e in entities}

    # 检查无效关系
    invalid = [r for r in relationships
               if r["source"] not in entity_ids or r["target"] not in entity_ids]
    if invalid:
        print(f"WARNING: 发现 {len(invalid)} 条无效关系，将被跳过")

    driver = GraphDatabase.driver(URI, auth=AUTH)
    driver.verify_connectivity()
    print("Neo4j 连接成功")

    with driver.session() as session:
        clear_graph(session)
        create_indexes(session)
        import_entities(session, entities)
        import_relationships(session, relationships, entity_ids)
        export_entity_dict(session, os.path.join(DATA_DIR, "entity_dict.json"))

    driver.close()
    print("全部完成")


if __name__ == "__main__":
    main()
