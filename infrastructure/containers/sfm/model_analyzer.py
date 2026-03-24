"""Analyze COLMAP text sparse models for quality and compatibility metrics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence


@dataclass(frozen=True)
class SparseModelMetrics:
    camera_count: int
    image_count: int
    point_count: int
    mean_observations_per_image: float
    mean_track_length: float
    mean_reprojection_error: float
    registered_image_names: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "camera_count": self.camera_count,
            "image_count": self.image_count,
            "point_count": self.point_count,
            "mean_observations_per_image": round(self.mean_observations_per_image, 4),
            "mean_track_length": round(self.mean_track_length, 4),
            "mean_reprojection_error": round(self.mean_reprojection_error, 6),
            "registered_image_names": self.registered_image_names,
        }


def analyze_sparse_text_model(model_dir: Path) -> SparseModelMetrics:
    """Parse COLMAP text outputs and compute stable summary metrics."""
    model_dir = Path(model_dir)
    cameras_file = model_dir / "cameras.txt"
    images_file = model_dir / "images.txt"
    points_file = model_dir / "points3D.txt"

    camera_lines = _non_comment_lines(cameras_file)
    image_lines = _non_comment_lines(images_file)
    point_lines = _non_comment_lines(points_file)

    registered_image_names: List[str] = []
    observation_count = 0
    image_count = 0
    for index in range(0, len(image_lines), 2):
        if index >= len(image_lines):
            break
        parts = image_lines[index].split()
        if len(parts) < 10:
            continue
        registered_image_names.append(parts[9])
        image_count += 1
        if index + 1 < len(image_lines):
            points2d_parts = image_lines[index + 1].split()
            for point_index in range(0, len(points2d_parts), 3):
                if point_index + 2 < len(points2d_parts) and points2d_parts[point_index + 2] != "-1":
                    observation_count += 1

    point_count = len(point_lines)
    track_lengths: List[int] = []
    reprojection_errors: List[float] = []
    for line in point_lines:
        parts = line.split()
        if len(parts) < 8:
            continue
        try:
            reprojection_errors.append(float(parts[7]))
        except ValueError:
            pass
        track_lengths.append(max(0, (len(parts) - 8) // 2))

    mean_observations = observation_count / image_count if image_count else 0.0
    mean_track_length = sum(track_lengths) / len(track_lengths) if track_lengths else 0.0
    mean_reprojection_error = (
        sum(reprojection_errors) / len(reprojection_errors) if reprojection_errors else 0.0
    )
    return SparseModelMetrics(
        camera_count=len(camera_lines),
        image_count=image_count,
        point_count=point_count,
        mean_observations_per_image=mean_observations,
        mean_track_length=mean_track_length,
        mean_reprojection_error=mean_reprojection_error,
        registered_image_names=registered_image_names,
    )


def quality_check_passed(
    metrics: SparseModelMetrics,
    *,
    input_image_count: int,
    minimum_registered_ratio: float = 0.6,
) -> bool:
    """Apply lightweight but meaningful quality floors."""
    required_images = max(5, int(round(input_image_count * minimum_registered_ratio)))
    required_points = max(500, metrics.image_count * 50)
    return (
        metrics.image_count >= required_images
        and metrics.point_count >= required_points
        and metrics.mean_track_length >= 2.0
    )


def _non_comment_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as handle:
        return [
            line.strip()
            for line in handle
            if line.strip() and not line.startswith("#")
        ]
