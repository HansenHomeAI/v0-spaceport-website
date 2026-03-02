/**
 * 2D Curved Path helper
 * Generates true circular arcs for drone flight paths, based on curve radius (curvesize).
 * Used for visualizing accurate flight paths on Mapbox.
 */

export interface PathWaypoint {
  lat: number;
  lng: number;
  curveSizeFt?: number;
}

// Earth constants for local planar projection
const EARTH_RADIUS_FT = 20902231; // approx 6371000m in feet

// Convert degrees to radians
const toRad = (deg: number) => (deg * Math.PI) / 180;
// Convert radians to degrees
const toDeg = (rad: number) => (rad * 180) / Math.PI;

interface Point2D {
  x: number; // local X (feet)
  y: number; // local Y (feet)
}

// Avoid unstable arc geometry for near-straight / near-180-degree turns.
const MIN_TURN_ANGLE_RAD = 0.05; // ~2.9 deg
const MAX_TURN_ANGLE_RAD = Math.PI - 0.05;

/**
 * Projects a lat/lng to a local cartesian coordinate system (in feet)
 * centered around a reference point.
 */
function projectToLocal(lat: number, lng: number, refLat: number, refLng: number): Point2D {
  const latRad = toRad(lat);
  const refLatRad = toRad(refLat);
  const refLngRad = toRad(refLng);
  const lngRad = toRad(lng);

  // Simple equirectangular projection
  const x = (lngRad - refLngRad) * Math.cos(refLatRad) * EARTH_RADIUS_FT;
  const y = (latRad - refLatRad) * EARTH_RADIUS_FT;

  return { x, y };
}

/**
 * Unprojects a local cartesian coordinate (feet) back to lat/lng
 * centered around a reference point.
 */
function unprojectFromLocal(p: Point2D, refLat: number, refLng: number): { lat: number; lng: number } {
  const refLatRad = toRad(refLat);
  
  const dLatRad = p.y / EARTH_RADIUS_FT;
  const dLngRad = p.x / (EARTH_RADIUS_FT * Math.cos(refLatRad));

  return {
    lat: refLat + toDeg(dLatRad),
    lng: refLng + toDeg(dLngRad)
  };
}

function normalize(v: Point2D): Point2D {
  const len = Math.hypot(v.x, v.y);
  if (len === 0) return { x: 0, y: 0 };
  return { x: v.x / len, y: v.y / len };
}

function sub(a: Point2D, b: Point2D): Point2D {
  return { x: a.x - b.x, y: a.y - b.y };
}

function add(a: Point2D, b: Point2D): Point2D {
  return { x: a.x + b.x, y: a.y + b.y };
}

function mult(v: Point2D, scalar: number): Point2D {
  return { x: v.x * scalar, y: v.y * scalar };
}

function dot(a: Point2D, b: Point2D): number {
  return a.x * b.x + a.y * b.y;
}

function cross(a: Point2D, b: Point2D): number {
  return a.x * b.y - a.y * b.x;
}

function lerp(a: Point2D, b: Point2D, t: number): Point2D {
  return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
}

function distance(a: Point2D, b: Point2D): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

/**
 * Computes a dense set of lat/lng points that approximate the curved segments.
 * Mirrors the logic in ShapeLab's PathView.
 */
export function generateCurvedPath(waypoints: PathWaypoint[]): Array<[number, number]> {
  if (waypoints.length < 2) {
    return waypoints.map(w => [w.lng, w.lat]);
  }

  // Use the first point as the projection reference
  const refLat = waypoints[0].lat;
  const refLng = waypoints[0].lng;

  const pts = waypoints.map(w => projectToLocal(w.lat, w.lng, refLat, refLng));
  
  const finalLocalPoints: Point2D[] = [];
  
  const addLine = (a: Point2D, b: Point2D, n: number) => {
    for (let i = 1; i <= n; i++) {
      finalLocalPoints.push(lerp(a, b, i / n));
    }
  };

  let last = pts[0];
  finalLocalPoints.push(last);

  for (let i = 1; i < pts.length - 1; i++) {
    const P0 = pts[i - 1];
    const P1 = pts[i];
    const P2 = pts[i + 1];
    
    let A = sub(P1, P0);
    let B = sub(P2, P1);
    
    const L0 = distance(P0, P1);
    const L1 = distance(P1, P2);
    
    if (L0 < 1e-3 || L1 < 1e-3) {
      addLine(last, P1, 6);
      last = P1;
      continue;
    }
    
    A = normalize(A);
    B = normalize(B);
    
    const cosPhi = Math.max(-1, Math.min(1, dot(A, B)));
    const phi = Math.acos(cosPhi);
    
    if (!Number.isFinite(phi) || phi < MIN_TURN_ANGLE_RAD || phi > MAX_TURN_ANGLE_RAD) {
      addLine(last, P1, 6);
      last = P1;
      continue;
    }
    
    const requestedRadius = Math.max(0, waypoints[i].curveSizeFt || 0);
    if (requestedRadius < 1e-3) {
      addLine(last, P1, 6);
      last = P1;
      continue;
    }
    
    let t = requestedRadius * Math.tan(phi / 2);
    const tMax = Math.min(L0, L1) * 0.49;
    t = Math.min(t, tMax);
    // If we had to clamp tangent offset, use an effective radius that
    // matches the clamped geometry. This prevents oversized loop-outs.
    const tanHalfPhi = Math.tan(phi / 2);
    const effectiveRadius = tanHalfPhi > 1e-6 ? (t / tanHalfPhi) : requestedRadius;
    
    const T0 = sub(P1, mult(A, t));
    const T1 = add(P1, mult(B, t));
    
    const W0 = mult(A, -1);
    const W1 = B;
    let bis = add(W0, W1);
    
    const bisLen = Math.hypot(bis.x, bis.y);
    if (bisLen < 1e-6) {
      addLine(last, P1, 6);
      last = P1;
      continue;
    }
    bis = normalize(bis);
    
    const distToCenter = effectiveRadius / Math.sin(phi / 2);
    const C = add(P1, mult(bis, distToCenter));
    
    const turnCross = cross(A, B);
    
    const a0 = Math.atan2(T0.y - C.y, T0.x - C.x);
    const a1 = Math.atan2(T1.y - C.y, T1.x - C.x);
    let startAng = a0;
    let endAng = a1;
    
    if (turnCross > 0) {
      if (endAng < startAng) endAng += 2 * Math.PI;
    } else {
      if (endAng > startAng) endAng -= 2 * Math.PI;
    }
    
    addLine(last, T0, 6);
    
    const arcSteps = Math.max(10, Math.min(36, Math.ceil(Math.abs(endAng - startAng) / (Math.PI / 18))));
    for (let k = 0; k <= arcSteps; k++) {
      const tt = k / arcSteps;
      const ang = startAng + (endAng - startAng) * tt;
      finalLocalPoints.push({
        x: C.x + effectiveRadius * Math.cos(ang),
        y: C.y + effectiveRadius * Math.sin(ang)
      });
    }
    
    last = finalLocalPoints[finalLocalPoints.length - 1];
  }
  
  const Pend = pts[pts.length - 1];
  addLine(last, Pend, 10);
  
  // Convert back to [lng, lat] for Mapbox GeoJSON
  return finalLocalPoints.map(p => {
    const unproj = unprojectFromLocal(p, refLat, refLng);
    return [unproj.lng, unproj.lat];
  });
}
