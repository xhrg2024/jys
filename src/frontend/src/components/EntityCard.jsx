import C from "../constants/colors";

/* ─────────────── SHARED: ENTITY DETAIL CARD ─────────────── */
function EntityCard({ navigate }) {
  return (
    <div style={{ background: C.white, borderRadius: 14, padding: "20px 18px", border: `1px solid ${C.border}`, minWidth: 230, boxShadow: "0 2px 12px rgba(0,0,0,0.06)" }}>
      <div style={{ fontSize: 17, fontWeight: 700, color: C.text, marginBottom: 8, fontFamily: "'Noto Serif SC', serif" }}>馬國翰</div>
      <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
        <span style={{ background: C.tagGreen, color: C.tagGreenT, borderRadius: 10, padding: "2px 9px", fontSize: 11 }}>輯佚者</span>
        <span style={{ background: C.tagBeig, color: C.tagBeigT, borderRadius: 10, padding: "2px 9px", fontSize: 11 }}>乾嘉學派</span>
      </div>
      <div style={{ fontSize: 12, color: C.textL, marginBottom: 2 }}>生卒</div>
      <div style={{ fontSize: 13, color: C.text, marginBottom: 10 }}>1794—1857</div>
      <div style={{ fontSize: 12, color: C.textL, marginBottom: 2 }}>代表作</div>
      <div style={{ fontSize: 13, color: C.text, marginBottom: 10 }}>玉函山房辑佚書（594種）</div>
      <div style={{ fontSize: 12, color: C.textL, marginBottom: 6 }}>直接關聯節點（點擊跳轉）</div>
      <div style={{ display: "flex", gap: 10, marginBottom: 14 }}>
        {["玉函山房辑佚書", "乾嘉學派"].map(t => (
          <span key={t} style={{ fontSize: 12, color: C.brown, cursor: "pointer", textDecoration: "underline" }}>{t}</span>
        ))}
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        {[["深入问答", () => navigate("research-chat")], ["查看书籍", () => {}]].map(([label, fn]) => (
          <button key={label} onClick={fn} style={{
            flex: 1, padding: "8px 0", border: `1px solid ${C.border}`, borderRadius: 8,
            background: C.bg, color: C.text, fontSize: 12.5, cursor: "pointer", fontFamily: "inherit",
          }}>{label}</button>
        ))}
      </div>
    </div>
  );
}

export default EntityCard;