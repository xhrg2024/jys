import { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Cell, ResponsiveContainer,
  PieChart, Pie, Tooltip, CartesianGrid, LabelList,
} from "recharts";
import C from "../constants/colors";
import TypeOverview from "../components/TypeOverview";
import { PALETTE, ChartTooltip, HBars, toChart, fmt } from "../components/OverviewCharts";

/* 实体类型 → 中文名 */
const LABEL_CN = {
  Compilation: "辑本", Scholar: "学者", Time: "时期", Method: "方法",
  Leishu: "类书", Academic: "学术", Methodology: "方法论",
  Resource_Catalog: "资源目录", Resource_Category: "资源类别",
  Subject_Category: "主题类别", Work_Process: "工作流程",
  Discipline: "学科", Academic_Requirement: "学术要求", Monograph: "专著",
  Medical_Work: "医学著作", Critical_Examination: "考据",
  Discipline_Component: "学科组成", Documentation_Component: "文献组成",
  Error_Classification: "错误分类", Historical_Monument: "历史遗迹",
  Journal: "期刊", Key_Book: "重要典籍", Method_Critique: "方法批评",
  Methodology_Classification: "方法论分类", Pseudo_Book: "伪书",
  Resource_Methodology: "资源方法论", Scholar_Group: "学者群体",
  Scientific_Work: "科学著作",
};

/* 实体类型 → 悬浮描述 */
const LABEL_DESC = {
  Compilation: "辑佚家从传世文献中辑录出的佚书",
  Scholar: "从事辑佚的学者",
  Time: "辑佚活动所处的历史时期",
  Method: "辑佚所采用的方法",
  Leishu: "辑佚所依据的类书",
  Academic: "与辑佚相关的学术概念、学派",
  Methodology: "辑佚方法论",
  Resource_Catalog: "辑佚参考的资源目录",
  Resource_Category: "资源分类",
  Subject_Category: "主题分类",
  Work_Process: "辑佚工作流程",
};

/* 关系类型 → 中文名 */
const REL_CN = {
  hasRepresentativeWork: "代表作", employsMethod: "采用方法",
  targetsText: "辑佚对象", hasTeacher: "师承关系",
  representsperiod: "代表时期", relatedToSchool: "关联学派",
  influencesSchool: "影响学派", methodEvaluation: "方法评价",
};

/* 关系类型 → 悬浮描述 */
const REL_DESC = {
  hasRepresentativeWork: "学者的代表性辑佚著作",
  employsMethod: "辑本所采用的方法",
  targetsText: "辑佚所针对的佚书对象",
  hasTeacher: "学者之间的师承关系",
  representsperiod: "实体所属的历史时期",
  relatedToSchool: "实体与学派的关联",
  influencesSchool: "实体对学派的影响",
  methodEvaluation: "方法评价关系",
};

/* 辑佚史时间轴：主要朝代按历史顺序，match 用于把杂乱的时期取值归并 */
const PERIOD_ORDER = [
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

function buildTimeline(dist) {
  const buckets = PERIOD_ORDER.map(p => ({ label: p.label, years: p.years, count: 0 }));
  let dropped = 0;
  Object.entries(dist || {}).forEach(([raw, count]) => {
    const idx = PERIOD_ORDER.findIndex(p => p.match.test(raw));
    if (idx >= 0) buckets[idx].count += count;
    else dropped += count;
  });
  const timeline = buckets.filter(b => b.count > 0);
  return { timeline, dropped };
}

function Timeline({ timeline, dropped }) {
  const [hover, setHover] = useState(null);
  const max = Math.max(...timeline.map(t => t.count));
  const total = timeline.reduce((s, t) => s + t.count, 0);
  return (
    <div style={{ position: "relative", padding: "6px 0 4px" }}>
      <div style={{ position: "absolute", top: 30, left: "3%", right: "3%", height: 2, background: C.border }} />
      <div style={{ display: "flex", position: "relative" }}>
        {timeline.map((t, i) => {
          const size = 28 + Math.round((t.count / max) * 34);
          const pct = total ? ((t.count / total) * 100).toFixed(1) : "0";
          const isHover = hover === i;
          return (
            <div key={t.label} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}
              onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
              <div style={{ height: 60, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div title={`${t.label}（${t.years}）：${t.count} 部，占 ${pct}%`}
                  style={{
                    width: size, height: size, borderRadius: "50%",
                    background: PALETTE[i % PALETTE.length], color: "#fff",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: size >= 42 ? 13 : 11, fontWeight: 700,
                    border: "2px solid #fff", boxShadow: "0 2px 8px rgba(0,0,0,0.18)",
                    transform: isHover ? "scale(1.14)" : "scale(1)",
                    transition: "transform .15s", zIndex: 1,
                  }}>{t.count}</div>
              </div>
              <div style={{ marginTop: 10, fontSize: 13, fontWeight: 600, color: C.text, fontFamily: "'Noto Serif SC', serif" }}>{t.label}</div>
              <div style={{ fontSize: 11, color: isHover ? C.textM : C.textL, marginTop: 2 }}>
                {isHover ? `${t.years} · ${pct}%` : t.years}
              </div>
            </div>
          );
        })}
      </div>
      {dropped > 0 && (
        <div style={{ fontSize: 12, color: C.textL, marginTop: 8, textAlign: "right" }}>
          另有 {dropped} 条无法归入朝代（如日本平安时代等）
        </div>
      )}
    </div>
  );
}

function Section({ title, action, children, style }) {
  return (
    <section style={{ marginTop: 30, ...style }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 12 }}>
        <h3 style={{ fontSize: 16, fontWeight: 700, color: C.text, margin: 0, fontFamily: "'Noto Serif SC', serif" }}>
          {title}
        </h3>
        {action}
      </div>
      {children}
    </section>
  );
}

function StatCard({ value, label, color, desc }) {
  return (
    <div title={desc} style={{
      background: C.white, borderRadius: 12, padding: "18px 24px",
      border: `1px solid ${C.border}`, flex: 1, textAlign: "center",
      cursor: "default",
    }}>
      <div style={{ fontSize: 28, fontWeight: 700, color, lineHeight: 1.2 }}>{value}</div>
      <div style={{ fontSize: 13, color: C.textM, marginTop: 4 }}>{label}</div>
    </div>
  );
}

function ChartCard({ children, title, note }) {
  return (
    <div style={{ background: C.white, borderRadius: 12, padding: "16px 20px", border: `1px solid ${C.border}` }}>
      {title && <div style={{ fontSize: 14, fontWeight: 600, color: C.text, marginBottom: 2 }}>{title}</div>}
      {note && <div style={{ fontSize: 12, color: C.textL, marginBottom: 8 }}>{note}</div>}
      {children}
    </div>
  );
}

function DataOverviewPage({ navigate, setResourceTab }) {
  const [hovered, setHovered] = useState(null);
  const [stats, setStats] = useState(null);
  const [sqlStats, setSqlStats] = useState(null);
  const [detail, setDetail] = useState(null);   // 下钻的实体类型 label
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("/stats")
      .then(res => res.json())
      .then(data => { setStats(data); setLoading(false); })
      .catch(err => { console.error("Failed to load stats:", err); setError("图谱统计加载失败"); setLoading(false); });

    // MySQL 统计（可选，数据库不可用时静默隐藏该区块）
    fetch("/sql/stats")
      .then(res => res.json())
      .then(data => setSqlStats(data))
      .catch(() => setSqlStats(null));
  }, []);

  if (loading) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: C.textM }}>
        加载中...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: C.textM }}>
        {error}
      </div>
    );
  }

  /* 下钻到某实体类型 */
  if (detail) {
    return (
      <TypeOverview
        label={detail}
        labelCn={LABEL_CN[detail] || detail}
        onBack={() => setDetail(null)}
      />
    );
  }

  const entityTotal = stats?.entity_count || 0;
  const entityTypes = Object.entries(stats?.entity_types || {})
    .map(([label, count]) => ({ label, name: LABEL_CN[label] || label, count }))
    .sort((a, b) => b.count - a.count);
  const relationTypes = toChart(stats?.relation_types, REL_CN);
  const periods = toChart(stats?.compilation_period_dist);
  const contentTypes = toChart(stats?.content_type_dist);
  const schools = toChart(stats?.school_dist).slice(0, 10);
  const birthplaces = toChart(stats?.birthplace_dist).slice(0, 10);
  const compilers = toChart(stats?.compiler_dist).slice(0, 10);
  const compilerMax = compilers.length ? compilers[0].count : 1;
  const { timeline, timelineDropped } = buildTimeline(stats?.compilation_period_dist);

  /* 环形图：Top 6 + 其他 */
  const donutData = entityTypes.slice(0, 6);
  const otherCount = entityTypes.slice(6).reduce((s, e) => s + e.count, 0);
  const donutAll = otherCount > 0 ? [...donutData, { label: "其他", name: "其他", count: otherCount }] : donutData;

  const sqlCards = sqlStats ? [
    { value: sqlStats.documents, label: "文献总数", unit: "部", color: C.nodeBeig },
    { value: sqlStats.authors, label: "编纂者", unit: "位", color: C.nodeTeal },
    { value: sqlStats.full_text_1, label: "正文片段", unit: "条", color: C.nodePurp },
    { value: sqlStats.titles, label: "层级标题", unit: "条", color: C.nodePink },
    { value: sqlStats.documents_with_full_text, label: "有全文的文献", unit: "部", color: C.nodeGray },
    { value: sqlStats.documents_with_metadata, label: "有元数据的文献", unit: "部", color: C.gold },
  ] : [];

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "28px 36px 48px" }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, color: C.text, marginBottom: 6, fontFamily: "'Noto Serif SC', serif" }}>
        数据概览
      </h2>
      <hr style={{ border: "none", borderTop: `1px solid ${C.border}`, marginBottom: 24 }} />

      {/* 统计总览 */}
      <div style={{ display: "flex", gap: 16 }}>
        <StatCard value={fmt(stats?.entity_count)} label="实体总数" color={C.nodeBeig} desc="知识图谱中的节点总数" />
        <StatCard value={fmt(stats?.relation_count)} label="关系总数" color={C.nodeTeal} desc="实体间的关联边总数" />
        <StatCard value={fmt(entityTypes.length)} label="实体类型数" color={C.nodePurp} desc="图谱中出现的实体类别数" />
        <StatCard value={fmt(relationTypes.length)} label="关系类型数" color={C.nodePink} desc="实体间关联的语义类型数" />
      </div>

      {/* 辑佚史时间轴 */}
      {timeline.length > 0 && (
        <Section title="辑佚史时间轴" action={<span style={{ fontSize: 12, color: C.textL }}>按历史时序 · 节点大小表示辑本数量</span>}>
          <div style={{ background: C.white, borderRadius: 12, padding: "20px 24px 12px", border: `1px solid ${C.border}` }}>
            <Timeline timeline={timeline} dropped={timelineDropped} />
          </div>
        </Section>
      )}

      {/* 实体类型分布 */}
      <Section title="实体类型分布" action={<span style={{ fontSize: 12, color: C.textL }}>点击类型卡片下钻查看详情</span>}>
        <div style={{ display: "flex", gap: 24, alignItems: "stretch" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, flex: 1, alignContent: "start" }}>
            {entityTypes.map(({ label, name, count }) => {
              const pct = entityTotal ? ((count / entityTotal) * 100).toFixed(1) : "0";
              const isHover = hovered === label;
              return (
                <div
                  key={label}
                  onClick={() => setDetail(label)}
                  onMouseEnter={() => setHovered(label)}
                  onMouseLeave={() => setHovered(null)}
                  style={{
                    background: C.white, borderRadius: 12, padding: "16px 18px",
                    border: `1px solid ${isHover ? C.brown : C.border}`, cursor: "pointer",
                    transition: "box-shadow .15s, border-color .15s",
                    boxShadow: isHover ? "0 6px 18px rgba(0,0,0,0.1)" : "0 1px 6px rgba(0,0,0,0.04)",
                  }}
                >
                  <div style={{ fontSize: 15, fontWeight: 600, color: C.text, marginBottom: 6, fontFamily: "'Noto Serif SC', serif" }}>
                    {name}
                  </div>
                  <div style={{ fontSize: 13, color: C.textM }}>总数：{fmt(count)}条</div>
                  <div style={{
                    fontSize: 12, color: C.textL, marginTop: 8, lineHeight: 1.5,
                    maxHeight: isHover ? 60 : 0, overflow: "hidden", opacity: isHover ? 1 : 0,
                    transition: "max-height .2s, opacity .2s",
                  }}>
                    占比 {pct}% · {LABEL_DESC[label] || "该类型的实体集合"} · 点击查看详情 →
                  </div>
                </div>
              );
            })}
          </div>

          {donutAll.length > 0 && (
            <div style={{ width: 300, background: C.white, borderRadius: 12, padding: "16px", border: `1px solid ${C.border}`, alignSelf: "start" }}>
              <div style={{ fontSize: 13, color: C.textM, marginBottom: 8 }}>类型占比</div>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ width: 150, height: 180, flexShrink: 0 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={donutAll} dataKey="count" nameKey="name"
                        cx="50%" cy="50%" innerRadius={44} outerRadius={70} paddingAngle={2} strokeWidth={0}>
                        {donutAll.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                      </Pie>
                      <Tooltip content={<ChartTooltip total={entityTotal} />} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
                  {donutAll.map((e, i) => {
                    const pct = entityTotal ? ((e.count / entityTotal) * 100).toFixed(1) : "0";
                    return (
                      <div key={e.name} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: C.textM }}>
                        <span style={{ width: 9, height: 9, borderRadius: 2, background: PALETTE[i % PALETTE.length], flexShrink: 0 }} />
                        <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{e.name}</span>
                        <span style={{ color: C.textL, flexShrink: 0 }}>{pct}%</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </Section>

      {/* 关系类型分布 */}
      {relationTypes.length > 0 && (
        <Section title="关系类型分布">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            <ChartCard>
              <HBars data={relationTypes} color={C.nodeTeal} total={stats?.relation_count || 0} />
            </ChartCard>
            <div style={{ display: "flex", flexDirection: "column", gap: 10, justifyContent: "center" }}>
              {relationTypes.map((r, i) => {
                const pct = stats?.relation_count ? ((r.count / stats.relation_count) * 100).toFixed(1) : "0";
                return (
                  <div key={r.name} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13 }}>
                    <span style={{ width: 9, height: 9, borderRadius: 2, background: PALETTE[i % PALETTE.length], flexShrink: 0 }} />
                    <span style={{ width: 88, color: C.text, flexShrink: 0 }}>{r.name}</span>
                    <span style={{ flex: 1, color: C.textL, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontStyle: "italic" }}
                      title={REL_DESC[r.raw] || ""}>
                      {REL_DESC[r.raw] || "—"}
                    </span>
                    <span style={{ color: C.textM, flexShrink: 0 }}>{r.count} · {pct}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        </Section>
      )}

      {/* 辑佚时期 + 内容类型 */}
      {(periods.length > 0 || contentTypes.length > 0) && (
        <Section title="辑本画像">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            {periods.length > 0 && (
              <ChartCard title="辑佚时期分布" note="辑本所归属的历史时期">
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={periods} margin={{ top: 20, right: 12, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={C.borderL} vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: C.textM }} />
                    <YAxis tick={{ fontSize: 11, fill: C.textM }} />
                    <Tooltip content={<ChartTooltip total={periods.reduce((s, e) => s + e.count, 0)} />} cursor={{ fill: C.borderL }} />
                    <Bar dataKey="count" radius={[3, 3, 0, 0]} maxBarSize={44}>
                      {periods.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                      <LabelList dataKey="count" position="top" style={{ fill: C.textM, fontSize: 11 }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            )}
            {contentTypes.length > 0 && (
              <ChartCard title="内容类型分布" note="辑本的内容体裁分类">
                <HBars data={contentTypes.slice(0, 12)} color={C.nodeBeig}
                  total={contentTypes.reduce((s, e) => s + e.count, 0)} />
              </ChartCard>
            )}
          </div>
        </Section>
      )}

      {/* Top 编纂者排行（比例条） */}
      {compilers.length > 0 && (
        <Section title="Top 编纂者" action={<span style={{ fontSize: 12, color: C.textL }}>按辑本数量排序</span>}>
          <div style={{ background: C.white, borderRadius: 12, padding: "16px 24px", border: `1px solid ${C.border}` }}>
            {compilers.map((c, i) => {
              const pct = compilerMax ? (c.count / compilerMax) * 100 : 0;
              return (
                <div key={c.name} onMouseEnter={() => setHovered(`c${i}`)} onMouseLeave={() => setHovered(null)}
                  style={{
                    display: "flex", alignItems: "center", gap: 14, padding: "7px 0",
                    background: hovered === `c${i}` ? C.bg : "transparent", borderRadius: 6,
                    paddingLeft: 8, paddingRight: 8, transition: "background .12s",
                  }}>
                  <span style={{ width: 22, fontSize: 14, fontWeight: 700, color: i < 3 ? C.gold : C.textL, fontFamily: "serif" }}>
                    {i + 1}
                  </span>
                  <span style={{ width: 150, fontSize: 13, color: C.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                    title={c.name}>{c.name}</span>
                  <div style={{ flex: 1, background: C.borderL, borderRadius: 4, height: 10 }}>
                    <div style={{ width: `${pct}%`, background: PALETTE[i % PALETTE.length], height: 10, borderRadius: 4, transition: "width .3s" }} />
                  </div>
                  <span style={{ width: 60, fontSize: 12, color: C.textM, textAlign: "right", flexShrink: 0 }}>
                    {hovered === `c${i}` ? `占比 ${(c.count / (stats?.compiler_dist ? Object.values(stats.compiler_dist).reduce((s, v) => s + v, 0) : 1) * 100).toFixed(1)}%` : `${c.count} 部`}
                  </span>
                </div>
              );
            })}
          </div>
        </Section>
      )}

      {/* 学者画像分布 */}
      {(schools.length > 0 || birthplaces.length > 0) && (
        <Section title="学者画像分布" action={<span onClick={() => setDetail("Scholar")} style={{ fontSize: 12, color: C.brownBtn, cursor: "pointer" }}>查看学者概览 →</span>}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            {schools.length > 0 && (
              <ChartCard title="学派分布（前 10）">
                <HBars data={schools} color={C.nodePurp} total={Object.values(stats?.school_dist || {}).reduce((s, v) => s + v, 0)} />
              </ChartCard>
            )}
            {birthplaces.length > 0 && (
              <ChartCard title="籍贯分布（前 10）">
                <HBars data={birthplaces} color={C.nodePink} total={Object.values(stats?.birthplace_dist || {}).reduce((s, v) => s + v, 0)} />
              </ChartCard>
            )}
          </div>
        </Section>
      )}

      {/* 文献数据库概览（MySQL 可选） */}
      {sqlCards.length > 0 && (
        <Section title="文献数据库概览">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 14 }}>
            {sqlCards.map(({ value, label, unit, color }) => (
              <div key={label} style={{
                background: C.white, borderRadius: 12, padding: "16px 14px",
                border: `1px solid ${C.border}`, textAlign: "center",
              }}>
                <div style={{ fontSize: 22, fontWeight: 700, color }}>{fmt(value)}</div>
                <div style={{ fontSize: 13, color: C.textM, marginTop: 4 }}>{label}<span style={{ fontSize: 11, color: C.textL }}>（{unit}）</span></div>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

export default DataOverviewPage;
