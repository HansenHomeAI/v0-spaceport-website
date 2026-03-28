"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createDefaultScenePayload } from "../../lib/sogsViewerSceneDefaults";
import { DEFAULT_SOGS_BUNDLE_URL, resolveSogsSource, type SogsViewerStage } from "../../lib/sogsViewerBundle";
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
const PRESET_CANYON_CONTENT_URLS = new Set(
  CANYON_VISTA_HOLES.map((hole) => resolveSogsSource(hole.bundleUrl ?? DEFAULT_SOGS_BUNDLE_URL)?.contentUrl).filter(
    (value): value is string => Boolean(value),
  ),
);
const STAGE_LABELS: Record<SogsViewerStage, string> = {
  compressed: "Compressed SOGS bundle",
  "3dgs": "3DGS model",
  sfm: "SfM sparse point cloud",
  direct: "Direct viewer asset",
};

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
  const canyonToolsRef = useRef(true);

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
  const [activeStage, setActiveStage] = useState<SogsViewerStage>("compressed");
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
  const [pathPanelOpen, setPathPanelOpen] = useState(false);
  const [useCanyonTools, setUseCanyonTools] = useState(true);

  const bumpPath = useCallback(() => setPathVersion((v) => v + 1), []);

  useEffect(() => {
    pathPlayingRef.current = pathPlaying;
  }, [pathPlaying]);
  useEffect(() => {
    autoRotateRef.current = autoRotate;
  }, [autoRotate]);
  useEffect(() => {
    canyonToolsRef.current = useCanyonTools;
    if (!useCanyonTools) {
      pathStateRef.current.playing = false;
      pathPlayingRef.current = false;
      setPathPlaying(false);
      setAutoRotate(false);
      setPathPanelOpen(false);
      setPhotoDot(null);
    }
  }, [useCanyonTools]);

  const attemptLoad = useCallback((rawValue: string) => {
    setError(null);
    const resolved = resolveSogsSource(rawValue);
    if (!resolved) {
      setError("Paste an S3 or HTTPS URL for an SfM, 3DGS, or compressed output folder/file.");
      setViewerState("idle");
      return false;
    }
    setViewerState("loading");
    setActiveUrl(resolved.contentUrl);
    setActiveStage(resolved.stage);
    setUseCanyonTools(PRESET_CANYON_CONTENT_URLS.has(resolved.contentUrl));
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
        if (canyonToolsRef.current) {
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
        } else {
          postToWindow(event.source as Window, { type: "sogs:cameraMode", mode: "free" });
          poseRef.current = null;
        }
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

  const toggleDisabled = viewerState !== "ready";

  return (
    <main className="sogs-migrated-root">
      <h1 className="sogs-migrated-sr-only">Canyon Vista (SOGS)</h1>
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
        {useCanyonTools ? <CanyonVignette /> : null}
        {useCanyonTools ? (
          <TapDotsOverlay
            enabled={viewerState === "ready" && showTapDots}
            tapDots={CANYON_VISTA_TAP_DOTS}
            poseRef={poseRef}
            containerRef={containerRef}
            onOpenPhotos={setPhotoDot}
          />
        ) : null}
        {useCanyonTools ? (
          <LotLinesOverlay
            enabled={viewerState === "ready" && showLotLines}
            poseRef={poseRef}
            containerRef={containerRef}
          />
        ) : null}
        {useCanyonTools ? (
          <SoldOverlays
            enabled={viewerState === "ready" && showSoldLabels}
            hotspots={CANYON_VISTA_SOLD_HOTSPOTS}
            poseRef={poseRef}
            containerRef={containerRef}
          />
        ) : null}
      </div>

      {/* Canyon-Vista: top-right editor toggles (HansenHomeAI/Canyon-Vista index.html) */}
      {useCanyonTools ? <div className="editor-toggles-wrap" id="editorTogglesWrap">
        <div className="animation-editor-toggle-wrap">
          <button
            type="button"
            id="animationEditorToggle"
            className={`lot-editor-toggle animation-editor-toggle-icon-only ${pathPanelOpen ? "active" : ""}`}
            aria-pressed={pathPanelOpen}
            aria-label="Toggle camera path editor"
            data-testid="path-editor-toggle"
            disabled={toggleDisabled}
            onClick={() => setPathPanelOpen((o) => !o)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M4 18.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z" />
              <path d="M20 10.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z" />
              <path d="M12 21a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z" />
              <path d="M6.2 14.2 17.7 9" />
              <path d="M10.4 18.3 6.3 16" />
            </svg>
          </button>
        </div>
        <div className="lot-editor-toggle-wrap">
          <button
            type="button"
            className={`lot-editor-toggle animation-editor-toggle-icon-only ${showLotLines ? "active" : ""}`}
            aria-pressed={showLotLines}
            aria-label="Toggle lot lines"
            disabled={toggleDisabled}
            onClick={() => setShowLotLines((v) => !v)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M3 17.5V21h3.5L17.2 10.3l-3.5-3.5L3 17.5z" />
              <path d="M12.4 7.6l3.5 3.5" />
              <path d="M18 6l1.2-1.2a1.8 1.8 0 1 1 2.5 2.5L20.5 8.5" />
            </svg>
          </button>
        </div>
        <div className="lot-editor-toggle-wrap">
          <button
            type="button"
            className={`lot-editor-toggle animation-editor-toggle-icon-only ${showTapDots ? "active" : ""}`}
            aria-pressed={showTapDots}
            aria-label="Toggle tap labels"
            disabled={toggleDisabled}
            onClick={() => setShowTapDots((v) => !v)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="3.5" />
            </svg>
          </button>
        </div>
        <div className="lot-editor-toggle-wrap">
          <button
            type="button"
            className={`lot-editor-toggle animation-editor-toggle-icon-only ${showSoldLabels ? "active" : ""}`}
            aria-pressed={showSoldLabels}
            aria-label="Toggle sold labels"
            disabled={toggleDisabled}
            onClick={() => setShowSoldLabels((v) => !v)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
              <line x1="7" y1="7" x2="7.01" y2="7" />
            </svg>
          </button>
        </div>
        <div className="lot-editor-toggle-wrap">
          <button
            type="button"
            className={`lot-editor-toggle animation-editor-toggle-icon-only ${autoRotate ? "active" : ""}`}
            aria-pressed={autoRotate}
            aria-label="Toggle auto-rotate"
            disabled={toggleDisabled}
            onClick={() => {
              setAutoRotate((v) => {
                const next = !v;
                if (next) {
                  setPathPlaying(false);
                }
                return next;
              });
            }}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M21 12a9 9 0 1 1-3-6.7" />
              <polyline points="21 3 21 9 15 9" />
            </svg>
          </button>
        </div>
      </div> : null}

      {useCanyonTools ? (
        <AnimationPathPanel
          open={pathPanelOpen}
          onClose={() => setPathPanelOpen(false)}
          pathStateRef={pathStateRef}
          pathVersion={pathVersion}
          bumpPath={bumpPath}
          disabled={toggleDisabled}
          onSeekCheckpoint={onSeekCheckpoint}
          onAddFromCurrentView={onAddFromCurrentView}
          onPlayTour={onPlayTour}
          onStopTour={onStopTour}
          pathPlaying={pathPlaying}
        />
      ) : null}

      {/* Canyon-Vista: bottom-left glass menu */}
      {useCanyonTools ? <div className="menu-container" id="menuContainer">
        <button
          type="button"
          className="menu-button"
          data-testid="focus-scene-center"
          aria-label="Focus scene"
          disabled={viewerState !== "ready"}
          onClick={onFocusSceneCenter}
        >
          <svg
            className="sogs-focus-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
          >
            <circle cx="12" cy="12" r="3" />
            <line x1="12" y1="2" x2="12" y2="5" />
            <line x1="12" y1="19" x2="12" y2="22" />
            <line x1="2" y1="12" x2="5" y2="12" />
            <line x1="19" y1="12" x2="22" y2="12" />
          </svg>
        </button>
        {viewerState === "ready" ? (
          <CanyonCompassLive
            poseRef={poseRef}
            orbitTarget={CANYON_VISTA_HOLE_VIEW.target}
            northDeg={CANYON_VISTA_HOLE_VIEW.northDirection}
            onClick={onFaceNorth}
          />
        ) : null}
      </div> : null}

      <div className="lot-editor-panel sogs-bundle-panel" aria-label="SOGS bundle">
        <div className="lot-editor-title">Source</div>
        <p className="lot-editor-status">Detected: {STAGE_LABELS[activeStage]}</p>
        {useCanyonTools ? (
          <div className="lot-editor-field sogs-bundle-hole-field">
            <label htmlFor="sogs-hole-picker">Hole</label>
            <select
              id="sogs-hole-picker"
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
          </div>
        ) : null}
        <form
          className="sogs-bundle-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (attemptLoad(inputUrl)) setPathPlaying(false);
          }}
        >
          <div className="lot-editor-field">
            <label htmlFor="sogs-migrated-url">Pipeline URL</label>
            <input
              id="sogs-migrated-url"
              type="text"
              inputMode="url"
              spellCheck={false}
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              placeholder="s3://… or https://…/meta.json | model.tar.gz | colmap/"
            />
          </div>
          <div className="lot-editor-actions sogs-bundle-actions">
            <button type="submit" className="lot-editor-action-btn" disabled={viewerState === "loading"}>
              Load
            </button>
          </div>
        </form>
        {error ? <p className="sogs-bundle-error">{error}</p> : null}
        {viewerState === "loading" ? <p className="lot-editor-status">Loading viewer…</p> : null}
      </div>

      {useCanyonTools ? <CanyonPhotoModal dot={photoDot} onClose={() => setPhotoDot(null)} /> : null}
    </main>
  );
}
