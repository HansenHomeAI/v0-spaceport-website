import type { PathCheckpoint, V3 } from "./types";

export type ViewerSceneManifest = {
  position: [number, number, number];
  rotation: [number, number, number];
  scale: number;
  fov: number;
  skyboxRotation?: [number, number, number];
  showWorldAxes?: boolean;
  focusTarget?: V3;
};

export type ViewerSkyboxManifest =
  | {
      type: "explicit";
      url: string | null;
      pitch?: number;
      vOffset?: number;
    }
  | {
      type: "adjacent-file";
      fileName: string;
      pitch?: number;
      vOffset?: number;
    }
  | {
      type: "spaceport-config";
      configFileName?: string;
      fallbackUrl?: string | null;
      pitch?: number;
      vOffset?: number;
    };

export type ViewerBundleManifest = {
  defaultUrl: string;
  skybox?: ViewerSkyboxManifest;
  preview?: ViewerPreviewManifest;
  viewerBase?: string;
  viewerSettingsPath?: string;
  useProxy?: boolean;
  streaming?: ViewerStreamingManifest;
};

export type ViewerPreviewManifest = {
  metaUrl?: string | null;
  configFileName?: string;
  fallbackUrl?: string | null;
  pointSize?: number;
  pointSizeDesktop?: number;
  pointSizeMobile?: number;
  initialVisiblePoints?: number;
  initialVisiblePointsDesktop?: number;
  initialVisiblePointsMobile?: number;
  revealDurationMs?: number;
  revealDurationDesktopMs?: number;
  revealDurationMobileMs?: number;
  fadeDelayMs?: number;
  fadeDelayDesktopMs?: number;
  fadeDelayMobileMs?: number;
  fadeDurationMs?: number;
  fadeDurationDesktopMs?: number;
  fadeDurationMobileMs?: number;
  minimumDisplayMs?: number;
  minimumDisplayDesktopMs?: number;
  minimumDisplayMobileMs?: number;
  revealChunkMetaCount?: number;
  revealChunkTextureCount?: number;
  skyboxFadeStart?: number;
};

export type ViewerStreamingManifest = {
  budget?: number;
  budgetDesktop?: number;
  budgetMobile?: number;
  lodMin?: number;
  lodMinDesktop?: number;
  lodMinMobile?: number;
  lodMax?: number | null;
  lodMaxDesktop?: number | null;
  lodMaxMobile?: number | null;
  lodDistances?: number[];
  lodDistancesDesktop?: number[];
  lodDistancesMobile?: number[];
  lodUnderfillLimit?: number;
  lodBehindPenalty?: number;
  lodUpdateDistance?: number;
  lodUpdateAngle?: number;
  colorUpdateDistance?: number;
  colorUpdateAngle?: number;
  colorUpdateDistanceLodScale?: number;
  colorUpdateAngleLodScale?: number;
};

export type ViewerHoleViewManifest = {
  startPosition: V3;
  target: V3;
  minDistance?: number;
  maxDistance?: number;
  minPolarAngle?: number;
  maxPolarAngle?: number;
  northDirection: number;
};

export type ViewerHoleManifest = {
  id: string;
  label: string;
  bundleUrl?: string;
  holeView?: Partial<ViewerHoleViewManifest>;
};

export type ViewerOrbitManifest = {
  autoRotateDefault?: boolean;
  speed: number;
  startRadius: number;
  initialAngle: number;
  center: V3;
};

export type ViewerIntroManifest = {
  revealDurationMs?: number;
  autoPlayPathOnFirstReady?: boolean;
  autoPlayDelayMs?: number;
};

export type ViewerCompassManifest = {
  mode?: "faceNorth" | "animationStart";
};

export type ViewerDetailsManifest = {
  title: string;
  paragraphs: string[];
};

export type ViewerToggleDefaultsManifest = {
  showTapDots?: boolean;
  showLotLines?: boolean;
  showSoldLabels?: boolean;
};

export type ViewerTapDotManifest = {
  position: V3;
  scale: number;
  icon: "camera" | "info";
  caption: string;
  photos: string[];
};

export type ViewerBorderDotManifest = {
  name: string;
  position: V3;
};

export type ViewerBorderLineManifest = {
  start: string;
  end: string;
};

export type ViewerSoldHotspotManifest = {
  text: string;
  position: V3;
  scale: number;
  verticalOffset: number;
};

export type ViewerOverlaysManifest = {
  tapDots?: ViewerTapDotManifest[];
  borderDots?: ViewerBorderDotManifest[];
  borderLines?: ViewerBorderLineManifest[];
  soldHotspots?: ViewerSoldHotspotManifest[];
};

export type ViewerTextManifest = {
  pageTitle: string;
  pageDescription: string;
  hiddenTitle: string;
  iframeTitle: string;
};

export type ViewerCameraBoundsManifest = {
  yMin: number;
  maxRadiusFromOrigin: number;
};

export type ViewerManifest = {
  slug: string;
  text: ViewerTextManifest;
  bundle: ViewerBundleManifest;
  scene: ViewerSceneManifest;
  holeView: ViewerHoleViewManifest;
  holes: ViewerHoleManifest[];
  orbit: ViewerOrbitManifest;
  intro?: ViewerIntroManifest;
  compass?: ViewerCompassManifest;
  details?: ViewerDetailsManifest;
  cameraBounds?: ViewerCameraBoundsManifest;
  path: {
    enabled?: boolean;
    loop?: boolean;
    speed?: number;
    checkpoints: PathCheckpoint[];
  };
  overlays?: ViewerOverlaysManifest;
  defaults?: ViewerToggleDefaultsManifest;
};

export function resolveHoleView(
  base: ViewerHoleViewManifest,
  hole: ViewerHoleManifest | undefined,
): ViewerHoleViewManifest {
  const override = hole?.holeView;
  if (!override) {
    return {
      ...base,
      startPosition: { ...base.startPosition },
      target: { ...base.target },
    };
  }

  return {
    ...base,
    ...override,
    startPosition: {
      ...base.startPosition,
      ...override.startPosition,
    },
    target: {
      ...base.target,
      ...override.target,
    },
  };
}

export function buildScenePayload(scene: ViewerSceneManifest) {
  return {
    position: [...scene.position] as [number, number, number],
    rotation: [...scene.rotation] as [number, number, number],
    scale: scene.scale,
    fov: scene.fov,
  };
}
