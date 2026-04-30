export const runtime = "edge";

import SogsViewerDevPanel from "../../components/sogs-viewer/SogsViewerDevPanel";
import { MD1_V18_PRODUCTION_LOD_URL } from "../../lib/md1ProductionViewer";

export default function PipelineViewerPage() {
  return <SogsViewerDevPanel defaultBundleUrl={MD1_V18_PRODUCTION_LOD_URL} />;
}
