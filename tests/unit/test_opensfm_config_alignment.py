#!/usr/bin/env python3
"""Unit tests for OpenSfM runtime config alignment defaults."""

from pathlib import Path
import sys
import yaml
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

pytest.importorskip("numpy")

from infrastructure.containers.sfm.run_opensfm_gps import OpenSfMGPSPipeline


def test_runtime_config_keeps_orientation_alignment_defaults(tmp_path: Path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    pipeline = OpenSfMGPSPipeline(input_dir=input_dir, output_dir=output_dir)
    pipeline.setup_workspace()
    pipeline.has_gps_priors = True
    pipeline.create_opensfm_config()

    config_path = pipeline.opensfm_dir / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    assert config["align_method"] == "orientation_prior"
    assert config["align_orientation_prior"] == "vertical"
