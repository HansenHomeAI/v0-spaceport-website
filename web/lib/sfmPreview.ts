import { AwsClient } from "aws4fetch";

type Vec3 = [number, number, number];
type Quaternion = [number, number, number, number];
type Matrix3 = [Vec3, Vec3, Vec3];

type ParsedPoint = {
  x: number;
  y: number;
  z: number;
  r: number;
  g: number;
  b: number;
  chunkIndex: number;
};

type RawCamera = {
  imageId: number;
  name: string;
  position: Vec3;
  chunkIndexes: number[];
  primaryChunkIndex: number | null;
};

type RawChunk = {
  index: number;
  coreNames: string[];
  overlapNames: string[];
  imageNames: string[];
};

export type SfmPreviewArtifact = {
  bucket: string;
  prefix: string;
  outputS3Uri: string;
  jobName: string;
};

export type SfmPreviewPayload = {
  artifact: SfmPreviewArtifact;
  exactPointCount: number | null;
  registeredImageCount: number | null;
  sampledPointCount: number;
  sourceSizeBytes: number;
  sampledRanges: number;
  chunkCount: number;
  bounds: {
    min: Vec3;
    max: Vec3;
    center: Vec3;
  };
  positions: number[];
  colors: number[];
  chunkColors: number[];
  pointChunkIndexes: number[];
  cameras: Array<{
    imageId: number;
    name: string;
    position: Vec3;
    chunkIndexes: number[];
    primaryChunkIndex: number | null;
  }>;
};

const REGION = process.env.AWS_REGION || process.env.AWS_DEFAULT_REGION || "us-west-2";
const RANGE_COUNT = 14;
const RANGE_BYTES = 768 * 1024;
const DEFAULT_SAMPLE_POINTS = 18_000;
const MAX_SAMPLE_POINTS = 45_000;
const DEFAULT_OUTPUT_S3_URI =
  "s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap";
const CHUNK_PALETTE: Vec3[] = [
  [0.98, 0.45, 0.12],
  [0.20, 0.72, 0.36],
  [0.22, 0.68, 0.92],
  [0.95, 0.74, 0.18],
  [0.92, 0.36, 0.54],
  [0.62, 0.48, 0.92],
  [0.18, 0.78, 0.70],
  [0.96, 0.56, 0.15],
];

let awsClient: AwsClient | null = null;

function getAwsClient() {
  if (!awsClient) {
    const accessKeyId = process.env.AWS_ACCESS_KEY_ID;
    const secretAccessKey = process.env.AWS_SECRET_ACCESS_KEY;
    const sessionToken = process.env.AWS_SESSION_TOKEN;

    if (!accessKeyId || !secretAccessKey) {
      throw new Error("Missing AWS credentials for SfM preview S3 access.");
    }

    awsClient = new AwsClient({
      accessKeyId,
      secretAccessKey,
      sessionToken,
      region: REGION,
      service: "s3",
    });
  }
  return awsClient;
}

function normalizePrefix(prefix: string) {
  return prefix.replace(/^\/+/, "").replace(/\/+$/, "");
}

export function parseSfmArtifact(rawUrl?: string | null): SfmPreviewArtifact {
  const value = (rawUrl || DEFAULT_OUTPUT_S3_URI).trim();
  if (value.startsWith("s3://")) {
    const withoutScheme = value.slice("s3://".length);
    const slashIndex = withoutScheme.indexOf("/");
    if (slashIndex <= 0) {
      throw new Error("SfM preview URL must include an S3 bucket and prefix.");
    }
    const bucket = withoutScheme.slice(0, slashIndex);
    const prefix = normalizePrefix(withoutScheme.slice(slashIndex + 1));
    return {
      bucket,
      prefix,
      outputS3Uri: `s3://${bucket}/${prefix}`,
      jobName: prefix.split("/").at(-2) || prefix.split("/").at(-1) || "sfm-output",
    };
  }

  const url = new URL(value);
  const hostParts = url.hostname.split(".");
  if (hostParts[1] === "s3") {
    const bucket = hostParts[0];
    const prefix = normalizePrefix(decodeURIComponent(url.pathname));
    return {
      bucket,
      prefix,
      outputS3Uri: `s3://${bucket}/${prefix}`,
      jobName: prefix.split("/").at(-2) || prefix.split("/").at(-1) || "sfm-output",
    };
  }

  if (hostParts[0] === "s3" && url.pathname.length > 1) {
    const [bucket, ...keyParts] = normalizePrefix(decodeURIComponent(url.pathname)).split("/");
    const prefix = normalizePrefix(keyParts.join("/"));
    return {
      bucket,
      prefix,
      outputS3Uri: `s3://${bucket}/${prefix}`,
      jobName: prefix.split("/").at(-2) || prefix.split("/").at(-1) || "sfm-output",
    };
  }

  throw new Error("SfM preview supports s3:// URLs or standard S3 HTTPS object prefixes.");
}

function artifactKey(artifact: SfmPreviewArtifact, suffix: string) {
  return `${artifact.prefix}/${suffix}`;
}

function encodeKey(key: string) {
  return key
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/");
}

function buildS3Url(bucket: string, key: string) {
  return `https://${bucket}.s3.${REGION}.amazonaws.com/${encodeKey(key)}`;
}

function buildS3ListUrl(bucket: string, prefix: string, continuationToken?: string) {
  const url = new URL(`https://${bucket}.s3.${REGION}.amazonaws.com/`);
  url.searchParams.set("list-type", "2");
  url.searchParams.set("prefix", prefix);
  url.searchParams.set("max-keys", "1000");
  if (continuationToken) {
    url.searchParams.set("continuation-token", continuationToken);
  }
  return url.toString();
}

async function fetchSignedUrl(url: string, init: RequestInit = {}) {
  const signedRequest = await getAwsClient().sign(new Request(url, init));
  const response = await fetch(signedRequest, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`S3 request failed (${response.status}) for ${url}`);
  }
  return response;
}

async function fetchSignedS3(bucket: string, key: string, init: RequestInit = {}) {
  return fetchSignedUrl(buildS3Url(bucket, key), init);
}

async function readObjectText(bucket: string, key: string) {
  const response = await fetchSignedS3(bucket, key);
  return response.text();
}

async function readRangeText(bucket: string, key: string, start: number, end: number) {
  const response = await fetchSignedS3(bucket, key, {
    headers: {
      Range: `bytes=${start}-${end}`,
    },
  });
  return response.text();
}

async function headSize(bucket: string, key: string) {
  const response = await fetchSignedS3(bucket, key, { method: "HEAD" });
  return Number(response.headers.get("content-length") || 0);
}

async function listS3Keys(bucket: string, prefix: string) {
  const keys: string[] = [];
  let continuationToken: string | undefined;
  do {
    const response = await fetchSignedUrl(buildS3ListUrl(bucket, prefix, continuationToken));
    const xml = await response.text();
    keys.push(...[...xml.matchAll(/<Key>([^<]+)<\/Key>/g)].map((match) => match[1]).filter(Boolean));
    continuationToken = /<IsTruncated>true<\/IsTruncated>/.test(xml)
      ? xml.match(/<NextContinuationToken>([^<]+)<\/NextContinuationToken>/)?.[1]
      : undefined;
  } while (continuationToken);
  return keys;
}

function parseCount(pattern: RegExp, text: string) {
  const match = text.match(pattern);
  if (!match) {
    return null;
  }
  const parsed = Number.parseInt(match[1].replace(/,/g, ""), 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function buildRanges(totalBytes: number) {
  if (totalBytes <= RANGE_BYTES) {
    return [[0, Math.max(0, totalBytes - 1)] as [number, number]];
  }
  const rangeCount: number = RANGE_COUNT;
  const lastStart = Math.max(0, totalBytes - RANGE_BYTES);
  const starts = new Set<number>();
  for (let index = 0; index < rangeCount; index += 1) {
    const ratio = rangeCount === 1 ? 0 : index / (rangeCount - 1);
    starts.add(Math.min(lastStart, Math.floor(lastStart * ratio)));
  }
  return [...starts]
    .sort((left, right) => left - right)
    .map((start) => [start, Math.min(totalBytes - 1, start + RANGE_BYTES - 1)] as [number, number]);
}

function reduceSample<T>(items: T[], maxCount: number) {
  if (items.length <= maxCount) {
    return items;
  }
  const output: T[] = [];
  const step = items.length / maxCount;
  for (let index = 0; index < maxCount; index += 1) {
    output.push(items[Math.floor(index * step)]);
  }
  return output;
}

function quatToMatrix([qw, qx, qy, qz]: Quaternion): Matrix3 {
  const xx = qx * qx;
  const yy = qy * qy;
  const zz = qz * qz;
  const xy = qx * qy;
  const xz = qx * qz;
  const yz = qy * qz;
  const wx = qw * qx;
  const wy = qw * qy;
  const wz = qw * qz;
  return [
    [1 - 2 * (yy + zz), 2 * (xy - wz), 2 * (xz + wy)],
    [2 * (xy + wz), 1 - 2 * (xx + zz), 2 * (yz - wx)],
    [2 * (xz - wy), 2 * (yz + wx), 1 - 2 * (xx + yy)],
  ];
}

function vecTransformTranspose(matrix: Matrix3, vec: Vec3): Vec3 {
  return [
    matrix[0][0] * vec[0] + matrix[1][0] * vec[1] + matrix[2][0] * vec[2],
    matrix[0][1] * vec[0] + matrix[1][1] * vec[1] + matrix[2][1] * vec[2],
    matrix[0][2] * vec[0] + matrix[1][2] * vec[1] + matrix[2][2] * vec[2],
  ];
}

function parseChunkRecords(text: string): RawChunk[] {
  const parsed = JSON.parse(text) as {
    chunks?: Array<{
      index?: number;
      core_names?: string[];
      overlap_names?: string[];
      image_names?: string[];
    }>;
    chunk_plans?: Array<{
      index?: number;
      core_names?: string[];
      overlap_names?: string[];
      image_names?: string[];
    }>;
  };
  return (parsed.chunks || parsed.chunk_plans || []).map((chunk, index) => ({
    index: Number.isFinite(chunk.index) ? Number(chunk.index) : index,
    coreNames: chunk.core_names || [],
    overlapNames: chunk.overlap_names || [],
    imageNames: chunk.image_names || chunk.core_names || [],
  }));
}

function buildImageMembership(chunkRecords: RawChunk[], imageNames: string[]) {
  const nameToId = new Map<string, number>();
  imageNames.forEach((name, index) => nameToId.set(name, index + 1));
  const membership = new Map<number, Set<number>>();

  for (const chunk of chunkRecords) {
    for (const name of [...chunk.coreNames, ...chunk.overlapNames, ...chunk.imageNames]) {
      const imageId = nameToId.get(name);
      if (!imageId) {
        continue;
      }
      const chunks = membership.get(imageId) || new Set<number>();
      chunks.add(chunk.index);
      membership.set(imageId, chunks);
    }
  }

  return membership;
}

function parseFrameCameras(framesText: string, imageNames: string[], membership: Map<number, Set<number>>) {
  const cameras: RawCamera[] = [];
  for (const line of framesText.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }
    const parts = trimmed.split(/\s+/);
    if (parts.length < 13) {
      continue;
    }
    const imageId = Number(parts[parts.length - 1]);
    const quaternion: Quaternion = [Number(parts[2]), Number(parts[3]), Number(parts[4]), Number(parts[5])];
    const translation: Vec3 = [Number(parts[6]), Number(parts[7]), Number(parts[8])];
    if (![imageId, ...quaternion, ...translation].every(Number.isFinite)) {
      continue;
    }
    const rotation = quatToMatrix(quaternion);
    const position = vecTransformTranspose(rotation, translation).map((value) => -value) as Vec3;
    const chunkIndexes = [...(membership.get(imageId) || new Set<number>())].sort((left, right) => left - right);
    cameras.push({
      imageId,
      name: imageNames[imageId - 1] || `image-${imageId}`,
      position,
      chunkIndexes,
      primaryChunkIndex: chunkIndexes[0] ?? null,
    });
  }
  return cameras;
}

function parsePointLine(line: string, membership: Map<number, Set<number>>): ParsedPoint | null {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#")) {
    return null;
  }
  const parts = trimmed.split(/\s+/);
  if (parts.length < 8) {
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

  const chunkVotes = new Map<number, number>();
  for (let index = 8; index < parts.length; index += 2) {
    const imageId = Number(parts[index]);
    const chunks = membership.get(imageId);
    if (!chunks) {
      continue;
    }
    for (const chunkIndex of chunks) {
      chunkVotes.set(chunkIndex, (chunkVotes.get(chunkIndex) || 0) + 1);
    }
  }
  const chunkIndex = [...chunkVotes.entries()].sort((left, right) => right[1] - left[1])[0]?.[0] ?? -1;
  return { x, y, z, r, g, b, chunkIndex };
}

function normalizeScene(points: ParsedPoint[], cameras: RawCamera[]) {
  const min: Vec3 = [Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY];
  const max: Vec3 = [Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY];
  const extend = ([x, y, z]: Vec3) => {
    min[0] = Math.min(min[0], x);
    min[1] = Math.min(min[1], y);
    min[2] = Math.min(min[2], z);
    max[0] = Math.max(max[0], x);
    max[1] = Math.max(max[1], y);
    max[2] = Math.max(max[2], z);
  };
  points.forEach((point) => extend([point.x, point.y, point.z]));
  cameras.forEach((camera) => extend(camera.position));

  const center: Vec3 = [
    (min[0] + max[0]) / 2,
    (min[1] + max[1]) / 2,
    (min[2] + max[2]) / 2,
  ];
  const span = Math.max(max[0] - min[0], max[1] - min[1], max[2] - min[2], 1);
  const scale = 2.6 / span;
  const normalize = ([x, y, z]: Vec3): Vec3 => [
    (x - center[0]) * scale,
    (y - center[1]) * scale,
    (z - center[2]) * scale,
  ];

  const positions: number[] = [];
  const colors: number[] = [];
  const chunkColors: number[] = [];
  const pointChunkIndexes: number[] = [];
  for (const point of points) {
    const normalized = normalize([point.x, point.y, point.z]);
    positions.push(...normalized);
    colors.push(point.r / 255, point.g / 255, point.b / 255);
    chunkColors.push(...(point.chunkIndex >= 0 ? CHUNK_PALETTE[point.chunkIndex % CHUNK_PALETTE.length] : [0.8, 0.82, 0.86]));
    pointChunkIndexes.push(point.chunkIndex);
  }

  return {
    bounds: { min: normalize(min), max: normalize(max), center: [0, 0, 0] as Vec3 },
    positions,
    colors,
    chunkColors,
    pointChunkIndexes,
    cameras: cameras.map((camera) => ({
      ...camera,
      position: normalize(camera.position),
    })),
  };
}

export async function buildSfmPreviewPayload(
  artifact: SfmPreviewArtifact,
  requestedMaxPoints = DEFAULT_SAMPLE_POINTS,
): Promise<SfmPreviewPayload> {
  const maxPoints = Math.min(MAX_SAMPLE_POINTS, Math.max(1000, requestedMaxPoints));
  const pointsKey = artifactKey(artifact, "sparse/0/points3D.txt");
  const framesKey = artifactKey(artifact, "sparse/0/frames.txt");
  const manifestKey = artifactKey(artifact, "chunk_planner_manifest.json");
  const sourceSizeBytes = await headSize(artifact.bucket, pointsKey);
  const ranges = buildRanges(sourceSizeBytes);
  const perRangeTarget = Math.max(250, Math.ceil(maxPoints / ranges.length));

  const [pointsHeader, framesText, manifestText, imageKeys] = await Promise.all([
    readRangeText(artifact.bucket, pointsKey, 0, 4095),
    readObjectText(artifact.bucket, framesKey),
    readObjectText(artifact.bucket, manifestKey).catch(() => "{\"chunks\":[]}"),
    listS3Keys(artifact.bucket, artifactKey(artifact, "images/")),
  ]);

  const imagePrefix = artifactKey(artifact, "images/");
  const imageNames = imageKeys
    .map((key) => key.slice(imagePrefix.length))
    .filter(Boolean)
    .sort((left, right) => left.localeCompare(right));
  const chunkRecords = parseChunkRecords(manifestText);
  const membership = buildImageMembership(chunkRecords, imageNames);
  const cameras = parseFrameCameras(framesText, imageNames, membership);
  const sampledPoints: ParsedPoint[] = [];

  for (const [start, end] of ranges) {
    const text = await readRangeText(artifact.bucket, pointsKey, start, end);
    const lines = text.split(/\r?\n/);
    if (start > 0) {
      lines.shift();
    }
    if (end < sourceSizeBytes - 1) {
      lines.pop();
    }
    sampledPoints.push(
      ...reduceSample(
        lines.map((line) => parsePointLine(line, membership)).filter((point): point is ParsedPoint => point !== null),
        perRangeTarget,
      ),
    );
  }

  const points = reduceSample(sampledPoints, maxPoints);
  const normalized = normalizeScene(points, cameras);

  return {
    artifact,
    exactPointCount: parseCount(/Number of points:\s*([\d,]+)/, pointsHeader),
    registeredImageCount: parseCount(/Number of frames:\s*([\d,]+)/, framesText),
    sampledPointCount: points.length,
    sourceSizeBytes,
    sampledRanges: ranges.length,
    chunkCount: chunkRecords.length,
    bounds: normalized.bounds,
    positions: normalized.positions,
    colors: normalized.colors,
    chunkColors: normalized.chunkColors,
    pointChunkIndexes: normalized.pointChunkIndexes,
    cameras: normalized.cameras,
  };
}
