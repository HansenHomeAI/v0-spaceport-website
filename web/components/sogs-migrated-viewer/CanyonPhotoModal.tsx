"use client";

import { useEffect, useState } from "react";
import { canyonAssetUrl, type TapDotConfig } from "../../lib/canyon-vista/canyonVistaOverlays";

type Props = {
  dot: TapDotConfig | null;
  onClose: () => void;
};

export function CanyonPhotoModal({ dot, onClose }: Props) {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    setIdx(0);
  }, [dot]);

  useEffect(() => {
    if (!dot) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dot, onClose]);

  if (!dot) {
    return null;
  }

  const urls = dot.photos.map(canyonAssetUrl);
  const src = urls[idx] ?? urls[0];

  return (
    <div className="canyon-photo-modal" role="dialog" aria-modal aria-labelledby="canyon-photo-title">
      <button type="button" className="canyon-photo-modal-backdrop" onClick={onClose} aria-label="Close" />
      <div className="canyon-photo-modal-panel">
        <div className="canyon-photo-modal-header">
          <h2 id="canyon-photo-title">{dot.caption}</h2>
          <button type="button" className="canyon-photo-modal-close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="canyon-photo-modal-body">
          {src ? (
            // eslint-disable-next-line @next/next/no-img-element -- remote Canyon-Vista assets
            <img src={src} alt="" className="canyon-photo-modal-img" />
          ) : null}
        </div>
        {urls.length > 1 ? (
          <div className="canyon-photo-modal-nav">
            <button
              type="button"
              onClick={() => setIdx((i) => (i - 1 + urls.length) % urls.length)}
              aria-label="Previous photo"
            >
              ‹
            </button>
            <span>
              {idx + 1} / {urls.length}
            </span>
            <button
              type="button"
              onClick={() => setIdx((i) => (i + 1) % urls.length)}
              aria-label="Next photo"
            >
              ›
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
