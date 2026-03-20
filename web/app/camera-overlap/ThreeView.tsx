'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, createPortal, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Line, Html } from '@react-three/drei';
import * as THREE from 'three';
import {
  FOV_V_DEG,
  TAN_H,
  TAN_V,
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

type TownSceneMode = 'base' | 'overlay';

type ProjectorPass = {
  key: string;
  camera: THREE.PerspectiveCamera;
  matrix: THREE.Matrix4;
  color: THREE.Color;
  renderTarget: THREE.WebGLRenderTarget;
  depthTexture: THREE.DepthTexture;
  opacity: number;
};

const PROJECTOR_ASPECT = TAN_H / TAN_V;
const PROJECTOR_RANGE = 2400;
const PROJECTOR_MAP_SIZE = 512;
const SPACE_ROTATION = new THREE.Matrix4().makeRotationY(Math.PI / 2);

const COVERAGE_VERTEX_SHADER = /* glsl */ `
  uniform mat4 projectorMatrix;
  varying vec4 vProjectorClip;

  void main() {
    vec3 displaced = position + normal * 0.12;
    vec4 worldPos = modelMatrix * vec4(displaced, 1.0);
    vProjectorClip = projectorMatrix * worldPos;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);
  }
`;

const COVERAGE_FRAGMENT_SHADER = /* glsl */ `
  uniform sampler2D projectorDepthTexture;
  uniform vec3 projectorColor;
  uniform float projectorOpacity;
  varying vec4 vProjectorClip;

  void main() {
    if (vProjectorClip.w <= 0.0) discard;

    vec3 ndc = vProjectorClip.xyz / vProjectorClip.w;
    if (abs(ndc.x) > 1.0 || abs(ndc.y) > 1.0 || ndc.z < -1.0 || ndc.z > 1.0) discard;

    vec2 uv = ndc.xy * 0.5 + 0.5;
    float projectedDepth = ndc.z * 0.5 + 0.5;
    float storedDepth = texture2D(projectorDepthTexture, uv).x;

    if (storedDepth <= 0.0) discard;
    if (projectedDepth > storedDepth + 0.0025) discard;

    float edge = min(1.0 - abs(ndc.x), 1.0 - abs(ndc.y));
    float edgeFade = smoothstep(0.0, 0.08, edge);

    gl_FragColor = vec4(projectorColor, projectorOpacity * edgeFade);
  }
`;

function buildCameraBasisLocal(pitchDeg: number, headingDeg: number) {
  const theta = (pitchDeg * Math.PI) / 180;
  const H = (headingDeg * Math.PI) / 180;
  const sinT = Math.sin(theta);
  const cosT = Math.cos(theta);
  const sinH = Math.sin(H);
  const cosH = Math.cos(H);

  // Same basis as `groundFootprint`, converted into the local coordinates of the
  // rotated scene group: three = [math.x, math.z, math.y].
  const forward = new THREE.Vector3(sinH * cosT, -sinT, cosH * cosT).normalize();
  const up = new THREE.Vector3(sinH * sinT, cosT, cosH * sinT).normalize();

  return { forward, up };
}

function buildProjectorCamera(
  localPosition: [number, number, number],
  pitchDeg: number,
  headingDeg: number,
): { camera: THREE.PerspectiveCamera; matrix: THREE.Matrix4 } {
  const originLocal = new THREE.Vector3(...localPosition);
  const { forward, up } = buildCameraBasisLocal(pitchDeg, headingDeg);

  const targetLocal = originLocal.clone().add(forward.clone().multiplyScalar(100));
  const originWorld = originLocal.clone().applyMatrix4(SPACE_ROTATION);
  const targetWorld = targetLocal.clone().applyMatrix4(SPACE_ROTATION);
  const upWorld = up.clone().transformDirection(SPACE_ROTATION).normalize();

  const camera = new THREE.PerspectiveCamera(FOV_V_DEG, PROJECTOR_ASPECT, 0.5, PROJECTOR_RANGE);
  camera.position.copy(originWorld);
  camera.up.copy(upWorld);
  camera.lookAt(targetWorld);
  camera.updateProjectionMatrix();
  camera.updateMatrixWorld(true);

  const matrix = new THREE.Matrix4().multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
  return { camera, matrix };
}

function createProjectorTarget() {
  const target = new THREE.WebGLRenderTarget(PROJECTOR_MAP_SIZE, PROJECTOR_MAP_SIZE, {
    minFilter: THREE.NearestFilter,
    magFilter: THREE.NearestFilter,
    depthBuffer: true,
    stencilBuffer: false,
  });
  target.texture.generateMipmaps = false;
  target.depthTexture = new THREE.DepthTexture(
    PROJECTOR_MAP_SIZE,
    PROJECTOR_MAP_SIZE,
    THREE.UnsignedIntType,
  );
  target.depthTexture.format = THREE.DepthFormat;
  target.depthTexture.minFilter = THREE.NearestFilter;
  target.depthTexture.magFilter = THREE.NearestFilter;
  return target;
}

function CoverageProjectionMaterial({ projector }: { projector: ProjectorPass }) {
  const uniforms = useMemo(
    () => ({
      projectorMatrix: { value: projector.matrix.clone() },
      projectorColor: { value: projector.color.clone() },
      projectorDepthTexture: { value: projector.depthTexture },
      projectorOpacity: { value: projector.opacity },
    }),
    [projector.color, projector.depthTexture, projector.matrix, projector.opacity],
  );

  useEffect(() => {
    uniforms.projectorMatrix.value.copy(projector.matrix);
    uniforms.projectorColor.value.copy(projector.color);
    uniforms.projectorDepthTexture.value = projector.depthTexture;
    uniforms.projectorOpacity.value = projector.opacity;
  }, [projector, uniforms]);

  return (
    <shaderMaterial
      uniforms={uniforms}
      vertexShader={COVERAGE_VERTEX_SHADER}
      fragmentShader={COVERAGE_FRAGMENT_SHADER}
      transparent
      depthWrite={false}
      polygonOffset
      polygonOffsetFactor={-4}
      polygonOffsetUnits={-4}
      side={THREE.DoubleSide}
      toneMapped={false}
    />
  );
}

// ---------------------------------------------------------------------------

/** Drone body at local origin — parent `<group position={dronePos}>` places it in scene. */
function DroneMarker({
  pitchDeg,
  heightFt,
}: {
  pitchDeg?: number;
  heightFt?: number;
}) {
  const y = heightFt ?? 100;
  const r = Math.max(2, y * 0.009);
  const [hovered, setHovered] = useState(false);

  return (
    <group
      onPointerOver={(e) => {
        e.stopPropagation();
        setHovered(true);
      }}
      onPointerOut={() => setHovered(false)}
    >
      <mesh>
        <sphereGeometry args={[r, 12, 12]} />
        <meshStandardMaterial
          color={hovered ? '#ffd60a' : '#f5f5f7'}
          emissive={hovered ? '#ffd60a' : '#222'}
          emissiveIntensity={hovered ? 0.35 : 0.16}
        />
      </mesh>
      {hovered && pitchDeg !== undefined && (
        <Html
          position={[0, r + 5, 0]}
          center
          distanceFactor={120}
          style={{ pointerEvents: 'none' }}
        >
          <div
            style={{
              background: 'rgba(10, 10, 10, 0.92)',
              border: '1px solid #3a8eff',
              borderRadius: 6,
              color: '#f5f5f7',
              fontFamily: 'ui-monospace, monospace',
              fontSize: 11,
              fontWeight: 500,
              padding: '4px 9px',
              whiteSpace: 'nowrap',
            }}
          >
            −{pitchDeg.toFixed(1)}° · {Math.round(y)} ft AGL
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
      verts.push(tx, ty + 0.35, tz);
    }
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(verts), 3));
    g.setIndex([0, 1, 2, 0, 2, 3]);
    g.computeVertexNormals();
    return g;
  }, [quad]);

  return (
    <mesh geometry={geo} renderOrder={3}>
      <meshBasicMaterial
        color={color}
        transparent
        opacity={opacity}
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
 * Frustum edges from the drone (local origin) to ground corners — must live in the same
 * `<group position={dronePos}>` as the sphere so drei `Line` shares the transform.
 */
function FrustumConeLines({
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
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(
          g[0] - dronePos[0],
          g[1] - dronePos[1],
          g[2] - dronePos[2],
        ),
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

/** Ground footprint border in scene space (sibling of the drone group). */
function FrustumFootprintBorder({
  quad,
  lineOpacity = 0.55,
}: {
  quad: GroundQuad;
  lineOpacity?: number;
}) {
  const lines = useMemo(() => {
    const edges: Array<[THREE.Vector3, THREE.Vector3]> = [];
    for (let i = 0; i < 4; i++) {
      const c1 = mathGroundToThree(quad[i]);
      const c2 = mathGroundToThree(quad[(i + 1) % 4]);
      edges.push([
        new THREE.Vector3(c1[0], c1[1], c1[2]),
        new THREE.Vector3(c2[0], c2[1], c2[2]),
      ]);
    }
    return edges;
  }, [quad]);

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

function Road({
  x,
  z,
  w,
  d,
  mode = 'base',
  projector,
}: {
  x: number;
  z: number;
  w: number;
  d: number;
  mode?: TownSceneMode;
  projector?: ProjectorPass;
}) {
  return (
    <mesh position={[x, 0.13, z]} receiveShadow={mode === 'base'} renderOrder={mode === 'overlay' ? 7 : 0}>
      <boxGeometry args={[w, 0.26, d]} />
      {mode === 'overlay' && projector ? (
        <CoverageProjectionMaterial projector={projector} />
      ) : (
        <meshStandardMaterial color="#1e1e1e" roughness={0.96} />
      )}
    </mesh>
  );
}

function Building({
  x,
  z,
  w,
  d,
  h,
  color,
  mode = 'base',
  projector,
}: {
  x: number;
  z: number;
  w: number;
  d: number;
  h: number;
  color: string;
  mode?: TownSceneMode;
  projector?: ProjectorPass;
}) {
  return (
    <group position={[x, 0, z]}>
      <mesh
        position={[0, h / 2, 0]}
        castShadow={mode === 'base'}
        receiveShadow={mode === 'base'}
        renderOrder={mode === 'overlay' ? 7 : 0}
      >
        <boxGeometry args={[w, h, d]} />
        {mode === 'overlay' && projector ? (
          <CoverageProjectionMaterial projector={projector} />
        ) : (
          <meshStandardMaterial color={color} roughness={0.72} metalness={0.08} />
        )}
      </mesh>
      <mesh
        position={[0, h + 0.6, 0]}
        receiveShadow={mode === 'base'}
        renderOrder={mode === 'overlay' ? 7 : 0}
      >
        <boxGeometry args={[w + 0.5, 1.2, d + 0.5]} />
        {mode === 'overlay' && projector ? (
          <CoverageProjectionMaterial projector={projector} />
        ) : (
          <meshStandardMaterial color="#181818" roughness={0.9} />
        )}
      </mesh>
    </group>
  );
}

function TreeFixed({
  x,
  z,
  trunkH,
  canopyH,
  canopyR,
  mode = 'base',
  projector,
}: {
  x: number;
  z: number;
  trunkH: number;
  canopyH: number;
  canopyR: number;
  mode?: TownSceneMode;
  projector?: ProjectorPass;
}) {
  return (
    <group position={[x, 0, z]}>
      <mesh
        position={[0, trunkH / 2, 0]}
        castShadow={mode === 'base'}
        receiveShadow={mode === 'base'}
        renderOrder={mode === 'overlay' ? 7 : 0}
      >
        <cylinderGeometry args={[trunkH * 0.028, trunkH * 0.042, trunkH, 7]} />
        {mode === 'overlay' && projector ? (
          <CoverageProjectionMaterial projector={projector} />
        ) : (
          <meshStandardMaterial color="#4a3828" roughness={0.95} />
        )}
      </mesh>
      <mesh
        position={[0, trunkH + canopyH * 0.36, 0]}
        castShadow={mode === 'base'}
        receiveShadow={mode === 'base'}
        renderOrder={mode === 'overlay' ? 7 : 0}
      >
        <coneGeometry args={[canopyR, canopyH * 0.72, 16]} />
        {mode === 'overlay' && projector ? (
          <CoverageProjectionMaterial projector={projector} />
        ) : (
          <meshStandardMaterial color="#2d4a2d" roughness={0.88} />
        )}
      </mesh>
      <mesh
        position={[0, trunkH + canopyH * 0.8, 0]}
        castShadow={mode === 'base'}
        receiveShadow={mode === 'base'}
        renderOrder={mode === 'overlay' ? 7 : 0}
      >
        <coneGeometry args={[canopyR * 0.6, canopyH * 0.42, 16]} />
        {mode === 'overlay' && projector ? (
          <CoverageProjectionMaterial projector={projector} />
        ) : (
          <meshStandardMaterial color="#355c35" roughness={0.82} />
        )}
      </mesh>
    </group>
  );
}

function TownScene({
  mode = 'base',
  projector,
}: {
  mode?: TownSceneMode;
  projector?: ProjectorPass;
}) {
  return (
    <group>
      <mesh position={[0, 0.04, 0]} receiveShadow={mode === 'base'} renderOrder={mode === 'overlay' ? 7 : 0}>
        <boxGeometry args={[3000, 0.08, 3000]} />
        {mode === 'overlay' && projector ? (
          <CoverageProjectionMaterial projector={projector} />
        ) : (
          <meshStandardMaterial color="#1c2a1c" roughness={1} />
        )}
      </mesh>

      <Road x={0} z={0} w={900} d={24} mode={mode} projector={projector} />
      <Road x={0} z={0} w={24} d={900} mode={mode} projector={projector} />
      <Road x={0} z={148} w={700} d={14} mode={mode} projector={projector} />
      <Road x={0} z={-148} w={700} d={14} mode={mode} projector={projector} />
      <Road x={148} z={0} w={14} d={700} mode={mode} projector={projector} />
      <Road x={-148} z={0} w={14} d={700} mode={mode} projector={projector} />
      <Road x={0} z={300} w={500} d={12} mode={mode} projector={projector} />
      <Road x={0} z={-300} w={500} d={12} mode={mode} projector={projector} />
      <Road x={300} z={0} w={12} d={500} mode={mode} projector={projector} />
      <Road x={-300} z={0} w={12} d={500} mode={mode} projector={projector} />

      <Building x={52} z={50} w={36} d={30} h={58} color="#5a6070" mode={mode} projector={projector} />
      <Building x={98} z={55} w={28} d={24} h={38} color="#7a6858" mode={mode} projector={projector} />
      <Building x={68} z={98} w={44} d={34} h={24} color="#5c5040" mode={mode} projector={projector} />
      <Building x={114} z={96} w={22} d={22} h={72} color="#4a5060" mode={mode} projector={projector} />
      <Building x={52} z={80} w={18} d={20} h={42} color="#626870" mode={mode} projector={projector} />
      <Building x={78} z={115} w={32} d={28} h={32} color="#506268" mode={mode} projector={projector} />

      <Building x={-52} z={48} w={30} d={24} h={20} color="#6d5b4c" mode={mode} projector={projector} />
      <Building x={-88} z={62} w={28} d={22} h={18} color="#7a6050" mode={mode} projector={projector} />
      <Building x={-62} z={102} w={26} d={22} h={22} color="#6a5848" mode={mode} projector={projector} />
      <Building x={-110} z={88} w={24} d={20} h={16} color="#705a48" mode={mode} projector={projector} />
      <Building x={-120} z={52} w={30} d={26} h={18} color="#5a5048" mode={mode} projector={projector} />
      <Building x={-78} z={120} w={28} d={24} h={20} color="#685840" mode={mode} projector={projector} />

      <Building x={-55} z={-50} w={28} d={22} h={18} color="#665242" mode={mode} projector={projector} />
      <Building x={-92} z={-68} w={24} d={20} h={16} color="#6e5a48" mode={mode} projector={projector} />
      <Building x={-62} z={-102} w={30} d={24} h={22} color="#6a5040" mode={mode} projector={projector} />
      <Building x={-114} z={-96} w={22} d={18} h={14} color="#584840" mode={mode} projector={projector} />
      <Building x={-75} z={-120} w={26} d={22} h={18} color="#6a5848" mode={mode} projector={projector} />

      <Building x={58} z={-52} w={32} d={26} h={30} color="#5e6268" mode={mode} projector={projector} />
      <Building x={102} z={-60} w={26} d={22} h={44} color="#4e5862" mode={mode} projector={projector} />
      <Building x={65} z={-102} w={38} d={30} h={20} color="#7a6850" mode={mode} projector={projector} />
      <Building x={114} z={-100} w={24} d={22} h={52} color="#4a5068" mode={mode} projector={projector} />
      <Building x={75} z={-118} w={28} d={24} h={28} color="#586060" mode={mode} projector={projector} />

      <Building x={195} z={62} w={36} d={30} h={22} color="#5a5040" mode={mode} projector={projector} />
      <Building x={210} z={-58} w={30} d={24} h={18} color="#6a5848" mode={mode} projector={projector} />
      <Building x={-192} z={58} w={28} d={24} h={20} color="#605848" mode={mode} projector={projector} />
      <Building x={-205} z={-62} w={32} d={26} h={16} color="#6e5c4a" mode={mode} projector={projector} />
      <Building x={62} z={205} w={30} d={26} h={24} color="#5e5240" mode={mode} projector={projector} />
      <Building x={-60} z={198} w={28} d={22} h={18} color="#685848" mode={mode} projector={projector} />
      <Building x={58} z={-205} w={34} d={28} h={22} color="#5a5040" mode={mode} projector={projector} />
      <Building x={-58} z={-200} w={26} d={22} h={20} color="#6a5848" mode={mode} projector={projector} />

      <TreeFixed x={60} z={340} trunkH={32} canopyH={62} canopyR={18} mode={mode} projector={projector} />
      <TreeFixed x={-80} z={360} trunkH={35} canopyH={65} canopyR={19} mode={mode} projector={projector} />
      <TreeFixed x={120} z={310} trunkH={30} canopyH={58} canopyR={17} mode={mode} projector={projector} />
      <TreeFixed x={340} z={55} trunkH={33} canopyH={63} canopyR={18} mode={mode} projector={projector} />
      <TreeFixed x={370} z={-70} trunkH={34} canopyH={64} canopyR={18} mode={mode} projector={projector} />
      <TreeFixed x={320} z={130} trunkH={31} canopyH={60} canopyR={17} mode={mode} projector={projector} />
      <TreeFixed x={-345} z={60} trunkH={33} canopyH={62} canopyR={18} mode={mode} projector={projector} />
      <TreeFixed x={-370} z={-55} trunkH={36} canopyH={66} canopyR={19} mode={mode} projector={projector} />
      <TreeFixed x={-310} z={125} trunkH={32} canopyH={61} canopyR={17} mode={mode} projector={projector} />
      <TreeFixed x={55} z={-340} trunkH={34} canopyH={64} canopyR={18} mode={mode} projector={projector} />
      <TreeFixed x={-75} z={-365} trunkH={35} canopyH={65} canopyR={19} mode={mode} projector={projector} />
      <TreeFixed x={125} z={-315} trunkH={30} canopyH={59} canopyR={17} mode={mode} projector={projector} />
      <TreeFixed x={-120} z={-310} trunkH={33} canopyH={63} canopyR={18} mode={mode} projector={projector} />
      <TreeFixed x={310} z={-120} trunkH={31} canopyH={60} canopyR={17} mode={mode} projector={projector} />
      <TreeFixed x={-310} z={-130} trunkH={34} canopyH={62} canopyR={18} mode={mode} projector={projector} />
      <TreeFixed x={400} z={400} trunkH={36} canopyH={66} canopyR={19} mode={mode} projector={projector} />
      <TreeFixed x={-400} z={400} trunkH={33} canopyH={63} canopyR={18} mode={mode} projector={projector} />
      <TreeFixed x={400} z={-400} trunkH={35} canopyH={65} canopyR={19} mode={mode} projector={projector} />
      <TreeFixed x={-400} z={-400} trunkH={32} canopyH={61} canopyR={17} mode={mode} projector={projector} />

      <TreeFixed x={220} z={220} trunkH={26} canopyH={52} canopyR={15} mode={mode} projector={projector} />
      <TreeFixed x={-225} z={215} trunkH={24} canopyH={48} canopyR={14} mode={mode} projector={projector} />
      <TreeFixed x={215} z={-222} trunkH={28} canopyH={54} canopyR={15} mode={mode} projector={projector} />
      <TreeFixed x={-218} z={-225} trunkH={25} canopyH={50} canopyR={14} mode={mode} projector={projector} />
      <TreeFixed x={255} z={60} trunkH={22} canopyH={46} canopyR={13} mode={mode} projector={projector} />
      <TreeFixed x={260} z={-55} trunkH={26} canopyH={52} canopyR={15} mode={mode} projector={projector} />
      <TreeFixed x={-258} z={65} trunkH={24} canopyH={48} canopyR={14} mode={mode} projector={projector} />
      <TreeFixed x={-255} z={-58} trunkH={27} canopyH={53} canopyR={15} mode={mode} projector={projector} />
      <TreeFixed x={62} z={255} trunkH={25} canopyH={50} canopyR={14} mode={mode} projector={projector} />
      <TreeFixed x={-60} z={260} trunkH={23} canopyH={47} canopyR={13} mode={mode} projector={projector} />
      <TreeFixed x={65} z={-258} trunkH={26} canopyH={52} canopyR={15} mode={mode} projector={projector} />
      <TreeFixed x={-62} z={-255} trunkH={24} canopyH={48} canopyR={14} mode={mode} projector={projector} />

      <TreeFixed x={40} z={170} trunkH={20} canopyH={44} canopyR={11} mode={mode} projector={projector} />
      <TreeFixed x={82} z={170} trunkH={18} canopyH={40} canopyR={10} mode={mode} projector={projector} />
      <TreeFixed x={-40} z={-170} trunkH={22} canopyH={46} canopyR={12} mode={mode} projector={projector} />
      <TreeFixed x={-82} z={-170} trunkH={19} canopyH={41} canopyR={10} mode={mode} projector={projector} />
      <TreeFixed x={170} z={42} trunkH={21} canopyH={44} canopyR={11} mode={mode} projector={projector} />
      <TreeFixed x={170} z={82} trunkH={18} canopyH={39} canopyR={10} mode={mode} projector={projector} />
      <TreeFixed x={-170} z={-42} trunkH={20} canopyH={42} canopyR={11} mode={mode} projector={projector} />
      <TreeFixed x={-170} z={-82} trunkH={19} canopyH={40} canopyR={10} mode={mode} projector={projector} />
      <TreeFixed x={-170} z={42} trunkH={22} canopyH={45} canopyR={12} mode={mode} projector={projector} />
      <TreeFixed x={-170} z={82} trunkH={18} canopyH={38} canopyR={10} mode={mode} projector={projector} />
      <TreeFixed x={170} z={-42} trunkH={21} canopyH={43} canopyR={11} mode={mode} projector={projector} />
      <TreeFixed x={170} z={-82} trunkH={19} canopyH={40} canopyR={10} mode={mode} projector={projector} />
    </group>
  );
}

// ---------------------------------------------------------------------------

function ProjectionDepthRenderer({
  depthScene,
  projectors,
}: {
  depthScene: THREE.Scene;
  projectors: ProjectorPass[];
}) {
  const gl = useThree((state) => state.gl);
  const invalidate = useThree((state) => state.invalidate);
  const depthMaterial = useMemo(() => new THREE.MeshDepthMaterial(), []);
  const dirtyRef = useRef(true);

  useEffect(() => {
    dirtyRef.current = true;
    invalidate();
  }, [projectors, invalidate]);

  useEffect(() => () => depthMaterial.dispose(), [depthMaterial]);

  useFrame(() => {
    if (!dirtyRef.current || projectors.length === 0) return;

    const previousRenderTarget = gl.getRenderTarget();
    const previousAutoClear = gl.autoClear;
    const previousXrEnabled = gl.xr.enabled;
    const previousOverrideMaterial = depthScene.overrideMaterial;

    gl.autoClear = true;
    gl.xr.enabled = false;
    depthScene.overrideMaterial = depthMaterial;

    for (const projector of projectors) {
      gl.setRenderTarget(projector.renderTarget);
      gl.clear();
      gl.render(depthScene, projector.camera);
    }

    depthScene.overrideMaterial = previousOverrideMaterial;
    gl.setRenderTarget(previousRenderTarget);
    gl.autoClear = previousAutoClear;
    gl.xr.enabled = previousXrEnabled;
    dirtyRef.current = false;
  }, -1);

  return null;
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
  const depthScene = useMemo(() => new THREE.Scene(), []);

  const numSpinCaptures = useMemo(
    () => Math.max(2, Math.min(30, Math.round(spacing / captureIntervalFt))),
    [spacing, captureIntervalFt],
  );

  const spinHeadings = useMemo(
    () => Array.from({ length: numSpinCaptures }, (_, i) => (
      numSpinCaptures > 1 ? (i / (numSpinCaptures - 1)) * captureArcDeg : 0
    )),
    [numSpinCaptures, captureArcDeg],
  );

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

  const projectorOpacity = activeN > 14 ? 0.13 : activeN > 8 ? 0.16 : 0.2;

  const projectors = useMemo<ProjectorPass[]>(
    () => dronePositions.map((dronePos, i) => {
      const { camera, matrix } = buildProjectorCamera(
        dronePos,
        activePitchDegs[i] ?? pitchDegs[0] ?? 30,
        activeHeadings[i] ?? 0,
      );
      const renderTarget = createProjectorTarget();
      return {
        key: `${i}-${dronePos[0].toFixed(1)}-${(activeHeadings[i] ?? 0).toFixed(1)}-${(activePitchDegs[i] ?? 30).toFixed(1)}`,
        camera,
        matrix,
        color: new THREE.Color(activeColors[i] ?? '#3a8eff'),
        renderTarget,
        depthTexture: renderTarget.depthTexture,
        opacity: projectorOpacity,
      };
    }),
    [dronePositions, activePitchDegs, activeHeadings, activeColors, projectorOpacity, pitchDegs],
  );

  useEffect(() => () => {
    for (const projector of projectors) {
      projector.depthTexture.dispose();
      projector.renderTarget.dispose();
    }
  }, [projectors]);

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
          enablePan
          enableDamping
          dampingFactor={0.1}
          minDistance={25}
          maxDistance={maxOrbit}
          minPolarAngle={0.08}
          maxPolarAngle={Math.PI / 2 - 0.08}
        />

        <OrbitOriginCamera gridSize={gridSize} height={height} target={initialTarget} />

        {createPortal(
          <group rotation={[0, Math.PI / 2, 0]}>
            <TownScene mode="base" />
          </group>,
          depthScene,
        )}

        <ProjectionDepthRenderer depthScene={depthScene} projectors={projectors} />

        <group rotation={[0, Math.PI / 2, 0]}>
          <TownScene mode="base" />

          {projectors.map((projector) => (
            <TownScene key={projector.key} mode="overlay" projector={projector} />
          ))}

          {activeFootprints.map((quad, i) => {
            const dronePos = dronePositions[i];
            const fpOpacity = spinMode
              ? 0.055
              : 0.035 + (i / Math.max(1, activeN - 1)) * 0.03;
            return (
              <group key={i}>
                <group position={dronePos}>
                  <DroneMarker
                    pitchDeg={activePitchDegs[i]}
                    heightFt={height}
                  />
                  <FrustumConeLines dronePos={dronePos} quad={quad} lineOpacity={lineOpacity} />
                </group>
                <FrustumFootprintBorder quad={quad} lineOpacity={lineOpacity} />
                <FootprintQuad quad={quad} color={activeColors[i]} opacity={fpOpacity} />
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
