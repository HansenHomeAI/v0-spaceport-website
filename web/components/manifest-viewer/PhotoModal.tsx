"use client";

import { useEffect, useState } from "react";
import type { ViewerTapDotManifest } from "../../lib/manifest-viewer/manifest";

type Props = {
  dot: ViewerTapDotManifest | null;
  onClose: () => void;
};

export function PhotoModal({ dot, onClose }: Props) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    setIndex(0);
  }, [dot]);

  useEffect(() => {
    if (!dot) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dot, onClose]);

  if (!dot) return null;

  const src = dot.photos[index] ?? dot.photos[0];

  return (
    <div className="canyon-photo-modal" role="dialog" aria-modal aria-labelledby="manifest-photo-title">
      <button type="button" className="canyon-photo-modal-backdrop" onClick={onClose} aria-label="Close" />
      <div className="canyon-photo-modal-panel">
        <div className="canyon-photo-modal-header">
          <h2 id="manifest-photo-title">{dot.caption}</h2>
          <button type="button" className="canyon-photo-modal-close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="canyon-photo-modal-body">
          {src ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={src} alt="" className="canyon-photo-modal-img" />
          ) : null}
        </div>
        {dot.photos.length > 1 ? (
          <div className="canyon-photo-modal-nav">
            <button type="button" onClick={() => setIndex((value) => (value - 1 + dot.photos.length) % dot.photos.length)} aria-label="Previous photo">
              ‹
            </button>
            <span>
              {index + 1} / {dot.photos.length}
            </span>
            <button type="button" onClick={() => setIndex((value) => (value + 1) % dot.photos.length)} aria-label="Next photo">
              ›
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
