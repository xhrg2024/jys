"""
模型加载器：加载 Qwen bf16 + intent LoRA + QA LoRA。
三个 LoRA 共享同一个 base model，不额外占显存。
"""
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models", "Qwen2.5-7B-Instruct")
INTENT_LORA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "lora_checkpoints", "intent_lora")
QA_LORA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "lora_checkpoints", "qa_lora")


class ModelLoader:
    def __init__(self):
        self.base_model = None
        self.tokenizer = None
        self.intent_model = None
        self.qa_model = None

    def load(self):
        if self.base_model is not None:
            return self.base_model, self.tokenizer

        print("加载 tokenizer...")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, trust_remote_code=True)
        self.tokenizer.pad_token = self.tokenizer.eos_token

        print("加载 Qwen2.5-7B-Instruct (bf16)...")
        self.base_model = AutoModelForCausalLM.from_pretrained(
            MODEL_DIR,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
        )
        print("模型加载完成")
        return self.base_model, self.tokenizer

    def get_intent_model(self):
        if self.base_model is None:
            self.load()
        if self.intent_model is None and os.path.exists(INTENT_LORA_DIR):
            from peft import PeftModel
            print("加载 intent LoRA...")
            self.intent_model = PeftModel.from_pretrained(self.base_model, INTENT_LORA_DIR)
        return self.intent_model or self.base_model, self.tokenizer

    def get_qa_model(self):
        if self.base_model is None:
            self.load()
        if self.qa_model is None and os.path.exists(QA_LORA_DIR):
            from peft import PeftModel
            print("加载 QA LoRA...")
            self.qa_model = PeftModel.from_pretrained(self.base_model, QA_LORA_DIR)
        return self.qa_model or self.base_model, self.tokenizer


_loader = None


def get_model():
    global _loader
    if _loader is None:
        _loader = ModelLoader()
    return _loader.load()


def get_intent_model():
    global _loader
    if _loader is None:
        _loader = ModelLoader()
    return _loader.get_intent_model()


def get_qa_model():
    global _loader
    if _loader is None:
        _loader = ModelLoader()
    return _loader.get_qa_model()
