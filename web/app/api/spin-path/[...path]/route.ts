import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function stripTrailingSlash(rawUrl: string): string {
  return rawUrl.replace(/\/+$/, "");
}

function resolveDronePathBase(): string {
  const publicUrl = (process.env.NEXT_PUBLIC_DRONE_PATH_API_URL || "").trim();
  return publicUrl.startsWith("http") ? stripTrailingSlash(publicUrl) : "";
}

function looksLikeHtml(body: string, contentType: string): boolean {
  if (contentType.toLowerCase().includes("text/html")) {
    return true;
  }

  const prefix = body.trimStart().slice(0, 200).toLowerCase();
  return prefix.startsWith("<!doctype html") || prefix.startsWith("<html");
}

async function proxySpinPath(request: NextRequest, path: string[]) {
  const base = resolveDronePathBase();
  if (!base) {
    return NextResponse.json(
      { error: "Drone Path API is not configured. Set NEXT_PUBLIC_DRONE_PATH_API_URL and restart the dev server." },
      { status: 500 },
    );
  }

  const search = request.nextUrl.search || "";
  const url = `${base}/api/spin-path/${path.join("/")}${search}`;

  const headers: Record<string, string> = {};
  const authHeader = request.headers.get("authorization");
  if (authHeader) {
    headers.Authorization = authHeader;
  }
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers["Content-Type"] = contentType;
  }

  const init: RequestInit = {
    method: request.method,
    headers,
  };

  if (!["GET", "HEAD"].includes(request.method)) {
    const bodyText = await request.text();
    if (bodyText) {
      init.body = bodyText;
    }
  }

  const response = await fetch(url, init);
  const responseText = await response.text();
  const responseContentType = response.headers.get("content-type") || "application/json";

  if (looksLikeHtml(responseText, responseContentType)) {
    return NextResponse.json(
      { error: "Drone Path API returned HTML instead of JSON. Check NEXT_PUBLIC_DRONE_PATH_API_URL." },
      { status: 502 },
    );
  }

  return new NextResponse(responseText, {
    status: response.status,
    headers: {
      "Content-Type": responseContentType,
    },
  });
}

export async function GET(request: NextRequest, context: { params: { path: string[] } }) {
  return proxySpinPath(request, context.params.path);
}

export async function POST(request: NextRequest, context: { params: { path: string[] } }) {
  return proxySpinPath(request, context.params.path);
}
