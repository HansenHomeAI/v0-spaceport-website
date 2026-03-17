import { expect, test } from "@playwright/test";
import {
  buildFlightPath3DScene,
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

test("buildFlightPath3DScene converts lat lng into elevated local points", async () => {
  const scene = buildFlightPath3DScene(
    [
      {
        batteryIndex: 1,
        color: "#ff6b6b",
        waypoints: [
          { lat: 39.7392, lng: -104.9903, altitudeFeet: 120 },
          { lat: 39.7395, lng: -104.9898, altitudeFeet: 240 },
        ],
      },
    ],
    { lat: 39.7392, lng: -104.9903 },
  );

  expect(scene.batteries).toHaveLength(1);
  expect(scene.batteries[0].points).toHaveLength(2);
  expect(scene.batteries[0].points[0].x).toBeCloseTo(0, 4);
  expect(scene.batteries[0].points[0].y).toBeCloseTo(0, 4);
  expect(scene.batteries[0].points[1].z).toBeGreaterThan(scene.batteries[0].points[0].z);
  expect(scene.verticalExaggeration).toBeGreaterThanOrEqual(2);
});
