"use client";

import { CSSProperties, FormEvent, useEffect, useMemo, useRef, useState } from "react";

const REMOTE_S3_BUNDLE =
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/sogs-test-1763664401/supersplat_bundle/meta.json";
const LOCAL_MIRROR_BUNDLE = "/test-sogs-1763664401/meta.json";
const DEFAULT_BUNDLE_URL = REMOTE_S3_BUNDLE;
const VIEWER_BASE = "/supersplat-viewer/index.html";
const ML_PIPELINE_API_URL = process.env.NEXT_PUBLIC_ML_PIPELINE_API_URL?.replace(/\/$/, "") || "";
const SPACEPORT_S3_HOST = /^spaceport-ml-processing(?:-[a-z0-9-]+)?\.s3(?:\.us-west-2)?\.amazonaws\.com$/i;
const SAMPLE_BUNDLES = [
  {
    label: "S3 proxy · sogs-test-1763664401",
    url: REMOTE_S3_BUNDLE,
  },
  {
    label: "Local mirror · sogs-test-1763664401",
    url: LOCAL_MIRROR_BUNDLE,
  },
];

const pillInputStyles: CSSProperties = {
  width: "100%",
  padding: "14px 20px",
  borderRadius: "999px",
  border: "1px solid rgba(255, 255, 255, 0.2)",
  background: "rgba(10, 10, 15, 0.35)",
  color: "#ffffff",
  fontSize: "0.95rem",
  outline: "none",
  transition: "border-color 0.2s ease, box-shadow 0.2s ease",
};

const buttonStyles: CSSProperties = {
  padding: "12px 26px",
  borderRadius: "999px",
  border: "1px solid rgba(255, 255, 255, 0.25)",
  background: "linear-gradient(90deg, #FF4F00, #FF8A00)",
  color: "#0b0b10",
  fontWeight: 600,
  fontSize: "0.95rem",
  cursor: "pointer",
  transition: "transform 0.2s ease, opacity 0.2s ease",
};

const formCardStyles: CSSProperties = {
  width: "100%",
  maxWidth: "820px",
  backdropFilter: "blur(18px)",
  background: "rgba(5, 5, 10, 0.45)",
  borderRadius: "36px",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  padding: "32px 38px",
  boxShadow: "0 20px 60px rgba(3, 3, 5, 0.6)",
  pointerEvents: "auto",
};

const statusTextStyles: CSSProperties = {
  fontSize: "0.85rem",
  letterSpacing: "0.04em",
  textTransform: "uppercase",
  opacity: 0.8,
};

const errorTextStyles: CSSProperties = {
  fontSize: "0.85rem",
  marginTop: "12px",
  color: "#FF7262",
};

const labelStyles: CSSProperties = {
  fontSize: "0.85rem",
  fontWeight: 600,
  letterSpacing: "0.05em",
  textTransform: "uppercase",
  marginBottom: "10px",
  color: "rgba(255, 255, 255, 0.8)",
};

const helperTextStyles: CSSProperties = {
  marginTop: "10px",
  color: "rgba(255, 255, 255, 0.65)",
  fontSize: "0.85rem",
};

const samplesWrapStyles: CSSProperties = {
  marginTop: "16px",
  display: "flex",
  flexDirection: "column",
  gap: "8px",
};

const samplesListStyles: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "8px",
};

const sampleButtonStyles: CSSProperties = {
  borderRadius: "999px",
  padding: "6px 14px",
  border: "1px solid rgba(255, 255, 255, 0.2)",
  background: "rgba(255, 255, 255, 0.06)",
  color: "#ffffff",
  fontSize: "0.78rem",
  letterSpacing: "0.02em",
  cursor: "pointer",
};

const viewerBackdropStyles: CSSProperties = {
  position: "absolute",
  inset: 0,
  background: "radial-gradient(circle at top, rgba(255, 111, 0, 0.15), transparent 45%)",
};

const overlayWrapperStyles: CSSProperties = {
  position: "absolute",
  inset: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "0 24px",
  pointerEvents: "none",
};

const hasFileExtension = (pathname: string) => /\.[a-z0-9]+$/i.test(pathname);

export default function SogsViewerPage() {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const requestIdRef = useRef(0);

  const getBaseOrigin = () => {
    return typeof window !== "undefined" ? window.location.origin : "https://spaceport.space";
  };

  const prettifySource = (rawValue: string) => {
    const trimmed = rawValue.trim();
    if (!trimmed) {
      return "none";
    }
    try {
      const parsed =
        trimmed.startsWith("http://") || trimmed.startsWith("https://")
          ? new URL(trimmed)
          : new URL(trimmed, getBaseOrigin());
      return parsed.host ? `${parsed.host}${parsed.pathname}` : parsed.pathname || trimmed;
    } catch {
      return trimmed;
    }
  };

  const convertToProxyPath = (url: URL) => {
    const base = `${url.protocol}//${url.host}`;
    const encodedBase = base.replace("://", ":/");
    return `/api/sogs-proxy/${encodedBase}${url.pathname}${url.search}`;
  };

  const convertToManagedBundlePath = (url: URL) => {
    const params = new URLSearchParams({
      url: url.toString(),
    });

    if (url.pathname.endsWith("/meta.json") || url.pathname === "/meta.json") {
      params.set("rewriteMeta", "true");
    }

    return `${ML_PIPELINE_API_URL}/bundle-resource?${params.toString()}`;
  };

  const normalizeAssetUrl = (rawValue: string, defaultFilename: string | null): string | null => {
    const trimmed = rawValue.trim();
    if (!trimmed) {
      return null;
    }

    try {
      const parsed =
        trimmed.startsWith("http://") || trimmed.startsWith("https://")
          ? new URL(trimmed)
          : new URL(trimmed, getBaseOrigin());

      if (!parsed.protocol.startsWith("http")) {
        return null;
      }

      if (defaultFilename && !hasFileExtension(parsed.pathname)) {
        parsed.pathname = parsed.pathname.replace(/\/?$/, `/${defaultFilename}`);
      }

      if (SPACEPORT_S3_HOST.test(parsed.host)) {
        if (ML_PIPELINE_API_URL) {
          return convertToManagedBundlePath(parsed);
        }
        return convertToProxyPath(parsed);
      }

      return parsed.toString();
    } catch {
      return null;
    }
  };

  const buildSiblingAssetRawUrl = (rawValue: string, filename: string) => {
    const parsed =
      rawValue.startsWith("http://") || rawValue.startsWith("https://")
        ? new URL(rawValue)
        : new URL(rawValue, getBaseOrigin());
    if (hasFileExtension(parsed.pathname)) {
      parsed.pathname = parsed.pathname.replace(/[^/]+$/, filename);
    } else {
      parsed.pathname = parsed.pathname.replace(/\/?$/, `/${filename}`);
    }
    return parsed.toString();
  };

  const fetchIfOk = async (url: string) => {
    try {
      const response = await fetch(url, {
        method: "GET",
        cache: "no-store",
      });
      if (!response.ok) {
        return null;
      }
      return response;
    } catch {
      return null;
    }
  };

  const resolveSkyboxUrl = async (bundleRawValue: string, explicitSkyboxRawValue?: string | null) => {
    if (explicitSkyboxRawValue) {
      const explicitUrl = normalizeAssetUrl(explicitSkyboxRawValue, null);
      if (explicitUrl && (await fetchIfOk(explicitUrl))) {
        return explicitUrl;
      }
    }

    const manifestRawUrl = buildSiblingAssetRawUrl(bundleRawValue, "background_manifest.json");
    const manifestUrl = normalizeAssetUrl(manifestRawUrl, null);
    if (manifestUrl) {
      const manifestResponse = await fetchIfOk(manifestUrl);
      if (manifestResponse) {
        try {
          const manifest = (await manifestResponse.json()) as { asset?: string };
          if (manifest?.asset) {
            const skyboxRawUrl = buildSiblingAssetRawUrl(bundleRawValue, manifest.asset);
            const skyboxUrl = normalizeAssetUrl(skyboxRawUrl, null);
            if (skyboxUrl && (await fetchIfOk(skyboxUrl))) {
              return skyboxUrl;
            }
          }
        } catch {
          // Ignore invalid manifests and fall back to the conventional filename.
        }
      }
    }

    const conventionalSkyboxRawUrl = buildSiblingAssetRawUrl(bundleRawValue, "background_skybox.webp");
    const conventionalSkyboxUrl = normalizeAssetUrl(conventionalSkyboxRawUrl, null);
    if (conventionalSkyboxUrl && (await fetchIfOk(conventionalSkyboxUrl))) {
      return conventionalSkyboxUrl;
    }

    return null;
  };

  const [inputUrl, setInputUrl] = useState(DEFAULT_BUNDLE_URL);
  const [activeUrl, setActiveUrl] = useState(DEFAULT_BUNDLE_URL);
  const [activeSkyboxUrl, setActiveSkyboxUrl] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("Paste an S3 bundle URL to render your splats.");
  const [sourceLabel, setSourceLabel] = useState(() => prettifySource(DEFAULT_BUNDLE_URL));
  const [error, setError] = useState<string | null>(null);
  const [iframeKey, setIframeKey] = useState(0);
  const [viewerState, setViewerState] = useState<"idle" | "loading" | "ready">("idle");
  const [chromeless, setChromeless] = useState(false);

  const attemptLoad = async (rawBundleValue: string, explicitSkyboxRawValue?: string | null) => {
    const normalizedBundleUrl = normalizeAssetUrl(rawBundleValue, "meta.json");
    if (!normalizedBundleUrl) {
      setError("Enter a valid HTTPS URL pointing to the SOGS bundle (folder or meta.json).");
      return false;
    }

    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;

    setError(null);
    setViewerState("loading");
    setStatusMessage("Resolving bundle assets…");
    setSourceLabel(prettifySource(rawBundleValue));

    const resolvedSkyboxUrl = await resolveSkyboxUrl(rawBundleValue, explicitSkyboxRawValue);
    if (requestIdRef.current !== requestId) {
      return false;
    }

    setStatusMessage(resolvedSkyboxUrl ? "Loading splats and baked skybox…" : "Loading splats…");
    setActiveUrl(normalizedBundleUrl);
    setActiveSkyboxUrl(resolvedSkyboxUrl);
    setIframeKey((prev) => prev + 1);
    return true;
  };

  const viewerSrc = useMemo(() => {
    const params = new URLSearchParams({
      settings: "/supersplat-viewer/settings.json",
      content: activeUrl || DEFAULT_BUNDLE_URL,
    });

    if (activeSkyboxUrl) {
      params.set("skybox", activeSkyboxUrl);
    }

    return `${VIEWER_BASE}?${params.toString()}`;
  }, [activeSkyboxUrl, activeUrl]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void attemptLoad(inputUrl);
  };

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === "supersplat:firstFrame" && event.source === iframeRef.current?.contentWindow) {
        setViewerState("ready");
        setStatusMessage(
          activeSkyboxUrl ? "SOGS bundle and baked skybox loaded." : "SOGS bundle loaded in the embedded viewer.",
        );
      }
    };

    window.addEventListener("message", handleMessage);
    return () => {
      window.removeEventListener("message", handleMessage);
    };
  }, [activeSkyboxUrl]);

  useEffect(() => {
    const poll = () => {
      const iframe = iframeRef.current;
      try {
        const doc = iframe?.contentDocument;
        if (!doc) {
          return;
        }
        const loadingWrap = doc.getElementById("loadingWrap");
        if (loadingWrap?.classList.contains("hidden")) {
          setViewerState((prev) => (prev === "ready" ? prev : "ready"));
          setStatusMessage(
            activeSkyboxUrl ? "SOGS bundle and baked skybox loaded." : "SOGS bundle loaded in the embedded viewer.",
          );
        }
      } catch {
        // Ignore cross-origin access errors.
      }
    };

    const id = window.setInterval(poll, 1000);
    return () => {
      window.clearInterval(id);
    };
  }, [activeSkyboxUrl, viewerSrc]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const bundleParam = params.get("bundle");
    const skyboxParam = params.get("skybox");
    const chromelessParam = params.get("chromeless");

    setChromeless(chromelessParam === "1" || chromelessParam === "true");

    if (bundleParam) {
      setInputUrl(bundleParam);
      void attemptLoad(bundleParam, skyboxParam);
      return;
    }

    void attemptLoad(DEFAULT_BUNDLE_URL);
  }, []);

  const isSubmitDisabled = !inputUrl.trim() || viewerState === "loading";

  return (
    <main
      style={{
        position: "relative",
        minHeight: "100vh",
        backgroundColor: "#010104",
        color: "#ffffff",
        overflow: "hidden",
        fontFamily: "'Space Grotesk', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      <div style={viewerBackdropStyles} />

      <div
        style={{
          position: "absolute",
          inset: 0,
        }}
      >
        <iframe
          key={iframeKey}
          ref={iframeRef}
          src={viewerSrc}
          title="SuperSplat Viewer"
          style={{ border: "none", width: "100%", height: "100%", display: "block" }}
          allow="xr-spatial-tracking"
        />
      </div>

      {!chromeless && (
        <div style={overlayWrapperStyles}>
          <form style={formCardStyles} onSubmit={handleSubmit}>
            <p style={statusTextStyles}>
              {viewerState === "ready" ? "Viewer ready" : viewerState === "loading" ? "Loading viewer" : "Idle"}
              {" · Source: "}
              {sourceLabel}
            </p>
            <h1
              style={{
                fontSize: "2.5rem",
                fontWeight: 600,
                margin: "10px 0 24px",
                letterSpacing: "-0.02em",
              }}
            >
              SOGS Viewer
            </h1>
            <label style={labelStyles} htmlFor="sogs-url-input">
              S3 bundle URL
            </label>
            <div
              style={{
                display: "flex",
                gap: "14px",
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <input
                id="sogs-url-input"
                type="url"
                inputMode="url"
                placeholder="https://bucket.s3.amazonaws.com/path/to/sogs/"
                value={inputUrl}
                onChange={(event) => setInputUrl(event.target.value)}
                style={{
                  ...pillInputStyles,
                  borderColor: error ? "#FF7262" : "rgba(255, 255, 255, 0.2)",
                  boxShadow: viewerState === "ready" ? "0 0 0 1px rgba(255, 79, 0, 0.2)" : "none",
                  flex: 1,
                }}
              />
              <button
                type="submit"
                style={{
                  ...buttonStyles,
                  opacity: isSubmitDisabled ? 0.6 : 1,
                  cursor: isSubmitDisabled ? "not-allowed" : "pointer",
                }}
                disabled={isSubmitDisabled}
              >
                {viewerState === "loading" ? "Loading…" : "Load"}
              </button>
            </div>
            <p style={helperTextStyles}>
              Expecting a public HTTPS S3 directory that contains the SuperSplat bundle files (for example{" "}
              <code>meta.json</code>, <code>means_l.webp</code>, <code>shN_centroids.webp</code>). If a baked skybox is
              present, this page auto-loads it from <code>background_manifest.json</code> or{" "}
              <code>background_skybox.webp</code>.
            </p>
            <div style={samplesWrapStyles}>
              <p style={{ ...helperTextStyles, marginTop: 0 }}>
                Quick samples (Spaceport buckets auto-route through the managed bundle API so preview builds can load
                private compressed artifacts; keep the local mirror handy if you need an offline fallback):
              </p>
              <div style={samplesListStyles}>
                {SAMPLE_BUNDLES.map((sample) => (
                  <button
                    key={sample.url}
                    type="button"
                    style={sampleButtonStyles}
                    onClick={() => {
                      setInputUrl(sample.url);
                      void attemptLoad(sample.url);
                    }}
                  >
                    {sample.label}
                  </button>
                ))}
              </div>
            </div>
            <p style={{ ...helperTextStyles, marginTop: "6px" }}>{statusMessage}</p>
            {error && <p style={errorTextStyles}>{error}</p>}
          </form>
        </div>
      )}
    </main>
  );
}
