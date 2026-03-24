import sys
import tempfile
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2] / "infrastructure" / "containers" / "sfm"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from colmap_runner import SegmentRunResult
from exif_manifest import ImageRecord
from model_merge import ModelMerger
from segmenter import Segment


def write_sparse_model(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "cameras.bin").write_text("stub", encoding="utf-8")
    (root / "images.bin").write_text("stub", encoding="utf-8")
    (root / "points3D.bin").write_text("stub", encoding="utf-8")
    (root / "cameras.txt").write_text("1 SIMPLE_RADIAL 4000 3000 2000 2000 1500 0.01\n", encoding="utf-8")
    (root / "images.txt").write_text(
        "1 1 0 0 0 0 0 0 1 DJI_0001.JPG\n10 10 1\n",
        encoding="utf-8",
    )
    (root / "points3D.txt").write_text("1 0 0 0 255 255 255 0.2 1 0\n", encoding="utf-8")


def make_record(name: str) -> ImageRecord:
    return ImageRecord(
        name=name,
        path=f"/tmp/{name}",
        capture_time="2026-03-08T09:00:00",
        capture_sort_key=name,
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
        enu_x_m=0.0,
        enu_y_m=0.0,
        enu_z_m=0.0,
    )


class FakeRunner:
    def __init__(self):
        self.merge_attempts = 0
        self.boundary_runs = 0

    def _run_command(self, command, *, segment_id, stage):
        output_path = Path(command[-1])
        if "model_merger" in command:
            self.merge_attempts += 1
            if self.merge_attempts == 1:
                raise RuntimeError("merge failed")
            write_sparse_model(output_path / "0")
            return
        if "bundle_adjuster" in command:
            write_sparse_model(output_path / "0")
            return
        if "model_converter" in command:
            output_path.mkdir(parents=True, exist_ok=True)
            (output_path / "cameras.txt").write_text("1 SIMPLE_RADIAL 4000 3000 2000 2000 1500 0.01\n", encoding="utf-8")
            (output_path / "images.txt").write_text("1 1 0 0 0 0 0 0 1 DJI_0001.JPG\n10 10 1\n", encoding="utf-8")
            (output_path / "points3D.txt").write_text("1 0 0 0 255 255 255 0.2 1 0\n", encoding="utf-8")
            return

    def _resolve_model_dir(self, output_root):
        if (Path(output_root) / "0" / "cameras.bin").exists():
            return Path(output_root) / "0"
        if (Path(output_root) / "cameras.bin").exists():
            return Path(output_root)
        return None

    def run_boundary_segment(self, *, segment_id, image_names, record_lookup):
        self.boundary_runs += 1
        boundary_root = Path(tempfile.mkdtemp()) / "boundary"
        write_sparse_model(boundary_root / "0")
        return SegmentRunResult(
            segment_id=segment_id,
            image_count=len(image_names),
            engine="mapper",
            duration_seconds=5.0,
            workspace_dir=str(boundary_root.parent),
            database_path=str(boundary_root.parent / "database.db"),
            binary_model_dir=str(boundary_root / "0"),
            text_model_dir=str(boundary_root / "0"),
            metrics={"image_count": len(image_names), "camera_count": 1, "point_count": 1},
        )


class ModelMergeTests(unittest.TestCase):
    def test_merge_retries_with_boundary_segment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            left_root = root / "left" / "0"
            right_root = root / "right" / "0"
            write_sparse_model(left_root)
            write_sparse_model(right_root)

            runner = FakeRunner()
            merger = ModelMerger(
                runner=runner,
                work_dir=root,
                source_images_dir=root / "images",
            )
            segments = [
                Segment("segment-000", ["DJI_0001.JPG", "DJI_0002.JPG"], "DJI_0001.JPG", "DJI_0002.JPG", 2, 0, 90, False),
                Segment("segment-001", ["DJI_0002.JPG", "DJI_0003.JPG"], "DJI_0002.JPG", "DJI_0003.JPG", 2, 90, 0, False),
            ]
            results = [
                SegmentRunResult("segment-000", 2, "global_mapper", 5.0, str(root / "left"), str(root / "left.db"), str(left_root), str(left_root), {"image_count": 2, "camera_count": 1, "point_count": 1}),
                SegmentRunResult("segment-001", 2, "global_mapper", 5.0, str(root / "right"), str(root / "right.db"), str(right_root), str(right_root), {"image_count": 2, "camera_count": 1, "point_count": 1}),
            ]
            record_lookup = {name: make_record(name) for name in ["DJI_0001.JPG", "DJI_0002.JPG", "DJI_0003.JPG"]}

            merge_result = merger.merge_segments(
                segments=segments,
                segment_results=results,
                record_lookup=record_lookup,
            )

            self.assertGreaterEqual(runner.merge_attempts, 3)
            self.assertEqual(runner.boundary_runs, 1)
            self.assertTrue(merge_result.merge_steps)


if __name__ == "__main__":
    unittest.main()
