"""
将 race_training_draft.json 转换为 ChatML 训练格式。
用法：python src/model/convert_race_data.py
"""
import json, os, random

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


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
    "5.语言风格：采用学术中文，简洁准确。全文须使用简体中文"
)


def main():
    with open(os.path.join(DATA_DIR, "race_training_draft.json"), "r", encoding="utf-8") as f:
        samples = json.load(f)

    formatted = []
    for s in samples:
        ref = s.get("reference", "")
        q = s.get("question", "")
        a = s.get("answer", "")
        user_content = f"【参考信息】\n{ref}\n\n【用户问题】\n{q}"
        chat = (
            f"<|im_start|>system\n{RACE_SYSTEM}<|im_end|>\n"
            f"<|im_start|>user\n{user_content}<|im_end|>\n"
            f"<|im_start|>assistant\n{a}<|im_end|>"
        )
        formatted.append(chat)

    random.shuffle(formatted)
    n = len(formatted)
    train = formatted[:int(n * 0.8)]
    val = formatted[int(n * 0.8):int(n * 0.9)]
    test = formatted[int(n * 0.9):]

    for name, data in [("train", train), ("val", val), ("test", test)]:
        path = os.path.join(DATA_DIR, f"race_{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"race_{name}: {len(data)} 条")

    print(f"\n总计: {len(formatted)} 条")


if __name__ == "__main__":
    main()
