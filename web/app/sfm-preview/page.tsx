import SfmPreviewClient from "../../components/sfm-preview/SfmPreviewClient";
import {
  DEFAULT_SFM_PREVIEW_ARTIFACT,
  getSfmPreviewPageData,
  type SfmPreviewPageData,
} from "../../lib/sfmPreview";

export const runtime = "edge";
export const dynamic = "force-dynamic";

export const metadata = {
  title: "2000 Rung Ladder SfM Inspector",
  description: "COLMAP inspector for the latest completed 2000-ladder SfM output.",
};

function fallbackPageData(message: string): SfmPreviewPageData {
  return {
    artifact: DEFAULT_SFM_PREVIEW_ARTIFACT,
    exactPointCount: null,
    registeredImageCount: null,
    chunkCount: null,
    planner: message,
    linkExpirySeconds: 0,
    links: [],
  };
}

export default async function SfmPreviewPage() {
  let pageData: SfmPreviewPageData;

  try {
    pageData = await getSfmPreviewPageData(DEFAULT_SFM_PREVIEW_ARTIFACT);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to reach S3 for preview metadata";
    pageData = fallbackPageData(message);
  }

  return <SfmPreviewClient pageData={pageData} />;
}
