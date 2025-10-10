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
        renderer.setClearColor(0x000000);
        renderer.setPixelRatio(window.devicePixelRatio);
        
        // Add grid helper
        const gridHelper = new THREE.GridHelper(10000, 40, 0x333333, 0x222222);
        scene.add(gridHelper);
        
        // Add axes helper
        const axesHelper = new THREE.AxesHelper(500);
        scene.add(axesHelper);
        
        // Center reference sphere
        const centerGeometry = new THREE.SphereGeometry(10, 16, 16);
        const centerMaterial = new THREE.MeshBasicMaterial({ color: 0x666666 });
        const centerSphere = new THREE.Mesh(centerGeometry, centerMaterial);
        scene.add(centerSphere);
        
        // Position camera for top-down view
        camera.position.set(0, -2500, 1200);
        camera.lookAt(0, 0, 0);
        
        // Generate flight path
        const N = mapBatteryToBounces(params.batteryDurationMinutes);
        const { waypoints } = buildSlice(sliceIndex, params.slices, N);
        const waypointsWithZ = applyAltitudeAGL(waypoints, params.minHeight, params.maxHeight);
        
        // Create flight path line
        if (waypointsWithZ.length >= 2) {
          const points = waypointsWithZ.map(wp => new THREE.Vector3(wp.x, wp.y, wp.z));
          const geometry = new THREE.BufferGeometry().setFromPoints(points);
          const material = new THREE.LineBasicMaterial({ color: 0x00ff88, linewidth: 2 });
          const line = new THREE.Line(geometry, material);
          scene.add(line);
        }
        
        // Add waypoint markers
        waypointsWithZ.forEach((wp, i) => {
          const isStart = wp.phase === 'outbound_start';
          const isBounce = wp.phase.includes('bounce');
          const isHold = wp.phase.includes('hold');
          
          let color = 0xffffff;
          let size = 6;
          if (isStart) { color = 0xff0000; size = 14; }
          else if (isBounce) { color = 0xffaa00; size = 9; }
          else if (isHold) { color = 0x0088ff; size = 9; }
          
          const geometry = new THREE.SphereGeometry(size, 16, 16);
          const material = new THREE.MeshBasicMaterial({ color });
          const sphere = new THREE.Mesh(geometry, material);
          sphere.position.set(wp.x, wp.y, wp.z);
          scene.add(sphere);
        });
        
        // Simple orbit controls
        let mouseDown = false;
        let mouseX = 0, mouseY = 0;
        
        canvas.addEventListener('mousedown', (e) => {
          mouseDown = true;
          mouseX = e.clientX;
          mouseY = e.clientY;
        });
        
        canvas.addEventListener('mouseup', () => {
          mouseDown = false;
        });
        
        canvas.addEventListener('mousemove', (e) => {
          if (!mouseDown) return;
          
          const deltaX = e.clientX - mouseX;
          const deltaY = e.clientY - mouseY;
          
          camera.position.x += deltaX * 2;
          camera.position.y += deltaY * 2;
          camera.lookAt(0, 0, 0);
          
          mouseX = e.clientX;
          mouseY = e.clientY;
        });
        
        canvas.addEventListener('wheel', (e) => {
          e.preventDefault();
          const scale = e.deltaY > 0 ? 1.1 : 0.9;
          camera.position.multiplyScalar(scale);
          camera.lookAt(0, 0, 0);
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
    <div style={{ width: '100%', height: 'calc(100vh - 120px)', background: '#0a0a0a', display: 'flex' }}>
      {/* Control Panel */}
      <div style={{
        width: 360,
        background: '#1a1a1a',
        padding: 20,
        overflowY: 'auto',
        borderRight: '1px solid #333',
        color: '#fff',
        fontFamily: 'monospace'
      }}>
        <h2 style={{ fontSize: 20, marginBottom: 16, color: '#00ff88' }}>3D Flight Shape Lab</h2>

        <div style={{ marginBottom: 16, padding: 12, background: '#252525', borderRadius: 8 }}>
          <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 6 }}>Diagnostics</div>
          <div style={{ fontSize: 12, lineHeight: '18px' }}>
            <div>N (bounces): {N}</div>
            <div>dphi: {(dphi).toFixed(4)} rad · {(360 / params.slices).toFixed(2)}°</div>
            <div>Slice: {sliceIndex + 1} / {params.slices}</div>
            <div>Units: 1 = 1 ft</div>
          </div>
        </div>

        {/* Slices */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 6, fontSize: 12, opacity: 0.85 }}>Number of Batteries (slices)</label>
          <input
            type="range"
            min={1}
            max={8}
            value={params.slices}
            onChange={(e) => setParams(p => ({ ...p, slices: parseInt(e.target.value, 10) }))}
            style={{ width: '100%' }}
          />
          <div style={{ fontSize: 13, marginTop: 6 }}>{params.slices}</div>
        </div>

        {/* Battery duration */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 6, fontSize: 12, opacity: 0.85 }}>Battery Duration (minutes)</label>
          <input
            type="range"
            min={5}
            max={30}
            value={params.batteryDurationMinutes}
            onChange={(e) => setParams(p => ({ ...p, batteryDurationMinutes: parseInt(e.target.value, 10) }))}
            style={{ width: '100%' }}
          />
          <div style={{ fontSize: 13, marginTop: 6 }}>{params.batteryDurationMinutes} min</div>
        </div>

        {/* Min height */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 6, fontSize: 12, opacity: 0.85 }}>Minimum Altitude (AGL, ft)</label>
          <input
            type="range"
            min={50}
            max={400}
            step={5}
            value={params.minHeight}
            onChange={(e) => setParams(p => ({ ...p, minHeight: parseInt(e.target.value, 10) }))}
            style={{ width: '100%' }}
          />
          <div style={{ fontSize: 13, marginTop: 6 }}>{params.minHeight} ft</div>
        </div>

        {/* Max height with toggle */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 6, fontSize: 12, opacity: 0.85 }}>Maximum Altitude (AGL, ft)</label>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <input
              type="checkbox"
              checked={typeof params.maxHeight === 'number'}
              onChange={(e) => setParams(p => ({ ...p, maxHeight: e.target.checked ? (p.maxHeight ?? Math.max(p.minHeight + 50, 200)) : null }))}
            />
            <span style={{ fontSize: 12 }}>{typeof params.maxHeight === 'number' ? 'Enabled' : 'Off'}</span>
          </div>
          <input
            type="range"
            min={100}
            max={800}
            step={10}
            value={typeof params.maxHeight === 'number' ? params.maxHeight : Math.max(params.minHeight + 50, 200)}
            onChange={(e) => setParams(p => ({ ...p, maxHeight: parseInt(e.target.value, 10) }))}
            style={{ width: '100%', marginTop: 8, opacity: typeof params.maxHeight === 'number' ? 1 : 0.4 }}
            disabled={typeof params.maxHeight !== 'number'}
          />
          <div style={{ fontSize: 13, marginTop: 6 }}>{typeof params.maxHeight === 'number' ? `${params.maxHeight} ft` : 'Off'}</div>
        </div>

        {/* Slice selector */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 6, fontSize: 12, opacity: 0.85 }}>View Battery/Slice</label>
          <input
            type="range"
            min={0}
            max={params.slices - 1}
            value={sliceIndex}
            onChange={(e) => setSliceIndex(parseInt(e.target.value, 10))}
            style={{ width: '100%' }}
          />
          <div style={{ fontSize: 13, marginTop: 6 }}>Battery {sliceIndex + 1} of {params.slices}</div>
        </div>

        {/* Labels toggle */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
            <input type="checkbox" checked={showLabels} onChange={(e) => setShowLabels(e.target.checked)} style={{ marginRight: 8 }} />
            <span style={{ fontSize: 12 }}>Show Waypoint Labels</span>
          </label>
        </div>

        <div style={{ marginTop: 16, padding: 12, background: '#252525', borderRadius: 8, fontSize: 11, lineHeight: '18px' }}>
          <div style={{ color: '#00ff88', marginBottom: 6 }}>Legend</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <div style={{ width: 12, height: 12, background: '#ff0000', borderRadius: 9999 }} /> Start
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <div style={{ width: 12, height: 12, background: '#ffaa00', borderRadius: 9999 }} /> Bounce
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 12, height: 12, background: '#0088ff', borderRadius: 9999 }} /> Hold
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
          position: 'absolute', top: 20, left: 20, background: 'rgba(0,0,0,0.7)', color: 'white',
          padding: '10px 15px', borderRadius: 8, fontSize: 12, fontFamily: 'monospace'
        }}>
          <div>3D View: Drag to orbit/pan, Scroll to zoom</div>
          <div style={{ marginTop: 5, opacity: 0.7 }}>Units in feet. Z shows AGL altitude.</div>
        </div>
      </div>
    </div>
  );
}


