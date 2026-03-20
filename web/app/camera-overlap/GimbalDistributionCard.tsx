'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  betaParams,
  betaPDFUnnorm,
  generatePitchSequence,
  intendedPitchNeg,
  makeSeededRandom,
  mixturePDFValues,
  paramsToSeed,
  pitchDomainFromEnvelope,
  toT,
  type PitchDomain,
} from '../../lib/gimbalPitchDistribution';
import styles from './page.module.css';

type EnvelopeSliderProps = {
  label: string;
  angleValue: number;
  angleMin: number;
  angleMax: number;
  onAngleChange: (v: number) => void;
  heightValue: number;
  heightMin: number;
  heightMax: number;
  onHeightChange: (v: number) => void;
};

function EnvelopeTile({
  label,
  angleValue,
  angleMin,
  angleMax,
  onAngleChange,
  heightValue,
  heightMin,
  heightMax,
  onHeightChange,
}: EnvelopeSliderProps) {
  const anglePct = ((angleValue - angleMin) / (angleMax - angleMin)) * 100;
  const heightPct = ((heightValue - heightMin) / (heightMax - heightMin)) * 100;

  return (
    <div className={styles.angleCard}>
      <p className={styles.angleCardLabel}>{label}</p>
      <p className={styles.angleCardValue}>
        &minus;{angleValue}&deg; @ {heightValue} ft
      </p>
      <div className={styles.angleCardSliders}>
        <input
          className={styles.rangeInput}
          type="range"
          min={angleMin}
          max={angleMax}
          step={1}
          value={angleValue}
          onChange={(e) => onAngleChange(Number(e.target.value))}
          style={{
            WebkitAppearance: 'none',
            appearance: 'none',
            background: `linear-gradient(to right, #ffd60a ${anglePct}%, #1e1e1e ${anglePct}%)`,
            borderRadius: 2,
            cursor: 'pointer',
            display: 'block',
            outline: 'none',
            width: '100%',
          }}
        />
        <input
          className={styles.rangeInput}
          type="range"
          min={heightMin}
          max={heightMax}
          step={1}
          value={heightValue}
          onChange={(e) => onHeightChange(Number(e.target.value))}
          style={{
            WebkitAppearance: 'none',
            appearance: 'none',
            background: `linear-gradient(to right, #3a8eff ${heightPct}%, #1e1e1e ${heightPct}%)`,
            borderRadius: 2,
            cursor: 'pointer',
            display: 'block',
            outline: 'none',
            width: '100%',
          }}
        />
      </div>
    </div>
  );
}

type DistSliderProps = {
  label: string;
  sublabel?: string;
  value: number;
  min: number;
  max: number;
  step: number;
  display: (v: number) => string;
  onChange: (v: number) => void;
};

function DistSlider({ label, sublabel, value, min, max, step, display, onChange }: DistSliderProps) {
  return (
    <div className={styles.distSliderRow}>
      <div className={styles.distSliderLabelCol}>
        <span className={styles.distSliderLabel}>{label}</span>
        {sublabel ? <span className={styles.distSliderSub}>{sublabel}</span> : null}
      </div>
      <input
        className={styles.rangeInput}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        data-testid={`gimbal-dist-${label.toLowerCase().replace(/\s+/g, '-')}`}
      />
      <span className={styles.distSliderValue}>{display(value)}</span>
    </div>
  );
}

function DistributionChart({
  domain,
  pitchLoNeg,
  pitchHiNeg,
  intPitchNeg,
  peakConc,
  baseConc,
  outlierRate,
  sequence,
}: {
  domain: PitchDomain;
  pitchLoNeg: number;
  pitchHiNeg: number;
  intPitchNeg: number;
  peakConc: number;
  baseConc: number;
  outlierRate: number;
  sequence: number[];
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    const padB = 28;
    const padT = 8;
    const padL = 4;
    const padR = 4;
    const chartW = W - padL - padR;
    const chartH = H - padB - padT;

    const domLo = Math.min(-45, domain.distLo - 8);
    const domHi = Math.max(-5, domain.distHi + 8);

    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#111';
    ctx.fillRect(0, 0, W, H);

    const toX = (d: number) => padL + ((d - domLo) / (domHi - domLo)) * chartW;

    const steps = Math.min(560, Math.max(80, Math.floor(chartW)));
    const pdfVals = mixturePDFValues(intPitchNeg, peakConc, baseConc, outlierRate, steps, domain, domLo, domHi);
    let maxPDF = 0;
    pdfVals.forEach((v) => {
      if (v > maxPDF) maxPDF = v;
    });
    const toY = (v: number) => padT + chartH - (maxPDF > 0 ? (v / maxPDF) * chartH : 0);

    ctx.strokeStyle = '#1a1a1a';
    ctx.lineWidth = 1;
    for (let d = Math.ceil(domLo / 5) * 5; d <= domHi; d += 5) {
      const x = toX(d);
      ctx.beginPath();
      ctx.moveTo(x, padT);
      ctx.lineTo(x, H - padB);
      ctx.stroke();
    }

    ctx.fillStyle = '#131010';
    ctx.fillRect(padL, padT, toX(domain.distLo) - padL, chartH);
    ctx.fillRect(toX(domain.distHi), padT, W - padR - toX(domain.distHi), chartH);

    ctx.fillStyle = '#1a1212';
    ctx.fillRect(toX(domain.distLo), padT, toX(pitchLoNeg) - toX(domain.distLo), chartH);
    ctx.fillRect(toX(pitchHiNeg), padT, toX(domain.distHi) - toX(pitchHiNeg), chartH);

    ctx.strokeStyle = '#1e1414';
    ctx.lineWidth = 1;
    [domain.distLo, domain.distHi].forEach((d) => {
      ctx.beginPath();
      ctx.moveTo(toX(d), padT);
      ctx.lineTo(toX(d), H - padB);
      ctx.stroke();
    });
    ctx.strokeStyle = '#2e1818';
    [pitchLoNeg, pitchHiNeg].forEach((d) => {
      ctx.beginPath();
      ctx.moveTo(toX(d), padT);
      ctx.lineTo(toX(d), H - padB);
      ctx.stroke();
    });

    const baseP = betaParams(intPitchNeg, baseConc, domain);
    const baseVals: number[] = [];
    let maxBase = 0;
    for (let i = 0; i <= steps; i++) {
      const d = domLo + (i / steps) * (domHi - domLo);
      const v = betaPDFUnnorm(toT(d, domain), baseP.alpha, baseP.beta);
      baseVals.push(v);
      if (v > maxBase) maxBase = v;
    }
    const toYbase = (v: number) =>
      padT + chartH - (maxBase > 0 ? (v / maxBase) * chartH * outlierRate : 0);

    ctx.beginPath();
    for (let i = 0; i <= steps; i++) {
      const px = padL + (i / steps) * chartW;
      if (i === 0) ctx.moveTo(px, toYbase(baseVals[i]));
      else ctx.lineTo(px, toYbase(baseVals[i]));
    }
    ctx.strokeStyle = '#2a2020';
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(padL, H - padB);
    for (let i = 0; i <= steps; i++) {
      const px = padL + (i / steps) * chartW;
      ctx.lineTo(px, toY(pdfVals[i]));
    }
    ctx.lineTo(padL + chartW, H - padB);
    ctx.closePath();
    ctx.fillStyle = '#1d1d1d';
    ctx.fill();

    ctx.beginPath();
    for (let i = 0; i <= steps; i++) {
      const px = padL + (i / steps) * chartW;
      if (i === 0) ctx.moveTo(px, toY(pdfVals[i]));
      else ctx.lineTo(px, toY(pdfVals[i]));
    }
    ctx.strokeStyle = '#555';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(toX(intPitchNeg), padT);
    ctx.lineTo(toX(intPitchNeg), H - padB);
    ctx.strokeStyle = '#444';
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 4]);
    ctx.stroke();
    ctx.setLineDash([]);

    const peakRange = ((domain.distHi - domain.distLo) * 0.5) / peakConc * 3;
    sequence.forEach((s, i) => {
      const x = toX(s);
      const y = H - padB - 10 - (i % 3) * 7;
      const isOutlier = Math.abs(s - intPitchNeg) > peakRange;
      ctx.beginPath();
      ctx.arc(x, y, 2.5, 0, 2 * Math.PI);
      ctx.fillStyle = i === sequence.length - 1 ? '#ddd' : isOutlier ? '#664444' : '#555';
      ctx.fill();
    });

    ctx.fillStyle = '#333';
    ctx.font = '10px monospace';
    ctx.textAlign = 'center';
    for (let d = Math.ceil(domLo / 10) * 10; d <= domHi; d += 10) {
      ctx.fillText(`${d}`, toX(d), H - 8);
    }
  }, [domain, pitchLoNeg, pitchHiNeg, intPitchNeg, peakConc, baseConc, outlierRate, sequence]);

  return (
    <canvas
      ref={canvasRef}
      width={560}
      height={140}
      className={styles.distChartCanvas}
      data-testid="gimbal-distribution-chart"
    />
  );
}

export type GimbalDistributionCardProps = {
  heightAgl: number;
  minAngle: number;
  maxAngle: number;
  minAngleHeight: number;
  maxAngleHeight: number;
  onMinAngle: (v: number) => void;
  onMaxAngle: (v: number) => void;
  onMinAngleHeight: (v: number) => void;
  onMaxAngleHeight: (v: number) => void;
  viewerWaypointCount: number;
  onViewerWaypointCount: (n: number) => void;
  onPitchSequenceGenerated: (pitchNegDeg: number[]) => void;
};

export default function GimbalDistributionCard({
  heightAgl,
  minAngle,
  maxAngle,
  minAngleHeight,
  maxAngleHeight,
  onMinAngle,
  onMaxAngle,
  onMinAngleHeight,
  onMaxAngleHeight,
  viewerWaypointCount,
  onViewerWaypointCount,
  onPitchSequenceGenerated,
}: GimbalDistributionCardProps) {
  const [peakConc, setPeakConc] = useState(200);
  const [baseConc, setBaseConc] = useState(3.3);
  const [outlierRate, setOutlierRate] = useState(0.25);
  const [rho, setRho] = useState(0.2);
  const [sequence, setSequence] = useState<number[]>([]);

  // Manual reshuffle seed lives here; auto-regen uses a deterministic seed
  // keyed by params so the same slider position always yields the same dots.
  const shuffleSeedRef = useRef<number | null>(null);

  const domain = useMemo(
    () => pitchDomainFromEnvelope(minAngle, maxAngle),
    [minAngle, maxAngle],
  );

  const intPitchNeg = useMemo(
    () => intendedPitchNeg(heightAgl, minAngle, minAngleHeight, maxAngle, maxAngleHeight),
    [heightAgl, minAngle, minAngleHeight, maxAngle, maxAngleHeight],
  );

  const runGenerate = useCallback(
    (seed: number) => {
      const rng = makeSeededRandom(seed);
      const seq = generatePitchSequence(
        intPitchNeg,
        rho,
        peakConc,
        baseConc,
        outlierRate,
        viewerWaypointCount,
        domain,
        rng,
      );
      setSequence(seq);
      onPitchSequenceGenerated(seq);
    },
    [intPitchNeg, rho, peakConc, baseConc, outlierRate, viewerWaypointCount, domain, onPitchSequenceGenerated],
  );

  // Auto-regenerate with a deterministic seed (debounced ~120ms).
  // shuffleSeedRef === null means "use param-derived seed"; after a manual
  // reshuffle it holds the random seed until params change again.
  const autoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (autoTimerRef.current !== null) clearTimeout(autoTimerRef.current);
    autoTimerRef.current = setTimeout(() => {
      autoTimerRef.current = null;
      const seed =
        shuffleSeedRef.current ??
        paramsToSeed([
          heightAgl, minAngle, maxAngle, minAngleHeight, maxAngleHeight,
          viewerWaypointCount, peakConc, baseConc, outlierRate, rho,
        ]);
      runGenerate(seed);
    }, 120);
    return () => {
      if (autoTimerRef.current !== null) clearTimeout(autoTimerRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [heightAgl, minAngle, maxAngle, minAngleHeight, maxAngleHeight, viewerWaypointCount, peakConc, baseConc, outlierRate, rho]);

  // Manual reshuffle: pick a fresh random seed so the user gets a different
  // draw without moving any sliders. Resets to param-derived seed on next change.
  const generate = useCallback(() => {
    shuffleSeedRef.current = (Math.random() * 0xffffffff) >>> 0;
    runGenerate(shuffleSeedRef.current);
  }, [runGenerate]);

  return (
    <div className={styles.gimbalDistributionCard} data-testid="gimbal-distribution-card">
      <p className={styles.gimbalCardTitle}>Gimbal pitch envelope &amp; distribution</p>
      <p className={styles.gimbalCardSub}>
        Intended at {heightAgl} ft AGL:{' '}
        <span className={styles.gimbalIntendedPitch}>{intPitchNeg.toFixed(1)}°</span>
        <span className={styles.gimbalCardMeta}>
          {' '}
          · caps &minus;{maxAngle}° / &minus;{minAngle}° · buffer ±5°
        </span>
      </p>

      <div className={styles.angleCardsRow}>
        <EnvelopeTile
          label="Min"
          angleValue={minAngle}
          angleMin={5}
          angleMax={30}
          onAngleChange={onMinAngle}
          heightValue={minAngleHeight}
          heightMin={50}
          heightMax={1000}
          onHeightChange={onMinAngleHeight}
        />
        <EnvelopeTile
          label="Max"
          angleValue={maxAngle}
          angleMin={15}
          angleMax={60}
          onAngleChange={onMaxAngle}
          heightValue={maxAngleHeight}
          heightMin={50}
          heightMax={1000}
          onHeightChange={onMaxAngleHeight}
        />
      </div>

      <p className={styles.gimbalSectionLabel}>Mixture density (β spike + wide base)</p>
      <div className={styles.distChartWrap}>
        <DistributionChart
          domain={domain}
          pitchLoNeg={domain.pitchLoNeg}
          pitchHiNeg={domain.pitchHiNeg}
          intPitchNeg={intPitchNeg}
          peakConc={peakConc}
          baseConc={baseConc}
          outlierRate={outlierRate}
          sequence={sequence}
        />
      </div>

      <p className={styles.gimbalSectionLabelMuted}>Shape</p>
      <DistSlider
        label="Peak"
        sublabel="spike tightness"
        value={peakConc}
        min={3}
        max={300}
        step={1}
        display={(v) => v.toFixed(1)}
        onChange={setPeakConc}
      />
      <DistSlider
        label="Base spread"
        sublabel="outlier reach"
        value={baseConc}
        min={2.1}
        max={12}
        step={0.1}
        display={(v) => v.toFixed(1)}
        onChange={setBaseConc}
      />
      <DistSlider
        label="Outlier rate"
        sublabel="% from base"
        value={outlierRate}
        min={0}
        max={0.5}
        step={0.01}
        display={(v) => `${Math.round(v * 100)}%`}
        onChange={setOutlierRate}
      />

      <p className={styles.gimbalSectionLabelMuted}>Sequence</p>
      <DistSlider
        label="Momentum"
        sublabel="AR(1) ρ"
        value={rho}
        min={0}
        max={0.95}
        step={0.05}
        display={(v) => v.toFixed(2)}
        onChange={setRho}
      />
      <DistSlider
        label="Viewer waypoints"
        sublabel="3D scene + sample count"
        value={viewerWaypointCount}
        min={2}
        max={30}
        step={1}
        display={(v) => `${v}`}
        onChange={onViewerWaypointCount}
      />

      <button type="button" className={styles.gimbalGenerateBtn} onClick={generate} data-testid="gimbal-generate-btn">
        Reshuffle pitches
      </button>

      {sequence.length > 0 ? (
        <div className={styles.gimbalPitchList}>
          <p className={styles.gimbalSectionLabelMuted}>Sampled pitches</p>
          {sequence.map((v, i) => {
            const pct = ((v - domain.distLo) / (domain.distHi - domain.distLo)) * 100;
            const intPct = ((intPitchNeg - domain.distLo) / (domain.distHi - domain.distLo)) * 100;
            const delta = v - intPitchNeg;
            const isOutlier =
              Math.abs(delta) > ((domain.distHi - domain.distLo) * 0.5) / peakConc * 3;
            return (
              <div key={i} className={styles.gimbalPitchRow}>
                <span className={styles.gimbalPitchIdx}>{i + 1}</span>
                <div className={styles.gimbalPitchTrack}>
                  <div className={styles.gimbalPitchIntended} style={{ left: `${intPct}%` }} />
                  <div
                    className={styles.gimbalPitchDot}
                    style={{
                      left: `${pct}%`,
                      opacity: 0.4 + (i / sequence.length) * 0.6,
                      background: isOutlier ? '#664444' : '#888',
                    }}
                  />
                </div>
                <span
                  className={styles.gimbalPitchDeg}
                  style={{ color: isOutlier ? '#c08080' : 'rgba(245,245,247,0.75)' }}
                >
                  {v.toFixed(1)}°
                </span>
                <span className={styles.gimbalPitchDelta}>
                  {delta >= 0 ? '+' : ''}
                  {delta.toFixed(1)}
                </span>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
