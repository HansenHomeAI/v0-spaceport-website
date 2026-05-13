#!/usr/bin/env python3
"""Create a small trainable COLMAP package from a larger COLMAP text model."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
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
    parser.add_argument("--image-max-width", type=int, default=0, help="Optional max copied image width; camera intrinsics are scaled to match.")
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


def count_base_comments(comments: list[str]) -> list[str]:
    return [line for line in comments if not line.startswith("# Number of ")]


def scaled_coordinate(value: str, scale: float) -> str:
    if scale == 1.0:
        return value
    return f"{float(value) * scale:.12g}"


def write_images_txt(
    output_path: Path,
    comments: list[str],
    selected: list[ImageRecord],
    kept_point_ids: set[int],
    camera_scales: dict[int, float],
) -> None:
    lines: list[str] = []
    lines.extend(count_base_comments(comments))
    lines.append(f"# Number of images: {len(selected)}\n")
    for record in selected:
        rewritten_points: list[str] = []
        scale = camera_scales.get(record.camera_id, 1.0)
        tokens = record.points2d.split()
        for index in range(0, len(tokens), 3):
            if index + 2 >= len(tokens):
                break
            point_id = int(tokens[index + 2])
            if point_id != -1 and point_id not in kept_point_ids:
                point_id = -1
            rewritten_points.extend(
                (
                    scaled_coordinate(tokens[index], scale),
                    scaled_coordinate(tokens[index + 1], scale),
                    str(point_id),
                )
            )
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

    header = count_base_comments(comments) + [f"# Number of points: {len(kept_lines)}\n"]
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
    header = count_base_comments(comments) + [f"# Number of frames: {len(kept_lines)}\n"]
    output_path.write_text("".join(header + kept_lines), encoding="utf-8")
    return len(kept_lines)


def camera_param_scale_indexes(model: str) -> tuple[int, ...]:
    model = model.upper()
    if model in {"SIMPLE_PINHOLE", "SIMPLE_RADIAL", "RADIAL", "SIMPLE_RADIAL_FISHEYE", "RADIAL_FISHEYE"}:
        return (0, 1, 2)
    if model in {"PINHOLE", "OPENCV", "OPENCV_FISHEYE", "FULL_OPENCV", "FOV", "THIN_PRISM_FISHEYE"}:
        return (0, 1, 2, 3)
    return ()


def scale_camera_line(line: str, image_max_width: int) -> tuple[str, float]:
    tokens = line.split()
    if len(tokens) < 5 or image_max_width <= 0:
        return line, 1.0

    width = int(tokens[2])
    height = int(tokens[3])
    if width <= image_max_width:
        return line, 1.0

    scale = image_max_width / width
    tokens[2] = str(max(1, int(round(width * scale))))
    tokens[3] = str(max(1, int(round(height * scale))))

    indexes = camera_param_scale_indexes(tokens[1])
    params = tokens[4:]
    for index in indexes:
        if index < len(params):
            params[index] = f"{float(params[index]) * scale:.12g}"
    return " ".join(tokens[:4] + params), scale


def write_cameras_txt(input_path: Path, output_path: Path, image_max_width: int) -> tuple[dict[int, float], int]:
    scales: dict[int, float] = {}
    scaled_count = 0
    comments: list[str] = []
    lines: list[str] = []
    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#") or not line.strip():
                comments.append(line)
                continue
            scaled_line, scale = scale_camera_line(line.strip(), image_max_width)
            camera_id = int(scaled_line.split()[0])
            scales[camera_id] = scale
            if scale < 1.0:
                scaled_count += 1
            lines.append(scaled_line + "\n")
    header = count_base_comments(comments) + [f"# Number of cameras: {len(lines)}\n"]
    output_path.write_text("".join(header + lines), encoding="utf-8")
    return scales, scaled_count


def resize_or_copy_image(source: Path, target: Path, max_width: int) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)
    if max_width <= 0:
        shutil.copy2(source, target)
        return False

    try:
        from PIL import Image  # type: ignore
    except Exception:
        Image = None

    if Image is not None:
        with Image.open(source) as image:
            if image.width <= max_width:
                shutil.copy2(source, target)
                return False
            image.thumbnail((max_width, max_width * 100), Image.Resampling.LANCZOS)
            image.save(target, quality=92)
            shutil.copystat(source, target)
            return True

    sips = shutil.which("sips")
    if not sips:
        raise RuntimeError("image downscale requested but neither Pillow nor sips is available")
    result = subprocess.run([sips, "--resampleWidth", str(max_width), str(source), "--out", str(target)], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"sips failed for {source.name}: {result.stderr.strip() or result.stdout.strip()}")
    shutil.copystat(source, target)
    return True


def copy_selected_images(
    source_images_dir: Path,
    output_images_dir: Path,
    selected: list[ImageRecord],
    *,
    image_max_width: int = 0,
) -> tuple[int, list[str], int]:
    output_images_dir.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    copied = 0
    downscaled = 0
    for record in selected:
        source = source_images_dir / record.name
        if not source.exists():
            missing.append(record.name)
            continue
        if resize_or_copy_image(source, output_images_dir / record.name, image_max_width):
            downscaled += 1
        copied += 1
    return copied, missing, downscaled


def prepare_sample(
    *,
    input_colmap_dir: Path,
    output_colmap_dir: Path,
    max_images: int,
    selection: str,
    min_track_length: int,
    source_images_dir: Path | None = None,
    image_max_width: int = 0,
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
    camera_scales, scaled_camera_count = write_cameras_txt(input_sparse / "cameras.txt", target_sparse / "cameras.txt", image_max_width)
    write_images_txt(target_sparse / "images.txt", comments, selected, kept_point_ids, camera_scales)
    rigs_source = input_sparse / "rigs.txt"
    if rigs_source.exists():
        shutil.copy2(rigs_source, target_sparse / "rigs.txt")
    frame_count = filter_frames(input_sparse / "frames.txt", target_sparse / "frames.txt", selected_image_ids)

    copied_images = 0
    missing_images: list[str] = []
    downscaled_images = 0
    if source_images_dir:
        copied_images, missing_images, downscaled_images = copy_selected_images(
            source_images_dir,
            output_colmap_dir / "images",
            selected,
            image_max_width=image_max_width,
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
        "image_max_width": image_max_width,
        "camera_scales": {str(camera_id): scale for camera_id, scale in sorted(camera_scales.items())},
        "scaled_camera_count": scaled_camera_count,
        "kept_points3d": kept_point_count,
        "kept_frames": frame_count,
        "copied_images": copied_images,
        "downscaled_images": downscaled_images,
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
        image_max_width=args.image_max_width,
    )
    Path(args.report_json_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report_json_output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["decision"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
