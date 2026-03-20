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

function lineIntersection2d(
  a1: [number, number],
  a2: [number, number],
  b1: [number, number],
  b2: [number, number],
): [number, number] {
  const [x1, y1] = a1;
  const [x2, y2] = a2;
  const [x3, y3] = b1;
  const [x4, y4] = b2;
  const denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4);
  assert.ok(Math.abs(denom) > 1e-9, 'diagonals must not be parallel');
  const px = (
    (x1 * y2 - y1 * x2) * (x3 - x4) -
    (x1 - x2) * (x3 * y4 - y3 * x4)
  ) / denom;
  const py = (
    (x1 * y2 - y1 * x2) * (y3 - y4) -
    (y1 - y2) * (x3 * y4 - y3 * x4)
  ) / denom;
  return [px, py];
}

function cameraRayVector(
  pitchDeg: number,
  headingDeg: number,
  alongSample: number,
  crossSample: number,
): [number, number, number] {
  const theta = (pitchDeg * Math.PI) / 180;
  const H = (headingDeg * Math.PI) / 180;
  const sinT = Math.sin(theta);
  const cosT = Math.cos(theta);
  const sinH = Math.sin(H);
  const cosH = Math.cos(H);
  const losX = sinH * cosT;
  const losY = -sinT;
  const losZ = cosH * cosT;
  const rightX = cosH;
  const rightY = 0;
  const rightZ = -sinH;
  const upX = sinH * sinT;
  const upY = cosT;
  const upZ = cosH * sinT;
  return [
    losX + alongSample * TAN_H * rightX + crossSample * TAN_V * upX,
    losY + alongSample * TAN_H * rightY + crossSample * TAN_V * upY,
    losZ + alongSample * TAN_H * rightZ + crossSample * TAN_V * upZ,
  ];
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
// centered at (droneX, 0) with half-extents h*TAN_H along X and h*TAN_V along Y.
const nadir = groundFootprint(0, 100, 90);
const nb = footprintBounds(nadir);
approx(nb.minX, -100 * TAN_H, 0.01);
approx(nb.maxX, 100 * TAN_H, 0.01);
approx(nb.minY, -100 * TAN_V, 0.01);
approx(nb.maxY, 100 * TAN_V, 0.01);

// ---- groundFootprint at 45° (side-looking) ----
// Optical axis is in +Y; footprint extends mostly along look direction (asymmetric in Y).
const tilted = groundFootprint(0, 200, 45);
const tb = footprintBounds(tilted);
assert.ok(tb.maxY > Math.abs(tb.minY) * 0.5, `look-direction (+Y) should dominate: maxY=${tb.maxY.toFixed(1)}, minY=${tb.minY.toFixed(1)}`);
// Along-track (X) span is still non-trivial (75° horizontal FOV on right)
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
  // dz = -sin(pitch) + TAN_V*cos(pitch) on upper image row (sh=+1)
  const toRad = (d: number) => d * Math.PI / 180;
  const dz15 = -Math.sin(toRad(15)) + TAN_V * Math.cos(toRad(15));
  const dz31 = -Math.sin(toRad(31)) + TAN_V * Math.cos(toRad(31));
  const dy15 = Math.cos(toRad(15)) + TAN_V * Math.sin(toRad(15));
  const dy31 = Math.cos(toRad(31)) + TAN_V * Math.sin(toRad(31));
  const expectedFar15 = dy15 * (h / Math.max(Math.abs(dz15), 1 / 300));
  const expectedFar31 = dy31 * (h / Math.max(Math.abs(dz31), 1 / 300));
  approx(b15.maxY, expectedFar15, 1);
  approx(b31.maxY, expectedFar31, 1);
}

// ---- optical axis vs footprint diagonals ----
// When all four corner rays physically hit the ground (pitch >= ~38.5°), the
// projected footprint is a true projective image and its diagonals intersect
// at the center LOS ground hit.
for (const { droneX, height, pitchDeg, headingDeg } of [
  { droneX: 10, height: 100, pitchDeg: 45, headingDeg: 0 },
  { droneX: 40, height: 100, pitchDeg: 60, headingDeg: 45 },
  { droneX: -25, height: 180, pitchDeg: 75, headingDeg: 90 },
]) {
  const fp = groundFootprint(droneX, height, pitchDeg, headingDeg);
  const diagHit = lineIntersection2d(
    [fp[0][0], fp[0][1]],
    [fp[2][0], fp[2][1]],
    [fp[1][0], fp[1][1]],
    [fp[3][0], fp[3][1]],
  );

  const theta = (pitchDeg * Math.PI) / 180;
  const H = (headingDeg * Math.PI) / 180;
  const losX = Math.sin(H) * Math.cos(theta);
  const losY = Math.cos(H) * Math.cos(theta);
  const losZ = -Math.sin(theta);
  const tCenter = height / Math.abs(losZ);
  const centerGroundHit: [number, number] = [
    droneX + losX * tCenter,
    losY * tCenter,
  ];

  approx(diagHit[0], centerGroundHit[0], 1e-6);
  approx(diagHit[1], centerGroundHit[1], 1e-6);
}

// For shallow pitches (< ~38.5°), the upper rays point above the horizon and
// `groundFootprint` intentionally uses a mirror-clip to synthesize a bounded
// far edge for overlap visualization. In that regime, the footprint quad is no
// longer a true projective image, so its diagonals should NOT be expected to
// pass through the optical-axis ground hit.
{
  const droneX = 0;
  const height = 100;
  const pitchDeg = 15;
  const headingDeg = 0;
  const fp = groundFootprint(droneX, height, pitchDeg, headingDeg);
  const diagHit = lineIntersection2d(
    [fp[0][0], fp[0][1]],
    [fp[2][0], fp[2][1]],
    [fp[1][0], fp[1][1]],
    [fp[3][0], fp[3][1]],
  );
  const theta = (pitchDeg * Math.PI) / 180;
  const losY = Math.cos(theta);
  const losZ = -Math.sin(theta);
  const tCenter = height / Math.abs(losZ);
  const centerGroundHitY = losY * tCenter;
  assert.ok(
    Math.abs(diagHit[1] - centerGroundHitY) > 100,
    `mirror-clipped shallow footprint should diverge from optical center: diag=${diagHit[1].toFixed(1)}, center=${centerGroundHitY.toFixed(1)}`,
  );
}

// The displayed 3D frustum mouth uses a constant camera-depth plane
// P(u,v) = O + d * (L + uR + vU). Its diagonals must always intersect at the
// optical axis point O + dL, even in shallow-pitch cases where the ground
// footprint is mirror-clipped and no longer projectively centered.
for (const { pitchDeg, headingDeg, depth } of [
  { pitchDeg: 15, headingDeg: 0, depth: 90 },
  { pitchDeg: 15, headingDeg: 45, depth: 90 },
  { pitchDeg: 75, headingDeg: 120, depth: 160 },
]) {
  const c00 = cameraRayVector(pitchDeg, headingDeg, -1, -1);
  const c01 = cameraRayVector(pitchDeg, headingDeg, -1, 1);
  const c11 = cameraRayVector(pitchDeg, headingDeg, 1, 1);
  const c10 = cameraRayVector(pitchDeg, headingDeg, 1, -1);
  const center = cameraRayVector(pitchDeg, headingDeg, 0, 0);
  const diagA: [number, number, number] = [
    depth * (c00[0] + c11[0]) / 2,
    depth * (c00[1] + c11[1]) / 2,
    depth * (c00[2] + c11[2]) / 2,
  ];
  const diagB: [number, number, number] = [
    depth * (c01[0] + c10[0]) / 2,
    depth * (c01[1] + c10[1]) / 2,
    depth * (c01[2] + c10[2]) / 2,
  ];
  const centerPoint: [number, number, number] = [
    depth * center[0],
    depth * center[1],
    depth * center[2],
  ];
  approx(diagA[0], centerPoint[0], 1e-9);
  approx(diagA[1], centerPoint[1], 1e-9);
  approx(diagA[2], centerPoint[2], 1e-9);
  approx(diagB[0], centerPoint[0], 1e-9);
  approx(diagB[1], centerPoint[1], 1e-9);
  approx(diagB[2], centerPoint[2], 1e-9);
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
