#!/usr/bin/env python3
"""CLI wrapper for converting Litchi waypoint CSV missions to DJI Fly KMZ."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mission_converter import ConversionOptions, convert_litchi_csv_to_dji_fly_kmz

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path, help="Path to the Litchi mission CSV file")
    parser.add_argument("--out", required=True, type=Path, help="Destination KMZ path")

    parser.add_argument(
        "--finish-action",
        default="goHome",
        choices=["goHome", "land", "hover", "returnToStartPoint"],
        help="Mission finish action (DJI Fly missionConfig)",
    )
    parser.add_argument(
        "--global-transitional-speed",
        type=float,
        default=3.0,
        help="Fallback speed (m/s) when per-waypoint speeds are absent",
    )
    parser.add_argument(
        "--set-heading-from-csv",
        action="store_true",
        help="Embed waypointHeadingAngle values from the CSV heading column",
    )
    parser.add_argument(
        "--insert-yaw-actions",
        action="store_true",
        help="Emit rotateYaw action groups (requires --set-heading-from-csv)",
    )
    parser.add_argument(
        "--emit-per-waypoint-photo",
        action="store_true",
        help="Translate positive photo_timeinterval values into multipleTiming takePhoto actions",
    )
    parser.add_argument(
        "--assume-agl",
        action="store_true",
        help="Allow missions flagged as AGL (altitudemode=1) without DEM conversion",
    )
    parser.add_argument(
        "--drone-enum-value",
        default="68",
        help="DJI droneEnumValue (defaults to Mini/Air class)",
    )
    parser.add_argument(
        "--drone-sub-enum-value",
        default="0",
        help="DJI droneSubEnumValue",
    )
    parser.add_argument(
        "--mission-author",
        default="SpaceportConverter",
        help="Author tag stored in template.kml",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    options = ConversionOptions(
        finish_action=args.finish_action,
        global_transitional_speed=args.global_transitional_speed,
        set_heading_from_csv=args.set_heading_from_csv,
        insert_yaw_actions=args.insert_yaw_actions,
        emit_per_waypoint_photo=args.emit_per_waypoint_photo,
        assume_agl=args.assume_agl,
        drone_enum_value=args.drone_enum_value,
        drone_sub_enum_value=args.drone_sub_enum_value,
        mission_author=args.mission_author,
    )

    if options.insert_yaw_actions and not options.set_heading_from_csv:
        parser.error("--insert-yaw-actions requires --set-heading-from-csv")

    try:
        convert_litchi_csv_to_dji_fly_kmz(args.csv, args.out, options)
    except Exception as exc:  # pragma: no cover - surfaced to CLI
        parser.exit(status=1, message=f"error: {exc}\n")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
