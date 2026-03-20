"use client";

import { latLngToLocalFeet, localFeetToLatLng } from "./flightBoundary";

export type BatteryPathWaypoint3D = {
  lat: number;
  lng: number;
  altitudeFeet: number;
  curveFeet?: number;
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

type LocalBatteryPathPoint = {
  xFt: number;
  yFt: number;
  altitudeFeet: number;
  curveFeet: number;
};

export type BatteryPathRenderedPoint = {
  lat: number;
  lng: number;
  altitudeFeet: number;
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
  const curveIndex = resolveColumnIndex(headers, ["curvesize(ft)", "curvesize", "curve"]);

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
    const curveFeet = curveIndex >= 0
      ? Number.parseFloat(parts[curveIndex] ?? "")
      : 0;

    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      continue;
    }

    waypoints.push({
      lat,
      lng,
      altitudeFeet: Number.isFinite(altitudeFeet) ? altitudeFeet : 0,
      curveFeet: Number.isFinite(curveFeet) ? curveFeet : 0,
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

function interpolateCurveFeet(
  sourceWaypoints: BatteryPathWaypoint3D[],
  targetLength: number,
  targetIndex: number,
): number {
  if (sourceWaypoints.length === 0) {
    return 0;
  }
  if (sourceWaypoints.length === 1 || targetLength <= 1) {
    return Number.isFinite(sourceWaypoints[0]?.curveFeet) ? sourceWaypoints[0].curveFeet! : 0;
  }

  const scaledIndex = (targetIndex * (sourceWaypoints.length - 1)) / (targetLength - 1);
  const lowerIndex = Math.floor(scaledIndex);
  const upperIndex = Math.min(sourceWaypoints.length - 1, Math.ceil(scaledIndex));
  const fraction = scaledIndex - lowerIndex;
  const lowerCurveFeet = Number.isFinite(sourceWaypoints[lowerIndex]?.curveFeet) ? sourceWaypoints[lowerIndex].curveFeet! : 0;
  const upperCurveFeet = Number.isFinite(sourceWaypoints[upperIndex]?.curveFeet) ? sourceWaypoints[upperIndex].curveFeet! : 0;

  return lowerCurveFeet + ((upperCurveFeet - lowerCurveFeet) * fraction);
}

export function syncBatteryPathWaypointsWithCoords(
  sourceWaypoints: BatteryPathWaypoint3D[],
  coords: Array<[number, number]>,
): BatteryPathWaypoint3D[] {
  return coords.map(([lng, lat], index) => ({
    lng,
    lat,
    altitudeFeet: interpolateAltitude(sourceWaypoints, coords.length, index),
    curveFeet: interpolateCurveFeet(sourceWaypoints, coords.length, index),
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

export function getWaypointCurveFeet(
  waypoints: BatteryPathWaypoint3D[],
  waypointIndex: number,
): number {
  const waypoint = waypoints[waypointIndex];
  if (!waypoint) {
    return 0;
  }

  return Number.isFinite(waypoint.curveFeet) ? waypoint.curveFeet! : 0;
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

function computePathReference(waypoints: BatteryPathWaypoint3D[]): { lat: number; lng: number } {
  if (waypoints.length === 0) {
    return { lat: 0, lng: 0 };
  }

  const totals = waypoints.reduce(
    (accumulator, waypoint) => ({
      lat: accumulator.lat + waypoint.lat,
      lng: accumulator.lng + waypoint.lng,
    }),
    { lat: 0, lng: 0 },
  );

  return {
    lat: totals.lat / waypoints.length,
    lng: totals.lng / waypoints.length,
  };
}

function appendRenderedPoint(points: LocalBatteryPathPoint[], point: LocalBatteryPathPoint) {
  const previous = points[points.length - 1];
  if (
    previous &&
    Math.abs(previous.xFt - point.xFt) < 1e-6 &&
    Math.abs(previous.yFt - point.yFt) < 1e-6 &&
    Math.abs(previous.altitudeFeet - point.altitudeFeet) < 1e-6
  ) {
    return;
  }

  points.push(point);
}

function appendLinearSegment(
  points: LocalBatteryPathPoint[],
  start: LocalBatteryPathPoint,
  end: LocalBatteryPathPoint,
) {
  const distanceFt = Math.hypot(end.xFt - start.xFt, end.yFt - start.yFt);
  const steps = Math.max(2, Math.ceil(distanceFt / 60));

  for (let index = 1; index <= steps; index += 1) {
    const t = index / steps;
    appendRenderedPoint(points, {
      xFt: start.xFt + ((end.xFt - start.xFt) * t),
      yFt: start.yFt + ((end.yFt - start.yFt) * t),
      altitudeFeet: start.altitudeFeet + ((end.altitudeFeet - start.altitudeFeet) * t),
      curveFeet: 0,
    });
  }
}

export function buildCurvedBatteryPathPoints(
  waypoints: BatteryPathWaypoint3D[],
): BatteryPathRenderedPoint[] {
  if (waypoints.length === 0) {
    return [];
  }
  if (waypoints.length === 1) {
    return [{
      lat: waypoints[0].lat,
      lng: waypoints[0].lng,
      altitudeFeet: waypoints[0].altitudeFeet,
    }];
  }

  const reference = computePathReference(waypoints);
  const localWaypoints: LocalBatteryPathPoint[] = waypoints.map((waypoint) => {
    const localPoint = latLngToLocalFeet(waypoint.lat, waypoint.lng, reference.lat, reference.lng);
    return {
      xFt: localPoint.xFt,
      yFt: localPoint.yFt,
      altitudeFeet: waypoint.altitudeFeet,
      curveFeet: Math.max(0, getWaypointCurveFeet([waypoint], 0)),
    };
  });

  const renderedPoints: LocalBatteryPathPoint[] = [];
  let lastPoint = { ...localWaypoints[0] };
  appendRenderedPoint(renderedPoints, lastPoint);

  for (let waypointIndex = 1; waypointIndex < localWaypoints.length - 1; waypointIndex += 1) {
    const previousWaypoint = localWaypoints[waypointIndex - 1];
    const currentWaypoint = localWaypoints[waypointIndex];
    const nextWaypoint = localWaypoints[waypointIndex + 1];

    const incomingDx = currentWaypoint.xFt - previousWaypoint.xFt;
    const incomingDy = currentWaypoint.yFt - previousWaypoint.yFt;
    const outgoingDx = nextWaypoint.xFt - currentWaypoint.xFt;
    const outgoingDy = nextWaypoint.yFt - currentWaypoint.yFt;

    const incomingLength = Math.hypot(incomingDx, incomingDy);
    const outgoingLength = Math.hypot(outgoingDx, outgoingDy);

    if (incomingLength < 1e-3 || outgoingLength < 1e-3) {
      appendLinearSegment(renderedPoints, lastPoint, currentWaypoint);
      lastPoint = { ...currentWaypoint };
      continue;
    }

    const incomingUnitX = incomingDx / incomingLength;
    const incomingUnitY = incomingDy / incomingLength;
    const outgoingUnitX = outgoingDx / outgoingLength;
    const outgoingUnitY = outgoingDy / outgoingLength;

    const clampedCosine = Math.max(
      -1,
      Math.min(1, (incomingUnitX * outgoingUnitX) + (incomingUnitY * outgoingUnitY)),
    );
    const turnAngle = Math.acos(clampedCosine);

    if (!Number.isFinite(turnAngle) || turnAngle < 1e-3 || Math.abs(Math.PI - turnAngle) < 1e-3) {
      appendLinearSegment(renderedPoints, lastPoint, currentWaypoint);
      lastPoint = { ...currentWaypoint };
      continue;
    }

    const requestedRadiusFt = Math.max(0, currentWaypoint.curveFeet);
    const tangentScale = Math.tan(turnAngle / 2);
    if (requestedRadiusFt < 1e-3 || tangentScale < 1e-6) {
      appendLinearSegment(renderedPoints, lastPoint, currentWaypoint);
      lastPoint = { ...currentWaypoint };
      continue;
    }

    const maxTangentDistance = Math.min(incomingLength, outgoingLength) * 0.49;
    const tangentDistance = Math.min(requestedRadiusFt * tangentScale, maxTangentDistance);
    if (tangentDistance < 1e-3) {
      appendLinearSegment(renderedPoints, lastPoint, currentWaypoint);
      lastPoint = { ...currentWaypoint };
      continue;
    }

    const effectiveRadiusFt = tangentDistance / tangentScale;
    const tangentStart: LocalBatteryPathPoint = {
      xFt: currentWaypoint.xFt - (incomingUnitX * tangentDistance),
      yFt: currentWaypoint.yFt - (incomingUnitY * tangentDistance),
      altitudeFeet: currentWaypoint.altitudeFeet
        - ((currentWaypoint.altitudeFeet - previousWaypoint.altitudeFeet) * (tangentDistance / incomingLength)),
      curveFeet: 0,
    };
    const tangentEnd: LocalBatteryPathPoint = {
      xFt: currentWaypoint.xFt + (outgoingUnitX * tangentDistance),
      yFt: currentWaypoint.yFt + (outgoingUnitY * tangentDistance),
      altitudeFeet: currentWaypoint.altitudeFeet
        + ((nextWaypoint.altitudeFeet - currentWaypoint.altitudeFeet) * (tangentDistance / outgoingLength)),
      curveFeet: 0,
    };

    const inwardIncomingX = -incomingUnitX;
    const inwardIncomingY = -incomingUnitY;
    const bisectorX = inwardIncomingX + outgoingUnitX;
    const bisectorY = inwardIncomingY + outgoingUnitY;
    const bisectorLength = Math.hypot(bisectorX, bisectorY);

    if (bisectorLength < 1e-6) {
      appendLinearSegment(renderedPoints, lastPoint, currentWaypoint);
      lastPoint = { ...currentWaypoint };
      continue;
    }

    const centerDistanceFt = effectiveRadiusFt / Math.sin(turnAngle / 2);
    const centerX = currentWaypoint.xFt + ((bisectorX / bisectorLength) * centerDistanceFt);
    const centerY = currentWaypoint.yFt + ((bisectorY / bisectorLength) * centerDistanceFt);

    const startAngle = Math.atan2(tangentStart.yFt - centerY, tangentStart.xFt - centerX);
    let endAngle = Math.atan2(tangentEnd.yFt - centerY, tangentEnd.xFt - centerX);
    const turnCross = (inwardIncomingX * outgoingUnitY) - (inwardIncomingY * outgoingUnitX);

    let normalizedStartAngle = startAngle;
    if (turnCross > 0) {
      if (endAngle < normalizedStartAngle) {
        endAngle += 2 * Math.PI;
      }
    } else if (turnCross < 0) {
      if (endAngle > normalizedStartAngle) {
        endAngle -= 2 * Math.PI;
      }
    } else {
      appendLinearSegment(renderedPoints, lastPoint, currentWaypoint);
      lastPoint = { ...currentWaypoint };
      continue;
    }

    appendLinearSegment(renderedPoints, lastPoint, tangentStart);

    const arcLengthFt = Math.abs(endAngle - normalizedStartAngle) * effectiveRadiusFt;
    const arcSteps = Math.max(8, Math.ceil(arcLengthFt / 30));
    for (let step = 1; step <= arcSteps; step += 1) {
      const t = step / arcSteps;
      const angle = normalizedStartAngle + ((endAngle - normalizedStartAngle) * t);
      appendRenderedPoint(renderedPoints, {
        xFt: centerX + (effectiveRadiusFt * Math.cos(angle)),
        yFt: centerY + (effectiveRadiusFt * Math.sin(angle)),
        altitudeFeet: tangentStart.altitudeFeet + ((tangentEnd.altitudeFeet - tangentStart.altitudeFeet) * t),
        curveFeet: 0,
      });
    }

    lastPoint = { ...tangentEnd };
  }

  appendLinearSegment(renderedPoints, lastPoint, localWaypoints[localWaypoints.length - 1]);

  return renderedPoints.map((point) => {
    const latLng = localFeetToLatLng(point.xFt, point.yFt, reference.lat, reference.lng);
    return {
      lat: latLng.lat,
      lng: latLng.lng,
      altitudeFeet: point.altitudeFeet,
    };
  });
}

export function buildBatteryPathElevatedFeature(
  coords: Array<[number, number]>,
  sourceWaypoints: BatteryPathWaypoint3D[],
): BatteryPathElevatedFeature {
  const syncedWaypoints = sourceWaypoints.length > 0
    ? syncBatteryPathWaypointsWithCoords(sourceWaypoints, coords)
    : coords.map(([lng, lat]) => ({ lng, lat, altitudeFeet: 0, curveFeet: 0 }));
  const renderedPoints = buildCurvedBatteryPathPoints(syncedWaypoints);

  return {
    type: "Feature",
    properties: {
      elevationMeters: renderedPoints.map((waypoint) => altitudeFeetToMeters(waypoint.altitudeFeet)),
    },
    geometry: {
      type: "LineString",
      coordinates: renderedPoints.map((waypoint) => [waypoint.lng, waypoint.lat]),
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
