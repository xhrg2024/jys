import { useState, useRef, useEffect, useCallback } from "react";
import C from "../constants/colors";
import ReferenceSidebar from "../components/ReferenceSidebar";

// 浅色主题（默认古籍暖色风）+ 深色主题补充语义键
const LIGHT_C = {
  ...C,
  thinkBg: "#fafaf5",        // 思考框背景
  retrievalBg: "#f5f7fa",    // 检索过程背景
  thinkText: "#888",         // 思考内容文字
  previewText: "#999",       // 检索结果预览文字
  citeColor: "#8a4520",      // [n] 角标颜色
  inputBg: C.bg,             // 输入框背景
};

// 深色沉浸主题：深度思考模式开启时，整体切换为墨色/深蓝紫风格
const DARK_C = {
  ...C,
  bg: "#17141f",            // 主背景：深墨
  sidebar: "#120f1a",       // 侧栏：更深
  sidebarAct: "#2a2438",
  sidebarHov: "#211c2e",
  white: "#201c2e",         // 卡片/气泡底：深紫灰
  brown: "#c48a6a",
  brownBtn: "#c4a240",      // 强调金
  brownDk: "#d9b878",
  border: "#342e44",
  borderL: "#2a2538",
  text: "#e7e1d3",          // 主文字：米白
  textM: "#b3a99b",
  textL: "#857c6e",
  gold: "#c4a240",
  thinkBg: "#221e30",
  retrievalBg: "#1d1930",
  thinkText: "#a49bb8",
  previewText: "#8d86a0",
  citeColor: "#e0b64a",
  inputBg: "#14111d",
};

function renderMessageWithCitations(text, sourceIndex, onCitationClick, citeColor = "#8a4520") {
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
          color: citeColor, cursor: "pointer", fontSize: 11,
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

// 检索工具名 → 中文标签（深度思考模式「检索过程」展示用）
const TOOL_LABELS = {
  kg_explore_entity: "图谱·实体详情",
  kg_explore_relation: "图谱·关系探索",
  kg_find_entities: "图谱·查实体",
  kg_get_entity_relations: "图谱·实体关系",
  kg_find_relation_between: "图谱·实体间关系",
  kg_list_by_type: "图谱·按类型列出",
  vector_search: "向量·语义检索",
  search_document: "SQL·文献详情",
  search_author: "SQL·作者",
  search_full_text: "SQL·全文",
  search_titles: "SQL·篇目",
  browse_documents: "SQL·浏览文献",
};

// 工具参数 → 简短字符串（如 {name:"马国翰"} → "name=马国翰"）
function formatToolArgs(args) {
  if (!args || typeof args !== "object") return "";
  const entries = Object.entries(args).filter(([, v]) => v !== "" && v != null);
  if (entries.length === 0) return "";
  return entries.map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : v}`).join("，");
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
  const [expandedRetrieval, setExpandedRetrieval] = useState({});
  const [deepMode, setDeepMode] = useState(false);   // 深度思考模式开关
  const composingRef = useRef(false);
  const chatEndRef = useRef(null);
  const streamRef = useRef({ thinking: "", content: "", retrieval: [] });  // 避免 StrictMode 双重调用

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
    streamRef.current = { thinking: "", content: "", retrieval: [] };
    setMessages(prev => [...prev, { role: "user", content: q }]);
    setMessages(prev => [...prev, { _id: msgIdx, role: "assistant", content: "", thinking: "", retrieval: [], _streaming: true }]);
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
        body: JSON.stringify({ question: q, use_api: useApi, model: useApi ? selectedModel : null, deep: deepMode }),
      });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      let pendingUpdate = null;
      const flushUpdate = () => {
        if (pendingUpdate) {
          updateMsg({ thinking: streamRef.current.thinking, content: streamRef.current.content, retrieval: streamRef.current.retrieval });
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
            } else if (evt.type === "answer_reset") {
              // 后端检测到截断并重试：清空已显示的截断正文，避免「半截 + 完整」拼接
              streamRef.current.content = "";
              updateMsg({ content: "" });
            } else if (evt.type === "agent_step") {
              streamRef.current.retrieval.push({
                round: evt.round, tool: evt.tool, args: evt.args, preview: evt.preview,
              });
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
              updateMsg({ _streaming: false, content: finalContent, plan_log: finalPlanLog, retrieval: streamRef.current.retrieval });
            } else if (evt.type === "error") {
              updateMsg({ content: "请求失败：" + evt.message, _streaming: false });
            }
            // 节流：每 60ms 最多更新一次 UI，避免闪烁
            // agent_step 也纳入节流，保证深度模式下「调用工具过程」实时呈现
            if (!pendingUpdate && (evt.type === "thinking" || evt.type === "answer" || evt.type === "agent_step")) {
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
      // SQL 无关联、无需实时生成：优先复用检索阶段随 source_index 下发的
      // 结构化 detail（表格渲染），其次 detail_text（纯文本），最后再查库。
      if (sourceData.detail) {
        setRefPanel(prev => ({ ...prev, detailData: sourceData.detail, loading: false }));
      } else if (sourceData.detail_text) {
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
      if (sourceData.detail) {
        setRefPanel(prev => ({ ...prev, detailData: sourceData.detail, loading: false }));
      } else {
        try {
          const res = await fetch(`/reference/sql?author_name=${encodeURIComponent(sourceData.author_name)}`);
          const detail = await res.json();
          setRefPanel(prev => ({ ...prev, detailData: detail, loading: false }));
        } catch (e) {
          setRefPanel(prev => ({ ...prev, detailData: { error: e.message }, loading: false }));
        }
      }
    } else if (sourceType === 'sql' && (sourceData.detail || sourceData.detail_text)) {
      // 全文/标题搜索：优先结构化卡片，其次纯文本（无 doc_title，属「相关文段」类）
      setRefPanel(prev => ({ ...prev, detailData: sourceData.detail || { detail_text: sourceData.detail_text }, loading: false }));
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

  // 图谱边点击 → 展示两端实体各自信息 + 关系信息，力导向图只显示两个节点与这条边
  const handleRelationJump = useCallback(async (edge) => {
    if (!edge || !edge.source || !edge.target) return;
    setRefPanel(prev => ({ ...prev, loading: true }));
    setGraphTrail([
      { id: edge.source, name: edge.fromName || edge.source },
      { id: edge.target, name: edge.toName || edge.target },
    ]);
    try {
      const res = await fetch(`/reference/relation?source=${encodeURIComponent(edge.source)}&target=${encodeURIComponent(edge.target)}`);
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

  // 生成并下载深度思考分析报告（Word）：点击时 POST 触发后端按需生成（不点击不生成）
  const handleGenerateReport = async (sessionId) => {
    try {
      const res = await fetch("/report/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `辑佚分析报告_${sessionId}.docx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("生成报告失败:", e);
    }
  };

  // 当前主题：深度思考模式切换为深色沉浸风格
  const theme = deepMode ? DARK_C : LIGHT_C;

  const selectStyle = {
    padding: "4px 8px", borderRadius: 6, border: `1px solid ${theme.border}`,
    background: theme.inputBg, fontSize: 12, color: theme.text, fontFamily: "inherit",
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
        width: sidebarCollapsed ? 52 : 200, background: theme.sidebar, flexShrink: 0,
        borderRight: `1px solid ${theme.border}`, display: "flex", flexDirection: "column",
        transition: "width .2s",
      }}>
        <div style={{ padding: "12px", display: "flex", justifyContent: sidebarCollapsed ? "center" : "flex-end" }}>
          <button onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            style={{ background: "none", border: "none", cursor: "pointer", padding: 4 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={theme.textM} strokeWidth="2">
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
            <span style={{ fontSize: sidebarCollapsed ? 18 : 15, color: theme.textM, fontFamily: "monospace" }}>{item.icon}</span>
            {!sidebarCollapsed && <span style={{ fontSize: 13.5, color: theme.text }}>{item.label}</span>}
          </div>
        ))}
        <div style={{ flex: 1 }} />
      </div>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: theme.bg }}>
        {/* 页内顶栏：右上角承载「深度思考」切换按钮 */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "10px 24px", borderBottom: `1px solid ${theme.border}`,
          background: theme.white, flexShrink: 0,
        }}>
          <div style={{
            fontSize: 14, fontWeight: 600, color: theme.text,
            fontFamily: "'Noto Serif SC', serif", letterSpacing: 1,
          }}>
            智能问答
            {deepMode && <span style={{ color: theme.citeColor, marginLeft: 8 }}>· 深度思考</span>}
          </div>
          {/* 深度思考切换按钮（专门的滑动开关） */}
          <button
            onClick={() => setDeepMode(v => !v)}
            title="开启后：RACE 定框架 → AI 多轮自主检索 → 最终回答"
            style={{
              display: "inline-flex", alignItems: "center", gap: 8,
              padding: "6px 14px", borderRadius: 20, cursor: "pointer",
              border: `1px solid ${deepMode ? theme.citeColor : theme.border}`,
              background: deepMode ? theme.citeColor : "transparent",
              color: deepMode ? "#17141f" : theme.textM,
              fontSize: 12.5, fontWeight: 600, fontFamily: "inherit",
              transition: "all .15s",
            }}>
            <span style={{
              width: 26, height: 14, borderRadius: 7, position: "relative",
              background: deepMode ? "rgba(0,0,0,0.25)" : theme.border,
              transition: "background .15s", flexShrink: 0,
            }}>
              <span style={{
                position: "absolute", top: 2, left: deepMode ? 14 : 2,
                width: 10, height: 10, borderRadius: "50%",
                background: deepMode ? "#fff" : theme.textM,
                transition: "left .15s",
              }} />
            </span>
            深度思考
          </button>
        </div>
        {chatState === "landing" ? (
          /* Landing */
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 20, padding: 40 }}>
            <div style={{ fontSize: 26, fontWeight: 700, color: theme.text, fontFamily: "'Noto Serif SC', serif", letterSpacing: 2 }}>
              中国古代辑佚研究智能体
            </div>
            <div style={{ color: theme.gold, fontSize: 13.5, textAlign: "center", maxWidth: 460, marginBottom: 16 }}>
              面向知识检索与关系分析的智能体，支持自然语言问答、知识图谱探索
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, width: 360 }}>
              {suggestQuestions.map((q, i) => (
                <button key={i} onClick={() => handleSend(q)}
                  style={{
                    padding: "12px 18px", border: `1px solid ${theme.border}`, borderRadius: 10,
                    background: theme.white, cursor: "pointer", textAlign: "left", fontSize: 13.5,
                    color: theme.text, fontFamily: "inherit",
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
                {/* 思考过程（DeepSeek 式：无边框、小字浅色、下拉展开） */}
                {msg.role === "assistant" && (msg.thinking || msg._streaming) ? (
                  <div style={{ maxWidth: "75%", marginBottom: 4 }}>
                    <div onClick={() => setExpandedThink(prev => ({ ...prev, [i]: !prev[i] }))}
                      style={{
                        padding: "4px 2px", cursor: "pointer",
                        display: "flex", alignItems: "center", gap: 6,
                        fontSize: 12, color: theme.textL, userSelect: "none",
                      }}>
                      <span style={{
                        display: "inline-block", fontSize: 10, color: theme.textL,
                        transition: "transform .15s",
                        transform: expandedThink[i] ? "rotate(90deg)" : "rotate(0deg)",
                      }}>▶</span>
                      <span>思考过程{msg._streaming && " ···"}</span>
                    </div>
                    {(expandedThink[i] || msg._streaming) && (
                      <div style={{
                        padding: "2px 0 2px 18px", fontSize: 12, color: theme.thinkText,
                        lineHeight: 1.7, whiteSpace: "pre-wrap",
                        fontFamily: "'Noto Sans SC', sans-serif",
                      }}>
                        {msg.thinking}
                        {msg._streaming && <span className="stream-cursor">|</span>}
                      </div>
                    )}
                  </div>
                ) : null}
                {/* 检索过程（深度思考模式：列出每轮调用的工具、参数与结果预览） */}
                {msg.role === "assistant" && msg.retrieval && msg.retrieval.length > 0 ? (
                  <div style={{
                    maxWidth: "75%", marginBottom: 8,
                    border: `1px solid ${theme.border}`, borderRadius: 10,
                    background: theme.retrievalBg, overflow: "hidden",
                  }}>
                    <div onClick={() => setExpandedRetrieval(prev => ({ ...prev, [i]: !prev[i] }))}
                      style={{
                        padding: "8px 14px", cursor: "pointer",
                        display: "flex", alignItems: "center", gap: 8,
                        fontSize: 12, color: theme.textM, userSelect: "none",
                        borderBottom: expandedRetrieval[i] ? `1px solid ${theme.border}` : "none",
                      }}>
                      <span style={{ transform: expandedRetrieval[i] ? "rotate(90deg)" : "rotate(0deg)", transition: "transform .15s", fontFamily: "monospace" }}>▶</span>
                      <span>检索过程（{msg.retrieval.length} 次工具调用）</span>
                    </div>
                    {(expandedRetrieval[i] !== false) && (
                      <div style={{ padding: "8px 0", maxHeight: 320, overflow: "auto" }}>
                        {msg.retrieval.map((step, si) => (
                          <div key={si} style={{
                            padding: "6px 14px", borderTop: si === 0 ? "none" : `1px solid ${theme.borderL}`,
                          }}>
                            <div style={{ fontSize: 11, color: theme.textL, marginBottom: 2 }}>
                              第 {step.round} 轮 · <span style={{ fontFamily: "monospace", color: theme.textM }}>{step.tool}</span>
                              <span style={{ color: theme.brownDk, fontWeight: 600 }}> {TOOL_LABELS[step.tool] || ""}</span>
                            </div>
                            {formatToolArgs(step.args) && (
                              <div style={{ fontSize: 11.5, color: theme.textM, marginBottom: 2, wordBreak: "break-all" }}>
                                参数：{formatToolArgs(step.args)}
                              </div>
                            )}
                            {step.preview && (
                              <div style={{ fontSize: 11.5, color: theme.previewText, lineHeight: 1.5, wordBreak: "break-all" }}>
                                {step.preview}…
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : null}
                {/* 正文 */}
                {(msg.role !== "assistant" || msg.content || msg._streaming) ? (
                  <div style={{
                    maxWidth: "75%", padding: "12px 18px",
                    borderRadius: msg.role === "user" ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
                    background: msg.role === "user" ? theme.bg : theme.white,
                    border: `1px solid ${theme.border}`,
                    fontSize: 14, color: theme.text, lineHeight: 1.7, whiteSpace: "pre-wrap",
                  }}>
                    {msg.role === "assistant" && msg.plan_log?.source_index ? (
                      renderMessageWithCitations(msg.content, msg.plan_log.source_index, handleCitationClick, theme.citeColor)
                    ) : (
                      msg.content
                    )}
                    {msg._streaming && <span className="stream-cursor">|</span>}
                  </div>
                ) : null}
                {/* 尾注 — 论文式参考文献列表（点击条目打开右侧详情） */}
                {msg.role === "assistant" && !msg._streaming && msg.plan_log?.source_index && (() => {
                  const sourceKeys = Object.keys(msg.plan_log.source_index);
                  if (sourceKeys.length === 0) return null;
                  return (
                    <div style={{
                      maxWidth: "75%", marginTop: 10, padding: "10px 16px",
                      background: theme.thinkBg, borderRadius: 8,
                      border: `1px solid ${theme.border}`,
                    }}>
                      <div style={{ fontSize: 11.5, color: theme.textM, fontWeight: 600, letterSpacing: 1, marginBottom: 4 }}>
                        参考资料
                      </div>
                      {sourceKeys.map((num) => {
                        const s = msg.plan_log.source_index[num];
                        const refLabel = (typeof s === 'object' && s.ref_label) ? s.ref_label : null;
                        const fallback = typeof s === 'object' ? (s.desc || `来源 ${num}`) : s;
                        return (
                          <div
                            key={num}
                            onClick={() => handleCitationClick(num)}
                            style={{
                              display: "flex", alignItems: "baseline", gap: 6,
                              padding: "3px 0", cursor: "pointer",
                              fontSize: 12.5, color: theme.text, lineHeight: 1.6,
                            }}
                            title={typeof s === 'object' ? s.desc : s}
                          >
                            <span style={{ color: theme.citeColor, fontWeight: 700, flexShrink: 0 }}>{num}.</span>
                            <span>{refLabel || fallback}</span>
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}
                {/* 深度思考分析报告生成（Word）：点击后按需生成并下载 */}
                {msg.role === "assistant" && !msg._streaming && msg.plan_log?.report_session ? (
                  <button onClick={() => handleGenerateReport(msg.plan_log.report_session)}
                    style={{
                      marginTop: 10, padding: "6px 14px", borderRadius: 6,
                      border: `1px solid ${theme.border}`, background: theme.white,
                      color: theme.text, fontSize: 12, cursor: "pointer", fontFamily: "inherit",
                    }}>
                    ⬇ 生成分析报告（Word）
                  </button>
                ) : null}
              </div>
            ))}
            {loading && !messages.some(m => m._streaming) && (
              <div style={{ color: theme.textM, fontSize: 13, padding: "8px 18px" }}>思考中...</div>
            )}
            <div ref={chatEndRef} />
          </div>
        )}

        {/* Input */}
        <div style={{ borderTop: `1px solid ${theme.border}`, padding: "16px 24px", background: theme.white }}>
          {/* 模型选择：供应商 → 具体模型 */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
            <span style={{ fontSize: 12, color: theme.textM }}>引擎:</span>
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
            <div style={{ flex: 1, background: theme.inputBg, border: `1px solid ${theme.border}`, borderRadius: 12, padding: "10px 16px", display: "flex", alignItems: "center", gap: 8 }}>
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onCompositionStart={() => { composingRef.current = true; }}
                onCompositionEnd={e => { composingRef.current = false; setInput(e.target.value); }}
                onKeyDown={e => { if (e.key === "Enter" && !composingRef.current) handleSend(); }}
                placeholder="输入问题..."
                disabled={loading}
                style={{ flex: 1, border: "none", outline: "none", fontSize: 14, background: "transparent", fontFamily: "inherit", color: theme.text }}
              />
              <button onClick={() => handleSend()} disabled={loading}
                style={{ background: "none", border: "none", cursor: "pointer", padding: 4 }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={theme.brownBtn} strokeWidth="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
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
        onEdgeClick={handleRelationJump}
        trail={graphTrail}
        onTrailClick={handleTrailBack}
        onClose={() => { setGraphTrail([]); setRefPanel({ open: false, citationNum: null, sourceData: null, detailData: null, loading: false }); }}
      />
    </div>
  );
}

export default ResearchSection;
