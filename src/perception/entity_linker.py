"""
3.1 实体链接：从用户问句中识别知识图谱中的实体。
策略：jieba 分词 + 实体词典模糊匹配 + 向量语义兜底。
"""
import json
import os
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


class EntityLinker:
    def __init__(self):
        self.entities = {}   # id → {name, label}
        self.name_to_ids = {}  # name → [id]
        self._load_dict()

    def _load_dict(self):
        path = os.path.join(DATA_DIR, "entity_dict.json")
        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)
        for r in records:
            self.entities[r["id"]] = {"name": r["name"], "label": r["label"]}
            self.name_to_ids.setdefault(r["name"], []).append(r["id"])

    def link_exact(self, question):
        """精确匹配：实体名直接出现在问句中"""
        hits = []
        for name, ids in self.name_to_ids.items():
            if name in question:
                for eid in ids:
                    hits.append({"id": eid, "name": name,
                                 "label": self.entities[eid]["label"],
                                 "method": "exact", "confidence": 0.99})
        return hits

    def link_blurry(self, question):
        """模糊匹配：jieba 分词后编辑距离 <= 2"""
        try:
            import Levenshtein
            import jieba
        except ImportError:
            return []

        words = set(jieba.lcut(question))
        hits = []
        for w in words:
            if len(w) < 2 or len(w) > 20:
                continue
            for name, ids in self.name_to_ids.items():
                if abs(len(w) - len(name)) > 2:
                    continue
                dist = Levenshtein.distance(w, name)
                if dist <= 2 and name not in question:
                    for eid in ids:
                        hits.append({
                            "id": eid, "name": name,
                            "label": self.entities[eid]["label"],
                            "method": "blurry",
                            "confidence": max(0, 0.8 - dist * 0.2),
                            "matched_word": w,
                        })
        return hits

    def link(self, question):
        """主入口：返回匹配到的实体列表，按置信度降序"""
        hits = self.link_exact(question)
        # 去重
        seen = {h["id"] for h in hits}
        for h in self.link_blurry(question):
            if h["id"] not in seen:
                hits.append(h)
                seen.add(h["id"])
        hits.sort(key=lambda x: x["confidence"], reverse=True)
        return hits
