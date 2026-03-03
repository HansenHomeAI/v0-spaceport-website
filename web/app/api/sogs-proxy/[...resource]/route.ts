import { NextRequest } from "next/server";

export const runtime = "edge";

const ALLOWED_HOSTS = new Set([
  "spaceport-ml-processing.s3.amazonaws.com",
  "spaceport-ml-processing.s3.us-west-2.amazonaws.com",
]);
const ALLOWED_PROTOCOLS = new Set(["http:", "https:"]);

const normalizeUpstreamUrl = (urlString: string): URL | null => {
  if (urlString.startsWith("https:/") && !urlString.startsWith("https://")) {
    urlString = urlString.replace("https:/", "https://");
  }
  if (urlString.startsWith("http:/") && !urlString.startsWith("http://")) {
    urlString = urlString.replace("http:/", "http://");
  }
  urlString = urlString.replace(/^https:\/\//, "https://").replace(/^http:\/\//, "http://");
  try {
    const url = new URL(urlString);
    if (!ALLOWED_PROTOCOLS.has(url.protocol)) {
      return null;
    }
    if (!ALLOWED_HOSTS.has(url.host)) {
      return null;
    }
    return url;
  } catch (error) {
    return null;
  }
};

const getProxyPrefixes = (request: NextRequest): string[] => {
  const basePath =
    (typeof request.nextUrl.basePath === "string" ? request.nextUrl.basePath : "") ||
    process.env.NEXT_PUBLIC_BASE_PATH ||
    "";

  const normalizedBasePath =
    basePath && basePath !== "/" ? `/${basePath.replace(/^\/+|\/+$/g, "")}` : "";

  return normalizedBasePath
    ? [`${normalizedBasePath}/api/sogs-proxy/`, "/api/sogs-proxy/"]
    : ["/api/sogs-proxy/"];
};

const getRawUpstreamUrl = (request: NextRequest): URL | null => {
  const requestUrl = new URL(request.url);
  let rawUpstream: string | null = null;

  for (const prefix of getProxyPrefixes(request)) {
    if (requestUrl.pathname.startsWith(prefix)) {
      rawUpstream = requestUrl.pathname.slice(prefix.length);
      break;
    }
  }

  if (!rawUpstream) {
    return null;
  }

  const looksLikeEncodedFullUrl = /^https?%3A/i.test(rawUpstream);
  let upstreamCandidate = rawUpstream;
  if (looksLikeEncodedFullUrl) {
    try {
      upstreamCandidate = decodeURIComponent(rawUpstream);
    } catch {
      return null;
    }
  }

  const upstreamUrl = normalizeUpstreamUrl(upstreamCandidate);
  if (!upstreamUrl) {
    return null;
  }

  if (request.nextUrl.search && !upstreamUrl.search) {
    upstreamUrl.search = request.nextUrl.search;
  }
  return upstreamUrl;
};

export async function GET(request: NextRequest, _context: { params: { resource: string[] } }) {
  const upstreamUrl = getRawUpstreamUrl(request);
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
