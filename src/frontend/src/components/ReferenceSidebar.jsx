import { useEffect } from "react";
import C from "../constants/colors";
import GraphSourcePanel from "./GraphSourcePanel";
import RelationSourcePanel from "./RelationSourcePanel";
import SqlSourcePanel from "./SqlSourcePanel";

/**
 * 参考资料右侧栏 — 固定定位滑入面板。
 * 根据 sourceData.source_type 分发到图表面板或 SQL 表格面板；detailData.kind==="relation" 时分发到关系面板。
 */
function ReferenceSidebar({ open, citationNum, sourceData, detailData, loading, onClose, onNodeClick, onEdgeClick, trail, onTrailClick }) {
  // Escape 键关闭
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const isObject = typeof sourceData === 'object';
  const sourceType = isObject ? sourceData.source_type : null;
  const label = isObject ? sourceData.label : "参考";
  const desc = isObject ? sourceData.desc : (sourceData || "");

  const badgeColors = {
    graph: { bg: "rgba(122,170,152,0.2)", tc: "#2a5040", border: "#7aa898" },
    sql: { bg: "rgba(180,140,140,0.2)", tc: "#6a3030", border: "#b48c8c" },
    vector: { bg: "rgba(155,142,196,0.2)", tc: "#4a3090", border: "#9b8ec4" },
  };
  const bc = badgeColors[sourceType] || badgeColors.graph;

  const renderContent = () => {
    if (loading) {
      return (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "60%", color: C.textM, fontSize: 13 }}>
          加载中...
        </div>
      );
    }

    if (detailData?.error) {
      return (
        <div style={{ padding: 20, color: "#a04040", fontSize: 13 }}>
          加载失败：{detailData.error}
        </div>
      );
    }

    if (detailData?.fallback) {
      // 纯文本/无结构化数据
      return (
        <div style={{ padding: 16, fontSize: 13, color: C.text, lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
          {typeof desc === 'string' ? desc.replace(/^[^：:]+[：:]\s*/, '') : JSON.stringify(sourceData, null, 2)}
        </div>
      );
    }

    if (detailData?.kind === "relation") {
      return <RelationSourcePanel data={detailData} onNodeClick={onNodeClick} onEdgeClick={onEdgeClick} trail={trail} onTrailClick={onTrailClick} />;
    }

    switch (sourceType) {
      case "graph":
        return <GraphSourcePanel data={detailData} sourceData={sourceData} onNodeClick={onNodeClick} onEdgeClick={onEdgeClick} trail={trail} onTrailClick={onTrailClick} />;
      case "sql":
        return <SqlSourcePanel data={detailData} sourceData={sourceData} />;
      default:
        return (
          <div style={{ padding: 16, fontSize: 13, color: C.text, lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
            {typeof desc === 'string' ? desc : JSON.stringify(sourceData, null, 2)}
          </div>
        );
    }
  };

  return (
    <>
      {/* 半透明遮罩 */}
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0, zIndex: 90,
          background: "rgba(0,0,0,0.08)",
        }}
      />

      {/* 侧栏面板 */}
      <div style={{
        position: "fixed", top: 0, right: 0, bottom: 0,
        width: 420, maxWidth: "94vw", zIndex: 100,
        background: C.white,
        borderLeft: `2px solid ${C.border}`,
        boxShadow: "-4px 0 20px rgba(0,0,0,0.12)",
        display: "flex", flexDirection: "column",
        animation: "slideIn 0.25s ease-out",
      }}>
        <style>{`
          @keyframes slideIn {
            from { transform: translateX(100%); }
            to { transform: translateX(0); }
          }
        `}</style>

        {/* 头部 */}
        <div style={{
          padding: "14px 16px",
          borderBottom: `1px solid ${C.border}`,
          display: "flex", alignItems: "center", gap: 10,
          flexShrink: 0,
        }}>
          <span style={{
            display: "inline-block", padding: "2px 10px", borderRadius: 10,
            fontSize: 11.5, fontWeight: 600,
            background: bc.bg, color: bc.tc, border: `1px solid ${bc.border}`,
          }}>
            {label}
          </span>
          <span style={{ fontSize: 13, color: C.text, fontWeight: 600 }}>
            {citationNum ? `来源 [${citationNum}]` : ''}
          </span>
          <div style={{ flex: 1 }} />
          <button onClick={onClose}
            style={{
              background: "none", border: "none", cursor: "pointer",
              fontSize: 18, color: C.textM, padding: "2px 6px",
            }}>
            ✕
          </button>
        </div>

        {/* 内容区域 */}
        <div style={{ flex: 1, overflow: "auto" }}>
          {renderContent()}
        </div>
      </div>
    </>
  );
}

export default ReferenceSidebar;
