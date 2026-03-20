import { expect, test } from "@playwright/test";
import {
  altitudeFeetToMeters,
  buildBatteryPathElevatedFeature,
  buildCurvedBatteryPathPoints,
  buildLineZOffsetExpression,
  interpolateSegmentAltitudeFeet,
  parseBatteryCsvWaypoints,
  syncBatteryPathWaypointsWithCoords,
} from "../../web/lib/flightPath3d";

test("parseBatteryCsvWaypoints reads latitude longitude altitude and curve columns", async () => {
  const csv = [
    "latitude,longitude,altitude(ft),curvesize(ft),speed(m/s)",
    "39.70000000,-104.90000000,120,40,8.85",
    "39.71000000,-104.91000000,180,120,8.85",
    "39.72000000,-104.92000000,240,80,8.85",
  ].join("\n");

  const waypoints = parseBatteryCsvWaypoints(csv);

  expect(waypoints).toEqual([
    { lat: 39.7, lng: -104.9, altitudeFeet: 120, curveFeet: 40 },
    { lat: 39.71, lng: -104.91, altitudeFeet: 180, curveFeet: 120 },
    { lat: 39.72, lng: -104.92, altitudeFeet: 240, curveFeet: 80 },
  ]);
});

test("syncBatteryPathWaypointsWithCoords preserves end altitudes and interpolates inserts", async () => {
  const synced = syncBatteryPathWaypointsWithCoords(
    [
      { lat: 39.7, lng: -104.9, altitudeFeet: 120, curveFeet: 40 },
      { lat: 39.71, lng: -104.91, altitudeFeet: 180, curveFeet: 120 },
      { lat: 39.72, lng: -104.92, altitudeFeet: 240, curveFeet: 80 },
    ],
    [
      [-104.9, 39.7],
      [-104.905, 39.705],
      [-104.91, 39.71],
      [-104.915, 39.715],
      [-104.92, 39.72],
    ],
  );

  expect(synced.map((waypoint) => Math.round(waypoint.altitudeFeet))).toEqual([120, 150, 180, 210, 240]);
  expect(synced.map((waypoint) => Math.round(waypoint.curveFeet ?? 0))).toEqual([40, 80, 120, 100, 80]);
  expect(synced[0]).toMatchObject({ lng: -104.9, lat: 39.7 });
  expect(synced[4]).toMatchObject({ lng: -104.92, lat: 39.72 });
});

test("buildBatteryPathElevatedFeature emits curved line coordinates and elevation meters", async () => {
  const feature = buildBatteryPathElevatedFeature(
    [
      [-104.9903, 39.7392],
      [-104.9903, 39.7402],
      [-104.9893, 39.7402],
    ],
    [
      { lat: 39.7392, lng: -104.9903, altitudeFeet: 120, curveFeet: 0 },
      { lat: 39.7402, lng: -104.9903, altitudeFeet: 180, curveFeet: 120 },
      { lat: 39.7402, lng: -104.9893, altitudeFeet: 240, curveFeet: 0 },
    ],
  );

  expect(feature.geometry.coordinates.length).toBeGreaterThan(3);
  expect(feature.properties.elevationMeters.length).toBe(feature.geometry.coordinates.length);
  expect(feature.geometry.coordinates[0]).toEqual([-104.9903, 39.7392]);
  expect(feature.geometry.coordinates[feature.geometry.coordinates.length - 1]).toEqual([-104.9893, 39.7402]);
  expect(feature.geometry.coordinates).not.toContainEqual([-104.9903, 39.7402]);
  expect(feature.properties.elevationMeters[0]).toBe(altitudeFeetToMeters(120));
  expect(feature.properties.elevationMeters[feature.properties.elevationMeters.length - 1]).toBe(altitudeFeetToMeters(240));
});

test("buildCurvedBatteryPathPoints bends around the curved waypoint instead of passing through it", async () => {
  const renderedPoints = buildCurvedBatteryPathPoints([
    { lat: 39.7392, lng: -104.9903, altitudeFeet: 120, curveFeet: 0 },
    { lat: 39.7402, lng: -104.9903, altitudeFeet: 180, curveFeet: 140 },
    { lat: 39.7402, lng: -104.9893, altitudeFeet: 240, curveFeet: 0 },
  ]);

  expect(renderedPoints.length).toBeGreaterThan(8);
  expect(renderedPoints[0]).toMatchObject({ lat: 39.7392, lng: -104.9903, altitudeFeet: 120 });
  expect(renderedPoints[renderedPoints.length - 1]).toMatchObject({ lat: 39.7402, lng: -104.9893, altitudeFeet: 240 });

  const touchesCornerWaypoint = renderedPoints.some((point) =>
    Math.abs(point.lat - 39.7402) < 1e-6 && Math.abs(point.lng + 104.9903) < 1e-6,
  );
  expect(touchesCornerWaypoint).toBeFalsy();
});

test("interpolateSegmentAltitudeFeet returns the segment midpoint altitude", async () => {
  const altitudeFeet = interpolateSegmentAltitudeFeet(
    [
      { lat: 39.7392, lng: -104.9903, altitudeFeet: 120, curveFeet: 0 },
      { lat: 39.7395, lng: -104.9898, altitudeFeet: 240, curveFeet: 0 },
    ],
    0,
    0.5,
  );

  expect(altitudeFeet).toBe(180);
});

test("buildLineZOffsetExpression targets the elevation array property", async () => {
  expect(buildLineZOffsetExpression()).toEqual([
    "at-interpolated",
    ["*", ["line-progress"], ["-", ["length", ["get", "elevationMeters"]], 1]],
    ["get", "elevationMeters"],
  ]);
});
