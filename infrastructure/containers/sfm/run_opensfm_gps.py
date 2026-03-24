#!/usr/bin/env python3
"""Backward-compatible wrapper around the COLMAP hybrid SfM pipeline."""

from __future__ import annotations

from run_colmap_hybrid import ColmapHybridPipeline, main


# Preserve the legacy import surface used by existing unit tests.
OpenSfMGPSPipeline = ColmapHybridPipeline


if __name__ == "__main__":
    main()
