"use client";

import { CSSProperties, FormEvent, useEffect, useMemo, useRef, useState } from "react";

const DEFAULT_BUNDLE_URL =
  "https://spaceport-ml-processing.s3.amazonaws.com/public-viewer/sogs-test-1753999934/meta.json";
const VIEWER_BASE = "/supersplat-viewer/index.html";

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
  const [inputUrl, setInputUrl] = useState(DEFAULT_BUNDLE_URL);
  const [activeUrl, setActiveUrl] = useState(DEFAULT_BUNDLE_URL);
  const [statusMessage, setStatusMessage] = useState("Paste an S3 bundle URL to render your splats.");
  const [error, setError] = useState<string | null>(null);
  const [iframeKey, setIframeKey] = useState(0);
  const [viewerState, setViewerState] = useState<"idle" | "loading" | "ready">("idle");

  const normalizeBundleUrl = (rawValue: string): string | null => {
    const trimmed = rawValue.trim();
    if (!trimmed) {
      return null;
    }

    try {
      const parsed = new URL(trimmed);
      if (!parsed.protocol.startsWith("http")) {
        return null;
      }

      if (!parsed.pathname.endsWith(".json")) {
        parsed.pathname = parsed.pathname.replace(/\/?$/, "/meta.json");
      }
      return parsed.toString();
    } catch (normalizeError) {
      return null;
    }
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
    setError(null);
    const normalized = normalizeBundleUrl(inputUrl);
    if (!normalized) {
      setError("Enter a valid HTTPS URL pointing to the SOGS bundle (folder or meta.json).");
      return;
    }

    setStatusMessage("Loading viewer…");
    setViewerState("loading");
    setActiveUrl(normalized);
    setIframeKey((prev) => prev + 1);
  };

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) {
      return;
    }

    const poll = () => {
      try {
        const doc = iframe.contentDocument;
        if (!doc) {
          return;
        }
        const loadingWrap = doc.getElementById("loadingWrap");
        if (loadingWrap?.classList.contains("hidden")) {
          setViewerState("ready");
          setStatusMessage("SOGS bundle loaded in the embedded viewer.");
        }
      } catch (pollError) {
        // ignore cross-origin errors (should not happen since the viewer is same-origin)
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
            {" · Bundle Source"}
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
          <p style={{ ...helperTextStyles, marginTop: "6px" }}>{statusMessage}</p>
          {error && <p style={errorTextStyles}>{error}</p>}
        </form>
      </div>
    </main>
  );
}
