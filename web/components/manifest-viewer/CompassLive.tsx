"use client";

import { CanyonCompass } from "../sogs-migrated-viewer/CanyonCompass";
const COMPASS_ICON_FIXED_ROTATION_DEG = 45;

type Props = {
  onClick: () => void;
  ariaLabel: string;
};

export function CompassLive({ onClick, ariaLabel }: Props) {
  return <CanyonCompass rotationDeg={COMPASS_ICON_FIXED_ROTATION_DEG} onClick={onClick} ariaLabel={ariaLabel} />;
}
