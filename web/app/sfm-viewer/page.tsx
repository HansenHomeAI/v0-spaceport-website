"use client";

export const runtime = "edge";

import React, { useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";

interface PointCloudData {
  positions: Float32Array;
  colors: Float32Array;
  count: number;
  center: THREE.Vector3;
  radius: number;
}

const DEFAULT_DATASET_KEY = "brass-full-chunk-a-1775237679";

function deriveDefaultDatasetUrl(): string {
  const datasetBase = process.env.NEXT_PUBLIC_SFM_COLMAP_BASE_URL?.trim();
  const explicit = process.env.NEXT_PUBLIC_SFM_DEFAULT_POINTS3D_URL?.trim();

  if (explicit) {
    return explicit;
  }

  if (!datasetBase) {
    return "";
  }

  return `${datasetBase.replace(/\/$/, "")}/${DEFAULT_DATASET_KEY}/sparse/0/points3D.txt`;
}

function parseColmapPoints3D(content: string): PointCloudData {
  const rows = content.split(/\r?\n/);

  const positions: number[] = [];
  const colors: number[] = [];

  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let minZ = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  let maxZ = Number.NEGATIVE_INFINITY;

  for (const row of rows) {
    const line = row.trim();

    if (!line || line.startsWith("#")) {
      continue;
    }

    const cols = line.split(/\s+/);
    if (cols.length < 7) {
      continue;
    }

    const x = Number(cols[1]);
    const y = Number(cols[2]);
    const z = Number(cols[3]);
    const r = Number(cols[4]);
    const g = Number(cols[5]);
    const b = Number(cols[6]);

    if (![x, y, z, r, g, b].every(Number.isFinite)) {
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
  }

  const pointCount = positions.length / 3;
  if (!pointCount) {
    throw new Error("No valid points found in points3D.txt.");
  }

  const center = new THREE.Vector3(
    (minX + maxX) * 0.5,
    (minY + maxY) * 0.5,
    (minZ + maxZ) * 0.5,
  );

  let maxDistance = 0;
  for (let idx = 0; idx < positions.length; idx += 3) {
    const dx = positions[idx] - center.x;
    const dy = positions[idx + 1] - center.y;
    const dz = positions[idx + 2] - center.z;
    const distance = Math.sqrt(dx * dx + dy * dy + dz * dz);
    if (distance > maxDistance) {
      maxDistance = distance;
    }
  }

  const radius = maxDistance || 1;

  const normalizedPositions = new Float32Array(positions.length);
  for (let idx = 0; idx < positions.length; idx += 3) {
    normalizedPositions[idx] = (positions[idx] - center.x) / radius;
    normalizedPositions[idx + 1] = (positions[idx + 1] - center.y) / radius;
    normalizedPositions[idx + 2] = (positions[idx + 2] - center.z) / radius;
  }

  return {
    positions: normalizedPositions,
    colors: new Float32Array(colors),
    count: pointCount,
    center,
    radius,
  };
}

function PointCloudScene({ cloud }: { cloud: PointCloudData }) {
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(cloud.positions, 3));
    g.setAttribute("color", new THREE.BufferAttribute(cloud.colors, 3));
    return g;
  }, [cloud]);

  useEffect(() => {
    return () => {
      geometry.dispose();
    };
  }, [geometry]);

  return (
    <>
      <ambientLight intensity={0.7} />
      <points geometry={geometry} frustumCulled={false}>
        <pointsMaterial
          size={0.005}
          sizeAttenuation
          vertexColors
          transparent
          opacity={0.95}
          depthWrite={false}
        />
      </points>
      <axesHelper args={[0.5]} />
      <gridHelper args={[2, 10, "#454545", "#2b2b2b"]} />
      <OrbitControls
        makeDefault
        target={[0, 0, 0]}
        enablePan
        enableRotate
        enableZoom
        minDistance={0.1}
        maxDistance={20}
        dampingFactor={0.08}
      />
    </>
  );
}

export default function SfmViewerPage() {
  const [datasetUrl, setDatasetUrl] = useState(deriveDefaultDatasetUrl());
  const [status, setStatus] = useState<string>(
    deriveDefaultDatasetUrl()
      ? "Ready. Click ‘Load dataset’ to fetch the default COLMAP output."
      : "Set NEXT_PUBLIC_SFM_COLMAP_BASE_URL or paste a points3D.txt URL.",
  );
  const [isLoading, setIsLoading] = useState(false);
  const [cloud, setCloud] = useState<PointCloudData | null>(null);

  const loadFromText = (content: string, source: string) => {
    const parsed = parseColmapPoints3D(content);
    setCloud(parsed);
    setStatus(
      `Loaded ${parsed.count.toLocaleString()} points from ${source}. Center: (${parsed.center.x.toFixed(2)}, ${parsed.center.y.toFixed(2)}, ${parsed.center.z.toFixed(2)}), radius: ${parsed.radius.toFixed(2)}.`,
    );
  };

  const loadFromUrl = async () => {
    const url = datasetUrl.trim();
    if (!url) {
      setStatus("Please provide a valid points3D.txt URL.");
      return;
    }

    setIsLoading(true);
    setStatus("Loading dataset...");

    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const text = await response.text();
      loadFromText(text, url);
    } catch (error) {
      setCloud(null);
      setStatus(`Failed to load dataset: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setIsLoading(false);
    }
  };

  const onFileSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setIsLoading(true);
    setStatus(`Reading ${file.name}...`);

    try {
      const text = await file.text();
      loadFromText(text, file.name);
    } catch (error) {
      setStatus(`Failed to read file: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setIsLoading(false);
      event.target.value = "";
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d", color: "#fff", padding: "16px" }}>
      <h1 style={{ margin: 0, fontSize: "20px" }}>SfM Point Cloud Viewer</h1>
      <p style={{ opacity: 0.8, marginTop: 8, lineHeight: 1.4 }}>
        Default target dataset: <strong>{DEFAULT_DATASET_KEY}</strong>. The viewer recenters to origin and scales the cloud to a normalized radius of 1 for intuitive orbit navigation.
      </p>

      <div style={{ display: "grid", gap: 8, marginBottom: 12 }}>
        <input
          type="text"
          value={datasetUrl}
          onChange={(event) => setDatasetUrl(event.target.value)}
          placeholder="https://.../points3D.txt"
          style={{
            width: "100%",
            padding: "10px 12px",
            borderRadius: 8,
            border: "1px solid #3a3a3a",
            background: "#171717",
            color: "#fff",
          }}
        />

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button
            onClick={loadFromUrl}
            disabled={isLoading}
            style={{
              padding: "10px 14px",
              borderRadius: 8,
              border: "none",
              background: isLoading ? "#4f5561" : "#4f83ff",
              color: "#fff",
              fontWeight: 600,
              cursor: isLoading ? "not-allowed" : "pointer",
            }}
          >
            {isLoading ? "Loading..." : "Load dataset"}
          </button>

          <label
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 14px",
              borderRadius: 8,
              border: "1px solid #3a3a3a",
              cursor: "pointer",
            }}
          >
            Load local points3D.txt
            <input type="file" accept=".txt" onChange={onFileSelected} style={{ display: "none" }} />
          </label>
        </div>

        <div
          style={{
            background: "#151515",
            border: "1px solid #2c2c2c",
            borderRadius: 8,
            padding: "10px 12px",
            fontSize: 13,
            lineHeight: 1.4,
          }}
        >
          {status}
        </div>
      </div>

      <div style={{ height: "calc(100vh - 240px)", minHeight: 400, border: "1px solid #2c2c2c", borderRadius: 8, overflow: "hidden" }}>
        {cloud ? (
          <Canvas camera={{ position: [0, 0, 2.8], fov: 55, near: 0.01, far: 100 }}>
            <color attach="background" args={["#0b0b0b"]} />
            <PointCloudScene cloud={cloud} />
          </Canvas>
        ) : (
          <div style={{ display: "grid", placeItems: "center", width: "100%", height: "100%", color: "#b3b3b3" }}>
            Load a COLMAP points3D.txt file to begin.
          </div>
        )}
      </div>
    </div>
  );
}
