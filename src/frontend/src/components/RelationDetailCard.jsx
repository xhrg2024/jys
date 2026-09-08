import C from "../constants/colors";

/* ─────────────── 关系详情卡（复用组件）───────────────
 * 入参 relation：点击连线得到的 {fromName, toName, type, description}
 * 展示两端实体名 + 关系类型 + 关系描述。供实体探索页与路径查询页共用。
 */
function RelationDetailCard({ relation }) {
  if (!relation) return null;
  return (
    <div style={{ background: "rgba(138,69,32,0.04)", borderRadius: 12, border: `1px solid rgba(138,69,32,0.2)`, padding: 14 }}>
      <div style={{ fontSize: 12, color: C.textL, marginBottom: 6 }}>关系详情</div>
      <div style={{ fontSize: 14, color: C.text, fontWeight: 600 }}>
        {relation.fromName}
        <span style={{ color: C.brownBtn, margin: "0 8px" }}>—{relation.type || "相关"}→</span>
        {relation.toName}
      </div>
      {relation.description && (
        <div style={{ fontSize: 12.5, color: C.textM, marginTop: 6, lineHeight: 1.6 }}>
          {relation.description}
        </div>
      )}
    </div>
  );
}

export default RelationDetailCard;
