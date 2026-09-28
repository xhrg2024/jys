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
_NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
if not _NEO4J_PASSWORD:
    raise RuntimeError("未配置 NEO4J_PASSWORD：请在项目根目录 .env 中设置")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), _NEO4J_PASSWORD)

_driver = None

# 路径查询黑名单：这些实体在路径遍历中作为中间节点时被屏蔽，避免高连通度的"枢纽"节点
# （如"辑佚"方法类实体）让任意两个实体之间都出现平凡路径。
# 仅影响 /path 的跳转遍历（起点/终点不受影响）；对黑名单节点本身直接检索其关系不受影响。
# 可通过环境变量 PATH_BLACKLIST（英文逗号分隔）覆盖，默认屏蔽「辑佚」。
_PATH_BLACKLIST_DEFAULT = "辑佚"
PATH_BLACKLIST = [
    n.strip()
    for n in os.environ.get("PATH_BLACKLIST", _PATH_BLACKLIST_DEFAULT).split(",")
    if n.strip()
]

# 路径查询改用无向 BFS（见 _find_paths），无跳数上限，黑名单中间节点在遍历时直接剪枝，
# 避免 Cypher 变长路径 `ORDER BY len` 带来的全路径枚举指数爆炸。

# 属性中文映射（模块级，供 _format_entity 与 /reference/graph 共用）
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
    "birthplace": "籍贯", "lifespan": "生卒年",
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



def _get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(URI, auth=AUTH)
    return _driver


class GraphDBError(Exception):
    """Neo4j 图数据库不可用或查询失败（区别于「查无结果」的空列表）。"""


def _run(cypher, **params):
    try:
        with _get_driver().session() as session:
            return list(session.run(cypher, **params))
    except GraphDBError:
        raise
    except Exception as e:
        print(f"[Neo4j] Cypher 执行失败: {e}")
        raise GraphDBError(f"Neo4j 数据库不可用或查询失败: {e}") from e


def _format_entity(rec, prefix="e"):
    """格式化一个实体节点为自然语言"""
    node = rec[prefix]
    d = dict(node)
    name = d.pop("name", "")
    d.pop("id", "")
    d.pop("embedding", None)
    # 剔除内部/冗余字段（多标签合并产生的噪音）
    for noise in ["mergedFromIds", "allDescriptions", "allCompilers",
                  "allCompilationPeriods", "allLabels"]:
        d.pop(noise, None)
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
        return f"未在知识图谱中找到「{name}」。"
    parts = []
    for r in results:
        parts.append(_format_entity(r))
    return "；\n".join(parts)


def resolve_entity(name=None, entity_id=None):
    """按 id（优先）或名称定位实体，返回单条记录（含 "e" 字段）或 None。
    仅按 name 时若存在同名实体（如"永乐大典"类书版 vs 辑本版），取邻居数最多的那个。
    """
    if entity_id:
        recs = _run("MATCH (e:Entity {id: $id}) RETURN e", id=entity_id)
    elif name:
        recs = _run("MATCH (e:Entity {name: $name}) RETURN e", name=name)
        if len(recs) > 1:
            def _degree(nid):
                d = _run("MATCH (a {id: $id})-[r]-(b) RETURN count(DISTINCT b) AS c", id=nid)
                return d[0]["c"] if d else 0
            recs = [max(recs, key=lambda r: _degree(r["e"].get("id", "")))]
    else:
        return None
    if not recs:
        return None
    return recs[0]


def query_entity_detail(name=None, entity_id=None):
    """按 id（优先）或名称返回实体结构化详情：{id, name, label, properties}。
    properties 的 key 已用 KEY_CN 映射为中文，值保留原始类型（含列表）。
    仅按 name 时同名实体取邻居最多者；供前端结构化渲染实体信息卡；查无结果返回 None。
    """
    rec = resolve_entity(name=name, entity_id=entity_id)
    if rec is None:
        return None
    node = rec["e"]
    d = dict(node)
    name_val = d.pop("name", "")
    eid = d.pop("id", "")
    d.pop("embedding", None)
    # 剔除内部/冗余字段（多标签合并产生的噪音）
    for noise in ["mergedFromIds", "allDescriptions", "allCompilers",
                  "allCompilationPeriods", "allLabels", "allPeriodValues",
                  "allCompletionPeriods", "allEditionInfo"]:
        d.pop(noise, None)
    labels = [l for l in node.labels if l != "Entity"]
    label = labels[0] if labels else "Entity"
    props = {KEY_CN.get(k, k): v for k, v in d.items() if v}
    return {"id": eid, "name": name_val, "label": label, "properties": props}


def query_entity_relations(entity_id, limit=None):
    """查实体的所有一跳关系，可选限制数量"""
    cypher = (
        "MATCH (e {id: $id})-[r]-(n) "
        "RETURN e.name AS entity, type(r) AS rel_type, r.description AS desc, n.name AS neighbor"
    )
    if limit:
        cypher += f" LIMIT {int(limit)}"
    results = _run(cypher, id=entity_id)
    if not results:
        return f"「{entity_id}」无关联关系。"
    parts = []
    for r in results:
        desc = f"（{r['desc']}）" if r["desc"] else ""
        parts.append(f"{r['entity']} → {r['rel_type']} → {r['neighbor']}{desc}")
    suffix = f"\n（以上为前{limit}条关系，共查到{len(results)}条）" if limit and len(results) >= limit else ""
    return "\n".join(parts) + suffix


def get_neighbor_struct(entity_id):
    """查询实体的邻居（结构化返回，供多跳遍历使用）"""
    results = _run(
        "MATCH (e {id: $id})-[r]-(n) RETURN n.name AS name, n.id AS nid",
        id=entity_id
    )
    return [(r["name"], r["nid"]) for r in results]


def _load_undirected_graph():
    """载入全图无向邻接（当前小图，一次载入），供 BFS 做无跳数上限的最短路径搜索。
    node_meta: id -> (name, label)；adj: id -> [(neighbor_id, rel_type, description)]。
    注：图较大时应改为按层增量查询邻居，避免一次载入全图。
    """
    rows = _run(
        "MATCH (a:Entity)-[r]-(b:Entity) "
        "RETURN a.id AS aid, a.name AS an, "
        "[l IN labels(a) WHERE l <> 'Entity'][0] AS al, "
        "b.id AS bid, b.name AS bn, "
        "[l IN labels(b) WHERE l <> 'Entity'][0] AS bl, "
        "type(r) AS rt, r.description AS desc"
    )
    node_meta = {}
    adj = {}

    def ensure(nid, name, label):
        if nid not in node_meta:
            node_meta[nid] = (name, label or "Entity")
            adj.setdefault(nid, [])

    for r in rows:
        ensure(r["aid"], r["an"], r["al"])
        ensure(r["bid"], r["bn"], r["bl"])
        desc = r["desc"] or ""
        adj[r["aid"]].append((r["bid"], r["rt"], desc))
        adj[r["bid"]].append((r["aid"], r["rt"], desc))
    return node_meta, adj


def _find_paths(name_a, name_b, blacklist, max_paths=3):
    """无向 BFS 求避开黑名单中间节点的最短若干条路径（无跳数上限）。
    返回 [{"length": L, "nodes": [{id,name,label}], "edges": [{source,target,type,description}]}]。
    查无结果返回 None。起点/终点不受黑名单影响。
    """
    from collections import deque
    node_meta, adj = _load_undirected_graph()

    start_ids = [i for i, (n, _) in node_meta.items() if n == name_a]
    target_ids = set(i for i, (n, _) in node_meta.items() if n == name_b)
    if not start_ids or not target_ids:
        return None
    black_set = set(blacklist)

    dist = {sid: 0 for sid in start_ids}
    parents = {sid: [] for sid in start_ids}
    queue = deque(start_ids)
    found_targets = []
    min_target_dist = None

    while queue:
        cur = queue.popleft()
        # BFS 按层扩展；处理完最浅目标所在层即可停止
        if min_target_dist is not None and dist[cur] > min_target_dist:
            break
        if cur in target_ids:
            found_targets.append(cur)
            min_target_dist = dist[cur]
            continue
        for nbr, rt, desc in adj.get(cur, []):
            name_nbr = node_meta.get(nbr, ("", "Entity"))[0]
            # 黑名单剪枝：仅当 nbr 为中间节点（非起点、非终点）时生效
            if name_nbr in black_set and nbr not in target_ids and nbr not in start_ids:
                continue
            nd = dist[cur] + 1
            if nbr not in dist:
                dist[nbr] = nd
                parents.setdefault(nbr, []).append(cur)
                queue.append(nbr)
            elif dist[nbr] == nd:
                # 等长的另一条最短路
                parents[nbr].append(cur)

    if not found_targets:
        return None

    # 回溯所有最短路（限 max_paths 条）
    def backtrack(node, acc):
        full = [node] + acc
        if node in start_ids:
            return [full]
        out = []
        for p in parents.get(node, []):
            out.extend(backtrack(p, full))
        return out

    path_ids_list = []
    seen = set()
    for t in found_targets:
        for p in backtrack(t, []):
            # 同名实体（如多个"惠栋"）会回溯出名字相同、仅 id 不同的重复路径，按名字序列去重
            sig = tuple(node_meta[pid][0] for pid in p)
            if sig in seen:
                continue
            seen.add(sig)
            path_ids_list.append(p)
            if len(path_ids_list) >= max_paths:
                break
        if len(path_ids_list) >= max_paths:
            break

    paths = []
    for pids in path_ids_list:
        nodes = [{"id": pid, "name": node_meta[pid][0], "label": node_meta[pid][1]} for pid in pids]
        edges = []
        for i in range(len(pids) - 1):
            a, b = pids[i], pids[i + 1]
            rt, desc = "RELATES", ""
            for nbr, r_type, r_desc in adj.get(a, []):
                if nbr == b:
                    rt, desc = r_type, r_desc
                    break
            edges.append({"source": a, "target": b, "type": rt, "description": desc})
        paths.append({"length": len(edges), "nodes": nodes, "edges": edges})
    return paths


def query_relation_between(name_a, name_b):
    """查两实体间最短路径（最多 3 条，按长度升序），文本形式。
    中间节点命中 PATH_BLACKLIST 的路径会被跳过（起点/终点不受影响）。
    """
    paths = _find_paths(name_a, name_b, PATH_BLACKLIST)
    if not paths:
        return f"「{name_a}」和「{name_b}」之间未找到关联路径。"
    all_paths = []
    for idx, p in enumerate(paths):
        names = [n["name"] for n in p["nodes"]]
        steps = []
        for i in range(len(names) - 1):
            steps.append(f"{names[i]} → {p['edges'][i]['type']} → {names[i+1]}")
        path_str = "，".join(steps)
        label = f"路径{idx+1}" if len(paths) > 1 else "路径"
        all_paths.append(f"{label}（{p['length']}跳）：{path_str}")
    return "\n".join(all_paths)


def query_path_struct(name_a, name_b):
    """查两实体间最短路径（最多 3 条，按长度升序），返回结构化 nodes/edges 供前端可视化。
    中间节点命中 PATH_BLACKLIST 的路径会被跳过（起点/终点不受影响）。查无结果返回 None。
    """
    return _find_paths(name_a, name_b, PATH_BLACKLIST)


def query_by_label(label, limit=None):
    """按类型查所有实体，可选限制数量"""
    cypher = (
        "MATCH (e:Entity) WHERE $label IN labels(e) RETURN e.name AS name"
    )
    if limit:
        cypher += f" LIMIT {int(limit)}"
    results = _run(cypher, label=label)
    names = [r["name"] for r in results]
    if not names:
        return f"无类型为\"{label}\"的实体。"
    suffix = f"（共{len(names)}个）" if limit else ""
    return f"类型\"{label}\"包含以下实体{suffix}：\n" + "、".join(names)


def explore_entity(name):
    """高层工具：深度探索一个实体——属性 + 全部关系 + 关联实体属性。
    封装了多跳遍历逻辑，一次调用返回完整画像。比单独调用 query_entity_by_name
    和 query_entity_relations 更全面。
    """
    parts = []

    # 1. 查实体自身属性（用 e.id 属性而非弃用的 id() 函数）
    entity_results = _run("MATCH (e {name: $name}) RETURN e, e.id AS eid", name=name)
    if not entity_results:
        return f"未在知识图谱中找到「{name}」。"

    for rec in entity_results:
        eid = rec["eid"]
        parts.append(f"【{name}】{_format_entity(rec)}")

        # 2. 查该实体的所有关系（用属性 id 匹配）
        rel_results = _run(
            "MATCH (e {id: $id})-[r]-(n) "
            "RETURN type(r) AS rel_type, r.description AS desc, n.name AS neighbor, "
            "labels(n) AS n_labels, n.id AS nid LIMIT 30",
            id=eid
        )
        if rel_results:
            rel_lines = []
            neighbors_seen = set()
            for rr in rel_results:
                desc = f"（{rr['desc']}）" if rr["desc"] else ""
                rel_lines.append(f"  {name} → {rr['rel_type']} → {rr['neighbor']}{desc}")
                neighbors_seen.add((rr["neighbor"], rr["nid"]))

            parts.append(f"  关系网络（{len(rel_lines)}条）：")
            parts.extend(rel_lines)

            # 3. 对关键邻居做浅层属性查询（选前 5 个不同标签的）
            neighbor_list = list(neighbors_seen)[:5]
            for nname, nid in neighbor_list:
                n_recs = _run("MATCH (e {id: $id}) RETURN e", id=nid)
                for nr in n_recs:
                    parts.append(f"  └ 关联实体：{_format_entity(nr)}")

    return "\n".join(parts)


def explore_relation(entity_a, entity_b):
    """高层工具：深度探索两个实体之间的关系——各自属性 + 各自关系网络 + 最短路径 + 共同邻居。
    封装了 relation_search + multi_hop 逻辑，一次调用完成全面关系分析。
    """
    parts = []
    parts.append(f"═══ 实体 A：{entity_a} ═══")
    parts.append(explore_entity(entity_a))
    parts.append("")
    parts.append(f"═══ 实体 B：{entity_b} ═══")
    parts.append(explore_entity(entity_b))
    parts.append("")
    parts.append(f"═══ 最短路径：{entity_a} ↔ {entity_b} ═══")
    parts.append(query_relation_between(entity_a, entity_b))

    return "\n".join(parts)


def close():
    global _driver
    if _driver:
        _driver.close()
        _driver = None
