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

# 复用图谱层的属性中文映射，保证向量检索返回的属性 key 与图谱一致
from .graph_tools import KEY_CN

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7688")
_NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
if not _NEO4J_PASSWORD:
    raise RuntimeError("未配置 NEO4J_PASSWORD：请在项目根目录 .env 中设置")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), _NEO4J_PASSWORD)
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


def _format_entity_node(node, score=None):
    """将 Neo4j 实体节点格式化为自然语言描述，与 graph_tools._format_entity 保持一致"""
    KEY_CN = {
        "compilationTitle": "书名", "contentType": "内容类型", "compiler": "编纂者",
        "editionInfo": "版本信息", "compilationStyle": "编纂体例",
        "annotationHistory": "注疏史", "volumeCount": "卷数", "volume": "卷数",
        "sourceText": "底本来源", "compilationFeature": "辑佚特征",
        "compilationPeriod": "辑佚时期", "compilationProcess": "辑佚过程",
        "completionPeriod": "成书时期", "publicationYear": "出版年份",
        "revisionHistory": "修订史", "roleInCompilation": "辑佚角色",
        "preserved_content": "保存内容", "publication": "出版信息",
        "notable_works": "重要著作", "key_works": "重要著作",
        "jing_section": "经部", "shi_section": "史部",
        "school": "学派", "academicLineage": "学术传承", "courtesyName": "字号",
        "courtesy name": "字号", "birthDeath": "生卒年", "nativePlace": "籍贯",
        "academicPosition": "学术地位", "academicRole": "学术角色",
        "academicImpact": "学术影响", "author": "作者", "editor": "编者",
        "organizer": "编纂者", "pseudonym": "别号",
        "key_compilers": "主要编纂者", "key_scholars": "主要学者",
        "representative_scholar": "代表性学者", "representatives": "代表人物",
        "methodName": "方法名", "methodDescription": "方法描述",
        "methodEvaluation": "方法评价", "methodCharacteristic": "方法特点",
        "methodology": "方法", "method": "方法", "methods": "方法",
        "methodological_skills": "方法技能", "steps": "步骤",
        "principles": "原则", "criteria": "标准", "standards": "标准",
        "resolution_1": "辨析一", "resolution_2": "辨析二", "resolution_3": "辨析三",
        "periodName": "时期", "period": "时期",
        "academicAtmosphere": "学术风气", "developmentStage": "发展阶段",
        "stage1": "阶段一", "stage2": "阶段二", "stage3": "阶段三", "stage4": "阶段四",
        "historical_evolution": "历史演变",
        "schoolName": "学派", "origin": "起源",
        "theory": "理论/方法", "theoretical_base": "理论基础",
        "representative_theory": "代表性理论", "representativeWork": "代表作",
        "academicLegacy": "学术遗产", "academicEvaluation": "学术评价",
        "academicValue": "学术价值", "contribution": "学术贡献",
        "researchFocus": "研究重点", "researchMethod": "研究方法",
        "originPeriod": "起源时期", "originDynasty": "起源朝代",
        "fieldOfStudy": "研究领域", "influence": "影响",
        "criticism": "批评", "critique": "批评", "issue": "学术问题",
        "issueName": "问题名", "impact": "影响",
        "significance": "意义", "value": "价值",
        "innovation": "创新", "limitations": "局限性",
        "description": "描述", "definition": "定义",
        "name": "名称", "title": "标题",
        "features": "特征", "feature": "特征", "characteristic": "特征",
        "content": "内容", "composition": "构成", "components": "构成",
        "structure": "结构", "categories": "分类", "sub_categories": "子类",
        "types": "类型", "elements": "要素",
        "scope": "范围", "status": "状态", "current_status": "当前状态",
        "nature": "性质", "objective": "目标", "purpose": "目的",
        "sources": "来源", "version": "版本",
        "case": "案例", "case_study": "案例研究", "example": "示例",
        "works": "著作", "other_works": "其他著作",
        "focus_areas": "重点领域", "foundational_knowledge": "基础知识",
        "data_features": "数据特征", "data_focus": "数据重点",
        "macro_perspective": "宏观视角", "special_value": "特殊价值",
        "modern_landmarks": "现代标志",
        "law_1": "定律一", "law_2": "定律二",
        "authorCount": "作者数量", "authors": "作者",
        "class_1_经": "经部类", "class_2_史": "史部类", "class_3_子": "子部类",
    }
    d = dict(node)
    name = d.pop("name", "")
    d.pop("id", "")
    d.pop("embedding", None)
    props = []
    for k, v in d.items():
        if not v:
            continue
        zh = KEY_CN.get(k, k)
        props.append(f"{zh}：{v}")
    prop_str = "；".join(props)
    body = f"{name}（{prop_str}）" if prop_str else name
    if score is not None:
        return f"{body} [向量相似度: {score:.2f}]"
    return body


def _format_entity_compact(node, score=None):
    """向量检索结果：返回实体名 + 类型标签 + 完整属性 + 相似度。

    向量检索是"语义兜底"，且普通检索流程（非深度思考）也会调用；
    若这里只返回实体名，普通流程不会再补查 kg_explore_entity 取属性，
    导致 agent 拿到名字却没有实体内容。因此直接下发完整属性。
    """
    d = dict(node)
    name = d.pop("name", "")
    d.pop("id", "")
    d.pop("embedding", None)
    # 过滤内部/冗余字段（多标签合并产生的噪音）
    for noise in ("mergedFromIds", "allDescriptions", "allCompilers",
                  "allCompilationPeriods", "allLabels", "allPeriodValues",
                  "allCompletionPeriods", "allEditionInfo"):
        d.pop(noise, None)
    type_labels = [lbl for lbl in node.labels if lbl != "Entity"]
    type_str = type_labels[0] if type_labels else ""
    props = []
    for k, v in d.items():
        if not v:
            continue
        zh = KEY_CN.get(k, k)
        props.append(f"{zh}：{v}")
    prop_str = "；".join(props)
    head = f"{name}（{type_str}）" if type_str else name
    body = f"{head}（{prop_str}）" if prop_str else head
    if score is not None:
        return f"{body} [向量相似度: {score:.2f}]"
    return body


def vector_search(query, k=5):
    """语义搜索 top-k 相似实体，仅返回实体名 + 类型 + 相似度（不返回完整属性）"""
    try:
        model = _get_model()
        vec = model.encode([query], normalize_embeddings=True)[0].tolist()

        with _get_driver().session() as session:
            # 先通过向量索引拿到 node + score
            results = session.run(
                "CALL db.index.vector.queryNodes('entity_vector_index', $k, $vec) "
                "YIELD node, score RETURN node, score "
                "ORDER BY score DESC",
                k=k, vec=vec
            )
            hits = []
            for r in results:
                node = r["node"]
                score = r["score"]
                # 余弦相似度理论范围 [-1,1]（归一化向量为 [0,1]），
                # 但索引开启 vector.quantization 后 ANN 近似分可能略超 1.0（如 1.01），夹回 [0,1]。
                score = min(max(score, 0.0), 1.0)
                if score < 0.60:  # 过滤低相关度结果
                    continue
                hits.append(_format_entity_compact(node, score))

        if not hits:
            return "未找到语义相关实体。"
        return "语义匹配结果：\n" + "\n".join(hits)
    except Exception as e:
        print(f"[Vector] 向量搜索失败: {e}")
        return "向量搜索失败"


def close():
    global _driver
    if _driver:
        _driver.close()
        _driver = None
