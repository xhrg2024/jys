import { useState, useEffect } from "react";
import C from "../constants/colors";

function HomePage({ navigate }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch("/stats")
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(() => {});
  }, []);

  const features = [
    {
      icon: " ",
      title: "智能问答",
      desc: "基于知识图谱与大语言模型的智能问答系统，支持辑佚学领域的专业问答",
      action: () => navigate("research-home"),
    },
    {
      icon: " ",
      title: "知识图谱",
      desc: "可视化展示学者、类书、辑本之间的复杂关联网络，支持多跳探索",
      action: () => { navigate("resources-overview"); },
    },
    {
      icon: " ",
      title: "实体探索",
      desc: "搜索并探索辑佚史中的各类实体，查看其详细信息与关联关系",
      action: () => { navigate("resources-overview"); },
    },
    {
      icon: " ",
      title: "路径查询",
      desc: "查询两个实体之间的最短关联路径，揭示学术传承脉络",
      action: () => { navigate("resources-overview"); },
    },
  ];

  return (
    <div style={{
      flex: 1, overflow: "auto",
      background: "linear-gradient(135deg, #faf8f5 0%, #f5f0ea 100%)",
    }}>
      {/* Hero 区域 */}
      <div style={{
        textAlign: "center", padding: "60px 20px 40px",
        background: "linear-gradient(180deg, rgba(138,69,32,0.08) 0%, transparent 100%)",
      }}>
        <h1 style={{
          fontSize: 36, fontWeight: 700, color: C.text,
          fontFamily: "'Noto Serif SC', serif", margin: "0 0 12px",
        }}>
          辑佚史智能体
        </h1>
        <p style={{
          fontSize: 16, color: C.textM, maxWidth: 500, margin: "0 auto 24px",
          lineHeight: 1.8,
        }}>
          基于 GraphRAG 的辑佚学知识问答系统
        </p>

        {/* 统计数据 */}
        {stats && (
          <div style={{ display: "flex", justifyContent: "center", gap: 40, marginBottom: 30 }}>
            {[
              [stats.entity_count, "实体数"],
              [stats.relation_count, "关系数"],
              [Object.keys(stats.entity_types || {}).length, "实体类型"],
            ].map(([value, label]) => (
              <div key={label} style={{ textAlign: "center" }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: C.brownBtn }}>{value}</div>
                <div style={{ fontSize: 12, color: C.textL }}>{label}</div>
              </div>
            ))}
          </div>
        )}

        <button onClick={() => navigate("research-home")} style={{
          background: C.brownBtn, color: "#fff", border: "none", borderRadius: 24,
          padding: "12px 36px", fontSize: 15, cursor: "pointer", fontFamily: "inherit",
          boxShadow: "0 4px 12px rgba(138,69,32,0.3)",
        }}>
          开始探索
        </button>
      </div>

      {/* 功能特色 */}
      <div style={{ padding: "40px 60px", maxWidth: 900, margin: "0 auto" }}>
        <h2 style={{
          fontSize: 22, fontWeight: 700, color: C.text, textAlign: "center",
          fontFamily: "'Noto Serif SC', serif", margin: "0 0 32px",
        }}>
          功能特色
        </h2>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {features.map((f, i) => (
            <div
              key={i}
              onClick={f.action}
              style={{
                background: C.white, borderRadius: 16, padding: "24px 28px",
                border: `1px solid ${C.border}`, cursor: "pointer",
                transition: "all .2s",
                boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
              }}
              onMouseEnter={e => {
                e.currentTarget.style.boxShadow = "0 8px 24px rgba(0,0,0,0.1)";
                e.currentTarget.style.transform = "translateY(-2px)";
              }}
              onMouseLeave={e => {
                e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.04)";
                e.currentTarget.style.transform = "translateY(0)";
              }}
            >
              <div style={{ fontSize: 28, marginBottom: 12 }}>{f.icon}</div>
              <h3 style={{
                fontSize: 16, fontWeight: 600, color: C.text, margin: "0 0 8px",
                fontFamily: "'Noto Serif SC', serif",
              }}>{f.title}</h3>
              <p style={{ fontSize: 13, color: C.textM, margin: 0, lineHeight: 1.6 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 技术架构 */}
      <div style={{ padding: "30px 60px 50px", maxWidth: 900, margin: "0 auto" }}>
        <h2 style={{
          fontSize: 22, fontWeight: 700, color: C.text, textAlign: "center",
          fontFamily: "'Noto Serif SC', serif", margin: "0 0 24px",
        }}>
          技术架构
        </h2>

        <div style={{
          background: C.white, borderRadius: 16, padding: "24px 32px",
          border: `1px solid ${C.border}`,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16 }}>
            {[
              ["Qwen2.5-7B", "大语言模型"],
              ["Neo4j", "知识图谱"],
              ["bge-large-zh", "向量检索"],
              ["RACE框架", "提示词工程"],
            ].map(([tech, desc], i) => (
              <div key={i} style={{ textAlign: "center", flex: 1, minWidth: 100 }}>
                <div style={{ fontSize: 15, fontWeight: 600, color: C.brownBtn }}>{tech}</div>
                <div style={{ fontSize: 11, color: C.textL }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default HomePage;
