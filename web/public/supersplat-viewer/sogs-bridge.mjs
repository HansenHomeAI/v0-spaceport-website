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
} from "https://esm.sh/playcanvas@2.13.2";

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

function hookCameraManagerFov(cameraManager) {
  const orig = cameraManager.update.bind(cameraManager);
  cameraManager.update = (dt, frame) => {
    orig(dt, frame);
    if (typeof window.__sogsUserFov === "number" && Number.isFinite(window.__sogsUserFov)) {
      cameraManager.camera.fov = window.__sogsUserFov;
    }
  };
}

/**
 * Move splat in world XZ (Y unchanged):
 * - Two-finger touch drag (centroid), no modifier keys.
 * - Middle mouse drag on desktop (left-drag stays orbit).
 * Capture phase so the viewer does not orbit/pan at the same time.
 */
function setupSogsSplatWorldXzDrag(app) {
  const canvas = app.graphicsDevice?.canvas;
  if (!canvas) {
    return;
  }

  /** Pixels → world units */
  const SENS = 0.0009;

  /** @type {{ mode: "touch2" | "mouse"; x: number; y: number } | null} */
  let drag = null;
  /** pointerId → last client position (touch only) */
  const touchPts = new Map();

  const touchCentroid = () => {
    if (touchPts.size < 2) {
      return null;
    }
    const pts = [...touchPts.values()];
    const a = pts[0];
    const b = pts[1];
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  };

  const applyDelta = (dx, dy, e) => {
    const g = app.root.findByName("gsplat");
    if (!g) {
      return;
    }
    const p = g.getPosition();
    g.setPosition(p.x + dx * SENS, p.y, p.z - dy * SENS);
    app.renderNextFrame = true;
    postSogsState();
    e.preventDefault();
    e.stopImmediatePropagation();
  };

  const syncTouchPoint = (e) => {
    if (e.pointerType === "touch") {
      touchPts.set(e.pointerId, { x: e.clientX, y: e.clientY });
    }
  };

  canvas.addEventListener(
    "pointerdown",
    (e) => {
      const g = app.root.findByName("gsplat");
      if (!g) {
        return;
      }
      syncTouchPoint(e);
      if (e.pointerType === "touch" && touchPts.size === 2) {
        const c = touchCentroid();
        if (c) {
          drag = { mode: "touch2", x: c.x, y: c.y };
          e.preventDefault();
          e.stopImmediatePropagation();
        }
        return;
      }
      if (e.pointerType === "mouse" && e.button === 1) {
        drag = { mode: "mouse", x: e.clientX, y: e.clientY };
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
      syncTouchPoint(e);

      if (!drag && e.pointerType === "touch" && touchPts.size >= 2) {
        const c = touchCentroid();
        if (c) {
          drag = { mode: "touch2", x: c.x, y: c.y };
        }
      }

      if (!drag) {
        return;
      }

      if (drag.mode === "touch2") {
        if (touchPts.size < 2) {
          drag = null;
          return;
        }
        const c = touchCentroid();
        if (!c) {
          return;
        }
        const dx = c.x - drag.x;
        const dy = c.y - drag.y;
        drag.x = c.x;
        drag.y = c.y;
        applyDelta(dx, dy, e);
        return;
      }

      if (drag.mode === "mouse") {
        const dx = e.clientX - drag.x;
        const dy = e.clientY - drag.y;
        drag.x = e.clientX;
        drag.y = e.clientY;
        applyDelta(dx, dy, e);
      }
    },
    true,
  );

  const endPointer = (e) => {
    if (e.pointerType === "touch") {
      touchPts.delete(e.pointerId);
      if (drag?.mode === "touch2" && touchPts.size < 2) {
        drag = null;
      }
      return;
    }
    if (e.pointerType === "mouse" && drag?.mode === "mouse") {
      if (e.type === "pointercancel" || e.button === 1) {
        drag = null;
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

  hookCameraManagerFov(viewer.cameraManager);
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
  });
});
