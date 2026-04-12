"use client";

import { useCallback, useState } from "react";
import {
  appendCheckpoint,
  removeCheckpointAt,
  serializePathPayload,
  setCheckpointDuration,
  setPathEnabled,
  setPathLoop,
  setPathSpeed,
} from "../../lib/manifest-viewer/pathEditing";
import { getPathSegmentCount } from "../../lib/manifest-viewer/pathAnimation";
import type { PathAnimationState } from "../../lib/manifest-viewer/types";

type Props = {
  open: boolean;
  onClose: () => void;
  pathStateRef: React.MutableRefObject<PathAnimationState>;
  pathVersion: number;
  bumpPath: () => void;
  disabled: boolean;
  onSeekCheckpoint: (checkpointIndex: number) => void;
  onAddFromCurrentView: () => void;
  onPlayTour: () => void;
  onStopTour: () => void;
  pathPlaying: boolean;
};

export function AnimationPathPanel({
  open,
  onClose,
  pathStateRef,
  pathVersion,
  bumpPath,
  disabled,
  onSeekCheckpoint,
  onAddFromCurrentView,
  onPlayTour,
  onStopTour,
  pathPlaying,
}: Props) {
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const state = pathStateRef.current;
  const checkpoints = state.checkpoints;
  const segmentCount = getPathSegmentCount(state);

  const exportJson = useCallback(() => {
    const json = JSON.stringify(serializePathPayload(pathStateRef.current), null, 2);
    void navigator.clipboard.writeText(json).then(
      () => {
        setCopyFeedback("Copied");
        window.setTimeout(() => setCopyFeedback(null), 2000);
      },
      () => setCopyFeedback("Copy failed"),
    );
  }, [pathStateRef]);

  return (
    <div
      id="animationEditorPanel"
      className={`lot-editor-panel animation-editor-panel ${open ? "active" : ""}`}
      aria-live="polite"
      aria-hidden={!open}
      data-testid="animation-path-panel"
    >
      <div className="animation-editor-header">
        <div className="lot-editor-title">Path</div>
        <button type="button" id="animationEditorCloseButton" className="animation-editor-close" aria-label="Close" onClick={onClose}>
          ×
        </button>
      </div>
      <div className="lot-editor-status animation-editor-status-compact">
        {disabled ? "Loading…" : "Edit camera checkpoints"}
      </div>
      <div className="animation-editor-summary">
        Segment {state.segmentIndex + 1} / {Math.max(1, segmentCount)} · {checkpoints.length} checkpoints
      </div>
      <div className="animation-path-toggles-row">
        <label className="animation-path-inline-label">
          <input
            type="checkbox"
            checked={state.enabled}
            disabled={disabled}
            onChange={(event) => {
              setPathEnabled(pathStateRef.current, event.target.checked);
              bumpPath();
            }}
          />
          Enabled
        </label>
        <label className="animation-path-inline-label">
          <input
            type="checkbox"
            checked={state.loop}
            disabled={disabled}
            onChange={(event) => {
              setPathLoop(pathStateRef.current, event.target.checked);
              bumpPath();
            }}
          />
          Loop
        </label>
        <label className="animation-path-inline-label animation-path-speed">
          Speed
          <input
            type="number"
            min={0.1}
            step={0.1}
            value={state.speed}
            disabled={disabled}
            onChange={(event) => {
              setPathSpeed(pathStateRef.current, parseFloat(event.target.value) || 1);
              bumpPath();
            }}
          />
        </label>
      </div>
      <div className="animation-checkpoint-strip" data-testid="animation-path-checkpoints" aria-label="Camera checkpoints">
        {checkpoints.map((_, index) => (
          <div key={`cp-${pathVersion}-${index}`} className="animation-checkpoint-item">
            <button
              type="button"
              className={`animation-checkpoint-pill ${state.segmentIndex === index && pathPlaying ? "playing" : ""}`}
              onClick={() => onSeekCheckpoint(index)}
            >
              <span className="animation-checkpoint-pill-label">{index + 1}</span>
            </button>
            <div className="animation-checkpoint-hover-actions">
              <button type="button" onClick={() => onSeekCheckpoint(index)} title="Go">
                Go
              </button>
              <button
                type="button"
                className="animation-checkpoint-delete-btn"
                onClick={() => {
                  if (removeCheckpointAt(pathStateRef.current, index)) bumpPath();
                }}
                disabled={checkpoints.length <= 2}
                title="Delete"
              >
                ×
              </button>
            </div>
          </div>
        ))}
      </div>
      <div className="lot-editor-grid animation-path-durations-grid">
        {checkpoints.map((checkpoint, index) => (
          <div key={`duration-${pathVersion}-${index}`} className="lot-editor-field">
            <label htmlFor={`path-duration-${index}`}>#{index + 1} (s)</label>
            <input
              id={`path-duration-${index}`}
              type="number"
              min={0.1}
              step={0.5}
              value={checkpoint.duration}
              disabled={disabled}
              onChange={(event) => {
                setCheckpointDuration(pathStateRef.current, index, parseFloat(event.target.value) || 5);
                bumpPath();
              }}
            />
          </div>
        ))}
      </div>
      <div className="animation-editor-actions">
        <button
          type="button"
          className="lot-editor-action-btn animation-editor-btn-icon"
          aria-label="Capture checkpoint"
          title="Insert checkpoint from current view"
          disabled={disabled}
          onClick={onAddFromCurrentView}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <circle cx="12" cy="12" r="4" fill="currentColor" stroke="none" />
          </svg>
        </button>
        <button
          type="button"
          className="lot-editor-action-btn animation-editor-btn-icon"
          aria-label={pathPlaying ? "Pause path" : "Play path"}
          title={pathPlaying ? "Pause" : "Play"}
          disabled={disabled}
          onClick={() => (pathPlaying ? onStopTour() : onPlayTour())}
        >
          {pathPlaying ? (
            <svg className="icon-pause" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
              <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
            </svg>
          ) : (
            <svg className="icon-play" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </button>
        <button
          type="button"
          className="lot-editor-action-btn animation-editor-btn-icon"
          aria-label="Copy JSON"
          title="Copy path JSON"
          disabled={disabled}
          onClick={exportJson}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
        </button>
      </div>
      {copyFeedback ? <p className="animation-path-copy-feedback">{copyFeedback}</p> : null}
    </div>
  );
}
