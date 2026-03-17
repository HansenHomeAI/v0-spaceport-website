"use client";

import { latLngToLocalFeet } from "./flightBoundary";

export type BatteryPathWaypoint3D = {
  lat: number;
  lng: number;
  altitudeFeet: number;
};

export type FlightPath3DBatteryScene = {
  batteryIndex: number;
  color: string;
  points: Array<{
    x: number;
    y: number;
    z: number;
    altitudeFeet: number;
  }>;
};

export type FlightPath3DScene = {
  baseAltitudeFeet: number;
  maxAltitudeFeet: number;
  verticalExaggeration: number;
  horizontalExtentFeet: number;
  altitudeRangeFeet: number;
  batteries: FlightPath3DBatteryScene[];
};

type SceneInput = {
  batteryIndex: number;
  color: string;
  waypoints: BatteryPathWaypoint3D[];
};

function splitCsvLine(line: string): string[] {
  return line.split(",").map((value) => value.trim());
}

function resolveColumnIndex(headers: string[], candidates: string[]): number {
  const normalized = headers.map((header) => header.trim().toLowerCase());
  return normalized.findIndex((header) => candidates.includes(header));
}

export function parseBatteryCsvWaypoints(csvText: string): BatteryPathWaypoint3D[] {
  const lines = csvText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length <= 1) {
    return [];
  }

  const headers = splitCsvLine(lines[0]);
  const latitudeIndex = resolveColumnIndex(headers, ["latitude", "lat"]);
  const longitudeIndex = resolveColumnIndex(headers, ["longitude", "lng", "lon"]);
  const altitudeIndex = resolveColumnIndex(headers, ["altitude(ft)", "altitude", "alt"]);

  if (latitudeIndex < 0 || longitudeIndex < 0) {
    return [];
  }

  const waypoints: BatteryPathWaypoint3D[] = [];

  for (let lineIndex = 1; lineIndex < lines.length; lineIndex += 1) {
    const parts = splitCsvLine(lines[lineIndex]);
    const lat = Number.parseFloat(parts[latitudeIndex] ?? "");
    const lng = Number.parseFloat(parts[longitudeIndex] ?? "");
    const altitudeFeet = altitudeIndex >= 0
      ? Number.parseFloat(parts[altitudeIndex] ?? "")
      : 0;

    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      continue;
    }

    waypoints.push({
      lat,
      lng,
      altitudeFeet: Number.isFinite(altitudeFeet) ? altitudeFeet : 0,
    });
  }

  return waypoints;
}

function interpolateAltitude(
  sourceWaypoints: BatteryPathWaypoint3D[],
  targetLength: number,
  targetIndex: number,
): number {
  if (sourceWaypoints.length === 0) {
    return 0;
  }
  if (sourceWaypoints.length === 1 || targetLength <= 1) {
    return sourceWaypoints[0].altitudeFeet;
  }

  const scaledIndex = (targetIndex * (sourceWaypoints.length - 1)) / (targetLength - 1);
  const lowerIndex = Math.floor(scaledIndex);
  const upperIndex = Math.min(sourceWaypoints.length - 1, Math.ceil(scaledIndex));
  const fraction = scaledIndex - lowerIndex;
  const lowerAltitude = sourceWaypoints[lowerIndex].altitudeFeet;
  const upperAltitude = sourceWaypoints[upperIndex].altitudeFeet;

  return lowerAltitude + ((upperAltitude - lowerAltitude) * fraction);
}

export function syncBatteryPathWaypointsWithCoords(
  sourceWaypoints: BatteryPathWaypoint3D[],
  coords: Array<[number, number]>,
): BatteryPathWaypoint3D[] {
  return coords.map(([lng, lat], index) => ({
    lng,
    lat,
    altitudeFeet: interpolateAltitude(sourceWaypoints, coords.length, index),
  }));
}

export function buildFlightPath3DScene(
  batteries: SceneInput[],
  center: { lat: number; lng: number },
): FlightPath3DScene {
  const allWaypoints = batteries.flatMap((battery) => battery.waypoints);
  const altitudeValues = allWaypoints.map((waypoint) => waypoint.altitudeFeet);
  const minAltitudeFeet = altitudeValues.length > 0 ? Math.min(...altitudeValues) : 0;
  const maxAltitudeFeet = altitudeValues.length > 0 ? Math.max(...altitudeValues) : minAltitudeFeet;
  const altitudeRangeFeet = Math.max(0, maxAltitudeFeet - minAltitudeFeet);

  let horizontalExtentFeet = 400;
  batteries.forEach((battery) => {
    battery.waypoints.forEach((waypoint) => {
      const local = latLngToLocalFeet(waypoint.lat, waypoint.lng, center.lat, center.lng);
      horizontalExtentFeet = Math.max(horizontalExtentFeet, Math.abs(local.xFt), Math.abs(local.yFt));
    });
  });

  const verticalExaggeration = altitudeRangeFeet <= 1
    ? 4
    : Math.max(2, Math.min(12, (horizontalExtentFeet * 0.18) / altitudeRangeFeet));
  const elevatedBase = altitudeRangeFeet <= 1 ? 14 : 10;

  return {
    baseAltitudeFeet: minAltitudeFeet,
    maxAltitudeFeet: maxAltitudeFeet,
    verticalExaggeration,
    horizontalExtentFeet,
    altitudeRangeFeet,
    batteries: batteries.map((battery) => ({
      batteryIndex: battery.batteryIndex,
      color: battery.color,
      points: battery.waypoints.map((waypoint) => {
        const local = latLngToLocalFeet(waypoint.lat, waypoint.lng, center.lat, center.lng);
        return {
          x: local.xFt,
          y: local.yFt,
          z: elevatedBase + ((waypoint.altitudeFeet - minAltitudeFeet) * verticalExaggeration),
          altitudeFeet: waypoint.altitudeFeet,
        };
      }),
    })),
  };
}
