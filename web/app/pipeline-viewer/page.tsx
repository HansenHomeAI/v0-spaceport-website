import SfmPreviewClient from "../../components/sfm-preview/SfmPreviewClient";

export const runtime = "edge";
export const dynamic = "force-dynamic";

const DEFAULT_OUTPUT_S3_URI =
  "s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap";

export const metadata = {
  title: "Pipeline Viewer",
  description: "COLMAP sparse output preview for pipeline validation runs.",
};

export default function PipelineViewerPage({
  searchParams,
}: {
  searchParams?: {
    url?: string;
  };
}) {
  return <SfmPreviewClient initialUrl={searchParams?.url || DEFAULT_OUTPUT_S3_URI} />;
}
