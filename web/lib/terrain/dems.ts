import type { DemDataset } from './types';

export interface DemDescriptor {
  id: string;
  name: string;
  description: string;
}

export const DEM_CATALOG: DemDescriptor[] = [
  { id: 'flat', name: 'Flat Prairie', description: 'Baseline plane for sanity checks.' },
  { id: 'sinusoid', name: 'Sinusoid Hills', description: 'Smooth rolling sine/cosine terrain.' },
  { id: 'ridge', name: 'Knife Ridge', description: 'Narrow ridge line with valleys east/west.' },
  { id: 'mountain', name: 'Mountain Range', description: 'Twin peaks with a saddle valley.' },
  { id: 'cliff', name: 'Mesa Cliff', description: 'Abrupt escarpment and gentle ramp.' },
  { id: 'mixed', name: 'Mixed Badlands', description: 'Interleaved bluffs, gullies, and plateaus.' },
  { id: 'dunes', name: 'Coastal Dunes', description: 'Low amplitude rolling dune field.' },
  { id: 'volcano', name: 'Caldera Volcano', description: 'Steep-sided cone with central bowl.' },
  { id: 'canyon', name: 'Slot Canyon', description: 'Meandering canyon with sheer walls.' },
  { id: 'plateau', name: 'Stepped Plateau', description: 'Tiered mesas with gully cuts.' },
  { id: 'sawtooth', name: 'Sawtooth Ridges', description: 'Alternating sharp ridges and valleys.' },
  { id: 'buttes', name: 'Stacked Buttes', description: 'Discrete buttes separated by washes.' },
  { id: 'glacier', name: 'Glacial Valley', description: 'Deep trough with moraines and headwall.' },
  { id: 'karst', name: 'Karst Spires', description: 'Dense spire field with sinkholes.' },
];

export async function loadDem(id: string): Promise<DemDataset> {
  const response = await fetch(`/dem/${id}.json`, { cache: 'no-cache' });
  if (!response.ok) {
    throw new Error(`Failed to load DEM ${id}: ${response.status}`);
  }
  const data = (await response.json()) as DemDataset;
  return data;
}

export function sampleDemElevation(dem: DemDataset, x: number, y: number): number {
  const { cellSizeFt, originFt, gridSize, elevationsFt } = dem;
  const cols = gridSize[0];
  const rows = gridSize[1];
  const localX = (x - originFt[0]) / cellSizeFt;
  const localY = (y - originFt[1]) / cellSizeFt;

  const ix = Math.floor(localX);
  const iy = Math.floor(localY);

  const fx = localX - ix;
  const fy = localY - iy;

  const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

  const ix0 = clamp(ix, 0, cols - 1);
  const iy0 = clamp(iy, 0, rows - 1);
  const ix1 = clamp(ix0 + 1, 0, cols - 1);
  const iy1 = clamp(iy0 + 1, 0, rows - 1);

  const v00 = elevationsFt[iy0][ix0];
  const v10 = elevationsFt[iy0][ix1];
  const v01 = elevationsFt[iy1][ix0];
  const v11 = elevationsFt[iy1][ix1];

  const interpX0 = v00 * (1 - fx) + v10 * fx;
  const interpX1 = v01 * (1 - fx) + v11 * fx;
  const interpolated = interpX0 * (1 - fy) + interpX1 * fy;

  return interpolated;
}
