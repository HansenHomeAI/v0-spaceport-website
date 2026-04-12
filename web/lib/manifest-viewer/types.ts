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

export type CameraPose = {
  position: V3;
  target: V3;
  fov: number;
};
