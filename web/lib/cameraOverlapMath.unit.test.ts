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
} from './cameraOverlapMath';

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

console.log('cameraOverlapMath.unit.test.ts: all assertions passed');
