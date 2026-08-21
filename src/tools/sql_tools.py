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
import threading
import re
from collections import OrderedDict
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
    # 读写超时（秒）：FULLTEXT 未命中时降级 LIKE '%kw%' 全表扫 227 万行这类慢查询，
    # 若无超时会无限期占用连接、串行拖垮所有 SQL 请求。超时由 pymysql 抛异常，交给 _fetchall 转 DatabaseError。
    "read_timeout": 30,
    "write_timeout": 30,
}

# 线程本地存储：FastAPI 的 sync 端点跑在线程池里，若共享单个 pymysql 连接，
# 并发请求会触发 ProtocolError /「Packet sequence number wrong」/ 结果串。
# 每个线程持有独立连接，互不干扰。
_thread_local = threading.local()

# 全文/标题/浏览的结构化结果缓存：检索阶段已查过一次库，
# 前端点击时直接复用，避免对同一检索词/筛选条件重复查询。
# key 含用户检索词，进程生命周期内只增不减会慢泄漏，用 OrderedDict 做 LRU 淘汰。
MAX_TEXT_SEARCH_CACHE = 256
_text_search_cache = OrderedDict()


def _cache_get(key):
    """读缓存并刷新 LRU 顺序；未命中返回 None。"""
    if key in _text_search_cache:
        _text_search_cache.move_to_end(key)
        return _text_search_cache[key]
    return None


def _cache_put(key, value):
    """写缓存；超过上限时淘汰最久未使用的条目。"""
    _text_search_cache[key] = value
    _text_search_cache.move_to_end(key)
    while len(_text_search_cache) > MAX_TEXT_SEARCH_CACHE:
        _text_search_cache.popitem(last=False)

# 文献元数据 → 前端表格字段（顺序与中文名，供 browse / 单文献详情共用，保证样式一致）
_DOC_FIELD_MAP = {
    "doc_specific_category": "类别", "dynasty": "朝代", "doc_style": "体例",
    "compilation_time": "编纂时间", "printing_time": "刊刻时间",
    "publication_time": "出版时间", "completeness": "完整性",
    "doc_theme": "主题", "source": "来源", "authors": "编者",
}


def _build_doc_fields(doc):
    """把一行文献元数据（dict）转成前端表格的 [{key, value}] 列表，跳过空值。"""
    fields = []
    for en, zh in _DOC_FIELD_MAP.items():
        val = doc.get(en)
        if val:
            fields.append({"key": zh, "value": str(val)})
    return fields


def _get_conn():
    """获取当前线程的连接（线程隔离），带重连机制。连接失败时抛出异常让调用方感知。"""
    conn = getattr(_thread_local, "conn", None)
    if conn is None or not conn.open:
        try:
            conn = pymysql.connect(**SQL_CONFIG, connect_timeout=10)
            _thread_local.conn = conn
        except Exception as e:
            print(f"[SQL] 连接失败: {e}")
            print(f"[SQL] 请检查: 1) MySQL 服务是否启动 2) .env 中 MYSQL_* 配置是否正确")
            raise
    else:
        try:
            conn.ping(reconnect=True)
        except Exception:
            try:
                conn = pymysql.connect(**SQL_CONFIG, connect_timeout=10)
                _thread_local.conn = conn
            except Exception as e:
                print(f"[SQL] 重连失败: {e}")
                raise
    return conn


class DatabaseError(Exception):
    """MySQL 数据库不可用或查询失败（区别于「查无结果」的空列表）。"""


def _fetchall(sql, params=None):
    """执行查询并返回所有结果（列表[字典]）。
    数据库不可用/查询失败时抛出 DatabaseError，而非静默返回空列表——
    否则上层会把「数据库挂了」误判成「未找到」，给出自信的错误答案。
    """
    try:
        conn = _get_conn()
        with conn.cursor(cursor=DictCursor) as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    except DatabaseError:
        raise
    except Exception as e:
        print(f"[SQL] 查询失败: {e}")
        raise DatabaseError(f"MySQL 数据库不可用或查询失败: {e}") from e


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
               d.dynasty, d.compilation_time, d.printing_time, d.publication_time,
               d.completeness, d.doc_theme, d.source,
               GROUP_CONCAT(CONCAT(a.author_name, '(', IFNULL(CONCAT(a.author_org, '·'), ''), dal.role, ')')
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
    hits = []
    for r in rows:
        title = r['doc_title'].strip('《》')
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
            f"《{title}》（{meta_str}）\n  编者：{author_str}"
        )

        # 同一循环内顺带构建结构化结果（多部文献竖排表格），缓存供前端点击复用。
        # 注意：这里只出元数据表格、不查正文预览——浏览一次会列出多部书，
        # 若每部都查正文会放大查询次数拖慢生成；正文预览仅保留在单文献详情里。
        hits.append({
            "doc_title": title,
            "fields": _build_doc_fields(r),
        })

    _cache_put(("browse", category, dynasty), {"kind": "browse", "hits": hits})

    return "\n".join(parts)


def get_documents_structured(category=None, dynasty=None):
    """浏览文献列表的结构化结果（dict），供前端右侧栏渲染成多张竖排表格。
    优先读取检索阶段 browse_documents 已缓存的结果，仅缓存未命中才兜底重查一次。
    """
    key = ("browse", category, dynasty)
    cached = _cache_get(key)
    if cached:
        return cached
    browse_documents(category=category, dynasty=dynasty)
    return _cache_get(key)


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
                      d.dynasty, d.compilation_time, d.printing_time, d.publication_time,
                      d.completeness, d.doc_theme, d.source,
                      GROUP_CONCAT(CONCAT(a.author_name, '(', IFNULL(CONCAT(a.author_org, '·'), ''), dal.role, ')')
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
        if d['printing_time']:
            meta_parts.append(f"刊刻时间：{d['printing_time']}")
        if d['publication_time']:
            meta_parts.append(f"出版时间：{d['publication_time']}")
        if d['completeness']:
            meta_parts.append(f"完整性：{d['completeness']}")
        if d['doc_theme']:
            meta_parts.append(f"主题：{d['doc_theme']}")
        if d['source']:
            meta_parts.append(f"来源：{d['source']}")

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
    """按作者姓名模糊查询，返回其参与编纂的文献。简繁双搜。"""
    def _do(t):
        return _fetchall(
            """SELECT a.author_name, a.author_org,
                      GROUP_CONCAT(CONCAT(d.doc_title, '(', dal.role, ')')
                                   SEPARATOR '、') AS works
               FROM authors a
               LEFT JOIN document_author_links dal ON a.author_id = dal.author_id
               LEFT JOIN documents d ON dal.doc_id = d.doc_id
               WHERE a.author_name LIKE %s
               GROUP BY a.author_id""",
            (f"%{t}%",)
        )

    variants = _search_variants(name)
    merged = {}
    for v in variants:
        for r in _do(v):
            if r['author_name'] not in merged:
                merged[r['author_name']] = r
    rows = list(merged.values())

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
        # FULLTEXT 无结果时，降级为 LIKE 模糊搜索（某些罕见词 ngram 可能未收录）。
        # 仅关键词 >=2 字才降级：空词/单字会触发 '%kw%' 全表扫 227 万行（ngram 为 2-gram，
        # 单字本就无法命中索引），read_timeout 再兜底，避免一次 miss 拖慢所有 SQL 请求。
        if len(keyword.strip()) >= 2:
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

    # MySQL FULLTEXT 的 relevance 是无界原始分（如 164 vs 31），不同关键词之间不可比，
    # 且没有 [0,1] 上限。这里按结果集内最大值归一到 [0,1]，与向量检索的相似度口径统一。
    real_scores = [r.get('relevance') or 0 for r in rows
                   if r.get('relevance') and r.get('relevance') != 999]
    max_rel = max(real_scores) if real_scores else 0

    parts = []
    hits = []
    for r in rows:
        text = r['full_text'][:120].replace('\n', ' ').replace('\r', ' ')
        doc_title = r['doc_title'].strip('《》') if r['doc_title'] else '未知文献'
        dynasty = f"〔{r['dynasty']}〕" if r['dynasty'] else ''
        category = f"（{r['doc_specific_category']}）" if r['doc_specific_category'] else ''
        rel_val = r.get('relevance')
        norm_rel = min(rel_val / max_rel, 1.0) if rel_val and rel_val != 999 and max_rel > 0 else None
        if norm_rel is not None:
            rel = f"相关度:{norm_rel:.2f}"
        else:
            rel = ""
        parts.append(
            f"【《{doc_title}》{dynasty}{category}】{rel}\n"
            f"  [{r['text_type'] or '正文'}] ……{text}……"
        )
        # 同一循环内顺带构建结构化结果，缓存供前端点击时复用（不再重复查库）
        hits.append({
            "doc_title": doc_title,
            "dynasty": r['dynasty'] or '',
            "category": r['doc_specific_category'] or '',
            "text_type": r['text_type'] or '正文',
            "relevance": norm_rel,
            "text": text,
        })

    # 缓存结构化结果（key 含 mode/limit：BOOLEAN 与 NATURAL 语义不同，不能互串结果）
    _cache_put(("full_text", keyword, mode, limit), {"kind": "full_text", "keyword": keyword, "hits": hits})

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
    """在层级标题中搜索关键词，了解类书的章节结构。简繁双搜。
    标题层级：h1=卷次, h2=部类, h3=小类, h4=条目。
    返回每条标题的父级路径 + 正文片段（如库中有对应全文），不再是光标题。
    """
    # 每条标题附带：父级标题（parent_name）+ 一段正文预览（snippet）
    SELECT_SQL = """
        SELECT t.title_name, t.title_level, t.title_order,
               p.title_name AS parent_name,
               d.doc_title, d.dynasty,
               (SELECT SUBSTRING(ft.full_text, 1, 80)
                  FROM full_text_1 ft
                 WHERE ft.title_id = t.title_id AND ft.text_type = '正文'
                 ORDER BY ft.full_text_order LIMIT 1) AS snippet
          FROM titles t
          LEFT JOIN titles p ON t.parent_id = p.title_id
          JOIN documents d ON t.doc_id = d.doc_id
    """

    def _do_like(kw):
        return _fetchall(
            SELECT_SQL + " WHERE t.title_name LIKE %s ORDER BY d.doc_id, t.title_order LIMIT %s",
            (f"%{kw}%", limit)
        )

    # 简繁双搜
    variants = _search_variants(keyword)
    merged = {}
    for v in variants:
        for r in _do_like(v):
            key = (r['title_name'], r['doc_title'])
            if key not in merged:
                merged[key] = r
    rows = sorted(merged.values(), key=lambda r: (r['doc_title'], r['title_order']))[:limit]

    if not rows:
        # 尝试 FULLTEXT（如果 titles 表有 FULLTEXT 索引）
        rows = _fetchall(
            SELECT_SQL + " WHERE MATCH(t.title_name) AGAINST(%s) ORDER BY d.doc_id, t.title_order LIMIT %s",
            (keyword, limit)
        )
    if not rows:
        return f"标题中未找到包含「{keyword}」的内容。"

    level_cn = {"h1": "卷次", "h2": "部类", "h3": "小类", "h4": "条目"}
    parts = []
    hits = []
    for r in rows:
        lvl = level_cn.get(r['title_level'], r['title_level'])
        dynasty = f"〔{r['dynasty']}〕" if r['dynasty'] else ''
        doc = r['doc_title'].strip('《》') if r['doc_title'] else '未知文献'
        path = f"{r['parent_name']} → " if r.get('parent_name') else ""
        snippet = f" ……{r['snippet']}……" if r.get('snippet') else ""
        parts.append(f"【{lvl}】{path}{r['title_name']} ——《{doc}》{dynasty}{snippet}")
        # 同一循环内顺带构建结构化结果，缓存供前端点击时复用（不再重复查库）
        hits.append({
            "level": lvl,
            "title_name": r['title_name'],
            "parent_name": r.get('parent_name') or '',
            "doc_title": doc,
            "dynasty": r.get('dynasty') or '',
            "snippet": r.get('snippet') or '',
        })

    # 缓存结构化结果（key 用检索词 + limit，避免不同条数的结果互串）
    _cache_put(("titles", keyword, limit), {"kind": "titles", "keyword": keyword, "hits": hits})

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
                   ORDER BY f.full_text_id LIMIT %s""",
                (f"%{title_term}%", f"%{keyword}%", limit)
            )
        else:
            return _fetchall(
                """SELECT f.full_text_id, f.full_text, f.full_text_order, f.text_type, f.title_level
                   FROM full_text_1 f
                   JOIN documents d ON f.doc_id = d.doc_id
                   WHERE d.doc_title LIKE %s
                   ORDER BY f.full_text_id LIMIT %s""",
                (f"%{title_term}%", limit)
            )

    # 同时用简体和繁体搜索，合并去重
    variants = _search_variants(doc_title)
    merged = {}
    for v in variants:
        for r in _do_query(v):
            if r['full_text_id'] not in merged:
                merged[r['full_text_id']] = r

    # 按 full_text_id（自然阅读顺序）排序，取前 limit 条。
    # 不能用 full_text_order：它在每个章节内从 1 重新计数，全局排序会把所有
    # 章节的"第1段"（多为引书）排到一起，导致预览全是书名、没有正文。
    rows = sorted(merged.values(), key=lambda r: r['full_text_id'])[:limit]

    if not rows:
        kw = f"且关键词「{keyword}」" if keyword else ""
        return f"未找到文献「{doc_title}」{kw}的全文内容。"
    parts = []
    for r in rows:
        text = r['full_text'][:120].replace('\n', ' ').replace('\r', ' ')
        parts.append(f"（{r['text_type'] or '正文'}）{text}")
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
    """按机构查询作者。简繁双搜。"""
    def _do(t):
        return _fetchall(
            "SELECT author_name, author_org FROM authors WHERE author_org LIKE %s",
            (f"%{t}%",)
        )

    variants = _search_variants(org)
    merged = {}
    for v in variants:
        for r in _do(v):
            if r['author_name'] not in merged:
                merged[r['author_name']] = r
    rows = list(merged.values())

    if not rows:
        return f"未找到机构包含「{org}」的作者。"
    parts = [f"{r['author_name']}（{r['author_org']}）" for r in rows]
    return "\n".join(parts)


def get_document_structured(title, text_limit=8):
    """返回结构化文献元数据 + 正文预览（dict），供前端右侧栏表格渲染。
    结构与 /reference/sql 的 title 分支一致：{"doc_title", "fields", "content_preview"}。
    仅返回一条有完整元数据的记录（sort_priority 优先），过滤 LIKE 噪音匹配。
    """
    clean = title.strip('《》').replace(' ', '')
    prefix = clean[:6] if len(clean) >= 3 else clean

    def _do_query(search_term):
        return _fetchall(
            """SELECT d.doc_id, d.doc_title, d.doc_specific_category, d.doc_style,
                      d.dynasty, d.compilation_time, d.printing_time, d.publication_time,
                      d.completeness, d.doc_theme, d.source,
                      GROUP_CONCAT(CONCAT(a.author_name, '(', IFNULL(CONCAT(a.author_org, '·'), ''), dal.role, ')')
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

    variants = _search_variants(prefix)
    merged = {}
    for v in variants:
        for r in _do_query(v):
            if r['doc_id'] not in merged:
                merged[r['doc_id']] = r
    rows = sorted(merged.values(), key=lambda r: (r['sort_priority'], r['doc_id']))

    if not rows:
        return None

    doc = rows[0]  # 有元数据的优先（sort_priority=0）
    doc["doc_title"] = (doc.get("doc_title") or title).strip("《》")

    # 书名已在面板头部大字展示，这里不再重复；字段与 browse 共用同一份映射保证样式一致
    fields = _build_doc_fields(doc)

    content = query_full_text_by_doc(title, limit=text_limit)
    has_content = content and "未找到" not in content

    return {
        "found": True,
        "doc_title": doc["doc_title"],
        "fields": fields,
        "content_preview": content if has_content else None,
    }


def get_full_text_structured(keyword, limit=5, mode="NATURAL"):
    """全文搜索结构化结果（dict），供前端右侧栏渲染成卡片列表。
    优先读取检索阶段 search_full_text 已缓存的 hits（同一次查询的结果），
    仅当缓存未命中（极少数情况，如检索词归一不一致）才兜底重查一次。
    """
    cached = _cache_get(("full_text", keyword, mode, limit))
    if cached:
        return cached

    if mode == "BOOLEAN":
        terms = keyword.split()
        boolean_query = " ".join(f"+{t}" for t in terms if len(t) >= 2) or f"+{keyword}"
        sql = """SELECT ft.full_text, ft.text_type, d.doc_title, d.dynasty, d.doc_specific_category,
                        MATCH(ft.full_text) AGAINST(%s IN BOOLEAN MODE) AS relevance
                 FROM full_text_1 ft JOIN documents d ON ft.doc_id = d.doc_id
                 WHERE MATCH(ft.full_text) AGAINST(%s IN BOOLEAN MODE)
                 ORDER BY relevance DESC LIMIT %s"""
        rows = _fetchall(sql, (boolean_query, boolean_query, limit))
    else:
        sql = """SELECT ft.full_text, ft.text_type, d.doc_title, d.dynasty, d.doc_specific_category,
                        MATCH(ft.full_text) AGAINST(%s) AS relevance
                 FROM full_text_1 ft JOIN documents d ON ft.doc_id = d.doc_id
                 WHERE MATCH(ft.full_text) AGAINST(%s)
                 ORDER BY relevance DESC LIMIT %s"""
        rows = _fetchall(sql, (keyword, keyword, limit))

    if not rows and len(keyword.strip()) >= 2:
        rows = _fetchall(
            """SELECT ft.full_text, ft.text_type, d.doc_title, d.dynasty, d.doc_specific_category,
                      999 AS relevance
               FROM full_text_1 ft JOIN documents d ON ft.doc_id = d.doc_id
               WHERE ft.full_text LIKE %s ORDER BY ft.full_text_id LIMIT %s""",
            (f"%{keyword}%", limit)
        )
    if not rows:
        return None

    real_scores = [r.get('relevance') or 0 for r in rows
                   if r.get('relevance') and r.get('relevance') != 999]
    max_rel = max(real_scores) if real_scores else 0

    hits = []
    for r in rows:
        rel_val = r.get('relevance')
        relevance = (min(rel_val / max_rel, 1.0)
                     if rel_val and rel_val != 999 and max_rel > 0 else None)
        hits.append({
            "doc_title": (r.get('doc_title') or '未知文献').strip('《》'),
            "dynasty": r.get('dynasty') or '',
            "category": r.get('doc_specific_category') or '',
            "text_type": r.get('text_type') or '正文',
            "relevance": relevance,
            "text": (r.get('full_text') or '')[:120].replace('\n', ' ').replace('\r', ' '),
        })
    result = {"kind": "full_text", "keyword": keyword, "hits": hits}
    _cache_put(("full_text", keyword, mode, limit), result)
    return result


def get_titles_structured(keyword, limit=15):
    """标题层级搜索结构化结果（dict），供前端右侧栏渲染。
    优先读取检索阶段 search_titles 已缓存的 hits，仅缓存未命中才兜底重查一次。
    """
    cached = _cache_get(("titles", keyword, limit))
    if cached:
        return cached

    SELECT_SQL = """SELECT t.title_name, t.title_level, t.title_order,
                           p.title_name AS parent_name, d.doc_title, d.dynasty,
                           (SELECT SUBSTRING(ft.full_text, 1, 80)
                              FROM full_text_1 ft
                             WHERE ft.title_id = t.title_id AND ft.text_type = '正文'
                             ORDER BY ft.full_text_order LIMIT 1) AS snippet
                      FROM titles t
                      LEFT JOIN titles p ON t.parent_id = p.title_id
                      JOIN documents d ON t.doc_id = d.doc_id"""

    def _do_like(kw):
        return _fetchall(
            SELECT_SQL + " WHERE t.title_name LIKE %s ORDER BY d.doc_id, t.title_order LIMIT %s",
            (f"%{kw}%", limit)
        )

    merged = {}
    for v in _search_variants(keyword):
        for r in _do_like(v):
            key = (r['title_name'], r['doc_title'])
            if key not in merged:
                merged[key] = r
    rows = sorted(merged.values(), key=lambda r: (r['doc_title'], r['title_order']))[:limit]

    if not rows:
        rows = _fetchall(
            SELECT_SQL + " WHERE MATCH(t.title_name) AGAINST(%s) ORDER BY d.doc_id, t.title_order LIMIT %s",
            (keyword, limit)
        )
    if not rows:
        return None

    level_cn = {"h1": "卷次", "h2": "部类", "h3": "小类", "h4": "条目"}
    hits = []
    for r in rows:
        hits.append({
            "level": level_cn.get(r['title_level'], r['title_level']),
            "title_name": r.get('title_name'),
            "parent_name": r.get('parent_name') or '',
            "doc_title": (r.get('doc_title') or '未知文献').strip('《》'),
            "dynasty": r.get('dynasty') or '',
            "snippet": r.get('snippet') or '',
        })
    result = {"kind": "titles", "keyword": keyword, "hits": hits}
    _cache_put(("titles", keyword, limit), result)
    return result


def get_author_structured(name):
    """返回结构化作者信息（dict），供前端右侧栏表格渲染。
    结构与 /reference/sql 的 author 分支一致：{"author_name", "works"}。
    """
    merged = {}
    for v in _search_variants(name):
        for r in _fetchall(
            """SELECT a.author_name, a.author_org, d.doc_title, dal.role
               FROM authors a
               LEFT JOIN document_author_links dal ON a.author_id = dal.author_id
               LEFT JOIN documents d ON dal.doc_id = d.doc_id
               WHERE a.author_name LIKE %s""",
            (f"%{v}%",)
        ):
            key = f"{r['author_name']}_{r.get('doc_title', '')}"
            if key not in merged:
                merged[key] = r
    rows = list(merged.values())
    if not rows:
        return None

    works = [{
        "author": r["author_name"],
        "org": r.get("author_org", ""),
        "doc": (r.get("doc_title") or "").strip("《》"),
        "role": r.get("role", ""),
    } for r in rows]
    return {"found": True, "author_name": name, "works": works}


# execute_raw_sql 的阻断名单：SELECT SLEEP(100) / INTO OUTFILE / LOAD_FILE 等危险关键字。
# 之前的白名单只看开头 token，`SELECT SLEEP(100)` 能直接通过；这里按词边界拒绝危险函数。
_SQL_BLOCKLIST = re.compile(
    r'\b(SLEEP|BENCHMARK|INTO\s+(OUTFILE|DUMPFILE)|LOAD_FILE|LOAD\s+DATA|'
    r'GET_LOCK|RELEASE_LOCK)\b',
    re.IGNORECASE,
)


def execute_raw_sql(sql, limit=50):
    """通用 SQL 执行（供调试 / 高级查询使用）。

    只允许【单条】只读 SELECT / SHOW / DESCRIBE / EXPLAIN，且对 SELECT 强制追加 LIMIT，
    拒绝多语句与危险关键字——避免日后被挂到 API 路由时变成 SQL 注入 / DoS 定时炸弹。
    """
    if not sql or not str(sql).strip():
        return "空 SQL。"
    s = str(sql).strip()

    # 只允许单条语句：去掉末尾单个分号后，若仍含分号则判为多语句
    stripped = s.rstrip()
    if stripped.endswith(';'):
        stripped = stripped[:-1].rstrip()
    if ';' in stripped:
        return "仅支持单条查询。"

    upper = stripped.upper()
    if not re.match(r'^(SELECT|SHOW|DESCRIBE|DESC|EXPLAIN)\b', upper):
        return "仅支持 SELECT / SHOW / DESCRIBE / EXPLAIN 查询。"
    if _SQL_BLOCKLIST.search(stripped):
        return "该查询包含被禁止的关键字。"

    # SELECT 强制限制返回行数，防止 `SELECT * FROM full_text_1` 一次拉 227 万行进内存
    if re.match(r'^SELECT\b', upper) and not re.search(r'\bLIMIT\s+\d+', upper):
        stripped = f"{stripped} LIMIT {limit}"

    rows = _fetchall(stripped)
    if not rows:
        return "查询无结果。"
    parts = []
    for r in rows[:limit]:
        parts.append(str(r))
    return "\n".join(parts)


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
    """关闭当前线程的数据库连接"""
    conn = getattr(_thread_local, "conn", None)
    if conn and conn.open:
        conn.close()
    _thread_local.conn = None
