import { AwsClient } from "aws4fetch";
import { DEFAULT_SFM_PREVIEW_ARTIFACT, type SfmPreviewArtifact } from "./sfmPreview";

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

type CameraIntrinsics = {
  model: string;
  width: number;
  height: number;
  fx: number;
  fy: number;
  cx: number;
  cy: number;
};

type ChunkMembership = {
  primaryChunkIndex: number | null;
  chunkIndexes: number[];
  role: "core" | "overlap" | "shared" | "unassigned";
};

type RawChunkRecord = {
  index: number;
  coreNames: string[];
  overlapNames: string[];
  imageNames: string[];
};

type RawCamera = {
  imageId: number;
  name: string;
  position: Vec3;
  rotation: Matrix3;
  primaryChunkIndex: number | null;
  chunkIndexes: number[];
  role: "core" | "overlap" | "shared" | "unassigned";
  color: string;
  forward?: Vec3;
  frustumCorners?: [Vec3, Vec3, Vec3, Vec3];
};

export type SfmPreviewChunk = {
  index: number;
  label: string;
  color: string;
  cameraCount: number;
  coreCount: number;
  overlapCount: number;
  sharedCount: number;
  bounds: {
    min: Vec3;
    max: Vec3;
    center: Vec3;
  } | null;
};

export type SfmPreviewCamera = {
  imageId: number;
  name: string;
  position: Vec3;
  forward: Vec3;
  frustumCorners: [Vec3, Vec3, Vec3, Vec3];
  primaryChunkIndex: number | null;
  chunkIndexes: number[];
  role: "core" | "overlap" | "shared" | "unassigned";
  color: string;
};

export type SfmPreviewInspectorPayload = {
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
  chunkPointColors: number[];
  pointChunkIndexes: number[];
  cameras: SfmPreviewCamera[];
  chunks: SfmPreviewChunk[];
  gaussianBundleUrl: string | null;
};

const REGION = process.env.AWS_REGION || process.env.AWS_DEFAULT_REGION || "us-west-2";
const RANGE_COUNT = 14;
const RANGE_BYTES = 768 * 1024;
const DEFAULT_SAMPLE_POINTS = 18_000;
const CHUNK_PALETTE = [
  "#f97316",
  "#22c55e",
  "#38bdf8",
  "#facc15",
  "#fb7185",
  "#a78bfa",
  "#2dd4bf",
  "#f59e0b",
  "#84cc16",
  "#60a5fa",
  "#f472b6",
  "#c084fc",
  "#34d399",
  "#e879f9",
] as const;

const inspectorCache = new Map<string, Promise<SfmPreviewInspectorPayload>>();
let awsClient: AwsClient | null = null;

function getAwsClient(): AwsClient {
  if (!awsClient) {
    const accessKeyId = process.env.AWS_ACCESS_KEY_ID;
    const secretAccessKey = process.env.AWS_SECRET_ACCESS_KEY;
    const sessionToken = process.env.AWS_SESSION_TOKEN;

    if (!accessKeyId || !secretAccessKey) {
      throw new Error("Missing AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY for SfM inspector runtime access.");
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

function toArray<T>(value: T | T[] | undefined | null): T[] {
  if (Array.isArray(value)) {
    return value;
  }
  return value == null ? [] : [value];
}

function artifactKey(artifact: SfmPreviewArtifact, suffix: string): string {
  return `${artifact.prefix}/${suffix}`;
}

function encodeKey(key: string): string {
  return key
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");
}

function buildS3ObjectUrl(bucket: string, key: string): string {
  return `https://${bucket}.s3.${REGION}.amazonaws.com/${encodeKey(key)}`;
}

function buildS3ListUrl(bucket: string, prefix: string, continuationToken?: string): string {
  const url = new URL(`https://${bucket}.s3.${REGION}.amazonaws.com/`);
  url.searchParams.set("list-type", "2");
  url.searchParams.set("prefix", prefix);
  url.searchParams.set("max-keys", "1000");
  if (continuationToken) {
    url.searchParams.set("continuation-token", continuationToken);
  }
  return url.toString();
}

async function fetchSignedUrl(url: string, init: RequestInit = {}): Promise<Response> {
  const request = new Request(url, init);
  const signedRequest = await getAwsClient().sign(request);
  const response = await fetch(signedRequest, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`S3 request failed for ${url} (${response.status} ${response.statusText})`);
  }

  return response;
}

async function fetchSignedS3(bucket: string, key: string, init: RequestInit = {}): Promise<Response> {
  return fetchSignedUrl(buildS3ObjectUrl(bucket, key), init);
}

async function readObjectText(bucket: string, key: string): Promise<string> {
  const response = await fetchSignedS3(bucket, key);
  return response.text();
}

async function readRangeText(bucket: string, key: string, start: number, end: number): Promise<string> {
  const response = await fetchSignedS3(bucket, key, {
    method: "GET",
    headers: {
      Range: `bytes=${start}-${end}`,
    },
  });
  return response.text();
}

async function headSize(bucket: string, key: string): Promise<number> {
  const response = await fetchSignedS3(bucket, key, { method: "HEAD" });
  const contentLength = response.headers.get("content-length");
  return contentLength ? Number.parseInt(contentLength, 10) : 0;
}

function parseCount(pattern: RegExp, text: string): number | null {
  const match = text.match(pattern);
  if (!match) {
    return null;
  }

  const parsed = Number.parseInt(match[1].replace(/,/g, ""), 10);
  return Number.isFinite(parsed) ? parsed : null;
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

function vecAdd(left: Vec3, right: Vec3): Vec3 {
  return [left[0] + right[0], left[1] + right[1], left[2] + right[2]];
}

function vecScale(vec: Vec3, scalar: number): Vec3 {
  return [vec[0] * scalar, vec[1] * scalar, vec[2] * scalar];
}

function vecNormalize(vec: Vec3): Vec3 {
  const length = Math.hypot(vec[0], vec[1], vec[2]) || 1;
  return [vec[0] / length, vec[1] / length, vec[2] / length];
}

function vecTransformTranspose(matrix: Matrix3, vec: Vec3): Vec3 {
  return [
    matrix[0][0] * vec[0] + matrix[1][0] * vec[1] + matrix[2][0] * vec[2],
    matrix[0][1] * vec[0] + matrix[1][1] * vec[1] + matrix[2][1] * vec[2],
    matrix[0][2] * vec[0] + matrix[1][2] * vec[1] + matrix[2][2] * vec[2],
  ];
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

function parseCameraIntrinsics(text: string): CameraIntrinsics {
  const line = text
    .split(/\r?\n/)
    .map((value) => value.trim())
    .find((value) => value && !value.startsWith("#"));

  if (!line) {
    throw new Error("Missing cameras.txt data for SfM inspector.");
  }

  const parts = line.split(/\s+/);
  const model = parts[1];
  const width = Number(parts[2]);
  const height = Number(parts[3]);
  const params = parts.slice(4).map(Number);

  if (!Number.isFinite(width) || !Number.isFinite(height)) {
    throw new Error("Invalid camera dimensions in cameras.txt.");
  }

  if (model === "SIMPLE_RADIAL" || model === "SIMPLE_PINHOLE") {
    return {
      model,
      width,
      height,
      fx: params[0],
      fy: params[0],
      cx: params[1],
      cy: params[2],
    };
  }

  if (model === "PINHOLE" || model === "OPENCV") {
    return {
      model,
      width,
      height,
      fx: params[0],
      fy: params[1],
      cx: params[2],
      cy: params[3],
    };
  }

  throw new Error(`Unsupported camera model for SfM inspector: ${model}`);
}

async function listS3Keys(bucket: string, prefix: string): Promise<string[]> {
  const keys: string[] = [];
  let continuationToken: string | undefined;

  while (true) {
    const response = await fetchSignedUrl(buildS3ListUrl(bucket, prefix, continuationToken));
    const xml = await response.text();
    keys.push(
      ...[...xml.matchAll(/<Key>([^<]+)<\/Key>/g)]
        .map((match) => match[1]?.trim() ?? "")
        .filter(Boolean),
    );

    const truncated = /<IsTruncated>true<\/IsTruncated>/.test(xml);
    continuationToken = truncated
      ? xml.match(/<NextContinuationToken>([^<]+)<\/NextContinuationToken>/)?.[1]?.trim()
      : undefined;

    if (!continuationToken) {
      break;
    }
  }

  return keys;
}

async function listImageNames(artifact: SfmPreviewArtifact): Promise<string[]> {
  const prefix = artifactKey(artifact, "images/");
  const keys = await listS3Keys(artifact.bucket, prefix);
  return keys
    .map((key) => key.slice(prefix.length))
    .filter(Boolean)
    .sort((left, right) => left.localeCompare(right));
}

function resolveChunkColor(index: number): string {
  return CHUNK_PALETTE[index % CHUNK_PALETTE.length];
}

function hexToRgb01(hex: string): Vec3 {
  const normalized = hex.replace("#", "");
  const value = Number.parseInt(normalized, 16);
  return [((value >> 16) & 255) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255];
}

function parseChunkRecords(text: string): RawChunkRecord[] {
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

  const source = parsed.chunks ?? parsed.chunk_plans ?? [];
  return source.map((chunk, index) => ({
    index: Number.isFinite(chunk.index) ? Number(chunk.index) : index,
    coreNames: chunk.core_names ?? [],
    overlapNames: chunk.overlap_names ?? [],
    imageNames: chunk.image_names ?? chunk.core_names ?? [],
  }));
}

function buildChunkMembershipMaps(chunkRecords: RawChunkRecord[], imageNames: string[]) {
  const nameToImageId = new Map<string, number>();
  imageNames.forEach((name, index) => {
    nameToImageId.set(name, index + 1);
  });

  const membershipMap = new Map<number, { core: Set<number>; overlap: Set<number>; all: Set<number> }>();

  for (const chunk of chunkRecords) {
    for (const name of chunk.coreNames) {
      const imageId = nameToImageId.get(name);
      if (!imageId) continue;
      const membership = membershipMap.get(imageId) ?? {
        core: new Set<number>(),
        overlap: new Set<number>(),
        all: new Set<number>(),
      };
      membership.core.add(chunk.index);
      membership.all.add(chunk.index);
      membershipMap.set(imageId, membership);
    }

    for (const name of chunk.overlapNames) {
      const imageId = nameToImageId.get(name);
      if (!imageId) continue;
      const membership = membershipMap.get(imageId) ?? {
        core: new Set<number>(),
        overlap: new Set<number>(),
        all: new Set<number>(),
      };
      membership.overlap.add(chunk.index);
      membership.all.add(chunk.index);
      membershipMap.set(imageId, membership);
    }
  }

  const resolvedMembership = new Map<number, ChunkMembership>();
  for (const [imageId, membership] of membershipMap.entries()) {
    const chunkIndexes = [...membership.all].sort((left, right) => left - right);
    const primaryChunkIndex =
      [...membership.core].sort((left, right) => left - right)[0] ??
      [...membership.overlap].sort((left, right) => left - right)[0] ??
      null;

    const role: ChunkMembership["role"] =
      chunkIndexes.length > 1
        ? "shared"
        : membership.core.size > 0
          ? "core"
          : membership.overlap.size > 0
            ? "overlap"
            : "unassigned";

    resolvedMembership.set(imageId, {
      primaryChunkIndex,
      chunkIndexes,
      role,
    });
  }

  return {
    nameToImageId,
    imageMembership: resolvedMembership,
  };
}

function parseFrameCameras(
  framesText: string,
  imageNames: string[],
  imageMembership: Map<number, ChunkMembership>,
): RawCamera[] {
  const cameras: RawCamera[] = [];

  for (const line of framesText.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    const parts = trimmed.split(/\s+/);
    if (parts.length < 12) {
      continue;
    }

    const imageId = Number(parts[parts.length - 1]);
    if (!Number.isFinite(imageId)) {
      continue;
    }

    const rotation = quatToMatrix([
      Number(parts[2]),
      Number(parts[3]),
      Number(parts[4]),
      Number(parts[5]),
    ]);
    const translation: Vec3 = [Number(parts[6]), Number(parts[7]), Number(parts[8])];
    const position = vecScale(vecTransformTranspose(rotation, translation), -1);
    const membership = imageMembership.get(imageId) ?? {
      primaryChunkIndex: null,
      chunkIndexes: [],
      role: "unassigned" as const,
    };

    cameras.push({
      imageId,
      name: imageNames[imageId - 1] ?? `image-${imageId}`,
      position,
      rotation,
      primaryChunkIndex: membership.primaryChunkIndex,
      chunkIndexes: membership.chunkIndexes,
      role: membership.role,
      color:
        membership.primaryChunkIndex === null
          ? "#cbd5e1"
          : resolveChunkColor(membership.primaryChunkIndex),
    });
  }

  return cameras;
}

function parsePointLine(line: string, imageMembership: Map<number, ChunkMembership>): ParsedPoint | null {
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

  const chunkCounts = new Map<number, number>();
  for (let index = 8; index < parts.length; index += 2) {
    const imageId = Number(parts[index]);
    if (!Number.isFinite(imageId)) {
      continue;
    }
    const membership = imageMembership.get(imageId);
    if (!membership) {
      continue;
    }
    for (const chunkIndex of membership.chunkIndexes) {
      chunkCounts.set(chunkIndex, (chunkCounts.get(chunkIndex) ?? 0) + 1);
    }
  }

  const chunkIndex =
    [...chunkCounts.entries()].sort((left, right) => right[1] - left[1])[0]?.[0] ?? -1;

  return { x, y, z, r, g, b, chunkIndex };
}

async function sampleSparsePoints(
  artifact: SfmPreviewArtifact,
  imageMembership: Map<number, ChunkMembership>,
  maxPoints = DEFAULT_SAMPLE_POINTS,
) {
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
      .map((line) => parsePointLine(line, imageMembership))
      .filter((point): point is ParsedPoint => point !== null);
    sampledPoints.push(...reduceSample(parsed, perRangeTarget));
  }

  return {
    exactPointCount: parseCount(/Number of points:\s*([\d,]+)/, pointsHeader),
    registeredImageCount: parseCount(/Number of images:\s*([\d,]+)/, imagesHeader),
    sampledRanges: ranges.length,
    sourceSizeBytes,
    points: reduceSample(sampledPoints, maxPoints),
  };
}

function computeBaseSpan(points: ParsedPoint[], cameras: RawCamera[]): number {
  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let minZ = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  let maxZ = Number.NEGATIVE_INFINITY;

  for (const point of points) {
    minX = Math.min(minX, point.x);
    minY = Math.min(minY, point.y);
    minZ = Math.min(minZ, point.z);
    maxX = Math.max(maxX, point.x);
    maxY = Math.max(maxY, point.y);
    maxZ = Math.max(maxZ, point.z);
  }

  for (const camera of cameras) {
    minX = Math.min(minX, camera.position[0]);
    minY = Math.min(minY, camera.position[1]);
    minZ = Math.min(minZ, camera.position[2]);
    maxX = Math.max(maxX, camera.position[0]);
    maxY = Math.max(maxY, camera.position[1]);
    maxZ = Math.max(maxZ, camera.position[2]);
  }

  return Math.max(maxX - minX, maxY - minY, maxZ - minZ, 1);
}

function applyFrustumGeometry(cameras: RawCamera[], intrinsics: CameraIntrinsics, frustumDepth: number) {
  const cornerPixels: Array<[number, number]> = [
    [0, 0],
    [intrinsics.width, 0],
    [intrinsics.width, intrinsics.height],
    [0, intrinsics.height],
  ];

  for (const camera of cameras) {
    const corners = cornerPixels.map(([u, v]) => {
      const rayCamera = vecNormalize([
        (u - intrinsics.cx) / intrinsics.fx,
        (v - intrinsics.cy) / intrinsics.fy,
        1,
      ]);
      const rayWorld = vecNormalize(vecTransformTranspose(camera.rotation, rayCamera));
      return vecAdd(camera.position, vecScale(rayWorld, frustumDepth));
    }) as [Vec3, Vec3, Vec3, Vec3];

    camera.forward = vecNormalize(vecTransformTranspose(camera.rotation, [0, 0, 1]));
    camera.frustumCorners = corners;
  }
}

function buildNormalizedScene(points: ParsedPoint[], cameras: RawCamera[]) {
  const min: Vec3 = [Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY];
  const max: Vec3 = [Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY];

  const extendBounds = (vec: Vec3) => {
    min[0] = Math.min(min[0], vec[0]);
    min[1] = Math.min(min[1], vec[1]);
    min[2] = Math.min(min[2], vec[2]);
    max[0] = Math.max(max[0], vec[0]);
    max[1] = Math.max(max[1], vec[1]);
    max[2] = Math.max(max[2], vec[2]);
  };

  for (const point of points) {
    extendBounds([point.x, point.y, point.z]);
  }

  for (const camera of cameras) {
    extendBounds(camera.position);
    for (const corner of camera.frustumCorners ?? []) {
      extendBounds(corner);
    }
  }

  const center: Vec3 = [
    (min[0] + max[0]) / 2,
    (min[1] + max[1]) / 2,
    (min[2] + max[2]) / 2,
  ];
  const span = Math.max(max[0] - min[0], max[1] - min[1], max[2] - min[2], 1);
  const scale = 2.6 / span;

  const normalizeVec = (vec: Vec3): Vec3 => [
    (vec[0] - center[0]) * scale,
    (vec[1] - center[1]) * scale,
    (vec[2] - center[2]) * scale,
  ];

  const positions: number[] = [];
  const colors: number[] = [];
  const chunkPointColors: number[] = [];
  const pointChunkIndexes: number[] = [];

  for (const point of points) {
    const normalized = normalizeVec([point.x, point.y, point.z]);
    positions.push(normalized[0], normalized[1], normalized[2]);
    colors.push(point.r / 255, point.g / 255, point.b / 255);

    if (point.chunkIndex >= 0) {
      const [cr, cg, cb] = hexToRgb01(resolveChunkColor(point.chunkIndex));
      chunkPointColors.push(cr, cg, cb);
    } else {
      chunkPointColors.push(0.78, 0.82, 0.88);
    }
    pointChunkIndexes.push(point.chunkIndex);
  }

  const normalizedCameras: SfmPreviewCamera[] = cameras.map((camera) => ({
    imageId: camera.imageId,
    name: camera.name,
    position: normalizeVec(camera.position),
    forward: vecNormalize(camera.forward ?? [0, 0, 1]),
    frustumCorners: (camera.frustumCorners ?? [
      camera.position,
      camera.position,
      camera.position,
      camera.position,
    ]).map(normalizeVec) as [Vec3, Vec3, Vec3, Vec3],
    primaryChunkIndex: camera.primaryChunkIndex,
    chunkIndexes: camera.chunkIndexes,
    role: camera.role,
    color: camera.color,
  }));

  return {
    bounds: {
      min: normalizeVec(min),
      max: normalizeVec(max),
      center: [0, 0, 0] as Vec3,
    },
    scale,
    positions,
    colors,
    chunkPointColors,
    pointChunkIndexes,
    cameras: normalizedCameras,
  };
}

function buildChunkSummaries(
  chunkRecords: RawChunkRecord[],
  cameras: SfmPreviewCamera[],
): SfmPreviewChunk[] {
  return chunkRecords.map((chunk) => {
    const chunkCameras = cameras.filter((camera) => camera.chunkIndexes.includes(chunk.index));
    const sharedCount = chunkCameras.filter((camera) => camera.chunkIndexes.length > 1).length;

    if (!chunkCameras.length) {
      return {
        index: chunk.index,
        label: `Chunk ${chunk.index + 1}`,
        color: resolveChunkColor(chunk.index),
        cameraCount: 0,
        coreCount: chunk.coreNames.length,
        overlapCount: chunk.overlapNames.length,
        sharedCount,
        bounds: null,
      };
    }

    const min: Vec3 = [Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY];
    const max: Vec3 = [Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY];

    for (const camera of chunkCameras) {
      const extentPoints = [camera.position, ...camera.frustumCorners];
      for (const position of extentPoints) {
        min[0] = Math.min(min[0], position[0]);
        min[1] = Math.min(min[1], position[1]);
        min[2] = Math.min(min[2], position[2]);
        max[0] = Math.max(max[0], position[0]);
        max[1] = Math.max(max[1], position[1]);
        max[2] = Math.max(max[2], position[2]);
      }
    }

    const center: Vec3 = [
      (min[0] + max[0]) / 2,
      (min[1] + max[1]) / 2,
      (min[2] + max[2]) / 2,
    ];

    return {
      index: chunk.index,
      label: `Chunk ${chunk.index + 1}`,
      color: resolveChunkColor(chunk.index),
      cameraCount: chunkCameras.length,
      coreCount: chunk.coreNames.length,
      overlapCount: chunk.overlapNames.length,
      sharedCount,
      bounds: {
        min,
        max,
        center,
      },
    };
  });
}

async function buildInspectorPayload(
  artifact: SfmPreviewArtifact,
  maxPoints = DEFAULT_SAMPLE_POINTS,
): Promise<SfmPreviewInspectorPayload> {
  const manifestKey = artifactKey(artifact, "chunk_planner_manifest.json");
  const framesKey = artifactKey(artifact, "sparse/0/frames.txt");
  const camerasKey = artifactKey(artifact, "sparse/0/cameras.txt");

  const [manifestText, framesText, camerasText, imageNames] = await Promise.all([
    readObjectText(artifact.bucket, manifestKey),
    readObjectText(artifact.bucket, framesKey),
    readObjectText(artifact.bucket, camerasKey),
    listImageNames(artifact),
  ]);

  const chunkRecords = parseChunkRecords(manifestText);
  const { imageMembership } = buildChunkMembershipMaps(chunkRecords, imageNames);
  const intrinsics = parseCameraIntrinsics(camerasText);
  const rawCameras = parseFrameCameras(framesText, imageNames, imageMembership);
  const sparsePoints = await sampleSparsePoints(artifact, imageMembership, maxPoints);

  const baseSpan = computeBaseSpan(sparsePoints.points, rawCameras);
  applyFrustumGeometry(rawCameras, intrinsics, baseSpan * 0.055);

  const normalizedScene = buildNormalizedScene(sparsePoints.points, rawCameras);
  const chunks = buildChunkSummaries(chunkRecords, normalizedScene.cameras);

  return {
    artifact,
    exactPointCount: sparsePoints.exactPointCount,
    registeredImageCount: sparsePoints.registeredImageCount,
    sampledPointCount: sparsePoints.points.length,
    sampledRanges: sparsePoints.sampledRanges,
    sourceSizeBytes: sparsePoints.sourceSizeBytes,
    sampleWindowBytes: Math.min(RANGE_BYTES, sparsePoints.sourceSizeBytes),
    scale: normalizedScene.scale,
    bounds: normalizedScene.bounds,
    positions: normalizedScene.positions,
    colors: normalizedScene.colors,
    chunkPointColors: normalizedScene.chunkPointColors,
    pointChunkIndexes: normalizedScene.pointChunkIndexes,
    cameras: normalizedScene.cameras,
    chunks,
    gaussianBundleUrl: null,
  };
}

export async function getSfmPreviewInspectorPayload(
  artifact: SfmPreviewArtifact = DEFAULT_SFM_PREVIEW_ARTIFACT,
  maxPoints = DEFAULT_SAMPLE_POINTS,
): Promise<SfmPreviewInspectorPayload> {
  const cacheKey = `${artifact.bucket}/${artifact.prefix}:${maxPoints}:inspector`;
  let pending = inspectorCache.get(cacheKey);
  if (!pending) {
    pending = buildInspectorPayload(artifact, maxPoints);
    inspectorCache.set(cacheKey, pending);
  }
  return pending;
}
