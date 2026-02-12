export type LatLng = { lat: number; lng: number };

const EARTH_RADIUS_METERS = 6378137;
const FEET_TO_METERS = 0.3048;

function makeSpiral(dphi: number, N: number, r0: number, rHold: number, steps = 500): Array<{ x: number; y: number }> {
  const baseAlpha = Math.log(rHold / r0) / (N * dphi);
  const radiusRatio = rHold / r0;

  let earlyDensityFactor = 1.0;
  let lateDensityFactor = 0.9;

  if (radiusRatio > 20) {
    earlyDensityFactor = 1.02;
    lateDensityFactor = 0.8;
  } else if (radiusRatio > 10) {
    earlyDensityFactor = 1.05;
    lateDensityFactor = 0.85;
  }

  const alphaEarly = baseAlpha * earlyDensityFactor;
  const alphaLate = baseAlpha * lateDensityFactor;

  const tOut = N * dphi;
  const tHold = dphi;
  const tTotal = 2 * tOut + tHold;

  const tTransition = tOut * 0.4;
  const rTransition = r0 * Math.exp(alphaEarly * tTransition);
  const actualMaxRadius = rTransition * Math.exp(alphaLate * (tOut - tTransition));

  const points: Array<{ x: number; y: number }> = [];

  for (let i = 0; i < steps; i += 1) {
    const t = (i * tTotal) / (steps - 1);

    let r: number;
    if (t <= tOut) {
      if (t <= tTransition) {
        r = r0 * Math.exp(alphaEarly * t);
      } else {
        r = rTransition * Math.exp(alphaLate * (t - tTransition));
      }
    } else if (t <= tOut + tHold) {
      r = actualMaxRadius;
    } else {
      const inboundT = t - (tOut + tHold);
      r = actualMaxRadius * Math.exp(-alphaLate * inboundT);
    }

    const phase = ((t / dphi) % 2 + 2) % 2;
    const phi = phase <= 1 ? phase * dphi : (2 - phase) * dphi;

    points.push({ x: r * Math.cos(phi), y: r * Math.sin(phi) });
  }

  return points;
}

function xyToLatLng(xFeet: number, yFeet: number, center: LatLng): LatLng {
  const xMeters = xFeet * FEET_TO_METERS;
  const yMeters = yFeet * FEET_TO_METERS;

  const dLat = yMeters / EARTH_RADIUS_METERS;
  const dLng = xMeters / (EARTH_RADIUS_METERS * Math.cos((center.lat * Math.PI) / 180));

  return {
    lat: center.lat + (dLat * 180) / Math.PI,
    lng: center.lng + (dLng * 180) / Math.PI,
  };
}

export function generateSpiralPreviewLine(center: LatLng, params: { slices: number; N: number; r0: number; rHold: number }): LatLng[] {
  const { slices, N, r0, rHold } = params;
  const dphi = (2 * Math.PI) / slices;
  const rawSpiral = makeSpiral(dphi, N, r0, rHold);

  const latLngPath: LatLng[] = [];
  for (let sliceIndex = 0; sliceIndex < slices; sliceIndex += 1) {
    const offset = Math.PI / 2 + sliceIndex * dphi;
    for (const point of rawSpiral) {
      const x = point.x * Math.cos(offset) - point.y * Math.sin(offset);
      const y = point.x * Math.sin(offset) + point.y * Math.cos(offset);
      latLngPath.push(xyToLatLng(x, y, center));
    }
  }

  return latLngPath;
}
