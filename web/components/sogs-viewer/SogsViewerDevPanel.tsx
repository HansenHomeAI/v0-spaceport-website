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
  /** Skip first sogs:state after each iframe load — it reflects viewer defaults before SOGS_DEFAULT_SCENE is applied. */
  const ignoreNextSogsStateRef = useRef(false);

  const [inputUrl, setInputUrl] = useState(DEFAULT_SOGS_BUNDLE_URL);
  const [activeUrl, setActiveUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [iframeKey, setIframeKey] = useState(0);
  const [viewerState, setViewerState] = useState<"idle" | "loading" | "ready">("idle");

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
    ignoreNextSogsStateRef.current = true;
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
        const d = createDefaultScenePayload();
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
        setForm(d);
        setViewerState("ready");
      }
      if (event.data?.type === "sogs:state" && event.source === iframeRef.current?.contentWindow) {
        if (ignoreNextSogsStateRef.current) {
          ignoreNextSogsStateRef.current = false;
          return;
        }
        const d = event.data as { position?: number[] };
        if (Array.isArray(d.position) && d.position.length === 3) {
          setForm((f) => ({
            ...f,
            position: [d.position[0], d.position[1], d.position[2]] as [number, number, number],
          }));
        }
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
                    updates. Two-finger drag (or middle mouse on desktop) translates the splat on the horizontal (world
                    X/Z) plane; position is synced from
                    the viewer. Paste copied JSON for maintainers to update{" "}
                    <code className="sogs-dev-code">web/lib/sogsViewerSceneDefaults.ts</code>.
                  </p>
                </details>
              </div>
            ) : null}
          </div>
        </div>
        <p className="sogs-hint">
          {viewerState === "ready" && activeUrl
            ? "Ready — two-finger drag moves the splat on world X/Z (middle mouse on desktop); left-drag orbits, right-drag pans the camera."
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
