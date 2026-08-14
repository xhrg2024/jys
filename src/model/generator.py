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


def _to_simplified(text):
    """把问题中的繁体字统一转为简体，保证与全简体的知识图谱检索对齐。"""
    if not text:
        return text
    try:
        from opencc import OpenCC
        return OpenCC('t2s').convert(text)
    except ImportError:
        return text


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
            {"id": "losofalx_2026xhrg786315", "label": "精调模型 v1 (微调版本)"},
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


def _build_tool_selection_system_prompt(intent):
    """构建工具选择 LLM 的 system prompt，包含意图引导。"""
    intent_guidance = {
        "FACTUAL": (
            "用户正在查证事实。应同时进行三类检索：\n"
            "1) 图谱：【优先用 kg_explore_entity 一次获取属性+关系网+关联实体】，如实体名不确定可先用 kg_list_by_type\n"
            "2) SQL：search_document + search_full_text + search_author（如涉及人名）\n"
            "3) 向量：vector_search"
        ),
        "RELATION": (
            "用户正在分析实体关联。【重要】图谱检索只需调用一个工具：kg_explore_relation(A,B)。"
            "该工具已内置：属性查询+关系网络+多跳扩展+最短路径，无需单独调用 kg_find_entities 等底层工具。\n"
            "完整组合：kg_explore_relation(A,B) + vector_search + SQL（search_document + search_full_text + search_author）"
        ),
        "CHAIN": (
            "用户正在梳理发展脉络。应同时进行三类检索：\n"
            "1) 图谱：kg_list_by_type（列出相关实体）+ kg_explore_entity（对关键实体深度探索）\n"
            "2) SQL：browse_documents + search_titles + search_full_text\n"
            "3) 向量：vector_search"
        ),
        "METHOD": (
            "用户正在探讨研究方法。应同时进行三类检索：\n"
            "1) 图谱：kg_list_by_type(Method) + kg_explore_entity（对核心方法实体深度探索）\n"
            "2) SQL：search_full_text（注意用'校勘''训诂''考证'等而非'辑佚'）+ search_titles + browse_documents\n"
            "3) 向量：vector_search"
        ),
        "COMPARE": (
            "用户正在比较两个事物。【重要】图谱检索只需调用一个工具：kg_explore_relation(A,B)。"
            "该工具已内置：双方属性+关系网络+多跳扩展+最短路径，无需单独调用底层工具。\n"
            "完整组合：kg_explore_relation(A,B) + vector_search + SQL（search_document×2 + search_author×2 + search_full_text）"
        ),
    }
    guidance = intent_guidance.get(intent, intent_guidance["FACTUAL"])

    return (
        "你是一个辑佚学文献检索助手。你的任务是根据用户问题选择合适的工具来检索信息。\n"
        "不要直接回答问题，只选择和调用合适的工具。\n\n"
        "【组合检索铁律 — 必须遵守】\n"
        "1. 每次检索必须覆盖三类工具，每类至少调用 2 个：图谱(kg_*) + SQL(search_*/browse_*) + 向量(vector_search)\n"
        "2. vector_search 是语义兜底，每次都调——防止精确名称在知识图谱中未命中\n"
        "3. kg_find_entities 和 kg_get_entity_relations 是固定搭档——查属性+查关系网缺一不可\n"
        "4. 涉及多个实体时，必须对每个实体分别调用 kg_find_entities + kg_get_entity_relations\n"
        "5. 涉及文献名时，必须同时调用 search_document + search_full_text + search_titles\n"
        "6. 涉及人名时，必须同时调用 search_author + kg_find_entities\n"
        "7. 宁可多调 5 个工具，不可遗漏关键信息。信息充分比精准克制更重要\n\n"
        f"【用户意图】{intent} — {guidance}\n\n"
        "【原则】\n"
        "1. 每种工具可调用 1-3 次，用不同参数覆盖不同实体或不同搜索词\n"
        "2. 模糊实体名先用 vector_search 定位，再用 kg_find_entities 查详情\n"
        "3. 查询古籍原文时使用 search_full_text，注意古文献术语与现代术语的差异\n"
        "4. 一次调用尽可能多地同时选择工具（并行执行，不会增加延迟）"
    )


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
        anti_hallucination = "【重要提醒】实体名称必须逐字照抄【实体名称清单】中的写法，不得凭记忆修改。\n"
        if thinking:
            # 从 thinking 中提取实体名，构建强制清单（兼容新版极简格式 A： 与旧版 人名：/书名：/方法名：）
            entity_lines = []
            for line in thinking.split('\n'):
                stripped = line.strip()
                if stripped.startswith('A：') or stripped.startswith('A:') or '直接相关实体名' in stripped:
                    entity_lines.append(stripped)
                elif '人名：' in stripped or '书名：' in stripped or '方法名：' in stripped:
                    entity_lines.append(stripped)
            entity_checklist = '\n'.join(entity_lines) if entity_lines else '（无）'
            print(f"[DEBUG entity_extract] 提取到 {len(entity_lines)} 行实体清单:")
            for el in entity_lines:
                print(f"  -> {el}")

            # 第二轮用精简 system prompt，不再用冗长的 RACE_SYSTEM
            system = (
                "你是一位专精于辑佚学的AI研究助手。直接输出答案正文，不要输出思考过程。\n"
                "答案用三段式：[结论]→[考据]→[总结]，简体中文。\n"
                "实体名称逐字照抄【实体名称清单】；引用参考信息用其原始编号 [n]，不得重新编号。"
            )

            # 清理 thinking 中的"不要输出最终回答"等 Think 阶段指令，避免误导第二轮
            clean_thinking = thinking
            for phrase in ["仅输出分析笔记", "不要输出最终回答", "不直接回答用户问题",
                           "这是内部分析笔记，不是最终回答", "只做分析笔记",
                           "不要直接回答", "不要输出最终回答。"]:
                clean_thinking = clean_thinking.replace(phrase, "【上一步指令，已完成】")

            # 用户消息结构：实体清单优先，thinking 补充，原始参考信息兜底
            user_content = (
                f"【实体名称清单】\n{entity_checklist}\n\n"
                f"【前置分析】\n{clean_thinking}\n\n"
                f"【参考信息】\n{context[:1200]}\n\n"
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

    def _call_api_tool_selection(self, question, intent):
        """调用 LLM 选择工具并执行，返回工具结果列表。
        失败时返回 None，由调用方降级为硬编码分派。
        """
        import requests
        import json
        from tools.tool_registry import TOOL_SCHEMAS, execute_tool_calls

        config = get_model_config(self.model_id)
        if not config["api_key"]:
            print("[ToolSelect] API Key 未配置，跳过工具选择")
            return None

        system_prompt = _build_tool_selection_system_prompt(intent)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]
        body = {
            "model": config["model"],
            "messages": messages,
            "tools": TOOL_SCHEMAS,
            "tool_choice": "auto",
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json; charset=utf-8",
        }

        try:
            body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
            response = requests.post(
                f"{config['base_url']}/chat/completions",
                headers=headers,
                data=body_bytes,
                timeout=(10, 60),
                stream=False,
            )
            if response.status_code != 200:
                print(f"[ToolSelect] HTTP {response.status_code}: {response.text[:300]}")
                return None

            result = response.json()
            if "choices" not in result or not result["choices"]:
                print("[ToolSelect] 响应无 choices，降级")
                return None

            message = result["choices"][0].get("message", {})
            tool_calls = message.get("tool_calls", [])
            if not tool_calls:
                print("[ToolSelect] LLM 未选择任何工具，降级")
                return None

            cfg_label = config["label"]
            tool_names = [tc["function"]["name"] for tc in tool_calls]
            print(f"[ToolSelect] {cfg_label} 选择了 {len(tool_calls)} 个工具: {tool_names}")

            results = execute_tool_calls(tool_calls)
            return results

        except Exception as e:
            print(f"[ToolSelect] 失败: {e}")
            return None

    def _build_think_messages(self, question, context):
        """构建 Think 阶段的 RACE 前置分析消息。

        提示词刻意精简，并对上下文截断，避免超长参考信息诱发推理模型陷入长思考。
        """
        if context and len(context) > 6000:
            context = context[:6000] + "\n（上下文过长，已截断）"
        system = "你是一位严谨的辑佚学专家。请对参考信息做极简前置分析笔记，只输出笔记，不要直接回答。"
        prompt = (
            f"【参考信息】\n{context}\n\n"
            f"【用户问题】\n{question}\n\n"
            "按以下四行输出，每行一句，全文不超过 1000 字：\n"
            "R：问题类型 + 关键要素\n"
            "A：直接相关实体名（照抄原文）\n"
            "C：一句话结论预判\n"
            "E：能答/缺失\n\n"
            "不要复述框架定义、不要解释思考过程、不要写\"我需要/我们要\"、不要枚举无关实体。\n"
            "直接输出笔记，不要输出最终回答。"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

    def _think(self, question, context):
        """第一轮推理（RACE 框架）：在正式回答前，按 RACE 结构进行前置分析。
        失败时返回 None，自动降级为单轮推理。
        """
        messages = self._build_think_messages(question, context)
        try:
            result = self._call_api(messages, max_tokens=4096)
            if result.startswith("API错误") or result.startswith("API调用失败"):
                print(f"\033[2m[Think] 分析失败，降级为单轮推理\033[0m")
                return None
            return result
        except Exception as e:
            print(f"\033[2m[Think] 异常，降级为单轮推理: {e}\033[0m")
            return None

    def _call_api_stream(self, messages, max_tokens=None, model_id=None, max_reasoning_chars=None):
        """流式调用API，yield (token_type, text) 元组。
        token_type: "text" | "reasoning"
        max_reasoning_chars: 推理内容（reasoning_content）超过该长度时主动断开，
                             防止推理模型陷入自我复读无限循环。
        """
        import requests
        import json
        import time

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
            # 抑制复读：推理型模型在冗长模板下易陷入自我循环
            "frequency_penalty": config.get("frequency_penalty", 0.5),
            "presence_penalty": config.get("presence_penalty", 0.0),
        }

        body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        url = f"{base_url}/chat/completions"

        # 网络层自动重试：连接重置/超时等瞬时错误，最多重试 3 次
        MAX_RETRIES = 3
        response = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    data=body_bytes,
                    timeout=(10, config.get("timeout", 180)),
                    stream=use_stream,
                )
                if response.status_code == 200:
                    break
                # 429/5xx 等瞬时错误才重试；4xx 是请求本身问题，重试无意义
                if response.status_code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                    wait = min(2 ** attempt, 8)
                    print(f"[API] HTTP {response.status_code}，第 {attempt + 1}/{MAX_RETRIES} 次重试（{wait}s）")
                    time.sleep(wait)
                    continue
                print(f"[API] HTTP {response.status_code}: {response.text[:500]}")
                yield ("text", f"API错误({response.status_code}): {response.text[:200]}")
                return
            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES:
                    wait = min(2 ** attempt, 8)
                    print(f"[API] 连接失败，第 {attempt + 1}/{MAX_RETRIES} 次重试（{wait}s）：{e}")
                    time.sleep(wait)
                    continue
                import traceback
                print(f"[API] 调用失败（已重试 {MAX_RETRIES} 次仍失败）: {e}")
                traceback.print_exc()
                yield ("text", f"API调用失败: {str(e)}")
                return

        if use_stream:
            # 强制 UTF-8 解码，避免部分 API 因缺少 charset 头而乱码
            reasoning_chars = 0
            for raw_line in response.iter_lines(decode_unicode=False):
                if not raw_line:
                    continue
                try:
                    line = raw_line.decode("utf-8")
                except UnicodeDecodeError:
                    line = raw_line.decode("utf-8", errors="replace")
                if not line.startswith("data: "):
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
                        reasoning_chars += len(reasoning)
                        if max_reasoning_chars and reasoning_chars > max_reasoning_chars:
                            print(f"\n[API] 推理内容超过 {max_reasoning_chars} 字，疑似陷入复读，主动中断")
                            try:
                                response.close()
                            except Exception:
                                pass
                            break
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
        question = _to_simplified(question)  # 先繁体→简体，再进入检索与解析
        effective = self.use_api if use_api is None else use_api
        if not effective:
            self._ensure_model(use_api=effective)

        intent = self._classify_intent(question, use_api=effective)

        # ── 会话日志 ──
        from utils.session_logger import SessionLogger
        logger = SessionLogger(question)
        cfg = get_model_config(self.model_id)
        logger.log_header(intent, cfg["label"])

        # ── LLM Tool Calling（仅 API 模式）──
        tool_results = None
        if effective:
            tool_results = self._call_api_tool_selection(question, intent)
            if tool_results:
                names = [tr["name"] for tr in tool_results if tr.get("result")]
                print(f"[ToolCall] ✅ LLM 选择了 {len(names)} 个工具: {', '.join(names)}")
                logger.log_tool_selection(True, names)
            else:
                print(f"[ToolCall] ⚠️ 工具选择失败或为空，降级为硬编码分派")
                logger.log_tool_selection(False, [], "API 返回空或失败")

        plan = self.planner.plan(question, intent_override=intent, tool_results=tool_results, logger=logger)

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

        # 日志：Think 阶段
        if thinking:
            logger.log_thinking(thinking)

        messages = self._build_messages(question, plan["context"], thinking)
        response = self._call_model(messages, use_api=effective)
        cleaned = self.planner.postprocess(response)

        # 日志：最终回答
        logger.log_raw_api_response("raw_response", response)
        logger.log_answer(cleaned)
        logger.close()
        print(f"[Log] 完整日志已写入: {logger.get_path()}")

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

        # 按正文首次出现顺序重排引用编号（[2][3][1] → [1][2][3]），并只保留被引用来源
        plan_log = plan.get("plan_log") or {}
        if plan_log.get("source_index"):
            cleaned, plan_log["source_index"] = self._renumber_citations_by_appearance(cleaned, plan_log["source_index"])

        return cleaned, plan_log

    def _filter_source_index_by_citations(self, answer_text, source_index):
        """根据回答中实际出现的 [N] 引用，过滤 source_index 只保留被引用条目。
        消除 LLM 生成的引用编号与 source_index 条目数不一致的幻觉。
        """
        import re
        if not source_index:
            return source_index
        cited = set()
        for m in re.finditer(r'\[(\d+)\]', answer_text or ""):
            cited.add(m.group(1))
        return {k: v for k, v in source_index.items() if k in cited}

    def _renumber_citations_by_appearance(self, answer_text, source_index):
        """按引用在正文中首次出现的顺序重新编号 [N]，并重排 source_index 的 key。
        例：正文依次出现 [2][3][1] → 重编号为 [1][2][3]；
        同时丢弃正文中未被引用的来源。返回 (new_answer_text, new_source_index)。
        """
        import re
        if not answer_text or not source_index:
            return answer_text, source_index
        order = []
        seen = set()
        for m in re.finditer(r'\[(\d+)\]', answer_text):
            n = m.group(1)
            if n not in seen:
                seen.add(n)
                order.append(n)
        if not order:
            return answer_text, {}
        remap = {old: str(i) for i, old in enumerate(order, 1)}

        def _repl(m):
            new = remap.get(m.group(1))
            return f"[{new}]" if new else m.group(0)

        new_text = re.sub(r'\[(\d+)\]', _repl, answer_text)
        new_si = {remap[k]: v for k, v in source_index.items() if k in remap}
        return new_text, new_si

    def answer_stream(self, question, model_id=None):
        """流式回答生成器，yield SSE 事件 dict 供前端实时渲染。
        事件类型：plan / thinking / answer / done / error
        """
        if model_id:
            self.model_id = model_id
        question = _to_simplified(question)  # 先繁体→简体，再进入检索与解析
        effective = self.use_api

        try:
            # ── 会话日志 ──
            from utils.session_logger import SessionLogger
            logger = SessionLogger(question)
            cfg = get_model_config(self.model_id)
            logger.log_header("(streaming)", cfg["label"])

            # ── 意图 + 检索 ──
            intent = self._classify_intent(question, use_api=effective)
            logger.log_header(intent, cfg["label"])  # 覆盖写入正确意图

            # LLM Tool Calling（仅 API 模式）
            tool_results = None
            if effective:
                tool_results = self._call_api_tool_selection(question, intent)
                if tool_results:
                    logger.log_tool_selection(True, [tr["name"] for tr in tool_results if tr.get("result")])
                else:
                    logger.log_tool_selection(False, [], "API 返回空或失败")

            plan = self.planner.plan(question, intent_override=intent, tool_results=tool_results, logger=logger)
            yield {"type": "plan", "intent": plan["intent"], "plan_log": plan.get("plan_log", {})}

            # ── Think 阶段 ──
            thinking = None
            if effective and TWO_PASS:
                yield {"type": "thinking_start"}
                think_full = []
                think_msgs = self._build_think_messages(question, plan["context"])
                for tt, text in self._call_api_stream(think_msgs, max_tokens=4096, model_id=self.model_id, max_reasoning_chars=6000):
                    # 同时捕获 content 与 reasoning_content（推理型模型会把分析放到 reasoning_content）
                    if tt in ("text", "reasoning") and not text.startswith("API错误") and not text.startswith("API调用失败"):
                        think_full.append(text)
                        yield {"type": "thinking", "content": text}
                thinking = "".join(think_full).strip()
                # 截断思考过程，避免占满上下文
                MAX_THINK_LEN = 1200
                if len(thinking) > MAX_THINK_LEN:
                    print(f"[Think] 思考过长 ({len(thinking)}字)，截断至 {MAX_THINK_LEN} 字")
                    thinking = thinking[:MAX_THINK_LEN] + "\n（思考过长已截断）"
                if thinking:
                    self.last_thinking = thinking
                    logger.log_thinking(thinking)
                yield {"type": "thinking_end"}

            # ── Answer 阶段 ──
            yield {"type": "answer_start"}

            def _stream_answer(msgs, max_tk):
                buf = []
                for tt, text in self._call_api_stream(msgs, max_tokens=max_tk, model_id=self.model_id):
                    if tt == "text":
                        buf.append(text)
                        yield {"type": "answer", "content": text}
                return buf

            full_answer = yield from _stream_answer(
                self._build_messages(question, plan["context"], thinking), 4096
            )

            # 空正文兜底：推理型模型可能把 max_tokens 额度全花在 reasoning_content 上，
            # 正文一个字都没生成就结束（表现为"思考一大段后无结果、前端空白"）。
            # 重试一次：更大额度 + 精简 prompt（不带 thinking，避免二次诱导长推理）。
            if not "".join(full_answer).strip():
                print("[Answer] 正文为空（推理耗尽额度），改用精简 prompt + 更大额度重试一次")
                retry_msgs = [
                    {"role": "system", "content": (
                        "你是一位专精于辑佚学的AI研究助手。请直接输出最终答案正文，"
                        "不要输出任何思考、分析或前置说明。答案采用三段式：[结论] → [考据] → [总结]。"
                        "全文使用简体中文。引用参考信息时直接使用其原始编号 [n]。"
                    )},
                    {"role": "user", "content": f"【参考信息】\n{plan['context'][:2000]}\n\n【用户问题】\n{question}"},
                ]
                full_answer = yield from _stream_answer(retry_msgs, 8192)

            # 重试后仍为空：给前端一个明确信号，避免空白/卡死
            if not "".join(full_answer).strip():
                msg = "（生成失败：模型未返回正文，请重试或更换模型）"
                full_answer = [msg]
                yield {"type": "answer", "content": msg}

            # 流式结束后写入日志
            raw = "".join(full_answer)
            cleaned = self.planner.postprocess(raw)
            logger.log_raw_api_response("stream_answer", raw)
            logger.log_answer(cleaned)
            logger.close()
            print(f"[Log] 完整日志已写入: {logger.get_path()}")

            # 过滤 source_index：只保留回答中实际引用的编号，避免"8条 vs 实际2条"的幻觉
            plan_log = plan.get("plan_log") or {}
            if plan_log.get("source_index"):
                plan_log["source_index"] = self._filter_source_index_by_citations(raw, plan_log["source_index"])

            yield {"type": "done", "plan_log": plan_log}

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
