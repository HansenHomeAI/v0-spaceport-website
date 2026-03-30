"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const DETAILS_ICON =
  "https://raw.githubusercontent.com/HansenHomeAI/FigmaSVGButtons/main/DetailsIconDefault.svg";
const CLOSE_ICON =
  "https://raw.githubusercontent.com/HansenHomeAI/FigmaSVGButtons/main/Close2IconDefault.svg";
const FULLSCREEN_ICON =
  "https://raw.githubusercontent.com/HansenHomeAI/FigmaSVGButtons/main/FullScreenIconDefault.svg";
const MINIMIZE_ICON =
  "https://raw.githubusercontent.com/HansenHomeAI/FigmaSVGButtons/main/MinimizeIconDefault.svg";

type MenuButtonProps = {
  disabled?: boolean;
  open: boolean;
  onToggle: () => void;
};

/**
 * Bottom-menu control that toggles the glass details panel (Canyon-Vista #detailsButton).
 * Icon URLs match HansenHomeAI/Canyon-Vista index.html.
 */
export function CanyonDetailsMenuButton({ disabled, open, onToggle }: MenuButtonProps) {
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

type PanelProps = {
  open: boolean;
  onClose: () => void;
};

/**
 * Full-screen glass panel with marketing copy (same substance as Canyon-Vista index.html).
 * All user-facing copy lives in this file only.
 */
export function CanyonDetailsPanel({ open, onClose }: PanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    const onFs = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onFs);
    return () => document.removeEventListener("fullscreenchange", onFs);
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
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <div
      id="detailsBox"
      className={`details-box ${open ? "show" : ""}`}
      aria-hidden={!open}
      role="dialog"
      aria-modal
      aria-labelledby="canyon-details-heading"
    >
      <div
        ref={scrollRef}
        id="detailsContent"
        className="details-content"
        tabIndex={open ? 0 : -1}
      >
        <div className="details-inner">
          <button
            type="button"
            id="fullscreenButton"
            className="details-fullscreen-button"
            aria-label={fullscreen ? "Exit fullscreen" : "Enter fullscreen"}
            onClick={onFullscreenClick}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={fullscreen ? MINIMIZE_ICON : FULLSCREEN_ICON} alt="" draggable={false} width={21} height={21} />
          </button>
          <h1 id="canyon-details-heading">Canyon Vista</h1>
          <p>
            Canyon Vista is a contemporary apartment community in Draper, Utah, just south of Sandy at the Point of the
            Mountain. Positioned for quick access to I-15, nearby TRAX, and the Silicon Slopes corridor, the property
            combines commuter convenience with Wasatch mountain views and a more residential setting. The community is
            centered on everyday livability, with modern interiors, in-home laundry, a resort-style pool and spa, fitness
            and yoga spaces, pickleball, play areas, and shared lounge amenities that support both workday routine and
            weekend downtime.
          </p>
          <p className="legal-disclaimer">
            Information and imagery are representative; amenities, finishes, and availability may vary. Not an offer to
            lease or sell; see leasing office for current terms.
          </p>
        </div>
      </div>
    </div>
  );
}
