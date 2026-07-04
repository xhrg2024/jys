"""
从 data.json 构造三元组抽取训练数据（扩充版）。
每个实体构造一条样本：自然语言段落 → 三元组列表。
三元组来源：properties（属性三元组） + object_properties（关系三元组）。
用法：python src/memory/build_extraction_data.py
"""
import json
import os
import random

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def load_data():
    with open(os.path.join(DATA_DIR, "data.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def props_to_text(name, label, props):
    """将实体属性转换为自然语言段落"""
    label_cn = {
        "Compilation": "辑本", "Person": "辑佚者", "Scholar": "辑佚者",
        "Time": "历史时期", "Method": "研究方法", "Academic": "学术流派"
    }.get(label, label)

    sentences = [f"《{name}》是一部{label_cn}。" if label == "Compilation" else f"{name}是一位{label_cn}。" if label in ("Person", "Scholar") else f"{name}是一个{label_cn}。"]

    for k, v in props.items():
        if not v:
            continue
        # 英文 key 转中文描述
        key_map = {
            "compilationTitle": "书名", "contentType": "内容类型", "compiler": "编纂者",
            "periodName": "时期名称", "compilationFeature": "辑佚特征",
            "academicAtmosphere": "学术风气",
            "methodName": "方法名称", "methodDescription": "方法描述",
            "methodEvaluation": "方法评价",
            "schoolName": "学派名称", "methodCharacteristic": "方法特点", "origin": "起源",
            "editionInfo": "版本信息", "compilationStyle": "编纂体例",
            "annotationHistory": "注疏史", "volumeCount": "卷数",
            "description": "描述", "compilationFeature": "辑佚特征",
        }
        key_cn = key_map.get(k, k)
        sentences.append(f"{key_cn}为{v}。")

    return "".join(sentences)


def props_to_triplets(name, props):
    """从实体属性生成三元组 (实体名, 属性名, 属性值)"""
    triplets = []
    for k, v in props.items():
        if not v:
            continue
        key_cn = {
            "compilationTitle": "书名", "contentType": "内容类型", "compiler": "编纂者",
            "periodName": "时期名称", "compilationFeature": "辑佚特征",
            "academicAtmosphere": "学术风气",
            "methodName": "方法名称", "methodDescription": "方法描述",
            "methodEvaluation": "方法评价",
            "schoolName": "学派名称", "methodCharacteristic": "方法特点", "origin": "起源",
            "editionInfo": "版本信息", "compilationStyle": "编纂体例",
            "annotationHistory": "注疏史", "volumeCount": "卷数",
            "description": "描述",
        }.get(k, k)
        triplets.append(f"({name}, {key_cn}, {v})")
    return triplets


def build_samples():
    data = load_data()
    entities = data["entities"]
    relations = data["object_properties"]

    id_to_entity = {e["id"]: e for e in entities}

    # 建立关系索引
    rel_by_entity = {}
    for r in relations:
        src, tgt = r["source"], r["target"]
        if src in id_to_entity and tgt in id_to_entity:
            rel_by_entity.setdefault(src, []).append(r)
            rel_by_entity.setdefault(tgt, []).append(r)

    # 几种 instruction 模板，增加多样性
    instructions = [
        "请从以下辑佚史文献描述中，抽取实体与关系三元组。三元组格式：(实体A, 关系/属性, 实体B/属性值)\n\n{text}",
        "阅读以下关于辑佚学的文本，提取其中蕴含的实体-关系三元组。格式：(实体, 关系, 客体)\n\n{text}",
        "你是一个辑佚学知识抽取系统。请从以下文本中识别出所有的实体关系三元组。\n\n{text}",
    ]

    samples = []
    for e in entities:
        props = dict(e.get("properties", {}))
        text = props_to_text(e["text"], e["label"], props)

        triplets = props_to_triplets(e["text"], props)

        # 加入关系三元组
        if e["id"] in rel_by_entity:
            for r in rel_by_entity[e["id"]]:
                src_name = id_to_entity[r["source"]]["text"]
                tgt_name = id_to_entity[r["target"]]["text"]
                rel_desc = r.get("description", "")
                triplets.append(f"({src_name}, {r['type']}, {tgt_name})")

        if not triplets:
            continue

        inst = random.choice(instructions).format(text=text)
        output = "\n".join(triplets)
        samples.append({"instruction": inst, "output": output})

    random.shuffle(samples)
    samples = samples[:500]

    n = len(samples)
    train = samples[:int(n * 0.8)]
    val = samples[int(n * 0.8):int(n * 0.9)]
    test = samples[int(n * 0.9):]

    for name, data in [("train", train), ("val", val), ("test", test)]:
        path = os.path.join(DATA_DIR, f"extraction_{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"{name}: {len(data)} 条 → {path}")

    print(f"\n共生成 {len(samples)} 条训练数据")


if __name__ == "__main__":
    build_samples()
