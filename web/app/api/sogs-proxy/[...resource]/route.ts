import { NextRequest } from "next/server";

export const runtime = "edge";

const ALLOWED_HOST_PATTERNS = [
  /^spaceport-ml-processing(?:-[a-z0-9-]+)?\.s3\.amazonaws\.com$/i,
  /^spaceport-ml-processing(?:-[a-z0-9-]+)?\.s3\.us-west-2\.amazonaws\.com$/i,
];

const encoder = new TextEncoder();
const EMPTY_SHA256 =
  "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

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

const encodeRfc3986 = (value: string) =>
  encodeURIComponent(value).replace(/[!'()*]/g, (char) => `%${char.charCodeAt(0).toString(16).toUpperCase()}`);

const toHex = (bytes: Uint8Array) => Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");

const toArrayBuffer = (bytes: Uint8Array) =>
  bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);

const sha256Hex = async (value: string) => {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(value));
  return toHex(new Uint8Array(digest));
};

const hmacSha256 = async (key: Uint8Array, value: string) => {
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    toArrayBuffer(key),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", cryptoKey, encoder.encode(value));
  return new Uint8Array(signature);
};

const deriveSigningKey = async (secretAccessKey: string, dateStamp: string, region: string, service: string) => {
  const kDate = await hmacSha256(encoder.encode(`AWS4${secretAccessKey}`), dateStamp);
  const kRegion = await hmacSha256(kDate, region);
  const kService = await hmacSha256(kRegion, service);
  return hmacSha256(kService, "aws4_request");
};

const buildCanonicalUri = (pathname: string) => pathname.split("/").map(encodeRfc3986).join("/");

const buildCanonicalQueryString = (url: URL) =>
  Array.from(url.searchParams.entries())
    .sort(([leftKey, leftValue], [rightKey, rightValue]) => {
      if (leftKey === rightKey) {
        return leftValue.localeCompare(rightValue);
      }
      return leftKey.localeCompare(rightKey);
    })
    .map(([key, value]) => `${encodeRfc3986(key)}=${encodeRfc3986(value)}`)
    .join("&");

const buildSignedS3Headers = async (url: URL) => {
  const accessKeyId = process.env.SOGS_PROXY_AWS_ACCESS_KEY_ID ?? "";
  const secretAccessKey = process.env.SOGS_PROXY_AWS_SECRET_ACCESS_KEY ?? "";
  const sessionToken = process.env.SOGS_PROXY_AWS_SESSION_TOKEN ?? "";
  const region = process.env.SOGS_PROXY_AWS_REGION ?? "us-west-2";
  if (!accessKeyId || !secretAccessKey) {
    return null;
  }

  const now = new Date();
  const isoString = now.toISOString().replace(/[:-]|\.\d{3}/g, "");
  const amzDate = `${isoString.slice(0, 8)}T${isoString.slice(8, 14)}Z`;
  const dateStamp = amzDate.slice(0, 8);

  const headers: Record<string, string> = {
    host: url.host,
    "x-amz-content-sha256": EMPTY_SHA256,
    "x-amz-date": amzDate,
  };
  if (sessionToken) {
    headers["x-amz-security-token"] = sessionToken;
  }

  const canonicalHeaders = Object.entries(headers)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => `${key}:${value.trim()}\n`)
    .join("");
  const signedHeaders = Object.keys(headers)
    .sort()
    .join(";");
  const canonicalRequest = [
    "GET",
    buildCanonicalUri(url.pathname),
    buildCanonicalQueryString(url),
    canonicalHeaders,
    signedHeaders,
    EMPTY_SHA256,
  ].join("\n");
  const credentialScope = `${dateStamp}/${region}/s3/aws4_request`;
  const stringToSign = [
    "AWS4-HMAC-SHA256",
    amzDate,
    credentialScope,
    await sha256Hex(canonicalRequest),
  ].join("\n");
  const signingKey = await deriveSigningKey(secretAccessKey, dateStamp, region, "s3");
  const signature = toHex(await hmacSha256(signingKey, stringToSign));

  return {
    ...headers,
    Authorization:
      `AWS4-HMAC-SHA256 Credential=${accessKeyId}/${credentialScope}, SignedHeaders=${signedHeaders}, Signature=${signature}`,
  };
};

export async function GET(request: NextRequest, { params }: { params: { resource: string[] } }) {
  const upstreamUrl = normalizeUpstreamUrl(params.resource ?? []);
  if (!upstreamUrl) {
    return new Response("Invalid or disallowed upstream resource", { status: 400 });
  }

  const signedHeaders = await buildSignedS3Headers(upstreamUrl);
  const upstreamResponse = await fetch(upstreamUrl, {
    headers: {
      Accept: request.headers.get("accept") ?? "*/*",
      ...(signedHeaders ?? {}),
    },
  });

  const headers = new Headers(upstreamResponse.headers);
  headers.set("Access-Control-Allow-Origin", "*");
  headers.delete("content-security-policy");
  headers.delete("content-disposition");

  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers,
  });
}
