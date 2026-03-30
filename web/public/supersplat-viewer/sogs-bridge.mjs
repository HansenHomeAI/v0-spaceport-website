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

function setupCameraManagerBridge(cameraManager) {
  const origUpdate = cameraManager.update.bind(cameraManager);
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  let prevScripted = false;

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
      flushSogsAccumulatedInputFrame(frame);
      prevScripted = true;
      return;
    }
    const cam = cameraManager.camera;
    const leftScripted = prevScripted;
    prevScripted = false;
    let focusBeforeClamp = null;
    let skipFirstOrbitAfterScripted = false;
    if (leftScripted) {
      const flushedOnExit = flushSogsAccumulatedInputFrame(frame);
      const frameSameRef = frame === window.__sogsCtx?.viewer?.inputController?.frame;
      if (typeof cameraManager.syncOrbitFromCurrentCamera === "function") {
        cameraManager.syncOrbitFromCurrentCamera();
      }
      const pose = window.__sogsCameraPose;
      const focusOrbit = getFocusPoint(cam);
      focusBeforeClamp = { x: focusOrbit.x, y: focusOrbit.y, z: focusOrbit.z };
      let targetMismatch = null;
      if (pose?.target?.length === 3) {
        const dx = focusOrbit.x - pose.target[0];
        const dy = focusOrbit.y - pose.target[1];
        const dz = focusOrbit.z - pose.target[2];
        targetMismatch = Math.sqrt(dx * dx + dy * dy + dz * dz);
      }
      skipFirstOrbitAfterScripted = true;
      // #region agent log
      fetch("http://127.0.0.1:7854/ingest/47d6cee9-3a45-4acf-a87f-28c0bc8ea975", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "191e7b" },
        body: JSON.stringify({
          sessionId: "191e7b",
          location: "sogs-bridge.mjs:first_free_after_scripted",
          message: "skip_origUpdate_keep_last_look_plus_flush",
          hypothesisId: "H10",
          runId: "skip-orbit-1",
          data: {
            flushedOnExit,
            frameSameRef,
            skippedOrigUpdate: true,
            pos: [cam.position.x, cam.position.y, cam.position.z],
            distance: cam.distance,
            angles: [cam.angles.x, cam.angles.y, cam.angles.z],
            focusFromOrbit: focusBeforeClamp,
            scriptedTarget: pose?.target ? [pose.target[0], pose.target[1], pose.target[2]] : null,
            targetMismatch,
          },
          timestamp: Date.now(),
        }),
      }).catch(() => {});
      // #endregion
    }
    if (!skipFirstOrbitAfterScripted) {
      origUpdate(dt, frame);
    }
    if (typeof window.__sogsUserFov === "number" && Number.isFinite(window.__sogsUserFov)) {
      cameraManager.camera.fov = window.__sogsUserFov;
    }
    let focusPreClampStep = null;
    if (leftScripted) {
      const fPre = getFocusPoint(cam);
      focusPreClampStep = { x: fPre.x, y: fPre.y, z: fPre.z };
    }
    clampCameraFocus(cam);
    if (leftScripted && focusPreClampStep) {
      const focusAfter = getFocusPoint(cam);
      const dx = focusAfter.x - focusPreClampStep.x;
      const dy = focusAfter.y - focusPreClampStep.y;
      const dz = focusAfter.z - focusPreClampStep.z;
      const clampDelta = Math.sqrt(dx * dx + dy * dy + dz * dz);
      // #region agent log
      fetch("http://127.0.0.1:7854/ingest/47d6cee9-3a45-4acf-a87f-28c0bc8ea975", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "191e7b" },
        body: JSON.stringify({
          sessionId: "191e7b",
          location: "sogs-bridge.mjs:setupCameraManagerBridge:after_clamp",
          message: "focus_delta_after_clampCameraFocus",
          hypothesisId: "H2",
          runId: "pre1",
          data: { clampDelta, focusAfter: { x: focusAfter.x, y: focusAfter.y, z: focusAfter.z }, focusPreClampStep },
          timestamp: Date.now(),
        }),
      }).catch(() => {});
      // #endregion
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
      const wasScripted = window.__sogsScriptedCamera;
      const scripted = d.mode === "scripted" || d.scripted === true;
      window.__sogsScriptedCamera = !!scripted;
      if (wasScripted && !window.__sogsScriptedCamera && viewer.cameraManager) {
        const cam = viewer.cameraManager.camera;
        const pose = window.__sogsCameraPose;
        // #region agent log
        fetch("http://127.0.0.1:7854/ingest/47d6cee9-3a45-4acf-a87f-28c0bc8ea975", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "191e7b" },
          body: JSON.stringify({
            sessionId: "191e7b",
            location: "sogs-bridge.mjs:message:cameraMode",
            message: "parent_set_cameraMode_free",
            hypothesisId: "H3",
            runId: "pre1",
            data: {
              pos: [cam.position.x, cam.position.y, cam.position.z],
              distance: cam.distance,
              angles: [cam.angles.x, cam.angles.y, cam.angles.z],
              scriptedPoseTarget: pose?.target ? [pose.target[0], pose.target[1], pose.target[2]] : null,
            },
            timestamp: Date.now(),
          }),
        }).catch(() => {});
        // #endregion
      }
      app.renderNextFrame = true;
    }
  });

  /** Tell parent to exit scripted tour / auto-orbit when the user grabs the view (orbit, zoom, touch). */
  const notifyUserInteraction = (e) => {
    if (window.__sogsScriptedCamera) {
      let pointerNorm = null;
      try {
        const c = window.__sogsCtx?.app?.graphicsDevice?.canvas;
        let cx = e?.clientX;
        let cy = e?.clientY;
        if (e?.touches?.length) {
          cx = e.touches[0].clientX;
          cy = e.touches[0].clientY;
        }
        if (c && cx != null && cy != null) {
          const r = c.getBoundingClientRect();
          const w = r.width || 1;
          const h = r.height || 1;
          pointerNorm = { nx: (cx - r.left) / w, ny: (cy - r.top) / h };
        }
      } catch {
        /* ignore */
      }
      // #region agent log
      fetch("http://127.0.0.1:7854/ingest/47d6cee9-3a45-4acf-a87f-28c0bc8ea975", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "191e7b" },
        body: JSON.stringify({
          sessionId: "191e7b",
          location: "sogs-bridge.mjs:notifyUserInteraction",
          message: "iframe_userInteraction_pointer_norm",
          hypothesisId: "H11",
          runId: "pre1",
          data: { hasPose: !!window.__sogsCameraPose, pointerNorm, evType: e?.type },
          timestamp: Date.now(),
        }),
      }).catch(() => {});
      // #endregion
      window.parent.postMessage({ type: "sogs:userInteraction" }, "*");
    }
  };
  for (const ev of ["pointerdown", "wheel", "touchstart"]) {
    window.addEventListener(ev, notifyUserInteraction, { capture: true, passive: true });
  }
});
