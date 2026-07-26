import { useState, useEffect, useRef } from "react";
import C from "../constants/colors";

/* ─────────────── 雷达图（不变）─────────────── */
function RadarChart({ data, labels, size = 260 }) {
  const cx = size / 2, cy = size / 2, r = size * 0.32, n = labels.length;
  const maxVal = 3;
  const getPoint = (i, val) => {
    const a = (2 * Math.PI / n) * i - Math.PI / 2;
    return { x: cx + (val / maxVal) * r * Math.cos(a), y: cy + (val / maxVal) * r * Math.sin(a) };
  };
  const pathD = (vals) => vals.map((v, i) => `${i ? "L" : "M"}${getPoint(i, v).x.toFixed(1)},${getPoint(i, v).y.toFixed(1)}`).join(" ") + " Z";
  const colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"];
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {[1, 2, 3].map(lvl => <path key={lvl} d={pathD(Array(n).fill(lvl))} fill="none" stroke="#ddd" strokeWidth={0.5} />)}
      {[1, 2, 3].map(lvl => <text key={`t${lvl}`} x={cx + 4} y={cy - (lvl / maxVal) * r + 3} fontSize={9} fill="#bbb">{lvl}</text>)}
      {labels.map((lb, i) => {
        const p = getPoint(i, maxVal + 0.45);
        return <text key={lb} x={p.x - 14} y={p.y + 4} fontSize={11} fill="#555" fontWeight={600}>{lb}</text>;
      })}
      {Object.entries(data).map(([model, vals], mi) => (
        <path key={model} d={pathD(vals)} fill={colors[mi % 5]} fillOpacity={0.12}
          stroke={colors[mi % 5]} strokeWidth={1.8} />
      ))}
    </svg>
  );
}

/* ─────────────── 指标定义 ─────────────── */
const INDICATORS = {
  C: { label: "C 检索有效性", short: "检索是否充分有效", rule: "3=三类检索全部命中无降级 | 2=有一类未命中或冗余 | 1=降级/大面积空" },
  D: { label: "D 论证质量", short: "推理是否合理有据", rule: "3=推理链清晰结论←论据←证据 | 2=有跳跃或未综合多源 | 1=答非所问自相矛盾" },
  A: { label: "A 事实正确性", short: "事实是否与检索一致", rule: "3=所有事实可验证无编造 | 2=轻微不精确 | 1=有编造/错字/数字错/关系颠倒" },
  B: { label: "B 信息完整性", short: "是否充分覆盖检索结果", rule: "3=全覆盖无遗漏 | 2=遗漏1-2个要点 | 1=大量信息未纳入" },
};

/* ─────────────── 主页面 ─────────────── */
export default function EvalPage() {
  const [questions, setQuestions] = useState([]);
  const [providers, setProviders] = useState([]);
  const [selectedModel, setSelectedModel] = useState("deepseek-chat");
  const [activeQid, setActiveQid] = useState(null);
  const [answers, setAnswers] = useState({});       // qid → {model → {answer, thinking, plan_log, loading}}
  const [scores, setScores] = useState({});          // qid → {model → {C,D,A,B, notes, saved}}
  const [results, setResults] = useState([]);         // all saved results
  const [summary, setSummary] = useState(null);
  const [tab, setTab] = useState("eval");
  const [newQuestion, setNewQuestion] = useState("");
  const [sidebarW, setSidebarW] = useState(280);
  const chatEndRef = useRef(null);
  const [tooltip, setTooltip] = useState({ show: false, text: "", x: 0, y: 0 });

  const activeQ = questions.find(q => q.id === activeQid);
  const modelKey = (qid, model) => `${qid}__${model}`;

  // 加载数据
  useEffect(() => {
    fetch("/eval/questions").then(r => r.json()).then(d => {
      setQuestions(d.questions || []);
      if (d.questions?.length && !activeQid) setActiveQid(d.questions[0].id);
    });
    fetch("/models").then(r => r.json()).then(d => {
      setProviders(d.providers || []);
      const first = (d.providers || []).find(p => p.configured);
      if (first?.models?.length) setSelectedModel(first.models[0].id);
    });
    loadResults();
  }, []);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [answers]);

  // 切换题目或模型时，恢复已保存的回答
  useEffect(() => {
    if (!activeQid) return;
    const stored = results.find(r => r.question_id === activeQid && r.model === selectedModel);
    if (stored) {
      const mk = modelKey(activeQid, selectedModel);
      setAnswers(prev => {
        if (prev[mk] && !prev[mk].loading) return prev; // 已有当前会话的回答，不覆盖
        return { ...prev, [mk]: { answer: stored.answer, thinking: stored.thinking, plan_log: stored.plan_log, model: stored.model } };
      });
    }
  }, [activeQid, selectedModel, results]);

  const loadResults = () => {
    fetch("/eval/results").then(r => r.json()).then(d => {
      setResults(d.results || []);
      const sc = {};
      (d.results || []).forEach(r => {
        if (r.question_id && r.model) {
          const mk = modelKey(r.question_id, r.model);
          sc[mk] = { ...(r.scores || {}), notes: r.notes || "", saved: true };
        }
      });
      setScores(sc);
    });
  };

  // 获取某题某模型的已有结果
  const getStoredAnswer = (qid, model) => {
    const r = results.find(r => r.question_id === qid && r.model === model);
    return r ? { answer: r.answer, thinking: r.thinking, plan_log: r.plan_log, model: r.model } : null;
  };

  // 调用 API（自动保存，除非重置否则结果持久保留）
  const handleRun = async () => {
    if (!activeQid || !activeQ) return;
    const mk = modelKey(activeQid, selectedModel);
    setAnswers(prev => ({ ...prev, [mk]: { loading: true } }));
    try {
      const res = await fetch("/eval/run", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_id: activeQid, question: activeQ.question, model: selectedModel }),
      });
      const data = await res.json();
      setAnswers(prev => ({ ...prev, [mk]: { ...data, loading: false } }));

      // 自动保存回答+工具调用信息（评分留空，用户后续手动打分）
      const existScore = scores[mk] || {};
      await fetch("/eval/save", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question_id: activeQid, question: activeQ.question, model: data.model || selectedModel,
          answer: data.answer, plan_log: data.plan_log, thinking: data.thinking,
          scores: { C: existScore.C || 0, D: existScore.D || 0, A: existScore.A || 0, B: existScore.B || 0 },
          notes: existScore.notes || "",
        }),
      });
      loadResults();
    } catch (e) {
      setAnswers(prev => ({ ...prev, [mk]: { loading: false, error: String(e) } }));
    }
  };

  // 评分
  const handleScore = (qid, model, key, val) => {
    const mk = modelKey(qid, model);
    setScores(prev => ({
      ...prev,
      [mk]: { ...(prev[mk] || {}), [key]: key === "notes" ? val : parseInt(val) || 0, saved: false },
    }));
  };

  // 保存
  const handleSave = async () => {
    const mk = modelKey(activeQid, selectedModel);
    const a = answers[mk];
    const s = scores[mk];
    if (!a || !s) return;
    await fetch("/eval/save", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question_id: activeQid, question: activeQ.question, model: a.model || selectedModel,
        answer: a.answer, plan_log: a.plan_log, thinking: a.thinking,
        scores: { C: s.C || 0, D: s.D || 0, A: s.A || 0, B: s.B || 0 },
        notes: s.notes || "",
      }),
    });
    loadResults();
  };

  // 重置单题单模型
  const handleReset = async () => {
    const mk = modelKey(activeQid, selectedModel);
    await fetch(`/eval/results/${activeQid}?model=${encodeURIComponent(selectedModel)}`, { method: "DELETE" });
    setAnswers(prev => { const n = { ...prev }; delete n[mk]; return n; });
    setScores(prev => { const n = { ...prev }; delete n[mk]; return n; });
    loadResults();
  };

  const handleAddQuestion = async () => {
    if (!newQuestion.trim()) return;
    const res = await fetch("/eval/questions", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: newQuestion.trim() }),
    });
    const data = await res.json();
    if (data.ok) {
      setQuestions(prev => [...prev, data.question]);
      setActiveQid(data.question.id);
      setNewQuestion("");
    }
  };

  const handleDeleteQuestion = async (qid) => {
    await fetch(`/eval/questions/${qid}`, { method: "DELETE" });
    setQuestions(prev => prev.filter(q => q.id !== qid));
    if (activeQid === qid) {
      const remaining = questions.filter(q => q.id !== qid);
      setActiveQid(remaining[0]?.id || null);
    }
    loadResults();
  };

  const handleLoadSummary = async () => {
    const res = await fetch("/eval/summary");
    setSummary(await res.json());
    setTab("summary");
  };

  // ── 当前题目各模型的结果汇总 ──
  const currentResults = results.filter(r => r.question_id === activeQid);
  const currentStoredModels = [...new Set(currentResults.map(r => r.model))];

  // 雷达图数据
  const radarData = {};
  if (summary) {
    Object.entries(summary.summary || {}).forEach(([model, v]) => {
      const avg = v.avg_scores || {};
      radarData[model] = [avg.C || 0, avg.D || 0, avg.A || 0, avg.B || 0];
    });
  }

  // 模型选项
  const modelOptions = [];
  providers.forEach(p => {
    (p.models || []).forEach(m => modelOptions.push({ value: m.id, label: `${p.label} · ${m.label}` }));
  });

  const mk = modelKey(activeQid, selectedModel);
  const currentAnswer = answers[mk];
  const currentScore = scores[mk] || {};
  const currentToolSummary = currentAnswer?.plan_log?.tool_summary || [];
  const hasSummary = currentToolSummary.length > 0;

  // ── 公共样式 ──
  const btn = (bg, disabled) => ({
    padding: "7px 16px", borderRadius: 6, border: "none", cursor: disabled ? "not-allowed" : "pointer",
    background: disabled ? "#ddd" : bg, color: "#fff", fontSize: 13, fontWeight: 600, opacity: disabled ? 0.5 : 1,
  });
  const sel = { padding: "7px 12px", borderRadius: 6, border: "1px solid #ddd", fontSize: 13, background: "#fff" };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: C.bg }}>
      {/* ── 顶栏 ── */}
      <div style={{ padding: "10px 20px", borderBottom: "1px solid #e0d5c7", display: "flex", alignItems: "center", gap: 16, background: "#fff", flexShrink: 0 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: C.primary, fontFamily: "'Noto Serif SC', serif" }}>API 评估</h2>
        <div style={{ flex: 1 }} />
        <button onClick={() => { setTab("eval"); loadResults(); }}
          style={{ ...btn(tab === "eval" ? C.primary : "#e8e0d5"), color: tab === "eval" ? "#fff" : "#666", background: tab === "eval" ? C.primary : "#e8e0d5" }}>评估</button>
        <button onClick={handleLoadSummary}
          style={{ ...btn(tab === "summary" ? C.primary : "#e8e0d5"), color: tab === "summary" ? "#fff" : "#666", background: tab === "summary" ? C.primary : "#e8e0d5" }}>汇总</button>
      </div>

      {tab === "eval" ? (
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          {/* ── 左侧选题栏 ── */}
          <div style={{
            width: sidebarW, minWidth: 200, borderRight: "1px solid #e0d5c7", background: "#faf8f5",
            display: "flex", flexDirection: "column", overflow: "hidden",
          }}>
            <div style={{ padding: 12, fontWeight: 700, fontSize: 13, color: "#8b7a62", borderBottom: "1px solid #e0d5c7" }}>
              测试题目（{questions.length}）
            </div>
            <div style={{ flex: 1, overflow: "auto", padding: "6px 0" }}>
              {questions.map((q, idx) => {
                const qResults = results.filter(r => r.question_id === q.id);
                const modelsDone = [...new Set(qResults.map(r => r.model))];
                const active = q.id === activeQid;
                return (
                  <div key={q.id} onClick={() => setActiveQid(q.id)} style={{
                    padding: "10px 14px", cursor: "pointer", fontSize: 13, lineHeight: 1.5,
                    background: active ? "#fff" : "transparent",
                    borderLeft: active ? `3px solid ${C.primary}` : "3px solid transparent",
                    borderBottom: "1px solid #f0ebe0",
                    transition: "background .15s",
                  }}>
                    <div style={{ fontWeight: active ? 700 : 500, color: active ? C.primary : "#444", marginBottom: 3 }}>
                      #{idx + 1} {q.question.length > 40 ? q.question.slice(0, 40) + "..." : q.question}
                    </div>
                    {modelsDone.length > 0 && (
                      <div style={{ fontSize: 11, color: "#999" }}>
                        已测: {modelsDone.map(m => m.split("-")[0]).join(", ")} ({qResults.length}次)
                      </div>
                    )}
                    {q.id.startsWith("custom_") && (
                      <button onClick={e => { e.stopPropagation(); handleDeleteQuestion(q.id); }}
                        style={{ fontSize: 10, color: "#c99", border: "none", background: "none", cursor: "pointer", padding: 0, marginTop: 2 }}>删除</button>
                    )}
                  </div>
                );
              })}
            </div>
            {/* 添加题目 */}
            <div style={{ padding: 10, borderTop: "1px solid #e0d5c7" }}>
              <input value={newQuestion} onChange={e => setNewQuestion(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") handleAddQuestion(); }}
                placeholder="+ 添加题目..."
                style={{ width: "100%", padding: "7px 10px", borderRadius: 5, border: "1px solid #ddd", fontSize: 12 }} />
            </div>
          </div>

          {/* 分隔条 */}
          <div onMouseDown={e => {
            e.preventDefault();
            const startX = e.clientX;
            const startW = sidebarW;
            const onMove = (ev) => setSidebarW(Math.max(180, Math.min(450, startW + ev.clientX - startX)));
            const onUp = () => { window.removeEventListener("mousemove", onMove); window.removeEventListener("mouseup", onUp); };
            window.addEventListener("mousemove", onMove);
            window.addEventListener("mouseup", onUp);
          }} style={{ width: 4, cursor: "col-resize", background: "transparent", flexShrink: 0 }} />

          {/* ── 右侧主区域 ── */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: "#fff" }}>
            {activeQ ? (
              <>
                {/* 题目 + 模型选择 + 操作 */}
                <div style={{ padding: "16px 20px", borderBottom: "1px solid #eee", background: "#fdfcf9" }}>
                  <div style={{ fontSize: 15, fontWeight: 700, color: "#333", marginBottom: 12, lineHeight: 1.5 }}>
                    {activeQ.question}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                    <select value={selectedModel} onChange={e => setSelectedModel(e.target.value)} style={sel}>
                      {modelOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                    <button onClick={handleRun} disabled={currentAnswer?.loading} style={btn(C.primary, currentAnswer?.loading)}>
                      {currentAnswer?.loading ? "检索中..." : currentAnswer ? "重新检索" : "开始检索"}
                    </button>
                    {currentAnswer && !currentAnswer.loading && (
                      <>
                        <button onClick={handleSave} style={btn("#27ae60", currentScore.saved)}>
                          {currentScore.saved ? "已保存 ✓" : "保存评分"}
                        </button>
                        <button onClick={handleReset} style={btn("#e74c3c", false)}>重置当前</button>
                      </>
                    )}
                    {/* 已有模型标签 */}
                    {currentStoredModels.length > 0 && (
                      <div style={{ fontSize: 11, color: "#999", marginLeft: 8 }}>
                        已测模型: {currentStoredModels.map(m => (
                          <span key={m} onClick={() => setSelectedModel(m)} style={{
                            display: "inline-block", margin: "0 2px", padding: "2px 6px", borderRadius: 3,
                            background: selectedModel === m ? C.primary : "#eee",
                            color: selectedModel === m ? "#fff" : "#666", cursor: "pointer", fontSize: 11,
                          }}>{m.split("-")[0]}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* 错误 */}
                {currentAnswer?.error && (
                  <div style={{ margin: "12px 20px", padding: 10, background: "#fff0f0", borderRadius: 5, color: "#c33", fontSize: 13 }}>
                    {currentAnswer.error}
                  </div>
                )}

                {/* 回答内容区 */}
                <div style={{ flex: 1, overflow: "auto", padding: "16px 20px" }}>
                  {/* 工具调用摘要表 */}
                  {hasSummary && (
                    <div style={{ marginBottom: 16, background: "#f9f7f3", borderRadius: 6, padding: 12, fontSize: 12 }}>
                      <div style={{ fontWeight: 700, marginBottom: 8, color: "#5a4e3c", fontSize: 13 }}>
                        工具调用摘要（共 {currentToolSummary.length} 次）
                      </div>
                      <table style={{ width: "100%", borderCollapse: "collapse" }}>
                        <thead>
                          <tr style={{ borderBottom: "2px solid #e0d5c7" }}>
                            <th style={{ ...smTh, width: 48 }}>分类</th>
                            <th style={smTh}>工具</th>
                            <th style={smTh}>检索参数</th>
                            <th style={smTh}>状态</th>
                            <th style={{ ...smTh, width: 120 }}>结果摘要</th>
                          </tr>
                        </thead>
                        <tbody>
                          {currentToolSummary.map((t, i) => {
                            const cat = t.tool.startsWith("kg_") ? "图谱" : t.tool === "vector_search" ? "语义" : "SQL";
                            const catColor = cat === "图谱" ? "#7b68ee" : cat === "语义" ? "#e67e22" : "#2980b9";
                            return (
                            <tr key={i} style={{ borderBottom: "1px solid #f0ebe0" }}>
                              <td style={smTd}>
                                <span style={{ display: "inline-block", padding: "1px 5px", borderRadius: 3, fontSize: 10,
                                  background: cat === "图谱" ? "#f3f0ff" : cat === "语义" ? "#fff8f0" : "#f0f6ff",
                                  color: catColor, fontWeight: 600 }}>{cat}</span>
                              </td>
                              <td style={smTd}>
                                <span style={{ fontWeight: 600, color: C.primary, fontSize: 11 }}>{t.tool}</span>
                              </td>
                              <td style={smTd}>
                                <span style={{ color: "#555" }}>{t.params}</span>
                              </td>
                              <td style={smTd}>
                                <span style={{
                                  display: "inline-block", padding: "2px 6px", borderRadius: 3, fontSize: 11,
                                  background: t.status === "命中" ? "#e8f5e9" : "#fff3e0",
                                  color: t.status === "命中" ? "#2e7d32" : "#e65100",
                                }}>{t.status}</span>
                              </td>
                              <td style={{ ...smTd, color: "#777" }}>{t.summary}</td>
                            </tr>
                          )})}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {currentAnswer && !currentAnswer.loading ? (
                    <div style={{ fontSize: 14, lineHeight: 1.8, whiteSpace: "pre-wrap", color: "#333" }}>
                      {currentAnswer.answer}
                    </div>
                  ) : currentAnswer?.loading ? (
                    <div style={{ color: "#aaa", fontSize: 14, padding: 40, textAlign: "center" }}>
                      正在检索，请稍候...
                    </div>
                  ) : (
                    <div style={{ color: "#ccc", fontSize: 14, padding: 60, textAlign: "center" }}>
                      选择模型后点击"开始检索"
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                {/* 评分区 */}
                {currentAnswer && !currentAnswer.loading && (
                  <div style={{ padding: "12px 20px", borderTop: "1px solid #eee", background: "#fdfcf9" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap", marginBottom: 6 }}>
                      <span style={{ fontWeight: 700, fontSize: 13, color: "#555" }}>评分 ({selectedModel.split("-")[0]}):</span>
                      {["C", "D", "A", "B"].map(k => {
                        const ind = INDICATORS[k];
                        return (
                          <label key={k} style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 4, cursor: "help" }}
                            onMouseEnter={e => setTooltip({ show: true, text: `${ind.label}: ${ind.rule}`, x: e.clientX, y: e.clientY })}
                            onMouseLeave={() => setTooltip({ show: false })}>
                            <span style={{ color: "#777", fontWeight: 600, whiteSpace: "nowrap" }}>{ind.label}</span>
                            <select value={currentScore[k] || 0} onChange={e => handleScore(activeQid, selectedModel, k, e.target.value)}
                              style={{ padding: "4px 6px", borderRadius: 4, border: "1px solid #ddd", fontSize: 12, width: 42 }}>
                              <option value={0}>-</option>
                              <option value={1}>1</option>
                              <option value={2}>2</option>
                              <option value={3}>3</option>
                            </select>
                          </label>
                        );
                      })}
                    </div>
                    <input placeholder="备注（可选）" value={currentScore.notes || ""}
                      onChange={e => handleScore(activeQid, selectedModel, "notes", e.target.value)}
                      style={{ padding: "5px 10px", borderRadius: 4, border: "1px solid #ddd", fontSize: 12, width: 300 }} />
                  </div>
                )}
              </>
            ) : (
              <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#ccc", fontSize: 14 }}>
                从左侧选择一道题目
              </div>
            )}
          </div>
        </div>
      ) : (
        /* ── 汇总页 ── */
        <div style={{ flex: 1, overflow: "auto", padding: 20 }}>
          {summary ? (
            <>
              <div style={{ background: "#fff", borderRadius: 8, padding: 20, marginBottom: 16, boxShadow: "0 1px 3px rgba(0,0,0,.06)" }}>
                <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 14 }}>汇总统计（共 {summary.total_results} 条记录）</div>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: "#f9f7f3" }}>
                      <th style={th}>模型</th><th style={th}>次数</th>
                      {["C", "D", "A", "B"].map(k => <th key={k} style={th}>{INDICATORS[k].label}</th>)}
                      <th style={th}>均分</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(summary.summary || {}).map(([model, v]) => {
                      const avg = v.avg_scores || {};
                      const overall = ((avg.C || 0) + (avg.D || 0) + (avg.A || 0) + (avg.B || 0)) / 4;
                      return (
                        <tr key={model} style={{ borderBottom: "1px solid #eee" }}>
                          <td style={td}>{model}</td>
                          <td style={{ ...td, textAlign: "center" }}>{v.count}</td>
                          {["C", "D", "A", "B"].map(k => <td key={k} style={{ ...td, textAlign: "center" }}>{avg[k]?.toFixed(1) || "-"}</td>)}
                          <td style={{ ...td, textAlign: "center", fontWeight: 700, color: C.primary }}>{overall.toFixed(1)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {Object.keys(radarData).length > 0 && (
                <div style={{ background: "#fff", borderRadius: 8, padding: 20, display: "flex", gap: 30, alignItems: "center", flexWrap: "wrap", boxShadow: "0 1px 3px rgba(0,0,0,.06)" }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 12 }}>雷达图对比</div>
                    <RadarChart data={radarData} labels={["C检索", "D论证", "A正确", "B完整"]} size={280} />
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, marginBottom: 8 }}>图例</div>
                    {Object.keys(radarData).map((m, i) => (
                      <div key={m} style={{ fontSize: 12, marginBottom: 4 }}>
                        <span style={{ display: "inline-block", width: 12, height: 12, borderRadius: 2, marginRight: 6,
                          background: ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"][i % 5] }} />
                        {m}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div style={{ textAlign: "center", padding: 60, color: "#999", fontSize: 14 }}>点击"汇总"加载统计数据</div>
          )}
        </div>
      )}

      {/* ── Tooltip ── */}
      {tooltip.show && (
        <div style={{ position: "fixed", left: tooltip.x + 12, top: tooltip.y - 10, background: "#333", color: "#fff",
          padding: "7px 11px", borderRadius: 5, fontSize: 11, maxWidth: 340, lineHeight: 1.5, zIndex: 9999,
          pointerEvents: "none", boxShadow: "0 2px 8px rgba(0,0,0,.3)" }}>{tooltip.text}</div>
      )}

      {/* ── 右下角指标速查 ── */}
      <div style={{ position: "fixed", right: 16, bottom: 16, zIndex: 100 }}>
        <span style={{ display: "inline-block", width: 30, height: 30, borderRadius: "50%", background: C.primary,
          color: "#fff", textAlign: "center", lineHeight: "30px", fontSize: 16, fontWeight: 700,
          cursor: "help", boxShadow: "0 2px 6px rgba(0,0,0,.2)" }}
          onMouseEnter={e => setTooltip({ show: true, criteria: true, x: e.clientX, y: e.clientY })}
          onMouseLeave={() => setTooltip({ show: false })}>?</span>
        {tooltip.criteria && (
          <div style={{ position: "fixed", right: 56, bottom: 16, background: "#fff", padding: 16, borderRadius: 8,
            width: 380, boxShadow: "0 4px 16px rgba(0,0,0,.15)", zIndex: 9999, fontSize: 12, lineHeight: 1.6 }}>
            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8, color: C.primary }}>评估指标速查</div>
            {Object.entries(INDICATORS).map(([k, v]) => (
              <div key={k} style={{ marginBottom: 6, paddingBottom: 6, borderBottom: "1px solid #f0f0f0" }}>
                <div style={{ fontWeight: 600 }}>{v.label} — {v.short}</div>
                <div style={{ color: "#666", fontSize: 11 }}>{v.rule}</div>
              </div>
            ))}
            <div style={{ color: "#999", fontSize: 11, marginTop: 4 }}>打分流程：看日志 C → 读答案 D → 对照检索 A → 检查覆盖 B</div>
          </div>
        )}
      </div>
    </div>
  );
}

const th = { padding: "8px 12px", textAlign: "left", fontWeight: 600, borderBottom: "2px solid #ddd", fontSize: 12 };
const td = { padding: "8px 12px", fontSize: 12 };
const smTh = { padding: "5px 8px", textAlign: "left", fontWeight: 600, fontSize: 11, color: "#8b7a62" };
const smTd = { padding: "5px 8px", fontSize: 11 };
