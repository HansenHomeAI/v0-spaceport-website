#!/usr/bin/env python3
"""Unit tests for NDVS benchmark scorecard gating."""

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_scorecard_progress_gate_passes(tmp_path: Path):
    config = {
        "scene_subsets": {
            "control9": ["mipnerf360/garden", "tanksandtemples/truck"],
        },
        "baselines": {
            "control9": {
                "metrics": {
                    "psnr": 26.0,
                    "ssim": 0.84,
                    "lpips": 0.25,
                    "time_s": 1000.0,
                }
            }
        },
        "gates": {
            "progress": {
                "subset": "control9",
                "minimums": {"psnr": 26.7, "ssim": 0.85},
                "maximums": {"lpips": 0.23},
                "max_relative_cost_increase": 0.25,
            }
        },
    }
    results = [
        {
            "method_name": "spaceport",
            "dataset_name": "mipnerf360",
            "scene_name": "garden",
            "psnr": 27.1,
            "ssim": 0.86,
            "lpips": 0.22,
            "time": 1100.0,
            "max_gpu_memory": 12000.0,
        },
        {
            "method_name": "spaceport",
            "dataset_name": "tanksandtemples",
            "scene_name": "truck",
            "psnr": 26.9,
            "ssim": 0.855,
            "lpips": 0.205,
            "time": 1150.0,
            "max_gpu_memory": 11800.0,
        },
    ]

    config_path = tmp_path / "config.json"
    results_path = tmp_path / "results.json"
    output_path = tmp_path / "scorecard.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    results_path.write_text(json.dumps(results), encoding="utf-8")

    cmd = [
        sys.executable,
        "scripts/benchmarks/ndvs_scorecard.py",
        "--config",
        str(config_path),
        "--results-json",
        str(results_path),
        "--method-name",
        "spaceport",
        "--subset",
        "control9",
        "--gate",
        "progress",
        "--strict-scenes",
        "--fail-on-gate",
        "--output-json",
        str(output_path),
    ]

    completed = subprocess.run(
        cmd,
        cwd=_repo_root(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout

    scorecard = json.loads(output_path.read_text(encoding="utf-8"))
    assert scorecard["gate"]["passed"] is True
    assert scorecard["missing_scenes"] == []


def test_scorecard_gate_fails_when_thresholds_not_met(tmp_path: Path):
    config = {
        "scene_subsets": {"primary3": ["deepblending/playroom"]},
        "gates": {
            "parity": {
                "subset": "primary3",
                "minimums": {"psnr": 30.0},
                "maximums": {"lpips": 0.2},
            }
        },
    }
    results = [
        {
            "method_name": "spaceport",
            "dataset_name": "deepblending",
            "scene_name": "playroom",
            "psnr": 28.0,
            "ssim": 0.9,
            "lpips": 0.3,
            "time": 900.0,
        }
    ]

    config_path = tmp_path / "config.json"
    results_path = tmp_path / "results.json"
    output_path = tmp_path / "scorecard.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    results_path.write_text(json.dumps(results), encoding="utf-8")

    cmd = [
        sys.executable,
        "scripts/benchmarks/ndvs_scorecard.py",
        "--config",
        str(config_path),
        "--results-json",
        str(results_path),
        "--method-name",
        "spaceport",
        "--subset",
        "primary3",
        "--gate",
        "parity",
        "--fail-on-gate",
        "--output-json",
        str(output_path),
    ]
    completed = subprocess.run(
        cmd,
        cwd=_repo_root(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 3
