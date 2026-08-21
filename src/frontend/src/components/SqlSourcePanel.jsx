import C from "../constants/colors";

/**
 * SQL 数据库参考资料面板：文献元数据表格 + 正文预览。
 * props.data = { found, doc_title, fields: [{key,value}], content_preview }
 *   或 { found, author_name, works: [{author, org, doc, role}] }
 */
function SqlSourcePanel({ data, sourceData }) {
  if (!data) return null;

  // 兜底：检索阶段未附带结构化数据时的纯文本展示
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

  // 全文搜索 → 正文片段卡片列表
  if (data.kind === "full_text") {
    return (
      <div style={{ padding: "16px", height: "100%", overflow: "auto" }}>
        <div style={{ fontSize: 17, fontWeight: 700, color: C.text, fontFamily: "'Noto Serif SC', serif", marginBottom: 4 }}>
          全文检索「{data.keyword}」
        </div>
        <div style={{ fontSize: 11.5, color: C.textL, marginBottom: 12, letterSpacing: 1 }}>
          匹配 {data.hits.length} 条正文片段
        </div>
        {data.hits.map((h, i) => (
          <div key={i} style={{
            border: `1px solid ${C.borderL}`, borderRadius: 8,
            padding: "10px 12px", marginBottom: 10, background: C.white,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, flexWrap: "wrap" }}>
              <span style={{ color: C.brownDk, fontWeight: 700, fontSize: 13, fontFamily: "'Noto Serif SC', serif" }}>
                《{h.doc_title}》
              </span>
              {h.dynasty && <span style={{ color: C.textM, fontSize: 11.5 }}>〔{h.dynasty}〕</span>}
              {h.category && <span style={{ color: C.textL, fontSize: 11.5 }}>（{h.category}）</span>}
              <span style={{
                marginLeft: "auto", fontSize: 11, color: C.textM,
                padding: "2px 8px", borderRadius: 10,
                background: "rgba(0,0,0,0.04)", whiteSpace: "nowrap",
              }}>
                相关度 {h.relevance != null ? h.relevance.toFixed(2) : "—"}
              </span>
            </div>
            <div style={{ fontSize: 11, color: C.textM, marginBottom: 4 }}>
              <span style={{ display: "inline-block", padding: "1px 6px", borderRadius: 4, background: "rgba(0,0,0,0.05)", fontSize: 10.5 }}>
                {h.text_type}
              </span>
            </div>
            <div style={{ fontSize: 12.5, color: C.text, lineHeight: 1.75, whiteSpace: "pre-wrap", fontFamily: "'Noto Serif SC', serif" }}>
              ……{h.text}……
            </div>
          </div>
        ))}
      </div>
    );
  }

  // 标题层级搜索 → 目录条目卡片列表
  if (data.kind === "titles") {
    return (
      <div style={{ padding: "16px", height: "100%", overflow: "auto" }}>
        <div style={{ fontSize: 17, fontWeight: 700, color: C.text, fontFamily: "'Noto Serif SC', serif", marginBottom: 4 }}>
          标题检索「{data.keyword}」
        </div>
        <div style={{ fontSize: 11.5, color: C.textL, marginBottom: 12, letterSpacing: 1 }}>
          匹配 {data.hits.length} 条层级标题
        </div>
        {data.hits.map((h, i) => (
          <div key={i} style={{
            border: `1px solid ${C.borderL}`, borderRadius: 8,
            padding: "10px 12px", marginBottom: 10, background: C.white,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, flexWrap: "wrap" }}>
              <span style={{
                fontSize: 10.5, color: C.brownDk, fontWeight: 600,
                padding: "1px 6px", borderRadius: 4,
                background: "rgba(122,170,152,0.15)",
              }}>
                {h.level}
              </span>
              {h.parent_name && <span style={{ fontSize: 11.5, color: C.textM }}>{h.parent_name} →</span>}
              <span style={{ fontSize: 13, color: C.text, fontWeight: 600 }}>{h.title_name}</span>
              <span style={{ marginLeft: "auto", fontSize: 11.5, color: C.textM, whiteSpace: "nowrap" }}>
                《{h.doc_title}》{h.dynasty ? `〔${h.dynasty}〕` : ""}
              </span>
            </div>
            {h.snippet && (
              <div style={{ fontSize: 12, color: C.textL, lineHeight: 1.7, whiteSpace: "pre-wrap", fontFamily: "'Noto Serif SC', serif", marginTop: 4 }}>
                ……{h.snippet}……
              </div>
            )}
          </div>
        ))}
      </div>
    );
  }

  // 浏览文献列表 → 多部文献竖排表格（每部一张元数据表 + 可选正文预览）
  if (data.kind === "browse") {
    return (
      <div style={{ padding: "16px", height: "100%", overflow: "auto" }}>
        <div style={{ fontSize: 17, fontWeight: 700, color: C.text, fontFamily: "'Noto Serif SC', serif", marginBottom: 4 }}>
          文献列表
        </div>
        <div style={{ fontSize: 11.5, color: C.textL, marginBottom: 12, letterSpacing: 1 }}>
          共 {data.hits.length} 部文献
        </div>
        {data.hits.map((d, i) => (
          <div key={i} style={{
            border: `1px solid ${C.borderL}`, borderRadius: 8,
            background: C.white, marginBottom: 14, overflow: "hidden",
          }}>
            {/* 书名头部 */}
            <div style={{
              padding: "10px 14px", borderBottom: `1px solid ${C.border}`,
              fontSize: 15, fontWeight: 700, color: C.brownDk,
              fontFamily: "'Noto Serif SC', serif",
            }}>
              《{d.doc_title}》
            </div>

            {/* 文献信息表 */}
            {d.fields && d.fields.length > 0 ? (
              d.fields.map((f, j) => (
                <div key={j} style={{
                  display: "flex",
                  background: j % 2 === 0 ? C.white : C.bg,
                }}>
                  <div style={{
                    width: 76, flexShrink: 0, padding: "7px 12px",
                    color: C.textM, fontSize: 12, fontWeight: 600,
                    borderRight: `1px solid ${C.borderL}`,
                    background: "rgba(0,0,0,0.015)",
                  }}>
                    {f.key}
                  </div>
                  <div style={{
                    flex: 1, padding: "7px 12px",
                    color: C.brownDk, fontSize: 12.5, lineHeight: 1.7,
                    wordBreak: "break-all",
                  }}>
                    {f.value}
                  </div>
                </div>
              ))
            ) : (
              <div style={{ padding: "10px 14px", fontSize: 12.5, color: C.textL }}>
                （无详细元数据）
              </div>
            )}
          </div>
        ))}
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

  // 作者查询结果 → 三列表格（文献 / 角色 / 机构）
  if (data.works) {
    return (
      <div style={{ padding: 16, height: "100%", overflow: "auto" }}>
        <div style={{
          fontSize: 17, fontWeight: 700, color: C.text,
          fontFamily: "'Noto Serif SC', serif", marginBottom: 4,
        }}>
          {data.author_name}
        </div>
        <div style={{ fontSize: 11.5, color: C.textL, marginBottom: 12, letterSpacing: 1 }}>
          参与编纂文献（{data.works.length}条）
        </div>

        <div style={{ border: `1px solid ${C.borderL}`, borderRadius: 8, overflow: "hidden" }}>
          <div style={{
            display: "flex", background: "rgba(0,0,0,0.03)",
            borderBottom: `1px solid ${C.borderL}`,
            fontSize: 11.5, color: C.textM, fontWeight: 600,
          }}>
            <div style={{ flex: 1.7, padding: "7px 12px", borderRight: `1px solid ${C.borderL}` }}>文献</div>
            <div style={{ flex: 1, padding: "7px 12px", borderRight: `1px solid ${C.borderL}` }}>角色</div>
            <div style={{ flex: 1.4, padding: "7px 12px" }}>机构</div>
          </div>
          {data.works.map((w, i) => (
            <div key={i} style={{ display: "flex", background: i % 2 === 0 ? C.white : C.bg }}>
              <div style={{
                flex: 1.7, padding: "7px 12px", borderRight: `1px solid ${C.borderL}`,
                color: C.brownDk, fontWeight: 600, fontSize: 12.5, wordBreak: "break-all",
              }}>
                《{w.doc}》
              </div>
              <div style={{
                flex: 1, padding: "7px 12px", borderRight: `1px solid ${C.borderL}`,
                color: C.textM, fontSize: 12.5,
              }}>
                {w.role || "—"}
              </div>
              <div style={{ flex: 1.4, padding: "7px 12px", color: C.textL, fontSize: 12, wordBreak: "break-all" }}>
                {w.org || "—"}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // 文献详情查询结果 → 字段表格 + 正文预览
  const { doc_title, fields, content_preview } = data;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* 文献元数据表 */}
      <div style={{
        flexShrink: 0, maxHeight: "55%", overflow: "auto",
        padding: "16px 16px 12px",
      }}>
        <div style={{
          fontSize: 17, fontWeight: 700, color: C.text,
          fontFamily: "'Noto Serif SC', serif", marginBottom: 4,
        }}>
          《{doc_title}》
        </div>
        <div style={{ fontSize: 11.5, color: C.textL, marginBottom: 12, letterSpacing: 1 }}>
          文献信息
        </div>

        {fields && fields.length > 0 ? (
          <div style={{ border: `1px solid ${C.borderL}`, borderRadius: 8, overflow: "hidden" }}>
            {fields.map((f, i) => (
              <div key={i} style={{
                display: "flex",
                background: i % 2 === 0 ? C.white : C.bg,
              }}>
                <div style={{
                  width: 76, flexShrink: 0, padding: "7px 12px",
                  color: C.textM, fontSize: 12, fontWeight: 600,
                  borderRight: `1px solid ${C.borderL}`,
                  background: "rgba(0,0,0,0.015)",
                }}>
                  {f.key}
                </div>
                <div style={{
                  flex: 1, padding: "7px 12px",
                  color: C.brownDk, fontSize: 12.5, lineHeight: 1.7,
                  wordBreak: "break-all",
                }}>
                  {f.value}
                </div>
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
