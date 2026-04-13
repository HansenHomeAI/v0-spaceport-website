"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CanyonVignette } from "../sogs-migrated-viewer/CanyonVignette";
import { AnimationPathPanel } from "./AnimationPathPanel";
import { CompassLive } from "./CompassLive";
import { DetailsMenuButton, DetailsPanel } from "./DetailsPanel";
import { LotLinesOverlay } from "./LotLinesOverlay";
import { PhotoModal } from "./PhotoModal";
import { SoldOverlays } from "./SoldOverlays";
import { TapPickFeedback } from "./TapPickFeedback";
import { TapDotsOverlay } from "./TapDotsOverlay";
import { resolveViewerBundle, type ResolvedViewerBundle } from "../../lib/manifest-viewer/bundle";
import { buildScenePayload, resolveHoleView, type ViewerManifest } from "../../lib/manifest-viewer/manifest";
import {
  createInitialPathState,
  jumpToPathStart,
  sampleAutoRotatePose,
  samplePathCamera,
  updatePathAnimation,
} from "../../lib/manifest-viewer/pathAnimation";
import { appendCheckpoint, snapCameraToCheckpointKey } from "../../lib/manifest-viewer/pathEditing";
import type { CameraPose, V3 } from "../../lib/manifest-viewer/types";
import "./../sogs-migrated-viewer/sogs-migrated-viewer.css";

const MOBILE_BOOT_TIMEOUT_MS = 6000;
const REQUEST_STATE_INTERVAL_MS = 1500;

function postToWindow(target: Window | null | undefined, payload: object) {
  if (!target) return;
  try {
    target.postMessage(payload, "*");
  } catch {
    /* ignore */
  }
}

function shouldUseMobileBootFallback() {
  if (typeof window === "undefined") return false;
  try {
    if (window.matchMedia?.("(pointer: coarse)").matches) return true;
  } catch {
    /* ignore */
  }
  try {
    if (typeof navigator !== "undefined") {
      if ((navigator as Navigator & { userAgentData?: { mobile?: boolean } }).userAgentData?.mobile) return true;
      if (/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || "")) return true;
      if (navigator.maxTouchPoints > 0 && window.innerWidth <= 1024) return true;
    }
  } catch {
    /* ignore */
  }
  try {
    if (window.matchMedia?.("(hover: none)").matches && window.innerWidth <= 1024) return true;
  } catch {
    /* ignore */
  }
  return false;
}

function getDeveloperToolsEnabled() {
  if (typeof window === "undefined") return false;
  try {
    const query = new URLSearchParams(window.location.search).get("dev");
    if (query === "1" || query === "true") return true;
    if (query === "0" || query === "false") return false;
  } catch {
    /* ignore */
  }
  return false;
}

type ViewerTelemetry = {
  loadedNodeCount: number;
  chunkMetaRequestCount: number;
  chunkMetaAtFirstFrame: number | null;
  totalRequestCount: number;
  firstFrameMs: number | null;
  splatBudget: number | null;
  lodRangeMin: number | null;
  lodRangeMax: number | null;
  rootManifestType: string | null;
  rootManifestUrl: string | null;
};

const EMPTY_VIEWER_TELEMETRY: ViewerTelemetry = {
  loadedNodeCount: 0,
  chunkMetaRequestCount: 0,
  chunkMetaAtFirstFrame: null,
  totalRequestCount: 0,
  firstFrameMs: null,
  splatBudget: null,
  lodRangeMin: null,
  lodRangeMax: null,
  rootManifestType: null,
  rootManifestUrl: null,
};

function parseOptionalInteger(value: string | null | undefined): number | null {
  const parsed = Number.parseInt(value?.trim() ?? "", 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function defaultStreamingBudget(
  streaming: ViewerManifest["bundle"]["streaming"] | undefined,
): number | null {
  if (!streaming) {
    return null;
  }
  if (typeof window === "undefined") {
    return streaming.budgetDesktop ?? streaming.budgetMobile ?? null;
  }

  const ua = window.navigator.userAgent.toLowerCase();
  const isMobileUa = /iphone|ipad|android|mobile|touch/.test(ua);
  const isNarrowViewport = window.innerWidth <= 768;
  if (isMobileUa || isNarrowViewport) {
    return streaming.budgetMobile ?? streaming.budgetDesktop ?? null;
  }
  return streaming.budgetDesktop ?? streaming.budgetMobile ?? null;
}

function resolveStreamingConfig(
  streaming: ViewerManifest["bundle"]["streaming"] | undefined,
): {
  splatBudget: number | null;
  lodRangeMin: number | null;
  lodRangeMax: number | null;
} {
  if (typeof window === "undefined") {
    return {
      splatBudget: defaultStreamingBudget(streaming),
      lodRangeMin: streaming?.lodMin ?? null,
      lodRangeMax: streaming?.lodMax ?? null,
    };
  }

  const params = new URLSearchParams(window.location.search);
  return {
    splatBudget: parseOptionalInteger(params.get("budget")) ?? defaultStreamingBudget(streaming),
    lodRangeMin: parseOptionalInteger(params.get("lodMin")) ?? streaming?.lodMin ?? null,
    lodRangeMax: parseOptionalInteger(params.get("lodMax")) ?? streaming?.lodMax ?? null,
  };
}

type BootMode = "default" | "mobile-fallback";
type PickFeedbackScreen = {
  x: number;
  y: number;
  t: number;
  ringSeq: number;
};

export function ManifestViewer({ manifest }: { manifest: ViewerManifest }) {
  const scene = useMemo(() => buildScenePayload(manifest.scene), [manifest.scene]);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const ignoreNextStateRef = useRef(false);
  const loadRequestRef = useRef(0);
  const poseRef = useRef<CameraPose | null>(null);
  const lastTickRef = useRef<number | null>(null);
  const angleRef = useRef((manifest.orbit.initialAngle * Math.PI) / 180);
  const outPos = useRef<V3>({ x: 0, y: 0, z: 0 });
  const outTarget = useRef<V3>({ x: 0, y: 0, z: 0 });
  const lastScriptedRef = useRef(false);
  const pathPlayingRef = useRef(false);
  const autoRotateRef = useRef(false);
  const orbitFocusRef = useRef<V3>({ ...manifest.holeView.target });
  const activeHoleViewRef = useRef(manifest.holeView);
  const viewerStateRef = useRef<"idle" | "loading" | "ready">("idle");
  const bootModeRef = useRef<BootMode>("default");
  const lastRequestedUrlRef = useRef(manifest.bundle.defaultUrl);
  const fallbackAttemptedRef = useRef(false);
  const introPathPlayedRef = useRef(false);

  const pathStateRef = useRef(
    createInitialPathState({
      checkpoints: manifest.path.checkpoints.map((checkpoint) => ({
        position: { ...checkpoint.position },
        lookAt: { ...checkpoint.lookAt },
        duration: checkpoint.duration,
      })),
      enabled: manifest.path.enabled,
      loop: manifest.path.loop,
      speed: manifest.path.speed,
    }),
  );

  const [inputUrl, setInputUrl] = useState(manifest.bundle.defaultUrl);
  const [activeUrl, setActiveUrl] = useState("");
  const [resolvedBundle, setResolvedBundle] = useState<ResolvedViewerBundle | null>(null);
  const [skyboxUrl, setSkyboxUrl] = useState<string | null>(null);
  const [skyboxPitch, setSkyboxPitch] = useState(0);
  const [skyboxVOffset, setSkyboxVOffset] = useState(0);
  const [iframeKey, setIframeKey] = useState(0);
  const [viewerState, setViewerState] = useState<"idle" | "loading" | "ready">("idle");
  const [bootMode, setBootMode] = useState<BootMode>("default");
  const [error, setError] = useState<string | null>(null);
  const [telemetry, setTelemetry] = useState<ViewerTelemetry>(EMPTY_VIEWER_TELEMETRY);
  const [pathVersion, setPathVersion] = useState(0);
  const [pathPlaying, setPathPlaying] = useState(false);
  const [autoRotate, setAutoRotate] = useState(manifest.orbit.autoRotateDefault ?? false);
  const [showTapDots, setShowTapDots] = useState(manifest.defaults?.showTapDots ?? false);
  const [showLotLines, setShowLotLines] = useState(manifest.defaults?.showLotLines ?? false);
  const [showSoldLabels, setShowSoldLabels] = useState(manifest.defaults?.showSoldLabels ?? false);
  const [pathPanelOpen, setPathPanelOpen] = useState(false);
  const [bundlePanelOpen, setBundlePanelOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [pickFeedbackScreen, setPickFeedbackScreen] = useState<PickFeedbackScreen | null>(null);
  const [photoDot, setPhotoDot] = useState<(typeof manifest.overlays)["tapDots"] extends Array<infer T> ? T | null : null>(null);
  const [selectedHoleId, setSelectedHoleId] = useState(manifest.holes[0]?.id ?? manifest.slug);
  const [developerToolsEnabled] = useState(getDeveloperToolsEnabled);
  const [mobileBootFallbackEnabled] = useState(shouldUseMobileBootFallback);
  const [revealDone, setRevealDone] = useState(false);
  const streamingConfig = useMemo(() => resolveStreamingConfig(manifest.bundle.streaming), [manifest.bundle.streaming]);

  const bumpPath = useCallback(() => setPathVersion((value) => value + 1), []);

  const selectedHole = useMemo(
    () => manifest.holes.find((hole) => hole.id === selectedHoleId) ?? manifest.holes[0],
    [manifest.holes, selectedHoleId],
  );

  const activeHoleView = useMemo(
    () => resolveHoleView(manifest.holeView, selectedHole),
    [manifest.holeView, selectedHole],
  );

  useEffect(() => {
    activeHoleViewRef.current = activeHoleView;
    orbitFocusRef.current = { ...activeHoleView.target };
  }, [activeHoleView]);

  useEffect(() => {
    pathPlayingRef.current = pathPlaying;
  }, [pathPlaying]);

  useEffect(() => {
    autoRotateRef.current = autoRotate;
  }, [autoRotate]);

  useEffect(() => {
    viewerStateRef.current = viewerState;
  }, [viewerState]);

  useEffect(() => {
    bootModeRef.current = bootMode;
  }, [bootMode]);

  useEffect(() => {
    if (viewerState !== "ready") return;
    const id = requestAnimationFrame(() => setRevealDone(true));
    return () => cancelAnimationFrame(id);
  }, [viewerState]);

  useEffect(() => {
    if (viewerState === "loading" || viewerState === "idle") {
      setRevealDone(false);
      introPathPlayedRef.current = false;
    }
  }, [viewerState]);

  useEffect(() => {
    if (
      viewerState !== "ready" ||
      !manifest.intro?.autoPlayPathOnFirstReady ||
      introPathPlayedRef.current
    ) {
      return;
    }

    introPathPlayedRef.current = true;
    const timer = window.setTimeout(() => {
      setAutoRotate(false);
      const focus = orbitFocusRef.current;
      jumpToPathStart(pathStateRef.current, { ...focus });
      pathPlayingRef.current = true;
      setPathPlaying(true);
    }, manifest.intro?.autoPlayDelayMs ?? 400);

    return () => clearTimeout(timer);
  }, [manifest.intro, viewerState]);

  const attemptLoad = useCallback(
    async (
      rawValue: string,
      options?: {
        bootMode?: BootMode;
        resetFallback?: boolean;
      },
    ) => {
      const nextLoadRequest = loadRequestRef.current + 1;
      loadRequestRef.current = nextLoadRequest;
      lastRequestedUrlRef.current = rawValue;

      const nextBootMode =
        options?.bootMode === "mobile-fallback" ||
        (options?.bootMode == null && mobileBootFallbackEnabled)
          ? "mobile-fallback"
          : "default";

      if ((options?.resetFallback ?? true) && nextBootMode === "default") {
        fallbackAttemptedRef.current = false;
      }

      setError(null);
      setViewerState("loading");
      setBootMode(nextBootMode);
      setResolvedBundle(null);
      setTelemetry(EMPTY_VIEWER_TELEMETRY);

      const resolved = await resolveViewerBundle(
        { ...manifest.bundle, useProxy: manifest.bundle.useProxy ?? false },
        rawValue,
      );
      if (nextLoadRequest !== loadRequestRef.current) {
        return false;
      }

      if (!resolved) {
        setError("Enter a valid HTTPS URL to the SOGS bundle (folder or meta.json).");
        setViewerState("idle");
        return false;
      }

      setResolvedBundle(resolved);
      orbitFocusRef.current = { ...activeHoleViewRef.current.target };
      setSkyboxUrl(resolved.skyboxUrl);
      setSkyboxPitch(resolved.skyboxPitch);
      setSkyboxVOffset(resolved.skyboxVOffset);
      setActiveUrl(resolved.contentUrl);
      setIframeKey((value) => value + 1);
      ignoreNextStateRef.current = true;
      poseRef.current = null;
      return true;
    },
    [manifest.bundle, mobileBootFallbackEnabled],
  );

  const requestMobileBootFallback = useCallback(
    (reason: string) => {
      if (
        !mobileBootFallbackEnabled ||
        fallbackAttemptedRef.current ||
        bootModeRef.current === "mobile-fallback" ||
        viewerStateRef.current === "ready"
      ) {
        return false;
      }

      fallbackAttemptedRef.current = true;
      pathStateRef.current.playing = false;
      pathPlayingRef.current = false;
      autoRotateRef.current = false;
      setPathPlaying(false);
      setAutoRotate(false);
      try {
        console.warn(`[viewer] mobile boot fallback: ${reason}`);
      } catch {
        /* ignore */
      }
      void attemptLoad(lastRequestedUrlRef.current, {
        bootMode: "mobile-fallback",
        resetFallback: false,
      });
      return true;
    },
    [attemptLoad, mobileBootFallbackEnabled],
  );

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const raw = params.get("url")?.trim() || manifest.holes[0]?.bundleUrl || manifest.bundle.defaultUrl;
    setInputUrl(raw);
    void attemptLoad(raw, { bootMode: "default" });
  }, [attemptLoad, manifest.bundle.defaultUrl, manifest.holes]);

  useEffect(() => {
    if (!mobileBootFallbackEnabled || viewerState !== "loading" || bootMode !== "default") {
      return;
    }
    const timer = window.setTimeout(() => {
      requestMobileBootFallback("first-frame-timeout");
    }, MOBILE_BOOT_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, [bootMode, mobileBootFallbackEnabled, requestMobileBootFallback, viewerState, iframeKey]);

  const viewerSrc = useMemo(() => {
    if (!activeUrl) return null;
    const params = new URLSearchParams({
      settings: manifest.bundle.viewerSettingsPath ?? "/supersplat-viewer/settings.json",
      content: activeUrl,
    });
    if (skyboxUrl?.trim()) {
      params.set("skybox", skyboxUrl.trim());
      params.set("skyboxPitch", String(skyboxPitch));
      params.set("skyboxVOffset", String(skyboxVOffset));
    }
    if (bootMode === "mobile-fallback") {
      params.set("quality", "lq");
      params.set("bootMode", "mobile-fallback");
    }
    if (streamingConfig.splatBudget != null) {
      params.set("budget", String(streamingConfig.splatBudget));
    }
    if (streamingConfig.lodRangeMin != null) {
      params.set("lodMin", String(streamingConfig.lodRangeMin));
    }
    if (streamingConfig.lodRangeMax != null) {
      params.set("lodMax", String(streamingConfig.lodRangeMax));
    }
    if (!developerToolsEnabled) {
      params.set("noui", "1");
    }
    return `${manifest.bundle.viewerBase ?? "/supersplat-viewer/index.html"}?${params.toString()}`;
  }, [
    activeUrl,
    bootMode,
    developerToolsEnabled,
    manifest.bundle.viewerBase,
    manifest.bundle.viewerSettingsPath,
    skyboxPitch,
    skyboxUrl,
    skyboxVOffset,
    streamingConfig,
  ]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.source !== iframeRef.current?.contentWindow) return;

      if (event.data?.type === "supersplat:firstFrame") {
        const holeView = activeHoleViewRef.current;
        const skyboxRotation = manifest.scene.skyboxRotation;
        ignoreNextStateRef.current = true;
        postToWindow(event.source as Window, {
          type: "sogs:apply",
          position: scene.position,
          rotation: scene.rotation,
          scale: scene.scale,
          fov: scene.fov,
        });
        postToWindow(event.source as Window, {
          type: "sogs:cameraLookAt",
          position: [holeView.startPosition.x, holeView.startPosition.y, holeView.startPosition.z],
          target: [holeView.target.x, holeView.target.y, holeView.target.z],
          fov: scene.fov,
        });
        postToWindow(event.source as Window, {
          type: "sogs:config",
          splatBudget: streamingConfig.splatBudget,
          lodRangeMin: streamingConfig.lodRangeMin,
          lodRangeMax: streamingConfig.lodRangeMax,
        });
        postToWindow(event.source as Window, { type: "sogs:cameraMode", mode: "free" });
        if (manifest.cameraBounds) {
          postToWindow(event.source as Window, {
            type: "sogs:cameraBounds",
            yMin: manifest.cameraBounds.yMin,
            maxRadiusFromOrigin: manifest.cameraBounds.maxRadiusFromOrigin,
          });
        }
        if (typeof manifest.scene.showWorldAxes === "boolean") {
          postToWindow(event.source as Window, {
            type: "sogs:worldGuides",
            enabled: manifest.scene.showWorldAxes,
          });
        }
        if (skyboxRotation) {
          postToWindow(event.source as Window, {
            type: "sogs:skyboxRotation",
            rotation: skyboxRotation,
          });
        }

        poseRef.current = {
          position: { ...holeView.startPosition },
          target: { ...holeView.target },
          fov: scene.fov,
        };
        orbitFocusRef.current = { ...holeView.target };
        lastScriptedRef.current = false;
        setViewerState("ready");
      }

      if (event.data?.type === "supersplat:bootError") {
        requestMobileBootFallback(typeof event.data.stage === "string" ? event.data.stage : "boot-error");
      }

      if (event.data?.type === "sogs:userInteraction") {
        if (!pathPlayingRef.current && !autoRotateRef.current) {
          return;
        }
        pathStateRef.current.playing = false;
        pathPlayingRef.current = false;
        setPathPlaying(false);
        setAutoRotate(false);
        postToWindow(event.source as Window, { type: "sogs:cameraMode", mode: "free" });
        lastScriptedRef.current = false;
      }

      if (event.data?.type === "sogs:pickFocus") {
        const data = event.data as {
          world?: number[];
          clientX?: number;
          clientY?: number;
          ringSeq?: number;
          ringT?: number;
        };
        if (Array.isArray(data.world) && data.world.length >= 3) {
          orbitFocusRef.current = {
            x: data.world[0],
            y: data.world[1],
            z: data.world[2],
          };
        }
        if (typeof data.clientX === "number" && typeof data.clientY === "number") {
          const iframeBounds = iframeRef.current?.getBoundingClientRect() ?? { left: 0, top: 0 };
          const ringSeq = typeof data.ringSeq === "number" ? data.ringSeq : null;
          const ringT = typeof data.ringT === "number" ? data.ringT : Date.now();
          setPickFeedbackScreen((previous) => {
            if (ringSeq !== null && previous && previous.ringSeq === ringSeq) {
              return { ...previous, x: iframeBounds.left + data.clientX, y: iframeBounds.top + data.clientY };
            }
            return {
              x: iframeBounds.left + data.clientX,
              y: iframeBounds.top + data.clientY,
              t: ringT,
              ringSeq: ringSeq ?? ringT,
            };
          });
        }
      }

      if (event.data?.type === "sogs:cameraPose") {
        const data = event.data as { position?: number[]; target?: number[]; fov?: number };
        if (!Array.isArray(data.position) || data.position.length < 3) return;
        if (!Array.isArray(data.target) || data.target.length < 3) return;
        if (pathPlayingRef.current || autoRotateRef.current) return;

        poseRef.current = {
          position: { x: data.position[0], y: data.position[1], z: data.position[2] },
          target: { x: data.target[0], y: data.target[1], z: data.target[2] },
          fov: typeof data.fov === "number" && Number.isFinite(data.fov) ? data.fov : scene.fov,
        };
        orbitFocusRef.current = {
          x: data.target[0],
          y: data.target[1],
          z: data.target[2],
        };
      }

      if (event.data?.type === "sogs:state") {
        const data = event.data as {
          loadedNodeCount?: number;
          chunkMetaRequestCount?: number;
          chunkMetaAtFirstFrame?: number | null;
          totalRequestCount?: number;
          firstFrameMs?: number | null;
          splatBudget?: number | null;
          lodRangeMin?: number | null;
          lodRangeMax?: number | null;
          rootManifestType?: string | null;
          rootManifestUrl?: string | null;
        };
        setTelemetry({
          loadedNodeCount:
            typeof data.loadedNodeCount === "number" && Number.isFinite(data.loadedNodeCount)
              ? data.loadedNodeCount
              : 0,
          chunkMetaRequestCount:
            typeof data.chunkMetaRequestCount === "number" && Number.isFinite(data.chunkMetaRequestCount)
              ? data.chunkMetaRequestCount
              : 0,
          chunkMetaAtFirstFrame:
            typeof data.chunkMetaAtFirstFrame === "number" && Number.isFinite(data.chunkMetaAtFirstFrame)
              ? data.chunkMetaAtFirstFrame
              : null,
          totalRequestCount:
            typeof data.totalRequestCount === "number" && Number.isFinite(data.totalRequestCount)
              ? data.totalRequestCount
              : 0,
          firstFrameMs:
            typeof data.firstFrameMs === "number" && Number.isFinite(data.firstFrameMs) ? data.firstFrameMs : null,
          splatBudget:
            typeof data.splatBudget === "number" && Number.isFinite(data.splatBudget) ? data.splatBudget : null,
          lodRangeMin:
            typeof data.lodRangeMin === "number" && Number.isFinite(data.lodRangeMin) ? data.lodRangeMin : null,
          lodRangeMax:
            typeof data.lodRangeMax === "number" && Number.isFinite(data.lodRangeMax) ? data.lodRangeMax : null,
          rootManifestType: typeof data.rootManifestType === "string" ? data.rootManifestType : null,
          rootManifestUrl: typeof data.rootManifestUrl === "string" ? data.rootManifestUrl : null,
        });
        if (ignoreNextStateRef.current) {
          ignoreNextStateRef.current = false;
        }
      }
    };

    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [
    manifest.cameraBounds,
    manifest.scene.showWorldAxes,
    manifest.scene.skyboxRotation,
    requestMobileBootFallback,
    scene,
    streamingConfig.lodRangeMax,
    streamingConfig.lodRangeMin,
    streamingConfig.splatBudget,
  ]);

  useEffect(() => {
    if (!activeUrl || viewerState !== "ready") {
      return;
    }
    const targetWindow = iframeRef.current?.contentWindow;
    postToWindow(targetWindow, {
      type: "sogs:config",
      splatBudget: streamingConfig.splatBudget,
      lodRangeMin: streamingConfig.lodRangeMin,
      lodRangeMax: streamingConfig.lodRangeMax,
    });
    postToWindow(targetWindow, { type: "sogs:requestState" });
  }, [activeUrl, iframeKey, streamingConfig, viewerState]);

  useEffect(() => {
    if (!activeUrl || viewerState !== "ready") {
      return;
    }
    const interval = window.setInterval(
      () => postToWindow(iframeRef.current?.contentWindow, { type: "sogs:requestState" }),
      REQUEST_STATE_INTERVAL_MS,
    );
    return () => window.clearInterval(interval);
  }, [activeUrl, iframeKey, viewerState]);

  useEffect(() => {
    if (viewerState !== "ready") return;
    let raf = 0;

    const tick = (now: number) => {
      const targetWindow = iframeRef.current?.contentWindow;
      const lastTick = lastTickRef.current;
      lastTickRef.current = now;
      const deltaSeconds = lastTick != null ? Math.min(Math.max((now - lastTick) / 1000, 0), 0.1) : 0;
      const pathState = pathStateRef.current;
      const playing = pathPlayingRef.current;
      const orbit = autoRotateRef.current;
      const scripted = playing || orbit;

      if (scripted && targetWindow) {
        postToWindow(targetWindow, { type: "sogs:cameraMode", mode: "scripted" });
        lastScriptedRef.current = true;
        if (playing && pathState.enabled && pathState.checkpoints.length >= 2) {
          updatePathAnimation(pathState, deltaSeconds);
          samplePathCamera(pathState, outPos.current, outTarget.current);
          if (!pathState.playing && pathPlayingRef.current) {
            pathPlayingRef.current = false;
            setPathPlaying(false);
          }
        } else if (orbit) {
          angleRef.current += manifest.orbit.speed * 60 * deltaSeconds;
          const focus = orbitFocusRef.current;
          const center = { x: focus.x, y: manifest.orbit.center.y, z: focus.z };
          outTarget.current.x = focus.x;
          outTarget.current.y = focus.y;
          outTarget.current.z = focus.z;
          sampleAutoRotatePose(
            angleRef.current,
            center,
            manifest.orbit.startRadius,
            focus,
            activeHoleViewRef.current.startPosition.y - manifest.orbit.center.y,
            outPos.current,
          );
        }

        poseRef.current = {
          position: { ...outPos.current },
          target: { ...outTarget.current },
          fov: scene.fov,
        };
        postToWindow(targetWindow, {
          type: "sogs:cameraLookAt",
          position: [outPos.current.x, outPos.current.y, outPos.current.z],
          target: [outTarget.current.x, outTarget.current.y, outTarget.current.z],
          fov: scene.fov,
        });
      } else if (targetWindow && lastScriptedRef.current) {
        postToWindow(targetWindow, { type: "sogs:cameraMode", mode: "free" });
        lastScriptedRef.current = false;
      }

      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [manifest.orbit, scene.fov, viewerState]);

  const onPlayTour = useCallback(() => {
    setAutoRotate(false);
    jumpToPathStart(pathStateRef.current, null);
    pathPlayingRef.current = true;
    setPathPlaying(true);
  }, []);

  const onStopTour = useCallback(() => {
    pathStateRef.current.playing = false;
    pathPlayingRef.current = false;
    setPathPlaying(false);
  }, []);

  const onAddFromCurrentView = useCallback(() => {
    const pose = poseRef.current;
    if (!pose) return;
    appendCheckpoint(pathStateRef.current, {
      position: { ...pose.position },
      lookAt: { ...pose.target },
      duration: 5,
    });
    bumpPath();
  }, [bumpPath]);

  const onSeekCheckpoint = useCallback(
    (index: number) => {
      pathStateRef.current.playing = false;
      pathPlayingRef.current = false;
      setPathPlaying(false);
      snapCameraToCheckpointKey(pathStateRef.current, index, outPos.current, outTarget.current);
      const targetWindow = iframeRef.current?.contentWindow;
      const fov = poseRef.current?.fov ?? scene.fov;
      postToWindow(targetWindow, { type: "sogs:cameraMode", mode: "scripted" });
      postToWindow(targetWindow, {
        type: "sogs:cameraLookAt",
        position: [outPos.current.x, outPos.current.y, outPos.current.z],
        target: [outTarget.current.x, outTarget.current.y, outTarget.current.z],
        fov,
      });
      poseRef.current = {
        position: { ...outPos.current },
        target: { ...outTarget.current },
        fov,
      };
      window.setTimeout(() => postToWindow(iframeRef.current?.contentWindow, { type: "sogs:cameraMode", mode: "free" }), 80);
      bumpPath();
    },
    [bumpPath, scene.fov],
  );

  const onFaceNorth = useCallback(() => {
    const pose = poseRef.current;
    const targetWindow = iframeRef.current?.contentWindow;
    if (!pose || !targetWindow) return;
    const target = orbitFocusRef.current;
    const deltaX = pose.position.x - target.x;
    const deltaZ = pose.position.z - target.z;
    const radius = Math.hypot(deltaX, deltaZ);
    const radians = (activeHoleViewRef.current.northDirection * Math.PI) / 180;
    const next = {
      x: target.x + Math.sin(radians) * radius,
      y: pose.position.y,
      z: target.z + Math.cos(radians) * radius,
    };
    postToWindow(targetWindow, { type: "sogs:cameraMode", mode: "scripted" });
    postToWindow(targetWindow, {
      type: "sogs:cameraLookAt",
      position: [next.x, next.y, next.z],
      target: [target.x, target.y, target.z],
      fov: pose.fov,
    });
    poseRef.current = {
      position: next,
      target: { ...target },
      fov: pose.fov,
    };
    window.setTimeout(() => postToWindow(iframeRef.current?.contentWindow, { type: "sogs:cameraMode", mode: "free" }), 100);
  }, []);

  const onCompassClick = useCallback(() => {
    if ((manifest.compass?.mode ?? "faceNorth") === "animationStart") {
      setAutoRotate(false);
      const focus = orbitFocusRef.current;
      jumpToPathStart(pathStateRef.current, { ...focus });
      pathPlayingRef.current = true;
      setPathPlaying(true);
      return;
    }
    onFaceNorth();
  }, [manifest.compass?.mode, onFaceNorth]);

  const toggleDisabled = viewerState !== "ready";
  const compassAriaLabel =
    (manifest.compass?.mode ?? "faceNorth") === "animationStart" ? "Go to animation start" : "Face north";

  return (
    <main className="sogs-migrated-root">
      <h1 className="sogs-migrated-sr-only">{manifest.text.hiddenTitle}</h1>
      <div ref={containerRef} className="sogs-migrated-stage">
        {viewerSrc ? (
          <iframe
            key={`${iframeKey}-${skyboxUrl ?? "no-skybox"}`}
            ref={iframeRef}
            src={viewerSrc}
            title={manifest.text.iframeTitle}
            className="sogs-migrated-iframe"
            allow="xr-spatial-tracking"
          />
        ) : (
          <div className="sogs-migrated-placeholder" aria-hidden />
        )}
        <CanyonVignette />
        <TapPickFeedback screen={pickFeedbackScreen} />
        {manifest.overlays?.tapDots?.length ? (
          <TapDotsOverlay
            enabled={viewerState === "ready" && showTapDots}
            tapDots={manifest.overlays.tapDots}
            poseRef={poseRef}
            containerRef={containerRef}
            onOpenPhotos={(dot) => {
              setDetailsOpen(false);
              setPhotoDot(dot);
            }}
          />
        ) : null}
        {manifest.overlays?.borderDots?.length && manifest.overlays?.borderLines?.length ? (
          <LotLinesOverlay
            enabled={viewerState === "ready" && showLotLines}
            borderDots={manifest.overlays.borderDots}
            borderLines={manifest.overlays.borderLines}
            poseRef={poseRef}
            containerRef={containerRef}
          />
        ) : null}
        {manifest.overlays?.soldHotspots?.length ? (
          <SoldOverlays
            enabled={viewerState === "ready" && showSoldLabels}
            hotspots={manifest.overlays.soldHotspots}
            poseRef={poseRef}
            containerRef={containerRef}
          />
        ) : null}
        <div
          className={`sogs-migrated-reveal ${revealDone ? "sogs-migrated-reveal--done" : ""}`}
          style={{ transitionDuration: `${manifest.intro?.revealDurationMs ?? 2800}ms` }}
          aria-hidden
        />
      </div>

      {detailsOpen ? (
        <div
          id="overlay-ui"
          className="sogs-migrated-overlay-ui active"
          onClick={() => setDetailsOpen(false)}
          aria-hidden
        />
      ) : null}

      {developerToolsEnabled ? (
        <>
          <div className="editor-toggles-wrap" id="editorTogglesWrap">
            <div className="animation-editor-toggle-wrap">
              <button
                type="button"
                id="animationEditorToggle"
                className={`lot-editor-toggle animation-editor-toggle-icon-only ${pathPanelOpen ? "active" : ""}`}
                aria-pressed={pathPanelOpen}
                aria-label="Toggle camera path editor"
                data-testid="path-editor-toggle"
                disabled={toggleDisabled}
                onClick={() => setPathPanelOpen((value) => !value)}
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
            {manifest.overlays?.borderLines?.length ? (
              <div className="lot-editor-toggle-wrap">
                <button
                  type="button"
                  className={`lot-editor-toggle animation-editor-toggle-icon-only ${showLotLines ? "active" : ""}`}
                  aria-pressed={showLotLines}
                  aria-label="Toggle lot lines"
                  disabled={toggleDisabled}
                  onClick={() => setShowLotLines((value) => !value)}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                    <path d="M3 17.5V21h3.5L17.2 10.3l-3.5-3.5L3 17.5z" />
                    <path d="M12.4 7.6l3.5 3.5" />
                    <path d="M18 6l1.2-1.2a1.8 1.8 0 1 1 2.5 2.5L20.5 8.5" />
                  </svg>
                </button>
              </div>
            ) : null}
            {manifest.overlays?.tapDots?.length ? (
              <div className="lot-editor-toggle-wrap">
                <button
                  type="button"
                  className={`lot-editor-toggle animation-editor-toggle-icon-only ${showTapDots ? "active" : ""}`}
                  aria-pressed={showTapDots}
                  aria-label="Toggle tap labels"
                  disabled={toggleDisabled}
                  onClick={() => setShowTapDots((value) => !value)}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                    <circle cx="12" cy="13" r="3.5" />
                  </svg>
                </button>
              </div>
            ) : null}
            {manifest.overlays?.soldHotspots?.length ? (
              <div className="lot-editor-toggle-wrap">
                <button
                  type="button"
                  className={`lot-editor-toggle animation-editor-toggle-icon-only ${showSoldLabels ? "active" : ""}`}
                  aria-pressed={showSoldLabels}
                  aria-label="Toggle sold labels"
                  disabled={toggleDisabled}
                  onClick={() => setShowSoldLabels((value) => !value)}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                    <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
                    <line x1="7" y1="7" x2="7.01" y2="7" />
                  </svg>
                </button>
              </div>
            ) : null}
            <div className="lot-editor-toggle-wrap">
              <button
                type="button"
                className={`lot-editor-toggle animation-editor-toggle-icon-only ${autoRotate ? "active" : ""}`}
                aria-pressed={autoRotate}
                aria-label="Toggle auto-rotate"
                disabled={toggleDisabled}
                onClick={() => {
                  setAutoRotate((value) => {
                    const next = !value;
                    if (next) {
                      pathPlayingRef.current = false;
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
            <div className="lot-editor-toggle-wrap sogs-bundle-toggle-wrap">
              <button
                type="button"
                id="sogsBundleToggle"
                className={`lot-editor-toggle animation-editor-toggle-icon-only ${bundlePanelOpen ? "active" : ""}`}
                aria-pressed={bundlePanelOpen}
                aria-expanded={bundlePanelOpen}
                aria-controls="manifestBundlePanel"
                aria-label="Toggle bundle loader"
                data-testid="sogs-bundle-toggle"
                disabled={toggleDisabled}
                onClick={() => setBundlePanelOpen((value) => !value)}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                  <path d="M3.27 6.96L12 12.01l8.73-5.05M12 22.08V12" />
                </svg>
              </button>
              <div
                id="manifestBundlePanel"
                className={`lot-editor-panel sogs-bundle-panel ${bundlePanelOpen ? "active" : ""}`}
                aria-label="Viewer bundle"
                aria-hidden={!bundlePanelOpen}
                data-testid="sogs-bundle-panel"
              >
                <div className="animation-editor-header">
                  <div className="lot-editor-title">Bundle</div>
                  <button type="button" className="animation-editor-close" aria-label="Close bundle panel" onClick={() => setBundlePanelOpen(false)}>
                    ×
                  </button>
                </div>
                <div className="lot-editor-field sogs-bundle-hole-field">
                  <label htmlFor="manifest-hole-picker">Manifest</label>
                  <select
                    id="manifest-hole-picker"
                    data-testid="sogs-hole-picker"
                    value={selectedHoleId}
                    onChange={(event) => {
                      const nextHoleId = event.target.value;
                      setSelectedHoleId(nextHoleId);
                      const nextHole = manifest.holes.find((hole) => hole.id === nextHoleId);
                      const nextUrl = nextHole?.bundleUrl ?? manifest.bundle.defaultUrl;
                      setInputUrl(nextUrl);
                      void attemptLoad(nextUrl, { bootMode: "default" }).then((loaded) => {
                        if (loaded) setPathPlaying(false);
                      });
                    }}
                    disabled={viewerState === "loading"}
                  >
                    {manifest.holes.map((hole) => (
                      <option key={hole.id} value={hole.id}>
                        {hole.label}
                      </option>
                    ))}
                  </select>
                </div>
                <form
                  className="sogs-bundle-form"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void attemptLoad(inputUrl, { bootMode: "default" }).then((loaded) => {
                      if (loaded) setPathPlaying(false);
                    });
                  }}
                >
                  <div className="lot-editor-field">
                    <label htmlFor="manifest-url">SOGS URL</label>
                    <input
                      id="manifest-url"
                      type="url"
                      value={inputUrl}
                      onChange={(event) => setInputUrl(event.target.value)}
                      placeholder="https://…/meta.json"
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
            </div>
          </div>
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
        </>
      ) : null}

      <div className="menu-container" id="menuContainer">
        {manifest.details ? (
          <DetailsMenuButton
            disabled={viewerState !== "ready"}
            open={detailsOpen}
            onToggle={() => setDetailsOpen((value) => !value)}
          />
        ) : null}
        {viewerState === "ready" ? (
          <CompassLive onClick={onCompassClick} ariaLabel={compassAriaLabel} />
        ) : null}
      </div>

      <DetailsPanel details={manifest.details} open={detailsOpen} onClose={() => setDetailsOpen(false)} />
      <PhotoModal dot={photoDot} onClose={() => setPhotoDot(null)} />
      <div
        hidden
        data-testid="sogs-bundle-metrics"
        data-bundle-kind={resolvedBundle?.bundleKind ?? ""}
        data-transport={resolvedBundle?.summary.transport ?? ""}
        data-root-file={resolvedBundle?.summary.rootFile ?? ""}
        data-source-url={resolvedBundle?.summary.sourceUrl ?? ""}
        data-lod-levels={resolvedBundle?.summary.lodLevels ?? ""}
        data-chunk-files={resolvedBundle?.summary.chunkFiles ?? ""}
        data-loaded-nodes={telemetry.loadedNodeCount}
        data-chunk-meta-requests={telemetry.chunkMetaRequestCount}
        data-chunk-meta-at-first-frame={telemetry.chunkMetaAtFirstFrame ?? ""}
        data-first-frame-ms={telemetry.firstFrameMs ?? ""}
        data-splat-budget={telemetry.splatBudget ?? streamingConfig.splatBudget ?? ""}
        data-lod-min={telemetry.lodRangeMin ?? streamingConfig.lodRangeMin ?? ""}
        data-lod-max={telemetry.lodRangeMax ?? streamingConfig.lodRangeMax ?? ""}
        data-bounds-min={resolvedBundle?.summary.bounds ? resolvedBundle.summary.bounds.min.join(",") : ""}
        data-bounds-max={resolvedBundle?.summary.bounds ? resolvedBundle.summary.bounds.max.join(",") : ""}
      />
    </main>
  );
}
