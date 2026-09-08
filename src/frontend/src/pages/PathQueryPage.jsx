import { useState } from "react";
import C from "../constants/colors";
import KnowledgeGraph from "../components/KnowledgeGraph";
import EntityInfoCard from "../components/EntityInfoCard";
import RelationDetailCard from "../components/RelationDetailCard";

function PathQueryPage({ navigate }) {
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [result, setResult] = useState(null);      // { source, target, path, paths }
  const [activePath, setActivePath] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 点击节点 → 展示实体详情（复用实体探索页的 /entity/{name} 逻辑）
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [entityInfo, setEntityInfo] = useState(null);
  const [selectedRelation, setSelectedRelation] = useState(null);

  const handleQuery = async () => {
    if (!source || !target) {
      setError("请输入起点和终点");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/path?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`);
      const data = await res.json();
      setResult(data);
      setActivePath(0);
      setSelectedEntity(null);
      setEntityInfo(null);
      setSelectedRelation(null);
    } catch (err) {
      setError("查询失败：" + err.message);
    }
    setLoading(false);
  };

  const handleNodeClick = async (node) => {
    if (!node) return;
    setSelectedEntity({ name: node.name, id: node.id, label: node.label });
    setSelectedRelation(null);
    try {
      const res = await fetch(`/entity/${encodeURIComponent(node.name)}`);
      const data = await res.json();
      setEntityInfo(data);
    } catch (err) {
      console.error("获取实体信息失败:", err);
    }
  };

  const handleEdgeClick = (edge) => {
    if (edge) setSelectedRelation(edge);
  };

  const paths = result?.paths || [];
  const found = paths && paths.length > 0;
  const current = paths[activePath];
  // 路径节点按顺序赋 hop，供线性布局从左到右排布
  const graphNodes = current ? current.nodes.map((n, i) => ({ ...n, hop: i, is_center: false })) : [];
  const graphEdges = current ? current.edges : [];

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "24px 28px" }}>
      <div style={{ fontSize: 15, color: C.textM, marginBottom: 18, fontFamily: "'Noto Serif SC', serif" }}>
        路径查询（请指定起点与终点）
      </div>

      {/* Input row */}
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 14, flexWrap: "wrap" }}>
        <input
          value={source}
          onChange={e => setSource(e.target.value)}
          placeholder="起点实体（如：马国翰）"
          style={{
            padding: "10px 18px", border: `1px solid ${C.border}`, borderRadius: 10,
            fontSize: 14, background: C.white, outline: "none", width: 180, color: C.text,
            fontFamily: "inherit"
          }}
        />
        <span style={{ fontSize: 20, color: C.textL }}>→</span>
        <input
          value={target}
          onChange={e => setTarget(e.target.value)}
          placeholder="终点实体（如：王应麟）"
          style={{
            padding: "10px 18px", border: `1px solid ${C.border}`, borderRadius: 10,
            fontSize: 14, background: C.white, outline: "none", width: 180, color: C.text,
            fontFamily: "inherit"
          }}
        />
        <button
          onClick={handleQuery}
          disabled={loading}
          style={{
            padding: "10px 28px", background: C.brownBtn, border: "none", borderRadius: 10,
            fontSize: 14, cursor: loading ? "wait" : "pointer", color: "#fff", fontFamily: "inherit",
          }}
        >
          {loading ? "查询中..." : "查询路径"}
        </button>
      </div>

      {error && (
        <div style={{ color: "#c04040", fontSize: 13, marginBottom: 16 }}>{error}</div>
      )}

      {!result && !loading && (
        <div style={{ color: C.textL, fontSize: 13, marginBottom: 8 }}>
          提示：输入两个实体名称，可查询它们在知识图谱中的最短关联路径。可先在「实体探索」中搜索确认实体名称。
        </div>
      )}

      {result && !found && (
        <div style={{
          background: "#fff8f0", borderRadius: 10, padding: "16px 20px",
          border: `1px solid ${C.border}`, color: C.textM, fontSize: 13, marginBottom: 16
        }}>
          「{result.source}」和「{result.target}」之间未找到关联路径。
          请确保输入的实体名称与知识图谱中的名称一致，可先在搜索框中输入部分名称进行搜索。
        </div>
      )}

      {found && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* 路径选择器（多条路径时切换） */}
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {paths.length > 1 && paths.map((p, i) => (
              <button
                key={i}
                onClick={() => { setActivePath(i); setSelectedRelation(null); setSelectedEntity(null); setEntityInfo(null); }}
                style={{
                  padding: "6px 16px", borderRadius: 20, fontSize: 13, cursor: "pointer",
                  background: activePath === i ? C.brownBtn : C.white,
                  color: activePath === i ? "#fff" : C.text,
                  border: `1px solid ${activePath === i ? C.brownBtn : C.border}`,
                  fontFamily: "inherit",
                }}
              >
                路径{i + 1}（{p.length}跳）
              </button>
            ))}
            <span style={{ fontSize: 12, color: C.textL, marginLeft: "auto" }}>
              {current.nodes.length} 个实体 · {current.edges.length} 条关系
            </span>
          </div>

          {/* 路径可视化（线性链）：点节点看实体 · 点连线看关系 */}
          <div style={{ background: C.white, borderRadius: 12, border: `1px solid ${C.border}`, padding: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <h4 style={{ fontSize: 15, fontWeight: 600, color: C.text, margin: 0 }}>
                关联路径 {paths.length > 1 ? `#${activePath + 1}` : ""}（{current.length}跳）
              </h4>
              <div style={{ fontSize: 11, color: C.textL }}>拖动视图 | 滚轮缩放 | 点节点看实体 · 点连线看关系</div>
            </div>
            <div style={{ height: 260 }}>
              <KnowledgeGraph
                key={`${result.source}-${result.target}-${activePath}`}
                nodes={graphNodes}
                edges={graphEdges}
                layout="linear"
                onNodeClick={handleNodeClick}
                onEdgeClick={handleEdgeClick}
                selected={selectedEntity?.id}
              />
            </div>
          </div>

          {/* 点击节点 / 连线的详情（复用实体探索页的组件） */}
          {entityInfo ? (
            <EntityInfoCard entityInfo={entityInfo} />
          ) : selectedEntity ? (
            <div style={{ color: C.textL, fontSize: 13 }}>加载实体详情中…</div>
          ) : null}

          {selectedRelation && <RelationDetailCard relation={selectedRelation} />}
        </div>
      )}
    </div>
  );
}

export default PathQueryPage;
