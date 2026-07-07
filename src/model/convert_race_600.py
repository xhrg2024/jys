import json
import os
import random

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
IM_S = chr(120001)
IM_E = chr(120002)
NL = chr(10)


def main():
    path = os.path.join(DATA_DIR, "\u95ee\u7b54\u96c6_RACE_600.json")
    with open(path, "r", encoding="utf-8") as f:
        race_data = json.load(f)

    print("读取到 " + str(len(race_data)) + " 条问答对")

    chatml_samples = []
    for item in race_data:
        messages = item.get("messages", [])
        if len(messages) < 2:
            continue
        parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            token = IM_S + role + NL + content + IM_E
            parts.append(token)
        chat_text = NL.join(parts) + NL + IM_S + "assistant"
        chatml_samples.append(chat_text)

    random.seed(42)
    random.shuffle(chatml_samples)
    n = len(chatml_samples)
    train = chatml_samples[:int(n * 0.8)]
    val = chatml_samples[int(n * 0.8):int(n * 0.9)]
    test = chatml_samples[int(n * 0.9):]

    for name, data in [("train", train), ("val", val), ("test", test)]:
        out_path = os.path.join(DATA_DIR, "race600_" + name + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("race600_" + name + ": " + str(len(data)) + " 条 -> " + out_path)

    print("总计: " + str(len(chatml_samples)) + " 条")
    print("下一步: python src/model/train_race_lora.py")


if __name__ == "__main__":
    main()
