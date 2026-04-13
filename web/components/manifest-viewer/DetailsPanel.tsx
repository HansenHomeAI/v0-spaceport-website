"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ViewerDetailsManifest } from "../../lib/manifest-viewer/manifest";

const DETAILS_ICON =
  "https://raw.githubusercontent.com/HansenHomeAI/FigmaSVGButtons/main/DetailsIconDefault.svg";
const CLOSE_ICON =
  "https://raw.githubusercontent.com/HansenHomeAI/FigmaSVGButtons/main/Close2IconDefault.svg";
const FULLSCREEN_ICON =
  "https://raw.githubusercontent.com/HansenHomeAI/FigmaSVGButtons/main/FullScreenIconDefault.svg";
const MINIMIZE_ICON =
  "https://raw.githubusercontent.com/HansenHomeAI/FigmaSVGButtons/main/MinimizeIconDefault.svg";

type DetailsMenuButtonProps = {
  disabled: boolean;
  open: boolean;
  onToggle: () => void;
};

export function DetailsMenuButton({ disabled, open, onToggle }: DetailsMenuButtonProps) {
  return (
    <button
      type="button"
      id="detailsButton"
      className={`menu-button ${open ? "active" : ""}`}
      aria-expanded={open}
      aria-label={open ? "Close details" : "Open details"}
      disabled={disabled}
      onClick={onToggle}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={open ? CLOSE_ICON : DETAILS_ICON} alt="" draggable={false} width={21} height={21} />
    </button>
  );
}

type DetailsPanelProps = {
  details: ViewerDetailsManifest | null | undefined;
  open: boolean;
  onClose: () => void;
};

export function DetailsPanel({ details, open, onClose }: DetailsPanelProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    const onFullscreenChange = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", onFullscreenChange);
  }, []);

  const onFullscreenClick = useCallback(async () => {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await document.documentElement.requestFullscreen();
      }
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, open]);

  if (!details) {
    return null;
  }

  return (
    <div
      id="detailsBox"
      className={`details-box ${open ? "show" : ""}`}
      aria-hidden={!open}
      role="dialog"
      aria-modal
      aria-labelledby="canyon-details-heading"
    >
      <div ref={scrollRef} id="detailsContent" className="details-content" tabIndex={open ? 0 : -1}>
        <div className="details-inner">
          <button
            type="button"
            id="fullscreenButton"
            className="details-fullscreen-button"
            aria-label={fullscreen ? "Exit fullscreen" : "Enter fullscreen"}
            onClick={onFullscreenClick}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={fullscreen ? MINIMIZE_ICON : FULLSCREEN_ICON}
              alt=""
              draggable={false}
              width={21}
              height={21}
            />
          </button>
          <h1 id="canyon-details-heading">{details.title}</h1>
          {details.paragraphs.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </div>
      </div>
    </div>
  );
}
