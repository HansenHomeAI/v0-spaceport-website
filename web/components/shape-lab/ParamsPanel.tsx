"use client";

import React from 'react';
import type { SamplerConfig } from '@/lib/terrain/types';

interface ParamsPanelProps {
  minAgl: number;
  maxAgl: number | null;
  config: SamplerConfig;
  onAglChange: (next: { minAgl: number; maxAgl: number | null }) => void;
  onConfigChange: (next: Partial<SamplerConfig>) => void;
}

function numeric(value: string, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function ParamsPanel({
  minAgl,
  maxAgl,
  config,
  onAglChange,
  onConfigChange,
}: ParamsPanelProps) {
  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-[#0b1018] p-4 text-slate-200 shadow-lg">
      <div>
        <h3 className="text-sm font-semibold tracking-wide text-slate-300">AGL Constraints</h3>
        <div className="mt-2 grid grid-cols-2 gap-3">
          <label className="flex flex-col text-xs uppercase tracking-wide text-slate-500">
            Min AGL (ft)
            <input
              type="number"
              value={minAgl}
              min={0}
              onChange={(event) => onAglChange({ minAgl: numeric(event.target.value, minAgl), maxAgl })}
              className="mt-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm focus:border-sky-400 focus:outline-none"
            />
          </label>
          <label className="flex flex-col text-xs uppercase tracking-wide text-slate-500">
            Max AGL (ft)
            <input
              type="number"
              value={maxAgl ?? ''}
              placeholder="∞"
              onChange={(event) => {
                const value = event.target.value.trim();
                onAglChange({
                  minAgl,
                  maxAgl: value === '' ? null : numeric(value, maxAgl ?? minAgl + 200),
                });
              }}
              className="mt-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm focus:border-sky-400 focus:outline-none"
            />
          </label>
        </div>
      </div>

      <div>
        <h3 className="text-sm font-semibold tracking-wide text-slate-300">Sampler Strategy</h3>
        <p className="mt-2 text-xs text-slate-400">
          Discovery share {Math.round(config.discoveryFraction * 100)}% · refinement {Math.round((1 - config.discoveryFraction) * 100)}%
        </p>
        <div className="mt-2 flex items-center gap-3 text-xs text-slate-400">
          <span className="uppercase tracking-wide">Discovery Fraction</span>
          <input
            type="range"
            min={10}
            max={80}
            step={5}
            value={Math.round(config.discoveryFraction * 100)}
            onChange={(event) => {
              const pct = numeric(event.target.value, config.discoveryFraction * 100);
              const fraction = Math.min(0.9, Math.max(0.05, pct / 100));
              onConfigChange({ discoveryFraction: fraction });
            }}
            className="flex-1"
          />
        </div>
      </div>

      <div>
        <h3 className="text-sm font-semibold tracking-wide text-slate-300">Intervals & Thresholds</h3>
        <div className="mt-2 grid grid-cols-2 gap-3 text-xs text-slate-400">
          <label className="flex flex-col gap-1">
            Discovery Interval (ft)
            <input
              type="number"
              value={config.discoveryIntervalFt}
              min={50}
              step={10}
              onChange={(event) => onConfigChange({ discoveryIntervalFt: numeric(event.target.value, config.discoveryIntervalFt) })}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-sky-400 focus:outline-none"
            />
          </label>
          <label className="flex flex-col gap-1">
            Dense Interval (ft)
            <input
              type="number"
              value={config.denseIntervalFt}
              min={10}
              step={5}
              onChange={(event) => onConfigChange({ denseIntervalFt: numeric(event.target.value, config.denseIntervalFt) })}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-sky-400 focus:outline-none"
            />
          </label>
          <label className="flex flex-col gap-1">
            Medium Interval (ft)
            <input
              type="number"
              value={config.mediumIntervalFt}
              min={40}
              step={10}
              onChange={(event) => onConfigChange({ mediumIntervalFt: numeric(event.target.value, config.mediumIntervalFt) })}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-sky-400 focus:outline-none"
            />
          </label>
          <label className="flex flex-col gap-1">
            Sparse Interval (ft)
            <input
              type="number"
              value={config.sparseIntervalFt}
              min={80}
              step={20}
              onChange={(event) => onConfigChange({ sparseIntervalFt: numeric(event.target.value, config.sparseIntervalFt) })}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-sky-400 focus:outline-none"
            />
          </label>
          <label className="flex flex-col gap-1">
            Medium Gradient (ft/100ft)
            <input
              type="number"
              value={config.gradMediumFtPer100}
              min={1}
              step={1}
              onChange={(event) => onConfigChange({ gradMediumFtPer100: numeric(event.target.value, config.gradMediumFtPer100) })}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-sky-400 focus:outline-none"
            />
          </label>
          <label className="flex flex-col gap-1">
            Critical Gradient (ft/100ft)
            <input
              type="number"
              value={config.gradCriticalFtPer100}
              min={10}
              step={2}
              onChange={(event) => onConfigChange({ gradCriticalFtPer100: numeric(event.target.value, config.gradCriticalFtPer100) })}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-sky-400 focus:outline-none"
            />
          </label>
        </div>
      </div>
    </div>
  );
}

export default ParamsPanel;
