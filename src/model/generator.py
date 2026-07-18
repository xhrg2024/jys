"""
推理接口：接收用户问题 → 全链路处理 → 返回答案。
支持本地Qwen模型和外部API（多家厂商）切换。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（从项目根目录）
dotenv_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path)

import torch
from planning.planner import Planner
from model.model_loader import get_qa_model, get_intent_model

MAX_HISTORY = 2

# ========== 从环境变量读取配置 ==========
USE_API = os.environ.get("USE_API", "false").lower() == "true"


def get_api_config():
    """从 .env 读取通用 API 配置"""
    return {
        "api_key": os.environ.get("API_KEY", ""),
        "base_url": os.environ.get("BASE_URL", "https://api.deepseek.com"),
        "model": os.environ.get("API_MODEL", "deepseek-chat"),
    }


class Generator:
    def __init__(self):
        self.planner = Planner()
        self.model, self.tokenizer = None, None

    def _ensure_model(self):
        if not USE_API and self.model is None:
            self.model, self.tokenizer = get_qa_model()

    def _build_messages(self, user_question, context):
        """构建 messages（每次独立，不保留历史）"""
        from planning.planner import RACE_SYSTEM
        system = RACE_SYSTEM
        user_content = f"【参考信息】\n{context}\n\n【用户问题】\n{user_question}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]

    def _call_api(self, messages):
        """调用外部API（兼容OpenAI格式的API）"""
        import requests

        config = get_api_config()
        if not config["api_key"]:
            return "错误：未配置API Key，请在 .env 文件中设置"

        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }

        data = {
            "model": config["model"],
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7,
        }

        try:
            response = requests.post(
                f"{config['base_url']}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            if response.status_code != 200:
                print(f"[API] 错误: {response.status_code} - {response.text}")
                return f"API错误: {response.status_code}"
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[API] 调用失败: {e}")
            return f"API调用失败: {str(e)}"

    def _call_local_model(self, messages):
        """调用本地Qwen模型"""
        chat_text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(
            chat_text, return_tensors="pt", truncation=True, max_length=2048
        ).to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.3,
                top_p=0.9,
                repetition_penalty=1.15,
                no_repeat_ngram_size=3,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.pad_token_id,
            )

        input_len = inputs.input_ids.shape[1]
        new_tokens = outputs[0][input_len:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    def _call_model(self, messages):
        """调用模型（根据配置选择本地或API）"""
        if USE_API:
            return self._call_api(messages)
        else:
            return self._call_local_model(messages)

    def _classify_intent(self, question):
        """快速判断意图（使用 intent LoRA，如不可用则 fallback 规则法）"""
        if USE_API:
            # 使用API判断意图
            messages = [
                {"role": "system", "content": "判断用户问题的意图类型。只输出以下之一：FACTUAL, RELATION, CHAIN, METHOD, COMPARE。不要输出其他内容。"},
                {"role": "user", "content": question},
            ]
            result = self._call_api(messages).strip().upper()
            for intent in ["FACTUAL", "RELATION", "CHAIN", "METHOD", "COMPARE"]:
                if intent in result:
                    return intent
            return "FACTUAL"
        else:
            # 使用本地intent LoRA
            messages = [
                {"role": "system", "content": "判断用户问题的意图类型。只输出以下之一：FACTUAL, RELATION, CHAIN, METHOD, COMPARE。不要输出其他内容。"},
                {"role": "user", "content": question},
            ]
            chat_text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            intent_model, _ = get_intent_model()
            inputs = self.tokenizer(
                chat_text, return_tensors="pt", truncation=True, max_length=256
            ).to(intent_model.device)
            with torch.no_grad():
                outputs = intent_model.generate(
                    **inputs, max_new_tokens=5, temperature=0.1,
                    do_sample=False, pad_token_id=self.tokenizer.pad_token_id
                )
            result = self.tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True
            ).strip().upper()
            for intent in ["FACTUAL", "RELATION", "CHAIN", "METHOD", "COMPARE"]:
                if intent in result:
                    return intent
            return "FACTUAL"

    def answer(self, question, verbose=False):
        """主入口：给定用户问题，返回 (answer, plan_log)"""
        if not USE_API:
            self._ensure_model()

        intent = self._classify_intent(question)
        plan = self.planner.plan(question, intent_override=intent)

        if verbose:
            print(f"\n[意图] {plan['intent']}")
            print(f"[实体] {[(e['name'], e['label']) for e in plan['parsed']['entities'][:5]]}")
            c = plan['context']
            if len(c) > 500:
                c = c[:500] + "..."
            print(f"[参考信息]\n{c}\n")

        messages = self._build_messages(question, plan["context"])
        response = self._call_model(messages)
        return self.planner.postprocess(response), plan.get("plan_log", {})


def main():
    """命令行交互式问答"""
    verbose = "-v" in sys.argv
    gen = Generator()
    print("=" * 50)
    print("辑佚史智能体 - 命令行问答")
    if USE_API:
        config = get_api_config()
        print(f"模式: 外部API")
        print(f"模型: {config['model']}")
    else:
        print("模式: 本地Qwen")
    if verbose:
        print("（Verbose 模式：显示检索过程）")
    print("输入 'quit' 退出")
    print("=" * 50)

    while True:
        try:
            q = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q.lower() == "quit":
            break
        answer, _ = gen.answer(q, verbose=verbose)
        print(f"\n{answer}")


if __name__ == "__main__":
    main()
