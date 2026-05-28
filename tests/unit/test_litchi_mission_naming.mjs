import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  buildLitchiMissionName,
  formatLitchiBatchId,
  sanitizeMissionSlug,
  sanitizeMissionTitle,
} from '../../web/lib/litchiMissionNaming.ts';

test('sanitizes project titles for Litchi mission names', () => {
  assert.equal(sanitizeMissionTitle('  Edgewood / Lot #1.csv  '), 'Edgewood Lot 1');
  assert.equal(sanitizeMissionTitle(''), 'Untitled');
  assert.equal(sanitizeMissionTitle(null), 'Untitled');
  assert.equal(sanitizeMissionSlug('  Edgewood / Lot #1.csv  '), 'edgewood-lot-1');
  assert.equal(sanitizeMissionSlug(''), 'spaceport-project');
});

test('formats stable local batch IDs', () => {
  assert.equal(formatLitchiBatchId(new Date(2026, 4, 28, 14, 7, 12)), '20260528-140712');
});

test('builds sortable battery mission names', () => {
  const batchDate = new Date(2026, 4, 28, 14, 7, 12);

  assert.equal(
    buildLitchiMissionName({
      projectTitle: 'Edgewood-1',
      batteryIndex: 3,
      totalBatteries: 12,
      batchDate,
    }),
    'edgewood-1_flight-03-of-12_20260528-140712',
  );

  assert.equal(
    buildLitchiMissionName({
      projectTitle: 'Edgewood-1',
      batteryIndex: 12,
      totalBatteries: 12,
      batchDate,
    }),
    'edgewood-1_flight-12-of-12_20260528-140712',
  );
});

test('caps long mission names to fit Litchi list views', () => {
  const missionName = buildLitchiMissionName({
    projectTitle: 'Very Long Property Name With Extra Neighborhood And Client Notes That Should Not Overflow',
    batteryIndex: 1,
    totalBatteries: 2,
    batchDate: new Date(2026, 4, 28, 14, 7, 12),
  });

  assert.ok(missionName.length <= 64);
  assert.match(missionName, /flight-01-of-02_20260528-140712$/);
});
