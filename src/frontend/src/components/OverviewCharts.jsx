import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, LabelList,
} from "recharts";
import C from "../constants/colors";

/* 图表配色 */
export const PALETTE = [
  C.nodeBeig, C.nodeTeal, C.nodePurp, C.nodePink, C.gold,
  "#8fbfae", "#b5a67e", "#a9a0cf", "#cfaa9a", "#7f9f8f",
];

export const fmt = n => (n == null ? 0 : Number(n).toLocaleString("zh-CN"));

/* 将 {key: count} 转为图表数组，key 经映射表转中文，降序；保留原始 key 于 raw */
export const toChart = (obj, cnMap) =>
  Object.entries(obj || {})
    .map(([k, count]) => ({ name: (cnMap && cnMap[k]) || k, raw: k, count }))
    .sort((a, b) => b.count - a.count);

/* 截断过长文本（按字符数，超出加省略号），用于坐标轴标签 */
export const truncate = (s, n) => (s && s.length > n ? s.slice(0, n) + "…" : s);

/* 悬浮提示：显示名称 + 数量 + 占比（total 为该分布总数） */
export function ChartTooltip({ active, payload, total }) {
  if (!active || !payload || !payload.length) return null;
  const p = payload[0];
  const v = p.value ?? p.payload?.count ?? 0;
  const name = p.payload?.name ?? p.name ?? "";
  const pct = total ? ((v / total) * 100).toFixed(1) : null;
  return (
    <div style={{
      background: C.brownDk, color: "#fff", borderRadius: 8,
      padding: "8px 12px", fontSize: 12, boxShadow: "0 4px 16px rgba(0,0,0,0.2)",
    }}>
      <div style={{ fontWeight: 600, marginBottom: 2, maxWidth: 240 }}>{name}</div>
      <div style={{ opacity: 0.92 }}>数量：{fmt(v)}</div>
      {pct && <div style={{ opacity: 0.92 }}>占比：{pct}%</div>}
    </div>
  );
}

/* 横向条形图（长中文标签友好，悬浮显示数量 + 占比） */
export function HBars({ data, color = C.nodeTeal, height = 260, total }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 36, left: 8, bottom: 4 }}>
        <XAxis type="number" hide />
        <YAxis type="category" dataKey="name" width={88}
          tick={({ x, y, payload }) => (
            <text x={x} y={y + 3} textAnchor="end" fill={C.textM} fontSize={12}>
              {truncate(payload.value, 6)}
            </text>
          )} />
        <Tooltip content={<ChartTooltip total={total} />} cursor={{ fill: C.borderL }} />
        <Bar dataKey="count" fill={color} radius={[0, 3, 3, 0]} maxBarSize={18}>
          <LabelList dataKey="count" position="right" style={{ fill: C.textM, fontSize: 11 }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
