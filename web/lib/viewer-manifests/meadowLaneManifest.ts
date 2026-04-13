import {
  CANYON_VISTA_BORDER_DOTS,
  CANYON_VISTA_BORDER_LINES,
  CANYON_VISTA_SOLD_HOTSPOTS,
  CANYON_VISTA_TAP_DOTS,
  canyonAssetUrl,
} from "../canyon-vista/canyonVistaOverlays";
import type { ViewerManifest } from "../manifest-viewer/manifest";

const DEFAULT_BUNDLE_URL =
  "https://spaceport-ml-processing-staging.s3.amazonaws.com/compressed/meadow-brassmatch-compress-20260413-lod-streaming-hqsh-horizon-public/supersplat_bundle/";

export const meadowLaneManifest: ViewerManifest = {
  slug: "meadow-ln",
  text: {
    pageTitle: "Incognito",
    pageDescription:
      "Incognito — a private Bozeman estate beneath the Bridger Mountains: refined lodge warmth, modern ranch scale, and Montana privacy.",
    hiddenTitle: "Incognito",
    iframeTitle: "meadow-ln-viewer",
  },
  bundle: {
    defaultUrl: DEFAULT_BUNDLE_URL,
    skybox: {
      type: "adjacent-file",
      fileName: "background_skybox.webp",
      pitch: 0,
      vOffset: 0,
    },
    viewerBase: "/supersplat-viewer/index.html",
    viewerSettingsPath: "/supersplat-viewer/settings.json",
    useProxy: false,
    streaming: {
      budgetDesktop: 0,
      budgetMobile: 250000,
      lodMin: 0,
      lodMaxDesktop: 2,
      lodMaxMobile: 3,
      lodDistancesDesktop: [30, 140, 320, 640],
      lodDistancesMobile: [12, 48, 120, 280],
      lodUnderfillLimit: 0,
      lodUpdateDistance: 0.5,
      lodUpdateAngle: 1,
      colorUpdateDistance: 0.1,
      colorUpdateAngle: 1,
      colorUpdateDistanceLodScale: 1.4,
      colorUpdateAngleLodScale: 1.4,
    },
  },
  scene: {
    position: [0.03, 0.18, -0.06],
    rotation: [91, 80, -179.2],
    scale: 1,
    fov: 60,
    skyboxRotation: [90, 0, 0],
    showWorldAxes: false,
    focusTarget: { x: -0.006600170184592136, y: 0.002587578995479123, z: -0.010300579670372907 },
  },
  holeView: {
    startPosition: { x: 0.22, y: 0.6, z: 2.75 },
    target: { x: 0, y: -0.06, z: 0 },
    minDistance: 0.65,
    maxDistance: 10.4,
    minPolarAngle: 14,
    maxPolarAngle: 179,
    northDirection: 358,
  },
  holes: [
    {
      id: "incognito",
      label: "Incognito",
      bundleUrl: DEFAULT_BUNDLE_URL,
    },
  ],
  orbit: {
    autoRotateDefault: false,
    speed: -0.0015,
    startRadius: 2.8,
    initialAngle: 292,
    center: { x: 0, y: -0.06, z: 0 },
  },
  intro: {
    revealDurationMs: 2800,
    autoPlayPathOnFirstReady: true,
    autoPlayDelayMs: 400,
  },
  compass: {
    mode: "animationStart",
  },
  details: {
    title: "Incognito",
    paragraphs: [
      "Tucked into nearly 30 acres beneath the Bridger Mountains, Incognito is a private Bozeman estate that blends the warmth of a refined lodge with the scale and flexibility of a modern ranch property. It is secluded without feeling remote—composed to support both solitude and gathering.",
      "The residence carries a strong sense of atmosphere: generous interior volume, natural materials, and a layout that feels equally suited to quiet retreat, creative work, and long-form hosting. An attached studio and guest apartment expand the property beyond a single-home experience, giving it a layered, adaptable character.",
      "Across the grounds, the estate reads as both polished and usable. The setting, views, and open land give the property its privacy, while the architecture and updated interiors keep it elevated and intentional rather than rustic for its own sake.",
      "Incognito is less about display than control—a hidden, fully formed retreat with presence, flexibility, and a distinctly Montana sense of distance.",
    ],
  },
  cameraBounds: {
    yMin: 0,
    maxRadiusFromOrigin: 1.2,
  },
  path: {
    enabled: true,
    loop: true,
    speed: 1,
    checkpoints: [
      {
        position: { x: -1.0314528349656162, y: 0.19211051841218524, z: -0.04821209286310063 },
        lookAt: { x: -0.006600170184592136, y: 0.002587578995479123, z: -0.010300579670372907 },
        duration: 5,
      },
      {
        position: { x: -0.6813023767852142, y: 0.12631993118022503, z: -0.7096817169047558 },
        lookAt: { x: -0.006600170184592136, y: 0.002587578995479123, z: -0.0103005796703729 },
        duration: 5,
      },
      {
        position: { x: -0.058167301989511436, y: 0.13338259919975387, z: -0.9797850980074916 },
        lookAt: { x: -0.006600170184592129, y: 0.0025875789954791506, z: -0.010300579670373011 },
        duration: 5,
      },
      {
        position: { x: 0.6305656273628224, y: 0.13245692700670272, z: -0.742980889608537 },
        lookAt: { x: -0.006600170184592025, y: 0.002587578995479123, z: -0.01030057967037279 },
        duration: 5,
      },
      {
        position: { x: 0.5854652711614696, y: 0.06151905108842326, z: -0.2889098793083718 },
        lookAt: { x: -0.006600170184592136, y: 0.00258757899547913, z: -0.01030057967037279 },
        duration: 5,
      },
      {
        position: { x: 0.4154039592229669, y: 0.08212920801278735, z: 0.16035842827325011 },
        lookAt: { x: -0.006600170184592136, y: 0.002587578995479123, z: -0.010300579670372872 },
        duration: 5,
      },
      {
        position: { x: 0.19310895544290083, y: 0.10233801028969992, z: 0.4160332454752667 },
        lookAt: { x: -0.006600170184592163, y: 0.002587578995479123, z: -0.0103005796703729 },
        duration: 5,
      },
      {
        position: { x: -0.22472329124403184, y: 0.09689303629406917, z: 0.15734760326588526 },
        lookAt: { x: -0.006600170184592163, y: 0.0025875789954791367, z: -0.010300579670372845 },
        duration: 5,
      },
      {
        position: { x: -0.22987646826404634, y: 0.06793459857665755, z: -0.14681861289905374 },
        lookAt: { x: -0.006600170184592136, y: 0.002587578995479123, z: -0.010300579670372845 },
        duration: 5,
      },
      {
        position: { x: 0.12888691111714234, y: 0.06570214767271616, z: -0.14217585280981712 },
        lookAt: { x: -0.006600170184592136, y: 0.002587578995479123, z: -0.010300579670372817 },
        duration: 5,
      },
      {
        position: { x: 0.5877298846363819, y: 0.3375942570927207, z: 0.3586888823432408 },
        lookAt: { x: -0.006600170184592136, y: 0.002587578995479123, z: -0.010300579670372845 },
        duration: 5,
      },
      {
        position: { x: -0.06392778871572002, y: 0.30059022901591587, z: 0.7166016148244266 },
        lookAt: { x: 0.002332758642647134, y: 0.003858392008141198, z: -0.0009804947738712988 },
        duration: 5,
      },
    ],
  },
  overlays: {
    tapDots: CANYON_VISTA_TAP_DOTS.map((tapDot) => ({
      ...tapDot,
      photos: tapDot.photos.map(canyonAssetUrl),
    })),
    borderDots: CANYON_VISTA_BORDER_DOTS,
    borderLines: CANYON_VISTA_BORDER_LINES,
    soldHotspots: CANYON_VISTA_SOLD_HOTSPOTS,
  },
  defaults: {
    showTapDots: false,
    showLotLines: false,
    showSoldLabels: false,
  },
};
