"use client";

import { useEffect, useRef, useState } from "react";
import {
  CANYON_BORDER_BY_NAME,
  CANYON_VISTA_BORDER_LINES,
} from "../../lib/canyon-vista/canyonVistaOverlays";
import {
  createOverlayPerspectiveCamera,
  projectWorldToScreen,
  syncOverlayCamera,
  type CameraPose,
} from "../../lib/canyon-vista/worldProjection";

type Props = {
  enabled: boolean;
  poseRef: React.MutableRefObject<CameraPose | null>;
  containerRef: React.RefObject<HTMLDivElement | null>;
};

type LineSeg = { x1: number; y1: number; x2: number; y2: number; visible: boolean };

export function LotLinesOverlay({ enabled, poseRef, containerRef }: Props) {
  const cameraRef = useRef(createOverlayPerspectiveCamera());
  const [pack, setPack] = useState<{ w: number; h: number; lines: LineSeg[] }>({ w: 0, h: 0, lines: [] });

  useEffect(() => {
    if (!enabled) {
      setPack({ w: 0, h: 0, lines: [] });
      return;
    }
    let raf = 0;
    const tick = () => {
      const el = containerRef.current;
      const pose = poseRef.current;
      if (el && pose) {
        const w = el.clientWidth;
        const h = el.clientHeight;
        const cam = cameraRef.current;
        syncOverlayCamera(cam, pose, w, h);
        const lines: LineSeg[] = [];
        for (const seg of CANYON_VISTA_BORDER_LINES) {
          const a = CANYON_BORDER_BY_NAME.get(seg.start);
          const b = CANYON_BORDER_BY_NAME.get(seg.end);
          if (!a || !b) continue;
          const pa = projectWorldToScreen(a.position, cam, w, h);
          const pb = projectWorldToScreen(b.position, cam, w, h);
          lines.push({
            x1: pa.x,
            y1: pa.y,
            x2: pb.x,
            y2: pb.y,
            visible: pa.visible && pb.visible,
          });
        }
        setPack({ w, h, lines });
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [enabled, poseRef, containerRef]);

  if (!enabled || pack.w <= 0 || pack.h <= 0) {
    return null;
  }

  return (
    <svg className="lot-lines-svg" width={pack.w} height={pack.h} viewBox={`0 0 ${pack.w} ${pack.h}`} aria-hidden>
      {pack.lines.map((ln, i) =>
        ln.visible ? (
          <line
            key={i}
            x1={ln.x1}
            y1={ln.y1}
            x2={ln.x2}
            y2={ln.y2}
            stroke="rgba(255,255,255,0.55)"
            strokeWidth={1.5}
          />
        ) : null,
      )}
    </svg>
  );
}
