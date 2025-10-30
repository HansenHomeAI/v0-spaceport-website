"use client";

import React from 'react';
import type { TerrainSamplingResult } from '@/lib/terrain/types';

interface HudMetricsProps {
  sampling: TerrainSamplingResult | null;
}

const LABELS: { key: keyof TerrainSamplingResult['metrics']; label: string }[] = [
  { key: 'discoveryPointsUsed', label: 'Discovery Samples' },
  { key: 'refinementPointsUsed', label: 'Refinement Samples' },
  { key: 'totalPointsUsed', label: 'Total Points' },
  { key: 'hazardsDetected', label: 'Hazards' },
  { key: 'safetyWaypoints', label: 'Safety Waypoints' },
];

export function HudMetrics({ sampling }: HudMetricsProps) {
  if (!sampling) {
    return (
      <div className="flex flex-wrap gap-3 rounded-2xl border border-slate-800 bg-[#0a111c] p-4 text-slate-400">
        Run the sampler to populate metrics.
      </div>
    );
  }

  const { metrics, hazards, safetyWaypoints } = sampling;

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-[#0a111c] p-4 text-slate-100">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {LABELS.map((item) => (
          <div key={item.key} className="rounded-xl border border-slate-700 bg-slate-900/60 px-3 py-2">
            <div className="text-xs uppercase tracking-wide text-slate-500">{item.label}</div>
            <div className="text-lg font-semibold text-sky-200">{metrics[item.key]}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-3">
          <div className="text-xs uppercase tracking-wide text-slate-500">Hazard Inventory</div>
          <ul className="mt-2 space-y-1 text-sm text-slate-300">
            {hazards.length === 0 && <li className="text-slate-500">No hazards flagged.</li>}
            {hazards.map((hazard, idx) => (
              <li key={idx} className="flex items-center justify-between gap-3">
                <span>{hazard.description}</span>
                <span className="text-xs text-slate-400">{hazard.severity.toFixed(1)}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-3">
          <div className="text-xs uppercase tracking-wide text-slate-500">Safety Injections</div>
          <ul className="mt-2 space-y-1 text-sm text-slate-300">
            {safetyWaypoints.length === 0 && <li className="text-slate-500">No safety inserts required.</li>}
            {safetyWaypoints.map((wp, idx) => (
              <li key={idx} className="flex items-center justify-between gap-3">
                <span>{wp.reason}</span>
                <span className="text-xs text-slate-400">{Math.round(wp.altitudeFt)} ft</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

export default HudMetrics;
