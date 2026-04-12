"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { CameraPose } from "../../lib/manifest-viewer/types";
import type { ViewerBorderDotManifest, ViewerBorderLineManifest } from "../../lib/manifest-viewer/manifest";
import {
  createOverlayPerspectiveCamera,
  projectWorldToScreen,
  syncOverlayCamera,
} from "../../lib/manifest-viewer/worldProjection";

type Props = {
  enabled: boolean;
  borderDots: ViewerBorderDotManifest[];
  borderLines: ViewerBorderLineManifest[];
  poseRef: React.MutableRefObject<CameraPose | null>;
  containerRef: React.RefObject<HTMLDivElement | null>;
};

type LineSegment = { x1: number; y1: number; x2: number; y2: number; visible: boolean };

export function LotLinesOverlay({ enabled, borderDots, borderLines, poseRef, containerRef }: Props) {
  const cameraRef = useRef(createOverlayPerspectiveCamera());
  const borderDotMap = useMemo(() => new Map(borderDots.map((dot) => [dot.name, dot])), [borderDots]);
  const [pack, setPack] = useState<{ width: number; height: number; lines: LineSegment[] }>({
    width: 0,
    height: 0,
    lines: [],
  });

  useEffect(() => {
    if (!enabled) {
      setPack({ width: 0, height: 0, lines: [] });
      return;
    }

    let raf = 0;
    const tick = () => {
      const element = containerRef.current;
      const pose = poseRef.current;
      if (element && pose) {
        const width = element.clientWidth;
        const height = element.clientHeight;
        const camera = cameraRef.current;
        syncOverlayCamera(camera, pose, width, height);
        const lines: LineSegment[] = [];
        for (const segment of borderLines) {
          const start = borderDotMap.get(segment.start);
          const end = borderDotMap.get(segment.end);
          if (!start || !end) continue;
          const projectedStart = projectWorldToScreen(start.position, camera, width, height);
          const projectedEnd = projectWorldToScreen(end.position, camera, width, height);
          lines.push({
            x1: projectedStart.x,
            y1: projectedStart.y,
            x2: projectedEnd.x,
            y2: projectedEnd.y,
            visible: projectedStart.visible && projectedEnd.visible,
          });
        }
        setPack({ width, height, lines });
      }
      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [borderDotMap, borderLines, containerRef, enabled, poseRef]);

  if (!enabled || pack.width <= 0 || pack.height <= 0) return null;

  return (
    <svg className="lot-lines-svg" width={pack.width} height={pack.height} viewBox={`0 0 ${pack.width} ${pack.height}`} aria-hidden>
      {pack.lines.map((line, index) =>
        line.visible ? (
          <line
            key={index}
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
            stroke="rgba(255,255,255,0.55)"
            strokeWidth={1.5}
          />
        ) : null,
      )}
    </svg>
  );
}
