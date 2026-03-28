import fs from "node:fs/promises";
import { buildExportArtifact } from "../../../../../../lib/splat-editor/session-store.js";

export const runtime = "nodejs";

export async function GET(
  _request: Request,
  { params }: { params: { sessionId: string } },
): Promise<Response> {
  try {
    const artifact = await buildExportArtifact(params.sessionId);
    const buffer = await fs.readFile(artifact.filePath);
    return new Response(new Uint8Array(buffer), {
      status: 200,
      headers: {
        "Content-Type": artifact.contentType,
        "Content-Disposition": `attachment; filename="${artifact.fileName}"`,
        "Cache-Control": "no-store, max-age=0",
      },
    });
  } catch (error: any) {
    return new Response(error?.message || "Failed to export artifact", { status: 500 });
  }
}
