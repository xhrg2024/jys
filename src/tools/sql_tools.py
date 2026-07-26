"""
4.4 SQL 查询工具：连接 MySQL 数据库 leishu_yongle，执行结构化查询。
支持 FULLTEXT 全文检索、文献元数据联合查询、标题层级搜索。
与 graph_tools / vector_tools 风格保持一致，供 planner 和 tool_registry 调用。

数据库结构摘要：
  documents      — 110,345 部文献（~17 部有完整元数据：类别/朝代/编者/体例）
  full_text_1    — 2,276,593 条正文片段（仅 8 部类书有数据，含 FULLTEXT 索引）
  titles         — 49,756 条层级标题 (h1~h4)
  authors        — 38 位编纂者
  document_author_links — 43 条文献-作者关联（含角色）
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（从项目根目录）
dotenv_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path, override=True)

import pymysql
from pymysql.cursors import DictCursor

# ── 简繁双向转换（opencc 自动逐字转换，非手动映射）──
try:
    from opencc import OpenCC
    _cc_s2t = OpenCC('s2t')  # 简体→繁体
    _cc_t2s = OpenCC('t2s')  # 繁体→简体
except ImportError:
    _cc_s2t = None
    _cc_t2s = None


def _search_variants(text):
    """输入一个搜索词，返回 [简体, 繁体] 两个变体（去重）。
    无论用户输入简体还是繁体，都能同时搜到数据库中的两种编码。
    """
    variants = [text]
    if _cc_s2t and _cc_t2s:
        trad = _cc_s2t.convert(text)
        simp = _cc_t2s.convert(text)
        if trad != text:
            variants.append(trad)
        if simp != text and simp not in variants:
            variants.append(simp)
    return variants


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
    """获取单例连接，带重连机制。连接失败时抛出异常让调用方感知。"""
    global _conn
    if _conn is None or not _conn.open:
        try:
            _conn = pymysql.connect(**SQL_CONFIG, connect_timeout=10)
        except Exception as e:
            print(f"[SQL] 连接失败: {e}")
            print(f"[SQL] 请检查: 1) MySQL 服务是否启动 2) .env 中 MYSQL_* 配置是否正确")
            raise
    else:
        try:
            _conn.ping(reconnect=True)
        except Exception:
            try:
                _conn = pymysql.connect(**SQL_CONFIG, connect_timeout=10)
            except Exception as e:
                print(f"[SQL] 重连失败: {e}")
                raise
    return _conn


def _fetchall(sql, params=None):
    """执行查询并返回所有结果（列表[字典]）"""
    try:
        conn = _get_conn()
        with conn.cursor(cursor=DictCursor) as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    except pymysql.err.OperationalError as e:
        print(f"[SQL] 数据库不可用: {e}")
        return []
    except Exception as e:
        print(f"[SQL] 查询异常: {e}")
        return []


def _fetchone(sql, params=None):
    """执行查询并返回第一条结果（字典）"""
    rows = _fetchall(sql, params)
    return rows[0] if rows else None


# ══════════════════════════════════════════════
# 文献元数据查询
# ══════════════════════════════════════════════

def browse_documents(category=None, dynasty=None, limit=30):
    """浏览文献列表，可按类别、朝代筛选。返回完整元数据。
    数据库中有 110,345 条文献记录，但仅 ~17 条有完整元数据。
    """
    sql = """
        SELECT d.doc_id, d.doc_title, d.doc_specific_category, d.doc_style,
               d.dynasty, d.compilation_time, d.completeness,
               GROUP_CONCAT(CONCAT(a.author_name, '(', dal.role, ')')
                            ORDER BY dal.da_id SEPARATOR '、') AS authors
        FROM documents d
        LEFT JOIN document_author_links dal ON d.doc_id = dal.doc_id
        LEFT JOIN authors a ON dal.author_id = a.author_id
        WHERE 1=1
    """
    params = []
    if category:
        sql += " AND d.doc_specific_category = %s"
        params.append(category)
    if dynasty:
        sql += " AND d.dynasty = %s"
        params.append(dynasty)
    sql += " GROUP BY d.doc_id ORDER BY d.doc_id LIMIT %s"
    params.append(limit)

    rows = _fetchall(sql, params)
    if not rows:
        filters = []
        if category:
            filters.append(f"类别={category}")
        if dynasty:
            filters.append(f"朝代={dynasty}")
        fstr = "、".join(filters) if filters else "全部"
        return f"未找到符合条件的文献（筛选条件：{fstr}）。"

    parts = []
    for r in rows:
        meta = []
        if r['dynasty']:
            meta.append(r['dynasty'])
        if r['doc_specific_category']:
            meta.append(r['doc_specific_category'])
        if r['doc_style']:
            meta.append(r['doc_style'])
        if r['compilation_time']:
            meta.append(r['compilation_time'])
        if r['completeness']:
            meta.append(r['completeness'])
        author_str = r['authors'] or '不详'
        meta_str = "；".join(meta) if meta else "元数据不详"
        parts.append(
            f"《{r['doc_title'].strip('《》')}》（{meta_str}）\n  编者：{author_str}"
        )
    return "\n".join(parts)


def query_document_by_title(title, limit=10):
    """按文献标题模糊查询。同时用简繁体搜索，合并去重。"""
    def _do(t):
        return _fetchall(
            "SELECT doc_id, doc_title, doc_specific_category, doc_style, "
            "       dynasty, compilation_time, completeness "
            "FROM documents WHERE doc_title LIKE %s LIMIT %s",
            (f"%{t}%", limit)
        )

    variants = _search_variants(title)
    merged = {}
    for v in variants:
        for r in _do(v):
            if r['doc_id'] not in merged:
                merged[r['doc_id']] = r
    rows = list(merged.values())[:limit]

    if not rows:
        return f"未找到标题包含「{title}」的文献。"
    parts = []
    for r in rows:
        parts.append(
            f"《{r['doc_title'].strip('《》')}》（"
            f"类别：{r['doc_specific_category'] or '未知'}，"
            f"朝代：{r['dynasty'] or '未知'}，"
            f"完整性：{r['completeness'] or '未知'}）"
        )
    return "\n".join(parts)


def query_document_detail(title):
    """查询文献完整信息：元数据 + 编者列表 + 标题结构。
    优先返回有元数据（类别/朝代）的文献，其次为无元数据的匹配。
    同时用简体和繁体各搜一次，合并去重，确保覆盖数据库中的混合编码。
    """
    clean = title.strip('《》').replace(' ', '')
    prefix = clean[:6] if len(clean) >= 3 else clean

    def _do_query(search_term):
        return _fetchall(
            """SELECT d.doc_id, d.doc_title, d.doc_specific_category, d.doc_style,
                      d.dynasty, d.compilation_time, d.completeness, d.doc_theme,
                      GROUP_CONCAT(CONCAT(a.author_name, '(', dal.role, ')')
                                   ORDER BY dal.da_id SEPARATOR '、') AS authors,
                      CASE WHEN d.doc_specific_category IS NOT NULL OR d.dynasty IS NOT NULL
                           THEN 0 ELSE 1 END AS sort_priority
               FROM documents d
               LEFT JOIN document_author_links dal ON d.doc_id = dal.doc_id
               LEFT JOIN authors a ON dal.author_id = a.author_id
               WHERE d.doc_title LIKE %s
               GROUP BY d.doc_id
               ORDER BY sort_priority, d.doc_id
               LIMIT 5""",
            (f"%{search_term}%",)
        )

    # 同时用简体和繁体搜索，合并去重
    variants = _search_variants(prefix)
    merged = {}
    for v in variants:
        for r in _do_query(v):
            if r['doc_id'] not in merged:
                merged[r['doc_id']] = r

    # 按 sort_priority 排序（有元数据的优先），取前 5
    doc_rows = sorted(merged.values(), key=lambda r: (r['sort_priority'], r['doc_id']))[:5]

    if not doc_rows:
        return f"未找到标题包含「{title}」的文献。"

    parts = []
    for d in doc_rows:
        meta_parts = []
        if d['dynasty']:
            meta_parts.append(f"朝代：{d['dynasty']}")
        if d['doc_specific_category']:
            meta_parts.append(f"类别：{d['doc_specific_category']}")
        if d['doc_style']:
            meta_parts.append(f"体例：{d['doc_style']}")
        if d['compilation_time']:
            meta_parts.append(f"编纂时间：{d['compilation_time']}")
        if d['completeness']:
            meta_parts.append(f"完整性：{d['completeness']}")
        if d['doc_theme']:
            meta_parts.append(f"主题：{d['doc_theme']}")

        authors_str = d['authors'] or '不详'

        # 查该文献的顶级标题（h1），了解卷次结构
        title_rows = _fetchall(
            """SELECT title_name FROM titles
               WHERE doc_id = %s AND title_level = 'h1'
               ORDER BY title_order LIMIT 5""",
            (d['doc_id'],)
        )
        title_preview = "、".join(r['title_name'] for r in title_rows) if title_rows else "无标题信息"

        # 查全文数据量
        ft_count = _fetchone(
            "SELECT COUNT(*) AS cnt FROM full_text_1 WHERE doc_id = %s",
            (d['doc_id'],)
        )
        ft_info = f"全文片段：{ft_count['cnt']}条" if ft_count and ft_count['cnt'] > 0 else "无全文数据"

        parts.append(
            f"《{d['doc_title'].strip('《》')}》\n"
            f"  {'；'.join(meta_parts)}\n"
            f"  编者：{authors_str}\n"
            f"  {ft_info}\n"
            f"  卷次示例：{title_preview}"
        )
    return "\n\n".join(parts)


# ══════════════════════════════════════════════
# 作者查询
# ══════════════════════════════════════════════

def query_author_by_name(name):
    """按作者姓名模糊查询，返回其参与编纂的文献"""
    rows = _fetchall(
        """SELECT a.author_name, a.author_org,
                  GROUP_CONCAT(CONCAT(d.doc_title, '(', dal.role, ')')
                               SEPARATOR '、') AS works
           FROM authors a
           LEFT JOIN document_author_links dal ON a.author_id = dal.author_id
           LEFT JOIN documents d ON dal.doc_id = d.doc_id
           WHERE a.author_name LIKE %s
           GROUP BY a.author_id""",
        (f"%{name}%",)
    )
    if not rows:
        return f"未找到姓名包含「{name}」的作者。"
    parts = []
    for r in rows:
        org = f"（{r['author_org']}）" if r['author_org'] else ""
        works = r['works'] or '无文献记录'
        parts.append(f"{r['author_name']}{org}\n  参与文献：{works}")
    return "\n".join(parts)


# ══════════════════════════════════════════════
# 全文检索（核心 — 使用 FULLTEXT 索引）
# ══════════════════════════════════════════════

def search_full_text(keyword, limit=5, mode="NATURAL"):
    """全文关键词搜索，使用 MySQL FULLTEXT ngram 索引。
    mode: NATURAL (自然语言模式) | BOOLEAN (布尔模式，支持 + - ~ 操作符)
    返回带文献元数据的匹配片段，按相关度排序。

    注意：数据库仅 8 部主要类书有全文数据，且"辑佚"一词在古文献原文中不出现。
    辑佚学相关查询建议改用：校勘、训诂、考证、辨伪、版本、目录、类书 等古文献用语。
    """
    if mode == "BOOLEAN":
        # 布尔模式：自动为每个词添加 + 前缀（要求必须出现）
        terms = keyword.split()
        boolean_query = " ".join(f"+{t}" for t in terms if len(t) >= 2)
        if not boolean_query:
            boolean_query = f"+{keyword}"
        sql = """
            SELECT ft.full_text_id, ft.full_text, ft.text_type, ft.title_level,
                   MATCH(ft.full_text) AGAINST(%s IN BOOLEAN MODE) AS relevance,
                   d.doc_id, d.doc_title, d.dynasty, d.doc_specific_category
            FROM full_text_1 ft
            JOIN documents d ON ft.doc_id = d.doc_id
            WHERE MATCH(ft.full_text) AGAINST(%s IN BOOLEAN MODE)
            ORDER BY relevance DESC
            LIMIT %s
        """
        rows = _fetchall(sql, (boolean_query, boolean_query, limit))
    else:
        sql = """
            SELECT ft.full_text_id, ft.full_text, ft.text_type, ft.title_level,
                   MATCH(ft.full_text) AGAINST(%s) AS relevance,
                   d.doc_id, d.doc_title, d.dynasty, d.doc_specific_category
            FROM full_text_1 ft
            JOIN documents d ON ft.doc_id = d.doc_id
            WHERE MATCH(ft.full_text) AGAINST(%s)
            ORDER BY relevance DESC
            LIMIT %s
        """
        rows = _fetchall(sql, (keyword, keyword, limit))

    if not rows:
        # FULLTEXT 无结果时，降级为 LIKE 模糊搜索（某些罕见词 ngram 可能未收录）
        rows = _fetchall(
            """SELECT ft.full_text_id, ft.full_text, ft.text_type, ft.title_level,
                      999 AS relevance,
                      d.doc_id, d.doc_title, d.dynasty, d.doc_specific_category
               FROM full_text_1 ft
               JOIN documents d ON ft.doc_id = d.doc_id
               WHERE ft.full_text LIKE %s
               ORDER BY ft.full_text_id
               LIMIT %s""",
            (f"%{keyword}%", limit)
        )
        if not rows:
            return f"全文搜索未找到包含「{keyword}」的内容。\n提示：古籍原文中可能使用不同的术语表达此概念，可尝试同义词搜索。"

    parts = []
    for r in rows:
        text = r['full_text'][:120].replace('\n', ' ').replace('\r', ' ')
        doc_title = r['doc_title'].strip('《》') if r['doc_title'] else '未知文献'
        dynasty = f"〔{r['dynasty']}〕" if r['dynasty'] else ''
        category = f"（{r['doc_specific_category']}）" if r['doc_specific_category'] else ''
        rel = f"相关度:{r.get('relevance', 0):.1f}" if r.get('relevance') and r.get('relevance') != 999 else ""
        parts.append(
            f"【《{doc_title}》{dynasty}{category}】{rel}\n"
            f"  [{r['text_type'] or '正文'}] ……{text}……"
        )

    if mode == "BOOLEAN":
        return "全文搜索（布尔模式）：\n" + "\n\n".join(parts)
    return "全文搜索结果：\n" + "\n\n".join(parts)


def query_full_text_by_keyword(keyword, limit=10):
    """兼容旧接口：全文关键词搜索"""
    return search_full_text(keyword, limit=limit, mode="NATURAL")


# ══════════════════════════════════════════════
# 标题层级检索
# ══════════════════════════════════════════════

def search_titles(keyword, limit=15):
    """在层级标题中搜索关键词，了解类书的章节结构。
    标题层级：h1=卷次, h2=部类, h3=小类, h4=条目
    """
    rows = _fetchall(
        """SELECT t.title_name, t.title_level, t.title_order,
                  d.doc_title, d.dynasty
           FROM titles t
           JOIN documents d ON t.doc_id = d.doc_id
           WHERE t.title_name LIKE %s
           ORDER BY d.doc_id, t.title_order
           LIMIT %s""",
        (f"%{keyword}%", limit)
    )
    if not rows:
        # 尝试 FULLTEXT（如果 titles 表有 FULLTEXT 索引）
        rows = _fetchall(
            """SELECT t.title_name, t.title_level, t.title_order,
                      d.doc_title, d.dynasty
               FROM titles t
               JOIN documents d ON t.doc_id = d.doc_id
               WHERE MATCH(t.title_name) AGAINST(%s)
               ORDER BY d.doc_id, t.title_order
               LIMIT %s""",
            (keyword, limit)
        )
    if not rows:
        return f"标题中未找到包含「{keyword}」的内容。"

    level_cn = {"h1": "卷次", "h2": "部类", "h3": "小类", "h4": "条目"}
    parts = []
    for r in rows:
        lvl = level_cn.get(r['title_level'], r['title_level'])
        dynasty = f"〔{r['dynasty']}〕" if r['dynasty'] else ''
        doc = r['doc_title'].strip('《》') if r['doc_title'] else '未知文献'
        parts.append(f"【{lvl}】{r['title_name']} ——《{doc}》{dynasty}")
    return "标题搜索结果：\n" + "\n".join(parts)


# ══════════════════════════════════════════════
# 兼容旧接口（保持 planner 调用不报错）
# ══════════════════════════════════════════════

def query_document_with_authors(title):
    """联合查询：文献信息 + 所有作者（兼容旧接口，委托给 query_document_detail）"""
    return query_document_detail(title)


def query_documents_by_category(category):
    """按类书类别查询（兼容旧接口，委托给 browse_documents）"""
    return browse_documents(category=category, limit=30)


def query_document_by_dynasty(dynasty):
    """按朝代查询文献（兼容旧接口，委托给 browse_documents）"""
    return browse_documents(dynasty=dynasty, limit=30)


def query_full_text_by_doc(doc_title, keyword=None, limit=30):
    """查某篇文献的全文段落，可选关键词过滤。
    同时用简体和繁体各搜一次，合并去重。
    """

    def _do_query(title_term):
        if keyword:
            return _fetchall(
                """SELECT f.full_text_id, f.full_text, f.full_text_order, f.text_type, f.title_level
                   FROM full_text_1 f
                   JOIN documents d ON f.doc_id = d.doc_id
                   WHERE d.doc_title LIKE %s AND f.full_text LIKE %s
                   ORDER BY f.full_text_order LIMIT %s""",
                (f"%{title_term}%", f"%{keyword}%", limit)
            )
        else:
            return _fetchall(
                """SELECT f.full_text_id, f.full_text, f.full_text_order, f.text_type, f.title_level
                   FROM full_text_1 f
                   JOIN documents d ON f.doc_id = d.doc_id
                   WHERE d.doc_title LIKE %s
                   ORDER BY f.full_text_order LIMIT %s""",
                (f"%{title_term}%", limit)
            )

    # 同时用简体和繁体搜索，合并去重
    variants = _search_variants(doc_title)
    merged = {}
    for v in variants:
        for r in _do_query(v):
            if r['full_text_id'] not in merged:
                merged[r['full_text_id']] = r

    # 按 full_text_order 排序，取前 limit 条
    rows = sorted(merged.values(), key=lambda r: r['full_text_order'])[:limit]

    if not rows:
        kw = f"且关键词「{keyword}」" if keyword else ""
        return f"未找到文献「{doc_title}」{kw}的全文内容。"
    parts = []
    for r in rows:
        text = r['full_text'][:120].replace('\n', ' ').replace('\r', ' ')
        parts.append(f"[第{r['full_text_order']}段]（{r['text_type'] or '正文'}）{text}")
    return "\n".join(parts)


def search_document(title, text_limit=8):
    """一站式文献搜索：正文内容预览 + 元数据。
    内容优先，元数据补充，供 planner 直接调用。
    """
    detail = query_document_detail(title)
    if "未找到" in detail:
        return detail

    # 先获取正文内容
    content = query_full_text_by_doc(title, limit=text_limit)
    has_content = content and "未找到" not in content

    if has_content:
        # 提取元数据的第一行（书名行）做摘要头
        first_line = detail.split('\n')[0] if detail else ''
        return f"{first_line}\n\n── 正文预览 ──\n{content}\n\n── 文献信息 ──\n{detail}"
    return detail


def query_by_author_org(org):
    """按机构查询作者"""
    rows = _fetchall(
        "SELECT author_name, author_org FROM authors WHERE author_org LIKE %s",
        (f"%{org}%",)
    )
    if not rows:
        return f"未找到机构包含「{org}」的作者。"
    parts = [f"{r['author_name']}（{r['author_org']}）" for r in rows]
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
    tables = ["documents", "authors", "document_author_links", "full_text_1",
              "titles", "pages", "historyrecords"]
    for tbl in tables:
        r = _fetchone(f"SELECT COUNT(*) AS cnt FROM {tbl}")
        stats[tbl] = r['cnt'] if r else 0

    # 额外统计
    docs_with_ft = _fetchone("SELECT COUNT(DISTINCT doc_id) AS cnt FROM full_text_1")
    stats['documents_with_full_text'] = docs_with_ft['cnt'] if docs_with_ft else 0

    docs_with_meta = _fetchone(
        "SELECT COUNT(*) AS cnt FROM documents WHERE doc_specific_category IS NOT NULL OR dynasty IS NOT NULL"
    )
    stats['documents_with_metadata'] = docs_with_meta['cnt'] if docs_with_meta else 0

    return stats


def close():
    """关闭数据库连接"""
    global _conn
    if _conn and _conn.open:
        _conn.close()
        _conn = None
