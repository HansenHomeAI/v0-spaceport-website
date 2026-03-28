import { NextResponse } from "next/server";
import { createSessionFromSource, DEFAULT_IMPORT_SOURCE } from "../../../../lib/splat-editor/session-store.js";

export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  try {
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

