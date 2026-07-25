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
load_dotenv(dotenv_path, override=True)

import torch
from planning.planner import Planner
from model.model_loader import get_qa_model, get_intent_model

MAX_HISTORY = 2

# ========== 从环境变量读取配置 ==========
USE_API = os.environ.get("USE_API", "false").lower() == "true"
TWO_PASS = os.environ.get("TWO_PASS", "true").lower() == "true"  # 两段式 CoT 推理

# ========== 模型供应商注册表 ==========
# 每个供应商一个 key → {label, prefix, base_url, models[]}
# prefix 对应 .env 中的 {PREFIX}_API_KEY, {PREFIX}_BASE_URL
# models 列表中每个模型：id（API 用的 model 名）, label（前端显示名）
PROVIDERS = [
    {
        "id": "deepseek",
        "label": "DeepSeek",
        "prefix": "DEEPSEEK",
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        "models": [
            {"id": "deepseek-v4-pro",   "label": "DeepSeek V4 Pro"},
            {"id": "deepseek-v4-flash", "label": "DeepSeek V4 Flash (高速)"},
            {"id": "deepseek-reasoner", "label": "DeepSeek-R1"},
        ],
    },
    {
        "id": "zhipu",
        "label": "智谱 GLM",
        "prefix": "ZHIPU",
        "base_url": os.environ.get("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
        "models": [
            {"id": "glm-5.2",         "label": "GLM-5.2 (旗舰·1M上下文)"},
            {"id": "glm-5.1",         "label": "GLM-5.1"},
            {"id": "glm-5",           "label": "GLM-5"},
            {"id": "glm-5-turbo",     "label": "GLM-5-Turbo"},
            {"id": "glm-4.7",         "label": "GLM-4.7"},
            {"id": "glm-4.7-flashx",  "label": "GLM-4.7-FlashX (轻量高速)"},
            {"id": "glm-4.6",         "label": "GLM-4.6"},
            {"id": "glm-4.5-air",     "label": "GLM-4.5-Air (高性价比)"},
            {"id": "glm-4.5-airx",    "label": "GLM-4.5-AirX (极速)"},
            {"id": "glm-4-long",      "label": "GLM-4-Long (1M上下文)"},
            {"id": "glm-4.7-flash",   "label": "GLM-4.7-Flash (免费)"},
            {"id": "glm-4-flashx",    "label": "GLM-4-FlashX (免费)"},
        ],
    },
    {
        "id": "kimi",
        "label": "Kimi (月之暗面)",
        "prefix": "KIMI",
        "base_url": os.environ.get("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
        "models": [
            {"id": "kimi-k3",                "label": "Kimi K3 (旗舰·1M上下文)", "temperature": 1, "max_tokens": 8192, "timeout": 300},
            {"id": "kimi-k2.7-code",         "label": "Kimi K2.7 Code",            "temperature": 1, "max_tokens": 4096, "timeout": 240},
            {"id": "kimi-k2.7-code-highspeed", "label": "Kimi K2.7 Code 高速版",   "temperature": 1, "max_tokens": 4096, "timeout": 120},
            {"id": "kimi-k2.6",              "label": "Kimi K2.6",                  "temperature": 1, "max_tokens": 4096, "timeout": 300},
        ],
    },
    {
        "id": "mimo",
        "label": "MiMo (小米)",
        "prefix": "MIMO",
        "base_url": os.environ.get("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1"),
        "models": [
            {"id": "mimo-v2.5-pro", "label": "MiMo v2.5 Pro (旗舰·1M上下文)"},
            {"id": "mimo-v2.5",     "label": "MiMo v2.5 (多模态)"},
        ],
    },
    {
        "id": "qwen",
        "label": "通义千问",
        "prefix": "QWEN",
        "base_url": os.environ.get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        "models": [
            {"id": "qwen3.7-max",   "label": "Qwen3.7-Max (旗舰)"},
            {"id": "qwen3.7-plus",  "label": "Qwen3.7-Plus"},
            {"id": "qwen3.6-flash", "label": "Qwen3.6-Flash (高速)"},
            {"id": "qwen-plus",     "label": "Qwen-Plus (经典)"},
            {"id": "qwen-max",      "label": "Qwen-Max (经典)"},
            {"id": "qwen-turbo",    "label": "Qwen-Turbo (经典)"},
            {"id": "qwen-long",     "label": "Qwen-Long (长上下文)"},
        ],
    },
    {
        "id": "qianfan",
        "label": "文心一言 (百度)",
        "prefix": "QIANFAN",
        "base_url": os.environ.get("QIANFAN_BASE_URL", "https://qianfan.baidubce.com/v2"),
        "models": [
            {"id": "ernie-5.1",       "label": "ERNIE 5.1"},
            {"id": "ernie-5.0",       "label": "ERNIE 5.0"},
            {"id": "ernie-4.5-turbo-128k", "label": "ERNIE 4.5 Turbo 128K"},
            {"id": "ernie-4.5-turbo-32k", "label": "ERNIE 4.5 Turbo 32K"},
            {"id": "ernie-4.5-turbo-vl", "label": "ERNIE 4.5 Turbo VL"},
            {"id": "ernie-4.5-turbo", "label": "ERNIE 4.5 Turbo"},
        ],
    },
    {
        "id": "st-gpt",
        "label": "SurplusToken GPT",
        "prefix": "ST_GPT",
        "base_url": os.environ.get("ST_GPT_BASE_URL", "https://surplustoken.com/v1"),
        "models": [
            {"id": "gpt-5.6-sol", "label": "GPT-5.6 Sol", "temperature": 0.7, "max_tokens": 8192, "timeout": 180},
        ],
    },
    {
        "id": "st-gemini",
        "label": "SurplusToken Gemini",
        "prefix": "ST_GEMINI",
        "base_url": os.environ.get("ST_GEMINI_BASE_URL", "https://surplustoken.com/v1"),
        "models": [
            {"id": "gemini-3.6-flash", "label": "Gemini 3.6 Flash", "temperature": 0.7, "max_tokens": 8192, "timeout": 120},
        ],
    },
    {
        "id": "spark",
        "label": "讯飞星火",
        "prefix": "SPARK",
        "base_url": "https://spark-api-open.xf-yun.com/v2",  # 默认，各模型可覆盖
        "models": [
            {"id": "spark-x2",   "label": "Spark X2",   "api_model": "spark-x",
             "base_url": "https://spark-api-open.xf-yun.com/x2"},
            {"id": "spark-x1.5", "label": "Spark X1.5", "api_model": "spark-x",
             "base_url": "https://spark-api-open.xf-yun.com/v2"},
        ],
    },
]

# 扁平化模型查找表（自动构建）
def _build_model_lookup():
    lookup = {}
    for p in PROVIDERS:
        for m in p["models"]:
            lookup[m["id"]] = {"provider": p, "model": m}
    return lookup

DEFAULT_MODEL = "deepseek-v4-pro"


def get_model_config(model_id):
    """根据 model_id 查找对应供应商和模型的完整 API 配置
    模型可覆盖供应商的 base_url 和 api_model（如星火通过不同 URL 区分模型）。
    """
    lookup = _build_model_lookup()
    if model_id not in lookup:
        print(f"[警告] 未知模型 '{model_id}'，回退到 '{DEFAULT_MODEL}'")
        model_id = DEFAULT_MODEL
    entry = lookup[model_id]
    p = entry["provider"]
    m = entry["model"]
    api_key = os.environ.get(f"{p['prefix']}_API_KEY", "")
    return {
        "api_key": api_key,
        "base_url": m.get("base_url") or p["base_url"],
        "model": m.get("api_model") or m["id"],
        "label": f"{p['label']} · {m['label']}",
        "temperature": m.get("temperature", 0.7),
        "max_tokens": m.get("max_tokens", 2048),
        "timeout": m.get("timeout", 180),
        "stream": m.get("stream", True),
    }


def list_providers():
    """返回供应商+模型层级列表（供前端两级下拉菜单）"""
    result = []
    for p in PROVIDERS:
        api_key = os.environ.get(f"{p['prefix']}_API_KEY", "")
        result.append({
            "id": p["id"],
            "label": p["label"],
            "configured": bool(api_key and api_key.strip()),
            "models": p["models"],
        })
    return result


class Generator:
    def __init__(self, model_id=None):
        self.planner = Planner()
        self.model, self.tokenizer = None, None
        self.use_api = USE_API  # 默认值从环境变量读取，可运行时覆盖
        self.model_id = model_id or DEFAULT_MODEL  # 当前使用的 API 模型

    def _ensure_model(self, use_api=None):
        effective = self.use_api if use_api is None else use_api
        if not effective and self.model is None:
            self.model, self.tokenizer = get_qa_model()

    def _build_messages(self, user_question, context, thinking=None):
        """构建 messages（每次独立，不保留历史）
        thinking: 第一轮 RACE 分析输出，作为第二轮的强制实体参考。
        有 thinking 时用简化 system prompt，实体名从 thinking 中提取清单。
        """
        import re
        anti_hallucination = (
            "【重要提醒】\n"
            "1. 所有实体名称（人名、书名、方法名）必须逐字照抄上方【实体名称清单】中的写法，一字不差。\n"
            "2. 清单中的名称已经过专家逐字核对，是唯一正确的写法，绝对不得凭记忆修改。\n"
            '3. "魏源"等未出现在清单中的名称绝对不得作为来源引用。\n'
        )
        if thinking:
            # 从 thinking 的【A-证据定位】中提取实体名称行，构建强制清单
            entity_lines = []
            in_evidence = False
            for line in thinking.split('\n'):
                stripped = line.strip()
                if '【A-证据定位】' in stripped:
                    in_evidence = True
                    continue
                if in_evidence and stripped.startswith('【') and '】' in stripped:
                    break
                if in_evidence and ('人名：' in stripped or '书名：' in stripped or '方法名' in stripped):
                    entity_lines.append(stripped)
            entity_checklist = '\n'.join(entity_lines) if entity_lines else '（参见前置分析【A-证据定位】）'
            print(f"[DEBUG entity_extract] 提取到 {len(entity_lines)} 行实体清单:")
            for el in entity_lines:
                print(f"  -> {el}")

            # 第二轮用精简 system prompt，不再用冗长的 RACE_SYSTEM
            system = (
                "你是一位专精于辑佚学的资深AI研究助手。"
                "你的回答必须严格遵循用户消息中提供的【实体名称清单】——"
                "清单中每个名称的写法是唯一正确的，你必须逐字照抄，不得凭记忆默写或修改任何字符。"
                "回答采用三段式：[结论] → [考据] → [总结]。"
                "标注出处时使用清单中的实体名，不得编造参考信息中未出现的来源名。"
                "全文使用简体中文，简洁准确。"
            )

            # 用户消息结构：实体清单优先，thinking 补充，原始参考信息兜底
            user_content = (
                f"【实体名称清单 — 必须逐字照抄以下写法，绝对禁止修改】\n"
                f"{entity_checklist}\n\n"
                f"【前置分析（专家已完成，包含回答结构和论据规划）】\n"
                f"{thinking}\n\n"
                f"【原始参考信息（补充）】\n{context[:1200]}\n\n"
                f"{anti_hallucination}\n"
                f"【用户问题】\n{user_question}"
            )
        else:
            from planning.planner import RACE_SYSTEM
            system = RACE_SYSTEM
            user_content = f"【参考信息】\n{context}\n\n{anti_hallucination}\n【用户问题】\n{user_question}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]

    def _think(self, question, context):
        """第一轮推理（RACE 框架）：在正式回答前，按 RACE 结构进行前置分析。
        - R: 确认角色定位，判断问题意图类型
        - A: 证据定位，逐字抄录参考信息中的实体名、关系、数据
        - C: 逻辑组织，规划回答结构（结论→论据→总结）
        - E: 预判要点，明确哪些能答、哪些缺失
        失败时返回 None，自动降级为单轮推理。
        """
        think_prompt = (
            "你是一位专精于辑佚学的资深AI研究助手。在正式回答用户问题之前，"
            "请先按以下 RACE 框架对参考信息进行前置分析。"
            "注意：这是内部分析笔记，不是最终回答，不要直接回答用户问题。\n\n"
            f"【参考信息】\n{context}\n\n"
            f"【用户问题】\n{question}\n\n"
            "━━━━━━ RACE 前置分析 ━━━━━━\n\n"
            "【R-角色定位】\n"
            "- 我作为辑佚学专家的身份\n"
            "- 此问题属于哪种类型：事实查证(FACTUAL)/关联分析(RELATION)/脉络梳理(CHAIN)/方法探讨(METHOD)/比较辨析(COMPARE)\n"
            "- 回答此问题需要覆盖的关键要素\n\n"
            "【A-证据定位】\n"
            "- 相关实体（逐字照抄参考信息原文，不得增删改任何字符）：\n"
            "  · 人名（精确到每个字）：\n"
            "  · 书名（精确到每个字，书名号内的文字不得增减）：\n"
            "  · 方法名/学派名：\n"
            "  · 时期/朝代：\n"
            "- 关键关系（使用参考信息原文表述）：\n"
            "- 关键数据（年代/卷数/数量等，照抄原文数值）：\n"
            "- 直接证据（与问题直接相关的信息）：\n"
            "- 辅助证据（提供背景的关联信息）：\n\n"
            "【C-逻辑组织】\n"
            "- 回答结构规划（结论→论据→总结 的三段式）\n"
            "- 结论预判（一句话核心答案）：\n"
            "- 论据分层（第一层/第二层/第三层各写什么）：\n"
            "- 信息脉络（实体间的因果/时序/层级关系）：\n\n"
            "【E-预期管理】\n"
            "- 参考信息足以回答的部分：\n"
            "- 参考信息不足或缺失的部分：\n"
            '- 回答中需要特别标注"据参考信息"的存疑点：\n'
            "- 预期回答长度和重点：\n\n"
            "【实体名自检 — 必须逐字拆分核对，确保与参考信息原文完全一致】\n"
            "请对上文【A-证据定位】中列出的每个实体名称，逐字拆开与参考信息比对：\n"
            "- 人名\"XXX\"：参考信息中确认为\"X-X-X\"（逐字拆分），比对结果：✓正确 或 ✗需修正为\"YYY\"\n"
            "- 书名\"XXX\"：参考信息中确认为\"X-X-X-...\"（逐字拆分），比对结果：✓正确 或 ✗需修正为\"YYY\"\n"
            "- 方法名\"XXX\"：参考信息中确认为\"X-X-X\"（逐字拆分），比对结果：✓正确 或 ✗需修正为\"YYY\"\n"
            "注意：逐字拆分是指把名称的每个汉字用\"-\"分隔写出（如\"辑-佚-书\"），以确认没有多字、少字、错字。"
            "如果发现某实体名写错了，立即在自检中修正并标注✗。仅输出分析笔记，不要输出最终回答。"
        )
        messages = [
            {"role": "system", "content": "你是一位严谨的辑佚学专家。请按 RACE 框架对参考信息进行前置分析，精确抄录实体名称和关系。只做分析笔记，不直接回答用户问题。"},
            {"role": "user", "content": think_prompt},
        ]
        try:
            result = self._call_api(messages, max_tokens=4096)
            if result.startswith("API错误") or result.startswith("API调用失败"):
                print(f"\033[2m[Think] 分析失败，降级为单轮推理\033[0m")
                return None
            return result
        except Exception as e:
            print(f"\033[2m[Think] 异常，降级为单轮推理: {e}\033[0m")
            return None

    def _call_api_stream(self, messages, max_tokens=None, model_id=None):
        """流式调用API，yield (token_type, text) 元组。
        token_type: "text" | "reasoning"
        """
        import requests
        import json

        mid = model_id or self.model_id
        config = get_model_config(mid)
        if max_tokens is None:
            max_tokens = config.get("max_tokens", 2048)
        api_key = config["api_key"].strip()
        base_url = config["base_url"].strip()
        model = config["model"].strip()
        label = config["label"]
        use_stream = config.get("stream", True)

        if not api_key:
            yield ("text", f"错误：{label} 的 API Key 未配置，请在 .env 文件中设置对应 API_KEY")
            return

        stream_tag = "⚡流式" if use_stream else "📦非流式"
        print(f"  [API] {label}  |  {stream_tag}  |  {base_url}  |  model={model}  |  max_tokens={max_tokens}  |  timeout={config['timeout']}s")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8",
        }
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": config["temperature"],
            "stream": use_stream,
        }

        try:
            body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                data=body_bytes,
                timeout=(10, config.get("timeout", 180)),
                stream=use_stream,
            )
            if response.status_code != 200:
                print(f"[API] HTTP {response.status_code}: {response.text[:500]}")
                yield ("text", f"API错误({response.status_code}): {response.text[:200]}")
                return

            if use_stream:
                for line in response.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        reasoning = delta.get("reasoning_content") or delta.get("thinking") or ""
                        if reasoning:
                            print(f"\033[2m{reasoning}\033[0m", end="", flush=True)
                            yield ("reasoning", reasoning)
                        content = delta.get("content", "")
                        if content:
                            print(content, end="", flush=True)
                            yield ("text", content)
                    except json.JSONDecodeError:
                        continue
                print()
            else:
                result = response.json()
                if "choices" not in result:
                    msg = f"API错误: 响应格式异常 - {json.dumps(result, ensure_ascii=False)[:200]}"
                    print(msg)
                    yield ("text", msg)
                    return
                content = result["choices"][0]["message"]["content"]
                if content is None:
                    msg = "API错误: 模型返回空内容"
                    print(msg)
                    yield ("text", msg)
                    return
                print(content.strip())
                yield ("text", content.strip())
        except Exception as e:
            import traceback
            print(f"[API] 调用失败: {e}")
            traceback.print_exc()
            yield ("text", f"API调用失败: {str(e)}")

    def _call_api(self, messages, max_tokens=None, model_id=None):
        """调用API并返回完整文本（内部使用 _call_api_stream）"""
        full_text = []
        for tt, text in self._call_api_stream(messages, max_tokens, model_id):
            if tt == "text":
                full_text.append(text)
        return "".join(full_text)

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

    def _call_model(self, messages, use_api=None):
        """调用模型（根据配置选择本地或API）"""
        effective = self.use_api if use_api is None else use_api
        if effective:
            return self._call_api(messages)
        else:
            return self._call_local_model(messages)

    def _classify_intent(self, question, use_api=None):
        """快速判断意图（使用 intent LoRA，如不可用则 fallback 规则法）"""
        effective = self.use_api if use_api is None else use_api
        if effective:
            # 使用API判断意图
            messages = [
                {"role": "system", "content": (
                    "你是一个意图分类器。根据用户问题判断其属于以下哪种类型，只输出类型名（大写），不要输出其他内容。\n\n"
                    "FACTUAL — 事实查证：询问某个实体的属性、定义、生平、卷数等基本信息。\n"
                    "  示例：「《玉函山房辑佚书》有多少卷？」「马国翰是谁？」\n\n"
                    "RELATION — 关联分析：询问两个或多个实体之间的关系、关联、传承。\n"
                    "  示例：「马国翰和王仁俊有什么关系？」「王仁俊继承了谁的工作？」\n\n"
                    "CHAIN — 脉络梳理：询问某事物的发展历程、演变阶段、历史脉络。\n"
                    "  示例：「清代辑佚学经历了哪几个阶段？」「辑佚方法是如何演变的？」\n\n"
                    "METHOD — 方法探讨：询问方法、原则、步骤、技术手段。\n"
                    "  示例：「辑佚的三原则是什么？」「如何从类书中辑佚？」\n\n"
                    "COMPARE — 比较辨析：询问两个事物的异同、优劣、区别。\n"
                    "  示例：「马国翰和严可均的辑佚方法有何不同？」「乾嘉学派与常州学派有何区别？」"
                )},
                {"role": "user", "content": question},
            ]
            result = self._call_api(messages).strip().upper()
            for intent in ["FACTUAL", "RELATION", "CHAIN", "METHOD", "COMPARE"]:
                if intent in result:
                    return intent
            # API 失败或返回异常时，规则法兜底
            print(f"  [意图] API 分类失败，启用规则法兜底")
            return self._rule_based_intent(question)
        else:
            # 使用本地intent LoRA
            messages = [
                {"role": "system", "content": (
                    "你是一个意图分类器。根据用户问题判断其属于以下哪种类型，只输出类型名（大写），不要输出其他内容。\n\n"
                    "FACTUAL — 事实查证：询问某个实体的属性、定义、生平、卷数等。示例：「《玉函山房辑佚书》有多少卷？」\n"
                    "RELATION — 关联分析：询问两个或多个实体之间的关系。示例：「马国翰和王仁俊有什么关系？」\n"
                    "CHAIN — 脉络梳理：询问发展历程、演变阶段。示例：「清代辑佚学经历了哪几个阶段？」\n"
                    "METHOD — 方法探讨：询问方法、原则、步骤。示例：「辑佚的三原则是什么？」\n"
                    "COMPARE — 比较辨析：询问两个事物的异同区别。示例：「马国翰和严可均的辑佚方法有何不同？」"
                )},
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

    @staticmethod
    def _rule_based_intent(question):
        """规则法判断意图（API 不可用时的兜底方案）"""
        if any(w in question for w in ["关系", "关联", "联系", "之间"]):
            return "RELATION"
        if any(w in question for w in ["发展", "演变", "历程", "阶段", "脉络", "源流"]):
            return "CHAIN"
        if any(w in question for w in ["方法", "原则", "步骤", "如何", "怎样", "怎么"]):
            return "METHOD"
        if any(w in question for w in ["区别", "比较", "对比", "异同", "哪个更", "谁更"]):
            return "COMPARE"
        return "FACTUAL"

    def answer(self, question, verbose=False, use_api=None, model_id=None):
        """主入口：给定用户问题，返回 (answer, plan_log)
        use_api: None=使用默认配置, True=强制API, False=强制本地模型
        model_id: 指定 API 模型（如 "deepseek-chat", "glm-4-plus"），None=使用当前默认

        API 模式下默认启用两段式 CoT 推理：
        1. 第一轮（Think）：分析参考信息，逐字抄录实体名
        2. 第二轮（Answer）：基于分析笔记 + 参考信息正式回答
        可通过 .env 中 TWO_PASS=false 关闭。
        """
        if model_id:
            self.model_id = model_id
        effective = self.use_api if use_api is None else use_api
        if not effective:
            self._ensure_model(use_api=effective)

        intent = self._classify_intent(question, use_api=effective)
        plan = self.planner.plan(question, intent_override=intent)

        if verbose:
            mode = "API" if effective else "本地"
            print(f"\n[模式] {mode}")
            print(f"[意图] {plan['intent']}")
            print(f"[实体] {[(e['name'], e['label']) for e in plan['parsed']['entities'][:5]]}")
            c = plan['context']
            if len(c) > 500:
                c = c[:500] + "..."
            print(f"[参考信息]\n{c}\n")

        # 两段式 CoT 推理（仅 API 模式，默认启用）
        thinking = None
        if effective and TWO_PASS:
            DIM = "\033[2m"
            RST = "\033[0m"
            cfg = get_model_config(self.model_id)
            print(f"{DIM}┌─ Think（RACE 前置分析）── {cfg['label']} ── 开始{RST}")
            thinking = self._think(question, plan["context"])
            if thinking:
                print(f"{DIM}└─ Think 结束 ──────────────{RST}\n")
            else:
                print(f"{DIM}└─ Think 失败，降级为单轮推理{RST}\n")

        self.last_thinking = thinking  # 暴露给 API 层

        messages = self._build_messages(question, plan["context"], thinking)
        response = self._call_model(messages, use_api=effective)
        cleaned = self.planner.postprocess(response)

        # 打印清理对比（仅当清理改变了原文时）
        BLD = "\033[1m"
        GRN = "\033[32m"
        RST = "\033[0m"
        cfg = get_model_config(self.model_id)
        if response != cleaned:
            print(f"\n{GRN}┌─ 清理修正 ──{RST}")
            for line in cleaned.split("\n"):
                print(f"{GRN}│ {line}{RST}")
            print(f"{GRN}└───────────────{RST}\n")
        print(f"{BLD}┌─ Answer 结束 ── {cfg['label']}{RST}\n")

        return cleaned, plan.get("plan_log", {})

    def answer_stream(self, question, model_id=None):
        """流式回答生成器，yield SSE 事件 dict 供前端实时渲染。
        事件类型：plan / thinking / answer / done / error
        """
        if model_id:
            self.model_id = model_id
        effective = self.use_api

        try:
            # ── 意图 + 检索 ──
            intent = self._classify_intent(question, use_api=effective)
            plan = self.planner.plan(question, intent_override=intent)
            yield {"type": "plan", "intent": plan["intent"], "plan_log": plan.get("plan_log", {})}

            # ── Think 阶段 ──
            thinking = None
            if effective and TWO_PASS:
                yield {"type": "thinking_start"}
                think_full = []
                think_msgs = [
                    {"role": "system", "content": "你是一位严谨的辑佚学专家。请按 RACE 框架对参考信息进行前置分析，精确抄录实体名称和关系。只做分析笔记，不直接回答用户问题。"},
                    {"role": "user", "content": (
                        "你是一位专精于辑佚学的资深AI研究助手。在正式回答用户问题之前，"
                        "请先按以下 RACE 框架对参考信息进行前置分析。"
                        "注意：这是内部分析笔记，不是最终回答，不要直接回答用户问题。\n\n"
                        f"【参考信息】\n{plan['context']}\n\n"
                        f"【用户问题】\n{question}\n\n"
                        "━━━━━━ RACE 前置分析 ━━━━━━\n\n"
                        "【R-角色定位】\n- 我作为辑佚学专家的身份\n"
                        "- 此问题属于哪种类型：FACTUAL/RELATION/CHAIN/METHOD/COMPARE\n"
                        "- 回答此问题需要覆盖的关键要素\n\n"
                        "【A-证据定位】\n"
                        "- 相关实体（逐字照抄参考信息原文，不得增删改任何字符）：\n"
                        "  · 人名（精确到每个字）：\n"
                        "  · 书名（精确到每个字，书名号内的文字不得增减）：\n"
                        "  · 方法名/学派名：\n"
                        "  · 时期/朝代：\n"
                        "- 关键关系（使用参考信息原文表述）：\n"
                        "- 关键数据（年代/卷数/数量等，照抄原文数值）：\n"
                        "- 直接证据（与问题直接相关的信息）：\n"
                        "- 辅助证据（提供背景的关联信息）：\n\n"
                        "【C-逻辑组织】\n"
                        "- 回答结构规划（结论→论据→总结 的三段式）\n"
                        "- 结论预判（一句话核心答案）：\n"
                        "- 论据分层：\n"
                        "- 信息脉络：\n\n"
                        "【E-预期管理】\n"
                        "- 参考信息足以回答的部分：\n"
                        "- 参考信息不足或缺失的部分：\n"
                        "- 回答中需要特别标注\"据参考信息\"的存疑点：\n"
                        "- 预期回答长度和重点：\n\n"
                        "【实体名自检】\n"
                        "逐字拆分核对每个实体名，格式：人名\"XXX\"→\"X-X-X\"，比对结果：✓正确 或 ✗需修正为\"YYY\"。\n"
                        "仅输出分析笔记，不要输出最终回答。"
                    )},
                ]
                for tt, text in self._call_api_stream(think_msgs, max_tokens=4096, model_id=self.model_id):
                    if tt == "text" and not text.startswith("API错误") and not text.startswith("API调用失败"):
                        think_full.append(text)
                        yield {"type": "thinking", "content": text}
                thinking = "".join(think_full).strip()
                if thinking:
                    self.last_thinking = thinking
                yield {"type": "thinking_end"}

            # ── Answer 阶段 ──
            yield {"type": "answer_start"}
            messages = self._build_messages(question, plan["context"], thinking)
            for tt, text in self._call_api_stream(messages, model_id=self.model_id):
                if tt == "text":
                    yield {"type": "answer", "content": text}

            yield {"type": "done"}

        except Exception as e:
            yield {"type": "error", "message": str(e)}


def main():
    """命令行交互式问答"""
    verbose = "-v" in sys.argv
    gen = Generator()
    print("=" * 50)
    print("辑佚史智能体 - 命令行问答")
    if USE_API:
        providers = list_providers()
        for p in providers:
            status = "✓" if p["configured"] else "✗(未配置)"
            model_names = ", ".join(m["label"] for m in p["models"])
            print(f"  [{status}] {p['label']}: {model_names}")
        print(f"当前: {get_model_config(gen.model_id)['label']}")
        print(f"推理: {'两段式CoT' if TWO_PASS else '单轮直答'}")
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
