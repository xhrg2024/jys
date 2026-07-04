"""
构造意图分类训练数据。
来源：sft_alpaca 问题 + data.json 实体模板生成 + 手工规则标注。
输出格式：ChatML，assistant 只输出意图标签。
用法：python src/model/build_intent_data.py
"""
import json, os, random

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
INTENTS = ["FACTUAL", "RELATION", "CHAIN", "METHOD", "COMPARE"]

# ── 模板：每种意图的变体句式 ──
FACTUAL_T = [
    "《{name}》是什么？", "{name}是谁？", "请介绍一下{name}。",
    "{name}有多少卷？", "{name}属于哪个时期？", "{name}的作者是谁？",
    "关于{name}，你知道哪些内容？", "{name}是哪个朝代的人？",
    "{name}的主要贡献是什么？", "什么是{name}？",
]
RELATION_T = [
    "{a}和{b}有什么关系？", "{a}对{b}有什么影响？",
    "{a}与{b}之间存在什么关联？", "{a}和{b}之间有什么联系？",
    "{a}是否影响了{b}？", "请说明{a}与{b}的关系。",
]
CHAIN_T = [
    "{name}经历了哪几个阶段？", "{name}的发展历程是怎样的？",
    "{name}的演变脉络如何？", "请梳理{name}的发展脉络。",
    "{name}的学术源流是怎样的？", "{name}经历了怎样的流变？",
]
METHOD_T = [
    "辑佚的方法有哪些？", "如何进行辑佚？", "辑佚的步骤是什么？",
    "{name}的方法论是什么？", "辑佚的三大原则是什么？",
    "进行辑佚工作需要注意什么？", "辑佚的基本流程是什么？",
]
COMPARE_T = [
    "{a}和{b}有什么不同？", "{a}与{b}的区别是什么？",
    "请比较{a}和{b}。", "{a}和{b}哪个更好？",
    "{a}与{b}有何差异？", "{a}和{b}的异同点是什么？",
]


def load_json(name):
    with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def from_sft():
    """从 sft_alpaca 提取问题，用规则标注意图"""
    data = load_json("sft_alpaca(1).json")
    samples = []

    rules = [
        (["区别", "对比", "比较", "不同", "异同", "差异"], "COMPARE"),
        (["关系", "关联", "联系", "之间", "相关"], "RELATION"),
        (["发展", "历程", "演变", "脉络", "阶段", "源流", "流变"], "CHAIN"),
        (["方法", "原则", "如何", "步骤", "程序", "怎么做", "怎样"], "METHOD"),
        (["谁", "什么", "多少", "哪", "是什么", "何人", "何时", "有哪些"], "FACTUAL"),
    ]

    for item in data:
        q = item.get("instruction", "").strip()
        if not q:
            continue
        intent = "FACTUAL"
        for keywords, label in rules:
            if any(kw in q for kw in keywords):
                intent = label
                break
        samples.append((q, intent))

    print(f"sft_alpaca → {len(samples)} 条")
    return samples


def from_entities():
    """基于 data.json 实体生成意图分类样本"""
    data = load_json("data.json")
    entities = data["entities"]
    rels = data["object_properties"]

    id_to_e = {e["id"]: e for e in entities}
    samples = []

    # 事实类：每个实体生成 1-2 条
    for e in entities:
        name = e["text"]
        for _ in range(min(2, len(FACTUAL_T))):
            q = random.choice(FACTUAL_T).format(name=name)
            samples.append((q, "FACTUAL"))

    # 关系类：从真实关系中取
    valid_rels = [r for r in rels if r["source"] in id_to_e and r["target"] in id_to_e]
    seen_pairs = set()
    for r in random.sample(valid_rels, min(60, len(valid_rels))):
        a = id_to_e[r["source"]]["text"]
        b = id_to_e[r["target"]]["text"]
        pair = (a, b)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        q = random.choice(RELATION_T).format(a=a, b=b)
        samples.append((q, "RELATION"))

    # 脉络类
    time_names = [e["text"] for e in entities if e["label"] == "Time"]
    topic_names = [e["text"] for e in entities if e["label"] in ("Method", "Academic")]
    for name in random.sample(time_names + topic_names, min(30, len(time_names) + len(topic_names))):
        q = random.choice(CHAIN_T).format(name=name)
        samples.append((q, "CHAIN"))

    # 方法类
    for _ in range(30):
        q = random.choice(METHOD_T).format(name="")
        samples.append((q, "METHOD"))

    # 比较类
    comp_entities = [e for e in entities if e["label"] in ("Compilation", "Person", "Scholar")]
    seen_pairs.clear()
    for _ in range(40):
        pair = random.sample(comp_entities, min(2, len(comp_entities)))
        if len(pair) < 2:
            continue
        a, b = pair[0]["text"], pair[1]["text"]
        if (a, b) in seen_pairs or a == b:
            continue
        seen_pairs.add((a, b))
        q = random.choice(COMPARE_T).format(a=a, b=b)
        samples.append((q, "COMPARE"))

    print(f"data.json 生成 → {len(samples)} 条")
    return samples


def format_sample(question, intent):
    return (
        f"<|im_start|>system\n判断用户问题的意图类型。只输出 FACTUAL, RELATION, CHAIN, METHOD, COMPARE 之一，不要输出任何其他内容。<|im_end|>\n"
        f"<|im_start|>user\n{question}<|im_end|>\n"
        f"<|im_start|>assistant\n{intent}<|im_end|>"
    )


def main():
    samples = from_sft() + from_entities()
    random.shuffle(samples)

    n = len(samples)
    train = samples[:int(n * 0.8)]
    val = samples[int(n * 0.8):int(n * 0.9)]
    test = samples[int(n * 0.9):]

    for name, data in [("train", train), ("val", val), ("test", test)]:
        formatted = [format_sample(q, i) for q, i in data]
        path = os.path.join(DATA_DIR, f"intent_{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(formatted, f, ensure_ascii=False, indent=2)
        print(f"intent_{name}: {len(formatted)} 条 → {path}")

    print(f"\n总计: {len(samples)} 条")


if __name__ == "__main__":
    main()
