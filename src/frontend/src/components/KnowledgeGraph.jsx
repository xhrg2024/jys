import { useState, useRef, useCallback } from "react";
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
};

function KnowledgeGraph({ onNodeClick, selected, nodes: propNodes, edges: propEdges }) {
  const nodes = propNodes || [];
  const edges = propEdges || [];
  const [hoveredEdge, setHoveredEdge] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);

  // 视图状态（支持拖动和缩放）
  const [viewBox, setViewBox] = useState({ x: 0, y: 0, w: 660, h: 480 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const svgRef = useRef(null);

  // 鼠标按下 - 开始拖动
  const handleMouseDown = useCallback((e) => {
    if (e.target.tagName === "circle" || e.target.tagName === "text") return;
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  }, []);

  // 鼠标移动 - 拖动视图
  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return;
    const dx = (e.clientX - dragStart.x) * (viewBox.w / 660);
    const dy = (e.clientY - dragStart.y) * (viewBox.h / 480);
    setViewBox(prev => ({
      ...prev,
      x: prev.x - dx,
      y: prev.y - dy,
    }));
    setDragStart({ x: e.clientX, y: e.clientY });
  }, [isDragging, dragStart, viewBox.w, viewBox.h]);

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

  // 计算节点位置
  const centerX = viewBox.w / 2 + viewBox.x;
  const centerY = viewBox.h / 2 + viewBox.y;

  const nodeMap = {};
  const centerNode = nodes.find(n => n.is_center);
  const otherNodes = nodes.filter(n => !n.is_center);

  if (centerNode) {
    nodeMap[centerNode.id] = {
      ...centerNode,
      x: centerX,
      y: centerY,
      r: 42,
      ...NODE_COLORS[centerNode.label] || NODE_COLORS.Entity,
      isCenter: true,
    };
  }

  otherNodes.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / otherNodes.length;
    const radius = 140 + (i % 3) * 40;
    const colors = NODE_COLORS[n.label] || NODE_COLORS.Entity;
    nodeMap[n.id] = {
      ...n,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
      r: 30,
      ...colors,
      isCenter: false,
    };
  });

  if (!centerNode) {
    nodes.forEach((n, i) => {
      if (!nodeMap[n.id]) {
        const angle = (2 * Math.PI * i) / nodes.length;
        const radius = 120;
        const colors = NODE_COLORS[n.label] || NODE_COLORS.Entity;
        nodeMap[n.id] = {
          ...n,
          x: centerX + radius * Math.cos(angle),
          y: centerY + radius * Math.sin(angle),
          r: 32,
          ...colors,
          isCenter: false,
        };
      }
    });
  }

  // 绘制边
  const edgeLines = edges.map((e, i) => {
    const from = nodeMap[e.source];
    const to = nodeMap[e.target];
    if (!from || !to) return null;

    const dx = to.x - from.x, dy = to.y - from.y, d = Math.hypot(dx, dy);
    if (d === 0) return null;

    // 查找源和目标的名称
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
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
    >
      {/* 绘制边 */}
      {edgeLines.map(e => (
        <g key={e.key}>
          <line
            x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2}
            stroke={hoveredEdge === e.key ? C.brownBtn : "#b0a090"}
            strokeWidth={hoveredEdge === e.key ? 2.5 : 1.5}
            onMouseEnter={() => setHoveredEdge(e.key)}
            onMouseLeave={() => setHoveredEdge(null)}
            style={{ cursor: "pointer" }}
          />
          {/* 边上的标签背景 */}
          <rect
            x={e.mx - 22} y={e.my - 10} width={44} height={16}
            fill="white" rx={4} opacity={0.9}
            stroke={hoveredEdge === e.key ? C.brownBtn : "transparent"}
            strokeWidth={1}
          />
          {/* 边上的关系类型 */}
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
            {e.type.length > 8 ? e.type.slice(0, 8) + "..." : e.type}
          </text>
        </g>
      ))}

      {/* 绘制节点 */}
      {Object.values(nodeMap).map(n => (
        <g
          key={n.id}
          onClick={() => onNodeClick && onNodeClick(n.id)}
          onMouseEnter={() => setHoveredNode(n.id)}
          onMouseLeave={() => setHoveredNode(null)}
          style={{ cursor: "pointer" }}
        >
          <circle
            cx={n.x} cy={n.y} r={n.r}
            fill={n.fill}
            stroke={selected === n.id ? C.brownBtn : n.stroke}
            strokeWidth={n.isCenter ? 3 : 2}
            filter={n.isCenter ? "url(#glow)" : "none"}
          />
          <text
            x={n.x} y={n.y + (n.isCenter ? 5 : 4)}
            textAnchor="middle"
            fontSize={n.isCenter ? 13 : 11}
            fill={n.tc}
            fontFamily="'Noto Serif SC', serif"
            fontWeight={n.isCenter ? "700" : "600"}
          >
            {n.name.length > 8 ? n.name.slice(0, 8) + "..." : n.name}
          </text>
        </g>
      ))}

      {/* 悬停提示框 - 显示关系详情 */}
      {hoveredEdge !== null && edgeLines[hoveredEdge] && (
        <g>
          <rect
            x={edgeLines[hoveredEdge].mx - 80}
            y={edgeLines[hoveredEdge].my - 50}
            width={160} height={40}
            fill="white" stroke={C.border} strokeWidth={1}
            rx={6} filter="url(#shadow)"
          />
          <text
            x={edgeLines[hoveredEdge].mx}
            y={edgeLines[hoveredEdge].my - 35}
            textAnchor="middle" fontSize={10} fill={C.text} fontWeight="600"
          >
            {edgeLines[hoveredEdge].fromName} → {edgeLines[hoveredEdge].toName}
          </text>
          <text
            x={edgeLines[hoveredEdge].mx}
            y={edgeLines[hoveredEdge].my - 20}
            textAnchor="middle" fontSize={9} fill={C.textM}
          >
            关系：{edgeLines[hoveredEdge].type}
          </text>
        </g>
      )}

      {/* 悬停提示框 - 显示节点详情 */}
      {hoveredNode && nodeMap[hoveredNode] && (
        <g>
          <rect
            x={nodeMap[hoveredNode].x - 60}
            y={nodeMap[hoveredNode].y - nodeMap[hoveredNode].r - 35}
            width={120} height={28}
            fill="white" stroke={C.border} strokeWidth={1}
            rx={6} filter="url(#shadow)"
          />
          <text
            x={nodeMap[hoveredNode].x}
            y={nodeMap[hoveredNode].y - nodeMap[hoveredNode].r - 17}
            textAnchor="middle" fontSize={10} fill={C.text}
          >
            {nodeMap[hoveredNode].label}
          </text>
        </g>
      )}

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
