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
                "1 0 0 0 255 0 0 0.5 1 0 2 0 1 1\n"
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
        self.assertNotIn(
            "prove reducer ingest from independent leaf prefixes before full fanout",
            report["next_required_gates"],
        )

    def test_render_and_visual_gates_can_promote_when_all_proof_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sparse = root / "sparse" / "0"
            sparse.mkdir(parents=True)
            (sparse / "images.txt").write_text(
                "1 1 0 0 0 0 0 0 1 A.JPG\n0 0 -1\n"
                "2 1 0 0 0 1 0 0 1 B.JPG\n0 0 -1\n",
                encoding="utf-8",
            )
            (sparse / "points3D.txt").write_text(
                "1 0 0 0 255 0 0 0.5 1 0 2 0 1 1\n"
                "2 1 0 0 0 255 0 1.0 1 1 2 1 1 2\n",
                encoding="utf-8",
            )
            reducer = root / "reducer.json"
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
                        "merged_registered_images": 2,
                        "leaf_retention_ratios": [1.0, 1.0],
                        "fallback": {"transforms": [{"leaf_index": 1, "shared_registered_images": 12}]},
                    }
                ),
                encoding="utf-8",
            )
            render = root / "render.json"
            render.write_text(
                json.dumps(
                    {
                        "artifact_kind": "splat_heldout_render_metrics",
                        "holdout_count": 8,
                        "successful_render_count": 8,
                        "metrics": {
                            "psnr": {"median": 28.0, "p10": 24.0},
                            "ssim": {"median": 0.86, "p10": 0.78},
                            "lpips": {"median": 0.18, "p90": 0.28},
                        },
                        "baseline_metrics": {
                            "psnr": {"median": 28.4},
                            "ssim": {"median": 0.87},
                            "lpips": {"median": 0.17},
                        },
                    }
                ),
                encoding="utf-8",
            )
            visual = root / "visual.json"
            visual.write_text(
                json.dumps(
                    {
                        "artifact_kind": "ai_visual_review_report",
                        "decision": "pass",
                        "panel_count": 6,
                        "reviewed_panel_count": 6,
                        "blocking_defect_count": 0,
                        "warning_defect_count": 0,
                    }
                ),
                encoding="utf-8",
            )

            report = quality_eval.build_report(
                SimpleNamespace(
                    sparse_dir=str(sparse),
                    viewer_api_json="",
                    sfm_metadata="",
                    reducer_metadata=str(reducer),
                    heldout_render_json=str(render),
                    ai_visual_review_json=str(visual),
                    expected_images=2,
                    min_registered_ratio=0.98,
                    min_points=2,
                    max_reprojection_error_p95=8.0,
                    output=str(root / "report.json"),
                )
            )

        gates = {gate["gate"]: gate["status"] for gate in report["gates"]}
        self.assertEqual(gates["heldout_render_metrics"], "pass")
        self.assertEqual(gates["ai_visual_review"], "pass")
        self.assertEqual(report["decision"], "promote")

    def test_incomplete_render_metrics_fail_instead_of_pretending_quality(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            render = root / "render.json"
            render.write_text(
                json.dumps(
                    {
                        "artifact_kind": "training_metadata",
                        "validation_images": 8,
                        "final_validation_psnr": 25.0,
                    }
                ),
                encoding="utf-8",
            )
            report = quality_eval.build_report(
                SimpleNamespace(
                    sparse_dir="",
                    viewer_api_json="",
                    sfm_metadata="",
                    reducer_metadata="",
                    heldout_render_json=str(render),
                    ai_visual_review_json="",
                    expected_images=0,
                    min_registered_ratio=0.98,
                    min_points=0,
                    max_reprojection_error_p95=8.0,
                    output=str(root / "report.json"),
                )
            )

        gates = {gate["gate"]: gate["status"] for gate in report["gates"]}
        self.assertEqual(gates["heldout_render_metrics"], "fail")

    def test_panel_diagnostics_warning_keeps_report_from_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            panel = root / "panel.json"
            panel.write_text(
                json.dumps(
                    {
                        "artifact_kind": "heldout_panel_diagnostics",
                        "decision": "warning",
                        "panel_count": 24,
                        "metrics": {
                            "edge_retention_ratio": {"median": 0.8066},
                            "top_band_rmse": {"median": 0.0575},
                            "bottom_band_rmse": {"p90": 0.1184},
                        },
                        "findings": [
                            {
                                "severity": "warning",
                                "category": "fine_detail_softness",
                                "evidence": "median edge retention 0.8066 < 0.92",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            reducer = root / "reducer.json"
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
                        "merged_registered_images": 0,
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
                    heldout_render_json="",
                    ai_visual_review_json="",
                    panel_diagnostics_json=str(panel),
                    expected_images=0,
                    min_registered_ratio=0.0,
                    min_points=0,
                    max_reprojection_error_p95=8.0,
                    min_panel_diagnostics_panels=6,
                    output=str(root / "report.json"),
                )
            )

        gates = {gate["gate"]: gate["status"] for gate in report["gates"]}
        self.assertEqual(gates["heldout_panel_diagnostics"], "warning")
        self.assertEqual(report["panel_diagnostics"]["warning_defect_count"], 1)
        self.assertEqual(report["decision"], "needs_more_proof")

    def test_double_surface_geometry_gate_fails_layered_sparse_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sparse = root / "sparse" / "0"
            sparse.mkdir(parents=True)
            (sparse / "images.txt").write_text(
                "1 1 0 0 0 0 0 0 1 A.JPG\n0 0 -1\n"
                "2 1 0 0 0 1 0 0 1 B.JPG\n0 0 -1\n",
                encoding="utf-8",
            )
            point_lines = []
            for index in range(20):
                z = 0.0 if index < 10 else 8.0
                x = (index % 5) * 0.05
                y = (index // 5) * 0.05
                point_lines.append(
                    f"{index + 1} {x:.3f} {y:.3f} {z:.3f} 255 255 255 0.5 1 0 2 0 1 1"
                )
            (sparse / "points3D.txt").write_text("\n".join(point_lines) + "\n", encoding="utf-8")

            report = quality_eval.build_report(
                SimpleNamespace(
                    sparse_dir=str(sparse),
                    viewer_api_json="",
                    sfm_metadata="",
                    reducer_metadata="",
                    expected_images=0,
                    min_registered_ratio=0.0,
                    min_points=1,
                    max_reprojection_error_p95=8.0,
                    output=str(root / "report.json"),
                )
            )

        gates = {gate["gate"]: gate["status"] for gate in report["gates"]}
        self.assertEqual(gates["double_surface_geometry"], "fail")
        self.assertGreater(report["sparse_points"]["double_surface"]["flagged_cell_count"], 0)


if __name__ == "__main__":
    unittest.main()
