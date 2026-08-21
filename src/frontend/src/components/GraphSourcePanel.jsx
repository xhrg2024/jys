import KnowledgeGraph from "./KnowledgeGraph";
import C from "../constants/colors";

/**
 * 图谱参考资料面板：实体属性卡片 + 2跳邻居网状图。
 * props.data = { entity_name, entity_type, properties: [{key, value}], graph: {nodes, edges} }
 */
function GraphSourcePanel({ data, sourceData, onNodeClick, onEdgeClick, trail, onTrailClick }) {
  if (!data) return null;

  const { entity_name, entity_type, properties, graph } = data;

  // 实体类型中文映射
  const TYPE_CN = {
    Scholar: "学者", Compilation: "辑本", Method: "方法",
    Time: "时期", Academic: "学派", Leishu: "类书",
    Methodology: "方法论", Entity: "实体",
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* 面包屑导航：原始节点 → ... → 当前节点 */}
      {trail && trail.length > 0 && (
        <div style={{
          flexShrink: 0, padding: "8px 16px", borderBottom: `1px solid ${C.borderL}`,
          display: "flex", alignItems: "center", flexWrap: "wrap", gap: 4,
          fontSize: 12, color: C.textM, background: "#fafaf5",
        }}>
          <span style={{ fontSize: 11, color: C.textL, marginRight: 2 }}>路径：</span>
          {trail.map((item, i) => {
            const name = typeof item === "object" ? item.name : item;
            return (
              <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                {i > 0 && <span style={{ color: C.textL, margin: "0 2px" }}>›</span>}
                <span
                  onClick={() => i < trail.length - 1 && onTrailClick && onTrailClick(i)}
                  style={{
                    cursor: i === trail.length - 1 ? "default" : "pointer",
                    color: i === trail.length - 1 ? C.brownDk : "#8a4520",
                    fontWeight: i === trail.length - 1 ? 700 : 500,
                    textDecoration: i === trail.length - 1 ? "none" : "underline",
                    textUnderlineOffset: 2,
                  }}
                >
                  {name}
                </span>
              </span>
            );
          })}
        </div>
      )}

      {/* 上半部分：实体属性卡片 */}
      <div style={{
        flexShrink: 0, maxHeight: "42%", overflow: "auto",
        padding: "14px 16px", borderBottom: `1px solid ${C.border}`,
      }}>
        <div style={{
          fontSize: 12, color: C.textM, marginBottom: 8,
          fontWeight: 600, letterSpacing: 1,
        }}>
          实体属性
        </div>

        {/* 实体名 + 类型标签 */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <span style={{ fontSize: 16, fontWeight: 700, color: C.text, fontFamily: "'Noto Serif SC', serif" }}>
            {entity_name}
          </span>
          {entity_type && (
            <span style={{
              fontSize: 10.5, padding: "1px 8px", borderRadius: 8,
              background: "rgba(122,170,152,0.15)", color: "#2a5040",
              border: "1px solid rgba(122,170,152,0.4)",
            }}>
              {TYPE_CN[entity_type] || entity_type}
            </span>
          )}
        </div>

        {/* 属性表 */}
        {properties && properties.length > 0 ? (
          <div style={{ fontSize: 12.5, lineHeight: 1.8 }}>
            {properties.map((p, i) => (
              <div key={i} style={{
                display: "flex", gap: 8, padding: "2px 0",
                borderBottom: i < properties.length - 1 ? `1px solid ${C.borderL}` : "none",
              }}>
                <span style={{ color: C.textM, minWidth: 70, flexShrink: 0 }}>{p.key}</span>
                <span style={{ color: C.brownDk, wordBreak: "break-all" }}>{p.value}</span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ fontSize: 12.5, color: C.textL }}>（无详细属性）</div>
        )}
      </div>

      {/* 下半部分：关系图谱 */}
      <div style={{ flex: 1, minHeight: 0, position: "relative" }}>
        <div style={{
          fontSize: 12, color: C.textM, fontWeight: 600, letterSpacing: 1,
          padding: "10px 16px 4px",
          display: "flex", justifyContent: "space-between", alignItems: "baseline",
        }}>
          <span>关联图谱 ({graph?.nodes?.length || 0}节点 · {graph?.edges?.length || 0}边)</span>
          <span style={{ fontWeight: 400, color: C.textL, fontSize: 11, letterSpacing: 0 }}>
            拖动节点可手动调整位置
          </span>
        </div>
        <div style={{ flex: 1, height: "calc(100% - 30px)" }}>
          {graph && graph.nodes?.length > 0 ? (
            <KnowledgeGraph
              nodes={graph.nodes}
              edges={graph.edges}
              layout="force"
              height="100%"
              onNodeClick={(node) => node && onNodeClick && onNodeClick(node)}
              onEdgeClick={(edge) => edge && onEdgeClick && onEdgeClick(edge)}
            />
          ) : (
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              height: "100%", color: C.textL, fontSize: 12.5,
            }}>
              无关联图谱数据
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default GraphSourcePanel;
