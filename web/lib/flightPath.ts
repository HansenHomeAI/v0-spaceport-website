import Papa from 'papaparse';

type RawRow = Record<string, unknown>;

export interface FlightWaypoint {
  latitude: number;
  longitude: number;
  altitudeFt: number;
  altitudeMeters: number;
  headingDeg: number;
  curveSizeFt: number;
  curveSizeMeters: number;
  rotationDir: number;
  gimbalMode: number;
  gimbalPitchAngle: number;
  altitudeMode: number;
  speedMs: number;
  poiLatitude?: number | null;
  poiLongitude?: number | null;
  poiAltitudeFt?: number | null;
  poiAltitudeMeters?: number | null;
  poiAltitudeMode?: number | null;
  photoTimeInterval?: number | null;
  photoDistInterval?: number | null;
}

export interface FlightWaypointRuntime extends FlightWaypoint {
  index: number;
  cumulativeDistanceMeters: number;
  cumulativeDistanceMeters3d: number;
  horizontalDistanceFromPrevMeters: number;
  verticalDeltaFromPrevMeters: number;
  slopePercentFromPrev: number | null;
  slopeDegreesFromPrev: number | null;
  headingChangeFromPrevDeg: number | null;
}

export interface FlightSegment {
  index: number;
  start: FlightWaypointRuntime;
  end: FlightWaypointRuntime;
  horizontalDistanceMeters: number;
  verticalGainMeters: number;
  slopePercent: number | null;
  slopeDegrees: number | null;
  curvatureInverseMeters: number | null;
}

export interface FlightPoi {
  latitude: number;
  longitude: number;
  altitudeFt: number;
  altitudeMeters: number;
  altitudeMode: number;
}

export interface MapBoundsLiteral {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface FlightPathStats {
  totalWaypoints: number;
  totalHorizontalDistanceMeters: number;
  total3dDistanceMeters: number;
  totalVerticalGainMeters: number;
  totalVerticalDropMeters: number;
  minAltitudeFt: number;
  maxAltitudeFt: number;
  minCurveSizeFt: number | null;
  maxCurveSizeFt: number | null;
  tightestCurveRadiusMeters: number | null;
  averageSpeedMs: number | null;
  averageSpeedMph: number | null;
  estimatedDurationSeconds: number | null;
  maxSlopePercent: number | null;
  maxSlopeDegrees: number | null;
  averageSlopePercent: number | null;
}

export interface FlightPathAnalysis {
  waypoints: FlightWaypointRuntime[];
  segments: FlightSegment[];
  stats: FlightPathStats;
  poi: FlightPoi | null;
  center: { lat: number; lng: number; altitudeMeters: number } | null;
  bounds: MapBoundsLiteral | null;
  warnings: string[];
}

const FEET_TO_METERS = 0.3048;
const EARTH_RADIUS_METERS = 6_371_000;

const HEADER_TRANSFORM = (header: string): string => {
  return header
    .trim()
    .toLowerCase()
    .replace(/[()]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '');
};

const toNumber = (value: unknown): number | null => {
  if (value === null || value === undefined) return null;
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const feetToMeters = (feet: number | null): number | null => {
  if (feet === null) return null;
  return feet * FEET_TO_METERS;
};

const normalizeHeadingDelta = (previous: number, next: number): number => {
  let delta = next - previous;
  while (delta > 180) delta -= 360;
  while (delta < -180) delta += 360;
  return delta;
};

const haversineDistanceMeters = (
  a: { latitude: number; longitude: number },
  b: { latitude: number; longitude: number }
): number => {
  const dLat = degreesToRadians(b.latitude - a.latitude);
  const dLon = degreesToRadians(b.longitude - a.longitude);
  const lat1 = degreesToRadians(a.latitude);
  const lat2 = degreesToRadians(b.latitude);

  const sinLat = Math.sin(dLat / 2);
  const sinLon = Math.sin(dLon / 2);

  const h = sinLat * sinLat + Math.cos(lat1) * Math.cos(lat2) * sinLon * sinLon;
  const c = 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
  return EARTH_RADIUS_METERS * c;
};

const degreesToRadians = (degrees: number): number => (degrees * Math.PI) / 180;

const radiansToDegrees = (radians: number): number => (radians * 180) / Math.PI;

export interface ParseFlightCsvOptions {
  /** Warn when curve size is smaller than this many feet */
  minimumCurveSizeFt?: number;
}

export function parseFlightCsv(
  content: string,
  options: ParseFlightCsvOptions = {}
): FlightPathAnalysis {
  const warnings: string[] = [];
  const minimumCurveSizeFt = options.minimumCurveSizeFt ?? 20;

  const parsed = Papa.parse<RawRow>(content, {
    header: true,
    skipEmptyLines: 'greedy',
    dynamicTyping: true,
    transformHeader: HEADER_TRANSFORM,
  });

  if (parsed.errors.length > 0) {
    parsed.errors.forEach((err) => {
      warnings.push(`Row ${err.row ?? 'unknown'}: ${err.message}`);
    });
  }

  const waypoints: FlightWaypointRuntime[] = [];
  const segments: FlightSegment[] = [];

  let cumulativeDistanceMeters = 0;
  let cumulativeDistanceMeters3d = 0;
  let totalVerticalGain = 0;
  let totalVerticalDrop = 0;
  let speedAccumulator = 0;
  let speedSamples = 0;
  let slopeAccumulator = 0;
  let slopeSamples = 0;

  let maxSlopePercent: number | null = null;
  let maxSlopeDegrees: number | null = null;

  let minAltitudeFt = Number.POSITIVE_INFINITY;
  let maxAltitudeFt = Number.NEGATIVE_INFINITY;
  let minCurveSizeFt: number | null = null;
  let maxCurveSizeFt: number | null = null;
  let tightestCurveMeters: number | null = null;

  let latSum = 0;
  let lonSum = 0;
  let altitudeSumMeters = 0;

  let bounds: MapBoundsLiteral | null = null;

  let previousWaypoint: FlightWaypointRuntime | null = null;

  let poi: FlightPoi | null = null;

  parsed.data.forEach((raw, rowIndex) => {
    const latitude = toNumber(raw.latitude);
    const longitude = toNumber(raw.longitude);
    const altitudeFt = toNumber(raw.altitude_ft);

    if (
      latitude === null ||
      longitude === null ||
      altitudeFt === null ||
      Number.isNaN(latitude) ||
      Number.isNaN(longitude) ||
      Number.isNaN(altitudeFt)
    ) {
      warnings.push(`Row ${rowIndex + 2}: skipped due to missing coordinates or altitude.`);
      return;
    }

    const altitudeMeters = feetToMeters(altitudeFt)!;
    const headingDeg = toNumber(raw.heading_deg) ?? 0;
    const curveSizeFt = Math.max(toNumber(raw.curvesize_ft) ?? 0, 0);
    const curveSizeMeters = feetToMeters(curveSizeFt) ?? 0;
    const rotationDir = toNumber(raw.rotationdir) ?? 0;
    const gimbalMode = toNumber(raw.gimbalmode) ?? 0;
    const gimbalPitchAngle = toNumber(raw.gimbalpitchangle) ?? 0;
    const altitudeMode = toNumber(raw.altitudemode) ?? 0;
    const speedMs = toNumber(raw.speed_m_s) ?? 0;
    const poiLatitude = toNumber(raw.poi_latitude);
    const poiLongitude = toNumber(raw.poi_longitude);
    const poiAltitudeFt = toNumber(raw.poi_altitude_ft);
    const poiAltitudeMode = toNumber(raw.poi_altitudemode);
    const photoTimeInterval = toNumber(raw.photo_timeinterval);
    const photoDistInterval = toNumber(raw.photo_distinterval);

    if (poi === null && poiLatitude !== null && poiLongitude !== null && poiAltitudeFt !== null) {
      poi = {
        latitude: poiLatitude,
        longitude: poiLongitude,
        altitudeFt: poiAltitudeFt,
        altitudeMeters: feetToMeters(poiAltitudeFt) ?? 0,
        altitudeMode: poiAltitudeMode ?? 0,
      };
    }

    if (curveSizeFt > 0 && curveSizeFt < minimumCurveSizeFt) {
      warnings.push(`Row ${rowIndex + 2}: curve radius ${curveSizeFt.toFixed(2)}ft is tighter than recommended minimum ${minimumCurveSizeFt}ft.`);
    }

    const waypoint: FlightWaypointRuntime = {
      index: waypoints.length,
      latitude,
      longitude,
      altitudeFt,
      altitudeMeters,
      headingDeg,
      curveSizeFt,
      curveSizeMeters,
      rotationDir,
      gimbalMode,
      gimbalPitchAngle,
      altitudeMode,
      speedMs,
      poiLatitude,
      poiLongitude,
      poiAltitudeFt,
      poiAltitudeMeters: poiAltitudeFt !== null ? feetToMeters(poiAltitudeFt) : null,
      poiAltitudeMode,
      photoTimeInterval,
      photoDistInterval,
      cumulativeDistanceMeters,
      cumulativeDistanceMeters3d,
      horizontalDistanceFromPrevMeters: 0,
      verticalDeltaFromPrevMeters: 0,
      slopePercentFromPrev: null,
      slopeDegreesFromPrev: null,
      headingChangeFromPrevDeg: null,
    };

    if (previousWaypoint) {
      const horizontalDistance = haversineDistanceMeters(previousWaypoint, waypoint);
      const verticalDelta = altitudeMeters - previousWaypoint.altitudeMeters;
      const distance3d = Math.sqrt(horizontalDistance ** 2 + verticalDelta ** 2);

      cumulativeDistanceMeters += horizontalDistance;
      cumulativeDistanceMeters3d += distance3d;

      waypoint.cumulativeDistanceMeters = cumulativeDistanceMeters;
      waypoint.cumulativeDistanceMeters3d = cumulativeDistanceMeters3d;
      waypoint.horizontalDistanceFromPrevMeters = horizontalDistance;
      waypoint.verticalDeltaFromPrevMeters = verticalDelta;

      if (horizontalDistance > 0) {
        const slope = (verticalDelta / horizontalDistance) * 100;
        waypoint.slopePercentFromPrev = slope;
        waypoint.slopeDegreesFromPrev = radiansToDegrees(Math.atan(verticalDelta / horizontalDistance));

        maxSlopePercent = maxSlopePercent === null ? Math.abs(slope) : Math.max(maxSlopePercent, Math.abs(slope));
        maxSlopeDegrees = maxSlopeDegrees === null ? Math.abs(waypoint.slopeDegreesFromPrev) : Math.max(maxSlopeDegrees, Math.abs(waypoint.slopeDegreesFromPrev ?? 0));

        slopeAccumulator += Math.abs(slope);
        slopeSamples += 1;
      }

      if (verticalDelta > 0) {
        totalVerticalGain += verticalDelta;
      } else {
        totalVerticalDrop += Math.abs(verticalDelta);
      }

      const headingDelta = normalizeHeadingDelta(previousWaypoint.headingDeg, headingDeg);
      waypoint.headingChangeFromPrevDeg = headingDelta;

      const segment: FlightSegment = {
        index: segments.length,
        start: previousWaypoint,
        end: waypoint,
        horizontalDistanceMeters: horizontalDistance,
        verticalGainMeters: Math.max(0, verticalDelta),
        slopePercent: waypoint.slopePercentFromPrev,
        slopeDegrees: waypoint.slopeDegreesFromPrev,
        curvatureInverseMeters: curveSizeMeters > 0 ? 1 / curveSizeMeters : null,
      };

      segments.push(segment);
    }

    if (speedMs > 0) {
      speedAccumulator += speedMs;
      speedSamples += 1;
    }

    minAltitudeFt = Math.min(minAltitudeFt, altitudeFt);
    maxAltitudeFt = Math.max(maxAltitudeFt, altitudeFt);

    if (curveSizeFt > 0) {
      minCurveSizeFt = minCurveSizeFt === null ? curveSizeFt : Math.min(minCurveSizeFt, curveSizeFt);
      maxCurveSizeFt = maxCurveSizeFt === null ? curveSizeFt : Math.max(maxCurveSizeFt, curveSizeFt);
      const curveMeters = feetToMeters(curveSizeFt);
      if (curveMeters !== null) {
        tightestCurveMeters = tightestCurveMeters === null ? curveMeters : Math.min(tightestCurveMeters, curveMeters);
      }
    }

    latSum += latitude;
    lonSum += longitude;
    altitudeSumMeters += altitudeMeters;

    if (!bounds) {
      bounds = { north: latitude, south: latitude, east: longitude, west: longitude };
    } else {
      bounds.north = Math.max(bounds.north, latitude);
      bounds.south = Math.min(bounds.south, latitude);
      bounds.east = Math.max(bounds.east, longitude);
      bounds.west = Math.min(bounds.west, longitude);
    }

    waypoints.push(waypoint);
    previousWaypoint = waypoint;
  });

  if (waypoints.length === 0) {
    throw new Error('No valid waypoints found in CSV input.');
  }

  const averageSpeedMs = speedSamples > 0 ? speedAccumulator / speedSamples : null;
  const averageSpeedMph = averageSpeedMs !== null ? averageSpeedMs * 2.23694 : null;
  const estimatedDurationSeconds = averageSpeedMs ? cumulativeDistanceMeters / averageSpeedMs : null;
  const averageSlopePercent = slopeSamples > 0 ? slopeAccumulator / slopeSamples : null;

  const center = {
    lat: latSum / waypoints.length,
    lng: lonSum / waypoints.length,
    altitudeMeters: altitudeSumMeters / waypoints.length,
  };

  const stats: FlightPathStats = {
    totalWaypoints: waypoints.length,
    totalHorizontalDistanceMeters: cumulativeDistanceMeters,
    total3dDistanceMeters: cumulativeDistanceMeters3d,
    totalVerticalGainMeters: totalVerticalGain,
    totalVerticalDropMeters: totalVerticalDrop,
    minAltitudeFt,
    maxAltitudeFt,
    minCurveSizeFt,
    maxCurveSizeFt,
    tightestCurveRadiusMeters: tightestCurveMeters,
    averageSpeedMs,
    averageSpeedMph,
    estimatedDurationSeconds,
    maxSlopePercent,
    maxSlopeDegrees,
    averageSlopePercent,
  };

  return {
    waypoints,
    segments,
    stats,
    poi,
    center,
    bounds,
    warnings,
  };
}
