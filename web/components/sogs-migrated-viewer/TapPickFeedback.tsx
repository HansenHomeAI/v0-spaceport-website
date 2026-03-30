"use client";

import { useEffect, useState } from "react";

type Props = {
  /** Screen coordinates (CSS pixels, viewport) */
  screen: { x: number; y: number } | null;
  /** Fade out after this many ms */
  durationMs?: number;
};

/**
 * Brief ring at double-tap / pick focus (Canyon-Vista #tap-focus-feedback style).
 */
export function TapPickFeedback({ screen, durationMs = 520 }: Props) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!screen) {
      setVisible(false);
      return;
    }
    setVisible(true);
    const t = window.setTimeout(() => setVisible(false), durationMs);
    return () => clearTimeout(t);
  }, [screen, durationMs]);

  if (!screen || !visible) {
    return null;
  }

  return (
    <div
      className="sogs-tap-pick-feedback"
      style={{ left: screen.x, top: screen.y }}
      aria-hidden
    />
  );
}
