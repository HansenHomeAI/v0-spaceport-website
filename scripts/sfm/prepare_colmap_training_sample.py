#!/usr/bin/env python3
"""Create a small trainable COLMAP package from a larger COLMAP text model."""

from __future__ import annotations

import argparse
import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path


SPARSE_FILES = ("cameras.txt", "images.txt", "points3D.txt", "frames.txt", "rigs.txt")


@dataclass(frozen=True)
class ImageRecord:
    image_id: int
    camera_id: int
    name: str
    header: str
    points2d: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-colmap-dir", required=True, help="Directory containing cameras/images/points3D text files.")
    parser.add_argument("--output-colmap-dir", required=True, help="Output COLMAP package root or sparse/0 directory.")
    parser.add_argument("--max-images", type=int, default=40)
    parser.add_argument("--selection", choices=("camera-stratified-contiguous", "evenly-spaced"), default="camera-stratified-contiguous")
    parser.add_argument("--min-track-length", type=int, default=2)
    parser.add_argument("--source-images-dir", help="Optional local image directory to copy selected images from.")
    parser.add_argument("--report-json-output", required=True)
    return parser.parse_args()


def sparse_dir(path: Path) -> Path:
    if (path / "images.txt").exists():
        return path
    candidate = path / "sparse" / "0"
    if (candidate / "images.txt").exists():
        return candidate
    raise FileNotFoundError(f"No COLMAP images.txt found at {path} or {candidate}")


def output_sparse_dir(path: Path) -> Path:
    if path.name == "0" and path.parent.name == "sparse":
        return path
    return path / "sparse" / "0"


def read_image_records(images_path: Path) -> tuple[list[str], list[ImageRecord]]:
    comments: list[str] = []
    records: list[ImageRecord] = []
    with images_path.open("r", encoding="utf-8") as handle:
        iterator = iter(handle)
        for line in iterator:
            if line.startswith("#") or not line.strip():
                comments.append(line)
                continue
            header = line.rstrip("\n")
            points2d = next(iterator, "").rstrip("\n")
            tokens = header.split()
            if len(tokens) < 10:
                raise ValueError(f"Invalid COLMAP image header: {header[:160]}")
            records.append(
                ImageRecord(
                    image_id=int(tokens[0]),
                    camera_id=int(tokens[8]),
                    name=tokens[9],
                    header=header,
                    points2d=points2d,
                )
            )
    return comments, records


def _allocate_counts(group_sizes: list[int], total: int) -> list[int]:
    if not group_sizes or total <= 0:
        return []
    total = min(total, sum(group_sizes))
    base = [min(size, total // len(group_sizes)) for size in group_sizes]
    remaining = total - sum(base)
    index = 0
    while remaining > 0:
        if base[index] < group_sizes[index]:
            base[index] += 1
            remaining -= 1
        index = (index + 1) % len(base)
    return base


def select_camera_stratified_contiguous(records: list[ImageRecord], max_images: int) -> list[ImageRecord]:
    groups: dict[int, list[ImageRecord]] = {}
    camera_order: list[int] = []
    for record in records:
        if record.camera_id not in groups:
            groups[record.camera_id] = []
            camera_order.append(record.camera_id)
        groups[record.camera_id].append(record)

    counts = _allocate_counts([len(groups[camera_id]) for camera_id in camera_order], max_images)
    selected: list[ImageRecord] = []
    for camera_id, count in zip(camera_order, counts):
        selected.extend(groups[camera_id][:count])
    selected_ids = {record.image_id for record in selected}
    return [record for record in records if record.image_id in selected_ids]


def select_evenly_spaced(records: list[ImageRecord], max_images: int) -> list[ImageRecord]:
    if max_images >= len(records):
        return list(records)
    if max_images <= 1:
        return records[:1]
    indexes = sorted({round(i * (len(records) - 1) / (max_images - 1)) for i in range(max_images)})
    while len(indexes) < max_images:
        for candidate in range(len(records)):
            if candidate not in indexes:
                indexes.append(candidate)
                break
    return [records[index] for index in sorted(indexes[:max_images])]


def select_records(records: list[ImageRecord], max_images: int, selection: str) -> list[ImageRecord]:
    if max_images <= 0:
        raise ValueError("--max-images must be positive")
    if selection == "evenly-spaced":
        return select_evenly_spaced(records, max_images)
    return select_camera_stratified_contiguous(records, max_images)


def write_images_txt(output_path: Path, comments: list[str], selected: list[ImageRecord], kept_point_ids: set[int]) -> None:
    lines: list[str] = []
    lines.extend(comments[:3])
    lines.append(f"# Number of images: {len(selected)}\n")
    for record in selected:
        rewritten_points: list[str] = []
        tokens = record.points2d.split()
        for index in range(0, len(tokens), 3):
            if index + 2 >= len(tokens):
                break
            point_id = int(tokens[index + 2])
            if point_id != -1 and point_id not in kept_point_ids:
                point_id = -1
            rewritten_points.extend((tokens[index], tokens[index + 1], str(point_id)))
        lines.append(record.header + "\n")
        lines.append(" ".join(rewritten_points) + "\n")
    output_path.write_text("".join(lines), encoding="utf-8")


def filter_points3d(
    input_path: Path,
    output_path: Path,
    selected_image_ids: set[int],
    min_track_length: int,
) -> tuple[set[int], int]:
    comments: list[str] = []
    kept_lines: list[str] = []
    kept_ids: set[int] = set()
    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#") or not line.strip():
                comments.append(line)
                continue
            tokens = line.split()
            point_id = int(tokens[0])
            track_tokens = tokens[8:]
            filtered_track: list[str] = []
            for index in range(0, len(track_tokens), 2):
                if index + 1 >= len(track_tokens):
                    break
                image_id = int(track_tokens[index])
                if image_id in selected_image_ids:
                    filtered_track.extend((track_tokens[index], track_tokens[index + 1]))
            if len(filtered_track) // 2 >= min_track_length:
                kept_ids.add(point_id)
                kept_lines.append(" ".join(tokens[:8] + filtered_track) + "\n")

    header = comments[:3] + [f"# Number of points: {len(kept_lines)}\n"]
    output_path.write_text("".join(header + kept_lines), encoding="utf-8")
    return kept_ids, len(kept_lines)


def filter_frames(input_path: Path, output_path: Path, selected_image_ids: set[int]) -> int:
    if not input_path.exists():
        return 0
    comments: list[str] = []
    kept_lines: list[str] = []
    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#") or not line.strip():
                comments.append(line)
                continue
            tokens = line.split()
            if len(tokens) < 10:
                continue
            prefix = tokens[:9]
            data_tokens = tokens[10:]
            kept_data: list[str] = []
            for index in range(0, len(data_tokens), 3):
                if index + 2 >= len(data_tokens):
                    break
                if int(data_tokens[index + 2]) in selected_image_ids:
                    kept_data.extend(data_tokens[index : index + 3])
            if kept_data:
                kept_lines.append(" ".join(prefix + [str(len(kept_data) // 3)] + kept_data) + "\n")
    header = comments[:3] + [f"# Number of frames: {len(kept_lines)}\n"]
    output_path.write_text("".join(header + kept_lines), encoding="utf-8")
    return len(kept_lines)


def copy_selected_images(source_images_dir: Path, output_images_dir: Path, selected: list[ImageRecord]) -> tuple[int, list[str]]:
    output_images_dir.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    copied = 0
    for record in selected:
        source = source_images_dir / record.name
        if not source.exists():
            missing.append(record.name)
            continue
        shutil.copy2(source, output_images_dir / record.name)
        copied += 1
    return copied, missing


def prepare_sample(
    *,
    input_colmap_dir: Path,
    output_colmap_dir: Path,
    max_images: int,
    selection: str,
    min_track_length: int,
    source_images_dir: Path | None = None,
) -> dict[str, object]:
    input_sparse = sparse_dir(input_colmap_dir)
    target_sparse = output_sparse_dir(output_colmap_dir)
    if target_sparse.exists():
        shutil.rmtree(target_sparse)
    target_sparse.mkdir(parents=True, exist_ok=True)

    comments, records = read_image_records(input_sparse / "images.txt")
    selected = select_records(records, max_images, selection)
    selected_image_ids = {record.image_id for record in selected}
    kept_point_ids, kept_point_count = filter_points3d(
        input_sparse / "points3D.txt",
        target_sparse / "points3D.txt",
        selected_image_ids,
        min_track_length,
    )
    write_images_txt(target_sparse / "images.txt", comments, selected, kept_point_ids)

    for file_name in ("cameras.txt", "rigs.txt"):
        source = input_sparse / file_name
        if source.exists():
            shutil.copy2(source, target_sparse / file_name)
    frame_count = filter_frames(input_sparse / "frames.txt", target_sparse / "frames.txt", selected_image_ids)

    copied_images = 0
    missing_images: list[str] = []
    if source_images_dir:
        copied_images, missing_images = copy_selected_images(
            source_images_dir,
            output_colmap_dir / "images",
            selected,
        )

    camera_counts: dict[str, int] = {}
    for record in selected:
        camera_counts[str(record.camera_id)] = camera_counts.get(str(record.camera_id), 0) + 1

    return {
        "artifact_kind": "colmap_training_sample_report",
        "input_colmap_dir": str(input_sparse),
        "output_colmap_dir": str(output_colmap_dir),
        "selection": selection,
        "max_images": max_images,
        "source_image_count": len(records),
        "selected_image_count": len(selected),
        "selected_camera_counts": camera_counts,
        "selected_image_ids": [record.image_id for record in selected],
        "selected_image_names": [record.name for record in selected],
        "min_track_length": min_track_length,
        "kept_points3d": kept_point_count,
        "kept_frames": frame_count,
        "copied_images": copied_images,
        "missing_images": missing_images,
        "decision": "pass" if selected and kept_point_count > 0 and not missing_images else "needs_attention",
    }


def main() -> int:
    args = parse_args()
    report = prepare_sample(
        input_colmap_dir=Path(args.input_colmap_dir),
        output_colmap_dir=Path(args.output_colmap_dir),
        max_images=args.max_images,
        selection=args.selection,
        min_track_length=args.min_track_length,
        source_images_dir=Path(args.source_images_dir) if args.source_images_dir else None,
    )
    Path(args.report_json_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report_json_output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["decision"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
