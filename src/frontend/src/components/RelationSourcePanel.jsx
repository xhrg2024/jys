import KnowledgeGraph from "./KnowledgeGraph";
import C from "../constants/colors";

// 实体类型中文映射
const TYPE_CN = {
  Scholar: "学者", Compilation: "辑本", Method: "方法",
  Time: "时期", Academic: "学派", Leishu: "类书",
  Methodology: "方法论", Entity: "实体",
};

// 单个实体属性卡片（节点详情与节点点开一致）
function EntityCard({ title, data, highlight }) {
  const { entity_name, entity_type, properties } = data || {};
  return (
    <div style={{
      border: `1px solid ${highlight ? C.brownBtn : C.border}`,
      borderRadius: 10, padding: "10px 12px",
      background: highlight ? "rgba(196,164,64,0.06)" : "#fafaf5",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 11, color: C.textM, fontWeight: 600 }}>{title}</span>
        <span style={{ fontSize: 14.5, fontWeight: 700, color: C.text, fontFamily: "'Noto Serif SC', serif" }}>
          {entity_name}
        </span>
        {entity_type && (
          <span style={{
            fontSize: 10, padding: "1px 7px", borderRadius: 8,
            background: "rgba(122,170,152,0.15)", color: "#2a5040",
            border: "1px solid rgba(122,170,152,0.4)",
          }}>
            {TYPE_CN[entity_type] || entity_type}
          </span>
        )}
      </div>
      {properties && properties.length > 0 ? (
        <div style={{ fontSize: 12, lineHeight: 1.7 }}>
          {properties.map((p, i) => (
            <div key={i} style={{
              display: "flex", gap: 8, padding: "1px 0",
              borderBottom: i < properties.length - 1 ? `1px solid ${C.borderL}` : "none",
            }}>
              <span style={{ color: C.textM, minWidth: 64, flexShrink: 0 }}>{p.key}</span>
              <span style={{ color: C.brownDk, wordBreak: "break-all" }}>{p.value}</span>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ fontSize: 12, color: C.textL }}>（无详细属性）</div>
      )}
    </div>
  );
}

/**
 * 关系参考资料面板：点击一条边后展示。
 * props.data = { kind:"relation", source:{...}, target:{...}, relation:{type,description}, graph:{nodes,edges} }
 * 布局：关系信息（这条线代表的信息）+ 两端实体各自信息 + 只含两节点的力导向图。
 */
function RelationSourcePanel({ data, onNodeClick, onEdgeClick, trail, onTrailClick }) {
  if (!data) return null;
  const { source, target, relation, graph } = data;
  const relType = relation?.type || "";
  const relDesc = relation?.description || "";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* 面包屑导航 */}
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

      {/* 关系信息（这条线代表的信息） */}
      <div style={{
        flexShrink: 0, padding: "12px 16px", borderBottom: `1px solid ${C.border}`,
        background: "rgba(196,164,64,0.06)",
      }}>
        <div style={{ fontSize: 12, color: C.textM, fontWeight: 600, letterSpacing: 1, marginBottom: 6 }}>
          关系信息
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          {relType && (
            <span style={{
              fontSize: 10.5, padding: "1px 9px", borderRadius: 8,
              background: "rgba(196,164,64,0.16)", color: "#7a5c20",
              border: "1px solid rgba(196,164,64,0.5)", fontWeight: 600,
            }}>
              {relType}
            </span>
          )}
          <span style={{ fontSize: 13, color: C.text, lineHeight: 1.6, wordBreak: "break-all" }}>
            {relDesc || "（无描述）"}
          </span>
        </div>
      </div>

      {/* 两端实体各自信息 */}
      <div style={{
        flexShrink: 0, maxHeight: "44%", overflow: "auto",
        padding: "12px 16px", borderBottom: `1px solid ${C.border}`,
        display: "flex", flexDirection: "column", gap: 10,
      }}>
        <EntityCard title="实体 A" data={source} highlight />
        <EntityCard title="实体 B" data={target} />
      </div>

      {/* 力导向图：只显示两个节点与这条边 */}
      <div style={{ flex: 1, minHeight: 0, position: "relative" }}>
        <div style={{
          fontSize: 12, color: C.textM, fontWeight: 600, letterSpacing: 1,
          padding: "10px 16px 4px",
          display: "flex", justifyContent: "space-between", alignItems: "baseline",
        }}>
          <span>关系图谱 ({graph?.nodes?.length || 0}节点 · {graph?.edges?.length || 0}边)</span>
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
              无关系图谱数据
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default RelationSourcePanel;
