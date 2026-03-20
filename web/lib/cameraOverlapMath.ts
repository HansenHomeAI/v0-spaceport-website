/**
 * Pure math for camera-overlap page (hypotenuse, gimbal interpolation, capture stats).
 */

export const TAN_30 = Math.tan(Math.PI / 6);
export const FULL_ROT_SEC = 20;
export const TRANSIT_SEC = 1;

// Rectangular FOV — 77° horizontal (cross-track), 55° vertical (along-track)
export const FOV_H_DEG = 77;
export const FOV_V_DEG = 55;
export const TAN_H = Math.tan((FOV_H_DEG / 2) * Math.PI / 180);
export const TAN_V = Math.tan((FOV_V_DEG / 2) * Math.PI / 180);

/** Gimbal angle (degrees below horizon, positive magnitude) from height thresholds. */
export function getGimbalAngleDeg(
  height: number,
  minAngle: number,
  minHeight: number,
  maxAngle: number,
  maxHeight: number,
): number {
  if (height <= minHeight) return minAngle;
  if (height >= maxHeight) return maxAngle;
  const t = (height - minHeight) / (maxHeight - minHeight);
  return minAngle + t * (maxAngle - minAngle);
}

export function hypotenuseFromHeight(height: number, angleDegBelowHorizon: number): number {
  const angleRad = (angleDegBelowHorizon * Math.PI) / 180;
  return height / Math.sin(angleRad);
}

export function footprintWidth(hypotenuseFt: number): number {
  return 2 * hypotenuseFt * TAN_30;
}

export function spacingFt(footprintFt: number, overlapPercent: number): number {
  return footprintFt * (1 - overlapPercent / 100);
}

export function rotationTimeSec(effectiveCapFraction: number): number {
  return effectiveCapFraction * FULL_ROT_SEC + 2 * TRANSIT_SEC;
}

// ---------------------------------------------------------------------------
// 3D rectangular-FOV ground projection
// ---------------------------------------------------------------------------

export type Vec3 = [number, number, number];
export type GroundQuad = [Vec3, Vec3, Vec3, Vec3]; // 4 ground corners [x, y, 0]

/**
 * Projects the 4 frustum corners of a rectangular FOV camera to the ground plane (z=0).
 *
 * Coordinate system: X = along-track (flight direction), Y = cross-track, Z = up.
 * Drone sits at (droneX, 0, height).
 *
 * **Parallel / side-looking capture:** the camera does not look along the flight path.
 * The optical axis lies in the YZ plane, pointing toward +Y and down (oblique / nadir),
 * so the drone “flies sideways” relative to where the lens points — like a port-side
 * survey line with the gimbal aimed out the side of the aircraft.
 *
 * FOV: 55° (TAN_V) spans **along-track** (sensor vertical → ground X);
 * 77° (TAN_H) spans **cross-track** (sensor horizontal → ground Y via image-up in YZ).
 *
 * Returns corners in order: [nearLeft, nearRight, farRight, farLeft] for quad winding.
 */
export function groundFootprint(
  droneX: number,
  height: number,
  pitchDeg: number,
): GroundQuad {
  const theta = (pitchDeg * Math.PI) / 180; // angle below horizon
  const cosT = Math.cos(theta);
  const sinT = Math.sin(theta);

  // Side-looking: LOS horizontal in +Y, pitched down (same θ convention as forward case).
  const losX = 0;
  const losY = cosT;
  const losZ = -sinT;

  // Along-track on ground = +X (55°): perpendicular to LOS and world up.
  const rightX = 1;
  const rightY = 0;
  const rightZ = 0;

  // Cross-track spread in the YZ plane (77°).
  const upX = 0;
  const upY = sinT;
  const upZ = cosT;

  const corners: Vec3[] = [];
  for (const sv of [-1, 1]) {
    for (const sh of [-1, 1]) {
      const dx = losX + sv * TAN_V * rightX + sh * TAN_H * upX;
      const dy = losY + sv * TAN_V * rightY + sh * TAN_H * upY;
      const dz = losZ + sv * TAN_V * rightZ + sh * TAN_H * upZ;

      if (dz >= 0) {
        const bigT = 10000;
        corners.push([droneX + dx * bigT, dy * bigT, 0]);
      } else {
        const t = height / -dz;
        corners.push([droneX + dx * t, dy * t, 0]);
      }
    }
  }

  return [corners[0], corners[1], corners[3], corners[2]];
}

export type FootprintBounds = { minX: number; maxX: number; minY: number; maxY: number };

/** Axis-aligned bounding box of a ground quad. */
export function footprintBounds(fp: GroundQuad): FootprintBounds {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const [x, y] of fp) {
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  return { minX, maxX, minY, maxY };
}

/**
 * Overlap fraction between two footprints on each axis.
 * Returns {alongTrack, crossTrack} each in [0, 1], measured as the overlap
 * span divided by the smaller footprint span on that axis.
 */
export function rectOverlapFraction(
  a: FootprintBounds,
  b: FootprintBounds,
): { alongTrack: number; crossTrack: number } {
  const overlapX = Math.max(0, Math.min(a.maxX, b.maxX) - Math.max(a.minX, b.minX));
  const overlapY = Math.max(0, Math.min(a.maxY, b.maxY) - Math.max(a.minY, b.minY));

  const spanAx = a.maxX - a.minX;
  const spanBx = b.maxX - b.minX;
  const spanAy = a.maxY - a.minY;
  const spanBy = b.maxY - b.minY;

  const alongTrack = (spanAx > 0 && spanBx > 0)
    ? overlapX / Math.min(spanAx, spanBx)
    : 0;
  const crossTrack = (spanAy > 0 && spanBy > 0)
    ? overlapY / Math.min(spanAy, spanBy)
    : 0;

  return {
    alongTrack: Math.min(1, alongTrack),
    crossTrack: Math.min(1, crossTrack),
  };
}

/**
 * Intersection-over-union of two axis-aligned ground footprints (0–1).
 * Single summary overlap between the two photo coverage areas.
 */
export function footprintOverlapIou(a: FootprintBounds, b: FootprintBounds): number {
  const ix = Math.max(0, Math.min(a.maxX, b.maxX) - Math.max(a.minX, b.minX));
  const iy = Math.max(0, Math.min(a.maxY, b.maxY) - Math.max(a.minY, b.minY));
  const intersection = ix * iy;
  const areaA = (a.maxX - a.minX) * (a.maxY - a.minY);
  const areaB = (b.maxX - b.minX) * (b.maxY - b.minY);
  const union = areaA + areaB - intersection;
  if (union <= 0) return 0;
  return intersection / union;
}
