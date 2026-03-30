"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { canyonAssetUrl, type TapDotConfig } from "../../lib/canyon-vista/canyonVistaOverlays";

const CLOSE_ICON =
  "https://raw.githubusercontent.com/HansenHomeAI/FigmaSVGButtons/main/Close2IconDefault.svg";

type Props = {
  dot: TapDotConfig | null;
  onClose: () => void;
};

/**
 * Canyon-Vista tapdot popup: centered card, bottom caption gradient, edge arrows, dots, spinner, image fade.
 */
export function CanyonPhotoModal({ dot, onClose }: Props) {
  const [idx, setIdx] = useState(0);
  const [visible, setVisible] = useState(false);
  const [spinner, setSpinner] = useState(false);
  const [imgFade, setImgFade] = useState(false);
  const swipeRef = useRef<{ x: number } | null>(null);

  useEffect(() => {
    setIdx(0);
    setVisible(false);
    setSpinner(false);
    setImgFade(false);
    if (!dot) return;
    setSpinner(true);
    const id = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(id);
  }, [dot]);

  useEffect(() => {
    if (!dot) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dot, onClose]);

  const urls = useMemo(() => (dot ? dot.photos.map(canyonAssetUrl) : []), [dot]);
  const src = urls[idx] ?? urls[0];
  const multi = urls.length > 1;

  const goTo = useCallback(
    (nextIdx: number) => {
      if (!urls.length) return;
      const i = ((nextIdx % urls.length) + urls.length) % urls.length;
      if (i === idx) return;
      setIdx(i);
      setImgFade(true);
      setSpinner(true);
    },
    [idx, urls],
  );

  const nav = useCallback(
    (dir: number) => {
      goTo(idx + dir);
    },
    [goTo, idx],
  );

  const onImgLoad = useCallback(() => {
    setSpinner(false);
    setImgFade(false);
  }, []);

  const onImgError = useCallback(() => {
    setSpinner(false);
    setImgFade(false);
  }, []);

  if (!dot) {
    return null;
  }

  return (
    <div className="tapdot-popup-root" aria-hidden={!visible}>
      <button type="button" className="tapdot-popup-backdrop" onClick={onClose} aria-label="Close" />
      <div
        className={`tapdot-popup ${visible ? "show" : ""}`}
        role="dialog"
        aria-modal
        aria-labelledby="tapdot-popup-caption"
        onTouchStart={(e) => {
          if (!multi || e.touches.length !== 1) return;
          swipeRef.current = { x: e.touches[0].clientX };
        }}
        onTouchEnd={(e) => {
          if (!multi || !swipeRef.current || e.changedTouches.length !== 1) return;
          const delta = e.changedTouches[0].clientX - swipeRef.current.x;
          swipeRef.current = null;
          if (delta < -50) nav(1);
          else if (delta > 50) nav(-1);
        }}
      >
        <div className="tapdot-popup-content">
          <div className="tapdot-photo-wrap">
            <div className={`tapdot-photo-spinner ${spinner ? "visible" : ""}`} aria-hidden />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              id="tapdotPopupPhoto"
              src={src}
              alt=""
              className={`tapdot-photo ${imgFade ? "fade" : ""}`}
              draggable={false}
              onLoad={onImgLoad}
              onError={onImgError}
              onClick={(e) => {
                e.stopPropagation();
                if (multi) nav(1);
              }}
            />
          </div>
          {multi ? (
            <div className="tapdot-carousel-nav visible">
              <button
                type="button"
                id="tapdotCarouselPrev"
                className="tapdot-carousel-arrow"
                aria-label="Previous photo"
                onClick={(e) => {
                  e.stopPropagation();
                  nav(-1);
                }}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path d="M15 18l-6-6 6-6" />
                </svg>
              </button>
              <button
                type="button"
                id="tapdotCarouselNext"
                className="tapdot-carousel-arrow"
                aria-label="Next photo"
                onClick={(e) => {
                  e.stopPropagation();
                  nav(1);
                }}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path d="M9 18l6-6-6-6" />
                </svg>
              </button>
            </div>
          ) : null}
        </div>

        <button
          type="button"
          id="tapdotPopupClose"
          className="tapdot-popup-close"
          aria-label="Close"
          onClick={onClose}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={CLOSE_ICON} alt="" width={21} height={21} draggable={false} />
        </button>

        <div className="tapdot-caption-overlay">
          <div className="tapdot-caption-gradient" aria-hidden />
          <div className="tapdot-caption-wrap">
            <p id="tapdot-popup-caption" className="tapdot-caption">
              {dot.caption}
            </p>
            {multi ? (
              <div className="tapdot-carousel-dots-wrap">
                <div id="tapdotCarouselDots" className="tapdot-carousel-dots">
                  {urls.map((_, i) => (
                    <button
                      key={`tapdot-dot-${i}`}
                      type="button"
                      data-index={i}
                      className={`tapdot-carousel-dot ${i === idx ? "active" : ""}`}
                      aria-label={`Photo ${i + 1} of ${urls.length}`}
                      aria-current={i === idx}
                      onClick={(e) => {
                        e.stopPropagation();
                        goTo(i);
                      }}
                    />
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
