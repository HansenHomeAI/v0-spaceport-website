import { Gunzip } from "fflate";
import { AwsClient } from "aws4fetch";
import { NextRequest } from "next/server";

export const runtime = "edge";

const ALLOWED_HOSTS = new Set([
  "spaceport-ml-processing.s3.amazonaws.com",
  "spaceport-ml-processing.s3.us-west-2.amazonaws.com",
]);

const ALLOWED_BUCKETS = new Set([
  "spaceport-ml-processing",
  "spaceport-ml-pipeline",
  "spaceport-sagemaker-us-west-2",
]);

type Mode = "raw" | "3dgs-ply" | "colmap-ply";

type S3Reference = {
  bucket: string;
  key: string;
};

let awsClient: AwsClient | null = null;

function getAwsClient(): AwsClient {
  if (!awsClient) {
    const accessKeyId = process.env.AWS_ACCESS_KEY_ID;
    const secretAccessKey = process.env.AWS_SECRET_ACCESS_KEY;
    const sessionToken = process.env.AWS_SESSION_TOKEN;

    if (!accessKeyId || !secretAccessKey) {
      throw new Error("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set for private pipeline artifacts");
    }

    awsClient = new AwsClient({
      accessKeyId,
      secretAccessKey,
      sessionToken,
      service: "s3",
      region: process.env.AWS_REGION ?? process.env.AWS_DEFAULT_REGION ?? "us-west-2",
    });
  }

  return awsClient;
}

function decodeSegments(segments: string[]): string[] {
  return segments.map((segment) => decodeURIComponent(segment));
}

function toResponseHeaders(contentType?: string | null): Headers {
  const headers = new Headers();
  headers.set("Access-Control-Allow-Origin", "*");
  headers.set("Cache-Control", "public, max-age=300");
  if (contentType) {
    headers.set("Content-Type", contentType);
  }
  return headers;
}

function isAllZeroBlock(block: Uint8Array): boolean {
  for (let i = 0; i < block.length; i += 1) {
    if (block[i] !== 0) {
      return false;
    }
  }
  return true;
}

function parseTarString(bytes: Uint8Array): string {
  let end = bytes.length;
  while (end > 0 && (bytes[end - 1] === 0 || bytes[end - 1] === 32)) {
    end -= 1;
  }
  return new TextDecoder().decode(bytes.subarray(0, end));
}

function parseTarSize(bytes: Uint8Array): number {
  const raw = parseTarString(bytes).trim();
  return raw ? Number.parseInt(raw, 8) : 0;
}

function tarEntryBasename(filename: string): string {
  const parts = filename.split("/").filter(Boolean);
  return parts[parts.length - 1] ?? "";
}

class BufferedReader {
  private buffer = new Uint8Array(0);
  private done = false;

  constructor(private readonly reader: ReadableStreamDefaultReader<Uint8Array>) {}

  private append(chunk: Uint8Array) {
    if (!chunk.length) return;
    const next = new Uint8Array(this.buffer.length + chunk.length);
    next.set(this.buffer, 0);
    next.set(chunk, this.buffer.length);
    this.buffer = next;
  }

  private async fill(minBytes: number) {
    while (!this.done && this.buffer.length < minBytes) {
      const { value, done } = await this.reader.read();
      if (done) {
        this.done = true;
        break;
      }
      this.append(value);
    }
  }

  async readExact(size: number): Promise<Uint8Array | null> {
    await this.fill(size);
    if (this.buffer.length < size) {
      return null;
    }
    const out = this.buffer.slice(0, size);
    this.buffer = this.buffer.slice(size);
    return out;
  }

  async readAtMost(size: number): Promise<Uint8Array | null> {
    if (!this.buffer.length) {
      await this.fill(1);
    }
    if (!this.buffer.length) {
      return null;
    }
    const take = Math.min(size, this.buffer.length);
    const out = this.buffer.slice(0, take);
    this.buffer = this.buffer.slice(take);
    return out;
  }

  async skip(size: number): Promise<boolean> {
    let remaining = size;
    while (remaining > 0) {
      const chunk = await this.readAtMost(remaining);
      if (!chunk) {
        return false;
      }
      remaining -= chunk.length;
    }
    return true;
  }

  async cancel(reason?: unknown) {
    await this.reader.cancel(reason);
  }
}

function gunzipStream(source: ReadableStream<Uint8Array>): ReadableStream<Uint8Array> {
  const reader = source.getReader();

  return new ReadableStream<Uint8Array>({
    start(controller) {
      const gunzip = new Gunzip((chunk, final) => {
        if (chunk.length) {
          controller.enqueue(chunk);
        }
        if (final) {
          controller.close();
        }
      });

      const pump = async () => {
        try {
          while (true) {
            const { value, done } = await reader.read();
            if (done) {
              gunzip.push(new Uint8Array(0), true);
              break;
            }
            gunzip.push(value, false);
          }
        } catch (error) {
          controller.error(error);
        }
      };

      void pump();
    },
    cancel: async () => {
      await reader.cancel();
    },
  });
}

function normalizeLegacyUpstreamUrl(segments: string[]): URL | null {
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
    if (!ALLOWED_HOSTS.has(url.host)) {
      return null;
    }
    return url;
  } catch {
    return null;
  }
}

function parseStageReference(rawSegments: string[]): { mode: Mode; ref: S3Reference } | null {
  const [mode, ...rest] = decodeSegments(rawSegments);
  if (!mode || !["raw", "3dgs-ply", "colmap-ply"].includes(mode)) {
    return null;
  }

  const withoutSynthetic = mode === "raw" ? rest : rest.slice(0, -1);
  const [scheme, bucket, ...keySegments] = withoutSynthetic;
  if (scheme !== "s3" || !bucket || !ALLOWED_BUCKETS.has(bucket) || !keySegments.length) {
    return null;
  }

  return {
    mode,
    ref: {
      bucket,
      key: keySegments.join("/"),
    },
  };
}

function buildSignedS3Url(ref: S3Reference): string {
  const encodedKey = ref.key
    .split("/")
    .filter(Boolean)
    .map((segment) => encodeURIComponent(segment))
    .join("/");
  return `https://${ref.bucket}.s3.us-west-2.amazonaws.com/${encodedKey}`;
}

async function signedS3Fetch(ref: S3Reference): Promise<Response> {
  return getAwsClient().fetch(buildSignedS3Url(ref), {
    method: "GET",
    cache: "no-store",
    headers: {
      Accept: "*/*",
    },
    aws: {
      service: "s3",
      region: process.env.AWS_REGION ?? process.env.AWS_DEFAULT_REGION ?? "us-west-2",
    },
  });
}

async function proxyLegacyHttp(url: URL, request: NextRequest): Promise<Response> {
  const upstreamResponse = await fetch(url, {
    cache: "no-store",
    headers: {
      Accept: request.headers.get("accept") ?? "*/*",
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

function signedError(message: string, error: unknown): Response {
  const details = error instanceof Error ? error.message : "unknown error";
  return new Response(`${message}: ${details}`, { status: 502 });
}

async function proxyRawAsset(ref: S3Reference, request: NextRequest): Promise<Response> {
  try {
    const upstreamResponse = await signedS3Fetch(ref);
    if (!upstreamResponse.ok) {
      return new Response(`Unable to fetch source asset from S3 (${upstreamResponse.status})`, {
        status: upstreamResponse.status,
      });
    }
    return new Response(upstreamResponse.body, {
      status: 200,
      headers: toResponseHeaders(upstreamResponse.headers.get("content-type") ?? request.headers.get("accept")),
    });
  } catch (error) {
    return signedError("Unable to fetch source asset from S3", error);
  }
}

async function streamPlyFromTar(ref: S3Reference): Promise<Response> {
  try {
    const upstreamResponse = await signedS3Fetch(ref);
    if (!upstreamResponse.ok || !upstreamResponse.body) {
      return new Response(`Unable to fetch 3DGS artifact from S3 (${upstreamResponse.status})`, {
        status: upstreamResponse.status || 502,
      });
    }

    const decompressed = gunzipStream(upstreamResponse.body);
    const buffered = new BufferedReader(decompressed.getReader());

    while (true) {
      const header = await buffered.readExact(512);
      if (!header) {
        return new Response("3DGS tarball ended before splat.ply was found", { status: 502 });
      }
      if (isAllZeroBlock(header)) {
        return new Response("3DGS tarball does not contain splat.ply", { status: 404 });
      }

      const name = parseTarString(header.subarray(0, 100));
      const prefix = parseTarString(header.subarray(345, 500));
      const filename = prefix ? `${prefix}/${name}` : name;
      const size = parseTarSize(header.subarray(124, 136));
      const typeflag = String.fromCharCode(header[156] || 48);
      const padding = (512 - (size % 512)) % 512;

      if (typeflag === "0" && tarEntryBasename(filename) === "splat.ply") {
        let remaining = size;
        const stream = new ReadableStream<Uint8Array>({
          pull: async (controller) => {
            if (remaining <= 0) {
              if (padding > 0) {
                await buffered.skip(padding);
              }
              await buffered.cancel();
              controller.close();
              return;
            }

            const chunk = await buffered.readAtMost(Math.min(remaining, 64 * 1024));
            if (!chunk) {
              controller.error(new Error("3DGS tarball ended while streaming splat.ply"));
              return;
            }
            remaining -= chunk.length;
            controller.enqueue(chunk);
          },
          cancel: async () => {
            await buffered.cancel();
          },
        });

        return new Response(stream, {
          status: 200,
          headers: toResponseHeaders("application/octet-stream"),
        });
      }

      if (!(await buffered.skip(size + padding))) {
        return new Response("3DGS tarball ended before file contents finished", { status: 502 });
      }
    }
  } catch (error) {
    return signedError("Unable to extract splat.ply from 3DGS artifact", error);
  }
}

function clampColor(value: number): number {
  return Math.max(0, Math.min(255, Math.round(value)));
}

async function convertColmapToPly(ref: S3Reference): Promise<Response> {
  if (!ref.key.endsWith("points3D.txt")) {
    return new Response("COLMAP stage currently supports points3D.txt inputs only", { status: 400 });
  }

  try {
    const upstreamResponse = await signedS3Fetch(ref);
    if (!upstreamResponse.ok) {
      return new Response(`Unable to fetch COLMAP point cloud from S3 (${upstreamResponse.status})`, {
        status: upstreamResponse.status || 502,
      });
    }

    const text = await upstreamResponse.text();
    const points: Array<[number, number, number, number, number, number]> = [];
    let minX = Number.POSITIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;
    let minZ = Number.POSITIVE_INFINITY;
    let maxX = Number.NEGATIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;
    let maxZ = Number.NEGATIVE_INFINITY;

    for (const line of text.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) {
        continue;
      }

      const parts = trimmed.split(/\s+/);
      if (parts.length < 7) {
        continue;
      }

      const x = Number(parts[1]);
      const y = Number(parts[2]);
      const z = Number(parts[3]);
      const r = Number(parts[4]);
      const g = Number(parts[5]);
      const b = Number(parts[6]);

      if (![x, y, z, r, g, b].every(Number.isFinite)) {
        continue;
      }

      points.push([x, y, z, clampColor(r), clampColor(g), clampColor(b)]);
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      minZ = Math.min(minZ, z);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);
      maxZ = Math.max(maxZ, z);
    }

    const maxExtent = Math.max(maxX - minX, maxY - minY, maxZ - minZ, 1);
    const defaultScale = Math.log(Math.max(maxExtent * 0.0025, 0.01));
    const defaultOpacity = 8;
    const shC0 = 0.28209479177387814;

    const header = [
      "ply",
      "format binary_little_endian 1.0",
      `element vertex ${points.length}`,
      "property float x",
      "property float y",
      "property float z",
      "property float scale_0",
      "property float scale_1",
      "property float scale_2",
      "property float rot_0",
      "property float rot_1",
      "property float rot_2",
      "property float rot_3",
      "property float f_dc_0",
      "property float f_dc_1",
      "property float f_dc_2",
      "property float opacity",
      "end_header",
    ].join("\n");

    const headerBytes = new TextEncoder().encode(`${header}\n`);
    const vertexStride = 56;
    const body = new Uint8Array(headerBytes.length + points.length * vertexStride);
    body.set(headerBytes, 0);

    const view = new DataView(body.buffer);
    let offset = headerBytes.length;
    for (const [x, y, z, r, g, b] of points) {
      view.setFloat32(offset, x, true);
      offset += 4;
      view.setFloat32(offset, y, true);
      offset += 4;
      view.setFloat32(offset, z, true);
      offset += 4;
      view.setFloat32(offset, defaultScale, true);
      offset += 4;
      view.setFloat32(offset, defaultScale, true);
      offset += 4;
      view.setFloat32(offset, defaultScale, true);
      offset += 4;
      view.setFloat32(offset, 1, true);
      offset += 4;
      view.setFloat32(offset, 0, true);
      offset += 4;
      view.setFloat32(offset, 0, true);
      offset += 4;
      view.setFloat32(offset, 0, true);
      offset += 4;
      view.setFloat32(offset, r / 255 / shC0 - 0.5 / shC0, true);
      offset += 4;
      view.setFloat32(offset, g / 255 / shC0 - 0.5 / shC0, true);
      offset += 4;
      view.setFloat32(offset, b / 255 / shC0 - 0.5 / shC0, true);
      offset += 4;
      view.setFloat32(offset, defaultOpacity, true);
      offset += 4;
    }

    return new Response(body, {
      status: 200,
      headers: toResponseHeaders("application/octet-stream"),
    });
  } catch (error) {
    return signedError("Unable to fetch COLMAP point cloud from S3", error);
  }
}

export async function GET(request: NextRequest, { params }: { params: { resource: string[] } }) {
  const segments = params.resource ?? [];
  const stageRef = parseStageReference(segments);
  if (stageRef) {
    if (stageRef.mode === "raw") {
      return proxyRawAsset(stageRef.ref, request);
    }
    if (stageRef.mode === "3dgs-ply") {
      return streamPlyFromTar(stageRef.ref);
    }
    return convertColmapToPly(stageRef.ref);
  }

  const legacyUrl = normalizeLegacyUpstreamUrl(segments);
  if (!legacyUrl) {
    return new Response("Invalid or disallowed upstream resource", { status: 400 });
  }

  return proxyLegacyHttp(legacyUrl, request);
}
