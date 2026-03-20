/**
 * Unit tests for camera overlap math (run: npx tsx lib/cameraOverlapMath.unit.test.ts)
 */
import assert from 'node:assert/strict';
import {
  FULL_ROT_SEC,
  TRANSIT_SEC,
  TAN_H,
  TAN_V,
  getGimbalAngleDeg,
  hypotenuseFromHeight,
  footprintWidth,
  spacingFt,
  rotationTimeSec,
  groundFootprint,
  footprintBounds,
  rectOverlapFraction,
  footprintOverlapIou,
  averageAdjacentFootprintIou,
} from './cameraOverlapMath';

import { makeSeededRandom, paramsToSeed, generatePitchSequence, pitchDomainFromEnvelope } from './gimbalPitchDistribution';

function approx(a: number, b: number, eps = 1e-6) {
  assert.ok(Math.abs(a - b) < eps, `expected ${a} ≈ ${b}`);
}

// Gimbal interpolation
approx(getGimbalAngleDeg(100, 15, 200, 35, 400), 15);
approx(getGimbalAngleDeg(500, 15, 200, 35, 400), 35);
approx(getGimbalAngleDeg(300, 15, 200, 35, 400), 25);

// Hypotenuse A = h / sin(theta), theta below horizon in degrees
const h100 = hypotenuseFromHeight(100, 15);
approx(h100, 100 / Math.sin((15 * Math.PI) / 180));

// Footprint & spacing
const fp = footprintWidth(h100);
approx(fp, 2 * h100 * Math.tan(Math.PI / 6));
approx(spacingFt(fp, 75), fp * 0.25);

// Rotation time
approx(rotationTimeSec(1), FULL_ROT_SEC + 2 * TRANSIT_SEC);
approx(rotationTimeSec(0.5), 0.5 * FULL_ROT_SEC + 2 * TRANSIT_SEC);

// ---- groundFootprint at nadir (90°) ----
// At 90° pitch the camera looks straight down. Footprint should be a rectangle
// centered at (droneX, 0) with half-extents h*TAN_V along X and h*TAN_H along Y.
const nadir = groundFootprint(0, 100, 90);
const nb = footprintBounds(nadir);
approx(nb.minX, -100 * TAN_V, 0.01);
approx(nb.maxX, 100 * TAN_V, 0.01);
approx(nb.minY, -100 * TAN_H, 0.01);
approx(nb.maxY, 100 * TAN_H, 0.01);

// ---- groundFootprint at 45° (side-looking) ----
// Optical axis is in +Y; footprint extends mostly along look direction (asymmetric in Y).
const tilted = groundFootprint(0, 200, 45);
const tb = footprintBounds(tilted);
assert.ok(tb.maxY > Math.abs(tb.minY) * 0.5, `look-direction (+Y) should dominate: maxY=${tb.maxY.toFixed(1)}, minY=${tb.minY.toFixed(1)}`);
// Along-track (X) span is still non-trivial (55° FOV)
assert.ok(tb.maxX - tb.minX > 50);

// ---- groundFootprint: far edge varies with pitch (not stuck at bigT=10000) ----
// For pitches < 38.5°, upper FOV edge is above horizon. Previously bigT=10000
// made all those pitches look identical at the far edge. With the mirror-clip fix,
// the far (maxY) edge must differ between pitches AND the near (minY) edge must
// also differ correctly: steeper pitch (31°) → closer near, farther far.
{
  const h = 100;
  const b15 = footprintBounds(groundFootprint(0, h, 15));
  const b31 = footprintBounds(groundFootprint(0, h, 31));

  // Near edge: steeper pitch sees ground closer to the drone
  assert.ok(b31.minY < b15.minY,
    `near edge must be closer for steeper pitch: 31°→${b31.minY.toFixed(1)}, 15°→${b15.minY.toFixed(1)}`);

  // Far edge: with mirror-clip the far edge is clearly different between pitches,
  // and must NOT be the same fixed bigT.
  assert.ok(Math.abs(b31.maxY - b15.maxY) > 50,
    `far edge must differ by >50 ft between pitches: 31°→${b31.maxY.toFixed(1)}, 15°→${b15.maxY.toFixed(1)}`);

  // Far edge is bounded to a reasonable multiple of height (not 10000)
  assert.ok(b15.maxY < h * 50,
    `far edge at pitch=15° must be < 50×height: ${b15.maxY.toFixed(1)}`);
  assert.ok(b31.maxY < h * 50,
    `far edge at pitch=31° must be < 50×height: ${b31.maxY.toFixed(1)}`);

  // Computed values match mirror-clip formula: t_far = h / |dz| where
  // dz = -sin(pitch) + TAN_H*cos(pitch)  [positive → above horizon]
  const toRad = (d: number) => d * Math.PI / 180;
  const dz15 = -Math.sin(toRad(15)) + TAN_H * Math.cos(toRad(15));
  const dz31 = -Math.sin(toRad(31)) + TAN_H * Math.cos(toRad(31));
  const dy15 = Math.cos(toRad(15)) + TAN_H * Math.sin(toRad(15));
  const dy31 = Math.cos(toRad(31)) + TAN_H * Math.sin(toRad(31));
  const expectedFar15 = dy15 * (h / Math.max(Math.abs(dz15), 1 / 300));
  const expectedFar31 = dy31 * (h / Math.max(Math.abs(dz31), 1 / 300));
  approx(b15.maxY, expectedFar15, 1);
  approx(b31.maxY, expectedFar31, 1);
}

// ---- groundFootprint offset drone ----
// Drone at x=500, nadir: footprint should be centered at x=500
const offset = groundFootprint(500, 100, 90);
const ob = footprintBounds(offset);
approx((ob.minX + ob.maxX) / 2, 500, 0.1);

// ---- rectOverlapFraction: identical footprints ----
const same = rectOverlapFraction(nb, nb);
approx(same.alongTrack, 1);
approx(same.crossTrack, 1);

// ---- rectOverlapFraction: no along-track overlap ----
// Footprints far apart on X axis still share the same Y range → crossTrack = 1
const farApart = footprintBounds(groundFootprint(10000, 100, 90));
const noOverlap = rectOverlapFraction(nb, farApart);
approx(noOverlap.alongTrack, 0);
approx(noOverlap.crossTrack, 1);

// ---- rectOverlapFraction: partial overlap ----
// Two nadir footprints shifted by 25% of their along-track span → 75% along-track overlap
const spanX = nb.maxX - nb.minX;
const shifted = footprintBounds(groundFootprint(spanX * 0.25, 100, 90));
const partial = rectOverlapFraction(nb, shifted);
approx(partial.alongTrack, 0.75, 0.01);
approx(partial.crossTrack, 1.0, 0.01);

// ---- footprintOverlapIou ----
approx(footprintOverlapIou(nb, nb), 1);
approx(footprintOverlapIou(nb, farApart), 0);
// Two equal squares [0,10]x[0,10] and [5,15]x[0,10]: intersection 5*10=50, union 150-50=150, IoU=50/150
const sqA = { minX: 0, maxX: 10, minY: 0, maxY: 10 };
const sqB = { minX: 5, maxX: 15, minY: 0, maxY: 10 };
approx(footprintOverlapIou(sqA, sqB), 50 / 150, 1e-9);

// ---- averageAdjacentFootprintIou (N waypoints) ----
const pos2 = [-25, 25];
const pitch2 = [30, 30];
const fp0 = groundFootprint(pos2[0], 100, pitch2[0]);
const fp1 = groundFootprint(pos2[1], 100, pitch2[1]);
const mean2 = averageAdjacentFootprintIou(pos2, 100, pitch2);
approx(mean2, footprintOverlapIou(footprintBounds(fp0), footprintBounds(fp1)));

assert.equal(averageAdjacentFootprintIou([0], 100, [30]), 0);
assert.equal(averageAdjacentFootprintIou([0, 50], 100, [30]), 0);

const pos3 = [-50, 0, 50];
const pitch3 = [28, 28, 28];
const m3 = averageAdjacentFootprintIou(pos3, 100, pitch3);
const a01 = footprintOverlapIou(
  footprintBounds(groundFootprint(-50, 100, 28)),
  footprintBounds(groundFootprint(0, 100, 28)),
);
const a12 = footprintOverlapIou(
  footprintBounds(groundFootprint(0, 100, 28)),
  footprintBounds(groundFootprint(50, 100, 28)),
);
approx(m3, (a01 + a12) / 2);

// ---- Flat-spin 18°/s identity ----
// For any nonzero capture fraction, the yaw rate over the spin segment is constant:
//   effectiveCapDeg / (effectiveCapPct * FULL_ROT_SEC) = 360 / 20 = 18°/s
for (const capDeg of [90, 180, 270, 360]) {
  const capPct = capDeg / 360;
  const tSpin = capPct * FULL_ROT_SEC;
  const yawRate = tSpin > 0 ? capDeg / tSpin : 0;
  approx(yawRate, 18, 1e-9);
}
// Full 360° capture → exactly 3 RPM
const fullCapYaw = 360 / (1 * FULL_ROT_SEC);
approx(fullCapYaw / 6, 3, 1e-9);

// ---- Seeded PRNG — deterministic output ----
const rng1 = makeSeededRandom(42);
const rng2 = makeSeededRandom(42);
for (let i = 0; i < 20; i++) {
  approx(rng1(), rng2());
}
// Different seeds produce different values (birthday paradox essentially impossible here)
const rngA = makeSeededRandom(1);
const rngB = makeSeededRandom(2);
const drawn = Array.from({ length: 10 }, () => [rngA(), rngB()]);
assert.ok(drawn.some(([a, b]) => Math.abs(a - b) > 1e-6), 'different seeds should diverge');

// ---- paramsToSeed — same params same seed ----
assert.equal(paramsToSeed([100, 15, 35, 200, 400]), paramsToSeed([100, 15, 35, 200, 400]));
assert.notEqual(paramsToSeed([100, 15, 35, 200, 400]), paramsToSeed([101, 15, 35, 200, 400]));

// ---- generatePitchSequence with seeded RNG — stable draws ----
const domain = pitchDomainFromEnvelope(15, 35);
const seq1 = generatePitchSequence(-25, 0.2, 200, 3.3, 0.25, 10, domain, makeSeededRandom(7));
const seq2 = generatePitchSequence(-25, 0.2, 200, 3.3, 0.25, 10, domain, makeSeededRandom(7));
seq1.forEach((v, i) => approx(v, seq2[i], 1e-12));
// Draws from different seeds should differ on at least one element
const seq3 = generatePitchSequence(-25, 0.2, 200, 3.3, 0.25, 10, domain, makeSeededRandom(8));
assert.ok(seq1.some((v, i) => Math.abs(v - seq3[i]) > 1e-6), 'different seeds should produce different pitch sequences');

console.log('cameraOverlapMath.unit.test.ts: all assertions passed');
