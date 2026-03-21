"use client";

import {
  groundFootprint,
  footprintBounds,
  footprintOverlapIou,
} from "./cameraOverlapMath";
import { localFeetToLatLng, latLngToLocalFeet } from "./flightBoundary";

export type SpinPathOverlapConfig = {
  speedFts: number;
  speedMph: number;
  speedEnvLoAglFt: number;
  speedEnvLoMph: number;
  speedEnvHiAglFt: number;
  speedEnvHiMph: number;
  captureSpacingFt: number;
  captureIntervalSeconds: number;
  captureIntervalUnit: "ft" | "s";
  captureDistanceIntervalFt: number;
  captureTimeIntervalSeconds: number;
  yawRateDegPerSec: number;
  captureArcDeg: number;
  maxHeadingDeltaDeg: number;
  defaultPitchDeg: number;
  pitchSequenceNeg: number[];
};

export type RealPathPreviewWaypoint = {
  lat: number;
  lng: number;
  altitudeFeet: number;
  curveFeet: number;
  headingDeg: number;
  gimbalPitchDeg: number;
  distanceFeet: number;
  stageNumber?: number;
  stageSpeedMph?: number;
};

export type RealPathBatteryTelemetry = {
  pathDistanceFeet: number;
  waypointCount: number;
  captureSpacingFeet: number;
  maxHeadingGapFeet: number | null;
  maxHeadingDeltaDeg: number;
  estimatedYawRateDegPerSec: number;
  captureArcDeg: number;
  captureIntervalSeconds: number;
  captureTriggerMode?: "ft" | "s";
  captureDistanceFeet?: number;
  stageCount: number;
  stageWaypointCounts: number[];
  stageAverageAglFeet?: number[];
  stageAverageSpeedMph?: number[];
};

export type RealPathPreviewBattery = {
  batteryIndex: number;
  waypoints: RealPathPreviewWaypoint[];
  telemetry: RealPathBatteryTelemetry;
};

export type RealPathOptimizeResponse = {
  optimizedParams: Record<string, unknown>;
  optimizationInfo?: Record<string, unknown> | null;
  previewPaths: Array<{ batteryIndex: number; coordinates: Array<[number, number]> }>;
  previewBatteries: RealPathPreviewBattery[];
  batterySummaries: Array<RealPathBatteryTelemetry & { batteryIndex: number }>;
  overlapTelemetry: Record<string, unknown>;
};

export type RealPathBatteryExportResponse = {
  batteryIndex: number;
  telemetry: RealPathBatteryTelemetry;
  stages: Array<{
    stageNumber: number;
    filename: string;
    waypointCount: number;
    csvText: string;
    averageAglFeet?: number;
    averageSpeedMph?: number;
  }>;
  previewPath: { batteryIndex: number; coordinates: Array<[number, number]> };
  previewWaypoints: RealPathPreviewWaypoint[];
};

export function buildSpinPathOverlapConfig(input: SpinPathOverlapConfig): SpinPathOverlapConfig {
  return {
    ...input,
    defaultPitchDeg: -Math.abs(input.defaultPitchDeg),
    pitchSequenceNeg: input.pitchSequenceNeg.map((value) => -Math.abs(value)),
  };
}

function computeReference(waypoints: RealPathPreviewWaypoint[]): { lat: number; lng: number } {
  if (waypoints.length === 0) {
    return { lat: 0, lng: 0 };
  }

  const totals = waypoints.reduce((accumulator, waypoint) => ({
    lat: accumulator.lat + waypoint.lat,
    lng: accumulator.lng + waypoint.lng,
  }), { lat: 0, lng: 0 });

  return {
    lat: totals.lat / waypoints.length,
    lng: totals.lng / waypoints.length,
  };
}

export function averageRealPathOverlapIou(waypoints: RealPathPreviewWaypoint[]): number {
  if (waypoints.length < 2) {
    return 0;
  }

  const reference = computeReference(waypoints);
  let overlapSum = 0;

  for (let index = 0; index < waypoints.length - 1; index += 1) {
    const waypointA = waypoints[index];
    const waypointB = waypoints[index + 1];
    const pointA = latLngToLocalFeet(waypointA.lat, waypointA.lng, reference.lat, reference.lng);
    const pointB = latLngToLocalFeet(waypointB.lat, waypointB.lng, reference.lat, reference.lng);
    const footprintA = groundFootprint(
      pointA.xFt,
      Math.max(1, waypointA.altitudeFeet),
      Math.abs(waypointA.gimbalPitchDeg),
      waypointA.headingDeg,
    ).map(([x, y]) => [x, y + pointA.yFt, 0]) as ReturnType<typeof groundFootprint>;
    const footprintB = groundFootprint(
      pointB.xFt,
      Math.max(1, waypointB.altitudeFeet),
      Math.abs(waypointB.gimbalPitchDeg),
      waypointB.headingDeg,
    ).map(([x, y]) => [x, y + pointB.yFt, 0]) as ReturnType<typeof groundFootprint>;
    overlapSum += footprintOverlapIou(footprintBounds(footprintA), footprintBounds(footprintB));
  }

  return overlapSum / (waypoints.length - 1);
}

function selectFootprintIndexes(total: number, limit: number): number[] {
  if (total <= 0 || limit <= 0) {
    return [];
  }
  if (total <= limit) {
    return Array.from({ length: total }, (_, index) => index);
  }
  return Array.from({ length: limit }, (_, index) => Math.round((index * (total - 1)) / (limit - 1)));
}

export function buildRealPathFootprintFeatureCollection(
  waypoints: RealPathPreviewWaypoint[],
  maxFootprints = 10,
): GeoJSON.FeatureCollection<GeoJSON.Polygon> {
  const reference = computeReference(waypoints);
  const indexes = selectFootprintIndexes(waypoints.length, maxFootprints);

  return {
    type: "FeatureCollection",
    features: indexes.map((waypointIndex) => {
      const waypoint = waypoints[waypointIndex];
      const localPoint = latLngToLocalFeet(waypoint.lat, waypoint.lng, reference.lat, reference.lng);
      const footprint = groundFootprint(
        localPoint.xFt,
        Math.max(1, waypoint.altitudeFeet),
        Math.abs(waypoint.gimbalPitchDeg),
        waypoint.headingDeg,
      );

      const coordinates = footprint.map(([x, y]) => {
        const latLng = localFeetToLatLng(x, y + localPoint.yFt, reference.lat, reference.lng);
        return [latLng.lng, latLng.lat] as [number, number];
      });
      coordinates.push(coordinates[0]);

      return {
        type: "Feature",
        properties: {
          waypointIndex,
        },
        geometry: {
          type: "Polygon",
          coordinates: [coordinates],
        },
      };
    }),
  };
}
