import { createContext, useCallback, useContext, useEffect, useState } from "react";
import LoginModal from "../components/LoginModal";

const AuthContext = createContext(null);

const TOKEN_KEY = "ai_user_token";
const NAME_KEY = "ai_user_name";

function readStorage(key) {
  try { return localStorage.getItem(key); } catch (_) { return null; }
}
function writeStorage(key, val) {
  try { localStorage.setItem(key, val); } catch (_) {}
}
function removeStorage(key) {
  try { localStorage.removeItem(key); } catch (_) {}
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => readStorage(NAME_KEY) || null);
  const [token, setToken] = useState(() => readStorage(TOKEN_KEY) || null);
  const [loginOpen, setLoginOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const clearAuth = useCallback(() => {
    setUser(null);
    setToken(null);
    removeStorage(TOKEN_KEY);
    removeStorage(NAME_KEY);
  }, []);

  // 启动时校验存量 token：401 视为失效并清空，网络异常保留本地状态（下次请求再校验）
  useEffect(() => {
    if (!token) return;
    let alive = true;
    (async () => {
      try {
        const res = await fetch("/auth/me");
        const data = await res.json();
        if (!alive) return;
        setUser(data.username);
        writeStorage(NAME_KEY, data.username);
      } catch (e) {
        if (!alive) return;
        if (e && e.status === 401) clearAuth();
      }
    })();
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const applyAuth = useCallback((username, tok) => {
    setUser(username);
    setToken(tok);
    writeStorage(TOKEN_KEY, tok);
    writeStorage(NAME_KEY, username);
    setLoginOpen(false);
    setError("");
  }, []);

  const login = useCallback(async (username, password) => {
    setBusy(true);
    setError("");
    try {
      const res = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      applyAuth(data.username, data.token);
      return true;
    } catch (e) {
      setError(e && e.status ? (e.message || "登录失败") : "网络错误，请重试");
      return false;
    } finally {
      setBusy(false);
    }
  }, [applyAuth]);

  const register = useCallback(async (username, password) => {
    setBusy(true);
    setError("");
    try {
      const res = await fetch("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      applyAuth(data.username, data.token);
      return true;
    } catch (e) {
      setError(e && e.status ? (e.message || "注册失败") : "网络错误，请重试");
      return false;
    } finally {
      setBusy(false);
    }
  }, [applyAuth]);

  const logout = useCallback(async () => {
    try {
      await fetch("/auth/logout", { method: "POST" });
    } catch (_) { /* 忽略登出接口失败，本地照常清登录态 */ }
    clearAuth();
  }, [clearAuth]);

  const openLogin = useCallback(() => { setError(""); setLoginOpen(true); }, []);
  const closeLogin = useCallback(() => { setLoginOpen(false); setError(""); }, []);

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, openLogin, closeLogin }}>
      {children}
      {loginOpen && (
        <LoginModal
          busy={busy}
          error={error}
          onLogin={login}
          onRegister={register}
          onClose={closeLogin}
        />
      )}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
