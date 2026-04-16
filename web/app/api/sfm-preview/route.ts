import { DEFAULT_SFM_PREVIEW_ARTIFACT, getSfmPreviewSample } from "../../../lib/sfmPreview";

export const runtime = "edge";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const payload = await getSfmPreviewSample(DEFAULT_SFM_PREVIEW_ARTIFACT);
    return Response.json(payload, {
      headers: {
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown SfM preview error";
    return Response.json(
      {
        error: message,
      },
      {
        status: 500,
        headers: {
          "Cache-Control": "no-store",
        },
      },
    );
  }
}
