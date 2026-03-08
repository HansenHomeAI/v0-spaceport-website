import * as THREE from "three";

export const PROXY_HOSTS = new Set([
  "spaceport-ml-processing.s3.amazonaws.com",
  "spaceport-ml-processing.s3.us-west-2.amazonaws.com",
  "spaceport-ml-processing-staging.s3.amazonaws.com",
  "spaceport-ml-processing-staging.s3.us-west-2.amazonaws.com",
  "spaceport-ml-processing-prod.s3.amazonaws.com",
  "spaceport-ml-processing-prod.s3.us-west-2.amazonaws.com",
]);

export const toHttpsFromS3 = (raw) => {
  if (!raw.startsWith("s3://")) {
    return raw;
  }
  const withoutScheme = raw.replace("s3://", "");
  const [bucket, ...rest] = withoutScheme.split("/");
  if (!bucket) {
    return raw;
  }
  return `https://${bucket}.s3.amazonaws.com/${rest.join("/")}`;
};

export const normalizeUrl = (rawValue, options = {}) => {
  const trimmed = rawValue.trim();
  if (!trimmed) {
    return null;
  }

  const normalized = toHttpsFromS3(trimmed);
  try {
    const baseOrigin = typeof window !== "undefined" ? window.location.origin : "https://spaceport.space";
    const parsed =
      normalized.startsWith("http://") || normalized.startsWith("https://")
        ? new URL(normalized)
        : new URL(normalized, baseOrigin);

    if (options.ensureTrailingSlash && !parsed.pathname.endsWith("/")) {
      parsed.pathname = `${parsed.pathname.replace(/\/?$/, "/")}`;
    }

    if (options.ensureMetaJson && !parsed.pathname.endsWith(".json")) {
      parsed.pathname = parsed.pathname.replace(/\/?$/, "/meta.json");
    }

    return parsed;
  } catch {
    return null;
  }
};

export const withProxyIfNeeded = (url) => {
  if (PROXY_HOSTS.has(url.host)) {
    const base = `${url.protocol}//${url.host}`;
    const encodedBase = base.replace("://", ":/");
    return `/api/sogs-proxy/${encodedBase}${url.pathname}${url.search}`;
  }
  return url.toString();
};

export const derivePipelineFromCompressed = (rawCompressed) => {
  const parsed = normalizeUrl(rawCompressed, { ensureMetaJson: true });
  if (!parsed) {
    return null;
  }

  const match = parsed.pathname.match(/\/compressed\/([^/]+)\//);
  if (!match) {
    return null;
  }

  const jobId = match[1];
  const baseOrigin = `${parsed.protocol}//${parsed.host}`;
  return {
    jobId,
    compressedBundle: parsed.toString(),
    colmapBase: `${baseOrigin}/colmap/${jobId}/`,
    gaussianPly: `${baseOrigin}/3dgs/${jobId}/splat.ply`,
  };
};

export const buildSfmFileUrls = (baseUrl, sparsePath) => {
  const normalized = normalizeUrl(baseUrl, { ensureTrailingSlash: true });
  if (!normalized) {
    return null;
  }
  const safeSparse = sparsePath.replace(/^\/+/, "").replace(/\/?$/, "/");
  const base = normalized.toString();
  return {
    cameras: `${base}${safeSparse}cameras.txt`,
    images: `${base}${safeSparse}images.txt`,
    points: `${base}${safeSparse}points3D.txt`,
  };
};

export const parsePoints = (text, maxPoints) => {
  const positions = [];
  const colors = [];
  let count = 0;
  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;

  for (const line of text.split(/\r?\n/)) {
    if (!line || line.startsWith("#")) {
      continue;
    }
    const parts = line.trim().split(/\s+/);
    if (parts.length < 7) {
      continue;
    }
    const x = Number(parts[1]);
    const y = Number(parts[2]);
    const z = Number(parts[3]);
    const r = Number(parts[4]);
    const g = Number(parts[5]);
    const b = Number(parts[6]);
    if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) {
      continue;
    }

    positions.push(x, y, z);
    colors.push(r / 255, g / 255, b / 255);

    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    minZ = Math.min(minZ, z);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
    maxZ = Math.max(maxZ, z);

    count += 1;
    if (count >= maxPoints) {
      break;
    }
  }

  if (count === 0) {
    minX = minY = minZ = 0;
    maxX = maxY = maxZ = 0;
  }

  return {
    positions: new Float32Array(positions),
    colors: new Float32Array(colors),
    count,
    bounds: {
      min: [minX, minY, minZ],
      max: [maxX, maxY, maxZ],
    },
  };
};

export const parseImages = (text, maxCameras) => {
  const linePositions = [];
  let count = 0;
  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;
  const lines = text.split(/\r?\n/);
  let skipNext = false;

  const pushLine = (a, b) => {
    linePositions.push(a.x, a.y, a.z, b.x, b.y, b.z);
  };

  for (const line of lines) {
    if (skipNext) {
      skipNext = false;
      continue;
    }
    if (!line || line.startsWith("#")) {
      continue;
    }

    const parts = line.trim().split(/\s+/);
    if (parts.length < 9) {
      continue;
    }

    const qw = Number(parts[1]);
    const qx = Number(parts[2]);
    const qy = Number(parts[3]);
    const qz = Number(parts[4]);
    const tx = Number(parts[5]);
    const ty = Number(parts[6]);
    const tz = Number(parts[7]);
    if (![qw, qx, qy, qz, tx, ty, tz].every(Number.isFinite)) {
      continue;
    }

    const worldToCam = new THREE.Quaternion(qx, qy, qz, qw);
    const camToWorld = worldToCam.clone().invert();
    const t = new THREE.Vector3(tx, ty, tz);
    const center = t.clone().applyQuaternion(camToWorld).multiplyScalar(-1);

    minX = Math.min(minX, center.x);
    minY = Math.min(minY, center.y);
    minZ = Math.min(minZ, center.z);
    maxX = Math.max(maxX, center.x);
    maxY = Math.max(maxY, center.y);
    maxZ = Math.max(maxZ, center.z);

    const depth = 0.4;
    const half = depth * 0.35;
    const localCorners = [
      new THREE.Vector3(-half, -half, depth),
      new THREE.Vector3(half, -half, depth),
      new THREE.Vector3(half, half, depth),
      new THREE.Vector3(-half, half, depth),
    ];
    const worldCorners = localCorners.map((corner) => corner.applyQuaternion(camToWorld).add(center));

    for (const corner of worldCorners) {
      pushLine(center, corner);
    }
    pushLine(worldCorners[0], worldCorners[1]);
    pushLine(worldCorners[1], worldCorners[2]);
    pushLine(worldCorners[2], worldCorners[3]);
    pushLine(worldCorners[3], worldCorners[0]);

    count += 1;
    if (count >= maxCameras) {
      break;
    }
    skipNext = true;
  }

  if (count === 0) {
    minX = minY = minZ = 0;
    maxX = maxY = maxZ = 0;
  }

  return {
    positions: new Float32Array(linePositions),
    count,
    bounds: {
      min: [minX, minY, minZ],
      max: [maxX, maxY, maxZ],
    },
  };
};

export const mergeBounds = (first, second) => ({
  min: [
    Math.min(first.min[0], second.min[0]),
    Math.min(first.min[1], second.min[1]),
    Math.min(first.min[2], second.min[2]),
  ],
  max: [
    Math.max(first.max[0], second.max[0]),
    Math.max(first.max[1], second.max[1]),
    Math.max(first.max[2], second.max[2]),
  ],
});
