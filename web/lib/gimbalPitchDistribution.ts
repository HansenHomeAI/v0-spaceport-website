/**
 * Beta-mixture gimbal pitch distribution (negative degrees, DJI-style).
 * Envelope ties to min/max pitch @ AGL from the same interpolation as getGimbalAngleDeg.
 */

import { getGimbalAngleDeg } from './cameraOverlapMath';

export const DEFAULT_DIST_BUFFER = 5;

export type PitchDomain = {
  pitchLoNeg: number;
  pitchHiNeg: number;
  distLo: number;
  distHi: number;
};

/** Steeper cap = -maxPitchDeg, shallower = -minPitchDeg (positive magnitudes from UI). */
export function pitchDomainFromEnvelope(
  minPitchDeg: number,
  maxPitchDeg: number,
  buffer = DEFAULT_DIST_BUFFER,
): PitchDomain {
  const pitchHiNeg = -minPitchDeg;
  const pitchLoNeg = -maxPitchDeg;
  return {
    pitchLoNeg,
    pitchHiNeg,
    distLo: pitchLoNeg - buffer,
    distHi: pitchHiNeg + buffer,
  };
}

/** Intended pitch (negative °) at AGL using the same ramp as the overlap page. */
export function intendedPitchNeg(
  agl: number,
  minPitchDeg: number,
  minAgl: number,
  maxPitchDeg: number,
  maxAgl: number,
): number {
  return -getGimbalAngleDeg(agl, minPitchDeg, minAgl, maxPitchDeg, maxAgl);
}

function gaussianRandom(): number {
  const u = 1 - Math.random();
  const v = Math.random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function gammaRandom(shape: number): number {
  if (shape < 1) return gammaRandom(1 + shape) * Math.random() ** (1 / shape);
  const d = shape - 1 / 3;
  const c = 1 / Math.sqrt(9 * d);
  for (;;) {
    let x: number;
    let v: number;
    do {
      x = gaussianRandom();
      v = 1 + c * x;
    } while (v <= 0);
    v = v ** 3;
    const u = Math.random();
    if (u < 1 - 0.0331 * x ** 4) return d * v;
    if (Math.log(u) < 0.5 * x ** 2 + d * (1 - v + Math.log(v))) return d * v;
  }
}

function betaRandom(alpha: number, beta: number): number {
  const x = gammaRandom(alpha);
  const y = gammaRandom(beta);
  return x / (x + y);
}

export function betaPDFUnnorm(t: number, alpha: number, beta: number): number {
  if (t <= 0 || t >= 1) return 0;
  return t ** (alpha - 1) * (1 - t) ** (beta - 1);
}

export function toT(deg: number, domain: PitchDomain): number {
  return (deg - domain.distLo) / (domain.distHi - domain.distLo);
}

export function fromT(t: number, domain: PitchDomain): number {
  return domain.distLo + t * (domain.distHi - domain.distLo);
}

export function betaParams(modeDeg: number, concentration: number, domain: PitchDomain): { alpha: number; beta: number } {
  const k = Math.max(2.01, concentration);
  const mode = Math.max(0.02, Math.min(0.98, toT(modeDeg, domain)));
  return {
    alpha: mode * (k - 2) + 1,
    beta: (1 - mode) * (k - 2) + 1,
  };
}

export function samplePitch(
  prevDeg: number,
  intDeg: number,
  rho: number,
  peakConc: number,
  baseConc: number,
  outlierRate: number,
  domain: PitchDomain,
): number {
  const modeT = toT(intDeg, domain) + rho * (toT(prevDeg, domain) - toT(intDeg, domain));
  const clampedMode = Math.max(0.05, Math.min(0.95, modeT));
  const modeDeg = fromT(clampedMode, domain);

  if (Math.random() < outlierRate) {
    const { alpha, beta } = betaParams(intDeg, baseConc, domain);
    return fromT(betaRandom(alpha, beta), domain);
  }
  const { alpha, beta } = betaParams(modeDeg, peakConc, domain);
  return fromT(betaRandom(alpha, beta), domain);
}

export function generatePitchSequence(
  intPitchNeg: number,
  rho: number,
  peakConc: number,
  baseConc: number,
  outlierRate: number,
  n: number,
  domain: PitchDomain,
): number[] {
  const seq: number[] = [];
  let prev = intPitchNeg;
  for (let i = 0; i < n; i++) {
    prev = samplePitch(prev, intPitchNeg, rho, peakConc, baseConc, outlierRate, domain);
    seq.push(prev);
  }
  return seq;
}

export function mixturePDFValues(
  intPitch: number,
  peakConc: number,
  baseConc: number,
  outlierRate: number,
  steps: number,
  domain: PitchDomain,
  domLo: number,
  domHi: number,
): number[] {
  const peakP = betaParams(intPitch, peakConc, domain);
  const baseP = betaParams(intPitch, baseConc, domain);

  const rawPeak: number[] = [];
  const rawBase: number[] = [];
  let maxPeak = 0;
  let maxBase = 0;

  for (let i = 0; i <= steps; i++) {
    const d = domLo + (i / steps) * (domHi - domLo);
    const t = toT(d, domain);
    const p = betaPDFUnnorm(t, peakP.alpha, peakP.beta);
    const b = betaPDFUnnorm(t, baseP.alpha, baseP.beta);
    rawPeak.push(p);
    rawBase.push(b);
    if (p > maxPeak) maxPeak = p;
    if (b > maxBase) maxBase = b;
  }

  return rawPeak.map((p, i) => {
    const normP = maxPeak > 0 ? p / maxPeak : 0;
    const normB = maxBase > 0 ? rawBase[i] / maxBase : 0;
    return (1 - outlierRate) * normP + outlierRate * normB;
  });
}
