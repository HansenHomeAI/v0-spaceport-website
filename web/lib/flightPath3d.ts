"use client";

export type BatteryPathWaypoint3D = {
  lat: number;
  lng: number;
  altitudeFeet: number;
};

export type BatteryPathElevatedFeature = {
  type: "Feature";
  properties: {
    elevationMeters: number[];
  };
  geometry: {
    type: "LineString";
    coordinates: Array<[number, number]>;
  };
};

export const FEET_TO_METERS = 0.3048;

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

export function altitudeFeetToMeters(altitudeFeet: number): number {
  return altitudeFeet * FEET_TO_METERS;
}

export function getWaypointAltitudeFeet(
  waypoints: BatteryPathWaypoint3D[],
  waypointIndex: number,
): number {
  const waypoint = waypoints[waypointIndex];
  if (!waypoint) {
    return 0;
  }

  return Number.isFinite(waypoint.altitudeFeet) ? waypoint.altitudeFeet : 0;
}

export function interpolateSegmentAltitudeFeet(
  waypoints: BatteryPathWaypoint3D[],
  segmentIndex: number,
  segmentProgress: number,
): number {
  const lowerAltitude = getWaypointAltitudeFeet(waypoints, segmentIndex);
  const upperAltitude = getWaypointAltitudeFeet(waypoints, segmentIndex + 1);
  return lowerAltitude + ((upperAltitude - lowerAltitude) * segmentProgress);
}

export function buildBatteryPathElevatedFeature(
  coords: Array<[number, number]>,
  sourceWaypoints: BatteryPathWaypoint3D[],
): BatteryPathElevatedFeature {
  const syncedWaypoints = sourceWaypoints.length > 0
    ? syncBatteryPathWaypointsWithCoords(sourceWaypoints, coords)
    : coords.map(([lng, lat]) => ({ lng, lat, altitudeFeet: 0 }));

  return {
    type: "Feature",
    properties: {
      elevationMeters: syncedWaypoints.map((waypoint) => altitudeFeetToMeters(waypoint.altitudeFeet)),
    },
    geometry: {
      type: "LineString",
      coordinates: coords,
    },
  };
}

export function buildLineZOffsetExpression(propertyName = "elevationMeters"): any[] {
  return [
    "at-interpolated",
    [
      "*",
      ["line-progress"],
      ["-", ["length", ["get", propertyName]], 1],
    ],
    ["get", propertyName],
  ];
}
