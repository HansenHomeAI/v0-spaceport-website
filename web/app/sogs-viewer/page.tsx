"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

const VIEWER_BASE = "/supersplat-viewer/index.html";

const DEFAULT_SOGS_BUNDLE_URL =
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/sogs-test-1763664401/supersplat_bundle/meta.json";

const PROXY_HOSTS = new Set([
  "spaceport-ml-processing.s3.amazonaws.com",
  "spaceport-ml-processing.s3.us-west-2.amazonaws.com",
]);

function getBaseOrigin(): string {
  return typeof window !== "undefined" ? window.location.origin : "https://spcprt.com";
}

function convertToProxyPath(url: URL): string {
  const base = `${url.protocol}//${url.host}`;
  const encodedBase = base.replace("://", ":/");
  return `/api/sogs-proxy/${encodedBase}${url.pathname}${url.search}`;
}

function normalizeBundleUrl(rawValue: string): string | null {
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
}

export default function SogsViewerPage() {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  const [inputUrl, setInputUrl] = useState(DEFAULT_SOGS_BUNDLE_URL);
  const [activeUrl, setActiveUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [iframeKey, setIframeKey] = useState(0);
  const [viewerState, setViewerState] = useState<"idle" | "loading" | "ready">("idle");

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
    setIframeKey((prev) => prev + 1);
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

    return `${VIEWER_BASE}?${params.toString()}`;
  }, [activeUrl, iframeKey]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    attemptLoad(inputUrl);
  };

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === "supersplat:firstFrame" && event.source === iframeRef.current?.contentWindow) {
        setViewerState("ready");
      }
    };

    window.addEventListener("message", handleMessage);
    return () => {
      window.removeEventListener("message", handleMessage);
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const q = params.get("url");
    const raw = q?.trim() ? q.trim() : DEFAULT_SOGS_BUNDLE_URL;
    setInputUrl(raw);
    attemptLoad(raw);
  }, [attemptLoad]);

  const isSubmitDisabled = !inputUrl.trim();

  return (
    <main
      style={{
        position: "fixed",
        inset: 0,
        margin: 0,
        padding: 0,
        backgroundColor: "#000000",
        overflow: "hidden",
      }}
    >
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
        <div style={{ position: "absolute", inset: 0, backgroundColor: "#000000" }} aria-hidden />
      )}

      <form
        onSubmit={handleSubmit}
        style={{
          position: "fixed",
          top: 12,
          left: 12,
          zIndex: 20,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          maxWidth: "min(420px, calc(100vw - 24px))",
          padding: "10px 12px",
          borderRadius: 10,
          background: "rgba(8, 8, 12, 0.72)",
          border: "1px solid rgba(255, 255, 255, 0.12)",
          backdropFilter: "blur(12px)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.45)",
        }}
      >
        <label htmlFor="sogs-url-input" style={{ fontSize: 11, letterSpacing: "0.06em", color: "rgba(255,255,255,0.55)" }}>
          S3 bundle URL
        </label>
        <div style={{ display: "flex", gap: 8, alignItems: "stretch", flexWrap: "wrap" }}>
          <input
            id="sogs-url-input"
            type="url"
            inputMode="url"
            autoComplete="off"
            placeholder="https://…/supersplat_bundle/ or …/meta.json"
            value={inputUrl}
            onChange={(e) => setInputUrl(e.target.value)}
            style={{
              flex: 1,
              minWidth: 180,
              padding: "8px 10px",
              borderRadius: 6,
              border: error ? "1px solid #c44" : "1px solid rgba(255,255,255,0.18)",
              background: "rgba(0,0,0,0.35)",
              color: "#fff",
              fontSize: 13,
              outline: "none",
            }}
          />
          <button
            type="submit"
            disabled={isSubmitDisabled}
            style={{
              padding: "8px 14px",
              borderRadius: 6,
              border: "1px solid rgba(255,255,255,0.2)",
              background: isSubmitDisabled ? "rgba(255,255,255,0.08)" : "rgba(255, 79, 0, 0.9)",
              color: isSubmitDisabled ? "rgba(255,255,255,0.4)" : "#0a0a0a",
              fontSize: 13,
              fontWeight: 600,
              cursor: isSubmitDisabled ? "not-allowed" : "pointer",
            }}
          >
            {viewerState === "loading" ? "…" : "Load"}
          </button>
        </div>
        <p style={{ margin: 0, fontSize: 11, color: "rgba(255,255,255,0.45)" }}>
          {viewerState === "ready" && activeUrl
            ? "Ready — use the viewer controls to move the scene."
            : viewerState === "loading" && activeUrl
              ? "Loading bundle…"
              : activeUrl
                ? "Idle"
                : "Paste a public HTTPS URL, then Load."}
        </p>
        {error ? (
          <p style={{ margin: 0, fontSize: 12, color: "#ff8a80" }}>{error}</p>
        ) : null}
      </form>
    </main>
  );
}
