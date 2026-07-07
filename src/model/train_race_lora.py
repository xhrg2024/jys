"""
第二阶段 LoRA 微调：RACE 问答生成。
用法：python src/model/train_race_lora.py
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

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models", "Qwen2.5-7B-Instruct")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "lora_checkpoints", "qa_lora")

LORA_RANK = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LEARNING_RATE = 1e-4
BATCH_SIZE = 1
EPOCHS = 5
MAX_LENGTH = 2048


def load_json(name):
    with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def tokenize_fn(examples, tokenizer):
    texts = examples["text"]
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
    train_data = [{"text": t} for t in load_json("race600_train.json")]
    val_data = [{"text": t} for t in load_json("race600_val.json")]
    print(f"训练集: {len(train_data)} 条, 验证集: {len(val_data)} 条")

    train_ds = Dataset.from_list(train_data)
    val_ds = Dataset.from_list(val_data)
    train_ds = train_ds.map(lambda x: tokenize_fn(x, tokenizer), batched=True, remove_columns=["text"])
    val_ds = val_ds.map(lambda x: tokenize_fn(x, tokenizer), batched=True, remove_columns=["text"])

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

    print("开始训练 RACE LoRA...")
    trainer.train()

    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"模型已保存到 {OUTPUT_DIR}")

    # 简单验证
    print("\n--- 验证推理 ---")
    test_data = load_json("race600_test.json")
    from peft import PeftModel
    for item in test_data[:2]:
        text = item if isinstance(item, str) else item["text"]
        # 去掉 assistant 部分，只喂 system + user
        end_user = text.find("<|im_start|>assistant")
        prompt = text[:end_user + len("<|im_start|>assistant\n")] if end_user > 0 else text
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=MAX_LENGTH).to(model.device)
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.3, top_p=0.9, repetition_penalty=1.05)
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(result[len(prompt):] if end_user > 0 else result)
        print("---")


if __name__ == "__main__":
    main()
