'use client';

import React, { useMemo, useEffect, useRef } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, Line } from '@react-three/drei';
import * as THREE from 'three';
import {
  groundFootprint,
  type GroundQuad,
} from '../../lib/cameraOverlapMath';
import styles from './page.module.css';

/**
 * Math uses X = along-track, Y = cross-track, Z = up.
 * Three.js uses Y-up; ground is the XZ plane (Y = 0).
 */
function mathGroundToThree(corner: [number, number, number]): [number, number, number] {
  return [corner[0], corner[2], corner[1]];
}

function mathDroneToThree(along: number, height: number, cross: number): [number, number, number] {
  return [along, height, cross];
}

// ---------------------------------------------------------------------------

function DroneMarker({ position }: { position: [number, number, number] }) {
  const y = position[1];
  return (
    <group position={position}>
      <mesh>
        <sphereGeometry args={[Math.max(1.5, y * 0.008), 12, 12]} />
        <meshStandardMaterial color="#f5f5f7" />
      </mesh>
      <mesh position={[0, -y / 2, 0]}>
        <cylinderGeometry args={[0.4, 0.4, y, 6]} />
        <meshStandardMaterial color="#333" transparent opacity={0.25} />
      </mesh>
    </group>
  );
}

function FootprintQuad({
  quad,
  color,
  opacity,
}: {
  quad: GroundQuad;
  color: string;
  opacity: number;
}) {
  const geo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    const verts: number[] = [];
    for (const c of quad) {
      const [tx, ty, tz] = mathGroundToThree(c);
      verts.push(tx, ty + 0.08, tz);
    }
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(verts), 3));
    g.setIndex([0, 1, 2, 0, 2, 3]);
    g.computeVertexNormals();
    return g;
  }, [quad]);

  return (
    <mesh geometry={geo}>
      <meshStandardMaterial
        color={color}
        transparent
        opacity={opacity}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}

function FrustumLines({
  dronePos,
  quad,
  lineOpacity = 0.55,
}: {
  dronePos: [number, number, number];
  quad: GroundQuad;
  lineOpacity?: number;
}) {
  const lines = useMemo(() => {
    const edges: Array<[THREE.Vector3, THREE.Vector3]> = [];
    for (const corner of quad) {
      const g = mathGroundToThree(corner);
      edges.push([
        new THREE.Vector3(dronePos[0], dronePos[1], dronePos[2]),
        new THREE.Vector3(g[0], g[1], g[2]),
      ]);
    }
    for (let i = 0; i < 4; i++) {
      const c1 = mathGroundToThree(quad[i]);
      const c2 = mathGroundToThree(quad[(i + 1) % 4]);
      edges.push([
        new THREE.Vector3(c1[0], c1[1], c1[2]),
        new THREE.Vector3(c2[0], c2[1], c2[2]),
      ]);
    }
    return edges;
  }, [dronePos, quad]);

  return (
    <>
      {lines.map((pts, i) => (
        <Line
          key={i}
          points={[pts[0], pts[1]]}
          color="#888"
          lineWidth={1}
          transparent
          opacity={lineOpacity}
        />
      ))}
    </>
  );
}

function GroundGrid({ size }: { size: number }) {
  const s = Math.max(40, Math.ceil(size / 40) * 40);
  const divisions = Math.min(40, Math.max(8, Math.round(s / 25)));
  return (
    <gridHelper args={[s, divisions, '#2a2a2a', '#1a1a1a']} position={[0, -0.02, 0]} />
  );
}

/** ~32×28 ft ranch + roof — feet scale */
function House({ x, z, rotationY = 0 }: { x: number; z: number; rotationY?: number }) {
  return (
    <group position={[x, 0, z]} rotation={[0, rotationY, 0]}>
      <mesh position={[0, 9, 0]} castShadow receiveShadow>
        <boxGeometry args={[32, 18, 26]} />
        <meshStandardMaterial color="#6d5b4c" roughness={0.85} />
      </mesh>
      <mesh position={[0, 9, 12.6]} castShadow>
        <boxGeometry args={[6, 8, 0.4]} />
        <meshStandardMaterial color="#3d4a5c" roughness={0.4} metalness={0.2} />
      </mesh>
      <mesh position={[0, 22, 0]} rotation={[0, Math.PI / 4, 0]} castShadow>
        <coneGeometry args={[22, 11, 4]} />
        <meshStandardMaterial color="#4a3f35" roughness={0.9} />
      </mesh>
      <mesh position={[0, 0.15, 0]} receiveShadow>
        <boxGeometry args={[36, 0.3, 30]} />
        <meshStandardMaterial color="#3a3530" roughness={1} />
      </mesh>
    </group>
  );
}

function Tree({ x, z, scale = 1 }: { x: number; z: number; scale?: number }) {
  const s = scale;
  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, 8 * s, 0]} castShadow>
        <cylinderGeometry args={[1.4 * s, 2.2 * s, 16 * s, 7]} />
        <meshStandardMaterial color="#4a3828" roughness={0.95} />
      </mesh>
      <mesh position={[0, 26 * s, 0]} castShadow>
        <coneGeometry args={[11 * s, 22 * s, 8]} />
        <meshStandardMaterial color="#2d4a2d" roughness={0.88} />
      </mesh>
      <mesh position={[0, 38 * s, 0]} castShadow>
        <coneGeometry args={[8 * s, 16 * s, 8]} />
        <meshStandardMaterial color="#355c35" roughness={0.82} />
      </mesh>
    </group>
  );
}

/** Homes & trees closer to scene center; more props for neighborhood feel. */
function GroundAnchors({ gridSize }: { gridSize: number }) {
  const r = Math.max(32, gridSize * 0.11);
  return (
    <group>
      <House x={r * 0.55} z={r * 0.35} rotationY={-0.25} />
      <House x={-r * 0.5} z={r * 0.42} rotationY={0.5} />
      <House x={r * 0.2} z={-r * 0.48} rotationY={0.12} />
      <House x={-r * 0.38} z={-r * 0.28} rotationY={-0.45} />

      <Tree x={r * 0.08} z={r * 0.58} scale={0.9} />
      <Tree x={-r * 0.62} z={r * 0.12} scale={0.75} />
      <Tree x={r * 0.48} z={-r * 0.15} scale={1} />
      <Tree x={-r * 0.22} z={-r * 0.55} scale={0.85} />
      <Tree x={r * 0.65} z={r * 0.08} scale={0.7} />
      <Tree x={-r * 0.08} z={-r * 0.08} scale={0.65} />
      <Tree x={r * -0.35} z={r * 0.22} scale={0.8} />
      <Tree x={r * 0.28} z={r * -0.62} scale={0.95} />
    </group>
  );
}

/** One-time camera placement; slider/orbit changes do not reset the view. */
function OrbitOriginCamera({ gridSize, height }: { gridSize: number; height: number }) {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const controls = useThree((s) => s.controls);
  const didInit = useRef(false);

  useEffect(() => {
    if (didInit.current) return;
    didInit.current = true;

    const span = Math.max(gridSize * 0.45, height * 1.1, 90);
    const dist = THREE.MathUtils.clamp(span * 0.36, 55, 520);

    const dir = new THREE.Vector3(0.85, 0.38, 0.85).normalize();
    camera.position.copy(dir.multiplyScalar(dist));
    camera.near = 0.4;
    camera.far = Math.max(dist * 80, 8000);
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();

    const oc = controls as unknown as { target: THREE.Vector3; update: () => void } | null;
    if (oc?.update) {
      oc.target.set(0, 0, 0);
      oc.update();
    }
  }, [camera, controls, gridSize, height]);

  return null;
}

// ---------------------------------------------------------------------------

export type ThreeViewProps = {
  height: number;
  /** Positive degrees below horizon; one entry per along-track waypoint. */
  pitchDegs: number[];
  spacing: number;
  /** 0–100 mean adjacent-pair IoU. */
  overlapPercent: number;
};

function footprintColor(i: number, n: number): string {
  const t = n <= 1 ? 0 : i / (n - 1);
  const h = 200 + t * 55;
  const l = 72 - t * 8;
  return `hsl(${h}, 72%, ${l}%)`;
}

export default function ThreeView({
  height,
  pitchDegs,
  spacing,
  overlapPercent,
}: ThreeViewProps) {
  const n = Math.max(1, pitchDegs.length);

  const alongPositions = useMemo(
    () => Array.from({ length: n }, (_, i) => (i - (n - 1) / 2) * spacing),
    [n, spacing],
  );

  const footprints = useMemo(
    () => alongPositions.map((x, i) => groundFootprint(x, height, pitchDegs[i] ?? pitchDegs[0])),
    [alongPositions, height, pitchDegs],
  );

  const gridSize = useMemo(() => {
    const all = footprints.flat();
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    for (const [x, y] of all) {
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
    }
    for (const x of alongPositions) {
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
    }
    const span = Math.max(maxX - minX, maxY - minY, spacing * Math.max(2, n) * 0.75, height * 0.08);
    return Math.min(span * 1.45, 6000);
  }, [footprints, alongPositions, spacing, height, n]);

  const dronePositions = useMemo(
    () => alongPositions.map((x) => mathDroneToThree(x, height, 0)),
    [alongPositions, height],
  );

  const lineOpacity = n > 14 ? 0.28 : n > 8 ? 0.4 : 0.55;

  const maxOrbit = useMemo(
    () => Math.max(gridSize * 4, height * 6, 2000),
    [gridSize, height],
  );

  return (
    <div
      data-testid="three-view-container"
      className={styles.threeViewWrap}
      style={{
        background: '#0d0d0d',
        border: '1px solid #1e1e1e',
        borderRadius: 14,
        height: 400,
        width: '100%',
      }}
    >
      <Canvas
        camera={{ fov: 48, near: 0.1, far: 500000 }}
        gl={{ antialias: true, alpha: false }}
        shadows
        onCreated={({ gl }) => {
          gl.setClearColor('#0d0d0d');
          gl.shadowMap.enabled = true;
          gl.shadowMap.type = THREE.PCFSoftShadowMap;
        }}
      >
        <ambientLight intensity={0.45} />
        <directionalLight
          castShadow
          position={[120, 180, 80]}
          intensity={1.05}
          shadow-mapSize-width={1024}
          shadow-mapSize-height={1024}
          shadow-camera-near={10}
          shadow-camera-far={8000}
          shadow-camera-left={-600}
          shadow-camera-right={600}
          shadow-camera-top={600}
          shadow-camera-bottom={-600}
        />
        <hemisphereLight args={['#87a4c4', '#1a1814', 0.35]} />

        <OrbitControls
          makeDefault
          target={[0, 0, 0]}
          enablePan={false}
          enableDamping
          dampingFactor={0.1}
          minDistance={25}
          maxDistance={maxOrbit}
          minPolarAngle={0.15}
          maxPolarAngle={Math.PI / 2 - 0.08}
        />

        <OrbitOriginCamera gridSize={gridSize} height={height} />

        <group rotation={[0, Math.PI / 2, 0]}>
          <group>
            <GroundGrid size={gridSize} />
            <GroundAnchors gridSize={gridSize} />

            {footprints.map((quad, i) => {
              const dronePos = dronePositions[i];
              const col = footprintColor(i, n);
              const fpOpacity = 0.14 + (i / Math.max(1, n - 1)) * 0.12;
              return (
                <group key={i}>
                  <DroneMarker position={dronePos} />
                  <FrustumLines dronePos={dronePos} quad={quad} lineOpacity={lineOpacity} />
                  <FootprintQuad quad={quad} color={col} opacity={fpOpacity} />
                </group>
              );
            })}
          </group>
        </group>
      </Canvas>

      <div className={styles.threeViewHud} data-testid="three-view-hud">
        <div className={styles.threeViewHudPrimary} data-testid="overlap-hud-primary">
          Overlap: {overlapPercent.toFixed(0)}%
        </div>
        <div className={styles.threeViewHudMeta} data-testid="overlap-hud-meta">
          {n} pts · {spacing.toFixed(0)} ft apart · {height} ft AGL
        </div>
      </div>
    </div>
  );
}
