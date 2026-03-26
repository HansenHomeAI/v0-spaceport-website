"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createDefaultScenePayload } from "../../lib/sogsViewerSceneDefaults";
import { DEFAULT_SOGS_BUNDLE_URL, normalizeBundleUrl } from "../../lib/sogsViewerBundle";
import {
  CANYON_VISTA_CAMERA_START_Y,
  CANYON_VISTA_DEFAULT_PATH_CHECKPOINTS,
  CANYON_VISTA_HOLE_VIEW,
  CANYON_VISTA_ORBIT,
} from "../../lib/canyon-vista/canyonVistaConfig";
import {
  createInitialPathState,
  jumpToPathStart,
  sampleAutoRotatePose,
  samplePathCamera,
  updatePathAnimation,
} from "../../lib/canyon-vista/pathAnimation";
import type { PathAnimationState, V3 } from "../../lib/canyon-vista/types";
import "./sogs-migrated-viewer.css";

const VIEWER_BASE = "/supersplat-viewer/index.html";

function postToWindow(win: Window | null | undefined, payload: object) {
  if (!win) return;
  try {
    win.postMessage(payload, "*");
  } catch {
    /* ignore */
  }
}

export default function SogsMigratedViewer() {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const ignoreNextSogsStateRef = useRef(false);

  const pathStateRef = useRef<PathAnimationState>(
    createInitialPathState({
      checkpoints: CANYON_VISTA_DEFAULT_PATH_CHECKPOINTS.map((c) => ({
        position: { ...c.position },
        lookAt: { ...c.lookAt },
        duration: c.duration,
      })),
      enabled: true,
      loop: true,
      speed: 1,
    }),
  );

  const angleRef = useRef((CANYON_VISTA_ORBIT.initialAngle * Math.PI) / 180);
  const lastTickRef = useRef<number | null>(null);
  const outPos = useRef<V3>({ x: 0, y: 0, z: 0 });
  const outTarget = useRef<V3>({ x: 0, y: 0, z: 0 });
  const lastScriptedRef = useRef(false);

  const pathPlayingRef = useRef(false);
  const autoRotateRef = useRef(false);

  const [inputUrl, setInputUrl] = useState(DEFAULT_SOGS_BUNDLE_URL);
  const [activeUrl, setActiveUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [iframeKey, setIframeKey] = useState(0);
  const [viewerState, setViewerState] = useState<"idle" | "loading" | "ready">("idle");
  const [pathPlaying, setPathPlaying] = useState(false);
  const [autoRotate, setAutoRotate] = useState(CANYON_VISTA_ORBIT.autoRotateDefault);

  useEffect(() => {
    pathPlayingRef.current = pathPlaying;
  }, [pathPlaying]);
  useEffect(() => {
    autoRotateRef.current = autoRotate;
  }, [autoRotate]);

  const attemptLoad = useCallback((rawValue: string) => {
    setError(null);
    const normalized = normalizeBundleUrl(rawValue);
    if (!normalized) {
      setError("Enter a valid HTTPS URL to the SOGS bundle (folder or meta.json).");
      setViewerState("idle");
      return false;
    }
    setViewerState("loading");
    setActiveUrl(normalized);
    setIframeKey((k) => k + 1);
    ignoreNextSogsStateRef.current = true;
    return true;
  }, []);

  const viewerSrc = (() => {
    if (!activeUrl) return null;
    const params = new URLSearchParams({
      settings: "/supersplat-viewer/settings.json",
      content: activeUrl,
    });
    return `${VIEWER_BASE}?${params.toString()}`;
  })();

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const q = params.get("url");
    const raw = q?.trim() ? q.trim() : DEFAULT_SOGS_BUNDLE_URL;
    setInputUrl(raw);
    attemptLoad(raw);
  }, [attemptLoad]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.data?.type === "supersplat:firstFrame" && event.source === iframeRef.current?.contentWindow) {
        const scene = createDefaultScenePayload();
        try {
          (event.source as Window).postMessage(
            {
              type: "sogs:apply",
              position: scene.position,
              rotation: scene.rotation,
              scale: scene.scale,
              fov: scene.fov,
            },
            "*",
          );
          (event.source as Window).postMessage(
            {
              type: "sogs:cameraLookAt",
              position: [
                CANYON_VISTA_HOLE_VIEW.startPosition.x,
                CANYON_VISTA_HOLE_VIEW.startPosition.y,
                CANYON_VISTA_HOLE_VIEW.startPosition.z,
              ],
              target: [CANYON_VISTA_HOLE_VIEW.target.x, CANYON_VISTA_HOLE_VIEW.target.y, CANYON_VISTA_HOLE_VIEW.target.z],
              fov: scene.fov,
            },
            "*",
          );
          (event.source as Window).postMessage({ type: "sogs:cameraMode", mode: "free" }, "*");
        } catch {
          /* ignore */
        }
        lastScriptedRef.current = false;
        setViewerState("ready");
      }
      if (event.data?.type === "sogs:state" && event.source === iframeRef.current?.contentWindow) {
        if (ignoreNextSogsStateRef.current) {
          ignoreNextSogsStateRef.current = false;
        }
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  useEffect(() => {
    if (viewerState !== "ready" || !iframeRef.current) return;
    let raf = 0;
    const tick = (now: number) => {
      const win = iframeRef.current?.contentWindow;
      const last = lastTickRef.current;
      lastTickRef.current = now;
      const deltaSeconds = last != null ? Math.min(Math.max((now - last) / 1000, 0), 0.1) : 0;
      const path = pathStateRef.current;
      const playing = pathPlayingRef.current;
      const orbit = autoRotateRef.current;
      const scripted = playing || orbit;

      if (scripted && win) {
        postToWindow(win, { type: "sogs:cameraMode", mode: "scripted" });
        lastScriptedRef.current = true;
        const fov = createDefaultScenePayload().fov;
        if (playing && path.enabled && path.checkpoints.length >= 2) {
          updatePathAnimation(path, deltaSeconds);
          samplePathCamera(path, outPos.current, outTarget.current);
          if (!path.playing && pathPlayingRef.current) {
            pathPlayingRef.current = false;
            setPathPlaying(false);
          }
        } else if (orbit) {
          angleRef.current += CANYON_VISTA_ORBIT.speed * 60 * deltaSeconds;
          sampleAutoRotatePose(
            angleRef.current,
            CANYON_VISTA_ORBIT.center,
            CANYON_VISTA_ORBIT.startRadius,
            CANYON_VISTA_HOLE_VIEW.target,
            CANYON_VISTA_CAMERA_START_Y,
            outPos.current,
          );
          outTarget.current.x = CANYON_VISTA_HOLE_VIEW.target.x;
          outTarget.current.y = CANYON_VISTA_HOLE_VIEW.target.y;
          outTarget.current.z = CANYON_VISTA_HOLE_VIEW.target.z;
        }
        postToWindow(win, {
          type: "sogs:cameraLookAt",
          position: [outPos.current.x, outPos.current.y, outPos.current.z],
          target: [outTarget.current.x, outTarget.current.y, outTarget.current.z],
          fov,
        });
      } else if (win && lastScriptedRef.current) {
        postToWindow(win, { type: "sogs:cameraMode", mode: "free" });
        lastScriptedRef.current = false;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [viewerState]);

  const onPlayTour = () => {
    setAutoRotate(false);
    jumpToPathStart(pathStateRef.current, null);
    setPathPlaying(true);
  };

  const onStopTour = () => {
    pathStateRef.current.playing = false;
    setPathPlaying(false);
  };

  return (
    <main className="sogs-migrated-root">
      {viewerSrc ? (
        <iframe
          key={iframeKey}
          ref={iframeRef}
          src={viewerSrc}
          title="sogs-migrated-viewer"
          className="sogs-migrated-iframe"
          allow="xr-spatial-tracking"
        />
      ) : (
        <div className="sogs-migrated-placeholder" aria-hidden />
      )}

      <div className="sogs-migrated-chrome">
        <p className="sogs-migrated-title">Canyon Vista (SOGS)</p>
        <div className="sogs-migrated-actions">
          <button type="button" className="sogs-migrated-btn" onClick={onPlayTour} disabled={viewerState !== "ready"}>
            Play tour
          </button>
          <button type="button" className="sogs-migrated-btn" onClick={onStopTour} disabled={viewerState !== "ready" || !pathPlaying}>
            Stop
          </button>
          <label className="sogs-migrated-check">
            <input
              type="checkbox"
              checked={autoRotate}
              onChange={(e) => {
                setAutoRotate(e.target.checked);
                if (e.target.checked) setPathPlaying(false);
              }}
              disabled={viewerState !== "ready"}
            />
            Auto-rotate
          </label>
        </div>
        <form
          className="sogs-migrated-url"
          onSubmit={(e) => {
            e.preventDefault();
            if (attemptLoad(inputUrl)) setPathPlaying(false);
          }}
        >
          <label htmlFor="sogs-migrated-url">SOGS URL</label>
          <input
            id="sogs-migrated-url"
            type="url"
            value={inputUrl}
            onChange={(e) => setInputUrl(e.target.value)}
            placeholder="https://…/meta.json"
          />
          <button type="submit" disabled={viewerState === "loading"}>
            Load
          </button>
        </form>
        {error ? <p className="sogs-migrated-error">{error}</p> : null}
        {viewerState === "loading" ? <p className="sogs-migrated-status">Loading viewer…</p> : null}
      </div>
    </main>
  );
}
