import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "enforce_leaf_preflight_gate.py"
SPEC = importlib.util.spec_from_file_location("enforce_leaf_preflight_gate_test_module", MODULE_PATH)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(gate)


def passing_preflight() -> dict:
    return {
        "artifact_uri": "s3://bucket/tile_10/model.tar.gz",
        "job_name": "tile10-proof",
        "tile_id": "tile_10",
        "decision": "leaf_preflight_passed_cache_candidate",
        "required_paths": {"missing": []},
        "training_metadata": {"training_completed": True},
        "training_selection": {
            "tile_id": "tile_10",
            "selected_image_count": 188,
            "scaffold_initialization": {
                "filtered_point_cloud": "/tmp/scaffold_init.ply",
                "inherited_gaussian_count": 300000,
                "fallback_used": False,
                "scaffold_inheritance_mode": "global_scaffold_ply_filtered_point_cloud",
            },
        },
        "splat_reference_guard": {
            "enabled": True,
            "status": "ok",
            "block_reason": None,
        },
        "splat_vertex_count": 540000,
    }


class EnforceLeafPreflightGateTests(unittest.TestCase):
    def test_allows_passing_guarded_leaf(self):
        summary = gate.evaluate_gate(
            preflight=passing_preflight(),
            gate={"required_leaf_preflight_gate": {"hard_max_splat_count": 580788}},
            expected_tile_id="tile_10",
            expected_selected_image_count=188,
            require_filtered_scaffold=True,
        )

        self.assertEqual(summary["decision"], "merge_review_allowed")
        self.assertEqual(summary["block_reasons"], [])

    def test_blocks_over_dense_leaf_even_if_preflight_decision_is_stale(self):
        preflight = passing_preflight()
        preflight["splat_vertex_count"] = 1_733_527
        preflight["splat_reference_guard"] = {
            "enabled": True,
            "status": "blocked",
            "block_reason": "splat_vertex_count_above_reference_ratio",
        }

        summary = gate.evaluate_gate(
            preflight=preflight,
            gate={"required_leaf_preflight_gate": {"hard_max_splat_count": 580788}},
            expected_tile_id="tile_10",
            expected_selected_image_count=188,
            require_filtered_scaffold=True,
        )

        self.assertEqual(summary["decision"], "merge_review_blocked")
        self.assertIn("splat_vertex_count_above_reference_ratio", summary["block_reasons"])
        self.assertIn("splat_vertex_count_above_hard_max", summary["block_reasons"])

    def test_blocks_under_dense_leaf_before_merge_review(self):
        preflight = passing_preflight()
        preflight["splat_vertex_count"] = 559_981
        preflight["splat_reference_guard"] = {
            "enabled": True,
            "status": "blocked",
            "block_reason": "splat_vertex_count_below_reference_ratio",
        }

        summary = gate.evaluate_gate(
            preflight=preflight,
            gate={"required_leaf_preflight_gate": {"hard_min_splat_count": 765021}},
            expected_tile_id="tile_10",
            expected_selected_image_count=188,
            require_filtered_scaffold=True,
        )

        self.assertEqual(summary["decision"], "merge_review_blocked")
        self.assertIn("splat_vertex_count_below_reference_ratio", summary["block_reasons"])
        self.assertIn("splat_vertex_count_below_hard_min", summary["block_reasons"])

    def test_blocks_missing_filtered_scaffold(self):
        preflight = passing_preflight()
        preflight["training_selection"]["scaffold_initialization"] = {"fallback_used": True}

        summary = gate.evaluate_gate(
            preflight=preflight,
            gate={"required_leaf_preflight_gate": {"hard_max_splat_count": 580788}},
            expected_tile_id="tile_10",
            expected_selected_image_count=188,
            require_filtered_scaffold=True,
        )

        self.assertEqual(summary["decision"], "merge_review_blocked")
        self.assertIn("filtered_scaffold_initialization_missing", summary["block_reasons"])

    def test_selects_tile_gate_from_benchmark_summary(self):
        summary = gate.evaluate_gate(
            preflight=passing_preflight(),
            gate={
                "post_leaf_preflight_gates": [
                    {
                        "tile_id": "tile_10",
                        "required_leaf_preflight_gate": {
                            "hard_max_splat_count": 580788,
                            "pass_decision": "leaf_preflight_passed_cache_candidate",
                        },
                    }
                ]
            },
            expected_tile_id="tile_10",
            expected_selected_image_count=188,
            require_filtered_scaffold=True,
        )

        self.assertEqual(summary["decision"], "merge_review_allowed")
        self.assertEqual(summary["hard_max_splat_count"], 580788)


if __name__ == "__main__":
    unittest.main()
