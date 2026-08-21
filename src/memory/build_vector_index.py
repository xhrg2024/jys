"""
为 Neo4j 中的实体节点生成 embedding 并构建向量索引。
用法：python src/memory/build_vector_index.py
"""
# Fix PyTorch 2.6 weights_only breaking change
import torch
_orig_load = torch.load
torch.load = lambda *a, **kw: _orig_load(*a, **{**kw, "weights_only": False})

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（从项目根目录）
dotenv_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path)

from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7688")
_NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
if not _NEO4J_PASSWORD:
    raise RuntimeError("未配置 NEO4J_PASSWORD：请在项目根目录 .env 中设置")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), _NEO4J_PASSWORD)

def main():
    # 1. 连接 Neo4j
    driver = GraphDatabase.driver(URI, auth=AUTH)
    driver.verify_connectivity()
    print("Neo4j 连接成功")

    # 2. 加载本地 embedding 模型
    MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "embeddings", "bge-large-zh-v1.5")
    print(f"加载 embedding 模型: {MODEL_DIR}")
    model = SentenceTransformer(MODEL_DIR)
    dim = model.get_embedding_dimension()
    print(f"模型加载完成，维度: {dim}")

    # 3. 取出所有实体，拼接文本
    with driver.session() as session:
        result = session.run("MATCH (e:Entity) RETURN e.id AS id, e.name AS name, properties(e) AS props")
        entities = []
        texts = []
        for r in result:
            props = r["props"]
            # 删掉 id/name，避免重复
            props.pop("id", None)
            props.pop("name", None)
            # 拼接所有属性值为一段文本
            prop_text = "，".join(str(v) for v in props.values() if v)
            full_text = f"{r['name']}：{prop_text}"
            entities.append(r["id"])
            texts.append(full_text)

        print(f"待向量化实体: {len(entities)}")

        # 4. 批量向量化
        print("正在向量化...")
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)

        # 5. 写回 Neo4j
        print("写回 Neo4j...")
        for eid, emb in zip(entities, embeddings):
            session.run(
                "MATCH (e:Entity {id: $id}) SET e.embedding = $emb",
                id=eid, emb=emb.tolist()
            )

    # 6. 建向量索引
    print("创建向量索引...")
    with driver.session() as session:
        # 先删旧索引（如果存在）
        try:
            session.run("DROP INDEX entity_vector_index")
        except:
            pass
        session.run(f"""
            CREATE VECTOR INDEX entity_vector_index
            FOR (e:Entity) ON e.embedding
            OPTIONS {{indexConfig: {{
                `vector.dimensions`: {dim},
                `vector.similarity_function`: 'cosine'
            }}}}
        """)
        print("向量索引创建完成")

    # 7. 验证
    with driver.session() as session:
        # 用一条测试查询验证
        test_vec = model.encode(["辑佚学方法"], normalize_embeddings=True)[0].tolist()
        result = session.run("""
            CALL db.index.vector.queryNodes('entity_vector_index', 3, $vec)
            YIELD node, score
            RETURN node.name, score
        """, vec=test_vec)
        print("\n验证查询 '辑佚学方法' top-3:")
        for r in result:
            print(f"  {r['node.name']} (score: {r['score']:.4f})")

    driver.close()
    print("\n全部完成")


if __name__ == "__main__":
    main()
