"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import "./sfm-point-cloud-viewer.css";

type ParseResult = {
  positions: Float32Array;
  colors: Float32Array;
  pointCount: number;
  center: THREE.Vector3;
  radius: number;
  boundsMin: THREE.Vector3;
  boundsMax: THREE.Vector3;
};

const S3_PUBLIC_HOST = "https://spaceport-ml-processing.s3.amazonaws.com";
const DEFAULT_DATASET = "brass-full-chunk-a-1775237679";

function buildCandidatePointUrls(dataset: string): string[] {
  const ds = dataset.trim().replace(/^\/+|\/+$/g, "");
  const bases = [
    `${S3_PUBLIC_HOST}/colmap/${ds}`,
    `${S3_PUBLIC_HOST}/colmap/${ds}/sparse/0`,
    `${S3_PUBLIC_HOST}/${ds}`,
    `${S3_PUBLIC_HOST}/${ds}/sparse/0`,
  ];

  return [...new Set(bases.map((b) => `${b}/points3D.txt`))];
}

function toProxyUrl(upstreamUrl: string): string {
  const encodedBase = upstreamUrl.replace("https://", "https:/").replace("http://", "http:/");
  return `/api/sogs-proxy/${encodedBase}`;
}

async function fetchPointsFile(dataset: string): Promise<{ text: string; sourceUrl: string }> {
  const candidates = buildCandidatePointUrls(dataset);
  let lastError = "";

  for (const url of candidates) {
    const res = await fetch(toProxyUrl(url), { cache: "no-store" });
    if (!res.ok) {
      lastError = `${url} -> HTTP ${res.status}`;
      continue;
    }
    return {
      text: await res.text(),
      sourceUrl: url,
    };
  }

  throw new Error(
    `Unable to load points3D.txt for dataset '${dataset}'. Tried: ${candidates.join(", ")}. Last error: ${lastError || "unknown"}`,
  );
}

function parseColmapPoints(text: string): ParseResult {
  const lines = text.split(/\r?\n/);

  const positionsBuffer: number[] = [];
  const colorsBuffer: number[] = [];

  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let minZ = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  let maxZ = Number.NEGATIVE_INFINITY;

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }

    const fields = line.split(/\s+/);
    if (fields.length < 7) {
      continue;
    }

    const x = Number(fields[1]);
    const y = Number(fields[2]);
    const z = Number(fields[3]);
    const r = Number(fields[4]);
    const g = Number(fields[5]);
    const b = Number(fields[6]);

    if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) {
      continue;
    }

    positionsBuffer.push(x, y, z);
    colorsBuffer.push(
      Number.isFinite(r) ? Math.max(0, Math.min(255, r)) / 255 : 1,
      Number.isFinite(g) ? Math.max(0, Math.min(255, g)) / 255 : 1,
      Number.isFinite(b) ? Math.max(0, Math.min(255, b)) / 255 : 1,
    );

    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    minZ = Math.min(minZ, z);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
    maxZ = Math.max(maxZ, z);
  }

  const pointCount = positionsBuffer.length / 3;
  if (pointCount === 0) {
    throw new Error("No valid points parsed from points3D.txt.");
  }

  const positions = new Float32Array(positionsBuffer);
  const colors = new Float32Array(colorsBuffer);

  const boundsMin = new THREE.Vector3(minX, minY, minZ);
  const boundsMax = new THREE.Vector3(maxX, maxY, maxZ);
  const center = new THREE.Vector3((minX + maxX) / 2, (minY + maxY) / 2, (minZ + maxZ) / 2);
  const radius = Math.max(boundsMax.distanceTo(center), 1e-4);

  for (let i = 0; i < pointCount; i += 1) {
    positions[i * 3 + 0] -= center.x;
    positions[i * 3 + 1] -= center.y;
    positions[i * 3 + 2] -= center.z;
  }

  return {
    positions,
    colors,
    pointCount,
    center,
    radius,
    boundsMin,
    boundsMax,
  };
}

function CameraController({ radius }: { radius: number }) {
  const { camera } = useThree();

  useEffect(() => {
    const distance = Math.max(radius * 2.2, 2);
    camera.position.set(distance, distance * 0.5, distance);
    camera.near = Math.max(0.01, radius / 2000);
    camera.far = Math.max(2000, radius * 40);
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();
  }, [camera, radius]);

  return null;
}

function CloudPoints({ data }: { data: ParseResult }) {
  const geometry = useMemo(() => {
    const geom = new THREE.BufferGeometry();
    geom.setAttribute("position", new THREE.BufferAttribute(data.positions, 3));
    geom.setAttribute("color", new THREE.BufferAttribute(data.colors, 3));
    return geom;
  }, [data]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  return (
    <points geometry={geometry}>
      <pointsMaterial size={Math.max(data.radius / 500, 0.005)} sizeAttenuation vertexColors />
    </points>
  );
}

export default function SfmPointCloudViewer() {
  const [dataset, setDataset] = useState(DEFAULT_DATASET);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [data, setData] = useState<ParseResult | null>(null);
  const controlsRef = useRef<any>(null);

  const loadDataset = useCallback(async (datasetId: string) => {
    setLoading(true);
    setError(null);
    try {
      const loaded = await fetchPointsFile(datasetId);
      const parsed = parseColmapPoints(loaded.text);
      setSourceUrl(loaded.sourceUrl);
      setData(parsed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load point cloud.");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDataset(DEFAULT_DATASET);
  }, [loadDataset]);

  useEffect(() => {
    if (!data || !controlsRef.current) {
      return;
    }
    controlsRef.current.target.set(0, 0, 0);
    controlsRef.current.update();
  }, [data]);

  return (
    <main className="sfm-viewer-shell">
      <section className="sfm-controls">
        <h1>SfM Point Cloud Viewer</h1>
        <p>Load COLMAP points3D output and orbit around the centered reconstruction.</p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            loadDataset(dataset);
          }}
        >
          <label htmlFor="dataset">Dataset</label>
          <div className="sfm-row">
            <input
              id="dataset"
              value={dataset}
              onChange={(e) => setDataset(e.target.value)}
              placeholder="brass-full-chunk-a-1775237679"
            />
            <button type="submit" disabled={!dataset.trim() || loading}>
              {loading ? "Loading…" : "Load"}
            </button>
          </div>
        </form>
        {sourceUrl ? <p className="sfm-meta">Source: {sourceUrl}</p> : null}
        {data ? (
          <ul className="sfm-stats">
            <li>Points: {data.pointCount.toLocaleString()}</li>
            <li>
              Bounds: [{data.boundsMin.x.toFixed(2)}, {data.boundsMin.y.toFixed(2)}, {data.boundsMin.z.toFixed(2)}] → [
              {data.boundsMax.x.toFixed(2)}, {data.boundsMax.y.toFixed(2)}, {data.boundsMax.z.toFixed(2)}]
            </li>
            <li>Centered at origin, orbit target fixed to (0,0,0).</li>
          </ul>
        ) : null}
        {error ? <p className="sfm-error">{error}</p> : null}
      </section>

      <section className="sfm-canvas-wrap">
        <Canvas camera={{ fov: 60 }}>
          <color attach="background" args={["#07090f"]} />
          {data ? <CameraController radius={data.radius} /> : null}
          <ambientLight intensity={0.6} />
          <pointLight position={[10, 10, 10]} intensity={0.5} />
          <gridHelper args={[10, 10, 0x444444, 0x222222]} />
          <axesHelper args={[1.5]} />
          {data ? <CloudPoints data={data} /> : null}
          <OrbitControls
            ref={controlsRef}
            enableDamping
            dampingFactor={0.08}
            target={[0, 0, 0]}
            minDistance={0.1}
            maxDistance={10000}
          />
        </Canvas>
      </section>
    </main>
  );
}
