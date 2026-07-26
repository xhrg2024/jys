"""
4.3 工具调用机制：定义 tool schemas，调度执行，结果回传。
供 generator 的 tool-calling LLM 调用使用。
"""
import json

from . import graph_tools, vector_tools, sql_tools

# ══════════════════════════════════════════════
# 工具定义（OpenAI function calling 格式）
# ══════════════════════════════════════════════

TOOL_SCHEMAS = [
    # ── 知识图谱工具 ──
    {
        "type": "function",
        "function": {
            "name": "kg_explore_entity",
            "description": (
                "【推荐优先使用】深度探索一个实体：返回实体完整属性 + 全部关系网络 + "
                "关键关联实体的属性。一次调用完成多跳遍历，信息量远超 kg_find_entities。"
                "适用于需要全面了解某个人物、书籍、方法、时期的场景。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "要探索的实体名称"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kg_explore_relation",
            "description": (
                "【推荐优先使用】深度探索两个实体之间的关系：自动完成以下全部步骤——"
                "分别查 A 和 B 的完整属性、各自的关系网络、关联实体属性、以及两者间的最短路径。"
                "一次调用替代 kg_find_entities×2 + kg_get_entity_relations×2 + kg_find_relation_between，"
                "且包含多跳扩展。适用于所有关系类、比较类问题。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_a": {"type": "string", "description": "第一个实体名称"},
                    "entity_b": {"type": "string", "description": "第二个实体名称"}
                },
                "required": ["entity_a", "entity_b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kg_find_entities",
            "description": (
                "通过实体名称在辑佚史知识图谱中查找实体属性信息（人名、书名、方法名、时期名等）。"
                "【重要】对于涉及多个实体的问题（如关系、比较），应对每个实体分别调用此工具，"
                "不要只查关系而不查各自属性。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "要查找的实体名称，如'马国翰'、'玉函山房辑佚书'、'清代'"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kg_get_entity_relations",
            "description": (
                "查询某个实体在知识图谱中的所有关联关系和相邻实体。"
                "适用于需要了解实体的学术传承、版本源流、方法论关联等。"
                "需要先通过 kg_find_entities 获取 entity_id。"
                "建议同时调用 kg_find_entities 获取实体自身属性，本工具只返回关系不返回属性。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "实体的唯一ID，从 kg_find_entities 返回结果中提取"
                    }
                },
                "required": ["entity_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kg_find_relation_between",
            "description": (
                "查询两个实体之间的最短关联路径。仅返回路径，不包含实体的完整属性。"
                "适用于'X和Y有什么关系'、'X如何影响Y'等问题。"
                "【重要】必须同时调用 kg_find_entities 分别查询 entity_a 和 entity_b 的完整属性，"
                "否则会缺少各实体自身的背景信息。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_a": {"type": "string", "description": "第一个实体名称"},
                    "entity_b": {"type": "string", "description": "第二个实体名称"}
                },
                "required": ["entity_a", "entity_b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kg_list_by_type",
            "description": (
                "列出指定类型的所有实体。"
                "类型包括：Compilation（辑本）、Scholar（辑佚者）、Time（时期）、"
                "Method（方法）、Academic（学派）"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "实体类型标签，如'Method'、'Scholar'、'Compilation'"
                    }
                },
                "required": ["label"]
            }
        }
    },

    # ── 向量语义检索 ──
    {
        "type": "function",
        "function": {
            "name": "vector_search",
            "description": (
                "语义搜索知识图谱中的实体。当用户问题用词模糊、"
                "未命中精确实体名称时使用。也可用于兜底搜索。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要语义搜索的文本"},
                    "k": {"type": "integer", "description": "返回结果数量，默认5"}
                },
                "required": ["query"]
            }
        }
    },

    # ── SQL 类书数据库工具 ──
    {
        "type": "function",
        "function": {
            "name": "search_document",
            "description": (
                "一站式文献搜索：返回文献完整元数据（朝代、类别、体例、编纂者、卷次结构）"
                "+ 正文内容预览。支持简繁体自动转换、部分书名匹配。"
                "适用于'介绍XX书'、'XX书写了什么'等查询。"
                "【重要】涉及多部文献时应对每部分别调用；涉及编者时应同时调用 search_author。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "文献标题或关键词，如'永乐大典'、'太平御览'、'艺文'"
                    },
                    "text_limit": {
                        "type": "integer",
                        "description": "返回的正文片段数量，默认8"
                    }
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_author",
            "description": (
                "在类书数据库中按姓名搜索作者/编纂者信息，返回其参与编纂的所有文献及角色。"
                "适用于'XX是谁'、'XX编过什么书'等查询。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "作者姓名关键词，如'解缙'、'欧阳询'、'李昉'"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_full_text",
            "description": (
                "在类书全文内容中搜索关键词，返回匹配的文本片段及出处文献。"
                "适用于古籍术语检索。注意：古籍中常用'校勘''训诂''考证'等术语，"
                "而非现代术语'辑佚'。搜索时请使用古文献中实际出现的词汇。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "要搜索的关键词，建议使用古文献中实际出现的术语"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量，默认5（建议不超过5）"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["NATURAL", "BOOLEAN"],
                        "description": "搜索模式：NATURAL=自然语言，BOOLEAN=布尔模式（更精确）"
                    }
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_titles",
            "description": (
                "在类书的层级标题中搜索关键词，了解文献的章节结构。"
                "标题层级：h1=卷次, h2=部类, h3=小类, h4=条目。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "要在标题中搜索的关键词"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量，默认15"
                    }
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browse_documents",
            "description": (
                "按类别和/或朝代浏览文献列表。"
                "类别：综合性类书、专书性类书；朝代用单字：明、宋、唐、清。"
                "适用于'明代有哪些类书'、'综合性类书有哪些'等查询。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "文献类别，如'综合性类书'、'专书性类书'"
                    },
                    "dynasty": {
                        "type": "string",
                        "description": "朝代单字，如'明'、'宋'、'唐'、'清'"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量，默认30"
                    }
                },
                "required": []
            }
        }
    },
]

# ══════════════════════════════════════════════
# 工具分发
# ══════════════════════════════════════════════

DISPATCH = {
    "kg_explore_entity":        lambda args: graph_tools.explore_entity(args["name"]),
    "kg_explore_relation":      lambda args: graph_tools.explore_relation(args["entity_a"], args["entity_b"]),
    "kg_find_entities":         lambda args: graph_tools.query_entity_by_name(args["name"]),
    "kg_get_entity_relations":  lambda args: graph_tools.query_entity_relations(args["entity_id"]),
    "kg_find_relation_between": lambda args: graph_tools.query_relation_between(args["entity_a"], args["entity_b"]),
    "kg_list_by_type":          lambda args: graph_tools.query_by_label(args["label"]),
    "vector_search":            lambda args: vector_tools.vector_search(args.get("query", ""), args.get("k", 5)),
    "search_document":          lambda args: sql_tools.search_document(args["title"], args.get("text_limit", 8)),
    "search_author":            lambda args: sql_tools.query_author_by_name(args["name"]),
    "search_full_text":         lambda args: sql_tools.search_full_text(args["keyword"], args.get("limit", 5), args.get("mode", "NATURAL")),
    "search_titles":            lambda args: sql_tools.search_titles(args["keyword"], args.get("limit", 8)),
    "browse_documents":         lambda args: sql_tools.browse_documents(category=args.get("category"), dynasty=args.get("dynasty"), limit=args.get("limit", 30)),
}


def get_schemas_text():
    """生成可注入 system prompt 的工具描述文本"""
    lines = ["可用工具："]
    for t in TOOL_SCHEMAS:
        f = t["function"]
        lines.append(f"- {f['name']}: {f['description']}")
    return "\n".join(lines)


def execute(function_name, arguments):
    """执行指定工具，返回结果文本。"""
    if function_name not in DISPATCH:
        return f"未知工具: {function_name}"
    try:
        return DISPATCH[function_name](arguments)
    except Exception as e:
        return f"工具执行出错: {e}"


def execute_from_model_call(function_call):
    """从模型的 function_call 输出执行工具。"""
    if isinstance(function_call, str):
        function_call = json.loads(function_call)
    name = function_call["name"]
    args = function_call.get("arguments", {})
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {}
    result = execute(name, args)
    return name, result


def execute_tool_calls(tool_calls):
    """批量执行多个工具调用，返回结果列表。
    tool_calls: OpenAI 格式的 tool_calls 列表，
        每项为 {"id": str, "function": {"name": str, "arguments": dict|str}}
    Returns: [{"name": str, "result": str}, ...]
    """
    results = []
    for tc in tool_calls:
        func = tc.get("function", tc) if isinstance(tc, dict) else {}
        name = func.get("name", "")
        args = func.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        result = execute(name, args)
        results.append({"name": name, "result": result})
        print(f"  🔧 {name}: {result[:80]}...")
    return results
