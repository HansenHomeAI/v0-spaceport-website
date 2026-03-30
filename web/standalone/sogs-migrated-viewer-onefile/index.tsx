import { createRoot } from "react-dom/client";
import SogsMigratedViewer from "../../components/sogs-migrated-viewer/SogsMigratedViewer";

declare global {
  interface Window {
    __SOGS_ONEFILE_VIEWER_SRCDOC__?: string;
  }
}

const mountNode = document.getElementById("root");

if (!mountNode) {
  throw new Error("Missing #root mount for sogs-migrated-viewer one-file app.");
}

createRoot(mountNode).render(
  <SogsMigratedViewer
    useBundleProxy={false}
    viewerSrcDoc={window.__SOGS_ONEFILE_VIEWER_SRCDOC__ ?? ""}
  />,
);
