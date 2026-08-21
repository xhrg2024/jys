import C from "../constants/colors";

/* ─────────────── SHARED: RESOURCE SIDEBAR ─────────────── */
function ResourceSidebar({ tab, setTab, navigate }) {
  const items = [
    { key: "overview", label: "数据概览" },
    { key: "explore",  label: "实体与关系探索" },
    { key: "path",     label: "路径查询" },
    { key: "global",   label: "全局浏览" },
  ];
  return (
    <aside style={{ width: 200, background: C.sidebar, flexShrink: 0, display: "flex", flexDirection: "column", borderRight: `1px solid ${C.border}` }}>
      <div style={{ flex: 1 }}>
        {items.map(item => (
          <div key={item.key} onClick={() => setTab(item.key)} style={{
            padding: "18px 24px", fontSize: 14.5, color: C.text, cursor: "pointer",
            background: tab === item.key ? C.sidebarAct : "transparent",
            borderLeft: tab === item.key ? `3px solid ${C.brownBtn}` : "3px solid transparent",
            fontWeight: tab === item.key ? 600 : 400,
            transition: "background .15s",
          }}>{item.label}</div>
        ))}
      </div>
      <div style={{ padding: "18px 16px", display: "flex", alignItems: "center", gap: 10, borderTop: `1px solid ${C.border}` }}>
        <div style={{ width: 32, height: 32, borderRadius: "50%", border: `1.5px solid ${C.textL}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={C.textL} strokeWidth="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
        </div>
        <span style={{ fontSize: 13, color: C.textM }}>username</span>
      </div>
    </aside>
  );
}

export default ResourceSidebar;