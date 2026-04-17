"use client";

import {
  CSSProperties,
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

const DEFAULT_COMPRESSED_BUNDLE =
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/sogs-test-1763664401/supersplat_bundle/meta.json";
const VIEWER_BASE = "/supersplat-viewer/index.html";
const PIPELINE_BUCKET_PATTERNS = [
  /^spaceport-ml-processing(?:-[a-z0-9-]+)?$/i,
  /^spaceport-ml-delivery(?:-[a-z0-9-]+)?$/i,
  /^spaceport-model-delivery(?:-[a-z0-9-]+)?$/i,
];
const S3_HOST_PATTERN = /^(.+)\.s3(?:[.-][a-z0-9-]+)?\.amazonaws\.com$/i;
const S3_PATH_STYLE_HOST_PATTERN = /^s3(?:[.-][a-z0-9-]+)?\.amazonaws\.com$/i;

type SfmData = {
  points: Float32Array;
  colors: Float32Array;
  cameraLines: Float32Array;
  pointCount: number;
  cameraCount: number;
  bounds: {
    min: [number, number, number];
    max: [number, number, number];
  };
};

type TransformOption = "native" | "rotateX90" | "rotateX-90" | "rotateY90" | "rotateZ90";

type SupersplatViewportProps = {
  defaultUrl: string;
  normalizeInputUrl?: (rawValue: string) => URL | null;
  onViewerStateChange?: (state: "idle" | "loading" | "ready" | "invalid") => void;
};

type DerivedPipelineArtifacts = {
  sourceKind: "compressed" | "gaussian" | "sfm";
  sourceLabel: string;
  jobId: string | null;
  sourceUrl: string;
  compressedBundle: string | null;
  colmapBase: string | null;
  gaussianPly: string | null;
  sparsePath: string | null;
};

const pageStyles: CSSProperties = {
  position: "relative",
  width: "100vw",
  height: "100vh",
  overflow: "hidden",
  backgroundColor: "#040507",
  color: "#f8f8fb",
  fontFamily: "'Space Grotesk', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
};

const viewportStyles: CSSProperties = {
  position: "absolute",
  inset: 0,
  background:
    "radial-gradient(circle at top left, rgba(255, 122, 26, 0.14), transparent 28%), radial-gradient(circle at top right, rgba(76, 170, 255, 0.14), transparent 26%), #040507",
};

const viewerShellStyles: CSSProperties = {
  position: "absolute",
  inset: 0,
  overflow: "hidden",
  background: "#040507",
};

const overlayStyles: CSSProperties = {
  position: "absolute",
  top: "20px",
  left: "20px",
  zIndex: 20,
  width: "min(560px, calc(100vw - 40px))",
  display: "grid",
  gap: "14px",
};

const collapsedOverlayStyles: CSSProperties = {
  position: "absolute",
  top: "20px",
  left: "20px",
  zIndex: 20,
  display: "flex",
  alignItems: "center",
  gap: "10px",
};

const glassPanelStyles: CSSProperties = {
  background: "rgba(10, 12, 18, 0.72)",
  borderRadius: "24px",
  border: "1px solid rgba(255, 255, 255, 0.12)",
  boxShadow: "0 24px 60px rgba(0, 0, 0, 0.42)",
  backdropFilter: "blur(22px)",
  padding: "16px",
};

const sourceFormStyles: CSSProperties = {
  display: "grid",
  gap: "12px",
};

const inputRowStyles: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "minmax(0, 1fr) auto",
  gap: "10px",
  alignItems: "center",
};

const labelStyles: CSSProperties = {
  fontSize: "0.72rem",
  fontWeight: 600,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "rgba(255, 255, 255, 0.7)",
  display: "block",
};

const inputStyles: CSSProperties = {
  width: "100%",
  padding: "13px 14px",
  borderRadius: "14px",
  border: "1px solid rgba(255, 255, 255, 0.14)",
  background: "rgba(5, 7, 11, 0.78)",
  color: "#ffffff",
  fontSize: "0.95rem",
  outline: "none",
};

const buttonStyles: CSSProperties = {
  padding: "12px 18px",
  borderRadius: "999px",
  border: "1px solid rgba(255, 255, 255, 0.2)",
  background: "linear-gradient(90deg, #ff6b00, #ff9a2b)",
  color: "#09090f",
  fontWeight: 600,
  fontSize: "0.9rem",
  cursor: "pointer",
};

const mutedTextStyles: CSSProperties = {
  fontSize: "0.82rem",
  color: "rgba(255, 255, 255, 0.6)",
  lineHeight: 1.5,
};

const tabListStyles: CSSProperties = {
  display: "flex",
  gap: "8px",
  flexWrap: "wrap",
};

const tabButtonStyles: CSSProperties = {
  padding: "8px 14px",
  borderRadius: "999px",
  border: "1px solid rgba(255, 255, 255, 0.2)",
  background: "rgba(255, 255, 255, 0.05)",
  color: "rgba(255, 255, 255, 0.75)",
  fontSize: "0.78rem",
  fontWeight: 600,
  cursor: "pointer",
};

const activeTabButtonStyles: CSSProperties = {
  ...tabButtonStyles,
  background: "rgba(255, 123, 0, 0.18)",
  border: "1px solid rgba(255, 123, 0, 0.5)",
  color: "#ffffff",
};

const statusPillStyles: CSSProperties = {
  padding: "6px 10px",
  borderRadius: "999px",
  background: "rgba(255, 255, 255, 0.08)",
  border: "1px solid rgba(255, 255, 255, 0.1)",
  fontSize: "0.72rem",
  letterSpacing: "0.05em",
  textTransform: "uppercase",
};

const collapseButtonStyles: CSSProperties = {
  padding: "8px 12px",
  borderRadius: "999px",
  border: "1px solid rgba(255, 255, 255, 0.16)",
  background: "rgba(255, 255, 255, 0.06)",
  color: "#f8f8fb",
  fontSize: "0.78rem",
  fontWeight: 600,
  cursor: "pointer",
  whiteSpace: "nowrap",
};

const collapsedToggleStyles: CSSProperties = {
  ...collapseButtonStyles,
  background: "rgba(10, 12, 18, 0.78)",
  boxShadow: "0 14px 32px rgba(0, 0, 0, 0.28)",
  backdropFilter: "blur(18px)",
};

const toolbarRowStyles: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "10px",
  alignItems: "center",
};

const inlineInputStyles: CSSProperties = {
  ...inputStyles,
  maxWidth: "118px",
  padding: "9px 12px",
  fontSize: "0.84rem",
};

const metaGridStyles: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
  gap: "8px",
};

const metaCardStyles: CSSProperties = {
  padding: "10px 12px",
  borderRadius: "14px",
  background: "rgba(255, 255, 255, 0.04)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  display: "grid",
  gap: "3px",
};

const metaValueStyles: CSSProperties = {
  fontSize: "0.79rem",
  color: "rgba(255, 255, 255, 0.82)",
  wordBreak: "break-word",
};

const sfmControlsStyles: CSSProperties = {
  display: "grid",
  gap: "10px",
};

const bottomStatusStyles: CSSProperties = {
  position: "absolute",
  left: "20px",
  bottom: "20px",
  zIndex: 20,
  maxWidth: "min(520px, calc(100vw - 40px))",
  padding: "12px 14px",
  borderRadius: "18px",
  background: "rgba(8, 10, 14, 0.62)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  backdropFilter: "blur(18px)",
};

const emptyStateStyles: CSSProperties = {
  position: "absolute",
  inset: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  color: "rgba(255, 255, 255, 0.45)",
  fontSize: "0.95rem",
  letterSpacing: "0.02em",
};

const transformOptions: { value: TransformOption; label: string; rotation: [number, number, number] }[] = [
  { value: "native", label: "Native", rotation: [0, 0, 0] },
  { value: "rotateX90", label: "Rotate +90° X", rotation: [Math.PI / 2, 0, 0] },
  { value: "rotateX-90", label: "Rotate -90° X", rotation: [-Math.PI / 2, 0, 0] },
  { value: "rotateY90", label: "Rotate +90° Y", rotation: [0, Math.PI / 2, 0] },
  { value: "rotateZ90", label: "Rotate +90° Z", rotation: [0, 0, Math.PI / 2] },
];

const toHttpsFromS3 = (raw: string) => {
  if (!raw.startsWith("s3://")) {
    return raw;
  }
  const withoutScheme = raw.replace("s3://", "");
  const [bucket, ...rest] = withoutScheme.split("/");
  if (!bucket) {
    return raw;
  }
  const path = rest.join("/");
  return `https://${bucket}.s3.amazonaws.com/${path}`;
};

const isAllowedPipelineBucket = (bucket: string) =>
  PIPELINE_BUCKET_PATTERNS.some((pattern) => pattern.test(bucket));

const getBucketFromUrl = (url: URL) => {
  if (url.protocol === "s3:") {
    return url.hostname.trim() || null;
  }

  const virtualHostedMatch = url.host.match(S3_HOST_PATTERN);
  if (virtualHostedMatch) {
    return virtualHostedMatch[1];
  }

  if (S3_PATH_STYLE_HOST_PATTERN.test(url.host)) {
    const bucket = url.pathname.replace(/^\/+/, "").split("/")[0];
    return bucket || null;
  }

  return null;
};

const normalizeUrl = (rawValue: string, options?: { ensureMetaJson?: boolean; ensureTrailingSlash?: boolean }) => {
  const trimmed = rawValue.trim();
  if (!trimmed) {
    return null;
  }
  const normalized = toHttpsFromS3(trimmed);
  try {
    const baseOrigin = typeof window !== "undefined" ? window.location.origin : "https://spaceport.space";
    const parsed = normalized.startsWith("http://") || normalized.startsWith("https://")
      ? new URL(normalized)
      : new URL(normalized, baseOrigin);

    if (options?.ensureTrailingSlash && !parsed.pathname.endsWith("/")) {
      parsed.pathname = `${parsed.pathname.replace(/\/?$/, "/")}`;
    }

    if (options?.ensureMetaJson && !parsed.pathname.endsWith(".json")) {
      parsed.pathname = parsed.pathname.replace(/\/?$/, "/meta.json");
    }

    return parsed;
  } catch {
    return null;
  }
};

const normalizeCompressedBundleUrl = (rawValue: string) => {
  const parsed = normalizeUrl(rawValue);
  if (!parsed) {
    return null;
  }

  if (!parsed.pathname.endsWith(".json")) {
    if (parsed.pathname.includes("/supersplat_bundle")) {
      parsed.pathname = parsed.pathname.replace(/\/?$/, "/meta.json");
    } else if (
      /\/compressed\/[^/]+\/?$/.test(parsed.pathname) ||
      /\/manual-validations\/[^/]+\/compressed\/?$/.test(parsed.pathname)
    ) {
      parsed.pathname = `${parsed.pathname.replace(/\/?$/, "/")}supersplat_bundle/meta.json`;
    } else {
      parsed.pathname = parsed.pathname.replace(/\/?$/, "/meta.json");
    }
  }

  return parsed;
};

const normalizeGaussianAssetUrl = (rawValue: string) => {
  const parsed = normalizeUrl(rawValue);
  if (!parsed) {
    return null;
  }

  if (parsed.pathname.endsWith("/")) {
    parsed.pathname = `${parsed.pathname}splat.ply`;
    return parsed;
  }

  if (parsed.pathname.endsWith("/model.tar.gz")) {
    const standard3dgsMatch = parsed.pathname.match(/\/3dgs\/([^/]+)\/.+\/model\.tar\.gz$/);
    if (standard3dgsMatch) {
      parsed.pathname = `/3dgs/${standard3dgsMatch[1]}/splat.ply`;
      return parsed;
    }

    parsed.pathname = parsed.pathname.replace(/model\.tar\.gz$/, "splat.ply");
  }

  return parsed;
};

const resolveSfmInput = (rawValue: string, fallbackSparsePath: string) => {
  const parsed = normalizeUrl(rawValue);
  if (!parsed) {
    return null;
  }

  const directFileMatch = parsed.pathname.match(/^(.*\/)(sparse\/\d+\/)(?:cameras|images|points3D)\.txt$/);
  if (directFileMatch) {
    parsed.pathname = directFileMatch[1];
    return {
      baseUrl: parsed.toString(),
      sparsePath: directFileMatch[2],
    };
  }

  const sparseDirectoryMatch = parsed.pathname.match(/^(.*\/)(sparse\/\d+\/)$/);
  if (sparseDirectoryMatch) {
    parsed.pathname = sparseDirectoryMatch[1];
    return {
      baseUrl: parsed.toString(),
      sparsePath: sparseDirectoryMatch[2],
    };
  }

  parsed.pathname = parsed.pathname.replace(/\/?$/, "/");
  return {
    baseUrl: parsed.toString(),
    sparsePath: fallbackSparsePath.replace(/^\/+/, "").replace(/\/?$/, "/"),
  };
};

const withProxyIfNeeded = (url: URL) => {
  const bucket = getBucketFromUrl(url);
  const shouldProxyBucket = bucket ? isAllowedPipelineBucket(bucket) : false;
  const shouldProxyEdgeBundle = url.host.endsWith(".cloudfront.net") && url.pathname.startsWith("/models/");
  if (shouldProxyBucket || shouldProxyEdgeBundle) {
    const base = `${url.protocol}//${url.host}`;
    const encodedBase = base.replace("://", ":/");
    return `/api/sogs-proxy/${encodedBase}${url.pathname}${url.search}`;
  }
  return url.toString();
};

const derivePipelineArtifacts = (rawSource: string): DerivedPipelineArtifacts | null => {
  const parsed = normalizeUrl(rawSource);
  if (!parsed) {
    return null;
  }
  const baseOrigin = `${parsed.protocol}//${parsed.host}`;

  const buildStandardArtifacts = (
    jobId: string,
    sourceKind: DerivedPipelineArtifacts["sourceKind"],
    sourceLabel: string
  ): DerivedPipelineArtifacts => ({
    sourceKind,
    sourceLabel,
    jobId,
    sourceUrl: parsed.toString(),
    compressedBundle: `${baseOrigin}/compressed/${jobId}/supersplat_bundle/meta.json`,
    colmapBase: `${baseOrigin}/colmap/${jobId}/`,
    gaussianPly: `${baseOrigin}/3dgs/${jobId}/splat.ply`,
    sparsePath: "sparse/0/",
  });

  const manualValidationMatch = parsed.pathname.match(/\/manual-validations\/([^/]+)\/(compressed|repair|colmap)(?:\/|$)/);
  if (manualValidationMatch) {
    const runId = manualValidationMatch[1];
    const sourceKind =
      manualValidationMatch[2] === "colmap" ? "sfm" : manualValidationMatch[2] === "repair" ? "gaussian" : "compressed";
    const sfmInput = resolveSfmInput(rawSource, "sparse/0/");
    return {
      sourceKind,
      sourceLabel:
        sourceKind === "sfm"
          ? "Manual validation COLMAP"
          : sourceKind === "gaussian"
            ? "Manual validation 3DGS"
            : "Manual validation compressed bundle",
      jobId: runId,
      sourceUrl:
        sourceKind === "compressed"
          ? normalizeCompressedBundleUrl(rawSource)?.toString() ?? parsed.toString()
          : sourceKind === "gaussian"
            ? normalizeGaussianAssetUrl(rawSource)?.toString() ?? parsed.toString()
            : sfmInput?.baseUrl ?? parsed.toString(),
      compressedBundle: `${baseOrigin}/manual-validations/${runId}/compressed/supersplat_bundle/meta.json`,
      colmapBase: `${baseOrigin}/manual-validations/${runId}/colmap/`,
      gaussianPly: `${baseOrigin}/manual-validations/${runId}/repair/splat.ply`,
      sparsePath: sfmInput?.sparsePath ?? "sparse/0/",
    };
  }

  const standardCompressedMatch = parsed.pathname.match(/^\/compressed\/([^/]+)\//);
  if (standardCompressedMatch) {
    return {
      ...buildStandardArtifacts(standardCompressedMatch[1], "compressed", "Compressed bundle"),
      sourceUrl: normalizeCompressedBundleUrl(rawSource)?.toString() ?? parsed.toString(),
    };
  }

  const standardGaussianMatch = parsed.pathname.match(/^\/3dgs\/([^/]+)(?:\/|$)/);
  if (standardGaussianMatch) {
    return {
      ...buildStandardArtifacts(standardGaussianMatch[1], "gaussian", "3DGS output"),
      sourceUrl: normalizeGaussianAssetUrl(rawSource)?.toString() ?? parsed.toString(),
      gaussianPly:
        normalizeGaussianAssetUrl(rawSource)?.toString() ?? `${baseOrigin}/3dgs/${standardGaussianMatch[1]}/splat.ply`,
    };
  }

  const standardSfmMatch = parsed.pathname.match(/^\/colmap\/([^/]+)(?:\/|$)/);
  if (standardSfmMatch) {
    const sfmInput = resolveSfmInput(rawSource, "sparse/0/");
    return {
      ...buildStandardArtifacts(standardSfmMatch[1], "sfm", "COLMAP output"),
      sourceUrl: sfmInput?.baseUrl ?? parsed.toString(),
      colmapBase: sfmInput?.baseUrl ?? `${baseOrigin}/colmap/${standardSfmMatch[1]}/`,
      sparsePath: sfmInput?.sparsePath ?? "sparse/0/",
    };
  }

  if (parsed.pathname.includes("/supersplat_bundle/")) {
    return {
      sourceKind: "compressed",
      sourceLabel: "Compressed bundle",
      jobId: null,
      sourceUrl: normalizeCompressedBundleUrl(rawSource)?.toString() ?? parsed.toString(),
      compressedBundle: normalizeCompressedBundleUrl(rawSource)?.toString() ?? parsed.toString(),
      colmapBase: null,
      gaussianPly: null,
      sparsePath: null,
    };
  }

  const genericSfmInput = resolveSfmInput(rawSource, "sparse/0/");
  if (
    genericSfmInput &&
    /(?:^|\/)(?:colmap|sparse\/\d+|(?:cameras|images|points3D)\.txt)(?:\/|$)/.test(parsed.pathname)
  ) {
    return {
      sourceKind: "sfm",
      sourceLabel: "COLMAP output",
      jobId: null,
      sourceUrl: genericSfmInput.baseUrl,
      compressedBundle: null,
      colmapBase: genericSfmInput.baseUrl,
      gaussianPly: null,
      sparsePath: genericSfmInput.sparsePath,
    };
  }

  return null;
};

const buildSfmFileUrls = (baseUrl: string, sparsePath: string) => {
  const resolved = resolveSfmInput(baseUrl, sparsePath);
  if (!resolved) {
    return null;
  }
  const safeSparse = resolved.sparsePath;
  const base = resolved.baseUrl;
  return {
    baseUrl: base,
    sparsePath: safeSparse,
    cameras: `${base}${safeSparse}cameras.txt`,
    images: `${base}${safeSparse}images.txt`,
    points: `${base}${safeSparse}points3D.txt`,
  };
};

const streamTextLines = async (
  resourceUrl: string,
  fetchErrorLabel: string,
  onLine: (line: string) => boolean | void,
  rangeWindowBytes?: number
) => {
  const decoder = new TextDecoder();
  const nextWindowSize = rangeWindowBytes ?? 0;
  let nextByteStart = 0;
  let trailingBuffer = "";
  let shouldContinue = true;
  const parseContentRange = (contentRange: string | null) => {
    if (!contentRange) {
      return null;
    }
    const match = contentRange.match(/^bytes\s+(\d+)-(\d+)\/(\d+|\*)$/i);
    if (!match) {
      return null;
    }
    return {
      end: Number(match[2]),
      total: match[3] === "*" ? null : Number(match[3]),
    };
  };

  while (shouldContinue) {
    const response = await fetch(resourceUrl, {
      headers: rangeWindowBytes
        ? {
            Range: `bytes=${nextByteStart}-${nextByteStart + nextWindowSize - 1}`,
          }
        : undefined,
    });
    if (!response.ok) {
      throw new Error(`${fetchErrorLabel} fetch failed (${response.status})`);
    }

    const contentRange = parseContentRange(response.headers.get("content-range"));
    const reachedEnd =
      !rangeWindowBytes ||
      response.status !== 206 ||
      !contentRange ||
      contentRange.total == null ||
      contentRange.end + 1 >= contentRange.total;

    if (!response.body) {
      const fallbackText = trailingBuffer + (await response.text());
      const lines = fallbackText.split(/\r?\n/);
      for (let index = 0; index < lines.length; index += 1) {
        const isLastLine = index === lines.length - 1;
        if (!reachedEnd && isLastLine) {
          trailingBuffer = lines[index];
          break;
        }
        if (onLine(lines[index]) === false) {
          shouldContinue = false;
          break;
        }
      }
    } else {
      const reader = response.body.getReader();
      let buffer = trailingBuffer;
      trailingBuffer = "";

      try {
        while (shouldContinue) {
          const { value, done } = await reader.read();
          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          let newlineIndex = buffer.indexOf("\n");
          while (newlineIndex !== -1) {
            let line = buffer.slice(0, newlineIndex);
            if (line.endsWith("\r")) {
              line = line.slice(0, -1);
            }
            shouldContinue = onLine(line) !== false;
            buffer = buffer.slice(newlineIndex + 1);
            if (!shouldContinue) {
              break;
            }
            newlineIndex = buffer.indexOf("\n");
          }
        }

        if (shouldContinue) {
          buffer += decoder.decode();
          if (reachedEnd) {
            const trailingLine = buffer.replace(/\r$/, "");
            if (trailingLine) {
              shouldContinue = onLine(trailingLine) !== false;
            }
          } else {
            trailingBuffer = buffer;
          }
        }
      } finally {
        await reader.cancel().catch(() => undefined);
      }
    }

    if (!shouldContinue || reachedEnd) {
      break;
    }

    nextByteStart = contentRange ? contentRange.end + 1 : nextByteStart + nextWindowSize;
  }
};

const finalizeBounds = (count: number, min: [number, number, number], max: [number, number, number]) => {
  if (count === 0) {
    return {
      min: [0, 0, 0] as [number, number, number],
      max: [0, 0, 0] as [number, number, number],
    };
  }

  return { min, max };
};

const loadPoints = async (pointsUrl: string, maxPoints: number) => {
  const positions: number[] = [];
  const colors: number[] = [];
  let count = 0;
  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;

  await streamTextLines(
    pointsUrl,
    "points3D.txt",
    (line) => {
      if (!line || line.startsWith("#")) {
        return true;
      }
      const parts = line.trim().split(/\s+/);
      if (parts.length < 7) {
        return true;
      }
      const x = Number(parts[1]);
      const y = Number(parts[2]);
      const z = Number(parts[3]);
      const r = Number(parts[4]);
      const g = Number(parts[5]);
      const b = Number(parts[6]);
      if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) {
        return true;
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
        return false;
      }
      return true;
    },
    32 * 1024 * 1024
  );

  return {
    positions: new Float32Array(positions),
    colors: new Float32Array(colors),
    count,
    bounds: finalizeBounds(count, [minX, minY, minZ], [maxX, maxY, maxZ]),
  };
};

const loadImages = async (imagesUrl: string, maxCameras: number) => {
  const linePositions: number[] = [];
  let count = 0;
  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;
  let skipNext = false;

  const pushLine = (a: THREE.Vector3, b: THREE.Vector3) => {
    linePositions.push(a.x, a.y, a.z, b.x, b.y, b.z);
  };

  await streamTextLines(
    imagesUrl,
    "images.txt",
    (line) => {
      if (skipNext) {
        skipNext = false;
        return true;
      }
      if (!line || line.startsWith("#")) {
        return true;
      }
      const parts = line.trim().split(/\s+/);
      if (parts.length < 9) {
        return true;
      }

      const qw = Number(parts[1]);
      const qx = Number(parts[2]);
      const qy = Number(parts[3]);
      const qz = Number(parts[4]);
      const tx = Number(parts[5]);
      const ty = Number(parts[6]);
      const tz = Number(parts[7]);

      if (![qw, qx, qy, qz, tx, ty, tz].every(Number.isFinite)) {
        return true;
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
        return false;
      }

      skipNext = true;
      return true;
    },
    8 * 1024 * 1024
  );

  return {
    positions: new Float32Array(linePositions),
    count,
    bounds: finalizeBounds(count, [minX, minY, minZ], [maxX, maxY, maxZ]),
  };
};

const mergeBounds = (a: SfmData["bounds"], b: SfmData["bounds"]) => {
  const min: [number, number, number] = [
    Math.min(a.min[0], b.min[0]),
    Math.min(a.min[1], b.min[1]),
    Math.min(a.min[2], b.min[2]),
  ];
  const max: [number, number, number] = [
    Math.max(a.max[0], b.max[0]),
    Math.max(a.max[1], b.max[1]),
    Math.max(a.max[2], b.max[2]),
  ];
  return { min, max };
};

const SfmCanvas = ({
  data,
  showAxes,
  showCameras,
  pointSize,
  transform,
}: {
  data: SfmData | null;
  showAxes: boolean;
  showCameras: boolean;
  pointSize: number;
  transform: TransformOption;
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const dataGroupRef = useRef<THREE.Group | null>(null);
  const pointsRef = useRef<THREE.Points | null>(null);
  const cameraLinesRef = useRef<THREE.LineSegments | null>(null);
  const axesRef = useRef<THREE.AxesHelper | null>(null);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return undefined;
    }

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#050508");
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(60, 1, 0.01, 1000);
    camera.position.set(1, 1, 2);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.setSize(container.clientWidth, container.clientHeight, false);
    rendererRef.current = renderer;
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controlsRef.current = controls;

    const dataGroup = new THREE.Group();
    scene.add(dataGroup);
    dataGroupRef.current = dataGroup;

    const axes = new THREE.AxesHelper(1);
    axes.visible = showAxes;
    scene.add(axes);
    axesRef.current = axes;

    const resizeObserver = new ResizeObserver(() => {
      if (!rendererRef.current || !cameraRef.current || !containerRef.current) {
        return;
      }
      const { clientWidth, clientHeight } = containerRef.current;
      rendererRef.current.setSize(clientWidth, clientHeight, false);
      cameraRef.current.aspect = clientWidth / Math.max(clientHeight, 1);
      cameraRef.current.updateProjectionMatrix();
    });

    resizeObserver.observe(container);

    const animate = () => {
      if (controlsRef.current) {
        controlsRef.current.update();
      }
      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current);
      }
      frameRef.current = requestAnimationFrame(animate);
    };
    frameRef.current = requestAnimationFrame(animate);

    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
      resizeObserver.disconnect();
      controls.dispose();
      renderer.dispose();
      container.removeChild(renderer.domElement);
      scene.clear();
    };
  }, []);

  useEffect(() => {
    if (!dataGroupRef.current || !sceneRef.current) {
      return;
    }
    const rotation = transformOptions.find((option) => option.value === transform)?.rotation ?? [0, 0, 0];
    dataGroupRef.current.rotation.set(rotation[0], rotation[1], rotation[2]);
  }, [transform]);

  useEffect(() => {
    if (axesRef.current) {
      axesRef.current.visible = showAxes;
    }
  }, [showAxes]);

  useEffect(() => {
    if (!dataGroupRef.current || !sceneRef.current || !cameraRef.current || !controlsRef.current) {
      return;
    }

    if (pointsRef.current) {
      pointsRef.current.geometry.dispose();
      if (Array.isArray(pointsRef.current.material)) {
        pointsRef.current.material.forEach((material) => material.dispose());
      } else {
        pointsRef.current.material.dispose();
      }
      dataGroupRef.current.remove(pointsRef.current);
      pointsRef.current = null;
    }

    if (cameraLinesRef.current) {
      cameraLinesRef.current.geometry.dispose();
      if (Array.isArray(cameraLinesRef.current.material)) {
        cameraLinesRef.current.material.forEach((material) => material.dispose());
      } else {
        cameraLinesRef.current.material.dispose();
      }
      dataGroupRef.current.remove(cameraLinesRef.current);
      cameraLinesRef.current = null;
    }

    if (!data) {
      return;
    }

    const pointGeometry = new THREE.BufferGeometry();
    pointGeometry.setAttribute("position", new THREE.BufferAttribute(data.points, 3));
    pointGeometry.setAttribute("color", new THREE.BufferAttribute(data.colors, 3));

    const pointMaterial = new THREE.PointsMaterial({
      size: pointSize,
      vertexColors: true,
      sizeAttenuation: true,
    });

    const points = new THREE.Points(pointGeometry, pointMaterial);
    dataGroupRef.current.add(points);
    pointsRef.current = points;

    if (data.cameraLines.length > 0) {
      const cameraGeometry = new THREE.BufferGeometry();
      cameraGeometry.setAttribute("position", new THREE.BufferAttribute(data.cameraLines, 3));
      const cameraMaterial = new THREE.LineBasicMaterial({ color: 0xff8a00, transparent: true, opacity: 0.85 });
      const lines = new THREE.LineSegments(cameraGeometry, cameraMaterial);
      lines.visible = showCameras;
      dataGroupRef.current.add(lines);
      cameraLinesRef.current = lines;
    }

    const min = new THREE.Vector3(...data.bounds.min);
    const max = new THREE.Vector3(...data.bounds.max);
    const center = new THREE.Vector3().addVectors(min, max).multiplyScalar(0.5);
    const size = new THREE.Vector3().subVectors(max, min);
    const radius = Math.max(size.length() * 0.5, 0.1);

    const camera = cameraRef.current;
    const distance = radius / Math.tan((camera.fov * Math.PI) / 360);
    camera.near = Math.max(distance / 100, 0.01);
    camera.far = distance * 200;
    camera.position.set(center.x + distance, center.y + distance * 0.6, center.z + distance);
    camera.lookAt(center);
    camera.updateProjectionMatrix();

    controlsRef.current.target.copy(center);
    controlsRef.current.update();

    if (axesRef.current) {
      const axisSize = Math.max(radius * 0.6, 0.5);
      axesRef.current.scale.set(axisSize, axisSize, axisSize);
      axesRef.current.position.copy(center);
    }
  }, [data, pointSize, showCameras]);

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
};

const SupersplatViewport = ({
  defaultUrl,
  normalizeInputUrl,
  onViewerStateChange,
}: SupersplatViewportProps) => {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [activeUrl, setActiveUrl] = useState("");
  const [iframeKey, setIframeKey] = useState(0);

  const normalizeForViewer = useCallback(
    (rawValue: string) => {
      const parsed = normalizeInputUrl ? normalizeInputUrl(rawValue) : normalizeUrl(rawValue);
      if (!parsed) {
        return null;
      }
      return {
        canonicalUrl: parsed.toString(),
        viewerUrl: withProxyIfNeeded(parsed),
      };
    },
    [normalizeInputUrl]
  );

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === "supersplat:firstFrame" && event.source === iframeRef.current?.contentWindow) {
        onViewerStateChange?.("ready");
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [onViewerStateChange]);

  useEffect(() => {
    const normalized = normalizeForViewer(defaultUrl);
    if (!normalized) {
      setActiveUrl("");
      onViewerStateChange?.("invalid");
      return;
    }
    setActiveUrl(normalized.viewerUrl);
    setIframeKey((prev) => prev + 1);
    onViewerStateChange?.("loading");
  }, [defaultUrl, normalizeForViewer, onViewerStateChange]);

  const viewerSrc = useMemo(() => {
    if (!activeUrl) {
      return "";
    }
    const params = new URLSearchParams({
      settings: "/supersplat-viewer/settings.json",
      content: activeUrl,
    });
    return `${VIEWER_BASE}?${params.toString()}`;
  }, [activeUrl]);

  return (
    <>
      {viewerSrc ? (
        <iframe
          key={iframeKey}
          ref={iframeRef}
          src={viewerSrc}
          title="Pipeline viewport"
          style={{ border: "none", width: "100%", height: "100%", display: "block" }}
          allow="xr-spatial-tracking"
        />
      ) : (
        <div style={emptyStateStyles}>Paste a supported pipeline link to load this stage.</div>
      )}
    </>
  );
};

export default function PipelineViewerPage() {
  const [activeTab, setActiveTab] = useState<"sfm" | "gaussian" | "compressed">("compressed");
  const [controlsCollapsed, setControlsCollapsed] = useState(false);
  const [pipelineSourceInput, setPipelineSourceInput] = useState(DEFAULT_COMPRESSED_BUNDLE);
  const [compressedBundleUrl, setCompressedBundleUrl] = useState(DEFAULT_COMPRESSED_BUNDLE);
  const [derivedJobId, setDerivedJobId] = useState<string | null>(null);
  const [derivedSourceLabel, setDerivedSourceLabel] = useState<string | null>("Compressed bundle");
  const [colmapBaseUrl, setColmapBaseUrl] = useState("");
  const [gaussianPlyUrl, setGaussianPlyUrl] = useState("");
  const [sfmSparsePath, setSfmSparsePath] = useState("sparse/0/");
  const [sfmMaxPoints, setSfmMaxPoints] = useState(150000);
  const [sfmMaxCameras, setSfmMaxCameras] = useState(600);
  const [sfmPointSize, setSfmPointSize] = useState(0.02);
  const [sfmTransform, setSfmTransform] = useState<TransformOption>("native");
  const [showAxes, setShowAxes] = useState(true);
  const [showCameras, setShowCameras] = useState(true);
  const [sfmData, setSfmData] = useState<SfmData | null>(null);
  const [sfmStatus, setSfmStatus] = useState("Awaiting data");
  const [sfmError, setSfmError] = useState<string | null>(null);
  const [sfmLoadNonce, setSfmLoadNonce] = useState(0);
  const [gaussianViewerState, setGaussianViewerState] = useState<"idle" | "loading" | "ready" | "invalid">("idle");
  const [compressedViewerState, setCompressedViewerState] = useState<"idle" | "loading" | "ready" | "invalid">("idle");

  const applyDerivedArtifacts = useCallback(
    (result: DerivedPipelineArtifacts | null, rawInput: string) => {
      if (!result) {
        setPipelineSourceInput(rawInput);
        setDerivedJobId(null);
        setDerivedSourceLabel(null);
        return;
      }
      setPipelineSourceInput(result.sourceUrl);
      setDerivedJobId(result.jobId);
      setDerivedSourceLabel(result.sourceLabel);
      setCompressedBundleUrl(result.compressedBundle ?? "");
      setColmapBaseUrl(result.colmapBase ?? "");
      setGaussianPlyUrl(result.gaussianPly ?? "");
      if (result.sparsePath) {
        setSfmSparsePath(result.sparsePath);
      }
      setActiveTab(result.sourceKind);
      if (result.colmapBase) {
        setSfmLoadNonce((value) => value + 1);
      }
    },
    []
  );

  const handleDerive = useCallback((rawInput: string) => {
    const result = derivePipelineArtifacts(rawInput);
    applyDerivedArtifacts(result, rawInput);
  }, [applyDerivedArtifacts]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const searchParams = new URLSearchParams(window.location.search);
    const preloadUrl = searchParams.get("url");
    if (!preloadUrl) {
      return;
    }
    handleDerive(preloadUrl);
  }, [handleDerive]);

  const handleSourceSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    handleDerive(pipelineSourceInput);
  };

  const handleLoadSfm = useCallback(async () => {
    setSfmError(null);
    setSfmStatus("Loading SFM output...");

    const derivedFromInput = derivePipelineArtifacts(pipelineSourceInput);
    const derivedSfmInput = derivedFromInput?.sourceKind === "sfm" ? derivedFromInput : null;
    const effectiveColmapBaseUrl = colmapBaseUrl || derivedSfmInput?.colmapBase || "";
    const effectiveSparsePath = derivedSfmInput?.sparsePath ?? sfmSparsePath;
    const fileUrls = buildSfmFileUrls(effectiveColmapBaseUrl, effectiveSparsePath);
    if (!fileUrls) {
      setSfmError("Enter a valid COLMAP base URL (s3:// or https).");
      setSfmStatus("Failed to load");
      return;
    }

    setColmapBaseUrl(fileUrls.baseUrl);
    setSfmSparsePath(fileUrls.sparsePath);
    if (derivedSfmInput) {
      setDerivedJobId(derivedSfmInput.jobId);
      setDerivedSourceLabel(derivedSfmInput.sourceLabel);
      setActiveTab("sfm");
      setPipelineSourceInput(derivedSfmInput.sourceUrl);
    }

    try {
      const pointsUrl = normalizeUrl(fileUrls.points) ?? new URL(fileUrls.points);

      const parsedPoints = await loadPoints(withProxyIfNeeded(pointsUrl), sfmMaxPoints);

      setSfmData({
        points: parsedPoints.positions,
        colors: parsedPoints.colors,
        cameraLines: new Float32Array(),
        pointCount: parsedPoints.count,
        cameraCount: 0,
        bounds: parsedPoints.bounds,
      });

      setSfmStatus(`Loaded ${parsedPoints.count} points.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setSfmError(message);
      setSfmStatus("Failed to load");
    }
  }, [colmapBaseUrl, pipelineSourceInput, sfmSparsePath, sfmMaxPoints, sfmMaxCameras]);

  useEffect(() => {
    if (activeTab !== "sfm" || sfmLoadNonce === 0 || !colmapBaseUrl) {
      return;
    }
    void handleLoadSfm();
  }, [activeTab, colmapBaseUrl, handleLoadSfm, sfmLoadNonce]);

  const sfmFileUrls = useMemo(() => buildSfmFileUrls(colmapBaseUrl, sfmSparsePath), [colmapBaseUrl, sfmSparsePath]);
  const activeViewerStatus =
    activeTab === "sfm"
      ? sfmError ?? sfmStatus
      : activeTab === "gaussian"
        ? gaussianViewerState === "ready"
          ? "Viewer ready"
          : gaussianViewerState === "loading"
            ? "Loading viewer..."
            : gaussianViewerState === "invalid"
              ? "Paste a valid 3DGS asset URL."
              : "Awaiting 3DGS input"
        : compressedViewerState === "ready"
          ? "Viewer ready"
          : compressedViewerState === "loading"
            ? "Loading viewer..."
            : compressedViewerState === "invalid"
              ? "Paste a valid compressed bundle URL."
              : "Awaiting compressed input";

  return (
    <main style={pageStyles}>
      <div style={viewportStyles} />
      <div style={viewerShellStyles}>
        {activeTab === "sfm" && <SfmCanvas data={sfmData} showAxes={showAxes} showCameras={showCameras} pointSize={sfmPointSize} transform={sfmTransform} />}
        {activeTab === "gaussian" && (
          <SupersplatViewport
            defaultUrl={gaussianPlyUrl}
            normalizeInputUrl={normalizeGaussianAssetUrl}
            onViewerStateChange={setGaussianViewerState}
          />
        )}
        {activeTab === "compressed" && (
          <SupersplatViewport
            defaultUrl={compressedBundleUrl}
            normalizeInputUrl={normalizeCompressedBundleUrl}
            onViewerStateChange={setCompressedViewerState}
          />
        )}
        {activeTab === "sfm" && !sfmData && sfmStatus === "Awaiting data" && (
          <div style={emptyStateStyles}>Resolve a pipeline URL, then load the SfM stage.</div>
        )}
      </div>

      {controlsCollapsed ? (
        <section style={collapsedOverlayStyles}>
          <button
            type="button"
            style={collapsedToggleStyles}
            onClick={() => setControlsCollapsed(false)}
            aria-label="Show pipeline viewer controls"
          >
            Show controls
          </button>
          <p style={{ ...statusPillStyles, margin: 0 }}>{activeViewerStatus}</p>
        </section>
      ) : (
        <>
          <section style={overlayStyles}>
            <div style={glassPanelStyles}>
              <div style={{ display: "grid", gap: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "start" }}>
                  <div style={{ display: "grid", gap: "6px" }}>
                    <p style={labelStyles}>Pipeline Viewer</p>
                    <h1 style={{ margin: 0, fontSize: "1.3rem", letterSpacing: "-0.02em" }}>Paste a pipeline S3 link</h1>
                  </div>
                  <div style={{ display: "flex", alignItems: "start", gap: "10px", flexWrap: "wrap", justifyContent: "end" }}>
                    <p style={statusPillStyles}>{activeViewerStatus}</p>
                    <button
                      type="button"
                      style={collapseButtonStyles}
                      onClick={() => setControlsCollapsed(true)}
                      aria-label="Hide pipeline viewer controls"
                    >
                      Hide controls
                    </button>
                  </div>
                </div>

                <form style={sourceFormStyles} onSubmit={handleSourceSubmit}>
                  <label style={labelStyles} htmlFor="compressed-seed">
                    Pipeline Artifact URL
                  </label>
                  <div style={inputRowStyles}>
                    <input
                      id="compressed-seed"
                      type="text"
                      style={inputStyles}
                      value={pipelineSourceInput}
                      onChange={(event) => setPipelineSourceInput(event.target.value)}
                      placeholder="s3://bucket/path or https://bucket.s3.amazonaws.com/..."
                    />
                    <button type="submit" style={buttonStyles}>
                      Open
                    </button>
                  </div>
                </form>

                <div style={tabListStyles}>
                  <button type="button" style={activeTab === "sfm" ? activeTabButtonStyles : tabButtonStyles} onClick={() => setActiveTab("sfm")}>
                    SfM
                  </button>
                  <button type="button" style={activeTab === "gaussian" ? activeTabButtonStyles : tabButtonStyles} onClick={() => setActiveTab("gaussian")}>
                    3DGS
                  </button>
                  <button type="button" style={activeTab === "compressed" ? activeTabButtonStyles : tabButtonStyles} onClick={() => setActiveTab("compressed")}>
                    SOGS
                  </button>
                </div>

                <div style={metaGridStyles}>
                  <div style={metaCardStyles}>
                    <span style={labelStyles}>Source</span>
                    <span style={metaValueStyles}>{derivedSourceLabel ?? "Not detected"}</span>
                  </div>
                  <div style={metaCardStyles}>
                    <span style={labelStyles}>Job</span>
                    <span style={metaValueStyles}>{derivedJobId ?? "—"}</span>
                  </div>
                </div>

                {activeTab === "sfm" && (
                  <div style={sfmControlsStyles}>
                    <div style={toolbarRowStyles}>
                      <div>
                        <label style={labelStyles} htmlFor="sfm-sparse">
                          Sparse
                        </label>
                        <input
                          id="sfm-sparse"
                          type="text"
                          style={inlineInputStyles}
                          value={sfmSparsePath}
                          onChange={(event) => setSfmSparsePath(event.target.value)}
                        />
                      </div>
                      <div>
                        <label style={labelStyles} htmlFor="sfm-points">
                          Points
                        </label>
                        <input
                          id="sfm-points"
                          type="number"
                          min={1000}
                          style={inlineInputStyles}
                          value={sfmMaxPoints}
                          onChange={(event) => setSfmMaxPoints(Number(event.target.value))}
                        />
                      </div>
                      <div>
                        <label style={labelStyles} htmlFor="sfm-cameras">
                          Cameras
                        </label>
                        <input
                          id="sfm-cameras"
                          type="number"
                          min={10}
                          style={inlineInputStyles}
                          value={sfmMaxCameras}
                          onChange={(event) => setSfmMaxCameras(Number(event.target.value))}
                        />
                      </div>
                      <div>
                        <label style={labelStyles} htmlFor="sfm-size">
                          Size
                        </label>
                        <input
                          id="sfm-size"
                          type="number"
                          step={0.01}
                          min={0.001}
                          style={inlineInputStyles}
                          value={sfmPointSize}
                          onChange={(event) => setSfmPointSize(Number(event.target.value))}
                        />
                      </div>
                    </div>

                    <div style={toolbarRowStyles}>
                      <select
                        value={sfmTransform}
                        onChange={(event) => setSfmTransform(event.target.value as TransformOption)}
                        style={{ ...inlineInputStyles, maxWidth: "180px" }}
                      >
                        {transformOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      <label style={{ ...mutedTextStyles, display: "flex", alignItems: "center", gap: "6px" }}>
                        <input type="checkbox" checked={showAxes} onChange={(event) => setShowAxes(event.target.checked)} />
                        Axes
                      </label>
                      <label style={{ ...mutedTextStyles, display: "flex", alignItems: "center", gap: "6px" }}>
                        <input type="checkbox" checked={showCameras} onChange={(event) => setShowCameras(event.target.checked)} />
                        Cameras
                      </label>
                      <button type="button" style={buttonStyles} onClick={handleLoadSfm}>
                        Load SfM
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>

          <div style={bottomStatusStyles}>
            <p style={{ ...mutedTextStyles, margin: 0 }}>
              {activeTab === "sfm" && sfmFileUrls
                ? `Using ${sfmFileUrls.points} and ${sfmFileUrls.images}`
                : activeViewerStatus}
            </p>
          </div>
        </>
      )}
    </main>
  );
}
