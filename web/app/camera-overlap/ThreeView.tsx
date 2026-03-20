'use client';

import React, { useMemo, useEffect, useRef, useState } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, Line, Html } from '@react-three/drei';
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

function DroneMarker({
  position,
  pitchDeg,
  heightFt,
}: {
  position: [number, number, number];
  pitchDeg?: number;
  heightFt?: number;
}) {
  const y = position[1];
  const r = Math.max(2, y * 0.009);
  const [hovered, setHovered] = useState(false);

  return (
    <group
      position={position}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true); }}
      onPointerOut={() => setHovered(false)}
    >
      <mesh>
        <sphereGeometry args={[r, 12, 12]} />
        <meshStandardMaterial color={hovered ? '#ffd60a' : '#f5f5f7'} />
      </mesh>
      <mesh position={[0, -y / 2, 0]}>
        <cylinderGeometry args={[0.5, 0.5, y, 6]} />
        <meshStandardMaterial color="#333" transparent opacity={0.25} />
      </mesh>
      {hovered && pitchDeg !== undefined && (
        <Html
          position={[0, r + 5, 0]}
          center
          distanceFactor={120}
          style={{ pointerEvents: 'none' }}
        >
          <div style={{
            background: 'rgba(10, 10, 10, 0.92)',
            border: '1px solid #3a8eff',
            borderRadius: 6,
            color: '#f5f5f7',
            fontFamily: 'ui-monospace, monospace',
            fontSize: 11,
            fontWeight: 500,
            padding: '4px 9px',
            whiteSpace: 'nowrap',
          }}>
            −{pitchDeg.toFixed(1)}° · {heightFt ?? Math.round(y)} ft AGL
          </div>
        </Html>
      )}
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

// ---------------------------------------------------------------------------
// Fixed town scene — absolute positions in feet, never re-randomised.
// ---------------------------------------------------------------------------

function Road({ x, z, w, d }: { x: number; z: number; w: number; d: number }) {
  return (
    <mesh position={[x, 0.13, z]} receiveShadow>
      <boxGeometry args={[w, 0.26, d]} />
      <meshStandardMaterial color="#1e1e1e" roughness={0.96} />
    </mesh>
  );
}

function Building({
  x, z, w, d, h, color,
}: { x: number; z: number; w: number; d: number; h: number; color: string }) {
  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, h / 2, 0]} castShadow receiveShadow>
        <boxGeometry args={[w, h, d]} />
        <meshStandardMaterial color={color} roughness={0.72} metalness={0.08} />
      </mesh>
      <mesh position={[0, h + 0.6, 0]}>
        <boxGeometry args={[w + 0.5, 1.2, d + 0.5]} />
        <meshStandardMaterial color="#181818" roughness={0.9} />
      </mesh>
    </group>
  );
}

function TreeFixed({
  x, z, trunkH, canopyH, canopyR,
}: { x: number; z: number; trunkH: number; canopyH: number; canopyR: number }) {
  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, trunkH / 2, 0]} castShadow>
        <cylinderGeometry args={[trunkH * 0.028, trunkH * 0.042, trunkH, 7]} />
        <meshStandardMaterial color="#4a3828" roughness={0.95} />
      </mesh>
      <mesh position={[0, trunkH + canopyH * 0.36, 0]} castShadow>
        <coneGeometry args={[canopyR, canopyH * 0.72, 8]} />
        <meshStandardMaterial color="#2d4a2d" roughness={0.88} />
      </mesh>
      <mesh position={[0, trunkH + canopyH * 0.8, 0]} castShadow>
        <coneGeometry args={[canopyR * 0.6, canopyH * 0.42, 8]} />
        <meshStandardMaterial color="#355c35" roughness={0.82} />
      </mesh>
    </group>
  );
}

/** Dense town at fixed world coordinates — independent of any scene parameter. */
function TownScene() {
  return (
    <group>
      {/* Ground plane — extends well beyond town to fill the horizon */}
      <mesh position={[0, 0.04, 0]} receiveShadow>
        <boxGeometry args={[3000, 0.08, 3000]} />
        <meshStandardMaterial color="#1c2a1c" roughness={1} />
      </mesh>

      {/* ── Road grid ── */}
      <Road x={0}    z={0}    w={900} d={24} />  {/* main E-W */}
      <Road x={0}    z={0}    w={24}  d={900} /> {/* main N-S */}
      <Road x={0}    z={148}  w={700} d={14} />
      <Road x={0}    z={-148} w={700} d={14} />
      <Road x={148}  z={0}    w={14}  d={700} />
      <Road x={-148} z={0}    w={14}  d={700} />
      <Road x={0}    z={300}  w={500} d={12} />
      <Road x={0}    z={-300} w={500} d={12} />
      <Road x={300}  z={0}    w={12}  d={500} />
      <Road x={-300} z={0}    w={12}  d={500} />

      {/* ── NE block: office/commercial ── */}
      <Building x={52}  z={50}  w={36} d={30} h={58}  color="#5a6070" />
      <Building x={98}  z={55}  w={28} d={24} h={38}  color="#7a6858" />
      <Building x={68}  z={98}  w={44} d={34} h={24}  color="#5c5040" />
      <Building x={114} z={96}  w={22} d={22} h={72}  color="#4a5060" />
      <Building x={52}  z={80}  w={18} d={20} h={42}  color="#626870" />
      <Building x={78}  z={115} w={32} d={28} h={32}  color="#506268" />

      {/* ── NW block: residential ── */}
      <Building x={-52}  z={48}  w={30} d={24} h={20} color="#6d5b4c" />
      <Building x={-88}  z={62}  w={28} d={22} h={18} color="#7a6050" />
      <Building x={-62}  z={102} w={26} d={22} h={22} color="#6a5848" />
      <Building x={-110} z={88}  w={24} d={20} h={16} color="#705a48" />
      <Building x={-120} z={52}  w={30} d={26} h={18} color="#5a5048" />
      <Building x={-78}  z={120} w={28} d={24} h={20} color="#685840" />

      {/* ── SW block: residential ── */}
      <Building x={-55}  z={-50}  w={28} d={22} h={18} color="#665242" />
      <Building x={-92}  z={-68}  w={24} d={20} h={16} color="#6e5a48" />
      <Building x={-62}  z={-102} w={30} d={24} h={22} color="#6a5040" />
      <Building x={-114} z={-96}  w={22} d={18} h={14} color="#584840" />
      <Building x={-75}  z={-120} w={26} d={22} h={18} color="#6a5848" />

      {/* ── SE block: mixed use ── */}
      <Building x={58}   z={-52}  w={32} d={26} h={30} color="#5e6268" />
      <Building x={102}  z={-60}  w={26} d={22} h={44} color="#4e5862" />
      <Building x={65}   z={-102} w={38} d={30} h={20} color="#7a6850" />
      <Building x={114}  z={-100} w={24} d={22} h={52} color="#4a5068" />
      <Building x={75}   z={-118} w={28} d={24} h={28} color="#586060" />

      {/* ── Outer ring ── */}
      <Building x={195}  z={62}   w={36} d={30} h={22} color="#5a5040" />
      <Building x={210}  z={-58}  w={30} d={24} h={18} color="#6a5848" />
      <Building x={-192} z={58}   w={28} d={24} h={20} color="#605848" />
      <Building x={-205} z={-62}  w={32} d={26} h={16} color="#6e5c4a" />
      <Building x={62}   z={205}  w={30} d={26} h={24} color="#5e5240" />
      <Building x={-60}  z={198}  w={28} d={22} h={18} color="#685848" />
      <Building x={58}   z={-205} w={34} d={28} h={22} color="#5a5040" />
      <Building x={-58}  z={-200} w={26} d={22} h={20} color="#6a5848" />

      {/* ── Tall trees: 150–200 ft — well outside town, for altitude reference ── */}
      <TreeFixed x={60}   z={340}  trunkH={70} canopyH={135} canopyR={35} />
      <TreeFixed x={-80}  z={360}  trunkH={74} canopyH={142} canopyR={37} />
      <TreeFixed x={120}  z={310}  trunkH={65} canopyH={125} canopyR={32} />
      <TreeFixed x={340}  z={55}   trunkH={62} canopyH={120} canopyR={31} />
      <TreeFixed x={370}  z={-70}  trunkH={72} canopyH={138} canopyR={36} />
      <TreeFixed x={320}  z={130}  trunkH={68} canopyH={130} canopyR={34} />
      <TreeFixed x={-345} z={60}   trunkH={64} canopyH={118} canopyR={30} />
      <TreeFixed x={-370} z={-55}  trunkH={76} canopyH={144} canopyR={37} />
      <TreeFixed x={-310} z={125}  trunkH={66} canopyH={126} canopyR={33} />
      <TreeFixed x={55}   z={-340} trunkH={68} canopyH={132} canopyR={34} />
      <TreeFixed x={-75}  z={-365} trunkH={72} canopyH={140} canopyR={36} />
      <TreeFixed x={125}  z={-315} trunkH={62} canopyH={122} canopyR={31} />
      <TreeFixed x={-120} z={-310} trunkH={70} canopyH={136} canopyR={35} />
      <TreeFixed x={310}  z={-120} trunkH={64} canopyH={124} canopyR={32} />
      <TreeFixed x={-310} z={-130} trunkH={68} canopyH={130} canopyR={34} />
      <TreeFixed x={400}  z={400}  trunkH={74} canopyH={146} canopyR={38} />
      <TreeFixed x={-400} z={400}  trunkH={70} canopyH={138} canopyR={36} />
      <TreeFixed x={400}  z={-400} trunkH={72} canopyH={142} canopyR={37} />
      <TreeFixed x={-400} z={-400} trunkH={66} canopyH={128} canopyR={33} />

      {/* ── Medium trees: 80–120 ft — suburban fringe ── */}
      <TreeFixed x={220}  z={220}  trunkH={44} canopyH={96}  canopyR={24} />
      <TreeFixed x={-225} z={215}  trunkH={40} canopyH={88}  canopyR={22} />
      <TreeFixed x={215}  z={-222} trunkH={48} canopyH={102} canopyR={26} />
      <TreeFixed x={-218} z={-225} trunkH={42} canopyH={90}  canopyR={23} />
      <TreeFixed x={255}  z={60}   trunkH={38} canopyH={82}  canopyR={20} />
      <TreeFixed x={260}  z={-55}  trunkH={44} canopyH={94}  canopyR={24} />
      <TreeFixed x={-258} z={65}   trunkH={40} canopyH={86}  canopyR={21} />
      <TreeFixed x={-255} z={-58}  trunkH={46} canopyH={98}  canopyR={25} />
      <TreeFixed x={62}   z={255}  trunkH={42} canopyH={90}  canopyR={23} />
      <TreeFixed x={-60}  z={260}  trunkH={38} canopyH={84}  canopyR={21} />
      <TreeFixed x={65}   z={-258} trunkH={44} canopyH={96}  canopyR={24} />
      <TreeFixed x={-62}  z={-255} trunkH={40} canopyH={88}  canopyR={22} />

      {/* ── Street trees: 40–60 ft — lining the outer roads ── */}
      <TreeFixed x={40}   z={170}  trunkH={20} canopyH={44} canopyR={11} />
      <TreeFixed x={82}   z={170}  trunkH={18} canopyH={40} canopyR={10} />
      <TreeFixed x={-40}  z={-170} trunkH={22} canopyH={46} canopyR={12} />
      <TreeFixed x={-82}  z={-170} trunkH={19} canopyH={41} canopyR={10} />
      <TreeFixed x={170}  z={42}   trunkH={21} canopyH={44} canopyR={11} />
      <TreeFixed x={170}  z={82}   trunkH={18} canopyH={39} canopyR={10} />
      <TreeFixed x={-170} z={-42}  trunkH={20} canopyH={42} canopyR={11} />
      <TreeFixed x={-170} z={-82}  trunkH={19} canopyH={40} canopyR={10} />
      <TreeFixed x={-170} z={42}   trunkH={22} canopyH={45} canopyR={12} />
      <TreeFixed x={-170} z={82}   trunkH={18} canopyH={38} canopyR={10} />
      <TreeFixed x={170}  z={-42}  trunkH={21} canopyH={43} canopyR={11} />
      <TreeFixed x={170}  z={-82}  trunkH={19} canopyH={40} canopyR={10} />
    </group>
  );
}

// ---------------------------------------------------------------------------

/** Camera placed once on first mount — orbit controls preserve position thereafter. */
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
  /** Positive degrees below horizon; one entry per waypoint / capture. */
  pitchDegs: number[];
  spacing: number;
  /** 0–100 mean adjacent-pair IoU. */
  overlapPercent: number;
  /** When true, visualise a flat-spin fan instead of the linear flight line. */
  spinMode?: boolean;
  /** Distance between successive captures along the flight path (ft). Spin mode only. */
  captureIntervalFt?: number;
  /** Total heading arc swept during the capture window (degrees). Spin mode only. */
  captureArcDeg?: number;
};

function footprintColor(i: number, n: number): string {
  const t = n <= 1 ? 0 : i / (n - 1);
  const h = 200 + t * 55;
  const l = 72 - t * 8;
  return `hsl(${h}, 72%, ${l}%)`;
}

function spinFootprintColor(headingDeg: number, arcDeg: number): string {
  const t = arcDeg > 0 ? headingDeg / arcDeg : 0;
  const h = 200 - t * 120;
  return `hsl(${(h + 360) % 360}, 80%, 62%)`;
}

export default function ThreeView({
  height,
  pitchDegs,
  spacing,
  overlapPercent,
  spinMode = false,
  captureIntervalFt = 6,
  captureArcDeg = 180,
}: ThreeViewProps) {

  // ── Spin mode ──────────────────────────────────────────────────────────────
  const numSpinCaptures = useMemo(
    () => Math.max(2, Math.min(30, Math.round(spacing / captureIntervalFt))),
    [spacing, captureIntervalFt],
  );

  const spinHeadings = useMemo(
    () => Array.from({ length: numSpinCaptures }, (_, i) =>
      numSpinCaptures > 1 ? (i / (numSpinCaptures - 1)) * captureArcDeg : 0,
    ),
    [numSpinCaptures, captureArcDeg],
  );

  const spinAlongX = useMemo(
    () => Array.from({ length: numSpinCaptures }, (_, i) =>
      (i - (numSpinCaptures - 1) / 2) * captureIntervalFt,
    ),
    [numSpinCaptures, captureIntervalFt],
  );

  const spinFootprints = useMemo(() => {
    if (!spinMode) return [];
    return spinAlongX.map((x, i) => {
      const pitch = pitchDegs[i % Math.max(1, pitchDegs.length)] ?? pitchDegs[0] ?? 30;
      return groundFootprint(x, height, pitch, spinHeadings[i]);
    });
  }, [spinMode, spinAlongX, spinHeadings, height, pitchDegs]);

  // ── Linear mode ────────────────────────────────────────────────────────────
  const n = Math.max(1, pitchDegs.length);

  const alongPositions = useMemo(
    () => Array.from({ length: n }, (_, i) => (i - (n - 1) / 2) * spacing),
    [n, spacing],
  );

  const linearFootprints = useMemo(
    () => alongPositions.map((x, i) => groundFootprint(x, height, pitchDegs[i] ?? pitchDegs[0])),
    [alongPositions, height, pitchDegs],
  );

  // ── Active set ─────────────────────────────────────────────────────────────
  const activeFootprints = spinMode ? spinFootprints : linearFootprints;
  const activeDroneX = spinMode ? spinAlongX : alongPositions;
  const activeN = spinMode ? numSpinCaptures : n;
  const activePitchDegs = spinMode
    ? spinAlongX.map((_, i) => pitchDegs[i % Math.max(1, pitchDegs.length)] ?? pitchDegs[0] ?? 30)
    : pitchDegs;

  const gridSize = useMemo(() => {
    if (activeFootprints.length === 0) return 800;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const fp of activeFootprints) {
      for (const [x, y] of fp) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
    for (const x of activeDroneX) {
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
    }
    const span = Math.max(maxX - minX, maxY - minY, 80);
    return Math.min(span * 1.5, 8000);
  }, [activeFootprints, activeDroneX]);

  const dronePositions = useMemo(
    () => activeDroneX.map((x) => mathDroneToThree(x, height, 0)),
    [activeDroneX, height],
  );

  const lineOpacity = activeN > 14 ? 0.22 : activeN > 8 ? 0.35 : 0.52;

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
          minPolarAngle={0.08}
          maxPolarAngle={Math.PI / 2 - 0.08}
        />

        <OrbitOriginCamera gridSize={gridSize} height={height} />

        <group rotation={[0, Math.PI / 2, 0]}>
          <TownScene />

          {activeFootprints.map((quad, i) => {
            const dronePos = dronePositions[i];
            const col = spinMode
              ? spinFootprintColor(spinHeadings[i], captureArcDeg)
              : footprintColor(i, activeN);
            const fpOpacity = spinMode
              ? 0.18
              : 0.14 + (i / Math.max(1, activeN - 1)) * 0.12;
            return (
              <group key={i}>
                <DroneMarker
                  position={dronePos}
                  pitchDeg={activePitchDegs[i]}
                  heightFt={height}
                />
                <FrustumLines dronePos={dronePos} quad={quad} lineOpacity={lineOpacity} />
                <FootprintQuad quad={quad} color={col} opacity={fpOpacity} />
              </group>
            );
          })}
        </group>
      </Canvas>

      <div className={styles.threeViewHud} data-testid="three-view-hud">
        {spinMode ? (
          <>
            <div className={styles.threeViewHudPrimary} data-testid="overlap-hud-primary">
              Spin: {captureArcDeg.toFixed(0)}° arc
            </div>
            <div className={styles.threeViewHudMeta} data-testid="overlap-hud-meta">
              {numSpinCaptures} captures · {captureIntervalFt} ft · {overlapPercent.toFixed(0)}% adj overlap · {height} ft AGL
            </div>
          </>
        ) : (
          <>
            <div className={styles.threeViewHudPrimary} data-testid="overlap-hud-primary">
              Overlap: {overlapPercent.toFixed(0)}%
            </div>
            <div className={styles.threeViewHudMeta} data-testid="overlap-hud-meta">
              {n} pts · {spacing.toFixed(0)} ft apart · {height} ft AGL
            </div>
          </>
        )}
      </div>
    </div>
  );
}
