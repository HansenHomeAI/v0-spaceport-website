#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPRESSOR_DIR = REPO_ROOT / "infrastructure" / "containers" / "compressor"
if str(COMPRESSOR_DIR) not in sys.path:
    sys.path.insert(0, str(COMPRESSOR_DIR))

from preview_sidecar import generate_preview_sidecar  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a point-preview sidecar from a SOG bundle root")
    parser.add_argument("bundle_root", help="Bundle directory or URL root (or meta.json URL/path)")
    parser.add_argument("output_dir", help="Output directory for preview-meta.json and preview-points.bin")
    parser.add_argument("--max-points", type=int, default=50_000, help="Maximum preview points to emit")
    parser.add_argument("--min-alpha", type=float, default=0.12, help="Minimum preview alpha in 0..1")
    args = parser.parse_args()

    result = generate_preview_sidecar(
      args.bundle_root,
      args.output_dir,
      max_points=args.max_points,
      min_alpha=args.min_alpha,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
