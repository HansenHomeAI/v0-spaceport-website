import { NextRequest } from "next/server";

export const runtime = "edge";

const ALLOWED_HOST_PATTERNS = [
  /^spaceport-ml-processing(?:-[a-z0-9-]+)?\.s3\.amazonaws\.com$/i,
  /^spaceport-ml-processing(?:-[a-z0-9-]+)?\.s3\.us-west-2\.amazonaws\.com$/i,
];

const normalizeUpstreamUrl = (segments: string[]): URL | null => {
  if (!segments.length) {
    return null;
  }

  const joined = segments.join("/");
  let urlString = joined;
  if (urlString.startsWith("https:/") && !urlString.startsWith("https://")) {
    urlString = urlString.replace("https:/", "https://");
  }
  if (urlString.startsWith("http:/") && !urlString.startsWith("http://")) {
    urlString = urlString.replace("http:/", "http://");
  }
  urlString = urlString.replace(/^https:\/\//, "https://").replace(/^http:\/\//, "http://");
  try {
    const url = new URL(urlString);
    if (!ALLOWED_HOST_PATTERNS.some((pattern) => pattern.test(url.host))) {
      return null;
    }
    return url;
  } catch (error) {
    return null;
  }
};

export async function GET(request: NextRequest, { params }: { params: { resource: string[] } }) {
  const upstreamUrl = normalizeUpstreamUrl(params.resource ?? []);
  if (!upstreamUrl) {
    return new Response("Invalid or disallowed upstream resource", { status: 400 });
  }

  const upstreamResponse = await fetch(upstreamUrl, {
    headers: {
      "Accept": request.headers.get("accept") ?? "*/*",
    },
  });

  const headers = new Headers(upstreamResponse.headers);
  headers.set("Access-Control-Allow-Origin", "*");
  headers.delete("content-security-policy");

  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers,
  });
}
