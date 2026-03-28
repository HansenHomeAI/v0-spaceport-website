import { NextResponse } from "next/server";
import { getSessionPublicState } from "../../../../../lib/splat-editor/session-store.js";

export const runtime = "nodejs";

export async function GET(
  _request: Request,
  { params }: { params: { sessionId: string } },
): Promise<Response> {
  try {
    const session = await getSessionPublicState(params.sessionId);
    return NextResponse.json({ ok: true, session });
  } catch (error: any) {
    return NextResponse.json(
      { ok: false, error: error?.message || "Failed to load session" },
      { status: 404 },
    );
  }
}

