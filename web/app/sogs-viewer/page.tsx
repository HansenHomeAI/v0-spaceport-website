"use client";

import { CSSProperties, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import Script from "next/script";

type SuperSplatViewerInstance = {
  loadFromUrl: (url: string) => Promise<void>;
  destroy?: () => void;
};

declare global {
  interface Window {
    SuperSplatViewer?: new (canvas: HTMLCanvasElement) => SuperSplatViewerInstance;
  }
}

const PLAYCANVAS_SCRIPT = "https://cdn.jsdelivr.net/npm/playcanvas@latest/build/playcanvas-stable.min.js";
const SUPERSPLAT_SCRIPT = "https://cdn.jsdelivr.net/npm/@playcanvas/supersplat@latest/dist/bundle.min.js";

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

const normalizeS3Url = (rawValue: string): string | null => {
  const trimmed = rawValue.trim();
  if (!trimmed) {
    return null;
  }

  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol !== "https:") {
      return null;
    }

    let normalized = parsed.toString();
    if (!normalized.endsWith("/")) {
      normalized = `${normalized}/`;
    }
    return normalized;
  } catch (error) {
    return null;
  }
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
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const viewerRef = useRef<SuperSplatViewerInstance | null>(null);
  const [s3Url, setS3Url] = useState("");
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Paste an S3 bundle URL to render your splats.");
  const [error, setError] = useState<string | null>(null);
  const [scriptsLoaded, setScriptsLoaded] = useState({ playcanvas: false, supersplat: false });
  const [viewerReady, setViewerReady] = useState(false);

  const scriptsReady = useMemo(
    () => scriptsLoaded.playcanvas && scriptsLoaded.supersplat,
    [scriptsLoaded]
  );

  useEffect(() => {
    if (!canvasRef.current) {
      return;
    }

    const handleResize = () => {
      if (!canvasRef.current) {
        return;
      }
      const deviceRatio = window.devicePixelRatio || 1;
      const { clientWidth, clientHeight } = canvasRef.current;
      canvasRef.current.width = clientWidth * deviceRatio;
      canvasRef.current.height = clientHeight * deviceRatio;
    };

    handleResize();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  useEffect(() => {
    if (!scriptsReady || !canvasRef.current) {
      return;
    }

    if (!viewerRef.current) {
      if (!window.SuperSplatViewer) {
        setError("SuperSplat viewer script is not available yet.");
        setViewerReady(false);
        return;
      }

      try {
        viewerRef.current = new window.SuperSplatViewer(canvasRef.current);
        setError(null);
      } catch (viewerError) {
        console.error("Failed to initialize SuperSplat viewer", viewerError);
        setError("Failed to initialize viewer. Refresh and try again.");
        setViewerReady(false);
        return;
      }
    }

    setViewerReady(true);

    return () => {
      viewerRef.current?.destroy?.();
      viewerRef.current = null;
      setViewerReady(false);
    };
  }, [scriptsReady]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (!viewerRef.current) {
      setError("Viewer is still preparing. Please wait a moment.");
      return;
    }

    const normalizedUrl = normalizeS3Url(s3Url);
    if (!normalizedUrl) {
      setError("Enter a valid HTTPS S3 URL ending with '/'.");
      return;
    }

    setLoading(true);
    setStatusMessage("Fetching SOGS bundle…");

    try {
      await viewerRef.current.loadFromUrl(normalizedUrl);
      setStatusMessage("SOGS bundle loaded.");
    } catch (loadError) {
      console.error("Failed to load SOGS bundle", loadError);
      setError("Unable to load the SOGS bundle. Confirm the URL and S3 CORS settings.");
      setStatusMessage("Waiting for a valid bundle URL.");
    } finally {
      setLoading(false);
    }
  };

  const scriptLoadHandler =
    (key: "playcanvas" | "supersplat") => () =>
      setScriptsLoaded((prev) => ({ ...prev, [key]: true }));

  const scriptErrorHandler = (label: string) => () => {
    setError(`Failed to load the ${label} runtime.`);
  };

  const isSubmitDisabled = loading || !s3Url.trim();

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
      <Script
        src={PLAYCANVAS_SCRIPT}
        strategy="afterInteractive"
        onLoad={scriptLoadHandler("playcanvas")}
        onError={scriptErrorHandler("PlayCanvas")}
      />
      <Script
        src={SUPERSPLAT_SCRIPT}
        strategy="afterInteractive"
        onLoad={scriptLoadHandler("supersplat")}
        onError={scriptErrorHandler("SuperSplat")}
      />

      <div style={viewerBackdropStyles} />

      <div
        style={{
          position: "absolute",
          inset: 0,
        }}
      >
        <canvas
          ref={canvasRef}
          style={{
            width: "100%",
            height: "100%",
            display: "block",
            background: "radial-gradient(circle at 25% 20%, rgba(255, 79, 0, 0.12), transparent 55%)",
          }}
        />
      </div>

      <div style={overlayWrapperStyles}>
        <form style={formCardStyles} onSubmit={handleSubmit}>
          <p style={statusTextStyles}>
            {viewerReady ? "Viewer ready" : "Initializing viewer"}
            {" · "}
            {scriptsReady ? "Runtime loaded" : "Loading runtime"}
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
              value={s3Url}
              onChange={(event) => setS3Url(event.target.value)}
              style={{
                ...pillInputStyles,
                borderColor: error ? "#FF7262" : "rgba(255, 255, 255, 0.2)",
                boxShadow: viewerReady ? "0 0 0 1px rgba(255, 79, 0, 0.2)" : "none",
                flex: 1,
              }}
              disabled={loading}
            />
            <button
              type="submit"
              style={{
                ...buttonStyles,
                opacity: isSubmitDisabled ? 0.6 : 1,
                cursor: isSubmitDisabled ? "not-allowed" : "pointer",
                transform: loading ? "scale(0.98)" : "none",
              }}
              disabled={isSubmitDisabled}
            >
              {loading ? "Loading…" : "Load"}
            </button>
          </div>
          <p style={helperTextStyles}>
            Expecting a public HTTPS S3 directory that contains the SuperSplat bundle files (e.g.{" "}
            <code>manifest.json</code>, <code>data.bin</code>).
          </p>
          <p style={{ ...helperTextStyles, marginTop: "6px" }}>{statusMessage}</p>
          {error && <p style={errorTextStyles}>{error}</p>}
        </form>
      </div>
    </main>
  );
}
