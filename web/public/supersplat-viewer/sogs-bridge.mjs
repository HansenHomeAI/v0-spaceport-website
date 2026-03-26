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
  StandardMaterial,
  Vec3,
} from "https://esm.sh/playcanvas@2.13.2";

/** Parent-driven camera (position + look-at). When `sogs:cameraMode` is `scripted`, orbit input is skipped. */
const tmpFrom = new Vec3();
const tmpTo = new Vec3();

const AXIS_LEN = 45;
const AXIS_RADIUS = 0.28;

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
function setupCameraManagerBridge(cameraManager) {
  const origUpdate = cameraManager.update.bind(cameraManager);
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
    }
  };
}

/**
 * Move splat in world XZ (Y unchanged):
 * - Touchscreens: TouchEvent API (2-finger centroid) — passive:false so preventDefault works (iOS).
 * - Trackpads: wheel with deltaX/deltaY (two-finger pan is not two Pointer touches).
 * - Pointer fallback: 2 touch pointers if Touch API did not claim the gesture.
 * - Middle mouse on desktop (left-drag stays orbit).
 * All listeners use capture phase so we run before the viewer’s bubble handlers.
 */
function setupSogsSplatWorldXzDrag(app) {
  const canvas = app.graphicsDevice?.canvas;
  if (!canvas) {
    return;
  }

  /** Screen pixels → world units (pointer / Touch centroid) */
  const SENS = 0.0009;
  /** Normalized wheel delta → world (trackpad sends larger numbers than pointer px) */
  const WHEEL_SENS = 0.00038;

  /** While true, Touch API owns the gesture — skip pointer duplicate handling */
  let touchTwoFingerActive = false;

  /** @type {{ mode: "touch2" | "mouse"; x: number; y: number } | null} */
  let pointerDrag = null;
  /** pointerId → last client position (touch, pointer fallback) */
  const touchPts = new Map();

  /** @type {{ x: number; y: number } | null} */
  let touchCentroidDrag = null;

  const centroidFromTouchList = (tl) => {
    if (tl.length < 2) {
      return null;
    }
    const a = tl[0];
    const b = tl[1];
    return { x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 };
  };

  const touchCentroidFromMap = () => {
    if (touchPts.size < 2) {
      return null;
    }
    const pts = [...touchPts.values()];
    const a = pts[0];
    const b = pts[1];
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  };

  const applyWorldDelta = (dwx, dwy) => {
    const g = app.root.findByName("gsplat");
    if (!g) {
      return;
    }
    const p = g.getPosition();
    g.setPosition(p.x + dwx, p.y, p.z - dwy);
    app.renderNextFrame = true;
    postSogsState();
  };

  const applyPixelDelta = (dx, dy, e) => {
    applyWorldDelta(dx * SENS, dy * SENS);
    e.preventDefault();
    e.stopImmediatePropagation();
  };

  const syncTouchPoint = (e) => {
    if (e.pointerType === "touch") {
      touchPts.set(e.pointerId, { x: e.clientX, y: e.clientY });
    }
  };

  const touchOpts = { capture: true, passive: false };

  canvas.addEventListener(
    "touchstart",
    (e) => {
      if (e.touches.length < 2) {
        return;
      }
      const c = centroidFromTouchList(e.touches);
      if (!c) {
        return;
      }
      touchTwoFingerActive = true;
      touchCentroidDrag = { x: c.x, y: c.y };
      e.preventDefault();
      e.stopImmediatePropagation();
    },
    touchOpts,
  );

  canvas.addEventListener(
    "touchmove",
    (e) => {
      if (e.touches.length < 2) {
        return;
      }
      if (!touchCentroidDrag) {
        const c0 = centroidFromTouchList(e.touches);
        if (c0) {
          touchCentroidDrag = { x: c0.x, y: c0.y };
        }
        return;
      }
      const c = centroidFromTouchList(e.touches);
      if (!c) {
        return;
      }
      const dx = c.x - touchCentroidDrag.x;
      const dy = c.y - touchCentroidDrag.y;
      touchCentroidDrag.x = c.x;
      touchCentroidDrag.y = c.y;
      applyPixelDelta(dx, dy, e);
    },
    touchOpts,
  );

  const endTouchCluster = (e) => {
    if (e.touches.length < 2) {
      touchCentroidDrag = null;
      touchTwoFingerActive = false;
    }
  };
  canvas.addEventListener("touchend", endTouchCluster, touchOpts);
  canvas.addEventListener("touchcancel", endTouchCluster, touchOpts);

  canvas.addEventListener(
    "wheel",
    (e) => {
      if (e.ctrlKey) {
        return;
      }
      if (touchTwoFingerActive) {
        return;
      }
      const ax = Math.abs(e.deltaX);
      const ay = Math.abs(e.deltaY);
      if (ax < 0.5 && ay < 0.5) {
        return;
      }
      /** Vertical-only scroll keeps orbit zoom; horizontal or diagonal = splat pan (trackpad two-finger). */
      if (ax < 1 && ay > ax * 2) {
        return;
      }
      applyWorldDelta(e.deltaX * WHEEL_SENS, e.deltaY * WHEEL_SENS);
      e.preventDefault();
      e.stopImmediatePropagation();
    },
    { capture: true, passive: false },
  );

  canvas.addEventListener(
    "pointerdown",
    (e) => {
      if (e.pointerType === "touch" && touchTwoFingerActive) {
        return;
      }
      const g = app.root.findByName("gsplat");
      if (!g) {
        return;
      }
      syncTouchPoint(e);
      if (e.pointerType === "touch" && touchPts.size === 2) {
        const c = touchCentroidFromMap();
        if (c) {
          pointerDrag = { mode: "touch2", x: c.x, y: c.y };
          e.preventDefault();
          e.stopImmediatePropagation();
        }
        return;
      }
      if (e.pointerType === "mouse" && e.button === 1) {
        pointerDrag = { mode: "mouse", x: e.clientX, y: e.clientY };
        try {
          canvas.setPointerCapture(e.pointerId);
        } catch {
          /* ignore */
        }
        e.preventDefault();
        e.stopImmediatePropagation();
      }
    },
    true,
  );

  canvas.addEventListener(
    "pointermove",
    (e) => {
      if (e.pointerType === "touch" && touchTwoFingerActive) {
        return;
      }
      syncTouchPoint(e);

      if (!pointerDrag && e.pointerType === "touch" && touchPts.size >= 2) {
        const c = touchCentroidFromMap();
        if (c) {
          pointerDrag = { mode: "touch2", x: c.x, y: c.y };
        }
      }

      if (!pointerDrag) {
        return;
      }

      if (pointerDrag.mode === "touch2") {
        if (touchPts.size < 2) {
          pointerDrag = null;
          return;
        }
        const c = touchCentroidFromMap();
        if (!c) {
          return;
        }
        const dx = c.x - pointerDrag.x;
        const dy = c.y - pointerDrag.y;
        pointerDrag.x = c.x;
        pointerDrag.y = c.y;
        applyPixelDelta(dx, dy, e);
        return;
      }

      if (pointerDrag.mode === "mouse") {
        const dx = e.clientX - pointerDrag.x;
        const dy = e.clientY - pointerDrag.y;
        pointerDrag.x = e.clientX;
        pointerDrag.y = e.clientY;
        applyPixelDelta(dx, dy, e);
      }
    },
    true,
  );

  const endPointer = (e) => {
    if (e.pointerType === "touch" && touchTwoFingerActive) {
      return;
    }
    if (e.pointerType === "touch") {
      touchPts.delete(e.pointerId);
      if (pointerDrag?.mode === "touch2" && touchPts.size < 2) {
        pointerDrag = null;
      }
      return;
    }
    if (e.pointerType === "mouse" && pointerDrag?.mode === "mouse") {
      if (e.type === "pointercancel" || e.button === 1) {
        pointerDrag = null;
        try {
          canvas.releasePointerCapture(e.pointerId);
        } catch {
          /* ignore */
        }
      }
    }
  };

  canvas.addEventListener("pointerup", endPointer, true);
  canvas.addEventListener("pointercancel", endPointer, true);

  window.__sogsSplatXzDragReady = true;
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
  setupSogsSplatWorldXzDrag(app);

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
      syncSogsAxesGuides(app);
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
