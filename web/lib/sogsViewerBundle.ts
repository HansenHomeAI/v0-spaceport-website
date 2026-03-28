export type SogsViewerStage = "compressed" | "3dgs" | "sfm" | "direct";

export type ResolvedSogsSource = {
  contentUrl: string;
  stage: SogsViewerStage;
};

export const DEFAULT_SOGS_BUNDLE_URL =
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/sogs-test-1763664401/supersplat_bundle/meta.json";

const KNOWN_CONTENT_EXTENSIONS = [".json", ".ply", ".gsplat", ".sog", ".tar.gz"];
const PIPELINE_BUCKETS = new Set([
  "spaceport-ml-processing",
  "spaceport-ml-pipeline",
  "spaceport-sagemaker-us-west-2",
]);

type S3Reference = {
  bucket: string;
  key: string;
};

function trimSlashes(value: string): string {
  return value.replace(/^\/+|\/+$/g, "");
}

function hasKnownContentExtension(pathname: string): boolean {
  return KNOWN_CONTENT_EXTENSIONS.some((ext) => pathname.toLowerCase().endsWith(ext));
}

function buildContentRoute(mode: "raw" | "3dgs-ply" | "colmap-ply", bucket: string, key: string, filename?: string): string {
  const path = ["/api/sogs-proxy", mode, "s3", encodeURIComponent(bucket)];
  if (trimSlashes(key)) {
    path.push(...trimSlashes(key).split("/").map((segment) => encodeURIComponent(segment)));
  }
  if (filename) {
    path.push(encodeURIComponent(filename));
  }
  return path.join("/");
}

export function getBaseOrigin(): string {
  return typeof window !== "undefined" ? window.location.origin : "https://spcprt.com";
}

function isS3PathHost(host: string): boolean {
  return host === "s3.amazonaws.com" || /^s3[.-][a-z0-9-]+\.amazonaws\.com$/i.test(host);
}

function parseS3Url(url: URL): S3Reference | null {
  if (url.protocol === "s3:") {
    const bucket = url.hostname;
    const key = trimSlashes(url.pathname);
    return bucket && key ? { bucket, key } : null;
  }

  const hostParts = url.hostname.split(".");
  if (hostParts.length >= 4 && hostParts[1] === "s3" && hostParts.at(-2) === "amazonaws" && hostParts.at(-1) === "com") {
    return {
      bucket: hostParts[0],
      key: trimSlashes(url.pathname),
    };
  }

  if (isS3PathHost(url.hostname)) {
    const [bucket, ...rest] = trimSlashes(url.pathname).split("/");
    if (!bucket || !rest.length) {
      return null;
    }
    return {
      bucket,
      key: rest.join("/"),
    };
  }

  return null;
}

function resolveCompressedKey(key: string): string {
  const trimmed = trimSlashes(key);
  if (!trimmed) {
    return trimmed;
  }
  if (trimmed.endsWith("/meta.json") || trimmed.endsWith(".webp") || trimmed.endsWith("settings.json")) {
    return trimmed;
  }
  if (trimmed.includes("/supersplat_bundle/") || trimmed.endsWith("/supersplat_bundle")) {
    return `${trimmed.replace(/\/$/, "")}/meta.json`;
  }
  if (trimmed.includes("/compressed_splat/") || trimmed.endsWith("/compressed_splat")) {
    return `${trimmed.replace(/\/$/, "")}/meta.json`;
  }
  return `${trimmed}/supersplat_bundle/meta.json`;
}

function resolveThreeDgsKey(key: string): string | null {
  const trimmed = trimSlashes(key);
  if (!trimmed) {
    return null;
  }
  if (trimmed.endsWith(".ply") || trimmed.endsWith(".gsplat") || trimmed.endsWith(".sog") || trimmed.endsWith(".tar.gz")) {
    return trimmed;
  }
  if (trimmed.endsWith("/output")) {
    return `${trimmed}/model.tar.gz`;
  }
  if (trimmed.endsWith("/output/")) {
    return `${trimmed}model.tar.gz`;
  }
  return null;
}

function resolveColmapKey(key: string): string {
  const trimmed = trimSlashes(key);
  if (!trimmed) {
    return trimmed;
  }
  if (trimmed.endsWith("/points3D.txt") || trimmed.endsWith("/points3D.bin")) {
    return trimmed;
  }
  if (trimmed.endsWith("/sfm_metadata.json")) {
    return trimmed.replace(/\/sfm_metadata\.json$/i, "/sparse/0/points3D.txt");
  }
  if (/\/sparse\/0\/[^/]+$/i.test(trimmed)) {
    return trimmed.replace(/\/[^/]+$/i, "/points3D.txt");
  }
  if (trimmed.endsWith("/sparse/0")) {
    return `${trimmed}/points3D.txt`;
  }
  return `${trimmed}/sparse/0/points3D.txt`;
}

function resolveS3Source(ref: S3Reference): ResolvedSogsSource | null {
  if (!PIPELINE_BUCKETS.has(ref.bucket)) {
    return null;
  }

  const key = trimSlashes(ref.key);
  if (!key) {
    return null;
  }

  if (
    key.startsWith("compressed/") ||
    key.startsWith("public-viewer/") ||
    key.includes("/supersplat_bundle/") ||
    key.includes("/compressed_splat/")
  ) {
    return {
      contentUrl: buildContentRoute("raw", ref.bucket, resolveCompressedKey(key)),
      stage: "compressed",
    };
  }

  if (key.startsWith("3dgs/") || key.endsWith("model.tar.gz") || key.endsWith("splat.ply") || key.endsWith(".gsplat")) {
    const resolvedKey = resolveThreeDgsKey(key);
    if (!resolvedKey) {
      return null;
    }
    const mode = resolvedKey.endsWith(".tar.gz") ? "3dgs-ply" : "raw";
    return {
      contentUrl: buildContentRoute(mode, ref.bucket, resolvedKey, mode === "3dgs-ply" ? "splat.ply" : undefined),
      stage: "3dgs",
    };
  }

  if (key.startsWith("colmap/") || key.endsWith("/sfm_metadata.json") || key.includes("/sparse/0/")) {
    return {
      contentUrl: buildContentRoute("colmap-ply", ref.bucket, resolveColmapKey(key), "points3D.ply"),
      stage: "sfm",
    };
  }

  return null;
}

function resolveDirectHttpUrl(url: URL): ResolvedSogsSource | null {
  if (!url.protocol.startsWith("http")) {
    return null;
  }

  const s3Ref = parseS3Url(url);
  if (s3Ref) {
    return resolveS3Source(s3Ref);
  }

  if (!hasKnownContentExtension(url.pathname)) {
    url.pathname = `${url.pathname.replace(/\/$/, "")}/meta.json`;
  }

  return {
    contentUrl: url.toString(),
    stage: "direct",
  };
}

export function resolveSogsSource(rawValue: string): ResolvedSogsSource | null {
  const trimmed = rawValue.trim();
  if (!trimmed) {
    return null;
  }

  try {
    const parsed =
      trimmed.startsWith("s3://") || trimmed.startsWith("http://") || trimmed.startsWith("https://")
        ? new URL(trimmed)
        : new URL(trimmed, getBaseOrigin());

    if (parsed.protocol === "s3:") {
      const s3Ref = parseS3Url(parsed);
      return s3Ref ? resolveS3Source(s3Ref) : null;
    }

    return resolveDirectHttpUrl(parsed);
  } catch {
    return null;
  }
}

export function normalizeBundleUrl(rawValue: string): string | null {
  return resolveSogsSource(rawValue)?.contentUrl ?? null;
}
