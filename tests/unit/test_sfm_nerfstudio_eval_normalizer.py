import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "normalize_nerfstudio_eval.py"
SPEC = importlib.util.spec_from_file_location("normalize_nerfstudio_eval_test_module", MODULE_PATH)
normalizer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = normalizer
SPEC.loader.exec_module(normalizer)


class NerfstudioEvalNormalizerTest(unittest.TestCase):
    def test_normalizes_nested_ns_eval_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            render_dir = root / "renders"
            render_dir.mkdir()
            (render_dir / "camera-1.png").write_bytes(b"fake")
            (render_dir / "camera-2.png").write_bytes(b"fake")
            raw = root / "ns-eval.json"
            raw.write_text(
                json.dumps(
                    {
                        "num_eval_images": 2,
                        "results": {
                            "eval/psnr": 27.5,
                            "eval/ssim": 0.84,
                            "eval/lpips": 0.18,
                        },
                    }
                ),
                encoding="utf-8",
            )

            report = normalizer.build_report(
                SimpleNamespace(
                    ns_eval_json=str(raw),
                    render_dir=str(render_dir),
                    output=str(root / "report.json"),
                    holdout_count=0,
                    successful_render_count=0,
                    model_uri="s3://example/model",
                    source_artifact_uri="",
                    render_artifact_uri="",
                )
            )

        self.assertEqual(report["decision"], "pass")
        self.assertEqual(report["holdout_count"], 2)
        self.assertEqual(report["successful_render_count"], 2)
        self.assertEqual(report["metrics"]["psnr"]["median"], 27.5)
        self.assertEqual(report["proof_panels"]["count"], 2)

    def test_missing_lpips_fails_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "ns-eval.json"
            raw.write_text(json.dumps({"results": {"psnr": 27.5, "ssim": 0.84}, "num_images": 3}), encoding="utf-8")

            report = normalizer.build_report(
                SimpleNamespace(
                    ns_eval_json=str(raw),
                    render_dir="",
                    output=str(root / "report.json"),
                    holdout_count=0,
                    successful_render_count=0,
                    model_uri="",
                    source_artifact_uri="",
                    render_artifact_uri="",
                )
            )

        self.assertEqual(report["decision"], "fail")
        self.assertIn("missing_lpips", report["blockers"])


if __name__ == "__main__":
    unittest.main()
