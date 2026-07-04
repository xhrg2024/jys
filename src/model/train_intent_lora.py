"""
意图分类 LoRA 微调：让 Qwen 精准判断用户意图。
训练数据格式：assistant 只输出意图标签（一个词）。
用法：python src/model/train_intent_lora.py
"""
import os, json, torch
from transformers import (
    AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer,
    DataCollatorForSeq2Seq, BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models", "Qwen2.5-7B-Instruct")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "lora_checkpoints", "intent_lora")

LORA_RANK = 8
LORA_ALPHA = 16
LORA_DROPOUT = 0.05
LEARNING_RATE = 1e-4
BATCH_SIZE = 4
EPOCHS = 5
MAX_LENGTH = 256  # 意图分类只需很短上下文


def main():
    print("加载模型...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR, dtype=torch.bfloat16, device_map="auto",
        quantization_config=bnb, trust_remote_code=True,
    )

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=LORA_RANK, lora_alpha=LORA_ALPHA, lora_dropout=LORA_DROPOUT,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # 加载数据
    train_data = load_json("intent_train.json")
    val_data = load_json("intent_val.json")
    print(f"训练集: {len(train_data)} 条, 验证集: {len(val_data)} 条")

    train_ds = Dataset.from_list([{"text": t} for t in train_data])
    val_ds = Dataset.from_list([{"text": t} for t in val_data])

    def tokenize(examples):
        tok = tokenizer(examples["text"], truncation=True, max_length=MAX_LENGTH, padding=False)
        tok["labels"] = tok["input_ids"].copy()
        return tok

    train_ds = train_ds.map(tokenize, batched=True, remove_columns=["text"])
    val_ds = val_ds.map(tokenize, batched=True, remove_columns=["text"])

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
        model=model, args=training_args,
        train_dataset=train_ds, eval_dataset=val_ds,
        data_collator=DataCollatorForSeq2Seq(tokenizer, model=model, padding=True),
    )

    print("开始训练意图分类 LoRA...")
    trainer.train()
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"保存到 {OUTPUT_DIR}")

    # 简单验证
    from peft import PeftModel
    print("\n验证：")
    test_data = load_json("intent_test.json")[:10]
    for text in test_data:
        end = text.find("<|im_start|>assistant\n")
        prompt = text[:end + len("<|im_start|>assistant\n")]
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=MAX_LENGTH).to(model.device)
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=5, temperature=0.1, do_sample=False,
                                     pad_token_id=tokenizer.pad_token_id)
        result = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
        # 找 ground truth
        gt = text.split("assistant\n")[-1].replace("<|im_end|>", "").strip()
        ok = "✅" if gt in result else "❌"
        print(f"  {ok} 预测: {result:12s}  期望: {gt}")


def load_json(name):
    with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    main()
