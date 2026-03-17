'use client';

import { useEffect, useRef, useState } from 'react';
import styles from './page.module.css';

const TAN_30 = Math.tan(Math.PI / 6);
const FULL_ROT_SEC = 20;
const TRANSIT_SEC = 1;
const C = 72;
const R = 50;
const SZ = 144;

type StatProps = {
  label: string;
  value: string;
  sub: string;
  color: string;
};

type SliderRowProps = {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (value: number) => void;
  display: string;
  pct: number;
};

function toDeg(cx: number, cy: number, x: number, y: number): number {
  const angle = (Math.atan2(y - cy, x - cx) * 180) / Math.PI + 90;
  return ((angle % 360) + 360) % 360;
}

function toXY(cx: number, cy: number, r: number, deg: number): [number, number] {
  const rad = ((deg - 90) * Math.PI) / 180;
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
}

function arcPath(cx: number, cy: number, r: number, a1: number, a2: number): string | null {
  const [x1, y1] = toXY(cx, cy, r, a1);
  const [x2, y2] = toXY(cx, cy, r, a2);
  const span = ((a2 - a1) + 360) % 360;

  if (span < 0.5) {
    return null;
  }

  const largeArcFlag = span > 180 ? 1 : 0;
  return `M${x1.toFixed(2)},${y1.toFixed(2)} A${r},${r},0,${largeArcFlag},1,${x2.toFixed(2)},${y2.toFixed(2)}`;
}

function Stat({ label, value, sub, color }: StatProps) {
  return (
    <div>
      <p className={styles.statLabel}>{label}</p>
      <p className={styles.statValue} style={{ color }}>{value}</p>
      <p className={styles.statSub}>{sub}</p>
    </div>
  );
}

function SliderRow({ label, min, max, step, value, onChange, display, pct }: SliderRowProps) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span className={styles.sliderLabel}>{label}</span>
        <span className={styles.sliderValue}>{display}</span>
      </div>
      <input
        className={styles.rangeInput}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        style={{
          WebkitAppearance: 'none',
          appearance: 'none',
          background: `linear-gradient(to right, #3a8eff ${pct}%, #1e1e1e ${pct}%)`,
          borderRadius: 2,
          cursor: 'pointer',
          display: 'block',
          height: 2,
          outline: 'none',
          width: '100%',
        }}
      />
    </div>
  );
}

export default function CameraOverlapPage() {
  const [height, setHeight] = useState(100);
  const [overlap, setOverlap] = useState(75);
  const [handles, setHandles] = useState([10, 100, 190, 280]);
  const dragIdx = useRef<number | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);

  const overlapPct = overlap / 100;
  const footprint = 2 * height * TAN_30;
  const distance = footprint * (1 - overlapPct);

  const sortedWithIndices = handles
    .map((angle, index) => ({ angle, index }))
    .sort((a, b) => a.angle - b.angle);
  const sorted = sortedWithIndices.map((x) => x.angle);

  const isCaptureArc = (k: number): boolean => {
    const i = sortedWithIndices[k].index;
    const j = sortedWithIndices[(k + 1) % 4].index;
    const [lo, hi] = i < j ? [i, j] : [j, i];
    return (lo === 0 && hi === 1) || (lo === 2 && hi === 3);
  };

  const arcSpan = (k: number): number => {
    const a1 = sorted[k];
    const a2 = sorted[(k + 1) % 4];
    return (a2 - a1 + 360) % 360;
  };

  const capDeg = [0, 1, 2, 3]
    .filter((k) => isCaptureArc(k))
    .reduce((sum, k) => sum + arcSpan(k), 0);
  const capPct = capDeg / 360;
  const rotTime = capPct * FULL_ROT_SEC + 2 * TRANSIT_SEC;
  const speedMph = (distance / rotTime) * 0.681818;
  const speedFts = distance / rotTime;

  useEffect(() => {
    const onMove = (event: PointerEvent) => {
      if (dragIdx.current === null || !svgRef.current) {
        return;
      }

      event.preventDefault();
      const rect = svgRef.current.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const angle = toDeg(cx, cy, event.clientX, event.clientY);

      setHandles((current) => {
        const next = [...current];
        next[dragIdx.current as number] = angle;
        return next;
      });
    };

    const onUp = () => {
      dragIdx.current = null;
    };

    window.addEventListener('pointermove', onMove, { passive: false });
    window.addEventListener('pointerup', onUp);

    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, []);

  const svgW = 300;
  const svgH = 160;
  const gY = svgH - 18;
  const tVal = (height - 50) / 350;
  const coneH = 44 + tVal * 82;
  const tipY = gY - coneH;
  const hBase = coneH * TAN_30;
  const sdist = (1 - overlapPct) * 2 * hBase;
  const c1x = svgW / 2 - sdist / 2;
  const c2x = svgW / 2 + sdist / 2;
  const c1l = c1x - hBase;
  const c1r = c1x + hBase;
  const c2l = c2x - hBase;
  const c2r = c2x + hBase;
  const overlapLeft = Math.max(c1l, c2l);
  const overlapRight = Math.min(c1r, c2r);

  return (
    <main
      className={styles.pageRoot}
      style={{
        background: '#0a0a0a',
        color: '#f5f5f7',
        minHeight: '100vh',
        paddingTop: 100,
        paddingBottom: 32,
      }}
    >
      <div className={styles.contentWrapper}>
        <div style={{ padding: '0 4px' }}>
          <p className={styles.pageLabel}>
            60° FOV · {overlap}% Overlap
          </p>
          <h1 className={styles.pageTitle}>
            Drone Path Spacing
          </h1>
        </div>

        <div style={{ padding: '10px 0 0' }}>
          <div className={styles.calculatorCard}>
            <svg
              ref={svgRef}
              width={SZ}
              height={SZ}
              viewBox={`0 0 ${SZ} ${SZ}`}
              style={{ flexShrink: 0, overflow: 'visible', touchAction: 'none' }}
            >
              <circle cx={C} cy={C} r={R} fill="none" stroke="#1e1e1e" strokeWidth={10} />

              {[0, 1, 2, 3].map((k) => {
                const a1 = sorted[k];
                const a2 = sorted[(k + 1) % 4];
                const path = arcPath(C, C, R, a1, a2);

                return path ? (
                  <path
                    key={k}
                    d={path}
                    fill="none"
                    stroke={isCaptureArc(k) ? '#34c759' : '#252525'}
                    strokeLinecap="butt"
                    strokeWidth={10}
                  />
                ) : null;
              })}

              {handles.map((handle, index) => {
                const [x, y] = toXY(C, C, R, handle);

                return (
                  <g key={index} style={{ cursor: 'grab' }}>
                    <circle
                      cx={x}
                      cy={y}
                      r={18}
                      fill="transparent"
                      onPointerDown={(event) => {
                        event.preventDefault();
                        dragIdx.current = index;
                      }}
                      style={{ touchAction: 'none' }}
                    />
                    <circle cx={x} cy={y} r={5} fill="#f5f5f7" style={{ pointerEvents: 'none' }} />
                    <circle cx={x} cy={y} r={3} fill="#0a0a0a" style={{ pointerEvents: 'none' }} />
                  </g>
                );
              })}

              <text x={C} y={C - 6} textAnchor="middle" fill="#f5f5f7" fontSize={15} fontWeight={700}>
                {(capPct * 100).toFixed(0)}%
              </text>
              <text x={C} y={C + 9} textAnchor="middle" fill="#444" fontSize={8} letterSpacing="0.05em">
                CAPTURE
              </text>
            </svg>

            <div style={{ display: 'flex', flex: 1, flexDirection: 'column', gap: 8, minWidth: 220 }}>
              <Stat
                label="Capture"
                value={`${capDeg.toFixed(0)}°`}
                sub={`${(capPct * 100).toFixed(0)}% of rotation`}
                color="#34c759"
              />
              <Stat
                label="Rot. Time"
                value={`${rotTime.toFixed(1)}s`}
                sub={`${capPct.toFixed(2)} × 20s + 2s`}
                color="#f5f5f7"
              />
              <Stat
                label="Speed"
                value={speedMph.toFixed(2)}
                sub={`mph · ${speedFts.toFixed(2)} ft/s`}
                color="#3a8eff"
              />
            </div>
          </div>
        </div>

        <div
          style={{
            alignItems: 'center',
            display: 'flex',
            justifyContent: 'center',
            minHeight: 0,
            padding: '8px 0',
          }}
        >
          <div className={styles.coneCard}>
            <svg viewBox={`0 0 ${svgW} ${svgH}`} style={{ display: 'block', height: 'auto', width: '100%' }}>
              <defs>
                <marker id="a1" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto-start-reverse">
                  <path d="M0,0 L0,5 L5,2.5 Z" fill="#3a8eff" />
                </marker>
                <marker id="a2" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto">
                  <path d="M0,0 L0,5 L5,2.5 Z" fill="#3a8eff" />
                </marker>
              </defs>

              <line x1={14} y1={gY} x2={svgW - 14} y2={gY} stroke="#222" strokeWidth={1} />

              {overlapRight > overlapLeft ? (
                <polygon
                  points={`${c1x},${tipY} ${overlapLeft},${gY} ${overlapRight},${gY} ${c2x},${tipY}`}
                  fill="#3a8eff"
                  opacity={0.1}
                />
              ) : null}

              <polygon
                points={`${c1x},${tipY} ${c1l},${gY} ${c1r},${gY}`}
                fill="none"
                stroke="#f5f5f7"
                strokeOpacity={0.38}
                strokeWidth={1.2}
              />
              <polygon
                points={`${c2x},${tipY} ${c2l},${gY} ${c2r},${gY}`}
                fill="none"
                stroke="#f5f5f7"
                strokeOpacity={0.38}
                strokeWidth={1.2}
              />

              {overlapRight > overlapLeft ? (
                <rect
                  x={overlapLeft}
                  y={gY - 3}
                  width={overlapRight - overlapLeft}
                  height={3}
                  fill="#3a8eff"
                  opacity={0.65}
                  rx={1.5}
                />
              ) : null}

              <circle cx={c1x} cy={tipY} r={4} fill="#f5f5f7" />
              <circle cx={c2x} cy={tipY} r={4} fill="#f5f5f7" />
              <line
                x1={c1x}
                y1={tipY}
                x2={c2x}
                y2={tipY}
                stroke="#3a8eff"
                strokeDasharray="3 3"
                strokeOpacity={0.35}
                strokeWidth={1}
              />

              {sdist > 14 ? (
                <>
                  <line
                    x1={c1x + 6}
                    y1={tipY - 10}
                    x2={c2x - 6}
                    y2={tipY - 10}
                    markerStart="url(#a1)"
                    markerEnd="url(#a2)"
                    stroke="#3a8eff"
                    strokeWidth={1}
                  />
                  <text
                    x={(c1x + c2x) / 2}
                    y={tipY - 14}
                    textAnchor="middle"
                    fill="#3a8eff"
                    fontSize={9}
                    fontWeight={600}
                  >
                    {distance.toFixed(1)} ft
                  </text>
                </>
              ) : (
                <text x={svgW / 2} y={tipY - 12} textAnchor="middle" fill="#3a8eff" fontSize={9} fontWeight={600}>
                  {distance.toFixed(1)} ft
                </text>
              )}

              <line x1={20} y1={tipY} x2={20} y2={gY} stroke="#2a2a2a" strokeWidth={1} />
              <line x1={16} y1={tipY} x2={24} y2={tipY} stroke="#2a2a2a" strokeWidth={1} />
              <line x1={16} y1={gY} x2={24} y2={gY} stroke="#2a2a2a" strokeWidth={1} />
              <text
                x={10}
                y={(tipY + gY) / 2 + 3}
                textAnchor="middle"
                fill="#333"
                fontSize={8}
                transform={`rotate(-90,10,${(tipY + gY) / 2})`}
              >
                {height} ft
              </text>

              {overlapRight - overlapLeft > 24 ? (
                <text
                  x={(overlapLeft + overlapRight) / 2}
                  y={gY + 13}
                  textAnchor="middle"
                  fill="#3a8eff"
                  fontSize={8}
                  opacity={0.45}
                >
                  {overlap}% overlap
                </text>
              ) : null}
            </svg>
          </div>
        </div>

        <div className={styles.slidersSection}>
          <SliderRow
            label="Height"
            min={50}
            max={400}
            step={1}
            value={height}
            onChange={setHeight}
            display={`${height} ft`}
            pct={((height - 50) / 350) * 100}
          />
          <SliderRow
            label="Overlap"
            min={10}
            max={95}
            step={1}
            value={overlap}
            onChange={setOverlap}
            display={`${overlap}%`}
            pct={((overlap - 10) / 85) * 100}
          />
          <p className={styles.footnote}>
            footprint {footprint.toFixed(0)} ft · spacing {distance.toFixed(1)} ft · {rotTime.toFixed(1)}s/pt
          </p>
        </div>
      </div>
    </main>
  );
}
