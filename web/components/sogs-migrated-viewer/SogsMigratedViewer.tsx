"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createDefaultScenePayload } from "../../lib/sogsViewerSceneDefaults";
import { DEFAULT_SOGS_BUNDLE_URL, normalizeBundleUrl } from "../../lib/sogsViewerBundle";
import {
  CANYON_VISTA_CAMERA_START_Y,
  CANYON_VISTA_DEFAULT_PATH_CHECKPOINTS,
  CANYON_VISTA_HOLE_VIEW,
  CANYON_VISTA_HOLES,
  CANYON_VISTA_ORBIT,
  CANYON_VISTA_SCENE_ORIGIN,
} from "../../lib/canyon-vista/canyonVistaConfig";
import {
  computeNorthFacingPosition,
  CANYON_VISTA_SOLD_HOTSPOTS,
  CANYON_VISTA_TAP_DOTS,
  type TapDotConfig,
} from "../../lib/canyon-vista/canyonVistaOverlays";
import {
  createInitialPathState,
  jumpToPathStart,
  sampleAutoRotatePose,
  samplePathCamera,
  updatePathAnimation,
} from "../../lib/canyon-vista/pathAnimation";
import { appendCheckpoint, snapCameraToCheckpointKey } from "../../lib/canyon-vista/pathEditing";
import type { PathAnimationState, V3 } from "../../lib/canyon-vista/types";
import type { CameraPose } from "../../lib/canyon-vista/worldProjection";
import { AnimationPathPanel } from "./AnimationPathPanel";
import { CanyonCompassLive } from "./CanyonCompassLive";
import { CanyonPhotoModal } from "./CanyonPhotoModal";
import { CanyonVignette } from "./CanyonVignette";
import { LotLinesOverlay } from "./LotLinesOverlay";
import { SoldOverlays } from "./SoldOverlays";
import { TapDotsOverlay } from "./TapDotsOverlay";
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
  const containerRef = useRef<HTMLDivElement | null>(null);
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

  const poseRef = useRef<CameraPose | null>(null);

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
  const [showTapDots, setShowTapDots] = useState(true);
  const [showLotLines, setShowLotLines] = useState(false);
  const [showSoldLabels, setShowSoldLabels] = useState(false);
  const [pathVersion, setPathVersion] = useState(0);
  const [selectedHoleId, setSelectedHoleId] = useState(() => CANYON_VISTA_HOLES[0]?.id ?? "canyon-vista");
  const [photoDot, setPhotoDot] = useState<TapDotConfig | null>(null);

  const bumpPath = useCallback(() => setPathVersion((v) => v + 1), []);

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
    poseRef.current = null;
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
        const t = CANYON_VISTA_HOLE_VIEW.target;
        const sp = CANYON_VISTA_HOLE_VIEW.startPosition;
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
              position: [sp.x, sp.y, sp.z],
              target: [t.x, t.y, t.z],
              fov: scene.fov,
            },
            "*",
          );
          (event.source as Window).postMessage({ type: "sogs:cameraMode", mode: "free" }, "*");
        } catch {
          /* ignore */
        }
        poseRef.current = {
          position: { x: sp.x, y: sp.y, z: sp.z },
          target: { x: t.x, y: t.y, z: t.z },
          fov: scene.fov,
        };
        lastScriptedRef.current = false;
        setViewerState("ready");
      }

      if (event.data?.type === "sogs:cameraPose" && event.source === iframeRef.current?.contentWindow) {
        if (pathPlayingRef.current || autoRotateRef.current) {
          return;
        }
        const d = event.data as { position: number[]; target: number[]; fov?: number };
        if (!Array.isArray(d.position) || d.position.length < 3) return;
        if (!Array.isArray(d.target) || d.target.length < 3) return;
        poseRef.current = {
          position: { x: d.position[0], y: d.position[1], z: d.position[2] },
          target: { x: d.target[0], y: d.target[1], z: d.target[2] },
          fov: typeof d.fov === "number" && Number.isFinite(d.fov) ? d.fov : createDefaultScenePayload().fov,
        };
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
      const fov = createDefaultScenePayload().fov;

      if (scripted && win) {
        postToWindow(win, { type: "sogs:cameraMode", mode: "scripted" });
        lastScriptedRef.current = true;
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
        poseRef.current = {
          position: { x: outPos.current.x, y: outPos.current.y, z: outPos.current.z },
          target: { x: outTarget.current.x, y: outTarget.current.y, z: outTarget.current.z },
          fov,
        };
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

  const onFaceNorth = () => {
    const p = poseRef.current;
    const win = iframeRef.current?.contentWindow;
    if (!p || !win) return;
    const next = computeNorthFacingPosition(
      p.position,
      CANYON_VISTA_HOLE_VIEW.target,
      CANYON_VISTA_HOLE_VIEW.northDirection,
    );
    const t = CANYON_VISTA_HOLE_VIEW.target;
    postToWindow(win, { type: "sogs:cameraMode", mode: "scripted" });
    postToWindow(win, {
      type: "sogs:cameraLookAt",
      position: [next.x, next.y, next.z],
      target: [t.x, t.y, t.z],
      fov: p.fov,
    });
    poseRef.current = {
      position: { x: next.x, y: next.y, z: next.z },
      target: { x: t.x, y: t.y, z: t.z },
      fov: p.fov,
    };
    window.setTimeout(() => {
      postToWindow(iframeRef.current?.contentWindow, { type: "sogs:cameraMode", mode: "free" });
    }, 100);
  };

  const onFocusSceneCenter = useCallback(() => {
    const p = poseRef.current;
    const win = iframeRef.current?.contentWindow;
    if (!p || !win) return;
    const t = CANYON_VISTA_SCENE_ORIGIN;
    postToWindow(win, { type: "sogs:cameraMode", mode: "scripted" });
    postToWindow(win, {
      type: "sogs:cameraLookAt",
      position: [p.position.x, p.position.y, p.position.z],
      target: [t.x, t.y, t.z],
      fov: p.fov,
    });
    poseRef.current = {
      position: { ...p.position },
      target: { x: t.x, y: t.y, z: t.z },
      fov: p.fov,
    };
    window.setTimeout(() => postToWindow(iframeRef.current?.contentWindow, { type: "sogs:cameraMode", mode: "free" }), 80);
  }, []);

  const onAddFromCurrentView = useCallback(() => {
    const p = poseRef.current;
    if (!p) return;
    appendCheckpoint(pathStateRef.current, {
      position: { ...p.position },
      lookAt: { ...p.target },
      duration: 5,
    });
    bumpPath();
  }, [bumpPath]);

  const onSeekCheckpoint = useCallback(
    (index: number) => {
      pathStateRef.current.playing = false;
      setPathPlaying(false);
      snapCameraToCheckpointKey(pathStateRef.current, index, outPos.current, outTarget.current);
      const win = iframeRef.current?.contentWindow;
      const fov = poseRef.current?.fov ?? createDefaultScenePayload().fov;
      postToWindow(win, { type: "sogs:cameraMode", mode: "scripted" });
      postToWindow(win, {
        type: "sogs:cameraLookAt",
        position: [outPos.current.x, outPos.current.y, outPos.current.z],
        target: [outTarget.current.x, outTarget.current.y, outTarget.current.z],
        fov,
      });
      poseRef.current = {
        position: { x: outPos.current.x, y: outPos.current.y, z: outPos.current.z },
        target: { x: outTarget.current.x, y: outTarget.current.y, z: outTarget.current.z },
        fov,
      };
      window.setTimeout(() => postToWindow(iframeRef.current?.contentWindow, { type: "sogs:cameraMode", mode: "free" }), 80);
      bumpPath();
    },
    [bumpPath],
  );

  return (
    <main className="sogs-migrated-root">
      <div ref={containerRef} className="sogs-migrated-stage">
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
        <CanyonVignette />
        <TapDotsOverlay
          enabled={viewerState === "ready" && showTapDots}
          tapDots={CANYON_VISTA_TAP_DOTS}
          poseRef={poseRef}
          containerRef={containerRef}
          onOpenPhotos={setPhotoDot}
        />
        <LotLinesOverlay
          enabled={viewerState === "ready" && showLotLines}
          poseRef={poseRef}
          containerRef={containerRef}
        />
        <SoldOverlays
          enabled={viewerState === "ready" && showSoldLabels}
          hotspots={CANYON_VISTA_SOLD_HOTSPOTS}
          poseRef={poseRef}
          containerRef={containerRef}
        />
      </div>

      <div className="sogs-migrated-bottom-menu">
        {viewerState === "ready" ? (
          <CanyonCompassLive
            poseRef={poseRef}
            orbitTarget={CANYON_VISTA_HOLE_VIEW.target}
            northDeg={CANYON_VISTA_HOLE_VIEW.northDirection}
            onClick={onFaceNorth}
          />
        ) : null}
        <div className="sogs-migrated-menu-spacer" />
      </div>

      <div className="sogs-migrated-chrome">
        <p className="sogs-migrated-title">Canyon Vista (SOGS)</p>
        <div className="sogs-migrated-actions">
          <label className="sogs-migrated-hole">
            Hole
            <select
              data-testid="sogs-hole-picker"
              value={selectedHoleId}
              onChange={(e) => {
                const id = e.target.value;
                setSelectedHoleId(id);
                const hole = CANYON_VISTA_HOLES.find((h) => h.id === id);
                const url = hole?.bundleUrl ?? DEFAULT_SOGS_BUNDLE_URL;
                setInputUrl(url);
                if (attemptLoad(url)) setPathPlaying(false);
              }}
              disabled={viewerState === "loading"}
            >
              {CANYON_VISTA_HOLES.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="sogs-migrated-btn"
            data-testid="focus-scene-center"
            onClick={onFocusSceneCenter}
            disabled={viewerState !== "ready"}
          >
            Focus scene
          </button>
          <AnimationPathPanel
            pathStateRef={pathStateRef}
            pathVersion={pathVersion}
            bumpPath={bumpPath}
            disabled={viewerState !== "ready"}
            onSeekCheckpoint={onSeekCheckpoint}
            onAddFromCurrentView={onAddFromCurrentView}
          />
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
          <label className="sogs-migrated-check">
            <input
              type="checkbox"
              checked={showTapDots}
              onChange={(e) => setShowTapDots(e.target.checked)}
              disabled={viewerState !== "ready"}
            />
            Tap labels
          </label>
          <label className="sogs-migrated-check">
            <input
              type="checkbox"
              checked={showLotLines}
              onChange={(e) => setShowLotLines(e.target.checked)}
              disabled={viewerState !== "ready"}
            />
            Lot lines
          </label>
          <label className="sogs-migrated-check">
            <input
              type="checkbox"
              checked={showSoldLabels}
              onChange={(e) => setShowSoldLabels(e.target.checked)}
              disabled={viewerState !== "ready"}
            />
            Sold labels
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

      <CanyonPhotoModal dot={photoDot} onClose={() => setPhotoDot(null)} />
    </main>
  );
}
