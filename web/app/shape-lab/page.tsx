"use client";

import React, { useEffect, useMemo, useState } from 'react';
import TerrainDemo from '@/components/shape-lab/TerrainDemo';
import DemSelector from '@/components/shape-lab/DemSelector';
import ParamsPanel from '@/components/shape-lab/ParamsPanel';
import HudMetrics from '@/components/shape-lab/HudMetrics';
import { DEM_CATALOG, loadDem } from '@/lib/terrain/dems';
import { buildSamplerConfig, twoPassAdaptiveSampling } from '@/lib/terrain/sampler';
import type {
  DemDataset,
  PathVertex,
  SamplerConfig,
  TerrainSamplingResult,
} from '@/lib/terrain/types';

export type Waypoint = {
  x: number;
  y: number;
  z: number; // altitude AGL
  phase: string;
  index: number;
  curve: number;
};

export type FlightParams = {
  slices: number;
  batteryDurationMinutes: number;
  minHeight: number;
  maxHeight: number | null;
};

const R0_FT = 150;
const BASE_RHOLD_FT = 1595;
const BASE_BATTERY_MINUTES = 10;

function mapBatteryToBounces(minutes: number): number {
  const n = Math.round(5 + 0.3 * (minutes - 10));
  return Math.max(3, Math.min(12, n));
}

function calculateHoldRadius(batteryMinutes: number): number {
  return BASE_RHOLD_FT * (batteryMinutes / BASE_BATTERY_MINUTES);
}

function makeSpiral(
  dphi: number,
  N: number,
  r0: number,
  rHold: number,
  steps = 1200,
): { x: number; y: number }[] {
  const baseAlpha = Math.log(rHold / r0) / (N * dphi);
  const radiusRatio = rHold / r0;

  let earlyDensityFactor: number;
  let lateDensityFactor: number;
  if (radiusRatio > 20) {
    earlyDensityFactor = 1.02;
    lateDensityFactor = 0.8;
  } else if (radiusRatio > 10) {
    earlyDensityFactor = 1.05;
    lateDensityFactor = 0.85;
  } else {
    earlyDensityFactor = 1.0;
    lateDensityFactor = 0.9;
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

function buildSlice(
  sliceIdx: number,
  slices: number,
  N: number,
  batteryMinutes: number,
): { waypoints: Omit<Waypoint, 'z'>[] } {
  const dphi = (2 * Math.PI) / slices;
  const offset = Math.PI / 2 + sliceIdx * dphi;

  const rHold = calculateHoldRadius(batteryMinutes);
  const spiralPts = makeSpiral(dphi, N, R0_FT, rHold);
  const tOut = N * dphi;
  const tHold = dphi;
  const tTotal = 2 * tOut + tHold;
  const isSingleSlice = slices === 1;
  const isDoubleSlice = slices === 2;

  const sharedMidFractions = isSingleSlice
    ? [1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6]
    : isDoubleSlice
      ? [1 / 3, 2 / 3]
      : [0.5];
  const outboundMidFractions = isSingleSlice || isDoubleSlice ? [...sharedMidFractions].reverse() : [0.5];
  const inboundMidFractions = sharedMidFractions;
  const holdMidFractions = sharedMidFractions;

  const sampleAt = (targetT: number, phase: string, index: number, isMidpoint = false): Omit<Waypoint, 'z'> => {
    const targetIndex = Math.round((targetT * (spiralPts.length - 1)) / tTotal);
    const clampedIndex = Math.max(0, Math.min(spiralPts.length - 1, targetIndex));
    const pt = spiralPts[clampedIndex];

    const rotX = pt.x * Math.cos(offset) - pt.y * Math.sin(offset);
    const rotY = pt.x * Math.sin(offset) + pt.y * Math.cos(offset);

    const distanceFromCenter = Math.hypot(rotX, rotY);
    let curveRadius: number;
    if (isMidpoint) {
      const baseCurve = 50;
      const scaleFactor = 1.2;
      const maxCurve = 1500;
      curveRadius = Math.min(maxCurve, baseCurve + distanceFromCenter * scaleFactor);
    } else {
      const baseCurve = 40;
      const scaleFactor = 0.05;
      const maxCurve = 160;
      curveRadius = Math.min(maxCurve, baseCurve + distanceFromCenter * scaleFactor);
    }
    curveRadius = Math.round(curveRadius * 10) / 10;

    return { x: rotX, y: rotY, phase, index, curve: curveRadius };
  };

  const labelFromFraction = (value: number) => Math.round((value + Number.EPSILON) * 100);

  const waypoints: Omit<Waypoint, 'z'>[] = [];
  let idx = 0;

  waypoints.push(sampleAt(0, 'outbound_start', idx++, false));
  for (let b = 1; b <= N; b++) {
    outboundMidFractions.forEach((fraction) => {
      const tMid = (b - fraction) * dphi;
      const progressLabel = labelFromFraction(1 - fraction);
      const phase = isSingleSlice || isDoubleSlice ? `outbound_mid_${b}_q${progressLabel}` : `outbound_mid_${b}`;
      waypoints.push(sampleAt(tMid, phase, idx++, true));
    });
    const tBounce = b * dphi;
    waypoints.push(sampleAt(tBounce, `outbound_bounce_${b}`, idx++, false));
  }

  const tEndHold = tOut + tHold;
  const customHoldPhases = isSingleSlice || isDoubleSlice;
  holdMidFractions.forEach((fraction) => {
    const tHoldPoint = tOut + fraction * tHold;
    const phase = customHoldPhases ? `hold_mid_q${labelFromFraction(fraction)}` : 'hold_mid';
    waypoints.push(sampleAt(tHoldPoint, phase, idx++, true));
  });
  waypoints.push(sampleAt(tEndHold, 'hold_end', idx++, false));

  inboundMidFractions.forEach((fraction) => {
    const tFirstInboundMid = tEndHold + fraction * dphi;
    const phase = isSingleSlice || isDoubleSlice ? `inbound_mid_0_q${labelFromFraction(fraction)}` : 'inbound_mid_0';
    waypoints.push(sampleAt(tFirstInboundMid, phase, idx++, true));
  });

  for (let b = 1; b <= N; b++) {
    const tBounce = tEndHold + b * dphi;
    waypoints.push(sampleAt(tBounce, `inbound_bounce_${b}`, idx++, false));
    if (b < N) {
      inboundMidFractions.forEach((fraction) => {
        const tMid = tEndHold + (b + fraction) * dphi;
        const phase = isSingleSlice || isDoubleSlice ? `inbound_mid_${b}_q${labelFromFraction(fraction)}` : `inbound_mid_${b}`;
        waypoints.push(sampleAt(tMid, phase, idx++, true));
      });
    }
  }

  return { waypoints };
}

function applyAltitudeAGL(
  waypoints: Omit<Waypoint, 'z'>[],
  minHeight: number,
  maxHeight?: number | null,
): Waypoint[] {
  if (waypoints.length === 0) return [];
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
      const aglIncrement = additionalDistance * 0.2;
      desiredAgl = minHeight + aglIncrement;
      if (desiredAgl > maxOutboundAltitude) {
        maxOutboundAltitude = desiredAgl;
        maxOutboundDistance = distFromCenter;
      }
    } else if (wp.phase.includes('inbound')) {
      const distFromMax = Math.max(0, maxOutboundDistance - distFromCenter);
      const altitudeIncrease = distFromMax * 0.1;
      desiredAgl = Math.max(minHeight, maxOutboundAltitude + altitudeIncrease);
    } else {
      const additionalDistance = Math.max(0, distFromCenter - firstDist);
      desiredAgl = minHeight + additionalDistance * 0.2;
    }

    if (typeof maxHeight === 'number' && !Number.isNaN(maxHeight)) {
      desiredAgl = Math.min(desiredAgl, maxHeight);
    }
    desiredAgl = Math.max(minHeight, desiredAgl);
    withZ.push({ ...wp, z: desiredAgl });
  }

  return withZ;
}

function buildMissionPath(params: FlightParams): PathVertex[] {
  const N = mapBatteryToBounces(params.batteryDurationMinutes);
  const path: PathVertex[] = [];
  for (let slice = 0; slice < params.slices; slice++) {
    const { waypoints } = buildSlice(slice, params.slices, N, params.batteryDurationMinutes);
    const withZ = applyAltitudeAGL(waypoints, params.minHeight, params.maxHeight);
    withZ.forEach((wp) => {
      path.push({ x: wp.x, y: wp.y, altitudeFt: wp.z, phase: wp.phase });
    });
  }
  return path;
}

export default function ShapeLabPage() {
  const [flightParams, setFlightParams] = useState<FlightParams>({
    slices: 3,
    batteryDurationMinutes: 18,
    minHeight: 120,
    maxHeight: 400,
  });
  const [selectedDemId, setSelectedDemId] = useState<string>('ridge');
  const [dem, setDem] = useState<DemDataset | null>(null);
  const [loadingDem, setLoadingDem] = useState(false);
  const [demError, setDemError] = useState<string | null>(null);

  const [samplerConfig, setSamplerConfig] = useState<SamplerConfig>(() => buildSamplerConfig());
  const [pointBudget, setPointBudget] = useState(120);
  const [aglConstraints, setAglConstraints] = useState<{ minAgl: number; maxAgl: number | null }>({
    minAgl: 120,
    maxAgl: 400,
  });

  useEffect(() => {
    let cancelled = false;
    setLoadingDem(true);
    setDemError(null);
    loadDem(selectedDemId)
      .then((dataset) => {
        if (!cancelled) {
          setDem(dataset);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setDemError(error instanceof Error ? error.message : 'Failed to load DEM');
          setDem(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingDem(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedDemId]);

  useEffect(() => {
    setFlightParams((prev) => ({
      ...prev,
      minHeight: aglConstraints.minAgl,
      maxHeight: aglConstraints.maxAgl,
    }));
  }, [aglConstraints.minAgl, aglConstraints.maxAgl]);

  const missionPath = useMemo(() => buildMissionPath(flightParams), [flightParams]);

  const samplingResult = useMemo<TerrainSamplingResult | null>(() => {
    if (!dem || missionPath.length < 2) return null;
    const result = twoPassAdaptiveSampling(
      missionPath,
      dem,
      samplerConfig,
      {
        minAglFt: aglConstraints.minAgl,
        maxAglFt: aglConstraints.maxAgl ?? undefined,
      },
      pointBudget,
    );
    return result;
  }, [dem, missionPath, samplerConfig, aglConstraints, pointBudget]);

  return (
    <div className="px-6 py-8 text-slate-100">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-white">Terrain Avoidance Lab</h1>
        <p className="mt-1 text-sm text-slate-400">
          Experiment with the v2 two-pass adaptive sampler against synthetic DEMs and live overlays.
        </p>
      </header>

      <section className="relative">
        <TerrainDemo dem={dem} path={missionPath} sampling={samplingResult} />
        {loadingDem && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-900/60 text-slate-200">
            Loading DEM…
          </div>
        )}
        {demError && !loadingDem && (
          <div className="absolute inset-x-0 top-4 mx-auto w-fit rounded-xl border border-rose-500 bg-rose-600/20 px-4 py-2 text-sm text-rose-200">
            {demError}
          </div>
        )}
      </section>

      <section className="mt-6 space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Synthetic DEMs</h2>
        <DemSelector options={DEM_CATALOG} value={selectedDemId} onChange={setSelectedDemId} disabled={loadingDem} />
      </section>

      <section className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <ParamsPanel
          minAgl={aglConstraints.minAgl}
          maxAgl={aglConstraints.maxAgl}
          pointBudget={pointBudget}
          config={samplerConfig}
          onAglChange={({ minAgl, maxAgl }) => {
            setAglConstraints({ minAgl, maxAgl });
          }}
          onConfigChange={(next) => setSamplerConfig((prev) => buildSamplerConfig({ ...prev, ...next }))}
          onPointBudgetChange={setPointBudget}
        />

        <div className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-[#0b1118] p-4">
          <h3 className="text-sm font-semibold tracking-wide text-slate-300">Flight Envelope</h3>
          <label className="flex items-center justify-between text-sm text-slate-300">
            <span>Battery Duration (min)</span>
            <input
              type="range"
              min={8}
              max={30}
              step={1}
              value={flightParams.batteryDurationMinutes}
              onChange={(event) =>
                setFlightParams((prev) => ({ ...prev, batteryDurationMinutes: Number(event.target.value) }))
              }
              className="ml-3 flex-1"
            />
            <span className="ml-3 w-10 text-right text-sky-300">
              {flightParams.batteryDurationMinutes}
            </span>
          </label>

          <label className="flex items-center justify-between text-sm text-slate-300">
            <span>Slices</span>
            <input
              type="range"
              min={1}
              max={6}
              step={1}
              value={flightParams.slices}
              onChange={(event) => setFlightParams((prev) => ({ ...prev, slices: Number(event.target.value) }))}
              className="ml-3 flex-1"
            />
            <span className="ml-3 w-10 text-right text-sky-300">{flightParams.slices}</span>
          </label>

          <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-3 text-xs text-slate-400">
            <div>Samplers tuned for {pointBudget} total elevation samples per run.</div>
            <div className="mt-1">
              Current N (bounces) = {mapBatteryToBounces(flightParams.batteryDurationMinutes)} · Hold radius ≈
              {Math.round(calculateHoldRadius(flightParams.batteryDurationMinutes))} ft
            </div>
          </div>
        </div>
      </section>

      <section className="mt-8">
        <HudMetrics sampling={samplingResult} />
      </section>
    </div>
  );
}
