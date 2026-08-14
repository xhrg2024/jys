import C from "../constants/colors";

/**
 * SQL 数据库参考资料面板：文献元数据表格 + 正文预览。
 * props.data = { found, doc_title, fields: [{key,value}], content_preview }
 *   或 { found, author_name, works: [{author, org, doc, role}] }
 */
function SqlSourcePanel({ data, sourceData }) {
  if (!data) return null;

  // 复用检索阶段已下发的完整原文（SQL 无关联，无需再查库）
  if (data.detail_text) {
    return (
      <div style={{
        padding: "14px 16px", height: "100%", overflow: "auto",
        fontSize: 12.5, color: C.text, lineHeight: 1.8,
        whiteSpace: "pre-wrap", fontFamily: "'Noto Serif SC', serif",
      }}>
        {data.detail_text}
      </div>
    );
  }

  if (!data.found) {
    return (
      <div style={{ padding: 20, fontSize: 13, color: C.textM }}>
        {data.message || "未找到相关数据"}
      </div>
    );
  }

  // 作者查询结果
  if (data.works) {
    return (
      <div style={{ padding: 14 }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: C.text, marginBottom: 10, fontFamily: "'Noto Serif SC', serif" }}>
          {data.author_name}
        </div>
        <div style={{ fontSize: 12, color: C.textM, marginBottom: 12 }}>
          参与编纂文献 ({data.works.length}条)
        </div>
        <div style={{ fontSize: 12.5, lineHeight: 1.8 }}>
          {data.works.map((w, i) => (
            <div key={i} style={{
              padding: "6px 10px", marginBottom: 4,
              background: i % 2 === 0 ? C.bg : C.white,
              borderRadius: 6, border: `1px solid ${C.borderL}`,
            }}>
              <span style={{ color: C.brownDk, fontWeight: 600 }}>《{w.doc}》</span>
              {w.role && <span style={{ color: C.textM, marginLeft: 8 }}>({w.role})</span>}
              {w.org && <span style={{ color: C.textL, marginLeft: 8, fontSize: 11 }}>{w.org}</span>}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // 文献详情查询结果
  const { doc_title, fields, content_preview } = data;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* 文献元数据表 */}
      <div style={{
        flexShrink: 0, maxHeight: "55%", overflow: "auto",
        padding: "14px 16px",
      }}>
        <div style={{
          fontSize: 16, fontWeight: 700, color: C.text,
          fontFamily: "'Noto Serif SC', serif", marginBottom: 12,
        }}>
          《{doc_title}》
        </div>

        {fields && fields.length > 0 ? (
          <div>
            {fields.map((f, i) => (
              <div key={i} style={{
                display: "flex", gap: 8, padding: "4px 0",
                borderBottom: i < fields.length - 1 ? `1px solid ${C.borderL}` : "none",
                fontSize: 12.5, lineHeight: 1.7,
              }}>
                <span style={{ color: C.textM, minWidth: 65, flexShrink: 0, fontWeight: 500 }}>
                  {f.key}
                </span>
                <span style={{ color: C.brownDk, wordBreak: "break-all" }}>
                  {f.value}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ fontSize: 12.5, color: C.textL }}>（无详细元数据）</div>
        )}
      </div>

      {/* 正文预览 */}
      {content_preview && (
        <div style={{
          flex: 1, overflow: "auto",
          borderTop: `1px solid ${C.border}`,
          padding: "12px 16px",
        }}>
          <div style={{
            fontSize: 12, color: C.textM, fontWeight: 600,
            letterSpacing: 1, marginBottom: 8,
          }}>
            正文预览
          </div>
          <div style={{
            fontSize: 12.5, color: C.text, lineHeight: 1.75,
            whiteSpace: "pre-wrap", fontFamily: "'Noto Serif SC', serif",
          }}>
            {content_preview}
          </div>
        </div>
      )}
    </div>
  );
}

export default SqlSourcePanel;
