/**
 * Spaceport SOGS bridge: postMessage API for parent page + optional RGB world axes (mesh, not drawLine overlay).
 * Uses PlayCanvas classes from the bundled viewer (`window.__sogsPc`), not a separate esm.sh build.
 */
import { main } from "./index.js";

const {
  Color,
  CylinderGeometry,
  Entity,
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
const PREVIEW_OVERLAY_ID = "sogs-preview-overlay";
const PREVIEW_DOT_COLOR = "rgba(255,255,255,0.96)";
const PREVIEW_HOLE_PADDING_PX = 48;
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
      pointSize: Math.max(0.5, Number.parseFloat(params.get("previewPointSize") ?? "1.35") || 1.35),
      initialVisiblePoints: Math.max(
        0,
        Math.trunc(Number.parseFloat(params.get("previewInitialVisiblePoints") ?? "0") || 0),
      ),
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
    mode: "white-point-cloud",
    revealStyle: "focus-out",
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
  if (controller.frame) {
    cancelAnimationFrame(controller.frame);
  }
  if (controller.fadeTimer) {
    clearTimeout(controller.fadeTimer);
  }
  try {
    window.removeEventListener("pointerdown", controller.fastReveal, true);
    window.removeEventListener("wheel", controller.fastReveal, true);
    window.removeEventListener("touchstart", controller.fastReveal, true);
  } catch {
    /* ignore */
  }
  try {
    controller.canvas?.remove();
  } catch {
    /* ignore */
  }
}

function applyPreviewVisibleCount(controller, visibleCount) {
  if (!controller) {
    return;
  }
  const nextVisible = Math.max(0, Math.min(controller.totalPoints, Math.trunc(visibleCount)));
  if (nextVisible === controller.visiblePoints) {
    return;
  }
  controller.visiblePoints = nextVisible;
  controller.app.renderNextFrame = true;
  setPreviewState({ visiblePoints: nextVisible, totalPoints: controller.totalPoints });
}

function schedulePreviewFade(controller, options = {}) {
  if (!controller) {
    return;
  }
  const startReveal = () => {
    if (controller.fadeTimer) {
      clearTimeout(controller.fadeTimer);
      controller.fadeTimer = 0;
    }
    controller.fadeScheduled = true;
    controller.revealStartedAt = performance.now();
    setPreviewState({ phase: "fading" });
  };
  if (controller.revealStartedAt) {
    if (options.immediate === true) {
      controller.revealStartedAt = Math.min(
        controller.revealStartedAt,
        performance.now() - Math.max(0, controller.config.fadeDurationMs * 0.35),
      );
    }
    return;
  }
  if (controller.fadeScheduled) {
    if (options.immediate === true && controller.fadeTimer) {
      startReveal();
    }
    return;
  }
  controller.fadeScheduled = true;
  if (options.immediate === true) {
    startReveal();
    return;
  }
  controller.fadeTimer = window.setTimeout(startReveal, controller.config.fadeDelayMs);
}

function notifyPreviewFirstFrame() {
  setPreviewState({ fadeRequested: true });
  const controller = window.__sogsPreviewController;
  if (controller) {
    schedulePreviewFade(controller);
  }
}

function decodePreviewPosition(meta, view, offset) {
  const encoding = typeof meta?.encoding === "string" ? meta.encoding : "";
  if (encoding === "position-u16-bounds") {
    const mins = Array.isArray(meta?.bounds?.min) ? meta.bounds.min : null;
    const maxs = Array.isArray(meta?.bounds?.max) ? meta.bounds.max : null;
    if (!mins || !maxs || mins.length !== 3 || maxs.length !== 3) {
      throw new Error("preview-meta-bounds");
    }
    const decodeAxis = (quantized, axis) => {
      const minimum = Number(mins[axis]);
      const maximum = Number(maxs[axis]);
      if (!Number.isFinite(minimum) || !Number.isFinite(maximum) || Math.abs(maximum - minimum) <= 1e-12) {
        return minimum || 0;
      }
      return minimum + (maximum - minimum) * (quantized / 65535);
    };
    return [
      decodeAxis(view.getUint16(offset, true), 0),
      decodeAxis(view.getUint16(offset + 2, true), 1),
      decodeAxis(view.getUint16(offset + 4, true), 2),
    ];
  }
  if (encoding === "position-f32-color-rgba8") {
    return [view.getFloat32(offset, true), view.getFloat32(offset + 4, true), view.getFloat32(offset + 8, true)];
  }
  throw new Error(`preview-encoding:${encoding || "unknown"}`);
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
  const stride = Number(meta.stride ?? 0);
  const count = Number(meta.count ?? 0);
  if (!Number.isFinite(stride) || stride <= 0 || !Number.isFinite(count) || count <= 0 || buffer.byteLength < stride * count) {
    throw new Error("preview-meta-invalid");
  }
  const view = new DataView(buffer);
  const focus = config.focusTarget;
  const points = new Array(count);
  for (let i = 0; i < count; i += 1) {
    const offset = i * stride;
    const [x, y, z] = decodePreviewPosition(meta, view, offset);
    points[i] = {
      x,
      y,
      z,
      distanceSq: (x - focus[0]) ** 2 + (y - focus[1]) ** 2 + (z - focus[2]) ** 2,
    };
  }
  points.sort((a, b) => a.distanceSq - b.distanceSq);
  const localPoints = new Float32Array(count * 3);
  const radialDistances = new Float32Array(count);
  for (let i = 0; i < count; i += 1) {
    const point = points[i];
    const base = i * 3;
    localPoints[base] = point.x;
    localPoints[base + 1] = point.y;
    localPoints[base + 2] = point.z;
    radialDistances[i] = Math.sqrt(point.distanceSq);
  }
  return { meta, localPoints, radialDistances };
}

function createPreviewOverlayCanvas() {
  const existing = document.getElementById(PREVIEW_OVERLAY_ID);
  if (existing instanceof HTMLCanvasElement) {
    existing.remove();
  }
  const canvas = document.createElement("canvas");
  canvas.id = PREVIEW_OVERLAY_ID;
  canvas.setAttribute("aria-hidden", "true");
  Object.assign(canvas.style, {
    position: "fixed",
    inset: "0",
    width: "100%",
    height: "100%",
    pointerEvents: "none",
    zIndex: "999",
  });
  document.body.appendChild(canvas);
  return canvas;
}

function syncPreviewOverlaySize(controller) {
  const sourceCanvas = controller.app?.graphicsDevice?.canvas;
  const pixelWidth = Math.max(1, sourceCanvas?.width ?? Math.round(window.innerWidth * (window.devicePixelRatio || 1)));
  const pixelHeight = Math.max(
    1,
    sourceCanvas?.height ?? Math.round(window.innerHeight * (window.devicePixelRatio || 1)),
  );
  if (controller.canvas.width !== pixelWidth) {
    controller.canvas.width = pixelWidth;
  }
  if (controller.canvas.height !== pixelHeight) {
    controller.canvas.height = pixelHeight;
  }
}

function projectPreviewFocus(controller, out) {
  const camera = window.__sogsCtx?.camera?.camera;
  if (!camera || !controller.focusWorld) {
    out.x = controller.canvas.width * 0.5;
    out.y = controller.canvas.height * 0.5;
    return out;
  }
  camera.worldToScreen(controller.focusWorld, out);
  if (!Number.isFinite(out.x) || !Number.isFinite(out.y)) {
    out.x = controller.canvas.width * 0.5;
    out.y = controller.canvas.height * 0.5;
  }
  return out;
}

function computePreviewMaxRadius(controller, focusScreen) {
  const width = controller.canvas.width;
  const height = controller.canvas.height;
  const padding = PREVIEW_HOLE_PADDING_PX * (window.devicePixelRatio || 1);
  return (
    Math.max(
      Math.hypot(focusScreen.x, focusScreen.y),
      Math.hypot(width - focusScreen.x, focusScreen.y),
      Math.hypot(focusScreen.x, height - focusScreen.y),
      Math.hypot(width - focusScreen.x, height - focusScreen.y),
    ) + padding
  );
}

function getPreviewVisibleCount(controller, now) {
  const initialVisible =
    controller.initialVisiblePoints > 0
      ? Math.min(controller.totalPoints, controller.initialVisiblePoints)
      : controller.totalPoints;
  if (initialVisible >= controller.totalPoints || controller.config.revealDurationMs <= 0) {
    return controller.totalPoints;
  }
  const progress = clamp01((now - controller.pointsStartedAt) / controller.config.revealDurationMs);
  return Math.round(initialVisible + (controller.totalPoints - initialVisible) * easeOutCubic(progress));
}

function renderPreviewOverlay(controller, now) {
  const camera = window.__sogsCtx?.camera?.camera;
  if (!camera || !controller.context) {
    controller.frame = requestAnimationFrame((nextNow) => renderPreviewOverlay(controller, nextNow));
    return;
  }

  syncPreviewOverlaySize(controller);

  const visibleCount = getPreviewVisibleCount(controller, now);
  applyPreviewVisibleCount(controller, visibleCount);

  const ctx = controller.context;
  const width = controller.canvas.width;
  const height = controller.canvas.height;
  const focusScreen = projectPreviewFocus(controller, controller.focusScreen);

  let revealProgress = 0;
  let revealRadius = 0;
  if (controller.revealStartedAt) {
    revealProgress = clamp01((now - controller.revealStartedAt) / Math.max(1, controller.config.fadeDurationMs));
    revealRadius = computePreviewMaxRadius(controller, focusScreen) * easeOutCubic(revealProgress);
  }

  controller.alpha = 1 - revealProgress;
  setPreviewState({
    phase:
      revealProgress >= 1
        ? "done"
        : visibleCount < controller.totalPoints
          ? "revealing"
          : controller.revealStartedAt
            ? "fading"
            : "waiting-for-real",
    alpha: controller.alpha,
  });

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "rgba(0,0,0,1)";
  ctx.fillRect(0, 0, width, height);

  if (revealRadius > 0) {
    ctx.save();
    ctx.globalCompositeOperation = "destination-out";
    ctx.beginPath();
    ctx.arc(focusScreen.x, focusScreen.y, revealRadius, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  const holeRadiusSq = revealRadius * revealRadius;
  const size = Math.max(1, Math.round(controller.pointPixelSize));
  const half = size * 0.5;
  ctx.fillStyle = PREVIEW_DOT_COLOR;

  for (let index = 0; index < visibleCount; index += 1) {
    const base = index * 3;
    controller.worldPoint.set(
      controller.worldPoints[base],
      controller.worldPoints[base + 1],
      controller.worldPoints[base + 2],
    );
    camera.worldToScreen(controller.worldPoint, controller.screenPoint);
    const x = controller.screenPoint.x;
    const y = controller.screenPoint.y;
    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      continue;
    }
    if (revealRadius > 0) {
      const dx = x - focusScreen.x;
      const dy = y - focusScreen.y;
      if (dx * dx + dy * dy <= holeRadiusSq) {
        continue;
      }
    }
    if (x < -size || x > width + size || y < -size || y > height + size) {
      continue;
    }
    ctx.fillRect(Math.round(x - half), Math.round(y - half), size, size);
  }

  if (revealProgress >= 1) {
    setPreviewState({ phase: "done", alpha: 0, visiblePoints: 0 });
    destroyPreviewController(controller);
    if (window.__sogsPreviewController === controller) {
      window.__sogsPreviewController = null;
    }
    return;
  }

  controller.frame = requestAnimationFrame((nextNow) => renderPreviewOverlay(controller, nextNow));
}

async function setupPreviewScaffold(app, gsplatEntity, config, preloadedData = null) {
  if (!config) {
    setPreviewState({
      enabled: false,
      phase: "error",
      error: "preview-config-missing",
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

  const previewData = preloadedData ?? (await loadPreviewPoints(config));
  const totalPoints = Math.trunc((previewData?.localPoints?.length ?? 0) / 3);
  if (!totalPoints) {
    setPreviewState({ phase: "done", enabled: false });
    return null;
  }

  const canvas = createPreviewOverlayCanvas();
  const context = canvas.getContext("2d", { alpha: true, desynchronized: true });
  if (!context) {
    throw new Error("preview-overlay-context");
  }

  const focusLocal = new Vec3(config.focusTarget[0], config.focusTarget[1], config.focusTarget[2]);
  const focusWorld = new Vec3();
  const localPoint = new Vec3();
  const transformedPoint = new Vec3();
  gsplatEntity.getWorldTransform().transformPoint(focusLocal, focusWorld);

  const worldPoints = new Float32Array(previewData.localPoints.length);
  for (let index = 0; index < totalPoints; index += 1) {
    const base = index * 3;
    localPoint.set(
      previewData.localPoints[base],
      previewData.localPoints[base + 1],
      previewData.localPoints[base + 2],
    );
    gsplatEntity.getWorldTransform().transformPoint(localPoint, transformedPoint);
    worldPoints[base] = transformedPoint.x;
    worldPoints[base + 1] = transformedPoint.y;
    worldPoints[base + 2] = transformedPoint.z;
  }

  const controller = {
    app,
    canvas,
    context,
    totalPoints,
    visiblePoints: 0,
    alpha: 1,
    frame: 0,
    fadeTimer: 0,
    fadeScheduled: false,
    revealStartedAt: 0,
    pointsStartedAt: performance.now(),
    initialVisiblePoints: config.initialVisiblePoints,
    worldPoints,
    focusWorld,
    worldPoint: new Vec3(),
    screenPoint: new Vec3(),
    focusScreen: new Vec3(),
    pointPixelSize: config.pointSize * (window.devicePixelRatio || 1),
    config,
    fastReveal: () => schedulePreviewFade(controller, { immediate: true }),
  };
  window.__sogsPreviewController = controller;

  window.addEventListener("pointerdown", controller.fastReveal, true);
  window.addEventListener("wheel", controller.fastReveal, true);
  window.addEventListener("touchstart", controller.fastReveal, true);

  setPreviewState({
    phase: "revealing",
    totalPoints,
    visiblePoints: 0,
    alpha: 1,
  });

  const initialVisible =
    config.initialVisiblePoints > 0 ? Math.min(totalPoints, config.initialVisiblePoints) : totalPoints;
  applyPreviewVisibleCount(controller, initialVisible);
  controller.frame = requestAnimationFrame((now) => renderPreviewOverlay(controller, now));

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
    const previewConfig = readPreviewBootConfig();
    const previewDataPromise = previewConfig
      ? loadPreviewPoints(previewConfig).catch((error) => {
          console.error("Preview preload failed", error);
          return null;
        })
      : null;

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

    if (previewConfig) {
      const previewData = previewDataPromise ? await previewDataPromise : null;
      void setupPreviewScaffold(app, gsplatEntity, previewConfig, previewData).catch((error) => {
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
