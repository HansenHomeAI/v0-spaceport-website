#!/usr/bin/env python3
"""Normalize Nerfstudio ns-eval output into the SfM visual gate schema."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any


METRIC_NAMES = {"psnr", "ssim", "lpips"}
RENDER_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".ppm"}


def load_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(max(math.ceil(q * len(ordered)) - 1, 0), len(ordered) - 1)
    return round(ordered[index], 4)


def summarize(values: list[float]) -> dict[str, float | int | None]:
    numbers = [float(value) for value in values if math.isfinite(float(value))]
    if not numbers:
        return {"count": 0, "min": None, "p10": None, "median": None, "p90": None, "p95": None, "max": None}
    return {
        "count": len(numbers),
        "min": round(min(numbers), 4),
        "p10": quantile(numbers, 0.10),
        "median": round(statistics.median(numbers), 4),
        "p90": quantile(numbers, 0.90),
        "p95": quantile(numbers, 0.95),
        "max": round(max(numbers), 4),
    }


def metric_name(key: str) -> str | None:
    normalized = key.lower().replace("-", "_")
    tail = normalized.split("/")[-1].split(".")[-1]
    if tail in METRIC_NAMES:
        return tail
    for name in METRIC_NAMES:
        if tail.endswith(f"_{name}"):
            return name
    return None


def collect_metrics(payload: Any, out: dict[str, list[float]]) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            name = metric_name(str(key))
            if name and isinstance(value, (int, float)) and math.isfinite(float(value)):
                out[name].append(float(value))
            else:
                collect_metrics(value, out)
    elif isinstance(payload, list):
        for item in payload:
            collect_metrics(item, out)


def find_count(payload: Any) -> int:
    if isinstance(payload, dict):
        for key in ("holdout_count", "validation_images", "eval_images", "num_eval_images", "num_images", "image_count"):
            value = payload.get(key)
            if isinstance(value, int) and value > 0:
                return value
        for value in payload.values():
            found = find_count(value)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = find_count(item)
            if found:
                return found
    return 0


def list_render_paths(render_dir: str) -> list[str]:
    if not render_dir:
        return []
    root = Path(render_dir)
    if not root.exists():
        return []
    return [
        str(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix.lower() in RENDER_SUFFIXES
    ]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    raw = load_json(args.ns_eval_json)
    metrics = {name: [] for name in sorted(METRIC_NAMES)}
    collect_metrics(raw, metrics)
    panel_paths = list_render_paths(args.render_dir)
    inferred_count = args.holdout_count or find_count(raw) or len(panel_paths) or len(metrics["psnr"])
    successful_count = args.successful_render_count or len(panel_paths) or (inferred_count if metrics["psnr"] else 0)

    blockers: list[str] = []
    for name in ("psnr", "ssim", "lpips"):
        if not metrics[name]:
            blockers.append(f"missing_{name}")
    if inferred_count <= 0:
        blockers.append("missing_holdout_count")

    return {
        "schema_version": 1,
        "artifact_kind": "splat_heldout_render_metrics",
        "source": "nerfstudio_ns_eval",
        "decision": "fail" if blockers else "pass",
        "model_uri": args.model_uri or raw.get("model_uri"),
        "source_artifact_uri": args.source_artifact_uri or raw.get("source_artifact_uri"),
        "render_artifact_uri": args.render_artifact_uri or raw.get("render_artifact_uri"),
        "raw_ns_eval_json": args.ns_eval_json,
        "holdout_count": inferred_count,
        "successful_render_count": successful_count,
        "metrics": {
            "psnr": summarize(metrics["psnr"]),
            "ssim": summarize(metrics["ssim"]),
            "lpips": summarize(metrics["lpips"]),
        },
        "proof_panels": {
            "panel_dir": args.render_dir,
            "count": len(panel_paths),
            "paths": panel_paths,
        },
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ns-eval-json", required=True)
    parser.add_argument("--render-dir", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--holdout-count", type=int, default=0)
    parser.add_argument("--successful-render-count", type=int, default=0)
    parser.add_argument("--model-uri", default="")
    parser.add_argument("--source-artifact-uri", default="")
    parser.add_argument("--render-artifact-uri", default="")
    args = parser.parse_args()

    report = build_report(args)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"decision": report["decision"], "output": str(output_path)}, indent=2))
    return 1 if report["decision"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
