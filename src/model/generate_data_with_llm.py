"""
用大模型批量生成高质量 RACE 训练数据。

用法：
  export OPENAI_API_KEY="your-api-key"
  export OPENAI_BASE_URL="https://api.deepseek.com"
  export LLM_MODEL="deepseek-chat"
  python src/model/generate_data_with_llm.py
"""
import json
import os
import time
import random

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def load_kg():
    with open(os.path.join(DATA_DIR, "data.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def entity_summary(e):
    props = dict(e.get("properties", {}))
    parts = []
    for k, v in props.items():
        if v and k != "embedding":
            parts.append(f"{k}: {v}")
    name = e["text"]
    return f"{name}（{'；'.join(parts)}）" if parts else name


def call_llm(client, model, prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=800,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"  retry {attempt+1}: {e}")
            time.sleep(2 ** attempt)
    return None


def build_prompt(ref, question, entity_name, intent_hint=""):
    system = (
        "你是一位辑佚学与中国古典文献学专家。请基于【参考信息】回答【用户问题】。\n"
        "要求：\n"
        "1. 答案必须是自然流畅的学术中文，不要复制参考信息的原始格式\n"
        "2. 每条关键信息后标注（来源：实体名称）\n"
        "3. 使用'据记载'、'据考证'等学术用语\n"
        "4. 全文使用简体中文，实体名称必须与参考信息一致\n"
        "5. 只输出答案，不要输出其他内容"
    )
    return f"{system}\n\n【参考信息】\n{ref}\n\n【用户问题】\n{question}"


def main():
    from openai import OpenAI

    # ========== 从环境变量读取 API 配置 ==========
    API_KEY = os.environ.get("OPENAI_API_KEY")
    BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
    MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")
    # ============================================

    if not API_KEY:
        raise SystemExit("未配置 OPENAI_API_KEY：请在 .env 或环境变量中设置后重试")

    print("=" * 50)
    print("用大模型生成高质量训练数据")
    print(f"API: {BASE_URL}, Model: {MODEL}")
    print("=" * 50)

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    kg = load_kg()
    entities = kg["entities"]
    relations = kg["object_properties"]
    id_to_e = {e["id"]: e for e in entities}

    all_samples = []

    # 1. 事实问答
    factual_templates = [
        "请介绍一下{name}。",
        "{name}是谁？",
        "关于{name}，你知道哪些内容？",
        "{name}的主要贡献是什么？",
        "{name}有什么学术价值？",
    ]
    print(f"\n1. 生成事实问答（{len(entities)} 个实体）...")
    for i, e in enumerate(entities):
        if len(all_samples) >= 500:
            break
        ref = entity_summary(e)
        name = e["text"]
        q = random.choice(factual_templates).format(name=name)
        prompt = build_prompt(ref, q, name)
        answer = call_llm(client, MODEL, prompt)
        if answer:
            all_samples.append({
                "intent": "FACTUAL", "question": q,
                "reference": ref, "answer": answer,
            })
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}] done")
        if (i + 1) % 5 == 0:
            time.sleep(0.5)

    # 2. 关系问答
    rel_templates = [
        "{a}和{b}有什么关系？",
        "{a}与{b}之间存在什么关联？",
        "{a}对{b}有什么影响？",
    ]
    valid_rels = [(id_to_e[r["source"]], id_to_e[r["target"]], r)
                  for r in relations
                  if r["source"] in id_to_e and r["target"] in id_to_e]
    random.shuffle(valid_rels)
    print(f"\n2. 生成关系问答（{min(200, len(valid_rels))} 条）...")
    for i, (src, tgt, rel) in enumerate(valid_rels[:200]):
        src_name, tgt_name = src["text"], tgt["text"]
        rel_desc = rel.get("description", "")
        ref = f"{entity_summary(src)}\n{entity_summary(tgt)}\n关系：{src_name} -> {rel['type']} -> {tgt_name}。{rel_desc}"
        q = random.choice(rel_templates).format(a=src_name, b=tgt_name)
        prompt = build_prompt(ref, q, src_name)
        answer = call_llm(client, MODEL, prompt)
        if answer:
            all_samples.append({
                "intent": "RELATION", "question": q,
                "reference": ref, "answer": answer,
            })
            if (i + 1) % 20 == 0:
                print(f"  [{i+1}] done")
        if (i + 1) % 5 == 0:
            time.sleep(0.5)

    # 3. 脉络问答
    time_entities = [e for e in entities if e["label"] == "Time"]
    chain_templates = [
        "{name}经历了哪几个发展阶段？",
        "{name}的发展历程是怎样的？",
        "请梳理{name}的发展脉络。",
    ]
    print(f"\n3. 生成脉络问答（{len(time_entities)} 个时期）...")
    for e in time_entities:
        ref = entity_summary(e)
        name = e["text"]
        q = random.choice(chain_templates).format(name=name)
        prompt = build_prompt(ref, q, name)
        answer = call_llm(client, MODEL, prompt)
        if answer:
            all_samples.append({
                "intent": "CHAIN", "question": q,
                "reference": ref, "answer": answer,
            })
        time.sleep(0.5)

    # 4. 方法问答
    method_entities = [e for e in entities if e["label"] in ("Method", "Methodology")]
    method_templates = [
        "{name}是什么？",
        "{name}在辑佚中起什么作用？",
        "{name}的基本步骤是什么？",
    ]
    print(f"\n4. 生成方法问答（{len(method_entities)} 个方法）...")
    for e in method_entities:
        ref = entity_summary(e)
        name = e["text"]
        q = random.choice(method_templates).format(name=name)
        prompt = build_prompt(ref, q, name)
        answer = call_llm(client, MODEL, prompt)
        if answer:
            all_samples.append({
                "intent": "METHOD", "question": q,
                "reference": ref, "answer": answer,
            })
        time.sleep(0.5)

    # 保存
    random.shuffle(all_samples)
    output_path = os.path.join(DATA_DIR, "llm_generated_qa.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_samples, f, ensure_ascii=False, indent=2)

    print(f"\n总计: {len(all_samples)} 条 -> {output_path}")
    print("下一步：将 llm_generated_qa.json 合并到 race_train.json 中重新训练")


if __name__ == "__main__":
    main()
