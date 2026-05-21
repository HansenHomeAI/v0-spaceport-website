import { buildSfmPreviewPayload, parseSfmArtifact } from "../../../lib/sfmPreview";

export const runtime = "edge";
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const params = new URL(request.url).searchParams;
    const artifact = parseSfmArtifact(params.get("url"));
    const maxPoints = Number(params.get("maxPoints") || 18000);
    const includeDebugSeams = params.get("debugSeams") === "1";
    const payload = await buildSfmPreviewPayload(
      artifact,
      Number.isFinite(maxPoints) ? maxPoints : 18000,
      includeDebugSeams,
    );
    return Response.json(payload, {
      headers: {
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    return Response.json(
      {
        error: error instanceof Error ? error.message : "Unknown SfM preview error",
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
