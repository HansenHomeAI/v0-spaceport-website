/**
 * Import/export snapshot for /camera-overlap — all user-controlled fields.
 */

export const CAMERA_OVERLAP_FLIGHT_CONFIG_VERSION = 1 as const;

export type RealPathFormSnapshot = {
  center: string;
  batteryMinutes: string;
  batteries: string;
  minHeight: string;
  maxHeight: string;
  formToTerrain: boolean;
  minExpansionDist: string;
  maxExpansionDist: string;
};

export type GimbalDistributionSnapshot = {
  peakConc: number;
  baseConc: number;
  outlierRate: number;
  rho: number;
};

export type CameraOverlapFlightConfigV1 = {
  version: typeof CAMERA_OVERLAP_FLIGHT_CONFIG_VERSION;
  workflowMode: 'straight' | 'realPath';
  height: number;
  handles: number[];
  speedEnv: {
    loAglFt: number;
    loMph: number;
    hiAglFt: number;
    hiMph: number;
  };
  minAngle: number;
  minAngleHeight: number;
  maxAngle: number;
  maxAngleHeight: number;
  customCaptureRing: boolean;
  viewerPathLengthFt: number;
  pitchSequenceNeg: number[];
  spinMode: boolean;
  captureIntervalFt: number;
  captureIntervalSec: number;
  captureIntervalUnit: 'ft' | 's';
  gimbalDistribution: GimbalDistributionSnapshot;
  realPath: RealPathFormSnapshot;
};

const DEFAULT_REAL_PATH: RealPathFormSnapshot = {
  center: '39.739200, -104.990300',
  batteryMinutes: '20',
  batteries: '2',
  minHeight: '120',
  maxHeight: '360',
  formToTerrain: false,
  minExpansionDist: '',
  maxExpansionDist: '',
};

const DEFAULT_GIMBAL_DIST: GimbalDistributionSnapshot = {
  peakConc: 200,
  baseConc: 3.3,
  outlierRate: 0.25,
  rho: 0.2,
};

function clamp(n: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, n));
}

function isNum(x: unknown): x is number {
  return typeof x === 'number' && Number.isFinite(x);
}

function isStr(x: unknown): x is string {
  return typeof x === 'string';
}

function isBool(x: unknown): x is boolean {
  return typeof x === 'boolean';
}

export function defaultRealPathForm(): RealPathFormSnapshot {
  return { ...DEFAULT_REAL_PATH };
}

export function defaultGimbalDistribution(): GimbalDistributionSnapshot {
  return { ...DEFAULT_GIMBAL_DIST };
}

/** Build a strict v1 snapshot from raw values (for copy). */
export function buildCameraOverlapFlightConfig(input: Omit<CameraOverlapFlightConfigV1, 'version'>): CameraOverlapFlightConfigV1 {
  return {
    version: CAMERA_OVERLAP_FLIGHT_CONFIG_VERSION,
    ...input,
    handles: input.handles.slice(0, 4),
    pitchSequenceNeg: [...input.pitchSequenceNeg],
    gimbalDistribution: { ...input.gimbalDistribution },
    realPath: { ...input.realPath },
  };
}

export type ParseFlightConfigResult =
  | { ok: true; config: CameraOverlapFlightConfigV1 }
  | { ok: false; error: string };

/**
 * Parse clipboard JSON into a v1 config with validation and safe clamps.
 */
function stripMarkdownJsonFence(raw: string): string {
  const t = raw.trim();
  if (!t.startsWith('```')) {
    return t;
  }
  const withoutStart = t.replace(/^```(?:json)?\s*\r?\n?/i, '');
  return withoutStart.replace(/\r?\n?```\s*$/i, '').trim();
}

export function parseCameraOverlapFlightConfigJson(raw: string): ParseFlightConfigResult {
  const cleaned = stripMarkdownJsonFence(raw);
  let parsed: unknown;
  try {
    parsed = JSON.parse(cleaned);
  } catch {
    return { ok: false, error: 'Invalid JSON' };
  }

  if (!parsed || typeof parsed !== 'object') {
    return { ok: false, error: 'Config must be a JSON object' };
  }

  const o = parsed as Record<string, unknown>;
  if (o.version !== 1) {
    return { ok: false, error: 'Unsupported version (expected 1)' };
  }

  const workflowMode = o.workflowMode === 'realPath' ? 'realPath' : 'straight';

  const height = clamp(isNum(o.height) ? o.height : 200, 50, 400);

  let handles: number[] = [10, 100, 190, 280];
  if (Array.isArray(o.handles) && o.handles.length >= 4) {
    handles = o.handles.slice(0, 4).map((h, i) => {
      const v = isNum(h) ? h : handles[i];
      return ((v % 360) + 360) % 360;
    });
  }

  const se = o.speedEnv && typeof o.speedEnv === 'object' ? (o.speedEnv as Record<string, unknown>) : {};
  const speedEnv = {
    loAglFt: clamp(isNum(se.loAglFt) ? se.loAglFt : 200, 50, 900),
    loMph: clamp(isNum(se.loMph) ? se.loMph : 17, 1, 30),
    hiAglFt: clamp(isNum(se.hiAglFt) ? se.hiAglFt : 400, 50, 900),
    hiMph: clamp(isNum(se.hiMph) ? se.hiMph : 22, 1, 30),
  };

  const minAngle = clamp(isNum(o.minAngle) ? o.minAngle : 15, 5, 30);
  let minAngleHeight = clamp(isNum(o.minAngleHeight) ? o.minAngleHeight : 200, 50, 1000);
  const maxAngle = clamp(isNum(o.maxAngle) ? o.maxAngle : 35, 15, 60);
  let maxAngleHeight = clamp(isNum(o.maxAngleHeight) ? o.maxAngleHeight : 400, 50, 1000);
  if (minAngleHeight >= maxAngleHeight) {
    minAngleHeight = Math.max(50, maxAngleHeight - 1);
  }

  const customCaptureRing = isBool(o.customCaptureRing) ? o.customCaptureRing : false;
  const viewerPathLengthFt = clamp(isNum(o.viewerPathLengthFt) ? o.viewerPathLengthFt : 150, 1, 5000);

  const pitchSequenceNeg = Array.isArray(o.pitchSequenceNeg)
    ? o.pitchSequenceNeg.filter(isNum).map((n) => -Math.abs(n))
    : [];

  const spinMode = isBool(o.spinMode) ? o.spinMode : false;

  const captureIntervalFt = clamp(isNum(o.captureIntervalFt) ? o.captureIntervalFt : 6, 1, 50);
  const captureIntervalSec = clamp(isNum(o.captureIntervalSec) ? o.captureIntervalSec : 1.5, 0.5, 10);
  const captureIntervalUnit = o.captureIntervalUnit === 'ft' ? 'ft' : 's';

  const gdIn = o.gimbalDistribution && typeof o.gimbalDistribution === 'object'
    ? (o.gimbalDistribution as Record<string, unknown>)
    : {};
  const gimbalDistribution: GimbalDistributionSnapshot = {
    peakConc: clamp(isNum(gdIn.peakConc) ? gdIn.peakConc : DEFAULT_GIMBAL_DIST.peakConc, 3, 300),
    baseConc: clamp(isNum(gdIn.baseConc) ? gdIn.baseConc : DEFAULT_GIMBAL_DIST.baseConc, 2.1, 12),
    outlierRate: clamp(isNum(gdIn.outlierRate) ? gdIn.outlierRate : DEFAULT_GIMBAL_DIST.outlierRate, 0, 0.5),
    rho: clamp(isNum(gdIn.rho) ? gdIn.rho : DEFAULT_GIMBAL_DIST.rho, 0, 0.95),
  };

  const rpIn = o.realPath && typeof o.realPath === 'object' ? (o.realPath as Record<string, unknown>) : {};
  const realPath: RealPathFormSnapshot = {
    center: isStr(rpIn.center) ? rpIn.center : DEFAULT_REAL_PATH.center,
    batteryMinutes: isStr(rpIn.batteryMinutes) ? rpIn.batteryMinutes : DEFAULT_REAL_PATH.batteryMinutes,
    batteries: isStr(rpIn.batteries) ? rpIn.batteries : DEFAULT_REAL_PATH.batteries,
    minHeight: isStr(rpIn.minHeight) ? rpIn.minHeight : DEFAULT_REAL_PATH.minHeight,
    maxHeight: isStr(rpIn.maxHeight) ? rpIn.maxHeight : DEFAULT_REAL_PATH.maxHeight,
    formToTerrain: isBool(rpIn.formToTerrain) ? rpIn.formToTerrain : DEFAULT_REAL_PATH.formToTerrain,
    minExpansionDist: isStr(rpIn.minExpansionDist) ? rpIn.minExpansionDist : DEFAULT_REAL_PATH.minExpansionDist,
    maxExpansionDist: isStr(rpIn.maxExpansionDist) ? rpIn.maxExpansionDist : DEFAULT_REAL_PATH.maxExpansionDist,
  };

  const config = buildCameraOverlapFlightConfig({
    workflowMode,
    height,
    handles,
    speedEnv,
    minAngle,
    minAngleHeight,
    maxAngle,
    maxAngleHeight,
    customCaptureRing,
    viewerPathLengthFt,
    pitchSequenceNeg,
    spinMode,
    captureIntervalFt,
    captureIntervalSec,
    captureIntervalUnit,
    gimbalDistribution,
    realPath,
  });

  return { ok: true, config };
}
