import C from "../constants/colors";

const TYPE_CN = {
  Scholar: "学者", Compilation: "辑本", Method: "方法",
  Time: "时期", Academic: "学派", Leishu: "类书",
  Methodology: "方法论", Discipline: "学科", Entity: "实体",
};

/**
 * 向量检索参考资料面板：展示语义匹配排名靠前的实体列表（Top-K）。
 * props.entities = [{ name, type, similarity }...]
 * 点击条目跳转到该实体的图谱详情。
 */
function VectorSourcePanel({ entities, onNodeClick }) {
  const list = entities || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{
        flexShrink: 0, padding: "14px 16px", borderBottom: `1px solid ${C.border}`,
      }}>
        <div style={{ fontSize: 12, color: C.textM, fontWeight: 600, letterSpacing: 1, marginBottom: 6 }}>
          语义匹配结果（Top {list.length}）
        </div>
        <div style={{ fontSize: 11.5, color: C.textL, lineHeight: 1.6 }}>
          按向量相似度排名靠前的实体；点击条目查看该实体的属性与关系图。
        </div>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "8px 12px" }}>
        {list.length === 0 ? (
          <div style={{ padding: 24, color: C.textL, fontSize: 13, textAlign: "center" }}>
            无匹配结果
          </div>
        ) : (
          list.map((e, i) => (
            <div
              key={`${e.name}-${i}`}
              onClick={() => onNodeClick && onNodeClick({ name: e.name, label: e.type })}
              style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "10px 12px", borderRadius: 8, cursor: "pointer",
                marginBottom: 4,
              }}
              onMouseEnter={(ev) => { ev.currentTarget.style.background = "rgba(138,69,32,0.05)"; }}
              onMouseLeave={(ev) => { ev.currentTarget.style.background = "transparent"; }}
            >
              <span style={{ fontSize: 11, color: C.textL, width: 16, flexShrink: 0 }}>{i + 1}</span>
              <span style={{ fontSize: 13.5, color: C.text, fontWeight: 600, flex: 1, wordBreak: "break-all" }}>
                {e.name}
              </span>
              {e.type && (
                <span style={{
                  fontSize: 10, padding: "1px 7px", borderRadius: 8, flexShrink: 0,
                  background: "rgba(122,170,152,0.15)", color: "#2a5040",
                  border: "1px solid rgba(122,170,152,0.4)",
                }}>
                  {TYPE_CN[e.type] || e.type}
                </span>
              )}
              {typeof e.similarity === "number" && (
                <span style={{ fontSize: 11, color: C.textM, flexShrink: 0 }}>
                  {(e.similarity * 100).toFixed(0)}%
                </span>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default VectorSourcePanel;
