#!/usr/bin/env python3
"""Run a local COLMAP reducer canary from independent leaf sparse models."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class ModelStats:
    registered_images: int
    points3d: int
    image_names: set[str]


@dataclass(frozen=True)
class SimilarityTransform:
    scale: float
    rotation: np.ndarray
    translation: np.ndarray
    residuals: list[float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--leaf",
        action="append",
        required=True,
        help="Local COLMAP text model directory. Pass once per independent leaf.",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report-json-output", required=True)
    parser.add_argument("--min-retention-ratio", type=float, default=0.95)
    parser.add_argument("--min-shared-images", type=int, default=8)
    parser.add_argument("--colmap-bin", default="colmap")
    return parser.parse_args()


def non_comment_lines(path: Path) -> Iterable[str]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                yield stripped


def image_records(images_path: Path) -> list[list[str]]:
    records: list[list[str]] = []
    image_line = True
    for line in non_comment_lines(images_path):
        parts = line.split()
        if image_line and len(parts) >= 10:
            records.append(parts)
        image_line = not image_line
    return records


def image_record_pairs(images_path: Path) -> list[tuple[list[str], str]]:
    pairs: list[tuple[list[str], str]] = []
    current: list[str] | None = None
    with images_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split()
            if current is None and len(parts) >= 10:
                current = parts
                continue
            if current is not None:
                pairs.append((current, stripped))
                current = None
    return pairs


def image_id_to_name(images_path: Path) -> dict[int, str]:
    return {int(parts[0]): parts[9] for parts in image_records(images_path)}


def stats_for_model(model_dir: Path) -> ModelStats:
    images = image_records(model_dir / "images.txt")
    names = {parts[9] for parts in images}
    points = sum(1 for _ in non_comment_lines(model_dir / "points3D.txt"))
    return ModelStats(registered_images=len(images), points3d=points, image_names=names)


def point_id_range(points_path: Path) -> tuple[int, int]:
    ids = [int(line.split()[0]) for line in non_comment_lines(points_path)]
    return (min(ids), max(ids)) if ids else (0, 0)


def camera_signatures(model_dirs: list[Path]) -> tuple[dict[tuple[str, ...], int], dict[Path, dict[int, int]]]:
    signature_to_id: dict[tuple[str, ...], int] = {}
    per_model: dict[Path, dict[int, int]] = {}
    for model_dir in model_dirs:
        camera_map: dict[int, int] = {}
        for line in non_comment_lines(model_dir / "cameras.txt"):
            parts = line.split()
            if len(parts) < 4:
                continue
            old_camera_id = int(parts[0])
            signature = tuple(parts[1:])
            if signature not in signature_to_id:
                signature_to_id[signature] = len(signature_to_id) + 1
            camera_map[old_camera_id] = signature_to_id[signature]
        per_model[model_dir] = camera_map
    return signature_to_id, per_model


def global_image_ids(model_dirs: list[Path]) -> dict[str, int]:
    names: set[str] = set()
    for model_dir in model_dirs:
        names.update(stats_for_model(model_dir).image_names)
    return {name: index + 1 for index, name in enumerate(sorted(names))}


def copy_header_lines(source_path: Path) -> list[str]:
    headers: list[str] = []
    if not source_path.exists():
        return headers
    with source_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith("#") or not line.strip():
                headers.append(line)
            else:
                break
    return headers


def qvec_to_rotmat(qvec: Iterable[float]) -> np.ndarray:
    qw, qx, qy, qz = [float(value) for value in qvec]
    return np.array(
        [
            [1 - 2 * qy * qy - 2 * qz * qz, 2 * qx * qy - 2 * qz * qw, 2 * qx * qz + 2 * qy * qw],
            [2 * qx * qy + 2 * qz * qw, 1 - 2 * qx * qx - 2 * qz * qz, 2 * qy * qz - 2 * qx * qw],
            [2 * qx * qz - 2 * qy * qw, 2 * qy * qz + 2 * qx * qw, 1 - 2 * qx * qx - 2 * qy * qy],
        ],
        dtype=float,
    )


def rotmat_to_qvec(rotmat: np.ndarray) -> list[float]:
    matrix = np.asarray(rotmat, dtype=float)
    trace = float(np.trace(matrix))
    if trace > 0.0:
        scale = math.sqrt(trace + 1.0) * 2.0
        qw = 0.25 * scale
        qx = (matrix[2, 1] - matrix[1, 2]) / scale
        qy = (matrix[0, 2] - matrix[2, 0]) / scale
        qz = (matrix[1, 0] - matrix[0, 1]) / scale
    else:
        axis = int(np.argmax(np.diag(matrix)))
        if axis == 0:
            scale = math.sqrt(1.0 + matrix[0, 0] - matrix[1, 1] - matrix[2, 2]) * 2.0
            qw = (matrix[2, 1] - matrix[1, 2]) / scale
            qx = 0.25 * scale
            qy = (matrix[0, 1] + matrix[1, 0]) / scale
            qz = (matrix[0, 2] + matrix[2, 0]) / scale
        elif axis == 1:
            scale = math.sqrt(1.0 + matrix[1, 1] - matrix[0, 0] - matrix[2, 2]) * 2.0
            qw = (matrix[0, 2] - matrix[2, 0]) / scale
            qx = (matrix[0, 1] + matrix[1, 0]) / scale
            qy = 0.25 * scale
            qz = (matrix[1, 2] + matrix[2, 1]) / scale
        else:
            scale = math.sqrt(1.0 + matrix[2, 2] - matrix[0, 0] - matrix[1, 1]) * 2.0
            qw = (matrix[1, 0] - matrix[0, 1]) / scale
            qx = (matrix[0, 2] + matrix[2, 0]) / scale
            qy = (matrix[1, 2] + matrix[2, 1]) / scale
            qz = 0.25 * scale
    qvec = np.array([qw, qx, qy, qz], dtype=float)
    qvec = qvec / np.linalg.norm(qvec)
    if qvec[0] < 0:
        qvec = -qvec
    return [float(value) for value in qvec]


def camera_center(image_parts: list[str]) -> np.ndarray:
    rotation = qvec_to_rotmat(float(value) for value in image_parts[1:5])
    translation = np.array([float(value) for value in image_parts[5:8]], dtype=float)
    return -rotation.T @ translation


def estimate_similarity(source: np.ndarray, target: np.ndarray) -> SimilarityTransform:
    if source.shape != target.shape or source.shape[0] < 3:
        raise ValueError("at least three shared camera centers are required for similarity alignment")
    source_mean = source.mean(axis=0)
    target_mean = target.mean(axis=0)
    source_centered = source - source_mean
    target_centered = target - target_mean
    covariance = (target_centered.T @ source_centered) / source.shape[0]
    u_matrix, singular_values, vt_matrix = np.linalg.svd(covariance)
    sign = np.sign(np.linalg.det(u_matrix @ vt_matrix))
    diagonal = np.diag([1.0, 1.0, sign])
    rotation = u_matrix @ diagonal @ vt_matrix
    variance = float(np.mean(np.sum(source_centered * source_centered, axis=1)))
    scale = float(np.trace(np.diag(singular_values) @ diagonal) / variance)
    translation = target_mean - scale * rotation @ source_mean
    aligned = (scale * (rotation @ source.T)).T + translation
    residuals = [float(np.linalg.norm(left - right)) for left, right in zip(aligned, target)]
    return SimilarityTransform(scale=scale, rotation=rotation, translation=translation, residuals=residuals)


def transform_point(parts: list[str], transform: SimilarityTransform) -> list[str]:
    point = np.array([float(parts[1]), float(parts[2]), float(parts[3])], dtype=float)
    transformed = transform.scale * transform.rotation @ point + transform.translation
    return [parts[0], *[format_float(value) for value in transformed], *parts[4:]]


def transform_image_parts(parts: list[str], transform: SimilarityTransform) -> list[str]:
    old_rotation = qvec_to_rotmat(float(value) for value in parts[1:5])
    old_center = camera_center(parts)
    new_center = transform.scale * transform.rotation @ old_center + transform.translation
    new_rotation = old_rotation @ transform.rotation.T
    new_translation = -new_rotation @ new_center
    return [
        parts[0],
        *[format_float(value) for value in rotmat_to_qvec(new_rotation)],
        *[format_float(value) for value in new_translation],
        *parts[8:],
    ]


def format_float(value: float) -> str:
    return f"{value:.12g}"


def write_pose_aligned_merge(
    *,
    normalized_dirs: list[Path],
    output_dir: Path,
    min_shared_images: int,
) -> dict[str, object]:
    anchor = normalized_dirs[0]
    output_dir.mkdir(parents=True, exist_ok=True)
    anchor_pairs = image_record_pairs(anchor / "images.txt")
    anchor_by_name = {parts[9]: (parts, points_line) for parts, points_line in anchor_pairs}
    emitted_names = set(anchor_by_name)
    transforms: list[dict[str, object]] = []
    additional_image_lines: list[tuple[list[str], str, dict[int, int]]] = []
    additional_points_lines: list[str] = []
    next_point_id = point_id_range(anchor / "points3D.txt")[1] + 1

    pending_leaf_dirs = list(enumerate(normalized_dirs[1:], start=1))
    while pending_leaf_dirs:
        ranked_leaf_dirs: list[tuple[int, int, Path, dict[str, tuple[list[str], str]], list[str]]] = []
        for leaf_index, leaf_dir in pending_leaf_dirs:
            leaf_pairs = image_record_pairs(leaf_dir / "images.txt")
            leaf_by_name = {parts[9]: (parts, points_line) for parts, points_line in leaf_pairs}
            shared_names = sorted(set(anchor_by_name).intersection(leaf_by_name))
            ranked_leaf_dirs.append((-len(shared_names), leaf_index, leaf_dir, leaf_by_name, shared_names))
        ranked_leaf_dirs.sort()
        shared_count = -ranked_leaf_dirs[0][0]
        if shared_count < min_shared_images:
            leaf_summaries = [
                {"leaf_index": leaf_index, "shared_registered_images": -negative_shared_count}
                for negative_shared_count, leaf_index, _, _, _ in ranked_leaf_dirs
            ]
            raise RuntimeError(
                f"unable to continue chained pose-aligned merge; best remaining leaf has "
                f"{shared_count} shared registered images, minimum is {min_shared_images}: {leaf_summaries}"
            )
        _, leaf_index, leaf_dir, leaf_by_name, shared_names = ranked_leaf_dirs[0]
        pending_leaf_dirs = [
            (candidate_index, candidate_dir)
            for candidate_index, candidate_dir in pending_leaf_dirs
            if candidate_index != leaf_index
        ]
        leaf_pairs = image_record_pairs(leaf_dir / "images.txt")
        source = np.array([camera_center(leaf_by_name[name][0]) for name in shared_names], dtype=float)
        target = np.array([camera_center(anchor_by_name[name][0]) for name in shared_names], dtype=float)
        transform = estimate_similarity(source, target)
        residuals = sorted(transform.residuals)
        point_map: dict[int, int] = {}
        leaf_image_id_to_name = image_id_to_name(leaf_dir / "images.txt")
        for line in non_comment_lines(leaf_dir / "points3D.txt"):
            parts = line.split()
            track: list[str] = []
            for offset in range(8, len(parts), 2):
                if offset + 1 >= len(parts):
                    break
                image_id = int(parts[offset])
                image_name = leaf_image_id_to_name.get(image_id, "")
                if image_name and image_name not in emitted_names:
                    track.extend((str(image_id), parts[offset + 1]))
            if len(track) < 4:
                continue
            old_point_id = int(parts[0])
            new_point_id = next_point_id
            next_point_id += 1
            point_map[old_point_id] = new_point_id
            transformed_parts = transform_point(parts, transform)
            transformed_parts[0] = str(new_point_id)
            additional_points_lines.append(" ".join([*transformed_parts[:8], *track]) + "\n")

        for parts, points_line in leaf_pairs:
            image_name = parts[9]
            if image_name in emitted_names:
                continue
            transformed_parts = transform_image_parts(parts, transform)
            rewritten_points: list[str] = []
            point_parts = points_line.split()
            for offset in range(0, len(point_parts), 3):
                if offset + 2 >= len(point_parts):
                    break
                old_point_id = int(float(point_parts[offset + 2]))
                new_point_id = point_map.get(old_point_id, -1)
                rewritten_points.extend((point_parts[offset], point_parts[offset + 1], str(new_point_id)))
            additional_image_lines.append((transformed_parts, " ".join(rewritten_points), point_map))
            emitted_names.add(image_name)
            anchor_by_name[image_name] = (transformed_parts, " ".join(rewritten_points))

        transforms.append(
            {
                "leaf_index": leaf_index,
                "shared_registered_images": len(shared_names),
                "scale": round(transform.scale, 8),
                "alignment_error_m": {
                    "min": round(residuals[0], 4),
                    "median": round(float(np.median(residuals)), 4),
                    "p95": round(residuals[min(math.ceil(0.95 * len(residuals)) - 1, len(residuals) - 1)], 4),
                    "max": round(residuals[-1], 4),
                },
                "new_points_kept": len(point_map),
            }
        )

    shutil.copy2(anchor / "cameras.txt", output_dir / "cameras.txt")
    if (anchor / "rigs.txt").exists():
        shutil.copy2(anchor / "rigs.txt", output_dir / "rigs.txt")
    anchor_point_lines = list(non_comment_lines(anchor / "points3D.txt"))
    with (output_dir / "images.txt").open("w", encoding="utf-8") as target:
        target.write("# Image list with two lines of data per image:\n")
        target.write("#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        target.write("#   POINTS2D[] as (X, Y, POINT3D_ID)\n")
        for parts, points_line in anchor_pairs:
            target.write(" ".join(parts) + "\n")
            target.write(points_line + "\n")
        for parts, points_line, _ in additional_image_lines:
            target.write(" ".join(parts) + "\n")
            target.write(points_line + "\n")
    all_image_parts = [parts for parts, _ in anchor_pairs] + [parts for parts, _, _ in additional_image_lines]
    with (output_dir / "frames.txt").open("w", encoding="utf-8") as target:
        target.write("# Frame list with one line of data per frame:\n")
        target.write(
            "#   FRAME_ID, RIG_ID, RIG_FROM_WORLD[QW, QX, QY, QZ, TX, TY, TZ], "
            "NUM_DATA_IDS, DATA_IDS[] as (SENSOR_TYPE, SENSOR_ID, DATA_ID)\n"
        )
        target.write(f"# Number of frames: {len(all_image_parts)}\n")
        for parts in all_image_parts:
            image_id = parts[0]
            camera_id = parts[8]
            target.write(
                " ".join(
                    [
                        image_id,
                        "1",
                        *parts[1:8],
                        "1",
                        "CAMERA",
                        camera_id,
                        image_id,
                    ]
                )
                + "\n"
            )
    with (output_dir / "points3D.txt").open("w", encoding="utf-8") as target:
        target.write("# 3D point list with one line of data per point:\n")
        target.write("#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
        target.write(f"# Number of points: {len(anchor_point_lines) + len(additional_points_lines)}\n")
        for line in anchor_point_lines:
            target.write(line + "\n")
        target.writelines(additional_points_lines)
    return {"strategy": "pose_aligned_text_merge", "transforms": transforms}


def rewrite_model_text(
    *,
    input_dir: Path,
    output_dir: Path,
    image_ids_by_name: dict[str, int],
    camera_ids_by_old_id: dict[int, int],
    global_camera_records: dict[int, list[str]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    old_to_new_image_ids: dict[int, int] = {}

    with (output_dir / "cameras.txt").open("w", encoding="utf-8") as target:
        for line in copy_header_lines(input_dir / "cameras.txt"):
            target.write(line)
        for camera_id in sorted(global_camera_records):
            target.write(" ".join([str(camera_id), *global_camera_records[camera_id]]) + "\n")

    image_line = True
    with (input_dir / "images.txt").open("r", encoding="utf-8", errors="replace") as source, (
        output_dir / "images.txt"
    ).open("w", encoding="utf-8") as target:
        for line in source:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                target.write(line)
                continue
            parts = stripped.split()
            if image_line and len(parts) >= 10:
                image_name = parts[9]
                old_image_id = int(parts[0])
                old_camera_id = int(parts[8])
                new_image_id = image_ids_by_name[image_name]
                new_camera_id = camera_ids_by_old_id[old_camera_id]
                old_to_new_image_ids[old_image_id] = new_image_id
                parts[0] = str(new_image_id)
                parts[8] = str(new_camera_id)
                target.write(" ".join(parts) + "\n")
            else:
                target.write(line)
            image_line = not image_line

    with (input_dir / "points3D.txt").open("r", encoding="utf-8", errors="replace") as source, (
        output_dir / "points3D.txt"
    ).open("w", encoding="utf-8") as target:
        for line in source:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                target.write(line)
                continue
            parts = stripped.split()
            rewritten_track: list[str] = []
            for offset in range(8, len(parts), 2):
                if offset + 1 >= len(parts):
                    break
                old_image_id = int(parts[offset])
                new_image_id = old_to_new_image_ids.get(old_image_id)
                if new_image_id is not None:
                    rewritten_track.extend((str(new_image_id), parts[offset + 1]))
            if len(rewritten_track) >= 4:
                target.write(" ".join([*parts[:8], *rewritten_track]) + "\n")

    frames_path = input_dir / "frames.txt"
    if frames_path.exists():
        with frames_path.open("r", encoding="utf-8", errors="replace") as source, (
            output_dir / "frames.txt"
        ).open("w", encoding="utf-8") as target:
            for line in source:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    target.write(line)
                    continue
                parts = stripped.split()
                if len(parts) >= 10:
                    try:
                        num_data_ids = int(parts[9])
                    except ValueError:
                        num_data_ids = 0
                    offset = 10
                    for _ in range(num_data_ids):
                        if offset + 2 >= len(parts):
                            break
                        old_image_id = int(parts[offset + 2])
                        if old_image_id in old_to_new_image_ids:
                            parts[offset + 2] = str(old_to_new_image_ids[old_image_id])
                        offset += 3
                target.write(" ".join(parts) + "\n")

    for source_file in input_dir.iterdir():
        if source_file.name in {"cameras.txt", "images.txt", "points3D.txt", "frames.txt"}:
            continue
        if source_file.is_file():
            shutil.copy2(source_file, output_dir / source_file.name)


def run_command(command: list[str]) -> dict[str, object]:
    started = time.time()
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    return {
        "command": command,
        "returncode": result.returncode,
        "seconds": round(time.time() - started, 2),
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }


def main() -> int:
    args = parse_args()
    leaf_dirs = [Path(item).resolve() for item in args.leaf]
    output_dir = Path(args.output_dir).resolve()
    normalized_root = output_dir / "normalized"
    binary_root = output_dir / "binary"
    merged_binary = output_dir / "merged_binary"
    merged_text = output_dir / "merged_text"
    fallback_text = output_dir / "pose_aligned_text"
    fallback_validation_binary = output_dir / "pose_aligned_binary"
    report_path = Path(args.report_json_output)

    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    before = [stats_for_model(model_dir) for model_dir in leaf_dirs]
    image_ids = global_image_ids(leaf_dirs)
    signature_to_id, camera_maps = camera_signatures(leaf_dirs)
    global_camera_records = {camera_id: list(signature) for signature, camera_id in signature_to_id.items()}

    convert_commands: list[dict[str, object]] = []
    normalized_dirs: list[Path] = []
    binary_dirs: list[Path] = []
    for index, model_dir in enumerate(leaf_dirs):
        normalized_dir = normalized_root / f"leaf-{index:02d}"
        binary_dir = binary_root / f"leaf-{index:02d}"
        rewrite_model_text(
            input_dir=model_dir,
            output_dir=normalized_dir,
            image_ids_by_name=image_ids,
            camera_ids_by_old_id=camera_maps[model_dir],
            global_camera_records=global_camera_records,
        )
        normalized_dirs.append(normalized_dir)
        binary_dir.mkdir(parents=True, exist_ok=True)
        command_result = run_command(
            [
                args.colmap_bin,
                "model_converter",
                "--input_path",
                str(normalized_dir),
                "--output_path",
                str(binary_dir),
                "--output_type",
                "BIN",
            ]
        )
        convert_commands.append(command_result)
        binary_dirs.append(binary_dir)
        if command_result["returncode"] != 0:
            break

    merge_command: dict[str, object] | None = None
    convert_merged_command: dict[str, object] | None = None
    fallback_report: dict[str, object] | None = None
    fallback_validation_command: dict[str, object] | None = None
    if all(command["returncode"] == 0 for command in convert_commands):
        if len(binary_dirs) == 2:
            merged_binary.mkdir(parents=True, exist_ok=True)
            merge_command = run_command(
                [
                    args.colmap_bin,
                    "model_merger",
                    "--input_path1",
                    str(binary_dirs[0]),
                    "--input_path2",
                    str(binary_dirs[1]),
                    "--output_path",
                    str(merged_binary),
                    "--max_reproj_error",
                    "64",
                ]
            )
        else:
            merge_command = {
                "command": ["colmap", "model_merger"],
                "returncode": 64,
                "seconds": 0.0,
                "stdout_tail": "",
                "stderr_tail": "stock model_merger skipped: more than two independent leaf models",
            }
        if merge_command["returncode"] == 0:
            merged_text.mkdir(parents=True, exist_ok=True)
            convert_merged_command = run_command(
                [
                    args.colmap_bin,
                    "model_converter",
                    "--input_path",
                    str(merged_binary),
                    "--output_path",
                    str(merged_text),
                    "--output_type",
                    "TXT",
                ]
            )
        else:
            try:
                fallback_report = write_pose_aligned_merge(
                    normalized_dirs=normalized_dirs,
                    output_dir=fallback_text,
                    min_shared_images=args.min_shared_images,
                )
                fallback_validation_binary.mkdir(parents=True, exist_ok=True)
                fallback_validation_command = run_command(
                    [
                        args.colmap_bin,
                        "model_converter",
                        "--input_path",
                        str(fallback_text),
                        "--output_path",
                        str(fallback_validation_binary),
                        "--output_type",
                        "BIN",
                    ]
                )
            except Exception as exc:  # pragma: no cover - surfaced in JSON report
                fallback_report = {"strategy": "pose_aligned_text_merge", "error": str(exc)}

    effective_merged_text = merged_text if (merged_text / "images.txt").exists() else fallback_text
    merged = (
        stats_for_model(effective_merged_text)
        if (effective_merged_text / "images.txt").exists()
        else ModelStats(0, 0, set())
    )
    leaf_retention = [
        round(len(merged.image_names.intersection(stats.image_names)) / stats.registered_images, 4)
        if stats.registered_images
        else 0.0
        for stats in before
    ]
    shared_before = len(before[0].image_names.intersection(before[1].image_names)) if len(before) >= 2 else 0
    unique_before = len(set().union(*(stats.image_names for stats in before)))
    blockers: list[str] = []
    if any(command["returncode"] != 0 for command in convert_commands):
        blockers.append("leaf_model_converter_failed")
    fallback_succeeded = (
        fallback_report is not None
        and "error" not in fallback_report
        and fallback_validation_command is not None
        and fallback_validation_command["returncode"] == 0
    )
    if (merge_command is None or merge_command["returncode"] != 0) and not fallback_succeeded:
        blockers.append("model_merger_failed")
    if fallback_report is not None and "error" in fallback_report:
        blockers.append("pose_aligned_merge_failed")
    if fallback_validation_command is not None and fallback_validation_command["returncode"] != 0:
        blockers.append("pose_aligned_model_validation_failed")
    if convert_merged_command is not None and convert_merged_command["returncode"] != 0:
        blockers.append("merged_model_converter_failed")
    if shared_before < args.min_shared_images:
        blockers.append("insufficient_shared_images")
    if leaf_retention and min(leaf_retention) < args.min_retention_ratio:
        blockers.append("leaf_retention_below_gate")
    if merged.registered_images < max((stats.registered_images for stats in before), default=0):
        blockers.append("merged_model_lost_dominant_leaf")

    report = {
        "schema_version": 1,
        "artifact_kind": "sfm_reducer_canary_report",
        "decision": "pass" if not blockers else "fail",
        "leaf_inputs": [str(path) for path in leaf_dirs],
        "output_dir": str(output_dir),
        "leaf_count": len(leaf_dirs),
        "input_registered_images": [stats.registered_images for stats in before],
        "input_points3d": [stats.points3d for stats in before],
        "shared_registered_images_before_merge": shared_before,
        "unique_registered_images_before_merge": unique_before,
        "merged_registered_images": merged.registered_images,
        "merged_points3d": merged.points3d,
        "leaf_retention_ratios": leaf_retention,
        "min_retention_ratio": args.min_retention_ratio,
        "min_shared_images": args.min_shared_images,
        "blockers": blockers,
        "commands": {
            "leaf_converters": convert_commands,
            "model_merger": merge_command,
            "merged_converter": convert_merged_command,
            "pose_aligned_validator": fallback_validation_command,
        },
        "fallback": fallback_report,
        "normalized_text_dirs": [str(path) for path in normalized_dirs],
        "binary_dirs": [str(path) for path in binary_dirs],
        "merged_text_dir": str(effective_merged_text),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("decision", "blockers", "merged_registered_images")}, indent=2))
    return 0 if report["decision"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
