"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  buildSogsSceneExport,
  createDefaultScenePayload,
  type SogsScenePayload,
} from "../../lib/sogsViewerSceneDefaults";
import { DEFAULT_SOGS_BUNDLE_URL, normalizeBundleUrl } from "../../lib/sogsViewerBundle";
import "./sogs-viewer.css";

const VIEWER_BASE = "/supersplat-viewer/index.html";

export default function SogsViewerDevPanel() {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  const [inputUrl, setInputUrl] = useState(DEFAULT_SOGS_BUNDLE_URL);
  const [activeUrl, setActiveUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [iframeKey, setIframeKey] = useState(0);
  const [viewerState, setViewerState] = useState<"idle" | "loading" | "ready">("idle");

  const [devOpen, setDevOpen] = useState(false);
  const [guides, setGuides] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const [scene, setScene] = useState<SogsScenePayload>(() => createDefaultScenePayload());
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

  const viewerSrc = (() => {
    if (!activeUrl) {
      return null;
    }
    const params = new URLSearchParams({
      settings: "/supersplat-viewer/settings.json",
      content: activeUrl,
    });
    return `${VIEWER_BASE}?${params.toString()}`;
  })();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    attemptLoad(inputUrl);
  };

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.data?.type === "supersplat:firstFrame" && event.source === iframeRef.current?.contentWindow) {
        setViewerState("ready");
      }
      if (event.data?.type === "sogs:state" && event.source === iframeRef.current?.contentWindow) {
        const d = event.data;
        if (
          !Array.isArray(d.position) ||
          d.position.length !== 3 ||
          !Array.isArray(d.rotation) ||
          d.rotation.length !== 3 ||
          typeof d.scale !== "number" ||
          typeof d.fov !== "number"
        ) {
          return;
        }
        const next: SogsScenePayload = {
          position: [d.position[0], d.position[1], d.position[2]],
          rotation: [d.rotation[0], d.rotation[1], d.rotation[2]],
          scale: d.scale,
          fov: d.fov,
        };
        setScene(next);
        setForm(next);
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
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

  useEffect(() => {
    if (!devOpen || !viewerSrc) {
      return;
    }
    postToIframe({ type: "sogs:requestState" });
  }, [devOpen, viewerSrc, postToIframe]);

  useEffect(() => {
    if (!activeUrl) {
      return;
    }
    postToIframe({ type: "sogs:guides", enabled: guides });
  }, [guides, postToIframe, activeUrl, iframeKey]);

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

  const applyDev = () => {
    postToIframe({
      type: "sogs:apply",
      position: form.position,
      rotation: form.rotation,
      scale: form.scale,
      fov: form.fov,
    });
  };

  const resetDev = () => {
    const d = createDefaultScenePayload();
    setForm(d);
    postToIframe({
      type: "sogs:apply",
      position: d.position,
      rotation: d.rotation,
      scale: d.scale,
      fov: d.fov,
    });
  };

  const syncFromScene = () => {
    setForm(scene);
  };

  const copySceneJson = async () => {
    const payload = buildSogsSceneExport({
      bundleUrl: activeUrl || inputUrl.trim() || "",
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
            placeholder="https://…/supersplat_bundle/ or …/meta.json"
            value={inputUrl}
            onChange={(e) => setInputUrl(e.target.value)}
            className={error ? "sogs-input-error" : undefined}
          />
          <button type="submit" className="sogs-btn-primary" disabled={isSubmitDisabled}>
            {viewerState === "loading" ? "…" : "Load"}
          </button>
        </div>
        <div className="sogs-toolbar-row">
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
                    Splat & camera
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

                <div className="sogs-dev-grid">
                  {(["x", "y", "z"] as const).map((axis, i) => (
                    <div key={`p-${axis}`} className="sogs-dev-field">
                      <label htmlFor={`pos-${axis}`}>Pos {axis.toUpperCase()}</label>
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
                  {(["x", "y", "z"] as const).map((axis, i) => (
                    <div key={`r-${axis}`} className="sogs-dev-field">
                      <label htmlFor={`rot-${axis}`}>Rot {axis.toUpperCase()}°</label>
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
                  <div className="sogs-dev-field sogs-dev-field-full">
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
                  <div className="sogs-dev-field sogs-dev-field-full">
                    <label htmlFor="cam-fov">FOV (°)</label>
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
                  Show axis guides (RGB = XYZ at splat origin)
                </label>

                <div className="sogs-dev-actions">
                  <div className="sogs-dev-actions-row">
                    <button type="button" className="sogs-btn-secondary" onClick={syncFromScene}>
                      Sync from scene
                    </button>
                    <button type="button" className="sogs-btn-secondary" onClick={resetDev}>
                      Reset defaults
                    </button>
                    <button type="button" className="sogs-btn-primary" onClick={applyDev}>
                      Apply
                    </button>
                  </div>
                  <div className="sogs-copy-row">
                    <button type="button" className="sogs-btn-secondary" onClick={copySceneJson}>
                      Copy scene JSON
                    </button>
                    {copyFeedback ? <span className="sogs-copy-feedback">{copyFeedback}</span> : null}
                  </div>
                </div>
                <p className="sogs-dev-note">
                  Defaults match the viewer: rotation Z = 180° (PlayCanvas gsplat). FOV is applied after the orbit camera
                  updates each frame (dev override). Paste copied JSON so maintainers can update{" "}
                  <code style={{ fontSize: "10px" }}>web/lib/sogsViewerSceneDefaults.ts</code>.
                </p>
              </div>
            ) : null}
          </div>
        </div>
        <p className="sogs-hint">
          {viewerState === "ready" && activeUrl
            ? "Ready — orbit or fly with the embedded viewer controls."
            : viewerState === "loading" && activeUrl
              ? "Loading bundle…"
              : activeUrl
                ? "Idle"
                : "Paste a public HTTPS URL, then Load."}
        </p>
        {error ? <p className="sogs-error">{error}</p> : null}
      </form>
    </main>
  );
}
