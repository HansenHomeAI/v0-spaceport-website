const EARTH_RADIUS_METERS = 6_378_137;
const FEET_TO_METERS = 0.3048;

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export interface CurvatureWaypoint {
  latitude: number;
  longitude: number;
  altitudeFt: number;
  curveSizeMeters: number;
  rotationDir?: number | null;
}

export interface CurvedPathPoint {
  latitude: number;
  longitude: number;
  altitudeFt: number;
}

export type TurnDirection = "left" | "right";

export interface CurvedArcSummary {
  waypointIndex: number;
  radiusMeters: number;
  turnDirection: TurnDirection;
  turnAngleRadians: number;
  entry: CurvedPathPoint;
  exit: CurvedPathPoint;
}

export interface CurvedPathResult {
  points: CurvedPathPoint[];
  totalLengthMeters: number;
  arcSummaries: CurvedArcSummary[];
}

interface Vec2 {
  x: number;
  y: number;
}

interface ArcComputation {
  entryPoint: Vec2;
  exitPoint: Vec2;
  entryAltitudeFt: number;
  exitAltitudeFt: number;
  center: Vec2;
  radius: number;
  turnDirection: TurnDirection;
  turnAngle: number;
  samples: { point: Vec2; altitudeFt: number }[];
}

function degreesToRadians(value: number): number {
  return (value * Math.PI) / 180;
}

function radiansToDegrees(value: number): number {
  return (value * 180) / Math.PI;
}

function rotate90(vector: Vec2, direction: TurnDirection): Vec2 {
  return direction === "left"
    ? { x: -vector.y, y: vector.x }
    : { x: vector.y, y: -vector.x };
}

function add(a: Vec2, b: Vec2): Vec2 {
  return { x: a.x + b.x, y: a.y + b.y };
}

function subtract(a: Vec2, b: Vec2): Vec2 {
  return { x: a.x - b.x, y: a.y - b.y };
}

function scale(vec: Vec2, scalar: number): Vec2 {
  return { x: vec.x * scalar, y: vec.y * scalar };
}

function dot(a: Vec2, b: Vec2): number {
  return a.x * b.x + a.y * b.y;
}

function magnitude(vec: Vec2): number {
  return Math.sqrt(vec.x ** 2 + vec.y ** 2);
}

function normalize(vec: Vec2): Vec2 {
  const mag = magnitude(vec);
  if (mag === 0) {
    return { x: 0, y: 0 };
  }
  return { x: vec.x / mag, y: vec.y / mag };
}

function toLocal(originLat: number, originLon: number, lat: number, lon: number): Vec2 {
  const dLat = degreesToRadians(lat - originLat);
  const dLon = degreesToRadians(lon - originLon);
  const meanLat = degreesToRadians((lat + originLat) / 2);
  const x = dLon * Math.cos(meanLat) * EARTH_RADIUS_METERS;
  const y = dLat * EARTH_RADIUS_METERS;
  return { x, y };
}

function toLatLon(originLat: number, originLon: number, point: Vec2): { latitude: number; longitude: number } {
  const lat = originLat + radiansToDegrees(point.y / EARTH_RADIUS_METERS);
  const lon = originLon + radiansToDegrees(point.x / (EARTH_RADIUS_METERS * Math.cos(degreesToRadians(originLat))));
  return { latitude: lat, longitude: lon };
}

function determineTurnDirection(dirIn: Vec2, dirOut: Vec2, rotationDir?: number | null): TurnDirection | null {
  const cross = dirIn.x * dirOut.y - dirIn.y * dirOut.x;
  if (Math.abs(cross) > 1e-8) {
    return cross > 0 ? "left" : "right";
  }
  if (rotationDir === 0) {
    return "right";
  }
  if (rotationDir === 1) {
    return "left";
  }
  return null;
}

function computeArc(
  prev: Vec2,
  curr: Vec2,
  next: Vec2,
  prevAltFt: number,
  currAltFt: number,
  nextAltFt: number,
  radiusMeters: number,
  rotationDir: number | null | undefined,
): ArcComputation | null {
  if (radiusMeters <= 0) {
    return null;
  }

  const vecIn = subtract(curr, prev);
  const vecOut = subtract(next, curr);
  const lenIn = magnitude(vecIn);
  const lenOut = magnitude(vecOut);
  if (lenIn < 1e-3 || lenOut < 1e-3) {
    return null;
  }

  const dirIn = normalize(vecIn);
  const dirOut = normalize(vecOut);
  const turnDirection = determineTurnDirection(dirIn, dirOut, rotationDir);
  if (!turnDirection) {
    return null;
  }

  const cosTheta = clamp(dot(dirIn, dirOut), -1, 1);
  const theta = Math.acos(cosTheta);
  if (!Number.isFinite(theta) || theta < degreesToRadians(1)) {
    return null;
  }

  const desiredOffset = radiusMeters / Math.tan(theta / 2);
  const maxOffset = Math.min(lenIn, lenOut) * 0.9;
  const offset = Math.min(desiredOffset, maxOffset);
  if (!Number.isFinite(offset) || offset <= 0) {
    return null;
  }

  const effectiveRadius = offset * Math.tan(theta / 2);
  if (!Number.isFinite(effectiveRadius) || effectiveRadius <= 0) {
    return null;
  }

  const entryPoint = subtract(curr, scale(dirIn, offset));
  const exitPoint = add(curr, scale(dirOut, offset));

  const entryFraction = magnitude(subtract(entryPoint, prev)) / lenIn;
  const exitFraction = magnitude(subtract(exitPoint, curr)) / lenOut;
  const entryAltitudeFt = prevAltFt + (currAltFt - prevAltFt) * entryFraction;
  const exitAltitudeFt = currAltFt + (nextAltFt - currAltFt) * exitFraction;

  const normalIn = normalize(rotate90(dirIn, turnDirection));
  const normalOut = normalize(rotate90(dirOut, turnDirection));
  const centerFromEntry = add(entryPoint, scale(normalIn, effectiveRadius));
  const centerFromExit = add(exitPoint, scale(normalOut, effectiveRadius));
  const center = {
    x: (centerFromEntry.x + centerFromExit.x) / 2,
    y: (centerFromEntry.y + centerFromExit.y) / 2,
  };

  const entryVec = subtract(entryPoint, center);
  const exitVec = subtract(exitPoint, center);
  const startAngle = Math.atan2(entryVec.y, entryVec.x);
  const endAngle = Math.atan2(exitVec.y, exitVec.x);

  let sweep = endAngle - startAngle;
  if (turnDirection === "left" && sweep < 0) {
    sweep += Math.PI * 2;
  } else if (turnDirection === "right" && sweep > 0) {
    sweep -= Math.PI * 2;
  }

  const arcAngle = Math.abs(sweep);
  if (!Number.isFinite(arcAngle) || arcAngle < degreesToRadians(1)) {
    return null;
  }

  const segmentCount = Math.max(3, Math.ceil(arcAngle / degreesToRadians(10)));
  const samples: { point: Vec2; altitudeFt: number }[] = [];
  for (let i = 1; i <= segmentCount; i += 1) {
    const t = i / segmentCount;
    const angle = turnDirection === "left"
      ? startAngle + t * arcAngle
      : startAngle - t * arcAngle;
    const point = {
      x: center.x + Math.cos(angle) * effectiveRadius,
      y: center.y + Math.sin(angle) * effectiveRadius,
    };
    const altitudeFt = entryAltitudeFt + (exitAltitudeFt - entryAltitudeFt) * t;
    samples.push({ point, altitudeFt });
  }

  return {
    entryPoint,
    exitPoint,
    entryAltitudeFt,
    exitAltitudeFt,
    center,
    radius: effectiveRadius,
    turnDirection,
    turnAngle: arcAngle,
    samples,
  };
}

export function buildCurvedPath(waypoints: CurvatureWaypoint[]): CurvedPathResult {
  if (waypoints.length === 0) {
    return { points: [], totalLengthMeters: 0, arcSummaries: [] };
  }
  if (waypoints.length === 1) {
    return {
      points: [{ ...waypoints[0] }],
      totalLengthMeters: 0,
      arcSummaries: [],
    };
  }

  const originLat = waypoints[0].latitude;
  const originLon = waypoints[0].longitude;

  const localPoints = waypoints.map(({ latitude, longitude }) =>
    toLocal(originLat, originLon, latitude, longitude)
  );

  const arcs: Array<ArcComputation | null> = waypoints.map(() => null);

  for (let i = 1; i < waypoints.length - 1; i += 1) {
    const radius = waypoints[i].curveSizeMeters;
    if (!Number.isFinite(radius) || radius <= 0) {
      continue;
    }
    const arc = computeArc(
      localPoints[i - 1],
      localPoints[i],
      localPoints[i + 1],
      waypoints[i - 1].altitudeFt,
      waypoints[i].altitudeFt,
      waypoints[i + 1].altitudeFt,
      radius,
      waypoints[i].rotationDir,
    );
    arcs[i] = arc;
  }

  const points: CurvedPathPoint[] = [];
  const arcSummaries: CurvedArcSummary[] = [];
  let totalLengthMeters = 0;

  const pushPoint = (point: Vec2, altitudeFt: number) => {
    const { latitude, longitude } = toLatLon(originLat, originLon, point);
    const curvedPoint: CurvedPathPoint = {
      latitude,
      longitude,
      altitudeFt,
    };
    if (points.length > 0) {
      const prev = points[points.length - 1];
      const prevLocal = toLocal(originLat, originLon, prev.latitude, prev.longitude);
      const dx = point.x - prevLocal.x;
      const dy = point.y - prevLocal.y;
      const dz = (altitudeFt - prev.altitudeFt) * FEET_TO_METERS;
      totalLengthMeters += Math.sqrt(dx ** 2 + dy ** 2 + dz ** 2);
    }
    points.push(curvedPoint);
  };

  pushPoint(localPoints[0], waypoints[0].altitudeFt);

  for (let i = 1; i < waypoints.length; i += 1) {
    const prevArc = arcs[i - 1];
    const currArc = arcs[i];

    const startPoint = prevArc ? prevArc.exitPoint : localPoints[i - 1];
    const startAltitudeFt = prevArc ? prevArc.exitAltitudeFt : waypoints[i - 1].altitudeFt;
    const endPoint = currArc ? currArc.entryPoint : localPoints[i];
    const endAltitudeFt = currArc ? currArc.entryAltitudeFt : waypoints[i].altitudeFt;

    if (points.length > 0) {
      const last = points[points.length - 1];
      if (Math.abs(last.latitude - (toLatLon(originLat, originLon, startPoint).latitude)) > 1e-8 ||
          Math.abs(last.longitude - (toLatLon(originLat, originLon, startPoint).longitude)) > 1e-8) {
        pushPoint(startPoint, startAltitudeFt);
      }
    }

    pushPoint(endPoint, endAltitudeFt);

    if (currArc) {
      let first = true;
      currArc.samples.forEach(sample => {
        if (first) {
          first = false;
          return;
        }
        pushPoint(sample.point, sample.altitudeFt);
      });

      arcSummaries.push({
        waypointIndex: i,
        radiusMeters: currArc.radius,
        turnDirection: currArc.turnDirection,
        turnAngleRadians: currArc.turnAngle,
        entry: {
          ...toLatLon(originLat, originLon, currArc.entryPoint),
          altitudeFt: currArc.entryAltitudeFt,
        },
        exit: {
          ...toLatLon(originLat, originLon, currArc.exitPoint),
          altitudeFt: currArc.exitAltitudeFt,
        },
      });
    }
  }

  const lastIndex = waypoints.length - 1;
  const lastArc = arcs[lastIndex];
  if (!lastArc) {
    const lastLocal = localPoints[lastIndex];
    const lastAltitudeFt = waypoints[lastIndex].altitudeFt;
    const lastPoint = points[points.length - 1];
    if (Math.abs(lastPoint.latitude - waypoints[lastIndex].latitude) > 1e-8 ||
        Math.abs(lastPoint.longitude - waypoints[lastIndex].longitude) > 1e-8) {
      pushPoint(lastLocal, lastAltitudeFt);
    }
  }

  return { points, totalLengthMeters, arcSummaries };
}
