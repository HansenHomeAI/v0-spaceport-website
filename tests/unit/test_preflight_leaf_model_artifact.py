import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "preflight_leaf_model_artifact.py"
SPEC = importlib.util.spec_from_file_location("preflight_leaf_model_artifact_test_module", MODULE_PATH)
preflight = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(preflight)


class PreflightLeafModelArtifactTests(unittest.TestCase):
    def test_reference_guard_blocks_over_dense_leaf(self):
        guard = preflight.build_splat_reference_guard(
            splat_vertex_count=1_733_527,
            reference_splat_count=387_192,
            max_reference_splat_ratio=1.5,
        )

        self.assertEqual(guard["status"], "blocked")
        self.assertEqual(guard["block_reason"], "splat_vertex_count_above_reference_ratio")
        self.assertAlmostEqual(guard["observed_reference_ratio"], 4.477, places=3)

    def test_reference_guard_passes_within_ratio(self):
        guard = preflight.build_splat_reference_guard(
            splat_vertex_count=420_000,
            reference_splat_count=387_192,
            max_reference_splat_ratio=1.5,
        )

        self.assertEqual(guard["status"], "ok")
        self.assertIsNone(guard["block_reason"])

    def test_reference_guard_is_optional(self):
        guard = preflight.build_splat_reference_guard(
            splat_vertex_count=1_733_527,
            reference_splat_count=0,
            max_reference_splat_ratio=0.0,
        )

        self.assertFalse(guard["enabled"])
        self.assertEqual(guard["status"], "not_configured")


if __name__ == "__main__":
    unittest.main()
