import C from "./colors";

/* ─────────────── GRAPH DATA ─────────────── */
export const NODES = [
  { id: "center", label: ["玉函山房", "輯佚書"], x: 330, y: 260, r: 52, fill: C.nodePurp, stroke: C.nodePurp, tc: "#fff", dashed: false },
  { id: "ma",     label: ["馬國翰"],              x: 130, y: 185, r: 37, fill: "rgba(122,170,152,0.18)", stroke: C.nodeTeal, tc: "#3a6050", dashed: true },
  { id: "tai",    label: ["太平御覽"],             x: 540, y: 155, r: 37, fill: "rgba(201,152,152,0.25)", stroke: C.nodePink, tc: "#7a4040", dashed: false },
  { id: "hui",    label: ["惠棟"],                x: 120, y: 355, r: 33, fill: "rgba(122,170,152,0.25)", stroke: C.nodeTeal, tc: "#3a6050", dashed: false },
  { id: "qian",   label: ["乾嘉", "學派"],         x: 535, y: 355, r: 38, fill: "rgba(196,170,128,0.25)", stroke: C.nodeBeig, tc: "#6a5030", dashed: false },
  { id: "zi",     label: ["子部"],                x: 325, y: 390, r: 30, fill: "rgba(184,180,176,0.25)", stroke: C.nodeGray, tc: "#6a6a6a", dashed: false },
];

export const EDGES = [
  { from: "ma",   to: "center", label: "輯佚者" },
  { from: "tai",  to: "center", label: "底本來源" },
  { from: "hui",  to: "ma",     label: "學術傳承" },
  { from: "qian", to: "center", label: "所屬流派" },
  { from: "zi",   to: "center", label: "涵蓋" },
];