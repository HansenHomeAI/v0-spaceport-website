/** 3D vector (Canyon-Vista / Three.js style: x, y, z). */

export type V3 = { x: number; y: number; z: number };

export type PathCheckpoint = {
  position: V3;
  lookAt: V3;
  duration: number;
};

export type PathAnimationState = {
  enabled: boolean;
  loop: boolean;
  speed: number;
  checkpoints: PathCheckpoint[];
  playing: boolean;
  segmentIndex: number;
  segmentElapsed: number;
  lookAtOverrideAtStart: V3 | null;
};
