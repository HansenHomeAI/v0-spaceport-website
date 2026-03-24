import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2] / "infrastructure" / "containers" / "sfm"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from colmap_runner import SegmentRunResult
from exif_manifest import ImageRecord
from model_analyzer import analyze_sparse_text_model
from model_merge import MergeResult
from run_colmap_hybrid import ColmapHybridPipeline
from segmenter import Segment


def write_minimal_sparse_model(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "cameras.txt").write_text(
        "# cameras\n1 SIMPLE_RADIAL 4000 3000 2000 2000 1500 0.01\n",
        encoding="utf-8",
    )
    (root / "images.txt").write_text(
        "# images\n"
        "1 1 0 0 0 0 0 0 1 DJI_0001.JPG\n10 10 1 20 20 -1\n"
        "2 1 0 0 0 1 0 0 1 DJI_0002.JPG\n11 11 1 21 21 2\n",
        encoding="utf-8",
    )
    (root / "points3D.txt").write_text(
        "# points\n1 0 0 0 255 255 255 0.4 1 0 2 0\n2 1 1 1 255 255 255 0.6 2 1\n",
        encoding="utf-8",
    )


def make_record(index: int) -> ImageRecord:
    return ImageRecord(
        name=f"DJI_{index:04d}.JPG",
        path=f"/tmp/DJI_{index:04d}.JPG",
        capture_time=f"2026-03-08T09:00:0{index}",
        capture_sort_key=f"{index:05d}",
        latitude=41.0,
        longitude=-111.0,
        absolute_altitude_m=1424.0,
        relative_altitude_m=40.0,
        chosen_altitude_m=1424.0,
        flight_yaw_deg=-179.0,
        gimbal_pitch_deg=0.0,
        focal_length_mm=4.5,
        model="FC7303",
        width=4000,
        height=3000,
        camera_group="FC7303_4000x3000",
        gps_accuracy_m=5.0,
        enu_x_m=float(index),
        enu_y_m=0.0,
        enu_z_m=0.0,
    )


class SfmMetadataTests(unittest.TestCase):
    def test_metadata_and_cost_report_include_runtime_diagnostics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            sparse_dir = output_dir / "sparse" / "0"
            input_dir.mkdir()
            output_dir.mkdir()
            write_minimal_sparse_model(sparse_dir)

            pipeline = ColmapHybridPipeline(input_dir, output_dir)
            pipeline.extracted_image_count = 2
            pipeline.exif_records = [make_record(1), make_record(2)]
            pipeline.exif_diagnostics = {"skipped_images": []}
            pipeline.segments = [
                Segment(
                    segment_id="segment-000",
                    image_names=[record.name for record in pipeline.exif_records],
                    start_name="DJI_0001.JPG",
                    end_name="DJI_0002.JPG",
                    image_count=2,
                    overlap_with_previous=0,
                    overlap_with_next=0,
                    hard_break_before=False,
                )
            ]
            pipeline.segment_results = [
                SegmentRunResult(
                    segment_id="segment-000",
                    image_count=2,
                    engine="global_mapper",
                    duration_seconds=12.5,
                    workspace_dir=str(root / "segment"),
                    database_path=str(root / "database.db"),
                    binary_model_dir=str(root / "segment" / "sparse"),
                    text_model_dir=str(sparse_dir),
                    metrics=analyze_sparse_text_model(sparse_dir).to_dict(),
                )
            ]
            pipeline.runtime_plan = {
                "selected_profile": "quality",
                "spatial_matcher_neighbors": 12,
                "estimated_pairs": 24,
                "segment_worker_count": 1,
                "segment_target_size": 400,
                "segment_overlap": 120,
                "segment_max_size": 600,
                "segment_min_size": 250,
                "projection_defaults": {
                    "target_image_count": 4750,
                    "projection_instance_type": "ml.c6i.8xlarge",
                    "projection_segment_worker_count": 4,
                },
                "stage_timeouts": {"job_total": 5400},
            }
            pipeline.merge_result = MergeResult(
                binary_model_dir=str(root / "segment" / "sparse"),
                text_model_dir=str(sparse_dir),
                metrics=analyze_sparse_text_model(sparse_dir).to_dict(),
                merge_steps=[],
            )
            pipeline.stage_metrics = {"reconstruct_segments": {"duration_seconds": 12.5}}
            pipeline.peak_memory_mb = 2048.0
            pipeline.sfm_only = True
            pipeline.sfm_instance_type = "ml.c6i.4xlarge"
            pipeline._start_time = time.time() - 60

            final_metrics = analyze_sparse_text_model(sparse_dir)
            pipeline._write_metadata(final_metrics)
            pipeline._write_cost_report()

            metadata = json.loads((output_dir / "sfm_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["sfm_engine"], "colmap_hybrid")
            self.assertEqual(metadata["selected_profile"], "quality")
            self.assertEqual(metadata["instance_type"], "ml.c6i.4xlarge")
            self.assertEqual(metadata["segment_count"], 1)

            cost_report = json.loads((output_dir / "cost_report.json").read_text(encoding="utf-8"))
            self.assertIn("runtimeEstimate", cost_report)
            self.assertIn("largeLandscapeProjection", cost_report)


if __name__ == "__main__":
    unittest.main()
