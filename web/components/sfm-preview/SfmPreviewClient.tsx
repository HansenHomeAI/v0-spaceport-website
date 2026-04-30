"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import type { SfmPreviewPayload } from "../../lib/sfmPreview";
import "./sfm-preview.css";

type PointColorMode = "chunk" | "source";

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

  useEffect(() => () => geometry.dispose(), [geometry]);

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
        transparent={opacity < 1}
        opacity={opacity}
        depthWrite={false}
      />
    </points>
  );
}

function LineLayer({ positions }: { positions: number[] }) {
  const geometry = useMemo(() => makeGeometry(positions), [positions]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  if (positions.length < 6) {
    return null;
  }

  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial color="#e8edf5" transparent opacity={0.42} />
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
  pointColorMode,
  showCameras,
  showTrajectory,
  pointSize,
}: {
  payload: SfmPreviewPayload;
  pointColorMode: PointColorMode;
  showCameras: boolean;
  showTrajectory: boolean;
  pointSize: number;
}) {
  const pointColors = pointColorMode === "chunk" ? payload.chunkColors : payload.colors;
  const cameraPositions = useMemo(() => payload.cameras.flatMap((camera) => camera.position), [payload.cameras]);
  const trajectory = useMemo(() => buildTrajectory(payload.cameras), [payload.cameras]);

  return (
    <>
      <color attach="background" args={["#05070a"]} />
      <ambientLight intensity={0.58} />
      <directionalLight position={[3, 4, 3]} intensity={0.9} />
      <gridHelper args={[4, 12, "#243244", "#121922"]} />
      <axesHelper args={[0.65]} />
      <PointLayer positions={payload.positions} colors={pointColors} size={pointSize} opacity={0.94} />
      {showTrajectory ? <LineLayer positions={trajectory} /> : null}
      {showCameras ? <PointLayer positions={cameraPositions} size={pointSize * 5.8} opacity={0.98} /> : null}
      <OrbitControls enableDamping dampingFactor={0.08} />
    </>
  );
}

export default function SfmPreviewClient({ initialUrl }: { initialUrl: string }) {
  const [inputUrl, setInputUrl] = useState(initialUrl);
  const [activeUrl, setActiveUrl] = useState(initialUrl);
  const [payload, setPayload] = useState<SfmPreviewPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [pointColorMode, setPointColorMode] = useState<PointColorMode>("chunk");
  const [showCameras, setShowCameras] = useState(true);
  const [showTrajectory, setShowTrajectory] = useState(true);
  const [pointSize, setPointSize] = useState(0.012);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetch(`/api/sfm-preview?url=${encodeURIComponent(activeUrl)}`, {
      cache: "no-store",
      signal: controller.signal,
    })
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
  }, [activeUrl]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextUrl = inputUrl.trim();
    if (nextUrl) {
      setActiveUrl(nextUrl);
    }
  };

  return (
    <main className="sfm-preview-shell">
      <Canvas className="sfm-preview-canvas" camera={{ position: [2.7, 2.1, 2.55], near: 0.01, far: 80 }}>
        {payload ? (
          <SfmScene
            payload={payload}
            pointColorMode={pointColorMode}
            showCameras={showCameras}
            showTrajectory={showTrajectory}
            pointSize={pointSize}
          />
        ) : (
          <>
            <color attach="background" args={["#05070a"]} />
            <ambientLight intensity={0.5} />
          </>
        )}
      </Canvas>

      <form className="sfm-preview-panel" onSubmit={handleSubmit}>
        <label htmlFor="sfm-preview-url">COLMAP output</label>
        <div className="sfm-preview-url-row">
          <input
            id="sfm-preview-url"
            value={inputUrl}
            onChange={(event) => setInputUrl(event.target.value)}
            spellCheck={false}
          />
          <button type="submit" disabled={loading || !inputUrl.trim()}>
            {loading ? "..." : "Load"}
          </button>
        </div>

        <div className="sfm-preview-controls">
          <button
            type="button"
            className={pointColorMode === "chunk" ? "active" : ""}
            onClick={() => setPointColorMode((mode) => (mode === "chunk" ? "source" : "chunk"))}
          >
            {pointColorMode === "chunk" ? "Chunk color" : "Source color"}
          </button>
          <button
            type="button"
            className={showCameras ? "active" : ""}
            onClick={() => setShowCameras((value) => !value)}
          >
            Cameras
          </button>
          <button
            type="button"
            className={showTrajectory ? "active" : ""}
            onClick={() => setShowTrajectory((value) => !value)}
          >
            Path
          </button>
        </div>

        <label htmlFor="sfm-preview-point-size">Point size</label>
        <input
          id="sfm-preview-point-size"
          type="range"
          min="0.006"
          max="0.032"
          step="0.002"
          value={pointSize}
          onChange={(event) => setPointSize(Number(event.target.value))}
        />

        {error ? <p className="sfm-preview-error">{error}</p> : null}
        {payload ? (
          <p className="sfm-preview-stats">
            {formatNumber(payload.sampledPointCount)} / {formatNumber(payload.exactPointCount)} points,{" "}
            {formatNumber(payload.registeredImageCount)} cameras, {formatNumber(payload.chunkCount)} chunks
          </p>
        ) : (
          <p className="sfm-preview-stats">{loading ? "Loading" : "Ready"}</p>
        )}
      </form>
    </main>
  );
}
