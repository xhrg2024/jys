import C from "../constants/colors";
import { useAuth } from "../context/AuthContext";

/* ─────────────── SHARED: TOP NAV ─────────────── */
function TopNav({ page, navigate }) {
  const { user, openLogin, logout } = useAuth();
  const items = [
    { label: "首页", key: "home" },
    { label: "智能研究", key: "research" },
  ];
  return (
    <nav style={{
      display: "flex", background: C.bg, borderBottom: `1px solid ${C.border}`,
      height: 52, flexShrink: 0, fontFamily: "'Noto Serif SC', serif",
    }}>
      <div style={{ flex: 1, display: "flex" }}>
        {items.map(item => {
          const active = (item.label === "首页" && page === "home") ||
            (item.label === "智能研究" && page === "research");
          return (
            <div key={item.label} onClick={() => navigate(item.key)} style={{
              flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 15, color: active ? C.brownBtn : C.text, fontWeight: active ? 600 : 400,
              cursor: "pointer", borderBottom: active ? `2px solid ${C.brownBtn}` : "2px solid transparent",
              transition: "color .15s",
            }}>{item.label}</div>
          );
        })}
      </div>

      {/* 右上角：登录/用户小按钮（网页嵌入，保持小巧） */}
      <div style={{
        flexShrink: 0, display: "flex", alignItems: "center", gap: 8,
        padding: "0 14px", borderLeft: `1px solid ${C.border}`,
      }}>
        {user ? (
          <>
            <span style={{ fontSize: 13, color: C.textM, maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={user}>
              {user}
            </span>
            <button
              onClick={logout}
              style={{
                background: "none", border: `1px solid ${C.border}`, borderRadius: 14,
                padding: "3px 12px", cursor: "pointer", fontSize: 12, color: C.textM,
                fontFamily: "inherit", transition: "color .15s",
              }}
              onMouseEnter={(e) => { e.currentTarget.style.color = C.brownBtn; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = C.textM; }}
            >退出</button>
          </>
        ) : (
          <button
            onClick={openLogin}
            style={{
              background: C.brownBtn, border: "none", borderRadius: 14,
              padding: "4px 16px", cursor: "pointer", fontSize: 12.5, color: "#fff",
              fontWeight: 600, fontFamily: "inherit",
            }}
          >登录</button>
        )}
      </div>
    </nav>
  );
}

export default TopNav;
