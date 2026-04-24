#!/usr/bin/env python3
"""Build reproducible md1 hybrid tiled-3DGS diagnostic artifacts."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from plyfile import PlyData, PlyElement

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTAINER_3DGS = REPO_ROOT / "infrastructure" / "containers" / "3dgs"
if str(CONTAINER_3DGS) not in sys.path:
    sys.path.insert(0, str(CONTAINER_3DGS))

from tile_pipeline import load_json, merge_tile_outputs  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-root", required=True, type=Path)
    parser.add_argument("--replacement-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--replacement-tile", action="append", default=[])
    parser.add_argument(
        "--replacement-mode",
        choices=["replace", "append"],
        default="replace",
        help="Whether replacement tile splats replace or append to historical tile splats.",
    )
    parser.add_argument("--merge-mode", default="support_weighted_overlap")
    parser.add_argument(
        "--opacity-policy",
        choices=["none", "median", "factor", "scale-aware"],
        default="none",
    )
    parser.add_argument("--opacity-factor", type=float, default=1.0)
    parser.add_argument("--scale-start-quantile", type=float, default=0.90)
    parser.add_argument("--scale-full-quantile", type=float, default=0.99)
    parser.add_argument("--scale-weight-power", type=float, default=1.0)
    parser.add_argument(
        "--skip-local-tarball",
        action="store_true",
        help="Build the artifact directory and summaries without writing model.tar.gz locally.",
    )
    parser.add_argument("--label", default="md1_hybrid")
    parser.add_argument("--purpose", default="")
    return parser.parse_args()


def read_vertex(path: Path) -> np.ndarray:
    return PlyData.read(str(path))["vertex"].data


def write_vertex(path: Path, vertex: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    PlyData([PlyElement.describe(vertex, "vertex")], text=False).write(str(path))


def link_or_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def expand_vertex_dtype(vertex: np.ndarray, target_dtype: np.dtype) -> np.ndarray:
    if vertex.dtype == target_dtype:
        return vertex.copy()
    expanded = np.zeros(len(vertex), dtype=target_dtype)
    for name in target_dtype.names or ():
        if name in (vertex.dtype.names or ()):
            expanded[name] = vertex[name]
    return expanded


def scale_metric(vertex: np.ndarray) -> np.ndarray:
    names = set(vertex.dtype.names or ())
    scale_names = [name for name in ("scale_0", "scale_1", "scale_2") if name in names]
    if not scale_names:
        return np.zeros(len(vertex), dtype=np.float32)
    scales = np.stack([np.asarray(vertex[name], dtype=np.float32) for name in scale_names], axis=1)
    return np.max(scales, axis=1)


def apply_opacity_policy(
    *,
    tile_id: str,
    historical_vertex: np.ndarray,
    replacement_vertex: np.ndarray,
    policy: str,
    factor: float,
    scale_start_quantile: float,
    scale_full_quantile: float,
    scale_weight_power: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    if "opacity" not in (replacement_vertex.dtype.names or ()) or policy == "none":
        return replacement_vertex, {"mode": policy, "adjusted": False}

    old_opacity = np.asarray(historical_vertex["opacity"], dtype=np.float32)
    new_opacity = np.asarray(replacement_vertex["opacity"], dtype=np.float32)
    old_median = float(np.median(old_opacity))
    new_median_before = float(np.median(new_opacity))
    full_shift = new_median_before - old_median
    adjusted = replacement_vertex.copy()

    if policy == "median":
        weights = np.ones(len(adjusted), dtype=np.float32)
    elif policy == "factor":
        weights = np.full(len(adjusted), float(factor), dtype=np.float32)
    elif policy == "scale-aware":
        old_scale = scale_metric(historical_vertex)
        new_scale = scale_metric(replacement_vertex)
        start = float(np.quantile(old_scale, scale_start_quantile))
        full = float(np.quantile(old_scale, scale_full_quantile))
        denom = max(full - start, 1e-6)
        weights = np.clip((new_scale - start) / denom, 0.0, 1.0).astype(np.float32)
        if scale_weight_power != 1.0:
            weights = np.power(weights, float(scale_weight_power)).astype(np.float32)
    else:  # pragma: no cover - argparse constrains this.
        raise ValueError(f"Unsupported opacity policy: {policy}")

    adjusted["opacity"] = new_opacity - (float(full_shift) * weights)
    after = np.asarray(adjusted["opacity"], dtype=np.float32)
    return adjusted, {
        "mode": policy,
        "adjusted": True,
        "tile_id": tile_id,
        "old_median_opacity": old_median,
        "replacement_median_opacity_before": new_median_before,
        "full_median_shift": float(full_shift),
        "opacity_factor": float(factor),
        "opacity_logit_shift_mean": float(np.mean(float(full_shift) * weights)),
        "replacement_median_opacity_after": float(np.median(after)),
        "weight_quantiles": [float(value) for value in np.quantile(weights, [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0])],
        "adjusted_gaussian_count": int(np.count_nonzero(weights > 0.0)),
        "fully_adjusted_gaussian_count": int(np.count_nonzero(weights >= 1.0)),
    }


def copy_tile_sidecars(source_tile_dir: Path, output_tile_dir: Path, *, prefer_link: bool = False) -> None:
    for sidecar in ("background_skybox.webp", "background_manifest.json", "export_manifest.json"):
        source = source_tile_dir / sidecar
        if source.exists():
            if prefer_link:
                link_or_copy(source, output_tile_dir / sidecar)
            else:
                shutil.copy2(source, output_tile_dir / sidecar)


def build_tarball(output_dir: Path) -> Path:
    tarball = output_dir / "model.tar.gz"
    with tarfile.open(tarball, "w:gz") as archive:
        for child in sorted(output_dir.iterdir()):
            if child.name == tarball.name:
                continue
            archive.add(child, arcname=child.name)
    return tarball


def main() -> int:
    args = parse_args()
    historical_root = args.historical_root.resolve()
    replacement_root = args.replacement_root.resolve()
    output_dir = args.output_dir.resolve()
    replacement_tiles = set(args.replacement_tile)
    if not replacement_tiles:
        raise SystemExit("At least one --replacement-tile is required")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    (output_dir / "tiles").mkdir(parents=True, exist_ok=True)

    manifest_source = historical_root / "3dgs_tile_manifest.fixed.json"
    if not manifest_source.exists():
        manifest_source = historical_root / "3dgs_tile_manifest.json"
    manifest = load_json(manifest_source)
    shutil.copy2(manifest_source, output_dir / "3dgs_tile_manifest.fixed.json")
    shutil.copy2(manifest_source, output_dir / "3dgs_tile_manifest.json")
    view_bucket_source = historical_root / "3dgs_view_buckets.fixed.json"
    if view_bucket_source.exists():
        shutil.copy2(view_bucket_source, output_dir / "3dgs_view_buckets.fixed.json")

    reference_dtype = read_vertex(historical_root / "tiles" / str(manifest["tiles"][0]["tile_id"]) / "splat.ply").dtype
    tile_dirs: dict[str, Path] = {}
    tile_policy: dict[str, Any] = {}
    for tile_entry in manifest.get("tiles", []):
        tile_id = str(tile_entry["tile_id"])
        output_tile_dir = output_dir / "tiles" / tile_id
        output_tile_dir.mkdir(parents=True, exist_ok=True)
        historical_tile_dir = historical_root / "tiles" / tile_id
        replacement_tile_dir = replacement_root / "tiles" / tile_id
        if tile_id in replacement_tiles:
            source_tile_dir = replacement_tile_dir
            source_vertex = read_vertex(source_tile_dir / "splat.ply")
            historical_vertex = read_vertex(historical_tile_dir / "splat.ply")
            expanded = expand_vertex_dtype(source_vertex, reference_dtype)
            adjusted, policy_summary = apply_opacity_policy(
                tile_id=tile_id,
                historical_vertex=historical_vertex,
                replacement_vertex=expanded,
                policy=args.opacity_policy,
                factor=args.opacity_factor,
                scale_start_quantile=args.scale_start_quantile,
                scale_full_quantile=args.scale_full_quantile,
                scale_weight_power=args.scale_weight_power,
            )
            if args.replacement_mode == "append":
                output_vertex = np.concatenate([historical_vertex, adjusted])
                tile_mode = "historical_plus_replacement"
            else:
                output_vertex = adjusted
                tile_mode = "replacement"
            write_vertex(output_tile_dir / "splat.ply", output_vertex)
            copy_tile_sidecars(source_tile_dir, output_tile_dir)
            tile_policy[tile_id] = {
                "mode": tile_mode,
                "source_splat": str(source_tile_dir / "splat.ply"),
                "historical_source_splat": str(historical_tile_dir / "splat.ply"),
                "source_property_count": len(source_vertex.dtype.names or ()),
                "expanded_to_dtype_property_count": len(reference_dtype.names or ()),
                "written_gaussian_count": int(len(output_vertex)),
                "opacity_policy": policy_summary,
            }
        else:
            source_tile_dir = historical_tile_dir
            link_or_copy(source_tile_dir / "splat.ply", output_tile_dir / "splat.ply")
            copy_tile_sidecars(source_tile_dir, output_tile_dir, prefer_link=True)
            tile_policy[tile_id] = {
                "mode": "historical",
                "source_splat": str(source_tile_dir / "splat.ply"),
                "storage": "hardlink_or_copy",
            }
        tile_dirs[tile_id] = output_tile_dir

    merge_report = merge_tile_outputs(
        tile_manifest=manifest,
        tile_output_dirs=tile_dirs,
        output_dir=output_dir / "merged",
        merge_mode=args.merge_mode,
    )

    summary = {
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "label": args.label,
        "purpose": args.purpose,
        "historical_source_root": str(historical_root),
        "replacement_source_root": str(replacement_root),
        "replacement_tiles": sorted(replacement_tiles),
        "replacement_mode": args.replacement_mode,
        "merge_mode": args.merge_mode,
        "opacity_policy": {
            "mode": args.opacity_policy,
            "factor": args.opacity_factor,
            "scale_start_quantile": args.scale_start_quantile,
            "scale_full_quantile": args.scale_full_quantile,
            "scale_weight_power": args.scale_weight_power,
        },
        "tile_policy": tile_policy,
        "merge_report": {
            key: merge_report.get(key)
            for key in (
                "merge_mode",
                "tile_count",
                "source_gaussians",
                "retained_gaussians",
                "dropped_gaussians",
                "fallback_tile_count",
                "retain_all_tile_count",
                "fallback_reasons",
            )
        },
    }
    (output_dir / "hybrid_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "training_metadata.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "tiled_pipeline_summary.json").write_text(
        json.dumps(
            {
                "pipeline": "md1_hybrid_diagnostic",
                "label": args.label,
                "merge": summary["merge_report"],
                "model_artifact": str(output_dir / "model.tar.gz"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    tarball = None if args.skip_local_tarball else build_tarball(output_dir)
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "model_tarball": None if tarball is None else str(tarball),
                "summary": summary,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
