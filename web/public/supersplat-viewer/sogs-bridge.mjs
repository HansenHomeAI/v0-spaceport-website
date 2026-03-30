/**
 * Spaceport SOGS bridge: postMessage API for parent page + optional RGB world axes (mesh, not drawLine overlay).
 */
import { main } from "./index.js";
import {
  Color,
  Quat,
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
const GUIDE_LINE_HIT_WIDTH = 56;
const GUIDE_AXIS_SAMPLE_STEP = 0.25;
const DEFAULT_AXIS_COLORS = {
  x: [0.95, 0.22, 0.18],
  y: [0.28, 0.92, 0.32],
  z: [0.32, 0.52, 0.98],
};

window.firstFrame = function sogsFirstFrameHook() {
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
    window.parent.postMessage(
      {
        type: "sogs:state",
        position: [p.x, p.y, p.z],
        rotation: [e.x, e.y, e.z],
        scale: sc.x,
        fov: ctx.camera.camera.fov,
      },
      "*",
    );
  } catch {
    /* ignore */
  }
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

function setAxesEnabled(root, enabled) {
  if (root) {
    root.enabled = enabled;
    if (root.overlay?.root) {
      root.overlay.root.style.display = enabled ? "block" : "none";
    }
  }
}

/**
 * Thin cylinders along world +X / +Y / +Z at the scene origin.
 */
function currentGuidesConfig() {
  return {
    length:
      typeof window.__sogsGuidesLength === "number" && Number.isFinite(window.__sogsGuidesLength)
        ? window.__sogsGuidesLength
        : AXIS_LEN,
    radius:
      typeof window.__sogsGuidesRadius === "number" && Number.isFinite(window.__sogsGuidesRadius)
        ? window.__sogsGuidesRadius
        : AXIS_RADIUS,
    colors: window.__sogsGuidesColors || DEFAULT_AXIS_COLORS,
  };
}

function axisValueText(axis, value) {
  return `${axis.toUpperCase()} ${formatAxisValue(value)}`;
}

function axisPoint(axis, value) {
  if (axis === "x") return new Vec3(value, 0, 0);
  if (axis === "y") return new Vec3(0, value, 0);
  return new Vec3(0, 0, value);
}

function formatAxisValue(value) {
  const rounded = Math.round(value * 100) / 100;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(2).replace(/\.?0+$/, "");
}

function projectWorldPoint(cameraEntity, point) {
  const screen = cameraEntity.camera.worldToScreen(point, new Vec3());
  return { x: screen.x, y: screen.y, z: screen.z };
}

function axisEndpoints(axis, length) {
  if (axis === "x") {
    return [new Vec3(-length, 0, 0), new Vec3(length, 0, 0)];
  }
  if (axis === "y") {
    return [new Vec3(0, -length, 0), new Vec3(0, length, 0)];
  }
  return [new Vec3(0, 0, -length), new Vec3(0, 0, length)];
}

function screenDistance(a, b) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  return Math.hypot(dx, dy);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function axisVisibleScreenSegment(cameraEntity, axis, length, viewportWidth, viewportHeight) {
  const samples = [];
  for (let value = -length; value <= length; value += GUIDE_AXIS_SAMPLE_STEP) {
    const world = axisPoint(axis, value);
    const screen = projectWorldPoint(cameraEntity, world);
    const inFront = screen.z > 0;
    const nearViewport =
      screen.x >= -viewportWidth * 0.25 &&
      screen.x <= viewportWidth * 1.25 &&
      screen.y >= -viewportHeight * 0.25 &&
      screen.y <= viewportHeight * 1.25;
    if (inFront && nearViewport) {
      samples.push({ value, x: screen.x, y: screen.y, z: screen.z });
    }
  }

  if (samples.length < 2) {
    return null;
  }

  return {
    start: samples[0],
    end: samples[samples.length - 1],
    values: samples,
  };
}

function createGuideOverlay(app, cameraEntity, length) {
  const root = document.createElement("div");
  root.style.position = "fixed";
  root.style.inset = "0";
  root.style.pointerEvents = "none";
  root.style.zIndex = "3";

  const markers = [];
  const markerMap = new Map();
  const axisState = {};
  const hoverLabel = document.createElement("div");
  hoverLabel.style.position = "absolute";
  hoverLabel.style.padding = "4px 6px";
  hoverLabel.style.borderRadius = "6px";
  hoverLabel.style.background = "rgba(8, 10, 12, 0.88)";
  hoverLabel.style.border = "1px solid rgba(255, 255, 255, 0.14)";
  hoverLabel.style.color = "#fff";
  hoverLabel.style.font = '600 11px/1 "IBM Plex Sans", sans-serif';
  hoverLabel.style.whiteSpace = "nowrap";
  hoverLabel.style.pointerEvents = "none";
  hoverLabel.style.display = "none";
  hoverLabel.style.transform = "translate(-50%, calc(-100% - 10px))";
  root.appendChild(hoverLabel);

  const overlay = {
    root,
    markers,
    markerMap,
    axisState,
    hoveredAxis: null,
    destroy() {
      root.remove();
    },
  };

  const showHoverLabel = (axis, value, point) => {
    hoverLabel.textContent = axisValueText(axis, value);
    hoverLabel.style.left = `${point.x}px`;
    hoverLabel.style.top = `${point.y}px`;
    hoverLabel.style.display = "block";
  };

  const hideHoverLabel = () => {
    if (!overlay.hoveredAxis) {
      hoverLabel.style.display = "none";
    }
  };

  const markerScreenPoint = (axis, value) => projectWorldPoint(cameraEntity, axisPoint(axis, value));

  const toggleMarker = (axis, value) => {
    const normalizedValue = Math.round(value * 100) / 100;
    const key = `${axis}:${normalizedValue}`;
    const existing = markerMap.get(key);
    if (existing) {
      existing.element.remove();
      markerMap.delete(key);
      const index = markers.indexOf(existing);
      if (index >= 0) {
        markers.splice(index, 1);
      }
      return;
    }

    const color = axisState[axis].rgb;
    const el = document.createElement("button");
    el.type = "button";
    el.setAttribute("aria-label", `marker ${axisValueText(axis, normalizedValue)}`);
    el.style.position = "absolute";
    el.style.width = "12px";
    el.style.height = "12px";
    el.style.borderRadius = "999px";
    el.style.border = `1px solid rgba(${color.join(", ")}, 0.95)`;
    el.style.background = `rgba(${color.join(", ")}, 0.3)`;
    el.style.boxShadow = `0 0 0 1px rgba(0, 0, 0, 0.24), 0 0 10px rgba(${color.join(", ")}, 0.35)`;
    el.style.color = "#fff";
    el.style.font = '600 11px/1 "IBM Plex Sans", sans-serif';
    el.style.padding = "0";
    el.style.margin = "0";
    el.style.pointerEvents = "auto";
    el.style.transform = "translate(-50%, -50%)";
    el.style.cursor = "pointer";

    const label = document.createElement("div");
    label.textContent = axisValueText(axis, normalizedValue);
    label.style.position = "absolute";
    label.style.top = "-28px";
    label.style.left = "50%";
    label.style.transform = "translateX(-50%)";
    label.style.padding = "4px 6px";
    label.style.borderRadius = "6px";
    label.style.background = "rgba(8, 10, 12, 0.88)";
    label.style.border = "1px solid rgba(255, 255, 255, 0.14)";
    label.style.whiteSpace = "nowrap";
    label.style.display = "none";
    label.style.pointerEvents = "none";
    el.appendChild(label);

    el.addEventListener("mouseenter", () => {
      label.style.display = "block";
    });
    el.addEventListener("mouseleave", () => {
      label.style.display = "block";
    });
    el.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleMarker(axis, normalizedValue);
    });

    root.appendChild(el);
    const marker = {
      key,
      axis,
      value: normalizedValue,
      element: el,
      label,
    };
    markers.push(marker);
    markerMap.set(key, marker);
  };

  const createAxisLine = (axis, rgb) => {
    const line = document.createElement("button");
    line.type = "button";
    line.setAttribute("aria-label", `${axis.toUpperCase()} axis`);
    line.style.position = "absolute";
    line.style.height = `${GUIDE_LINE_HIT_WIDTH}px`;
    line.style.border = "0";
    line.style.padding = "0";
    line.style.margin = "0";
    line.style.background = "transparent";
    line.style.pointerEvents = "auto";
    line.style.cursor = "crosshair";
    line.style.transformOrigin = "0 50%";

    const stroke = document.createElement("div");
    stroke.style.position = "absolute";
    stroke.style.left = "0";
    stroke.style.top = "50%";
    stroke.style.width = "100%";
    stroke.style.height = "2px";
    stroke.style.transform = "translateY(-50%)";
    stroke.style.borderRadius = "999px";
    stroke.style.background = `rgba(${rgb.join(", ")}, 0.95)`;
    stroke.style.boxShadow = `0 0 10px rgba(${rgb.join(", ")}, 0.24)`;
    line.appendChild(stroke);

    const state = { axis, line, rgb, start: null, end: null };
    axisState[axis] = state;

    const lineValueFromEvent = (event) => {
      const dx = state.end.x - state.start.x;
      const dy = state.end.y - state.start.y;
      const lengthSq = dx * dx + dy * dy;
      if (lengthSq < 1e-6) {
        return null;
      }
      const px = event.clientX - state.start.x;
      const py = event.clientY - state.start.y;
      const t = clamp((px * dx + py * dy) / lengthSq, 0, 1);
      const value = state.startValue + t * (state.endValue - state.startValue);
      const point = {
        x: state.start.x + dx * t,
        y: state.start.y + dy * t,
      };
      return { value, point };
    };

    line.addEventListener("pointermove", (event) => {
      if (!state.start || !state.end) {
        return;
      }
      const result = lineValueFromEvent(event);
      if (!result) {
        return;
      }
      overlay.hoveredAxis = axis;
      showHoverLabel(axis, result.value, result.point);
    });

    line.addEventListener("pointerleave", () => {
      overlay.hoveredAxis = null;
      hideHoverLabel();
    });

    line.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (!state.start || !state.end) {
        return;
      }
      const result = lineValueFromEvent(event);
      if (!result) {
        return;
      }
      toggleMarker(axis, result.value);
      showHoverLabel(axis, result.value, result.point);
    });

    root.appendChild(line);
  };

  const colors = currentGuidesConfig().colors;
  createAxisLine("x", colors.x.map((value) => Math.round(value * 255)));
  createAxisLine("y", colors.y.map((value) => Math.round(value * 255)));
  createAxisLine("z", colors.z.map((value) => Math.round(value * 255)));

  document.body.appendChild(root);

  overlay.update = () => {
    const width = app.graphicsDevice.width;
    const height = app.graphicsDevice.height;
    for (const axis of ["x", "y", "z"]) {
      const state = axisState[axis];
      const segment = axisVisibleScreenSegment(cameraEntity, axis, length, width, height);
      state.line.style.display = segment ? "block" : "none";
      if (!segment) {
        continue;
      }
      const { start, end } = segment;
      state.start = start;
      state.end = end;
      state.startValue = start.value;
      state.endValue = end.value;
      const distance = screenDistance(start, end);
      const angle = Math.atan2(end.y - start.y, end.x - start.x);
      state.line.style.left = `${start.x}px`;
      state.line.style.top = `${start.y - GUIDE_LINE_HIT_WIDTH / 2}px`;
      state.line.style.width = `${distance}px`;
      state.line.style.transform = `rotate(${angle}rad)`;
      state.line.style.opacity = "1";
    }

    for (const marker of markers) {
      const screen = markerScreenPoint(marker.axis, marker.value);
      const visible = screen.z > 0 && screen.x >= 0 && screen.x <= width && screen.y >= 0 && screen.y <= height;
      marker.element.style.display = visible ? "block" : "none";
      if (!visible) {
        continue;
      }
      marker.element.style.left = `${screen.x}px`;
      marker.element.style.top = `${screen.y}px`;
      marker.label.style.display = "block";
    }
  };

  return overlay;
}

function setupSogsAxesGuides(app, cameraEntity, gsplatEntity) {
  if (window.__sogsAxesRoot) {
    try {
      window.__sogsAxesRoot.destroy();
    } catch {
      /* ignore */
    }
    window.__sogsAxesRoot = null;
  }

  const guides = currentGuidesConfig();
  const [negX, posX] = axisEndpoints("x", guides.length);
  const [negY, posY] = axisEndpoints("y", guides.length);
  const [negZ, posZ] = axisEndpoints("z", guides.length);
  const colorX = new Color(guides.colors.x[0], guides.colors.x[1], guides.colors.x[2]);
  const colorY = new Color(guides.colors.y[0], guides.colors.y[1], guides.colors.y[2]);
  const colorZ = new Color(guides.colors.z[0], guides.colors.z[1], guides.colors.z[2]);
  const overlay = createGuideOverlay(app, cameraEntity, guides.length);
  const draw = () => {
    if (!window.__sogsAxesRoot?.enabled) {
      return;
    }
    app.drawLine(negX, posX, colorX, false);
    app.drawLine(negY, posY, colorY, false);
    app.drawLine(negZ, posZ, colorZ, false);
    overlay.update();
  };

  const root = {
    name: "sogsAxes",
    enabled: true,
    children: [{ name: "sogsAxisX" }, { name: "sogsAxisY" }, { name: "sogsAxisZ" }],
    overlay,
    destroy() {
      app.off("prerender", draw);
      overlay.destroy();
    },
  };
  app.on("prerender", draw);
  window.__sogsAxesRoot = root;
  setAxesEnabled(root, !!window.__sogsGuidesEnabled);
}

function syncSogsAxesGuides(app, cameraEntity) {
  const g = app.root.findByName("gsplat");
  if (!g) {
    return;
  }
  if (window.__sogsGuidesEnabled && !window.__sogsAxesRoot) {
    setupSogsAxesGuides(app, cameraEntity, g);
  }
  if (window.__sogsAxesRoot) {
    setAxesEnabled(window.__sogsAxesRoot, !!window.__sogsGuidesEnabled);
    window.__sogsAxesRoot.overlay?.update?.();
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

  setupCameraManagerBridge(viewer.cameraManager);
  syncSogsAxesGuides(app, camera);
  queueMicrotask(() => {
    window.parent.postMessage({ type: "supersplat:firstFrame" }, "*");
    postSogsState();
  });
  /** Primary pointer + pointermove pan was removed: it fought orbit/touch and caused bounce. */
  window.__sogsSplatXzDragReady = true;

  window.addEventListener("message", (event) => {
    const d = event.data;
    if (!d || typeof d !== "object") {
      return;
    }
    if (d.type === "sogs:apply") {
      const g = app.root.findByName("gsplat");
      if (!g) {
        return;
      }
      if (Array.isArray(d.position) && d.position.length === 3) {
        g.setLocalPosition(d.position[0], d.position[1], d.position[2]);
      }
      if (Array.isArray(d.rotation) && d.rotation.length === 3) {
        g.setLocalEulerAngles(d.rotation[0], d.rotation[1], d.rotation[2]);
      }
      if (typeof d.scale === "number" && Number.isFinite(d.scale)) {
        g.setLocalScale(d.scale, d.scale, d.scale);
      }
      if (typeof d.fov === "number" && Number.isFinite(d.fov)) {
        window.__sogsUserFov = d.fov;
      }
      app.renderNextFrame = true;
      postSogsState();
    }
    if (d.type === "sogs:guides") {
      window.__sogsGuidesEnabled = !!d.enabled;
      if (typeof d.length === "number" && Number.isFinite(d.length)) {
        window.__sogsGuidesLength = d.length;
      }
      if (typeof d.radius === "number" && Number.isFinite(d.radius)) {
        window.__sogsGuidesRadius = d.radius;
      }
      if (d.colors && typeof d.colors === "object") {
        window.__sogsGuidesColors = {
          x: Array.isArray(d.colors.x) ? d.colors.x : DEFAULT_AXIS_COLORS.x,
          y: Array.isArray(d.colors.y) ? d.colors.y : DEFAULT_AXIS_COLORS.y,
          z: Array.isArray(d.colors.z) ? d.colors.z : DEFAULT_AXIS_COLORS.z,
        };
      }
      if (window.__sogsAxesRoot) {
        try {
          window.__sogsAxesRoot.destroy();
        } catch {
          /* ignore */
        }
        window.__sogsAxesRoot = null;
      }
      syncSogsAxesGuides(app, camera);
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
    }
    if (d.type === "sogs:cameraMode") {
      const scripted = d.mode === "scripted" || d.scripted === true;
      window.__sogsScriptedCamera = !!scripted;
      app.renderNextFrame = true;
    }
  });
});
