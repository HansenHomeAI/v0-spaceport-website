"use client";

const COMPASS_OUTLINE =
  "https://raw.githubusercontent.com/HansenHomeAI/FigmaSVGButtons/main/NorthOutline.svg";

type Props = {
  rotationDeg: number;
  onClick: () => void;
};

/** Matches Canyon-Vista `#compassButton.menu-button` + `#compassIcon`. */
export function CanyonCompass({ rotationDeg, onClick }: Props) {
  return (
    <button type="button" id="compassButton" className="menu-button" onClick={onClick} aria-label="Face north">
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
