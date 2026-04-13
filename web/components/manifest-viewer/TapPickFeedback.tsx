"use client";

import { useEffect, useState } from "react";

type PickFeedbackScreen = {
  x: number;
  y: number;
  t: number;
  ringSeq: number;
};

type Props = {
  screen: PickFeedbackScreen | null;
  durationMs?: number;
};

export function TapPickFeedback({ screen, durationMs = 720 }: Props) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!screen) {
      setVisible(false);
      return;
    }
    setVisible(true);
    const timer = window.setTimeout(() => setVisible(false), durationMs);
    return () => clearTimeout(timer);
  }, [durationMs, screen]);

  if (!screen || !visible) {
    return null;
  }

  return (
    <div className="sogs-tap-pick-feedback" style={{ left: screen.x, top: screen.y }} aria-hidden>
      {screen.t}
    </div>
  );
}
