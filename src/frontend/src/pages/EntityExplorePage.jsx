import { useState } from "react";
import C from "../constants/colors";
import KnowledgeGraph from "../components/KnowledgeGraph";

// 实体类型 label → 中文（展示用）
const LABEL_CN = {
  Scholar: "学者", Compilation: "辑本", Time: "时期", Method: "方法",
  Methodology: "方法", Academic: "学术", Leishu: "类书", Entity: "实体",
};

// 属性值格式化：列表转顿号分隔，其余转字符串
const fmtVal = (v) => (Array.isArray(v) ? v.filter(Boolean).join("、") : String(v ?? ""));

function EntityExplorePage({ navigate }) {
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [entityInfo, setEntityInfo] = useState(null);
  const [selectedRelation, setSelectedRelation] = useState(null);
  const [graphNodes, setGraphNodes] = useState([]);
  const [graphEdges, setGraphEdges] = useState([]);
  const [loading, setLoading] = useState(false);
  const [graphLoading, setGraphLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      setSearchResults(data.results || []);
    } catch (err) {
      console.error("搜索失败:", err);
    }
    setLoading(false);
  };

  const handleSelectEntity = async (entity) => {
    setSelectedEntity(entity);
    setSelectedRelation(null); // 切换实体时清空已选关系
    setLoading(true);
    setGraphLoading(true);
    // 实体结构化详情
    try {
      const infoRes = await fetch(`/entity/${encodeURIComponent(entity.name)}`);
      const infoData = await infoRes.json();
      setEntityInfo(infoData);
    } catch (err) {
      console.error("获取实体信息失败:", err);
    }
    // 力导向图数据（中心节点 + 两跳邻居）
    try {
      const graphRes = await fetch(`/graph?name=${encodeURIComponent(entity.name)}&depth=2&limit=60`);
      const graphData = await graphRes.json();
      setGraphNodes(graphData.nodes || []);
      setGraphEdges(graphData.edges || []);
    } catch (err) {
      console.error("加载图谱失败:", err);
    }
    setGraphLoading(false);
    setLoading(false);
  };

  const handleEdgeClick = (edge) => {
    if (edge) setSelectedRelation(edge);
  };

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "24px 28px", display: "flex", flexDirection: "column" }}>
      {/* Search */}
      <div style={{ display: "flex", alignItems: "center", background: C.white, border: `1px solid ${C.border}`, borderRadius: 28, padding: "10px 20px", marginBottom: 8, maxWidth: 560, alignSelf: "center", width: "100%" }}>
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleSearch()}
          placeholder="搜索实体（如：马国翰、玉函山房辑佚书）"
          style={{ flex: 1, border: "none", outline: "none", fontSize: 14, background: "transparent", color: C.text, fontFamily: "inherit" }}
        />
        <button onClick={handleSearch} style={{
          background: C.brownBtn, color: "#fff", border: "none", borderRadius: 20,
          padding: "6px 20px", fontSize: 13, cursor: "pointer", fontFamily: "inherit"
        }}>搜索</button>
      </div>
      <div style={{ textAlign: "center", fontSize: 12, color: C.textL, marginBottom: 16 }}>
        支持实体种类：人物、辑本、历史时期、研究方法等；点击图谱节点探索实体，点击连线查看关系
      </div>

      <div style={{ display: "flex", flex: 1, gap: 16, minHeight: 360 }}>
        {/* 左侧：搜索结果列表 */}
        <div style={{ width: 280, background: C.white, borderRadius: 12, border: `1px solid ${C.border}`, padding: 12, overflow: "auto" }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: C.text, marginBottom: 12 }}>搜索结果</div>
          {loading && <div style={{ color: C.textM, fontSize: 13 }}>搜索中...</div>}
          {searchResults.length === 0 && !loading && (
            <div style={{ color: C.textL, fontSize: 13 }}>输入关键词搜索实体</div>
          )}
          {searchResults.map((entity, i) => (
            <div
              key={i}
              onClick={() => handleSelectEntity(entity)}
              style={{
                padding: "10px 12px", borderRadius: 8, cursor: "pointer",
                background: selectedEntity?.name === entity.name ? "rgba(138,69,32,0.1)" : "transparent",
                marginBottom: 4, transition: "background .15s",
              }}
            >
              <div style={{ fontSize: 14, color: C.text, fontWeight: 500 }}>{entity.name}</div>
              <div style={{ fontSize: 11, color: C.textL }}>{entity.labels.join(", ")}</div>
            </div>
          ))}
        </div>

        {/* 右侧：实体详情 + 关系详情 + 力导向图 */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
          {/* 实体信息卡（结构化） */}
          {entityInfo ? (
            <div style={{ background: C.white, borderRadius: 12, border: `1px solid ${C.border}`, padding: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
                <h3 style={{ fontSize: 18, fontWeight: 700, color: C.text, margin: 0, fontFamily: "'Noto Serif SC', serif" }}>
                  {entityInfo.name}
                </h3>
                {entityInfo.label && (
                  <span style={{
                    fontSize: 11, color: C.brownBtn, background: "rgba(138,69,32,0.08)",
                    padding: "2px 10px", borderRadius: 12, border: `1px solid rgba(138,69,32,0.2)`,
                  }}>
                    {LABEL_CN[entityInfo.label] || entityInfo.label}
                  </span>
                )}
              </div>
              {entityInfo.properties && Object.keys(entityInfo.properties).length > 0 ? (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 10 }}>
                  {Object.entries(entityInfo.properties).map(([k, v]) => (
                    <div key={k} style={{ background: "#faf7f0", borderRadius: 8, padding: "8px 12px", border: `1px solid ${C.borderL}` }}>
                      <div style={{ fontSize: 11, color: C.textL, marginBottom: 3 }}>{k}</div>
                      <div style={{ fontSize: 13, color: C.text, lineHeight: 1.5 }}>{fmtVal(v)}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: 13, color: C.textL }}>该实体暂无属性信息</div>
              )}
            </div>
          ) : (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: C.textL }}>
              选择一个实体查看详情
            </div>
          )}

          {/* 关系详情卡（点击连线后展示） */}
          {selectedRelation && (
            <div style={{ background: "rgba(138,69,32,0.04)", borderRadius: 12, border: `1px solid rgba(138,69,32,0.2)`, padding: 14 }}>
              <div style={{ fontSize: 12, color: C.textL, marginBottom: 6 }}>关系详情</div>
              <div style={{ fontSize: 14, color: C.text, fontWeight: 600 }}>
                {selectedRelation.fromName}
                <span style={{ color: C.brownBtn, margin: "0 8px" }}>—{selectedRelation.type || "相关"}→</span>
                {selectedRelation.toName}
              </div>
              {selectedRelation.description && (
                <div style={{ fontSize: 12.5, color: C.textM, marginTop: 6, lineHeight: 1.6 }}>
                  {selectedRelation.description}
                </div>
              )}
            </div>
          )}

          {/* 力导向图（节点可点切换实体，连线可点查看关系） */}
          {selectedEntity && (
            <div style={{ background: C.white, borderRadius: 12, border: `1px solid ${C.border}`, padding: 20, flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <h4 style={{ fontSize: 15, fontWeight: 600, color: C.text, margin: 0 }}>
                  关联关系图谱 {graphLoading ? "(加载中...)" : ""}
                </h4>
                <div style={{ fontSize: 11, color: C.textL }}>拖动节点 | 滚轮缩放 | 点节点看实体 · 点连线看关系</div>
              </div>
              <div style={{ height: 380 }}>
                <KnowledgeGraph
                  nodes={graphNodes}
                  edges={graphEdges}
                  layout="force"
                  onNodeClick={(node) => {
                    if (node) handleSelectEntity({ name: node.name, id: node.id, labels: [node.label] });
                  }}
                  onEdgeClick={handleEdgeClick}
                  selected={selectedEntity?.id}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default EntityExplorePage;
