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
        "--preserve-context-tile",
        action="append",
        default=[],
        help="Tile id whose explicit context bounds should preserve non-core far-field gaussians during merge.",
    )
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
    parser.add_argument("--context-padding-ratio", type=float, default=0.0)
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


def vertex_bounds_dict(vertex: np.ndarray, padding_ratio: float = 0.0) -> dict[str, float]:
    if len(vertex) == 0:
        return {
            "min_x": 0.0,
            "max_x": 0.0,
            "min_y": 0.0,
            "max_y": 0.0,
            "min_z": 0.0,
            "max_z": 0.0,
        }
    coords = np.stack(
        [
            np.asarray(vertex["x"], dtype=np.float32),
            np.asarray(vertex["y"], dtype=np.float32),
            np.asarray(vertex["z"], dtype=np.float32),
        ],
        axis=1,
    )
    mins = np.nanmin(coords, axis=0).astype(np.float64)
    maxs = np.nanmax(coords, axis=0).astype(np.float64)
    padding = np.maximum(maxs - mins, 1e-6) * max(float(padding_ratio), 0.0)
    mins -= padding
    maxs += padding
    return {
        "min_x": float(mins[0]),
        "max_x": float(maxs[0]),
        "min_y": float(mins[1]),
        "max_y": float(maxs[1]),
        "min_z": float(mins[2]),
        "max_z": float(maxs[2]),
    }


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


TILE_SIDECARS = (
    "background_skybox.webp",
    "background_manifest.json",
    "export_manifest.json",
    "stage_summary.json",
    "training_metadata.json",
    "training_selection.json",
    "floater_pruning_summary.json",
)


def copy_tile_sidecars(source_tile_dir: Path, output_tile_dir: Path, *, prefer_link: bool = False) -> None:
    for sidecar in TILE_SIDECARS:
        source = source_tile_dir / sidecar
        if source.exists():
            if prefer_link:
                link_or_copy(source, output_tile_dir / sidecar)
            else:
                shutil.copy2(source, output_tile_dir / sidecar)


def write_json_if_missing(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def resolve_artifact_root(root: Path) -> Path:
    """Find the model artifact root even when SageMaker wraps the tarball contents."""
    marker_names = ("3dgs_tile_manifest.fixed.json", "3dgs_tile_manifest.json")
    if (root / "tiles").is_dir() and any((root / name).exists() for name in marker_names):
        return root
    if (root / "tiles").is_dir() and any((root / "tiled_pipeline" / "inputs").glob("*/3dgs_tile_manifest.json")):
        return root

    candidates: list[Path] = []
    for marker_name in marker_names:
        for marker in root.rglob(marker_name):
            candidate = marker.parent
            if (candidate / "tiles").is_dir():
                candidates.append(candidate)

    if not candidates:
        return root
    return sorted(candidates, key=lambda path: (len(path.relative_to(root).parts), str(path)))[0]


def find_tile_manifest(root: Path) -> Path:
    for name in ("3dgs_tile_manifest.fixed.json", "3dgs_tile_manifest.json"):
        path = root / name
        if path.exists():
            return path
    nested = sorted((root / "tiled_pipeline" / "inputs").glob("*/3dgs_tile_manifest.json"))
    if nested:
        return nested[0]
    return root / "3dgs_tile_manifest.json"


def find_view_buckets(root: Path) -> Path | None:
    for name in ("3dgs_view_buckets.fixed.json", "3dgs_view_buckets.json"):
        path = root / name
        if path.exists():
            return path
    nested = sorted((root / "tiled_pipeline" / "inputs").glob("*/3dgs_view_buckets.json"))
    return nested[0] if nested else None


def copy_or_synthesize_input_metadata(
    *,
    output_dir: Path,
    source_root: Path,
    tile_id: str,
    manifest: dict[str, Any],
    view_buckets: dict[str, Any],
    tile_policy: dict[str, Any],
) -> None:
    input_dir = output_dir / "tiled_pipeline" / "inputs" / tile_id
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "3dgs_tile_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (input_dir / "3dgs_view_buckets.json").write_text(json.dumps(view_buckets, indent=2), encoding="utf-8")

    source_scaffold = source_root / "tiled_pipeline" / "inputs" / tile_id / "scaffold_init_metadata.json"
    if source_scaffold.exists():
        shutil.copy2(source_scaffold, input_dir / "scaffold_init_metadata.json")
        return
    write_json_if_missing(
        input_dir / "scaffold_init_metadata.json",
        {
            "scaffold_source_artifact": tile_policy.get("source_splat"),
            "scaffold_inheritance_mode": "hybrid_preserved_or_appended_tile_splat",
            "inherited_gaussian_count": tile_policy.get("written_gaussian_count"),
            "hybrid_tile_policy": tile_policy,
        },
    )


def synthesize_required_tile_metadata(
    *,
    tile_dir: Path,
    tile_id: str,
    tile_policy: dict[str, Any],
    vertex_count: int | None,
) -> None:
    hybrid_mode = tile_policy.get("mode", "hybrid")
    write_json_if_missing(
        tile_dir / "export_manifest.json",
        {
            "tile_id": tile_id,
            "stage": "hybrid_artifact_build",
            "training_completed": True,
            "source_splat": tile_policy.get("source_splat"),
            "written_gaussian_count": vertex_count,
            "hybrid_tile_policy": tile_policy,
        },
    )
    write_json_if_missing(
        tile_dir / "stage_summary.json",
        {
            "tile_id": tile_id,
            "stage": "hybrid_artifact_build",
            "training_completed": True,
            "remaining_gaussians": vertex_count,
            "hybrid_tile_policy": tile_policy,
        },
    )
    write_json_if_missing(
        tile_dir / "training_metadata.json",
        {
            "tile_id": tile_id,
            "training_completed": True,
            "training_mode": f"hybrid_{hybrid_mode}",
            "model_variant": "md1_hybrid_diagnostic",
            "hybrid_tile_policy": tile_policy,
        },
    )
    write_json_if_missing(
        tile_dir / "training_selection.json",
        {
            "tile_id": tile_id,
            "training_mode": f"hybrid_{hybrid_mode}",
            "selected_image_count": None,
            "view_bucket_counts": None,
            "hybrid_tile_policy": tile_policy,
        },
    )


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
    historical_root = resolve_artifact_root(args.historical_root.resolve())
    replacement_root = resolve_artifact_root(args.replacement_root.resolve())
    output_dir = args.output_dir.resolve()
    replacement_tiles = set(args.replacement_tile)
    preserve_context_tiles = set(args.preserve_context_tile)
    if not replacement_tiles:
        raise SystemExit("At least one --replacement-tile is required")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    (output_dir / "tiles").mkdir(parents=True, exist_ok=True)

    manifest_source = find_tile_manifest(historical_root)
    manifest = load_json(manifest_source)
    shutil.copy2(manifest_source, output_dir / "3dgs_tile_manifest.fixed.json")
    shutil.copy2(manifest_source, output_dir / "3dgs_tile_manifest.json")
    view_buckets = {}
    view_bucket_source = find_view_buckets(historical_root)
    if view_bucket_source is not None:
        shutil.copy2(view_bucket_source, output_dir / "3dgs_view_buckets.fixed.json")
        shutil.copy2(view_bucket_source, output_dir / "3dgs_view_buckets.json")
        view_buckets = load_json(view_bucket_source)

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
            vertex_count = int(len(output_vertex))
        else:
            source_tile_dir = historical_tile_dir
            source_vertex = read_vertex(source_tile_dir / "splat.ply") if tile_id in preserve_context_tiles else None
            link_or_copy(source_tile_dir / "splat.ply", output_tile_dir / "splat.ply")
            copy_tile_sidecars(source_tile_dir, output_tile_dir, prefer_link=True)
            tile_policy[tile_id] = {
                "mode": "historical",
                "source_splat": str(source_tile_dir / "splat.ply"),
                "storage": "hardlink_or_copy",
            }
            output_vertex = source_vertex
            vertex_count = int(len(source_vertex)) if source_vertex is not None else None
        if tile_id in preserve_context_tiles:
            context_vertex = output_vertex if output_vertex is not None else read_vertex(output_tile_dir / "splat.ply")
            tile_entry["context_bounds"] = vertex_bounds_dict(context_vertex, args.context_padding_ratio)
            tile_entry["preserve_context_gaussians"] = True
            tile_entry["context_bounds_strategy"] = "hybrid_output_splat_extent"
            tile_entry["context_padding_ratio"] = float(args.context_padding_ratio)
            tile_policy[tile_id]["context_preservation"] = {
                "enabled": True,
                "context_bounds": tile_entry["context_bounds"],
                "strategy": tile_entry["context_bounds_strategy"],
                "padding_ratio": float(args.context_padding_ratio),
            }
        synthesize_required_tile_metadata(
            tile_dir=output_tile_dir,
            tile_id=tile_id,
            tile_policy=tile_policy[tile_id],
            vertex_count=vertex_count,
        )
        copy_or_synthesize_input_metadata(
            output_dir=output_dir,
            source_root=historical_root if tile_id not in replacement_tiles else replacement_root,
            tile_id=tile_id,
            manifest=manifest,
            view_buckets=view_buckets,
            tile_policy=tile_policy[tile_id],
        )
        tile_dirs[tile_id] = output_tile_dir

    for manifest_name in ("3dgs_tile_manifest.fixed.json", "3dgs_tile_manifest.json"):
        (output_dir / manifest_name).write_text(json.dumps(manifest, indent=2), encoding="utf-8")

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
        "training_completed": True,
        "training_mode": "md1_hybrid_diagnostic",
        "model_variant": "md1_hybrid_diagnostic",
        "historical_source_root": str(historical_root),
        "replacement_source_root": str(replacement_root),
        "replacement_tiles": sorted(replacement_tiles),
        "preserve_context_tiles": sorted(preserve_context_tiles),
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
                "mode": "md1_hybrid_diagnostic",
                "label": args.label,
                "selected_tile_ids": sorted(tile_dirs),
                "include_scaffold": False,
                "include_merge": True,
                "tile_manifest_resolution": "fixed" if (output_dir / "3dgs_tile_manifest.fixed.json").exists() else "base",
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
