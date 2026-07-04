import { useState } from "react";
import C from "../constants/colors";

/* ─────────────── PAGE: 数据下载 ─────────────── */
function DataDownloadPage({ navigate }) {
  const [exportContent, setExportContent] = useState("主表格");
  const [exportFormat, setExportFormat] = useState("Excel");
  const [exportFields, setExportFields] = useState(["全部"]);
  const [sortBy, setSortBy] = useState("年代（升序/降序）");

  const toggleField = f => setExportFields(prev => prev.includes(f) ? prev.filter(x => x !== f) : [...prev, f]);

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "32px 40px", display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div style={{ width: "100%", maxWidth: 760, background: C.white, borderRadius: 16, padding: "28px 32px", border: `1px solid ${C.border}` }}>
        <div style={{ textAlign: "center", marginBottom: 22 }}>
          <div style={{ fontSize: 14, color: C.textM }}>当前结果类型：辑本列表</div>
          <div style={{ fontSize: 14, color: C.textM }}>字段结构：书名 / 辑佚者 / 年代 / 部类 / 底本来源</div>
          <div style={{ fontSize: 14, color: C.textM }}>数据总笔数：1000笔</div>
        </div>

        {/* Preview */}
        <div style={{ textAlign: "center", marginBottom: 12 }}>
          <div style={{ display: "inline-block", background: C.bg, borderRadius: 16, padding: "6px 24px", fontSize: 13, border: `1px solid ${C.border}` }}>表格预览</div>
        </div>
        <div style={{ background: C.bg, borderRadius: 12, padding: "12px", marginBottom: 24, border: `1px solid ${C.border}`, overflow: "hidden" }}>
          <div style={{ filter: "blur(3px)", opacity: 0.7 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "#d4c8b0" }}>
                  {["书名", "辑佚者", "年代/部类", "底本来源", "底本类型/说明", "文献来源/辑佚说明"].map(h => (
                    <th key={h} style={{ padding: "6px 8px", border: "1px solid #c0b098", textAlign: "left", color: C.text }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[1, 2, 3, 4, 5].map(i => (
                  <tr key={i} style={{ background: i % 2 === 0 ? "#f0ebe0" : C.white }}>
                    {[1, 2, 3, 4, 5, 6].map(j => <td key={j} style={{ padding: "5px 8px", border: "1px solid #e0d8c8" }}>样例数据</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Export settings */}
        <div style={{ textAlign: "center", marginBottom: 12 }}>
          <div style={{ display: "inline-block", background: C.bg, borderRadius: 16, padding: "6px 24px", fontSize: 13, border: `1px solid ${C.border}` }}>导出设置</div>
        </div>
        <div style={{ background: C.bg, borderRadius: 12, padding: "20px 24px", border: `1px solid ${C.border}`, display: "flex", flexDirection: "column", gap: 16 }}>
          {[
            ["导出内容：", ["主表格", "原始数据", "OCR内容"], exportContent, setExportContent, "radio"],
            ["导出格式：", ["Excel", "CSV"], exportFormat, setExportFormat, "radio"],
            ["导出字段选择：", ["全部", "书名", "辑佚者", "年代", "部类", "底本来源"], exportFields, toggleField, "check"],
            ["导出排序依据：", ["年代（升序/降序）", "编纂者", "分类"], sortBy, setSortBy, "radio"],
          ].map(([label, options, value, setter, type]) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
              <span style={{ fontSize: 13, color: C.textM, width: 100, flexShrink: 0 }}>{label}</span>
              {options.map(opt => (
                <label key={opt} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 13, cursor: "pointer", color: C.text }}>
                  <input
                    type={type === "radio" ? "radio" : "checkbox"}
                    checked={type === "radio" ? value === opt : (Array.isArray(value) ? value.includes(opt) : false)}
                    onChange={() => setter(type === "radio" ? opt : opt)}
                    name={label}
                    style={{ accentColor: C.brownBtn }}
                  />
                  {opt}
                </label>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Buttons */}
      <div style={{ display: "flex", justifyContent: "space-between", width: "100%", maxWidth: 760, marginTop: 24 }}>
        <button onClick={() => navigate("resources-overview")} style={{
          padding: "10px 24px", background: C.white, border: `1px solid ${C.border}`,
          borderRadius: 10, fontSize: 14, cursor: "pointer", color: C.text, fontFamily: "inherit",
        }}>返回</button>
        <button style={{
          padding: "12px 48px", background: C.brownBtn, border: "none",
          borderRadius: 10, fontSize: 15, cursor: "pointer", color: "#fff", fontFamily: "inherit", fontWeight: 600,
        }}>导出</button>
      </div>
    </div>
  );
}

export default DataDownloadPage;