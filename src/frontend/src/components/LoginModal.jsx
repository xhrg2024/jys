import { useState } from "react";
import C from "../constants/colors";

const inputStyle = {
  width: "100%", padding: "9px 12px", marginBottom: 10,
  borderRadius: 8, border: `1px solid ${C.border}`, background: "#fff",
  fontSize: 13.5, color: C.text, outline: "none", boxSizing: "border-box",
};

function LoginModal({ busy, error, onLogin, onRegister, onClose }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password) return;
    const fn = mode === "login" ? onLogin : onRegister;
    await fn(username.trim(), password);
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 300,
        display: "flex", alignItems: "center", justifyContent: "center",
        background: "rgba(0,0,0,0.25)",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 340, maxWidth: "92vw", background: C.white, borderRadius: 12,
          boxShadow: "0 12px 40px rgba(0,0,0,0.2)", padding: "22px 24px 18px",
          fontFamily: "'Noto Serif SC', 'Noto Sans SC', 'PingFang SC', sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: C.text }}>
            {mode === "login" ? "登录" : "注册"}
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", cursor: "pointer", fontSize: 18, color: C.textM, padding: "2px 6px" }}
          >
            ✕
          </button>
        </div>

        <form onSubmit={submit}>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="用户名"
            autoFocus
            style={inputStyle}
          />
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            placeholder="密码（至少 4 位）"
            style={inputStyle}
          />
          {error && <div style={{ color: "#a04040", fontSize: 12.5, margin: "-2px 0 8px" }}>{error}</div>}
          <button
            type="submit"
            disabled={busy}
            style={{
              width: "100%", marginTop: 6, padding: "10px 0", borderRadius: 8, border: "none",
              background: C.brownBtn, color: "#fff", fontSize: 14, fontWeight: 600, cursor: busy ? "not-allowed" : "pointer",
              opacity: busy ? 0.6 : 1, fontFamily: "inherit",
            }}
          >
            {busy ? "请稍候…" : (mode === "login" ? "登录" : "注册并登录")}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: 12, fontSize: 12.5, color: C.textM }}>
          {mode === "login" ? (
            <>没有账号？<span onClick={() => setMode("register")} style={{ color: C.brownBtn, cursor: "pointer", fontWeight: 600 }}>注册</span></>
          ) : (
            <>已有账号？<span onClick={() => setMode("login")} style={{ color: C.brownBtn, cursor: "pointer", fontWeight: 600 }}>登录</span></>
          )}
        </div>
      </div>
    </div>
  );
}

export default LoginModal;
