"""
规划层（5.1-5.5）：检索策略选择、多跳查询、结果融合、RACE Prompt 构建、后处理。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from perception.question_parser import QuestionParser
from tools import graph_tools, vector_tools

# ── RACE 固定模板（与训练数据一致）──
RACE_SYSTEM = """【R-角色】你是一位专精于辑佚学与中国古典文献学的AI助教。你的知识体系涵盖：唐宋类书辑佚、清代辑佚学史、辑佚方法论（校勘、辨伪、考证）、辑佚流派与学术传承。

【A-行动】请基于以下【参考信息】回答用户的问题。执行步骤：1.理解问题意图 2.在参考信息中定位相关证据 3.组织为严谨的学术回答 4.标注每条信息的出处。如果参考信息不足以完整回答，明确说明哪些部分有据可查、哪些部分存疑。

【E-期望】请遵循以下输出规范：
1.答案结构：先给出直接结论，再展开论据说明
2.来源标注：每条关键信息后以（来源：{实体名称}）格式标注出处
3.学术用语：使用"据记载"、"据考证"、"推测"等分层级的确信度表述
4.不确定性处理：参考信息不足时，如实说明而非编造
5.语言风格：采用学术中文，简洁准确。全文须使用简体中文。
6.【严格禁止】必须且只能使用参考信息中出现的实体名称，绝对禁止编造、改写、增减任何字。例如参考信息写"马国翰"，就必须写"马国翰"，不能写"马国磐"、"马国槃"等任何变体。
7.数字信息（卷数、年代、数量等）必须与参考信息严格一致，不得编造或修改。"""

MAX_CHARS_REF = 600  # C 段参考信息最大字数（中文约 1 token/字）


class Planner:
    def __init__(self):
        self.parser = QuestionParser()

    def plan(self, question, intent_override=None):
        """主入口：给定用户问题，返回完整 RACE Prompt 和检索摘要。"""
        # 感知
        parsed = self.parser.parse(question)
        intent = intent_override or parsed["intent"]
        entities = parsed["entities"]

        # 检索策略选择 (5.1)
        graph_results = []
        vector_results = []

        if intent == "FACTUAL":
            graph_results = self._factual_search(entities, parsed["parsed"])
            if not graph_results:
                vector_results = [vector_tools.vector_search(question, k=5)]

        elif intent == "RELATION":
            graph_results = self._relation_search(entities, parsed["parsed"])
            if not graph_results:
                vector_results = [vector_tools.vector_search(question, k=5)]

        elif intent == "CHAIN":
            graph_results = self._chain_search(entities, parsed["parsed"])
            vector_results = [vector_tools.vector_search(question, k=5)]

        elif intent == "METHOD":
            graph_results = self._method_search(parsed["parsed"])
            vector_results = [vector_tools.vector_search(question, k=5)]

        elif intent == "COMPARE":
            graph_results = self._compare_search(entities, parsed["parsed"])
            vector_results = [vector_tools.vector_search(question, k=5)]

        # 结果融合 (5.3)
        context = self._merge(graph_results, vector_results)

        # RACE Prompt 构建 (5.4)
        prompt = self._build_race_prompt(question, context)

        return {
            "parsed": parsed,
            "context": context,
            "prompt": prompt,
            "intent": intent,
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

    # ── 结果融合 (5.3) ──

    def _merge(self, graph_results, vector_results):
        """去重、排序、截断、格式化为 C 段文本。
        排序策略：直接关系/路径优先 → 实体属性 → 邻域扩展 → 向量兜底
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
        """清理 Qwen 7B 常见输出问题"""
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
        # 3. 修正"魏源"幻觉 - 移除所有包含魏源的来源标注
        # 匹配各种格式: (魏源："xxx") (魏源: "xxx") （魏源："xxx"） (魏源:"xxx")
        text = re.sub(r'[（(]\s*魏源\s*[：:]\s*[""「」]?[^)）]*?[""」]?\s*[)）]', '', text)
        # 匹配没有引号的格式: (魏源：xxx)
        text = re.sub(r'[（(]\s*魏源\s*[：:]\s*[^)）]+[)）]', '', text)
        # 匹配只有魏源的格式
        text = re.sub(r'[（(]\s*魏源\s*[)）]', '', text)
        # 4. 修被空格打断的实体名
        entities = cls._load_entities()
        for name in entities:
            if len(name) < 3 or name in text:
                continue
            for i in range(1, len(name)):
                bad = name[:i] + ' ' + name[i:]
                if bad in text:
                    text = text.replace(bad, name)
        # 4. 修正幻觉的实体名（编辑距离≤1的替换为标准名）
        try:
            import Levenshtein
            # 提取文本中所有2-6字的中文词
            candidates = set(re.findall(r'[\u4e00-\u9fff]{2,6}', text))
            for cand in candidates:
                if cand in entities:
                    continue
                for name in entities:
                    if len(name) >= 2 and Levenshtein.distance(cand, name) <= 1:
                        text = text.replace(cand, name)
                        break
        except ImportError:
            pass
        # 5. 去中文文本前的英文前缀
        text = re.sub(r'\b[A-Za-z]+([一-鿿]{2,})', r'\1', text)
        return text.strip()

    @classmethod
    def postprocess(cls, answer):
        if not answer or len(answer.strip()) < 5:
            return "抱歉，根据现有参考信息无法回答该问题。"
        answer = cls._clean_answer(answer)
        has_source = "来源" in answer or "据记" in answer or "据考" in answer
        if not has_source:
            answer += "\n（提示：以上信息来源于知识图谱检索结果，具体出处未能标注，建议核实。）"
        return answer
