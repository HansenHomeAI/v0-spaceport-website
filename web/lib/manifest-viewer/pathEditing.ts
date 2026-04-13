import { getPathSegmentCount } from "./pathAnimation";
import type { PathAnimationState, PathCheckpoint, V3 } from "./types";

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
    checkpoints: state.checkpoints.map((checkpoint) => ({
      position: { ...checkpoint.position },
      lookAt: { ...checkpoint.lookAt },
      duration: checkpoint.duration,
    })),
  };
}

export function removeCheckpointAt(state: PathAnimationState, index: number): boolean {
  if (state.checkpoints.length <= 2) return false;
  if (index < 0 || index >= state.checkpoints.length) return false;
  state.checkpoints.splice(index, 1);
  const segmentCount = getPathSegmentCount(state);
  if (segmentCount <= 0) {
    state.segmentIndex = 0;
    state.playing = false;
    return true;
  }
  state.segmentIndex = Math.min(state.segmentIndex, segmentCount - 1);
  return true;
}

export function appendCheckpoint(state: PathAnimationState, checkpoint: PathCheckpoint): void {
  state.checkpoints.push({
    position: { ...checkpoint.position },
    lookAt: { ...checkpoint.lookAt },
    duration: Math.max(0.1, checkpoint.duration || 5),
  });
}

export function setCheckpointDuration(state: PathAnimationState, index: number, duration: number): void {
  const checkpoint = state.checkpoints[index];
  if (!checkpoint) return;
  checkpoint.duration = Math.max(0.1, duration);
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

export function snapCameraToCheckpointKey(
  state: PathAnimationState,
  index: number,
  outPos: V3,
  outTarget: V3,
): void {
  const checkpoint = state.checkpoints[index];
  if (!checkpoint) return;
  outPos.x = checkpoint.position.x;
  outPos.y = checkpoint.position.y;
  outPos.z = checkpoint.position.z;
  outTarget.x = checkpoint.lookAt.x;
  outTarget.y = checkpoint.lookAt.y;
  outTarget.z = checkpoint.lookAt.z;
  const segmentCount = getPathSegmentCount(state);
  if (segmentCount <= 0) return;
  state.segmentIndex = Math.min(Math.max(0, index), segmentCount - 1);
  state.segmentElapsed = 0;
}
