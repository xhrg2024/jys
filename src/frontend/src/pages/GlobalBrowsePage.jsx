import { useState, useEffect } from "react";
import C from "../constants/colors";
import KnowledgeGraph from "../components/KnowledgeGraph";

function GlobalBrowsePage({ navigate }) {
  const [entities, setEntities] = useState([]);
  const [filteredEntities, setFilteredEntities] = useState([]);
  const [selectedLabel, setSelectedLabel] = useState("all");
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [entityInfo, setEntityInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  // 图谱数据
  const [graphNodes, setGraphNodes] = useState([]);
  const [graphEdges, setGraphEdges] = useState([]);
  const [graphLoading, setGraphLoading] = useState(false);

  // 获取所有实体
  useEffect(() => {
    fetch("/entities")
      .then(res => res.json())
      .then(data => {
        setEntities(data.entities || []);
        setFilteredEntities(data.entities || []);
        setLoading(false);
      })
      .catch(err => {
        console.error("加载实体失败:", err);
        setLoading(false);
      });
  }, []);

  // 按类型筛选
  useEffect(() => {
    if (selectedLabel === "all") {
      setFilteredEntities(entities);
    } else {
      setFilteredEntities(entities.filter(e => e.labels.includes(selectedLabel)));
    }
  }, [selectedLabel, entities]);

  // 加载图谱数据
  const loadGraph = (entityName) => {
    setGraphLoading(true);
    const url = entityName
      ? `/graph?name=${encodeURIComponent(entityName)}&depth=1&limit=30`
      : `/graph?limit=20`;
    fetch(url)
      .then(res => res.json())
      .then(data => {
        setGraphNodes(data.nodes || []);
        setGraphEdges(data.edges || []);
        setGraphLoading(false);
      })
      .catch(err => {
        console.error("加载图谱失败:", err);
        setGraphLoading(false);
      });
  };

  // 初始加载
  useEffect(() => {
    loadGraph(null);
  }, []);

  const handleSelectEntity = async (entity) => {
    setSelectedEntity(entity);
    // 加载该实体的图谱
    loadGraph(entity.name);
    try {
      const res = await fetch(`/entity/${encodeURIComponent(entity.name)}`);
      const data = await res.json();
      setEntityInfo(data);
    } catch (err) {
      console.error("获取实体信息失败:", err);
    }
  };

  // 统计各类型数量
  const typeCount = {};
  entities.forEach(e => {
    e.labels.forEach(l => {
      typeCount[l] = (typeCount[l] || 0) + 1;
    });
  });

  const types = Object.entries(typeCount).sort((a, b) => b[1] - a[1]);

  if (loading) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: C.textM }}>
        加载中...
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "24px 28px" }}>
      {/* 筛选面板 */}
      <h2 style={{ fontSize: 18, fontWeight: 700, color: C.text, marginBottom: 20, fontFamily: "'Noto Serif SC', serif" }}>
        全局浏览
      </h2>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 18, flexWrap: "wrap" }}>
        <span style={{ fontSize: 13.5, color: C.textM }}>实体类型：</span>
        <button
          onClick={() => setSelectedLabel("all")}
          style={{
            padding: "6px 16px", borderRadius: 20,
            border: `1px solid ${selectedLabel === "all" ? C.brownBtn : C.border}`,
            background: selectedLabel === "all" ? "rgba(138,69,32,0.12)" : C.white,
            color: selectedLabel === "all" ? C.brownBtn : C.text,
            fontSize: 13.5, cursor: "pointer", fontFamily: "inherit",
          }}
        >
          全部 ({entities.length})
        </button>
        {types.slice(0, 10).map(([label, count]) => (
          <button
            key={label}
            onClick={() => setSelectedLabel(label)}
            style={{
              padding: "6px 16px", borderRadius: 20,
              border: `1px solid ${selectedLabel === label ? C.brownBtn : C.border}`,
              background: selectedLabel === label ? "rgba(138,69,32,0.12)" : C.white,
              color: selectedLabel === label ? C.brownBtn : C.text,
              fontSize: 13.5, cursor: "pointer", fontFamily: "inherit",
            }}
          >
            {label} ({count})
          </button>
        ))}
      </div>

      <div style={{ display: "flex", gap: 20, minHeight: 400 }}>
        {/* 左侧：实体列表 */}
        <div style={{ width: 320, background: C.white, borderRadius: 12, border: `1px solid ${C.border}`, padding: 12, overflow: "auto", maxHeight: 500 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: C.text, marginBottom: 12 }}>
            实体列表 ({filteredEntities.length})
          </div>
          {filteredEntities.map((entity, i) => (
            <div
              key={i}
              onClick={() => handleSelectEntity(entity)}
              style={{
                padding: "10px 12px", borderRadius: 8, cursor: "pointer",
                background: selectedEntity?.name === entity.name ? "rgba(138,69,32,0.1)" : "transparent",
                marginBottom: 4, transition: "background .15s",
                borderBottom: `1px solid ${C.borderL}`,
              }}
            >
              <div style={{ fontSize: 14, color: C.text, fontWeight: 500 }}>{entity.name}</div>
              <div style={{ fontSize: 11, color: C.textL }}>
                {entity.labels.join(", ")} | ID: {entity.id}
              </div>
            </div>
          ))}
        </div>

          {/* 中间：知识图谱 */}
          <div style={{ flex: 1, background: C.white, borderRadius: 12, border: `1px solid ${C.border}`, padding: 16, minHeight: 400 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: C.text }}>
                知识图谱 {graphLoading ? "(加载中...)" : ""}
              </div>
              <div style={{ fontSize: 11, color: C.textL }}>
                拖动移动 | 滚轮缩放 | 点击节点展开
              </div>
            </div>
            <div style={{ height: 360 }}>
              <KnowledgeGraph
                nodes={graphNodes}
                edges={graphEdges}
                onNodeClick={(id) => {
                  const node = graphNodes.find(n => n.id === id);
                  if (node) {
                    handleSelectEntity({ name: node.name, id: node.id, labels: [node.label] });
                  }
                }}
                selected={selectedEntity?.id}
              />
            </div>
          </div>

        {/* 右侧：实体详情 */}
        <div style={{ width: 280, background: C.white, borderRadius: 12, border: `1px solid ${C.border}`, padding: 16, overflow: "auto", maxHeight: 500 }}>
          {entityInfo ? (
            <>
              <h3 style={{ fontSize: 16, fontWeight: 700, color: C.text, margin: "0 0 12px", fontFamily: "'Noto Serif SC', serif" }}>
                {selectedEntity?.name}
              </h3>
              <div style={{ fontSize: 12, color: C.text, lineHeight: 1.8, whiteSpace: "pre-wrap" }}>
                {entityInfo.info}
              </div>
            </>
          ) : (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: C.textL, fontSize: 13 }}>
              选择一个实体查看详情
            </div>
          )}
        </div>
      </div>

      {/* 底部统计 */}
      <div style={{ display: "flex", alignItems: "center", gap: 24, marginTop: 16 }}>
        <div style={{ display: "flex", gap: 28 }}>
          {types.slice(0, 4).map(([label, count]) => (
            <div key={label} style={{ textAlign: "center" }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: C.text }}>{count}</div>
              <div style={{ fontSize: 11, color: C.textL }}>{label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default GlobalBrowsePage;
