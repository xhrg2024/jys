import C from "../constants/colors";

/* ─────────────── SHARED: TOP NAV ─────────────── */
function TopNav({ page, navigate }) {
  const items = [
    { label: "首页", key: "home" },
    { label: "资源浏览", key: "resources-overview" },
    { label: "智能研究", key: "research-home" },
    { label: "图谱导入", key: "import" },
    { label: "关于我们", key: "about" },
  ];
  return (
    <nav style={{
      display: "flex", background: C.bg, borderBottom: `1px solid ${C.border}`,
      height: 52, flexShrink: 0, fontFamily: "'Noto Serif SC', serif",
    }}>
      {items.map(item => {
        const active = (item.label === "首页" && page === "home") ||
          (item.label === "资源浏览" && page.startsWith("resources")) ||
          (item.label === "智能研究" && page.startsWith("research")) ||
          (item.label === "图谱导入" && page === "import") ||
          (item.label === "关于我们" && page === "about");
        return (
          <div key={item.label} onClick={() => navigate(item.key)} style={{
            flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 15, color: active ? C.brownBtn : C.text, fontWeight: active ? 600 : 400,
            cursor: "pointer", borderBottom: active ? `2px solid ${C.brownBtn}` : "2px solid transparent",
            transition: "color .15s",
          }}>{item.label}</div>
        );
      })}
    </nav>
  );
}

export default TopNav;