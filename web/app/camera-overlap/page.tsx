'use client';

import dynamic from 'next/dynamic';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  averageAdjacentFootprintIou,
  FULL_ROT_SEC,
  getGimbalAngleDeg,
  hypotenuseFromHeight,
  linearViewerPathMaxFt,
  linearViewerPathMinFt,
  rotationTimeSec,
  waypointCountFromLinearPathSpan,
} from '../../lib/cameraOverlapMath';
import { buildSpinPathOverlapConfig } from '../../lib/realPathSpin';
import styles from './page.module.css';
import GimbalDistributionCard from './GimbalDistributionCard';
import RealPathPlanner from './RealPathPlanner';

const ThreeView = dynamic(() => import('./ThreeView'), { ssr: false });

/** Slider range: ft/s (22.4 mph max). */
const MIN_SPEED_FTS = 0.5;
const MAX_SPEED_MPH = 22.4;
const MAX_SPEED_FTS = (MAX_SPEED_MPH * 5280) / 3600;
const MPH_TO_FTS = 5280 / 3600;
const DEFAULT_SPEED_AGL_MIN_FT = 200;
const DEFAULT_SPEED_AGL_MAX_FT = 400;
const DEFAULT_SPEED_MPH_MIN = 17;
const DEFAULT_SPEED_MPH_MAX = 22;

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

type SliderRowPropsWithTestId = SliderRowProps & { testId?: string };

function SliderRow({ label, min, max, step, value, onChange, display, pct, testId }: SliderRowPropsWithTestId) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span className={styles.sliderLabel}>{label}</span>
        <span className={styles.sliderValue}>{display}</span>
      </div>
      <input
        className={styles.rangeInput}
        data-testid={testId}
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
  const [workflowMode, setWorkflowMode] = useState<'straight' | 'realPath'>('straight');
  const [height, setHeight] = useState(200);
  const [handles, setHandles] = useState([10, 100, 190, 280]);

  const [speedEnvLoAgl, setSpeedEnvLoAgl] = useState(DEFAULT_SPEED_AGL_MIN_FT);
  const [speedEnvLoMph, setSpeedEnvLoMph] = useState(DEFAULT_SPEED_MPH_MIN);
  const [speedEnvHiAgl, setSpeedEnvHiAgl] = useState(DEFAULT_SPEED_AGL_MAX_FT);
  const [speedEnvHiMph, setSpeedEnvHiMph] = useState(DEFAULT_SPEED_MPH_MAX);

  const [minAngle, setMinAngle] = useState(15);
  const [minAngleHeight, setMinAngleHeight] = useState(200);
  const [maxAngle, setMaxAngle] = useState(35);
  const [maxAngleHeight, setMaxAngleHeight] = useState(400);
  const [customCaptureRing, setCustomCaptureRing] = useState(false);
  const [viewerPathLengthFt, setViewerPathLengthFt] = useState(150);
  const [pitchSequenceNeg, setPitchSequenceNeg] = useState<number[]>([]);
  const [spinMode, setSpinMode] = useState(false);
  const [captureIntervalFt, setCaptureIntervalFt] = useState(6);
  const [captureIntervalSec, setCaptureIntervalSec] = useState(1.5);
  const [captureIntervalUnit, setCaptureIntervalUnit] = useState<'ft' | 's'>('s');

  const dragIdx = useRef<number | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);

  const speedMphFromAgl = useMemo(() => {
    const h = Math.min(400, Math.max(50, height));
    const a0 = speedEnvLoAgl;
    const m0 = speedEnvLoMph;
    const a1 = speedEnvHiAgl;
    const m1 = speedEnvHiMph;
    const lo = Math.min(a0, a1);
    const hi = Math.max(a0, a1);
    const mphLo = a0 <= a1 ? m0 : m1;
    const mphHi = a0 <= a1 ? m1 : m0;
    if (hi - lo < 1e-6) {
      return mphLo;
    }
    const hh = Math.min(hi, Math.max(lo, h));
    const t = (hh - lo) / (hi - lo);
    return mphLo + t * (mphHi - mphLo);
  }, [height, speedEnvLoAgl, speedEnvLoMph, speedEnvHiAgl, speedEnvHiMph]);

  const speedFtsManual = useMemo(
    () => Math.min(MAX_SPEED_FTS, Math.max(MIN_SPEED_FTS, speedMphFromAgl * MPH_TO_FTS)),
    [speedMphFromAgl],
  );

  const angleDeg = getGimbalAngleDeg(height, minAngle, minAngleHeight, maxAngle, maxAngleHeight);
  const hypotenuse = hypotenuseFromHeight(height, angleDeg);

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
  const effectiveCapPct = customCaptureRing ? capPct : 1;
  const effectiveCapDeg = customCaptureRing ? capDeg : 360;
  const rotTime = rotationTimeSec(effectiveCapPct);
  const spacingFromSpeed = speedFtsManual * rotTime;

  const activeCaptureIntervalFt = captureIntervalUnit === 's'
    ? captureIntervalSec * speedFtsManual
    : captureIntervalFt;

  const pathSpanSpacingFt = spinMode ? activeCaptureIntervalFt : spacingFromSpeed;
  const pathSpanMinFt = linearViewerPathMinFt(pathSpanSpacingFt);
  const pathSpanMaxFt = linearViewerPathMaxFt(pathSpanSpacingFt);

  useEffect(() => {
    setViewerPathLengthFt((prev) =>
      Math.min(pathSpanMaxFt, Math.max(pathSpanMinFt, prev)),
    );
  }, [pathSpanMinFt, pathSpanMaxFt]);

  const viewerWaypointCount = useMemo(
    () => waypointCountFromLinearPathSpan(viewerPathLengthFt, spacingFromSpeed),
    [viewerPathLengthFt, spacingFromSpeed],
  );

  const tSpin = effectiveCapPct * FULL_ROT_SEC;
  const yawRateDegPerSec = tSpin > 0 ? effectiveCapDeg / tSpin : 0;
  const headingRpm = yawRateDegPerSec / 6;

  const pitchDegsViewer = useMemo(() => {
    const base = getGimbalAngleDeg(height, minAngle, minAngleHeight, maxAngle, maxAngleHeight);
    return Array.from({ length: viewerWaypointCount }, (_, i) => {
      const s = pitchSequenceNeg[i];
      return typeof s === 'number' ? Math.abs(s) : base;
    });
  }, [height, minAngle, minAngleHeight, maxAngle, maxAngleHeight, viewerWaypointCount, pitchSequenceNeg]);

  const alongPositions = useMemo(
    () =>
      Array.from({ length: viewerWaypointCount }, (_, i) => (i - (viewerWaypointCount - 1) / 2) * spacingFromSpeed),
    [viewerWaypointCount, spacingFromSpeed],
  );

  // Spin-mode: path span drives along-track count; yaw steps by Δθ = ω·Δt (capture % sets ω).
  const captureCadenceSec = activeCaptureIntervalFt / Math.max(0.01, speedFtsManual);
  const deltaHeadingPerCaptureDeg = yawRateDegPerSec * captureCadenceSec;

  const nCapturesFromYawStep = useMemo(() => {
    const d = Math.max(1e-9, deltaHeadingPerCaptureDeg);
    return Math.min(30, Math.max(2, Math.floor(effectiveCapDeg / d) + 1));
  }, [deltaHeadingPerCaptureDeg, effectiveCapDeg]);

  const effectiveSpinCaptures = useMemo(
    () => waypointCountFromLinearPathSpan(viewerPathLengthFt, activeCaptureIntervalFt),
    [viewerPathLengthFt, activeCaptureIntervalFt],
  );

  const spinHeadings = useMemo(() => {
    const d = Math.max(1e-9, deltaHeadingPerCaptureDeg);
    return Array.from({ length: effectiveSpinCaptures }, (_, i) => i * d);
  }, [effectiveSpinCaptures, deltaHeadingPerCaptureDeg]);

  const spinAlongPositions = useMemo(
    () => Array.from({ length: effectiveSpinCaptures }, (_, i) =>
      (i - (effectiveSpinCaptures - 1) / 2) * activeCaptureIntervalFt,
    ),
    [effectiveSpinCaptures, activeCaptureIntervalFt],
  );

  const spinPitchDegs = useMemo(() => {
    const base = getGimbalAngleDeg(height, minAngle, minAngleHeight, maxAngle, maxAngleHeight);
    return Array.from({ length: effectiveSpinCaptures }, (_, i) => {
      const s = pitchSequenceNeg[i % Math.max(1, pitchSequenceNeg.length)];
      return typeof s === 'number' ? Math.abs(s) : base;
    });
  }, [height, minAngle, minAngleHeight, maxAngle, maxAngleHeight, effectiveSpinCaptures, pitchSequenceNeg]);

  const spinOverlapIou = useMemo(
    () => averageAdjacentFootprintIou(spinAlongPositions, height, spinPitchDegs, spinHeadings),
    [spinAlongPositions, height, spinPitchDegs, spinHeadings],
  );
  // ──────────────────────────────────────────────────────────────────────────

  const overlapIou = useMemo(
    () => averageAdjacentFootprintIou(alongPositions, height, pitchDegsViewer),
    [alongPositions, height, pitchDegsViewer],
  );

  const realPathOverlapConfig = useMemo(
    () => buildSpinPathOverlapConfig({
      speedFts: speedFtsManual,
      speedMph: speedMphFromAgl,
      captureSpacingFt: activeCaptureIntervalFt,
      captureIntervalSeconds: captureCadenceSec,
      yawRateDegPerSec,
      captureArcDeg: effectiveCapDeg,
      maxHeadingDeltaDeg: 179,
      defaultPitchDeg: -Math.abs(angleDeg),
      pitchSequenceNeg,
    }),
    [
      speedFtsManual,
      speedMphFromAgl,
      activeCaptureIntervalFt,
      captureCadenceSec,
      yawRateDegPerSec,
      effectiveCapDeg,
      angleDeg,
      pitchSequenceNeg,
    ],
  );

  const isRealPathMode = workflowMode === 'realPath';
  const showSpinCaptureControls = spinMode || isRealPathMode;
  const pageLabel = isRealPathMode
    ? `Mapbox real path · ${activeCaptureIntervalFt.toFixed(1)} ft capture spacing · ${yawRateDegPerSec.toFixed(1)}°/s yaw`
    : `75°×55° FOV · ${((spinMode ? spinOverlapIou : overlapIou) * 100).toFixed(0)}% overlap`;

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

  const handleMinAngleHeight = (val: number) => {
    setMinAngleHeight(Math.min(val, maxAngleHeight - 1));
  };

  const handleMaxAngleHeight = (val: number) => {
    setMaxAngleHeight(Math.max(val, minAngleHeight + 1));
  };

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
          <p className={styles.pageLabel} data-testid="camera-overlap-page-label">
            {pageLabel}
          </p>
          <h1 className={styles.pageTitle}>
            {isRealPathMode ? 'Camera Overlap Real Path' : 'Drone Path Spacing'}
          </h1>
        </div>

        <div className={styles.viewModeToggle} style={{ padding: '8px 4px 0' }}>
          <button
            type="button"
            data-testid="workflow-straight-btn"
            className={`${styles.viewModeBtn} ${!isRealPathMode ? styles.viewModeBtnActive : ''}`}
            onClick={() => setWorkflowMode('straight')}
          >
            Straight Lab
          </button>
          <button
            type="button"
            data-testid="workflow-real-path-btn"
            className={`${styles.viewModeBtn} ${isRealPathMode ? styles.viewModeBtnActive : ''}`}
            onClick={() => setWorkflowMode('realPath')}
          >
            Real Path
          </button>
        </div>

        <div className={styles.topCard}>
          <div style={{ padding: '8px 0' }}>
            {isRealPathMode ? (
              <RealPathPlanner overlapConfig={realPathOverlapConfig} />
            ) : (
              <>
                <div className={styles.viewModeToggle}>
                  <button
                    type="button"
                    className={`${styles.viewModeBtn} ${!spinMode ? styles.viewModeBtnActive : ''}`}
                    onClick={() => {
                      setSpinMode(false);
                    }}
                  >
                    Linear
                  </button>
                  <button
                    type="button"
                    className={`${styles.viewModeBtn} ${spinMode ? styles.viewModeBtnActive : ''}`}
                    onClick={() => setSpinMode(true)}
                  >
                    Flat spin
                  </button>
                </div>

                <div className={styles.viewerWaypointBar}>
                  <span className={styles.viewerWaypointBarLabel}>3D path span</span>
                  <div className={styles.viewerWaypointBarTrack}>
                    <input
                      className={styles.rangeInput}
                      data-testid="viewer-3d-path-span"
                      type="range"
                      min={pathSpanMinFt}
                      max={pathSpanMaxFt}
                      step={1}
                      value={viewerPathLengthFt}
                      onChange={(e) => setViewerPathLengthFt(Number(e.target.value))}
                      aria-label="End-to-end path length sampled in 3D viewer (feet)"
                      style={{
                        WebkitAppearance: 'none',
                        appearance: 'none',
                        background: `linear-gradient(to right, #3a8eff ${
                          pathSpanMaxFt > pathSpanMinFt
                            ? ((viewerPathLengthFt - pathSpanMinFt) / (pathSpanMaxFt - pathSpanMinFt)) * 100
                            : 0
                        }%, #1e1e1e ${
                          pathSpanMaxFt > pathSpanMinFt
                            ? ((viewerPathLengthFt - pathSpanMinFt) / (pathSpanMaxFt - pathSpanMinFt)) * 100
                            : 0
                        }%)`,
                        borderRadius: 2,
                        cursor: 'pointer',
                        display: 'block',
                        height: 2,
                        outline: 'none',
                        width: '100%',
                      }}
                    />
                  </div>
                  <span className={styles.sliderValue} style={{ flexShrink: 0, minWidth: '9rem', textAlign: 'right' }}>
                    {Math.round(viewerPathLengthFt)} ft
                    <span style={{ color: 'rgba(255,255,255,0.35)' }}>
                      {' '}
                      · {spinMode ? effectiveSpinCaptures : viewerWaypointCount} pts
                    </span>
                  </span>
                </div>

                <ThreeView
                  height={height}
                  pitchDegs={spinMode ? spinPitchDegs : pitchDegsViewer}
                  spacing={spacingFromSpeed}
                  overlapPercent={(spinMode ? spinOverlapIou : overlapIou) * 100}
                  spinMode={spinMode}
                  captureIntervalFt={activeCaptureIntervalFt}
                  captureArcDeg={effectiveCapDeg}
                  spinHeadingDegs={spinMode ? spinHeadings : undefined}
                />
              </>
            )}
          </div>

          <div className={styles.slidersSection}>
            <SliderRow
              label={isRealPathMode ? 'Overlap AGL' : 'Height'}
              min={50}
              max={400}
              step={1}
              value={Math.min(height, 400)}
              onChange={setHeight}
              display={`${Math.min(height, 400)} ft`}
              pct={((Math.min(height, 400) - 50) / 350) * 100}
              testId="height-slider"
            />

            <div className={styles.speedEnvelopeRow}>
              <div className={styles.speedEnvelopeCard}>
                <p className={styles.speedEnvelopeTitle}>Low AGL</p>
                <label className={styles.speedEnvelopeField}>
                  <span>AGL (ft)</span>
                  <input
                    type="number"
                    min={50}
                    max={900}
                    step={1}
                    value={speedEnvLoAgl}
                    onChange={(e) => setSpeedEnvLoAgl(Number(e.target.value))}
                  />
                </label>
                <label className={styles.speedEnvelopeField}>
                  <span>Speed (mph)</span>
                  <input
                    type="number"
                    min={1}
                    max={30}
                    step={0.5}
                    value={speedEnvLoMph}
                    onChange={(e) => setSpeedEnvLoMph(Number(e.target.value))}
                  />
                </label>
              </div>
              <div className={styles.speedEnvelopeCard}>
                <p className={styles.speedEnvelopeTitle}>High AGL</p>
                <label className={styles.speedEnvelopeField}>
                  <span>AGL (ft)</span>
                  <input
                    type="number"
                    min={50}
                    max={900}
                    step={1}
                    value={speedEnvHiAgl}
                    onChange={(e) => setSpeedEnvHiAgl(Number(e.target.value))}
                  />
                </label>
                <label className={styles.speedEnvelopeField}>
                  <span>Speed (mph)</span>
                  <input
                    type="number"
                    min={1}
                    max={30}
                    step={0.5}
                    value={speedEnvHiMph}
                    onChange={(e) => setSpeedEnvHiMph(Number(e.target.value))}
                  />
                </label>
              </div>
            </div>
            <p className={styles.speedAutoNote}>
              Cruise speed: <strong>{speedMphFromAgl.toFixed(2)} mph</strong> ({speedFtsManual.toFixed(2)} ft/s) from AGL vs. anchors
            </p>

            {showSpinCaptureControls && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span className={styles.sliderLabel} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    Capture interval
                    <span className={styles.unitToggle}>
                      <button
                        type="button"
                        className={`${styles.unitBtn} ${captureIntervalUnit === 'ft' ? styles.unitBtnActive : ''}`}
                        onClick={() => setCaptureIntervalUnit('ft')}
                      >ft</button>
                      <button
                        type="button"
                        className={`${styles.unitBtn} ${captureIntervalUnit === 's' ? styles.unitBtnActive : ''}`}
                        onClick={() => setCaptureIntervalUnit('s')}
                      >s</button>
                    </span>
                  </span>
                  <span className={styles.sliderValue}>
                    {captureIntervalUnit === 'ft'
                      ? `${captureIntervalFt} ft`
                      : `${captureIntervalSec} s · ${activeCaptureIntervalFt.toFixed(1)} ft`
                    }
                    {' '}· Δθ ≈ {deltaHeadingPerCaptureDeg.toFixed(2)}° · ~{nCapturesFromYawStep} in one arc
                  </span>
                </div>
                {captureIntervalUnit === 'ft' ? (
                  <input
                    className={styles.rangeInput}
                    data-testid="capture-interval-slider"
                    type="range"
                    min={1}
                    max={50}
                    step={1}
                    value={captureIntervalFt}
                    onChange={(e) => setCaptureIntervalFt(Number(e.target.value))}
                    style={{
                      WebkitAppearance: 'none',
                      appearance: 'none',
                      background: `linear-gradient(to right, #3a8eff ${((captureIntervalFt - 1) / 49) * 100}%, #1e1e1e ${((captureIntervalFt - 1) / 49) * 100}%)`,
                      borderRadius: 2,
                      cursor: 'pointer',
                      display: 'block',
                      height: 2,
                      outline: 'none',
                      width: '100%',
                    }}
                  />
                ) : (
                  <input
                    className={styles.rangeInput}
                    data-testid="capture-interval-slider"
                    type="range"
                    min={0.5}
                    max={10}
                    step={0.1}
                    value={captureIntervalSec}
                    onChange={(e) => setCaptureIntervalSec(Number(e.target.value))}
                    style={{
                      WebkitAppearance: 'none',
                      appearance: 'none',
                      background: `linear-gradient(to right, #3a8eff ${((captureIntervalSec - 0.5) / 9.5) * 100}%, #1e1e1e ${((captureIntervalSec - 0.5) / 9.5) * 100}%)`,
                      borderRadius: 2,
                      cursor: 'pointer',
                      display: 'block',
                      height: 2,
                      outline: 'none',
                      width: '100%',
                    }}
                  />
                )}
              </div>
            )}
            <p className={styles.footnote}>
              gimbal &minus;{angleDeg.toFixed(0)}° &middot; hyp {hypotenuse.toFixed(0)} ft &middot; spacing {spacingFromSpeed.toFixed(1)} ft &middot; {rotTime.toFixed(1)}s/pt
              {tSpin > 0 && (
                <>
                  {' '}· flat spin {effectiveCapDeg.toFixed(0)}° @ {yawRateDegPerSec.toFixed(1)}°/s ({headingRpm.toFixed(2)} RPM) · drone advances {spacingFromSpeed.toFixed(0)} ft between spins
                  {isRealPathMode ? ` · real-path capture spacing ${activeCaptureIntervalFt.toFixed(1)} ft` : ''}
                </>
              )}
            </p>
          </div>
        </div>

        <div style={{ padding: '10px 0 0' }}>
          <div className={styles.calculatorCard}>
            <div className={styles.captureRingColumn}>
              <label className={styles.captureToggleLabel}>
                <span className={styles.captureToggleText}>Custom ring</span>
                <button
                  type="button"
                  data-testid="capture-ring-switch"
                  role="switch"
                  aria-checked={customCaptureRing}
                  aria-label={
                    customCaptureRing
                      ? 'Custom capture ring on. Click for full 100 percent capture.'
                      : 'Full capture. Click to customize ring with handles.'
                  }
                  title="On: drag handles to set capture arc. Off: 100% full rotation capture."
                  className={styles.captureSwitch}
                  onClick={() => setCustomCaptureRing((v) => !v)}
                >
                  <span className={styles.captureSwitchThumb} />
                </button>
              </label>
              <svg
                ref={svgRef}
                width={SZ}
                height={SZ}
                viewBox={`0 0 ${SZ} ${SZ}`}
                style={{ flexShrink: 0, overflow: 'visible', touchAction: 'none' }}
              >
                <circle cx={C} cy={C} r={R} fill="none" stroke="#1e1e1e" strokeWidth={10} />

                {customCaptureRing ? (
                  <>
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
                  </>
                ) : (
                  <circle cx={C} cy={C} r={R} fill="none" stroke="#34c759" strokeWidth={10} />
                )}

                <text
                  data-testid="capture-pct-text"
                  x={C}
                  y={C - 6}
                  textAnchor="middle"
                  fill="#f5f5f7"
                  fontSize={15}
                  fontWeight={700}
                >
                  {(effectiveCapPct * 100).toFixed(0)}%
                </text>
                <text x={C} y={C + 9} textAnchor="middle" fill="#444" fontSize={8} letterSpacing="0.05em">
                  CAPTURE
                </text>
              </svg>
            </div>

            <div style={{ display: 'flex', flex: 1, flexDirection: 'column', gap: 8, minWidth: 220 }}>
              <Stat
                label="Capture"
                value={`${effectiveCapDeg.toFixed(0)}°`}
                sub={`${(effectiveCapPct * 100).toFixed(0)}% of rotation`}
                color="#34c759"
              />
              <Stat
                label="Rot. Time"
                value={`${rotTime.toFixed(1)}s`}
                sub={`${effectiveCapPct.toFixed(2)} × 20s + 2s`}
                color="#f5f5f7"
              />
              <Stat
                label="Speed"
                value={speedMphFromAgl.toFixed(2)}
                sub={`mph · ${speedFtsManual.toFixed(2)} ft/s (from AGL)`}
                color="#3a8eff"
              />
              <Stat
                label="Flat spin"
                value={tSpin > 0 ? `${yawRateDegPerSec.toFixed(1)}°/s` : '—'}
                sub={tSpin > 0 ? `${headingRpm.toFixed(2)} RPM · ${tSpin.toFixed(1)}s spin / ${rotTime.toFixed(1)}s total` : 'no capture arc'}
                color="#ffd60a"
              />
            </div>
          </div>
        </div>

        <GimbalDistributionCard
          heightAgl={height}
          minAngle={minAngle}
          maxAngle={maxAngle}
          minAngleHeight={minAngleHeight}
          maxAngleHeight={maxAngleHeight}
          onMinAngle={setMinAngle}
          onMaxAngle={setMaxAngle}
          onMinAngleHeight={handleMinAngleHeight}
          onMaxAngleHeight={handleMaxAngleHeight}
          pathSpanSpacingFt={showSpinCaptureControls ? activeCaptureIntervalFt : spacingFromSpeed}
          viewerPathLengthFt={viewerPathLengthFt}
          onViewerPathLengthFt={setViewerPathLengthFt}
          onPitchSequenceGenerated={setPitchSequenceNeg}
        />
      </div>
    </main>
  );
}
