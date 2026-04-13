"use client";

import { useEffect, useRef, useState } from "react";
import type { CameraPose } from "../../lib/manifest-viewer/types";
import type { ViewerTapDotManifest } from "../../lib/manifest-viewer/manifest";
import {
  createOverlayPerspectiveCamera,
  projectWorldToScreen,
  syncOverlayCamera,
} from "../../lib/manifest-viewer/worldProjection";

type ProjectedDot = {
  x: number;
  y: number;
  visible: boolean;
  caption: string;
  dot: ViewerTapDotManifest;
};

type Props = {
  enabled: boolean;
  tapDots: ViewerTapDotManifest[];
  poseRef: React.MutableRefObject<CameraPose | null>;
  containerRef: React.RefObject<HTMLDivElement | null>;
  onOpenPhotos: (dot: ViewerTapDotManifest) => void;
};

export function TapDotsOverlay({ enabled, tapDots, poseRef, containerRef, onOpenPhotos }: Props) {
  const cameraRef = useRef(createOverlayPerspectiveCamera());
  const [projected, setProjected] = useState<ProjectedDot[]>([]);

  useEffect(() => {
    if (!enabled) {
      setProjected([]);
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
        setProjected(
          tapDots.map((tapDot) => {
            const point = projectWorldToScreen(tapDot.position, camera, width, height);
            return { ...point, caption: tapDot.caption, dot: tapDot };
          }),
        );
      }
      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [containerRef, enabled, poseRef, tapDots]);

  if (!enabled) return null;

  return (
    <div className="tapdot-layer" aria-hidden={!projected.length}>
      {projected.map((dot, index) =>
        dot.visible ? (
          <button
            key={`${dot.caption}-${index}`}
            type="button"
            className="tapdot-label-bubble"
            style={{ left: dot.x, top: dot.y, opacity: 1 }}
            onClick={() => onOpenPhotos(dot.dot)}
            aria-label={dot.caption}
          >
            <span className="tapdot-label-text">{dot.caption}</span>
          </button>
        ) : null,
      )}
    </div>
  );
}
