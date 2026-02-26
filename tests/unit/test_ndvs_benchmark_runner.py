#!/usr/bin/env python3
"""Unit tests for NDVS benchmark orchestration script."""

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_run_ndvs_benchmark_executes_gate_successfully(tmp_path: Path):
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
        },
        {
            "method_name": "spaceport",
            "dataset_name": "tanksandtemples",
            "scene_name": "truck",
            "psnr": 26.9,
            "ssim": 0.855,
            "lpips": 0.205,
            "time": 1120.0,
        },
    ]

    config_path = tmp_path / "config.json"
    results_path = tmp_path / "results.json"
    output_dir = tmp_path / "ndvs-out"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    results_path.write_text(json.dumps(results), encoding="utf-8")

    cmd = [
        sys.executable,
        "scripts/benchmarks/run_ndvs_benchmark.py",
        "--config",
        str(config_path),
        "--method-name",
        "spaceport",
        "--subset",
        "control9",
        "--gate",
        "progress",
        "--results-json",
        str(results_path),
        "--output-dir",
        str(output_dir),
    ]
    completed = subprocess.run(
        cmd,
        cwd=_repo_root(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout

    scorecard_file = output_dir / "scorecard.json"
    assert scorecard_file.exists()
    scorecard = json.loads(scorecard_file.read_text(encoding="utf-8"))
    assert scorecard["gate"]["passed"] is True


def test_run_ndvs_benchmark_dry_run_without_results_file(tmp_path: Path):
    config = {
        "scene_subsets": {"control9": ["mipnerf360/garden"]},
        "gates": {"progress": {"subset": "control9", "minimums": {"psnr": 0.0}}},
    }
    config_path = tmp_path / "config.json"
    output_dir = tmp_path / "ndvs-out"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    cmd = [
        sys.executable,
        "scripts/benchmarks/run_ndvs_benchmark.py",
        "--config",
        str(config_path),
        "--method-name",
        "spaceport",
        "--subset",
        "control9",
        "--gate",
        "progress",
        "--output-dir",
        str(output_dir),
        "--dry-run",
    ]
    completed = subprocess.run(
        cmd,
        cwd=_repo_root(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
