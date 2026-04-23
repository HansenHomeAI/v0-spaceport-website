#!/usr/bin/env python3
"""Merge tiled Gaussian outputs into a single PLY using manifest ownership rules."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tile_pipeline import load_json, merge_tile_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tile-manifest", required=True, help="Path to 3dgs_tile_manifest.json")
    parser.add_argument(
        "--tiles-root",
        required=True,
        help="Directory containing per-tile subdirectories named after tile_id values",
    )
    parser.add_argument("--output-dir", required=True, help="Directory for merged_splat.ply and merge_report.json")
    parser.add_argument(
        "--merge-mode",
        default="strict_core",
        choices=["raw_union", "strict_core", "support_weighted_overlap"],
        help="Tile merge strategy",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tile_manifest = load_json(args.tile_manifest)
    tiles_root = Path(args.tiles_root)
    tile_output_dirs = {
        str(tile_entry["tile_id"]): tiles_root / str(tile_entry["tile_id"])
        for tile_entry in tile_manifest.get("tiles", [])
    }
    report = merge_tile_outputs(
        tile_manifest=tile_manifest,
        tile_output_dirs=tile_output_dirs,
        output_dir=Path(args.output_dir),
        merge_mode=args.merge_mode,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
