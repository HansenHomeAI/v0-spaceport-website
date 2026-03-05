"use client";

import { BoundaryEllipse, BoundaryPreviewPath, normalizeBoundary } from './flightBoundary';

export type WaypointOverrides = {
  schemaVersion: 1;
  boundarySignature: string | null;
  batteries: Record<string, Array<[number, number]>>;
};

function round(value: number, decimals: number): number {
  const power = 10 ** decimals;
  return Math.round(value * power) / power;
}

function cloneCoords(coords: Array<[number, number]>): Array<[number, number]> {
  return coords.map(([lng, lat]) => [lng, lat] as [number, number]);
}

export function createEmptyWaypointOverrides(boundarySignature: string | null = null): WaypointOverrides {
  return {
    schemaVersion: 1,
    boundarySignature,
    batteries: {},
  };
}

export function cloneWaypointOverrides(overrides: WaypointOverrides): WaypointOverrides {
  const batteries: Record<string, Array<[number, number]>> = {};
  Object.entries(overrides.batteries).forEach(([key, coords]) => {
    batteries[key] = cloneCoords(coords);
  });

  return {
    schemaVersion: 1,
    boundarySignature: overrides.boundarySignature ?? null,
    batteries,
  };
}

export function buildBoundarySignature(boundary: BoundaryEllipse | null | undefined): string | null {
  if (!boundary?.enabled) {
    return null;
  }

  const normalized = normalizeBoundary(boundary);
  return [
    round(normalized.centerLat, 6).toFixed(6),
    round(normalized.centerLng, 6).toFixed(6),
    round(normalized.majorRadiusFt, 2).toFixed(2),
    round(normalized.minorRadiusFt, 2).toFixed(2),
    round(normalized.rotationDeg, 2).toFixed(2),
  ].join('|');
}

export function normalizeWaypointOverrides(input: unknown): WaypointOverrides {
  if (!input || typeof input !== 'object') {
    return createEmptyWaypointOverrides(null);
  }

  const raw = input as Record<string, any>;
  const rawBatteries = raw.batteries;
  const batteries: Record<string, Array<[number, number]>> = {};

  if (rawBatteries && typeof rawBatteries === 'object') {
    Object.entries(rawBatteries).forEach(([key, value]) => {
      const batteryIndex = Number.parseInt(key, 10);
      if (!Number.isFinite(batteryIndex) || batteryIndex <= 0) {
        return;
      }
      if (!Array.isArray(value) || value.length < 2) {
        return;
      }

      const coords: Array<[number, number]> = [];
      value.forEach((pair) => {
        if (!Array.isArray(pair) || pair.length < 2) {
          return;
        }
        const lng = Number(pair[0]);
        const lat = Number(pair[1]);
        if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
          return;
        }
        coords.push([lng, lat]);
      });

      if (coords.length >= 2) {
        batteries[String(batteryIndex)] = coords;
      }
    });
  }

  return {
    schemaVersion: 1,
    boundarySignature: typeof raw.boundarySignature === 'string' ? raw.boundarySignature : null,
    batteries,
  };
}

export function isWaypointOverridesCompatible(
  overrides: WaypointOverrides,
  boundarySignature: string | null
): boolean {
  return (overrides.boundarySignature ?? null) === (boundarySignature ?? null);
}

export function clearWaypointOverrides(boundarySignature: string | null): WaypointOverrides {
  return createEmptyWaypointOverrides(boundarySignature);
}

export function upsertBatteryWaypointOverride(
  overrides: WaypointOverrides,
  batteryIndex: number,
  coords: Array<[number, number]>,
  boundarySignature: string | null
): WaypointOverrides {
  const next = cloneWaypointOverrides(overrides);
  next.boundarySignature = boundarySignature;
  next.batteries[String(batteryIndex)] = cloneCoords(coords);
  return next;
}

export function applyWaypointOverridesToPreviewPaths(
  previewPaths: BoundaryPreviewPath[],
  overrides: WaypointOverrides,
  boundarySignature: string | null
): BoundaryPreviewPath[] {
  if (!isWaypointOverridesCompatible(overrides, boundarySignature)) {
    return previewPaths.map((path) => ({
      batteryIndex: path.batteryIndex,
      coordinates: cloneCoords(path.coordinates),
    }));
  }

  return previewPaths.map((path) => {
    const overrideCoords = overrides.batteries[String(path.batteryIndex)];
    if (!overrideCoords || overrideCoords.length < 2) {
      return {
        batteryIndex: path.batteryIndex,
        coordinates: cloneCoords(path.coordinates),
      };
    }

    return {
      batteryIndex: path.batteryIndex,
      coordinates: cloneCoords(overrideCoords),
    };
  });
}

function parseCsvRows(csvText: string): { header: string; rows: string[][] } {
  const lines = csvText.trim().split(/\r?\n/).filter((line) => line.trim().length > 0);
  if (!lines.length) {
    return { header: '', rows: [] };
  }
  const [header, ...rows] = lines;
  return {
    header,
    rows: rows.map((line) => line.split(',')),
  };
}

function buildProgressFromCoords(coords: Array<[number, number]>): number[] {
  if (!coords.length) {
    return [];
  }

  if (coords.length === 1) {
    return [0];
  }

  const cumulative: number[] = [0];
  let distance = 0;

  for (let index = 1; index < coords.length; index += 1) {
    const [prevLng, prevLat] = coords[index - 1];
    const [lng, lat] = coords[index];
    distance += Math.hypot(lng - prevLng, lat - prevLat);
    cumulative.push(distance);
  }

  if (distance <= Number.EPSILON) {
    return coords.map((_, index) => index / (coords.length - 1));
  }

  return cumulative.map((value) => value / distance);
}

function pickTemplateIndex(templateProgress: number[], targetProgress: number): number {
  if (!templateProgress.length) {
    return 0;
  }

  let low = 0;
  let high = templateProgress.length - 1;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (templateProgress[middle] < targetProgress) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }

  const rightIndex = low;
  const leftIndex = Math.max(0, rightIndex - 1);
  const leftDistance = Math.abs(templateProgress[leftIndex] - targetProgress);
  const rightDistance = Math.abs(templateProgress[rightIndex] - targetProgress);
  return rightDistance < leftDistance ? rightIndex : leftIndex;
}

function extractTemplateCoords(rows: string[][]): Array<[number, number]> {
  const coords: Array<[number, number]> = [];
  rows.forEach((row) => {
    const lat = Number.parseFloat(row[0] ?? '');
    const lng = Number.parseFloat(row[1] ?? '');
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      coords.push([lng, lat]);
    }
  });
  return coords;
}

export function rebuildBatteryCsvWithLiveCoords(
  originalCsvText: string,
  liveCoords: Array<[number, number]>
): string {
  if (!liveCoords.length) {
    return originalCsvText;
  }

  const { header, rows } = parseCsvRows(originalCsvText);
  if (!header || rows.length === 0) {
    return originalCsvText;
  }

  const templateCoords = extractTemplateCoords(rows);
  const templateProgress = buildProgressFromCoords(templateCoords.length ? templateCoords : liveCoords);
  const liveProgress = buildProgressFromCoords(liveCoords);

  const rebuiltRows = liveCoords.map(([lng, lat], index) => {
    const targetProgress = liveProgress[index] ?? (liveCoords.length === 1 ? 0 : index / (liveCoords.length - 1));
    const templateIndex = pickTemplateIndex(templateProgress, targetProgress);
    const templateRow = [...(rows[templateIndex] ?? rows[Math.min(index, rows.length - 1)] ?? [])];

    if (templateRow.length < 2) {
      while (templateRow.length < 2) {
        templateRow.push('');
      }
    }

    templateRow[0] = lat.toFixed(8);
    templateRow[1] = lng.toFixed(8);
    return templateRow;
  });

  return [header, ...rebuiltRows.map((row) => row.join(','))].join('\n');
}
