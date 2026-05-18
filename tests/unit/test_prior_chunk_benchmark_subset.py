import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "prepare_prior_chunk_subset.py"
SPEC = importlib.util.spec_from_file_location("prepare_prior_chunk_subset_test_module", MODULE_PATH)
prepare_subset = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = prepare_subset
SPEC.loader.exec_module(prepare_subset)


run_colmap_sfm = prepare_subset.run_colmap_sfm


class PriorChunkBenchmarkSubsetTests(unittest.TestCase):
    def test_build_retry_context_group_indices_expands_non_contiguous_intervals(self):
        chunk_plan = run_colmap_sfm.ChunkPlan(
            index=4,
            core_names=["IMG_010.jpg", "IMG_020.jpg", "IMG_021.jpg"],
            image_names=["IMG_010.jpg", "IMG_020.jpg", "IMG_021.jpg"],
            overlap_names=[],
            core_group_indices=[10, 20, 21],
            group_indices=[10, 20, 21],
            overlap_group_indices=[],
            segment_indices=[1, 2],
        )

        retry_group_indices = prepare_subset.build_retry_context_group_indices(
            chunk_plan=chunk_plan,
            chunk_group_count=30,
            retry_group_context=2,
        )

        self.assertEqual(retry_group_indices, [8, 9, 10, 11, 12, 18, 19, 20, 21, 22, 23])

    def test_collect_selected_image_names_includes_retry_context_groups(self):
        chunk_groups = [
            run_colmap_sfm.CaptureGroup(index=0, image_names=["IMG_001.jpg"], centroid_x_m=0.0, centroid_y_m=0.0, centroid_z_m=0.0, heading_deg=0.0, pitch_deg=0.0, start_capture_time_s=0.0, end_capture_time_s=0.0),
            run_colmap_sfm.CaptureGroup(index=1, image_names=["IMG_002.jpg"], centroid_x_m=1.0, centroid_y_m=0.0, centroid_z_m=0.0, heading_deg=0.0, pitch_deg=0.0, start_capture_time_s=1.0, end_capture_time_s=1.0),
            run_colmap_sfm.CaptureGroup(index=2, image_names=["IMG_003.jpg"], centroid_x_m=2.0, centroid_y_m=0.0, centroid_z_m=0.0, heading_deg=0.0, pitch_deg=0.0, start_capture_time_s=2.0, end_capture_time_s=2.0),
            run_colmap_sfm.CaptureGroup(index=3, image_names=["IMG_004.jpg"], centroid_x_m=3.0, centroid_y_m=0.0, centroid_z_m=0.0, heading_deg=0.0, pitch_deg=0.0, start_capture_time_s=3.0, end_capture_time_s=3.0),
        ]
        chunk_plan = run_colmap_sfm.ChunkPlan(
            index=1,
            core_names=["IMG_002.jpg", "IMG_003.jpg"],
            image_names=["IMG_002.jpg", "IMG_003.jpg"],
            overlap_names=[],
            core_group_indices=[1, 2],
            group_indices=[1, 2],
            overlap_group_indices=[],
            segment_indices=[0],
        )

        selected = prepare_subset.collect_selected_image_names(
            chunk_groups=chunk_groups,
            selected_chunk_plans=[chunk_plan],
            retry_group_context=1,
            include_retry_context=True,
        )

        self.assertEqual(selected, ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg", "IMG_004.jpg"])

    def test_collect_selected_image_names_can_skip_retry_context(self):
        chunk_groups = [
            run_colmap_sfm.CaptureGroup(index=0, image_names=["IMG_001.jpg"], centroid_x_m=0.0, centroid_y_m=0.0, centroid_z_m=0.0, heading_deg=0.0, pitch_deg=0.0, start_capture_time_s=0.0, end_capture_time_s=0.0),
            run_colmap_sfm.CaptureGroup(index=1, image_names=["IMG_002.jpg"], centroid_x_m=1.0, centroid_y_m=0.0, centroid_z_m=0.0, heading_deg=0.0, pitch_deg=0.0, start_capture_time_s=1.0, end_capture_time_s=1.0),
            run_colmap_sfm.CaptureGroup(index=2, image_names=["IMG_003.jpg"], centroid_x_m=2.0, centroid_y_m=0.0, centroid_z_m=0.0, heading_deg=0.0, pitch_deg=0.0, start_capture_time_s=2.0, end_capture_time_s=2.0),
        ]
        chunk_plan = run_colmap_sfm.ChunkPlan(
            index=1,
            core_names=["IMG_002.jpg"],
            image_names=["IMG_002.jpg"],
            overlap_names=[],
            core_group_indices=[1],
            group_indices=[1],
            overlap_group_indices=[],
            segment_indices=[0],
        )

        selected = prepare_subset.collect_selected_image_names(
            chunk_groups=chunk_groups,
            selected_chunk_plans=[chunk_plan],
            retry_group_context=2,
            include_retry_context=False,
        )

        self.assertEqual(selected, ["IMG_002.jpg"])


if __name__ == "__main__":
    unittest.main()
