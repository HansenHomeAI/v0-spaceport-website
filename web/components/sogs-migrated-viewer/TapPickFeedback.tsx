"use client";

import { useEffect, useState } from "react";

type Props = {
  /** Viewport coordinates (parent page) + stamp so repeated taps re-run the ring animation */
  screen: { x: number; y: number; t: number } | null;
  /** Hold visible then fade (Canyon-Vista tap-focus-feedback timing) */
  durationMs?: number;
};

/**
 * Ring at tap-to-focus screen position (HansenHomeAI/Canyon-Vista #tap-focus-feedback).
 */
export function TapPickFeedback({ screen, durationMs = 720 }: Props) {
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
      key={screen.t}
      className="sogs-tap-pick-feedback"
      style={{ left: screen.x, top: screen.y }}
      aria-hidden
    />
  );
}
