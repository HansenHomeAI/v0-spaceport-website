#!/usr/bin/env python3
"""Analyze whether a selected MD1 tile subset can support review cameras."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REVIEW_BUCKETS = (
    ("near_detail_camera_ids", "near_detail"),
    ("boundary_camera_ids", "boundary"),
    ("horizon_camera_ids", "horizon"),
)


def ordered_unique(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = Path(str(item).lstrip("./")).name
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def parse_tile_ids(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        for tile_id in str(value).split(","):
            cleaned = tile_id.strip()
            if cleaned:
                result.append(cleaned)
    return ordered_unique(result)


def review_images_by_bucket(
    review_manifest: Mapping[str, Any],
    *,
    camera_set: str = "auto",
    max_images_per_bucket: int | None = None,
) -> dict[str, list[str]]:
    explicit = review_manifest.get("review_image_names_by_bucket")
    if isinstance(explicit, Mapping):
        source = explicit
    else:
        requested = camera_set.strip().lower()
        if requested in {"", "auto"}:
            requested = "smoke" if "smoke_buckets" in review_manifest else "buckets"
        if requested == "smoke":
            source = review_manifest.get("smoke_buckets") or review_manifest.get("buckets") or {}
        elif requested in {"full", "promotion", "buckets"}:
            source = review_manifest.get("buckets") or {}
        else:
            raise ValueError(f"Unsupported camera_set={camera_set!r}")

    limit = max_images_per_bucket if max_images_per_bucket and max_images_per_bucket > 0 else None
    images: dict[str, list[str]] = {}
    for bucket_key, bucket_label in REVIEW_BUCKETS:
        raw_names = source.get(bucket_key, source.get(bucket_label, [])) if isinstance(source, Mapping) else []
        names = ordered_unique([str(name) for name in raw_names]) if isinstance(raw_names, Sequence) else []
        images[bucket_key] = names[:limit] if limit is not None else names
    return images


def camera_tile_roles(tile_manifest: Mapping[str, Any]) -> dict[str, dict[str, list[str]]]:
    by_camera: dict[str, dict[str, list[str]]] = {}
    role_fields = (
        ("base", "base_camera_ids"),
        ("border", "border_camera_ids"),
        ("context", "context_camera_ids"),
        ("image", "image_names"),
    )
    for tile in tile_manifest.get("tiles", []):
        if not isinstance(tile, Mapping):
            continue
        tile_id = str(tile.get("tile_id") or "").strip()
        if not tile_id:
            continue
        for role, field in role_fields:
            raw_names = tile.get(field, [])
            if not isinstance(raw_names, Sequence) or isinstance(raw_names, (str, bytes)):
                continue
            for image_name in ordered_unique([str(name) for name in raw_names]):
                by_camera.setdefault(image_name, {}).setdefault(tile_id, [])
                if role not in by_camera[image_name][tile_id]:
                    by_camera[image_name][tile_id].append(role)
    return by_camera


def greedy_any_support_additions(
    *,
    rows: Sequence[Mapping[str, Any]],
    selected_tile_ids: Sequence[str],
) -> list[str]:
    selected = set(selected_tile_ids)
    uncovered = {
        int(index)
        for index, row in enumerate(rows)
        if not set(row.get("support_tile_ids", [])).intersection(selected)
    }
    additions: list[str] = []
    while uncovered:
        scores: Counter[str] = Counter()
        for index in uncovered:
            for tile_id in rows[index].get("support_tile_ids", []):
                if tile_id not in selected:
                    scores[str(tile_id)] += 1
        if not scores:
            break
        best_tile, _count = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[0]
        selected.add(best_tile)
        additions.append(best_tile)
        uncovered = {
            index
            for index in uncovered
            if not set(rows[index].get("support_tile_ids", [])).intersection(selected)
        }
    return additions


def analyze_coverage(
    *,
    tile_manifest: Mapping[str, Any],
    review_manifest: Mapping[str, Any],
    selected_tile_ids: Sequence[str],
    camera_set: str = "auto",
    max_images_per_bucket: int | None = None,
) -> dict[str, Any]:
    selected = set(selected_tile_ids)
    images_by_bucket = review_images_by_bucket(
        review_manifest,
        camera_set=camera_set,
        max_images_per_bucket=max_images_per_bucket,
    )
    support_by_camera = camera_tile_roles(tile_manifest)
    rows: list[dict[str, Any]] = []
    missing_frequency: Counter[str] = Counter()
    support_frequency: Counter[str] = Counter()
    per_bucket_counts: dict[str, dict[str, int]] = {}
    matched_full: dict[str, list[str]] = {}
    matched_any: dict[str, list[str]] = {}

    for bucket_key, bucket_label in REVIEW_BUCKETS:
        bucket_rows_before = len(rows)
        matched_full[bucket_key] = []
        matched_any[bucket_key] = []
        for image_name in images_by_bucket.get(bucket_key, []):
            role_map = support_by_camera.get(Path(image_name).name, {})
            support_tile_ids = sorted(role_map)
            selected_support = [tile_id for tile_id in support_tile_ids if tile_id in selected]
            missing_support = [tile_id for tile_id in support_tile_ids if tile_id not in selected]
            support_frequency.update(support_tile_ids)
            missing_frequency.update(missing_support)
            if not support_tile_ids:
                status = "missing_manifest_support"
            elif not missing_support:
                status = "full_support_selected"
                matched_full[bucket_key].append(image_name)
                matched_any[bucket_key].append(image_name)
            elif selected_support:
                status = "partial_support_selected"
                matched_any[bucket_key].append(image_name)
            else:
                status = "no_selected_support"
            rows.append(
                {
                    "bucket": bucket_label,
                    "bucket_key": bucket_key,
                    "image_name": image_name,
                    "status": status,
                    "support_tile_ids": support_tile_ids,
                    "selected_support_tile_ids": selected_support,
                    "missing_support_tile_ids": missing_support,
                    "support_roles_by_tile": {tile_id: role_map[tile_id] for tile_id in support_tile_ids},
                }
            )
        bucket_rows = rows[bucket_rows_before:]
        per_bucket_counts[bucket_label] = {
            "review_camera_count": len(bucket_rows),
            "full_support_selected_count": sum(row["status"] == "full_support_selected" for row in bucket_rows),
            "any_support_selected_count": sum(
                row["status"] in {"full_support_selected", "partial_support_selected"} for row in bucket_rows
            ),
            "no_selected_support_count": sum(row["status"] == "no_selected_support" for row in bucket_rows),
            "missing_manifest_support_count": sum(row["status"] == "missing_manifest_support" for row in bucket_rows),
        }

    missing_tiles = sorted(missing_frequency)
    any_support_additions = greedy_any_support_additions(rows=rows, selected_tile_ids=selected_tile_ids)
    all_full_selected = all(row["status"] == "full_support_selected" for row in rows)
    all_any_selected = all(
        row["status"] in {"full_support_selected", "partial_support_selected"}
        for row in rows
    )
    block_reasons: list[str] = []
    if not all_full_selected:
        block_reasons.append("review_cameras_missing_full_tile_support")
    if not all_any_selected:
        block_reasons.append("review_cameras_missing_any_selected_tile_support")

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "selected_tile_ids": list(selected_tile_ids),
        "camera_set": camera_set,
        "max_images_per_bucket": max_images_per_bucket,
        "review_image_names_by_bucket": images_by_bucket,
        "status": "ok" if not block_reasons else "blocked",
        "block_reasons": block_reasons,
        "per_bucket_counts": per_bucket_counts,
        "per_camera": rows,
        "support_tile_frequency": dict(sorted(support_frequency.items())),
        "missing_support_tile_frequency": dict(sorted(missing_frequency.items())),
        "matched_full_support_camera_subset": matched_full,
        "matched_any_support_camera_subset": matched_any,
        "minimum_any_support_tile_additions": any_support_additions,
        "minimum_any_support_selected_tile_ids": ordered_unique([*selected_tile_ids, *any_support_additions]),
        "full_support_tile_additions": missing_tiles,
        "full_support_selected_tile_ids": ordered_unique([*selected_tile_ids, *missing_tiles]),
        "recommendation": {
            "run_current_subset_review": all_full_selected,
            "minimum_any_support_is_diagnostic_only": bool(any_support_additions),
            "next_no_spend_step": "dry_run_expanded_full_support_canary"
            if missing_tiles
            else "same_camera_v18_non_regression_review",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tile-manifest-json", required=True, type=Path)
    parser.add_argument("--review-manifest-json", required=True, type=Path)
    parser.add_argument("--selected-tile-id", action="append", default=[])
    parser.add_argument("--selected-tile-ids", default="")
    parser.add_argument("--camera-set", default="auto")
    parser.add_argument("--max-images-per-bucket", type=int, default=0)
    parser.add_argument("--output-json", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_tile_ids = parse_tile_ids([*args.selected_tile_id, args.selected_tile_ids])
    if not selected_tile_ids:
        raise SystemExit("At least one --selected-tile-id or --selected-tile-ids value is required")
    result = analyze_coverage(
        tile_manifest=load_json(args.tile_manifest_json),
        review_manifest=load_json(args.review_manifest_json),
        selected_tile_ids=selected_tile_ids,
        camera_set=args.camera_set,
        max_images_per_bucket=args.max_images_per_bucket or None,
    )
    if args.output_json:
        write_json(args.output_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
