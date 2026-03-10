import { NextRequest } from "next/server";

export const runtime = "edge";

const ALLOWED_BUCKETS = new Set([
  "spaceport-ml-processing",
  "spaceport-ml-processing-staging",
  "spaceport-ml-processing-prod",
]);
const ALLOWED_S3_HOST_SUFFIXES = [".s3.amazonaws.com", ".s3.us-west-2.amazonaws.com"];

const isAllowedUpstreamHost = (host: string): boolean =>
  ALLOWED_S3_HOST_SUFFIXES.some((suffix) => {
    if (!host.endsWith(suffix)) {
      return false;
    }

    const bucketName = host.slice(0, -suffix.length);
    return ALLOWED_BUCKETS.has(bucketName);
  });

const normalizeUpstreamUrl = (urlString: string): URL | null => {
  if (/^http:\//i.test(urlString)) {
    return null;
  }
  if (urlString.startsWith("https:/") && !urlString.startsWith("https://")) {
    urlString = urlString.replace("https:/", "https://");
  }
  urlString = urlString.replace(/^https:\/\//, "https://");
  try {
    const url = new URL(urlString);
    if (url.protocol !== "https:") {
      return null;
    }
    if (!isAllowedUpstreamHost(url.host)) {
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
    return new Response("Invalid upstream URL. Only HTTPS S3 URLs are allowed.", { status: 400 });
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
