import { expect, test } from "@playwright/test";
import {
  altitudeFeetToMeters,
  buildBatteryPathElevatedFeature,
  buildLineZOffsetExpression,
  interpolateSegmentAltitudeFeet,
  parseBatteryCsvWaypoints,
  syncBatteryPathWaypointsWithCoords,
} from "../../web/lib/flightPath3d";

test("parseBatteryCsvWaypoints reads latitude longitude and altitude columns", async () => {
  const csv = [
    "latitude,longitude,altitude(ft),speed(m/s)",
    "39.70000000,-104.90000000,120,8.85",
    "39.71000000,-104.91000000,180,8.85",
    "39.72000000,-104.92000000,240,8.85",
  ].join("\n");

  const waypoints = parseBatteryCsvWaypoints(csv);

  expect(waypoints).toEqual([
    { lat: 39.7, lng: -104.9, altitudeFeet: 120 },
    { lat: 39.71, lng: -104.91, altitudeFeet: 180 },
    { lat: 39.72, lng: -104.92, altitudeFeet: 240 },
  ]);
});

test("syncBatteryPathWaypointsWithCoords preserves end altitudes and interpolates inserts", async () => {
  const synced = syncBatteryPathWaypointsWithCoords(
    [
      { lat: 39.7, lng: -104.9, altitudeFeet: 120 },
      { lat: 39.71, lng: -104.91, altitudeFeet: 180 },
      { lat: 39.72, lng: -104.92, altitudeFeet: 240 },
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
  expect(synced[0]).toMatchObject({ lng: -104.9, lat: 39.7 });
  expect(synced[4]).toMatchObject({ lng: -104.92, lat: 39.72 });
});

test("buildBatteryPathElevatedFeature emits line coordinates and elevation meters", async () => {
  const feature = buildBatteryPathElevatedFeature(
    [
      [-104.9903, 39.7392],
      [-104.9898, 39.7395],
      [-104.9892, 39.7397],
    ],
    [
      { lat: 39.7392, lng: -104.9903, altitudeFeet: 120 },
      { lat: 39.7395, lng: -104.9898, altitudeFeet: 180 },
      { lat: 39.7397, lng: -104.9892, altitudeFeet: 240 },
    ],
  );

  expect(feature.geometry.coordinates).toEqual([
    [-104.9903, 39.7392],
    [-104.9898, 39.7395],
    [-104.9892, 39.7397],
  ]);
  expect(feature.properties.elevationMeters).toEqual([
    altitudeFeetToMeters(120),
    altitudeFeetToMeters(180),
    altitudeFeetToMeters(240),
  ]);
});

test("interpolateSegmentAltitudeFeet returns the segment midpoint altitude", async () => {
  const altitudeFeet = interpolateSegmentAltitudeFeet(
    [
      { lat: 39.7392, lng: -104.9903, altitudeFeet: 120 },
      { lat: 39.7395, lng: -104.9898, altitudeFeet: 240 },
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
