"""
4.3 工具调用机制：定义 tool schemas，调度执行，结果回传。
"""
import json

from . import graph_tools, vector_tools, sql_tools

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "kg_find_entities",
            "description": "通过实体名称在辑佚史知识图谱中查找实体属性信息。适用于问句中提到了明确的人名、书名、方法名、时期名等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "要查找的实体名称，如“马国翰”、“玉函山房辑佚书”"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kg_get_entity_relations",
            "description": "查询某个实体在知识图谱中的所有关联关系和相邻实体。适用于需要了解实体的学术传承、版本源流、方法论关联等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string", "description": "实体的唯一ID"}
                },
                "required": ["entity_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kg_find_relation_between",
            "description": "查询两个实体之间的路径关系，返回最短关联路径。",
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
            "description": "列出指定类型的所有实体。类型包括：Compilation（辑本）、Person/Scholar（辑佚者）、Time（历史时期）、Method（研究方法）、Academic（学术流派）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "实体类型标签"}
                },
                "required": ["label"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "vector_search",
            "description": "语义搜索知识图谱中的实体。当用户问题用词模糊、未命中精确实体名称时使用。",
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
    {
        "type": "function",
        "function": {
            "name": "sql_find_document",
            "description": "在 MySQL 类书数据库中按标题模糊搜索文献信息。适用于查询类书、辑本的元数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "文献标题关键词，如“永乐大典”、“玉函山房”"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sql_find_author",
            "description": "在 MySQL 类书数据库中按姓名搜索作者/编纂者信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "作者姓名关键词"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sql_document_detail",
            "description": "查询文献的详细信息，包括作者、编纂者角色等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "文献标题关键词"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sql_search_text",
            "description": "在类书全文内容中搜索关键词，返回匹配的文本片段及出处。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "要搜索的关键词"},
                    "limit": {"type": "integer", "description": "返回结果数量，默认10"}
                },
                "required": ["keyword"]
            }
        }
    }
]

# 工具名 → 执行函数
DISPATCH = {
    "kg_find_entities": lambda args: graph_tools.query_entity_by_name(args["name"]),
    "kg_get_entity_relations": lambda args: graph_tools.query_entity_relations(args["entity_id"]),
    "kg_find_relation_between": lambda args: graph_tools.query_relation_between(args["entity_a"], args["entity_b"]),
    "kg_list_by_type": lambda args: graph_tools.query_by_label(args["label"]),
    "vector_search": lambda args: vector_tools.vector_search(args.get("query", ""), args.get("k", 5)),
    "sql_find_document": lambda args: sql_tools.query_document_by_title(args["title"]),
    "sql_find_author": lambda args: sql_tools.query_author_by_name(args["name"]),
    "sql_document_detail": lambda args: sql_tools.query_document_with_authors(args["title"]),
    "sql_search_text": lambda args: sql_tools.query_full_text_by_keyword(args["keyword"], args.get("limit", 10)),
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
    args = json.loads(function_call.get("arguments", "{}")) if isinstance(function_call.get("arguments"), str) else function_call.get("arguments", {})
    result = execute(name, args)
    return name, result
