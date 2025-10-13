"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Line, Html } from '@react-three/drei';
import * as THREE from 'three';

interface Waypoint {
  x: number;
  y: number;
  z: number;
  phase: string;
  index: number;
}

interface FlightParams {
  slices: number;
  N: number;
  r0: number;
  rHold: number;
  battery_duration_minutes: number;
}

// Flight path generator (simplified, no elevation queries)
class SpiralGenerator {
  private FT2M = 0.3048;
  private EARTH_R = 6371000;
  
  makeSpiral(
    dphi: number,
    N: number,
    r0: number,
    r_hold: number,
    steps: number = 1200,
    options: { fullCircle?: boolean } = {}
  ): { x: number; y: number }[] {
    const base_alpha = Math.log(r_hold / r0) / (N * dphi);
    const radius_ratio = r_hold / r0;
    
    let early_density_factor: number, late_density_factor: number;
    if (radius_ratio > 20) {
      early_density_factor = 1.02;
      late_density_factor = 0.80;
    } else if (radius_ratio > 10) {
      early_density_factor = 1.05;
      late_density_factor = 0.85;
    } else {
      early_density_factor = 1.0;
      late_density_factor = 0.90;
    }
    
    const alpha_early = base_alpha * early_density_factor;
    const alpha_late = base_alpha * late_density_factor;
    
    const t_out = N * dphi;
    const t_hold = dphi;
    const t_total = 2 * t_out + t_hold;
    
    const t_transition = t_out * 0.4;
    const r_transition = r0 * Math.exp(alpha_early * t_transition);
    const actual_max_radius = r_transition * Math.exp(alpha_late * (t_out - t_transition));
    
    const spiral_points: { x: number; y: number }[] = [];
    
    for (let i = 0; i < steps; i++) {
      const th = i * t_total / (steps - 1);
      
      let r: number;
      if (th <= t_out) {
        if (th <= t_transition) {
          r = r0 * Math.exp(alpha_early * th);
        } else {
          r = r_transition * Math.exp(alpha_late * (th - t_transition));
        }
      } else if (th <= t_out + t_hold) {
        r = actual_max_radius;
      } else {
        const inbound_t = th - (t_out + t_hold);
        r = actual_max_radius * Math.exp(-alpha_late * inbound_t);
      }
      
      const phase = ((th / dphi) % 2 + 2) % 2;
      const phi = options.fullCircle
        ? th
        : phase <= 1
          ? phase * dphi
          : (2 - phase) * dphi;
      
      spiral_points.push({
        x: r * Math.cos(phi),
        y: r * Math.sin(phi)
      });
    }
    
    return spiral_points;
  }
  
  buildSlice(slice_idx: number, params: FlightParams): Waypoint[] {
    const dphi = 2 * Math.PI / params.slices;
    const offset = Math.PI / 2 + slice_idx * dphi;
    const singleSlice = params.slices === 1;
    
    const spiral_pts = this.makeSpiral(dphi, params.N, params.r0, params.rHold, 1200, {
      fullCircle: singleSlice
    });
    const t_out = params.N * dphi;
    const t_hold = dphi;
    const t_total = 2 * t_out + t_hold;
    const t_mid_hold = t_out + t_hold / 2;
    const t_end_hold = t_out + t_hold;
    const t_first_inbound_mid = t_end_hold + 0.5 * dphi;
    
    const schedule: { time: number; phase: string }[] = [];
    schedule.push({ time: 0, phase: 'outbound_start' });
    
    for (let bounce = 1; bounce <= params.N; bounce++) {
      const segment_start = (bounce - 1) * dphi;
      if (singleSlice) {
        schedule.push({ time: segment_start + 0.25 * dphi, phase: `outbound_support_${bounce}_pre` });
      }
      schedule.push({ time: segment_start + 0.5 * dphi, phase: `outbound_mid_${bounce}` });
      if (singleSlice) {
        schedule.push({ time: segment_start + 0.75 * dphi, phase: `outbound_support_${bounce}_post` });
      }
      schedule.push({ time: bounce * dphi, phase: `outbound_bounce_${bounce}` });
    }
    
    if (singleSlice) {
      schedule.push({ time: t_out + 0.25 * dphi, phase: 'hold_support_pre' });
    }
    schedule.push({ time: t_mid_hold, phase: 'hold_mid' });
    if (singleSlice) {
      schedule.push({ time: t_out + 0.75 * dphi, phase: 'hold_support_post' });
    }
    schedule.push({ time: t_end_hold, phase: 'hold_end' });
    if (singleSlice) {
      schedule.push({ time: t_end_hold + 0.25 * dphi, phase: 'inbound_support_entry_pre' });
    }
    schedule.push({ time: t_first_inbound_mid, phase: 'inbound_mid_0' });
    
    for (let bounce = 1; bounce <= params.N; bounce++) {
      if (singleSlice) {
        schedule.push({
          time: t_end_hold + (bounce - 0.25) * dphi,
          phase: `inbound_support_${bounce}_pre`
        });
      }
      const bounce_time = t_end_hold + bounce * dphi;
      schedule.push({ time: bounce_time, phase: `inbound_bounce_${bounce}` });
      if (singleSlice && bounce < params.N) {
        schedule.push({
          time: t_end_hold + (bounce + 0.25) * dphi,
          phase: `inbound_support_${bounce}_post`
        });
      }
      if (bounce < params.N) {
        const mid_time = t_end_hold + (bounce + 0.5) * dphi;
        schedule.push({ time: mid_time, phase: `inbound_mid_${bounce}` });
      }
    }
    
    const findSpiralPoint = (target_t: number, phase: string, index: number): Waypoint => {
      const normalized = Math.max(0, Math.min(t_total, target_t));
      const target_index = Math.round(normalized * (spiral_pts.length - 1) / t_total);
      const pt = spiral_pts[target_index];
      const rot_x = pt.x * Math.cos(offset) - pt.y * Math.sin(offset);
      const rot_y = pt.x * Math.sin(offset) + pt.y * Math.cos(offset);
      
      return {
        x: rot_x,
        y: rot_y,
        z: 0,
        phase,
        index
      };
    };
    
    const waypoints: Waypoint[] = [];
    let index = 0;
    for (const entry of schedule) {
      waypoints.push(findSpiralPoint(entry.time, entry.phase, index++));
    }
    
    return waypoints;
  }
  
  generateFlightPath(params: FlightParams, batteryIndex: number): Waypoint[] {
    return this.buildSlice(batteryIndex, params);
  }
}

function FlightPathVisualization({ waypoints, showLabels }: { waypoints: Waypoint[]; showLabels: boolean }) {
  const vectors = waypoints.map(wp => new THREE.Vector3(wp.x, wp.y, 0));
  
  return (
    <group>
      {/* Smooth path line */}
      {vectors.length >= 2 && (
        <Line
          points={vectors}
          color="#00ff88"
          lineWidth={2.5}
          transparent
          opacity={0.9}
        />
      )}
      
      {/* Grid reference */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, -1]}>
        <planeGeometry args={[10000, 10000]} />
        <meshBasicMaterial color="#1a1a1a" transparent opacity={0.5} />
      </mesh>
      
      {/* Grid lines for scale */}
      {Array.from({ length: 21 }, (_, i) => {
        const pos = (i - 10) * 500;
        return (
          <group key={i}>
            <mesh position={[pos, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
              <planeGeometry args={[10000, 1]} />
              <meshBasicMaterial color="#333333" transparent opacity={0.3} />
            </mesh>
            <mesh position={[0, pos, 0]}>
              <planeGeometry args={[10000, 1]} />
              <meshBasicMaterial color="#333333" transparent opacity={0.3} />
            </mesh>
          </group>
        );
      })}
      
      {/* Center marker */}
      <mesh position={[0, 0, 0]}>
        <circleGeometry args={[15, 32]} />
        <meshBasicMaterial color="#666666" />
      </mesh>
      
      {/* Waypoint markers */}
      {waypoints.map((wp, i) => {
        const isStart = wp.phase === 'outbound_start';
        const isBounce = wp.phase.includes('bounce');
        const isHold = wp.phase.includes('hold');
        
        let color = '#ffffff';
        let size = 4;
        
        if (isStart) {
          color = '#ff0000';
          size = 12;
        } else if (isBounce) {
          color = '#ffaa00';
          size = 7;
        } else if (isHold) {
          color = '#0088ff';
          size = 7;
        }
        
        return (
          <mesh key={i} position={[wp.x, wp.y, 1]}>
            <circleGeometry args={[size, 32]} />
            <meshBasicMaterial color={color} />
            {showLabels && (
              <Html distanceFactor={100} center>
                <div style={{
                  background: 'rgba(0,0,0,0.85)',
                  color: 'white',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  whiteSpace: 'nowrap',
                  transform: 'translateY(-25px)'
                }}>
                  {wp.index}: {wp.phase}
                </div>
              </Html>
            )}
          </mesh>
        );
      })}
    </group>
  );
}

function Scene({ params, batteryIndex, showLabels }: { params: FlightParams; batteryIndex: number; showLabels: boolean }) {
  const [waypoints, setWaypoints] = useState<Waypoint[]>([]);
  
  useEffect(() => {
    const generator = new SpiralGenerator();
    const path = generator.generateFlightPath(params, batteryIndex);
    setWaypoints(path);
  }, [params, batteryIndex]);
  
  return (
    <>
      <ambientLight intensity={1} />
      <FlightPathVisualization waypoints={waypoints} showLabels={showLabels} />
      <OrbitControls 
        makeDefault 
        enableRotate={false}
        mouseButtons={{
          LEFT: THREE.MOUSE.PAN,
          MIDDLE: THREE.MOUSE.DOLLY,
          RIGHT: THREE.MOUSE.PAN
        }}
      />
    </>
  );
}

export default function ShapeViewerPage() {
  const [params, setParams] = useState<FlightParams>({
    slices: 1,
    N: 6,
    r0: 100,
    rHold: 1000,
    battery_duration_minutes: 10
  });
  
  const [batteryIndex, setBatteryIndex] = useState(0);
  const [showLabels, setShowLabels] = useState(false);
  
  const updateParam = (key: keyof FlightParams, value: number) => {
    setParams(prev => ({ ...prev, [key]: value }));
    if (key === 'slices' && batteryIndex >= value) {
      setBatteryIndex(Math.max(0, value - 1));
    }
  };
  
  return (
    <div style={{ width: '100vw', height: '100vh', background: '#0a0a0a', display: 'flex' }}>
      {/* Control Panel */}
      <div style={{
        width: '350px',
        background: '#1a1a1a',
        padding: '20px',
        overflowY: 'auto',
        borderRight: '1px solid #333',
        color: '#fff',
        fontFamily: 'monospace'
      }}>
        <h1 style={{ fontSize: '20px', marginBottom: '20px', color: '#00ff88' }}>
          Flight Shape Viewer
        </h1>
        
        <div style={{ marginBottom: '20px', padding: '10px', background: '#252525', borderRadius: '8px' }}>
          <div style={{ fontSize: '12px', opacity: 0.7, marginBottom: '5px' }}>DIAGNOSTICS</div>
          <div style={{ fontSize: '11px' }}>
            <div>dphi: {(2 * Math.PI / params.slices).toFixed(4)} rad</div>
            <div>dphi: {(360 / params.slices).toFixed(2)}°</div>
            <div>Waypoints: {(2 * params.N + 5)} per battery</div>
          </div>
        </div>
        
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', opacity: 0.8 }}>
            Number of Batteries (slices)
          </label>
          <input
            type="range"
            min="1"
            max="8"
            value={params.slices}
            onChange={(e) => updateParam('slices', parseInt(e.target.value))}
            style={{ width: '100%' }}
          />
          <div style={{ fontSize: '14px', marginTop: '5px' }}>{params.slices}</div>
        </div>
        
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', opacity: 0.8 }}>
            Number of Bounces (N)
          </label>
          <input
            type="range"
            min="3"
            max="12"
            value={params.N}
            onChange={(e) => updateParam('N', parseInt(e.target.value))}
            style={{ width: '100%' }}
          />
          <div style={{ fontSize: '14px', marginTop: '5px' }}>{params.N}</div>
        </div>
        
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', opacity: 0.8 }}>
            Starting Radius (r0) ft
          </label>
          <input
            type="range"
            min="50"
            max="300"
            step="10"
            value={params.r0}
            onChange={(e) => updateParam('r0', parseInt(e.target.value))}
            style={{ width: '100%' }}
          />
          <div style={{ fontSize: '14px', marginTop: '5px' }}>{params.r0} ft</div>
        </div>
        
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', opacity: 0.8 }}>
            Hold Radius (rHold) ft
          </label>
          <input
            type="range"
            min="200"
            max="5000"
            step="100"
            value={params.rHold}
            onChange={(e) => updateParam('rHold', parseInt(e.target.value))}
            style={{ width: '100%' }}
          />
          <div style={{ fontSize: '14px', marginTop: '5px' }}>{params.rHold} ft</div>
        </div>
        
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', opacity: 0.8 }}>
            Battery Duration (minutes)
          </label>
          <input
            type="range"
            min="5"
            max="30"
            value={params.battery_duration_minutes}
            onChange={(e) => updateParam('battery_duration_minutes', parseInt(e.target.value))}
            style={{ width: '100%' }}
          />
          <div style={{ fontSize: '14px', marginTop: '5px' }}>{params.battery_duration_minutes} min</div>
        </div>
        
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', opacity: 0.8 }}>
            View Battery/Slice
          </label>
          <input
            type="range"
            min="0"
            max={params.slices - 1}
            value={batteryIndex}
            onChange={(e) => setBatteryIndex(parseInt(e.target.value))}
            style={{ width: '100%' }}
          />
          <div style={{ fontSize: '14px', marginTop: '5px' }}>Battery {batteryIndex + 1} of {params.slices}</div>
        </div>
        
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={showLabels}
              onChange={(e) => setShowLabels(e.target.checked)}
              style={{ marginRight: '8px' }}
            />
            <span style={{ fontSize: '12px' }}>Show Waypoint Labels</span>
          </label>
        </div>
        
        <div style={{ 
          marginTop: '20px', 
          padding: '15px', 
          background: '#252525', 
          borderRadius: '8px',
          fontSize: '11px',
          lineHeight: '1.6'
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '10px', color: '#00ff88' }}>Legend:</div>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '5px' }}>
            <div style={{ width: '12px', height: '12px', background: '#ff0000', borderRadius: '50%', marginRight: '8px' }} />
            Start Point
          </div>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '5px' }}>
            <div style={{ width: '12px', height: '12px', background: '#ffaa00', borderRadius: '50%', marginRight: '8px' }} />
            Bounce Points
          </div>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '5px' }}>
            <div style={{ width: '12px', height: '12px', background: '#0088ff', borderRadius: '50%', marginRight: '8px' }} />
            Hold Pattern
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ width: '12px', height: '12px', background: '#ffffff', borderRadius: '50%', marginRight: '8px' }} />
            Midpoints
          </div>
        </div>
        
        <div style={{ 
          marginTop: '15px', 
          padding: '15px', 
          background: '#331a1a', 
          borderRadius: '8px',
          fontSize: '11px',
          lineHeight: '1.6',
          border: '1px solid #ff4444'
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '5px', color: '#ff6666' }}>Bug Description:</div>
          <div>At slices=1, dphi=2π causes phase oscillation to span full circle, collapsing all waypoints onto same radial line.</div>
        </div>
      </div>
      
      {/* 2D Shape Viewer */}
      <div style={{ flex: 1, position: 'relative' }}>
        <Canvas 
          camera={{ position: [0, 0, 3000], fov: 50 }}
          orthographic
        >
          <Scene params={params} batteryIndex={batteryIndex} showLabels={showLabels} />
        </Canvas>
        
        <div style={{
          position: 'absolute',
          top: '20px',
          left: '20px',
          background: 'rgba(0,0,0,0.7)',
          color: 'white',
          padding: '10px 15px',
          borderRadius: '8px',
          fontSize: '12px',
          fontFamily: 'monospace'
        }}>
          <div>2D Top-Down View: Drag to pan, Scroll to zoom</div>
          <div style={{ marginTop: '5px', opacity: 0.7 }}>Grid = 500ft spacing, Red dot = start point</div>
        </div>
      </div>
    </div>
  );
}
