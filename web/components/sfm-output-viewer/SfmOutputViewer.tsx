"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { Line, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import "./sfm-output-viewer.css";

const DEFAULT_SFM_URL =
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-r5-v18-sfm-viewer-1776314974/sfm_points_every4.json";

type Bounds = {
  min: [number, number, number];
  max: [number, number, number];
};

type SfmMetadata = {
  sourceColmapS3Uri?: string;
  sourcePointCount?: number;
  sampledPointCount?: number;
  sampleStride?: number;
  sourceCameraCount?: number;
  cameraCount?: number;
  excludedCameraCount?: number;
  pointStride?: number;
  cameraStride?: number;
  pointBounds?: Bounds;
  cameraBounds?: Bounds;
  notes?: string;
};

type SfmPayload = {
  metadata: SfmMetadata;
  points: number[];
  cameras: number[];
};

type SceneFrame = {
  center: [number, number, number];
  extent: number;
};

function isValidUrl(value: string) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:";
  } catch {
    return false;
  }
}

function mergeBounds(a?: Bounds, b?: Bounds): Bounds | null {
  if (!a && !b) {
    return null;
  }
  if (!a) {
    return b ?? null;
  }
  if (!b) {
    return a;
  }
  return {
    min: [
      Math.min(a.min[0], b.min[0]),
      Math.min(a.min[1], b.min[1]),
      Math.min(a.min[2], b.min[2]),
    ],
    max: [
      Math.max(a.max[0], b.max[0]),
      Math.max(a.max[1], b.max[1]),
      Math.max(a.max[2], b.max[2]),
    ],
  };
}

function buildSceneFrame(metadata: SfmMetadata): SceneFrame {
  const bounds = mergeBounds(metadata.pointBounds, metadata.cameraBounds);
  if (!bounds) {
    return { center: [0, 0, 0], extent: 100 };
  }
  const center: [number, number, number] = [
    (bounds.min[0] + bounds.max[0]) / 2,
    (bounds.min[1] + bounds.max[1]) / 2,
    (bounds.min[2] + bounds.max[2]) / 2,
  ];
  const extent = Math.max(
    bounds.max[0] - bounds.min[0],
    bounds.max[1] - bounds.min[1],
    bounds.max[2] - bounds.min[2],
    1,
  );
  return { center, extent };
}

function makePointGeometry(data: number[], stride: number) {
  const count = Math.floor(data.length / stride);
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  for (let i = 0; i < count; i += 1) {
    const src = i * stride;
    const dst = i * 3;
    positions[dst] = data[src];
    positions[dst + 1] = data[src + 1];
    positions[dst + 2] = data[src + 2];
    colors[dst] = (data[src + 3] ?? 255) / 255;
    colors[dst + 1] = (data[src + 4] ?? 255) / 255;
    colors[dst + 2] = (data[src + 5] ?? 255) / 255;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  geometry.computeBoundingSphere();
  return geometry;
}

function makeCameraGeometry(data: number[], stride: number) {
  const count = Math.floor(data.length / stride);
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i += 1) {
    const src = i * stride;
    const dst = i * 3;
    positions[dst] = data[src + 1];
    positions[dst + 1] = data[src + 2];
    positions[dst + 2] = data[src + 3];
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.computeBoundingSphere();
  return geometry;
}

function makeCameraPath(data: number[], stride: number) {
  const count = Math.floor(data.length / stride);
  const points: Array<[number, number, number]> = [];
  for (let i = 0; i < count; i += 1) {
    const src = i * stride;
    points.push([data[src + 1], data[src + 2], data[src + 3]]);
  }
  return points;
}

function CameraRig({ frame }: { frame: SceneFrame }) {
  const { camera } = useThree();
  useEffect(() => {
    const distance = frame.extent * 1.2;
    camera.near = Math.max(frame.extent / 10000, 0.01);
    camera.far = frame.extent * 8;
    camera.position.set(0, -distance, frame.extent * 0.45);
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();
  }, [camera, frame]);
  return null;
}

function SfmScene({
  payload,
  showPoints,
  showCameras,
  showPath,
  pointSize,
}: {
  payload: SfmPayload;
  showPoints: boolean;
  showCameras: boolean;
  showPath: boolean;
  pointSize: number;
}) {
  const pointStride = payload.metadata.pointStride ?? 6;
  const cameraStride = payload.metadata.cameraStride ?? 4;
  const pointGeometry = useMemo(() => makePointGeometry(payload.points, pointStride), [payload.points, pointStride]);
  const cameraGeometry = useMemo(
    () => makeCameraGeometry(payload.cameras, cameraStride),
    [payload.cameras, cameraStride],
  );
  const cameraPath = useMemo(() => makeCameraPath(payload.cameras, cameraStride), [payload.cameras, cameraStride]);
  const frame = useMemo(() => buildSceneFrame(payload.metadata), [payload.metadata]);

  useEffect(() => {
    return () => {
      pointGeometry.dispose();
      cameraGeometry.dispose();
    };
  }, [pointGeometry, cameraGeometry]);

  return (
    <>
      <CameraRig frame={frame} />
      <color attach="background" args={["#020204"]} />
      <fog attach="fog" args={["#020204", frame.extent * 1.2, frame.extent * 3.5]} />
      <ambientLight intensity={0.5} />
      <group position={[-frame.center[0], -frame.center[1], -frame.center[2]]}>
        {showPoints ? (
          <points geometry={pointGeometry}>
            <pointsMaterial vertexColors size={pointSize} sizeAttenuation depthWrite={false} />
          </points>
        ) : null}
        {showPath && cameraPath.length > 1 ? (
          <Line points={cameraPath} color="#f2a23a" lineWidth={1.25} transparent opacity={0.72} />
        ) : null}
        {showCameras ? (
          <points geometry={cameraGeometry}>
            <pointsMaterial color="#ffcf5a" size={pointSize * 5} sizeAttenuation depthWrite={false} />
          </points>
        ) : null}
      </group>
      <OrbitControls makeDefault enableDamping dampingFactor={0.08} target={[0, 0, 0]} />
    </>
  );
}

function compactNumber(value?: number) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "0";
  }
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
}

export default function SfmOutputViewer() {
  const [inputUrl, setInputUrl] = useState(DEFAULT_SFM_URL);
  const [activeUrl, setActiveUrl] = useState("");
  const [payload, setPayload] = useState<SfmPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showPoints, setShowPoints] = useState(true);
  const [showCameras, setShowCameras] = useState(true);
  const [showPath, setShowPath] = useState(true);
  const [pointSize, setPointSize] = useState(1.2);

  const loadUrl = (raw: string) => {
    const value = raw.trim();
    if (!isValidUrl(value)) {
      setError("Enter a valid SfM JSON URL.");
      return false;
    }
    setError(null);
    setActiveUrl(value);
    return true;
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    loadUrl(inputUrl);
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const url = params.get("url")?.trim() || DEFAULT_SFM_URL;
    setInputUrl(url);
    loadUrl(url);
  }, []);

  useEffect(() => {
    if (!activeUrl) {
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetch(activeUrl, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        return response.json() as Promise<SfmPayload>;
      })
      .then((data) => {
        if (!Array.isArray(data.points) || !Array.isArray(data.cameras) || !data.metadata) {
          throw new Error("SfM payload is missing points, cameras, or metadata.");
        }
        setPayload(data);
      })
      .catch((err: Error) => {
        if (err.name !== "AbortError") {
          setError(err.message || "Unable to load SfM payload.");
          setPayload(null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [activeUrl]);

  return (
    <main className="sfm-shell">
      <Canvas className="sfm-canvas" camera={{ fov: 45, position: [0, -160, 80] }} dpr={[1, 2]}>
        {payload ? (
          <SfmScene
            payload={payload}
            showPoints={showPoints}
            showCameras={showCameras}
            showPath={showPath}
            pointSize={pointSize}
          />
        ) : (
          <>
            <color attach="background" args={["#020204"]} />
            <ambientLight intensity={0.4} />
          </>
        )}
      </Canvas>

      <form className="sfm-panel" onSubmit={handleSubmit}>
        <label htmlFor="sfm-url-input">SfM JSON URL</label>
        <div className="sfm-url-row">
          <input
            id="sfm-url-input"
            type="url"
            inputMode="url"
            autoComplete="off"
            value={inputUrl}
            onChange={(event) => setInputUrl(event.target.value)}
            placeholder="https://.../sfm_points.json"
          />
          <button type="submit" disabled={!inputUrl.trim() || loading}>
            {loading ? "..." : "Load"}
          </button>
        </div>

        <div className="sfm-controls" aria-label="SfM viewer controls">
          <button
            type="button"
            className={showPoints ? "sfm-active" : ""}
            onClick={() => setShowPoints((value) => !value)}
          >
            Points
          </button>
          <button
            type="button"
            className={showCameras ? "sfm-active" : ""}
            onClick={() => setShowCameras((value) => !value)}
          >
            Cameras
          </button>
          <button
            type="button"
            className={showPath ? "sfm-active" : ""}
            onClick={() => setShowPath((value) => !value)}
          >
            Path
          </button>
        </div>

        <label className="sfm-slider-label" htmlFor="sfm-point-size">
          Point size
        </label>
        <input
          id="sfm-point-size"
          type="range"
          min="0.4"
          max="4"
          step="0.1"
          value={pointSize}
          onChange={(event) => setPointSize(Number(event.target.value))}
        />

        {error ? <p className="sfm-error">{error}</p> : null}
        {payload ? (
          <p className="sfm-stats">
            {compactNumber(payload.metadata.sampledPointCount)} of{" "}
            {compactNumber(payload.metadata.sourcePointCount)} points,{" "}
            {compactNumber(payload.metadata.cameraCount)} of{" "}
            {compactNumber(payload.metadata.sourceCameraCount ?? payload.metadata.cameraCount)} cameras.
          </p>
        ) : (
          <p className="sfm-stats">{loading ? "Loading..." : "Ready."}</p>
        )}
      </form>
    </main>
  );
}
