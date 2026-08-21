"""
规划层（5.1-5.5）：检索策略选择、多跳查询、结果融合、RACE Prompt 构建、后处理。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from perception.question_parser import QuestionParser
from tools import graph_tools, vector_tools, sql_tools

# ── RACE 固定模板（与训练数据一致）──
# 版本: v2.0 — 扩展优化版
RACE_SYSTEM = """【R-角色】你是一位专精于辑佚学（中国古典文献辑佚）的资深AI研究助手。你的知识体系全面覆盖以下领域：

1. 辑佚学基础：唐宋类书（《太平御览》《册府元龟》《艺文类聚》《初学记》等）辑佚方法、佚书源流考证、佚文鉴别与归派
2. 辑佚学史：从宋代王应麟发端，经明代零散辑佚，至清代乾嘉时期大规模辑佚（马国翰、黄奭、严可均、王谟等）的完整学术脉络
3. 辑佚方法论：校勘（对校、他校、理校）、辨伪（内证、外证、旁证）、考证（本证、旁证、默证）、定派（据书定派、据人定派、据说定派）等方法体系
4. 辑佚流派与学术传承：乾嘉考据学派、常州学派、扬州学派等的辑佚实践与相互影响
5. 类书与辑本关系：笔记体、类书体、小学书中的佚文分布规律

【A-行动】请严格按照以下四步流程基于【参考信息】回答用户问题。

第一步 ─ 意图理解：
- 判断用户问题属于哪种类型：事实查证（FACTUAL）、关联分析（RELATION）、脉络梳理（CHAIN）、方法探讨（METHOD）、比较辨析（COMPARE）
- 明确回答所需的关键要素：何类实体、何种关系、何时段、何方法

第二步 ─ 证据定位：
- 在参考信息中精准定位与问题相关的实体名称、属性及关系描述
- 区分直接证据（与问题直接相关的实体）和辅助证据（提供背景的关联实体）
- 注意参考信息中可能存在的多源信息交叉印证

第三步 ─ 逻辑组织：
- 根据问题类型选择恰当的叙述结构：
  · 事实类：结论先行 → 关键证据 → 补充说明
  · 关联类：两方实体分别说明 → 共同交集/关联点 → 整体判断
  · 脉络类：时间线分段（起→承→转→合）→ 各阶段特征总结
  · 方法类：概念定义 → 操作程序 → 适用条件 → 代表案例
  · 比较类：共同前提 → 差异逐项对比（表格优先）→ 异同总结

第四步 ─ 分析与回答：
- 基于以上步骤构建完整回答，每条关键信息标注出处
- 参考信息不足时，明确标注"据现有参考信息"的可靠部分与存疑部分

【E-期望】请严格遵循以下输出规范：

1. 答案结构
   · 全文必须采用以下三段式结构：[结论] — 一句话明确回答核心问题 → [论据] — 分层展开证据与推理 → [总结] — 提炼核心观点或提出延伸思考
   · 段落之间以空行分隔，保持清晰的信息层级

2. 来源标注规范
   · 参考信息全部来自知识图谱和数据库检索，其中并无"魏源""《四库全书》""《清史稿》"等外部来源名
   · 标注出处时，使用参考信息中实际出现的实体名称，格式为"（据{实体名}）"，例如"（据马国翰）""（据玉函山房辑佚书）"
   · 当无法对应到具体实体时，统一使用"（据参考信息）"，绝对禁止编造任何参考信息中未出现的来源名称
   · 引用参考信息中的直接数据（卷数、年代、数量等）必须紧附来源标注
   · 多源信息交叉印证时，标注格式为"（据{实体A}；据{实体B}）"
   · 【严禁】使用"魏源""魏源记载""据魏源"等任何包含"魏源"的来源标注 — 参考信息中从未出现此来源

3. 学术用语层级
   · 确凿无疑的信息：使用"据记载"、"据考证"、"由{文献名}可知"
   · 证据支持但非直接的信息：使用"推测"、"可推断"、"很可能"
   · 缺乏直接证据的关联：使用"或可认为"、"有待考证"

4. 不确定性处理
   · 参考信息完全不足以回答时：直接回复"根据现有参考信息，无法明确回答该问题"，并说明缺失哪些关键信息
   · 参考信息部分不足时：明确划分"有据可查"与"存疑待考"两部分
   · 参考信息存在矛盾时：如实呈现双方记述，不做强行统一

5. 语言风格
   · 采用现代学术中文，简洁、准确、客观
   · 全文必须使用简体中文，不得出现繁体字
   · 避免过度修辞，以信息传达为首要目标
   · 禁止使用口语化表达、网络用语或主观评价性语言

6. 【严格禁止】实体名精确性
   · 必须且只能使用参考信息中出现的实体名称原文，绝对禁止编造、改写、增减任何字
   · 示例：参考信息写"马国翰"时，必须用"马国翰"，不得写成"马国磐"、"马国槃"、"马国翰（清代）"等任何变体
   · 实体名中不得插入空格、括号、标点等无关字符
   · 书名尤其容易出错：参考信息写"玉函山房辑佚书"，必须照抄，不得写成"玉函山房辑佚书书"（多字）或"玉函山房辑书"（少字）
   · 参考信息写"玉函山房辑佚书续编"，不得写成"玉函山房辑佚书书续编"（多一"书"字）

7. 【严格禁止】数字信息精确性
   · 所有数字信息（卷数：如"579条"；年代：如"约1840年代"；数量：如"三部"等）必须与参考信息严格一致
   · 不得对数字进行四舍五入、估算扩缩或任何形式的修改
   · 参考信息中未提供的数字，不得自行编造

8. 回答长度控制
   · 简洁回答（一般性问题）：150-300字
   · 详细回答（需要多源论证的问题）：300-600字
   · 综合分析（脉络梳理、比较类问题）：600-1000字
   · 当回答需要超过1000字时，在末尾添加"（以上为基于参考信息的主要分析，如需进一步深入某一方面可继续提问）"

9. 多轮对话处理
   · 用户后续提问与前文相关时，如需引用前文已提供的信息，应以"如上所述"或"前文已提及"引用，避免重复表述
   · 用户在同一话题下追问时，可适当精简背景信息，聚焦追问点

10. 格式规范
    · 比较类回答优先使用表格呈现逐项对比
    · 脉络类回答优先使用时间线或序号列举
    · 全文不使用Markdown标记语言（不加**、##、-等标记）
    · 不使用英文标点，全部使用中文全角标点

11. 【附加要求】来源编号标注（照抄原始编号，不重排）
    · 参考信息中的每条内容已有固定编号（形如 [1] [2] [3] …），引用时直接使用该条内容本身的编号
    · 编号必须与参考信息中该条内容的编号一一对应：引用第几条就标 [几]，严禁自行按引用顺序重新编号
    · 示例：你引用的内容来自参考信息第5条，就标 [5]，绝对不要改成 [1]
    · 多条引用使用 [1][2] 或 [3][5] 格式，未引用参考信息的内容不加编号
    · 【严禁】使用 [补]、[续]、[甲]、[一] 等非数字编号，只允许使用 [数字] 格式"""

MAX_CHARS_REF = 6000  # C 段参考信息最大字数（6000*3=18000 字，约 9000 token）

# 数据库 dynasty 列存的是单字，需要做映射
DYNASTY_TO_DB = {
    "清代": "清", "明代": "明", "宋代": "宋", "唐代": "唐", "元代": "元",
    "漢代": "汉", "汉代": "汉", "秦代": "秦", "晋代": "晋",
    "隋代": "隋", "先秦": "先秦", "三国": "三国", "南北朝": "南北朝",
    "五代十国": "五代十国", "民国": "民国", "近现代": "近现代", "当代": "当代",
    # 单字直接映射到自身
    "清": "清", "明": "明", "宋": "宋", "唐": "唐", "元": "元",
    "汉": "汉", "秦": "秦", "晋": "晋", "隋": "隋",
}

# 现代辑佚学术语 → 古籍原文中实际出现的同义/相关词
# 数据库 full_text_1 中"辑佚"命中 0 条，需用古文献用语替代
CLASSICAL_SYNONYMS = {
    "辑佚": ["校勘", "考证", "训诂", "辨伪", "佚文", "散佚", "遗书", "逸书"],
    "辑佚学": ["校勘", "考证", "训诂", "辨伪", "目录"],
    "辑佚方法": ["校勘", "考证", "辨伪", "版本", "目录"],
    "辑佚三原则": ["校勘", "考证", "辨伪", "训诂"],
    "类书": ["类书", "类事", "类文", "事文"],
    "校勘": ["校勘", "校对", "校订", "校雠"],
    "辨伪": ["辨伪", "真伪", "伪书", "托名"],
    "考证": ["考证", "考据", "考订", "考辨"],
}

# 问句中要剔除的疑问词
QUESTION_NOISE = ["是什么", "有哪些", "经历了", "哪几个", "怎么样", "如何",
                   "怎样", "为什么", "什么", "多少", "哪", "吗", "呢", "？", "?"]


class Planner:
    def __init__(self):
        self.parser = QuestionParser()

    # ── 关键词清洗 ──
    @staticmethod
    def _clean_topic(raw):
        """从正则提取的粗糙 topic 中剔除疑问词和数量修饰，得到干净的搜索词"""
        import re
        text = raw.strip()
        # 去掉常见疑问词碎片
        for noise in QUESTION_NOISE:
            text = text.replace(noise, "")
        # 去掉"的三"、"的二"等数量修饰残余（如"辑佚的三"→"辑佚"）
        text = re.sub(r'的[一二三四五六七八九十两几][种类个项条]?$', '', text)
        # 去掉"有几"、"有哪些"等
        text = re.sub(r'有几$', '', text)
        text = re.sub(r'有哪些$', '', text)
        # 去掉末尾的"的之了着过"
        text = text.rstrip("的之了着过")
        # 如果 topic 仍然很长（>8字），可能混入了无关文字，取前段
        if len(text) > 8:
            for sep in ["经历", "发展", "包括", "涉及", "哪"]:
                idx = text.find(sep)
                if 2 <= idx <= 8:
                    text = text[:idx]
                    break
        return text.strip()

    @staticmethod
    def _search_dynasty(dynasty_name):
        """尝试用映射后的朝代值查询数据库"""
        db_value = DYNASTY_TO_DB.get(dynasty_name, dynasty_name)
        res = sql_tools.query_document_by_dynasty(db_value)
        if "未找到" not in res:
            return res
        # 如果映射值查不到，尝试原始值（处理单字已在映射中的情况）
        if db_value != dynasty_name:
            res = sql_tools.query_document_by_dynasty(dynasty_name)
            if "未找到" not in res:
                return res
        return None

    @staticmethod
    def _extract_sql_keywords(question, topic=""):
        """从问句中提取古籍原文中可能出现的搜索词。
        优先用 CLASSICAL_SYNONYMS 映射，其次用 topic 本身，再兜底用预设学术词。
        """
        keywords = set()
        # 1. 从同义词表查找
        for modern, classical_list in CLASSICAL_SYNONYMS.items():
            if modern in question:
                keywords.update(classical_list)
        # 2. 添加清洗后的 topic
        if topic:
            clean = Planner._clean_topic(topic)
            if clean and len(clean) >= 2:
                keywords.add(clean)
        # 3. 兜底：问句中出现的已知高频学术词
        FALLBACK_TERMS = ["校勘", "训诂", "考证", "辨伪", "版本", "目录", "类书",
                          "永乐", "太平", "艺文", "初学", "古今", "集成"]
        for term in FALLBACK_TERMS:
            if term in question:
                keywords.add(term)
        # 4. 最多取 5 个，按词长降序（长词更精确）
        sorted_kw = sorted(keywords, key=lambda x: -len(x))[:5]
        return sorted_kw if sorted_kw else [topic] if topic else []

    def plan(self, question, intent_override=None, tool_results=None, logger=None):
        """主入口：给定用户问题，返回完整 RACE Prompt 和检索摘要。
        tool_results: LLM tool-calling 返回的工具执行结果列表，
                      格式 [{"name": str, "result": str}, ...]。
                      为 None 时使用硬编码分派（fallback）。
        logger: SessionLogger 实例，传入时写入完整无截断的检索日志。
        """
        # 感知
        parsed = self.parser.parse(question)
        intent = intent_override or parsed["intent"]
        entities = parsed["entities"]

        # 检索策略选择 (5.1)
        graph_results = []
        vector_results = []
        sql_results = []

        if tool_results:
            # ── LLM Tool-Calling 路径 ──
            for tr in tool_results:
                name = tr.get("name", "")
                result = tr.get("result", "")
                if not result:
                    continue
                # 日志：完整工具结果（不截断）
                if logger:
                    logger.log_tool_result(name, result)
                # 纯"未找到"结果不作为可引用来源（仍保留在日志中供排查）。
                # 图谱负结果用「未在知识图谱中找到」，不含「未找到」二字，需单独过滤，
                # 否则负结果漏进 prompt 浪费上下文。「向量搜索失败」是硬错误信号，不过滤。
                if "未找到" in result or "未在知识图谱中找到" in result:
                    continue
                # 按工具名前缀分类到 graph / vector / sql
                if name.startswith("kg_"):
                    graph_results.append(f"[{name}] {result}")
                elif name == "vector_search":
                    vector_results.append(result)
                else:
                    # SQL 工具：把关键参数内嵌进前缀（如 [search_full_text:校勘]、
                    # [browse_documents:综合性类书,明]），供 _merge 生成尾注/复用缓存时提取。
                    args = tr.get("args") or {}
                    if name in ("search_full_text", "search_titles") and args.get("keyword"):
                        sql_results.append(f"[{name}:{args['keyword']}] {result}")
                    elif name == "browse_documents":
                        cat = args.get("category") or ""
                        dyn = args.get("dynasty") or ""
                        if cat or dyn:
                            sql_results.append(f"[{name}:{cat},{dyn}] {result}")
                        else:
                            sql_results.append(f"[{name}] {result}")
                    else:
                        sql_results.append(f"[{name}] {result}")
            print(f"[Planner] Tool-Calling: "
                  f"{len(graph_results)} graph, {len(sql_results)} sql, {len(vector_results)} vector")

        else:
            # ── Fallback：硬编码分派（完整保留）──
            if intent == "FACTUAL":
                graph_results = self._factual_search(entities, parsed["parsed"])
                sql_results = self._sql_factual_search(question, parsed["parsed"])
                if not graph_results and not sql_results:
                    vector_results = [vector_tools.vector_search(question, k=5)]

            elif intent == "RELATION":
                graph_results = self._relation_search(entities, parsed["parsed"])
                sql_results = self._sql_relation_search(question, parsed["parsed"])
                if not graph_results and not sql_results:
                    vector_results = [vector_tools.vector_search(question, k=5)]

            elif intent == "CHAIN":
                graph_results = self._chain_search(entities, parsed["parsed"])
                sql_results = self._sql_chain_search(question, parsed["parsed"])
                vector_results = [vector_tools.vector_search(question, k=5)]

            elif intent == "METHOD":
                graph_results = self._method_search(parsed["parsed"])
                sql_results = self._sql_method_search(question, parsed["parsed"])
                vector_results = [vector_tools.vector_search(question, k=5)]

            elif intent == "COMPARE":
                graph_results = self._compare_search(entities, parsed["parsed"])
                sql_results = self._sql_compare_search(question, parsed["parsed"])
                vector_results = [vector_tools.vector_search(question, k=5)]

        # 工具调用日志
        graph_count = len([r for r in graph_results if r])
        sql_count = len([r for r in sql_results if r])
        vector_count = len([r for r in vector_results if r])
        sql_detail = [r[:800] for r in sql_results if r]
        graph_detail = [r[:400] for r in graph_results if r]
        vector_detail = [r[:300] for r in vector_results if r]

        # 工具来源标识
        if tool_results:
            tool_names = [tr.get("name", "?") for tr in tool_results if tr.get("result")]
            source_label = f"LLM Tool Calling ({len(tool_names)} tools: {', '.join(tool_names)})"
        else:
            source_label = "硬编码分派 (Fallback)"

        print(f"\n{'─'*60}")
        print(f"[Planner] 意图: {intent} | 来源: {source_label}")
        print(f"[Planner] 问题: {question[:80]}")
        print(f"[工具调用] 图查询: {graph_count}条 | "
              f"SQL查询: {sql_count}条 | "
              f"向量检索: {vector_count}条")
        for r in graph_results:
            if r:
                print(f"  🔗 {r[:300]}")
        for r in sql_results:
            if r:
                print(f"  🗄️ {r[:600]}")
        for r in vector_results:
            if r:
                print(f"  🔍 {r[:200]}")
        print(f"{'─'*60}")

        # ── 完整日志（不截断，写入文件）──
        if logger:
            logger.log_graph_results(graph_results)
            logger.log_sql_results(sql_results)
            logger.log_vector_results(vector_results)

        # 结果融合 (5.3)
        context, source_index = self._merge(graph_results, vector_results, sql_results)
        if logger:
            logger.log_context(context)
            logger.log_source_index(source_index)

        # RACE Prompt 构建 (5.4)
        prompt = self._build_race_prompt(question, context)

        # 构建结构化的工具调用摘要（供评估页面展示）
        tool_summary = self._build_tool_summary(tool_results, graph_results, sql_results, vector_results)

        return {
            "parsed": parsed,
            "context": context,
            "prompt": prompt,
            "intent": intent,
            # 评估用日志
            "plan_log": {
                "intent": intent,
                "graph_count": graph_count,
                "sql_count": sql_count,
                "vector_count": vector_count,
                "sql_details": sql_detail,
                "graph_details": graph_detail,
                "vector_details": vector_detail,
                "entities_matched": [(e["name"], e["label"]) for e in entities[:5]],
                "question": question,
                "tool_summary": tool_summary,
                "using_tool_calling": bool(tool_results),
                "source_index": source_index,
            }
        }

    # ── 多跳查询 (5.2) ──

    def _multi_hop(self, seed_entities, max_hops=3):
        """从种子实体出发，迭代查询多跳邻域。遇到环路或最大跳数停止。

        批量查询：每一跳只发 2 次 Cypher（本层属性 + 本层关系/邻居），
        而非每实体 3 次往返——否则 frontier 按「每实体 3 邻居」指数扩张时，
        会放大成 ~78 次 N+1 查询。
        """
        visited_ids = set()
        all_results = []
        frontier = [(e["id"], e["name"]) for e in seed_entities if e.get("id")]

        for hop in range(max_hops):
            if not frontier:
                break
            # 去掉本层已访问过的实体（只处理首次出现的）
            frontier = [(eid, ename) for eid, ename in frontier if eid not in visited_ids]
            if not frontier:
                break
            ids = [eid for eid, _ in frontier]
            for eid, _ in frontier:
                visited_ids.add(eid)

            # 1) 批量查本层实体属性（按 id 精确定位，避免同名实体歧义）
            prop_recs = graph_tools._run("MATCH (e) WHERE e.id IN $ids RETURN e", ids=ids)
            for rec in prop_recs:
                text = graph_tools._format_entity(rec)
                if text and text not in all_results:
                    all_results.append(text)

            # 2) 批量查关系 + 邻居（一次往返同时拿到关系文本和下一跳候选）
            rel_recs = graph_tools._run(
                "MATCH (e)-[r]-(n) WHERE e.id IN $ids "
                "RETURN e.id AS eid, e.name AS entity, type(r) AS rel_type, "
                "r.description AS desc, n.name AS neighbor, n.id AS nid",
                ids=ids,
            )
            rel_by_entity = {}
            next_candidates = {}
            for r in rel_recs:
                eid = r["eid"]
                desc = f"（{r['desc']}）" if r["desc"] else ""
                rel_by_entity.setdefault(eid, []).append(
                    f"{r['entity']} → {r['rel_type']} → {r['neighbor']}{desc}"
                )
                if r["nid"] and r["nid"] not in visited_ids:
                    next_candidates.setdefault(eid, []).append((r["nid"], r["neighbor"]))

            # 本层关系文本（每实体最多 10 条，供 C 段显示）
            for eid, _ in frontier:
                lines = rel_by_entity.get(eid, [])[:10]
                if lines:
                    text = "\n".join(lines)
                    if text not in all_results:
                        all_results.append(text)

            # 下一跳：每实体最多扩展 3 个邻居（保持原语义，限制 frontier 指数增长）
            next_frontier = []
            seen_next = set()
            for eid, _ in frontier:
                for nid, nname in next_candidates.get(eid, [])[:3]:
                    if nid not in seen_next and nid not in visited_ids:
                        seen_next.add(nid)
                        next_frontier.append((nid, nname))
            frontier = next_frontier

        return all_results

    # ── 检索策略 (5.1) ──

    def _factual_search(self, entities, parsed):
        results = []
        for e in entities[:3]:
            results.append(graph_tools.query_entity_by_name(e["name"]))
        return results

    def _relation_search(self, entities, parsed):
        results = []
        a = parsed.get("entity_a")
        b = parsed.get("entity_b")
        if a and b:
            results.append(graph_tools.query_relation_between(a, b))
        # 多跳查询：从已知实体出发，探索关联网络
        results.extend(self._multi_hop(entities[:2], max_hops=2))
        return results

    def _chain_search(self, entities, parsed):
        results = []
        # 多跳：从时间实体出发，展开脉络关联
        time_entities = [e for e in entities if e["label"] == "Time"]
        if time_entities:
            results.extend(self._multi_hop(time_entities, max_hops=2))
        # 也查主题实体（先清洗 topic，避免"辑佚的三"这类残留）
        topic = parsed.get("topic", "")
        if topic:
            clean = self._clean_topic(topic)
            if clean:
                results.append(graph_tools.query_entity_by_name(clean))
        return results

    def _method_search(self, parsed):
        results = []
        # 优先用清洗后的 topic 精准查实体，不要直接列所有 Method
        topic = parsed.get("topic", "")
        clean_topic = self._clean_topic(topic) if topic else ""
        if clean_topic:
            entity_res = graph_tools.query_entity_by_name(clean_topic)
            if "未在知识图谱中找到" not in entity_res:
                results.append(entity_res)
                # 同时查该实体的关联关系，获取方法论细节（限制数量避免撑满上下文）
                id_recs = graph_tools._run(
                    "MATCH (e {name: $name}) RETURN e.id AS id", name=clean_topic
                )
                for rec in id_recs:
                    rel_res = graph_tools.query_entity_relations(rec["id"], limit=10)
                    if rel_res and "无关联关系" not in rel_res:
                        results.append(rel_res)
            else:
                # topic 实体没找到，降级列出 Method 类型（限制数量）
                results.append(graph_tools.query_by_label("Method", limit=30))
        else:
            # 无 topic，列出 Method 类型（限制数量）
            results.append(graph_tools.query_by_label("Method", limit=30))
        return results

    def _compare_search(self, entities, parsed):
        results = []
        for e in entities[:2]:
            results.append(graph_tools.query_entity_by_name(e["name"]))
            results.append(graph_tools.query_entity_relations(e["id"], limit=10))
        a = parsed.get("entity_a")
        b = parsed.get("entity_b")
        if a and b:
            results.append(graph_tools.query_relation_between(a, b))
        return results

    # ── SQL 检索方法 ──
    # 数据库关键约束：仅 8 部类书有全文，"辑佚"命中 0 条
    # 策略：用 _extract_sql_keywords 将现代术语映射为古籍中真实出现的词汇

    def _sql_factual_search(self, question, parsed):
        """事实类：查文献元数据 + 正文内容 + 作者信息"""
        results = []
        primary = parsed.get("primary_entity", "")
        if primary:
            clean = self._clean_topic(primary)
            if clean:
                doc_res = sql_tools.search_document(clean)
                if "未找到" not in doc_res:
                    results.append(f"[SQL 文献详情] {doc_res}")
                author_res = sql_tools.query_author_by_name(clean)
                if "未找到" not in author_res:
                    results.append(f"[SQL 作者查询] {author_res}")
        # 如果实体链路没找到文献，用关键词兜底
        if not results:
            results.extend(self._sql_keyword_fallback(question))
        # 朝代文献浏览：仅匹配多字朝代名（「明代」「清代」…），
        # 跳过单字「明/元/唐/汉」等，避免在「说明」「公元」「荒唐」「汉子」等词中确定性误命中。
        for name in DYNASTY_TO_DB:
            if len(name) > 1 and name in question:
                res = self._search_dynasty(name)
                if res:
                    results.append(f"[SQL {name}文献] {res}")
                break
        return results

    def _sql_chain_search(self, question, parsed):
        """脉络类：按朝代浏览文献 + 标题层级搜索 + 文献正文"""
        results = []
        topic = parsed.get("topic", "")
        # 先直接用 topic 搜文献
        if topic:
            clean = self._clean_topic(topic)
            if clean:
                doc_res = sql_tools.search_document(clean)
                if "未找到" not in doc_res:
                    results.append(f"[SQL 文献详情] {doc_res}")
        # 用映射后的关键词做全文搜索
        keywords = self._extract_sql_keywords(question, topic)
        for kw in keywords[:3]:
            text_res = sql_tools.search_full_text(kw, limit=8)
            if "未找到" not in text_res:
                results.append(f"[SQL 全文搜索:{kw}] {text_res}")
                break  # 一个有效关键词就够
        # 朝代维度
        time_range = parsed.get("time_range", [])
        for t in time_range:
            res = self._search_dynasty(t)
            if res:
                results.append(f"[SQL {t}文献] {res}")
        # 标题层级浏览
        if topic:
            clean = self._clean_topic(topic)
            if clean:
                title_res = sql_tools.search_titles(clean, limit=10)
                if "未找到" not in title_res:
                    results.append(f"[SQL 标题搜索] {title_res}")
        if not results:
            results.extend(self._sql_keyword_fallback(question))
        return results

    def _sql_relation_search(self, question, parsed):
        """关系类：对涉及的实体分别查文献详情+正文"""
        results = []
        a = parsed.get("entity_a", "")
        b = parsed.get("entity_b", "")
        for name in [a, b]:
            if not name:
                continue
            doc_res = sql_tools.search_document(name)
            if "未找到" not in doc_res:
                results.append(f"[SQL 文献详情:{name}] {doc_res}")
            author_res = sql_tools.query_author_by_name(name)
            if "未找到" not in author_res:
                results.append(f"[SQL 作者查询:{name}] {author_res}")
        if not results:
            results.extend(self._sql_keyword_fallback(question))
        # 用关键词做全文搜索找交集
        keywords = self._extract_sql_keywords(question)
        for kw in keywords[:2]:
            text_res = sql_tools.search_full_text(kw, limit=5)
            if "未找到" not in text_res:
                results.append(f"[SQL 全文搜索:{kw}] {text_res}")
                break
        return results

    def _sql_method_search(self, question, parsed):
        """方法类：用映射后的古籍术语做全文搜索。

        关键改进：不再搜索"辑佚"（命中0条），而是用 CLASSICAL_SYNONYMS
        映射到古文献中实际出现的词（校勘、考证、训诂、辨伪等）。
        """
        results = []
        topic = parsed.get("topic", "")
        # 先尝试用 topic 直接搜文献
        if topic:
            clean = self._clean_topic(topic)
            if clean:
                doc_res = sql_tools.search_document(clean)
                if "未找到" not in doc_res:
                    results.append(f"[SQL 文献详情] {doc_res}")
        # 提取古籍中真实存在的搜索词
        keywords = self._extract_sql_keywords(question, topic)
        if keywords:
            # 用布尔模式提高精度
            kw_str = " ".join(keywords[:3])
            text_res = sql_tools.search_full_text(kw_str, limit=10, mode="BOOLEAN")
            if "未找到" in text_res:
                # 布尔模式太严格，降级为自然语言模式逐个尝试
                for kw in keywords[:3]:
                    text_res = sql_tools.search_full_text(kw, limit=8)
                    if "未找到" not in text_res:
                        break
            if "未找到" not in text_res:
                results.append(f"[SQL 全文搜索] {text_res}")
        # 也查标题层级
        if topic:
            clean = self._clean_topic(topic)
            if clean:
                title_res = sql_tools.search_titles(clean, limit=10)
                if "未找到" not in title_res:
                    results.append(f"[SQL 标题搜索] {title_res}")
        # 查文献元数据中是否有方法相关文献
        for cat in ["综合性类书", "专书性类书"]:
            if cat in question:
                doc_res = sql_tools.browse_documents(category=cat, limit=10)
                if "未找到" not in doc_res:
                    results.append(f"[SQL 类别浏览] {doc_res}")
        if not results:
            results.extend(self._sql_keyword_fallback(question))
        return results

    def _sql_compare_search(self, question, parsed):
        """比较类：查两个实体的文献详情+正文 + 同义词全文搜索"""
        results = []
        a = parsed.get("entity_a", "")
        b = parsed.get("entity_b", "")
        for name in [a, b]:
            if not name:
                continue
            doc_res = sql_tools.search_document(name)
            if "未找到" not in doc_res:
                results.append(f"[SQL 文献详情:{name}] {doc_res}")
            author_res = sql_tools.query_author_by_name(name)
            if "未找到" not in author_res:
                results.append(f"[SQL 作者查询:{name}] {author_res}")
        if not results:
            results.extend(self._sql_keyword_fallback(question))
        # 用关键词做全文搜索
        keywords = self._extract_sql_keywords(question)
        for kw in keywords[:2]:
            text_res = sql_tools.search_full_text(kw, limit=5)
            if "未找到" not in text_res:
                results.append(f"[SQL 全文搜索:{kw}] {text_res}")
                break
        return results

    # ── 关键词兜底检索 ──

    def _sql_keyword_fallback(self, question):
        """当实体链路未触发 SQL 检索时，从问句中提取关键词直接搜文献。
        解决"永乐"等部分书名无法触发 SQL 的问题。
        """
        results = []
        try:
            import jieba
            words = jieba.lcut(question)
        except ImportError:
            words = []

        # 词长 >= 2 且有意义的词（过滤纯数字、纯标点、单字）
        candidates = [w for w in words if len(w) >= 2 and not w.isdigit()
                      and w not in ['是', '的', '了', '吗', '呢', '什么', '哪', '怎么', '如何']]

        seen_titles = set()
        for w in candidates[:5]:  # 最多试 5 个候选词
            doc_res = sql_tools.search_document(w)
            if doc_res and "未找到" not in doc_res:
                # 避免重复
                first_line = doc_res.split('\n')[0] if doc_res else ''
                if first_line not in seen_titles:
                    seen_titles.add(first_line)
                    results.append(f"[SQL 关键词匹配:{w}] {doc_res}")

        return results

    # ── 结果融合 (5.3) ──

    # ── source_index 结构化辅助函数 ──

    @staticmethod
    def _extract_entity_name(text):
        """从图谱/向量工具结果中提取主实体名称。"""
        import re
        clean = re.sub(r'\s*\[.*?\]\s*', '', text)
        # 跳过常见的标题行（如"语义匹配结果（含属性）"）
        skip_patterns = ['语义匹配结果', '知识图谱检索结果', '搜索', '查询', '类型']
        # 实体格式: ChineseName（prop1；prop2...）
        for m in re.finditer(r'([一-鿿\w·]{2,20})[（(]', clean):
            name = m.group(1)
            if name not in skip_patterns:
                return name
        # 路径格式: Name → ...
        m = re.search(r'([一-鿿\w·]+)\s*→', clean)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _extract_doc_title(text):
        """从SQL工具结果中提取文献标题。"""
        import re
        m = re.search(r'《([一-鿿\w·▲╔═─└，；。、\s]+)》', text)
        if m and len(m.group(1)) <= 50:
            return m.group(1).strip()
        return None

    @staticmethod
    def _extract_author_name(text):
        """从SQL作者查询结果中提取作者姓名。"""
        import re
        # 去掉工具前缀（如 [search_author]），否则 re.match 锚定位置 0 会被前缀挡住，
        # 导致 author_name 提取失败 → 尾注退化为「数据库」、结构化卡片不生成。
        clean = re.sub(r'^\s*\[[a-z_]+(?::[^\]]*)?\]\s*', '', text)
        # 格式: "作者「姓名」..." 或 "姓名（机构）"
        m = re.search(r'作者[「「]([^」」]+)[」」]', clean)
        if m:
            return m.group(1)
        m = re.match(r'([一-鿿·]{2,4})[（(]', clean)
        if m:
            return m.group(1)
        return None

    def _merge(self, graph_results, vector_results, sql_results=None):
        """去重、排序、截断、格式化为 C 段文本。
        排序策略：知识图谱(kg_* + 语义检索，合并为一个来源) → SQL（每条一个来源）
        返回 (context_text, source_index)
        source_index 每个条目为 dict: {desc, source_type, tool_name, entity_name?, doc_title?}
        同时兼容旧版字符串格式，desc 字段供现有 tooltip 使用。
        """
        import re

        parts = []
        seen = set()

        # ── 知识图谱检索（kg_* 工具）+ 语义检索（vector_search）合并为【一个来源】──
        # 同一实体经 kg_explore_entity / kg_find_entities 等多次命中不应被拆成多个角标；
        # 语义检索本质上也属于知识图谱检索，一并并入该来源。
        kg_items = []
        for r in graph_results:
            if r and r not in seen:
                if "→" in r:
                    pri = 0            # 路径/关系
                elif "：" in r and "相似度" not in r:
                    pri = 1            # 实体属性
                else:
                    pri = 2            # 其他图结果
                kg_items.append((pri, r))
                seen.add(r)
        for r in vector_results:
            if r and r not in seen:
                if "向量相似度" in r:
                    pri = 1            # 含属性的语义匹配，与实体属性同级
                else:
                    pri = 3            # 纯名称兜底
                kg_items.append((pri, r))
                seen.add(r)
        kg_items.sort(key=lambda x: x[0])
        if kg_items:
            parts.append((0, "\n\n".join(t for _, t in kg_items)))

        # ── SQL 检索：每条结果单独一个来源 ──
        if sql_results:
            for r in sql_results:
                if r and r not in seen:
                    parts.append((1.5, r))
                    seen.add(r)

        # 按优先级排序
        parts.sort(key=lambda x: x[0])

        # 组装带编号的上下文和来源索引
        combined = ""
        source_index = {}
        idx = 0
        for pri, text in parts:
            idx += 1
            clean_text = text.strip()

            # ── 结构化元数据提取 ──
            source_type = "graph"
            tool_name = None
            tool_keyword = ""
            is_text_search = False
            is_browse = False
            browse_cat = None
            browse_dyn = None
            entity_name = None
            doc_title = None
            author_name = None
            label = "图谱"

            # 提取工具名（可选带检索词后缀，如 [search_full_text:校勘]）
            tool_m = re.match(r'\[([a-z_]+)(?::([^\]]*))?\]', clean_text)
            if tool_m:
                tool_name = tool_m.group(1)
                tool_keyword = tool_m.group(2) or ""

            # 按工具名分类
            if tool_name and tool_name.startswith("kg_"):
                source_type = "graph"
                label = "图谱"
                entity_name = self._extract_entity_name(clean_text)
            elif tool_name == "search_document":
                source_type = "sql"
                label = "数据库"
                doc_title = self._extract_doc_title(clean_text)
            elif tool_name == "browse_documents":
                source_type = "sql"
                label = "数据库"
                is_browse = True
                # 前缀 [browse_documents:类别,朝代] 内嵌了筛选条件，供复用检索阶段缓存
                if tool_keyword:
                    _bw = tool_keyword.split(",")
                    browse_cat = _bw[0] or None
                    browse_dyn = _bw[1] if len(_bw) > 1 and _bw[1] else None
            elif tool_name in ("search_full_text", "search_titles"):
                # 关键词/文段搜索，非文献实体：不设 doc_title，避免把片段里的《书》误当实体
                source_type = "sql"
                label = "数据库"
                is_text_search = True
            elif tool_name == "search_author":
                source_type = "sql"
                label = "数据库"
                author_name = self._extract_author_name(clean_text)
            elif tool_name == "vector_search":
                # 向量检索命中的是 Neo4j 的 Entity 节点，本质就是知识图谱实体。
                # 按 graph 类型下发，前端即可复用「实体属性卡片 + 力导向图」展示。
                source_type = "graph"
                label = "向量检索"
                # 向量结果可能也包含实体名
                entity_name = self._extract_entity_name(clean_text)
            else:
                # Fallback: 从内容判断
                if "[SQL" in clean_text or "[search_" in clean_text:
                    source_type = "sql"
                    label = "数据库"
                    # 文段搜索（全文/标题）优先识别，避免把片段里的《书》误当成文献实体
                    kw_m = re.search(r'(?:全文搜索|标题搜索):?([^\]\]]*)', clean_text)
                    if kw_m:
                        is_text_search = True
                        tool_keyword = kw_m.group(1).strip()
                    else:
                        doc_title = self._extract_doc_title(clean_text)
                        if not doc_title:
                            author_name = self._extract_author_name(clean_text)
                elif "相似度" in clean_text or "向量" in clean_text:
                    # 向量检索命中 = 知识图谱实体，按 graph 下发以复用图表面板展示
                    source_type = "graph"
                    label = "向量检索"
                    entity_name = self._extract_entity_name(clean_text)
                else:
                    source_type = "graph"
                    label = "图谱"
                    entity_name = self._extract_entity_name(clean_text)

            # 提取来源描述（前端 tooltip 展示用，截断加省略号）
            desc = clean_text.replace("\n", " ")
            if len(desc) > 200:
                desc = desc[:200] + "……"

            # 结构化条目
            entry = {
                "desc": f"{label}：{desc}",
                "source_type": source_type,
                "label": label,
            }
            if tool_name:
                entry["tool_name"] = tool_name
            if entity_name:
                entry["entity_name"] = entity_name
            if doc_title:
                entry["doc_title"] = doc_title
            if author_name:
                entry["author_name"] = author_name

            # 尾注标签（论文式参考文献列表）：按来源类别生成「知识图谱/数据库 —— 实体/相关文段」。
            ref_label = ""
            if source_type == "graph":
                ref_label = f"知识图谱 —— 实体 {entity_name}" if entity_name else "知识图谱"
            elif source_type == "sql":
                if is_text_search:
                    ref_label = "数据库 —— 相关文段" + (f" “{tool_keyword}”" if tool_keyword else "")
                elif is_browse:
                    ref_label = "数据库 —— 文献列表"
                elif doc_title:
                    ref_label = f"数据库 —— 实体 《{doc_title}》"
                elif author_name:
                    ref_label = f"数据库 —— 实体 {author_name}"
                else:
                    ref_label = "数据库"
            if ref_label:
                entry["ref_label"] = ref_label

            # SQL 来源：把检索阶段已生成的完整结果一并下发，
            # 前端点击角标时直接复用，无需再实时查 SQL（耗时）。
            if source_type == "sql":
                detail = re.sub(r'^\[[a-z_]+(?::[^\]]*)?\]\s*', '', clean_text)
                entry["detail_text"] = detail
                # 结构化数据（供前端渲染）：文献/作者/全文/标题
                # 优先复用，避免前端把整段纯文本倒出来。
                try:
                    if tool_name == "search_document" and doc_title:
                        entry["detail"] = sql_tools.get_document_structured(doc_title)
                    elif tool_name == "search_author" and author_name:
                        entry["detail"] = sql_tools.get_author_structured(author_name)
                    elif tool_name == "browse_documents":
                        entry["detail"] = sql_tools.get_documents_structured(category=browse_cat, dynasty=browse_dyn)
                    elif is_text_search and tool_keyword:
                        # 全文/标题搜索：有检索词时生成结构化卡片数据
                        if tool_name == "search_titles":
                            entry["detail"] = sql_tools.get_titles_structured(tool_keyword)
                        else:
                            entry["detail"] = sql_tools.get_full_text_structured(tool_keyword)
                except Exception:
                    pass  # 结构化失败则回退 detail_text

            source_index[str(idx)] = entry
            combined += f"[{idx}] {clean_text}\n\n"

        # 安全兜底：极端情况下超过 18000 字时做软截断。
        # 截断后必须同步裁剪 source_index，否则被裁掉的 [15] 等条目仍留在 source_index 里，
        # 模型照旧引用却对不上号（空引用）。
        if len(combined) > MAX_CHARS_REF * 3:
            combined = combined[:MAX_CHARS_REF * 3] + "\n（上下文已达上限，部分结果未展示）"
            kept_ids = set(re.findall(r'\[(\d+)\]', combined))
            source_index = {k: v for k, v in source_index.items() if k in kept_ids}

        return combined.strip(), source_index

    # ── 工具调用摘要 (评估用) ──

    @staticmethod
    def _build_tool_summary(tool_results, graph_results, sql_results, vector_results):
        """从工具调用结果中提取结构化摘要，供评估页面展示。
        返回 [{"tool": 工具名, "params": 关键参数, "status": 命中/未命中, "summary": 简短摘要}]
        """
        import re
        summary = []

        all_results = []
        if tool_results:
            for tr in tool_results:
                name = tr.get("name", "")
                result = tr.get("result", "")
                all_results.append((name, result))
        else:
            # Fallback 路径：从结果前缀提取
            for r in graph_results + sql_results + vector_results:
                if not r:
                    continue
                m = re.match(r'^\[(\w+)\]', r)
                if m:
                    all_results.append((m.group(1), r[len(m.group(0)):].strip()))

        for tool_name, result in all_results:
            entry = {"tool": tool_name, "params": "", "status": "命中", "summary": ""}

            # 提取参数和摘要
            if tool_name in ("kg_explore_entity", "kg_find_entities", "kg_explore_relation"):
                # 从结果第一行提取实体名
                first_line = result.split("\n")[0] if result else ""
                name_m = re.search(r'【(.+?)】', first_line)
                entry["params"] = f'实体: {name_m.group(1)}' if name_m else tool_name
                # 统计关系数
                rel_m = re.search(r'关系网络（(\d+)条）', result)
                if rel_m:
                    entry["summary"] = f'{rel_m.group(1)}条关系'
                elif "未在知识图谱中找到" in result:
                    entry["status"] = "未命中"
                    entry["summary"] = "未找到"
                else:
                    entry["summary"] = "已找到属性"

            elif tool_name == "kg_find_relation_between":
                entry["params"] = "查两实体间最短路径"
                paths = [l for l in result.split("\n") if "路径" in l and "跳" in l]
                entry["summary"] = f'{len(paths)}条路径' if paths else ("未找到" if "未找到" in result else "已找到")

            elif tool_name == "kg_get_entity_relations":
                entry["params"] = "查实体关系网络"
                entry["summary"] = "已找到" if "无关联关系" not in result else "无关联"

            elif tool_name == "kg_list_by_type":
                entry["params"] = "列出类型实体"
                cnt_m = re.search(r'共(\d+)个', result)
                entry["summary"] = f'{cnt_m.group(1)}个实体' if cnt_m else "已列出"

            elif tool_name == "vector_search":
                entry["params"] = "语义搜索"
                if "未找到" in result or "失败" in result:
                    entry["status"] = "未命中"
                    entry["summary"] = "无结果"
                else:
                    cnt = result.count("[向量相似度")
                    entry["summary"] = f'{cnt}个匹配' if cnt > 0 else "有结果"

            elif tool_name == "search_document":
                # 从结果中提取文献名
                title_m = re.search(r'《(.+?)》', result)
                entry["params"] = f'文献: {title_m.group(1)}' if title_m else "文献搜索"
                if "未找到" in result.split("\n")[0] if result else "":
                    entry["status"] = "未命中"
                    entry["summary"] = "未找到"
                else:
                    frag_m = re.search(r'全文片段：(\d+)条', result)
                    entry["summary"] = f'{frag_m.group(1)}条全文' if frag_m else "找到元数据"

            elif tool_name == "search_author":
                author_m = re.search(r'姓名包含「(.+?)」', result)
                entry["params"] = f'作者: {author_m.group(1)}' if author_m else "作者搜索"
                if "未找到" in result:
                    entry["status"] = "未命中"
                    entry["summary"] = "未找到"
                else:
                    entry["summary"] = "找到"

            elif tool_name == "search_full_text":
                entry["params"] = "全文关键词搜索"
                if "未找到" in result:
                    entry["status"] = "未命中"
                    entry["summary"] = "无匹配"
                else:
                    cnt = result.count("相关度:")
                    entry["summary"] = f'{cnt}条匹配'

            elif tool_name == "search_titles":
                entry["params"] = "标题关键词搜索"
                if "未找到" in result:
                    entry["status"] = "未命中"
                    entry["summary"] = "无匹配"
                else:
                    cnt = result.count("【")
                    entry["summary"] = f'{cnt}条匹配'

            elif tool_name == "browse_documents":
                entry["params"] = "浏览文献列表"
                if "未找到" in result:
                    entry["status"] = "未命中"
                    entry["summary"] = "无结果"
                else:
                    cnt = result.count("《")
                    entry["summary"] = f'{cnt}部文献'

            else:
                entry["params"] = tool_name
                entry["summary"] = "已执行" if "未找到" not in result else "未命中"

            summary.append(entry)

        return summary

    # ── RACE Prompt 构建 (5.4) ──

    def _build_race_prompt(self, question, context):
        """组装完整的 system + user messages"""
        user_content = f"【参考信息】\n{context}\n\n【用户问题】\n{question}"
        return {
            "system": RACE_SYSTEM,
            "user": user_content,
        }

    # ── 后处理 (5.5) ──

    _entity_names = None

    @classmethod
    def _load_entities(cls):
        if cls._entity_names is not None:
            return cls._entity_names
        import json
        path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "entity_dict.json")
        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)
        cls._entity_names = sorted([r["name"] for r in records], key=lambda x: -len(x))
        return cls._entity_names

    @classmethod
    def _clean_answer(cls, text, max_ref=None):
        """清理模型输出：只做安全的格式修正，不碰实体名内容。
        max_ref: 参考信息条目数（source_index 长度）。用于剔除超出范围的幻觉引用编号；
                 为 None 时不剔除（避免误删合法引用）。
        """
        import re
        # 0. 繁转简
        try:
            from opencc import OpenCC
            cc = OpenCC('t2s')
            text = cc.convert(text)
        except ImportError:
            pass
        # 1. 去 markdown 格式
        text = text.replace('**', '')
        text = text.replace('##', '')
        # 2. 去中文字间随机空格
        text = re.sub(r'([一-鿿])\s+([一-鿿])', r'\1\2', text)
        # 3. 修正"魏源"幻觉（参考信息中无"魏源"，纯属模型编造）
        text = re.sub(r'[（(]\s*魏源\s*[：:]\s*[""「」]?[^)）]*?[""」]?\s*[)）]', '', text)
        text = re.sub(r'[（(]\s*魏源\s*[：:]\s*[^)）]+[)）]', '', text)
        text = re.sub(r'[（(]\s*魏源\s*[)）]', '', text)
        text = re.sub(r'魏源\s*[：:]\s*[^\s，。；、\n）)]+', '', text)
        text = re.sub(r'[,，]\s*魏源', '', text)
        text = re.sub(r'魏源\s*[,，]', '', text)
        text = re.sub(r'[（(]\s*魏源\s*', '（', text)
        text = re.sub(r'魏源', '', text)
        # 4. 修正已知的特定幻觉模式（仅限频繁出现且验证过的）
        FIX_TITLES = {
            '玉函山房辑佚书书续编': '玉函山房辑佚书续编',
            '玉函山房辑佚书书补编': '玉函山房辑佚书补编',
            '玉函山房辑佚书书': '玉函山房辑佚书',
            '玉函山房辑书': '玉函山房辑佚书',
            '玉函山房辑佚续编': '玉函山房辑佚书续编',
            '玉函山房辑佚补编': '玉函山房辑佚书补编',
        }
        for wrong, correct in FIX_TITLES.items():
            if wrong in text:
                text = text.replace(wrong, correct)
        # 5. 修正残留的空括号
        text = re.sub(r'[（(]\s*[)）]', '', text)
        text = re.sub(r'[（(]\s*[,，;；:\s]*\s*[)）]', '', text)
        # 6. 过滤错误的编号标记：只允许 [数字] 格式，移除 [补][续][甲] 等非法标记
        text = re.sub(r'\[(?!\d+\])([^\[\]]+)\]', '', text)
        # 7. 剔除超出参考信息条目数的幻觉引用编号（[N+1]+ 均为编造）。
        #    上限来自实际 source_index 长度，而非硬编码 20，避免误删合法的 [21]+ 引用。
        import re as _re
        all_nums = _re.findall(r'\[(\d+)\]', text)
        for num in all_nums:
            if max_ref is not None and int(num) > max_ref:
                text = text.replace(f'[{num}]', '')
        return text.strip()

    @classmethod
    def postprocess(cls, answer, max_ref=None):
        if not answer or len(answer.strip()) < 5:
            return "抱歉，根据现有参考信息无法回答该问题。"
        answer = cls._clean_answer(answer, max_ref=max_ref)
        return answer