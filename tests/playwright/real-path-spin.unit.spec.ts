import { expect, test } from "@playwright/test";
import {
  averageRealPathOverlapIou,
  buildRealPathFootprintFeatureCollection,
  buildSpinPathOverlapConfig,
} from "../../web/lib/realPathSpin";

test("buildSpinPathOverlapConfig normalizes the exported pitch envelope", async () => {
  const config = buildSpinPathOverlapConfig({
    speedFts: 24.93,
    speedMph: 17,
    captureSpacingFt: 12,
    captureIntervalSeconds: 0.5,
    yawRateDegPerSec: 90,
    captureArcDeg: 180,
    maxHeadingDeltaDeg: 179,
    defaultPitchDeg: 25,
    pitchSequenceNeg: [20, -25, 30],
  });

  expect(config.defaultPitchDeg).toBe(-25);
  expect(config.pitchSequenceNeg).toEqual([-20, -25, -30]);
  expect(config.captureSpacingFt).toBe(12);
});

test("real path helper builds footprint polygons and overlap from preview waypoints", async () => {
  const waypoints = [
    {
      lat: 39.7392,
      lng: -104.9903,
      altitudeFeet: 180,
      curveFeet: 0,
      headingDeg: 0,
      gimbalPitchDeg: -25,
      distanceFeet: 0,
    },
    {
      lat: 39.73945,
      lng: -104.9903,
      altitudeFeet: 180,
      curveFeet: 20,
      headingDeg: 18,
      gimbalPitchDeg: -26,
      distanceFeet: 18,
    },
    {
      lat: 39.7397,
      lng: -104.99015,
      altitudeFeet: 210,
      curveFeet: 24,
      headingDeg: 36,
      gimbalPitchDeg: -27,
      distanceFeet: 36,
    },
  ];

  const collection = buildRealPathFootprintFeatureCollection(waypoints, 3);
  const averageIou = averageRealPathOverlapIou(waypoints);

  expect(collection.features).toHaveLength(3);
  expect(collection.features[0].geometry.type).toBe("Polygon");
  expect(collection.features[0].geometry.coordinates[0].length).toBeGreaterThan(4);
  expect(averageIou).toBeGreaterThan(0);
  expect(averageIou).toBeLessThanOrEqual(1);
});
