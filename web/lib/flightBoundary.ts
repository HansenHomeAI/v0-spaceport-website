"use client";

export type BoundaryEllipse = {
  version: 1;
  enabled: boolean;
  centerLat: number;
  centerLng: number;
  majorRadiusFt: number;
  minorRadiusFt: number;
  rotationDeg: number;
};

export type BoundaryBatteryPlan = {
  batteryIndex: number;
  startAngleDeg: number;
  sweepAngleDeg: number;
  bounceCount: number;
  estimatedTimeMinutes: number;
  waypointCount: number;
  coverageShare: number;
  fitStatus: "full" | "best_effort";
};

export type BoundaryPlan = {
  version: 1;
  fitStatus: "full" | "best_effort";
  coverageRatio: number;
  limitingBatteryIndex: number | null;
  batteries: BoundaryBatteryPlan[];
};

export type BoundaryPreviewPath = {
  batteryIndex: number;
  coordinates: Array<[number, number]>;
};

export type BoundaryOptimizationResponse = {
  boundary: BoundaryEllipse;
  boundaryPlan: BoundaryPlan;
  previewPaths: BoundaryPreviewPath[];
  toastMessage?: string | null;
};

type LocalPoint = {
  xFt: number;
  yFt: number;
};

const EARTH_RADIUS_METERS = 6378137;
const FEET_TO_METERS = 0.3048;
const MIN_BOUNDARY_RADIUS_FT = 150;

export function normalizeRotationDeg(rotationDeg: number): number {
  const normalized = rotationDeg % 360;
  return normalized >= 0 ? normalized : normalized + 360;
}

export function normalizeBoundary(boundary: BoundaryEllipse): BoundaryEllipse {
  const majorRadiusFt = Math.max(MIN_BOUNDARY_RADIUS_FT, boundary.majorRadiusFt || MIN_BOUNDARY_RADIUS_FT);
  const minorRadiusFt = Math.min(
    majorRadiusFt,
    Math.max(MIN_BOUNDARY_RADIUS_FT, boundary.minorRadiusFt || MIN_BOUNDARY_RADIUS_FT)
  );

  return {
    ...boundary,
    majorRadiusFt,
    minorRadiusFt,
    rotationDeg: normalizeRotationDeg(boundary.rotationDeg || 0),
  };
}

export function rotatePoint(point: LocalPoint, rotationDeg: number): LocalPoint {
  const theta = (normalizeRotationDeg(rotationDeg) * Math.PI) / 180;
  const cosTheta = Math.cos(theta);
  const sinTheta = Math.sin(theta);
  return {
    xFt: point.xFt * cosTheta - point.yFt * sinTheta,
    yFt: point.xFt * sinTheta + point.yFt * cosTheta,
  };
}

export function localFeetToLatLng(
  xFt: number,
  yFt: number,
  centerLat: number,
  centerLng: number
): { lat: number; lng: number } {
  const xMeters = xFt * FEET_TO_METERS;
  const yMeters = yFt * FEET_TO_METERS;

  const dLat = yMeters / EARTH_RADIUS_METERS;
  const dLng = xMeters / (EARTH_RADIUS_METERS * Math.cos((centerLat * Math.PI) / 180));

  return {
    lat: centerLat + (dLat * 180) / Math.PI,
    lng: centerLng + (dLng * 180) / Math.PI,
  };
}

export function latLngToLocalFeet(
  lat: number,
  lng: number,
  centerLat: number,
  centerLng: number
): LocalPoint {
  const dLat = ((lat - centerLat) * Math.PI) / 180;
  const dLng = ((lng - centerLng) * Math.PI) / 180;

  const yMeters = dLat * EARTH_RADIUS_METERS;
  const xMeters = dLng * EARTH_RADIUS_METERS * Math.cos((centerLat * Math.PI) / 180);

  return {
    xFt: xMeters / FEET_TO_METERS,
    yFt: yMeters / FEET_TO_METERS,
  };
}

export function boundaryHandlePositions(boundary: BoundaryEllipse): {
  center: { lat: number; lng: number };
  major: { lat: number; lng: number };
  minor: { lat: number; lng: number };
} {
  const normalized = normalizeBoundary(boundary);
  const majorLocal = rotatePoint({ xFt: normalized.majorRadiusFt, yFt: 0 }, normalized.rotationDeg);
  const minorLocal = rotatePoint({ xFt: 0, yFt: normalized.minorRadiusFt }, normalized.rotationDeg);

  return {
    center: { lat: normalized.centerLat, lng: normalized.centerLng },
    major: localFeetToLatLng(majorLocal.xFt, majorLocal.yFt, normalized.centerLat, normalized.centerLng),
    minor: localFeetToLatLng(minorLocal.xFt, minorLocal.yFt, normalized.centerLat, normalized.centerLng),
  };
}

export function buildEllipseOutlineCoordinates(
  boundary: BoundaryEllipse,
  points: number = 120
): Array<[number, number]> {
  const normalized = normalizeBoundary(boundary);
  const coordinates: Array<[number, number]> = [];

  for (let index = 0; index <= points; index += 1) {
    const angle = (index / points) * Math.PI * 2;
    const rotated = rotatePoint(
      {
        xFt: normalized.majorRadiusFt * Math.cos(angle),
        yFt: normalized.minorRadiusFt * Math.sin(angle),
      },
      normalized.rotationDeg
    );
    const { lat, lng } = localFeetToLatLng(rotated.xFt, rotated.yFt, normalized.centerLat, normalized.centerLng);
    coordinates.push([lng, lat]);
  }

  return coordinates;
}

export function buildBoundaryGuideCoordinates(boundary: BoundaryEllipse): {
  major: Array<[number, number]>;
  minor: Array<[number, number]>;
} {
  const normalized = normalizeBoundary(boundary);
  const handles = boundaryHandlePositions(normalized);
  const oppositeMajor = rotatePoint({ xFt: -normalized.majorRadiusFt, yFt: 0 }, normalized.rotationDeg);
  const oppositeMinor = rotatePoint({ xFt: 0, yFt: -normalized.minorRadiusFt }, normalized.rotationDeg);
  const majorTail = localFeetToLatLng(oppositeMajor.xFt, oppositeMajor.yFt, normalized.centerLat, normalized.centerLng);
  const minorTail = localFeetToLatLng(oppositeMinor.xFt, oppositeMinor.yFt, normalized.centerLat, normalized.centerLng);

  return {
    major: [
      [majorTail.lng, majorTail.lat],
      [normalized.centerLng, normalized.centerLat],
      [handles.major.lng, handles.major.lat],
    ],
    minor: [
      [minorTail.lng, minorTail.lat],
      [normalized.centerLng, normalized.centerLat],
      [handles.minor.lng, handles.minor.lat],
    ],
  };
}

export function computeAutoFitCircle(
  coordinates: Array<[number, number]>,
  centerLat: number,
  centerLng: number,
  paddingRatio: number = 1.05
): BoundaryEllipse {
  const maxRadiusFt = coordinates.reduce((maxRadius, [lng, lat]) => {
    const local = latLngToLocalFeet(lat, lng, centerLat, centerLng);
    const distance = Math.hypot(local.xFt, local.yFt);
    return Math.max(maxRadius, distance);
  }, MIN_BOUNDARY_RADIUS_FT);

  const radius = Math.max(MIN_BOUNDARY_RADIUS_FT, maxRadiusFt * paddingRatio);

  return {
    version: 1,
    enabled: true,
    centerLat,
    centerLng,
    majorRadiusFt: radius,
    minorRadiusFt: radius,
    rotationDeg: 0,
  };
}

export function isPointInsideBoundary(
  lat: number,
  lng: number,
  boundary: BoundaryEllipse,
  paddingRatio: number = 1
): boolean {
  const normalized = normalizeBoundary(boundary);
  const local = latLngToLocalFeet(lat, lng, normalized.centerLat, normalized.centerLng);
  const unrotated = rotatePoint(local, -normalized.rotationDeg);
  const major = normalized.majorRadiusFt * paddingRatio;
  const minor = normalized.minorRadiusFt * paddingRatio;
  const value = (unrotated.xFt * unrotated.xFt) / (major * major) + (unrotated.yFt * unrotated.yFt) / (minor * minor);
  return value <= 1.00001;
}
