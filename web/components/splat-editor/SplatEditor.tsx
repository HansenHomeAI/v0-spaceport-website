"use client";

import { DragEvent, FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createDefaultScenePayload } from "../../lib/sogsViewerSceneDefaults";
import "./splat-editor.css";

const VIEWER_BASE = "/supersplat-viewer/index.html";
const DEFAULT_SOURCE =
  "s3://spaceport-ml-processing/3dgs/manual-3dgs-1774642514/ml-job-20260327-201514-manual-3-3dgs/output/model.tar.gz";
const DEFAULT_SCENE = createDefaultScenePayload();
const SESSION_STORAGE_KEY = "spaceport:splat-editor:session-id";

type SessionState = {
  sessionId: string;
  sourceUrl: string;
  sourceArtifactType: "ply" | "model.tar.gz";
  sourceArtifactPath: string;
  workingPlyPath: string;
  exportTargetName: string;
  trainingMetadataPath: string | null;
  autoRefreshEnabled: boolean;
  revisionHash: string;
  lastModifiedMs: number;
  sizeBytes: number;
  vertexCount: number;
};

type TransformState = {
  position: [number, number, number];
  rotation: [number, number, number];
};

const DEFAULT_TRANSFORM: TransformState = {
  position: [...DEFAULT_SCENE.position],
  rotation: [...DEFAULT_SCENE.rotation],
};

const GUIDES_PAYLOAD = {
  type: "sogs:guides",
  enabled: true,
  length: 20,
  radius: 0.03,
  colors: {
    x: [0.92, 0.26, 0.22],
    y: [0.96, 0.85, 0.2],
    z: [0.24, 0.56, 0.98],
  },
} as const;

export default function SplatEditor() {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const lastRevisionRef = useRef<string | null>(null);
  const transformRef = useRef<TransformState>(DEFAULT_TRANSFORM);
  const ignoreNextSogsStateRef = useRef(false);
  const allowRestoreRef = useRef(true);
  const userTouchedSourceRef = useRef(false);

  const [source, setSource] = useState(DEFAULT_SOURCE);
  const [session, setSession] = useState<SessionState | null>(null);
  const [iframeKey, setIframeKey] = useState(0);
  const [viewerState, setViewerState] = useState<"idle" | "loading" | "ready">("idle");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [busyLabel, setBusyLabel] = useState<string | null>(null);
  const [clientReady, setClientReady] = useState(false);
  const [transform, setTransform] = useState<TransformState>(DEFAULT_TRANSFORM);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const [dropActive, setDropActive] = useState(false);

  const viewerSrc = useMemo(() => {
    if (!session) return null;
    const content = `/api/splat-editor/sessions/${session.sessionId}/splat.ply?rev=${encodeURIComponent(session.revisionHash)}`;
    const params = new URLSearchParams({
      settings: "/supersplat-viewer/settings.json",
      content,
      noui: "1",
    });
    return `${VIEWER_BASE}?${params.toString()}`;
  }, [session]);

  const sessionId = session?.sessionId ?? null;

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

  const applySceneToViewer = useCallback(
    (nextTransform: TransformState) => {
      postToIframe(GUIDES_PAYLOAD);
      postToIframe({
        type: "sogs:apply",
        position: nextTransform.position,
        rotation: nextTransform.rotation,
        scale: DEFAULT_SCENE.scale,
        fov: DEFAULT_SCENE.fov,
      });
    },
    [postToIframe],
  );

  const applySession = useCallback((nextSession: SessionState) => {
    setSession(nextSession);
    setSource(nextSession.sourceUrl);
    lastRevisionRef.current = nextSession.revisionHash;
    ignoreNextSogsStateRef.current = true;
    setViewerState("loading");
    setIframeKey((value) => value + 1);
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(SESSION_STORAGE_KEY, nextSession.sessionId);
    }
  }, []);

  useEffect(() => {
    transformRef.current = transform;
  }, [transform]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.data?.type === "supersplat:firstFrame" && event.source === iframeRef.current?.contentWindow) {
        applySceneToViewer(transformRef.current);
        setViewerState("ready");
        return;
      }
      if (event.data?.type === "sogs:state" && event.source === iframeRef.current?.contentWindow) {
        if (ignoreNextSogsStateRef.current) {
          ignoreNextSogsStateRef.current = false;
        }
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [applySceneToViewer]);

  useEffect(() => {
    setClientReady(true);
  }, []);

  useEffect(() => {
    if (!userTouchedSourceRef.current && source !== DEFAULT_SOURCE) {
      userTouchedSourceRef.current = true;
    }
  }, [source]);

  useEffect(() => {
    if (!clientReady) return;
    let cancelled = false;

    async function restoreLatestSession() {
      try {
        setBusy(true);
        setBusyLabel("Restoring local splat…");
        const storedSessionId =
          typeof window !== "undefined" ? window.sessionStorage.getItem(SESSION_STORAGE_KEY) : null;
        const preferredResponse = storedSessionId
          ? await fetch(`/api/splat-editor/sessions/${storedSessionId}`, { cache: "no-store" })
          : null;
        const preferredPayload = preferredResponse ? await preferredResponse.json() : null;
        const shouldIgnoreStoredSession =
          !!preferredPayload?.session &&
          preferredPayload.session.sourceUrl !== DEFAULT_SOURCE &&
          !userTouchedSourceRef.current &&
          source === DEFAULT_SOURCE;
        const response = shouldIgnoreStoredSession
          ? await fetch("/api/splat-editor/latest", { cache: "no-store" })
          : preferredResponse ?? (await fetch("/api/splat-editor/latest", { cache: "no-store" }));
        const payload =
          shouldIgnoreStoredSession || !preferredPayload ? await response.json() : preferredPayload;
        if (
          !response.ok ||
          !payload.ok ||
          !payload.session ||
          cancelled ||
          !allowRestoreRef.current ||
          userTouchedSourceRef.current ||
          source !== DEFAULT_SOURCE
        ) {
          if (storedSessionId && (!response.ok || !payload.ok || !payload.session) && typeof window !== "undefined") {
            window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
          }
          return;
        }
        applySession(payload.session as SessionState);
      } catch {
        /* ignore missing latest session */
      } finally {
        if (!cancelled) {
          setBusy(false);
          setBusyLabel(null);
        }
      }
    }

    void restoreLatestSession();
    return () => {
      cancelled = true;
    };
  }, [applySession, clientReady, source]);

  useEffect(() => {
    if (!sessionId) return;
    const interval = window.setInterval(async () => {
      try {
        const response = await fetch(`/api/splat-editor/sessions/${sessionId}`, { cache: "no-store" });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          return;
        }
        const nextSession = payload.session as SessionState;
        setSession((current) => (current && current.revisionHash === nextSession.revisionHash ? current : nextSession));
        if (lastRevisionRef.current && lastRevisionRef.current !== nextSession.revisionHash) {
          lastRevisionRef.current = nextSession.revisionHash;
          setViewerState("loading");
          setIframeKey((value) => value + 1);
          ignoreNextSogsStateRef.current = true;
        }
      } catch {
        /* ignore transient poll errors */
      }
    }, 3000);
    return () => window.clearInterval(interval);
  }, [sessionId]);

  async function importSource(event: FormEvent) {
    event.preventDefault();
    allowRestoreRef.current = false;
    userTouchedSourceRef.current = true;
    setBusy(true);
    setBusyLabel("Importing splat…");
    setError(null);
    setViewerState("loading");
    try {
      const response = await fetch("/api/splat-editor/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Import failed");
      }
      applySession(payload.session as SessionState);
    } catch (importError: any) {
      setViewerState("idle");
      setError(importError?.message || "Import failed");
    } finally {
      setBusy(false);
      setBusyLabel(null);
    }
  }

  async function importFile(file: File) {
    allowRestoreRef.current = false;
    userTouchedSourceRef.current = true;
    setBusy(true);
    setBusyLabel("Importing local splat…");
    setError(null);
    setViewerState("loading");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch("/api/splat-editor/import", {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Import failed");
      }
      applySession(payload.session as SessionState);
    } catch (importError: any) {
      setViewerState("idle");
      setError(importError?.message || "Import failed");
    } finally {
      setBusy(false);
      setBusyLabel(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  async function handleDroppedFile(fileList: FileList | null) {
    const file = fileList?.[0];
    if (!file) {
      return;
    }
    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith(".ply") && !lowerName.endsWith(".tar.gz")) {
      setError("Drop a .ply or .tar.gz artifact");
      return;
    }
    await importFile(file);
  }

  function onShellDragOver(event: DragEvent<HTMLElement>) {
    event.preventDefault();
    if (!busy) {
      setDropActive(true);
    }
  }

  function onShellDragLeave(event: DragEvent<HTMLElement>) {
    if (event.currentTarget === event.target) {
      setDropActive(false);
    }
  }

  async function onShellDrop(event: DragEvent<HTMLElement>) {
    event.preventDefault();
    setDropActive(false);
    await handleDroppedFile(event.dataTransfer.files);
  }

  useEffect(() => {
    if (!session || viewerState !== "ready") {
      return;
    }
    applySceneToViewer(transform);
  }, [applySceneToViewer, session, transform, viewerState]);

  const exportHref = session ? `/api/splat-editor/sessions/${session.sessionId}/export` : null;

  function setTransformAxis(kind: "position" | "rotation", axisIndex: 0 | 1 | 2, value: string) {
    const nextValue = Number(value);
    setTransform((current) => {
      const next = {
        position: [...current.position] as [number, number, number],
        rotation: [...current.rotation] as [number, number, number],
      };
      next[kind][axisIndex] = Number.isFinite(nextValue) ? nextValue : 0;
      return next;
    });
  }

  async function copySettings() {
    const text = JSON.stringify(
      {
        position: transform.position,
        rotation: transform.rotation,
        scale: DEFAULT_SCENE.scale,
        fov: DEFAULT_SCENE.fov,
      },
      null,
      2,
    );
    try {
      await navigator.clipboard.writeText(text);
      setCopyFeedback("Copied");
    } catch {
      setCopyFeedback("Copy failed");
    }
    window.setTimeout(() => setCopyFeedback(null), 1500);
  }

  return (
    <main
      className={`splat-editor-shell${dropActive ? " splat-editor-shell--drop-active" : ""}`}
      onDragOver={onShellDragOver}
      onDragLeave={onShellDragLeave}
      onDrop={onShellDrop}
    >
      {viewerSrc ? (
        <iframe
          key={iframeKey}
          ref={iframeRef}
          src={viewerSrc}
          title="splat-editor-viewer"
          className="splat-editor-iframe"
          allow="xr-spatial-tracking"
        />
      ) : (
        <div className="splat-editor-empty" aria-hidden />
      )}

      <section className="splat-editor-panel">
        <form className="splat-editor-form" onSubmit={importSource}>
          <input
            ref={fileInputRef}
            type="file"
            className="splat-editor-file-input"
            onChange={(event) => {
              void handleDroppedFile(event.target.files);
            }}
          />
          <div className="splat-editor-row">
            <input
              data-testid="splat-source-input"
              id="splat-source-input"
              type="text"
              value={source}
              onFocus={() => {
                allowRestoreRef.current = false;
                userTouchedSourceRef.current = true;
              }}
              onChange={(event) => {
                allowRestoreRef.current = false;
                userTouchedSourceRef.current = true;
                setSource(event.target.value);
              }}
              placeholder="s3://…/model.tar.gz or …/splat.ply"
              spellCheck={false}
            />
            <button data-testid="splat-import-button" type="submit" disabled={busy || !source.trim() || !clientReady}>
              Import
            </button>
            <button
              type="button"
              className="splat-editor-browse-button"
              onClick={() => fileInputRef.current?.click()}
              disabled={busy || !clientReady}
            >
              Drop / Browse
            </button>
            {exportHref ? (
              <a data-testid="splat-export-link" className="splat-editor-export-link" href={exportHref}>
                Export
              </a>
              ) : null}
          </div>
        </form>

        <div className="splat-editor-drop-hint">Drop `model.tar.gz` or `splat.ply` anywhere</div>

        <div className="splat-editor-status-row" data-testid="splat-status-grid">
          <strong data-testid="splat-status-text">{busyLabel || viewerState}</strong>
          {busy ? <span className="splat-editor-spinner" aria-label="Importing" /> : null}
          <span className="splat-editor-dim" data-testid="splat-viewer-state">
            {viewerState}
          </span>
        </div>

        {error ? <p className="splat-editor-error">{error}</p> : null}

        <div className="splat-editor-card">
          <div className="splat-editor-card-title">Transform</div>
          <div className="splat-editor-transform-group">
            <div className="splat-editor-transform-label">Position</div>
            <div className="splat-editor-transform-grid">
              {(["X", "Y", "Z"] as const).map((axis, index) => (
                <label key={`position-${axis}`} className="splat-editor-transform-field">
                  <span>{axis}</span>
                  <input
                    type="number"
                    step="0.01"
                    value={transform.position[index]}
                    onChange={(event) => setTransformAxis("position", index as 0 | 1 | 2, event.target.value)}
                  />
                </label>
              ))}
            </div>
          </div>
          <div className="splat-editor-transform-group">
            <div className="splat-editor-transform-label">Rotation</div>
            <div className="splat-editor-transform-grid">
              {(["X", "Y", "Z"] as const).map((axis, index) => (
                <label key={`rotation-${axis}`} className="splat-editor-transform-field">
                  <span>{axis}</span>
                  <input
                    type="number"
                    step="0.1"
                    value={transform.rotation[index]}
                    onChange={(event) => setTransformAxis("rotation", index as 0 | 1 | 2, event.target.value)}
                  />
                </label>
              ))}
            </div>
          </div>
          <div className="splat-editor-actions">
            <button type="button" className="splat-editor-copy-button" onClick={copySettings}>
              Copy Settings
            </button>
            {copyFeedback ? <span className="splat-editor-dim">{copyFeedback}</span> : null}
          </div>
        </div>

        {session ? (
          <div className="splat-editor-session-strip" data-testid="splat-session-metadata">
            <span data-testid="splat-session-id">{session.sessionId}</span>
            <span data-testid="splat-artifact-type">{session.sourceArtifactType}</span>
            <span data-testid="splat-vertex-count">{session.vertexCount.toLocaleString()}</span>
            <span data-testid="splat-revision-hash">{session.revisionHash}</span>
            <code data-testid="splat-working-ply-path">{session.workingPlyPath}</code>
            <span data-testid="splat-export-name">{session.exportTargetName}</span>
          </div>
        ) : null}
      </section>
      {dropActive ? <div className="splat-editor-drop-overlay">Drop local splat</div> : null}
    </main>
  );
}
