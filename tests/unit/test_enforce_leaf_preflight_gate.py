import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "enforce_leaf_preflight_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("enforce_leaf_preflight_gate", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def passing_preflight(**overrides):
    payload = {
        "decision": "leaf_preflight_passed_cache_candidate",
        "block_reasons": [],
        "tile_id": "tile_00",
        "required_paths": {"present": ["splat.ply"], "missing": []},
        "training_metadata": {"training_completed": True},
        "training_selection": {
            "tile_id": "tile_00",
            "selected_image_count": 240,
            "scaffold_initialization": {
                "fallback_used": False,
                "scaffold_filter_selective": True,
                "source_filtered_gaussian_count": 24867,
                "inherited_gaussian_count": 24867,
            },
        },
        "splat_reference_guard": {"status": "ok"},
        "splat_vertex_count": 218479,
    }
    payload.update(overrides)
    return payload


class EnforceLeafPreflightGateTests(unittest.TestCase):
    def test_passes_clean_filtered_scaffold_leaf(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            preflight = Path(tmp) / "preflight.json"
            output = Path(tmp) / "gate.json"
            preflight.write_text(json.dumps(passing_preflight()), encoding="utf-8")

            report = module.build_report(
                SimpleNamespace(
                    preflight_json=str(preflight),
                    gate_json="<benchmark-summary-json>",
                    expected_tile_id="tile_00",
                    expected_selected_image_count=240,
                    require_filtered_scaffold=True,
                    summary_json_output=str(output),
                )
            )

            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["block_reasons"], [])

    def test_blocks_selected_image_count_mismatch(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            preflight = Path(tmp) / "preflight.json"
            output = Path(tmp) / "gate.json"
            preflight.write_text(json.dumps(passing_preflight()), encoding="utf-8")

            report = module.build_report(
                SimpleNamespace(
                    preflight_json=str(preflight),
                    gate_json="",
                    expected_tile_id="tile_00",
                    expected_selected_image_count=241,
                    require_filtered_scaffold=True,
                    summary_json_output=str(output),
                )
            )

            self.assertEqual(report["status"], "blocked")
            self.assertIn("leaf_selected_image_count_mismatch", report["block_reasons"])

    def test_blocks_scaffold_fallback(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            scaffold = {
                "fallback_used": True,
                "scaffold_filter_selective": False,
                "source_filtered_gaussian_count": 0,
                "inherited_gaussian_count": 0,
            }
            preflight = Path(tmp) / "preflight.json"
            output = Path(tmp) / "gate.json"
            preflight.write_text(
                json.dumps(
                    passing_preflight(
                        training_selection={
                            "tile_id": "tile_00",
                            "selected_image_count": 240,
                            "scaffold_initialization": scaffold,
                        }
                    )
                ),
                encoding="utf-8",
            )

            report = module.build_report(
                SimpleNamespace(
                    preflight_json=str(preflight),
                    gate_json="",
                    expected_tile_id="tile_00",
                    expected_selected_image_count=240,
                    require_filtered_scaffold=True,
                    summary_json_output=str(output),
                )
            )

            self.assertEqual(report["status"], "blocked")
            self.assertIn("leaf_scaffold_fallback_used", report["block_reasons"])
            self.assertIn("leaf_scaffold_filter_not_selective", report["block_reasons"])
            self.assertIn("leaf_filtered_scaffold_count_invalid", report["block_reasons"])


if __name__ == "__main__":
    unittest.main()
