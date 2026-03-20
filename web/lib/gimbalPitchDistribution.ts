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

// ---------------------------------------------------------------------------
// Seeded PRNG — mulberry32 (public domain, ~2 ns/call, high quality)
// ---------------------------------------------------------------------------

/** Returns a seeded PRNG. Pass as `random` to avoid global Math.random state. */
export function makeSeededRandom(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) >>> 0;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Deterministic integer seed from an array of numeric parameters.
 * Same values → same seed every time.
 */
export function paramsToSeed(values: number[]): number {
  let h = 5381;
  for (const v of values) {
    const bits = Math.round(v * 1000);
    h = (Math.imul(h, 33) + bits) | 0;
  }
  return h >>> 0;
}

// ---------------------------------------------------------------------------
// Beta-distribution samplers (accept injectable `random`)
// ---------------------------------------------------------------------------

function gaussianRandom(random: () => number): number {
  const u = 1 - random();
  const v = random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function gammaRandom(shape: number, random: () => number): number {
  if (shape < 1) return gammaRandom(1 + shape, random) * random() ** (1 / shape);
  const d = shape - 1 / 3;
  const c = 1 / Math.sqrt(9 * d);
  for (;;) {
    let x: number;
    let v: number;
    do {
      x = gaussianRandom(random);
      v = 1 + c * x;
    } while (v <= 0);
    v = v ** 3;
    const u = random();
    if (u < 1 - 0.0331 * x ** 4) return d * v;
    if (Math.log(u) < 0.5 * x ** 2 + d * (1 - v + Math.log(v))) return d * v;
  }
}

function betaRandom(alpha: number, beta: number, random: () => number): number {
  const x = gammaRandom(alpha, random);
  const y = gammaRandom(beta, random);
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
  random: () => number = Math.random,
): number {
  const modeT = toT(intDeg, domain) + rho * (toT(prevDeg, domain) - toT(intDeg, domain));
  const clampedMode = Math.max(0.05, Math.min(0.95, modeT));
  const modeDeg = fromT(clampedMode, domain);

  if (random() < outlierRate) {
    const { alpha, beta } = betaParams(intDeg, baseConc, domain);
    return fromT(betaRandom(alpha, beta, random), domain);
  }
  const { alpha, beta } = betaParams(modeDeg, peakConc, domain);
  return fromT(betaRandom(alpha, beta, random), domain);
}

export function generatePitchSequence(
  intPitchNeg: number,
  rho: number,
  peakConc: number,
  baseConc: number,
  outlierRate: number,
  n: number,
  domain: PitchDomain,
  random: () => number = Math.random,
): number[] {
  const seq: number[] = [];
  let prev = intPitchNeg;
  for (let i = 0; i < n; i++) {
    prev = samplePitch(prev, intPitchNeg, rho, peakConc, baseConc, outlierRate, domain, random);
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
