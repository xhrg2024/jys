import { useState } from "react";
import C from "../constants/colors";

function PathQueryPage({ navigate }) {
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [pathResult, setPathResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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
      setPathResult(data);
    } catch (err) {
      setError("查询失败：" + err.message);
    }
    setLoading(false);
  };

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "24px 28px" }}>
      <div style={{ fontSize: 15, color: C.textM, marginBottom: 18, fontFamily: "'Noto Serif SC', serif" }}>
        路径查询（请指定起点与终点）
      </div>

      {/* Input row */}
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 14 }}>
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
            padding: "10px 28px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10,
            fontSize: 14, cursor: loading ? "wait" : "pointer", color: C.text, fontFamily: "inherit",
          }}
        >
          {loading ? "查询中..." : "查询路径"}
        </button>
      </div>

      {error && (
        <div style={{ color: "#c04040", fontSize: 13, marginBottom: 16 }}>{error}</div>
      )}

      {pathResult && (
        <div>
          <div style={{ fontSize: 14, color: C.text, marginBottom: 12 }}>
            {pathResult.path && !pathResult.path.includes("未找到")
              ? `找到路径：${pathResult.source} → ${pathResult.target}`
              : "未找到路径"}
          </div>

          {pathResult.path && !pathResult.path.includes("未找到") && (
            <div style={{
              background: C.white, borderRadius: 10, padding: "16px 20px",
              border: `1px solid ${C.border}`, marginBottom: 16
            }}>
              <div style={{ fontSize: 13, color: C.textM, marginBottom: 8 }}>路径详情：</div>
              <div style={{ fontSize: 14, color: C.text, lineHeight: 1.8 }}>
                {pathResult.path.split("，").map((step, i, arr) => (
                  <span key={i}>
                    <span style={{ fontWeight: 600, color: C.nodePurp }}>{step}</span>
                    {i < arr.length - 1 && <span style={{ color: C.textL }}> → </span>}
                  </span>
                ))}
              </div>
            </div>
          )}

          {!pathResult.path || pathResult.path.includes("未找到") ? (
            <div style={{
              background: "#fff8f0", borderRadius: 10, padding: "16px 20px",
              border: `1px solid ${C.border}`, color: C.textM, fontSize: 13
            }}>
              提示：请确保输入的实体名称与知识图谱中的名称一致。
              可以先在搜索框中输入部分名称进行搜索。
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

export default PathQueryPage;
