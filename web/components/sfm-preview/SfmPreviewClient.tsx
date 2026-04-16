"use client";

import { startTransition, useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import type {
  SfmPreviewCamera,
  SfmPreviewChunk,
  SfmPreviewInspectorPayload,
} from "../../lib/sfmInspector";
import type { SfmPreviewPageData } from "../../lib/sfmPreview";

type Vec3 = [number, number, number];
type PointColorMode = "chunk" | "source";
type PointSizePreset = "fine" | "balanced" | "bold";

const POINT_SIZES: Record<PointSizePreset, number> = {
  fine: 0.011,
  balanced: 0.016,
  bold: 0.023,
};

function formatNumber(value: number | null): string {
  if (value === null || Number.isNaN(value)) {
    return "Unavailable";
  }
  return new Intl.NumberFormat("en-US").format(value);
}

function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value <= 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  return `${size.toFixed(size >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function hexToRgb01(hex: string): Vec3 {
  const normalized = hex.replace("#", "");
  const value = Number.parseInt(normalized, 16);
  return [((value >> 16) & 255) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255];
}

function buildPointGeometry(positions: number[], colors: number[]) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  geometry.computeBoundingSphere();
  return geometry;
}

function buildFrustumGeometry(cameras: SfmPreviewCamera[]) {
  const positions: number[] = [];
  const colors: number[] = [];

  for (const camera of cameras) {
    const [r, g, b] = hexToRgb01(camera.color);
    const center = camera.position;
    const corners = camera.frustumCorners;
    const faceCenter: Vec3 = [
      (corners[0][0] + corners[1][0] + corners[2][0] + corners[3][0]) / 4,
      (corners[0][1] + corners[1][1] + corners[2][1] + corners[3][1]) / 4,
      (corners[0][2] + corners[1][2] + corners[2][2] + corners[3][2]) / 4,
    ];

    const edges: Array<[Vec3, Vec3]> = [
      [center, corners[0]],
      [center, corners[1]],
      [center, corners[2]],
      [center, corners[3]],
      [corners[0], corners[1]],
      [corners[1], corners[2]],
      [corners[2], corners[3]],
      [corners[3], corners[0]],
      [center, faceCenter],
    ];

    for (const [start, end] of edges) {
      positions.push(start[0], start[1], start[2], end[0], end[1], end[2]);
      colors.push(r, g, b, r, g, b);
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  geometry.computeBoundingSphere();
  return geometry;
}

function buildTrajectoryGeometry(cameras: SfmPreviewCamera[]) {
  const ordered = [...cameras].sort((left, right) => left.imageId - right.imageId);
  const positions: number[] = [];
  for (let index = 1; index < ordered.length; index += 1) {
    const start = ordered[index - 1].position;
    const end = ordered[index].position;
    positions.push(start[0], start[1], start[2], end[0], end[1], end[2]);
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.computeBoundingSphere();
  return geometry;
}

function buildBoundsGeometry(bounds: NonNullable<SfmPreviewChunk["bounds"]>) {
  const { min, max } = bounds;
  const corners: Vec3[] = [
    [min[0], min[1], min[2]],
    [max[0], min[1], min[2]],
    [max[0], max[1], min[2]],
    [min[0], max[1], min[2]],
    [min[0], min[1], max[2]],
    [max[0], min[1], max[2]],
    [max[0], max[1], max[2]],
    [min[0], max[1], max[2]],
  ];
  const edges = [
    [0, 1],
    [1, 2],
    [2, 3],
    [3, 0],
    [4, 5],
    [5, 6],
    [6, 7],
    [7, 4],
    [0, 4],
    [1, 5],
    [2, 6],
    [3, 7],
  ];

  const positions: number[] = [];
  for (const [startIndex, endIndex] of edges) {
    const start = corners[startIndex];
    const end = corners[endIndex];
    positions.push(start[0], start[1], start[2], end[0], end[1], end[2]);
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.computeBoundingSphere();
  return geometry;
}

function PointLayer({
  positions,
  colors,
  size,
  opacity,
}: {
  positions: number[];
  colors: number[];
  size: number;
  opacity: number;
}) {
  const geometry = useMemo(() => buildPointGeometry(positions, colors), [colors, positions]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  if (!positions.length) {
    return null;
  }

  return (
    <points geometry={geometry}>
      <pointsMaterial size={size} sizeAttenuation vertexColors transparent opacity={opacity} />
    </points>
  );
}

function FrustumLayer({ cameras }: { cameras: SfmPreviewCamera[] }) {
  const geometry = useMemo(() => buildFrustumGeometry(cameras), [cameras]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  if (!cameras.length) {
    return null;
  }

  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial vertexColors transparent opacity={0.26} />
    </lineSegments>
  );
}

function TrajectoryLayer({ cameras }: { cameras: SfmPreviewCamera[] }) {
  const geometry = useMemo(() => buildTrajectoryGeometry(cameras), [cameras]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  if (cameras.length < 2) {
    return null;
  }

  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial color="#f8fafc" transparent opacity={0.32} />
    </lineSegments>
  );
}

function ChunkBoundsLayer({ chunk }: { chunk: SfmPreviewChunk | null }) {
  const geometry = useMemo(() => {
    if (!chunk?.bounds) {
      return null;
    }
    return buildBoundsGeometry(chunk.bounds);
  }, [chunk]);

  useEffect(
    () => () => {
      geometry?.dispose();
    },
    [geometry],
  );

  if (!chunk?.bounds || !geometry) {
    return null;
  }

  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial color={chunk.color} transparent opacity={0.9} />
    </lineSegments>
  );
}

function chunkTagStyle(active: boolean) {
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    borderRadius: 999,
    padding: "8px 12px",
    border: active ? "1px solid rgba(248,250,252,0.34)" : "1px solid rgba(148,163,184,0.14)",
    background: active ? "rgba(248,250,252,0.12)" : "rgba(15,23,42,0.72)",
    color: "#f8fafc",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
  } as const;
}

function toggleStyle(active: boolean) {
  return {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 999,
    padding: "9px 12px",
    border: active ? "1px solid rgba(244,114,182,0.45)" : "1px solid rgba(148,163,184,0.14)",
    background: active ? "rgba(244,114,182,0.16)" : "rgba(15,23,42,0.72)",
    color: active ? "#fbcfe8" : "#cbd5e1",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
  } as const;
}

function visibleLabel(chunk: SfmPreviewChunk | null) {
  return chunk ? `${chunk.label} isolated` : "All chunks visible";
}

export default function SfmPreviewClient({ pageData }: { pageData: SfmPreviewPageData }) {
  const [preview, setPreview] = useState<SfmPreviewInspectorPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeChunkIndex, setActiveChunkIndex] = useState<number | null>(null);
  const [pointColorMode, setPointColorMode] = useState<PointColorMode>("chunk");
  const [pointSizePreset, setPointSizePreset] = useState<PointSizePreset>("fine");
  const [showFrustums, setShowFrustums] = useState(true);
  const [showCameras, setShowCameras] = useState(true);
  const [showTrajectory, setShowTrajectory] = useState(true);
  const [showGrid, setShowGrid] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadPreview() {
      try {
        const response = await fetch("/api/sfm-preview", { cache: "no-store" });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload?.error || "Failed to fetch SfM preview data");
        }

        if (!cancelled) {
          startTransition(() => {
            setPreview(payload);
            setError(null);
          });
        }
      } catch (fetchError) {
        if (!cancelled) {
          setError(fetchError instanceof Error ? fetchError.message : "Failed to fetch SfM preview data");
        }
      }
    }

    loadPreview();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedChunk = useMemo(
    () => preview?.chunks.find((chunk) => chunk.index === activeChunkIndex) ?? null,
    [activeChunkIndex, preview],
  );

  const visibleData = useMemo(() => {
    if (!preview) {
      return null;
    }

    const activeColors = pointColorMode === "chunk" ? preview.chunkPointColors : preview.colors;

    if (activeChunkIndex === null) {
      return {
        pointPositions: preview.positions,
        pointColors: activeColors,
        cameras: preview.cameras,
        pointCount: preview.positions.length / 3,
      };
    }

    const pointPositions: number[] = [];
    const pointColors: number[] = [];

    for (let index = 0; index < preview.pointChunkIndexes.length; index += 1) {
      if (preview.pointChunkIndexes[index] !== activeChunkIndex) {
        continue;
      }

      const offset = index * 3;
      pointPositions.push(
        preview.positions[offset],
        preview.positions[offset + 1],
        preview.positions[offset + 2],
      );
      pointColors.push(activeColors[offset], activeColors[offset + 1], activeColors[offset + 2]);
    }

    return {
      pointPositions,
      pointColors,
      cameras: preview.cameras.filter((camera) => camera.chunkIndexes.includes(activeChunkIndex)),
      pointCount: pointPositions.length / 3,
    };
  }, [activeChunkIndex, pointColorMode, preview]);

  const viewerUrl = preview?.gaussianBundleUrl
    ? `/sogs-viewer?url=${encodeURIComponent(preview.gaussianBundleUrl)}`
    : null;

  return (
    <main
      style={{
        minHeight: "100vh",
        background:
          "radial-gradient(circle at top left, rgba(251,146,60,0.18), transparent 30%), radial-gradient(circle at top right, rgba(56,189,248,0.12), transparent 26%), linear-gradient(180deg, #09111a 0%, #05080d 100%)",
        color: "#f8fafc",
        padding: "28px 22px 48px",
      }}
    >
      <div style={{ maxWidth: 1480, margin: "0 auto", display: "grid", gap: 22 }}>
        <section
          style={{
            display: "grid",
            gap: 18,
            border: "1px solid rgba(148,163,184,0.16)",
            borderRadius: 28,
            padding: "28px 30px",
            background: "rgba(7, 14, 23, 0.82)",
            boxShadow: "0 28px 72px rgba(0,0,0,0.34)",
          }}
        >
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center" }}>
            <span
              style={{
                padding: "7px 11px",
                borderRadius: 999,
                background: "rgba(249,115,22,0.16)",
                color: "#fdba74",
                fontSize: 13,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
              }}
            >
              Verified completed SfM run
            </span>
            <span
              style={{
                padding: "7px 11px",
                borderRadius: 999,
                background: "rgba(52,211,153,0.16)",
                color: "#86efac",
                fontSize: 13,
              }}
            >
              {pageData.artifact.subsetName}
            </span>
            <span
              style={{
                padding: "7px 11px",
                borderRadius: 999,
                background: "rgba(56,189,248,0.14)",
                color: "#7dd3fc",
                fontSize: 13,
              }}
            >
              COLMAP inspector
            </span>
          </div>

          <div style={{ display: "grid", gap: 10 }}>
            <h1 style={{ margin: 0, fontSize: "clamp(2rem, 3.6vw, 3.4rem)", lineHeight: 1.02 }}>
              2000 Rung Ladder SfM Inspector
            </h1>
            <p style={{ margin: 0, maxWidth: 1040, color: "#cbd5e1", fontSize: 16, lineHeight: 1.68 }}>
              This artifact only published raw COLMAP output, so the repo&apos;s gaussian viewers cannot render it yet.
              The existing bundle-backed routes are{" "}
              <a href="/sogs-viewer" style={{ color: "#7dd3fc" }}>
                /sogs-viewer
              </a>{" "}
              and{" "}
              <a href="/sogs-migrated-viewer" style={{ color: "#7dd3fc" }}>
                /sogs-migrated-viewer
              </a>
              , but they need a <code>supersplat_bundle/meta.json</code> that is not present under{" "}
              <code>{pageData.artifact.jobName}</code>. This page renders the full sparse scene, camera centers, camera
              frustums, and planner chunk structure directly from the verified COLMAP files instead.
            </p>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 12,
            }}
          >
            {[
              ["Sparse points", formatNumber(pageData.exactPointCount)],
              ["Registered images", formatNumber(pageData.registeredImageCount)],
              ["Planner chunks", formatNumber(pageData.chunkCount)],
              ["Created", formatDate(pageData.artifact.createdAt)],
              ["Completed", formatDate(pageData.artifact.completedAt)],
              ["Bundle viewer", preview?.gaussianBundleUrl ? "Available" : "Not published"],
            ].map(([label, value]) => (
              <div
                key={label}
                style={{
                  padding: "14px 16px",
                  borderRadius: 20,
                  border: "1px solid rgba(148,163,184,0.14)",
                  background: "rgba(15, 23, 42, 0.62)",
                }}
              >
                <div style={{ color: "#94a3b8", fontSize: 13 }}>{label}</div>
                <div style={{ marginTop: 6, fontSize: 20, fontWeight: 600 }}>{value}</div>
              </div>
            ))}
          </div>

          <div style={{ display: "grid", gap: 8, color: "#94a3b8", fontSize: 14 }}>
            <div>
              <strong style={{ color: "#e2e8f0" }}>Output S3 URI:</strong>{" "}
              <code>{pageData.artifact.outputS3Uri}</code>
            </div>
            <div>
              <strong style={{ color: "#e2e8f0" }}>Source ZIP:</strong>{" "}
              <code>{pageData.artifact.sourceZipS3Uri}</code>
            </div>
            <div>
              <strong style={{ color: "#e2e8f0" }}>Planner:</strong> {pageData.planner || "Unavailable"} with signed
              preview-side download links backed by verified S3 reads.
            </div>
            {viewerUrl ? (
              <div>
                <strong style={{ color: "#e2e8f0" }}>Gaussian viewer:</strong>{" "}
                <a href={viewerUrl} style={{ color: "#7dd3fc" }}>
                  Open this run in /sogs-viewer
                </a>
              </div>
            ) : (
              <div>
                <strong style={{ color: "#e2e8f0" }}>Gaussian viewer:</strong> No bundle exists under this artifact
                prefix, so this page stays in COLMAP mode.
              </div>
            )}
          </div>
        </section>

        <section
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 2.15fr) minmax(360px, 0.95fr)",
            gap: 20,
            alignItems: "start",
          }}
        >
          <div
            style={{
              display: "grid",
              gap: 16,
              borderRadius: 28,
              border: "1px solid rgba(148,163,184,0.16)",
              background: "rgba(6, 12, 18, 0.84)",
              overflow: "hidden",
              boxShadow: "0 24px 70px rgba(0,0,0,0.28)",
            }}
          >
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 10,
                justifyContent: "space-between",
                alignItems: "center",
                padding: "18px 20px 0",
              }}
            >
              <div style={{ display: "grid", gap: 4 }}>
                <strong style={{ fontSize: 18 }}>{visibleLabel(selectedChunk)}</strong>
                <span style={{ color: "#94a3b8", fontSize: 14 }}>
                  {visibleData
                    ? `${formatNumber(visibleData.pointCount)} sampled sparse points, ${formatNumber(
                        visibleData.cameras.length,
                      )} camera poses`
                    : "Loading sparse points and camera poses"}
                </span>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                <button type="button" style={toggleStyle(showFrustums)} onClick={() => setShowFrustums((value) => !value)}>
                  Frustums
                </button>
                <button type="button" style={toggleStyle(showCameras)} onClick={() => setShowCameras((value) => !value)}>
                  Cameras
                </button>
                <button
                  type="button"
                  style={toggleStyle(showTrajectory)}
                  onClick={() => setShowTrajectory((value) => !value)}
                >
                  Trajectory
                </button>
                <button type="button" style={toggleStyle(showGrid)} onClick={() => setShowGrid((value) => !value)}>
                  Grid
                </button>
              </div>
            </div>

            <div style={{ minHeight: 760 }}>
              {visibleData ? (
                <Canvas camera={{ position: [2.35, 1.8, 2.55], near: 0.01, far: 60 }}>
                  <color attach="background" args={["#05080d"]} />
                  <ambientLight intensity={0.55} />
                  <directionalLight position={[3, 4, 2]} intensity={0.9} />
                  {showGrid ? <gridHelper args={[5, 16, "#243041", "#131b27"]} /> : null}
                  <axesHelper args={[0.72]} />
                  <PointLayer
                    positions={visibleData.pointPositions}
                    colors={visibleData.pointColors}
                    size={POINT_SIZES[pointSizePreset]}
                    opacity={0.93}
                  />
                  {showTrajectory ? <TrajectoryLayer cameras={visibleData.cameras} /> : null}
                  {showFrustums ? <FrustumLayer cameras={visibleData.cameras} /> : null}
                  {showCameras ? (
                    <PointLayer
                      positions={visibleData.cameras.flatMap((camera) => camera.position)}
                      colors={visibleData.cameras.flatMap((camera) => hexToRgb01(camera.color))}
                      size={0.035}
                      opacity={0.98}
                    />
                  ) : null}
                  <ChunkBoundsLayer chunk={selectedChunk} />
                  <OrbitControls enableDamping dampingFactor={0.08} />
                </Canvas>
              ) : (
                <div
                  style={{
                    minHeight: 760,
                    display: "grid",
                    placeItems: "center",
                    padding: 24,
                    color: error ? "#fca5a5" : "#cbd5e1",
                    textAlign: "center",
                  }}
                >
                  <div style={{ display: "grid", gap: 10 }}>
                    <strong style={{ fontSize: 18 }}>{error ? "Inspector load failed" : "Loading COLMAP inspector"}</strong>
                    <span style={{ maxWidth: 560, lineHeight: 1.6 }}>
                      {error ||
                        "Fetching frames.txt, cameras.txt, the chunk planner manifest, and a sparse point sample from S3."}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          <aside style={{ display: "grid", gap: 16, alignContent: "start" }}>
            <div
              style={{
                borderRadius: 24,
                border: "1px solid rgba(148,163,184,0.16)",
                background: "rgba(10, 17, 27, 0.88)",
                padding: 22,
                display: "grid",
                gap: 16,
              }}
            >
              <div style={{ display: "grid", gap: 8 }}>
                <h2 style={{ margin: 0, fontSize: 20 }}>Scene controls</h2>
                <p style={{ margin: 0, color: "#94a3b8", lineHeight: 1.6 }}>
                  Switch between chunk coloring and the source RGB sample, then isolate a planner chunk to make the
                  ladder camera coverage easier to read.
                </p>
              </div>

              <div style={{ display: "grid", gap: 10 }}>
                <div style={{ color: "#94a3b8", fontSize: 13, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Point color
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button
                    type="button"
                    style={toggleStyle(pointColorMode === "chunk")}
                    onClick={() => setPointColorMode("chunk")}
                  >
                    Chunk
                  </button>
                  <button
                    type="button"
                    style={toggleStyle(pointColorMode === "source")}
                    onClick={() => setPointColorMode("source")}
                  >
                    Source RGB
                  </button>
                </div>
              </div>

              <div style={{ display: "grid", gap: 10 }}>
                <div style={{ color: "#94a3b8", fontSize: 13, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Point size
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {(["fine", "balanced", "bold"] as PointSizePreset[]).map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      style={toggleStyle(pointSizePreset === preset)}
                      onClick={() => setPointSizePreset(preset)}
                    >
                      {preset}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ display: "grid", gap: 10 }}>
                <div style={{ color: "#94a3b8", fontSize: 13, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Chunk filter
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button
                    type="button"
                    style={chunkTagStyle(activeChunkIndex === null)}
                    onClick={() => setActiveChunkIndex(null)}
                  >
                    All chunks
                  </button>
                  {preview?.chunks.map((chunk) => (
                    <button
                      key={chunk.index}
                      type="button"
                      style={chunkTagStyle(activeChunkIndex === chunk.index)}
                      onClick={() => setActiveChunkIndex(chunk.index)}
                    >
                      <span
                        style={{
                          width: 10,
                          height: 10,
                          borderRadius: 999,
                          background: chunk.color,
                          boxShadow: `0 0 18px ${chunk.color}`,
                        }}
                      />
                      {chunk.label}
                    </button>
                  ))}
                </div>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
                  gap: 10,
                }}
              >
                <div
                  style={{
                    padding: "12px 14px",
                    borderRadius: 18,
                    background: "rgba(15, 23, 42, 0.7)",
                    border: "1px solid rgba(148,163,184,0.14)",
                  }}
                >
                  <div style={{ color: "#94a3b8", fontSize: 12 }}>Visible points</div>
                  <div style={{ marginTop: 4, fontSize: 18, fontWeight: 700 }}>
                    {formatNumber(visibleData?.pointCount ?? null)}
                  </div>
                </div>
                <div
                  style={{
                    padding: "12px 14px",
                    borderRadius: 18,
                    background: "rgba(15, 23, 42, 0.7)",
                    border: "1px solid rgba(148,163,184,0.14)",
                  }}
                >
                  <div style={{ color: "#94a3b8", fontSize: 12 }}>Visible cameras</div>
                  <div style={{ marginTop: 4, fontSize: 18, fontWeight: 700 }}>
                    {formatNumber(visibleData?.cameras.length ?? null)}
                  </div>
                </div>
                <div
                  style={{
                    padding: "12px 14px",
                    borderRadius: 18,
                    background: "rgba(15, 23, 42, 0.7)",
                    border: "1px solid rgba(148,163,184,0.14)",
                  }}
                >
                  <div style={{ color: "#94a3b8", fontSize: 12 }}>Sampled ranges</div>
                  <div style={{ marginTop: 4, fontSize: 18, fontWeight: 700 }}>
                    {formatNumber(preview?.sampledRanges ?? null)}
                  </div>
                </div>
              </div>
            </div>

            <div
              style={{
                borderRadius: 24,
                border: "1px solid rgba(148,163,184,0.16)",
                background: "rgba(10, 17, 27, 0.88)",
                padding: 22,
                display: "grid",
                gap: 12,
              }}
            >
              <h2 style={{ margin: 0, fontSize: 20 }}>Selected chunk</h2>
              {selectedChunk ? (
                <>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span
                      style={{
                        width: 12,
                        height: 12,
                        borderRadius: 999,
                        background: selectedChunk.color,
                        boxShadow: `0 0 18px ${selectedChunk.color}`,
                      }}
                    />
                    <strong style={{ fontSize: 18 }}>{selectedChunk.label}</strong>
                  </div>
                  <div style={{ display: "grid", gap: 8, color: "#cbd5e1", fontSize: 14 }}>
                    <div>Cameras in view: {formatNumber(visibleData?.cameras.length ?? null)}</div>
                    <div>Core images: {formatNumber(selectedChunk.coreCount)}</div>
                    <div>Overlap images: {formatNumber(selectedChunk.overlapCount)}</div>
                    <div>Shared camera poses: {formatNumber(selectedChunk.sharedCount)}</div>
                  </div>
                  <p style={{ margin: 0, color: "#94a3b8", lineHeight: 1.6 }}>
                    The inspector box wraps the chunk&apos;s visible camera centers and frustum extents so you can read
                    its footprint without the full reconstruction clutter.
                  </p>
                </>
              ) : (
                <p style={{ margin: 0, color: "#94a3b8", lineHeight: 1.6 }}>
                  All planner chunks are visible. Pick a chunk above to isolate its camera coverage and tighten the
                  bounds box around that section of the ladder capture.
                </p>
              )}
            </div>

            <div
              style={{
                borderRadius: 24,
                border: "1px solid rgba(148,163,184,0.16)",
                background: "rgba(10, 17, 27, 0.88)",
                padding: 22,
                display: "grid",
                gap: 10,
              }}
            >
              <h2 style={{ margin: 0, fontSize: 20 }}>Artifact status</h2>
              <div style={{ display: "grid", gap: 8, color: "#e2e8f0", fontSize: 14 }}>
                <div>Sampled points: {formatNumber(preview?.sampledPointCount ?? null)}</div>
                <div>Source point file: {preview ? formatBytes(preview.sourceSizeBytes) : "Loading…"}</div>
                <div>Per-range read: {preview ? formatBytes(preview.sampleWindowBytes) : "Loading…"}</div>
                <div>Registered camera poses: {formatNumber(preview?.cameras.length ?? null)}</div>
              </div>
              <p style={{ margin: 0, color: "#94a3b8", lineHeight: 1.6 }}>
                This is the fullest viewer possible for the published artifact. There is no gaussian compression output
                under this run yet, so colored gaussians can&apos;t be shown from S3 for this exact ladder job.
              </p>
            </div>

            <div
              style={{
                borderRadius: 24,
                border: "1px solid rgba(148,163,184,0.16)",
                background: "rgba(10, 17, 27, 0.88)",
                padding: 22,
                display: "grid",
                gap: 14,
              }}
            >
              <h2 style={{ margin: 0, fontSize: 20 }}>Verified artifact links</h2>
              {pageData.links.map((link) => (
                <a
                  key={link.key}
                  href={link.signedUrl}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    display: "grid",
                    gap: 6,
                    textDecoration: "none",
                    color: "#f8fafc",
                    padding: "14px 16px",
                    borderRadius: 18,
                    background: "rgba(15, 23, 42, 0.7)",
                    border: "1px solid rgba(148,163,184,0.14)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                    <strong>{link.label}</strong>
                    <span style={{ color: link.verified ? "#86efac" : "#fda4af", fontSize: 13 }}>
                      {link.verified ? "Verified" : "Unavailable"}
                    </span>
                  </div>
                  <span style={{ color: "#cbd5e1", fontSize: 13 }}>{formatBytes(link.sizeBytes)}</span>
                  <code
                    style={{
                      color: "#94a3b8",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {link.s3Uri}
                  </code>
                </a>
              ))}
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}
