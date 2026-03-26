"use client";

import { useEffect, useRef, useState } from "react";
import type { V3 } from "../../lib/canyon-vista/types";
import {
  createOverlayPerspectiveCamera,
  projectWorldToScreen,
  syncOverlayCamera,
  type CameraPose,
} from "../../lib/canyon-vista/worldProjection";

export type SoldHotspot = {
  text: string;
  position: V3;
  scale: number;
  verticalOffset: number;
};

type Props = {
  enabled: boolean;
  hotspots: SoldHotspot[];
  poseRef: React.MutableRefObject<CameraPose | null>;
  containerRef: React.RefObject<HTMLDivElement | null>;
};

type Proj = { x: number; y: number; visible: boolean; text: string; fontSize: number };

export function SoldOverlays({ enabled, hotspots, poseRef, containerRef }: Props) {
  const cameraRef = useRef(createOverlayPerspectiveCamera());
  const [items, setItems] = useState<Proj[]>([]);

  useEffect(() => {
    if (!enabled || !hotspots.length) {
      setItems([]);
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
        const next: Proj[] = hotspots.map((spot) => {
          const world: V3 = {
            x: spot.position.x,
            y: spot.position.y + spot.verticalOffset,
            z: spot.position.z,
          };
          const p = projectWorldToScreen(world, cam, w, h);
          return {
            ...p,
            text: spot.text,
            fontSize: Math.max(10, 14 + spot.scale * 40),
          };
        });
        setItems(next);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [enabled, hotspots, poseRef, containerRef]);

  if (!enabled || !items.length) {
    return null;
  }

  return (
    <div className="sold-hotspot-layer" aria-hidden>
      {items.map((d, i) =>
        d.visible ? (
          <div
            key={`sold-${i}`}
            className="sold-hotspot-label"
            style={{ left: d.x, top: d.y, fontSize: d.fontSize }}
          >
            {d.text}
          </div>
        ) : null,
      )}
    </div>
  );
}
