"""
3.2 意图识别：判断问句类型，决定检索策略。
规则法：关键词匹配 → {FACTUAL, RELATION, CHAIN, METHOD, COMPARE}
"""
import re


INTENT_RULES = {
    "COMPARE": ["区别", "对比", "比较", "谁更", "异同", "不同", "差异", "相较", "哪个更"],
    "RELATION": ["关系", "关联", "联系", "与.*什么", "跟.*什么", "之间", "相关"],
    "CHAIN": ["发展", "历程", "演变", "脉络", "阶段", "源流", "流变", "过程", "史上", "经历了"],
    "METHOD": ["方法", "原则", "如何", "步骤", "程序", "怎么做", "怎样辑", "怎么辑", "用什么方法", "手段"],
    "FACTUAL": ["谁", "什么", "多少", "哪", "是什么", "何人", "何时", "何种", "有哪些", "叫什么"],
}


class IntentRecognizer:
    def classify(self, question):
        """返回意图类型和匹配关键词"""
        for intent, keywords in INTENT_RULES.items():
            for kw in keywords:
                if re.search(kw, question):
                    return intent
        return "FACTUAL"

    def should_parallel(self, intent):
        """是否图检索和向量检索并行"""
        return intent in ("CHAIN", "METHOD", "COMPARE")

    def graph_first(self, intent):
        """是否图检索优先"""
        return intent in ("FACTUAL", "RELATION")
