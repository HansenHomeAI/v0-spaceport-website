"use client";

import React from 'react';
import type { DemDescriptor } from '@/lib/terrain/dems';

interface DemSelectorProps {
  options: DemDescriptor[];
  value: string;
  onChange: (id: string) => void;
  disabled?: boolean;
}

export function DemSelector({ options, value, onChange, disabled }: DemSelectorProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => {
        const isActive = option.id === value;
        return (
          <button
            key={option.id}
            type="button"
            disabled={disabled}
            onClick={() => onChange(option.id)}
            className={`rounded-full border px-4 py-2 text-sm transition ${
              isActive
                ? 'border-sky-400 bg-sky-500/20 text-sky-100 shadow'
                : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500 hover:text-white'
            } ${disabled ? 'opacity-50' : ''}`}
          >
            <div className="font-medium">{option.name}</div>
            <div className="text-xs text-slate-400">{option.description}</div>
          </button>
        );
      })}
    </div>
  );
}

export default DemSelector;
