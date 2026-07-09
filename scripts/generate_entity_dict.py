"""
从 data.json 直接生成 entity_dict.json（无需 Neo4j 连接）。
用法：python scripts/generate_entity_dict.py
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def main():
    # 读取 data.json
    data_path = os.path.join(DATA_DIR, "data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entities = data["entities"]

    # 构建实体词典
    records = []
    for e in entities:
        records.append({
            "name": e["text"],
            "id": e["id"],
            "label": e["label"]
        })

    # 写入 entity_dict.json
    output_path = os.path.join(DATA_DIR, "entity_dict.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"实体词典已生成，共 {len(records)} 条 → {output_path}")


if __name__ == "__main__":
    main()