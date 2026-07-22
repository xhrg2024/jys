"""
4.1 图查询工具：Cypher 查询 Neo4j，结果转为自然语言。
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（从项目根目录）
dotenv_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path, override=True)

from neo4j import GraphDatabase

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7688")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "jys123456"))

_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(URI, auth=AUTH)
    return _driver


def _run(cypher, **params):
    with _get_driver().session() as session:
        try:
            return list(session.run(cypher, **params))
        except Exception as e:
            print(f"[Neo4j] Cypher 执行失败: {e}")
            return []


def _format_entity(rec, prefix="e"):
    """格式化一个实体节点为自然语言"""
    node = rec[prefix]
    KEY_CN = {
        # 辑本相关
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
        # 学者相关
        "school": "学派", "academicLineage": "学术传承", "courtesyName": "字号",
        "courtesy name": "字号", "birthDeath": "生卒年", "nativePlace": "籍贯",
        "academicPosition": "学术地位", "academicRole": "学术角色",
        "academicImpact": "学术影响", "author": "作者", "editor": "编者",
        "organizer": "编纂者", "pseudonym": "别号",
        "key_compilers": "主要编纂者", "key_scholars": "主要学者",
        "representative_scholar": "代表性学者", "representatives": "代表人物",
        # 方法相关
        "methodName": "方法名", "methodDescription": "方法描述",
        "methodEvaluation": "方法评价", "methodCharacteristic": "方法特点",
        "methodology": "方法", "method": "方法", "methods": "方法",
        "methodological_skills": "方法技能", "steps": "步骤",
        "principles": "原则", "criteria": "标准", "standards": "标准",
        "resolution_1": "辨析一", "resolution_2": "辨析二", "resolution_3": "辨析三",
        # 时间相关
        "periodName": "时期", "period": "时期",
        "academicAtmosphere": "学术风气",
        "developmentStage": "发展阶段",
        "stage1": "阶段一", "stage2": "阶段二", "stage3": "阶段三", "stage4": "阶段四",
        "historical_evolution": "历史演变",
        # 学术相关
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
        # 通用
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
        "modern_landmarks": "现代标志", "key_compilers": "主要编纂者",
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
    return f"{name}（{prop_str}）" if prop_str else name


def query_entity_by_name(name):
    """按名称查实体属性"""
    results = _run("MATCH (e {name: $name}) RETURN e", name=name)
    if not results:
        return f"未在知识图谱中找到“{name}”。"
    parts = []
    for r in results:
        parts.append(_format_entity(r))
    return "；\n".join(parts)


def query_entity_relations(entity_id):
    """查实体的所有一跳关系"""
    results = _run(
        "MATCH (e {id: $id})-[r]-(n) RETURN e.name AS entity, type(r) AS rel_type, r.description AS desc, n.name AS neighbor",
        id=entity_id
    )
    if not results:
        return f"“{entity_id}”无关联关系。"
    parts = []
    for r in results:
        desc = f"（{r['desc']}）" if r["desc"] else ""
        parts.append(f"{r['entity']} → {r['rel_type']} → {r['neighbor']}{desc}")
    return "\n".join(parts)


def get_neighbor_struct(entity_id):
    """查询实体的邻居（结构化返回，供多跳遍历使用）"""
    results = _run(
        "MATCH (e {id: $id})-[r]-(n) RETURN n.name AS name, n.id AS nid",
        id=entity_id
    )
    return [(r["name"], r["nid"]) for r in results]


def query_relation_between(name_a, name_b):
    """查两实体间最短路径"""
    results = _run(
        "MATCH p=shortestPath((a {name: $a})-[*..4]-(b {name: $b})) "
        "RETURN [n IN nodes(p) | n.name] AS path, "
        "[r IN relationships(p) | type(r)] AS rels",
        a=name_a, b=name_b
    )
    if not results:
        return f"“{name_a}”和“{name_b}”之间未找到关联路径。"
    r = results[0]
    steps = []
    for i in range(len(r["path"]) - 1):
        steps.append(f"{r['path'][i]} → {r['rels'][i]} → {r['path'][i+1]}")
    return "，".join(steps)


def query_by_label(label):
    """按类型查所有实体"""
    results = _run(
        "MATCH (e:Entity) WHERE $label IN labels(e) RETURN e.name AS name",
        label=label
    )
    names = [r["name"] for r in results]
    if not names:
        return f"无类型为“{label}”的实体。"
    return f"类型“{label}”包含以下实体：\n" + "、".join(names)


def close():
    global _driver
    if _driver:
        _driver.close()
        _driver = None
