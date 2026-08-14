import { useState, useRef, useCallback, useEffect } from "react";
import { forceSimulation, forceLink, forceManyBody, forceCollide } from "d3-force";
import C from "../constants/colors";

// 节点颜色映射
const NODE_COLORS = {
  Scholar: { fill: "rgba(122,170,152,0.5)", stroke: "#7aa898", tc: "#2a5040" },
  Compilation: { fill: "rgba(155,142,196,0.5)", stroke: "#9b8ec4", tc: "#4a3090" },
  Time: { fill: "rgba(196,170,128,0.45)", stroke: "#c4a880", tc: "#5a4020" },
  Method: { fill: "rgba(180,140,140,0.5)", stroke: "#b48c8c", tc: "#6a3030" },
  Methodology: { fill: "rgba(180,140,140,0.5)", stroke: "#b48c8c", tc: "#6a3030" },
  Academic: { fill: "rgba(140,160,180,0.5)", stroke: "#8ca0b4", tc: "#304050" },
  Entity: { fill: "rgba(180,180,180,0.4)", stroke: "#b0b0b0", tc: "#505050" },
  Leishu: { fill: "rgba(196,170,128,0.45)", stroke: "#c4a880", tc: "#5a4020" },
};

// hop 0/1/2 的视觉强度：填充/描边/文字透明度（中心最深，二跳最浅）
const HOP_VISUAL = {
  fill: [0.9, 0.62, 0.28],
  stroke: [1, 0.8, 0.45],
  text: [1, 0.85, 0.5],
};

// 根据 hop 层级调整节点填充透明度
function fillForHop(colors, hop) {
  const m = (colors.fill || "").match(/rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)/);
  if (!m) return colors.fill;
  const i = Math.min(Math.max(typeof hop === "number" ? hop : 1, 0), 2);
  return `rgba(${m[1]}, ${m[2]}, ${m[3]}, ${HOP_VISUAL.fill[i]})`;
}

// 径向约束力：中心锚定居中，一跳/二跳拉向各自理想半径，趋于分层"太阳花"布局，
// 配合斥力让节点沿环分布，从而大幅减少边与边之间的交叉。
function radialForce(nodes, cx, cy) {
  const radii = [0, 130, 230];
  return (alpha) => {
    for (const d of nodes) {
      const hop = Math.min(Math.max(typeof d.hop === "number" ? d.hop : 1, 0), 2);
      const targetR = radii[hop];
      const dx = d.x - cx;
      const dy = d.y - cy;
      const r = Math.hypot(dx, dy) || 1e-6;
      const strength = hop === 0 ? 0.4 : 0.12;
      const dr = (targetR - r) * strength * alpha;
      d.vx += (dx / r) * dr;
      d.vy += (dy / r) * dr;
    }
  };
}

// 是否为通用/无意义的关系类型（如 RELATES），这类不显示类型名，改用描述
function isGenericRel(label) {
  const t = String(label || "").trim().toLowerCase();
  return t === "" || t === "relates";
}

// 截断过长文本（用于边标签/提示框）
function truncate(s, n) {
  s = String(s || "");
  return s.length > n ? s.slice(0, n) + "…" : s;
}

// 让节点文字始终落在圆形内：过长先截断（最多 6 字），再按字符数动态缩小字号。
// CJK 全角字符宽≈字号，取圆形直径的 80% 作为可用宽度，确保两侧留边不溢出。
function fitNodeText(name, radius, maxSize) {
  const raw = String(name || "");
  let text = raw;
  if (text.length > 6) text = text.slice(0, 6) + "…";
  const usable = radius * 2 * 0.8;
  const size = Math.min(maxSize, Math.max(7, usable / text.length));
  return { text, size };
}

// ─── 径向布局 ───────────────────────────────────────────────────
function layoutRadial(nodes, width, height) {
  const results = [];
  const cx = width / 2;
  const cy = height / 2;

  const centerNode = nodes.find((n) => n.is_center);
  const otherNodes = nodes.filter((n) => !n.is_center);

  if (centerNode) {
    results.push({ ...centerNode, x: cx, y: cy, r: 42, isCenter: true });
  }

  otherNodes.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / otherNodes.length - Math.PI / 2;
    const radius = 140 + (i % 3) * 40;
    results.push({ ...n, x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle), r: 30, isCenter: false });
  });

  if (!centerNode) {
    nodes.forEach((n, i) => {
      if (!results.find((r) => r.id === n.id)) {
        const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
        results.push({ ...n, x: cx + 120 * Math.cos(angle), y: cy + 120 * Math.sin(angle), r: 32, isCenter: false });
      }
    });
  }

  return results;
}

function KnowledgeGraph({ onNodeClick, selected, nodes: propNodes, edges: propEdges, layout = "radial", height: propHeight }) {
  const nodes = propNodes || [];
  const edges = propEdges || [];
  const svgW = 660;
  // height 为数字时直接使用；字符串（如 "100%"）时使用默认 480（viewBox 需要数值坐标，CSS height:100% 已处理拉伸）
  const numericHeight = typeof propHeight === "number" ? propHeight : 480;

  const [hoveredEdge, setHoveredEdge] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);

  // 视图状态（支持拖动和缩放）
  const [viewBox, setViewBox] = useState({ x: 0, y: 0, w: svgW, h: numericHeight });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const svgRef = useRef(null);

  // d3-force 仿真实例与节点拖拽状态（供拖拽节点手动调整位置）
  const simulationRef = useRef(null);
  const nodeDragRef = useRef(null);       // { node, moved, startX, startY }
  const suppressClickRef = useRef(false); // 拖拽后抑制 click，避免误触发节点跳转

  // 力布局结果
  const [forcePositions, setForcePositions] = useState(null);

  // layout="force" 时运行 d3-force 仿真，随 tick 实时更新位置（动画效果）。
  // 注意：不再用 useRef 缓存 key 做去重——StrictMode 下双调用会使第二次直接跳过仿真。
  useEffect(() => {
    if (layout !== "force" || nodes.length === 0) {
      setForcePositions(null);
      return;
    }

    // 初始位置：中心节点居中，一跳/二跳按 hop 分层随机散布
    const simNodes = nodes.map((n) => {
      const hop = typeof n.hop === "number" ? n.hop : (n.is_center ? 0 : 1);
      const baseR = hop === 0 ? 0 : hop === 1 ? 120 : 220;
      const angle = Math.random() * Math.PI * 2;
      const radius = baseR + Math.random() * 60;
      return {
        ...n,
        x: svgW / 2 + Math.cos(angle) * radius,
        y: numericHeight / 2 + Math.sin(angle) * radius,
      };
    });

    const idSet = new Set(simNodes.map((n) => n.id));
    const links = edges
      .map((e) => ({ source: e.source, target: e.target }))
      .filter((l) => idSet.has(l.source) && idSet.has(l.target));

    const nodeRadius = (d) => (d.hop === 0 ? 46 : d.hop === 1 ? 34 : 28);

    // 立即渲染初始分层布局，避免先显示旧图
    setForcePositions(simNodes.map(({ vx, vy, ...n }) => ({ ...n, x: n.x, y: n.y })));

    const simulation = forceSimulation(simNodes)
      .force("link", forceLink(links).id((d) => d.id).distance(130).strength(0.5))
      .force("charge", forceManyBody().strength(-480).distanceMax(560))
      .force("collide", forceCollide().radius(nodeRadius).strength(1))
      .force("radial", radialForce(simNodes, svgW / 2, numericHeight / 2))
      .alphaDecay(0.03)
      .velocityDecay(0.4);

    simulation.on("tick", () => {
      setForcePositions(simNodes.map(({ vx, vy, ...n }) => ({ ...n, x: n.x, y: n.y })));
    });

    simulationRef.current = simulation;

    return () => {
      simulation.stop();
      simulationRef.current = null;
    };
  }, [layout, nodes, edges, svgW, numericHeight]);

  // 计算最终节点位置（含颜色、半径等）
  const nodePositions = (() => {
    const applyStyle = (n) => {
      const colors = NODE_COLORS[n.label] || NODE_COLORS.Entity;
      const hop = typeof n.hop === "number" ? n.hop : (n.is_center ? 0 : 1);
      const isCenter = n.is_center === true || n.hop === 0;
      const r = isCenter ? 42 : hop === 1 ? 30 : 24;
      const vi = Math.min(Math.max(hop, 0), 2);
      return {
        ...n,
        isCenter,
        r,
        fill: fillForHop(colors, hop),
        stroke: colors.stroke,
        tc: colors.tc,
        strokeOpacity: HOP_VISUAL.stroke[vi],
        textOpacity: HOP_VISUAL.text[vi],
      };
    };
    if (layout === "force" && forcePositions) {
      return forcePositions.map((n) => applyStyle({ ...n, x: n.x, y: n.y }));
    }
    return layoutRadial(nodes, svgW, numericHeight).map(applyStyle);
  })();

  // 构建 nodeMap（按 id 索引）
  const nodeMap = {};
  nodePositions.forEach((n) => { nodeMap[n.id] = n; });

  // 鼠标按下 - 开始拖动
  const handleMouseDown = useCallback((e) => {
    if (e.target.tagName === "circle" || e.target.tagName === "text") return;
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  }, []);

  // 屏幕坐标 → viewBox（力导向世界）坐标
  const toSvgCoords = useCallback((clientX, clientY) => {
    const svg = svgRef.current;
    if (!svg) return null;
    const rect = svg.getBoundingClientRect();
    return {
      x: viewBox.x + ((clientX - rect.left) / rect.width) * viewBox.w,
      y: viewBox.y + ((clientY - rect.top) / rect.height) * viewBox.h,
    };
  }, [viewBox]);

  // ── 节点拖拽：把节点钉到指针位置并加热仿真，其他节点随力实时避让 ──
  const handleNodeDragStart = useCallback((e, n) => {
    e.stopPropagation();
    e.preventDefault();
    const sim = simulationRef.current;
    if (!sim) return;
    const target = sim.nodes().find((d) => d.id === n.id);
    if (!target) return;
    const p = toSvgCoords(e.clientX, e.clientY);
    if (!p) return;
    target.fx = p.x;
    target.fy = p.y;
    nodeDragRef.current = { node: target, moved: false, startX: p.x, startY: p.y };
    suppressClickRef.current = false;
    sim.alphaTarget(0.3).restart();
  }, [toSvgCoords]);

  const handleNodeDragMove = useCallback((e) => {
    const drag = nodeDragRef.current;
    if (!drag) return;
    const p = toSvgCoords(e.clientX, e.clientY);
    if (!p) return;
    if (Math.hypot(p.x - drag.startX, p.y - drag.startY) > 4) {
      drag.moved = true;
      suppressClickRef.current = true;
    }
    drag.node.fx = p.x;
    drag.node.fy = p.y;
  }, [toSvgCoords]);

  const handleNodeDragEnd = useCallback(() => {
    const drag = nodeDragRef.current;
    if (!drag) return;
    drag.node.fx = null;
    drag.node.fy = null;
    nodeDragRef.current = null;
    simulationRef.current?.alphaTarget(0);
  }, []);

  // 鼠标移动 - 拖动视图
  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return;
    const dx = (e.clientX - dragStart.x) * (viewBox.w / svgW);
    const dy = (e.clientY - dragStart.y) * (viewBox.h / numericHeight);
    setViewBox((prev) => ({
      ...prev,
      x: prev.x - dx,
      y: prev.y - dy,
    }));
    setDragStart({ x: e.clientX, y: e.clientY });
  }, [isDragging, dragStart, viewBox.w, viewBox.h, svgW, numericHeight]);

  // 鼠标松开 - 结束拖动
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // 滚轮 - 缩放
  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const scale = e.deltaY > 0 ? 1.1 : 0.9;
    const svg = svgRef.current;
    if (!svg) return;

    const rect = svg.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * viewBox.w + viewBox.x;
    const mouseY = ((e.clientY - rect.top) / rect.height) * viewBox.h + viewBox.y;

    const newW = viewBox.w * scale;
    const newH = viewBox.h * scale;

    if (newW < 100 || newW > 2000) return;

    setViewBox({
      x: mouseX - (mouseX - viewBox.x) * scale,
      y: mouseY - (mouseY - viewBox.y) * scale,
      w: newW,
      h: newH,
    });
  }, [viewBox]);

  if (nodes.length === 0) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: C.textL }}>
        选择一个实体查看其知识图谱
      </div>
    );
  }

  // 绘制边
  const edgeLines = edges.map((e, i) => {
    const from = nodeMap[e.source];
    const to = nodeMap[e.target];
    if (!from || !to) return null;

    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const d = Math.hypot(dx, dy);
    if (d === 0) return null;

    const fromName = from.name || "";
    const toName = to.name || "";

    return {
      key: i,
      x1: from.x + (dx / d) * from.r,
      y1: from.y + (dy / d) * from.r,
      x2: to.x - (dx / d) * to.r,
      y2: to.y - (dy / d) * to.r,
      mx: (from.x + to.x) / 2,
      my: (from.y + to.y) / 2,
      type: e.type,
      description: e.description || "",
      label: isGenericRel(e.type) ? "" : (e.type || "").trim(),
      fromName,
      toName,
    };
  }).filter(Boolean);

  return (
    <svg
      ref={svgRef}
      viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`}
      style={{
        width: "100%",
        height: "100%",
        cursor: isDragging ? "grabbing" : "grab",
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={(e) => { handleNodeDragMove(e); handleMouseMove(e); }}
      onMouseUp={() => { handleNodeDragEnd(); handleMouseUp(); }}
      onMouseLeave={() => { handleNodeDragEnd(); handleMouseUp(); }}
      onWheel={handleWheel}
    >
      {/* 绘制边 */}
      {edgeLines.map((e) => (
        <g key={e.key}>
          <line
            x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2}
            stroke={hoveredEdge === e.key ? C.brownBtn : "#a89880"}
            strokeWidth={hoveredEdge === e.key ? 2.2 : 1.1}
            opacity={hoveredEdge === e.key ? 1 : 0.45}
            onMouseEnter={() => setHoveredEdge(e.key)}
            onMouseLeave={() => setHoveredEdge(null)}
            style={{ cursor: "pointer" }}
          />
          {/* 边上的标签背景（通用 RELATES 类型不显示标签，避免重叠） */}
          {e.label ? (
            <rect
              x={e.mx - 22} y={e.my - 10} width={44} height={16}
              fill="white" rx={4} opacity={0.9}
              stroke={hoveredEdge === e.key ? C.brownBtn : "transparent"}
              strokeWidth={1}
            />
          ) : null}
          {/* 边上的关系类型 */}
          {e.label ? (
            <text
              x={e.mx} y={e.my + 2}
              textAnchor="middle" fontSize={9}
              fill={hoveredEdge === e.key ? C.brownBtn : C.textM}
              fontFamily="'Noto Serif SC', serif"
              fontWeight={hoveredEdge === e.key ? "600" : "400"}
              onMouseEnter={() => setHoveredEdge(e.key)}
              onMouseLeave={() => setHoveredEdge(null)}
              style={{ cursor: "pointer" }}
            >
              {truncate(e.label, 8)}
            </text>
          ) : null}
        </g>
      ))}

      {/* 绘制节点 */}
      {nodePositions.map((n) => {
        const { text: nodeText, size: nodeFontSize } = fitNodeText(n.name, n.r, n.isCenter ? 13 : 11);
        return (
        <g
          key={n.id}
          onClick={() => {
            if (suppressClickRef.current) { suppressClickRef.current = false; return; }
            onNodeClick && onNodeClick(n);
          }}
          onMouseDown={(e) => handleNodeDragStart(e, n)}
          onMouseEnter={() => setHoveredNode(n.id)}
          onMouseLeave={() => setHoveredNode(null)}
          style={{ cursor: "grab" }}
        >
          <circle
            cx={n.x} cy={n.y} r={n.r}
            fill={n.fill}
            stroke={selected === n.id ? C.brownBtn : n.stroke}
            strokeWidth={n.isCenter ? 3 : 2}
            strokeOpacity={n.strokeOpacity}
            filter={n.isCenter ? "url(#glow)" : "none"}
          />
          <text
            x={n.x} y={n.y + (n.isCenter ? 5 : 4)}
            textAnchor="middle"
            fontSize={nodeFontSize}
            fill={n.tc}
            opacity={n.textOpacity}
            fontFamily="'Noto Serif SC', serif"
            fontWeight={n.isCenter ? "700" : "600"}
          >
            {nodeText}
          </text>
        </g>
        );
      })}

      {/* 悬停提示框 - 显示关系详情（通用 RELATES 显示描述而非类型名） */}
      {hoveredEdge !== null && edgeLines[hoveredEdge] && (() => {
        const he = edgeLines[hoveredEdge];
        const line2 = he.label ? `关系：${he.label}` : truncate(he.description, 18);
        return (
          <g>
            <rect
              x={he.mx - 90}
              y={he.my - 50}
              width={180} height={40}
              fill="white" stroke={C.border} strokeWidth={1}
              rx={6} filter="url(#shadow)"
            />
            <text
              x={he.mx}
              y={he.my - 35}
              textAnchor="middle" fontSize={10} fill={C.text} fontWeight="600"
            >
              {he.fromName} → {he.toName}
            </text>
            {line2 ? (
              <text
                x={he.mx}
                y={he.my - 20}
                textAnchor="middle" fontSize={9} fill={C.textM}
              >
                {line2}
              </text>
            ) : null}
          </g>
        );
      })()}

      {/* 悬停提示框 - 显示节点详情（完整名称 + 类型） */}
      {hoveredNode && nodeMap[hoveredNode] && (() => {
        const hn = nodeMap[hoveredNode];
        const fullName = hn.name || "";
        const boxW = Math.min(Math.max(80, fullName.length * 13 + 28), 260);
        return (
          <g>
            <rect
              x={hn.x - boxW / 2}
              y={hn.y - hn.r - 50}
              width={boxW} height={42}
              fill="white" stroke={C.border} strokeWidth={1}
              rx={6} filter="url(#shadow)"
            />
            <text
              x={hn.x}
              y={hn.y - hn.r - 32}
              textAnchor="middle" fontSize={11} fill={C.text} fontWeight="600"
            >
              {fullName}
            </text>
            <text
              x={hn.x}
              y={hn.y - hn.r - 17}
              textAnchor="middle" fontSize={9} fill={C.textM}
            >
              {hn.label}
            </text>
          </g>
        );
      })()}

      {/* 滤镜定义 */}
      <defs>
        <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="shadow" x="-10%" y="-10%" width="120%" height="130%">
          <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity="0.15" />
        </filter>
      </defs>
    </svg>
  );
}

export default KnowledgeGraph;
