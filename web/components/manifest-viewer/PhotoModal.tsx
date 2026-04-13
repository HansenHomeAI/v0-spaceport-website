"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ViewerTapDotManifest } from "../../lib/manifest-viewer/manifest";

const CLOSE_ICON =
  "https://raw.githubusercontent.com/HansenHomeAI/FigmaSVGButtons/main/Close2IconDefault.svg";

type Props = {
  dot: ViewerTapDotManifest | null;
  onClose: () => void;
};

export function PhotoModal({ dot, onClose }: Props) {
  const [index, setIndex] = useState(0);
  const [visible, setVisible] = useState(false);
  const [spinner, setSpinner] = useState(false);
  const [imageFade, setImageFade] = useState(false);
  const swipeRef = useRef<{ x: number } | null>(null);

  useEffect(() => {
    setIndex(0);
    setVisible(false);
    setSpinner(false);
    setImageFade(false);
    if (!dot) return;
    setSpinner(true);
    const id = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(id);
  }, [dot]);

  useEffect(() => {
    if (!dot) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dot, onClose]);

  const urls = useMemo(() => dot?.photos ?? [], [dot]);
  const src = urls[index] ?? urls[0];
  const multi = urls.length > 1;

  const goTo = useCallback(
    (nextIndex: number) => {
      if (!urls.length) return;
      const wrappedIndex = (nextIndex % urls.length + urls.length) % urls.length;
      if (wrappedIndex === index) return;
      setIndex(wrappedIndex);
      setImageFade(true);
      setSpinner(true);
    },
    [index, urls],
  );

  const navigate = useCallback((direction: number) => goTo(index + direction), [goTo, index]);

  const onImageLoad = useCallback(() => {
    setSpinner(false);
    setImageFade(false);
  }, []);

  const onImageError = useCallback(() => {
    setSpinner(false);
    setImageFade(false);
  }, []);

  if (!dot) return null;

  return (
    <div className="tapdot-popup-root" aria-hidden={!visible}>
      <button type="button" className="tapdot-popup-backdrop" onClick={onClose} aria-label="Close" />
      <div
        className={`tapdot-popup ${visible ? "show" : ""}`}
        role="dialog"
        aria-modal
        aria-labelledby="tapdot-popup-caption"
        onTouchStart={(event) => {
          if (!multi || event.touches.length !== 1) return;
          swipeRef.current = { x: event.touches[0].clientX };
        }}
        onTouchEnd={(event) => {
          if (!multi || !swipeRef.current || event.changedTouches.length !== 1) return;
          const delta = event.changedTouches[0].clientX - swipeRef.current.x;
          swipeRef.current = null;
          if (delta < -50) navigate(1);
          else if (delta > 50) navigate(-1);
        }}
      >
        <div className="tapdot-popup-content">
          <div className="tapdot-photo-wrap">
            <div className={`tapdot-photo-spinner ${spinner ? "visible" : ""}`} aria-hidden />
            {src ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                id="tapdotPopupPhoto"
                src={src}
                alt=""
                className={`tapdot-photo ${imageFade ? "fade" : ""}`}
                draggable={false}
                onLoad={onImageLoad}
                onError={onImageError}
                onClick={(event) => {
                  event.stopPropagation();
                  if (multi) navigate(1);
                }}
              />
            ) : null}
          </div>
          <div id="tapdot-popup-caption" className="tapdot-popup-caption">
            {dot.caption}
          </div>
          {multi ? (
            <div className="tapdot-popup-dots" role="tablist" aria-label="Photo selector">
              {urls.map((url, urlIndex) => (
                <button
                  key={url}
                  type="button"
                  className={`tapdot-popup-dot ${urlIndex === index ? "active" : ""}`}
                  aria-label={`Go to photo ${urlIndex + 1}`}
                  aria-pressed={urlIndex === index}
                  onClick={() => goTo(urlIndex)}
                />
              ))}
            </div>
          ) : null}
        </div>
        <button type="button" className="tapdot-popup-close" onClick={onClose} aria-label="Close">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={CLOSE_ICON} alt="" draggable={false} width={21} height={21} />
        </button>
      </div>
    </div>
  );
}
