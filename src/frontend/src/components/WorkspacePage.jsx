import C from "../constants/colors";
import ResourceSidebar from "./ResourceSidebar";
import DataOverviewPage from "../pages/DataOverviewPage";
import EntityListPage from "../pages/EntityListPage";
import EntityExplorePage from "../pages/EntityExplorePage";
import PathQueryPage from "../pages/PathQueryPage";
import ResearchSection from "../pages/ResearchSection";
import ImportPage from "../pages/ImportPage";

/* ─────────────── WORKSPACE：资源浏览 / 智能对话 / 图谱导入 三合一 ─────────────── */
function WorkspacePage({ navigate, workspaceTab, setWorkspaceTab, resourceTab, setResourceTab }) {
  const items = [
    { key: "browse", label: "资源浏览" },
    { key: "chat", label: "智能对话" },
    { key: "import", label: "图谱导入" },
  ];

  const renderContent = () => {
    if (workspaceTab === "chat") return <ResearchSection navigate={navigate} />;
    if (workspaceTab === "import") return <ImportPage navigate={navigate} />;
    // 资源浏览：沿用原有 ResourceSidebar（全局浏览 / 实体探索 / 路径查询）
    const tab = resourceTab;
    let content = null;
    if (tab === "overview") content = <DataOverviewPage navigate={navigate} setResourceTab={setResourceTab} />;
    else if (tab === "entity-list") content = <EntityListPage />;
    else if (tab === "explore") content = <EntityExplorePage navigate={navigate} />;
    else if (tab === "path") content = <PathQueryPage navigate={navigate} />;
    return (
      <>
        <ResourceSidebar tab={resourceTab} setTab={setResourceTab} navigate={navigate} />
        <div style={{ flex: 1, display: "flex", overflow: "hidden", minHeight: 0 }}>{content}</div>
      </>
    );
  };

  return (
    <div style={{ flex: 1, display: "flex", overflow: "hidden", minHeight: 0 }}>
      <aside style={{
        width: 150, background: C.sidebar, flexShrink: 0, display: "flex", flexDirection: "column",
        borderRight: `1px solid ${C.border}`,
      }}>
        {items.map(item => (
          <div key={item.key} onClick={() => setWorkspaceTab(item.key)} style={{
            padding: "18px 20px", fontSize: 14.5, color: C.text, cursor: "pointer",
            background: workspaceTab === item.key ? C.sidebarAct : "transparent",
            borderLeft: workspaceTab === item.key ? `3px solid ${C.brownBtn}` : "3px solid transparent",
            fontWeight: workspaceTab === item.key ? 600 : 400,
            transition: "background .15s",
          }}>{item.label}</div>
        ))}
      </aside>
      <div style={{ flex: 1, display: "flex", overflow: "hidden", minHeight: 0 }}>
        {renderContent()}
      </div>
    </div>
  );
}

export default WorkspacePage;
