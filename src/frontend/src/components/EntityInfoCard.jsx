import C from "../constants/colors";

// 实体类型 label → 中文（展示用）
const LABEL_CN = {
  Scholar: "学者", Compilation: "辑本", Time: "时期", Method: "方法",
  Methodology: "方法", Academic: "学术", Leishu: "类书", Entity: "实体",
};

// 属性值格式化：列表转顿号分隔，其余转字符串
const fmtVal = (v) => (Array.isArray(v) ? v.filter(Boolean).join("、") : String(v ?? ""));

/* ─────────────── 实体信息卡（复用组件）───────────────
 * 入参 entityInfo：/entity/{name} 返回的 {id, name, label, properties}
 * 结构化渲染实体名称 + 类型标签 + 属性网格。供实体探索页与路径查询页共用。
 */
function EntityInfoCard({ entityInfo }) {
  if (!entityInfo) return null;
  const props = entityInfo.properties || {};
  return (
    <div style={{ background: C.white, borderRadius: 12, border: `1px solid ${C.border}`, padding: 20 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
        <h3 style={{ fontSize: 18, fontWeight: 700, color: C.text, margin: 0, fontFamily: "'Noto Serif SC', serif" }}>
          {entityInfo.name}
        </h3>
        {entityInfo.label && (
          <span style={{
            fontSize: 11, color: C.brownBtn, background: "rgba(138,69,32,0.08)",
            padding: "2px 10px", borderRadius: 12, border: `1px solid rgba(138,69,32,0.2)`,
          }}>
            {LABEL_CN[entityInfo.label] || entityInfo.label}
          </span>
        )}
      </div>
      {Object.keys(props).length > 0 ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 10 }}>
          {Object.entries(props).map(([k, v]) => (
            <div key={k} style={{ background: "#faf7f0", borderRadius: 8, padding: "8px 12px", border: `1px solid ${C.borderL}` }}>
              <div style={{ fontSize: 11, color: C.textL, marginBottom: 3 }}>{k}</div>
              <div style={{ fontSize: 13, color: C.text, lineHeight: 1.5 }}>{fmtVal(v)}</div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ fontSize: 13, color: C.textL }}>该实体暂无属性信息</div>
      )}
    </div>
  );
}

export default EntityInfoCard;
