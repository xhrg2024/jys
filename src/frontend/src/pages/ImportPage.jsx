import { useMemo, useState } from "react";
import C from "../constants/colors";

function ImportPage({ navigate }) {
  const [jsonText, setJsonText] = useState("");
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);

  // 实时解析预览
  const parsed = useMemo(() => {
    if (!jsonText.trim()) return null;
    try {
      const data = JSON.parse(jsonText);
      const entities = Array.isArray(data.entities) ? data.entities : [];
      const relations = Array.isArray(data.relations) ? data.relations : [];
      return { entities, relations };
    } catch (e) {
      return { error: e.message };
    }
  }, [jsonText]);

  const handleFile = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => setJsonText(String(e.target.result || ""));
    reader.readAsText(file, "utf-8");
  };

  const handleImport = async () => {
    if (!parsed || parsed.error || importing) return;
    setImporting(true);
    setImportResult(null);
    try {
      const res = await fetch("/import/graph", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entities: parsed.entities, relations: parsed.relations }),
      });
      const data = await res.json();
      setImportResult(data);
    } catch (err) {
      setImportResult({ error: err.message || String(err) });
    }
    setImporting(false);
  };

  const canImport = parsed && !parsed.error && parsed.entities.length > 0 && !importing;

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "24px 28px" }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: C.text, margin: "0 0 8px", fontFamily: "'Noto Serif SC', serif" }}>
        知识图谱导入
      </h2>
      <div style={{ fontSize: 12.5, color: C.textM, marginBottom: 20, lineHeight: 1.7 }}>
        导入 data.json 格式的知识图谱（{"{ entities: [...], relations: [...] }"}）。
        采用<strong>增量合并</strong>：按实体 id 去重，已存在则更新属性，不清空现有数据；导入后自动为涉及实体重算语义向量（embedding）。
      </div>

      <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>
        {/* 左侧：输入区 */}
        <div style={{ flex: 1, minWidth: 380, display: "flex", flexDirection: "column", gap: 16 }}>
          {/* 文件上传 */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); handleFile(e.dataTransfer.files?.[0]); }}
            style={{
              background: C.white, border: `1px dashed ${C.border}`, borderRadius: 12,
              padding: 24, textAlign: "center", color: C.textM, fontSize: 13,
            }}
          >
            <div style={{ marginBottom: 8 }}>拖拽 JSON 文件到此处，或</div>
            <label style={{
              display: "inline-block", background: C.brownBtn, color: "#fff", borderRadius: 20,
              padding: "8px 22px", fontSize: 13, cursor: "pointer",
            }}>
              选择文件
              <input
                type="file"
                accept=".json,application/json"
                style={{ display: "none" }}
                onChange={(e) => handleFile(e.target.files?.[0])}
              />
            </label>
          </div>

          {/* 粘贴 JSON */}
          <div style={{ background: C.white, borderRadius: 12, border: `1px solid ${C.border}`, padding: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: C.text, marginBottom: 10 }}>或粘贴 JSON 内容</div>
            <textarea
              value={jsonText}
              onChange={(e) => setJsonText(e.target.value)}
              placeholder={`{
  "entities": [
    {
      "id": "s1",
      "text": "马国翰",
      "label": "Scholar",
      "properties": { "birthDeath": "1794-1857" }
    },
    {
      "id": "c1",
      "text": "玉函山房辑佚书",
      "label": "Compilation",
      "properties": { "compilationTitle": "玉函山房辑佚书", "compiler": "马国翰" }
    }
  ],
  "relations": [
    { "source": "s1", "target": "c1", "type": "编纂", "description": "马国翰辑" }
  ]
}`}
              style={{
                width: "100%", height: 220, border: `1px solid ${C.border}`, borderRadius: 8,
                padding: 12, fontSize: 12.5, fontFamily: "Consolas, 'Courier New', monospace",
                color: C.text, resize: "vertical", outline: "none", boxSizing: "border-box",
                background: "#faf7f0",
              }}
            />
          </div>
        </div>

        {/* 右侧：预览 + 导入 */}
        <div style={{ width: 380, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ background: C.white, borderRadius: 12, border: `1px solid ${C.border}`, padding: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: C.text, marginBottom: 12 }}>预览</div>
            {!jsonText.trim() ? (
              <div style={{ color: C.textL, fontSize: 13 }}>等待输入…</div>
            ) : parsed?.error ? (
              <div style={{ color: "#b3261e", fontSize: 13 }}>JSON 解析失败：{parsed.error}</div>
            ) : (
              <>
                <div style={{ fontSize: 13, color: C.text, marginBottom: 4 }}>
                  实体 <strong>{parsed.entities.length}</strong> 个 · 关系 <strong>{parsed.relations.length}</strong> 条
                </div>
                <div style={{ fontSize: 12, color: C.textL, marginBottom: 8, maxHeight: 180, overflow: "auto", lineHeight: 1.7 }}>
                  {parsed.entities.slice(0, 5).map((e, i) => (
                    <div key={i}>{e.text || e.id} <span style={{ color: C.brownBtn }}>[{e.label}]</span></div>
                  ))}
                  {parsed.entities.length > 5 && <div>… 等 {parsed.entities.length} 个实体</div>}
                </div>
              </>
            )}
          </div>

          <button
            onClick={handleImport}
            disabled={!canImport}
            style={{
              background: canImport ? C.brownBtn : C.border, color: canImport ? "#fff" : C.textL,
              border: "none", borderRadius: 8, padding: "12px 0", fontSize: 14, fontWeight: 600,
              cursor: canImport ? "pointer" : "not-allowed", fontFamily: "inherit",
            }}
          >
            {importing ? "导入中…" : "导入到知识图谱"}
          </button>

          {importResult && (
            <div style={{ background: C.white, borderRadius: 12, border: `1px solid ${C.border}`, padding: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: C.text, marginBottom: 10 }}>导入结果</div>
              {importResult.error ? (
                <div style={{ color: "#b3261e", fontSize: 13 }}>{importResult.error}</div>
              ) : (
                <div style={{ fontSize: 13, color: C.textM, lineHeight: 1.9 }}>
                  <div>实体：共 {importResult.entities_total}，新建 {importResult.entities_created}</div>
                  <div>关系：共 {importResult.relations_total}，新建 {importResult.relations_created}，跳过 {importResult.relations_skipped}</div>
                  <div>语义向量：重算 {importResult.embeddings} 个</div>
                  {importResult.embeddings_error && (
                    <div style={{ color: "#b3261e" }}>语义更新失败：{importResult.embeddings_error}</div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ImportPage;
