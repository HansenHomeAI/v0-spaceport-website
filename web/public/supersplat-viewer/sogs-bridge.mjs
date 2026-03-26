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
 * Orbit focus (look-at) is clamped to a horizontal slab: X,Z ∈ [-FOCUS_XZ_MAX, FOCUS_XZ_MAX], Y = FOCUS_Y.
 * - Wheel / trackpad scroll: unchanged — passes through to the viewer (orbit zoom). We no longer intercept wheel.
 * - Primary button drag: pans the orbit focus in the camera tangent plane (same basis as supersplat InputController).
 * - After every camera update, focus is clamped so scripted / orbit drift cannot leave the box.
 */
function hookCameraFocusInteraction(cameraManager, canvas) {
  if (!canvas) {
    return;
  }

  const FOCUS_XZ_MAX = 10;
  const FOCUS_Y = 0;

  let pendPx = 0;
  let pendPy = 0;
  /** @type {{ id: number; x: number; y: number } | null} */
  let focusDrag = null;

  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

  /** Use (ex,ey,ez) numbers — bundled viewer Vec3 is a different class than esm.sh Vec3, so passing cam.angles breaks Quat. */
  const getFocusPoint = (cam) => {
    const q = new Quat().setFromEulerAngles(cam.angles.x, cam.angles.y, cam.angles.z);
    const dir = new Vec3();
    q.transformVector(Vec3.FORWARD, dir);
    dir.mulScalar(cam.distance);
    return new Vec3().copy(cam.position).add(dir);
  };

  const setCameraFromFocus = (cam, focus) => {
    const q = new Quat().setFromEulerAngles(cam.angles.x, cam.angles.y, cam.angles.z);
    const dir = new Vec3();
    q.transformVector(Vec3.FORWARD, dir);
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

  /** Matches supersplat `screenToWorld` (orbit pan): mouse px deltas → world offset at current distance. */
  const screenToWorldPan = (cam, dxPx, dyPx) => {
    const d = cam.distance;
    const fov = cam.fov;
    const rect = canvas.getBoundingClientRect();
    const w = rect.width || 1;
    const h = rect.height || 1;
    const aspect = w / h;
    const halfSlice = d * Math.tan(0.5 * fov * (Math.PI / 180));
    const halfX = halfSlice * aspect;
    const halfY = halfSlice;
    const nx = -(dxPx / w) * 2;
    const ny = (dyPx / h) * 2;
    const local = new Vec3(nx * halfX, ny * halfY, 0);
    const q = new Quat().setFromEulerAngles(cam.angles.x, cam.angles.y, cam.angles.z);
    q.transformVector(local, local);
    return local;
  };

  const orig = cameraManager.update.bind(cameraManager);
  cameraManager.update = (dt, frame) => {
    orig(dt, frame);
    const cam = cameraManager.camera;
    if (pendPx !== 0 || pendPy !== 0) {
      const pan = screenToWorldPan(cam, pendPx, pendPy);
      pendPx = 0;
      pendPy = 0;
      const focus = getFocusPoint(cam);
      focus.add(pan);
      focus.x = clamp(focus.x, -FOCUS_XZ_MAX, FOCUS_XZ_MAX);
      focus.z = clamp(focus.z, -FOCUS_XZ_MAX, FOCUS_XZ_MAX);
      focus.y = FOCUS_Y;
      setCameraFromFocus(cam, focus);
    }
    clampCameraFocus(cam);
  };

  const onPointerDown = (e) => {
    if (e.button !== 0) {
      return;
    }
    if (!canvas.contains(e.target)) {
      return;
    }
    focusDrag = { id: e.pointerId, x: e.clientX, y: e.clientY };
  };

  const onPointerMove = (e) => {
    if (!focusDrag || e.pointerId !== focusDrag.id) {
      return;
    }
    const dx = e.clientX - focusDrag.x;
    const dy = e.clientY - focusDrag.y;
    focusDrag.x = e.clientX;
    focusDrag.y = e.clientY;
    pendPx += dx;
    pendPy += dy;
    e.preventDefault();
    e.stopImmediatePropagation();
  };

  const onPointerEnd = (e) => {
    if (focusDrag && e.pointerId === focusDrag.id) {
      focusDrag = null;
    }
  };

  window.addEventListener("pointerdown", onPointerDown, { capture: true });
  window.addEventListener("pointermove", onPointerMove, { capture: true });
  window.addEventListener("pointerup", onPointerEnd, { capture: true });
  window.addEventListener("pointercancel", onPointerEnd, { capture: true });

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

  hookCameraManagerFov(viewer.cameraManager);
  hookCameraFocusInteraction(viewer.cameraManager, app.graphicsDevice.canvas);

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
