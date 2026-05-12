import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "train_nerfstudio_production.py"
CONFIG_PATH = REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "nerfstudio_config.yaml"


def load_training_module():
    original_torch = sys.modules.get("torch")
    original_yaml = sys.modules.get("yaml")
    sys.modules["torch"] = types.SimpleNamespace(
        _dynamo=types.SimpleNamespace(config=types.SimpleNamespace(suppress_errors=False))
    )
    sys.modules["yaml"] = types.SimpleNamespace(safe_load=lambda _handle: {})
    try:
        spec = importlib.util.spec_from_file_location("nerfstudio_training_quality_test_module", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if original_torch is None:
            sys.modules.pop("torch", None)
        else:
            sys.modules["torch"] = original_torch
        if original_yaml is None:
            sys.modules.pop("yaml", None)
        else:
            sys.modules["yaml"] = original_yaml


class NerfstudioTrainingQualityGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.training = load_training_module()

    def test_ns_eval_report_passes_only_with_all_metrics_and_panels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            render_dir = root / "renders"
            render_dir.mkdir()
            (render_dir / "heldout-000.png").write_bytes(b"fake")
            raw = root / "ns_eval.json"
            raw.write_text(
                json.dumps(
                    {
                        "num_eval_images": 1,
                        "results": {
                            "eval/psnr": 28.0,
                            "eval/ssim": 0.86,
                            "eval/lpips": 0.16,
                        },
                    }
                ),
                encoding="utf-8",
            )

            report = self.training.build_splat_heldout_render_report(raw, render_dir, root / "config.yml")

        self.assertEqual(report["decision"], "pass")
        self.assertEqual(report["holdout_count"], 1)
        self.assertEqual(report["successful_render_count"], 1)
        self.assertEqual(report["metrics"]["lpips"]["median"], 0.16)
        self.assertEqual(report["proof_panels"]["count"], 1)

    def test_ns_eval_report_fails_without_lpips_or_render_panels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "ns_eval.json"
            raw.write_text(json.dumps({"num_eval_images": 2, "results": {"psnr": 25.0, "ssim": 0.8}}), encoding="utf-8")

            report = self.training.build_splat_heldout_render_report(raw, root / "missing-renders", root / "config.yml")

        self.assertEqual(report["decision"], "fail")
        self.assertIn("missing_lpips", report["blockers"])
        self.assertIn("missing_render_proof_panels", report["blockers"])

    def test_container_config_enables_required_heldout_eval(self):
        config_text = CONFIG_PATH.read_text(encoding="utf-8")
        self.assertIn("quality:", config_text)
        self.assertIn("heldout_eval:", config_text)
        self.assertIn("enabled: true", config_text)
        self.assertIn("fail_on_missing_metrics: true", config_text)


if __name__ == "__main__":
    unittest.main()
