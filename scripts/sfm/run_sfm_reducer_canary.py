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
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

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


@dataclass(frozen=True)
class SeamThresholds:
    min_shared_images: int
    max_scale_delta: float
    max_sim3_p95_residual_m: float
    max_baseline_normalized_residual: float
    strict_production_gates: bool = False


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
    parser.add_argument("--min-shared-images", type=int, default=20)
    parser.add_argument("--max-scale-delta", type=float, default=0.15)
    parser.add_argument("--max-sim3-p95-residual-m", type=float, default=0.25)
    parser.add_argument("--max-baseline-normalized-residual", type=float, default=0.01)
    parser.add_argument("--strict-production-gates", action="store_true")
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


def identity_similarity() -> SimilarityTransform:
    return SimilarityTransform(
        scale=1.0,
        rotation=np.eye(3, dtype=float),
        translation=np.zeros(3, dtype=float),
        residuals=[],
    )


def compose_similarity(
    outer: SimilarityTransform,
    inner: SimilarityTransform,
    *,
    residuals: list[float] | None = None,
) -> SimilarityTransform:
    """Return the similarity transform produced by applying inner, then outer."""
    return SimilarityTransform(
        scale=outer.scale * inner.scale,
        rotation=outer.rotation @ inner.rotation,
        translation=outer.scale * (outer.rotation @ inner.translation) + outer.translation,
        residuals=residuals or [],
    )


def transform_points(points: np.ndarray, transform: SimilarityTransform) -> np.ndarray:
    if points.size == 0:
        return points
    return (transform.scale * (transform.rotation @ points.T)).T + transform.translation


def transform_coords(
    coords: list[tuple[float, float, float]],
    transform: SimilarityTransform,
) -> list[tuple[float, float, float]]:
    if not coords:
        return []
    transformed = transform_points(np.array(coords, dtype=float), transform)
    return [(float(point[0]), float(point[1]), float(point[2])) for point in transformed]


def residual_summary(residuals: list[float]) -> dict[str, float | int | None]:
    if not residuals:
        return {"count": 0, "min": None, "p50": None, "p95": None, "max": None}
    ordered = sorted(float(value) for value in residuals)
    return {
        "count": len(ordered),
        "min": round(ordered[0], 6),
        "p50": round(float(np.median(ordered)), 6),
        "p95": round(percentile(ordered, 0.95) or 0.0, 6),
        "max": round(ordered[-1], 6),
    }


def camera_distribution_stats(points: np.ndarray) -> dict[str, object]:
    if points.size == 0 or points.shape[0] < 2:
        return {
            "rank": 0,
            "baseline_m": 0.0,
            "singular_values": [],
            "normalized_singular_values": [],
        }
    centered = points - points.mean(axis=0)
    singular_values = np.linalg.svd(centered, compute_uv=False)
    largest = float(singular_values[0]) if len(singular_values) else 0.0
    rank = int(sum(1 for value in singular_values if largest > 0.0 and float(value) / largest > 1e-3))
    min_corner = points.min(axis=0)
    max_corner = points.max(axis=0)
    baseline = float(np.linalg.norm(max_corner - min_corner))
    normalized = [float(value / largest) if largest > 0.0 else 0.0 for value in singular_values]
    return {
        "rank": rank,
        "baseline_m": round(baseline, 6),
        "singular_values": [round(float(value), 6) for value in singular_values],
        "normalized_singular_values": [round(value, 6) for value in normalized],
    }


def candidate_similarity_triplets(count: int) -> list[tuple[int, int, int]]:
    if count < 3:
        return []
    all_indices = range(count)
    if count <= 14:
        return list(combinations(all_indices, 3))
    candidates: set[tuple[int, int, int]] = set()
    third = max(count // 3, 1)
    for offset in range(min(count, 64)):
        candidates.add(tuple(sorted((offset % count, (offset + third) % count, (offset + 2 * third) % count))))
    candidates.add((0, count // 2, count - 1))
    candidates.add((0, max(1, count // 3), max(2, (2 * count) // 3)))
    return [item for item in sorted(candidates) if len(set(item)) == 3]


def estimate_robust_similarity(source: np.ndarray, target: np.ndarray) -> SimilarityTransform:
    if source.shape != target.shape or source.shape[0] < 3:
        raise ValueError("at least three shared camera centers are required for similarity alignment")
    source_layout = camera_distribution_stats(source)
    target_layout = camera_distribution_stats(target)
    if int(source_layout["rank"]) < 2 or int(target_layout["rank"]) < 2:
        transform = estimate_similarity(source, target)
        return transform

    best: tuple[float, float, float, SimilarityTransform] | None = None
    for triplet in candidate_similarity_triplets(source.shape[0]):
        indices = np.array(triplet, dtype=int)
        try:
            candidate = estimate_similarity(source[indices], target[indices])
        except Exception:
            continue
        residuals = sorted(
            float(np.linalg.norm(left - right))
            for left, right in zip(transform_points(source, candidate), target)
        )
        score = (
            float(np.median(residuals)),
            float(percentile(residuals, 0.95) or residuals[-1]),
            float(residuals[-1]),
        )
        if best is None or score < best[:3]:
            best = (*score, candidate)

    if best is None:
        return estimate_similarity(source, target)

    initial = best[3]
    initial_residuals = [
        float(np.linalg.norm(left - right))
        for left, right in zip(transform_points(source, initial), target)
    ]
    median = float(np.median(initial_residuals))
    median_abs_deviation = float(np.median([abs(value - median) for value in initial_residuals]))
    robust_sigma = 1.4826 * median_abs_deviation
    inlier_cutoff = max(0.05, median + max(0.05, robust_sigma * 3.0))
    inlier_indices = [index for index, value in enumerate(initial_residuals) if value <= inlier_cutoff]
    if len(inlier_indices) >= 3:
        try:
            refined = estimate_similarity(source[np.array(inlier_indices)], target[np.array(inlier_indices)])
            aligned = transform_points(source, refined)
            refined_residuals = [float(np.linalg.norm(left - right)) for left, right in zip(aligned, target)]
            return SimilarityTransform(
                scale=refined.scale,
                rotation=refined.rotation,
                translation=refined.translation,
                residuals=refined_residuals,
            )
        except Exception:
            pass

    aligned = transform_points(source, initial)
    return SimilarityTransform(
        scale=initial.scale,
        rotation=initial.rotation,
        translation=initial.translation,
        residuals=[float(np.linalg.norm(left - right)) for left, right in zip(aligned, target)],
    )


def heldout_similarity_residual(
    source: np.ndarray,
    target: np.ndarray,
) -> dict[str, object]:
    if source.shape[0] < 5:
        return {"status": "not_run", "reason": "requires_at_least_5_shared_cameras"}
    heldout_indices = [index for index in range(source.shape[0]) if index % 5 == 0]
    train_indices = [index for index in range(source.shape[0]) if index not in set(heldout_indices)]
    if len(train_indices) < 3 or not heldout_indices:
        return {"status": "not_run", "reason": "insufficient_train_or_heldout_shared_cameras"}
    try:
        train_transform = estimate_robust_similarity(source[np.array(train_indices)], target[np.array(train_indices)])
    except Exception as exc:
        return {"status": "failed", "reason": str(exc)}
    aligned = transform_points(source[np.array(heldout_indices)], train_transform)
    residuals = [float(np.linalg.norm(left - right)) for left, right in zip(aligned, target[np.array(heldout_indices)])]
    return {
        "status": "pass",
        "heldout_count": len(heldout_indices),
        "train_count": len(train_indices),
        "residual_m": residual_summary(residuals),
    }


def axis_surface_overlap_stats(
    existing_points: list[tuple[float, float, float]],
    incoming_points: list[tuple[float, float, float]],
    *,
    projection_axes: tuple[int, int],
    separation_axis: int,
    min_points_per_side: int = 6,
) -> dict[str, object]:
    if not existing_points or not incoming_points:
        return {
            "overlap_cell_count": 0,
            "flagged_overlap_cell_count": 0,
            "flagged_overlap_cell_ratio": 0.0,
            "median_abs_gap_m": None,
            "p95_abs_gap_m": None,
            "max_abs_gap_m": None,
            "examples": [],
        }
    combined = existing_points + incoming_points
    axis_a_values = [point[projection_axes[0]] for point in combined]
    axis_b_values = [point[projection_axes[1]] for point in combined]
    span = max(max(axis_a_values) - min(axis_a_values), max(axis_b_values) - min(axis_b_values), 1.0)
    cell_size = max(span / 80.0, 2.0)
    min_a = min(axis_a_values)
    min_b = min(axis_b_values)

    def group(points: list[tuple[float, float, float]]) -> dict[tuple[int, int], list[float]]:
        cells: dict[tuple[int, int], list[float]] = {}
        for point in points:
            key = (
                int((point[projection_axes[0]] - min_a) / cell_size),
                int((point[projection_axes[1]] - min_b) / cell_size),
            )
            cells.setdefault(key, []).append(point[separation_axis])
        return cells

    existing_cells = group(existing_points)
    incoming_cells = group(incoming_points)
    gaps: list[float] = []
    flagged: list[dict[str, object]] = []
    for key in sorted(set(existing_cells).intersection(incoming_cells)):
        left = existing_cells[key]
        right = incoming_cells[key]
        if len(left) < min_points_per_side or len(right) < min_points_per_side:
            continue
        left_median = float(np.median(left))
        right_median = float(np.median(right))
        gap = abs(left_median - right_median)
        gaps.append(gap)
        left_span = max(left) - min(left)
        right_span = max(right) - min(right)
        tolerance = max(1.5, 0.35 * max(left_span, right_span, cell_size))
        if gap <= tolerance:
            continue
        flagged.append(
            {
                "cell": [key[0], key[1]],
                "existing_count": len(left),
                "incoming_count": len(right),
                "median_gap_m": round(gap, 4),
                "existing_axis_median": round(left_median, 4),
                "incoming_axis_median": round(right_median, 4),
                "tolerance_m": round(tolerance, 4),
            }
        )
    overlap_count = len(gaps)
    return {
        "overlap_cell_count": overlap_count,
        "flagged_overlap_cell_count": len(flagged),
        "flagged_overlap_cell_ratio": round(len(flagged) / overlap_count, 4) if overlap_count else 0.0,
        "median_abs_gap_m": round(float(np.median(gaps)), 4) if gaps else None,
        "p95_abs_gap_m": round(percentile(gaps, 0.95), 4) if gaps else None,
        "max_abs_gap_m": round(max(gaps), 4) if gaps else None,
        "cell_size_m": round(cell_size, 4),
        "examples": sorted(flagged, key=lambda item: (-float(item["median_gap_m"]), item["cell"]))[:20],
    }


def cross_leaf_duplicate_surface_stats(
    existing_points: list[tuple[float, float, float]],
    incoming_points: list[tuple[float, float, float]],
) -> dict[str, object]:
    axes = [
        ("xy_z", (0, 1), 2),
        ("xz_y", (0, 2), 1),
        ("yz_x", (1, 2), 0),
    ]
    reports = {
        name: axis_surface_overlap_stats(
            existing_points,
            incoming_points,
            projection_axes=projection_axes,
            separation_axis=separation_axis,
        )
        for name, projection_axes, separation_axis in axes
    }
    blocking_axis = max(
        reports,
        key=lambda name: (
            float(reports[name].get("flagged_overlap_cell_ratio") or 0.0),
            int(reports[name].get("flagged_overlap_cell_count") or 0),
        ),
    )
    return {
        "axis_reports": reports,
        "blocking_axis": blocking_axis,
        "max_flagged_overlap_cell_ratio": reports[blocking_axis].get("flagged_overlap_cell_ratio"),
        "max_flagged_overlap_cell_count": reports[blocking_axis].get("flagged_overlap_cell_count"),
        "max_overlap_cell_count": reports[blocking_axis].get("overlap_cell_count"),
    }


def edge_confidence(edge: dict[str, object], thresholds: SeamThresholds) -> float:
    shared = float(edge.get("shared_registered_images") or 0)
    residual = ((edge.get("sim3_residual_m") or {}) if isinstance(edge.get("sim3_residual_m"), dict) else {}).get("p95")
    residual_value = float(residual) if residual is not None else thresholds.max_sim3_p95_residual_m * 10.0
    baseline_norm = float(edge.get("baseline_normalized_residual") or thresholds.max_baseline_normalized_residual * 10.0)
    scale_delta = float(edge.get("scale_delta") or thresholds.max_scale_delta * 10.0)
    blockers = len(edge.get("blockers") or [])
    surface_warning = float(edge.get("surface_overlap_warning_score") or 0.0)
    return round(
        shared
        + max(0.0, 1.0 - residual_value / max(thresholds.max_sim3_p95_residual_m, 1e-9)) * 20.0
        + max(0.0, 1.0 - baseline_norm / max(thresholds.max_baseline_normalized_residual, 1e-9)) * 20.0
        + max(0.0, 1.0 - scale_delta / max(thresholds.max_scale_delta, 1e-9)) * 10.0
        - min(surface_warning, 1.0) * 25.0
        - blockers * (100.0 if thresholds.strict_production_gates else 12.0),
        6,
    )


def evaluate_seam_edge(
    *,
    leaf_a: int,
    leaf_b: int,
    leaf_a_by_name: dict[str, tuple[list[str], str]],
    leaf_b_by_name: dict[str, tuple[list[str], str]],
    thresholds: SeamThresholds,
    surface_a: list[tuple[float, float, float]] | None = None,
    surface_b: list[tuple[float, float, float]] | None = None,
    pose_priors: dict[str, tuple[float, float, float]] | None = None,
    image_roles_by_leaf: dict[int, dict[str, str]] | None = None,
) -> tuple[dict[str, object], SimilarityTransform | None]:
    shared_names = sorted(set(leaf_a_by_name).intersection(leaf_b_by_name))
    report: dict[str, object] = {
        "leaf_a": leaf_a,
        "leaf_b": leaf_b,
        "alignment_direction": f"leaf_{leaf_b:02d}_to_leaf_{leaf_a:02d}",
        "shared_registered_images": len(shared_names),
        "shared_image_sample": shared_names[:16],
        "blockers": [],
        "warnings": [],
    }
    blockers: list[str] = []
    warnings: list[str] = []
    if len(shared_names) < thresholds.min_shared_images:
        blockers.append("weak_shared_camera_count")
    if len(shared_names) < 3:
        blockers.append("insufficient_shared_cameras_for_sim3")
        report["decision"] = "reject"
        report["strict_decision"] = "reject"
        report["blockers"] = blockers
        report["confidence"] = edge_confidence(report, thresholds)
        return report, None

    source = np.array([camera_center(leaf_b_by_name[name][0]) for name in shared_names], dtype=float)
    target = np.array([camera_center(leaf_a_by_name[name][0]) for name in shared_names], dtype=float)
    source_layout = camera_distribution_stats(source)
    target_layout = camera_distribution_stats(target)
    report["shared_camera_distribution"] = {
        "source_leaf_b": source_layout,
        "target_leaf_a": target_layout,
        "rank": min(int(source_layout["rank"]), int(target_layout["rank"])),
    }
    if int(source_layout["rank"]) < 2 or int(target_layout["rank"]) < 2:
        blockers.append("degenerate_shared_camera_layout")

    transform: SimilarityTransform | None = None
    try:
        transform = estimate_robust_similarity(source, target)
    except Exception as exc:
        blockers.append("sim3_estimation_failed")
        report["sim3_error"] = str(exc)

    if transform is not None:
        residual_rows = residual_rows_for_shared_cameras(
            shared_names=shared_names,
            residuals=transform.residuals,
            leaf_a=leaf_a,
            leaf_b=leaf_b,
            image_roles_by_leaf=image_roles_by_leaf,
            target_centers=target,
        )
        residual_role_stats = residual_role_report(
            residual_rows,
            thresholds=thresholds,
            target_baseline_m=max(float(target_layout.get("baseline_m") or 0.0), 1e-9),
        )
        inlier_support = seam_inlier_support_report(
            residual_rows,
            threshold_m=thresholds.max_sim3_p95_residual_m,
        )
        residuals = sorted(transform.residuals)
        residual_report = residual_summary(residuals)
        p95 = float(residual_report["p95"] or 0.0)
        baseline = max(float(target_layout.get("baseline_m") or 0.0), 1e-9)
        baseline_normalized = p95 / baseline
        trusted_residual_report = residual_role_stats["trusted_core_involved_residual_m"]
        trusted_p95_raw = (trusted_residual_report if isinstance(trusted_residual_report, dict) else {}).get("p95")
        trusted_p95 = float(trusted_p95_raw) if trusted_p95_raw is not None else p95
        trusted_baseline_raw = residual_role_stats.get("trusted_core_involved_baseline_normalized_residual")
        trusted_baseline_normalized = (
            float(trusted_baseline_raw) if trusted_baseline_raw is not None else baseline_normalized
        )
        trusted_count = int(residual_role_stats.get("trusted_core_involved_count") or 0)
        scale_delta = abs(transform.scale - 1.0)
        report.update(
            {
                "sim3": {
                    "scale": round(transform.scale, 8),
                    "rotation": [[round(float(value), 10) for value in row] for row in transform.rotation.tolist()],
                    "translation": [round(float(value), 6) for value in transform.translation.tolist()],
                },
                "scale_delta": round(scale_delta, 8),
                "sim3_residual_m": residual_report,
                "baseline_normalized_residual": round(baseline_normalized, 8),
                "shared_camera_residual_roles": residual_role_stats,
                "seam_inlier_support": inlier_support,
                "heldout_shared_camera_residual": heldout_similarity_residual(source, target),
            }
        )
        if scale_delta > thresholds.max_scale_delta:
            blockers.append("scale_delta_exceeds_gate")
        p95_blocked = p95 > thresholds.max_sim3_p95_residual_m
        baseline_blocked = baseline_normalized > thresholds.max_baseline_normalized_residual
        trusted_camera_evidence_passes = (
            image_roles_by_leaf is not None
            and trusted_count >= thresholds.min_shared_images
            and trusted_p95 <= thresholds.max_sim3_p95_residual_m
            and trusted_baseline_normalized <= thresholds.max_baseline_normalized_residual
        )
        inlier_count = int(inlier_support.get("inlier_count") or 0)
        inlier_ratio = float(inlier_support.get("inlier_ratio") or 0.0)
        trusted_inlier_count = int(inlier_support.get("trusted_core_involved_inlier_count") or 0)
        inlier_residual_report = inlier_support.get("inlier_residual_m")
        inlier_p95_raw = (inlier_residual_report if isinstance(inlier_residual_report, dict) else {}).get("p95")
        inlier_p95 = float(inlier_p95_raw) if inlier_p95_raw is not None else p95
        inlier_baseline_normalized = inlier_p95 / baseline
        inlier_support["inlier_baseline_normalized_residual"] = round(inlier_baseline_normalized, 8)
        inlier_distribution = inlier_support.get("inlier_camera_distribution")
        inlier_rank = int((inlier_distribution if isinstance(inlier_distribution, dict) else {}).get("rank") or 0)
        inlier_baseline = float(
            (inlier_distribution if isinstance(inlier_distribution, dict) else {}).get("baseline_m") or 0.0
        )
        spatially_supported_inliers = (
            inlier_count >= thresholds.min_shared_images
            and inlier_rank >= 2
            and inlier_baseline >= max(50.0, baseline * 0.05)
        )
        robust_camera_evidence_passes = (
            inlier_count >= thresholds.min_shared_images
            and (inlier_ratio >= 0.5 or spatially_supported_inliers)
            and (image_roles_by_leaf is None or trusted_inlier_count >= max(3, thresholds.min_shared_images // 3))
            and inlier_baseline_normalized <= thresholds.max_baseline_normalized_residual
        )
        if p95_blocked and not trusted_camera_evidence_passes and not robust_camera_evidence_passes:
            blockers.append("sim3_p95_residual_exceeds_gate")
        if baseline_blocked and not trusted_camera_evidence_passes and not robust_camera_evidence_passes:
            blockers.append("baseline_normalized_residual_exceeds_gate")
        if (p95_blocked or baseline_blocked) and trusted_camera_evidence_passes:
            warnings.append("overlap_only_camera_residual_tail_quarantined")
        if (p95_blocked or baseline_blocked) and robust_camera_evidence_passes and not trusted_camera_evidence_passes:
            warnings.append("shared_camera_residual_tail_quarantined_by_inlier_support")
            if inlier_ratio < 0.5:
                warnings.append("low_ratio_tail_quarantined_by_spatial_inlier_support")
        if surface_a is not None and surface_b is not None:
            transformed_b = transform_coords(surface_b, transform)
            report["pre_overlap_surface_stats"] = cross_leaf_duplicate_surface_stats(surface_a, surface_b)
            post_overlap = cross_leaf_duplicate_surface_stats(surface_a, transformed_b)
            report["post_overlap_surface_stats"] = post_overlap
            flagged_ratio = float(post_overlap.get("max_flagged_overlap_cell_ratio") or 0.0)
            if flagged_ratio > 0.02:
                warnings.append("duplicate_surface_overlap_suspect")
                report["surface_overlap_warning_score"] = round(flagged_ratio, 6)

    if transform is not None and pose_priors:
        prior_names = [name for name in shared_names if name in pose_priors]
        if len(prior_names) >= 3:
            prior = np.array([pose_priors[name] for name in prior_names], dtype=float)
            leaf_a_centers = np.array([camera_center(leaf_a_by_name[name][0]) for name in prior_names], dtype=float)
            leaf_b_centers = np.array([camera_center(leaf_b_by_name[name][0]) for name in prior_names], dtype=float)
            leaf_b_transformed = transform_points(leaf_b_centers, transform)
            try:
                leaf_a_to_prior = estimate_robust_similarity(leaf_a_centers, prior)
                leaf_a_prior_frame = transform_points(leaf_a_centers, leaf_a_to_prior)
                leaf_b_prior_frame = transform_points(leaf_b_transformed, leaf_a_to_prior)
            except Exception:
                leaf_a_prior_frame = leaf_a_centers
                leaf_b_prior_frame = leaf_b_transformed
            leaf_a_residuals = sorted(float(np.linalg.norm(left - right)) for left, right in zip(leaf_a_prior_frame, prior))
            leaf_b_residuals = sorted(float(np.linalg.norm(left - right)) for left, right in zip(leaf_b_prior_frame, prior))
            gps_p95 = max(
                float(residual_summary(leaf_a_residuals)["p95"] or 0.0),
                float(residual_summary(leaf_b_residuals)["p95"] or 0.0),
            )
            report["gps_exif_residual"] = {
                "status": "evaluated",
                "frame": "leaf_a_aligned_to_planner_priors",
                "shared_reference_count": len(prior_names),
                "leaf_a_camera_to_prior_m": residual_summary(leaf_a_residuals),
                "leaf_b_transformed_camera_to_prior_m": residual_summary(leaf_b_residuals),
                "max_p95_m": round(gps_p95, 6),
            }
            if thresholds.strict_production_gates and gps_p95 > 50.0:
                blockers.append("gps_exif_residual_exceeds_gate")
        else:
            report["gps_exif_residual"] = {
                "status": "not_evaluated",
                "reason": "fewer_than_three_shared_pose_priors",
                "shared_reference_count": len(prior_names),
            }
    else:
        report["gps_exif_residual"] = {
            "status": "not_available",
            "reason": "planner manifest does not include image_pose_priors_local",
        }
    report["blockers"] = list(dict.fromkeys(blockers))
    report["warnings"] = list(dict.fromkeys(warnings))
    fatal_blockers = {
        "insufficient_shared_cameras_for_sim3",
        "sim3_estimation_failed",
    }
    strict_reject = bool(report["blockers"])
    non_strict_reject = any(blocker in fatal_blockers for blocker in report["blockers"])
    report["decision"] = "reject" if (strict_reject if thresholds.strict_production_gates else non_strict_reject) else "accept"
    report["strict_decision"] = "reject" if strict_reject else "accept"
    report["confidence"] = edge_confidence(report, thresholds)
    return report, transform


def build_seam_merge_graph(
    *,
    normalized_dirs: list[Path],
    thresholds: SeamThresholds,
    planner_manifest: dict[str, Any] | None = None,
) -> dict[str, object]:
    leaf_pairs = [image_record_pairs(path / "images.txt") for path in normalized_dirs]
    leaf_by_name = [{parts[9]: (parts, points_line) for parts, points_line in pairs} for pairs in leaf_pairs]
    surface_points = [point_coords(path / "points3D.txt") for path in normalized_dirs]
    pose_priors = pose_priors_from_planner_manifest(planner_manifest)
    planner_leaf_maps = planner_chunk_leaf_maps(normalized_dirs, planner_manifest)
    image_roles_by_leaf = planner_leaf_maps.get("image_roles_by_leaf")
    if not isinstance(image_roles_by_leaf, dict):
        image_roles_by_leaf = {}
    edge_reports: list[dict[str, object]] = []
    edge_lookup: dict[tuple[int, int], dict[str, object]] = {}
    for leaf_a, leaf_b in combinations(range(len(normalized_dirs)), 2):
        report, _ = evaluate_seam_edge(
            leaf_a=leaf_a,
            leaf_b=leaf_b,
            leaf_a_by_name=leaf_by_name[leaf_a],
            leaf_b_by_name=leaf_by_name[leaf_b],
            thresholds=thresholds,
            surface_a=surface_points[leaf_a],
            surface_b=surface_points[leaf_b],
            pose_priors=pose_priors,
            image_roles_by_leaf=image_roles_by_leaf,
        )
        edge_reports.append(report)
        edge_lookup[(leaf_a, leaf_b)] = report

    parent = list(range(len(normalized_dirs)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> bool:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return False
        parent[right_root] = left_root
        return True

    candidate_edges = [edge for edge in edge_reports if edge.get("decision") == "accept"]
    tree: list[dict[str, object]] = []
    for edge in sorted(candidate_edges, key=lambda item: (-float(item.get("confidence") or 0.0), int(item["leaf_a"]), int(item["leaf_b"]))):
        leaf_a = int(edge["leaf_a"])
        leaf_b = int(edge["leaf_b"])
        if union(leaf_a, leaf_b):
            tree.append(
                {
                    "leaf_a": leaf_a,
                    "leaf_b": leaf_b,
                    "confidence": edge.get("confidence"),
                    "shared_registered_images": edge.get("shared_registered_images"),
                    "strict_decision": edge.get("strict_decision"),
                    "blockers": edge.get("blockers") or [],
                }
            )
        if len(tree) == max(0, len(normalized_dirs) - 1):
            break

    confidence_by_leaf = {index: 0.0 for index in range(len(normalized_dirs))}
    for edge in tree:
        confidence = float(edge.get("confidence") or 0.0)
        confidence_by_leaf[int(edge["leaf_a"])] += confidence
        confidence_by_leaf[int(edge["leaf_b"])] += confidence
    stats = [stats_for_model(path) for path in normalized_dirs]
    root_leaf = min(
        range(len(normalized_dirs)),
        key=lambda index: (-confidence_by_leaf[index], -stats[index].registered_images, index),
    ) if normalized_dirs else 0

    tree_pairs = {tuple(sorted((int(edge["leaf_a"]), int(edge["leaf_b"])))) for edge in tree}
    non_tree_accepted = [
        edge for edge in candidate_edges if tuple(sorted((int(edge["leaf_a"]), int(edge["leaf_b"])))) not in tree_pairs
    ]
    graph_blockers: list[str] = []
    if len(tree) != max(0, len(normalized_dirs) - 1):
        graph_blockers.append("accepted_seam_graph_is_disconnected")
    return {
        "schema_version": 1,
        "artifact_kind": "seam_merge_report",
        "merge_strategy": "seam_graph_sim3_v1",
        "thresholds": {
            "min_shared_images": thresholds.min_shared_images,
            "max_scale_delta": thresholds.max_scale_delta,
            "max_sim3_p95_residual_m": thresholds.max_sim3_p95_residual_m,
            "max_baseline_normalized_residual": thresholds.max_baseline_normalized_residual,
            "strict_production_gates": thresholds.strict_production_gates,
            "gps_exif_p95_residual_m": 50.0,
        },
        "leaf_count": len(normalized_dirs),
        "root_leaf": root_leaf,
        "planner_leaf_mapping": {
            "status": planner_leaf_maps.get("status"),
            "assignments": planner_leaf_maps.get("assignments") or [],
            "leaf_to_chunk_index": {
                str(key): value for key, value in (planner_leaf_maps.get("leaf_to_chunk_index") or {}).items()
            },
        },
        "candidate_edges": edge_reports,
        "accepted_merge_tree": tree,
        "rejected_edges": [edge for edge in edge_reports if edge.get("decision") == "reject"],
        "non_tree_accepted_edges": non_tree_accepted,
        "cycle_consistency": {
            "status": "not_evaluated_until_root_transforms_are_known",
            "non_tree_edge_count": len(non_tree_accepted),
        },
        "post_merge_jurisdiction_culling": {
            "status": "pending",
            "removed_point_count": 0,
            "by_reason": {},
            "records": [],
        },
        "seam_local_ba": {
            "enabled": False,
            "status": "not_run",
            "reason": "local text reducer has no bounded COLMAP BA window implementation yet",
        },
        "promotion_blockers": graph_blockers,
        "decision": "fail" if graph_blockers else "pass",
    }


def transform_point(parts: list[str], transform: SimilarityTransform) -> list[str]:
    point = np.array([float(parts[1]), float(parts[2]), float(parts[3])], dtype=float)
    transformed = transform.scale * transform.rotation @ point + transform.translation
    return [parts[0], *[format_float(value) for value in transformed], *parts[4:]]


def point_coords(points_path: Path) -> list[tuple[float, float, float]]:
    coords: list[tuple[float, float, float]] = []
    for line in non_comment_lines(points_path):
        parts = line.split()
        if len(parts) >= 4:
            coords.append((float(parts[1]), float(parts[2]), float(parts[3])))
    return coords


def track_length_from_parts(parts: list[str]) -> int:
    return max((len(parts) - 8) // 2, 0)


def rewrite_points_line_with_kept_ids(points_line: str, kept_point_ids: set[int]) -> str:
    rewritten: list[str] = []
    point_parts = points_line.split()
    for offset in range(0, len(point_parts), 3):
        if offset + 2 >= len(point_parts):
            break
        point_id = int(float(point_parts[offset + 2]))
        rewritten.extend(
            (
                point_parts[offset],
                point_parts[offset + 1],
                str(point_id if point_id in kept_point_ids else -1),
            )
        )
    return " ".join(rewritten)


def pose_priors_from_planner_manifest(
    planner_manifest: dict[str, Any] | None,
) -> dict[str, tuple[float, float, float]]:
    if not isinstance(planner_manifest, dict):
        return {}
    raw_priors = planner_manifest.get("image_pose_priors_local") or {}
    if not isinstance(raw_priors, dict):
        return {}
    priors: dict[str, tuple[float, float, float]] = {}
    for image_name, payload in raw_priors.items():
        if not isinstance(payload, dict):
            continue
        if "local_x_m" not in payload or "local_y_m" not in payload:
            continue
        priors[str(image_name)] = (
            float(payload["local_x_m"]),
            float(payload["local_y_m"]),
            float(payload.get("local_z_m", 0.0)),
        )
    return priors


def planner_chunk_leaf_maps(
    normalized_dirs: list[Path],
    planner_manifest: dict[str, Any] | None,
) -> dict[str, object]:
    if not isinstance(planner_manifest, dict):
        return {
            "status": "not_available",
            "leaf_to_chunk_index": {},
            "image_roles_by_leaf": {},
            "core_names_by_leaf": {},
        }
    chunks = planner_manifest.get("chunks") or planner_manifest.get("chunk_plans") or []
    if not isinstance(chunks, list):
        return {
            "status": "not_available",
            "leaf_to_chunk_index": {},
            "image_roles_by_leaf": {},
            "core_names_by_leaf": {},
        }

    chunk_records: list[dict[str, object]] = []
    for fallback_index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            continue
        chunk_index = int(chunk.get("index", fallback_index))
        image_names = {str(name) for name in (chunk.get("image_names") or [])}
        core_names = {str(name) for name in (chunk.get("core_names") or chunk.get("coreNames") or [])}
        overlap_names = {str(name) for name in (chunk.get("overlap_names") or chunk.get("overlapNames") or [])}
        if image_names or core_names or overlap_names:
            chunk_records.append(
                {
                    "chunk_index": chunk_index,
                    "image_names": image_names,
                    "core_names": core_names,
                    "overlap_names": overlap_names,
                }
            )

    leaf_to_chunk: dict[int, int] = {}
    image_roles_by_leaf: dict[int, dict[str, str]] = {}
    core_names_by_leaf: dict[int, set[str]] = {}
    assignments: list[dict[str, object]] = []
    used_chunks: set[int] = set()
    for leaf_index, model_dir in enumerate(normalized_dirs):
        leaf_names = stats_for_model(model_dir).image_names
        best_record: dict[str, object] | None = None
        best_score = -1.0
        best_intersection = 0
        for record in chunk_records:
            chunk_index = int(record["chunk_index"])
            if chunk_index in used_chunks:
                continue
            chunk_names = record["image_names"]
            if not isinstance(chunk_names, set):
                continue
            intersection = len(leaf_names.intersection(chunk_names))
            union = len(leaf_names.union(chunk_names)) or 1
            score = intersection / union
            if score > best_score:
                best_record = record
                best_score = score
                best_intersection = intersection
        if best_record is None or best_score <= 0.0:
            fallback_record = next(
                (
                    record
                    for record in chunk_records
                    if int(record["chunk_index"]) == leaf_index and int(record["chunk_index"]) not in used_chunks
                ),
                None,
            )
            if fallback_record is not None:
                best_record = fallback_record
                best_score = 0.0
                best_intersection = 0
            else:
                assignments.append(
                    {
                        "leaf_index": leaf_index,
                        "chunk_index": None,
                        "match_score": 0.0,
                        "intersection_image_count": 0,
                        "leaf_image_count": len(leaf_names),
                        "status": "unmatched",
                    }
                )
                continue
        if best_record is None:
            assignments.append(
                {
                    "leaf_index": leaf_index,
                    "chunk_index": None,
                    "match_score": 0.0,
                    "intersection_image_count": 0,
                    "leaf_image_count": len(leaf_names),
                    "status": "unmatched",
                }
            )
            continue
        chunk_index = int(best_record["chunk_index"])
        used_chunks.add(chunk_index)
        leaf_to_chunk[leaf_index] = chunk_index
        core_names = best_record["core_names"] if isinstance(best_record["core_names"], set) else set()
        overlap_names = best_record["overlap_names"] if isinstance(best_record["overlap_names"], set) else set()
        roles: dict[str, str] = {}
        for name in leaf_names:
            if name in core_names:
                roles[name] = "core"
            elif name in overlap_names:
                roles[name] = "overlap"
            else:
                roles[name] = "unknown"
        image_roles_by_leaf[leaf_index] = roles
        core_names_by_leaf[leaf_index] = set(core_names)
        assignments.append(
            {
                "leaf_index": leaf_index,
                "chunk_index": chunk_index,
                "match_score": round(best_score, 6),
                "intersection_image_count": best_intersection,
                "leaf_image_count": len(leaf_names),
                "status": "matched" if best_score >= 0.8 else "index_fallback",
            }
        )

    return {
        "status": "matched" if len(leaf_to_chunk) == len(normalized_dirs) else "partial",
        "leaf_to_chunk_index": leaf_to_chunk,
        "image_roles_by_leaf": image_roles_by_leaf,
        "core_names_by_leaf": core_names_by_leaf,
        "assignments": assignments,
    }


def residual_rows_for_shared_cameras(
    *,
    shared_names: list[str],
    residuals: list[float],
    leaf_a: int,
    leaf_b: int,
    image_roles_by_leaf: dict[int, dict[str, str]] | None,
    target_centers: np.ndarray | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    roles_a = (image_roles_by_leaf or {}).get(leaf_a, {})
    roles_b = (image_roles_by_leaf or {}).get(leaf_b, {})
    for index, (name, residual) in enumerate(zip(shared_names, residuals)):
        role_a = roles_a.get(name, "unknown")
        role_b = roles_b.get(name, "unknown")
        row = {
            "image_name": name,
            "residual_m": round(float(residual), 6),
            "leaf_a_role": role_a,
            "leaf_b_role": role_b,
            "role_pair": f"{role_a}|{role_b}",
            "trusted_core_involved": "core" in {role_a, role_b},
        }
        if target_centers is not None and index < len(target_centers):
            row["target_center_m"] = [float(value) for value in target_centers[index].tolist()]
        rows.append(row)
    return rows


def residual_role_report(
    rows: list[dict[str, object]],
    *,
    thresholds: SeamThresholds,
    target_baseline_m: float,
) -> dict[str, object]:
    by_role: dict[str, list[float]] = {}
    trusted_residuals: list[float] = []
    untrusted_residuals: list[float] = []
    for row in rows:
        residual = float(row["residual_m"])
        role_pair = str(row["role_pair"])
        by_role.setdefault(role_pair, []).append(residual)
        if bool(row.get("trusted_core_involved")):
            trusted_residuals.append(residual)
        else:
            untrusted_residuals.append(residual)
    role_stats = {role_pair: residual_summary(values) for role_pair, values in sorted(by_role.items())}
    trusted_summary = residual_summary(sorted(trusted_residuals))
    trusted_p95 = float(trusted_summary.get("p95") or 0.0)
    trusted_baseline_normalized = trusted_p95 / max(target_baseline_m, 1e-9)
    high_outliers = [
        row
        for row in sorted(rows, key=lambda item: float(item["residual_m"]), reverse=True)
        if float(row["residual_m"]) > thresholds.max_sim3_p95_residual_m
    ][:24]
    return {
        "role_pair_stats": role_stats,
        "trusted_core_involved_count": len(trusted_residuals),
        "trusted_core_involved_residual_m": trusted_summary,
        "trusted_core_involved_baseline_normalized_residual": round(trusted_baseline_normalized, 8),
        "untrusted_overlap_only_count": len(untrusted_residuals),
        "untrusted_overlap_only_residual_m": residual_summary(sorted(untrusted_residuals)),
        "top_outlier_images": high_outliers,
    }


def seam_inlier_support_report(
    rows: list[dict[str, object]],
    *,
    threshold_m: float,
) -> dict[str, object]:
    inlier_rows = [row for row in rows if float(row["residual_m"]) <= threshold_m]
    trusted_inliers = [row for row in inlier_rows if bool(row.get("trusted_core_involved"))]
    total_count = len(rows)
    inlier_residuals = sorted(float(row["residual_m"]) for row in inlier_rows)
    inlier_centers = [
        row["target_center_m"]
        for row in inlier_rows
        if isinstance(row.get("target_center_m"), list) and len(row.get("target_center_m") or []) == 3
    ]
    inlier_distribution = (
        camera_distribution_stats(np.array(inlier_centers, dtype=float))
        if len(inlier_centers) >= 2
        else {
            "rank": 0,
            "baseline_m": 0.0,
            "singular_values": [],
            "normalized_singular_values": [],
        }
    )
    return {
        "threshold_m": round(float(threshold_m), 6),
        "inlier_count": len(inlier_rows),
        "total_shared_count": total_count,
        "inlier_ratio": round(len(inlier_rows) / total_count, 6) if total_count else 0.0,
        "trusted_core_involved_inlier_count": len(trusted_inliers),
        "trusted_core_involved_inlier_ratio": round(len(trusted_inliers) / total_count, 6) if total_count else 0.0,
        "inlier_residual_m": residual_summary(inlier_residuals),
        "inlier_camera_distribution": inlier_distribution,
        "sample_outlier_images": [
            {
                "image_name": row["image_name"],
                "residual_m": row["residual_m"],
                "role_pair": row["role_pair"],
                "trusted_core_involved": row["trusted_core_involved"],
            }
            for row in sorted(rows, key=lambda item: float(item["residual_m"]), reverse=True)
            if float(row["residual_m"]) > threshold_m
        ][:24],
    }


def kept_point_lines_and_coords(
    points_path: Path,
    *,
    min_track_length: int,
) -> tuple[list[str], set[int], list[tuple[float, float, float]]]:
    point_lines: list[str] = []
    kept_point_ids: set[int] = set()
    coords: list[tuple[float, float, float]] = []
    for line in non_comment_lines(points_path):
        parts = line.split()
        if len(parts) < 8 or track_length_from_parts(parts) < min_track_length:
            continue
        point_lines.append(line)
        kept_point_ids.add(int(parts[0]))
        coords.append((float(parts[1]), float(parts[2]), float(parts[3])))
    return point_lines, kept_point_ids, coords


def rewrite_points_line_without_ids(points_line: str, removed_point_ids: set[int]) -> str:
    point_parts = points_line.split()
    rewritten: list[str] = []
    for offset in range(0, len(point_parts), 3):
        if offset + 2 >= len(point_parts):
            break
        point_id = int(float(point_parts[offset + 2]))
        rewritten.extend(
            (
                point_parts[offset],
                point_parts[offset + 1],
                "-1" if point_id in removed_point_ids else point_parts[offset + 2],
            )
        )
    return " ".join(rewritten)


def cull_low_support_global_double_surface_points(
    point_lines: list[str],
    *,
    max_points_per_cell: int = 32,
) -> tuple[list[str], set[int], dict[str, object]]:
    """Remove tiny, ambiguous post-merge layered cells without masking real large seams."""

    point_records: list[dict[str, object]] = []
    coords: list[tuple[float, float, float]] = []
    for line in point_lines:
        parts = line.split()
        if len(parts) < 8:
            continue
        coord = (float(parts[1]), float(parts[2]), float(parts[3]))
        point_records.append(
            {
                "id": int(parts[0]),
                "line": line,
                "coord": coord,
                "error": float(parts[7]),
                "track_length": track_length_from_parts(parts),
            }
        )
        coords.append(coord)
    if len(point_records) < 16:
        return point_lines, set(), {
            "status": "pass_not_enough_points",
            "removed_point_count": 0,
            "flagged_cell_count": 0,
            "removed_cells": [],
        }

    axes = list(zip(*coords))
    model_bounds = {
        axis_name: {"min": min(values), "max": max(values), "span": max(values) - min(values)}
        for axis_name, values in zip(("x", "y", "z"), axes)
    }
    span_x = float(model_bounds.get("x", {}).get("span") or 1.0)
    span_y = float(model_bounds.get("y", {}).get("span") or 1.0)
    cell_size = max(max(span_x, span_y) / 48.0, 1.0)
    min_x = float(model_bounds["x"]["min"])
    min_y = float(model_bounds["y"]["min"])
    cells: dict[tuple[int, int], list[dict[str, object]]] = {}
    for record in point_records:
        x, y, _ = record["coord"]  # type: ignore[misc]
        key = (int((float(x) - min_x) / cell_size), int((float(y) - min_y) / cell_size))
        cells.setdefault(key, []).append(record)

    removed_point_ids: set[int] = set()
    removed_cells: list[dict[str, object]] = []
    flagged_but_retained_cells: list[dict[str, object]] = []
    for key, records in sorted(cells.items()):
        if len(records) < 8:
            continue
        ordered = sorted(float(record["coord"][2]) for record in records)  # type: ignore[index]
        gaps = [(ordered[index + 1] - ordered[index], index) for index in range(len(ordered) - 1)]
        if not gaps:
            continue
        largest_gap, split_index = max(gaps, key=lambda item: item[0])
        lower_count = split_index + 1
        upper_count = len(ordered) - lower_count
        min_mode_count = max(3, int(len(ordered) * 0.2))
        local_span = ordered[-1] - ordered[0]
        tolerance = max(1.5, local_span * 0.35)
        if largest_gap <= tolerance or lower_count < min_mode_count or upper_count < min_mode_count:
            continue
        cell_report = {
            "cell": [key[0], key[1]],
            "point_count": len(records),
            "mode_separation": round(largest_gap, 4),
            "z_min": round(ordered[0], 4),
            "z_max": round(ordered[-1], 4),
        }
        if len(records) > max_points_per_cell:
            flagged_but_retained_cells.append(cell_report)
            continue
        for record in records:
            removed_point_ids.add(int(record["id"]))
        removed_cells.append(cell_report)

    filtered_lines = [
        line
        for line in point_lines
        if line.split() and int(line.split()[0]) not in removed_point_ids
    ]
    status = "pass_culled_low_support_cells" if removed_point_ids else "pass_no_low_support_cells"
    return filtered_lines, removed_point_ids, {
        "status": status,
        "removed_point_count": len(removed_point_ids),
        "removed_cell_count": len(removed_cells),
        "flagged_but_retained_cell_count": len(flagged_but_retained_cells),
        "cell_size_m": round(cell_size, 4),
        "max_points_per_cell": max_points_per_cell,
        "removed_cells": sorted(removed_cells, key=lambda item: (-float(item["mode_separation"]), item["cell"]))[:20],
        "flagged_but_retained_cells": sorted(
            flagged_but_retained_cells,
            key=lambda item: (-float(item["mode_separation"]), item["cell"]),
        )[:20],
    }


def transformed_point_coords(points_path: Path, transform: SimilarityTransform) -> list[tuple[float, float, float]]:
    coords: list[tuple[float, float, float]] = []
    for line in non_comment_lines(points_path):
        parts = line.split()
        if len(parts) < 4:
            continue
        point = np.array([float(parts[1]), float(parts[2]), float(parts[3])], dtype=float)
        transformed = transform.scale * transform.rotation @ point + transform.translation
        coords.append((float(transformed[0]), float(transformed[1]), float(transformed[2])))
    return coords


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(max(math.ceil(q * len(ordered)) - 1, 0), len(ordered) - 1)
    return float(ordered[index])


def cross_leaf_surface_overlap_stats(
    existing_points: list[tuple[float, float, float]],
    incoming_points: list[tuple[float, float, float]],
    *,
    min_points_per_side: int = 6,
) -> dict[str, object]:
    if not existing_points or not incoming_points:
        return {
            "overlap_cell_count": 0,
            "flagged_overlap_cell_count": 0,
            "flagged_overlap_cell_ratio": 0.0,
            "median_abs_z_gap_m": None,
            "p95_abs_z_gap_m": None,
            "max_abs_z_gap_m": None,
            "examples": [],
        }
    combined = existing_points + incoming_points
    xs = [point[0] for point in combined]
    ys = [point[1] for point in combined]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
    cell_size = max(span / 80.0, 2.0)
    min_x = min(xs)
    min_y = min(ys)

    def group(points: list[tuple[float, float, float]]) -> dict[tuple[int, int], list[float]]:
        cells: dict[tuple[int, int], list[float]] = {}
        for x, y, z in points:
            key = (int((x - min_x) / cell_size), int((y - min_y) / cell_size))
            cells.setdefault(key, []).append(z)
        return cells

    existing_cells = group(existing_points)
    incoming_cells = group(incoming_points)
    z_gaps: list[float] = []
    flagged: list[dict[str, object]] = []
    for key in sorted(set(existing_cells).intersection(incoming_cells)):
        left = existing_cells[key]
        right = incoming_cells[key]
        if len(left) < min_points_per_side or len(right) < min_points_per_side:
            continue
        left_median = float(np.median(left))
        right_median = float(np.median(right))
        gap = abs(left_median - right_median)
        z_gaps.append(gap)
        left_span = max(left) - min(left)
        right_span = max(right) - min(right)
        tolerance = max(1.5, 0.35 * max(left_span, right_span, cell_size))
        if gap <= tolerance:
            continue
        flagged.append(
            {
                "cell": [key[0], key[1]],
                "existing_count": len(left),
                "incoming_count": len(right),
                "median_z_gap_m": round(gap, 4),
                "existing_z_median": round(left_median, 4),
                "incoming_z_median": round(right_median, 4),
                "tolerance_m": round(tolerance, 4),
            }
        )
    overlap_count = len(z_gaps)
    flagged_ratio = round(len(flagged) / overlap_count, 4) if overlap_count else 0.0
    return {
        "overlap_cell_count": overlap_count,
        "flagged_overlap_cell_count": len(flagged),
        "flagged_overlap_cell_ratio": flagged_ratio,
        "median_abs_z_gap_m": round(float(np.median(z_gaps)), 4) if z_gaps else None,
        "p95_abs_z_gap_m": round(percentile(z_gaps, 0.95), 4) if z_gaps else None,
        "max_abs_z_gap_m": round(max(z_gaps), 4) if z_gaps else None,
        "cell_size_m": round(cell_size, 4),
        "grid": {"min_x": min_x, "min_y": min_y, "cell_size_m": cell_size},
        "flagged_cells": [item["cell"] for item in flagged],
        "min_points_per_side": min_points_per_side,
        "examples": sorted(flagged, key=lambda item: (-float(item["median_z_gap_m"]), item["cell"]))[:20],
    }


def point_overlap_cell(point: tuple[float, float, float], grid: dict[str, object]) -> tuple[int, int] | None:
    try:
        min_x = float(grid["min_x"])
        min_y = float(grid["min_y"])
        cell_size = float(grid["cell_size_m"])
    except (KeyError, TypeError, ValueError):
        return None
    if cell_size <= 0:
        return None
    return (int((point[0] - min_x) / cell_size), int((point[1] - min_y) / cell_size))


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
    min_final_track_length: int = 2,
    planner_manifest: dict[str, Any] | None = None,
    max_scale_delta: float = 0.15,
    max_sim3_p95_residual_m: float = 0.25,
    max_baseline_normalized_residual: float = 0.01,
    enable_seam_local_ba: bool = False,
    strict_production_gates: bool = False,
) -> dict[str, object]:
    thresholds = SeamThresholds(
        min_shared_images=min_shared_images,
        max_scale_delta=max_scale_delta,
        max_sim3_p95_residual_m=max_sim3_p95_residual_m,
        max_baseline_normalized_residual=max_baseline_normalized_residual,
        strict_production_gates=strict_production_gates,
    )
    seam_report = build_seam_merge_graph(
        normalized_dirs=normalized_dirs,
        thresholds=thresholds,
        planner_manifest=planner_manifest,
    )
    if seam_report.get("decision") == "fail" and strict_production_gates:
        return {
            "strategy": "seam_graph_sim3_v1",
            "error": "strict seam graph rejected reducer merge",
            "root_leaf": seam_report.get("root_leaf"),
            "transforms": [],
            "accepted_merge_tree": seam_report.get("accepted_merge_tree"),
            "rejected_edges": seam_report.get("rejected_edges"),
            "cycle_consistency": seam_report.get("cycle_consistency"),
            "post_merge_jurisdiction_culling": seam_report.get("post_merge_jurisdiction_culling"),
            "promotion_blockers": seam_report.get("promotion_blockers") or [],
            "seam_merge_report": seam_report,
        }

    root_index = int(seam_report.get("root_leaf") or 0)
    tree_edges = seam_report.get("accepted_merge_tree") or []
    adjacency: dict[int, list[int]] = {index: [] for index in range(len(normalized_dirs))}
    for edge in tree_edges:
        left = int(edge["leaf_a"])
        right = int(edge["leaf_b"])
        adjacency.setdefault(left, []).append(right)
        adjacency.setdefault(right, []).append(left)
    merge_sequence: list[tuple[int | None, int]] = [(None, root_index)]
    visited = {root_index}
    queue = [root_index]
    while queue:
        parent_index = queue.pop(0)
        for child_index in sorted(adjacency.get(parent_index, [])):
            if child_index in visited:
                continue
            visited.add(child_index)
            queue.append(child_index)
            merge_sequence.append((parent_index, child_index))
    if len(visited) != len(normalized_dirs):
        missing = sorted(set(range(len(normalized_dirs))) - visited)
        raise RuntimeError(f"accepted seam graph is disconnected; missing leaves {missing}")

    planner_leaf_maps = planner_chunk_leaf_maps(normalized_dirs, planner_manifest)
    raw_core_names_by_leaf = planner_leaf_maps.get("core_names_by_leaf") if isinstance(planner_leaf_maps, dict) else {}
    core_names_by_leaf: dict[int, set[str]] = (
        raw_core_names_by_leaf if isinstance(raw_core_names_by_leaf, dict) else {}
    )

    anchor = normalized_dirs[root_index]
    output_dir.mkdir(parents=True, exist_ok=True)
    anchor_pairs = image_record_pairs(anchor / "images.txt")
    anchor_by_name = {parts[9]: (parts, points_line) for parts, points_line in anchor_pairs}
    anchor_point_lines, anchor_kept_point_ids, merged_surface_points = kept_point_lines_and_coords(
        anchor / "points3D.txt",
        min_track_length=min_final_track_length,
    )
    anchor_output_pairs = [
        (parts, rewrite_points_line_with_kept_ids(points_line, anchor_kept_point_ids))
        for parts, points_line in anchor_pairs
    ]
    emitted_names = set(anchor_by_name)
    transforms: list[dict[str, object]] = []
    additional_image_lines: list[tuple[list[str], str, dict[int, int]]] = []
    additional_points_lines: list[str] = []
    global_double_surface_culling: dict[str, object] = {
        "status": "not_run",
        "removed_point_count": 0,
    }
    next_point_id = point_id_range(anchor / "points3D.txt")[1] + 1
    root_transforms: dict[int, SimilarityTransform] = {root_index: identity_similarity()}
    culling_records: list[dict[str, object]] = []
    culling_by_reason: dict[str, int] = {}
    culling_blockers: list[dict[str, object]] = []

    def record_cull(reason: str, leaf_index: int, point_id: int, seam: str) -> None:
        culling_by_reason[reason] = culling_by_reason.get(reason, 0) + 1
        if len(culling_records) < 200:
            culling_records.append(
                {
                    "leaf_index": leaf_index,
                    "old_point_id": point_id,
                    "reason": reason,
                    "affected_seam": seam,
                }
            )

    for parent_index, leaf_index in merge_sequence[1:]:
        if parent_index is None or parent_index not in root_transforms:
            raise RuntimeError(f"accepted seam tree reached leaf {leaf_index} before its parent transform was known")
        parent_dir = normalized_dirs[parent_index]
        parent_pairs = image_record_pairs(parent_dir / "images.txt")
        parent_by_name = {parts[9]: (parts, points_line) for parts, points_line in parent_pairs}
        leaf_dir = normalized_dirs[leaf_index]
        leaf_pairs = image_record_pairs(leaf_dir / "images.txt")
        leaf_by_name = {parts[9]: (parts, points_line) for parts, points_line in leaf_pairs}
        shared_names = sorted(set(parent_by_name).intersection(leaf_by_name))
        if len(shared_names) < min_shared_images:
            raise RuntimeError(
                f"accepted seam tree reached leaf {leaf_index} but parent leaf {parent_index} only has "
                f"{len(shared_names)} shared registered images, minimum is {min_shared_images}"
            )
        source = np.array([camera_center(leaf_by_name[name][0]) for name in shared_names], dtype=float)
        target_parent = np.array([camera_center(parent_by_name[name][0]) for name in shared_names], dtype=float)
        seam_transform = estimate_robust_similarity(source, target_parent)
        parent_transform = root_transforms[parent_index]
        parent_root_centers = transform_points(target_parent, parent_transform)
        leaf_root_centers = transform_points(source, compose_similarity(parent_transform, seam_transform))
        root_residuals = [
            float(np.linalg.norm(left - right))
            for left, right in zip(leaf_root_centers, parent_root_centers)
        ]
        transform = compose_similarity(parent_transform, seam_transform, residuals=root_residuals)
        root_transforms[leaf_index] = transform
        residuals = sorted(transform.residuals)
        point_map: dict[int, int] = {}
        candidate_points: list[tuple[int, int, list[str], list[str], tuple[float, float, float]]] = []
        kept_leaf_surface_points: list[tuple[float, float, float]] = []
        leaf_image_id_to_name = image_id_to_name(leaf_dir / "images.txt")
        core_names = core_names_by_leaf.get(leaf_index, set())
        seam_name = f"leaf_{parent_index if parent_index is not None else root_index:02d}_to_leaf_{leaf_index:02d}"
        for line in non_comment_lines(leaf_dir / "points3D.txt"):
            parts = line.split()
            track: list[str] = []
            original_track_names: set[str] = set()
            for offset in range(8, len(parts), 2):
                if offset + 1 >= len(parts):
                    break
                image_id = int(parts[offset])
                image_name = leaf_image_id_to_name.get(image_id, "")
                if image_name:
                    original_track_names.add(image_name)
                if image_name and image_name not in emitted_names:
                    track.extend((str(image_id), parts[offset + 1]))
            if len(track) < min_final_track_length * 2:
                continue
            old_point_id = int(parts[0])
            if core_names and not original_track_names.intersection(core_names):
                record_cull("no_core_owned_track", leaf_index, old_point_id, seam_name)
                continue
            new_point_id = next_point_id
            next_point_id += 1
            transformed_parts = transform_point(parts, transform)
            transformed_parts[0] = str(new_point_id)
            coord = (float(transformed_parts[1]), float(transformed_parts[2]), float(transformed_parts[3]))
            candidate_points.append((old_point_id, new_point_id, transformed_parts, track, coord))

        pre_cull_surface_overlap = cross_leaf_surface_overlap_stats(
            merged_surface_points,
            [candidate[-1] for candidate in candidate_points],
        )
        flagged_cells = {
            tuple(cell)
            for cell in pre_cull_surface_overlap.get("flagged_cells", [])
            if isinstance(cell, list) and len(cell) == 2
        }
        overlap_grid = (
            pre_cull_surface_overlap.get("grid")
            if isinstance(pre_cull_surface_overlap.get("grid"), dict)
            else {}
        )
        seam_conflict_points_removed = 0
        for old_point_id, new_point_id, transformed_parts, track, coord in candidate_points:
            if flagged_cells and point_overlap_cell(coord, overlap_grid) in flagged_cells:
                seam_conflict_points_removed += 1
                record_cull("cross_leaf_surface_overlap_flagged_cell", leaf_index, old_point_id, seam_name)
                continue
            point_map[old_point_id] = new_point_id
            additional_points_lines.append(" ".join([*transformed_parts[:8], *track]) + "\n")
            kept_leaf_surface_points.append(coord)

        seam_cull_ratio = seam_conflict_points_removed / len(candidate_points) if candidate_points else 0.0
        if candidate_points and seam_cull_ratio > 0.5:
            culling_blockers.append(
                {
                    "reason": "excessive_duplicate_surface_culling",
                    "affected_seam": seam_name,
                    "leaf_index": leaf_index,
                    "candidate_points": len(candidate_points),
                    "removed_points": seam_conflict_points_removed,
                    "removed_ratio": round(seam_cull_ratio, 6),
                }
            )

        surface_overlap = cross_leaf_surface_overlap_stats(
            merged_surface_points,
            kept_leaf_surface_points,
        )

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

        surface_overlap = cross_leaf_surface_overlap_stats(merged_surface_points, kept_leaf_surface_points)
        transforms.append(
            {
                "leaf_index": leaf_index,
                "parent_leaf_index": parent_index,
                "shared_registered_images": len(shared_names),
                "scale": round(transform.scale, 8),
                "alignment_error_m": {
                    "min": round(residuals[0], 4),
                    "median": round(float(np.median(residuals)), 4),
                    "p95": round(residuals[min(math.ceil(0.95 * len(residuals)) - 1, len(residuals) - 1)], 4),
                    "max": round(residuals[-1], 4),
                },
                "surface_overlap": surface_overlap,
                "pre_cull_surface_overlap": pre_cull_surface_overlap,
                "duplicate_surface_overlap": cross_leaf_duplicate_surface_stats(merged_surface_points, kept_leaf_surface_points),
                "seam_conflict_points_removed": seam_conflict_points_removed,
                "seam_conflict_points_removed_ratio": round(seam_cull_ratio, 6),
                "new_points_kept": len(point_map),
            }
        )
        merged_surface_points.extend(kept_leaf_surface_points)

    if strict_production_gates:
        all_point_lines = anchor_point_lines + additional_points_lines
        filtered_point_lines, removed_global_point_ids, global_double_surface_culling = (
            cull_low_support_global_double_surface_points(all_point_lines)
        )
        if removed_global_point_ids:
            kept_global_point_ids = {int(line.split()[0]) for line in filtered_point_lines if line.split()}
            anchor_point_lines = [
                line
                for line in anchor_point_lines
                if line.split() and int(line.split()[0]) in kept_global_point_ids
            ]
            additional_points_lines = [
                line
                for line in additional_points_lines
                if line.split() and int(line.split()[0]) in kept_global_point_ids
            ]
            anchor_output_pairs = [
                (parts, rewrite_points_line_without_ids(points_line, removed_global_point_ids))
                for parts, points_line in anchor_output_pairs
            ]
            additional_image_lines = [
                (parts, rewrite_points_line_without_ids(points_line, removed_global_point_ids), point_map)
                for parts, points_line, point_map in additional_image_lines
            ]
            for removed_id in sorted(removed_global_point_ids):
                record_cull(
                    "global_double_surface_low_support_cell",
                    -1,
                    removed_id,
                    "post_merge_global",
                )

    shutil.copy2(anchor / "cameras.txt", output_dir / "cameras.txt")
    if (anchor / "rigs.txt").exists():
        shutil.copy2(anchor / "rigs.txt", output_dir / "rigs.txt")
    with (output_dir / "images.txt").open("w", encoding="utf-8") as target:
        target.write("# Image list with two lines of data per image:\n")
        target.write("#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        target.write("#   POINTS2D[] as (X, Y, POINT3D_ID)\n")
        for parts, points_line in anchor_output_pairs:
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

    non_tree_cycles: list[dict[str, object]] = []
    for edge in seam_report.get("non_tree_accepted_edges") or []:
        leaf_a = int(edge["leaf_a"])
        leaf_b = int(edge["leaf_b"])
        if leaf_a not in root_transforms or leaf_b not in root_transforms:
            continue
        predicted_scale = root_transforms[leaf_b].scale / max(root_transforms[leaf_a].scale, 1e-12)
        measured_scale = ((edge.get("sim3") or {}) if isinstance(edge.get("sim3"), dict) else {}).get("scale")
        scale_error = abs(float(measured_scale) - predicted_scale) if measured_scale is not None else None
        non_tree_cycles.append(
            {
                "leaf_a": leaf_a,
                "leaf_b": leaf_b,
                "measured_scale": measured_scale,
                "predicted_scale_from_tree": round(predicted_scale, 8),
                "scale_cycle_error": round(scale_error, 8) if scale_error is not None else None,
                "decision": "fail" if scale_error is not None and scale_error > max_scale_delta else "pass",
            }
        )
    if non_tree_cycles:
        cycle_failures = [item for item in non_tree_cycles if item["decision"] == "fail"]
        seam_report["cycle_consistency"] = {
            "status": "fail" if cycle_failures else "pass",
            "non_tree_edge_count": len(non_tree_cycles),
            "failures": cycle_failures,
            "checks": non_tree_cycles,
        }
        if cycle_failures:
            seam_report.setdefault("promotion_blockers", []).append("cycle_consistency_failed")
    else:
        seam_report["cycle_consistency"] = {
            "status": "not_run_no_cycles",
            "non_tree_edge_count": 0,
            "checks": [],
        }

    seam_report["actual_merge_sequence"] = [
        {"parent_leaf_index": parent, "leaf_index": leaf} for parent, leaf in merge_sequence
    ]
    seam_report["post_merge_jurisdiction_culling"] = {
        "status": "fail_excessive_duplicate_surface_culling" if culling_blockers else "pass" if culling_by_reason else "pass_no_points_removed",
        "removed_point_count": sum(culling_by_reason.values()),
        "by_reason": culling_by_reason,
        "records": culling_records,
        "blockers": culling_blockers,
        "spatial_jurisdiction_rechecked": False,
        "spatial_jurisdiction_note": (
            "planner cell bounds are not guaranteed to share the root COLMAP coordinate frame; "
            "core-track ownership is enforced when a planner manifest is supplied"
        ),
    }
    seam_report["post_merge_global_double_surface_culling"] = global_double_surface_culling
    if culling_blockers:
        seam_report.setdefault("promotion_blockers", []).append("excessive_duplicate_surface_culling")
    seam_report["seam_local_ba"] = {
        "enabled": enable_seam_local_ba,
        "status": "not_run",
        "reason": (
            "bounded seam-local BA is recorded as an interface flag; this local text reducer does not "
            "run COLMAP bundle_adjuster windows yet"
        ),
    }
    seam_report["decision"] = "fail" if seam_report.get("promotion_blockers") else "pass"

    return {
        "strategy": "seam_graph_sim3_v1",
        "root_leaf": root_index,
        "transforms": transforms,
        "accepted_merge_tree": seam_report.get("accepted_merge_tree"),
        "rejected_edges": seam_report.get("rejected_edges"),
        "cycle_consistency": seam_report.get("cycle_consistency"),
        "post_merge_jurisdiction_culling": seam_report.get("post_merge_jurisdiction_culling"),
        "promotion_blockers": seam_report.get("promotion_blockers") or [],
        "seam_merge_report": seam_report,
    }


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
                    max_scale_delta=args.max_scale_delta,
                    max_sim3_p95_residual_m=args.max_sim3_p95_residual_m,
                    max_baseline_normalized_residual=args.max_baseline_normalized_residual,
                    strict_production_gates=args.strict_production_gates,
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
    if fallback_report is not None:
        blockers.extend(str(item) for item in (fallback_report.get("promotion_blockers") or []))
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
        "merge_strategy": (fallback_report or {}).get("strategy") or "stock_colmap_model_merger",
        "seam_merge_report": (fallback_report or {}).get("seam_merge_report"),
        "accepted_merge_tree": (fallback_report or {}).get("accepted_merge_tree"),
        "rejected_edges": (fallback_report or {}).get("rejected_edges"),
        "cycle_consistency": (fallback_report or {}).get("cycle_consistency"),
        "post_merge_jurisdiction_culling": (fallback_report or {}).get("post_merge_jurisdiction_culling"),
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
