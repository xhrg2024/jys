"""
构建第二阶段 LoRA 训练数据（RACE 格式）。
来源：sft_alpaca + sharegpt_toolcall + data.json 自动增强。
用法：python src/model/build_race_data.py
"""
import json
import os
import random
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

# R+A+E 固定模板（与推理规划层完全一致）
RACE_SYSTEM = (
    "【R-角色】你是一位专精于辑佚学与中国古典文献学的AI助教。你的知识体系涵盖："
    "唐宋类书辑佚、清代辑佚学史、辑佚方法论（校勘、辨伪、考证）、辑佚流派与学术传承。\n\n"
    "【A-行动】请基于以下【参考信息】回答用户的问题。执行步骤："
    "1.理解问题意图 2.在参考信息中定位相关证据 3.组织为严谨的学术回答 "
    "4.标注每条信息的出处。如果参考信息不足以完整回答，明确说明哪些部分有据可查、哪些部分存疑。\n\n"
    "【E-期望】请遵循以下输出规范："
    "1.答案结构：先给出直接结论，再展开论据说明 "
    "2.来源标注：每条关键信息后以（来源：{实体名称/关系描述}）格式标注出处 "
    "3.学术用语：使用\"据记载\"、\"据考证\"、\"推测\"等分层级的确信度表述 "
    "4.不确定性处理：参考信息不足时，如实说明而非编造 "
    "5.语言风格：采用学术中文，简洁准确"
)

CHATML_SYSTEM = "<|im_start|>system\n{system}<|im_end|>"
CHATML_USER = "<|im_start|>user\n{user}<|im_end|>"
CHATML_ASSISTANT = "<|im_start|>assistant\n{output}<|im_end|>"


def load_json(name):
    with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def from_sft_alpaca():
    """从 sft_alpaca 提取 RACE 格式样本"""
    data = load_json("sft_alpaca(1).json")
    samples = []

    for item in data:
        question = item.get("instruction", "").strip()
        answer = item.get("output", "").strip()
        inp = item.get("input", "").strip()

        if not question or not answer:
            continue

        # C 段 = input 作为参考信息，没有则用空
        user_content = f"【参考信息】\n{inp}\n\n【用户问题】\n{question}" if inp else f"【参考信息】\n无额外参考信息。\n\n【用户问题】\n{question}"

        full = (
            CHATML_SYSTEM.format(system=RACE_SYSTEM) + "\n"
            + CHATML_USER.format(user=user_content) + "\n"
            + CHATML_ASSISTANT.format(output=answer)
        )
        samples.append(full)

    print(f"sft_alpaca → {len(samples)} 条")
    return samples


def from_sharegpt():
    """从 sharegpt_toolcall 平铺为 RACE 格式"""
    data = load_json("sharegpt_toolcall(1).json")
    samples = []

    for item in data:
        convs = item.get("conversations", [])
        question = ""
        answer = ""
        ref_parts = []

        for turn in convs:
            frm = turn.get("from", "")
            val = turn.get("value", "")
            if frm == "human":
                question = val.strip()
            elif frm == "function_call":
                try:
                    fc = json.loads(val) if isinstance(val, str) else val
                    ref_parts.append(f"[工具调用] {fc.get('name', '')}: {json.dumps(fc.get('arguments', {}), ensure_ascii=False)}")
                except:
                    pass
            elif frm == "observation":
                try:
                    obs = json.loads(val) if isinstance(val, str) else val
                    results = obs.get("results", [])
                    for r in results[:3]:
                        name = r.get("text", r.get("name", ""))
                        props = r.get("properties", {})
                        prop_str = "，".join(f"{k}: {v}" for k, v in props.items() if v)
                        ref_parts.append(f"{name}：{prop_str}")
                except:
                    pass
            elif frm == "gpt":
                answer = val.strip()

        if not question or not answer:
            continue

        ref_text = "\n".join(ref_parts[:10]) if ref_parts else "无额外参考信息。"
        user_content = f"【参考信息】\n{ref_text}\n\n【用户问题】\n{question}"

        full = (
            CHATML_SYSTEM.format(system=RACE_SYSTEM) + "\n"
            + CHATML_USER.format(user=user_content) + "\n"
            + CHATML_ASSISTANT.format(output=answer)
        )
        samples.append(full)

    print(f"sharegpt_toolcall → {len(samples)} 条")
    return samples


def from_data_json():
    """基于 data.json 生成增强问答对"""
    data = load_json("data.json")
    entities = data["entities"]
    relations = data["object_properties"]

    id_to_entity = {e["id"]: e for e in entities}
    rel_by_entity = {}
    for r in relations:
        src, tgt = r["source"], r["target"]
        if src in id_to_entity and tgt in id_to_entity:
            rel_by_entity.setdefault(src, []).append(r)

    templates_factual = [
        "请介绍一下《{name}》。",
        "《{name}》是什么？",
        "关于{name}，你知道哪些内容？",
        "{name}是谁？",
        "{name}属于哪个时期？",
    ]
    templates_relation = [
        "{a}和{b}有什么关系？",
        "{a}对{b}有什么影响？",
        "{a}与{b}之间存在什么关联？",
    ]

    samples = []

    for e in entities:
        name = e["text"]
        props = dict(e.get("properties", {}))
        prop_text = "；".join(f"{k}: {v}" for k, v in props.items() if v)

        # 事实问答
        q = random.choice(templates_factual).format(name=name)
        if prop_text:
            a = f"{name}的信息如下：{prop_text}。（来源：{name}实体记录）"
        else:
            a = f"{name}是辑佚史知识图谱中的一个{e.get('label', '')}实体。（来源：{name}实体记录）"

        ref = f"{name}：{prop_text}" if prop_text else f"{name}（{e.get('label', '')}）"
        user_content = f"【参考信息】\n{ref}\n\n【用户问题】\n{q}"

        full = (
            CHATML_SYSTEM.format(system=RACE_SYSTEM) + "\n"
            + CHATML_USER.format(user=user_content) + "\n"
            + CHATML_ASSISTANT.format(output=a)
        )
        samples.append(full)

        # 关系问答
        if e["id"] in rel_by_entity:
            for r in rel_by_entity[e["id"]][:2]:
                src_name = id_to_entity[r["source"]]["text"]
                tgt_name = id_to_entity[r["target"]]["text"]
                desc = r.get("description", "")
                q = random.choice(templates_relation).format(a=src_name, b=tgt_name)
                a = f"{src_name}与{tgt_name}之间存在{r['type']}关系。{desc}（来源：关系{r['type']}的定义记录）"
                ref = f"{src_name} → {r['type']} → {tgt_name}：{desc}"
                user_content = f"【参考信息】\n{ref}\n\n【用户问题】\n{q}"

                full = (
                    CHATML_SYSTEM.format(system=RACE_SYSTEM) + "\n"
                    + CHATML_USER.format(user=user_content) + "\n"
                    + CHATML_ASSISTANT.format(output=a)
                )
                samples.append(full)

    # 限制增强数量
    random.shuffle(samples)
    samples = samples[:600]

    print(f"data.json 增强 → {len(samples)} 条")
    return samples


def main():
    sft = from_sft_alpaca()
    sgpt = from_sharegpt()
    aug = from_data_json()

    # 加载 generate_training_set.py 生成的高质量数据
    draft_path = os.path.join(DATA_DIR, "race_training_draft.json")
    if os.path.exists(draft_path):
        with open(draft_path, "r", encoding="utf-8") as f:
            draft_data = json.load(f)
        draft_samples = []
        for item in draft_data:
            user_content = f"【参考信息】\n{item['reference']}\n\n【用户问题】\n{item['question']}"
            full = (
                CHATML_SYSTEM.format(system=RACE_SYSTEM) + "\n"
                + CHATML_USER.format(user=user_content) + "\n"
                + CHATML_ASSISTANT.format(output=item['answer'])
            )
            draft_samples.append(full)
        print(f"race_training_draft → {len(draft_samples)} 条")
    else:
        draft_samples = []

    samples = sft + sgpt + aug + draft_samples
    random.shuffle(samples)
    print(f"\nsft_alpaca: {len(sft)}, sharegpt: {len(sgpt)}, 增强: {len(aug)}, 高质量: {len(draft_samples)}")
    print(f"总计: {len(samples)} 条")

    n = len(samples)
    train = samples[:int(n * 0.8)]
    val = samples[int(n * 0.8):int(n * 0.9)]
    test = samples[int(n * 0.9):]

    for name, data in [("train", train), ("val", val), ("test", test)]:
        path = os.path.join(DATA_DIR, f"race_{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"race_{name}: {len(data)} 条 → {path}")


if __name__ == "__main__":
    main()
