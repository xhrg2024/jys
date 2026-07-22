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
    · 不使用英文标点，全部使用中文全角标点"""

MAX_CHARS_REF = 600  # C 段参考信息最大字数（中文约 1 token/字）

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
# 问句中要剔除的疑问词
QUESTION_NOISE = ["是什么", "有哪些", "经历了", "哪几个", "怎么样", "如何",
                   "怎样", "为什么", "什么", "多少", "哪", "吗", "呢", "？", "?"]


class Planner:
    def __init__(self):
        self.parser = QuestionParser()

    # ── 关键词清洗 ──
    @staticmethod
    def _clean_topic(raw):
        """从正则提取的粗糙 topic 中剔除疑问词，得到干净的搜索词"""
        import re
        text = raw.strip()
        # 去掉常见疑问词碎片
        for noise in QUESTION_NOISE:
            text = text.replace(noise, "")
        # 去掉末尾虚词和数量词尾缀 如"辑佚的三"→"辑佚"
        text = re.sub(r'(的[一二三四五六七八九十]个?[种类]?)$', '', text)
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

    def plan(self, question, intent_override=None):
        """主入口：给定用户问题，返回完整 RACE Prompt 和检索摘要。"""
        # 感知
        parsed = self.parser.parse(question)
        intent = intent_override or parsed["intent"]
        entities = parsed["entities"]

        # 检索策略选择 (5.1)
        graph_results = []
        vector_results = []
        sql_results = []

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
        sql_detail = [r[:300] for r in sql_results if r]
        graph_detail = [r[:150] for r in graph_results if r]

        print(f"\n{'─'*50}")
        print(f"[Planner] 意图: {intent} | 问题: {question[:60]}")
        print(f"[工具调用] 图查询: {graph_count}条 | "
              f"SQL查询: {sql_count}条 | "
              f"向量检索: {vector_count}条")
        for r in sql_results:
            if r:
                print(f"  🗄️ {r[:200]}")
        for r in graph_results:
            if r:
                print(f"  🔗 {r[:150]}")
        print(f"{'─'*50}")

        # 结果融合 (5.3)
        context = self._merge(graph_results, vector_results, sql_results)

        # RACE Prompt 构建 (5.4)
        prompt = self._build_race_prompt(question, context)

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
                "entities_matched": [(e["name"], e["label"]) for e in entities[:5]],
                "question": question,
            }
        }

    # ── 多跳查询 (5.2) ──

    def _multi_hop(self, seed_entities, max_hops=3):
        """从种子实体出发，迭代查询多跳邻域。遇到环路或最大跳数停止。"""
        visited_ids = set()
        all_results = []
        frontier = [(e["id"], e["name"]) for e in seed_entities if e.get("id")]

        for hop in range(max_hops):
            if not frontier:
                break
            next_frontier = []
            for eid, ename in frontier:
                if eid in visited_ids:
                    continue
                visited_ids.add(eid)

                # 查实体属性
                entity_text = graph_tools.query_entity_by_name(ename)
                if entity_text and entity_text not in all_results:
                    all_results.append(entity_text)

                # 查一跳关系（自然语言，供 C 段显示）
                rel_text = graph_tools.query_entity_relations(eid)
                if rel_text and rel_text not in all_results:
                    all_results.append(rel_text)

                # 结构化查邻居（精确 ID，供下一跳），每实体最多扩展 3 个邻居
                neighbors = graph_tools.get_neighbor_struct(eid)
                for nname, nid in neighbors[:3]:
                    if nid not in visited_ids:
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
        # 也查主题实体
        topic = parsed.get("topic", "")
        if topic:
            results.append(graph_tools.query_entity_by_name(topic))
        return results

    def _method_search(self, parsed):
        results = []
        # 查所有 Method 类型实体
        results.append(graph_tools.query_by_label("Method"))
        topic = parsed.get("topic", "")
        if topic:
            results.append(graph_tools.query_entity_by_name(topic))
        return results

    def _compare_search(self, entities, parsed):
        results = []
        for e in entities[:2]:
            results.append(graph_tools.query_entity_by_name(e["name"]))
            results.append(graph_tools.query_entity_relations(e["id"]))
        a = parsed.get("entity_a")
        b = parsed.get("entity_b")
        if a and b:
            results.append(graph_tools.query_relation_between(a, b))
        return results

    # ── SQL 检索方法 ──

    def _sql_factual_search(self, question, parsed):
        """从问句中提取关键词，在 MySQL 中查文献/作者"""
        results = []
        primary = parsed.get("primary_entity", "")
        if primary:
            clean = self._clean_topic(primary)
            doc_res = sql_tools.query_document_by_title(clean, limit=5)
            if "未找到" not in doc_res:
                results.append(f"[SQL 文献查询] {doc_res}")
            author_res = sql_tools.query_author_by_name(clean)
            if "未找到" not in author_res:
                results.append(f"[SQL 作者查询] {author_res}")
        # 检测问句中的朝代关键词
        for name in DYNASTY_TO_DB:
            if name in question:
                res = self._search_dynasty(name)
                if res:
                    results.append(f"[SQL {name}文献] {res}")
                break  # 只匹配第一个朝代
        return results

    def _sql_chain_search(self, question, parsed):
        """按朝代查文献发展脉络"""
        results = []
        topic = parsed.get("topic", "")
        if topic:
            clean = self._clean_topic(topic)
            if clean:
                doc_res = sql_tools.query_document_by_title(clean, limit=5)
                if "未找到" not in doc_res:
                    results.append(f"[SQL 文献查询] {doc_res}")
        time_range = parsed.get("time_range", [])
        for t in time_range:
            res = self._search_dynasty(t)
            if res:
                results.append(f"[SQL {t}文献] {res}")
        return results

    def _sql_relation_search(self, question, parsed):
        """关系类问题：对涉及的实体分别查文献/作者/全文"""
        results = []
        entities_to_search = []
        a = parsed.get("entity_a", "")
        b = parsed.get("entity_b", "")
        if a:
            entities_to_search.append(a)
        if b:
            entities_to_search.append(b)
        for name in entities_to_search:
            doc_res = sql_tools.query_document_by_title(name, limit=3)
            if "未找到" not in doc_res:
                results.append(f"[SQL 文献查询:{name}] {doc_res}")
            author_res = sql_tools.query_author_by_name(name)
            if "未找到" not in author_res:
                results.append(f"[SQL 作者查询:{name}] {author_res}")
            text_res = sql_tools.query_full_text_by_keyword(name, limit=5)
            if "未找到" not in text_res:
                results.append(f"[SQL 全文搜索:{name}] {text_res}")
        return results

    def _sql_method_search(self, question, parsed):
        """方法类问题：全文搜索方法关键词"""
        results = []
        topic = parsed.get("topic", "")
        if topic:
            clean = self._clean_topic(topic)
            if clean:
                # 全文搜索
                text_res = sql_tools.query_full_text_by_keyword(clean, limit=10)
                if "未找到" not in text_res:
                    results.append(f"[SQL 全文搜索:{clean}] {text_res}")
                # 也查文献标题
                doc_res = sql_tools.query_document_by_title(clean, limit=5)
                if "未找到" not in doc_res:
                    results.append(f"[SQL 文献查询:{clean}] {doc_res}")
        # 额外：从问题中提取核心词做全文搜索（类书语境词）
        keywords = ["类书", "永乐", "辑佚", "校勘", "辨伪", "考证", "版本", "目录", "训诂"]
        for kw in keywords:
            if kw in question and kw != topic:
                text_res = sql_tools.query_full_text_by_keyword(kw, limit=5)
                if "未找到" not in text_res:
                    results.append(f"[SQL 全文搜索:{kw}] {text_res}")
        return results

    def _sql_compare_search(self, question, parsed):
        """比较类问题：对两个实体分别查文献/作者/全文"""
        results = []
        a = parsed.get("entity_a", "")
        b = parsed.get("entity_b", "")
        for name in [a, b]:
            if not name:
                continue
            doc_res = sql_tools.query_document_by_title(name, limit=3)
            if "未找到" not in doc_res:
                results.append(f"[SQL 文献查询:{name}] {doc_res}")
            author_res = sql_tools.query_author_by_name(name)
            if "未找到" not in author_res:
                results.append(f"[SQL 作者查询:{name}] {author_res}")
            text_res = sql_tools.query_full_text_by_keyword(name, limit=5)
            if "未找到" not in text_res:
                results.append(f"[SQL 全文搜索:{name}] {text_res}")
        return results

    # ── 结果融合 (5.3) ──

    def _merge(self, graph_results, vector_results, sql_results=None):
        """去重、排序、截断、格式化为 C 段文本。
        排序策略：直接关系/路径优先 → 实体属性 → SQL 结构化结果 → 邻域扩展 → 向量兜底
        """
        parts = []
        seen = set()
        for r in graph_results:
            if r and r not in seen:
                # 路径结果优先（含→的为路径/关系），实体属性其次
                if "→" in r:
                    priority = 0
                elif "：" in r and "相似度" not in r:
                    priority = 1
                else:
                    priority = 2
                parts.append((priority, r))
                seen.add(r)
        if sql_results:
            for r in sql_results:
                if r and r not in seen:
                    parts.append((1.5, r))
                    seen.add(r)
        for r in vector_results:
            if r and r not in seen:
                parts.append((3, r))
                seen.add(r)

        # 按优先级排序
        parts.sort(key=lambda x: x[0])

        # 格式化：优先结果完整保留，低优结果可能截断
        combined = ""
        for pri, text in parts:
            seg = text.strip() + "\n\n"
            if len(combined) + len(seg) > MAX_CHARS_REF * 3:
                if pri <= 1:
                    combined += seg[:MAX_CHARS_REF] + "\n...[截断]\n"
                break
            combined += seg

        return combined.strip()

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
    def _clean_answer(cls, text):
        """清理模型输出：只做安全的格式修正，不碰实体名内容。"""
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
        return text.strip()

    @classmethod
    def postprocess(cls, answer):
        if not answer or len(answer.strip()) < 5:
            return "抱歉，根据现有参考信息无法回答该问题。"
        answer = cls._clean_answer(answer)
        return answer