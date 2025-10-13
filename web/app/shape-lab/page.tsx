"use client";

import React, { useMemo, useState, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Line, Html } from '@react-three/drei';
import * as THREE from 'three';

type Waypoint = {
  x: number;
  y: number;
  z: number; // AGL in feet
  phase: string;
  index: number;
};

type FlightParams = {
  slices: number; // number of batteries
  batteryDurationMinutes: number; // user input
  minHeight: number; // feet AGL
  maxHeight?: number | null; // feet AGL, optional
};

// Internal constants (mirrors production defaults)
const R0_FT = 150; // starting radius (ft)
const RHOLD_FT = 1595; // target hold radius (ft) used for alpha calc

// Map battery minutes to bounce count N (10min→5, 20min→8; clamped [3,12])
function mapBatteryToBounces(minutes: number): number {
  const n = Math.round(5 + 0.3 * (minutes - 10));
  return Math.max(3, Math.min(12, n));
}

// Core spiral generator (ported from production logic, elevation-agnostic)
function makeSpiral(dphi: number, N: number, r0: number, rHold: number, steps: number = 1200): { x: number; y: number }[] {
  const baseAlpha = Math.log(rHold / r0) / (N * dphi);
  const radiusRatio = rHold / r0;

  let earlyDensityFactor: number;
  let lateDensityFactor: number;
  if (radiusRatio > 20) {
    earlyDensityFactor = 1.02;
    lateDensityFactor = 0.80;
  } else if (radiusRatio > 10) {
    earlyDensityFactor = 1.05;
    lateDensityFactor = 0.85;
  } else {
    earlyDensityFactor = 1.0;
    lateDensityFactor = 0.90;
  }

  const alphaEarly = baseAlpha * earlyDensityFactor;
  const alphaLate = baseAlpha * lateDensityFactor;

  const tOut = N * dphi;
  const tHold = dphi;
  const tTotal = 2 * tOut + tHold;

  const tTransition = tOut * 0.4;
  const rTransition = r0 * Math.exp(alphaEarly * tTransition);
  const actualMaxRadius = rTransition * Math.exp(alphaLate * (tOut - tTransition));

  const spiralPoints: { x: number; y: number }[] = [];

  for (let i = 0; i < steps; i++) {
    const th = (i * tTotal) / (steps - 1);

    let r: number;
    if (th <= tOut) {
      if (th <= tTransition) {
        r = r0 * Math.exp(alphaEarly * th);
      } else {
        r = rTransition * Math.exp(alphaLate * (th - tTransition));
      }
    } else if (th <= tOut + tHold) {
      r = actualMaxRadius;
    } else {
      const inboundT = th - (tOut + tHold);
      r = actualMaxRadius * Math.exp(-alphaLate * inboundT);
    }

    const phaseVal = ((th / dphi) % 2 + 2) % 2;
    const phi = phaseVal <= 1 ? phaseVal * dphi : (2 - phaseVal) * dphi;

    spiralPoints.push({ x: r * Math.cos(phi), y: r * Math.sin(phi) });
  }

  return spiralPoints;
}

function buildSlice(sliceIdx: number, slices: number, N: number): { waypoints: Omit<Waypoint, 'z'>[]; tTotal: number; dphi: number; } {
  const dphi = (2 * Math.PI) / slices;
  const offset = Math.PI / 2 + sliceIdx * dphi;

  const spiralPts = makeSpiral(dphi, N, R0_FT, RHOLD_FT);
  const tOut = N * dphi;
  const tHold = dphi;
  const tTotal = 2 * tOut + tHold;

  const sampleAt = (targetT: number, phase: string, index: number): Omit<Waypoint, 'z'> => {
    const targetIndex = Math.round((targetT * (spiralPts.length - 1)) / tTotal);
    const clampedIndex = Math.max(0, Math.min(spiralPts.length - 1, targetIndex));
    const pt = spiralPts[clampedIndex];

    const rotX = pt.x * Math.cos(offset) - pt.y * Math.sin(offset);
    const rotY = pt.x * Math.sin(offset) + pt.y * Math.cos(offset);

    return { x: rotX, y: rotY, phase, index } as Omit<Waypoint, 'z'>;
  };

  const waypoints: Omit<Waypoint, 'z'>[] = [];
  let idx = 0;

  // outbound start
  waypoints.push(sampleAt(0, 'outbound_start', idx++));

  // outbound mid + bounce for each bounce
  for (let b = 1; b <= N; b++) {
    const tMid = (b - 0.5) * dphi;
    waypoints.push(sampleAt(tMid, `outbound_mid_${b}`, idx++));
    const tBounce = b * dphi;
    waypoints.push(sampleAt(tBounce, `outbound_bounce_${b}`, idx++));
  }

  // hold mid + end
  const tMidHold = tOut + tHold / 2;
  const tEndHold = tOut + tHold;
  waypoints.push(sampleAt(tMidHold, 'hold_mid', idx++));
  waypoints.push(sampleAt(tEndHold, 'hold_end', idx++));

  // inbound first mid
  const tFirstInboundMid = tEndHold + 0.5 * dphi;
  waypoints.push(sampleAt(tFirstInboundMid, 'inbound_mid_0', idx++));

  // inbound bounce + midpoints
  for (let b = 1; b <= N; b++) {
    const tBounce = tEndHold + b * dphi;
    waypoints.push(sampleAt(tBounce, `inbound_bounce_${b}`, idx++));
    if (b < N) {
      const tMid = tEndHold + (b + 0.5) * dphi;
      waypoints.push(sampleAt(tMid, `inbound_mid_${b}`, idx++));
    }
  }

  return { waypoints, tTotal, dphi };
}

// Compute 3D altitudes (AGL) per production rules, no terrain
function applyAltitudeAGL(waypoints: Omit<Waypoint, 'z'>[], minHeight: number, maxHeight?: number | null): Waypoint[] {
  if (waypoints.length === 0) return [] as Waypoint[];

  // First waypoint: baseline at minHeight
  const firstDist = Math.hypot(waypoints[0].x, waypoints[0].y);
  let maxOutboundAltitude = minHeight;
  let maxOutboundDistance = firstDist;

  const withZ: Waypoint[] = [];

  for (let i = 0; i < waypoints.length; i++) {
    const wp = waypoints[i];
    const distFromCenter = Math.hypot(wp.x, wp.y);

    let desiredAgl: number;
    if (i === 0) {
      desiredAgl = minHeight;
      maxOutboundAltitude = desiredAgl;
      maxOutboundDistance = distFromCenter;
    } else if (wp.phase.includes('outbound') || wp.phase.includes('hold')) {
      const additionalDistance = Math.max(0, distFromCenter - firstDist);
      const aglIncrement = additionalDistance * 0.37; // outbound climb
      desiredAgl = minHeight + aglIncrement;
      if (desiredAgl > maxOutboundAltitude) {
        maxOutboundAltitude = desiredAgl;
        maxOutboundDistance = distFromCenter;
      }
    } else if (wp.phase.includes('inbound')) {
      const distFromMax = Math.max(0, maxOutboundDistance - distFromCenter);
      const altitudeDecrease = distFromMax * 0.1; // inbound descent
      desiredAgl = maxOutboundAltitude - altitudeDecrease;
      desiredAgl = Math.max(minHeight, desiredAgl);
    } else {
      const additionalDistance = Math.max(0, distFromCenter - firstDist);
      const aglIncrement = additionalDistance * 0.37;
      desiredAgl = minHeight + aglIncrement;
    }

    // Clamp to max if present
    if (typeof maxHeight === 'number' && !Number.isNaN(maxHeight)) {
      desiredAgl = Math.min(desiredAgl, maxHeight);
    }
    desiredAgl = Math.max(minHeight, desiredAgl);

    withZ.push({ ...wp, z: desiredAgl });
  }

  return withZ;
}

function PathView({ params, sliceIndex, showLabels }: { params: FlightParams; sliceIndex: number; showLabels: boolean }) {
  const N = useMemo(() => mapBatteryToBounces(params.batteryDurationMinutes), [params.batteryDurationMinutes]);

  const waypoints = useMemo(() => {
    const { waypoints } = buildSlice(sliceIndex, params.slices, N);
    return applyAltitudeAGL(waypoints, params.minHeight, params.maxHeight);
  }, [params.slices, params.minHeight, params.maxHeight, sliceIndex, N]);

  const vectors = useMemo(() => waypoints.map(w => new THREE.Vector3(w.x, w.y, w.z)), [waypoints]);

  return (
    <group>
      {vectors.length >= 2 && (
        <Line points={vectors} color="#00ff88" lineWidth={2.5} transparent opacity={0.95} />
      )}

      {/* Center reference */}
      <mesh position={[0, 0, 0]}>
        <sphereGeometry args={[10, 16, 16]} />
        <meshBasicMaterial color="#666666" />
      </mesh>

      {/* Waypoint markers */}
      {waypoints.map((wp, i) => {
        const isStart = wp.phase === 'outbound_start';
        const isBounce = wp.phase.includes('bounce');
        const isHold = wp.phase.includes('hold');

        let color = '#ffffff';
        let size = 6;
        if (isStart) { color = '#ff0000'; size = 14; }
        else if (isBounce) { color = '#ffaa00'; size = 9; }
        else if (isHold) { color = '#0088ff'; size = 9; }

        return (
          <group key={i}>
            <mesh position={[wp.x, wp.y, wp.z]}>
              <sphereGeometry args={[size, 16, 16]} />
              <meshBasicMaterial color={color} />
            </mesh>
            {showLabels && (
              <Html distanceFactor={150} center>
                <div style={{
                  background: 'rgba(0,0,0,0.85)', color: 'white', padding: '3px 8px',
                  borderRadius: 4, fontSize: 11, whiteSpace: 'nowrap', transform: 'translateY(-25px)'
                }}>
                  {wp.index}: {wp.phase} · {Math.round(wp.z)}ft
                </div>
              </Html>
            )}
          </group>
        );
      })}
    </group>
  );
}

export default function ShapeLabPage() {
  const [params, setParams] = useState<FlightParams>({
    slices: 3,
    batteryDurationMinutes: 15,
    minHeight: 120,
    maxHeight: 400,
  });
  const [sliceIndex, setSliceIndex] = useState(0);
  const [showLabels, setShowLabels] = useState(false);

  // Three.js setup with flight path visualization
  useEffect(() => {
    const canvas = document.getElementById('shape-lab-canvas') as HTMLCanvasElement;
    if (!canvas) return;

    // Wait a bit to ensure the canvas is ready
    setTimeout(() => {
      try {
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, canvas.clientWidth / canvas.clientHeight, 0.1, 10000);
        const renderer = new THREE.WebGLRenderer({ 
          canvas, 
          antialias: true,
          alpha: false,
          powerPreference: "high-performance"
        });
        
        renderer.setSize(canvas.clientWidth, canvas.clientHeight);
        renderer.setClearColor(0x0a0a0a);
        renderer.setPixelRatio(window.devicePixelRatio);
        
        // Add grid helper on XZ plane (Three.js standard: Y is up)
        // Scaled 1.5x for better visual presence
        const gridHelper = new THREE.GridHelper(15000, 40, 0x3a3a3c, 0x1c1c1e);
        scene.add(gridHelper);
        
        // Add axes helper (Apple colors: X=red, Y=green/up, Z=blue)
        const axesHelper = new THREE.AxesHelper(750);
        scene.add(axesHelper);
        
        // Center reference sphere (subtle)
        const centerGeometry = new THREE.SphereGeometry(12, 16, 16);
        const centerMaterial = new THREE.MeshBasicMaterial({ 
          color: 0x8e8e93,
          transparent: true,
          opacity: 0.3
        });
        const centerSphere = new THREE.Mesh(centerGeometry, centerMaterial);
        scene.add(centerSphere);
        
        // Position camera for perspective view from above and to the side
        // Scaled 1.5x for larger visualization
        camera.position.set(3000, 2250, 3000);
        camera.lookAt(0, 0, 0); // Focus on true origin
        
        // Generate flight path
        const N = mapBatteryToBounces(params.batteryDurationMinutes);
        const { waypoints } = buildSlice(sliceIndex, params.slices, N);
        const waypointsWithZ = applyAltitudeAGL(waypoints, params.minHeight, params.maxHeight);
        
        // Coordinate transform: Our (x,y,z) -> Three.js (x,y,z) where our z=altitude becomes Three.js y
        // Our system: x=horizontal1, y=horizontal2, z=altitude
        // Three.js: x=horizontal1, y=altitude, z=horizontal2
        // Scaled 1.5x for better visual presence (doesn't change actual flight path data)
        const VISUAL_SCALE = 1.5;
        const toThreeJS = (wp: { x: number; y: number; z: number }) => 
          new THREE.Vector3(wp.x * VISUAL_SCALE, wp.z * VISUAL_SCALE, wp.y * VISUAL_SCALE);
        
        // Create flight path line (Apple blue)
        if (waypointsWithZ.length >= 2) {
          const points = waypointsWithZ.map(wp => toThreeJS(wp));
          const geometry = new THREE.BufferGeometry().setFromPoints(points);
          const material = new THREE.LineBasicMaterial({ 
            color: 0x007AFF, 
            linewidth: 3,
            transparent: true,
            opacity: 0.9
          });
          const line = new THREE.Line(geometry, material);
          scene.add(line);
        }
        
        // Camera/gimbal parameters (typical drone specs)
        const cameraFOV = 84; // degrees (DJI typical wide FOV)
        const frustumLength = 150; // visual length of frustum (scaled 1.5x)
        const projectionLength = 750; // length of projection lines when hovering (scaled 1.5x)
        
        // Store frustum meshes for hover interaction
        const frustumMeshes: Array<{ mesh: THREE.Group; waypoint: typeof waypointsWithZ[0]; index: number }> = [];
        let hoveredFrustum: THREE.Group | null = null;
        const projectionLines: THREE.Line[] = [];
        
        // Function to create camera frustum
        const createFrustum = (wp: typeof waypointsWithZ[0], wpIndex: number) => {
          const group = new THREE.Group();
          const pos = toThreeJS(wp);
          group.position.copy(pos);
          
          // For photogrammetry spiral: camera aims at center (0,0,0)
          // Calculate heading: angle from waypoint to center in XZ plane
          const horizontalDist = Math.hypot(wp.x, wp.y);
          let heading = 0;
          if (horizontalDist > 0.1) {
            // In Three.js: X and Z are horizontal, Y is vertical
            // atan2(x, z) gives angle toward center
            heading = Math.atan2(-wp.x, -wp.y);
          }
          
          // Calculate gimbal pitch: angle to look down at center
          // Pitch = atan2(altitude, horizontal_distance)
          let gimbalPitch = -90; // default nadir
          if (horizontalDist > 0.1) {
            const pitchAngle = Math.atan2(wp.z, horizontalDist);
            gimbalPitch = -(90 - (pitchAngle * 180 / Math.PI)); // convert to gimbal convention
          }
          
          // Create frustum pyramid
          const fovRad = (cameraFOV * Math.PI) / 180;
          const halfFOV = fovRad / 2;
          const width = Math.tan(halfFOV) * frustumLength;
          
          // Frustum vertices (pyramid pointing down and forward)
          const vertices = new Float32Array([
            // Apex (camera position)
            0, 0, 0,
            // Base corners
            -width, -frustumLength, -width,
            width, -frustumLength, -width,
            width, -frustumLength, width,
            -width, -frustumLength, width,
          ]);
          
          const indices = new Uint16Array([
            // Lines from apex to corners
            0, 1,  0, 2,  0, 3,  0, 4,
            // Base rectangle
            1, 2,  2, 3,  3, 4,  4, 1
          ]);
          
          const geometry = new THREE.BufferGeometry();
          geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
          geometry.setIndex(new THREE.BufferAttribute(indices, 1));
          
          const material = new THREE.LineBasicMaterial({ 
            color: 0x8e8e93, 
            transparent: true, 
            opacity: 0.2 
          });
          const frustum = new THREE.LineSegments(geometry, material);
          
          // Orient frustum: YXZ rotation order to prevent roll
          // Y rotation (heading) first, then X rotation (pitch)
          frustum.rotation.order = 'YXZ';
          frustum.rotation.y = heading;
          frustum.rotation.x = (gimbalPitch * Math.PI) / 180;
          frustum.rotation.z = 0; // explicitly no roll
          
          // Debug: Log heading and pitch for first few waypoints
          if (wpIndex < 5) {
            console.log(`WP ${wpIndex}: heading=${(heading * 180 / Math.PI).toFixed(1)}°, pitch=${gimbalPitch.toFixed(1)}°, dist=${horizontalDist.toFixed(0)}ft, alt=${wp.z.toFixed(0)}ft`);
          }
          
          group.add(frustum);
          
          // Add small direction indicator
          const arrowGeometry = new THREE.ConeGeometry(3, 12, 8); // scaled 1.5x
          const arrowMaterial = new THREE.MeshBasicMaterial({ color: 0x8e8e93, transparent: true, opacity: 0.4 });
          const arrow = new THREE.Mesh(arrowGeometry, arrowMaterial);
          arrow.rotation.order = 'YXZ';
          arrow.rotation.y = heading;
          arrow.rotation.x = Math.PI + (gimbalPitch * Math.PI) / 180; // point down + pitch
          arrow.rotation.z = 0; // no roll
          arrow.position.y = -frustumLength / 2;
          group.add(arrow);
          
          return group;
        };
        
        // Add waypoint markers and frustums
        waypointsWithZ.forEach((wp, i) => {
          const isStart = wp.phase === 'outbound_start';
          const isBounce = wp.phase.includes('bounce');
          const isHold = wp.phase.includes('hold');
          
          let color = 0x8e8e93;
          let size = 4.5; // scaled 1.5x
          if (isStart) { color = 0xff3b30; size = 9; } // scaled 1.5x
          else if (isBounce) { color = 0xff9500; size = 6; } // scaled 1.5x
          else if (isHold) { color = 0x007aff; size = 6; } // scaled 1.5x
          
          const geometry = new THREE.SphereGeometry(size, 16, 16);
          const material = new THREE.MeshBasicMaterial({ color });
          const sphere = new THREE.Mesh(geometry, material);
          const pos = toThreeJS(wp);
          sphere.position.copy(pos);
          scene.add(sphere);
          
          // Add camera frustum
          const frustum = createFrustum(wp, i);
          scene.add(frustum);
          frustumMeshes.push({ mesh: frustum, waypoint: wp, index: i });
        });
        
        // Proper orbit controls with dynamic orbit center
        let isDragging = false;
        let mouseButton = 0; // Track which button is pressed (0=left, 2=right)
        let previousMousePosition = { x: 0, y: 0 };
        const rotationSpeed = 0.005;
        const panSpeed = 3; // Scaled for larger visualization
        
        // Orbit center point (can be moved with pan)
        const orbitCenter = new THREE.Vector3(0, 0, 0);
        
        // Spherical coordinates for orbit (Y-up system)
        // Scaled 1.5x to match larger visualization
        const initialOffset = new THREE.Vector3(3000, 2250, 3000);
        let theta = Math.atan2(initialOffset.x, initialOffset.z); // horizontal angle
        let phi = Math.acos(initialOffset.y / initialOffset.length()); // vertical angle from Y axis
        let radius = initialOffset.length();
        
        const updateCameraPosition = () => {
          const offset = new THREE.Vector3(
            radius * Math.sin(phi) * Math.sin(theta),
            radius * Math.cos(phi),
            radius * Math.sin(phi) * Math.cos(theta)
          );
          camera.position.copy(orbitCenter).add(offset);
          camera.lookAt(orbitCenter);
        };
        
        canvas.addEventListener('mousedown', (e) => {
          isDragging = true;
          mouseButton = e.button; // 0=left, 1=middle, 2=right
          previousMousePosition = { x: e.clientX, y: e.clientY };
          e.preventDefault(); // Prevent context menu on right click
        });
        
        canvas.addEventListener('mouseup', () => {
          isDragging = false;
        });
        
        canvas.addEventListener('mouseleave', () => {
          isDragging = false;
        });
        
        canvas.addEventListener('contextmenu', (e) => {
          e.preventDefault(); // Prevent context menu on right click
        });
        
        canvas.addEventListener('mousemove', (e) => {
          if (!isDragging) return;
          
          const deltaX = e.clientX - previousMousePosition.x;
          const deltaY = e.clientY - previousMousePosition.y;
          
          // Pan mode: right mouse button (2) OR ctrl/cmd key
          const isPanMode = mouseButton === 2 || e.ctrlKey || e.metaKey;
          
          if (isPanMode) {
            // Pan mode - move the orbit center
            const panVector = new THREE.Vector3(-deltaX * panSpeed, deltaY * panSpeed, 0);
            panVector.applyQuaternion(camera.quaternion);
            orbitCenter.add(panVector);
            updateCameraPosition();
          } else {
            // Orbit mode (default) - reversed for natural feel
            theta -= deltaX * rotationSpeed;
            phi -= deltaY * rotationSpeed;
            
            // Clamp phi to prevent camera from flipping
            phi = Math.max(0.1, Math.min(Math.PI - 0.1, phi));
            
            updateCameraPosition();
          }
          
          previousMousePosition = { x: e.clientX, y: e.clientY };
        });
        
        canvas.addEventListener('wheel', (e) => {
          e.preventDefault();
          const zoomSpeed = 1.02; // Reduced sensitivity for smoother zoom
          radius *= e.deltaY > 0 ? zoomSpeed : 1 / zoomSpeed;
          radius = Math.max(100, Math.min(15000, radius)); // Clamp zoom (adjusted for larger scale)
          updateCameraPosition();
        });
        
        const animate = () => {
          requestAnimationFrame(animate);
          renderer.render(scene, camera);
        };
        
        animate();
        
        // Store cleanup function
        (window as any).shapeLabCleanup = () => {
          renderer.dispose();
        };
      } catch (error) {
        console.error('Three.js setup failed:', error);
      }
    }, 100);
    
    return () => {
      if ((window as any).shapeLabCleanup) {
        (window as any).shapeLabCleanup();
      }
    };
  }, [params, sliceIndex]);

  useEffect(() => {
    if (sliceIndex >= params.slices) {
      setSliceIndex(Math.max(0, params.slices - 1));
    }
  }, [params.slices, sliceIndex]);

  const N = mapBatteryToBounces(params.batteryDurationMinutes);
  const dphi = (2 * Math.PI) / params.slices;

  return (
    <div style={{ 
      width: '100%', 
      height: 'calc(100vh - 120px)', 
      background: '#000000', 
      display: 'flex',
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif'
    }}>
      {/* Control Panel - Apple Style */}
      <div style={{ 
        width: 320, 
        background: 'rgba(28, 28, 30, 0.95)', 
        backdropFilter: 'blur(20px)',
        borderRight: '0.5px solid rgba(255, 255, 255, 0.1)',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Header */}
        <div style={{ 
          padding: '24px 20px 16px', 
          borderBottom: '0.5px solid rgba(255, 255, 255, 0.1)' 
        }}>
          <h1 style={{ 
            color: '#ffffff', 
            margin: 0, 
            fontSize: '22px', 
            fontWeight: '600',
            letterSpacing: '-0.02em'
          }}>
            Flight Shape Lab
          </h1>
          <p style={{ 
            color: 'rgba(255, 255, 255, 0.6)', 
            margin: '4px 0 0', 
            fontSize: '14px',
            fontWeight: '400'
          }}>
            Design and visualize 3D drone flight patterns
          </p>
        </div>

        
        {/* Controls Container */}
        <div style={{ flex: 1, padding: '20px', overflowY: 'auto' }}>
          
          {/* Diagnostics Card */}
          <div style={{ 
            background: 'rgba(255, 255, 255, 0.05)', 
            borderRadius: '12px', 
            padding: '16px', 
            marginBottom: '24px',
            border: '0.5px solid rgba(255, 255, 255, 0.1)'
          }}>
            <div style={{ color: '#ffffff', fontSize: '15px', fontWeight: '600', marginBottom: '12px' }}>
              Flight Parameters
            </div>
            <div style={{ fontSize: '13px', lineHeight: '1.4', color: 'rgba(255, 255, 255, 0.7)' }}>
              <div>Bounces: {N}</div>
              <div>Angle: {(360 / params.slices).toFixed(1)}°</div>
              <div>Slice: {sliceIndex + 1} of {params.slices}</div>
            </div>
          </div>

          {/* Control Groups */}
          <div style={{ marginBottom: '24px' }}>
            <label style={{ 
              color: '#ffffff', 
              display: 'block', 
              marginBottom: '12px', 
              fontSize: '15px',
              fontWeight: '500'
            }}>
              Battery Configuration
            </label>
            
            <div style={{ marginBottom: '20px' }}>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginBottom: '8px'
              }}>
                <span style={{ color: 'rgba(255, 255, 255, 0.8)', fontSize: '14px' }}>
                  Number of Batteries
                </span>
                <span style={{ 
                  color: '#007AFF', 
                  fontSize: '14px', 
                  fontWeight: '600',
                  background: 'rgba(0, 122, 255, 0.15)',
                  padding: '2px 8px',
                  borderRadius: '6px'
                }}>
                  {params.slices}
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="8"
                value={params.slices}
                onChange={(e) => setParams(p => ({ ...p, slices: parseInt(e.target.value, 10) }))}
                style={{ 
                  width: '100%', 
                  height: '6px',
                  background: 'rgba(255, 255, 255, 0.2)',
                  borderRadius: '3px',
                  outline: 'none',
                  appearance: 'none'
                }}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginBottom: '8px'
              }}>
                <span style={{ color: 'rgba(255, 255, 255, 0.8)', fontSize: '14px' }}>
                  Battery Duration
                </span>
                <span style={{ 
                  color: '#34C759', 
                  fontSize: '14px', 
                  fontWeight: '600',
                  background: 'rgba(52, 199, 89, 0.15)',
                  padding: '2px 8px',
                  borderRadius: '6px'
                }}>
                  {params.batteryDurationMinutes}m
                </span>
              </div>
              <input
                type="range"
                min="5"
                max="30"
                value={params.batteryDurationMinutes}
                onChange={(e) => setParams(p => ({ ...p, batteryDurationMinutes: parseInt(e.target.value, 10) }))}
                style={{ 
                  width: '100%', 
                  height: '6px',
                  background: 'rgba(255, 255, 255, 0.2)',
                  borderRadius: '3px',
                  outline: 'none',
                  appearance: 'none'
                }}
              />
            </div>
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label style={{ 
              color: '#ffffff', 
              display: 'block', 
              marginBottom: '12px', 
              fontSize: '15px',
              fontWeight: '500'
            }}>
              Altitude Settings
            </label>
            
            <div style={{ marginBottom: '20px' }}>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginBottom: '8px'
              }}>
                <span style={{ color: 'rgba(255, 255, 255, 0.8)', fontSize: '14px' }}>
                  Minimum Altitude
                </span>
                <span style={{ 
                  color: '#FF9500', 
                  fontSize: '14px', 
                  fontWeight: '600',
                  background: 'rgba(255, 149, 0, 0.15)',
                  padding: '2px 8px',
                  borderRadius: '6px'
                }}>
                  {params.minHeight}ft
                </span>
              </div>
              <input
                type="range"
                min="50"
                max="400"
                step="5"
                value={params.minHeight}
                onChange={(e) => setParams(p => ({ ...p, minHeight: parseInt(e.target.value, 10) }))}
                style={{ 
                  width: '100%', 
                  height: '6px',
                  background: 'rgba(255, 255, 255, 0.2)',
                  borderRadius: '3px',
                  outline: 'none',
                  appearance: 'none'
                }}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginBottom: '8px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <input
                    type="checkbox"
                    checked={typeof params.maxHeight === 'number'}
                    onChange={(e) => setParams(p => ({ ...p, maxHeight: e.target.checked ? (p.maxHeight ?? Math.max(p.minHeight + 50, 200)) : null }))}
                    style={{ 
                      marginRight: '8px',
                      accentColor: '#007AFF'
                    }}
                  />
                  <span style={{ color: 'rgba(255, 255, 255, 0.8)', fontSize: '14px' }}>
                    Maximum Altitude
                  </span>
                </div>
                {typeof params.maxHeight === 'number' && (
                  <span style={{ 
                    color: '#FF3B30', 
                    fontSize: '14px', 
                    fontWeight: '600',
                    background: 'rgba(255, 59, 48, 0.15)',
                    padding: '2px 8px',
                    borderRadius: '6px'
                  }}>
                    {params.maxHeight}ft
                  </span>
                )}
              </div>
              {typeof params.maxHeight === 'number' && (
                <input
                  type="range"
                  min={params.minHeight + 10}
                  max="1000"
                  step="10"
                  value={params.maxHeight}
                  onChange={(e) => setParams(p => ({ ...p, maxHeight: parseInt(e.target.value, 10) }))}
                  style={{ 
                    width: '100%', 
                    height: '6px',
                    background: 'rgba(255, 255, 255, 0.2)',
                    borderRadius: '3px',
                    outline: 'none',
                    appearance: 'none'
                  }}
                />
              )}
            </div>
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label style={{ 
              color: '#ffffff', 
              display: 'block', 
              marginBottom: '12px', 
              fontSize: '15px',
              fontWeight: '500'
            }}>
              View Options
            </label>
            
            <div style={{ marginBottom: '20px' }}>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginBottom: '8px'
              }}>
                <span style={{ color: 'rgba(255, 255, 255, 0.8)', fontSize: '14px' }}>
                  Active Slice
                </span>
                <span style={{ 
                  color: '#AF52DE', 
                  fontSize: '14px', 
                  fontWeight: '600',
                  background: 'rgba(175, 82, 222, 0.15)',
                  padding: '2px 8px',
                  borderRadius: '6px'
                }}>
                  {sliceIndex + 1}
                </span>
              </div>
              <input
                type="range"
                min="0"
                max={params.slices - 1}
                value={sliceIndex}
                onChange={(e) => setSliceIndex(parseInt(e.target.value, 10))}
                style={{ 
                  width: '100%', 
                  height: '6px',
                  background: 'rgba(255, 255, 255, 0.2)',
                  borderRadius: '3px',
                  outline: 'none',
                  appearance: 'none'
                }}
              />
            </div>

            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              padding: '12px',
              background: 'rgba(255, 255, 255, 0.05)',
              borderRadius: '8px',
              border: '0.5px solid rgba(255, 255, 255, 0.1)'
            }}>
              <span style={{ color: 'rgba(255, 255, 255, 0.8)', fontSize: '14px' }}>
                Show Labels
              </span>
              <input
                type="checkbox"
                checked={showLabels}
                onChange={(e) => setShowLabels(e.target.checked)}
                style={{ accentColor: '#007AFF' }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* 3D Viewer */}
      <div style={{ flex: 1, position: 'relative' }}>
        <div style={{ width: '100%', height: '100%', background: '#000' }}>
          <canvas 
            id="shape-lab-canvas"
            style={{ width: '100%', height: '100%', display: 'block' }}
          />
        </div>

        <div style={{
          position: 'absolute', top: 20, left: 20, 
          background: 'rgba(28, 28, 30, 0.95)', 
          backdropFilter: 'blur(20px)',
          color: 'white',
          padding: '16px 20px', 
          borderRadius: 12, 
          fontSize: 13, 
          fontFamily: '-apple-system, BlinkMacSystemFont, system-ui, sans-serif',
          lineHeight: '1.5',
          border: '0.5px solid rgba(255, 255, 255, 0.1)'
        }}>
          <div style={{ fontWeight: '600', marginBottom: 8, color: '#ffffff' }}>3D Controls</div>
          <div style={{ marginBottom: 4 }}>• Left Drag: Orbit around focus point</div>
          <div style={{ marginBottom: 4 }}>• Right Drag / Ctrl(⌘)+Drag: Move focus point</div>
          <div style={{ marginBottom: 8 }}>• Scroll: Zoom in/out</div>
          <div style={{ 
            marginTop: 8, 
            paddingTop: 8, 
            borderTop: '0.5px solid rgba(255, 255, 255, 0.2)', 
            opacity: 0.7,
            fontSize: 12
          }}>
            Units in feet. Green (Y) axis = altitude (AGL)
          </div>
        </div>
      </div>
    </div>
  );
}


