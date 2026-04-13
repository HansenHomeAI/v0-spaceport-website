"use client";

import { useEffect, useRef, useState } from "react";
import type { CameraPose, V3 } from "../../lib/manifest-viewer/types";
import type { ViewerSoldHotspotManifest } from "../../lib/manifest-viewer/manifest";
import {
  createOverlayPerspectiveCamera,
  projectWorldToScreen,
  syncOverlayCamera,
} from "../../lib/manifest-viewer/worldProjection";

type Props = {
  enabled: boolean;
  hotspots: ViewerSoldHotspotManifest[];
  poseRef: React.MutableRefObject<CameraPose | null>;
  containerRef: React.RefObject<HTMLDivElement | null>;
};

type Projection = { x: number; y: number; visible: boolean; text: string; fontSize: number };

export function SoldOverlays({ enabled, hotspots, poseRef, containerRef }: Props) {
  const cameraRef = useRef(createOverlayPerspectiveCamera());
  const [items, setItems] = useState<Projection[]>([]);

  useEffect(() => {
    if (!enabled || !hotspots.length) {
      setItems([]);
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
        setItems(
          hotspots.map((hotspot) => {
            const world: V3 = {
              x: hotspot.position.x,
              y: hotspot.position.y + hotspot.verticalOffset,
              z: hotspot.position.z,
            };
            const projected = projectWorldToScreen(world, camera, width, height);
            return {
              ...projected,
              text: hotspot.text,
              fontSize: Math.max(10, 14 + hotspot.scale * 40),
            };
          }),
        );
      }
      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [containerRef, enabled, hotspots, poseRef]);

  if (!enabled || !items.length) return null;

  return (
    <div className="sold-hotspot-layer" aria-hidden>
      {items.map((item, index) =>
        item.visible ? (
          <div
            key={`sold-${index}`}
            className="sold-hotspot-label"
            style={{ left: item.x, top: item.y, fontSize: item.fontSize }}
          >
            {item.text}
          </div>
        ) : null,
      )}
    </div>
  );
}
