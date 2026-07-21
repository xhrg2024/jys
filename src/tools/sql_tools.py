"""
4.4 SQL 查询工具：连接 MySQL 数据库 leishu_yongle，执行结构化查询。
与 graph_tools / vector_tools 风格保持一致，供 planner 和 tool_registry 调用。
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（从项目根目录）
dotenv_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path)

import pymysql
from pymysql.cursors import DictCursor

# ── MySQL 连接配置（从环境变量读取，避免密码硬编码） ──
SQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DATABASE", "leishu_yongle"),
    "charset": "utf8mb4",
}

_conn = None


def _get_conn():
    """获取单例连接，带重连机制"""
    global _conn
    try:
        if _conn is None or not _conn.open:
            _conn = pymysql.connect(**SQL_CONFIG, connect_timeout=10)
        else:
            # 测试连接是否有效
            _conn.ping(reconnect=True)
    except Exception:
        _conn = pymysql.connect(**SQL_CONFIG, connect_timeout=10)
    return _conn


def _fetchall(sql, params=None):
    """执行查询并返回所有结果（列表[字典]）"""
    try:
        conn = _get_conn()
        with conn.cursor(cursor=DictCursor) as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    except Exception as e:
        print(f"[SQL] 查询失败: {e}")
        global _conn
        _conn = None  # 重置连接
        return []


def _fetchone(sql, params=None):
    """执行查询并返回第一条结果（字典）"""
    rows = _fetchall(sql, params)
    return rows[0] if rows else None


# ══════════════════════════════════════════════
# 业务查询函数
# ══════════════════════════════════════════════

def query_document_by_title(title, limit=10):
    """按文献标题模糊查询"""
    rows = _fetchall(
        "SELECT doc_id, doc_title, doc_specific_category, doc_style, "
        "       dynasty, compilation_time, completeness, source "
        "FROM documents WHERE doc_title LIKE %s LIMIT %s",
        (f"%{title}%", limit)
    )
    if not rows:
        return f"未找到标题包含“{title}”的文献。"
    parts = []
    for r in rows:
        parts.append(
            f"{r['doc_title']}（类别：{r['doc_specific_category'] or '未知'}，"
            f"朝代：{r['dynasty'] or '未知'}，"
            f"完整性：{r['completeness'] or '未知'}）"
        )
    return "；\n".join(parts)


def query_author_by_name(name):
    """按作者姓名模糊查询"""
    rows = _fetchall(
        "SELECT author_id, author_name, author_org "
        "FROM authors WHERE author_name LIKE %s",
        (f"%{name}%",)
    )
    if not rows:
        return f"未找到姓名包含“{name}”的作者。"
    parts = []
    for r in rows:
        org = r['author_org'] or '不详'
        parts.append(f"{r['author_name']}（机构：{org}）")
    return "；\n".join(parts)


def query_document_with_authors(title):
    """联合查询：文献信息 + 所有作者"""
    rows = _fetchall(
        "SELECT d.doc_id, d.doc_title, d.doc_specific_category, d.doc_style, "
        "       d.dynasty, d.compilation_time, d.completeness, "
        "       a.author_name, a.author_org, dal.role "
        "FROM documents d "
        "LEFT JOIN document_author_links dal ON d.doc_id = dal.doc_id "
        "LEFT JOIN authors a ON dal.author_id = a.author_id "
        "WHERE d.doc_title LIKE %s "
        "ORDER BY d.doc_id, dal.da_id",
        (f"%{title}%",)
    )
    if not rows:
        return f"未找到标题包含“{title}”的文献。"
    # 按 doc_id 分组
    doc_map = {}
    for r in rows:
        did = r['doc_id']
        if did not in doc_map:
            doc_map[did] = {
                "title": r['doc_title'],
                "category": r['doc_specific_category'] or '未知',
                "style": r['doc_style'] or '未知',
                "dynasty": r['dynasty'] or '未知',
                "compilation_time": r['compilation_time'] or '未知',
                "completeness": r['completeness'] or '未知',
                "authors": [],
            }
        if r['author_name']:
            role = r['role'] or '参与'
            doc_map[did]["authors"].append(f"{r['author_name']}（{role}）")
    parts = []
    for did, info in doc_map.items():
        authors_str = "、".join(info["authors"]) if info["authors"] else "不详"
        parts.append(
            f"《{info['title']}》（类别：{info['category']}，"
            f"体例：{info['style']}，朝代：{info['dynasty']}，"
            f"编纂时间：{info['compilation_time']}，"
            f"完整性：{info['completeness']}）\n"
            f"  作者：{authors_str}"
        )
    return "\n".join(parts)


def query_full_text_by_keyword(keyword, limit=20):
    """全文关键词搜索：在 full_text_1 中匹配文本片段，返回文档标题 + 上下文"""
    rows = _fetchall(
        "SELECT f.full_text_id, f.full_text, f.doc_id, "
        "       d.doc_title, f.text_type "
        "FROM full_text_1 f "
        "LEFT JOIN documents d ON f.doc_id = d.doc_id "
        "WHERE f.full_text LIKE %s "
        "LIMIT %s",
        (f"%{keyword}%", limit)
    )
    if not rows:
        return f"未找到包含“{keyword}”的文本。"
    parts = []
    seen = set()
    for r in rows:
        key = (r['doc_id'], r['full_text'][:50])
        if key in seen:
            continue
        seen.add(key)
        text_preview = r['full_text'][:80].replace('\n', ' ')
        parts.append(
            f"【{r['doc_title'] or '未知文献'}】（类型：{r['text_type'] or '正文'}）"
            f"\n  ……{text_preview}……"
        )
        if len(parts) >= 10:
            break
    return "\n\n".join(parts)


def query_documents_by_category(category):
    """按类书类别查询"""
    rows = _fetchall(
        "SELECT doc_id, doc_title, dynasty, compilation_time "
        "FROM documents WHERE doc_specific_category = %s "
        "LIMIT 30",
        (category,)
    )
    if not rows:
        return f"未找到类别为“{category}”的文献。"
    parts = []
    for r in rows:
        parts.append(
            f"{r['doc_title']}（朝代：{r['dynasty'] or '未知'}，"
            f"编纂时间：{r['compilation_time'] or '未知'}）"
        )
    return "；\n".join(parts)


def query_by_author_org(org):
    """按机构查询作者"""
    rows = _fetchall(
        "SELECT author_name, author_org FROM authors WHERE author_org LIKE %s",
        (f"%{org}%",)
    )
    if not rows:
        return f"未找到机构包含“{org}”的作者。"
    parts = [f"{r['author_name']}（{r['author_org']}）" for r in rows]
    return "；\n".join(parts)


def query_document_by_dynasty(dynasty):
    """按朝代查询文献"""
    rows = _fetchall(
        "SELECT doc_id, doc_title, doc_specific_category, compilation_time "
        "FROM documents WHERE dynasty = %s LIMIT 30",
        (dynasty,)
    )
    if not rows:
        return f"未找到朝代为“{dynasty}”的文献。"
    parts = []
    for r in rows:
        parts.append(
            f"{r['doc_title']}（类别：{r['doc_specific_category'] or '未知'}，"
            f"编纂时间：{r['compilation_time'] or '未知'}）"
        )
    return "；\n".join(parts)


def query_full_text_by_doc(doc_title, keyword=None, limit=30):
    """查某篇文献的全文段落，可选关键词过滤"""
    if keyword:
        rows = _fetchall(
            "SELECT f.full_text_id, f.full_text, f.full_text_order, f.text_type, f.title_level "
            "FROM full_text_1 f "
            "JOIN documents d ON f.doc_id = d.doc_id "
            "WHERE d.doc_title LIKE %s AND f.full_text LIKE %s "
            "ORDER BY f.full_text_order LIMIT %s",
            (f"%{doc_title}%", f"%{keyword}%", limit)
        )
    else:
        rows = _fetchall(
            "SELECT f.full_text_id, f.full_text, f.full_text_order, f.text_type, f.title_level "
            "FROM full_text_1 f "
            "JOIN documents d ON f.doc_id = d.doc_id "
            "WHERE d.doc_title LIKE %s "
            "ORDER BY f.full_text_order LIMIT %s",
            (f"%{doc_title}%", limit)
        )
    if not rows:
        kw = f"且关键词“{keyword}”" if keyword else ""
        return f"未找到文献“{doc_title}”{kw}的全文内容。"
    parts = []
    for r in rows:
        text = r['full_text'][:120].replace('\n', ' ')
        parts.append(
            f"[第{r['full_text_order']}段]（{r['text_type'] or '正文'}）{text}"
        )
    return "\n".join(parts)


def execute_raw_sql(sql, limit=50):
    """通用 SQL 执行（供调试 / 高级查询使用）"""
    sql_upper = sql.strip().upper()
    if sql_upper.startswith("SELECT") or sql_upper.startswith("SHOW") or sql_upper.startswith("DESCRIBE"):
        rows = _fetchall(sql)
        if not rows:
            return "查询无结果。"
        parts = []
        for r in rows[:limit]:
            parts.append(str(r))
        return "\n".join(parts)
    else:
        return "仅支持 SELECT / SHOW / DESCRIBE 查询。"


def get_stats():
    """获取数据库统计信息"""
    stats = {}
    tables = ["documents", "authors", "document_author_links", "full_text_1", "historyrecords"]
    for tbl in tables:
        r = _fetchone(f"SELECT COUNT(*) AS cnt FROM {tbl}")
        stats[tbl] = r['cnt'] if r else 0
    return stats


def close():
    """关闭数据库连接"""
    global _conn
    if _conn and _conn.open:
        _conn.close()
        _conn = None