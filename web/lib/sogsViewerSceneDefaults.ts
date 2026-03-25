/**
 * Default splat transform + camera FOV for the embedded SuperSplat viewer.
 * Paste JSON from the viewer’s “Copy scene JSON” into chat to update these values in code.
 */
export const SOGS_DEFAULT_SCENE = {
  position: [0, 0, 0] as [number, number, number],
  /** Euler ° (PlayCanvas order: X, Y, Z) */
  rotation: [0, 0, -90] as [number, number, number],
  scale: 1,
  fov: 60,
} as const;

export type SogsScenePayload = {
  position: [number, number, number];
  rotation: [number, number, number];
  scale: number;
  fov: number;
};

export function createDefaultScenePayload(): SogsScenePayload {
  return {
    position: [...SOGS_DEFAULT_SCENE.position],
    rotation: [...SOGS_DEFAULT_SCENE.rotation],
    scale: SOGS_DEFAULT_SCENE.scale,
    fov: SOGS_DEFAULT_SCENE.fov,
  };
}

/** Clipboard payload for sharing tuned splat/camera values with maintainers. */
export function buildSogsSceneExport(params: {
  bundleUrl: string;
  scene: SogsScenePayload;
  guides: boolean;
}) {
  return {
    $schema: "spaceport/sogs-viewer/scene-v1",
    generatedAt: new Date().toISOString(),
    bundleUrl: params.bundleUrl,
    guides: params.guides,
    scene: {
      position: params.scene.position,
      rotation: params.scene.rotation,
      scale: params.scene.scale,
      fov: params.scene.fov,
    },
    codeHint:
      "To ship these as app defaults: update SOGS_DEFAULT_SCENE in web/lib/sogsViewerSceneDefaults.ts (and any matching initial state in SogsViewerDevPanel).",
  };
}
