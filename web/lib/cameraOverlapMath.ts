/**
 * Pure math for camera-overlap page (hypotenuse, gimbal interpolation, capture stats).
 */

export const TAN_30 = Math.tan(Math.PI / 6);
export const FULL_ROT_SEC = 20;
export const TRANSIT_SEC = 1;

// Rectangular FOV — 75° horizontal (cross-track), 55° vertical (along-track)
export const FOV_H_DEG = 75;
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
 * FOV (landscape): **75° horizontal** on **camera right** (image width / along-track for H=0);
 * **55° vertical** on **camera up** (image height → cross-track + vertical via up in YZ).
 * `right` and `up` are orthonormal to LOS; TAN_H must multiply `right`, TAN_V must multiply `up`.
 *
 * Returns corners in order: [nearLeft, nearRight, farRight, farLeft] for quad winding.
 *
 * @param headingDeg  Yaw rotation in degrees. 0 = camera looks in +Y (cross-track),
 *                    matching the original side-looking convention.  Positive values
 *                    rotate the footprint CW when viewed from above.
 */
export function groundFootprint(
  droneX: number,
  height: number,
  pitchDeg: number,
  headingDeg = 0,
): GroundQuad {
  const theta = (pitchDeg * Math.PI) / 180; // angle below horizon
  const cosT = Math.cos(theta);
  const sinT = Math.sin(theta);

  const H = (headingDeg * Math.PI) / 180;
  const sinH = Math.sin(H);
  const cosH = Math.cos(H);

  // Camera looks to the "right" of heading H, pitched down by theta.
  // H=0: LOS = (0, cosT, -sinT) — backward-compatible side-looking default.
  const losX = sinH * cosT;
  const losY = cosH * cosT;
  const losZ = -sinT;

  // Camera-right (image horizontal / wide FOV axis for landscape).
  // H=0: (1, 0, 0) = +X along-track.
  const rightX = cosH;
  const rightY = -sinH;
  const rightZ = 0;

  // Camera-up (image vertical / narrow FOV axis).
  // H=0: (0, sinT, cosT).
  const upX = sinH * sinT;
  const upY = cosH * sinT;
  const upZ = cosT;

  const corners: Vec3[] = [];
  for (const sv of [-1, 1]) {
    for (const sh of [-1, 1]) {
      const dx = losX + sv * TAN_H * rightX + sh * TAN_V * upX;
      const dy = losY + sv * TAN_H * rightY + sh * TAN_V * upY;
      const dz = losZ + sv * TAN_H * rightZ + sh * TAN_V * upZ;

      // dz is independent of heading — only pitch determines whether a ray
      // is above or below the horizon.  Mirror-clip keeps the far edge
      // pitch-dependent; 1/300 caps slant to 300× height near the threshold.
      const t = height / Math.max(Math.abs(dz), 1 / 300);
      corners.push([droneX + dx * t, dy * t, 0]);
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

/**
 * Mean IoU between consecutive footprints (N ≥ 2 waypoints).
 *
 * Accepts an optional `headingDegs` array for spin-mode captures where each
 * waypoint faces a different direction.  Defaults to all-0 (side-looking).
 */
export function averageAdjacentFootprintIou(
  alongPositions: number[],
  height: number,
  pitchDegsBelowHorizon: number[],
  headingDegs: number[] = [],
): number {
  const n = alongPositions.length;
  if (n < 2 || pitchDegsBelowHorizon.length !== n) return 0;
  let sum = 0;
  for (let i = 0; i < n - 1; i++) {
    const hA = headingDegs[i] ?? 0;
    const hB = headingDegs[i + 1] ?? 0;
    const a = groundFootprint(alongPositions[i], height, pitchDegsBelowHorizon[i], hA);
    const b = groundFootprint(alongPositions[i + 1], height, pitchDegsBelowHorizon[i + 1], hB);
    sum += footprintOverlapIou(footprintBounds(a), footprintBounds(b));
  }
  return sum / (n - 1);
}
