"use client";

import { useCallback, useState } from "react";
import {
  removeCheckpointAt,
  serializePathPayload,
  setCheckpointDuration,
  setPathEnabled,
  setPathLoop,
  setPathSpeed,
} from "../../lib/canyon-vista/pathEditing";
import { getPathSegmentCount } from "../../lib/canyon-vista/pathAnimation";
import type { PathAnimationState } from "../../lib/canyon-vista/types";

type Props = {
  pathStateRef: React.MutableRefObject<PathAnimationState>;
  pathVersion: number;
  bumpPath: () => void;
  disabled: boolean;
  onSeekCheckpoint: (checkpointIndex: number) => void;
  onAddFromCurrentView: () => void;
};

export function AnimationPathPanel({
  pathStateRef,
  pathVersion,
  bumpPath,
  disabled,
  onSeekCheckpoint,
  onAddFromCurrentView,
}: Props) {
  const [open, setOpen] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const state = pathStateRef.current;
  const checkpoints = state.checkpoints;
  const segCount = getPathSegmentCount(state);

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
    <div className="animation-path-panel-wrap" data-testid="animation-path-panel">
      <button
        type="button"
        className="sogs-migrated-btn animation-path-toggle"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        disabled={disabled}
      >
        Path editor
      </button>
      {open ? (
        <div className="animation-path-panel" role="region" aria-label="Camera path editor">
          <div className="animation-path-row">
            <label>
              <input
                type="checkbox"
                checked={state.enabled}
                onChange={(e) => {
                  setPathEnabled(pathStateRef.current, e.target.checked);
                  bumpPath();
                }}
              />
              Enabled
            </label>
            <label>
              <input
                type="checkbox"
                checked={state.loop}
                onChange={(e) => {
                  setPathLoop(pathStateRef.current, e.target.checked);
                  bumpPath();
                }}
              />
              Loop
            </label>
            <label className="animation-path-speed">
              Speed{" "}
              <input
                type="number"
                min={0.1}
                step={0.1}
                value={state.speed}
                onChange={(e) => {
                  setPathSpeed(pathStateRef.current, parseFloat(e.target.value) || 1);
                  bumpPath();
                }}
              />
            </label>
          </div>
          <p className="animation-path-hint">
            Segment {state.segmentIndex + 1} / {Math.max(1, segCount)} · {checkpoints.length} checkpoints
          </p>
          <ul className="animation-path-list" data-testid="animation-path-checkpoints">
            {checkpoints.map((cp, i) => (
              <li key={`cp-${pathVersion}-${i}`}>
                <span className="animation-path-idx">#{i + 1}</span>
                <label className="animation-path-dur">
                  s
                  <input
                    type="number"
                    min={0.1}
                    step={0.5}
                    value={cp.duration}
                    onChange={(e) => {
                      setCheckpointDuration(pathStateRef.current, i, parseFloat(e.target.value) || 5);
                      bumpPath();
                    }}
                  />
                </label>
                <button
                  type="button"
                  className="sogs-migrated-btn animation-path-mini"
                  onClick={() => onSeekCheckpoint(i)}
                >
                  Go
                </button>
                <button
                  type="button"
                  className="sogs-migrated-btn animation-path-mini"
                  onClick={() => {
                    if (removeCheckpointAt(pathStateRef.current, i)) bumpPath();
                  }}
                  disabled={checkpoints.length <= 2}
                >
                  Del
                </button>
              </li>
            ))}
          </ul>
          <div className="animation-path-actions">
            <button type="button" className="sogs-migrated-btn" onClick={onAddFromCurrentView}>
              Add checkpoint from view
            </button>
            <button type="button" className="sogs-migrated-btn" onClick={exportJson}>
              Copy path JSON
            </button>
            {copyFeedback ? <span className="animation-path-copy">{copyFeedback}</span> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
