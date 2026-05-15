"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  MD1_STREAMING_CONFIG,
  MD1_V18_COMPRESSION,
  MD1_V18_COMPUTE,
  MD1_V18_LINEAGE,
  MD1_V18_PRODUCTION_LOD_URL,
  MD1_V18_PRODUCTION_MANIFEST_URL,
  MD1_V18_PROMOTED_ARTIFACT_URI,
  MD1_V18_RAW_PLY_URL,
  MD1_V18_SAMPLED_INSPECTION_URL,
  MD1_V18_SFM_URL,
  buildMd1ViewerConfigPayload,
  isProbablyMobileViewport,
  withMd1ViewerOverrides,
} from "../../lib/md1ProductionViewer";
import {
  normalizeBundleUrl,
  resolveSogsViewerBundle,
  type ResolvedSogsViewerBundle,
} from "../../lib/sogsViewerBundle";
import "./md1-viewer.css";

const VIEWER_BASE = "/supersplat-lod-viewer/index.html";

type Tab = "splat" | "sfm" | "evidence";

type ViewerTelemetry = {
  loadedNodeCount: number;
  chunkMetaRequestCount: number;
  chunkMetaAtFirstFrame: number | null;
  totalRequestCount: number;
  firstFrameMs: number | null;
  splatBudget: number | null;
  lodRangeMin: number | null;
  lodRangeMax: number | null;
  lodDistances: number[] | null;
  rootManifestType: string | null;
  rootManifestUrl: string | null;
};

type StreamingOverrides = {
  splatBudget?: number | null;
  lodRangeMin?: number | null;
  lodRangeMax?: number | null;
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
    lodDistances?: number[] | null;
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
  lodDistances: null,
  rootManifestType: null,
  rootManifestUrl: null,
};

function compactNumber(value: number | null | undefined, digits = 0) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "n/a";
  }
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(value);
}

function secondsFromMs(value: number | null) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "pending";
  }
  return `${(value / 1000).toFixed(1)}s`;
}

function readNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function readNumberList(value: unknown): number[] | null {
  if (!Array.isArray(value) || value.length === 0) {
    return null;
  }
  const parsed = value.map((entry) => Number(entry));
  return parsed.every(Number.isFinite) ? parsed : null;
}

function readIntegerParam(params: URLSearchParams, key: string): number | null {
  const raw = params.get(key);
  if (!raw) {
    return null;
  }
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function readSkyboxOverride(params: URLSearchParams): string | null | undefined {
  const raw = params.get("skybox");
  if (raw == null) {
    return undefined;
  }
  const trimmed = raw.trim();
  if (!trimmed) {
    return undefined;
  }
  if (["0", "off", "none", "null"].includes(trimmed.toLowerCase())) {
    return null;
  }
  return trimmed;
}

export default function Md1ProductionViewer() {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [tab, setTab] = useState<Tab>("splat");
  const [manifestUrl, setManifestUrl] = useState(MD1_V18_PRODUCTION_LOD_URL);
  const [activeManifestUrl, setActiveManifestUrl] = useState(MD1_V18_PRODUCTION_LOD_URL);
  const [iframeKey, setIframeKey] = useState(0);
  const [viewerState, setViewerState] = useState<"loading" | "ready">("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [resolvedBundle, setResolvedBundle] = useState<ResolvedSogsViewerBundle | null>(null);
  const [streamingOverrides, setStreamingOverrides] = useState<StreamingOverrides>({});
  const [explicitSkybox, setExplicitSkybox] = useState<string | null | undefined>(undefined);
  const [telemetry, setTelemetry] = useState<ViewerTelemetry>(EMPTY_TELEMETRY);
  const [isMobileViewport, setIsMobileViewport] = useState(false);

  const fallbackContentUrl = useMemo(
    () => normalizeBundleUrl(activeManifestUrl) ?? activeManifestUrl,
    [activeManifestUrl],
  );
  const resolvedContentUrl = resolvedBundle?.contentUrl ?? fallbackContentUrl;
  const activeContentUrl = resolvedContentUrl;

  const viewerSrc = useMemo(() => {
    const configPayload = withMd1ViewerOverrides(
      buildMd1ViewerConfigPayload(MD1_STREAMING_CONFIG, isMobileViewport),
      streamingOverrides,
    );
    const params = new URLSearchParams({
      settings: "/supersplat-lod-viewer/settings.json",
      content: activeContentUrl,
      noanim: "1",
      noui: "1",
    });
    params.set("quality", isMobileViewport ? "lq" : "hq");
    if (resolvedBundle?.skyboxUrl?.trim()) {
      params.set("skybox", resolvedBundle.skyboxUrl.trim());
    }
    if (configPayload.splatBudget != null) {
      params.set("budget", String(configPayload.splatBudget));
    }
    if (configPayload.lodRangeMin != null) {
      params.set("lodMin", String(configPayload.lodRangeMin));
    }
    if (configPayload.lodRangeMax != null) {
      params.set("lodMax", String(configPayload.lodRangeMax));
    }
    if (Array.isArray(configPayload.lodDistances)) {
      params.set("lodDistances", configPayload.lodDistances.join(","));
    }
    params.set("lodUnderfillLimit", String(configPayload.lodUnderfillLimit));
    params.set("lodUpdateDistance", String(configPayload.lodUpdateDistance));
    params.set("lodUpdateAngle", String(configPayload.lodUpdateAngle));
    params.set("colorUpdateDistance", String(configPayload.colorUpdateDistance));
    params.set("colorUpdateAngle", String(configPayload.colorUpdateAngle));
    params.set("colorUpdateDistanceLodScale", String(configPayload.colorUpdateDistanceLodScale));
    params.set("colorUpdateAngleLodScale", String(configPayload.colorUpdateAngleLodScale));
    return `${VIEWER_BASE}?${params.toString()}`;
  }, [activeContentUrl, isMobileViewport, resolvedBundle, streamingOverrides]);

  const sfmSrc = useMemo(() => {
    const params = new URLSearchParams({ url: MD1_V18_SFM_URL });
    return `/sfm-output-viewer?${params.toString()}`;
  }, []);

  const postToViewer = useCallback((payload: object) => {
    try {
      iframeRef.current?.contentWindow?.postMessage(payload, "*");
    } catch {
      /* ignore */
    }
  }, []);

  const loadManifest = useCallback((rawUrl: string) => {
    const value = rawUrl.trim();
    if (!value) {
      return;
    }
    setViewerState("loading");
    setLoadError(null);
    setResolvedBundle(null);
    setTelemetry(EMPTY_TELEMETRY);
    setActiveManifestUrl(value);
    setIframeKey((key) => key + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoadError(null);
    setResolvedBundle(null);
    void resolveSogsViewerBundle(activeManifestUrl, explicitSkybox).then((bundle) => {
      if (cancelled) {
        return;
      }
      if (!bundle) {
        setLoadError("LOD manifest is not reachable yet.");
        return;
      }
      setResolvedBundle(bundle);
    });
    return () => {
      cancelled = true;
    };
  }, [activeManifestUrl, explicitSkybox]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const override = params.get("url")?.trim();
    setIsMobileViewport(isProbablyMobileViewport());
    setStreamingOverrides({
      splatBudget: readIntegerParam(params, "budget"),
      lodRangeMin: readIntegerParam(params, "lodMin"),
      lodRangeMax: readIntegerParam(params, "lodMax"),
    });
    setExplicitSkybox(readSkyboxOverride(params));
    if (override) {
      setManifestUrl(override);
      loadManifest(override);
    }
  }, [loadManifest]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      postToViewer({ type: "sogs:requestState" });
    }, 1500);
    return () => window.clearInterval(interval);
  }, [postToViewer, iframeKey]);

  const readIframeTelemetry = useCallback(() => {
    const viewerWindow = iframeRef.current?.contentWindow as ViewerWindow | null | undefined;
    const network = viewerWindow?.__sogsNetworkMetrics;
    if (!network) {
      return;
    }
    const config = viewerWindow?.__sogsInitialViewerConfig;
    const firstFrameAt = readNumber(network.firstFrame?.at);
    const loadStartedAt = readNumber(network.loadStartedAt);
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
        readNumber(network.firstFrame?.chunkMetaRequestCount) ?? current.chunkMetaAtFirstFrame,
      totalRequestCount: Math.max(
        current.totalRequestCount,
        Array.isArray(network.events) ? network.events.length : 0,
      ),
      firstFrameMs: firstFrameMs ?? current.firstFrameMs,
      splatBudget: readNumber(config?.splatBudget) ?? current.splatBudget,
      lodRangeMin: readNumber(config?.lodRangeMin) ?? current.lodRangeMin,
      lodRangeMax: readNumber(config?.lodRangeMax) ?? current.lodRangeMax,
      lodDistances: readNumberList(config?.lodDistances) ?? current.lodDistances,
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

  useEffect(() => {
    readIframeTelemetry();
    const interval = window.setInterval(readIframeTelemetry, 1000);
    return () => window.clearInterval(interval);
  }, [iframeKey, readIframeTelemetry]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.source !== iframeRef.current?.contentWindow) {
        return;
      }
      if (event.data?.type === "supersplat:firstFrame") {
        setViewerState("ready");
        postToViewer(
          withMd1ViewerOverrides(
            buildMd1ViewerConfigPayload(MD1_STREAMING_CONFIG, isMobileViewport),
            streamingOverrides,
          ),
        );
        postToViewer({ type: "sogs:requestState" });
      }
      if (event.data?.type === "sogs:state") {
        const data = event.data as Record<string, unknown>;
        const nextTelemetry: ViewerTelemetry = {
          loadedNodeCount: readNumber(data.loadedNodeCount) ?? 0,
          chunkMetaRequestCount: readNumber(data.chunkMetaRequestCount) ?? 0,
          chunkMetaAtFirstFrame: readNumber(data.chunkMetaAtFirstFrame),
          totalRequestCount: readNumber(data.totalRequestCount) ?? 0,
          firstFrameMs: readNumber(data.firstFrameMs),
          splatBudget: readNumber(data.splatBudget),
          lodRangeMin: readNumber(data.lodRangeMin),
          lodRangeMax: readNumber(data.lodRangeMax),
          lodDistances: readNumberList(data.lodDistances),
          rootManifestType: typeof data.rootManifestType === "string" ? data.rootManifestType : null,
          rootManifestUrl: typeof data.rootManifestUrl === "string" ? data.rootManifestUrl : null,
        };
        setTelemetry((current) => ({
          loadedNodeCount: Math.max(current.loadedNodeCount, nextTelemetry.loadedNodeCount),
          chunkMetaRequestCount: Math.max(
            current.chunkMetaRequestCount,
            nextTelemetry.chunkMetaRequestCount,
          ),
          chunkMetaAtFirstFrame: nextTelemetry.chunkMetaAtFirstFrame ?? current.chunkMetaAtFirstFrame,
          totalRequestCount: Math.max(current.totalRequestCount, nextTelemetry.totalRequestCount),
          firstFrameMs: nextTelemetry.firstFrameMs ?? current.firstFrameMs,
          splatBudget: nextTelemetry.splatBudget ?? current.splatBudget,
          lodRangeMin: nextTelemetry.lodRangeMin ?? current.lodRangeMin,
          lodRangeMax: nextTelemetry.lodRangeMax ?? current.lodRangeMax,
          lodDistances: nextTelemetry.lodDistances ?? current.lodDistances,
          rootManifestType: nextTelemetry.rootManifestType ?? current.rootManifestType,
          rootManifestUrl: nextTelemetry.rootManifestUrl ?? current.rootManifestUrl,
        }));
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [isMobileViewport, postToViewer, streamingOverrides]);

  const isMd1ProductionManifest =
    activeManifestUrl === MD1_V18_PRODUCTION_LOD_URL ||
    activeManifestUrl.includes("/md1-r5-v18-splattransform-lod-nosingle-public-1777575472/") ||
    activeManifestUrl.includes("/md1-r5-v18-production-lod-1777560644/lod-meta.json");
  const isLodManifest = activeManifestUrl.includes("/lod-meta.json");
  const bundleSummary = resolvedBundle?.summary;
  const effectiveBundleKind = bundleSummary?.bundleKind ?? (isLodManifest ? "lod-streaming" : "");
  const effectiveRootFile =
    bundleSummary?.rootFile ?? telemetry.rootManifestType ?? (isLodManifest ? "lod-meta.json" : "");
  const effectiveLodLevels = bundleSummary?.lodLevels ?? (isMd1ProductionManifest ? MD1_V18_COMPRESSION.lodLevels : null);
  const effectiveChunkFiles =
    bundleSummary?.chunkFiles ?? (isMd1ProductionManifest ? MD1_V18_COMPRESSION.chunkFiles : null);
  const totalChunks = effectiveChunkFiles ?? null;

  return (
    <main className="md1-shell">
      <div className="md1-stage" data-tab={tab}>
        {tab === "splat" ? (
          <iframe
            key={iframeKey}
            ref={iframeRef}
            src={viewerSrc}
            title="MD1 production Gaussian splat"
            className="md1-frame"
            allow="xr-spatial-tracking"
          />
        ) : null}
        {tab === "sfm" ? <iframe src={sfmSrc} title="MD1 SfM input" className="md1-frame" /> : null}
        {tab === "evidence" ? (
          <section className="md1-evidence" aria-label="MD1 V18 evidence">
            <h1>MD1 V18 Production Evidence</h1>
            <dl>
              <div>
                <dt>Source artifact</dt>
                <dd>{MD1_V18_PROMOTED_ARTIFACT_URI}</dd>
              </div>
              <div>
                <dt>Full retained gaussians</dt>
                <dd>{compactNumber(MD1_V18_LINEAGE.promotedGaussianCount)}</dd>
              </div>
              <div>
                <dt>LOD manifest</dt>
                <dd>{bundleSummary?.sourceUrl ?? activeManifestUrl}</dd>
              </div>
              <div>
                <dt>Production manifest</dt>
                <dd>{MD1_V18_PRODUCTION_MANIFEST_URL}</dd>
              </div>
              <div>
                <dt>Compression path</dt>
                <dd>
                  {MD1_V18_COMPRESSION.compressor} {MD1_V18_COMPRESSION.compressorVersion},{" "}
                  {MD1_V18_COMPRESSION.mode}, {compactNumber(MD1_V18_COMPRESSION.chunkFiles)} chunks.
                </dd>
              </div>
              <div>
                <dt>SfM diagnostic JSON</dt>
                <dd>{MD1_V18_SFM_URL}</dd>
              </div>
              <div>
                <dt>Raw full PLY</dt>
                <dd>{MD1_V18_RAW_PLY_URL}</dd>
              </div>
              <div>
                <dt>Training compute</dt>
                <dd>
                  {MD1_V18_COMPUTE.jobName}, {MD1_V18_COMPUTE.billableHours}h on{" "}
                  {MD1_V18_COMPUTE.instanceType}, about ${MD1_V18_COMPUTE.estimatedUsd.toFixed(2)}.
                </dd>
              </div>
            </dl>
          </section>
        ) : null}
      </div>

      <aside className="md1-panel" aria-label="MD1 viewer controls">
        <div className="md1-title-row">
          <div>
            <h1>MD1 V18</h1>
            <p>{isMd1ProductionManifest ? "Production LOD" : isLodManifest ? "Custom LOD" : "Inspection asset"}</p>
          </div>
          <span className={viewerState === "ready" ? "md1-pill md1-pill-ready" : "md1-pill"}>
            {viewerState === "ready" ? "Ready" : "Loading"}
          </span>
        </div>

        <div className="md1-tabs" role="tablist" aria-label="MD1 viewer tabs">
          <button type="button" className={tab === "splat" ? "active" : ""} onClick={() => setTab("splat")}>
            3DGS
          </button>
          <button type="button" className={tab === "sfm" ? "active" : ""} onClick={() => setTab("sfm")}>
            SfM
          </button>
          <button type="button" className={tab === "evidence" ? "active" : ""} onClick={() => setTab("evidence")}>
            Evidence
          </button>
        </div>

        <form
          className="md1-url"
          onSubmit={(event) => {
            event.preventDefault();
            loadManifest(manifestUrl);
          }}
        >
          <label htmlFor="md1-manifest-url">LOD manifest</label>
          <div>
            <input
              id="md1-manifest-url"
              type="url"
              value={manifestUrl}
              onChange={(event) => setManifestUrl(event.target.value)}
            />
            <button type="submit">Load</button>
          </div>
        </form>

        <div className="md1-grid">
          <div>
            <span>Chunks</span>
            <strong>
              {compactNumber(telemetry.chunkMetaRequestCount)}
              {totalChunks ? `/${compactNumber(totalChunks)}` : ""}
            </strong>
          </div>
          <div>
            <span>First frame</span>
            <strong>{secondsFromMs(telemetry.firstFrameMs)}</strong>
          </div>
          <div>
            <span>LOD range</span>
            <strong>
              {telemetry.lodRangeMin ??
                (isMobileViewport ? MD1_STREAMING_CONFIG.lodRangeMinMobile : MD1_STREAMING_CONFIG.lodRangeMinDesktop)}
              -
              {telemetry.lodRangeMax ?? MD1_STREAMING_CONFIG.lodRangeMaxDesktop}
            </strong>
          </div>
          <div>
            <span>Full source</span>
            <strong>{compactNumber(MD1_V18_LINEAGE.promotedGaussianCount)}</strong>
          </div>
          <div>
            <span>Manifest</span>
            <strong>{effectiveRootFile || "pending"}</strong>
          </div>
          <div>
            <span>Engine</span>
            <strong>{effectiveBundleKind === "lod-streaming" || isLodManifest ? "SOGS LOD" : "SOGS"}</strong>
          </div>
        </div>

        {loadError ? <p className="md1-error">{loadError}</p> : null}

        <p className="md1-note">
          This route defaults to the true V18 LOD manifest. The every-8th PLY remains only as an inspection fallback:
          <br />
          <a href={MD1_V18_SAMPLED_INSPECTION_URL}>sampled PLY</a>
        </p>

        <div
          data-testid="md1-bundle-metrics"
          className="md1-hidden-metrics"
          data-bundle-kind={effectiveBundleKind}
          data-transport={bundleSummary?.transport ?? ""}
          data-root-file={effectiveRootFile}
          data-source-url={bundleSummary?.sourceUrl ?? activeManifestUrl}
          data-viewer-url={activeContentUrl}
          data-lod-levels={effectiveLodLevels ?? ""}
          data-chunk-files={effectiveChunkFiles ?? ""}
          data-loaded-nodes={telemetry.loadedNodeCount}
          data-chunk-meta-requests={telemetry.chunkMetaRequestCount}
          data-chunk-meta-at-first-frame={telemetry.chunkMetaAtFirstFrame ?? ""}
          data-first-frame-ms={telemetry.firstFrameMs ?? ""}
          data-splat-budget={telemetry.splatBudget ?? ""}
          data-lod-min={telemetry.lodRangeMin ?? ""}
          data-lod-max={telemetry.lodRangeMax ?? ""}
          data-bounds-min={bundleSummary?.bounds ? bundleSummary.bounds.min.join(",") : ""}
          data-bounds-max={bundleSummary?.bounds ? bundleSummary.bounds.max.join(",") : ""}
        />
      </aside>
    </main>
  );
}
