/**
 * Spaceport SOGS bridge: postMessage API for parent page + optional world axes (PlayCanvas drawLine).
 * Loaded after window.sse is set by index.html.
 */
import { main } from "./index.js";
import { Vec3, Color } from "https://esm.sh/playcanvas@2.13.2";

const AXIS_LEN = 45;

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

function drawGuides(app, gsplatEntity) {
  if (!window.__sogsGuidesEnabled) {
    return;
  }
  const p = new Vec3();
  gsplatEntity.getPosition(p);
  const rot = gsplatEntity.getRotation();
  const ax = new Vec3(1, 0, 0);
  const ay = new Vec3(0, 1, 0);
  const az = new Vec3(0, 0, 1);
  rot.transformVector(ax, ax);
  rot.transformVector(ay, ay);
  rot.transformVector(az, az);
  ax.mulScalar(AXIS_LEN);
  ay.mulScalar(AXIS_LEN);
  az.mulScalar(AXIS_LEN);
  const endX = p.clone().add(ax);
  const endY = p.clone().add(ay);
  const endZ = p.clone().add(az);
  app.drawLine(p, endX, new Color(0.95, 0.25, 0.2));
  app.drawLine(p, endY, new Color(0.35, 0.9, 0.35));
  app.drawLine(p, endZ, new Color(0.35, 0.55, 0.95));
  const dot = 0.35;
  app.drawLine(
    new Vec3(p.x - dot, p.y, p.z),
    new Vec3(p.x + dot, p.y, p.z),
    new Color(1, 1, 1),
  );
  app.drawLine(
    new Vec3(p.x, p.y - dot, p.z),
    new Vec3(p.x, p.y + dot, p.z),
    new Color(1, 1, 1),
  );
  app.drawLine(
    new Vec3(p.x, p.y, p.z - dot),
    new Vec3(p.x, p.y, p.z + dot),
    new Color(1, 1, 1),
  );
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

  app.on("update", () => {
    const g = app.root.findByName("gsplat");
    if (g) {
      drawGuides(app, g);
    }
  });

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
      app.renderNextFrame = true;
    }
    if (d.type === "sogs:requestState") {
      postSogsState();
    }
  });
});
