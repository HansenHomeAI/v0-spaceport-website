"use client";

const COMPASS_OUTLINE =
  "https://raw.githubusercontent.com/HansenHomeAI/FigmaSVGButtons/main/NorthOutline.svg";

type Props = {
  rotationDeg: number;
  onClick: () => void;
};

export function CanyonCompass({ rotationDeg, onClick }: Props) {
  return (
    <button type="button" className="canyon-compass-btn" onClick={onClick} aria-label="Face north">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={COMPASS_OUTLINE}
        alt=""
        className="canyon-compass-icon"
        style={{ transform: `rotate(${rotationDeg}deg)` }}
      />
    </button>
  );
}
