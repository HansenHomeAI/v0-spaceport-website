import { expect, test } from '@playwright/test';
import {
  applyWaypointOverridesToPreviewPaths,
  buildBoundarySignature,
  clearWaypointOverrides,
  createEmptyWaypointOverrides,
  normalizeWaypointOverrides,
  rebuildBatteryCsvWithLiveCoords,
  upsertBatteryWaypointOverride,
} from '../../web/lib/waypointOverrides';

const boundary = {
  version: 1 as const,
  enabled: true,
  centerLat: 39.7392,
  centerLng: -104.9903,
  majorRadiusFt: 1000,
  minorRadiusFt: 700,
  rotationDeg: 45,
};

test('boundary signature normalizes values consistently', async () => {
  const signatureA = buildBoundarySignature(boundary);
  const signatureB = buildBoundarySignature({
    ...boundary,
    rotationDeg: 405,
    majorRadiusFt: 1000.001,
    minorRadiusFt: 699.999,
  });

  expect(signatureA).toBe(signatureB);
});

test('normalizeWaypointOverrides drops invalid entries', async () => {
  const normalized = normalizeWaypointOverrides({
    schemaVersion: 1,
    boundarySignature: 'abc',
    batteries: {
      '1': [[-104.99, 39.73], [-104.98, 39.74]],
      '2': [[-104.97, 39.75]],
      bad: [[1, 2], [3, 4]],
      '3': [[-104.96, 'x'], [-104.95, 39.76]],
    },
  });

  expect(normalized.boundarySignature).toBe('abc');
  expect(Object.keys(normalized.batteries)).toEqual(['1']);
  expect(normalized.batteries['1']).toHaveLength(2);
});

test('applyWaypointOverridesToPreviewPaths respects boundary signature', async () => {
  const signature = buildBoundarySignature(boundary);
  const overrides = upsertBatteryWaypointOverride(
    createEmptyWaypointOverrides(signature),
    1,
    [[-104.91, 39.71], [-104.90, 39.72], [-104.89, 39.73]],
    signature
  );

  const preview = [
    { batteryIndex: 1, coordinates: [[-104.99, 39.73], [-104.98, 39.74]] as Array<[number, number]> },
  ];

  const withMatch = applyWaypointOverridesToPreviewPaths(preview, overrides, signature);
  expect(withMatch[0].coordinates).toHaveLength(3);

  const withMismatch = applyWaypointOverridesToPreviewPaths(
    preview,
    overrides,
    buildBoundarySignature({ ...boundary, rotationDeg: 90 })
  );
  expect(withMismatch[0].coordinates).toHaveLength(2);
});

test('rebuildBatteryCsvWithLiveCoords patches same-length coordinates', async () => {
  const csv = [
    'latitude,longitude,alt,speed',
    '39.70000000,-104.90000000,120,5',
    '39.71000000,-104.91000000,121,5',
  ].join('\n');

  const rebuilt = rebuildBatteryCsvWithLiveCoords(csv, [
    [-104.95, 39.75],
    [-104.96, 39.76],
  ]);

  const lines = rebuilt.split('\n');
  expect(lines).toHaveLength(3);
  expect(lines[1].startsWith('39.75000000,-104.95000000,120,5')).toBeTruthy();
  expect(lines[2].startsWith('39.76000000,-104.96000000,121,5')).toBeTruthy();
});

test('rebuildBatteryCsvWithLiveCoords supports insertions and deletions', async () => {
  const csv = [
    'latitude,longitude,alt,speed',
    '39.70000000,-104.90000000,120,5',
    '39.71000000,-104.91000000,121,5',
    '39.72000000,-104.92000000,122,5',
    '39.73000000,-104.93000000,123,5',
  ].join('\n');

  const inserted = rebuildBatteryCsvWithLiveCoords(csv, [
    [-104.90, 39.70],
    [-104.905, 39.705],
    [-104.91, 39.71],
    [-104.92, 39.72],
    [-104.93, 39.73],
  ]);
  expect(inserted.split('\n')).toHaveLength(6);

  const deleted = rebuildBatteryCsvWithLiveCoords(csv, [
    [-104.90, 39.70],
    [-104.93, 39.73],
  ]);
  expect(deleted.split('\n')).toHaveLength(3);
});

test('clearWaypointOverrides resets batteries but keeps signature', async () => {
  const signature = buildBoundarySignature(boundary);
  const cleared = clearWaypointOverrides(signature);
  expect(cleared.boundarySignature).toBe(signature);
  expect(Object.keys(cleared.batteries)).toHaveLength(0);
});
