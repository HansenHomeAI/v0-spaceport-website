import { NextResponse } from "next/server";
import { undoSession } from "../../../../../../lib/splat-editor/session-store.js";

export const runtime = "nodejs";

export async function POST(
  _request: Request,
  { params }: { params: { sessionId: string } },
): Promise<Response> {
  try {
    const session = await undoSession(params.sessionId);
    return NextResponse.json({ ok: true, session });
  } catch (error: any) {
    return NextResponse.json(
      { ok: false, error: error?.message || "Failed to undo session change" },
      { status: 400 },
    );
  }
}
