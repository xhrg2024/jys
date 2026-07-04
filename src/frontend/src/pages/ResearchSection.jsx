import { useState, useRef, useEffect } from "react";
import C from "../constants/colors";

function ResearchSection({ navigate }) {
  const [chatState, setChatState] = useState("landing");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);   // [{role, content}]
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (overrideText) => {
    const q = (overrideText || input).trim();
    if (!q || loading) return;
    setChatState("chat");
    setInput("");

    const userMsg = { role: "user", content: q };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.answer }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: "assistant", content: "请求失败：" + e.message }]);
    }
    setLoading(false);
  };

  const suggestQuestions = [
    "《玉函山房辑佚书》有多少卷？",
    "马国翰和王仁俊有什么关系？",
    "辑佚的三原则是什么？",
    "清代辑佚学经历了哪几个阶段？",
  ];

  return (
    <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
      {/* Sidebar */}
      <div style={{
        width: sidebarCollapsed ? 52 : 200, background: C.sidebar, flexShrink: 0,
        borderRight: `1px solid ${C.border}`, display: "flex", flexDirection: "column",
        transition: "width .2s",
      }}>
        <div style={{ padding: "12px", display: "flex", justifyContent: sidebarCollapsed ? "center" : "flex-end" }}>
          <button onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            style={{ background: "none", border: "none", cursor: "pointer", padding: 4 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={C.textM} strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/>
            </svg>
          </button>
        </div>
        {[
          { icon: "?", label: "智能问答", action: () => {} },
          { icon: "↓", label: "数据下载", action: () => navigate("data-download") },
          { icon: "⊙", label: "关系探索", action: () => navigate("resources-explore") },
        ].map(item => (
          <div key={item.label} onClick={item.action} style={{
            padding: sidebarCollapsed ? "16px 0" : "14px 24px", display: "flex",
            alignItems: "center", gap: 10, cursor: "pointer",
            justifyContent: sidebarCollapsed ? "center" : "flex-start",
          }}>
            <span style={{ fontSize: sidebarCollapsed ? 18 : 15, color: C.textM, fontFamily: "monospace" }}>{item.icon}</span>
            {!sidebarCollapsed && <span style={{ fontSize: 13.5, color: C.text }}>{item.label}</span>}
          </div>
        ))}
        <div style={{ flex: 1 }} />
      </div>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {chatState === "landing" ? (
          /* Landing */
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 20, padding: 40 }}>
            <div style={{ fontSize: 26, fontWeight: 700, color: C.text, fontFamily: "'Noto Serif SC', serif", letterSpacing: 2 }}>
              中国古代辑佚研究智能体
            </div>
            <div style={{ color: C.gold, fontSize: 13.5, textAlign: "center", maxWidth: 460, marginBottom: 16 }}>
              面向知识检索与关系分析的智能体，支持自然语言问答、知识图谱探索
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, width: 360 }}>
              {suggestQuestions.map((q, i) => (
                <button key={i} onClick={() => handleSend(q)}
                  style={{
                    padding: "12px 18px", border: `1px solid ${C.border}`, borderRadius: 10,
                    background: C.white, cursor: "pointer", textAlign: "left", fontSize: 13.5,
                    color: C.text, fontFamily: "inherit",
                  }}>{q}</button>
              ))}
            </div>
          </div>
        ) : (
          /* Chat messages */
          <div style={{ flex: 1, overflow: "auto", padding: "20px 28px" }}>
            {messages.map((msg, i) => (
              <div key={i} style={{
                display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                marginBottom: 16,
              }}>
                <div style={{
                  maxWidth: "75%", padding: "12px 18px", borderRadius: msg.role === "user" ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
                  background: msg.role === "user" ? C.bg : C.white,
                  border: `1px solid ${C.border}`,
                  fontSize: 14, color: C.text, lineHeight: 1.7, whiteSpace: "pre-wrap",
                }}>
                  {msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ color: C.textM, fontSize: 13, padding: "8px 18px" }}>思考中...</div>
            )}
            <div ref={chatEndRef} />
          </div>
        )}

        {/* Input */}
        <div style={{ borderTop: `1px solid ${C.border}`, padding: "16px 24px", background: C.white }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ flex: 1, background: C.bg, border: `1px solid ${C.border}`, borderRadius: 12, padding: "10px 16px", display: "flex", alignItems: "center", gap: 8 }}>
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSend()}
                placeholder="输入问题..."
                disabled={loading}
                style={{ flex: 1, border: "none", outline: "none", fontSize: 14, background: "transparent", fontFamily: "inherit" }}
              />
              <button onClick={() => handleSend()} disabled={loading}
                style={{ background: "none", border: "none", cursor: "pointer", padding: 4 }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={C.brownBtn} strokeWidth="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ResearchSection;
