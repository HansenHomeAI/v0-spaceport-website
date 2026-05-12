import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "evaluate_sfm_quality.py"
SPEC = importlib.util.spec_from_file_location("evaluate_sfm_quality_test_module", MODULE_PATH)
quality_eval = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = quality_eval
SPEC.loader.exec_module(quality_eval)


class SfmQualityEvalTest(unittest.TestCase):
    def test_report_passes_structural_geometry_with_unrun_render_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sparse = root / "sparse" / "0"
            sparse.mkdir(parents=True)
            (sparse / "images.txt").write_text(
                "# header\n"
                "1 1 0 0 0 0 0 0 1 A.JPG\n"
                "0 0 -1\n"
                "2 1 0 0 0 1 0 0 1 B.JPG\n"
                "0 0 -1\n",
                encoding="utf-8",
            )
            (sparse / "points3D.txt").write_text(
                "# header\n"
                "1 0 0 0 255 0 0 0.5 1 0 2 0\n"
                "2 1 0 0 0 255 0 1.0 1 1 2 1 1 2\n",
                encoding="utf-8",
            )
            sfm = root / "sfm.json"
            sfm.write_text(
                json.dumps(
                    {
                        "dataset_image_count": 2,
                        "points_3d": 2,
                        "chunk_merge_proof": {
                            "pre_merge_retention_ratio": 1.0,
                            "final_merged_registered_images": 2,
                            "merge_nodes": [
                                {
                                    "sequence": 1,
                                    "shared_registered_image_count": 12,
                                    "cross_edge_count": 20,
                                }
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )
            reducer = root / "reducer.json"
            reducer.write_text(
                json.dumps(
                    {
                        "leaf_count": 2,
                        "passed_leaf_count": 2,
                        "failed_leaf_count": 0,
                        "merged_component_count": 1,
                        "expected_component_count": 1,
                        "promotion_blockers": [],
                    }
                ),
                encoding="utf-8",
            )

            report = quality_eval.build_report(
                SimpleNamespace(
                    sparse_dir=str(sparse),
                    viewer_api_json="",
                    sfm_metadata=str(sfm),
                    reducer_metadata=str(reducer),
                    expected_images=2,
                    min_registered_ratio=0.98,
                    min_points=2,
                    max_reprojection_error_p95=8.0,
                    output=str(root / "report.json"),
                )
            )

        self.assertEqual(report["decision"], "needs_more_proof")
        self.assertEqual(report["summary"]["registered_images"], 2)
        self.assertEqual(report["sparse_points"]["reprojection_error"]["p95"], 1.0)
        self.assertIn("not_run", {gate["status"] for gate in report["gates"]})

    def test_failed_reducer_blocks_promotion(self):
        report = quality_eval.build_report(
            SimpleNamespace(
                sparse_dir="",
                viewer_api_json="",
                sfm_metadata="",
                reducer_metadata="",
                expected_images=10,
                min_registered_ratio=0.98,
                min_points=1000,
                max_reprojection_error_p95=8.0,
                output="unused.json",
            )
        )
        self.assertEqual(report["decision"], "do_not_promote")

    def test_reducer_canary_report_counts_as_component_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reducer = root / "reducer_canary.json"
            reducer.write_text(
                json.dumps(
                    {
                        "artifact_kind": "sfm_reducer_canary_report",
                        "decision": "pass",
                        "leaf_count": 2,
                        "merged_registered_images": 3,
                        "leaf_retention_ratios": [1.0, 1.0],
                        "blockers": [],
                        "fallback": {
                            "transforms": [
                                {
                                    "leaf_index": 1,
                                    "shared_registered_images": 12,
                                }
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            report = quality_eval.build_report(
                SimpleNamespace(
                    sparse_dir="",
                    viewer_api_json="",
                    sfm_metadata="",
                    reducer_metadata=str(reducer),
                    expected_images=3,
                    min_registered_ratio=0.98,
                    min_points=0,
                    max_reprojection_error_p95=8.0,
                    output=str(root / "report.json"),
                )
            )

        gates = {gate["gate"]: gate["status"] for gate in report["gates"]}
        self.assertEqual(gates["single_component"], "pass")

    def test_fanout_reducer_report_counts_as_component_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reducer = root / "fanout_reducer.json"
            reducer.write_text(
                json.dumps(
                    {
                        "artifact_kind": "sfm_fanout_reducer_report",
                        "decision": "pass",
                        "leaf_count": 2,
                        "passed_leaf_count": 2,
                        "failed_leaf_count": 0,
                        "merged_component_count": 1,
                        "expected_component_count": 1,
                        "promotion_blockers": [],
                        "merged_registered_images": 3,
                        "leaf_retention_ratios": [1.0, 1.0],
                        "fallback": {"transforms": [{"leaf_index": 1, "shared_registered_images": 12}]},
                    }
                ),
                encoding="utf-8",
            )
            report = quality_eval.build_report(
                SimpleNamespace(
                    sparse_dir="",
                    viewer_api_json="",
                    sfm_metadata="",
                    reducer_metadata=str(reducer),
                    expected_images=3,
                    min_registered_ratio=0.98,
                    min_points=0,
                    max_reprojection_error_p95=8.0,
                    output=str(root / "report.json"),
                )
            )

        gates = {gate["gate"]: gate["status"] for gate in report["gates"]}
        self.assertEqual(gates["reducer_blockers"], "pass")


if __name__ == "__main__":
    unittest.main()
