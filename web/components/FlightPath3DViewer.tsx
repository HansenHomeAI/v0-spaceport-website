"use client";

import React, { useEffect, useMemo, useRef } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { Html, Line, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import {
  BatteryPathWaypoint3D,
  buildFlightPath3DScene,
} from "../lib/flightPath3d";

type FlightPath3DViewerProps = {
  batteryPaths: Array<{
    batteryIndex: number;
    color: string;
    waypoints: BatteryPathWaypoint3D[];
  }>;
  center: { lat: number; lng: number };
};

function AutoFrameCamera({
  radiusFeet,
  heightFeet,
}: {
  radiusFeet: number;
  heightFeet: number;
}) {
  const { camera } = useThree();

  useEffect(() => {
    const distance = Math.max(radiusFeet * 1.35, 650);
    camera.position.set(distance, -distance * 0.72, Math.max(heightFeet, radiusFeet * 0.45));
    camera.near = 1;
    camera.far = Math.max(distance * 12, 12000);
    camera.lookAt(0, 0, Math.max(40, heightFeet * 0.3));
    camera.updateProjectionMatrix();
  }, [camera, heightFeet, radiusFeet]);

  return null;
}

function Scene({
  batteryPaths,
  center,
}: FlightPath3DViewerProps) {
  const scene = useMemo(() => buildFlightPath3DScene(batteryPaths, center), [batteryPaths, center]);
  const controlsRef = useRef<any>(null);
  const gridSize = Math.max(1200, scene.horizontalExtentFeet * 2.6);
  const cameraHeight = Math.max(220, scene.altitudeRangeFeet * scene.verticalExaggeration + 220);

  useEffect(() => {
    controlsRef.current?.target?.set(0, 0, Math.max(25, cameraHeight * 0.22));
    controlsRef.current?.update?.();
  }, [cameraHeight, scene]);

  return (
    <>
      <color attach="background" args={["#04070d"]} />
      <fog attach="fog" args={["#04070d", gridSize * 1.8, gridSize * 3.8]} />
      <ambientLight intensity={0.72} />
      <directionalLight position={[900, -700, 1400]} intensity={0.95} />
      <directionalLight position={[-600, 500, 900]} intensity={0.5} color="#8fb5ff" />
      <AutoFrameCamera radiusFeet={scene.horizontalExtentFeet} heightFeet={cameraHeight} />

      <gridHelper
        args={[gridSize, 24, "#5f7591", "#223043"]}
        rotation={[Math.PI / 2, 0, 0]}
        position={[0, 0, 0]}
      />

      <mesh position={[0, 0, 4]}>
        <sphereGeometry args={[18, 28, 28]} />
        <meshStandardMaterial color="#f4f7fb" emissive="#6c88a6" emissiveIntensity={0.32} />
      </mesh>

      {scene.batteries.map((battery) => {
        const vectors = battery.points.map((point) => new THREE.Vector3(point.x, point.y, point.z));
        const startPoint = battery.points[0];
        const endPoint = battery.points[battery.points.length - 1];

        return (
          <group key={battery.batteryIndex}>
            {vectors.length >= 2 && (
              <Line
                points={vectors}
                color={battery.color}
                lineWidth={2.6}
                transparent
                opacity={0.96}
              />
            )}

            {battery.points.map((point, pointIndex) => {
              const isAnchor = pointIndex === 0 || pointIndex === battery.points.length - 1;
              return (
                <mesh
                  key={`${battery.batteryIndex}-${pointIndex}`}
                  position={[point.x, point.y, point.z]}
                >
                  <sphereGeometry args={[isAnchor ? 10 : 5.2, 18, 18]} />
                  <meshStandardMaterial
                    color={isAnchor ? "#ffffff" : battery.color}
                    emissive={battery.color}
                    emissiveIntensity={isAnchor ? 0.4 : 0.18}
                  />
                </mesh>
              );
            })}

            {startPoint && (
              <Html position={[startPoint.x, startPoint.y, startPoint.z + 28]} center>
                <div className="flight-path-3d-label">
                  B{battery.batteryIndex} Start
                </div>
              </Html>
            )}

            {endPoint && (
              <Html position={[endPoint.x, endPoint.y, endPoint.z + 28]} center>
                <div className="flight-path-3d-label">
                  B{battery.batteryIndex} End
                </div>
              </Html>
            )}
          </group>
        );
      })}

      <OrbitControls
        ref={controlsRef}
        enableDamping
        dampingFactor={0.08}
        minDistance={160}
        maxDistance={gridSize * 3}
        maxPolarAngle={Math.PI * 0.495}
      />
    </>
  );
}

export default function FlightPath3DViewer({
  batteryPaths,
  center,
}: FlightPath3DViewerProps) {
  const hasPaths = batteryPaths.some((battery) => battery.waypoints.length > 1);
  const summary = useMemo(() => buildFlightPath3DScene(batteryPaths, center), [batteryPaths, center]);

  if (!hasPaths) {
    return (
      <div className="flight-path-3d-empty" data-flight-path-3d="empty">
        3D path data unavailable.
      </div>
    );
  }

  return (
    <div className="flight-path-3d-viewer" data-flight-path-3d="ready">
      <div className="flight-path-3d-overlay">
        <div className="flight-path-3d-title">3D Flight Path</div>
        <div className="flight-path-3d-metrics">
          Vertical x{summary.verticalExaggeration.toFixed(1)} | Alt {summary.baseAltitudeFeet.toFixed(0)}-{summary.maxAltitudeFeet.toFixed(0)} ft
        </div>
      </div>
      <Canvas gl={{ antialias: true }} dpr={[1, 2]}>
        <Scene batteryPaths={batteryPaths} center={center} />
      </Canvas>
    </div>
  );
}
