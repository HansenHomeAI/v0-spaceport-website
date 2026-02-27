#!/usr/bin/env python3
"""Compute NDVS benchmark scorecards and enforce promotion gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCALAR_KEYS = ("psnr", "ssim", "lpips", "time", "max_gpu_memory")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("benchmarks/ndvs/benchmark_config.json"),
        help="Path to NDVS benchmark config JSON.",
    )
    parser.add_argument(
        "--results-json",
        type=Path,
        required=True,
        help="Path to NDVS results JSON (list of scene-level records).",
    )
    parser.add_argument(
        "--method-name",
        required=True,
        help="Method name to evaluate (must match NDVS result records).",
    )
    parser.add_argument(
        "--subset",
        default="control9",
        help="Scene subset key from config.scene_subsets.",
    )
    parser.add_argument(
        "--gate",
        default=None,
        help="Gate key from config.gates. If omitted, only summary is produced.",
    )
    parser.add_argument(
        "--orientation-failures",
        type=int,
        default=0,
        help="Number of orientation failures observed for this run.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("logs/ndvs-scorecard.json"),
        help="Output scorecard JSON path.",
    )
    parser.add_argument(
        "--fail-on-gate",
        action="store_true",
        help="Exit non-zero if gate check fails.",
    )
    parser.add_argument(
        "--strict-scenes",
        action="store_true",
        help="Exit non-zero if any required scene is missing in results.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_scene_token(token: str) -> Tuple[str, str]:
    if "/" not in token:
        raise ValueError(f"Invalid scene token '{token}'. Expected dataset/scene.")
    dataset, scene = token.split("/", 1)
    return dataset, scene


def flatten_results(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, list):
        return [row for row in raw if isinstance(row, dict)]
    if isinstance(raw, dict):
        if isinstance(raw.get("results"), list):
            return [row for row in raw["results"] if isinstance(row, dict)]
    raise ValueError("Unsupported NDVS results format.")


def index_rows(rows: Iterable[Dict[str, Any]], method_name: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        if row.get("method_name") != method_name:
            continue
        dataset = row.get("dataset_name")
        scene = row.get("scene_name")
        if not dataset or not scene:
            continue
        key = (str(dataset), str(scene))
        # Keep first record deterministically if duplicates exist.
        if key not in indexed:
            indexed[key] = row
    return indexed


def metric_averages(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    metrics: Dict[str, float] = {}
    for key in SCALAR_KEYS:
        values = [float(row[key]) for row in rows if key in row and row[key] is not None]
        if values:
            metrics[key] = mean(values)
    return metrics


def check_gate(
    gate_cfg: Dict[str, Any],
    metrics: Dict[str, float],
    baseline_metrics: Optional[Dict[str, float]],
    orientation_failures: int,
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    for metric_name, threshold in gate_cfg.get("minimums", {}).items():
        actual = metrics.get(metric_name)
        passed = actual is not None and actual >= float(threshold)
        checks.append(
            {
                "kind": "minimum",
                "metric": metric_name,
                "threshold": float(threshold),
                "actual": actual,
                "passed": bool(passed),
            }
        )

    for metric_name, threshold in gate_cfg.get("maximums", {}).items():
        actual = metrics.get(metric_name)
        passed = actual is not None and actual <= float(threshold)
        checks.append(
            {
                "kind": "maximum",
                "metric": metric_name,
                "threshold": float(threshold),
                "actual": actual,
                "passed": bool(passed),
            }
        )

    if "max_relative_cost_increase" in gate_cfg and baseline_metrics:
        max_rel = float(gate_cfg["max_relative_cost_increase"])
        actual_time = metrics.get("time")
        base_time = baseline_metrics.get("time_s")
        rel = None
        passed = False
        if actual_time is not None and base_time:
            rel = (actual_time - base_time) / base_time
            passed = rel <= max_rel
        checks.append(
            {
                "kind": "max_relative_cost_increase",
                "metric": "time",
                "threshold": max_rel,
                "actual": rel,
                "passed": bool(passed),
            }
        )

    if "max_orientation_failures" in gate_cfg:
        threshold = int(gate_cfg["max_orientation_failures"])
        passed = orientation_failures <= threshold
        checks.append(
            {
                "kind": "maximum",
                "metric": "orientation_failures",
                "threshold": threshold,
                "actual": orientation_failures,
                "passed": bool(passed),
            }
        )

    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }


def main() -> int:
    args = parse_args()
    config = load_json(args.config)
    raw_results = load_json(args.results_json)
    rows = flatten_results(raw_results)
    indexed = index_rows(rows, args.method_name)

    scene_tokens = config["scene_subsets"].get(args.subset)
    if not scene_tokens:
        raise KeyError(f"Unknown subset '{args.subset}' in {args.config}")

    selected_rows: List[Dict[str, Any]] = []
    missing_scenes: List[str] = []
    per_scene: List[Dict[str, Any]] = []

    for token in scene_tokens:
        dataset, scene = parse_scene_token(token)
        row = indexed.get((dataset, scene))
        if not row:
            missing_scenes.append(token)
            continue
        selected_rows.append(row)
        per_scene.append(
            {
                "dataset": dataset,
                "scene": scene,
                "psnr": float(row["psnr"]),
                "ssim": float(row["ssim"]),
                "lpips": float(row["lpips"]),
                "time": float(row.get("time", 0.0)),
                "max_gpu_memory": float(row.get("max_gpu_memory", 0.0)),
            }
        )

    aggregates = metric_averages(selected_rows)

    baseline = config.get("baselines", {}).get(args.subset, {}).get("metrics")
    deltas: Dict[str, float] = {}
    if isinstance(baseline, dict):
        for key in ("psnr", "ssim", "lpips", "time_s"):
            if key == "time_s":
                if "time" in aggregates:
                    deltas["time_delta_vs_baseline"] = aggregates["time"] - float(baseline[key])
                continue
            if key in aggregates and key in baseline:
                deltas[f"{key}_delta_vs_baseline"] = aggregates[key] - float(baseline[key])

    gate_result = None
    if args.gate:
        gate_cfg = config.get("gates", {}).get(args.gate)
        if gate_cfg is None:
            raise KeyError(f"Unknown gate '{args.gate}' in {args.config}")
        gate_result = check_gate(gate_cfg, aggregates, baseline, args.orientation_failures)

    output = {
        "method_name": args.method_name,
        "subset": args.subset,
        "scene_count": len(scene_tokens),
        "scenes_found": len(selected_rows),
        "missing_scenes": missing_scenes,
        "aggregates": aggregates,
        "deltas": deltas,
        "gate": {
            "name": args.gate,
            **gate_result,
        }
        if gate_result is not None
        else None,
        "per_scene": per_scene,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote scorecard to {args.output_json}")

    if args.strict_scenes and missing_scenes:
        print("Missing required scenes in NDVS results.")
        return 2

    if args.fail_on_gate and gate_result and not gate_result["passed"]:
        print(f"Gate '{args.gate}' failed.")
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
