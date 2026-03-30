"use client";

import { useEffect, useState } from "react";
import { compassArrowRotationDeg } from "../../lib/canyon-vista/canyonVistaOverlays";
import type { V3 } from "../../lib/canyon-vista/types";
import type { CameraPose } from "../../lib/canyon-vista/worldProjection";
import { CanyonCompass } from "./CanyonCompass";

type Props = {
  poseRef: React.MutableRefObject<CameraPose | null>;
  /** Orbit pivot (world); ref updates during free navigation / tap-to-focus without re-rendering parent. */
  orbitTargetRef: React.MutableRefObject<V3>;
  northDeg: number;
  onClick: () => void;
  compassAriaLabel?: string;
};

export function CanyonCompassLive({ poseRef, orbitTargetRef, northDeg, onClick, compassAriaLabel }: Props) {
  const [rot, setRot] = useState(0);

  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const p = poseRef.current;
      const ot = orbitTargetRef.current;
      if (p) {
        setRot(compassArrowRotationDeg(p.position, ot, northDeg));
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [poseRef, orbitTargetRef, northDeg]);

  return <CanyonCompass rotationDeg={rot} onClick={onClick} ariaLabel={compassAriaLabel} />;
}
