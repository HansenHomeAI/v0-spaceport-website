import { GetObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { once } from "node:events";
import { createReadStream, createWriteStream, existsSync } from "node:fs";
import { mkdir, rename, unlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, extname, join } from "node:path";
import { Readable } from "node:stream";
import { pipeline as streamPipeline } from "node:stream/promises";
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
const TAR_EXTRACTION_CACHE_DIR = join(tmpdir(), "pipeline-viewer-tar-cache");
const DEFAULT_GAUSSIAN_TAR_MEMBER = "merged/merged_splat.ply";

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

function toNodeReadable(body: unknown): Readable | null {
  if (!body) {
    return null;
  }

  if (body instanceof Readable) {
    return body;
  }

  if (typeof (body as { transformToWebStream?: () => ReadableStream<Uint8Array> }).transformToWebStream === "function") {
    return Readable.fromWeb(
      (body as { transformToWebStream: () => ReadableStream<Uint8Array> }).transformToWebStream()
    );
  }

  return null;
}

function hashForCache(value: string): string {
  return createHash("sha256").update(value).digest("hex");
}

function parseSingleRange(rangeHeader: string | null, size: number): { start: number; end: number } | null {
  if (!rangeHeader) {
    return null;
  }

  const match = rangeHeader.match(/^bytes=(\d*)-(\d*)$/i);
  if (!match) {
    return null;
  }

  const [, rawStart, rawEnd] = match;
  if (!rawStart && !rawEnd) {
    return null;
  }

  let start = rawStart ? Number(rawStart) : Math.max(size - Number(rawEnd), 0);
  let end = rawEnd ? Number(rawEnd) : size - 1;

  if (!Number.isFinite(start) || !Number.isFinite(end)) {
    return null;
  }

  start = Math.max(0, start);
  end = Math.min(size - 1, end);
  if (start > end || start >= size) {
    return null;
  }

  return { start, end };
}

async function downloadS3ObjectToFile(bucket: string, key: string, filePath: string): Promise<void> {
  const object = await s3Client.send(
    new GetObjectCommand({
      Bucket: bucket,
      Key: decodeURIComponent(key),
    })
  );

  const body = toNodeReadable(object.Body);
  if (!body) {
    throw new Error("S3 object body was not readable");
  }

  await mkdir(dirname(filePath), { recursive: true });
  const tempPath = `${filePath}.part`;
  await streamPipeline(body, createWriteStream(tempPath));
  await rename(tempPath, filePath);
}

async function extractTarMemberToFile(tarPath: string, memberName: string, outputPath: string): Promise<void> {
  await mkdir(dirname(outputPath), { recursive: true });
  const tempPath = `${outputPath}.part`;
  const tarProcess = spawn("tar", ["-xOf", tarPath, memberName], {
    stdio: ["ignore", "pipe", "pipe"],
  });
  const stderrChunks: Buffer[] = [];
  tarProcess.stderr.on("data", (chunk) => stderrChunks.push(Buffer.from(chunk)));

  try {
    await streamPipeline(tarProcess.stdout, createWriteStream(tempPath));
    const [exitCode] = (await once(tarProcess, "close")) as [number | null];
    if (exitCode !== 0) {
      throw new Error(Buffer.concat(stderrChunks).toString("utf8").trim() || `tar exited with code ${exitCode}`);
    }
    await rename(tempPath, outputPath);
  } catch (error) {
    tarProcess.kill("SIGKILL");
    await unlink(tempPath).catch(() => undefined);
    throw error;
  }
}

async function ensureTarMemberCached(bucket: string, key: string, memberName: string): Promise<string> {
  const sourceHash = hashForCache(`${bucket}/${key}`);
  const memberHash = hashForCache(memberName);
  const memberExtension = extname(memberName) || ".bin";
  const tarPath = join(TAR_EXTRACTION_CACHE_DIR, `${sourceHash}.tar.gz`);
  const memberPath = join(TAR_EXTRACTION_CACHE_DIR, `${sourceHash}-${memberHash}${memberExtension}`);

  if (!existsSync(tarPath)) {
    await downloadS3ObjectToFile(bucket, key, tarPath);
  }

  if (!existsSync(memberPath)) {
    await extractTarMemberToFile(tarPath, memberName, memberPath);
  }

  return memberPath;
}

async function serveCachedFile(filePath: string, request: NextRequest, contentType: string): Promise<Response> {
  const { size } = await import("node:fs/promises").then((fs) => fs.stat(filePath));
  const range = parseSingleRange(request.headers.get("range"), size);
  const headers = normalizeResponseHeaders(new Headers());
  headers.set("content-type", contentType);
  headers.set("accept-ranges", "bytes");
  headers.set("cache-control", "public, max-age=3600");

  if (range) {
    headers.set("content-range", `bytes ${range.start}-${range.end}/${size}`);
    headers.set("content-length", String(range.end - range.start + 1));
    return new Response(Readable.toWeb(createReadStream(filePath, range)) as BodyInit, {
      status: 206,
      headers,
    });
  }

  headers.set("content-length", String(size));
  return new Response(Readable.toWeb(createReadStream(filePath)) as BodyInit, {
    status: 200,
    headers,
  });
}

async function fetchSignedS3Object(bucket: string, key: string, rangeHeader?: string | null): Promise<Response> {
  const object = await s3Client.send(
    new GetObjectCommand({
      Bucket: bucket,
      Key: decodeURIComponent(key),
      Range: rangeHeader ?? undefined,
    })
  );

  const headers = normalizeResponseHeaders(new Headers());
  if (object.ContentType) {
    headers.set("content-type", object.ContentType);
  }
  if (object.ContentLength != null) {
    headers.set("content-length", String(object.ContentLength));
  }
  if (object.AcceptRanges) {
    headers.set("accept-ranges", object.AcceptRanges);
  }
  if (object.CacheControl) {
    headers.set("cache-control", object.CacheControl);
  }
  if (object.ContentRange) {
    headers.set("content-range", object.ContentRange);
  }
  if (object.ETag) {
    headers.set("etag", object.ETag);
  }
  if (object.LastModified) {
    headers.set("last-modified", object.LastModified.toUTCString());
  }

  return new Response(toResponseBody(object.Body), {
    status: object.ContentRange ? 206 : 200,
    headers,
  });
}

async function fetchUpstream(request: NextRequest, upstreamUrl: URL): Promise<Response> {
  const rangeHeader = request.headers.get("range");
  const upstreamResponse = await fetch(upstreamUrl, {
    headers: {
      Accept: request.headers.get("accept") ?? "*/*",
      ...(rangeHeader ? { Range: rangeHeader } : {}),
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
      if (request.nextUrl.searchParams.get("pipeline-viewer-source") === "model-tar-gz") {
        const tarMember = request.nextUrl.searchParams.get("tar-member") ?? DEFAULT_GAUSSIAN_TAR_MEMBER;
        const cachedMemberPath = await ensureTarMemberCached(s3Location.bucket, s3Location.key, tarMember);
        return serveCachedFile(cachedMemberPath, request, "application/octet-stream");
      }
      return await fetchSignedS3Object(s3Location.bucket, s3Location.key, request.headers.get("range"));
    } catch {
      return fetchUpstream(request, upstreamUrl);
    }
  }

  return fetchUpstream(request, upstreamUrl);
}
