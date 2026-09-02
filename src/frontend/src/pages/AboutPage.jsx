import { useState, useEffect } from "react";
import C from "../constants/colors";

const SEAL = "#a34a3a"; // 印章朱砂红（克制点缀）

/* 线性图标（stroke 风格，随卡片主题色） */
const ICONS = {
  qa: (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5c-1.6 0-3.1-.4-4.3-1.2L3 20l1.2-5.2A8.5 8.5 0 1 1 21 11.5z" />
    </svg>
  ),
  graph: (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="5" cy="6" r="2" /><circle cx="19" cy="6" r="2" /><circle cx="12" cy="18" r="2" />
      <path d="M6.5 7.6 10.5 16.4M17.5 7.6 13.5 16.4M7 6h10" />
    </svg>
  ),
  path: (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="5" cy="18" r="2" /><circle cx="19" cy="6" r="2" /><path d="M7 16.5 17 7.5" />
    </svg>
  ),
  report: (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" /><path d="M14 2v6h6" /><path d="M9 13h6M9 17h6" />
    </svg>
  ),
  import: (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 21V9M7 14l5-5 5 5M4 3h16" />
    </svg>
  ),
};

const fmt = n => (n == null ? null : Number(n).toLocaleString("zh-CN"));

function AboutPage({ navigate }) {
  const [stats, setStats] = useState(null);
  const [sqlStats, setSqlStats] = useState(null);

  useEffect(() => {
    fetch("/stats").then(r => r.json()).then(setStats).catch(() => {});
    fetch("/sql/stats").then(r => r.json()).then(setSqlStats).catch(() => {});
  }, []);

  const capabilities = [
    { icon: "qa", title: "智能问答", desc: "GraphRAG 检索增强，融合图谱、向量与关系型数据库三重证据，回答辑佚学专业问题。", action: () => navigate("research-home") },
    { icon: "graph", title: "图谱探索", desc: "学者、辑本、类书、方法、时期多跳关联，力导向图可视化呈现复杂学术网络。", action: () => navigate("resources-overview") },
    { icon: "path", title: "路径查询", desc: "解析实体间最短关联路径，揭示师承授受与学术传承的脉络。", action: () => navigate("resources-path") },
    { icon: "report", title: "研究报告", desc: "将一次研究会话沉淀为结构化 Word 报告，一键导出。", action: () => navigate("research-home") },
    { icon: "import", title: "图谱导入", desc: "支持 JSON 知识图谱增量合并，同步重算语义向量，持续生长。", action: () => navigate("import") },
  ];

  const graphNums = [
    { v: stats?.entity_count, label: "图谱实体", sub: "Entity" },
    { v: stats?.relation_count, label: "语义关系", sub: "Relation" },
    { v: stats?.entity_types?.Compilation, label: "辑本", sub: "Compilation" },
    { v: stats?.entity_types?.Scholar, label: "学者", sub: "Scholar" },
  ];
  const docNums = [
    { v: sqlStats?.documents, label: "古籍文献", sub: "Documents" },
    { v: sqlStats?.full_text_1, label: "正文片段", sub: "Full Text" },
    { v: sqlStats?.titles, label: "层级标题", sub: "Titles" },
    { v: sqlStats?.authors, label: "编纂者", sub: "Compilers" },
  ];

  const layers = [
    { name: "应用层", color: C.nodeBeig, items: ["React + Vite 前端", "FastAPI 后端", "SSE 流式响应"] },
    { name: "智能层", color: C.nodeTeal, items: ["多模型大语言模型", "bge-large-zh 向量化", "GraphRAG 检索增强", "两段式推理"] },
    { name: "数据层", color: C.nodePurp, items: ["Neo4j 知识图谱", "MySQL 文献库", "向量索引"] },
  ];

  return (
    <div style={{ flex: 1, overflow: "auto", background: "linear-gradient(160deg, #faf7f2 0%, #f5efe7 60%, #f0e9de 100%)" }}>
      {/* ───── Hero ───── */}
      <div style={{ textAlign: "center", padding: "64px 24px 48px" }}>
        <div style={{
          width: 64, height: 64, margin: "0 auto 24px", borderRadius: 10,
          border: `2px solid ${SEAL}`, color: SEAL, display: "flex",
          alignItems: "center", justifyContent: "center",
          fontSize: 20, fontWeight: 700, lineHeight: 1.2, letterSpacing: 2,
          fontFamily: "'Noto Serif SC', serif", background: "rgba(163,74,58,0.04)",
        }}>
          辑佚
        </div>
        <h1 style={{
          fontSize: 38, fontWeight: 700, color: C.text, margin: 0,
          fontFamily: "'Noto Serif SC', serif", letterSpacing: 6,
        }}>
          辑佚史智能体
        </h1>
        <div style={{ fontSize: 13, color: C.textL, letterSpacing: 4, marginTop: 10, textTransform: "uppercase" }}>
          Jiyi Studies Agent
        </div>
        <p style={{ fontSize: 16, color: C.textM, maxWidth: 560, margin: "24px auto 0", lineHeight: 2, letterSpacing: 1 }}>
          以知识图谱与人工智能，重续辑佚学的千年文脉
        </p>
      </div>

      {/* ───── 缘起 ───── */}
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "0 32px" }}>
        <div style={{
          background: C.white, borderRadius: 16, padding: "36px 44px",
          border: `1px solid ${C.border}`, boxShadow: "0 2px 12px rgba(0,0,0,0.04)",
        }}>
          <div style={{ width: 32, height: 3, background: C.gold, marginBottom: 18 }} />
          <p style={{ fontSize: 15, color: C.text, lineHeight: 2.1, margin: 0, letterSpacing: 0.5 }}>
            辑佚之学，起于宋、盛于清，是对散佚古籍「网罗放佚、掇拾遗文」的专门学问。
            本项目以辑佚史为线索，将<strong style={{ color: C.brownBtn }}>学者、辑本、类书、方法、时期</strong>等要素结构化为知识图谱，
            融合多模型大语言模型与 GraphRAG 检索，提供<strong style={{ color: C.brownBtn }}>可溯源</strong>的智能问答、可视化探索与研究报告生成，
            为古典文献与学术史研究提供数字化支撑。
          </p>
        </div>
      </div>

      {/* ───── 数据规模 ───── */}
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "56px 32px 0" }}>
        <SectionTitle en="SCALE" zh="数据规模" />
        {stats && (
          <NumRow items={graphNums} />
        )}
        {sqlStats && (
          <div style={{ marginTop: 20 }}>
            <NumRow items={docNums} />
          </div>
        )}
      </div>

      {/* ───── 核心能力 ───── */}
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "56px 32px 0" }}>
        <SectionTitle en="CAPABILITIES" zh="核心能力" />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 18 }}>
          {capabilities.map(c => (
            <div key={c.title} onClick={c.action} style={{
              background: C.white, borderRadius: 14, padding: "26px 24px",
              border: `1px solid ${C.border}`, cursor: "pointer",
              transition: "transform .18s, box-shadow .18s",
              boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
            }}
              onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-3px)"; e.currentTarget.style.boxShadow = "0 10px 26px rgba(0,0,0,0.1)"; }}
              onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.04)"; }}
            >
              <div style={{ color: C.brownBtn, marginBottom: 14 }}>{ICONS[c.icon]}</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: C.text, marginBottom: 8, fontFamily: "'Noto Serif SC', serif" }}>
                {c.title}
              </div>
              <div style={{ fontSize: 13, color: C.textM, lineHeight: 1.7 }}>{c.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ───── 技术架构 ───── */}
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "56px 32px 0" }}>
        <SectionTitle en="ARCHITECTURE" zh="技术架构" />
        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          {layers.map((layer, i) => (
            <div key={layer.name}>
              {i > 0 && (
                <div style={{ textAlign: "center", color: C.textL, fontSize: 16, lineHeight: 1.6, letterSpacing: 2 }}>↓</div>
              )}
              <div style={{
                background: C.white, borderRadius: 14, padding: "22px 28px",
                border: `1px solid ${C.border}`, display: "flex", alignItems: "center", gap: 24,
              }}>
                <div style={{
                  width: 44, height: 44, borderRadius: 10, background: layer.color,
                  color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
                  fontWeight: 700, fontSize: 13, flexShrink: 0,
                }}>{i + 1}</div>
                <div style={{ width: 96, fontSize: 15, fontWeight: 600, color: C.text, flexShrink: 0, fontFamily: "'Noto Serif SC', serif" }}>
                  {layer.name}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {layer.items.map(it => (
                    <span key={it} style={{
                      background: C.bg, border: `1px solid ${C.border}`, borderRadius: 14,
                      padding: "5px 14px", fontSize: 12.5, color: C.textM,
                    }}>{it}</span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ───── 理念 ───── */}
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "56px 32px 0" }}>
        <SectionTitle en="PRINCIPLES" zh="设计理念" />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 18 }}>
          {[
            ["可溯源", "每次回答均附图谱 / 向量 / 文献检索依据，答案可回溯。"],
            ["少幻觉", "两段式推理：先分析参考信息并逐字抄录实体名，再作答。"],
            ["结构化", "知识图谱 + 向量 + 关系型数据库三层互补，各擅其长。"],
          ].map(([t, d]) => (
            <div key={t} style={{ textAlign: "center", padding: "24px 20px", background: C.white, borderRadius: 14, border: `1px solid ${C.border}` }}>
              <div style={{ fontSize: 16, fontWeight: 600, color: C.brownBtn, marginBottom: 10, fontFamily: "'Noto Serif SC', serif" }}>{t}</div>
              <div style={{ fontSize: 13, color: C.textM, lineHeight: 1.7 }}>{d}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ───── 页脚 ───── */}
      <div style={{ marginTop: 72, borderTop: `1px solid ${C.border}`, padding: "32px 24px 40px", textAlign: "center" }}>
        <div style={{ fontSize: 14, color: C.text, letterSpacing: 2, fontFamily: "'Noto Serif SC', serif" }}>辑佚史智能体</div>
        <div style={{ fontSize: 12, color: C.textL, marginTop: 8, letterSpacing: 1 }}>
          © 2026 Jiyi Studies Agent
        </div>
      </div>
    </div>
  );
}

function SectionTitle({ en, zh }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 24 }}>
      <span style={{ fontSize: 11, color: C.textL, letterSpacing: 3, textTransform: "uppercase" }}>{en}</span>
      <span style={{ fontSize: 20, fontWeight: 700, color: C.text, fontFamily: "'Noto Serif SC', serif" }}>{zh}</span>
      <span style={{ flex: 1, height: 1, background: C.border, alignSelf: "center" }} />
    </div>
  );
}

function NumRow({ items }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 18 }}>
      {items.map(it => (
        <div key={it.label} style={{ textAlign: "center", background: C.white, borderRadius: 14, padding: "24px 16px", border: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 30, fontWeight: 700, color: C.brownBtn, fontFamily: "'Noto Serif SC', serif", lineHeight: 1.1 }}>
            {it.v != null ? fmt(it.v) : "—"}
          </div>
          <div style={{ fontSize: 13, color: C.text, marginTop: 6 }}>{it.label}</div>
          <div style={{ fontSize: 10.5, color: C.textL, letterSpacing: 1, marginTop: 2 }}>{it.sub}</div>
        </div>
      ))}
    </div>
  );
}

export default AboutPage;
