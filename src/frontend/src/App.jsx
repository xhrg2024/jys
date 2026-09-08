import { useState } from "react";
import C from "./constants/colors";

import TopNav from "./components/TopNav";
import WorkspacePage from "./components/WorkspacePage";

import HomePage from "./pages/HomePage";
import DataDownloadPage from "./pages/DataDownloadPage";
import AboutPage from "./pages/AboutPage";

/* ─────────────── MAIN APP ─────────────── */
export default function App() {
  const [page, setPage] = useState("home");
  const [workspaceTab, setWorkspaceTab] = useState("chat");   // 资源浏览 / 智能对话 / 图谱导入
  const [resourceTab, setResourceTab] = useState("overview");  // 资源浏览内部的子页

  const navigate = (target) => {
    if (target === "home") { setPage("home"); return; }
    if (target === "data-download") { setPage("data-download"); return; }
    if (target === "about") { setPage("about"); return; }
    // 智能研究工作台（资源浏览 / 智能对话 / 图谱导入）
    setPage("research");
    if (target === "import") {
      setWorkspaceTab("import");
    } else if (target === "research-home" || target === "research-chat" || target === "research") {
      setWorkspaceTab("chat");
    } else {
      setWorkspaceTab("browse");
      if (target === "resources-explore") setResourceTab("explore");
      else if (target === "resources-path") setResourceTab("path");
      else if (target === "entity-list") setResourceTab("entity-list");
      else setResourceTab("overview");
    }
  };

  const isHomePage = page === "home";
  const isDownloadPage = page === "data-download";
  const isAboutPage = page === "about";

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
        .stream-cursor { animation: blink 0.8s infinite; }
        @keyframes blink { 0%,50% { opacity:1; } 51%,100% { opacity:0; } }
      `}</style>

      <TopNav page={page} navigate={navigate} />

      <div style={{ flex: 1, display: "flex", overflow: "hidden", minHeight: 0 }}>
        {isHomePage ? (
          <HomePage navigate={navigate} />
        ) : isDownloadPage ? (
          <DataDownloadPage navigate={navigate} />
        ) : isAboutPage ? (
          <AboutPage navigate={navigate} />
        ) : (
          <WorkspacePage
            navigate={navigate}
            workspaceTab={workspaceTab}
            setWorkspaceTab={setWorkspaceTab}
            resourceTab={resourceTab}
            setResourceTab={setResourceTab}
          />
        )}
      </div>
    </div>
  );
}
