import test from "node:test";
import assert from "node:assert/strict";

import { buildCurvedPath, CurvatureWaypoint } from "../lib/curvedPath";

function feet(value: number): number {
  return value * 0.3048;
}

test("buildCurvedPath preserves straight segments when radius is zero", () => {
  const waypoints: CurvatureWaypoint[] = [
    { latitude: 38.0, longitude: -78.0, altitudeFt: 200, curveSizeMeters: 0 },
    { latitude: 38.0002, longitude: -78.0001, altitudeFt: 220, curveSizeMeters: 0 },
    { latitude: 38.0004, longitude: -78.0002, altitudeFt: 240, curveSizeMeters: 0 },
  ];

  const result = buildCurvedPath(waypoints);

  assert.equal(result.points.length, waypoints.length, "No additional vertices should be created");
  assert.equal(result.arcSummaries.length, 0, "No arcs expected without curve radii");
  assert.ok(result.totalLengthMeters > 0, "Total length should be positive");
});

test("buildCurvedPath inserts arc samples for curved waypoint", () => {
  const curveMeters = feet(60);
  const waypoints: CurvatureWaypoint[] = [
    { latitude: 38.0, longitude: -78.0, altitudeFt: 200, curveSizeMeters: 0 },
    { latitude: 38.0, longitude: -77.9985, altitudeFt: 200, curveSizeMeters: curveMeters },
    { latitude: 38.0015, longitude: -77.9985, altitudeFt: 200, curveSizeMeters: 0 },
  ];

  const result = buildCurvedPath(waypoints);

  assert.ok(result.points.length > waypoints.length, "Curved path should include sampled arc points");
  assert.equal(result.arcSummaries.length, 1, "Single curved waypoint expected");
  assert.ok(
    Math.abs(result.arcSummaries[0].radiusMeters - curveMeters) < 1,
    "Computed radius should closely match requested radius"
  );

  const entry = result.arcSummaries[0].entry;
  const exit = result.arcSummaries[0].exit;
  assert.notDeepStrictEqual(entry, waypoints[1], "Entry point should differ from raw waypoint location");
  assert.notDeepStrictEqual(exit, waypoints[1], "Exit point should differ from raw waypoint location");
  assert.ok(result.totalLengthMeters > curveMeters, "Total length should include arc contribution");
});
