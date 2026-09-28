import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import ErrorBoundary from "./components/ErrorBoundary";

// 统一 fetch 包装：
// 1) 若后端配置了 API_TOKEN，为同源请求注入 Authorization 头；
// 2) 检查 res.ok，非 2xx 抛出携带后端 detail 的错误——否则各页面会把
//    FastAPI 的 {"detail": ...} 错误体当成功 JSON 解析（500 时转圈/误报成功）。
const API_TOKEN = typeof __API_TOKEN__ !== "undefined" ? __API_TOKEN__ : "";
const _fetch = window.fetch.bind(window);
window.fetch = async (input, init = {}) => {
  const url = typeof input === "string" ? input : input.url;
  const sameOrigin = url.startsWith("/") || url.startsWith(window.location.origin);
  if (sameOrigin) {
    const userToken = localStorage.getItem("ai_user_token");
    if (API_TOKEN || userToken) {
      const headers = new Headers(init.headers || {});
      if (API_TOKEN) headers.set("Authorization", `Bearer ${API_TOKEN}`);
      if (userToken) headers.set("X-User-Token", userToken);
      init = { ...init, headers };
    }
  }
  const res = await _fetch(input, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body && body.detail) detail = body.detail;
    } catch (_) { /* 非 JSON 错误体，忽略 */ }
    const err = new Error(detail || `请求失败 (HTTP ${res.status})`);
    err.status = res.status;
    throw err;
  }
  return res;
};

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
