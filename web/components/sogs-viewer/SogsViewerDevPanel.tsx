"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  buildSogsSceneExport,
  createDefaultScenePayload,
  type SogsScenePayload,
} from "../../lib/sogsViewerSceneDefaults";
import {
  DEFAULT_SOGS_BUNDLE_URL,
  normalizeBundleUrl,
  resolveSogsViewerBundle,
  type ResolvedSogsViewerBundle,
} from "../../lib/sogsViewerBundle";
import "./sogs-viewer.css";

const VIEWER_BASE = "/supersplat-viewer/index.html";
const REQUEST_STATE_INTERVAL_MS = 1500;

type ViewerLoadState = "idle" | "loading" | "ready";

type StreamingConfig = {
  budget: string;
  lodMin: string;
  lodMax: string;
};

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

const EMPTY_TELEMETRY: ViewerTelemetry = {
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

function getDefaultBudget(): number {
  if (typeof window === "undefined") {
    return 3_000_000;
  }

  const ua = window.navigator.userAgent.toLowerCase();
  const isMobileUa = /iphone|ipad|android|mobile|touch/.test(ua);
  const isNarrowViewport = window.innerWidth <= 768;
  return isMobileUa || isNarrowViewport ? 1_000_000 : 3_000_000;
}

function parseOptionalInteger(value: string): number | null {
  const parsed = Number.parseInt(value.trim(), 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatInteger(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString() : "auto";
}

function formatDurationMs(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? `${(value / 1000).toFixed(1)}s` : "—";
}

function parseStreamingConfig(config: StreamingConfig) {
  return {
    splatBudget: parseOptionalInteger(config.budget),
    lodRangeMin: parseOptionalInteger(config.lodMin),
    lodRangeMax: parseOptionalInteger(config.lodMax),
  };
}

export default function SogsViewerDevPanel() {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  const ignoreNextSogsStateRef = useRef(false);
  const loadRequestRef = useRef(0);

  const [inputUrl, setInputUrl] = useState(DEFAULT_SOGS_BUNDLE_URL);
  const [loadedInputUrl, setLoadedInputUrl] = useState(DEFAULT_SOGS_BUNDLE_URL);
  const [activeUrl, setActiveUrl] = useState("");
  const [resolvedBundle, setResolvedBundle] = useState<ResolvedSogsViewerBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [iframeKey, setIframeKey] = useState(0);
  const [viewerState, setViewerState] = useState<ViewerLoadState>("idle");
  const [telemetry, setTelemetry] = useState<ViewerTelemetry>(EMPTY_TELEMETRY);

  const [streamingConfig, setStreamingConfig] = useState<StreamingConfig>({
    budget: "",
    lodMin: "0",
    lodMax: "",
  });

  const [devOpen, setDevOpen] = useState(false);
  const [guides, setGuides] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const [form, setForm] = useState<SogsScenePayload>(() => createDefaultScenePayload());

  const postToIframe = useCallback((payload: object) => {
    const win = iframeRef.current?.contentWindow;
    if (!win) {
      return;
    }
    try {
      win.postMessage(payload, "*");
    } catch {
      /* ignore */
    }
  }, []);

  const applyStreamingConfigToIframe = useCallback(() => {
    const parsed = parseStreamingConfig(streamingConfig);
    postToIframe({
      type: "sogs:config",
      splatBudget: parsed.splatBudget,
      lodRangeMin: parsed.lodRangeMin,
      lodRangeMax: parsed.lodRangeMax,
    });
  }, [postToIframe, streamingConfig]);

  const attemptLoad = useCallback(async (rawValue: string) => {
    const normalizedInput = normalizeBundleUrl(rawValue);
    if (!normalizedInput) {
      setError("Enter a valid HTTPS URL to the SOGS bundle (folder, meta.json, or lod-meta.json).");
      setViewerState("idle");
      return false;
    }

    const requestId = loadRequestRef.current + 1;
    loadRequestRef.current = requestId;
    setError(null);
    setViewerState("loading");
    setTelemetry(EMPTY_TELEMETRY);

    const resolved = await resolveSogsViewerBundle(normalizedInput);
    if (requestId !== loadRequestRef.current) {
      return false;
    }

    if (!resolved) {
      setError("Could not fetch a valid SuperSplat bundle from that URL.");
      setViewerState("idle");
      return false;
    }

    setResolvedBundle(resolved);
    setLoadedInputUrl(normalizedInput);
    setActiveUrl(resolved.contentUrl);
    setIframeKey((prev) => prev + 1);
    ignoreNextSogsStateRef.current = true;
    return true;
  }, []);

  const viewerSrc = useMemo(() => {
    if (!activeUrl) {
      return null;
    }
    const params = new URLSearchParams({
      settings: "/supersplat-viewer/settings.json",
      content: activeUrl,
    });
    if (resolvedBundle?.skyboxUrl?.trim()) {
      params.set("skybox", resolvedBundle.skyboxUrl.trim());
    }
    const parsed = parseStreamingConfig(streamingConfig);
    if (parsed.splatBudget != null) {
      params.set("budget", String(parsed.splatBudget));
    }
    if (parsed.lodRangeMin != null) {
      params.set("lodMin", String(parsed.lodRangeMin));
    }
    if (parsed.lodRangeMax != null) {
      params.set("lodMax", String(parsed.lodRangeMax));
    }
    return `${VIEWER_BASE}?${params.toString()}`;
  }, [activeUrl, resolvedBundle, streamingConfig]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void attemptLoad(inputUrl);
  };

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.source !== iframeRef.current?.contentWindow || !event.data || typeof event.data !== "object") {
        return;
      }

      if (event.data.type === "supersplat:firstFrame") {
        const defaults = createDefaultScenePayload();
        try {
          (event.source as Window).postMessage(
            {
              type: "sogs:apply",
              position: defaults.position,
              rotation: defaults.rotation,
              scale: defaults.scale,
              fov: defaults.fov,
            },
            "*",
          );
        } catch {
          /* ignore */
        }
        setForm(defaults);
        setViewerState("ready");
        applyStreamingConfigToIframe();
        postToIframe({ type: "sogs:guides", enabled: guides });
        postToIframe({ type: "sogs:requestState" });
      }

      if (event.data.type === "sogs:state") {
        if (ignoreNextSogsStateRef.current) {
          ignoreNextSogsStateRef.current = false;
          return;
        }

        const data = event.data as {
          position?: number[];
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

        if (Array.isArray(data.position) && data.position.length === 3) {
          setForm((current) => ({
            ...current,
            position: [data.position[0], data.position[1], data.position[2]] as [number, number, number],
          }));
        }

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
      }
    };

    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [applyStreamingConfigToIframe, guides, postToIframe]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const params = new URLSearchParams(window.location.search);
    const raw = params.get("url")?.trim() || DEFAULT_SOGS_BUNDLE_URL;
    const defaultBudget = String(parseOptionalInteger(params.get("budget") ?? "") ?? getDefaultBudget());
    const lodMin = params.get("lodMin")?.trim() || "0";
    const lodMax = params.get("lodMax")?.trim() || "";

    setInputUrl(raw);
    setLoadedInputUrl(raw);
    setStreamingConfig({
      budget: defaultBudget,
      lodMin,
      lodMax,
    });
    void attemptLoad(raw);
  }, [attemptLoad]);

  useEffect(() => {
    if (!activeUrl || viewerState !== "ready") {
      return;
    }
    applyStreamingConfigToIframe();
    postToIframe({ type: "sogs:requestState" });
  }, [activeUrl, applyStreamingConfigToIframe, postToIframe, viewerState, iframeKey]);

  useEffect(() => {
    if (!activeUrl) {
      return;
    }
    postToIframe({ type: "sogs:guides", enabled: guides });
  }, [activeUrl, guides, iframeKey, postToIframe]);

  useEffect(() => {
    if (!activeUrl || viewerState !== "ready") {
      return;
    }
    const interval = window.setInterval(() => postToIframe({ type: "sogs:requestState" }), REQUEST_STATE_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [activeUrl, postToIframe, viewerState]);

  useEffect(() => {
    if (typeof window === "undefined" || !loadedInputUrl.trim()) {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    params.set("url", loadedInputUrl.trim());
    const parsed = parseStreamingConfig(streamingConfig);
    if (parsed.splatBudget != null) {
      params.set("budget", String(parsed.splatBudget));
    } else {
      params.delete("budget");
    }
    if (parsed.lodRangeMin != null) {
      params.set("lodMin", String(parsed.lodRangeMin));
    } else {
      params.delete("lodMin");
    }
    if (parsed.lodRangeMax != null) {
      params.set("lodMax", String(parsed.lodRangeMax));
    } else {
      params.delete("lodMax");
    }
    window.history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);
  }, [loadedInputUrl, streamingConfig]);

  useEffect(() => {
    if (!activeUrl || viewerState !== "ready" || !devOpen) {
      return;
    }
    postToIframe({
      type: "sogs:apply",
      position: form.position,
      rotation: form.rotation,
      scale: form.scale,
      fov: form.fov,
    });
  }, [form, activeUrl, viewerState, iframeKey, devOpen, postToIframe]);

  useEffect(() => {
    if (!devOpen) {
      return;
    }
    const onDoc = (event: MouseEvent) => {
      const element = dropdownRef.current;
      if (!element) {
        return;
      }
      if (event.target instanceof Node && !element.contains(event.target)) {
        setDevOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setDevOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [devOpen]);

  const copySceneJson = async () => {
    const payload = buildSogsSceneExport({
      bundleUrl: resolvedBundle?.summary.sourceUrl || loadedInputUrl.trim() || "",
      scene: form,
      guides,
    });
    const text = JSON.stringify(payload, null, 2);
    try {
      await navigator.clipboard.writeText(text);
      setCopyFeedback("Scene JSON copied");
    } catch {
      setCopyFeedback("Copy failed");
    }
    window.setTimeout(() => setCopyFeedback(null), 2200);
  };

  const copyShareLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopyFeedback("Share link copied");
    } catch {
      setCopyFeedback("Copy failed");
    }
    window.setTimeout(() => setCopyFeedback(null), 2200);
  };

  const isSubmitDisabled = !inputUrl.trim();
  const parsedStreaming = parseStreamingConfig(streamingConfig);
  const totalNodes = resolvedBundle?.summary.chunkFiles ?? 0;
  const statusText =
    viewerState === "ready" && resolvedBundle
      ? resolvedBundle.bundleKind === "lod-streaming"
        ? `Ready — Streaming LOD · ${formatInteger(resolvedBundle.summary.lodLevels)} levels · ${formatInteger(totalNodes)} chunk files`
        : `Ready — Single SOG · ${formatInteger(resolvedBundle.summary.splatCount)} splats`
      : viewerState === "loading" && inputUrl
        ? "Loading bundle…"
        : activeUrl
          ? "Idle"
          : "Paste a public HTTPS URL, then Load.";

  return (
    <main className="sogs-shell">
      {viewerSrc ? (
        <iframe
          key={iframeKey}
          ref={iframeRef}
          src={viewerSrc}
          title="sogs-viewer"
          style={{ border: "none", width: "100%", height: "100%", display: "block" }}
          allow="xr-spatial-tracking"
        />
      ) : (
        <div style={{ position: "absolute", inset: 0, backgroundColor: "#000" }} aria-hidden />
      )}

      <form className="sogs-url-panel" onSubmit={handleSubmit}>
        <label htmlFor="sogs-url-input">Bundle URL</label>
        <div className="sogs-url-row">
          <input
            id="sogs-url-input"
            type="url"
            inputMode="url"
            autoComplete="off"
            placeholder="https://…/supersplat_bundle/ or …/lod-meta.json"
            value={inputUrl}
            onChange={(event) => setInputUrl(event.target.value)}
            className={error ? "sogs-input-error" : undefined}
          />
          <button type="submit" className="sogs-btn-primary" disabled={isSubmitDisabled}>
            {viewerState === "loading" ? "…" : "Load"}
          </button>
        </div>

        <div className="sogs-stream-row">
          <div className="sogs-stream-field">
            <label htmlFor="sogs-budget-input">Budget</label>
            <input
              id="sogs-budget-input"
              type="number"
              min={1}
              step={1000}
              value={streamingConfig.budget}
              onChange={(event) =>
                setStreamingConfig((current) => ({
                  ...current,
                  budget: event.target.value,
                }))
              }
            />
          </div>
          <div className="sogs-stream-field">
            <label htmlFor="sogs-lod-min-input">LOD min</label>
            <input
              id="sogs-lod-min-input"
              type="number"
              min={0}
              step={1}
              value={streamingConfig.lodMin}
              onChange={(event) =>
                setStreamingConfig((current) => ({
                  ...current,
                  lodMin: event.target.value,
                }))
              }
            />
          </div>
          <div className="sogs-stream-field">
            <label htmlFor="sogs-lod-max-input">LOD max</label>
            <input
              id="sogs-lod-max-input"
              type="number"
              min={0}
              step={1}
              placeholder="auto"
              value={streamingConfig.lodMax}
              onChange={(event) =>
                setStreamingConfig((current) => ({
                  ...current,
                  lodMax: event.target.value,
                }))
              }
            />
          </div>
        </div>

        <div className="sogs-toolbar-row">
          <div className="sogs-dropdown-wrap" ref={dropdownRef}>
            <button
              type="button"
              className="sogs-btn-secondary sogs-dropdown-trigger"
              aria-expanded={devOpen}
              aria-haspopup="dialog"
              aria-controls="sogs-scene-panel"
              onClick={() => setDevOpen((open) => !open)}
            >
              Scene & lens
              <span className={`sogs-dropdown-chevron${devOpen ? " sogs-open" : ""}`} aria-hidden>
                ▼
              </span>
            </button>
            {devOpen ? (
              <div
                id="sogs-scene-panel"
                className="sogs-dropdown-panel"
                role="dialog"
                aria-labelledby="sogs-dev-title"
                onClick={(event) => event.stopPropagation()}
              >
                <div className="sogs-dev-header">
                  <div id="sogs-dev-title" className="sogs-dev-title">
                    Scene
                  </div>
                  <button
                    type="button"
                    className="sogs-dev-close"
                    aria-label="Close scene panel"
                    onClick={() => setDevOpen(false)}
                  >
                    ×
                  </button>
                </div>

                <div className="sogs-dev-section">
                  <div className="sogs-dev-section-label">Transform</div>
                  <div className="sogs-dev-grid sogs-dev-grid-3">
                    {(["x", "y", "z"] as const).map((axis, index) => (
                      <div className="sogs-dev-field" key={`pos-${axis}`}>
                        <label htmlFor={`pos-${axis}`}>Pos {axis.toUpperCase()}</label>
                        <input
                          id={`pos-${axis}`}
                          type="number"
                          step="0.001"
                          value={form.position[index]}
                          onChange={(event) => {
                            const value = Number.parseFloat(event.target.value);
                            setForm((current) => {
                              const next = [...current.position] as [number, number, number];
                              next[index] = Number.isFinite(value) ? value : 0;
                              return { ...current, position: next };
                            });
                          }}
                        />
                      </div>
                    ))}
                  </div>

                  <div className="sogs-dev-grid sogs-dev-grid-3">
                    {(["x", "y", "z"] as const).map((axis, index) => (
                      <div className="sogs-dev-field" key={`rot-${axis}`}>
                        <label htmlFor={`rot-${axis}`}>Rot {axis.toUpperCase()}</label>
                        <input
                          id={`rot-${axis}`}
                          type="number"
                          step="0.1"
                          value={form.rotation[index]}
                          onChange={(event) => {
                            const value = Number.parseFloat(event.target.value);
                            setForm((current) => {
                              const next = [...current.rotation] as [number, number, number];
                              next[index] = Number.isFinite(value) ? value : 0;
                              return { ...current, rotation: next };
                            });
                          }}
                        />
                      </div>
                    ))}
                  </div>

                  <div className="sogs-dev-grid sogs-dev-grid-2">
                    <div className="sogs-dev-field">
                      <label htmlFor="splat-scale">Scale</label>
                      <input
                        id="splat-scale"
                        type="number"
                        step="0.001"
                        min={0.0001}
                        value={form.scale}
                        onChange={(event) => {
                          const value = Number.parseFloat(event.target.value);
                          setForm((current) => ({ ...current, scale: Number.isFinite(value) ? value : 1 }));
                        }}
                      />
                    </div>
                    <div className="sogs-dev-field">
                      <label htmlFor="cam-fov">FOV°</label>
                      <input
                        id="cam-fov"
                        type="number"
                        step="0.5"
                        min={10}
                        max={120}
                        value={form.fov}
                        onChange={(event) => {
                          const value = Number.parseFloat(event.target.value);
                          setForm((current) => ({ ...current, fov: Number.isFinite(value) ? value : 60 }));
                        }}
                      />
                    </div>
                  </div>
                </div>

                <label className="sogs-dev-toggle-row">
                  <input type="checkbox" checked={guides} onChange={(event) => setGuides(event.target.checked)} />
                  RGB axes (world, at splat origin)
                </label>

                <div className="sogs-dev-actions">
                  <button type="button" className="sogs-btn-ghost" onClick={copySceneJson}>
                    Copy JSON
                  </button>
                  <button type="button" className="sogs-btn-ghost" onClick={copyShareLink}>
                    Copy link
                  </button>
                  {copyFeedback ? (
                    <div className="sogs-copy-row">
                      <span className="sogs-copy-feedback">{copyFeedback}</span>
                    </div>
                  ) : null}
                </div>
                <details className="sogs-dev-details">
                  <summary>Notes</summary>
                  <p className="sogs-dev-details-body">
                    The loader probes <code className="sogs-dev-code">lod-meta.json</code> before{" "}
                    <code className="sogs-dev-code">meta.json</code> when you paste a folder URL. Rotation fields stay
                    as you type them; the engine can represent the same pose with different Euler triples, so the form
                    is not overwritten from the iframe. The streaming controls apply the viewer&apos;s{" "}
                    <code className="sogs-dev-code">splatBudget</code> and LOD range live.
                  </p>
                </details>
              </div>
            ) : null}
          </div>
        </div>

        <div className="sogs-status-card">
          <p className="sogs-hint">{statusText}</p>
          {resolvedBundle ? (
            <div className="sogs-status-grid">
              <div>
                <span className="sogs-status-label">Transport</span>
                <strong>{resolvedBundle.summary.transport}</strong>
              </div>
              <div>
                <span className="sogs-status-label">Manifest</span>
                <strong>{resolvedBundle.summary.rootFile}</strong>
              </div>
              <div>
                <span className="sogs-status-label">Budget</span>
                <strong>{formatInteger(telemetry.splatBudget ?? parsedStreaming.splatBudget)}</strong>
              </div>
              <div>
                <span className="sogs-status-label">Loaded nodes</span>
                <strong>
                  {resolvedBundle.bundleKind === "lod-streaming"
                    ? `${formatInteger(telemetry.loadedNodeCount)}/${formatInteger(totalNodes)}`
                    : "n/a"}
                </strong>
              </div>
              <div>
                <span className="sogs-status-label">First frame</span>
                <strong>{formatDurationMs(telemetry.firstFrameMs)}</strong>
              </div>
              <div>
                <span className="sogs-status-label">Chunk requests</span>
                <strong>{formatInteger(telemetry.chunkMetaRequestCount)}</strong>
              </div>
            </div>
          ) : null}
          {resolvedBundle?.summary.sourceUrl ? (
            <p className="sogs-source-url">{resolvedBundle.summary.sourceUrl}</p>
          ) : null}
        </div>

        <div
          data-testid="sogs-bundle-metrics"
          className="sogs-hidden-metrics"
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
          data-splat-budget={telemetry.splatBudget ?? parsedStreaming.splatBudget ?? ""}
          data-lod-min={telemetry.lodRangeMin ?? parsedStreaming.lodRangeMin ?? ""}
          data-lod-max={telemetry.lodRangeMax ?? parsedStreaming.lodRangeMax ?? ""}
          data-bounds-min={resolvedBundle?.summary.bounds ? resolvedBundle.summary.bounds.min.join(",") : ""}
          data-bounds-max={resolvedBundle?.summary.bounds ? resolvedBundle.summary.bounds.max.join(",") : ""}
        />

        {error ? <p className="sogs-error">{error}</p> : null}
      </form>
    </main>
  );
}
