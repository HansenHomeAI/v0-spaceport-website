'use client';

import React, {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, Line, Html, useCursor } from '@react-three/drei';
import * as THREE from 'three';
import {
  TAN_H,
  TAN_V,
  groundFootprint,
  type GroundQuad,
} from '../../lib/cameraOverlapMath';
import styles from './page.module.css';

function HoverSceneCursor({ active }: { active: boolean }) {
  useCursor(active);
  return null;
}

/** Feet — raycast far enough to cover the whole town + distant trees from survey altitude. */
const COVERAGE_RAY_MAX_FT = 72_000;
/** Minimum visualization depth (ft) for frustum mouth when upper rays are above horizon. */
const FRUSTUM_VIS_MIN_EXTENT_FT = 14_000;
/** Delay before hover shows tag / frustum emphasis (avoids flicker when scanning the scene). */
const HOVER_HIGHLIGHT_HOLD_MS = 1000;

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

type CoveragePatchData = {
  position: [number, number, number];
  normal: [number, number, number];
  color: string;
  size: number;
  opacity: number;
};

function sampleOffsets(count: number): number[] {
  if (count <= 1) return [0];
  return Array.from({ length: count }, (_, i) => (((i / (count - 1)) * 2) - 1) * 0.92);
}

function coverageSamplingFor(activeCount: number): { cols: number; rows: number; size: number } {
  if (activeCount <= 4) return { cols: 18, rows: 13, size: 11 };
  if (activeCount <= 10) return { cols: 14, rows: 10, size: 9 };
  return { cols: 11, rows: 8, size: 8 };
}

function buildCameraRayVectorLocal(
  pitchDeg: number,
  headingDeg: number,
  alongSample: number,
  crossSample: number,
): THREE.Vector3 {
  const theta = (pitchDeg * Math.PI) / 180;
  const H = (headingDeg * Math.PI) / 180;
  const sinT = Math.sin(theta);
  const cosT = Math.cos(theta);
  const sinH = Math.sin(H);
  const cosH = Math.cos(H);

  // Same basis as `groundFootprint`, converted into the local coordinates of the
  // rotated scene group: three = [math.x, math.z, math.y].
  const los = new THREE.Vector3(sinH * cosT, -sinT, cosH * cosT);
  const right = new THREE.Vector3(cosH, 0, -sinH);
  const up = new THREE.Vector3(sinH * sinT, cosT, cosH * sinT);

  // along = image horizontal (75°), cross = image vertical (55°) — matches groundFootprint
  return los
    .addScaledVector(right, alongSample * TAN_H)
    .addScaledVector(up, crossSample * TAN_V);
}

function buildCameraRayLocal(
  pitchDeg: number,
  headingDeg: number,
  alongSample: number,
  crossSample: number,
): THREE.Vector3 {
  return buildCameraRayVectorLocal(pitchDeg, headingDeg, alongSample, crossSample).normalize();
}

/** World-space intersection with horizontal plane y = planeY (infinite ground). */
function rayPlaneY(
  origin: THREE.Vector3,
  dir: THREE.Vector3,
  planeY: number,
  tMin: number,
  tMax: number,
): THREE.Vector3 | null {
  if (Math.abs(dir.y) < 1e-8) return null;
  const t = (planeY - origin.y) / dir.y;
  if (t < tMin || t > tMax) return null;
  return origin.clone().addScaledVector(dir, t);
}

function CoveragePatch({
  position,
  normal,
  color,
  size,
  opacity,
}: CoveragePatchData) {
  const quaternion = useMemo(() => {
    const q = new THREE.Quaternion();
    q.setFromUnitVectors(
      new THREE.Vector3(0, 0, 1),
      new THREE.Vector3(normal[0], normal[1], normal[2]).normalize(),
    );
    return q;
  }, [normal]);

  return (
    <mesh position={position} quaternion={quaternion} renderOrder={8}>
      <planeGeometry args={[size, size]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        depthWrite={false}
        side={THREE.DoubleSide}
        polygonOffset
        polygonOffsetFactor={-3}
        polygonOffsetUnits={-3}
        toneMapped={false}
      />
    </mesh>
  );
}

function CoverageOverlay({
  spaceRef,
  coverageRootRef,
  dronePositions,
  pitchDegs,
  headingDegs,
  colors,
  emphasizeIndex,
}: {
  spaceRef: React.RefObject<THREE.Group | null>;
  coverageRootRef: React.RefObject<THREE.Group | null>;
  dronePositions: [number, number, number][];
  pitchDegs: number[];
  headingDegs: number[];
  colors: string[];
  emphasizeIndex: number | null;
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const patches = useMemo(() => {
    if (!mounted || !spaceRef.current || !coverageRootRef.current || dronePositions.length === 0) {
      return [] as CoveragePatchData[];
    }

    const { cols, rows, size } = coverageSamplingFor(dronePositions.length);
    const alongOffsets = sampleOffsets(cols);
    const crossOffsets = sampleOffsets(rows);
    const raycaster = new THREE.Raycaster();
    const results: CoveragePatchData[] = [];
    const space = spaceRef.current;
    const coverageRoot = coverageRootRef.current;

    for (let i = 0; i < dronePositions.length; i++) {
      const dronePos = dronePositions[i];
      const pitchDeg = pitchDegs[i] ?? pitchDegs[0] ?? 30;
      const headingDeg = headingDegs[i] ?? 0;
      const color = colors[i] ?? colors[0] ?? '#3a8eff';
      const originWorld = space.localToWorld(new THREE.Vector3(...dronePos));

      for (const alongSample of alongOffsets) {
        for (const crossSample of crossOffsets) {
          const dirLocal = buildCameraRayLocal(pitchDeg, headingDeg, alongSample, crossSample);
          const dirWorld = dirLocal.clone().transformDirection(space.matrixWorld);
          raycaster.set(originWorld, dirWorld);
          raycaster.near = 0.5;
          const far = Math.max(COVERAGE_RAY_MAX_FT, dronePos[1] * 120);
          raycaster.far = far;

          const hit = raycaster.intersectObject(coverageRoot, true).find((entry) => entry.face !== null);

          let pointWorld: THREE.Vector3;
          let normalWorld: THREE.Vector3;

          if (hit?.face) {
            normalWorld = hit.face.normal.clone().transformDirection(hit.object.matrixWorld).normalize();
            pointWorld = hit.point.clone().addScaledVector(normalWorld, 0.25);
          } else {
            // Town ground mesh is finite (~3000 ft); shallow / long rays miss it. Project to y=0
            // so colored coverage matches the full frustum extent on the ground plane.
            const ground = rayPlaneY(originWorld, dirWorld, 0, 0.5, far);
            if (!ground) continue;
            normalWorld = new THREE.Vector3(0, 1, 0);
            pointWorld = ground.clone().addScaledVector(normalWorld, 0.25);
          }

          results.push({
            position: [pointWorld.x, pointWorld.y, pointWorld.z],
            normal: [normalWorld.x, normalWorld.y, normalWorld.z],
            color,
            size,
            opacity: emphasizeIndex === i ? 0.52 : 0.32,
          });
        }
      }
    }

    return results;
  }, [mounted, spaceRef, coverageRootRef, dronePositions, pitchDegs, headingDegs, colors, emphasizeIndex]);

  return (
    <group>
      {patches.map((patch, i) => (
        <CoveragePatch
          key={`${i}-${patch.position[0].toFixed(1)}-${patch.position[1].toFixed(1)}-${patch.position[2].toFixed(1)}`}
          {...patch}
        />
      ))}
    </group>
  );
}

// ---------------------------------------------------------------------------

export type DroneMarkerHandle = { focus: () => void };

const DroneMarker = forwardRef<
  DroneMarkerHandle,
  {
    position: [number, number, number];
    pitchDeg?: number;
    headingDeg: number;
    heightFt?: number;
    isHighlighted: boolean;
    showTag: boolean;
    onTagActivate?: () => void;
  }
>(function DroneMarker(
  {
    position,
    pitchDeg,
    headingDeg,
    heightFt,
    isHighlighted,
    showTag,
    onTagActivate,
  },
  ref,
) {
  const y = position[1];
  const r = Math.max(2, y * 0.009);
  const groupRef = useRef<THREE.Group>(null);
  const { camera, controls } = useThree();

  const focusCamera = useCallback(() => {
    if (!groupRef.current) return;
    const p = pitchDeg ?? 0;
    const h = headingDeg;
    const losLocal = buildCameraRayLocal(p, h, 0, 0);
    const losWorld = losLocal.clone().transformDirection(groupRef.current.matrixWorld);
    const droneWorld = new THREE.Vector3().setFromMatrixPosition(groupRef.current.matrixWorld);
    const pullBack = Math.max(95, y * 0.95);
    const lookAhead = Math.max(70, y * 0.55);
    camera.position.copy(droneWorld.clone().addScaledVector(losWorld, -pullBack));
    const oc = controls as unknown as { target: THREE.Vector3; update: () => void } | null;
    if (oc?.target) {
      oc.target.copy(droneWorld.clone().addScaledVector(losWorld, lookAhead));
      oc.update?.();
    }
  }, [camera, controls, headingDeg, pitchDeg, y]);

  useImperativeHandle(ref, () => ({ focus: focusCamera }), [focusCamera]);

  return (
    <group ref={groupRef} position={position}>
      <mesh>
        <sphereGeometry args={[r, 12, 12]} />
        <meshStandardMaterial
          color={isHighlighted ? '#ffd60a' : '#f5f5f7'}
          emissive={isHighlighted ? '#ffd60a' : '#222'}
          emissiveIntensity={isHighlighted ? 0.35 : 0.16}
        />
      </mesh>
      <mesh position={[0, -y / 2, 0]}>
        <cylinderGeometry args={[0.5, 0.5, y, 6]} />
        <meshStandardMaterial color="#333" transparent opacity={0.25} />
      </mesh>
      {showTag && pitchDeg !== undefined && (
        <Html
          position={[0, r + 5, 0]}
          center
          transform={false}
          style={{ pointerEvents: 'auto' }}
          zIndexRange={[200, 0]}
        >
          <div
            className={styles.waypointTag}
            role="button"
            tabIndex={0}
            onClick={(e) => {
              e.stopPropagation();
              onTagActivate?.();
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onTagActivate?.();
              }
            }}
          >
            −{pitchDeg.toFixed(1)}° · {heightFt ?? Math.round(y)} ft AGL
          </div>
        </Html>
      )}
    </group>
  );
});

DroneMarker.displayName = 'DroneMarker';

function FootprintQuad({
  quad,
  color,
  opacity,
  emphasize = false,
}: {
  quad: GroundQuad;
  color: string;
  opacity: number;
  emphasize?: boolean;
}) {
  const geo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    const verts: number[] = [];
    for (const c of quad) {
      const [tx, ty, tz] = mathGroundToThree(c);
      verts.push(tx, ty + 0.35, tz);
    }
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(verts), 3));
    g.setIndex([0, 1, 2, 0, 2, 3]);
    g.computeVertexNormals();
    return g;
  }, [quad]);

  const effOpacity = Math.min(opacity * (emphasize ? 1.45 : 1), 0.42);

  return (
    <mesh geometry={geo} renderOrder={3}>
      <meshBasicMaterial
        color={color}
        transparent
        opacity={effOpacity}
        side={THREE.DoubleSide}
        depthWrite={false}
        polygonOffset
        polygonOffsetFactor={-2}
        polygonOffsetUnits={-2}
        toneMapped={false}
      />
    </mesh>
  );
}

/**
 * True camera frustum wireframe.  Each of the 4 edge rays follows its real
 * direction from `buildCameraRayVectorLocal` so the frustum is visually
 * centered on the optical-axis vector regardless of pitch.
 *
 * Downward rays end at the ground plane (y ≈ 0).  Above-horizon rays extend to
 * `visFar` (tens of k ft) so the wireframe mouth matches scene scale.  Colored
 * coverage uses the same long raycast range to paint overlap on all geometry.
 */
function FrustumLines({
  dronePos,
  pitchDeg,
  headingDeg,
  lineOpacity = 0.55,
  emphasize = false,
}: {
  dronePos: [number, number, number];
  pitchDeg: number;
  headingDeg: number;
  lineOpacity?: number;
  emphasize?: boolean;
}) {
  const lines = useMemo(() => {
    const edges: Array<[THREE.Vector3, THREE.Vector3]> = [];
    const origin = new THREE.Vector3(dronePos[0], dronePos[1], dronePos[2]);

    const h = dronePos[1];
    const centerRay = buildCameraRayVectorLocal(pitchDeg, headingDeg, 0, 0);
    const centerT = centerRay.y < -1e-6 ? h / -centerRay.y : h * 5;
    /** Shared far depth so wireframe extends far enough to read overlap vs scene scale. */
    const visFar = Math.max(centerT * 6, h * 72, FRUSTUM_VIS_MIN_EXTENT_FT);

    const cornerSamples: [number, number][] = [[-1, -1], [-1, 1], [1, 1], [1, -1]];
    const endpoints = cornerSamples.map(([sv, sh]) => {
      const ray = buildCameraRayVectorLocal(pitchDeg, headingDeg, sv, sh);
      const t = ray.y < -1e-6 ? h / -ray.y : visFar;
      return new THREE.Vector3(
        dronePos[0] + ray.x * t,
        dronePos[1] + ray.y * t,
        dronePos[2] + ray.z * t,
      );
    });

    for (const ep of endpoints) {
      edges.push([origin.clone(), ep]);
    }
    for (let i = 0; i < 4; i++) {
      edges.push([endpoints[i], endpoints[(i + 1) % 4]]);
    }
    return edges;
  }, [dronePos, pitchDeg, headingDeg]);

  const op = Math.min(lineOpacity + (emphasize ? 0.38 : 0), 0.99);
  const col = emphasize ? '#e8eef8' : '#888';

  return (
    <>
      {lines.map((pts, i) => (
        <Line
          key={i}
          points={[pts[0], pts[1]]}
          color={col}
          lineWidth={emphasize ? 2.25 : 1}
          transparent
          opacity={op}
        />
      ))}
    </>
  );
}

function DirectionVector({
  dronePos,
  pitchDeg,
  headingDeg,
  length = 22,
  emphasize = false,
}: {
  dronePos: [number, number, number];
  pitchDeg: number;
  headingDeg: number;
  length?: number;
  emphasize?: boolean;
}) {
  const end = useMemo(() => {
    const dir = buildCameraRayLocal(pitchDeg, headingDeg, 0, 0);
    return new THREE.Vector3(
      dronePos[0] + dir.x * length,
      dronePos[1] + dir.y * length,
      dronePos[2] + dir.z * length,
    );
  }, [dronePos, pitchDeg, headingDeg, length]);

  return (
    <Line
      points={[
        new THREE.Vector3(dronePos[0], dronePos[1], dronePos[2]),
        end,
      ]}
      color={emphasize ? '#ffffff' : '#ffffff'}
      lineWidth={emphasize ? 3 : 2}
      transparent
      opacity={emphasize ? 1 : 0.95}
    />
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
      <mesh position={[0, h + 0.6, 0]} receiveShadow>
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
      <mesh position={[0, trunkH / 2, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[trunkH * 0.028, trunkH * 0.042, trunkH, 7]} />
        <meshStandardMaterial color="#4a3828" roughness={0.95} />
      </mesh>
      <mesh position={[0, trunkH + canopyH * 0.36, 0]} castShadow receiveShadow>
        <coneGeometry args={[canopyR, canopyH * 0.72, 8]} />
        <meshStandardMaterial color="#2d4a2d" roughness={0.88} />
      </mesh>
      <mesh position={[0, trunkH + canopyH * 0.8, 0]} castShadow receiveShadow>
        <coneGeometry args={[canopyR * 0.6, canopyH * 0.42, 8]} />
        <meshStandardMaterial color="#355c35" roughness={0.82} />
      </mesh>
    </group>
  );
}

function TownScene({ rootRef }: { rootRef?: React.Ref<THREE.Group> }) {
  return (
    <group ref={rootRef}>
      <mesh position={[0, 0.04, 0]} receiveShadow>
        <boxGeometry args={[3000, 0.08, 3000]} />
        <meshStandardMaterial color="#1c2a1c" roughness={1} />
      </mesh>

      <Road x={0} z={0} w={900} d={24} />
      <Road x={0} z={0} w={24} d={900} />
      <Road x={0} z={148} w={700} d={14} />
      <Road x={0} z={-148} w={700} d={14} />
      <Road x={148} z={0} w={14} d={700} />
      <Road x={-148} z={0} w={14} d={700} />
      <Road x={0} z={300} w={500} d={12} />
      <Road x={0} z={-300} w={500} d={12} />
      <Road x={300} z={0} w={12} d={500} />
      <Road x={-300} z={0} w={12} d={500} />

      <Building x={52} z={50} w={36} d={30} h={58} color="#5a6070" />
      <Building x={98} z={55} w={28} d={24} h={38} color="#7a6858" />
      <Building x={68} z={98} w={44} d={34} h={24} color="#5c5040" />
      <Building x={114} z={96} w={22} d={22} h={72} color="#4a5060" />
      <Building x={52} z={80} w={18} d={20} h={42} color="#626870" />
      <Building x={78} z={115} w={32} d={28} h={32} color="#506268" />

      <Building x={-52} z={48} w={30} d={24} h={20} color="#6d5b4c" />
      <Building x={-88} z={62} w={28} d={22} h={18} color="#7a6050" />
      <Building x={-62} z={102} w={26} d={22} h={22} color="#6a5848" />
      <Building x={-110} z={88} w={24} d={20} h={16} color="#705a48" />
      <Building x={-120} z={52} w={30} d={26} h={18} color="#5a5048" />
      <Building x={-78} z={120} w={28} d={24} h={20} color="#685840" />

      <Building x={-55} z={-50} w={28} d={22} h={18} color="#665242" />
      <Building x={-92} z={-68} w={24} d={20} h={16} color="#6e5a48" />
      <Building x={-62} z={-102} w={30} d={24} h={22} color="#6a5040" />
      <Building x={-114} z={-96} w={22} d={18} h={14} color="#584840" />
      <Building x={-75} z={-120} w={26} d={22} h={18} color="#6a5848" />

      <Building x={58} z={-52} w={32} d={26} h={30} color="#5e6268" />
      <Building x={102} z={-60} w={26} d={22} h={44} color="#4e5862" />
      <Building x={65} z={-102} w={38} d={30} h={20} color="#7a6850" />
      <Building x={114} z={-100} w={24} d={22} h={52} color="#4a5068" />
      <Building x={75} z={-118} w={28} d={24} h={28} color="#586060" />

      <Building x={195} z={62} w={36} d={30} h={22} color="#5a5040" />
      <Building x={210} z={-58} w={30} d={24} h={18} color="#6a5848" />
      <Building x={-192} z={58} w={28} d={24} h={20} color="#605848" />
      <Building x={-205} z={-62} w={32} d={26} h={16} color="#6e5c4a" />
      <Building x={62} z={205} w={30} d={26} h={24} color="#5e5240" />
      <Building x={-60} z={198} w={28} d={22} h={18} color="#685848" />
      <Building x={58} z={-205} w={34} d={28} h={22} color="#5a5040" />
      <Building x={-58} z={-200} w={26} d={22} h={20} color="#6a5848" />

      <TreeFixed x={60} z={340} trunkH={32} canopyH={62} canopyR={18} />
      <TreeFixed x={-80} z={360} trunkH={35} canopyH={65} canopyR={19} />
      <TreeFixed x={120} z={310} trunkH={30} canopyH={58} canopyR={17} />
      <TreeFixed x={340} z={55} trunkH={33} canopyH={63} canopyR={18} />
      <TreeFixed x={370} z={-70} trunkH={34} canopyH={64} canopyR={18} />
      <TreeFixed x={320} z={130} trunkH={31} canopyH={60} canopyR={17} />
      <TreeFixed x={-345} z={60} trunkH={33} canopyH={62} canopyR={18} />
      <TreeFixed x={-370} z={-55} trunkH={36} canopyH={66} canopyR={19} />
      <TreeFixed x={-310} z={125} trunkH={32} canopyH={61} canopyR={17} />
      <TreeFixed x={55} z={-340} trunkH={34} canopyH={64} canopyR={18} />
      <TreeFixed x={-75} z={-365} trunkH={35} canopyH={65} canopyR={19} />
      <TreeFixed x={125} z={-315} trunkH={30} canopyH={59} canopyR={17} />
      <TreeFixed x={-120} z={-310} trunkH={33} canopyH={63} canopyR={18} />
      <TreeFixed x={310} z={-120} trunkH={31} canopyH={60} canopyR={17} />
      <TreeFixed x={-310} z={-130} trunkH={34} canopyH={62} canopyR={18} />
      <TreeFixed x={400} z={400} trunkH={36} canopyH={66} canopyR={19} />
      <TreeFixed x={-400} z={400} trunkH={33} canopyH={63} canopyR={18} />
      <TreeFixed x={400} z={-400} trunkH={35} canopyH={65} canopyR={19} />
      <TreeFixed x={-400} z={-400} trunkH={32} canopyH={61} canopyR={17} />

      <TreeFixed x={220} z={220} trunkH={26} canopyH={52} canopyR={15} />
      <TreeFixed x={-225} z={215} trunkH={24} canopyH={48} canopyR={14} />
      <TreeFixed x={215} z={-222} trunkH={28} canopyH={54} canopyR={15} />
      <TreeFixed x={-218} z={-225} trunkH={25} canopyH={50} canopyR={14} />
      <TreeFixed x={255} z={60} trunkH={22} canopyH={46} canopyR={13} />
      <TreeFixed x={260} z={-55} trunkH={26} canopyH={52} canopyR={15} />
      <TreeFixed x={-258} z={65} trunkH={24} canopyH={48} canopyR={14} />
      <TreeFixed x={-255} z={-58} trunkH={27} canopyH={53} canopyR={15} />
      <TreeFixed x={62} z={255} trunkH={25} canopyH={50} canopyR={14} />
      <TreeFixed x={-60} z={260} trunkH={23} canopyH={47} canopyR={13} />
      <TreeFixed x={65} z={-258} trunkH={26} canopyH={52} canopyR={15} />
      <TreeFixed x={-62} z={-255} trunkH={24} canopyH={48} canopyR={14} />

      <TreeFixed x={40} z={170} trunkH={20} canopyH={44} canopyR={11} />
      <TreeFixed x={82} z={170} trunkH={18} canopyH={40} canopyR={10} />
      <TreeFixed x={-40} z={-170} trunkH={22} canopyH={46} canopyR={12} />
      <TreeFixed x={-82} z={-170} trunkH={19} canopyH={41} canopyR={10} />
      <TreeFixed x={170} z={42} trunkH={21} canopyH={44} canopyR={11} />
      <TreeFixed x={170} z={82} trunkH={18} canopyH={39} canopyR={10} />
      <TreeFixed x={-170} z={-42} trunkH={20} canopyH={42} canopyR={11} />
      <TreeFixed x={-170} z={-82} trunkH={19} canopyH={40} canopyR={10} />
      <TreeFixed x={-170} z={42} trunkH={22} canopyH={45} canopyR={12} />
      <TreeFixed x={-170} z={82} trunkH={18} canopyH={38} canopyR={10} />
      <TreeFixed x={170} z={-42} trunkH={21} canopyH={43} canopyR={11} />
      <TreeFixed x={170} z={-82} trunkH={19} canopyH={40} canopyR={10} />
    </group>
  );
}

// ---------------------------------------------------------------------------

/** Camera placed once on first mount — orbit controls preserve position thereafter. */
function OrbitOriginCamera({
  gridSize,
  height,
  target,
}: {
  gridSize: number;
  height: number;
  target: [number, number, number];
}) {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const controls = useThree((s) => s.controls);
  const didInit = useRef(false);

  useEffect(() => {
    if (didInit.current) return;
    didInit.current = true;

    const span = Math.max(gridSize * 0.45, height * 1.1, 90);
    const dist = THREE.MathUtils.clamp(span * 0.36, 55, 520);

    const dir = new THREE.Vector3(0.85, 0.38, 0.85).normalize();
    camera.position.copy(dir.multiplyScalar(dist).add(new THREE.Vector3(...target)));
    camera.near = 0.4;
    camera.far = Math.max(dist * 80, 8000);
    camera.lookAt(target[0], target[1], target[2]);
    camera.updateProjectionMatrix();

    const oc = controls as unknown as { target: THREE.Vector3; update: () => void } | null;
    if (oc?.update) {
      oc.target.set(target[0], target[1], target[2]);
      oc.update();
    }
  }, [camera, controls, gridSize, height, target]);

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
  /**
   * Flat spin: yaw angle (deg) per capture at index i. From page: min(i·Δθ, arc) with
   * Δθ = ω·(interval_ft/speed) so RPM stays fixed when interval changes.
   */
  spinHeadingDegs?: number[];
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
  const coverageSpaceRef = useRef<THREE.Group>(null);
  const coverageRootRef = useRef<THREE.Group>(null);
  const droneMarkerRefs = useRef<Array<DroneMarkerHandle | null>>([]);
  const [hoveredWaypointIndex, setHoveredWaypointIndex] = useState<number | null>(null);
  const [selectedWaypointIndex, setSelectedWaypointIndex] = useState<number | null>(null);
  const hoverHoldTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hoverPendingIndexRef = useRef<number | null>(null);

  const clearHoverHoldTimer = useCallback(() => {
    if (hoverHoldTimerRef.current !== null) {
      clearTimeout(hoverHoldTimerRef.current);
      hoverHoldTimerRef.current = null;
    }
  }, []);

  const scheduleHoverHighlight = useCallback(
    (i: number) => {
      hoverPendingIndexRef.current = i;
      clearHoverHoldTimer();
      hoverHoldTimerRef.current = setTimeout(() => {
        hoverHoldTimerRef.current = null;
        if (hoverPendingIndexRef.current === i) {
          setHoveredWaypointIndex(i);
        }
      }, HOVER_HIGHLIGHT_HOLD_MS);
    },
    [clearHoverHoldTimer],
  );

  const cancelHoverHighlight = useCallback(
    (i: number) => {
      if (hoverPendingIndexRef.current === i) {
        hoverPendingIndexRef.current = null;
      }
      clearHoverHoldTimer();
      setHoveredWaypointIndex((prev) => (prev === i ? null : prev));
    },
    [clearHoverHoldTimer],
  );

  useEffect(() => () => clearHoverHoldTimer(), [clearHoverHoldTimer]);

  const goToWaypoint = useCallback((i: number) => {
    droneMarkerRefs.current[i]?.focus();
    setSelectedWaypointIndex(i);
  }, []);

  /** Formula suggestion when not in spin mode; spin scene length follows `pitchDegs.length` from the page. */
  const autoSpinCaptureCount = useMemo(
    () => Math.max(2, Math.min(30, Math.round(spacing / Math.max(0.01, captureIntervalFt)))),
    [spacing, captureIntervalFt],
  );

  const numSpinCaptures = spinMode
    ? Math.max(2, Math.min(30, pitchDegs.length))
    : autoSpinCaptureCount;

  const spinHeadings = useMemo(() => {
    if (
      spinMode
      && externalSpinHeadingDegs
      && externalSpinHeadingDegs.length === pitchDegs.length
    ) {
      return externalSpinHeadingDegs;
    }
    return Array.from({ length: numSpinCaptures }, (_, i) => (
      numSpinCaptures > 1 ? (i / (numSpinCaptures - 1)) * captureArcDeg : 0
    ));
  }, [spinMode, externalSpinHeadingDegs, pitchDegs.length, numSpinCaptures, captureArcDeg]);

  const spinAlongX = useMemo(
    () => Array.from({ length: numSpinCaptures }, (_, i) => (
      (i - (numSpinCaptures - 1) / 2) * captureIntervalFt
    )),
    [numSpinCaptures, captureIntervalFt],
  );

  const spinFootprints = useMemo(() => {
    if (!spinMode) return [];
    return spinAlongX.map((x, i) => {
      const pitch = pitchDegs[i % Math.max(1, pitchDegs.length)] ?? pitchDegs[0] ?? 30;
      return groundFootprint(x, height, pitch, spinHeadings[i]);
    });
  }, [spinMode, spinAlongX, spinHeadings, height, pitchDegs]);

  const n = Math.max(1, pitchDegs.length);

  const alongPositions = useMemo(
    () => Array.from({ length: n }, (_, i) => (i - (n - 1) / 2) * spacing),
    [n, spacing],
  );

  const linearFootprints = useMemo(
    () => alongPositions.map((x, i) => groundFootprint(x, height, pitchDegs[i] ?? pitchDegs[0])),
    [alongPositions, height, pitchDegs],
  );

  const activeFootprints = spinMode ? spinFootprints : linearFootprints;
  const activeDroneX = spinMode ? spinAlongX : alongPositions;
  const activeN = spinMode ? numSpinCaptures : n;

  const activePitchDegs = useMemo(
    () => (
      spinMode
        ? spinAlongX.map((_, i) => pitchDegs[i % Math.max(1, pitchDegs.length)] ?? pitchDegs[0] ?? 30)
        : pitchDegs
    ),
    [spinMode, spinAlongX, pitchDegs],
  );

  const activeHeadings = useMemo(
    () => (spinMode ? spinHeadings : Array.from({ length: n }, () => 0)),
    [spinMode, spinHeadings, n],
  );

  const activeColors = useMemo(
    () => Array.from({ length: activeN }, (_, i) => (
      spinMode
        ? spinFootprintColor(activeHeadings[i] ?? 0, captureArcDeg)
        : footprintColor(i, activeN)
    )),
    [activeN, spinMode, activeHeadings, captureArcDeg],
  );

  const activeBounds = useMemo(() => {
    if (activeFootprints.length === 0) {
      return {
        minX: -40,
        maxX: 40,
        minY: -40,
        maxY: 40,
      };
    }
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    for (const fp of activeFootprints) {
      for (const [x, y] of fp) {
        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);
      }
    }
    for (const x of activeDroneX) {
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
    }
    return { minX, maxX, minY, maxY };
  }, [activeFootprints, activeDroneX]);

  const gridSize = useMemo(() => {
    const span = Math.max(
      activeBounds.maxX - activeBounds.minX,
      activeBounds.maxY - activeBounds.minY,
      80,
    );
    return Math.min(span * 1.5, 8000);
  }, [activeBounds]);

  const initialTarget = useMemo<[number, number, number]>(() => {
    const centerX = (activeBounds.minX + activeBounds.maxX) / 2;
    const centerY = (activeBounds.minY + activeBounds.maxY) / 2;
    const blendTowardCoverage = 0.55;
    return [
      centerY * blendTowardCoverage,
      0,
      -centerX * blendTowardCoverage,
    ];
  }, [activeBounds]);

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
        onPointerMissed={() => setSelectedWaypointIndex(null)}
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
          enablePan
          enableDamping
          dampingFactor={0.1}
          minDistance={25}
          maxDistance={maxOrbit}
          minPolarAngle={0.08}
          maxPolarAngle={Math.PI / 2 - 0.08}
        />

        <OrbitOriginCamera gridSize={gridSize} height={height} target={initialTarget} />

        <HoverSceneCursor active={hoveredWaypointIndex !== null || selectedWaypointIndex !== null} />

        <group ref={coverageSpaceRef} rotation={[0, Math.PI / 2, 0]}>
          <TownScene rootRef={coverageRootRef} />

          {activeFootprints.map((quad, i) => {
            const dronePos = dronePositions[i];
            const fpOpacity = spinMode
              ? 0.08
              : 0.05 + (i / Math.max(1, activeN - 1)) * 0.05;
            const em = hoveredWaypointIndex === i || selectedWaypointIndex === i;
            return (
              <group
                key={i}
                onPointerOver={(e) => {
                  e.stopPropagation();
                  scheduleHoverHighlight(i);
                }}
                onPointerOut={() => {
                  cancelHoverHighlight(i);
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  goToWaypoint(i);
                }}
              >
                <DroneMarker
                  ref={(el) => {
                    droneMarkerRefs.current[i] = el;
                  }}
                  position={dronePos}
                  pitchDeg={activePitchDegs[i]}
                  headingDeg={activeHeadings[i] ?? 0}
                  heightFt={height}
                  isHighlighted={em}
                  showTag={em}
                  onTagActivate={() => goToWaypoint(i)}
                />
                <DirectionVector
                  dronePos={dronePos}
                  pitchDeg={activePitchDegs[i] ?? 0}
                  headingDeg={activeHeadings[i] ?? 0}
                  length={Math.max(18, height * 0.14)}
                  emphasize={em}
                />
                <FrustumLines
                  dronePos={dronePos}
                  pitchDeg={activePitchDegs[i] ?? 0}
                  headingDeg={activeHeadings[i] ?? 0}
                  lineOpacity={lineOpacity}
                  emphasize={em}
                />
                <FootprintQuad quad={quad} color={activeColors[i]} opacity={fpOpacity} emphasize={em} />
              </group>
            );
          })}
        </group>

        <CoverageOverlay
          spaceRef={coverageSpaceRef}
          coverageRootRef={coverageRootRef}
          dronePositions={dronePositions}
          pitchDegs={activePitchDegs}
          headingDegs={activeHeadings}
          colors={activeColors}
          emphasizeIndex={hoveredWaypointIndex ?? selectedWaypointIndex}
        />
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
