import { useState, useEffect } from "react";
import C from "../constants/colors";
import { HBars, toChart, fmt } from "./OverviewCharts";

/* 属性键 → 中文 */
const ATTR_CN = {
  compilationPeriod: "辑佚时期", contentType: "内容类型",
  compilationStyle: "编纂体例", completionPeriod: "成书时期",
  compiler: "编纂者", school: "学派", birthplace: "籍贯",
  periodName: "活跃时期", methodName: "方法", methodEvaluation: "方法评价",
  schoolName: "学派", origin: "起源",
};

const ATTR_COLOR = {
  compilationPeriod: C.nodeBeig, contentType: C.nodeTeal,
  compilationStyle: C.nodePurp, completionPeriod: C.nodePink,
  compiler: C.nodeBeig, school: C.nodePurp, birthplace: C.nodePink,
  periodName: C.nodeTeal, methodName: C.nodeGray, methodEvaluation: C.nodeTeal,
  schoolName: C.nodePurp, origin: C.nodeTeal,
};

function AttrBlock({ attrKey, dist }) {
  const entries = toChart(dist);            // 全量降序
  const total = entries.reduce((s, e) => s + e.count, 0);
  const top = entries.slice(0, 15);
  const shown = entries.length - top.length; // 被截断的其余取值数
  return (
    <div style={{ background: C.white, borderRadius: 12, padding: "16px 20px", border: `1px solid ${C.border}` }}>
      <div style={{ fontSize: 14, fontWeight: 600, color: C.text, marginBottom: 4, fontFamily: "'Noto Serif SC', serif" }}>
        {ATTR_CN[attrKey] || attrKey}
      </div>
      <div style={{ fontSize: 12, color: C.textL, marginBottom: 10 }}>
        共 {entries.length} 种取值，累计 {fmt(total)} 条
        {shown > 0 && <span>（仅展示前 15 种）</span>}
      </div>
      <HBars data={top} color={ATTR_COLOR[attrKey] || C.nodeTeal} total={total} height={Math.max(180, top.length * 26)} />
    </div>
  );
}

function TypeOverview({ label, labelCn, onBack }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`/stats/type/${label}`)
      .then(res => res.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(err => { console.error(err); setError("该类型统计加载失败"); setLoading(false); });
  }, [label]);

  const attrs = data?.attrs ? Object.entries(data.attrs) : [];

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "28px 36px 48px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 6 }}>
        <button
          onClick={onBack}
          style={{
            background: "transparent", border: `1px solid ${C.border}`, borderRadius: 8,
            padding: "6px 14px", fontSize: 13, color: C.textM, cursor: "pointer",
          }}
        >← 返回总览</button>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: C.text, margin: 0, fontFamily: "'Noto Serif SC', serif" }}>
          {labelCn}概览
        </h2>
      </div>
      <div style={{ fontSize: 13, color: C.textM, marginBottom: 20 }}>
        共 {fmt(data?.count)} 个实体
      </div>
      <hr style={{ border: "none", borderTop: `1px solid ${C.border}`, marginBottom: 24 }} />

      {loading ? (
        <div style={{ color: C.textM, textAlign: "center", padding: 40 }}>加载中...</div>
      ) : error ? (
        <div style={{ color: C.textM, textAlign: "center", padding: 40 }}>{error}</div>
      ) : attrs.length === 0 ? (
        <div style={{ color: C.textM, textAlign: "center", padding: 40 }}>该类型暂无可用统计维度</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "start" }}>
          {attrs.map(([key, dist]) => <AttrBlock key={key} attrKey={key} dist={dist} />)}
        </div>
      )}
    </div>
  );
}

export default TypeOverview;
