"use client";

import { CSSProperties, FormEvent, useEffect, useMemo, useRef, useState } from "react";

const DEFAULT_BUNDLE_URL = "/test-sogs-1763664401/meta.json";
const REMOTE_S3_BUNDLE =
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/sogs-test-1763664401/supersplat_bundle/meta.json";
const VIEWER_BASE = "/supersplat-viewer/index.html";
const PROXY_HOSTS = new Set([
  "spaceport-ml-processing.s3.amazonaws.com",
  "spaceport-ml-processing.s3.us-west-2.amazonaws.com",
]);
const SAMPLE_BUNDLES = [
  {
    label: "Local copy · sogs-test-1763664401",
    url: DEFAULT_BUNDLE_URL,
  },
  {
    label: "S3 proxy · sogs-test-1763664401",
    url: REMOTE_S3_BUNDLE,
  },
  {
    label: "Legacy local demo",
    url: "/test-sogs-bundle/meta.json",
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

export default function SogsViewerPage() {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
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
      if (PROXY_HOSTS.has(parsed.host)) {
        return `${parsed.host}${parsed.pathname}`;
      }
      return parsed.host ? `${parsed.host}${parsed.pathname}` : parsed.pathname || trimmed;
    } catch {
      return trimmed;
    }
  };

  const [inputUrl, setInputUrl] = useState(DEFAULT_BUNDLE_URL);
  const [activeUrl, setActiveUrl] = useState(DEFAULT_BUNDLE_URL);
  const [statusMessage, setStatusMessage] = useState("Paste an S3 bundle URL to render your splats.");
  const [sourceLabel, setSourceLabel] = useState(() => prettifySource(DEFAULT_BUNDLE_URL));
  const [error, setError] = useState<string | null>(null);
  const [iframeKey, setIframeKey] = useState(0);
  const [viewerState, setViewerState] = useState<"idle" | "loading" | "ready">("idle");

  const convertToProxyPath = (url: URL) => {
    const base = `${url.protocol}//${url.host}`;
    const encodedBase = base.replace("://", ":/");
    return `/api/sogs-proxy/${encodedBase}${url.pathname}${url.search}`;
  };

  const normalizeBundleUrl = (rawValue: string): string | null => {
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

      if (!parsed.pathname.endsWith(".json")) {
        parsed.pathname = parsed.pathname.replace(/\/?$/, "/meta.json");
      }

      if (PROXY_HOSTS.has(parsed.host)) {
        return convertToProxyPath(parsed);
      }

      return parsed.toString();
    } catch {
      return null;
    }
  };

  const attemptLoad = (rawValue: string) => {
    setError(null);
    const normalized = normalizeBundleUrl(rawValue);
    if (!normalized) {
      setError("Enter a valid HTTPS URL pointing to the SOGS bundle (folder or meta.json).");
      return false;
    }

    setStatusMessage("Loading viewer…");
    setViewerState("loading");
    setSourceLabel(prettifySource(rawValue));
    setActiveUrl(normalized);
    setIframeKey((prev) => prev + 1);
    return true;
  };

  const viewerSrc = useMemo(() => {
    if (!activeUrl) {
      return `${VIEWER_BASE}?settings=/supersplat-viewer/settings.json`;
    }

    const params = new URLSearchParams({
      settings: "/supersplat-viewer/settings.json",
      content: activeUrl,
    });

    return `${VIEWER_BASE}?${params.toString()}`;
  }, [activeUrl, iframeKey]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    attemptLoad(inputUrl);
  };

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === "supersplat:firstFrame" && event.source === iframeRef.current?.contentWindow) {
        console.info("[sogs-viewer] first frame event received");
        setViewerState("ready");
        setStatusMessage("SOGS bundle loaded in the embedded viewer.");
      }
    };

    window.addEventListener("message", handleMessage);
    return () => {
      window.removeEventListener("message", handleMessage);
    };
  }, []);

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
          setStatusMessage("SOGS bundle loaded in the embedded viewer.");
        }
      } catch {
        // ignore cross-origin access errors
      }
    };

    const id = window.setInterval(poll, 1000);
    return () => {
      window.clearInterval(id);
    };
  }, [viewerSrc]);

  useEffect(() => {
    setViewerState("loading");
    setStatusMessage("Loading viewer…");
    const normalizedDefault = normalizeBundleUrl(DEFAULT_BUNDLE_URL);
    if (normalizedDefault && normalizedDefault !== DEFAULT_BUNDLE_URL) {
      setActiveUrl(normalizedDefault);
    }
  }, []);

  const isSubmitDisabled = !inputUrl.trim();

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
            Expecting a public HTTPS S3 directory that contains the SuperSplat bundle files (e.g.{" "}
            <code>meta.json</code>, <code>means_l.webp</code>, <code>shN_centroids.webp</code>).
          </p>
          <div style={samplesWrapStyles}>
            <p style={{ ...helperTextStyles, marginTop: 0 }}>
              Quick samples (spaceport buckets are auto-routed through the proxy to bypass CORS; the direct S3
              entry still requires AWS SigV4, so use the mirrored local copy if that bucket is locked down):
            </p>
            <div style={samplesListStyles}>
              {SAMPLE_BUNDLES.map((sample) => (
                <button
                  key={sample.url}
                  type="button"
                  style={sampleButtonStyles}
                  onClick={() => {
                    setInputUrl(sample.url);
                    attemptLoad(sample.url);
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
    </main>
  );
}
