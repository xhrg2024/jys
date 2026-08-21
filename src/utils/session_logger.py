"""
会话日志：每次问答运行生成一个完整日志文件，包含所有检索结果、工具调用、
模型输出，不做任何截断。
"""
import os
import json
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(exist_ok=True)


class SessionLogger:
    """单次问答的完整日志记录器"""

    def __init__(self, question):
        self.question = question
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_q = question[:30].replace('/', '_').replace('\\', '_').replace(':', '_')
        self.path = LOG_DIR / f"{self.timestamp}_{safe_q}.log"
        self._closed = False
        # 先建一个空文件（"w" 截断），后续 _write 用追加模式逐行写，
        # 避免每次写回整个 buffer 导致的 O(n²) 磁盘 IO。
        with open(self.path, "w", encoding="utf-8") as f:
            pass

    def _write(self, text):
        # 逐行追加并刷到磁盘，防止中途崩溃丢日志；不再全量重写已写内容
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    # ── 各阶段日志方法 ──

    def log_header(self, intent, model_label):
        self._write("=" * 70)
        self._write(f"  辑佚史智能体 — 会话日志")
        self._write(f"  时间: {self.timestamp}")
        self._write(f"  模型: {model_label}")
        self._write(f"  意图: {intent}")
        self._write(f"  问题: {self.question}")
        self._write("=" * 70)

    def log_tool_selection(self, success, tool_names, fallback_reason=""):
        self._write("")
        self._write("─" * 50)
        if success:
            self._write(f"  🧠 LLM Tool Calling: 成功选择了 {len(tool_names)} 个工具")
            for i, name in enumerate(tool_names, 1):
                self._write(f"     {i}. {name}")
        else:
            self._write(f"  ⚠️  LLM Tool Calling: 失败/降级 — {fallback_reason}")
        self._write("─" * 50)

    def log_tool_result(self, tool_name, full_result):
        self._write("")
        self._write(f"  ┌─ 工具: {tool_name} ─" + "─" * 55)
        self._write(f"  │  (全长 {len(full_result)} 字符)")
        for line in full_result.split("\n"):
            self._write(f"  │  {line}")
        self._write(f"  └" + "─" * 65)

    def log_graph_results(self, results):
        self._write("")
        self._write("─" * 50)
        self._write(f"  📊 知识图谱检索结果 ({len(results)} 条)")
        self._write("─" * 50)
        for i, r in enumerate(results, 1):
            if r:
                self._write(f"  [{i}] {r}")

    def log_sql_results(self, results):
        self._write("")
        self._write("─" * 50)
        self._write(f"  🗄️  SQL 检索结果 ({len(results)} 条)")
        self._write("─" * 50)
        for i, r in enumerate(results, 1):
            if r:
                self._write(f"  [{i}] (全长 {len(r)} 字符)")
                self._write(f"  {r}")

    def log_vector_results(self, results):
        self._write("")
        self._write("─" * 50)
        self._write(f"  🔍 向量检索结果 ({len(results)} 条)")
        self._write("─" * 50)
        for i, r in enumerate(results, 1):
            if r:
                self._write(f"  [{i}] {r}")

    def log_context(self, context):
        self._write("")
        self._write("─" * 50)
        self._write(f"  📝 合并后上下文 (全长 {len(context)} 字符)")
        self._write("─" * 50)
        self._write(context)

    def log_source_index(self, source_index):
        """记录结构化来源索引：每条编号的来源类型 + 实体/文献名。
        便于核对图谱 / 数据库 / 向量各类来源是否都被正确标注。
        """
        if not source_index:
            return
        self._write("")
        self._write("─" * 50)
        self._write(f"  🏷️  来源索引 source_index ({len(source_index)} 条)")
        self._write("─" * 50)
        for num in sorted(source_index, key=lambda k: int(k) if str(k).isdigit() else 0):
            entry = source_index[num]
            if isinstance(entry, dict):
                stype = entry.get("source_type", "?")
                label = entry.get("label", "?")
                tool = entry.get("tool_name", "")
                entity = entry.get("entity_name", "")
                doc = entry.get("doc_title", "")
                author = entry.get("author_name", "")
                detail = []
                if tool:
                    detail.append(f"tool={tool}")
                if entity:
                    detail.append(f"实体={entity}")
                if doc:
                    detail.append(f"文献={doc}")
                if author:
                    detail.append(f"作者={author}")
                extra = f" ({', '.join(detail)})" if detail else ""
                self._write(f"  [{num}] {label}({stype}){extra}")
            else:
                self._write(f"  [{num}] {entry}")

    def log_thinking(self, thinking):
        self._write("")
        self._write("═" * 50)
        self._write(f"  🧠 RACE 前置分析 (Think)")
        self._write("═" * 50)
        self._write(thinking if thinking else "(无)")

    def log_answer(self, answer):
        self._write("")
        self._write("═" * 50)
        self._write(f"  💬 最终回答 (全长 {len(answer)} 字符)")
        self._write("═" * 50)
        self._write(answer)

    def log_raw_api_response(self, stage, raw_text):
        """记录原始的 API 返回内容（不含截断）"""
        self._write("")
        self._write(f"  ┌─ API 原始返回 [{stage}] (全长 {len(raw_text)} 字符) ─")
        self._write(raw_text)
        self._write(f"  └─ API 原始返回 [{stage}] 结束 ─")

    def close(self):
        if not self._closed:
            self._write("")
            self._write("=" * 70)
            self._write("  日志结束")
            self._write("=" * 70)
            self._closed = True

    def get_path(self):
        return str(self.path)
