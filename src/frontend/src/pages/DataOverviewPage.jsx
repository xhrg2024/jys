import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Cell, ResponsiveContainer } from "recharts";
import C from "../constants/colors";

function DataOverviewPage({ navigate, setResourceTab }) {
  const [hovered, setHovered] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/stats")
      .then(res => res.json())
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load stats:", err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: C.textM }}>
        加载中...
      </div>
    );
  }

  // 转换数据为图表格式
  const entityTypes = stats?.entity_types
    ? Object.entries(stats.entity_types).map(([label, count]) => ({ label, count }))
    : [];

  const entityCards = [
    ["Compilation", "类书", "辑本"],
    ["Scholar", "辑佚者", "学者"],
    ["Time", "历史时期", ""],
    ["Method", "研究方法", ""],
  ];

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "28px 36px" }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, color: C.text, marginBottom: 6, fontFamily: "'Noto Serif SC', serif" }}>
        数据概览
      </h2>
      <hr style={{ border: "none", borderTop: `1px solid ${C.border}`, marginBottom: 24 }} />

      {/* 统计卡片 */}
      <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
        <div style={{
          background: C.white, borderRadius: 12, padding: "18px 24px",
          border: `1px solid ${C.border}`, flex: 1, textAlign: "center"
        }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: C.nodeBeig }}>{stats?.entity_count || 0}</div>
          <div style={{ fontSize: 13, color: C.textM }}>实体总数</div>
        </div>
        <div style={{
          background: C.white, borderRadius: 12, padding: "18px 24px",
          border: `1px solid ${C.border}`, flex: 1, textAlign: "center"
        }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: C.nodeBeig }}>{stats?.relation_count || 0}</div>
          <div style={{ fontSize: 13, color: C.textM }}>关系总数</div>
        </div>
      </div>

      <h2 style={{ fontSize: 20, fontWeight: 700, color: C.text, marginBottom: 6, fontFamily: "'Noto Serif SC', serif" }}>
        实体类型
      </h2>
      <hr style={{ border: "none", borderTop: `1px solid ${C.border}`, marginBottom: 24 }} />

      <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, flex: 1 }}>
          {entityTypes.slice(0, 6).map(({ label, count }) => (
            <div
              key={label}
              onClick={() => setResourceTab("entity-list")}
              style={{
                background: C.white, borderRadius: 12, padding: "18px 20px",
                border: `1px solid ${C.border}`, cursor: "pointer",
                transition: "box-shadow .15s",
                boxShadow: hovered === label ? "0 4px 16px rgba(0,0,0,0.1)" : "0 1px 6px rgba(0,0,0,0.04)",
              }}
              onMouseEnter={() => setHovered(label)}
              onMouseLeave={() => setHovered(null)}
            >
              <div style={{ fontSize: 15, fontWeight: 600, color: C.text, marginBottom: 8, fontFamily: "'Noto Serif SC', serif" }}>
                {label}
              </div>
              <hr style={{ border: "none", borderTop: `1px solid ${C.borderL}`, marginBottom: 8 }} />
              <div style={{ fontSize: 13, color: C.textM }}>总数：{count}条</div>
            </div>
          ))}
        </div>

        {entityTypes.length > 0 && (
          <div style={{ width: 320, background: C.white, borderRadius: 12, padding: "16px", border: `1px solid ${C.border}` }}>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={entityTypes.slice(0, 6)} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: C.textM }} />
                <YAxis tick={{ fontSize: 11, fill: C.textM }} />
                <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                  {entityTypes.slice(0, 6).map((_, i) => (
                    <Cell key={i} fill={i === 0 ? C.nodeBeig : "#c4b090"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}

export default DataOverviewPage;
