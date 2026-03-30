"use client";

import { useEffect, useRef, useState } from "react";
import {
  canyonAssetUrl,
  type TapDotConfig,
} from "../../lib/canyon-vista/canyonVistaOverlays";
import {
  createOverlayPerspectiveCamera,
  projectWorldToScreen,
  syncOverlayCamera,
  type CameraPose,
} from "../../lib/canyon-vista/worldProjection";

const TAPDOT_CAMERA_ICON =
  "https://raw.githubusercontent.com/HansenHomeAI/WhiteCameraIcon/main/3TestIcons-9.png";

type ProjectedDot = {
  x: number;
  y: number;
  visible: boolean;
  caption: string;
  dot: TapDotConfig;
};

type Props = {
  enabled: boolean;
  tapDots: TapDotConfig[];
  poseRef: React.MutableRefObject<CameraPose | null>;
  containerRef: React.RefObject<HTMLDivElement | null>;
  onOpenPhotos: (dot: TapDotConfig) => void;
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
      const el = containerRef.current;
      const pose = poseRef.current;
      if (el && pose) {
        const w = el.clientWidth;
        const h = el.clientHeight;
        const cam = cameraRef.current;
        syncOverlayCamera(cam, pose, w, h);
        const next: ProjectedDot[] = tapDots.map((td) => {
          const p = projectWorldToScreen(td.position, cam, w, h);
          return { ...p, caption: td.caption, dot: td };
        });
        setProjected(next);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [enabled, tapDots, poseRef, containerRef]);

  if (!enabled) {
    return null;
  }

  return (
    <div className="tapdot-layer" aria-hidden={!projected.length}>
      {projected.map((d, i) => {
        if (!d.visible) {
          return null;
        }
        const dot = d.dot;
        const isCamera = dot.icon === "camera";
        const iconOnly = dot.icon === "info" && (!dot.photos || dot.photos.length === 0);
        const bubbleClass = [
          "tapdot-label-bubble",
          isCamera ? "has-camera" : "",
          iconOnly ? "icon-only" : "",
        ]
          .filter(Boolean)
          .join(" ");
        return (
          <button
            key={`${d.caption}-${i}`}
            type="button"
            className={bubbleClass}
            style={{
              left: d.x,
              top: d.y,
              opacity: 1,
            }}
            onClick={() => onOpenPhotos(d.dot)}
            aria-label={d.caption}
          >
            {isCamera ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img className="tapdot-camera-icon" src={TAPDOT_CAMERA_ICON} alt="" draggable={false} />
            ) : null}
            {!iconOnly ? <span className="tapdot-label-text">{d.caption}</span> : null}
          </button>
        );
      })}
    </div>
  );
}
