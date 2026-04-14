/**
 * Spaceport SOGS bridge: postMessage API for parent page + optional RGB world axes (mesh, not drawLine overlay).
 * Uses PlayCanvas classes from the bundled viewer (`window.__sogsPc`), not a separate esm.sh build.
 */
import { main } from "./index.js";

const {
  Asset,
  Color,
  CylinderGeometry,
  Entity,
  FloatPacking,
  GSplatData,
  GSplatResource,
  Mesh,
  MeshInstance,
  Quat,
  StandardMaterial,
  Vec3,
} = window.__sogsPc ?? {};

/** Parent-driven camera (position + look-at). When `sogs:cameraMode` is `scripted`, orbit input is skipped. */
const tmpFrom = new Vec3();
const tmpTo = new Vec3();
/** Orbit focus point for `sogs:cameraPose` (parent overlays / Three.js projection). */
const tmpFocus = new Vec3();

/** Half-length of each axis arm from the origin (total span 2× this along each axis). */
const AXIS_LEN = 10;
/** Cylinder radius (÷10 vs prior 0.05 for skinnier rods). */
const AXIS_RADIUS = 0.005;
const MAIN_BOOT_TIMEOUT_MS = 15e3;
const BRIDGE_WAIT_TIMEOUT_MS = 12e3;
const PREVIEW_ALPHA_UPDATE_STEPS = 24;
const PREVIEW_REVEAL_UPDATE_STEPS = 36;
const SH_C0 = 0.28209479177387814;
/**
 * PlayCanvas default layer ids (must match bundled engine). Gsplat draws in World; we draw axes
 * on Immediate so they composite after the splat and stay visible.
 */
const LAYER_ID_IMMEDIATE = 3;

function finiteNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function finiteInteger(value) {
  return finiteNumber(value) ? Math.trunc(value) : null;
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

function getBootOptions() {
  if (typeof window === "undefined") {
    return { quality: "hq", lowQuality: false };
  }
  const fromWindow = window.__sogsBootOptions;
  if (fromWindow && typeof fromWindow === "object") {
    return {
      quality: fromWindow.quality === "lq" ? "lq" : "hq",
      lowQuality: fromWindow.lowQuality === true || fromWindow.quality === "lq"
    };
  }
  try {
    const params = new URLSearchParams(window.location.search);
    const lowQuality = params.get("quality") === "lq";
    return {
      quality: lowQuality ? "lq" : "hq",
      lowQuality
    };
  } catch {
    return { quality: "hq", lowQuality: false };
  }
}

function clamp01(value) {
  return Math.min(1, Math.max(0, value));
}

function easeOutCubic(value) {
  return 1 - Math.pow(1 - clamp01(value), 3);
}

function parseVector(value) {
  if (typeof value !== "string" || !value.trim()) {
    return null;
  }
  const parts = value.split(",").map((entry) => Number.parseFloat(entry.trim()));
  return parts.length === 3 && parts.every(Number.isFinite) ? parts : null;
}

function readPreviewBootConfig() {
  try {
    const params = new URLSearchParams(window.location.search);
    const metaUrl = params.get("previewMeta")?.trim() ?? "";
    if (!metaUrl) {
      return null;
    }
    return {
      metaUrl,
      pointSize: Math.max(0.0001, Number.parseFloat(params.get("previewPointSize") ?? "0.011") || 0.011),
      initialVisiblePoints: Math.max(1, Math.trunc(Number.parseFloat(params.get("previewInitialVisiblePoints") ?? "750") || 750)),
      revealDurationMs: Math.max(0, Math.trunc(Number.parseFloat(params.get("previewRevealDurationMs") ?? "900") || 900)),
      fadeDelayMs: Math.max(0, Math.trunc(Number.parseFloat(params.get("previewFadeDelayMs") ?? "250") || 250)),
      fadeDurationMs: Math.max(0, Math.trunc(Number.parseFloat(params.get("previewFadeDurationMs") ?? "900") || 900)),
      focusTarget: parseVector(params.get("previewFocus")) ?? [0, 0, 0],
    };
  } catch {
    return null;
  }
}

function setPreviewState(patch) {
  const previous = window.__sogsPreviewState ?? {
    enabled: false,
    phase: "idle",
    visiblePoints: 0,
    totalPoints: 0,
    alpha: 1,
    fadeRequested: false,
    maxVisiblePoints: 0,
    everRevealed: false,
    everFaded: false,
    error: null,
  };
  const nextPhase = patch.phase ?? previous.phase;
  const nextVisible = finiteInteger(patch.visiblePoints) ?? previous.visiblePoints ?? 0;
  window.__sogsPreviewState = {
    ...previous,
    ...patch,
    maxVisiblePoints: Math.max(previous.maxVisiblePoints ?? 0, nextVisible),
    everRevealed:
      previous.everRevealed ||
      nextPhase === "revealing" ||
      nextPhase === "waiting-for-real" ||
      nextPhase === "fading" ||
      nextPhase === "done",
    everFaded: previous.everFaded || nextPhase === "fading" || nextPhase === "done",
  };
}

function destroyPreviewController(controller) {
  if (!controller) {
    return;
  }
  if (controller.revealFrame) {
    cancelAnimationFrame(controller.revealFrame);
  }
  if (controller.fadeFrame) {
    cancelAnimationFrame(controller.fadeFrame);
  }
  if (controller.fadeTimer) {
    clearTimeout(controller.fadeTimer);
  }
  try {
    controller.entity?.destroy();
  } catch {
    /* ignore */
  }
  try {
    if (controller.asset?.registry) {
      controller.asset.registry.remove(controller.asset);
    }
  } catch {
    /* ignore */
  }
  try {
    controller.resource?.destroy();
  } catch {
    /* ignore */
  }
}

function applyPreviewVisibleCount(controller, visibleCount) {
  if (!controller?.instance?.sorter) {
    return;
  }
  const nextVisible = Math.max(0, Math.min(controller.totalPoints, Math.trunc(visibleCount)));
  if (nextVisible === controller.visiblePoints) {
    return;
  }
  controller.visiblePoints = nextVisible;
  controller.instance.sorter.setMapping(getPreviewMapping(controller, nextVisible));
  controller.entity.enabled = nextVisible > 0;
  controller.app.renderNextFrame = true;
  setPreviewState({ visiblePoints: nextVisible, totalPoints: controller.totalPoints });
}

function applyPreviewAlpha(controller, alpha) {
  if (!controller?.resource?.colorTexture || !controller?.baseAlphas) {
    return;
  }
  const nextAlpha = clamp01(alpha);
  const nextBucket = Math.round(nextAlpha * PREVIEW_ALPHA_UPDATE_STEPS);
  if (nextBucket === controller.alphaBucket) {
    return;
  }
  controller.alphaBucket = nextBucket;
  controller.alpha = nextBucket / PREVIEW_ALPHA_UPDATE_STEPS;
  const colorData = controller.resource.colorTexture.lock();
  for (let i = 0; i < controller.totalPoints; i += 1) {
    colorData[i * 4 + 3] = FloatPacking.float2Half(controller.baseAlphas[i] * controller.alpha);
  }
  controller.resource.colorTexture.unlock();
  controller.instance?.sorter?.setMapping(getPreviewMapping(controller, controller.visiblePoints));
  controller.app.renderNextFrame = true;
  setPreviewState({ alpha: controller.alpha });
}

function schedulePreviewFade(controller) {
  if (!controller || controller.fadeScheduled) {
    return;
  }
  controller.fadeScheduled = true;
  controller.fadeTimer = window.setTimeout(() => {
    controller.fadeTimer = 0;
    setPreviewState({ phase: "fading" });
    const startedAt = performance.now();
    const duration = Math.max(1, controller.config.fadeDurationMs);
    const tick = (now) => {
      const progress = clamp01((now - startedAt) / duration);
      applyPreviewAlpha(controller, 1 - progress);
      if (progress >= 1) {
        setPreviewState({ phase: "done", alpha: 0, visiblePoints: 0 });
        destroyPreviewController(controller);
        if (window.__sogsPreviewController === controller) {
          window.__sogsPreviewController = null;
        }
        return;
      }
      controller.fadeFrame = requestAnimationFrame(tick);
    };
    controller.fadeFrame = requestAnimationFrame(tick);
  }, controller.config.fadeDelayMs);
}

function notifyPreviewFirstFrame() {
  setPreviewState({ fadeRequested: true });
  const controller = window.__sogsPreviewController;
  if (controller) {
    schedulePreviewFade(controller);
  }
}

async function loadPreviewPoints(config) {
  const metaResponse = await fetch(config.metaUrl, {
    headers: { Accept: "application/json" },
    cache: "force-cache",
  });
  if (!metaResponse.ok) {
    throw new Error(`preview-meta:${metaResponse.status}`);
  }
  const meta = await metaResponse.json();
  const assetUrl = new URL(meta.asset, config.metaUrl).toString();
  const pointsResponse = await fetch(assetUrl, { cache: "force-cache" });
  if (!pointsResponse.ok) {
    throw new Error(`preview-points:${pointsResponse.status}`);
  }
  const buffer = await pointsResponse.arrayBuffer();
  const stride = Number(meta.stride ?? 16);
  const count = Number(meta.count ?? 0);
  if (!Number.isFinite(stride) || stride !== 16 || !Number.isFinite(count) || count <= 0) {
    throw new Error("preview-meta-invalid");
  }
  const view = new DataView(buffer);
  const focus = config.focusTarget;
  const points = new Array(count);
  for (let i = 0; i < count; i += 1) {
    const offset = i * stride;
    const x = view.getFloat32(offset, true);
    const y = view.getFloat32(offset + 4, true);
    const z = view.getFloat32(offset + 8, true);
    points[i] = {
      x,
      y,
      z,
      r: view.getUint8(offset + 12),
      g: view.getUint8(offset + 13),
      b: view.getUint8(offset + 14),
      a: view.getUint8(offset + 15),
      distanceSq: (x - focus[0]) ** 2 + (y - focus[1]) ** 2 + (z - focus[2]) ** 2,
    };
  }
  points.sort((a, b) => a.distanceSq - b.distanceSq);
  return { meta, points };
}

function encodePreviewDc(rgb) {
  return (rgb - 0.5) / SH_C0;
}

function encodePreviewOpacity(alpha) {
  const clamped = Math.min(0.999, Math.max(0.001, alpha));
  return Math.log(clamped / (1 - clamped));
}

function getPreviewMapping(controller, visibleCount) {
  const nextVisible = Math.max(0, Math.min(controller.totalPoints, Math.trunc(visibleCount)));
  if (nextVisible >= controller.totalPoints) {
    return null;
  }
  const cached = controller.mappings.get(nextVisible);
  if (cached) {
    return cached;
  }
  const mapping = new Uint32Array(nextVisible);
  for (let i = 0; i < nextVisible; i += 1) {
    mapping[i] = i;
  }
  controller.mappings.set(nextVisible, mapping);
  return mapping;
}

function createPreviewGsplatAsset(app, points, config) {
  const count = points.length;
  const pointScale = Math.max(0.0005, config.pointSize);
  const pointScaleLog = Math.log(pointScale);
  const rotations0 = new Float32Array(count);
  const rotations1 = new Float32Array(count);
  const rotations2 = new Float32Array(count);
  const rotations3 = new Float32Array(count);
  const scales0 = new Float32Array(count);
  const scales1 = new Float32Array(count);
  const scales2 = new Float32Array(count);
  const xs = new Float32Array(count);
  const ys = new Float32Array(count);
  const zs = new Float32Array(count);
  const dc0 = new Float32Array(count);
  const dc1 = new Float32Array(count);
  const dc2 = new Float32Array(count);
  const opacity = new Float32Array(count);
  const baseAlphas = new Float32Array(count);

  for (let i = 0; i < count; i += 1) {
    const point = points[i];
    const alpha = Math.max(0.12, point.a / 255);
    xs[i] = point.x;
    ys[i] = point.y;
    zs[i] = point.z;
    rotations0[i] = 1;
    rotations1[i] = 0;
    rotations2[i] = 0;
    rotations3[i] = 0;
    scales0[i] = pointScaleLog;
    scales1[i] = pointScaleLog;
    scales2[i] = pointScaleLog;
    dc0[i] = encodePreviewDc(point.r / 255);
    dc1[i] = encodePreviewDc(point.g / 255);
    dc2[i] = encodePreviewDc(point.b / 255);
    opacity[i] = encodePreviewOpacity(alpha);
    baseAlphas[i] = alpha;
  }

  const createProp = (name, storage) => ({
    type: "float",
    name,
    storage,
    byteSize: 4,
  });
  const gsplatData = new GSplatData([
    {
      name: "vertex",
      count,
      properties: [
        createProp("x", xs),
        createProp("y", ys),
        createProp("z", zs),
        createProp("rot_0", rotations0),
        createProp("rot_1", rotations1),
        createProp("rot_2", rotations2),
        createProp("rot_3", rotations3),
        createProp("scale_0", scales0),
        createProp("scale_1", scales1),
        createProp("scale_2", scales2),
        createProp("f_dc_0", dc0),
        createProp("f_dc_1", dc1),
        createProp("f_dc_2", dc2),
        createProp("opacity", opacity),
      ],
    },
  ]);

  const resource = new GSplatResource(app.graphicsDevice, gsplatData);
  const asset = new Asset(`preview-gsplat-${Date.now()}`, "gsplat", null, {});
  asset.resource = resource;
  asset.loaded = true;
  app.assets.add(asset);

  return { asset, baseAlphas, resource };
}

async function setupPreviewScaffold(app, gsplatEntity, config) {
  if (!config || !Asset || !GSplatData || !GSplatResource || !FloatPacking) {
    setPreviewState({
      enabled: false,
      phase: "error",
      error: "preview-support-missing",
    });
    return null;
  }

  destroyPreviewController(window.__sogsPreviewController);
  window.__sogsPreviewController = null;

  setPreviewState({
    enabled: true,
    phase: "loading",
    visiblePoints: 0,
    totalPoints: 0,
    alpha: 1,
    error: null,
  });

  const { points } = await loadPreviewPoints(config);
  if (!points.length) {
    setPreviewState({ phase: "done", enabled: false });
    return null;
  }

  const { asset, baseAlphas, resource } = createPreviewGsplatAsset(app, points, config);

  const previewEntity = new Entity("preview-gsplat", app);
  previewEntity.addComponent("gsplat", {
    asset,
    unified: false,
  });
  gsplatEntity.addChild(previewEntity);
  const instance = await waitForValue(() => previewEntity.gsplat?.instance, "previewInstance");
  previewEntity.gsplat.highQualitySH = false;

  const controller = {
    app,
    asset,
    entity: previewEntity,
    baseAlphas,
    instance,
    mappings: new Map(),
    resource,
    totalPoints: points.length,
    visiblePoints: 0,
    alpha: 1,
    alphaBucket: PREVIEW_ALPHA_UPDATE_STEPS,
    revealFrame: 0,
    fadeFrame: 0,
    fadeTimer: 0,
    fadeScheduled: false,
    config,
  };
  window.__sogsPreviewController = controller;
  setPreviewState({
    phase: "revealing",
    totalPoints: points.length,
    visiblePoints: 0,
    alpha: 1,
  });

  const initialVisible = Math.min(points.length, config.initialVisiblePoints);
  applyPreviewVisibleCount(controller, initialVisible);
  applyPreviewAlpha(controller, 1);

  const revealStartedAt = performance.now();
  const revealDuration = Math.max(1, config.revealDurationMs);
  const revealTick = (now) => {
    const progress = clamp01((now - revealStartedAt) / revealDuration);
    const quantizedProgress = Math.round(progress * PREVIEW_REVEAL_UPDATE_STEPS) / PREVIEW_REVEAL_UPDATE_STEPS;
    const visible = Math.round(initialVisible + (points.length - initialVisible) * easeOutCubic(quantizedProgress));
    applyPreviewVisibleCount(controller, visible);
    if (progress >= 1) {
      setPreviewState({ phase: "waiting-for-real", visiblePoints: points.length });
      if (window.__sogsPreviewState?.fadeRequested) {
        schedulePreviewFade(controller);
      }
      return;
    }
    controller.revealFrame = requestAnimationFrame(revealTick);
  };
  controller.revealFrame = requestAnimationFrame(revealTick);

  if (window.__sogsPreviewState?.fadeRequested) {
    schedulePreviewFade(controller);
  }

  return controller;
}

function postBootEvent(type, detail = {}) {
  try {
    window.parent.postMessage(
      {
        type,
        ...detail
      },
      "*"
    );
  } catch {
    /* ignore */
  }
}

function withTimeout(promise, timeoutMs, stage) {
  return new Promise((resolve, reject) => {
    const id = window.setTimeout(() => {
      reject(new Error(`timeout:${stage}`));
    }, timeoutMs);
    Promise.resolve(promise).then(
      (value) => {
        clearTimeout(id);
        resolve(value);
      },
      (error) => {
        clearTimeout(id);
        reject(error);
      }
    );
  });
}

function waitForValue(getValue, stage, timeoutMs = BRIDGE_WAIT_TIMEOUT_MS, intervalMs = 30) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;
    const finishReject = (error) => {
      clearInterval(id);
      reject(error);
    };
    const tick = () => {
      try {
        const value = getValue();
        if (value) {
          clearInterval(id);
          resolve(value);
          return;
        }
        if (Date.now() >= deadline) {
          finishReject(new Error(`timeout:${stage}`));
        }
      } catch (error) {
        finishReject(error);
      }
    };
    const id = window.setInterval(tick, intervalMs);
    tick();
  });
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

window.firstFrame = function sogsFirstFrameHook() {
  const metrics = window.__sogsNetworkMetrics;
  if (metrics && !metrics.firstFrame) {
    metrics.firstFrame = {
      at: performance.now(),
      chunkMetaRequestCount: Array.isArray(metrics.uniqueChunkMetaUrls) ? metrics.uniqueChunkMetaUrls.length : 0,
      totalRequestCount: Array.isArray(metrics.events) ? metrics.events.length : 0,
    };
  }
  notifyPreviewFirstFrame();
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
    const telemetry = metricsSnapshot();
    const previewState = window.__sogsPreviewState ?? null;
    let skyboxRotation = [0, 0, 0];
    try {
      const scene = ctx.app.scene;
      if (scene?.skyboxRotation) {
        const se = scene.skyboxRotation.getEulerAngles();
        skyboxRotation = [se.x, se.y, se.z];
      }
    } catch {
      /* ignore */
    }
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
        previewPhase: typeof previewState?.phase === "string" ? previewState.phase : null,
        previewVisiblePoints: finiteInteger(previewState?.visiblePoints),
        previewTotalPoints: finiteInteger(previewState?.totalPoints),
        previewAlpha: finiteNumber(previewState?.alpha) ? previewState.alpha : null,
        skyboxRotation,
        ...telemetry,
      },
      "*",
    );
  } catch {
    /* ignore */
  }
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
  if (gsplatEntity?.gsplat) {
    gsplatEntity.gsplat.highQualitySH = true;
    if (Array.isArray(merged.lodDistances) && merged.lodDistances.length > 0) {
      gsplatEntity.gsplat.lodDistances = merged.lodDistances;
    }
  }
  app.renderNextFrame = true;
}

function applyScenePayload(app, payload) {
  const gsplat = app?.root?.findByName("gsplat");
  if (!gsplat || !payload || typeof payload !== "object") {
    return;
  }
  if (Array.isArray(payload.position) && payload.position.length === 3) {
    gsplat.setLocalPosition(payload.position[0], payload.position[1], payload.position[2]);
  }
  if (Array.isArray(payload.rotation) && payload.rotation.length === 3) {
    gsplat.setLocalEulerAngles(payload.rotation[0], payload.rotation[1], payload.rotation[2]);
  }
  if (typeof payload.scale === "number" && Number.isFinite(payload.scale)) {
    gsplat.setLocalScale(payload.scale, payload.scale, payload.scale);
  }
  if (typeof payload.fov === "number" && Number.isFinite(payload.fov)) {
    window.__sogsUserFov = payload.fov;
  }
  app.renderNextFrame = true;
}

function applyInitialSkyboxRotation(app, rotation) {
  if (!app?.scene || !Array.isArray(rotation) || rotation.length !== 3) {
    return;
  }
  const rx = Number(rotation[0]);
  const ry = Number(rotation[1]);
  const rz = Number(rotation[2]);
  if (!Number.isFinite(rx) || !Number.isFinite(ry) || !Number.isFinite(rz)) {
    return;
  }
  app.scene.skyboxRotation = new Quat().setFromEulerAngles(rx, ry, rz);
  app.renderNextFrame = true;
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

/**
 * Wraps CameraManager.update: free orbit vs scripted pose from `window.__sogsCameraPose`.
 * Orbit consumes InputFrame via `frame.read()` each update; while scripted we skip `origUpdate`,
 * so flush the same `frame` reference each scripted frame. First free frame skips one `origUpdate`
 * so orbit integration cannot nudge the camera away from the last `look()` pose.
 */
function flushSogsAccumulatedInputFrame(frame) {
  try {
    const inputFrame = frame ?? window.__sogsCtx?.viewer?.inputController?.frame;
    if (!inputFrame || typeof inputFrame.read !== "function") return null;
    const fr = inputFrame.read();
    if (!fr) return null;
    const m = fr.move || [0, 0, 0];
    const r = fr.rotate || [0, 0, 0];
    return {
      moveLen: Math.hypot(m[0], m[1], m[2] || 0),
      rotateLen: Math.hypot(r[0], r[1], r[2] || 0),
    };
  } catch {
    return null;
  }
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

/**
 * Keeps the camera eye (logical `Camera.position`) above a world Y floor and/or inside a sphere around origin.
 * Iterates so Y and radius limits can both apply without fighting.
 *
 * After moving only `position`, the orbit camera's `angles` + `distance` would still describe the *old* focus.
 * `calcFocusPoint` would then report a bogus target (often very far). We snapshot the true focus before clamping
 * and run `look(clampedEye, savedFocus)` so the pivot stays fixed while the eye is constrained.
 */
function clampSogsCameraPosition(cameraManager) {
  const yMin = window.__sogsCameraYMin;
  const maxR = window.__sogsCameraMaxRadius;
  const hasY = typeof yMin === "number" && Number.isFinite(yMin);
  const hasR = typeof maxR === "number" && Number.isFinite(maxR) && maxR > 0;
  if (!hasY && !hasR) return false;
  const cam = cameraManager.camera;
  cam.calcFocusPoint(tmpFocus);
  const pos = cam.position;
  let changed = false;
  for (let i = 0; i < 6; i++) {
    if (hasY) {
      const ny = Math.max(pos.y, yMin);
      if (ny !== pos.y) changed = true;
      pos.y = ny;
    }
    if (hasR) {
      const len = pos.length();
      if (len > maxR && len > 1e-20) {
        pos.mulScalar(maxR / len);
        changed = true;
      }
    }
  }
  if (changed) {
    tmpFrom.copy(pos);
    cam.look(tmpFrom, tmpFocus);
  }
  return changed;
}

function setupCameraManagerBridge(cameraManager) {
  const origUpdate = cameraManager.update.bind(cameraManager);
  let prevScripted = false;

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
      clampSogsCameraPosition(cameraManager);
      flushSogsAccumulatedInputFrame(frame);
      prevScripted = true;
      return;
    }
    const leftScripted = prevScripted;
    prevScripted = false;
    let skipFirstOrbitAfterScripted = false;
    if (leftScripted) {
      flushSogsAccumulatedInputFrame(frame);
      if (typeof cameraManager.syncOrbitFromCurrentCamera === "function") {
        cameraManager.syncOrbitFromCurrentCamera();
      }
      skipFirstOrbitAfterScripted = true;
    }
    if (!skipFirstOrbitAfterScripted) {
      origUpdate(dt, frame);
    }
    if (typeof window.__sogsUserFov === "number" && Number.isFinite(window.__sogsUserFov)) {
      cameraManager.camera.fov = window.__sogsUserFov;
    }
    if (clampSogsCameraPosition(cameraManager) && typeof cameraManager.syncOrbitFromCurrentCamera === "function") {
      cameraManager.syncOrbitFromCurrentCamera();
    }
    postCameraPoseFromViewer(cameraManager);
  };
}

function axisMaterial(rgb) {
  const m = new StandardMaterial();
  m.diffuse = new Color(0, 0, 0);
  m.emissive = new Color(rgb[0], rgb[1], rgb[2]);
  m.emissiveIntensity = 1;
  m.useLighting = false;
  return m;
}

/** After `render` exists: draw on Immediate layer (after World), so gsplat does not paint over axes. */
function setAxisGuideRenderLayer(ent) {
  try {
    if (ent.render) {
      ent.render.layers = [LAYER_ID_IMMEDIATE];
    }
  } catch {
    /* ignore */
  }
}

/**
 * Thin cylinders along local +X / +Y / +Z at the splat origin, parented to gsplat.
 * Uses Immediate render layer so gsplat does not occlude them.
 */
function buildAxisCylinderMesh(app, radius = AXIS_RADIUS) {
  const device = app.graphicsDevice;
  const geom = new CylinderGeometry({
    height: AXIS_LEN,
    radius,
    heightSegments: 1,
    capSegments: 12,
  });
  return Mesh.fromGeometry(device, geom);
}

const AXIS_CONFIGS = [
  { name: "sogsAxisX", ex: 0, ey: 0, ez: -90, px: AXIS_LEN / 2, py: 0, pz: 0, rgb: [0.95, 0.22, 0.18] },
  { name: "sogsAxisY", ex: 0, ey: 0, ez: 0, px: 0, py: AXIS_LEN / 2, pz: 0, rgb: [0.28, 0.92, 0.32] },
  { name: "sogsAxisZ", ex: 90, ey: 0, ez: 0, px: 0, py: 0, pz: AXIS_LEN / 2, rgb: [0.32, 0.52, 0.98] },
];

function setupSogsAxesGuides(app, gsplatEntity) {
  if (window.__sogsAxesRoot) {
    try {
      window.__sogsAxesRoot.destroy();
    } catch {
      /* ignore */
    }
    window.__sogsAxesRoot = null;
  }

  const mesh = buildAxisCylinderMesh(app);

  const root = new Entity("sogsAxes", app);
  gsplatEntity.addChild(root);

  for (const c of AXIS_CONFIGS) {
    const mat = axisMaterial(c.rgb);
    const ent = new Entity(c.name, app);
    ent.setLocalEulerAngles(c.ex, c.ey, c.ez);
    ent.setLocalPosition(c.px, c.py, c.pz);
    const mi = new MeshInstance(mesh, mat, ent);
    mi.drawOrder = 0xffffff;
    ent.addComponent("render", {
      meshInstances: [mi],
      castShadows: false,
      receiveShadows: false,
    });
    setAxisGuideRenderLayer(ent);
    root.addChild(ent);
  }

  window.__sogsAxesRoot = root;
  root.enabled = !!window.__sogsGuidesEnabled;
}

/**
 * RGB XYZ cylinders at world origin (0,0,0), identity rotation — true world +X/+Y/+Z, independent of gsplat transform.
 */
function setupWorldAxesGuides(app) {
  if (window.__sogsWorldAxesRoot) {
    try {
      window.__sogsWorldAxesRoot.destroy();
    } catch {
      /* ignore */
    }
    window.__sogsWorldAxesRoot = null;
  }

  const mesh = buildAxisCylinderMesh(app);
  const root = new Entity("sogsWorldAxes", app);
  root.setLocalPosition(0, 0, 0);
  root.setLocalEulerAngles(0, 0, 0);
  app.root.addChild(root);

  for (const c of AXIS_CONFIGS) {
    const mat = axisMaterial(c.rgb);
    const ent = new Entity(`${c.name}World`, app);
    ent.setLocalEulerAngles(c.ex, c.ey, c.ez);
    ent.setLocalPosition(c.px, c.py, c.pz);
    const mi = new MeshInstance(mesh, mat, ent);
    mi.drawOrder = 0xffffff;
    ent.addComponent("render", {
      meshInstances: [mi],
      castShadows: false,
      receiveShadows: false,
    });
    setAxisGuideRenderLayer(ent);
    root.addChild(ent);
  }

  window.__sogsWorldAxesRoot = root;
  root.enabled = !!window.__sogsWorldGuidesEnabled;
}

function syncWorldAxesGuides(app) {
  const g = app.root.findByName("gsplat");
  if (!g) {
    return;
  }
  if (window.__sogsWorldGuidesEnabled && !window.__sogsWorldAxesRoot) {
    setupWorldAxesGuides(app);
  }
  if (window.__sogsWorldAxesRoot) {
    window.__sogsWorldAxesRoot.enabled = !!window.__sogsWorldGuidesEnabled;
  }
  app.renderNextFrame = true;
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

document.addEventListener("DOMContentLoaded", async () => {
  const bootOptions = getBootOptions();
  postBootEvent("supersplat:bootStart", { quality: bootOptions.quality });
  const { config, configReady, settings } = window.sse;
  try {
    const resolvedConfig = await Promise.resolve(configReady ?? config);
    const bootConfig = {
      ...resolvedConfig,
      lowQuality: bootOptions.lowQuality
    };
    const { poster } = bootConfig;

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
    const viewer = await withTimeout(main(app, camera, settingsJson, bootConfig), MAIN_BOOT_TIMEOUT_MS, "main");

    if (bootOptions.lowQuality) {
      try {
        appElement.highResolution = false;
      } catch {
        /* ignore */
      }
      try {
        viewer.global.state.hqMode = false;
      } catch {
        /* ignore */
      }
      try {
        app.graphicsDevice.maxPixelRatio = 1;
      } catch {
        /* ignore */
      }
    }

    window.__sogsCtx = { viewer, app, camera };

    const gsplatEntity = await waitForValue(() => app.root.findByName("gsplat"), "gsplat");
    await waitForValue(() => viewer.cameraManager, "cameraManager");

    const previewConfig = readPreviewBootConfig();
    if (previewConfig) {
      void setupPreviewScaffold(app, gsplatEntity, previewConfig).catch((error) => {
        console.error("Preview scaffold failed", error);
        setPreviewState({
          enabled: false,
          phase: "error",
          error: error instanceof Error ? error.message : String(error),
        });
      });
    } else {
      setPreviewState({ enabled: false, phase: "idle" });
    }

    applyScenePayload(app, window.__sogsInitialScenePayload ?? {});
    applyInitialSkyboxRotation(app, window.__sogsInitialSkyboxRotation ?? null);
    applyViewerConfig(app, window.__sogsInitialViewerConfig ?? {});
    setupCameraManagerBridge(viewer.cameraManager);
    const initialCameraPose = window.__sogsInitialCameraPose;
    if (initialCameraPose?.position?.length === 3 && initialCameraPose?.target?.length === 3) {
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
        postSogsState();
      }
      if (d.type === "sogs:worldGuides") {
        window.__sogsWorldGuidesEnabled = !!d.enabled;
        syncWorldAxesGuides(app);
        postSogsState();
      }
      if (d.type === "sogs:config") {
        applyViewerConfig(app, d);
        postSogsState();
      }
      if (d.type === "sogs:requestState") {
        postSogsState();
      }
      if (d.type === "sogs:cameraLookAt") {
        window.__sogsCameraPose = {
          position: d.position,
          target: d.target,
          fov: d.fov,
        };
        app.renderNextFrame = true;
        postSogsState();
      }
      if (d.type === "sogs:cameraMode") {
        const scripted = d.mode === "scripted" || d.scripted === true;
        window.__sogsScriptedCamera = !!scripted;
        app.renderNextFrame = true;
        postSogsState();
      }
      if (d.type === "sogs:cameraBounds") {
        window.__sogsCameraYMin =
          typeof d.yMin === "number" && Number.isFinite(d.yMin) ? d.yMin : null;
        window.__sogsCameraMaxRadius =
          typeof d.maxRadiusFromOrigin === "number" && Number.isFinite(d.maxRadiusFromOrigin) && d.maxRadiusFromOrigin > 0
            ? d.maxRadiusFromOrigin
            : null;
        app.renderNextFrame = true;
        postSogsState();
      }
      if (d.type === "sogs:skyboxRotation") {
        try {
          const scene = app.scene;
          if (scene && Array.isArray(d.rotation) && d.rotation.length === 3) {
            const rx = Number(d.rotation[0]);
            const ry = Number(d.rotation[1]);
            const rz = Number(d.rotation[2]);
            if (Number.isFinite(rx) && Number.isFinite(ry) && Number.isFinite(rz)) {
              scene.skyboxRotation = new Quat().setFromEulerAngles(rx, ry, rz);
              app.renderNextFrame = true;
              postSogsState();
            }
          }
        } catch {
          /* ignore */
        }
      }
    });

    /** Tell parent to exit scripted tour / auto-orbit when the user grabs the view (orbit, zoom, touch). */
    const notifyUserInteraction = () => {
      window.parent.postMessage({ type: "sogs:userInteraction" }, "*");
    };
    for (const ev of ["pointerdown", "wheel", "touchstart"]) {
      window.addEventListener(ev, notifyUserInteraction, { capture: true, passive: true });
    }
    postSogsState();
    postBootEvent("supersplat:bridgeReady", { quality: bootOptions.quality });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const stage = message.startsWith("timeout:") ? message.slice("timeout:".length) : "unknown";
    console.error("SOGS boot failed", error);
    postBootEvent("supersplat:bootError", {
      quality: bootOptions.quality,
      stage,
      message,
    });
  }
});
