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

const VIEWER_BASE = "/supersplat-lod-viewer/index.html";
const VIEWER_SETTINGS = "/supersplat-lod-viewer/settings.json";
const REQUEST_STATE_INTERVAL_MS = 1500;

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

type SogsViewerDevPanelProps = {
  defaultBundleUrl?: string;
};

type ViewerWindow = Window & {
  __sogsNetworkMetrics?: {
    rootManifestType?: string | null;
    rootManifestUrl?: string | null;
    loadStartedAt?: number | null;
    firstFrame?: { at?: number | null; chunkMetaRequestCount?: number | null } | null;
    events?: unknown[];
    uniqueChunkMetaUrls?: string[];
  };
  __sogsInitialViewerConfig?: {
    splatBudget?: number | null;
    lodRangeMin?: number | null;
    lodRangeMax?: number | null;
  };
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

function readFiniteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatInteger(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString() : "auto";
}

function formatDurationMs(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? `${(value / 1000).toFixed(1)}s` : "-";
}

function getDefaultBudget(): number {
  if (typeof window === "undefined") {
    return 3_000_000;
  }
  const ua = window.navigator.userAgent.toLowerCase();
  return /iphone|ipad|android|mobile|touch/.test(ua) || window.innerWidth <= 768 ? 1_000_000 : 3_000_000;
}

function parseOptionalInteger(value: string): number | null {
  const parsed = Number.parseInt(value.trim(), 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseStreamingConfig(config: StreamingConfig) {
  return {
    splatBudget: parseOptionalInteger(config.budget),
    lodRangeMin: parseOptionalInteger(config.lodMin),
    lodRangeMax: parseOptionalInteger(config.lodMax),
  };
}

export default function SogsViewerDevPanel({
  defaultBundleUrl = DEFAULT_SOGS_BUNDLE_URL,
}: SogsViewerDevPanelProps = {}) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  /** Skip first sogs:state after each iframe load — it reflects viewer defaults before SOGS_DEFAULT_SCENE is applied. */
  const ignoreNextSogsStateRef = useRef(false);

  const [inputUrl, setInputUrl] = useState(defaultBundleUrl);
  const [loadedInputUrl, setLoadedInputUrl] = useState(defaultBundleUrl);
  const [activeUrl, setActiveUrl] = useState("");
  const [resolvedBundle, setResolvedBundle] = useState<ResolvedSogsViewerBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [iframeKey, setIframeKey] = useState(0);
  const [viewerState, setViewerState] = useState<"idle" | "loading" | "ready">("idle");
  const [telemetry, setTelemetry] = useState<ViewerTelemetry>(EMPTY_TELEMETRY);

  const [devOpen, setDevOpen] = useState(false);
  const [guides, setGuides] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const [streamingConfig, setStreamingConfig] = useState<StreamingConfig>({
    budget: "",
    lodMin: "0",
    lodMax: "3",
  });

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

  const readIframeTelemetry = useCallback(() => {
    const viewerWindow = iframeRef.current?.contentWindow as ViewerWindow | null | undefined;
    const network = viewerWindow?.__sogsNetworkMetrics;
    if (!network) {
      return;
    }

    const config = viewerWindow?.__sogsInitialViewerConfig;
    const firstFrameAt = readFiniteNumber(network.firstFrame?.at);
    const loadStartedAt = readFiniteNumber(network.loadStartedAt);
    const firstFrameMs =
      firstFrameAt != null && loadStartedAt != null ? firstFrameAt - loadStartedAt : null;

    if (firstFrameMs != null) {
      setViewerState("ready");
    }

    setTelemetry((current) => ({
      loadedNodeCount: current.loadedNodeCount,
      chunkMetaRequestCount: Math.max(
        current.chunkMetaRequestCount,
        Array.isArray(network.uniqueChunkMetaUrls) ? network.uniqueChunkMetaUrls.length : 0,
      ),
      chunkMetaAtFirstFrame:
        readFiniteNumber(network.firstFrame?.chunkMetaRequestCount) ?? current.chunkMetaAtFirstFrame,
      totalRequestCount: Math.max(
        current.totalRequestCount,
        Array.isArray(network.events) ? network.events.length : 0,
      ),
      firstFrameMs: firstFrameMs ?? current.firstFrameMs,
      splatBudget: readFiniteNumber(config?.splatBudget) ?? current.splatBudget,
      lodRangeMin: readFiniteNumber(config?.lodRangeMin) ?? current.lodRangeMin,
      lodRangeMax: readFiniteNumber(config?.lodRangeMax) ?? current.lodRangeMax,
      rootManifestType:
        typeof network.rootManifestType === "string"
          ? network.rootManifestType
          : current.rootManifestType,
      rootManifestUrl:
        typeof network.rootManifestUrl === "string"
          ? network.rootManifestUrl
          : current.rootManifestUrl,
    }));
  }, []);

  const attemptLoad = useCallback(async (rawValue: string) => {
    setError(null);
    const normalized = normalizeBundleUrl(rawValue);
    if (!normalized) {
      setError("Enter a valid HTTPS URL to the SOGS bundle, meta.json, .sog, or raw .ply file.");
      setViewerState("idle");
      return false;
    }

    setViewerState("loading");
    setTelemetry(EMPTY_TELEMETRY);
    const resolved = await resolveSogsViewerBundle(rawValue);
    if (!resolved) {
      setError("Could not fetch a valid SOGS bundle, LOD manifest, .sog, or raw .ply file.");
      setViewerState("idle");
      return false;
    }
    setResolvedBundle(resolved);
    setLoadedInputUrl(rawValue.trim());
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
      settings: VIEWER_SETTINGS,
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
      if (event.data?.type === "supersplat:firstFrame" && event.source === iframeRef.current?.contentWindow) {
        const d = createDefaultScenePayload();
        if (resolvedBundle?.summary?.bundleKind !== "lod-streaming") {
          try {
            (event.source as Window).postMessage(
              {
                type: "sogs:apply",
                position: d.position,
                rotation: d.rotation,
                scale: d.scale,
                fov: d.fov,
              },
              "*",
            );
          } catch {
            /* ignore */
          }
        }
        setForm(d);
        setViewerState("ready");
        applyStreamingConfigToIframe();
        postToIframe({ type: "sogs:requestState" });
      }
      if (event.data?.type === "sogs:state" && event.source === iframeRef.current?.contentWindow) {
        if (ignoreNextSogsStateRef.current) {
          ignoreNextSogsStateRef.current = false;
          return;
        }
        const d = event.data as Record<string, unknown> & { position?: number[] };
        if (Array.isArray(d.position) && d.position.length === 3) {
          setForm((f) => ({
            ...f,
            position: [d.position[0], d.position[1], d.position[2]] as [number, number, number],
          }));
        }
        setTelemetry({
          loadedNodeCount: typeof d.loadedNodeCount === "number" ? d.loadedNodeCount : 0,
          chunkMetaRequestCount: typeof d.chunkMetaRequestCount === "number" ? d.chunkMetaRequestCount : 0,
          chunkMetaAtFirstFrame: typeof d.chunkMetaAtFirstFrame === "number" ? d.chunkMetaAtFirstFrame : null,
          totalRequestCount: typeof d.totalRequestCount === "number" ? d.totalRequestCount : 0,
          firstFrameMs: typeof d.firstFrameMs === "number" ? d.firstFrameMs : null,
          splatBudget: typeof d.splatBudget === "number" ? d.splatBudget : null,
          lodRangeMin: typeof d.lodRangeMin === "number" ? d.lodRangeMin : null,
          lodRangeMax: typeof d.lodRangeMax === "number" ? d.lodRangeMax : null,
          rootManifestType: typeof d.rootManifestType === "string" ? d.rootManifestType : null,
          rootManifestUrl: typeof d.rootManifestUrl === "string" ? d.rootManifestUrl : null,
        });
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [applyStreamingConfigToIframe, postToIframe, resolvedBundle]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const q = params.get("url");
    const raw = q?.trim() ? q.trim() : defaultBundleUrl;
    const budget = String(parseOptionalInteger(params.get("budget") ?? "") ?? getDefaultBudget());
    const lodMin = params.get("lodMin")?.trim() || "0";
    const lodMax = params.get("lodMax")?.trim() || "3";
    setInputUrl(raw);
    setLoadedInputUrl(raw);
    setStreamingConfig({ budget, lodMin, lodMax });
    void attemptLoad(raw);
  }, [attemptLoad, defaultBundleUrl]);

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
    readIframeTelemetry();
    const interval = window.setInterval(readIframeTelemetry, 1000);
    return () => window.clearInterval(interval);
  }, [activeUrl, iframeKey, readIframeTelemetry]);

  useEffect(() => {
    if (!activeUrl || viewerState !== "ready") {
      return;
    }
    const interval = window.setInterval(() => postToIframe({ type: "sogs:requestState" }), REQUEST_STATE_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [activeUrl, postToIframe, viewerState]);

  useEffect(() => {
    if (typeof window === "undefined" || !activeUrl || !loadedInputUrl.trim()) {
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
  }, [activeUrl, loadedInputUrl, streamingConfig]);

  useEffect(() => {
    if (!activeUrl) {
      return;
    }
    postToIframe({ type: "sogs:guides", enabled: guides });
  }, [guides, postToIframe, activeUrl, iframeKey]);

  /** Push splat/camera to iframe whenever values change (panel open + viewer ready). */
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
    const onDoc = (e: MouseEvent) => {
      const el = dropdownRef.current;
      if (!el) {
        return;
      }
      if (e.target instanceof Node && !el.contains(e.target)) {
        setDevOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
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
      bundleUrl: resolvedBundle?.summary?.sourceUrl || activeUrl || inputUrl.trim() || "",
      scene: form,
      guides,
    });
    const text = JSON.stringify(payload, null, 2);
    try {
      await navigator.clipboard.writeText(text);
      setCopyFeedback("Copied");
    } catch {
      setCopyFeedback("Copy failed — try a secure context (HTTPS).");
    }
    window.setTimeout(() => setCopyFeedback(null), 2200);
  };

  const isSubmitDisabled = !inputUrl.trim();
  const summary = resolvedBundle?.summary;
  const parsedStreaming = parseStreamingConfig(streamingConfig);
  const statusText =
    viewerState === "ready" && summary
      ? summary.bundleKind === "lod-streaming"
        ? `Ready - Streaming LOD · ${formatInteger(summary.lodLevels)} levels · ${formatInteger(summary.chunkFiles)} chunks`
        : summary.bundleKind === "asset"
          ? "Ready - Inspection asset"
          : `Ready - Single SOG · ${formatInteger(summary.splatCount)} splats`
      : viewerState === "loading" && activeUrl
        ? "Loading bundle..."
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
        <label htmlFor="sogs-url-input">S3 bundle URL</label>
        <div className="sogs-url-row">
          <input
            id="sogs-url-input"
            type="url"
            inputMode="url"
            autoComplete="off"
            placeholder="https://…/supersplat_bundle/, …/meta.json, …/model.sog, or …/merged_splat.ply"
            value={inputUrl}
            onChange={(e) => setInputUrl(e.target.value)}
            className={error ? "sogs-input-error" : undefined}
          />
          <button type="submit" className="sogs-btn-primary" disabled={isSubmitDisabled}>
            {viewerState === "loading" ? "…" : "Load"}
          </button>
        </div>
        <div className="sogs-toolbar-row">
          <div className="sogs-stream-row" aria-label="Streaming controls">
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
          <div className="sogs-dropdown-wrap" ref={dropdownRef}>
            <button
              type="button"
              className="sogs-btn-secondary sogs-dropdown-trigger"
              aria-expanded={devOpen}
              aria-haspopup="dialog"
              aria-controls="sogs-scene-panel"
              onClick={() => setDevOpen((o) => !o)}
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
                onClick={(e) => e.stopPropagation()}
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
                  <div className="sogs-dev-section-label">Position</div>
                  <div className="sogs-dev-grid sogs-dev-grid-3">
                    {(["x", "y", "z"] as const).map((axis, i) => (
                      <div key={`p-${axis}`} className="sogs-dev-field">
                        <label htmlFor={`pos-${axis}`}>{axis.toUpperCase()}</label>
                        <input
                          id={`pos-${axis}`}
                          type="number"
                          step="0.001"
                          value={form.position[i]}
                          onChange={(e) => {
                            const v = parseFloat(e.target.value);
                            const next = [...form.position] as [number, number, number];
                            next[i] = Number.isFinite(v) ? v : 0;
                            setForm((f) => ({ ...f, position: next }));
                          }}
                        />
                      </div>
                    ))}
                  </div>
                </div>

                <div className="sogs-dev-section">
                  <div className="sogs-dev-section-label">Rotation (°)</div>
                  <div className="sogs-dev-grid sogs-dev-grid-3">
                    {(["x", "y", "z"] as const).map((axis, i) => (
                      <div key={`r-${axis}`} className="sogs-dev-field">
                        <label htmlFor={`rot-${axis}`}>{axis.toUpperCase()}</label>
                        <input
                          id={`rot-${axis}`}
                          type="number"
                          step="0.1"
                          value={form.rotation[i]}
                          onChange={(e) => {
                            const v = parseFloat(e.target.value);
                            const next = [...form.rotation] as [number, number, number];
                            next[i] = Number.isFinite(v) ? v : 0;
                            setForm((f) => ({ ...f, rotation: next }));
                          }}
                        />
                      </div>
                    ))}
                  </div>
                </div>

                <div className="sogs-dev-grid sogs-dev-grid-2">
                  <div className="sogs-dev-field">
                    <label htmlFor="splat-scale">Scale</label>
                    <input
                      id="splat-scale"
                      type="number"
                      step="0.01"
                      min={0.01}
                      value={form.scale}
                      onChange={(e) => {
                        const v = parseFloat(e.target.value);
                        setForm((f) => ({ ...f, scale: Number.isFinite(v) ? Math.max(0.01, v) : 1 }));
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
                      onChange={(e) => {
                        const v = parseFloat(e.target.value);
                        setForm((f) => ({ ...f, fov: Number.isFinite(v) ? v : 60 }));
                      }}
                    />
                  </div>
                </div>

                <label className="sogs-dev-toggle-row">
                  <input type="checkbox" checked={guides} onChange={(e) => setGuides(e.target.checked)} />
                  RGB axes (world, at splat origin)
                </label>

                <div className="sogs-dev-actions">
                  <button type="button" className="sogs-btn-ghost" onClick={copySceneJson}>
                    Copy JSON
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
                    Rotation fields stay as you type them; the engine can represent the same pose with different Euler
                    triples, so we do not overwrite the inputs from the iframe. Defaults match{" "}
                    <code className="sogs-dev-code">SOGS_DEFAULT_SCENE</code>.                     FOV applies after the orbit camera
                    updates. On a touchscreen use two fingers; on a trackpad use a two-finger scroll (not
                    vertical-only, which zooms). Middle mouse on desktop. Position is synced from
                    the viewer. Paste copied JSON for maintainers to update{" "}
                    <code className="sogs-dev-code">web/lib/sogsViewerSceneDefaults.ts</code>.
                  </p>
                </details>
              </div>
            ) : null}
          </div>
        </div>
        <div className="sogs-status-card">
          <p className="sogs-hint">{error ?? statusText}</p>
          {summary ? (
            <div className="sogs-status-grid">
              <div>
                <span className="sogs-status-label">Transport</span>
                <strong>{summary.transport}</strong>
              </div>
              <div>
                <span className="sogs-status-label">Manifest</span>
                <strong>{summary.rootFile}</strong>
              </div>
              <div>
                <span className="sogs-status-label">Budget</span>
                <strong>{formatInteger(telemetry.splatBudget ?? parsedStreaming.splatBudget)}</strong>
              </div>
              <div>
                <span className="sogs-status-label">Loaded chunks</span>
                <strong>
                  {summary.bundleKind === "lod-streaming"
                    ? `${formatInteger(telemetry.loadedNodeCount)}/${formatInteger(summary.chunkFiles)}`
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
          {summary?.sourceUrl ? <p className="sogs-source-url">{summary.sourceUrl}</p> : null}
        </div>

        <div
          data-testid="sogs-bundle-metrics"
          className="sogs-hidden-metrics"
          data-bundle-kind={summary?.bundleKind ?? ""}
          data-transport={summary?.transport ?? ""}
          data-root-file={summary?.rootFile ?? telemetry.rootManifestType ?? ""}
          data-source-url={summary?.sourceUrl ?? inputUrl}
          data-lod-levels={summary?.lodLevels ?? ""}
          data-chunk-files={summary?.chunkFiles ?? ""}
          data-loaded-nodes={telemetry.loadedNodeCount}
          data-chunk-meta-requests={telemetry.chunkMetaRequestCount}
          data-chunk-meta-at-first-frame={telemetry.chunkMetaAtFirstFrame ?? ""}
          data-first-frame-ms={telemetry.firstFrameMs ?? ""}
          data-splat-budget={telemetry.splatBudget ?? parsedStreaming.splatBudget ?? ""}
          data-lod-min={telemetry.lodRangeMin ?? parsedStreaming.lodRangeMin ?? ""}
          data-lod-max={telemetry.lodRangeMax ?? parsedStreaming.lodRangeMax ?? ""}
          data-bounds-min={summary?.bounds ? summary.bounds.min.join(",") : ""}
          data-bounds-max={summary?.bounds ? summary.bounds.max.join(",") : ""}
        />
        {error ? <p className="sogs-error">{error}</p> : null}
      </form>
    </main>
  );
}
