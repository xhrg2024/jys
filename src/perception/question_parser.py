"""
3.3 问题解析：提取检索所需的结构化要素。
输出：{"intent": ..., "entities": [...], "parsed": {...}}
"""
import re

from .intent_recognizer import IntentRecognizer
from .entity_linker import EntityLinker


class QuestionParser:
    def __init__(self):
        self.recognizer = IntentRecognizer()
        self.linker = EntityLinker()

    def parse(self, question):
        intent = self.recognizer.classify(question)
        entities = self.linker.link(question)
        parsed = self._extract(intent, question, entities)
        return {
            "question": question,
            "intent": intent,
            "entities": entities,
            "parsed": parsed,
        }

    def _extract(self, intent, question, entities):
        result = {}

        if intent == "RELATION":
            # 尝试提取 A 和 B：X和Y的关系
            m = re.search(r"(.+?)(?:和|与|跟)(.+?)(?:的|之间)?(?:关系|有什么|有何|关联|联系|什么)", question)
            if m:
                result["entity_a"] = m.group(1).strip()
                result["entity_b"] = m.group(2).strip()
            elif len(entities) >= 2:
                result["entity_a"] = entities[0]["name"]
                result["entity_b"] = entities[1]["name"]

        elif intent == "CHAIN":
            m = re.search(r"(\S+?)的?(?:发展|历程|演变|脉络|阶段|源流)", question)
            if m:
                raw_topic = m.group(1).strip()
                raw_topic = re.sub(r'的[一二三四五六七八九十两几][种类个项条]?$', '', raw_topic)
                raw_topic = raw_topic.rstrip("的之了着过")
                result["topic"] = raw_topic
            # 尝试抽取时间范围
            time_m = re.findall(r"(清代|明代|宋代|元代|唐代|汉代|先秦|民国|清初|乾嘉|南宋|北宋|晚清)", question)
            if time_m:
                result["time_range"] = time_m

        elif intent == "COMPARE":
            m = re.search(r"(.+?)(?:和|与|跟)(.+?)(?:的)?(?:区别|对比|比较|谁更|异同|区别)", question)
            if m:
                result["entity_a"] = m.group(1).strip()
                result["entity_b"] = m.group(2).strip()
            elif len(entities) >= 2:
                result["entity_a"] = entities[0]["name"]
                result["entity_b"] = entities[1]["name"]

        elif intent == "METHOD":
            m = re.search(r"(\S+?)的?(?:方法|原则|步骤|程序)|如何(.*)|怎样(.*)", question)
            if m:
                raw_topic = next((g.strip() for g in m.groups() if g), "")
                # 基础清洗：去掉末尾的数量修饰残余（如"辑佚的三"→"辑佚"）
                raw_topic = re.sub(r'的[一二三四五六七八九十两几][种类个项条]?$', '', raw_topic)
                raw_topic = raw_topic.rstrip("的之了着过")
                result["topic"] = raw_topic

        elif intent == "FACTUAL":
            if entities:
                result["primary_entity"] = entities[0]["name"]

        return result
