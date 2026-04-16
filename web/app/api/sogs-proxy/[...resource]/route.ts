import { GetObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { Readable } from "node:stream";
import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const S3_REGION = process.env.AWS_REGION ?? "us-west-2";
const s3Client = new S3Client({ region: S3_REGION });

const PIPELINE_BUCKET_PATTERNS = [
  /^spaceport-ml-processing(?:-[a-z0-9-]+)?$/i,
  /^spaceport-ml-delivery(?:-[a-z0-9-]+)?$/i,
  /^spaceport-model-delivery(?:-[a-z0-9-]+)?$/i,
];

const S3_VIRTUAL_HOST_PATTERN = /^(.+)\.s3(?:[.-][a-z0-9-]+)?\.amazonaws\.com$/i;
const S3_PATH_STYLE_HOST_PATTERN = /^s3(?:[.-][a-z0-9-]+)?\.amazonaws\.com$/i;

function isAllowedPipelineBucket(bucket: string): boolean {
  return PIPELINE_BUCKET_PATTERNS.some((pattern) => pattern.test(bucket));
}

function isAllowedEdgeBundleUrl(url: URL): boolean {
  return url.host.endsWith(".cloudfront.net") && url.pathname.startsWith("/models/");
}

function normalizeResponseHeaders(headers: Headers): Headers {
  headers.set("Access-Control-Allow-Origin", "*");
  headers.delete("content-security-policy");
  return headers;
}

function getS3Location(url: URL): { bucket: string; key: string } | null {
  if (url.protocol === "s3:") {
    const bucket = url.hostname.trim();
    const key = url.pathname.replace(/^\/+/, "");
    if (!bucket || !key) {
      return null;
    }
    return { bucket, key };
  }

  const virtualHostMatch = url.host.match(S3_VIRTUAL_HOST_PATTERN);
  if (virtualHostMatch) {
    const key = url.pathname.replace(/^\/+/, "");
    if (!key) {
      return null;
    }
    return {
      bucket: virtualHostMatch[1],
      key,
    };
  }

  if (S3_PATH_STYLE_HOST_PATTERN.test(url.host)) {
    const [bucket, ...keyParts] = url.pathname.replace(/^\/+/, "").split("/");
    const key = keyParts.join("/");
    if (!bucket || !key) {
      return null;
    }
    return { bucket, key };
  }

  return null;
}

function toResponseBody(body: unknown): BodyInit | null {
  if (!body) {
    return null;
  }

  if (typeof (body as { transformToWebStream?: () => ReadableStream<Uint8Array> }).transformToWebStream === "function") {
    return (body as { transformToWebStream: () => ReadableStream<Uint8Array> }).transformToWebStream();
  }

  if (body instanceof Readable) {
    return Readable.toWeb(body) as BodyInit;
  }

  return body as BodyInit;
}

async function fetchSignedS3Object(bucket: string, key: string): Promise<Response> {
  const object = await s3Client.send(
    new GetObjectCommand({
      Bucket: bucket,
      Key: decodeURIComponent(key),
    })
  );

  const headers = normalizeResponseHeaders(new Headers());
  if (object.ContentType) {
    headers.set("content-type", object.ContentType);
  }
  if (object.ContentLength != null) {
    headers.set("content-length", String(object.ContentLength));
  }
  if (object.CacheControl) {
    headers.set("cache-control", object.CacheControl);
  }
  if (object.ETag) {
    headers.set("etag", object.ETag);
  }
  if (object.LastModified) {
    headers.set("last-modified", object.LastModified.toUTCString());
  }

  return new Response(toResponseBody(object.Body), {
    status: 200,
    headers,
  });
}

async function fetchUpstream(request: NextRequest, upstreamUrl: URL): Promise<Response> {
  const upstreamResponse = await fetch(upstreamUrl, {
    headers: {
      Accept: request.headers.get("accept") ?? "*/*",
    },
  });

  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers: normalizeResponseHeaders(new Headers(upstreamResponse.headers)),
  });
}

function normalizeUpstreamUrl(segments: string[]): URL | null {
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
  if (urlString.startsWith("s3:/") && !urlString.startsWith("s3://")) {
    urlString = urlString.replace("s3:/", "s3://");
  }
  urlString = urlString
    .replace(/^https:\/\//, "https://")
    .replace(/^http:\/\//, "http://")
    .replace(/^s3:\/\//, "s3://");

  try {
    const url = new URL(urlString);
    const s3Location = getS3Location(url);
    if (!isAllowedEdgeBundleUrl(url) && (!s3Location || !isAllowedPipelineBucket(s3Location.bucket))) {
      return null;
    }
    return url;
  } catch {
    return null;
  }
}

export async function GET(request: NextRequest, { params }: { params: { resource: string[] } }) {
  const upstreamUrl = normalizeUpstreamUrl(params.resource ?? []);
  if (!upstreamUrl) {
    return new Response("Invalid or disallowed upstream resource", { status: 400 });
  }

  const s3Location = getS3Location(upstreamUrl);
  if (s3Location && isAllowedPipelineBucket(s3Location.bucket)) {
    try {
      return await fetchSignedS3Object(s3Location.bucket, s3Location.key);
    } catch {
      return fetchUpstream(request, upstreamUrl);
    }
  }

  return fetchUpstream(request, upstreamUrl);
}
