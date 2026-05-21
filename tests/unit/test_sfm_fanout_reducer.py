import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SFM_SCRIPT_DIR = REPO_ROOT / "scripts" / "sfm"
if str(SFM_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SFM_SCRIPT_DIR))
MODULE_PATH = SFM_SCRIPT_DIR / "run_sfm_fanout_reducer.py"
SPEC = importlib.util.spec_from_file_location("run_sfm_fanout_reducer_test_module", MODULE_PATH)
fanout_reducer = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = fanout_reducer
SPEC.loader.exec_module(fanout_reducer)


class SfmFanoutReducerTest(unittest.TestCase):
    def test_materialize_leaf_sparse_prefers_filtered_sparse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leaf = root / "leaf"
            sparse_raw = leaf / "sparse_raw" / "0"
            sparse = leaf / "sparse" / "0"
            sparse_raw.mkdir(parents=True)
            sparse.mkdir(parents=True)
            for directory, marker in ((sparse_raw, "raw"), (sparse, "filtered")):
                (directory / "cameras.txt").write_text(f"# {marker}\n", encoding="utf-8")
                (directory / "images.txt").write_text(f"# {marker}\n", encoding="utf-8")
                (directory / "points3D.txt").write_text(f"# {marker}\n", encoding="utf-8")

            materialized, report = fanout_reducer.materialize_leaf_sparse(str(leaf), root / "downloaded")

            self.assertEqual((materialized / "cameras.txt").read_text(encoding="utf-8"), "# filtered\n")
            self.assertEqual(report["source"], str(sparse))

    def test_write_standard_output_package_writes_sparse_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            merged = root / "merged"
            merged.mkdir()
            for file_name in ("cameras.txt", "images.txt", "points3D.txt"):
                (merged / file_name).write_text(file_name, encoding="utf-8")
            output = root / "output"

            fanout_reducer.write_standard_output_package(
                merged_text_dir=merged,
                output_dir=output,
                reducer_metadata={"decision": "pass", "seam_merge_report": {"decision": "pass"}},
            )

            self.assertTrue((output / "sparse" / "0" / "images.txt").exists())
            self.assertTrue((output / "sparse_raw" / "0" / "points3D.txt").exists())
            self.assertIn("\"decision\": \"pass\"", (output / "reducer_metadata.json").read_text(encoding="utf-8"))
            self.assertIn("\"decision\": \"pass\"", (output / "seam_merge_report.json").read_text(encoding="utf-8"))

    def test_more_than_two_leaf_merge_skips_per_leaf_binary_converters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leaf_dirs = [root / f"leaf-{index:02d}" for index in range(3)]
            for leaf_dir in leaf_dirs:
                leaf_dir.mkdir()

            commands: list[list[str]] = []
            original_stats_for_model = fanout_reducer.stats_for_model
            original_global_image_ids = fanout_reducer.global_image_ids
            original_camera_signatures = fanout_reducer.camera_signatures
            original_rewrite_model_text = fanout_reducer.rewrite_model_text
            original_write_pose_aligned_merge = fanout_reducer.write_pose_aligned_merge
            original_run_command = fanout_reducer.run_command
            try:
                fanout_reducer.stats_for_model = lambda model_dir: fanout_reducer.ModelStats(1, 1, {str(model_dir)})
                fanout_reducer.global_image_ids = lambda model_dirs: {}
                fanout_reducer.camera_signatures = lambda model_dirs: ({}, {model_dir: {} for model_dir in model_dirs})

                def fake_rewrite_model_text(*, output_dir, **_kwargs):
                    output_dir.mkdir(parents=True, exist_ok=True)

                def fake_write_pose_aligned_merge(*, output_dir, **_kwargs):
                    output_dir.mkdir(parents=True, exist_ok=True)
                    for file_name in ("cameras.txt", "images.txt", "points3D.txt"):
                        (output_dir / file_name).write_text("# merged\n", encoding="utf-8")
                    return {
                        "strategy": "seam_graph_sim3_v1",
                        "transforms": [],
                        "seam_merge_report": {"decision": "pass", "accepted_merge_tree": []},
                        "promotion_blockers": [],
                    }

                def fake_run_command(command):
                    commands.append(command)
                    return {"command": command, "returncode": 0, "seconds": 0.0, "stdout_tail": "", "stderr_tail": ""}

                fanout_reducer.rewrite_model_text = fake_rewrite_model_text
                fanout_reducer.write_pose_aligned_merge = fake_write_pose_aligned_merge
                fanout_reducer.run_command = fake_run_command

                report = fanout_reducer.merge_leaf_models(
                    leaf_dirs=leaf_dirs,
                    work_dir=root / "merge",
                    colmap_bin="colmap",
                    min_shared_images=8,
                    scratch_cleanup_paths=[],
                )
            finally:
                fanout_reducer.stats_for_model = original_stats_for_model
                fanout_reducer.global_image_ids = original_global_image_ids
                fanout_reducer.camera_signatures = original_camera_signatures
                fanout_reducer.rewrite_model_text = original_rewrite_model_text
                fanout_reducer.write_pose_aligned_merge = original_write_pose_aligned_merge
                fanout_reducer.run_command = original_run_command

            self.assertEqual(report["commands"]["leaf_converters"], [])
            self.assertEqual(len(commands), 1)
            self.assertTrue(any("pose_aligned_text" in part for part in commands[0]))
            self.assertEqual(report["blockers"], [])
            self.assertEqual(report["fallback"]["strategy"], "seam_graph_sim3_v1")


if __name__ == "__main__":
    unittest.main()
