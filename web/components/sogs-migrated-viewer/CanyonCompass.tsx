"use client";

const COMPASS_OUTLINE =
  "https://raw.githubusercontent.com/HansenHomeAI/FigmaSVGButtons/main/NorthOutline.svg";

type Props = {
  rotationDeg: number;
  onClick: () => void;
  ariaLabel?: string;
};

/** Matches Canyon-Vista `#compassButton.menu-button` + `#compassIcon`. */
export function CanyonCompass({ rotationDeg, onClick, ariaLabel = "Face north" }: Props) {
  return (
    <button type="button" id="compassButton" className="menu-button" onClick={onClick} aria-label={ariaLabel}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        id="compassIcon"
        src={COMPASS_OUTLINE}
        alt=""
        draggable={false}
        style={{ transform: `rotate(${rotationDeg}deg)` }}
      />
    </button>
  );
}
