"""
4.2 向量检索工具：将问句向量化，在 Neo4j 向量索引中检索相似实体。
"""
import os
from pathlib import Path
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=FutureWarning)

# 加载 .env 文件（从项目根目录）
dotenv_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path)

from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7688")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "jys123456"))
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "embeddings", "bge-large-zh-v1.5")

_model = None
_driver = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_DIR)
    return _model


def _get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(URI, auth=AUTH)
    return _driver


def vector_search(query, k=5):
    """语义搜索 top-k 相似实体"""
    model = _get_model()
    vec = model.encode([query], normalize_embeddings=True)[0].tolist()

    with _get_driver().session() as session:
        results = session.run(
            "CALL db.index.vector.queryNodes('entity_vector_index', $k, $vec) "
            "YIELD node, score RETURN node.name, score "
            "ORDER BY score DESC",
            k=k, vec=vec
        )
        hits = []
        for r in results:
            hits.append(f"{r['node.name']}（相似度: {r['score']:.2f}）")

    if not hits:
        return "未找到语义相关实体。"
    return "语义匹配结果：\n" + "；\n".join(hits)


def close():
    global _driver
    if _driver:
        _driver.close()
        _driver = None
