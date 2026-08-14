import { useState, useRef, useEffect, useCallback } from "react";
import C from "../constants/colors";
import ReferenceSidebar from "../components/ReferenceSidebar";

function renderMessageWithCitations(text, sourceIndex, onCitationClick) {
  if (!sourceIndex || Object.keys(sourceIndex).length === 0) return text;

  // 匹配 [数字] 格式的引用标记
  const parts = [];
  let lastIndex = 0;
  const regex = /\[(\d+)\]/g;
  let match;

  while ((match = regex.exec(text)) !== null) {
    // 添加匹配前的文本
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    const num = match[1];
    const source = sourceIndex[num];
    const tooltip = typeof source === 'object' ? source.desc : source;

    parts.push(
      <sup
        key={match.index}
        onClick={(e) => { e.stopPropagation(); onCitationClick && onCitationClick(num); }}
        style={{
          color: "#8a4520", cursor: "pointer", fontSize: 11,
          fontWeight: 600, textDecoration: "underline",
          textUnderlineOffset: 2,
        }}
        title={tooltip || ('来源索引 ' + num)}
      >[{num}]</sup>
    );

    lastIndex = match.index + match[0].length;
  }

  // 添加剩余文本
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

// 按引用在正文中首次出现的顺序重新编号 [N]（[2][3][1] → [1][2][3]），
// 并同步重排 source_index 的 key，保证角标点击仍对应到正确的来源。
function renumberCitations(text, sourceIndex) {
  if (!sourceIndex || !text) return { text, sourceIndex };
  const order = [];
  const seen = new Set();
  const regex = /\[(\d+)\]/g;
  let m;
  while ((m = regex.exec(text)) !== null) {
    if (!seen.has(m[1])) {
      seen.add(m[1]);
      order.push(m[1]);
    }
  }
  if (order.length === 0) return { text, sourceIndex };
  const remap = {};
  order.forEach((old, i) => { remap[old] = String(i + 1); });
  const newText = text.replace(/\[(\d+)\]/g, (full, num) => (remap[num] ? `[${remap[num]}]` : full));
  const newSI = {};
  Object.keys(sourceIndex).forEach((k) => { newSI[remap[k] || k] = sourceIndex[k]; });
  return { text: newText, sourceIndex: newSI };
}

function ResearchSection({ navigate }) {
  const [chatState, setChatState] = useState("landing");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);   // [{role, content}]
  const [loading, setLoading] = useState(false);
  const [useApi, setUseApi] = useState(true);     // 模型切换：true=API, false=本地Qwen
  const [providers, setProviders] = useState([]);  // [{id, label, configured, models:[{id,label}]}]
  const [selectedProvider, setSelectedProvider] = useState("deepseek");
  const [selectedModel, setSelectedModel] = useState("deepseek-chat");
  const [expandedThink, setExpandedThink] = useState({});
  const composingRef = useRef(false);
  const chatEndRef = useRef(null);
  const streamRef = useRef({ thinking: "", content: "" });  // 避免 StrictMode 双重调用

  // 参考资料右侧栏状态
  const [refPanel, setRefPanel] = useState({
    open: false, citationNum: null, sourceData: null,
    detailData: null, loading: false,
  });
  // 图谱节点跳转路径（面包屑）：[原始实体, ..., 当前实体]
  const [graphTrail, setGraphTrail] = useState([]);

  // 加载供应商+模型列表；供应商切换时自动选该供应商第一个模型
  useEffect(() => {
    fetch("/models").then(r => r.json()).then(data => {
      const list = data.providers || [];
      setProviders(list);
      // 自动选第一个已配置的供应商
      const first = list.find(p => p.configured);
      if (first && first.models.length > 0) {
        setSelectedProvider(first.id);
        setSelectedModel(first.models[0].id);
      }
    }).catch(() => {});
  }, []);

  const currentProvider = providers.find(p => p.id === selectedProvider);
  const providerModels = currentProvider ? currentProvider.models : [];

  const handleProviderChange = (provId) => {
    if (provId === "local") { setUseApi(false); return; }
    setUseApi(true);
    setSelectedProvider(provId);
    const p = providers.find(x => x.id === provId);
    if (p && p.models.length > 0) setSelectedModel(p.models[0].id);
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (overrideText) => {
    const q = (overrideText || input).trim();
    if (!q || loading) return;
    setChatState("chat");
    setInput("");

    const msgIdx = Date.now();
    streamRef.current = { thinking: "", content: "" };
    setMessages(prev => [...prev, { role: "user", content: q }]);
    setMessages(prev => [...prev, { _id: msgIdx, role: "assistant", content: "", thinking: "", _streaming: true }]);
    setLoading(true);
    // assistant 消息位于 user 之后（messages.length+1 索引），据此定位思考框
    const thinkKey = messages.length + 1;
    setExpandedThink(prev => ({ ...prev, [thinkKey]: true }));

    const updateMsg = (patch) => {
      setMessages(prev => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (!last || last._id !== msgIdx) return updated;
        Object.assign(last, patch);
        return updated;
      });
    };

    try {
      const res = await fetch("/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, use_api: useApi, model: useApi ? selectedModel : null }),
      });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      let pendingUpdate = null;
      const flushUpdate = () => {
        if (pendingUpdate) {
          updateMsg({ thinking: streamRef.current.thinking, content: streamRef.current.content });
          pendingUpdate = null;
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() || "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const evt = JSON.parse(line.slice(6));
            if (evt.type === "thinking") {
              streamRef.current.thinking += evt.content;
            } else if (evt.type === "answer") {
              streamRef.current.content += evt.content;
            } else if (evt.type === "done") {
              flushUpdate();
              // 按正文首次出现顺序重排引用编号，避免 [2][3][1] 这类乱序
              const si = evt.plan_log?.source_index;
              let finalContent = streamRef.current.content;
              let finalPlanLog = evt.plan_log || null;
              if (si && finalContent) {
                const rn = renumberCitations(finalContent, si);
                finalContent = rn.text;
                finalPlanLog = { ...evt.plan_log, source_index: rn.sourceIndex };
              }
              updateMsg({ _streaming: false, content: finalContent, plan_log: finalPlanLog });
            } else if (evt.type === "error") {
              updateMsg({ content: "请求失败：" + evt.message, _streaming: false });
            }
            // 节流：每 60ms 最多更新一次 UI，避免闪烁
            if (!pendingUpdate && (evt.type === "thinking" || evt.type === "answer")) {
              pendingUpdate = setTimeout(flushUpdate, 60);
            }
          } catch {}
        }
      }
      flushUpdate();
    } catch (e) {
      updateMsg({ content: "请求失败：" + e.message, _streaming: false });
    }
    setLoading(false);
  };

  // 角标点击 → 打开右侧参考资料面板
  const handleCitationClick = useCallback(async (num) => {
    // 从最新消息中查找 source_index
    let sourceData = null;
    for (let i = messages.length - 1; i >= 0; i--) {
      const si = messages[i]?.plan_log?.source_index;
      if (si && si[num]) {
        sourceData = si[num];
        break;
      }
    }
    if (!sourceData) return;

    // sourceData 可能是字符串（旧格式）或对象（新格式）
    const isObject = typeof sourceData === 'object';
    const sourceType = isObject ? sourceData.source_type : null;

    setRefPanel({ open: true, citationNum: num, sourceData, detailData: null, loading: true });

    // 重置图谱跳转路径：图谱源以来源实体为起点，其余类型清空
    setGraphTrail(sourceType === 'graph' && sourceData.entity_name ? [{ id: null, name: sourceData.entity_name }] : []);

    // 如果有结构化元数据，获取详细信息
    if (sourceType === 'graph' && sourceData.entity_name) {
      try {
        const res = await fetch(`/reference/graph?entity_name=${encodeURIComponent(sourceData.entity_name)}&depth=2`);
        const detail = await res.json();
        setRefPanel(prev => ({ ...prev, detailData: detail, loading: false }));
      } catch (e) {
        setRefPanel(prev => ({ ...prev, detailData: { error: e.message }, loading: false }));
      }
    } else if (sourceType === 'sql' && sourceData.doc_title) {
      // SQL 无关联、无需实时生成：复用检索阶段已随 source_index 下发的 detail_text，不再查库。
      if (sourceData.detail_text) {
        setRefPanel(prev => ({ ...prev, detailData: { detail_text: sourceData.detail_text, doc_title: sourceData.doc_title }, loading: false }));
      } else {
        try {
          const res = await fetch(`/reference/sql?title=${encodeURIComponent(sourceData.doc_title)}`);
          const detail = await res.json();
          setRefPanel(prev => ({ ...prev, detailData: detail, loading: false }));
        } catch (e) {
          setRefPanel(prev => ({ ...prev, detailData: { error: e.message }, loading: false }));
        }
      }
    } else if (sourceType === 'sql' && sourceData.author_name) {
      try {
        const res = await fetch(`/reference/sql?author_name=${encodeURIComponent(sourceData.author_name)}`);
        const detail = await res.json();
        setRefPanel(prev => ({ ...prev, detailData: detail, loading: false }));
      } catch (e) {
        setRefPanel(prev => ({ ...prev, detailData: { error: e.message }, loading: false }));
      }
    } else {
      // 文本/向量类型或无结构化数据 → 纯文本展示
      setRefPanel(prev => ({ ...prev, detailData: { fallback: true }, loading: false }));
    }
  }, [messages]);

  // 图谱节点点击 → 跳转到该节点，展开同样的介绍与力导向图
  // node 为节点对象 {id, name, label, ...}（也可兼容字符串 name）
  const handleNodeJump = useCallback(async (node) => {
    const name = typeof node === "object" ? node?.name : node;
    const id = typeof node === "object" ? node?.id : null;
    if (!name && !id) return;
    setRefPanel(prev => ({ ...prev, loading: true }));
    setGraphTrail(prev => [...prev, { id: id || null, name }]);
    const q = id ? `entity_id=${encodeURIComponent(id)}` : `entity_name=${encodeURIComponent(name)}`;
    try {
      const res = await fetch(`/reference/graph?${q}&depth=2`);
      const detail = await res.json();
      setRefPanel(prev => ({ ...prev, detailData: detail, loading: false }));
    } catch (e) {
      setRefPanel(prev => ({ ...prev, detailData: { error: e.message }, loading: false }));
    }
  }, []);

  // 面包屑点击 → 回到该节点（截断后续路径）
  const handleTrailBack = useCallback(async (index) => {
    const item = graphTrail[index];
    if (!item) return;
    const name = typeof item === "object" ? item.name : item;
    const id = typeof item === "object" ? item.id : null;
    setGraphTrail(prev => prev.slice(0, index + 1));
    setRefPanel(prev => ({ ...prev, loading: true }));
    const q = id ? `entity_id=${encodeURIComponent(id)}` : `entity_name=${encodeURIComponent(name)}`;
    try {
      const res = await fetch(`/reference/graph?${q}&depth=2`);
      const detail = await res.json();
      setRefPanel(prev => ({ ...prev, detailData: detail, loading: false }));
    } catch (e) {
      setRefPanel(prev => ({ ...prev, detailData: { error: e.message }, loading: false }));
    }
  }, [graphTrail]);

  const selectStyle = {
    padding: "4px 8px", borderRadius: 6, border: `1px solid ${C.border}`,
    background: C.bg, fontSize: 12, color: C.text, fontFamily: "inherit",
    cursor: "pointer", outline: "none",
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
                display: "flex", flexDirection: "column",
                alignItems: msg.role === "user" ? "flex-end" : "flex-start",
                marginBottom: 16,
              }}>
                {/* 思考过程（assistant + 有 thinking 内容或正在流式传输时显示） */}
                {msg.role === "assistant" && (msg.thinking || msg._streaming) ? (
                  <div style={{
                    maxWidth: "75%", marginBottom: 8,
                    border: `1px solid ${C.border}`, borderRadius: 10,
                    background: "#fafaf5", overflow: "hidden",
                  }}>
                    <div onClick={() => setExpandedThink(prev => ({ ...prev, [i]: !prev[i] }))}
                      style={{
                        padding: "8px 14px", cursor: "pointer",
                        display: "flex", alignItems: "center", gap: 8,
                        fontSize: 12, color: C.textM, userSelect: "none",
                        borderBottom: expandedThink[i] ? `1px solid ${C.border}` : "none",
                      }}>
                      <span style={{ transform: expandedThink[i] ? "rotate(90deg)" : "rotate(0deg)", transition: "transform .15s", fontFamily: "monospace" }}>▶</span>
                      <span>思考过程（RACE 前置分析）{msg._streaming && " ···"}</span>
                    </div>
                    {(expandedThink[i] || msg._streaming) && (
                      <div ref={msg._streaming ? el => { if (el) el.scrollTop = el.scrollHeight; } : null} style={{
                        padding: "10px 14px", fontSize: 12.5, color: "#888",
                        lineHeight: 1.65, whiteSpace: "pre-wrap",
                        height: msg._streaming ? 280 : undefined,
                        maxHeight: 360, overflow: "auto",
                        fontFamily: "'Noto Sans SC', sans-serif",
                      }}>
                        {msg.thinking}
                        {msg._streaming && <span className="stream-cursor">|</span>}
                      </div>
                    )}
                  </div>
                ) : null}
                {/* 正文 */}
                {(msg.role !== "assistant" || msg.content || msg._streaming) ? (
                  <div style={{
                    maxWidth: "75%", padding: "12px 18px",
                    borderRadius: msg.role === "user" ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
                    background: msg.role === "user" ? C.bg : C.white,
                    border: `1px solid ${C.border}`,
                    fontSize: 14, color: C.text, lineHeight: 1.7, whiteSpace: "pre-wrap",
                  }}>
                    {msg.role === "assistant" && msg.plan_log?.source_index ? (
                      renderMessageWithCitations(msg.content, msg.plan_log.source_index, handleCitationClick)
                    ) : (
                      msg.content
                    )}
                    {msg._streaming && <span className="stream-cursor">|</span>}
                  </div>
                ) : null}
                {/* 来源提示 — 点击文中编号查看可视化详情 */}
                {msg.role === "assistant" && !msg._streaming && msg.plan_log?.source_index && (() => {
                  const sourceKeys = Object.keys(msg.plan_log.source_index);
                  if (sourceKeys.length === 0) return null;
                  return (
                    <div style={{
                      maxWidth: "75%", marginTop: 6, padding: "6px 14px",
                      background: "#fafaf5", borderRadius: 8,
                      border: `1px solid ${C.border}`,
                      fontSize: 11.5, color: C.textM,
                    }}>
                      点击文中<sup style={{color:"#8a4520",fontWeight:600}}>[N]</sup>编号查看{sourceKeys.length}条参考资料可视化详情
                    </div>
                  );
                })()}
              </div>
            ))}
            {loading && !messages.some(m => m._streaming) && (
              <div style={{ color: C.textM, fontSize: 13, padding: "8px 18px" }}>思考中...</div>
            )}
            <div ref={chatEndRef} />
          </div>
        )}

        {/* Input */}
        <div style={{ borderTop: `1px solid ${C.border}`, padding: "16px 24px", background: C.white }}>
          {/* 模型选择：供应商 → 具体模型 */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
            <span style={{ fontSize: 12, color: C.textM }}>引擎:</span>
            <select
              value={useApi ? selectedProvider : "local"}
              onChange={e => handleProviderChange(e.target.value)}
              style={selectStyle}>
              <option value="local">本地 Qwen</option>
              <option disabled>── 云 API ──</option>
              {providers.map(p => (
                <option key={p.id} value={p.id} disabled={!p.configured}>
                  {p.label}{p.configured ? "" : "（未配置）"}
                </option>
              ))}
            </select>
            {useApi && providerModels.length > 0 && (
              <select
                value={selectedModel}
                onChange={e => setSelectedModel(e.target.value)}
                style={selectStyle}>
                {providerModels.map(m => (
                  <option key={m.id} value={m.id}>{m.label}</option>
                ))}
              </select>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ flex: 1, background: C.bg, border: `1px solid ${C.border}`, borderRadius: 12, padding: "10px 16px", display: "flex", alignItems: "center", gap: 8 }}>
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onCompositionStart={() => { composingRef.current = true; }}
                onCompositionEnd={e => { composingRef.current = false; setInput(e.target.value); }}
                onKeyDown={e => { if (e.key === "Enter" && !composingRef.current) handleSend(); }}
                placeholder="输入问题..."
                disabled={loading}
                style={{ flex: 1, border: "none", outline: "none", fontSize: 14, background: "transparent", fontFamily: "inherit", color: C.text }}
              />
              <button onClick={() => handleSend()} disabled={loading}
                style={{ background: "none", border: "none", cursor: "pointer", padding: 4 }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={C.brownBtn} strokeWidth="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 参考资料右侧栏 */}
      <ReferenceSidebar
        open={refPanel.open}
        citationNum={refPanel.citationNum}
        sourceData={refPanel.sourceData}
        detailData={refPanel.detailData}
        loading={refPanel.loading}
        onNodeClick={handleNodeJump}
        trail={graphTrail}
        onTrailClick={handleTrailBack}
        onClose={() => { setGraphTrail([]); setRefPanel({ open: false, citationNum: null, sourceData: null, detailData: null, loading: false }); }}
      />
    </div>
  );
}

export default ResearchSection;
