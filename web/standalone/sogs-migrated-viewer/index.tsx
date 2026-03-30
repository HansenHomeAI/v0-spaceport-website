import { createRoot } from "react-dom/client";
import SogsMigratedViewer from "../../components/sogs-migrated-viewer/SogsMigratedViewer";

const mountNode = document.getElementById("root");

if (!mountNode) {
  throw new Error("Missing #root mount for sogs-migrated-viewer standalone app.");
}

createRoot(mountNode).render(<SogsMigratedViewer />);
