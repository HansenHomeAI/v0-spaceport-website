import type { PathAnimationState, PathCheckpoint, V3 } from "./types";

function sanitizePathVector(raw: Partial<V3> | undefined, fallback: V3): V3 {
  return {
    x: Number.isFinite(raw?.x) ? raw!.x! : fallback.x,
    y: Number.isFinite(raw?.y) ? raw!.y! : fallback.y,
    z: Number.isFinite(raw?.z) ? raw!.z! : fallback.z,
  };
}

export function sanitizePathCheckpoint(
  rawCheckpoint: Partial<{ position: Partial<V3>; lookAt: Partial<V3>; duration: number }> | undefined,
  baseCamera: V3,
  baseLookAt: V3,
): PathCheckpoint {
  const position = sanitizePathVector(rawCheckpoint?.position, baseCamera);
  const lookAt = sanitizePathVector(rawCheckpoint?.lookAt, baseLookAt);
  const duration =
    Number.isFinite(rawCheckpoint?.duration) && (rawCheckpoint!.duration as number) > 0.1
      ? (rawCheckpoint!.duration as number)
      : 5;
  return { position, lookAt, duration };
}

export function createInitialPathState(params: {
  checkpoints: PathCheckpoint[];
  enabled?: boolean;
  loop?: boolean;
  speed?: number;
}): PathAnimationState {
  const defaults = params;
  return {
    enabled: defaults.enabled !== false,
    loop: defaults.loop !== false,
    speed: Number.isFinite(defaults.speed) && (defaults.speed as number) > 0 ? (defaults.speed as number) : 1,
    checkpoints: defaults.checkpoints,
    playing: false,
    segmentIndex: 0,
    segmentElapsed: 0,
    lookAtOverrideAtStart: null,
  };
}

export function getPathSegmentCount(state: PathAnimationState): number {
  const count = state.checkpoints.length;
  if (count < 2) return 0;
  return state.loop ? count : count - 1;
}

function getPathIndex(state: PathAnimationState, index: number): number {
  const count = state.checkpoints.length;
  if (!count) return 0;
  if (state.loop) {
    return ((index % count) + count) % count;
  }
  return Math.min(Math.max(index, 0), count - 1);
}

function getPathCheckpoint(state: PathAnimationState, index: number): PathCheckpoint {
  return state.checkpoints[getPathIndex(state, index)];
}

function getPathDurationForSegment(state: PathAnimationState, segmentIndex: number): number {
  const checkpoint = getPathCheckpoint(state, segmentIndex);
  if (!checkpoint) return 5;
  return Math.max(0.1, checkpoint.duration || 5);
}

function catmullRomScalar(p0: number, p1: number, p2: number, p3: number, t: number): number {
  const t2 = t * t;
  const t3 = t2 * t;
  return (
    0.5 *
    (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
  );
}

function catmullRomVector(
  v0: V3,
  v1: V3,
  v2: V3,
  v3: V3,
  t: number,
  out: V3,
): void {
  out.x = catmullRomScalar(v0.x, v1.x, v2.x, v3.x, t);
  out.y = catmullRomScalar(v0.y, v1.y, v2.y, v3.y, t);
  out.z = catmullRomScalar(v0.z, v1.z, v2.z, v3.z, t);
}

/**
 * Writes camera position and look-at for the current segment and progress (Canyon-Vista Catmull–Rom path).
 */
export function applyPathPose(
  state: PathAnimationState,
  segmentIndex: number,
  progress: number,
  outPos: V3,
  outTarget: V3,
): void {
  const checkpointCount = state.checkpoints.length;
  const segmentCount = getPathSegmentCount(state);
  if (!segmentCount || checkpointCount < 2) return;
  const clampedProgress = Math.min(Math.max(progress, 0), 1);
  const i1 = state.loop
    ? getPathIndex(state, segmentIndex)
    : Math.min(Math.max(segmentIndex, 0), checkpointCount - 2);
  const i2 = state.loop ? getPathIndex(state, i1 + 1) : Math.min(i1 + 1, checkpointCount - 1);
  const p0 = getPathCheckpoint(state, i1 - 1).position;
  const p1 = getPathCheckpoint(state, i1).position;
  const p2 = getPathCheckpoint(state, i2).position;
  const p3 = getPathCheckpoint(state, i2 + 1).position;
  const l0 = getPathCheckpoint(state, i1 - 1).lookAt;
  const l1 = getPathCheckpoint(state, i1).lookAt;
  const l2 = getPathCheckpoint(state, i2).lookAt;
  const l3 = getPathCheckpoint(state, i2 + 1).lookAt;
  catmullRomVector(p0, p1, p2, p3, clampedProgress, outPos);
  catmullRomVector(l0, l1, l2, l3, clampedProgress, outTarget);
  const override = state.lookAtOverrideAtStart;
  if (override && segmentIndex === 0 && clampedProgress < 0.02) {
    outTarget.x = override.x;
    outTarget.y = override.y;
    outTarget.z = override.z;
    if (clampedProgress >= 0.015) state.lookAtOverrideAtStart = null;
  }
}

export type PathTickResult = { ended: boolean };

/** Advance path playback; mutates `state`. Call `applyPathPose` after for the current frame. */
export function updatePathAnimation(state: PathAnimationState, deltaSeconds: number): PathTickResult {
  let ended = false;
  if (!state.enabled || !state.playing) return { ended: false };
  const segmentCount = getPathSegmentCount(state);
  if (!segmentCount) {
    state.playing = false;
    return { ended: false };
  }
  let remaining = Math.max(0, deltaSeconds * state.speed);
  while (remaining > 0 && state.playing) {
    const duration = getPathDurationForSegment(state, state.segmentIndex);
    const segmentRemaining = Math.max(0, duration - state.segmentElapsed);
    if (remaining < segmentRemaining) {
      state.segmentElapsed += remaining;
      remaining = 0;
      break;
    }
    remaining -= segmentRemaining;
    if (state.loop) {
      state.segmentIndex = (state.segmentIndex + 1) % segmentCount;
      state.segmentElapsed = 0;
      continue;
    }
    const lastSegment = segmentCount - 1;
    if (state.segmentIndex >= lastSegment) {
      state.segmentElapsed = getPathDurationForSegment(state, state.segmentIndex);
      state.playing = false;
      ended = true;
      remaining = 0;
      break;
    }
    state.segmentIndex += 1;
    state.segmentElapsed = 0;
  }
  return { ended };
}

export function getCurrentPathProgress(state: PathAnimationState): number {
  const duration = getPathDurationForSegment(state, state.segmentIndex);
  return duration > 0 ? Math.min(state.segmentElapsed / duration, 1) : 1;
}

/** Apply pose for the current playback state (after `updatePathAnimation`). */
export function samplePathCamera(state: PathAnimationState, outPos: V3, outTarget: V3): void {
  const progress = getCurrentPathProgress(state);
  applyPathPose(state, state.segmentIndex, progress, outPos, outTarget);
}

/** Reset to path start (optional primary-focus override for compass “animation start”). */
export function jumpToPathStart(state: PathAnimationState, primaryFocus: V3 | null): void {
  if (!state.checkpoints.length) return;
  state.segmentIndex = 0;
  state.segmentElapsed = 0;
  state.lookAtOverrideAtStart = primaryFocus ? { ...primaryFocus } : null;
  state.playing = state.checkpoints.length >= 2;
}

/** Auto-orbit: camera on circle in XZ, looking at fixed target (Canyon-Vista `animate` branch). */
export function sampleAutoRotatePose(
  angleRad: number,
  center: V3,
  startRadius: number,
  orbitTarget: V3,
  cameraStartY: number,
  outPos: V3,
): void {
  outPos.x = center.x + Math.sin(angleRad) * startRadius;
  outPos.z = center.z + Math.cos(angleRad) * startRadius;
  outPos.y = center.y + cameraStartY;
  /* look-at is orbitTarget — caller sends as `target` in sogs:cameraLookAt */
}
