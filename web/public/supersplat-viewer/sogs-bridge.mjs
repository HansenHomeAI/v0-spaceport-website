/**
 * Spaceport SOGS bridge: postMessage API for parent page + optional RGB world axes (mesh, not drawLine overlay).
 */
import { main } from "./index.js";
import {
  Color,
  CylinderGeometry,
  Entity,
  Mesh,
  MeshInstance,
  Quat,
  StandardMaterial,
  Vec3,
} from "https://esm.sh/playcanvas@2.13.2";

/** Parent-driven camera (position + look-at). When `sogs:cameraMode` is `scripted`, orbit input is skipped. */
const tmpFrom = new Vec3();
const tmpTo = new Vec3();
/** Orbit focus point for `sogs:cameraPose` (parent overlays / Three.js projection). */
const tmpFocus = new Vec3();

/** PlayCanvas: camera looks down -Z; matches supersplat Camera.calcFocusPoint. */
const CAM_FORWARD = new Vec3(0, 0, -1);

const FOCUS_XZ_MAX = 10;
const FOCUS_Y = 0;

const AXIS_LEN = 45;
const AXIS_RADIUS = 0.28;

function finiteNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function sanitizeNumberList(value) {
  if (!Array.isArray(value) || value.length === 0) {
    return null;
  }
  const parsed = value.map((entry) => Number(entry));
  return parsed.every((entry) => Number.isFinite(entry)) ? parsed : null;
}

function resolveIntegerConfig(currentValue, incomingValue, min = 0) {
  if (finiteNumber(incomingValue) && incomingValue >= min) {
    return Math.trunc(incomingValue);
  }
  return currentValue ?? null;
}

function resolveNumberConfig(currentValue, incomingValue, min = 0) {
  if (finiteNumber(incomingValue) && incomingValue >= min) {
    return Number(incomingValue);
  }
  return currentValue ?? null;
}

function metricsSnapshot() {
  const metrics = window.__sogsNetworkMetrics ?? {};
  const firstFrame = metrics.firstFrame ?? null;
  return {
    loadedNodeCount: Array.isArray(metrics.uniqueChunkMetaUrls) ? metrics.uniqueChunkMetaUrls.length : 0,
    chunkMetaRequestCount: Array.isArray(metrics.uniqueChunkMetaUrls) ? metrics.uniqueChunkMetaUrls.length : 0,
    chunkMetaAtFirstFrame:
      firstFrame && finiteNumber(firstFrame.chunkMetaRequestCount) ? firstFrame.chunkMetaRequestCount : null,
    totalRequestCount: Array.isArray(metrics.events) ? metrics.events.length : 0,
    firstFrameMs:
      firstFrame && finiteNumber(firstFrame.at) && finiteNumber(metrics.loadStartedAt)
        ? firstFrame.at - metrics.loadStartedAt
        : null,
    rootManifestType: typeof metrics.rootManifestType === "string" ? metrics.rootManifestType : null,
    rootManifestUrl: typeof metrics.rootManifestUrl === "string" ? metrics.rootManifestUrl : null,
  };
}

function markFirstFrameIfReady() {
  const metrics = window.__sogsNetworkMetrics;
  if (!metrics || metrics.firstFrame) {
    return false;
  }

  const ctx = window.__sogsCtx;
  const hasGsplat = !!ctx?.app?.root?.findByName("gsplat");
  const chunkMetaRequestCount = Array.isArray(metrics.uniqueChunkMetaUrls)
    ? metrics.uniqueChunkMetaUrls.length
    : 0;
  const hasLodActivity =
    typeof metrics.rootManifestType === "string" &&
    metrics.rootManifestType === "lod-meta.json" &&
    chunkMetaRequestCount > 0;

  if (!hasGsplat || !hasLodActivity) {
    return false;
  }

  metrics.firstFrame = {
    at: performance.now(),
    chunkMetaRequestCount,
    totalRequestCount: Array.isArray(metrics.events) ? metrics.events.length : 0,
    source: "lod-telemetry",
  };
  window.parent.postMessage({ type: "supersplat:firstFrame" }, "*");
  return true;
}

window.firstFrame = function sogsFirstFrameHook() {
  const metrics = window.__sogsNetworkMetrics;
  if (metrics && !metrics.firstFrame) {
    metrics.firstFrame = {
      at: performance.now(),
      chunkMetaRequestCount: Array.isArray(metrics.uniqueChunkMetaUrls) ? metrics.uniqueChunkMetaUrls.length : 0,
      totalRequestCount: Array.isArray(metrics.events) ? metrics.events.length : 0,
    };
  }
  window.parent.postMessage({ type: "supersplat:firstFrame" }, "*");
  queueMicrotask(() => postSogsState());
};

function postSogsState() {
  try {
    const ctx = window.__sogsCtx;
    if (!ctx?.app || !ctx.camera) {
      return;
    }
    const g = ctx.app.root.findByName("gsplat");
    if (!g) {
      return;
    }
    const p = g.getLocalPosition();
    const e = g.getLocalEulerAngles();
    const sc = g.getLocalScale();
    const gsplatComponent = g.gsplat ?? null;
    const sceneGsplat = ctx.app.scene?.gsplat;
    markFirstFrameIfReady();
    const telemetry = metricsSnapshot();
    window.parent.postMessage(
      {
        type: "sogs:state",
        position: [p.x, p.y, p.z],
        rotation: [e.x, e.y, e.z],
        scale: sc.x,
        fov: ctx.camera.camera.fov,
        splatBudget: finiteNumber(sceneGsplat?.splatBudget) ? sceneGsplat.splatBudget : null,
        lodRangeMin: finiteNumber(sceneGsplat?.lodRangeMin) ? sceneGsplat.lodRangeMin : null,
        lodRangeMax: finiteNumber(sceneGsplat?.lodRangeMax) ? sceneGsplat.lodRangeMax : null,
        lodDistances: sanitizeNumberList(gsplatComponent?.lodDistances),
        lodUnderfillLimit: finiteNumber(sceneGsplat?.lodUnderfillLimit) ? sceneGsplat.lodUnderfillLimit : null,
        lodBehindPenalty: finiteNumber(sceneGsplat?.lodBehindPenalty) ? sceneGsplat.lodBehindPenalty : null,
        lodUpdateDistance: finiteNumber(sceneGsplat?.lodUpdateDistance) ? sceneGsplat.lodUpdateDistance : null,
        lodUpdateAngle: finiteNumber(sceneGsplat?.lodUpdateAngle) ? sceneGsplat.lodUpdateAngle : null,
        colorUpdateDistance: finiteNumber(sceneGsplat?.colorUpdateDistance) ? sceneGsplat.colorUpdateDistance : null,
        colorUpdateAngle: finiteNumber(sceneGsplat?.colorUpdateAngle) ? sceneGsplat.colorUpdateAngle : null,
        colorUpdateDistanceLodScale: finiteNumber(sceneGsplat?.colorUpdateDistanceLodScale)
          ? sceneGsplat.colorUpdateDistanceLodScale
          : null,
        colorUpdateAngleLodScale: finiteNumber(sceneGsplat?.colorUpdateAngleLodScale)
          ? sceneGsplat.colorUpdateAngleLodScale
          : null,
        ...telemetry,
      },
      "*",
    );
  } catch {
    /* ignore */
  }
}

function startSogsTelemetryPump() {
  const startedAt = performance.now();
  const id = window.setInterval(() => {
    markFirstFrameIfReady();
    postSogsState();
    const elapsed = performance.now() - startedAt;
    if (elapsed > 60000) {
      window.clearInterval(id);
    }
  }, 500);
}

/**
 * Wraps CameraManager.update: free orbit vs scripted pose from `window.__sogsCameraPose`.
 * `sogs:cameraMode` sets `window.__sogsScriptedCamera` (true = scripted).
 */
function postCameraPoseFromViewer(cameraManager) {
  try {
    if (window.__sogsScriptedCamera) {
      return;
    }
    const cam = cameraManager.camera;
    cam.calcFocusPoint(tmpFocus);
    window.parent.postMessage(
      {
        type: "sogs:cameraPose",
        position: [cam.position.x, cam.position.y, cam.position.z],
        target: [tmpFocus.x, tmpFocus.y, tmpFocus.z],
        fov: cam.fov,
      },
      "*",
    );
  } catch {
    /* ignore */
  }
}

function setupCameraManagerBridge(cameraManager) {
  const origUpdate = cameraManager.update.bind(cameraManager);
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

  const getFocusPoint = (cam) => {
    // `cam.angles` comes from the bundled viewer build, not the esm.sh Vec3 class.
    const q = new Quat().setFromEulerAngles(cam.angles.x, cam.angles.y, cam.angles.z);
    const dir = new Vec3();
    q.transformVector(CAM_FORWARD, dir);
    dir.mulScalar(cam.distance);
    return new Vec3().copy(cam.position).add(dir);
  };

  const setCameraFromFocus = (cam, focus) => {
    const q = new Quat().setFromEulerAngles(cam.angles.x, cam.angles.y, cam.angles.z);
    const dir = new Vec3();
    q.transformVector(CAM_FORWARD, dir);
    dir.mulScalar(cam.distance);
    cam.position.copy(focus).sub(dir);
  };

  const clampCameraFocus = (cam) => {
    const focus = getFocusPoint(cam);
    const fx = clamp(focus.x, -FOCUS_XZ_MAX, FOCUS_XZ_MAX);
    const fz = clamp(focus.z, -FOCUS_XZ_MAX, FOCUS_XZ_MAX);
    const fy = FOCUS_Y;
    if (fx !== focus.x || fz !== focus.z || Math.abs(fy - focus.y) > 1e-5) {
      focus.set(fx, fy, fz);
      setCameraFromFocus(cam, focus);
    }
  };

  cameraManager.update = (dt, frame) => {
    if (window.__sogsScriptedCamera) {
      const pose = window.__sogsCameraPose;
      if (pose?.position?.length === 3 && pose?.target?.length === 3) {
        tmpFrom.set(pose.position[0], pose.position[1], pose.position[2]);
        tmpTo.set(pose.target[0], pose.target[1], pose.target[2]);
        cameraManager.camera.look(tmpFrom, tmpTo);
        if (typeof pose.fov === "number" && Number.isFinite(pose.fov)) {
          cameraManager.camera.fov = pose.fov;
          window.__sogsUserFov = pose.fov;
        }
      }
    } else {
      origUpdate(dt, frame);
      if (typeof window.__sogsUserFov === "number" && Number.isFinite(window.__sogsUserFov)) {
        cameraManager.camera.fov = window.__sogsUserFov;
      }
      clampCameraFocus(cameraManager.camera);
      postCameraPoseFromViewer(cameraManager);
    }
  };
}

function installInitialCameraRelease(app) {
  if (window.__sogsInitialCameraReleaseInstalled) {
    return;
  }
  const release = () => {
    if (!window.__sogsScriptedCamera) {
      return;
    }
    window.__sogsScriptedCamera = false;
    app.renderNextFrame = true;
  };
  window.addEventListener("pointerdown", release, { capture: true });
  window.addEventListener("wheel", release, { capture: true, passive: true });
  window.addEventListener("keydown", release, { capture: true });
  window.__sogsInitialCameraReleaseInstalled = true;
}

function axisMaterial(rgb) {
  const m = new StandardMaterial();
  m.diffuse = new Color(0, 0, 0);
  m.emissive = new Color(rgb[0], rgb[1], rgb[2]);
  m.emissiveIntensity = 1;
  m.useLighting = false;
  return m;
}

function copyRenderLayers(fromEntity, toEntity) {
  try {
    const layers = fromEntity.render?.layers;
    if (layers?.length && toEntity.render) {
      toEntity.render.layers = layers.slice();
    }
  } catch {
    /* ignore */
  }
}

/**
 * Thin cylinders along local +X / +Y / +Z at the splat origin, parented to gsplat.
 * Renders in the normal forward pass (depth-tested), not as immediate drawLine overlay.
 */
function setupSogsAxesGuides(app, gsplatEntity) {
  if (window.__sogsAxesRoot) {
    try {
      window.__sogsAxesRoot.destroy();
    } catch {
      /* ignore */
    }
    window.__sogsAxesRoot = null;
  }

  const device = app.graphicsDevice;
  const geom = new CylinderGeometry({
    height: AXIS_LEN,
    radius: AXIS_RADIUS,
    heightSegments: 1,
    capSegments: 18,
  });
  const mesh = Mesh.fromGeometry(device, geom);

  const root = new Entity("sogsAxes");
  gsplatEntity.addChild(root);

  const configs = [
    { name: "sogsAxisX", ex: 0, ey: 0, ez: -90, px: AXIS_LEN / 2, py: 0, pz: 0, rgb: [0.95, 0.22, 0.18] },
    { name: "sogsAxisY", ex: 0, ey: 0, ez: 0, px: 0, py: AXIS_LEN / 2, pz: 0, rgb: [0.28, 0.92, 0.32] },
    { name: "sogsAxisZ", ex: 90, ey: 0, ez: 0, px: 0, py: 0, pz: AXIS_LEN / 2, rgb: [0.32, 0.52, 0.98] },
  ];

  for (const c of configs) {
    const mat = axisMaterial(c.rgb);
    const ent = new Entity(c.name);
    ent.setLocalEulerAngles(c.ex, c.ey, c.ez);
    ent.setLocalPosition(c.px, c.py, c.pz);
    const mi = new MeshInstance(mesh, mat, ent);
    ent.addComponent("render", {
      meshInstances: [mi],
      castShadows: false,
      receiveShadows: false,
    });
    copyRenderLayers(gsplatEntity, ent);
    root.addChild(ent);
  }

  window.__sogsAxesRoot = root;
  root.enabled = !!window.__sogsGuidesEnabled;
}

function syncSogsAxesGuides(app) {
  const g = app.root.findByName("gsplat");
  if (!g) {
    return;
  }
  if (window.__sogsGuidesEnabled && !window.__sogsAxesRoot) {
    setupSogsAxesGuides(app, g);
  }
  if (window.__sogsAxesRoot) {
    window.__sogsAxesRoot.enabled = !!window.__sogsGuidesEnabled;
  }
  app.renderNextFrame = true;
}

function applyScenePayload(app, payload) {
  const g = app.root.findByName("gsplat");
  if (!g || !payload || typeof payload !== "object") {
    return;
  }
  if (Array.isArray(payload.position) && payload.position.length === 3) {
    g.setLocalPosition(payload.position[0], payload.position[1], payload.position[2]);
  }
  if (Array.isArray(payload.rotation) && payload.rotation.length === 3) {
    g.setLocalEulerAngles(payload.rotation[0], payload.rotation[1], payload.rotation[2]);
  }
  if (typeof payload.scale === "number" && Number.isFinite(payload.scale)) {
    g.setLocalScale(payload.scale, payload.scale, payload.scale);
  }
  if (typeof payload.fov === "number" && Number.isFinite(payload.fov)) {
    window.__sogsUserFov = payload.fov;
  }
  app.renderNextFrame = true;
}

function applyViewerConfig(app, incomingConfig) {
  if (!app?.scene?.gsplat || !incomingConfig || typeof incomingConfig !== "object") {
    return;
  }

  const current = window.__sogsViewerConfig ?? {};
  const merged = {
    splatBudget: resolveIntegerConfig(current.splatBudget, incomingConfig.splatBudget, 0),
    lodRangeMin: resolveIntegerConfig(current.lodRangeMin, incomingConfig.lodRangeMin, 0),
    lodRangeMax: resolveIntegerConfig(current.lodRangeMax, incomingConfig.lodRangeMax, 0),
    lodDistances: sanitizeNumberList(incomingConfig.lodDistances) ?? current.lodDistances ?? null,
    lodUnderfillLimit: resolveIntegerConfig(current.lodUnderfillLimit, incomingConfig.lodUnderfillLimit, 0),
    lodBehindPenalty: resolveNumberConfig(current.lodBehindPenalty, incomingConfig.lodBehindPenalty, 0),
    lodUpdateDistance: resolveNumberConfig(current.lodUpdateDistance, incomingConfig.lodUpdateDistance, 0),
    lodUpdateAngle: resolveNumberConfig(current.lodUpdateAngle, incomingConfig.lodUpdateAngle, 0),
    colorUpdateDistance: resolveNumberConfig(current.colorUpdateDistance, incomingConfig.colorUpdateDistance, 0),
    colorUpdateAngle: resolveNumberConfig(current.colorUpdateAngle, incomingConfig.colorUpdateAngle, 0),
    colorUpdateDistanceLodScale: resolveNumberConfig(
      current.colorUpdateDistanceLodScale,
      incomingConfig.colorUpdateDistanceLodScale,
      0,
    ),
    colorUpdateAngleLodScale: resolveNumberConfig(
      current.colorUpdateAngleLodScale,
      incomingConfig.colorUpdateAngleLodScale,
      0,
    ),
  };

  window.__sogsViewerConfig = merged;

  const sceneGsplat = app.scene.gsplat;
  if (finiteNumber(merged.splatBudget) && merged.splatBudget >= 0) {
    sceneGsplat.splatBudget = merged.splatBudget;
  }
  if (finiteNumber(merged.lodRangeMin) && merged.lodRangeMin >= 0) {
    sceneGsplat.lodRangeMin = merged.lodRangeMin;
  }
  if (finiteNumber(merged.lodRangeMax) && merged.lodRangeMax >= 0) {
    sceneGsplat.lodRangeMax = merged.lodRangeMax;
  }
  if (finiteNumber(merged.lodUnderfillLimit) && merged.lodUnderfillLimit >= 0) {
    sceneGsplat.lodUnderfillLimit = merged.lodUnderfillLimit;
  }
  if (finiteNumber(merged.lodBehindPenalty) && merged.lodBehindPenalty >= 0) {
    sceneGsplat.lodBehindPenalty = merged.lodBehindPenalty;
  }
  if (finiteNumber(merged.lodUpdateDistance) && merged.lodUpdateDistance >= 0) {
    sceneGsplat.lodUpdateDistance = merged.lodUpdateDistance;
  }
  if (finiteNumber(merged.lodUpdateAngle) && merged.lodUpdateAngle >= 0) {
    sceneGsplat.lodUpdateAngle = merged.lodUpdateAngle;
  }
  if (finiteNumber(merged.colorUpdateDistance) && merged.colorUpdateDistance >= 0) {
    sceneGsplat.colorUpdateDistance = merged.colorUpdateDistance;
  }
  if (finiteNumber(merged.colorUpdateAngle) && merged.colorUpdateAngle >= 0) {
    sceneGsplat.colorUpdateAngle = merged.colorUpdateAngle;
  }
  if (finiteNumber(merged.colorUpdateDistanceLodScale) && merged.colorUpdateDistanceLodScale >= 0) {
    sceneGsplat.colorUpdateDistanceLodScale = merged.colorUpdateDistanceLodScale;
  }
  if (finiteNumber(merged.colorUpdateAngleLodScale) && merged.colorUpdateAngleLodScale >= 0) {
    sceneGsplat.colorUpdateAngleLodScale = merged.colorUpdateAngleLodScale;
  }

  const gsplatEntity = app.root.findByName("gsplat");
  if (gsplatEntity?.gsplat && Array.isArray(merged.lodDistances) && merged.lodDistances.length > 0) {
    gsplatEntity.gsplat.lodDistances = merged.lodDistances;
  }
  app.renderNextFrame = true;
}

document.addEventListener("DOMContentLoaded", async () => {
  const { config, settings } = window.sse;
  const { poster } = config;

  if (poster) {
    const element = document.getElementById("poster");
    element.style.backgroundImage = `url(${poster.src})`;
    element.style.display = "block";
    element.style.filter = "blur(40px)";
  }

  const [appElement, cameraElement, settingsJson] = await Promise.all([
    document.querySelector("pc-app").ready(),
    document.querySelector('pc-entity[name="camera"]').ready(),
    settings,
  ]);

  const app = appElement.app;
  const camera = cameraElement.entity;
  const viewer = await main(app, camera, settingsJson, config);

  window.__sogsCtx = { viewer, app, camera };

  const waitGsplat = () =>
    new Promise((resolve) => {
      const id = setInterval(() => {
        const e = app.root.findByName("gsplat");
        if (e) {
          clearInterval(id);
          resolve(e);
        }
      }, 30);
    });

  await waitGsplat();

  await new Promise((resolve) => {
    const id = setInterval(() => {
      if (viewer.cameraManager) {
        clearInterval(id);
        resolve(undefined);
      }
    }, 30);
  });

  applyScenePayload(app, window.__sogsInitialScenePayload ?? {});
  applyViewerConfig(app, window.__sogsInitialViewerConfig ?? {});
  setupCameraManagerBridge(viewer.cameraManager);
  const initialCameraPose = window.__sogsInitialCameraPose;
  if (
    initialCameraPose?.position?.length === 3 &&
    initialCameraPose?.target?.length === 3
  ) {
    window.__sogsCameraPose = {
      position: initialCameraPose.position,
      target: initialCameraPose.target,
      fov: initialCameraPose.fov ?? null,
    };
    window.__sogsScriptedCamera = true;
    tmpFrom.set(initialCameraPose.position[0], initialCameraPose.position[1], initialCameraPose.position[2]);
    tmpTo.set(initialCameraPose.target[0], initialCameraPose.target[1], initialCameraPose.target[2]);
    viewer.cameraManager.camera.look(tmpFrom, tmpTo);
    if (finiteNumber(initialCameraPose.fov)) {
      viewer.cameraManager.camera.fov = initialCameraPose.fov;
      window.__sogsUserFov = initialCameraPose.fov;
    }
    installInitialCameraRelease(app);
    app.renderNextFrame = true;
  }
  /** Primary pointer + pointermove pan was removed: it fought orbit/touch and caused bounce. */
  window.__sogsSplatXzDragReady = true;
  startSogsTelemetryPump();
  postSogsState();

  window.addEventListener("message", (event) => {
    const d = event.data;
    if (!d || typeof d !== "object") {
      return;
    }
    if (d.type === "sogs:apply") {
      applyScenePayload(app, d);
      postSogsState();
    }
    if (d.type === "sogs:guides") {
      window.__sogsGuidesEnabled = !!d.enabled;
      syncSogsAxesGuides(app);
    }
    if (d.type === "sogs:requestState") {
      postSogsState();
    }
    if (d.type === "sogs:config") {
      applyViewerConfig(app, d);
      postSogsState();
    }
    if (d.type === "sogs:cameraLookAt") {
      window.__sogsCameraPose = {
        position: d.position,
        target: d.target,
        fov: d.fov,
      };
      app.renderNextFrame = true;
    }
    if (d.type === "sogs:cameraMode") {
      const scripted = d.mode === "scripted" || d.scripted === true;
      window.__sogsScriptedCamera = !!scripted;
      app.renderNextFrame = true;
    }
  });
});
