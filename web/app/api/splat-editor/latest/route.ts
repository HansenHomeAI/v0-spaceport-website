import { NextResponse } from "next/server";
import { getLatestSessionPublicState } from "../../../../lib/splat-editor/session-store.js";

export const runtime = "nodejs";

export async function GET(): Promise<Response> {
  try {
    const session = await getLatestSessionPublicState();
    return NextResponse.json({ ok: true, session });
  } catch (error: any) {
    return NextResponse.json(
      { ok: false, error: error?.message || "Failed to load latest session" },
      { status: 500 },
    );
  }
}
