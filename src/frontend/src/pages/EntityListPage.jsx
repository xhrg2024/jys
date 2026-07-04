import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, CartesianGrid,
} from "recharts";
import C from "../constants/colors";

/* ─────────────── PAGE: 辑佚者列表 ─────────────── */
const ALPHA = "ABCDEFGHIJKLMNOPQRS".split("");
const FREQ_DATA = [
  { x: "1", y: 320 }, { x: "2-5", y: 270 }, { x: "6-10", y: 200 },
  { x: "11-20", y: 140 }, { x: "21-50", y: 65 }, { x: "51-100", y: 18 }, { x: "100+", y: 8 },
];
const PIE_DATA = [
  { name: "内文提及", value: 52, fill: "#9a8060" },
  { name: "标题出现", value: 31, fill: "#c4a870" },
  { name: "文章作者", value: 17, fill: "#ddc8a0" },
];
const LINE_DATA = [
  { x: "前1", y: 8 }, { x: "前5", y: 22 }, { x: "前10", y: 38 }, { x: "前20", y: 55 },
  { x: "前50", y: 72 }, { x: "前100", y: 85 }, { x: "前200", y: 94 }, { x: "全部", y: 100 },
];

function EntityListPage() {
  const [activeLetter, setActiveLetter] = useState("L");
  return (
    <div style={{ flex: 1, overflow: "auto", padding: "28px 32px", position: "relative" }}>
      <div style={{ display: "flex", gap: 12, alignItems: "baseline", marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: C.text, fontFamily: "'Noto Serif SC', serif", margin: 0 }}>辑佚者</h2>
        <span style={{ fontSize: 13, color: C.textL }}>共100条，总引用次数240次</span>
      </div>

      {/* Stats row */}
      <div style={{ display: "flex", gap: 32, marginBottom: 24 }}>
        {[["1,024", "收录作者数", "+38"], ["48,302", "总引用次数", "+1,240"], ["4.7", "平均著数\n每位作者", null], ["312", "本月新提及", "-12"]].map(([v, l, d]) => (
          <div key={l}>
            <div style={{ fontSize: 22, fontWeight: 700, color: C.text, fontFamily: "'Noto Serif SC', serif" }}>{v}</div>
            <div style={{ fontSize: 11, color: C.textL, whiteSpace: "pre" }}>{l}</div>
            {d && <div style={{ fontSize: 11, color: d.startsWith("+") ? "#4a8a60" : "#c04040" }}>个{d.startsWith("+") ? "较上月 " : "↓较上月 "}{d}</div>}
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div style={{ display: "flex", gap: 20, marginBottom: 28 }}>
        <div style={{ flex: 1, background: C.white, borderRadius: 12, padding: "14px 14px 8px", border: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: C.textM, marginBottom: 2 }}>提及次数分布</div>
          <div style={{ fontSize: 10, color: C.textL, marginBottom: 6 }}>各提及次数区间的作者人数</div>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={FREQ_DATA} margin={{ top: 0, right: 4, left: -20, bottom: 0 }}>
              <XAxis dataKey="x" tick={{ fontSize: 9.5, fill: C.textL }} />
              <YAxis tick={{ fontSize: 9.5, fill: C.textL }} />
              <Bar dataKey="y" fill="#9a8060" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div style={{ width: 200, background: C.white, borderRadius: 12, padding: "14px", border: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: C.textM, marginBottom: 2 }}>提及来源类型</div>
          <div style={{ fontSize: 10, color: C.textL, marginBottom: 4 }}>出现在文章内文、标题或作者橱窗的比例</div>
          <div style={{ display: "flex", gap: 6, marginBottom: 6, flexWrap: "wrap" }}>
            {PIE_DATA.map(p => <span key={p.name} style={{ fontSize: 9.5, color: C.textL }}>■ {p.name} {p.value}%</span>)}
          </div>
          <ResponsiveContainer width="100%" height={110}>
            <PieChart>
              <Pie data={PIE_DATA} cx="50%" cy="50%" innerRadius={30} outerRadius={52} dataKey="value">
                {PIE_DATA.map((p, i) => <Cell key={i} fill={p.fill} />)}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div style={{ flex: 1, background: C.white, borderRadius: 12, padding: "14px", border: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: C.textM, marginBottom: 2 }}>累积提及占比</div>
          <div style={{ fontSize: 10, color: C.textL, marginBottom: 6 }}>前N名作者估全站总提及的比例</div>
          <ResponsiveContainer width="100%" height={130}>
            <LineChart data={LINE_DATA} margin={{ top: 0, right: 4, left: -20, bottom: 0 }}>
              <XAxis dataKey="x" tick={{ fontSize: 9, fill: C.textL }} />
              <YAxis tick={{ fontSize: 9, fill: C.textL }} domain={[0, 100]} tickFormatter={v => `${v}%`} />
              <CartesianGrid strokeDasharray="3 3" stroke={C.borderL} />
              <Line type="monotone" dataKey="y" stroke="#9a8060" strokeWidth={2} dot={{ r: 3, fill: "#9a8060" }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* List */}
      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 10 }}>
            <span style={{ fontSize: 24, fontWeight: 700, color: C.brownBtn, fontFamily: "serif" }}>{activeLetter}</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "auto 1fr 2fr", gap: "0", borderTop: `1px solid ${C.border}` }}>
            {["", "提及次数", "出处"].map(h => (
              <div key={h} style={{ padding: "8px 12px", fontSize: 12.5, fontWeight: 600, color: C.textM, borderBottom: `1px solid ${C.border}` }}>{h}</div>
            ))}
            <div style={{ padding: "14px 12px", display: "flex", alignItems: "center" }}>
              <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 20, padding: "6px 20px", fontSize: 14, fontFamily: "'Noto Serif SC', serif", cursor: "pointer" }}>李白</div>
            </div>
            <div style={{ padding: "14px 12px", fontSize: 13.5, color: C.text, display: "flex", alignItems: "center" }}>32次</div>
            <div style={{ padding: "14px 12px", display: "flex", gap: 8, alignItems: "center" }}>
              {["《寄李白》", "《太平御覽》", "《李白傳》"].map(t => (
                <span key={t} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 14, padding: "5px 12px", fontSize: 12, color: C.text }}>{t}</span>
              ))}
            </div>
            {[1, 2].map(i => (
              <React.Fragment key={i}>
                <div style={{ padding: "14px 12px" }}><div style={{ background: "#ebe5d8", borderRadius: 20, height: 32, width: 80 }} /></div>
                <div style={{ padding: "14px 12px" }} />
                <div style={{ padding: "14px 12px" }} />
              </React.Fragment>
            ))}
          </div>
        </div>
        {/* Alpha index */}
        <div style={{ display: "flex", flexDirection: "column", gap: 2, paddingTop: 4 }}>
          {ALPHA.map(l => (
            <div key={l} onClick={() => setActiveLetter(l)} style={{
              fontSize: 11.5, color: l === activeLetter ? C.brownBtn : C.textL, cursor: "pointer",
              fontWeight: l === activeLetter ? 700 : 400, padding: "1px 4px",
            }}>{l}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default EntityListPage;