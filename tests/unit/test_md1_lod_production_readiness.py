import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "3dgs"
    / "md1_lod_production_readiness.py"
)

SPEC = importlib.util.spec_from_file_location("md1_lod_production_readiness", MODULE_PATH)
readiness = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(readiness)


def bundle_validation():
    return {
        "lod_meta_uri": "s3://bucket/prefix/supersplat_bundle/lod-meta.json",
        "output_prefix": "s3://bucket/prefix/",
        "gates": {
            "required_objects_present": True,
            "lod_meta_parse_ok": True,
            "sidecar_lineage_ok": True,
            "skybox_wired": True,
            "referenced_meta_present": True,
        },
        "lod_meta": {"lod_levels": 4, "filename_count": 44},
        "summary": {
            "source": "md1-r4-tile10-rollback-v18-nonregression-tile11-accepted",
            "fileCount": 356,
            "bundleSizeBytes": 166616347,
        },
    }


def smoke(*, first_frame_ms=500.0, pass_value=True):
    return {
        "checkedAt": "2026-05-06T03:21:15.242Z",
        "pass": pass_value,
        "health": {"https://preview.example": {"ok": True, "status": 200, "text": "OK"}},
        "results": [
            {
                "name": "desktop",
                "pass": pass_value,
                "url": "https://preview.example/md1-viewer",
                "manifest": "https://bucket.example/lod-meta.json",
                "metrics": {
                    "bundleKind": "lod-streaming",
                    "transport": "proxy",
                    "rootFile": "lod-meta.json",
                    "chunkFiles": "44",
                    "chunkMetaRequests": "3",
                    "firstFrameMs": str(first_frame_ms),
                    "lodMin": "0",
                    "lodMax": "3",
                },
                "interaction": {"ok": True},
                "canvasProbe": {"ok": True, "nonBlankProbe": True},
                "consoleMessages": [],
                "pageErrors": [],
            }
        ],
    }


def review(status="promoted", block_reasons=None):
    return {
        "promotion_decision": {
            "status": status,
            "block_reasons": block_reasons or [],
            "camera_coverage": {"status": "ok"},
            "render_sanity": {"status": "ok"},
            "fallback_tile_count": 0,
            "retain_all_tile_count": 0,
        }
    }


class MD1LODProductionReadinessTests(unittest.TestCase):
    def test_viewer_ready_quality_blocked_keeps_promotion_blocked(self):
        report = readiness.evaluate_readiness(
            bundle_validation=bundle_validation(),
            local_smoke=smoke(),
            preview_smoke=smoke(),
            review_comparison=review("blocked", ["boundary_no_required_improvement"]),
            min_lod_levels=4,
            min_chunk_files=1,
            expected_source="tile10-rollback",
            max_first_frame_ms=10_000,
        )

        self.assertEqual(report["status"], "viewer_ready_quality_blocked")
        self.assertTrue(report["viewer_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertEqual(report["quality_gate"]["block_reasons"], ["boundary_no_required_improvement"])
        self.assertEqual(readiness.exit_code_for(report, require_promotion_ready=False), 0)
        self.assertEqual(readiness.exit_code_for(report, require_promotion_ready=True), 3)

    def test_promotion_ready_requires_bundle_viewer_and_quality(self):
        report = readiness.evaluate_readiness(
            bundle_validation=bundle_validation(),
            local_smoke=smoke(),
            preview_smoke=smoke(),
            review_comparison=review("promoted"),
            min_lod_levels=4,
            min_chunk_files=1,
            expected_source="tile10-rollback",
            max_first_frame_ms=10_000,
        )

        self.assertEqual(report["status"], "production_promotion_ready")
        self.assertTrue(report["viewer_ready"])
        self.assertTrue(report["promotion_ready"])
        self.assertEqual(readiness.exit_code_for(report, require_promotion_ready=True), 0)

    def test_slow_first_frame_blocks_viewer_readiness(self):
        report = readiness.evaluate_readiness(
            bundle_validation=bundle_validation(),
            local_smoke=smoke(first_frame_ms=12_000),
            preview_smoke=smoke(),
            review_comparison=review("promoted"),
            min_lod_levels=4,
            min_chunk_files=1,
            expected_source="tile10-rollback",
            max_first_frame_ms=10_000,
        )

        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["viewer_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertEqual(readiness.exit_code_for(report, require_promotion_ready=False), 2)
        self.assertEqual(readiness.exit_code_for(report, require_promotion_ready=True), 3)
        self.assertIn(
            "desktop:scenario_first_frame_over_budget",
            report["local_viewer_gate"]["failures"],
        )

    def test_lineage_mismatch_blocks_bundle_gate(self):
        report = readiness.evaluate_readiness(
            bundle_validation=bundle_validation(),
            local_smoke=smoke(),
            preview_smoke=smoke(),
            review_comparison=review("promoted"),
            min_lod_levels=4,
            min_chunk_files=1,
            expected_source="wrong-lineage",
            max_first_frame_ms=10_000,
        )

        self.assertEqual(report["status"], "blocked")
        self.assertIn("bundle_source_lineage_mismatch", report["bundle_gate"]["failures"])


if __name__ == "__main__":
    unittest.main()
