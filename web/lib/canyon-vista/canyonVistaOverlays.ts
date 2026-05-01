/**
 * Canyon-Vista overlay data (HansenHomeAI/Canyon-Vista). Images load from the upstream repo.
 */
import type { V3 } from "./types";

export const CANYON_VISTA_REMOTE_BASE = "https://raw.githubusercontent.com/HansenHomeAI/Canyon-Vista/main";
const ABSOLUTE_PHOTO_URL_PATTERN = /^(https:|http:|data:|blob:)/i;

export function canyonAssetUrl(relativePath: string): string {
  if (ABSOLUTE_PHOTO_URL_PATTERN.test(relativePath)) {
    return relativePath;
  }
  const p = relativePath.startsWith("/") ? relativePath.slice(1) : relativePath;
  return `${CANYON_VISTA_REMOTE_BASE}/${p}`;
}

export type TapDotConfig = {
  position: V3;
  scale: number;
  icon: "camera" | "info";
  caption: string;
  /** Paths relative to Canyon-Vista repo root, or full public image URLs. */
  photos: string[];
};

/** Single hole index 0 — Canyon Vista */
export const CANYON_VISTA_TAP_DOTS: TapDotConfig[] = [
  {
    position: { x: -0.193602, y: -0.057, z: 0.341913 },
    scale: 0.225,
    icon: "camera",
    caption: "Playground",
    photos: [
      "assets/playground/playground-01.jpg",
      "assets/playground/playground-02.jpg",
      "assets/playground/playground-03.jpg",
      "assets/playground/playground-04.jpg",
      "assets/playground/playground-05.jpg",
      "assets/playground/playground-06.jpg",
    ],
  },
  {
    position: { x: 0.455091, y: -0.057, z: 0.414509 },
    scale: 0.225,
    icon: "camera",
    caption: "Pool Area",
    photos: [
      "assets/pool/pool-01.jpg",
      "assets/pool/pool-02.jpg",
      "assets/pool/pool-03.jpg",
      "assets/pool/pool-04.jpg",
      "assets/pool/pool-05.jpg",
      "assets/pool/pool-06.jpg",
    ],
  },
  {
    position: { x: 0.091675, y: -0.057, z: -0.267314 },
    scale: 0.225,
    icon: "camera",
    caption: "Courtyard Park",
    photos: [
      "assets/courtyard-park/courtyard-park-01.jpg",
      "assets/courtyard-park/courtyard-park-02.jpg",
      "assets/courtyard-park/courtyard-park-03.jpg",
      "assets/courtyard-park/courtyard-park-04.jpg",
      "assets/courtyard-park/courtyard-park-05.jpg",
      "assets/courtyard-park/courtyard-park-06.jpg",
      "assets/courtyard-park/courtyard-park-07.jpg",
    ],
  },
];

export type BorderDotConfig = { name: string; position: V3 };

export const CANYON_VISTA_BORDER_DOTS: BorderDotConfig[] = [
  { name: "Lot_V1", position: { x: 0.619899, y: -0.07236, z: 0.910146 } },
  { name: "Lot_V4", position: { x: 0.613988, y: -0.12955, z: -0.646242 } },
  { name: "Lot_V5", position: { x: 0.432838, y: -0.1341, z: -0.769965 } },
  { name: "Lot_V6", position: { x: 0.356929, y: -0.13712, z: -0.852191 } },
  { name: "Lot_V7", position: { x: 0.134329, y: -0.139, z: -0.90331 } },
  { name: "Lot_V8", position: { x: 0.047765, y: -0.14156, z: -0.972969 } },
  { name: "Lot_V9", position: { x: -0.858899, y: -0.15415, z: -1.315852 } },
  { name: "Lot_V10", position: { x: -0.903571, y: -0.15539, z: -1.3497 } },
  { name: "Lot_V11", position: { x: -1.743049, y: -0.152, z: -1.527306 } },
  { name: "Lot_V12", position: { x: -1.877436, y: -0.105, z: -0.181094 } },
  { name: "Lot_V13", position: { x: -1.830478, y: -0.06, z: 0.921714 } },
  { name: "Lot_V15", position: { x: -0.851375, y: -0.12134, z: -0.344962 } },
  { name: "Lot_V16", position: { x: -0.860571, y: -0.07236, z: 0.910337 } },
  { name: "Lot_V18", position: { x: 0.608931, y: -0.09746, z: 0.230155 } },
  { name: "Lot_V19", position: { x: -0.907887, y: -0.15727, z: -1.432879 } },
  { name: "Lot_V20", position: { x: -0.970607, y: -0.1613, z: -1.52137 } },
  { name: "Lot_V21", position: { x: 0.480793, y: -0.09984, z: 0.164791 } },
  { name: "Lot_V22", position: { x: -0.208798, y: -0.14321, z: -1.079954 } },
  { name: "Lot_V23", position: { x: -0.68705, y: -0.15194, z: -1.24425 } },
  { name: "Lot_V24", position: { x: -0.520112, y: -0.14624, z: -1.139954 } },
  { name: "Lot_V25", position: { x: -0.140558, y: -0.14154, z: -1.024829 } },
];

export const CANYON_BORDER_BY_NAME = new Map<string, BorderDotConfig>(
  CANYON_VISTA_BORDER_DOTS.map((b) => [b.name, b]),
);

export const CANYON_VISTA_BORDER_LINES: { start: string; end: string }[] = [
  { start: "Lot_V1", end: "Lot_V18" },
  { start: "Lot_V18", end: "Lot_V4" },
  { start: "Lot_V4", end: "Lot_V5" },
  { start: "Lot_V5", end: "Lot_V6" },
  { start: "Lot_V6", end: "Lot_V7" },
  { start: "Lot_V7", end: "Lot_V8" },
  { start: "Lot_V8", end: "Lot_V25" },
  { start: "Lot_V25", end: "Lot_V22" },
  { start: "Lot_V22", end: "Lot_V24" },
  { start: "Lot_V24", end: "Lot_V23" },
  { start: "Lot_V23", end: "Lot_V9" },
  { start: "Lot_V9", end: "Lot_V10" },
  { start: "Lot_V10", end: "Lot_V19" },
  { start: "Lot_V19", end: "Lot_V20" },
  { start: "Lot_V20", end: "Lot_V11" },
  { start: "Lot_V11", end: "Lot_V12" },
  { start: "Lot_V12", end: "Lot_V13" },
  { start: "Lot_V13", end: "Lot_V16" },
  { start: "Lot_V16", end: "Lot_V1" },
  { start: "Lot_V16", end: "Lot_V15" },
  { start: "Lot_V15", end: "Lot_V9" },
  { start: "Lot_V18", end: "Lot_V21" },
  { start: "Lot_V21", end: "Lot_V15" },
];

export function compassArrowRotationDeg(
  cameraPos: V3,
  orbitTarget: V3,
  northDirectionDeg: number,
): number {
  const deltaX = cameraPos.x - orbitTarget.x;
  const deltaZ = cameraPos.z - orbitTarget.z;
  const cameraBearing = ((Math.atan2(deltaX, deltaZ) * 180) / Math.PI + 360) % 360;
  return (northDirectionDeg - cameraBearing + 360) % 360;
}

/** Optional “SOLD” labels (Canyon-Vista had this block commented; we ship one demo point). */
export type SoldHotspotConfig = {
  text: string;
  position: V3;
  scale: number;
  verticalOffset: number;
};

export const CANYON_VISTA_SOLD_HOTSPOTS: SoldHotspotConfig[] = [
  { text: "SOLD", position: { x: 0.22, y: 0.5, z: -0.85 }, scale: 0.2, verticalOffset: 0.06 },
];

/** Orbit camera position in XZ so bearing matches `northDirectionDeg` (Canyon-Vista `animateCameraToNorth`). */
export function computeNorthFacingPosition(current: V3, orbitTarget: V3, northDirectionDeg: number): V3 {
  const dx = current.x - orbitTarget.x;
  const dz = current.z - orbitTarget.z;
  const r = Math.hypot(dx, dz);
  const rad = (northDirectionDeg * Math.PI) / 180;
  return {
    x: orbitTarget.x + Math.sin(rad) * r,
    y: current.y,
    z: orbitTarget.z + Math.cos(rad) * r,
  };
}
