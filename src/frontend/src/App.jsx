import { useState } from "react";
import C from "./constants/colors";

import TopNav from "./components/TopNav";
import ResourceSidebar from "./components/ResourceSidebar";

import HomePage from "./pages/HomePage";
import DataOverviewPage from "./pages/DataOverviewPage";
import EntityListPage from "./pages/EntityListPage";
import EntityExplorePage from "./pages/EntityExplorePage";
import PathQueryPage from "./pages/PathQueryPage";
import GlobalBrowsePage from "./pages/GlobalBrowsePage";
import ResearchSection from "./pages/ResearchSection";
import DataDownloadPage from "./pages/DataDownloadPage";

/* ─────────────── MAIN APP ─────────────── */
export default function App() {
  const [page, setPage] = useState("home");
  const [resourceTab, setResourceTab] = useState("overview");

  const navigate = (target) => {
    setPage(target);
    if (target === "resources-overview") setResourceTab("overview");
    if (target === "resources-explore") setResourceTab("explore");
    if (target === "resources-path") setResourceTab("path");
    if (target === "resources-global") setResourceTab("global");
    if (target === "entity-list") setResourceTab("entity-list");
  };

  const isHomePage = page === "home";
  const isResourcePage = page.startsWith("resources") || page === "entity-list" || resourceTab === "entity-list";
  const isResearchPage = page.startsWith("research");
  const isDownloadPage = page === "data-download";

  const renderResourceContent = () => {
    const tab = resourceTab;
    if (tab === "overview") return <DataOverviewPage navigate={navigate} setResourceTab={setResourceTab} />;
    if (tab === "entity-list") return <EntityListPage />;
    if (tab === "explore") return <EntityExplorePage navigate={navigate} />;
    if (tab === "path") return <PathQueryPage navigate={navigate} />;
    if (tab === "global") return <GlobalBrowsePage navigate={navigate} />;
    return null;
  };

  return (
    <div style={{
      fontFamily: "'Noto Serif SC', 'Noto Sans SC', 'PingFang SC', sans-serif",
      background: C.bg, minHeight: "100vh", display: "flex", flexDirection: "column",
      fontSize: 14,
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&display=swap');
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #c4b8a8; border-radius: 3px; }
        button { font-family: inherit; }
        input { font-family: inherit; }
      `}</style>

      <TopNav page={page} navigate={navigate} />

      <div style={{ flex: 1, display: "flex", overflow: "hidden", minHeight: 0 }}>
        {isHomePage ? (
          <HomePage navigate={navigate} />
        ) : isDownloadPage ? (
          <DataDownloadPage navigate={navigate} />
        ) : isResearchPage ? (
          <ResearchSection navigate={navigate} />
        ) : (
          <>
            <ResourceSidebar
              tab={resourceTab}
              setTab={(t) => { setResourceTab(t); setPage("resources-overview"); }}
              navigate={navigate}
            />
            <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
              {renderResourceContent()}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
