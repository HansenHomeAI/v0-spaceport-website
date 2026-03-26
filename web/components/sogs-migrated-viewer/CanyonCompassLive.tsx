"use client";

import { useEffect, useState } from "react";
import { compassArrowRotationDeg } from "../../lib/canyon-vista/canyonVistaOverlays";
import type { V3 } from "../../lib/canyon-vista/types";
import type { CameraPose } from "../../lib/canyon-vista/worldProjection";
import { CanyonCompass } from "./CanyonCompass";

type Props = {
  poseRef: React.MutableRefObject<CameraPose | null>;
  orbitTarget: V3;
  northDeg: number;
  onClick: () => void;
};

export function CanyonCompassLive({ poseRef, orbitTarget, northDeg, onClick }: Props) {
  const [rot, setRot] = useState(0);

  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const p = poseRef.current;
      if (p) {
        setRot(compassArrowRotationDeg(p.position, orbitTarget, northDeg));
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [poseRef, orbitTarget, northDeg]);

  return <CanyonCompass rotationDeg={rot} onClick={onClick} />;
}
