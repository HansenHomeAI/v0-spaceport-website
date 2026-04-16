import { GetObjectCommand, HeadObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { Readable } from "node:stream";

type Vec3 = [number, number, number];

type ParsedPoint = {
  x: number;
  y: number;
  z: number;
  r: number;
  g: number;
  b: number;
};

export type SfmPreviewArtifact = {
  title: string;
  jobName: string;
  subsetName: string;
  strategy: string;
  bucket: string;
  prefix: string;
  outputS3Uri: string;
  sourceZipS3Uri: string;
  sourceBucket: string;
  sourceKey: string;
  createdAt: string;
  completedAt: string;
};

export type SfmPreviewLink = {
  label: string;
  key: string;
  s3Uri: string;
  signedUrl: string;
  sizeBytes: number;
  verified: boolean;
};

export type SfmPreviewPageData = {
  artifact: SfmPreviewArtifact;
  exactPointCount: number | null;
  registeredImageCount: number | null;
  chunkCount: number | null;
  planner: string | null;
  linkExpirySeconds: number;
  links: SfmPreviewLink[];
};

export type SfmPreviewSamplePayload = {
  artifact: SfmPreviewArtifact;
  exactPointCount: number | null;
  registeredImageCount: number | null;
  sampledPointCount: number;
  sampledRanges: number;
  sourceSizeBytes: number;
  sampleWindowBytes: number;
  scale: number;
  bounds: {
    min: Vec3;
    max: Vec3;
    center: Vec3;
  };
  positions: number[];
  colors: number[];
};

const REGION = process.env.AWS_REGION || process.env.AWS_DEFAULT_REGION || "us-west-2";
const LINK_EXPIRY_SECONDS = 60 * 60 * 24;
const RANGE_COUNT = 14;
const RANGE_BYTES = 768 * 1024;
const DEFAULT_SAMPLE_POINTS = 18_000;

export const DEFAULT_SFM_PREVIEW_ARTIFACT: SfmPreviewArtifact = {
  title: "2000 Rung Ladder SfM Preview",
  jobName: "md1p24e752k-1776314974",
  subsetName: "ladder_2000",
  strategy: "md1_phase2_candidate_ladder_2000",
  bucket: "spaceport-ml-processing-staging",
  prefix: "manual-validations/md1p24e752k-1776314974/colmap",
  outputS3Uri: "s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap",
  sourceZipS3Uri: "s3://spaceport-uploads/1775750905123-vg76vr-md1-dji-images.zip",
  sourceBucket: "spaceport-uploads",
  sourceKey: "1775750905123-vg76vr-md1-dji-images.zip",
  createdAt: "2026-04-15T22:49:35.212-06:00",
  completedAt: "2026-04-16T08:58:41.108-06:00",
};

const previewCache = new Map<string, Promise<SfmPreviewSamplePayload>>();
let s3Client: S3Client | null = null;

function getS3Client(): S3Client {
  if (!s3Client) {
    s3Client = new S3Client({ region: REGION });
  }
  return s3Client;
}

function artifactKey(artifact: SfmPreviewArtifact, suffix: string): string {
  return `${artifact.prefix}/${suffix}`;
}

function toS3Uri(bucket: string, key: string): string {
  return `s3://${bucket}/${key}`;
}

function parseCount(pattern: RegExp, text: string): number | null {
  const match = text.match(pattern);
  if (!match) {
    return null;
  }

  const parsed = Number.parseInt(match[1].replace(/,/g, ""), 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseChunkCount(text: string): number | null {
  return parseCount(/"chunk_count"\s*:\s*(\d+)/, text);
}

function parsePlanner(text: string): string | null {
  const match = text.match(/"planner"\s*:\s*"([^"]+)"/);
  return match?.[1] ?? null;
}

async function bodyToString(body: unknown): Promise<string> {
  if (!body) {
    return "";
  }

  if (typeof (body as { transformToString?: () => Promise<string> }).transformToString === "function") {
    return (body as { transformToString: () => Promise<string> }).transformToString();
  }

  if (body instanceof Readable) {
    const chunks: Buffer[] = [];
    for await (const chunk of body) {
      chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
    }
    return Buffer.concat(chunks).toString("utf8");
  }

  return await new Response(body as BodyInit).text();
}

async function readRangeText(bucket: string, key: string, start: number, end: number): Promise<string> {
  const response = await getS3Client().send(
    new GetObjectCommand({
      Bucket: bucket,
      Key: key,
      Range: `bytes=${start}-${end}`,
    }),
  );
  return bodyToString(response.Body);
}

function buildRanges(totalBytes: number, count = RANGE_COUNT, chunkBytes = RANGE_BYTES): Array<[number, number]> {
  if (totalBytes <= chunkBytes) {
    return [[0, Math.max(0, totalBytes - 1)]];
  }

  const lastStart = Math.max(0, totalBytes - chunkBytes);
  const starts = new Set<number>();

  for (let index = 0; index < count; index += 1) {
    const ratio = count === 1 ? 0 : index / (count - 1);
    starts.add(Math.min(lastStart, Math.floor(lastStart * ratio)));
  }

  return [...starts]
    .sort((left, right) => left - right)
    .map((start) => [start, Math.min(totalBytes - 1, start + chunkBytes - 1)]);
}

function parsePointLine(line: string): ParsedPoint | null {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#")) {
    return null;
  }

  const parts = trimmed.split(/\s+/, 8);
  if (parts.length < 7) {
    return null;
  }

  const x = Number(parts[1]);
  const y = Number(parts[2]);
  const z = Number(parts[3]);
  const r = Number(parts[4]);
  const g = Number(parts[5]);
  const b = Number(parts[6]);

  if (![x, y, z, r, g, b].every(Number.isFinite)) {
    return null;
  }

  return { x, y, z, r, g, b };
}

function reduceSample<T>(items: T[], maxCount: number): T[] {
  if (items.length <= maxCount) {
    return items;
  }

  const reduced: T[] = [];
  const step = items.length / maxCount;
  for (let index = 0; index < maxCount; index += 1) {
    reduced.push(items[Math.floor(index * step)]);
  }
  return reduced;
}

function normalizePoints(points: ParsedPoint[]) {
  const min: Vec3 = [Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY];
  const max: Vec3 = [Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY];

  for (const point of points) {
    min[0] = Math.min(min[0], point.x);
    min[1] = Math.min(min[1], point.y);
    min[2] = Math.min(min[2], point.z);
    max[0] = Math.max(max[0], point.x);
    max[1] = Math.max(max[1], point.y);
    max[2] = Math.max(max[2], point.z);
  }

  const center: Vec3 = [
    (min[0] + max[0]) / 2,
    (min[1] + max[1]) / 2,
    (min[2] + max[2]) / 2,
  ];
  const span = Math.max(max[0] - min[0], max[1] - min[1], max[2] - min[2], 1);
  const scale = 2.6 / span;
  const positions: number[] = [];
  const colors: number[] = [];

  for (const point of points) {
    positions.push(
      (point.x - center[0]) * scale,
      (point.y - center[1]) * scale,
      (point.z - center[2]) * scale,
    );
    colors.push(point.r / 255, point.g / 255, point.b / 255);
  }

  return {
    bounds: { min, max, center },
    scale,
    positions,
    colors,
  };
}

async function headSize(bucket: string, key: string): Promise<number> {
  const response = await getS3Client().send(
    new HeadObjectCommand({
      Bucket: bucket,
      Key: key,
    }),
  );
  return response.ContentLength ?? 0;
}

export async function getSfmPreviewPageData(
  artifact: SfmPreviewArtifact = DEFAULT_SFM_PREVIEW_ARTIFACT,
): Promise<SfmPreviewPageData> {
  const pointsKey = artifactKey(artifact, "sparse/0/points3D.txt");
  const imagesKey = artifactKey(artifact, "sparse/0/images.txt");
  const manifestKey = artifactKey(artifact, "chunk_planner_manifest.json");
  const camerasKey = artifactKey(artifact, "sparse/0/cameras.txt");
  const framesKey = artifactKey(artifact, "sparse/0/frames.txt");

  const [pointsHeader, imagesHeader, manifestHeader] = await Promise.all([
    readRangeText(artifact.bucket, pointsKey, 0, 4095),
    readRangeText(artifact.bucket, imagesKey, 0, 4095),
    readRangeText(artifact.bucket, manifestKey, 0, 4095),
  ]);

  const linkDefinitions = [
    { label: "Sparse points", bucket: artifact.bucket, key: pointsKey },
    { label: "Chunk planner manifest", bucket: artifact.bucket, key: manifestKey },
    { label: "Frames", bucket: artifact.bucket, key: framesKey },
    { label: "Cameras", bucket: artifact.bucket, key: camerasKey },
    { label: "Source ZIP", bucket: artifact.sourceBucket, key: artifact.sourceKey },
  ];

  const links = await Promise.all(
    linkDefinitions.map(async ({ label, bucket, key }) => {
      const [sizeBytes, signedUrl] = await Promise.all([
        headSize(bucket, key),
        getSignedUrl(
          getS3Client(),
          new GetObjectCommand({
            Bucket: bucket,
            Key: key,
          }),
          { expiresIn: LINK_EXPIRY_SECONDS },
        ),
      ]);

      return {
        label,
        key,
        s3Uri: toS3Uri(bucket, key),
        signedUrl,
        sizeBytes,
        verified: true,
      };
    }),
  );

  return {
    artifact,
    exactPointCount: parseCount(/Number of points:\s*([\d,]+)/, pointsHeader),
    registeredImageCount: parseCount(/Number of images:\s*([\d,]+)/, imagesHeader),
    chunkCount: parseChunkCount(manifestHeader),
    planner: parsePlanner(manifestHeader),
    linkExpirySeconds: LINK_EXPIRY_SECONDS,
    links,
  };
}

async function buildSfmPreviewSample(
  artifact: SfmPreviewArtifact,
  maxPoints = DEFAULT_SAMPLE_POINTS,
): Promise<SfmPreviewSamplePayload> {
  const pointsKey = artifactKey(artifact, "sparse/0/points3D.txt");
  const imagesKey = artifactKey(artifact, "sparse/0/images.txt");
  const sourceSizeBytes = await headSize(artifact.bucket, pointsKey);
  const ranges = buildRanges(sourceSizeBytes);
  const perRangeTarget = Math.max(250, Math.ceil(maxPoints / ranges.length));
  const sampledPoints: ParsedPoint[] = [];
  const [pointsHeader, imagesHeader] = await Promise.all([
    readRangeText(artifact.bucket, pointsKey, 0, 4095),
    readRangeText(artifact.bucket, imagesKey, 0, 4095),
  ]);

  for (const [start, end] of ranges) {
    const chunk = await readRangeText(artifact.bucket, pointsKey, start, end);
    const lines = chunk.split(/\r?\n/);

    if (start > 0 && lines.length > 0) {
      lines.shift();
    }
    if (end < sourceSizeBytes - 1 && lines.length > 0) {
      lines.pop();
    }

    const parsed = lines
      .map(parsePointLine)
      .filter((point): point is ParsedPoint => point !== null);
    const reduced = reduceSample(parsed, perRangeTarget);
    sampledPoints.push(...reduced);
  }

  const finalPoints = reduceSample(sampledPoints, maxPoints);
  const normalized = normalizePoints(finalPoints);

  return {
    artifact,
    exactPointCount: parseCount(/Number of points:\s*([\d,]+)/, pointsHeader),
    registeredImageCount: parseCount(/Number of images:\s*([\d,]+)/, imagesHeader),
    sampledPointCount: finalPoints.length,
    sampledRanges: ranges.length,
    sourceSizeBytes,
    sampleWindowBytes: RANGE_BYTES,
    scale: normalized.scale,
    bounds: normalized.bounds,
    positions: normalized.positions,
    colors: normalized.colors,
  };
}

export async function getSfmPreviewSample(
  artifact: SfmPreviewArtifact = DEFAULT_SFM_PREVIEW_ARTIFACT,
  maxPoints = DEFAULT_SAMPLE_POINTS,
): Promise<SfmPreviewSamplePayload> {
  const cacheKey = `${artifact.bucket}/${artifact.prefix}:${maxPoints}`;
  let pending = previewCache.get(cacheKey);
  if (!pending) {
    pending = buildSfmPreviewSample(artifact, maxPoints);
    previewCache.set(cacheKey, pending);
  }
  return pending;
}
