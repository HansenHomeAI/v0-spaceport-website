"use client";

import React, { useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Line } from '@react-three/drei';
import * as THREE from 'three';
import type { DemDataset, PathVertex, TerrainSamplingResult } from '@/lib/terrain/types';
import { sampleDemElevation } from '@/lib/terrain/dems';

interface TerrainDemoProps {
  dem: DemDataset | null;
  path: PathVertex[];
  sampling: TerrainSamplingResult | null;
}

type TerrainMesh = {
  geometry: THREE.BufferGeometry;
  minElevation: number;
  maxElevation: number;
  verticalScale: number;
};

const DISCOVERY_COLOR = new THREE.Color('#00d1ff');
const REFINEMENT_COLOR = new THREE.Color('#ff9f0a');
const HAZARD_COLOR = new THREE.Color('#ff453a');
const SAFETY_COLOR = new THREE.Color('#32d74b');

function useTerrainMesh(dem: DemDataset | null): TerrainMesh | null {
  return useMemo(() => {
    if (!dem) return null;
    const { elevationsFt, gridSize, cellSizeFt, originFt } = dem;
    const cols = gridSize[0];
    const rows = gridSize[1];
    const positions = new Float32Array(cols * rows * 3);
    const indices: number[] = [];
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const elevation = elevationsFt[row][col];
        min = Math.min(min, elevation);
        max = Math.max(max, elevation);
        const index = row * cols + col;
        const base = index * 3;
        positions[base] = originFt[0] + col * cellSizeFt; // X
        positions[base + 1] = originFt[1] + row * cellSizeFt; // Y
        positions[base + 2] = elevation; // Z (before scaling)
      }
    }

    const verticalScale = 0.015; // exaggerate relief for visual clarity
    for (let i = 2; i < positions.length; i += 3) {
      positions[i] = (positions[i] - min) * verticalScale;
    }

    for (let row = 0; row < rows - 1; row++) {
      for (let col = 0; col < cols - 1; col++) {
        const a = row * cols + col;
        const b = a + 1;
        const c = a + cols;
        const d = c + 1;
        indices.push(a, b, d);
        indices.push(a, d, c);
      }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();

    return {
      geometry,
      minElevation: min,
      maxElevation: max,
      verticalScale,
    };
  }, [dem]);
}

function PathPolyline({ path, mesh, dem }: { path: PathVertex[]; mesh: TerrainMesh; dem: DemDataset }) {
  const points = useMemo(() => {
    if (!path.length) return [];
    return path.map((vertex) => {
      const groundFt = sampleDemElevation(dem, vertex.x, vertex.y);
      const absoluteAlt = groundFt + vertex.altitudeFt;
      const z = (absoluteAlt - mesh.minElevation) * mesh.verticalScale;
      return new THREE.Vector3(vertex.x, vertex.y, z);
    });
  }, [path, mesh, dem]);

  if (!points.length) return null;

  return <Line points={points} color="#007AFF" lineWidth={2.8} />;
}

function SamplePoints({
  samples,
  mesh,
  color,
}: {
  samples: { x: number; y: number; groundFt: number }[];
  mesh: TerrainMesh;
  color: THREE.ColorRepresentation;
}) {
  return (
    <group>
      {samples.map((sample, idx) => {
        const z = (sample.groundFt - mesh.minElevation) * mesh.verticalScale;
        return (
          <mesh key={idx} position={[sample.x, sample.y, z]}>
            <sphereGeometry args={[18, 16, 16]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.4} />
          </mesh>
        );
      })}
    </group>
  );
}

function SafetyMarkers({ safety, mesh }: { safety: TerrainSamplingResult['safetyWaypoints']; mesh: TerrainMesh }) {
  return (
    <group>
      {safety.map((wp, idx) => {
        const z = (wp.altitudeFt - mesh.minElevation) * mesh.verticalScale;
        return (
          <mesh key={idx} position={[wp.x, wp.y, z]}>
            <coneGeometry args={[35, 90, 16]} />
            <meshStandardMaterial color={SAFETY_COLOR} emissive={SAFETY_COLOR} emissiveIntensity={0.45} />
          </mesh>
        );
      })}
    </group>
  );
}

export function TerrainDemo({ dem, path, sampling }: TerrainDemoProps) {
  const mesh = useTerrainMesh(dem);
  React.useEffect(() => {
    return () => {
      mesh?.geometry.dispose();
    };
  }, [mesh]);

  const discoveryPoints = useMemo(() => sampling?.samples ?? [], [sampling?.samples]);
  const refinementPoints = useMemo(() => sampling?.refinementSamples ?? [], [sampling?.refinementSamples]);
  const hazards = useMemo(() => sampling?.hazards ?? [], [sampling?.hazards]);
  const safety = useMemo(() => sampling?.safetyWaypoints ?? [], [sampling?.safetyWaypoints]);

  return (
    <div className="relative h-[600px] w-full overflow-hidden rounded-2xl border border-slate-800 bg-[#090b10] shadow-inner">
      {dem && mesh ? (
        <Canvas camera={{ position: [1600, 1600, 1600], fov: 55 }}>
          <color attach="background" args={[0x090b10]} />
          <ambientLight intensity={0.65} />
          <directionalLight position={[800, 1100, 900]} intensity={0.9} />
          <pointLight position={[-900, 500, -600]} intensity={0.6} />

          <mesh geometry={mesh.geometry} rotation={[-Math.PI / 2, 0, 0]}>
            <meshStandardMaterial color="#1c1f29" roughness={0.85} metalness={0.05} />
          </mesh>

          <gridHelper args={[7000, 28, '#1f2937', '#111827']} rotation={[Math.PI / 2, 0, 0]} />

          {path.length > 1 && <PathPolyline path={path} mesh={mesh} dem={dem} />}

          {discoveryPoints.length > 0 && (
            <SamplePoints
              samples={discoveryPoints.map((s) => ({ x: s.x, y: s.y, groundFt: s.groundFt }))}
              mesh={mesh}
              color={DISCOVERY_COLOR}
            />
          )}

          {refinementPoints.length > 0 && (
            <SamplePoints
              samples={refinementPoints.map((s) => ({ x: s.x, y: s.y, groundFt: s.groundFt }))}
              mesh={mesh}
              color={REFINEMENT_COLOR}
            />
          )}

          {hazards.length > 0 && (
            <SamplePoints
              samples={hazards.map((h) => ({ x: h.x, y: h.y, groundFt: h.groundFt }))}
              mesh={mesh}
              color={HAZARD_COLOR}
            />
          )}

          {safety.length > 0 && <SafetyMarkers safety={safety} mesh={mesh} />}

          <OrbitControls enableDamping dampingFactor={0.08} maxPolarAngle={Math.PI * 0.95} />
        </Canvas>
      ) : (
        <div className="flex h-full items-center justify-center text-slate-500">
          Select a DEM to visualise the adaptive sampling overlays.
        </div>
      )}
    </div>
  );
}

export default TerrainDemo;
