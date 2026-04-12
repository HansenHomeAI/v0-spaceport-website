"use client";

import { useEffect, useState } from "react";
import { CanyonCompass } from "../sogs-migrated-viewer/CanyonCompass";
import type { CameraPose, V3 } from "../../lib/manifest-viewer/types";

function compassArrowRotationDeg(cameraPos: V3, orbitTarget: V3, northDirectionDeg: number): number {
  const deltaX = cameraPos.x - orbitTarget.x;
  const deltaZ = cameraPos.z - orbitTarget.z;
  const cameraBearing = ((Math.atan2(deltaX, deltaZ) * 180) / Math.PI + 360) % 360;
  return (northDirectionDeg - cameraBearing + 360) % 360;
}

type Props = {
  poseRef: React.MutableRefObject<CameraPose | null>;
  orbitTarget: V3;
  northDeg: number;
  onClick: () => void;
};

export function CompassLive({ poseRef, orbitTarget, northDeg, onClick }: Props) {
  const [rotationDeg, setRotationDeg] = useState(0);

  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const pose = poseRef.current;
      if (pose) {
        setRotationDeg(compassArrowRotationDeg(pose.position, orbitTarget, northDeg));
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [northDeg, orbitTarget, poseRef]);

  return <CanyonCompass rotationDeg={rotationDeg} onClick={onClick} />;
}
