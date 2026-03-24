"""Merge segment reconstructions into one COLMAP sparse model."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from colmap_runner import ColmapRunner, SegmentRunResult
from exif_manifest import ImageRecord
from model_analyzer import SparseModelMetrics, analyze_sparse_text_model
from segmenter import Segment


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MergeResult:
    """Merged sparse model metadata."""

    binary_model_dir: str
    text_model_dir: str
    metrics: Dict[str, object]
    merge_steps: List[Dict[str, object]]


class ModelMerger:
    """Merge adjacent segment models and export a final text model."""

    def __init__(
        self,
        *,
        runner: ColmapRunner,
        work_dir: Path,
        source_images_dir: Path,
    ):
        self.runner = runner
        self.work_dir = Path(work_dir)
        self.source_images_dir = Path(source_images_dir)

    def merge_segments(
        self,
        *,
        segments: Sequence[Segment],
        segment_results: Sequence[SegmentRunResult],
        record_lookup: Dict[str, ImageRecord],
    ) -> MergeResult:
        if not segment_results:
            raise ValueError("No segment results were provided")

        merge_steps: List[Dict[str, object]] = []
        current_binary_model = Path(segment_results[0].binary_model_dir)

        for index, next_result in enumerate(segment_results[1:], start=1):
            merge_output_root = self.work_dir / "merged" / f"merge_{index:03d}"
            merge_output_root.mkdir(parents=True, exist_ok=True)
            if self._try_model_merge(current_binary_model, Path(next_result.binary_model_dir), merge_output_root):
                current_binary_model = self._require_model_dir(merge_output_root)
                merge_steps.append(
                    {
                        "step": f"merge-{index:03d}",
                        "status": "merged",
                        "leftModel": str(current_binary_model),
                        "rightModel": next_result.binary_model_dir,
                    }
                )
                continue

            left_segment = segments[index - 1]
            right_segment = segments[index]
            boundary_names = self._boundary_image_names(left_segment, right_segment)
            logger.warning(
                "Model merge failed between %s and %s; retrying with boundary remap",
                left_segment.segment_id,
                right_segment.segment_id,
            )
            boundary_result = self.runner.run_boundary_segment(
                segment_id=f"boundary-{index:03d}",
                image_names=boundary_names,
                record_lookup=record_lookup,
            )

            bridge_root_a = self.work_dir / "merged" / f"bridge_{index:03d}_a"
            bridge_root_a.mkdir(parents=True, exist_ok=True)
            if not self._try_model_merge(
                current_binary_model,
                Path(boundary_result.binary_model_dir),
                bridge_root_a,
            ):
                raise RuntimeError(f"Boundary remap failed to align with merged model at step {index}")

            bridge_root_b = self.work_dir / "merged" / f"bridge_{index:03d}_b"
            bridge_root_b.mkdir(parents=True, exist_ok=True)
            bridge_model = self._require_model_dir(bridge_root_a)
            if not self._try_model_merge(
                bridge_model,
                Path(next_result.binary_model_dir),
                bridge_root_b,
            ):
                raise RuntimeError(f"Boundary remap failed to align next segment at step {index}")

            current_binary_model = self._require_model_dir(bridge_root_b)
            merge_steps.append(
                {
                    "step": f"merge-{index:03d}",
                    "status": "boundary_remap",
                    "boundarySegmentId": boundary_result.segment_id,
                    "boundaryImageCount": len(boundary_names),
                    "rightModel": next_result.binary_model_dir,
                }
            )

        final_binary_dir = current_binary_model
        final_adjusted_root = self.work_dir / "merged" / "bundle_adjusted"
        final_adjusted_root.mkdir(parents=True, exist_ok=True)
        self.runner._run_command(
            [
                "colmap",
                "bundle_adjuster",
                "--input_path",
                str(final_binary_dir),
                "--output_path",
                str(final_adjusted_root),
            ],
            segment_id="merge",
            stage="bundle_adjuster",
        )
        final_binary_dir = self._require_model_dir(final_adjusted_root)

        final_text_dir = self.work_dir / "merged" / "final_text"
        self.runner._run_command(
            [
                "colmap",
                "model_converter",
                "--input_path",
                str(final_binary_dir),
                "--output_path",
                str(final_text_dir),
                "--output_type",
                "TXT",
            ],
            segment_id="merge",
            stage="final_model_converter",
        )
        metrics = analyze_sparse_text_model(final_text_dir).to_dict()
        return MergeResult(
            binary_model_dir=str(final_binary_dir),
            text_model_dir=str(final_text_dir),
            metrics=metrics,
            merge_steps=merge_steps,
        )

    def _try_model_merge(
        self,
        left_model_dir: Path,
        right_model_dir: Path,
        output_root: Path,
    ) -> bool:
        try:
            self.runner._run_command(
                [
                    "colmap",
                    "model_merger",
                    "--input_path1",
                    str(left_model_dir),
                    "--input_path2",
                    str(right_model_dir),
                    "--output_path",
                    str(output_root),
                ],
                segment_id="merge",
                stage=f"model_merger[{output_root.name}]",
            )
            return self.runner._resolve_model_dir(output_root) is not None
        except Exception as error:
            logger.warning("model_merger failed: %s", error)
            return False

    @staticmethod
    def _boundary_image_names(left_segment: Segment, right_segment: Segment) -> List[str]:
        overlap = max(
            90,
            left_segment.overlap_with_next,
            right_segment.overlap_with_previous,
        )
        left_tail = left_segment.image_names[-overlap:]
        right_head = right_segment.image_names[:overlap]
        ordered = []
        seen = set()
        for image_name in [*left_tail, *right_head]:
            if image_name in seen:
                continue
            seen.add(image_name)
            ordered.append(image_name)
        return ordered

    def _require_model_dir(self, output_root: Path) -> Path:
        model_dir = self.runner._resolve_model_dir(output_root)
        if model_dir is None:
            raise RuntimeError(f"No COLMAP sparse model found under {output_root}")
        return model_dir
