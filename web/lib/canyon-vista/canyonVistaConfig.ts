/**
 * Canyon-Vista viewer defaults (ported from HansenHomeAI/Canyon-Vista index.html).
 * SOGS splat framing uses SOGS_DEFAULT_SCENE; camera tours use coordinates from the original Luma build.
 */
import type { PathCheckpoint, V3 } from "./types";

export const CANYON_VISTA_SCENE_ORIGIN: V3 = { x: 0, y: -0.06, z: 0 };

/** Selectable holes (extend with `bundleUrl` when multiple SOGS bundles exist). */
export type CanyonHoleConfig = {
  id: string;
  label: string;
  /** If omitted, the app default bundle URL is used. */
  bundleUrl?: string;
};

export const CANYON_VISTA_HOLES: CanyonHoleConfig[] = [{ id: "canyon-vista", label: "Canyon Vista" }];

/** Single-hole layout: SOGS bundle URL is supplied at runtime (?url=). */
export const CANYON_VISTA_HOLE_VIEW = {
  startPosition: { x: 0.22, y: 0.6, z: 2.75 } as V3,
  target: { x: 0, y: -0.06, z: 0 } as V3,
  minDistance: 0.65,
  maxDistance: 10.4,
  minPolarAngle: 14,
  maxPolarAngle: 179,
  /** Degrees: positive Z = 0; matches Canyon-Vista `compass.northDirection`. */
  northDirection: 358,
};

export const CANYON_VISTA_ORBIT = {
  autoRotateDefault: false,
  speed: -0.0015,
  startRadius: 2.8,
  /** degrees */
  initialAngle: 292,
  center: { x: 0, y: -0.06, z: 0 } as V3,
};

/** Matches Canyon-Vista `compass.northButtonMode`. */
export type CanyonCompassNorthMode = "north" | "animationStart";

export const CANYON_VISTA_COMPASS: { northButtonMode: CanyonCompassNorthMode } = {
  northButtonMode: "animationStart",
};

/** Intro: fade from black + optional auto path (Canyon-Vista–style landing motion). */
export const CANYON_VISTA_INTRO = {
  revealDurationMs: 2800,
  autoPlayPathOnFirstReady: true,
  autoPlayDelayMs: 400,
};

/** Global default camera path (hole `path: null` defers to this in Canyon-Vista). */
export const CANYON_VISTA_DEFAULT_PATH_CHECKPOINTS: PathCheckpoint[] = [
  { position: { x: 1.582791, y: -0.07165, z: 1.155954 }, lookAt: { x: 0.1521, y: -0.180213, z: 0.600098 }, duration: 5 },
  { position: { x: -0.989708, y: -0.161084, z: 1.283174 }, lookAt: { x: -0.17469, y: -0.18147, z: -0.161278 }, duration: 5 },
  { position: { x: -1.530198, y: -0.097836, z: -1.906522 }, lookAt: { x: 2.724609, y: -0.227332, z: 3.281251 }, duration: 5 },
  { position: { x: -1.325258, y: -0.030263, z: -2.667343 }, lookAt: { x: 0.354004, y: -0.305945, z: 0.594727 }, duration: 5 },
  { position: { x: 1.444272, y: 0.169617, z: -0.76639 }, lookAt: { x: -0.090491, y: -0.217613, z: 0.15015 }, duration: 5 },
  { position: { x: 1.478771, y: 0.194052, z: 1.019511 }, lookAt: { x: 0.745117, y: -0.074988, z: 0.486328 }, duration: 5 },
  { position: { x: -1.265139, y: 0.211001, z: 1.352802 }, lookAt: { x: -0.423096, y: -0.072303, z: 0.484131 }, duration: 5 },
  { position: { x: -2.512238, y: 0.821241, z: -0.829907 }, lookAt: { x: -0.094055, y: -0.085242, z: -0.053162 }, duration: 5 },
  { position: { x: 0.342197, y: 0.528242, z: -3.460023 }, lookAt: { x: 0.077108, y: -0.104422, z: -0.347646 }, duration: 5 },
  { position: { x: 1.917807, y: 0.84939, z: 2.072994 }, lookAt: { x: 0.077108, y: -0.104422, z: -0.347646 }, duration: 5 },
];

/** Matches Canyon-Vista `parameters.camera.startPosition` for orbit height. */
export const CANYON_VISTA_CAMERA_START_Y = 0.55;
