import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, LabelList, Cell,
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

/* 辑佚史朝代顺序与归并规则：match 用于把 清初/清末/清代康熙年间 等散碎取值归并到朝代 */
export const PERIOD_ORDER = [
  { label: "先秦", years: "—前221", match: /先秦|春秋|战国|周朝|西周|东周/ },
  { label: "两汉", years: "前202–220", match: /两汉|西汉|东汉|汉/ },
  { label: "魏晋南北朝", years: "220–589", match: /魏晋|三国|南北朝|北魏|南朝|北朝|两晋|十六国/ },
  { label: "隋唐", years: "581–907", match: /隋|唐/ },
  { label: "五代十国", years: "907–960", match: /五代|十国/ },
  { label: "宋代", years: "960–1279", match: /宋/ },
  { label: "辽金", years: "916–1234", match: /辽|金/ },
  { label: "元代", years: "1271–1368", match: /元/ },
  { label: "明代", years: "1368–1644", match: /明/ },
  { label: "清代", years: "1644–1912", match: /清|乾隆|康熙|雍正|嘉庆|道光|咸丰|同治|光绪|宣统|1[78]\d\d/ },
  { label: "近现代", years: "1912–", match: /民国|近现代|现代|当代|19\d\d|20\d\d/ },
];

/* 将时期分布按朝代归并（未命中的保留原值，如 日本平安时代） */
export function groupPeriods(dist) {
  const buckets = {};
  Object.entries(dist || {}).forEach(([raw, count]) => {
    const idx = PERIOD_ORDER.findIndex(p => p.match.test(raw));
    const key = idx >= 0 ? PERIOD_ORDER[idx].label : raw;
    buckets[key] = (buckets[key] || 0) + count;
  });
  return buckets;
}

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
export function HBars({ data, color = C.nodeTeal, height = 260, total, usePalette = false }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 36, left: 8, bottom: 4 }}>
        <XAxis type="number" hide />
        <YAxis type="category" dataKey="name" width={88} interval={0}
          tick={({ x, y, payload }) => (
            <text x={x} y={y + 3} textAnchor="end" fill={C.textM} fontSize={12}>
              {truncate(payload.value, 6)}
            </text>
          )} />
        <Tooltip content={<ChartTooltip total={total} />} cursor={{ fill: C.borderL }} />
        <Bar dataKey="count" fill={color} radius={[0, 3, 3, 0]} maxBarSize={18}>
          {usePalette && data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
          <LabelList dataKey="count" position="right" style={{ fill: C.textM, fontSize: 11 }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
