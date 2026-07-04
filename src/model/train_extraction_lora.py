"""
第一阶段 LoRA 微调：三元组抽取。
用法：python src/model/train_extraction_lora.py
"""
import os
import json
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset

# ── 配置 ──────────────────────────────────────────────
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models", "Qwen2.5-7B-Instruct")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "lora_checkpoints", "extraction_lora")

LORA_RANK = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LEARNING_RATE = 2e-4
BATCH_SIZE = 4
EPOCHS = 3
MAX_LENGTH = 1024

CHAT_TEMPLATE = """<|im_start|>system
你是一个专业的辑佚史实体与关系抽取助手。<|im_end|>
<|im_start|>user
{instruction}<|im_end|>
<|im_start|>assistant
{output}<|im_end|>"""


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_sample(item):
    """转换为 Qwen ChatML 格式"""
    return CHAT_TEMPLATE.format(instruction=item["instruction"], output=item["output"])


def tokenize_fn(examples, tokenizer):
    texts = [format_sample({"instruction": inst, "output": out})
             for inst, out in zip(examples["instruction"], examples["output"])]
    tokenized = tokenizer(
        texts,
        truncation=True,
        max_length=MAX_LENGTH,
        padding=False,
    )
    tokenized["labels"] = tokenized["input_ids"].copy()
    return tokenized


def main():
    print("加载模型...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR,
        dtype=torch.bfloat16,
        device_map="auto",
        quantization_config=bnb_config,
        trust_remote_code=True,
    )

    # LoRA 配置
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # 加载数据
    train_data = load_json(os.path.join(DATA_DIR, "extraction_train.json"))
    val_data = load_json(os.path.join(DATA_DIR, "extraction_val.json"))
    print(f"训练集: {len(train_data)} 条, 验证集: {len(val_data)} 条")

    train_ds = Dataset.from_list(train_data)
    val_ds = Dataset.from_list(val_data)

    train_ds = train_ds.map(lambda x: tokenize_fn(x, tokenizer), batched=True, remove_columns=train_ds.column_names)
    val_ds = val_ds.map(lambda x: tokenize_fn(x, tokenizer), batched=True, remove_columns=val_ds.column_names)

    # 训练
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        warmup_ratio=0.05,
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        bf16=True,
        gradient_checkpointing=True,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=DataCollatorForSeq2Seq(tokenizer, model=model, padding=True),
    )

    print("开始训练...")
    trainer.train()

    # 保存
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"模型已保存到 {OUTPUT_DIR}")
    print(f"\n# 评估测试集")
    test_data = load_json(os.path.join(DATA_DIR, "extraction_test.json"))
    print(f"测试集: {len(test_data)} 条")
    # 简单推理验证
    print("\n测试集样例推理：")
    for item in test_data[:3]:
        prompt = CHAT_TEMPLATE.replace("{instruction}", item["instruction"]).replace("{output}\n", "")
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=MAX_LENGTH).to(model.device)
        outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.5, top_p=0.9)
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"  结果:\n{result[len(prompt):]}\n")
        print("  ---")


if __name__ == "__main__":
    main()
