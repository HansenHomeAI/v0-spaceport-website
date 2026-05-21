"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import type { SfmPreviewPayload } from "../../lib/sfmPreview";
import "./sfm-preview.css";

type PointColorMode = "source" | "height" | "chunk";

const QUALITY_OPTIONS = [
  { label: "Fast", value: 18_000, pointSize: 0.008 },
  { label: "Quality", value: 80_000, pointSize: 0.005 },
  { label: "Dense", value: 140_000, pointSize: 0.003 },
];

function formatNumber(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "0";
  }
  return new Intl.NumberFormat("en-US").format(value);
}

function makeGeometry(positions: number[], colors?: number[]) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  if (colors) {
    geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  }
  geometry.computeBoundingSphere();
  return geometry;
}

function makeDiscTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 64;
  const context = canvas.getContext("2d");
  if (!context) {
    return null;
  }
  const gradient = context.createRadialGradient(32, 32, 0, 32, 32, 30);
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.62, "rgba(255,255,255,0.98)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, 64, 64);
  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

function makeHeightColors(positions: number[]) {
  const colors: number[] = [];
  let minY = Number.POSITIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  for (let index = 1; index < positions.length; index += 3) {
    minY = Math.min(minY, positions[index]);
    maxY = Math.max(maxY, positions[index]);
  }
  const span = Math.max(maxY - minY, 0.001);
  for (let index = 1; index < positions.length; index += 3) {
    const t = Math.min(1, Math.max(0, (positions[index] - minY) / span));
    colors.push(0.16 + t * 0.78, 0.48 + t * 0.34, 0.72 - t * 0.52);
  }
  return colors;
}

function filterPointCloud(payload: SfmPreviewPayload, showOutliers: boolean) {
  if (showOutliers) {
    return {
      positions: payload.positions,
      colors: payload.colors,
      chunkColors: payload.chunkColors,
      pointCount: Math.floor(payload.positions.length / 3),
    };
  }

  const positions: number[] = [];
  const colors: number[] = [];
  const chunkColors: number[] = [];
  for (let index = 0; index < payload.positions.length; index += 3) {
    const pointIndex = index / 3;
    const x = payload.positions[index];
    const y = payload.positions[index + 1];
    const z = payload.positions[index + 2];
    const error = payload.pointErrors[pointIndex];
    const trackLength = payload.pointTrackLengths[pointIndex] || 0;
    if (Math.max(Math.abs(x), Math.abs(y), Math.abs(z)) > 2.15) {
      continue;
    }
    if (trackLength < 3 || (Number.isFinite(error) && error > 5)) {
      continue;
    }
    positions.push(x, y, z);
    colors.push(payload.colors[index], payload.colors[index + 1], payload.colors[index + 2]);
    chunkColors.push(payload.chunkColors[index], payload.chunkColors[index + 1], payload.chunkColors[index + 2]);
  }
  return { positions, colors, chunkColors, pointCount: Math.floor(positions.length / 3) };
}

function PointLayer({
  positions,
  colors,
  size,
  opacity = 1,
}: {
  positions: number[];
  colors?: number[];
  size: number;
  opacity?: number;
}) {
  const geometry = useMemo(() => makeGeometry(positions, colors), [colors, positions]);
  const discTexture = useMemo(() => makeDiscTexture(), []);

  useEffect(() => () => geometry.dispose(), [geometry]);
  useEffect(() => () => discTexture?.dispose(), [discTexture]);

  if (!positions.length) {
    return null;
  }

  return (
    <points geometry={geometry}>
      <pointsMaterial
        vertexColors={Boolean(colors)}
        color={colors ? undefined : "#f6c85f"}
        size={size}
        sizeAttenuation
        map={discTexture || undefined}
        alphaTest={0.18}
        transparent
        opacity={opacity}
        depthWrite
      />
    </points>
  );
}

function LineLayer({
  positions,
  color = "#e8edf5",
  opacity = 0.42,
}: {
  positions: number[];
  color?: string;
  opacity?: number;
}) {
  const geometry = useMemo(() => makeGeometry(positions), [positions]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  if (positions.length < 6) {
    return null;
  }

  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial color={color} transparent opacity={opacity} depthWrite={false} />
    </lineSegments>
  );
}

function CameraFrustums({ cameras, visible }: { cameras: SfmPreviewPayload["cameras"]; visible: boolean }) {
  const positions = useMemo(() => {
    if (!visible || cameras.length === 0) {
      return [];
    }
    const output: number[] = [];
    const step = Math.max(1, Math.ceil(cameras.length / 90));
    const size = 0.019;
    for (let index = 0; index < cameras.length; index += step) {
      const camera = cameras[index];
      const origin = new THREE.Vector3(...camera.position);
      const forward = new THREE.Vector3(...camera.forward).normalize();
      const right = new THREE.Vector3(...camera.right).normalize();
      const up = new THREE.Vector3(...camera.up).normalize();
      const center = origin.clone().add(forward.multiplyScalar(size * 1.7));
      const halfWidth = size * 0.95;
      const halfHeight = size * 0.62;
      const corners = [
        center.clone().add(right.clone().multiplyScalar(-halfWidth)).add(up.clone().multiplyScalar(-halfHeight)),
        center.clone().add(right.clone().multiplyScalar(halfWidth)).add(up.clone().multiplyScalar(-halfHeight)),
        center.clone().add(right.clone().multiplyScalar(halfWidth)).add(up.clone().multiplyScalar(halfHeight)),
        center.clone().add(right.clone().multiplyScalar(-halfWidth)).add(up.clone().multiplyScalar(halfHeight)),
      ];
      for (const corner of corners) {
        output.push(...origin.toArray(), ...corner.toArray());
      }
      for (let cornerIndex = 0; cornerIndex < corners.length; cornerIndex += 1) {
        output.push(...corners[cornerIndex].toArray(), ...corners[(cornerIndex + 1) % corners.length].toArray());
      }
    }
    return output;
  }, [cameras, visible]);

  const geometry = useMemo(() => makeGeometry(positions), [positions]);
  useEffect(() => () => geometry.dispose(), [geometry]);

  if (!positions.length) {
    return null;
  }
  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial color="#5eead4" transparent opacity={0.26} depthWrite={false} />
    </lineSegments>
  );
}

function buildTrajectory(cameras: SfmPreviewPayload["cameras"]) {
  const positions: number[] = [];
  const ordered = [...cameras].sort((left, right) => left.imageId - right.imageId);
  for (let index = 1; index < ordered.length; index += 1) {
    positions.push(...ordered[index - 1].position, ...ordered[index].position);
  }
  return positions;
}

function SfmScene({
  payload,
  pointData,
  pointColorMode,
  showCameras,
  showTrajectory,
  showGrid,
  pointSize,
}: {
  payload: SfmPreviewPayload;
  pointData: ReturnType<typeof filterPointCloud>;
  pointColorMode: PointColorMode;
  showCameras: boolean;
  showTrajectory: boolean;
  showGrid: boolean;
  pointSize: number;
}) {
  const heightColors = useMemo(() => makeHeightColors(pointData.positions), [pointData.positions]);
  const pointColors =
    pointColorMode === "chunk" ? pointData.chunkColors : pointColorMode === "height" ? heightColors : pointData.colors;
  const cameraPositions = useMemo(() => payload.cameras.flatMap((camera) => camera.position), [payload.cameras]);
  const trajectory = useMemo(() => buildTrajectory(payload.cameras), [payload.cameras]);

  return (
    <>
      <color attach="background" args={["#050608"]} />
      <fog attach="fog" args={["#050608", 5.2, 9.5]} />
      <ambientLight intensity={0.62} />
      <directionalLight position={[3, 4, 3]} intensity={0.75} />
      {showGrid ? <gridHelper args={[4, 10, "#1f2c3a", "#0d131b"]} /> : null}
      <PointLayer positions={pointData.positions} colors={pointColors} size={pointSize} opacity={1} />
      {showTrajectory ? <LineLayer positions={trajectory} color="#94a3b8" opacity={0.2} /> : null}
      <CameraFrustums cameras={payload.cameras} visible={showCameras} />
      {showCameras ? (
        <PointLayer positions={cameraPositions} size={Math.max(pointSize * 1.4, 0.005)} opacity={0.78} />
      ) : null}
      <OrbitControls enableDamping dampingFactor={0.08} makeDefault />
    </>
  );
}

export default function SfmPreviewClient({
  initialUrl,
  initialMaxPoints = 18_000,
  initialDebugSeams = false,
}: {
  initialUrl: string;
  initialMaxPoints?: number;
  initialDebugSeams?: boolean;
}) {
  const [inputUrl, setInputUrl] = useState(initialUrl);
  const [activeUrl, setActiveUrl] = useState(initialUrl);
  const [maxPoints, setMaxPoints] = useState(initialMaxPoints);
  const [payload, setPayload] = useState<SfmPreviewPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [panelCollapsed, setPanelCollapsed] = useState(true);
  const [pointColorMode, setPointColorMode] = useState<PointColorMode>("source");
  const [showCameras, setShowCameras] = useState(true);
  const [showTrajectory, setShowTrajectory] = useState(false);
  const [showGrid, setShowGrid] = useState(false);
  const [showOutliers, setShowOutliers] = useState(false);
  const [showSeamDebug, setShowSeamDebug] = useState(initialDebugSeams);
  const [pointSize, setPointSize] = useState(() => {
    const selected = QUALITY_OPTIONS.find((option) => option.value === initialMaxPoints);
    return selected?.pointSize ?? (initialMaxPoints >= 100_000 ? 0.003 : initialMaxPoints >= 60_000 ? 0.005 : 0.008);
  });

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetch(
      `/api/sfm-preview?url=${encodeURIComponent(activeUrl)}&maxPoints=${maxPoints}&debugSeams=${
        showSeamDebug ? "1" : "0"
      }`,
      {
      cache: "no-store",
      signal: controller.signal,
      },
    )
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data?.error || `HTTP ${response.status}`);
        }
        setPayload(data as SfmPreviewPayload);
      })
      .catch((fetchError: Error) => {
        if (fetchError.name !== "AbortError") {
          setPayload(null);
          setError(fetchError.message || "Preview load failed.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [activeUrl, maxPoints, showSeamDebug]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextUrl = inputUrl.trim();
    if (nextUrl) {
      setActiveUrl(nextUrl);
    }
  };

  const pointData = useMemo(
    () =>
      payload
        ? filterPointCloud(payload, showOutliers)
        : { positions: [], colors: [], chunkColors: [], pointCount: 0 },
    [payload, showOutliers],
  );
  const selectedQuality = QUALITY_OPTIONS.find((option) => option.value === maxPoints) || QUALITY_OPTIONS[0];

  return (
    <main className="sfm-preview-shell">
      <Canvas className="sfm-preview-canvas" camera={{ position: [1.55, 0.98, 1.5], fov: 42, near: 0.01, far: 120 }}>
        {payload ? (
          <SfmScene
            payload={payload}
            pointData={pointData}
            pointColorMode={pointColorMode}
            showCameras={showCameras}
            showTrajectory={showTrajectory}
            showGrid={showGrid}
            pointSize={pointSize}
          />
        ) : (
          <>
            <color attach="background" args={["#05070a"]} />
            <ambientLight intensity={0.5} />
          </>
        )}
      </Canvas>

      {panelCollapsed ? (
        <button
          className="sfm-preview-peek"
          type="button"
          aria-label={`Show SfM inspector, ${formatNumber(pointData.pointCount)} shown of ${formatNumber(payload?.exactPointCount)} total points`}
          onClick={() => setPanelCollapsed(false)}
        >
          <span>{loading ? "Loading" : "SfM"}</span>
        </button>
      ) : (
      <form className="sfm-preview-panel" onSubmit={handleSubmit}>
        <div className="sfm-preview-heading">
          <div>
            <p>SfM Inspector</p>
            <h1>{payload?.artifact.jobName || "COLMAP output"}</h1>
          </div>
          <div className="sfm-preview-heading-actions">
            <button type="button" onClick={() => setPanelCollapsed(true)} aria-label="Collapse inspector">
              x
            </button>
          </div>
        </div>

        <div className="sfm-preview-metrics">
          <span>{formatNumber(pointData.pointCount)} shown</span>
          <span>{formatNumber(payload?.exactPointCount)} total</span>
          <span>{formatNumber(payload?.registeredImageCount)} cameras</span>
          <span>{formatNumber(payload?.chunkCount)} chunks</span>
        </div>

        <details className="sfm-preview-drawer">
          <summary>Display</summary>
          <div className="sfm-preview-field-grid">
            <label htmlFor="sfm-preview-color-mode">
              Color
              <select
                id="sfm-preview-color-mode"
                value={pointColorMode}
                onChange={(event) => setPointColorMode(event.target.value as PointColorMode)}
              >
                <option value="source">Photo</option>
                <option value="height">Height</option>
                <option value="chunk">Chunk</option>
              </select>
            </label>

            <label htmlFor="sfm-preview-density">
              Density
              <select
                id="sfm-preview-density"
                value={String(maxPoints)}
                onChange={(event) => {
                  const next = QUALITY_OPTIONS.find((option) => option.value === Number(event.target.value)) || QUALITY_OPTIONS[0];
                  setMaxPoints(next.value);
                  setPointSize(next.pointSize);
                }}
              >
                {QUALITY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="sfm-preview-checks">
            <label>
              <input type="checkbox" checked={showCameras} onChange={(event) => setShowCameras(event.target.checked)} />
              Cameras
            </label>
            <label>
              <input
                type="checkbox"
                checked={showTrajectory}
                onChange={(event) => setShowTrajectory(event.target.checked)}
              />
              Path
            </label>
            <label>
              <input type="checkbox" checked={showGrid} onChange={(event) => setShowGrid(event.target.checked)} />
              Grid
            </label>
            <label>
              <input
                type="checkbox"
                checked={!showOutliers}
                onChange={(event) => setShowOutliers(!event.target.checked)}
              />
              Clean points
            </label>
            <label>
              <input
                type="checkbox"
                checked={showSeamDebug}
                onChange={(event) => setShowSeamDebug(event.target.checked)}
              />
              Seams
            </label>
          </div>

          <div className="sfm-preview-range-row">
            <label htmlFor="sfm-preview-point-size">Point size</label>
            <span>{selectedQuality.label}</span>
          </div>
          <input
            id="sfm-preview-point-size"
            type="range"
            min="0.0015"
            max="0.014"
            step="0.0005"
            value={pointSize}
            onChange={(event) => setPointSize(Number(event.target.value))}
          />
        </details>

        {error ? <p className="sfm-preview-error">{error}</p> : null}
        {payload?.seamDebug && showSeamDebug ? (
          <div className="sfm-preview-seam-debug">
            <span>{payload.seamDebug.strategy || "seam report"}</span>
            <span>{payload.seamDebug.decision || "unknown"}</span>
            <span>{payload.seamDebug.acceptedEdgeCount} accepted</span>
            <span>{payload.seamDebug.rejectedEdgeCount} rejected</span>
            <span>{payload.seamDebug.culledPointCount ?? 0} culled</span>
            <span>{payload.seamDebug.cycleStatus || "cycle n/a"}</span>
          </div>
        ) : null}
        <details className="sfm-preview-source">
          <summary>Source</summary>
          <div className="sfm-preview-url-row">
            <input
              id="sfm-preview-url"
              value={inputUrl}
              onChange={(event) => setInputUrl(event.target.value)}
              spellCheck={false}
            />
            <button type="submit" disabled={loading || !inputUrl.trim()}>
              Load
            </button>
          </div>
        </details>
      </form>
      )}
    </main>
  );
}
