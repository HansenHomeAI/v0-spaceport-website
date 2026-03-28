"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import "./splat-editor.css";

const VIEWER_BASE = "/supersplat-viewer/index.html";
const DEFAULT_SOURCE =
  "s3://spaceport-ml-processing/3dgs/manual-3dgs-1774642514/ml-job-20260327-201514-manual-3-3dgs/output/model.tar.gz";

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

function formatBytes(bytes: number) {
  if (!Number.isFinite(bytes)) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(unitIndex === 0 ? 0 : 2)} ${units[unitIndex]}`;
}

export default function SplatEditor() {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const lastRevisionRef = useRef<string | null>(null);

  const [source, setSource] = useState(DEFAULT_SOURCE);
  const [session, setSession] = useState<SessionState | null>(null);
  const [iframeKey, setIframeKey] = useState(0);
  const [viewerState, setViewerState] = useState<"idle" | "loading" | "ready">("idle");
  const [status, setStatus] = useState("No local session yet.");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [clientReady, setClientReady] = useState(false);

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

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.data?.type === "supersplat:firstFrame" && event.source === iframeRef.current?.contentWindow) {
        setViewerState("ready");
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  useEffect(() => {
    setClientReady(true);
  }, []);

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
          setStatus(`Detected local file change. Reloaded revision ${nextSession.revisionHash.slice(0, 12)}.`);
        }
      } catch {
        /* ignore transient poll errors */
      }
    }, 3000);
    return () => window.clearInterval(interval);
  }, [sessionId]);

  async function importSource(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setStatus("Downloading and staging 3DGS artifact locally…");
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
      setSession(payload.session as SessionState);
      lastRevisionRef.current = payload.session.revisionHash;
      setIframeKey((value) => value + 1);
      setStatus("Local staged copy ready. External edits can now target the working PLY path below.");
    } catch (importError: any) {
      setViewerState("idle");
      setError(importError?.message || "Import failed");
      setStatus("Import failed.");
    } finally {
      setBusy(false);
    }
  }

  const commandExample = session
    ? `node web/scripts/edit-3dgs-ply.mjs --input "${session.workingPlyPath}" --y-gt 2.5`
    : `node web/scripts/edit-3dgs-ply.mjs --input "/absolute/path/to/staged/splat.ply" --y-gt 2.5`;

  return (
    <main className="splat-editor-shell">
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
        <div className="splat-editor-heading">
          <h1>Local 3DGS Splat Editor</h1>
          <p>Import once from S3 or HTTPS, stage locally, edit the staged PLY in place, and export when done.</p>
        </div>

        <form className="splat-editor-form" onSubmit={importSource}>
          <label htmlFor="splat-source-input">3DGS source artifact</label>
          <div className="splat-editor-row">
            <input
              data-testid="splat-source-input"
              id="splat-source-input"
              type="text"
              value={source}
              onChange={(event) => setSource(event.target.value)}
              placeholder="s3://…/model.tar.gz or …/splat.ply"
              spellCheck={false}
            />
            <button data-testid="splat-import-button" type="submit" disabled={busy || !source.trim() || !clientReady}>
              {busy ? "Importing…" : "Import"}
            </button>
          </div>
        </form>

        <div className="splat-editor-status-grid" data-testid="splat-status-grid">
          <div>
            <span>Status</span>
            <strong data-testid="splat-status-text">{status}</strong>
          </div>
          <div>
            <span>Viewer</span>
            <strong data-testid="splat-viewer-state">{viewerState}</strong>
          </div>
          <div>
            <span>Auto-refresh</span>
            <strong>{session?.autoRefreshEnabled ? "Enabled" : "Waiting for session"}</strong>
          </div>
        </div>

        {error ? <p className="splat-editor-error">{error}</p> : null}

        <div className="splat-editor-card">
          <div className="splat-editor-card-title">Session metadata</div>
          {session ? (
            <dl className="splat-editor-metadata" data-testid="splat-session-metadata">
              <div>
                <dt>Session id</dt>
                <dd data-testid="splat-session-id">{session.sessionId}</dd>
              </div>
              <div>
                <dt>Artifact type</dt>
                <dd data-testid="splat-artifact-type">{session.sourceArtifactType}</dd>
              </div>
              <div>
                <dt>Vertices</dt>
                <dd data-testid="splat-vertex-count">{session.vertexCount.toLocaleString()}</dd>
              </div>
              <div>
                <dt>Revision hash</dt>
                <dd data-testid="splat-revision-hash">{session.revisionHash}</dd>
              </div>
              <div>
                <dt>Last modified</dt>
                <dd>{new Date(session.lastModifiedMs).toLocaleString()}</dd>
              </div>
              <div>
                <dt>Working size</dt>
                <dd>{formatBytes(session.sizeBytes)}</dd>
              </div>
              <div className="splat-editor-metadata-wide">
                <dt>Remote source</dt>
                <dd>{session.sourceUrl}</dd>
              </div>
              <div className="splat-editor-metadata-wide">
                <dt>Local source artifact path</dt>
                <dd>{session.sourceArtifactPath}</dd>
              </div>
              <div className="splat-editor-metadata-wide">
                <dt>Working PLY path</dt>
                <dd data-testid="splat-working-ply-path">{session.workingPlyPath}</dd>
              </div>
              <div className="splat-editor-metadata-wide">
                <dt>Export target</dt>
                <dd data-testid="splat-export-name">{session.exportTargetName}</dd>
              </div>
              {session.trainingMetadataPath ? (
                <div className="splat-editor-metadata-wide">
                  <dt>Training metadata path</dt>
                  <dd>{session.trainingMetadataPath}</dd>
                </div>
              ) : null}
            </dl>
          ) : (
            <p className="splat-editor-placeholder">Import an artifact to create a local editing session.</p>
          )}
        </div>

        <div className="splat-editor-card">
          <div className="splat-editor-card-title">External edit command</div>
          <p className="splat-editor-hint">
            The viewer only watches the staged local file. Run the CLI against the working PLY path and this page will
            reload the preview when the file changes.
          </p>
          <pre>{commandExample}</pre>
        </div>

        <div className="splat-editor-card">
          <div className="splat-editor-card-title">Supported delete rules</div>
          <ul>
            <li>
              <code>--y-gt</code> and <code>--y-lt</code>
            </li>
            <li>
              <code>--radius-gt</code> and <code>--radius-lt</code>
            </li>
            <li>
              <code>--bounds minX,maxX,minY,maxY,minZ,maxZ</code>
            </li>
          </ul>
          {session ? (
            <a
              data-testid="splat-export-link"
              className="splat-editor-export-link"
              href={`/api/splat-editor/sessions/${session.sessionId}/export`}
            >
              Export Splat
            </a>
          ) : null}
        </div>
      </section>
    </main>
  );
}
