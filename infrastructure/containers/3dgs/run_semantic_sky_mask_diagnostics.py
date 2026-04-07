#!/usr/bin/env python3
"""Generate semantic sky mask QC artifacts for a local COLMAP dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Sequence

import numpy as np
from PIL import Image

from semantic_sky_masks import (
    SemanticSkyMaskSettings,
    compact_semantic_mask_summary,
    generate_source_semantic_sky_masks,
    load_colmap_image_records,
)


def build_overlay(image_path: Path, mask_path: Path, output_path: Path) -> None:
    with Image.open(image_path) as image_handle, Image.open(mask_path) as mask_handle:
        rgb = image_handle.convert("RGBA")
        mask = mask_handle.convert("L")

    rgb_array = np.array(rgb)
    mask_array = np.array(mask) > 0
    overlay_array = rgb_array.copy()
    overlay_array[mask_array] = (
        0.65 * overlay_array[mask_array] + 0.35 * np.array([54, 170, 255, 255], dtype=np.float32)
    ).astype(np.uint8)

    Image.fromarray(overlay_array, mode="RGBA").save(output_path)


def evenly_sample_records(records: Sequence, sample_count: int) -> List:
    if sample_count <= 0:
        return []
    if len(records) <= sample_count:
        return records
    sampled_indices = np.linspace(0, len(records) - 1, sample_count, dtype=int)
    return [records[index] for index in sampled_indices]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate semantic sky mask diagnostics")
    parser.add_argument("--input-dir", type=Path, required=True, help="Local COLMAP dataset directory")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for masks and overlays")
    parser.add_argument("--sample-count", type=int, default=24, help="Number of overlay samples to save")
    parser.add_argument(
        "--max-images",
        type=int,
        default=0,
        help="Limit diagnostics to an evenly sampled subset of registered COLMAP images; 0 uses all images",
    )
    parser.add_argument("--device", default="cpu", help="Torch device for segmentation inference")
    parser.add_argument("--confidence-threshold", type=float, default=0.55)
    parser.add_argument("--min-component-area", type=float, default=0.002)
    parser.add_argument("--fill-hole-area", type=float, default=0.001)
    parser.add_argument(
        "--disable-top-connected-only",
        action="store_true",
        help="Allow non-top-connected sky components in the diagnostic masks",
    )
    parser.add_argument("--model-id", default="nvidia/segformer-b0-finetuned-ade-512-512")
    args = parser.parse_args()

    masks_dir = args.output_dir / "masks"
    overlays_dir = args.output_dir / "overlays"
    masks_dir.mkdir(parents=True, exist_ok=True)
    overlays_dir.mkdir(parents=True, exist_ok=True)

    settings = SemanticSkyMaskSettings(
        enabled=True,
        model_id=args.model_id,
        confidence_threshold=args.confidence_threshold,
        min_component_area=args.min_component_area,
        fill_hole_area=args.fill_hole_area,
        keep_top_connected_only=not args.disable_top_connected_only,
    )

    all_records = load_colmap_image_records(args.input_dir / "sparse" / "0" / "images.txt")
    selected_records = evenly_sample_records(all_records, args.max_images) if args.max_images else all_records
    selected_image_names = [record.name for record in selected_records]

    source_summary = generate_source_semantic_sky_masks(
        dataset_dir=args.input_dir,
        output_dir=masks_dir,
        settings=settings,
        device=args.device,
        selected_image_names=selected_image_names,
    )

    compact_summary = compact_semantic_mask_summary(source_summary)
    compact_summary["available_registered_image_count"] = len(all_records)
    compact_summary["selected_registered_image_count"] = len(selected_records)
    compact_summary["sample_count"] = min(args.sample_count, len(source_summary["mask_records"]))
    compact_summary["frames_with_nonzero_mask_ratio"] = float(
        np.mean([record["mask_ratio"] > 0 for record in source_summary["mask_records"]])
    ) if source_summary["mask_records"] else 0.0
    compact_summary["frames_with_top_border_connection_ratio"] = float(
        np.mean([record["top_border_ratio"] > 0 for record in source_summary["mask_records"]])
    ) if source_summary["mask_records"] else 0.0
    compact_summary["per_frame_stats"] = source_summary["mask_records"]

    sampled_records = evenly_sample_records(source_summary["mask_records"], args.sample_count)
    image_root = args.input_dir / "images"

    for sample_index, record in enumerate(sampled_records):
        source_image_path = image_root / record["image_name"]
        overlay_path = overlays_dir / f"{sample_index:02d}-{Path(record['image_name']).stem}.png"
        build_overlay(
            image_path=source_image_path,
            mask_path=Path(record["mask_path"]),
            output_path=overlay_path,
        )

    with open(args.output_dir / "diagnostic_summary.json", "w", encoding="utf-8") as handle:
        json.dump(compact_summary, handle, indent=2)

    print(json.dumps({"output_dir": str(args.output_dir), **compact_summary}, indent=2))


if __name__ == "__main__":
    main()
