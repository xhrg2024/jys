import { Component } from "react";

// 顶层渲染错误兜底：捕获 commit 阶段的异常（如 removeChild NotFoundError），
// 避免单个组件渲染崩溃导致整页白屏。
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("渲染错误已捕获:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          padding: "60px 24px", textAlign: "center",
          fontFamily: "'Noto Serif SC', 'Noto Sans SC', 'PingFang SC', sans-serif",
        }}>
          <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 12 }}>页面渲染出错</div>
          <div style={{ fontSize: 13, color: "#888", marginBottom: 20, wordBreak: "break-all" }}>
            {String(this.state.error)}
          </div>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: "8px 24px", borderRadius: 8, border: "none",
              background: "#8a4520", color: "#fff", cursor: "pointer",
              fontSize: 14, fontFamily: "inherit",
            }}
          >
            刷新页面
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
