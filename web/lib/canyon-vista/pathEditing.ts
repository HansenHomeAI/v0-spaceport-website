/** Mutations and serialization for the camera path editor (Canyon-Vista style). */
import type { PathAnimationState, PathCheckpoint, V3 } from "./types";
import { getPathSegmentCount } from "./pathAnimation";

export type SerializedPathPayload = {
  enabled: boolean;
  loop: boolean;
  speed: number;
  checkpoints: PathCheckpoint[];
};

export function serializePathPayload(state: PathAnimationState): SerializedPathPayload {
  return {
    enabled: state.enabled,
    loop: state.loop,
    speed: state.speed,
    checkpoints: state.checkpoints.map((c) => ({
      position: { ...c.position },
      lookAt: { ...c.lookAt },
      duration: c.duration,
    })),
  };
}

export function jumpToSegment(state: PathAnimationState, segmentIndex: number): void {
  const sc = getPathSegmentCount(state);
  if (sc <= 0) return;
  state.segmentIndex = Math.min(Math.max(0, segmentIndex), sc - 1);
  state.segmentElapsed = 0;
}

export function removeCheckpointAt(state: PathAnimationState, index: number): boolean {
  if (state.checkpoints.length <= 2) return false;
  if (index < 0 || index >= state.checkpoints.length) return false;
  state.checkpoints.splice(index, 1);
  const sc = getPathSegmentCount(state);
  if (sc <= 0) {
    state.segmentIndex = 0;
    state.playing = false;
    return true;
  }
  state.segmentIndex = Math.min(state.segmentIndex, sc - 1);
  return true;
}

export function appendCheckpoint(state: PathAnimationState, cp: PathCheckpoint): void {
  state.checkpoints.push({
    position: { ...cp.position },
    lookAt: { ...cp.lookAt },
    duration: Math.max(0.1, cp.duration || 5),
  });
}

export function setCheckpointDuration(state: PathAnimationState, index: number, duration: number): void {
  const c = state.checkpoints[index];
  if (!c) return;
  c.duration = Math.max(0.1, duration);
}

export function setPathSpeed(state: PathAnimationState, speed: number): void {
  state.speed = Number.isFinite(speed) && speed > 0 ? speed : 1;
}

export function setPathLoop(state: PathAnimationState, loop: boolean): void {
  state.loop = loop;
}

export function setPathEnabled(state: PathAnimationState, enabled: boolean): void {
  state.enabled = enabled;
}

/** Snap camera to the stored key pose at `index` (Canyon-Vista `applyPathCheckpoint`). */
export function snapCameraToCheckpointKey(state: PathAnimationState, index: number, outPos: V3, outTarget: V3): void {
  const cp = state.checkpoints[index];
  if (!cp) return;
  outPos.x = cp.position.x;
  outPos.y = cp.position.y;
  outPos.z = cp.position.z;
  outTarget.x = cp.lookAt.x;
  outTarget.y = cp.lookAt.y;
  outTarget.z = cp.lookAt.z;
  const sc = getPathSegmentCount(state);
  if (sc <= 0) return;
  state.segmentIndex = Math.min(Math.max(0, index), sc - 1);
  state.segmentElapsed = 0;
}
