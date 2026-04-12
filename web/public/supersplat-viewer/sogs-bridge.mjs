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
} from "https://esm.sh/playcanvas@2.17.1";

const tmpFrom = new Vec3();
const tmpTo = new Vec3();
const tmpFocus = new Vec3();
const CAM_FORWARD = new Vec3(0, 0, -1);

const FOCUS_XZ_MAX = 10;
const FOCUS_Y = 0;
const AXIS_LEN = 45;
const AXIS_RADIUS = 0.28;

function finiteNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
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

function postSogsState() {
  try {
    const ctx = window.__sogsCtx;
    if (!ctx?.app || !ctx.camera) {
      return;
    }
    const gsplatEntity = ctx.app.root.findByName("gsplat");
    if (!gsplatEntity) {
      return;
    }

    const sceneGsplat = ctx.app.scene?.gsplat;
    const position = gsplatEntity.getLocalPosition();
    const rotation = gsplatEntity.getLocalEulerAngles();
    const scale = gsplatEntity.getLocalScale();
    const telemetry = metricsSnapshot();

    window.parent.postMessage(
      {
        type: "sogs:state",
        position: [position.x, position.y, position.z],
        rotation: [rotation.x, rotation.y, rotation.z],
        scale: scale.x,
        fov: ctx.camera.camera.fov,
        splatBudget: finiteNumber(sceneGsplat?.splatBudget) ? sceneGsplat.splatBudget : null,
        lodRangeMin: finiteNumber(sceneGsplat?.lodRangeMin) ? sceneGsplat.lodRangeMin : null,
        lodRangeMax: finiteNumber(sceneGsplat?.lodRangeMax) ? sceneGsplat.lodRangeMax : null,
        ...telemetry,
      },
      "*",
    );
  } catch {
    /* ignore */
  }
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

function applyViewerConfig(app, incomingConfig) {
  if (!app?.scene?.gsplat || !incomingConfig || typeof incomingConfig !== "object") {
    return;
  }

  const current = window.__sogsViewerConfig ?? {};
  const merged = {
    splatBudget:
      finiteNumber(incomingConfig.splatBudget) && incomingConfig.splatBudget > 0
        ? Math.trunc(incomingConfig.splatBudget)
        : current.splatBudget ?? null,
    lodRangeMin:
      finiteNumber(incomingConfig.lodRangeMin) && incomingConfig.lodRangeMin >= 0
        ? Math.trunc(incomingConfig.lodRangeMin)
        : current.lodRangeMin ?? null,
    lodRangeMax:
      finiteNumber(incomingConfig.lodRangeMax) && incomingConfig.lodRangeMax >= 0
        ? Math.trunc(incomingConfig.lodRangeMax)
        : current.lodRangeMax ?? null,
  };

  window.__sogsViewerConfig = merged;

  const sceneGsplat = app.scene.gsplat;
  if (finiteNumber(merged.splatBudget) && merged.splatBudget > 0) {
    sceneGsplat.splatBudget = merged.splatBudget;
  }
  if (finiteNumber(merged.lodRangeMin) && merged.lodRangeMin >= 0) {
    sceneGsplat.lodRangeMin = merged.lodRangeMin;
  }
  if (finiteNumber(merged.lodRangeMax) && merged.lodRangeMax >= 0) {
    sceneGsplat.lodRangeMax = merged.lodRangeMax;
  }
  app.renderNextFrame = true;
}

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

function setupCameraManagerBridge(cameraManager, app) {
  const origUpdate = cameraManager.update.bind(cameraManager);
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

  const getFocusPoint = (cam) => {
    const quat = new Quat().setFromEulerAngles(cam.angles.x, cam.angles.y, cam.angles.z);
    const direction = new Vec3();
    quat.transformVector(CAM_FORWARD, direction);
    direction.mulScalar(cam.distance);
    return new Vec3().copy(cam.position).add(direction);
  };

  const setCameraFromFocus = (cam, focus) => {
    const quat = new Quat().setFromEulerAngles(cam.angles.x, cam.angles.y, cam.angles.z);
    const direction = new Vec3();
    quat.transformVector(CAM_FORWARD, direction);
    direction.mulScalar(cam.distance);
    cam.position.copy(focus).sub(direction);
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
        if (finiteNumber(pose.fov)) {
          cameraManager.camera.fov = pose.fov;
          window.__sogsUserFov = pose.fov;
        }
      }
    } else {
      origUpdate(dt, frame);
      if (finiteNumber(window.__sogsUserFov)) {
        cameraManager.camera.fov = window.__sogsUserFov;
      }
      clampCameraFocus(cameraManager.camera);
      postCameraPoseFromViewer(cameraManager);
    }
  };
}

function axisMaterial(rgb) {
  const material = new StandardMaterial();
  material.diffuse = new Color(0, 0, 0);
  material.emissive = new Color(rgb[0], rgb[1], rgb[2]);
  material.emissiveIntensity = 1;
  material.useLighting = false;
  return material;
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

function setupSogsAxesGuides(app, gsplatEntity) {
  if (window.__sogsAxesRoot) {
    try {
      window.__sogsAxesRoot.destroy();
    } catch {
      /* ignore */
    }
    window.__sogsAxesRoot = null;
  }

  const geometry = new CylinderGeometry({
    height: AXIS_LEN,
    radius: AXIS_RADIUS,
    heightSegments: 1,
    capSegments: 18,
  });
  const mesh = Mesh.fromGeometry(app.graphicsDevice, geometry);
  const root = new Entity("sogsAxes");
  gsplatEntity.addChild(root);

  const configs = [
    { name: "sogsAxisX", ex: 0, ey: 0, ez: -90, px: AXIS_LEN / 2, py: 0, pz: 0, rgb: [0.95, 0.22, 0.18] },
    { name: "sogsAxisY", ex: 0, ey: 0, ez: 0, px: 0, py: AXIS_LEN / 2, pz: 0, rgb: [0.28, 0.92, 0.32] },
    { name: "sogsAxisZ", ex: 90, ey: 0, ez: 0, px: 0, py: 0, pz: AXIS_LEN / 2, rgb: [0.32, 0.52, 0.98] },
  ];

  for (const config of configs) {
    const material = axisMaterial(config.rgb);
    const entity = new Entity(config.name);
    entity.setLocalEulerAngles(config.ex, config.ey, config.ez);
    entity.setLocalPosition(config.px, config.py, config.pz);
    const meshInstance = new MeshInstance(mesh, material, entity);
    entity.addComponent("render", {
      meshInstances: [meshInstance],
      castShadows: false,
      receiveShadows: false,
    });
    copyRenderLayers(gsplatEntity, entity);
    root.addChild(entity);
  }

  window.__sogsAxesRoot = root;
  root.enabled = !!window.__sogsGuidesEnabled;
}

function syncSogsAxesGuides(app) {
  const gsplatEntity = app.root.findByName("gsplat");
  if (!gsplatEntity) {
    return;
  }
  if (window.__sogsGuidesEnabled && !window.__sogsAxesRoot) {
    setupSogsAxesGuides(app, gsplatEntity);
  }
  if (window.__sogsAxesRoot) {
    window.__sogsAxesRoot.enabled = !!window.__sogsGuidesEnabled;
  }
  app.renderNextFrame = true;
}

function waitFor(predicate, intervalMs = 30, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const startedAt = performance.now();
    const timer = window.setInterval(() => {
      const value = predicate();
      if (value) {
        window.clearInterval(timer);
        resolve(value);
        return;
      }
      if (performance.now() - startedAt > timeoutMs) {
        window.clearInterval(timer);
        reject(new Error("Timed out waiting for viewer resource"));
      }
    }, intervalMs);
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  const { config, settings } = window.sse;
  const { poster } = config;

  if (poster) {
    const element = document.getElementById("poster");
    element.style.setProperty("--poster-url", `url(${poster.src})`);
    element.style.display = "block";
    element.style.filter = "blur(40px)";
    document.documentElement.style.setProperty("--canvas-opacity", "0");
  }

  const canvas = document.getElementById("application-canvas");
  const settingsJson = await settings;
  const viewer = await main(canvas, settingsJson, config);
  const app = viewer?.global?.app;
  const camera = viewer?.global?.camera;
  if (!app || !camera) {
    throw new Error("SuperSplat viewer failed to expose app/camera");
  }

  window.__sogsCtx = { viewer, app, camera };

  await waitFor(() => app.root.findByName("gsplat"));
  await waitFor(() => viewer.cameraManager);

  applyViewerConfig(app, window.__sogsInitialViewerConfig ?? {});
  setupCameraManagerBridge(viewer.cameraManager, app);
  window.__sogsSplatXzDragReady = true;

  window.addEventListener("message", (event) => {
    const data = event.data;
    if (!data || typeof data !== "object") {
      return;
    }

    if (data.type === "sogs:apply") {
      const gsplatEntity = app.root.findByName("gsplat");
      if (!gsplatEntity) {
        return;
      }
      if (Array.isArray(data.position) && data.position.length === 3) {
        gsplatEntity.setLocalPosition(data.position[0], data.position[1], data.position[2]);
      }
      if (Array.isArray(data.rotation) && data.rotation.length === 3) {
        gsplatEntity.setLocalEulerAngles(data.rotation[0], data.rotation[1], data.rotation[2]);
      }
      if (finiteNumber(data.scale)) {
        gsplatEntity.setLocalScale(data.scale, data.scale, data.scale);
      }
      if (finiteNumber(data.fov)) {
        window.__sogsUserFov = data.fov;
      }
      app.renderNextFrame = true;
      postSogsState();
    }

    if (data.type === "sogs:guides") {
      window.__sogsGuidesEnabled = !!data.enabled;
      syncSogsAxesGuides(app);
      postSogsState();
    }

    if (data.type === "sogs:config") {
      applyViewerConfig(app, data);
      postSogsState();
    }

    if (data.type === "sogs:requestState") {
      postSogsState();
    }

    if (data.type === "sogs:cameraLookAt") {
      window.__sogsCameraPose = {
        position: data.position,
        target: data.target,
        fov: data.fov,
      };
      app.renderNextFrame = true;
      postSogsState();
    }

    if (data.type === "sogs:cameraMode") {
      const scripted = data.mode === "scripted" || data.scripted === true;
      window.__sogsScriptedCamera = !!scripted;
      app.renderNextFrame = true;
      postSogsState();
    }
  });

  postSogsState();
});
