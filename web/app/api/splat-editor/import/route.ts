import { NextResponse } from "next/server";
import {
  createSessionFromSource,
  createSessionFromUpload,
  DEFAULT_IMPORT_SOURCE,
} from "../../../../lib/splat-editor/session-store.js";

export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  try {
    const contentType = request.headers.get("content-type") || "";
    if (contentType.includes("multipart/form-data")) {
      const formData = await request.formData();
      const file = formData.get("file");
      if (!(file instanceof File)) {
        return NextResponse.json({ ok: false, error: "Missing upload file" }, { status: 400 });
      }
      const session = await createSessionFromUpload(file.name, Buffer.from(await file.arrayBuffer()));
      return NextResponse.json({ ok: true, session });
    }

    const body = await request.json().catch(() => ({}));
    const source = typeof body?.source === "string" && body.source.trim() ? body.source.trim() : DEFAULT_IMPORT_SOURCE;
    const session = await createSessionFromSource(source);
    return NextResponse.json({ ok: true, session });
  } catch (error: any) {
    return NextResponse.json(
      { ok: false, error: error?.message || "Failed to import artifact" },
      { status: 500 },
    );
  }
}
