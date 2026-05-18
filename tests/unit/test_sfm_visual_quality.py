import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "evaluate_visual_quality.py"
try:
    import numpy  # noqa: F401
except ModuleNotFoundError:
    visual_quality = None
else:
    SPEC = importlib.util.spec_from_file_location("evaluate_visual_quality_test_module", MODULE_PATH)
    visual_quality = importlib.util.module_from_spec(SPEC)
    sys.modules[SPEC.name] = visual_quality
    SPEC.loader.exec_module(visual_quality)


def write_ppm(path: Path, pixels: list[tuple[int, int, int]]) -> None:
    values = " ".join(f"{red} {green} {blue}" for red, green, blue in pixels)
    path.write_text(f"P3\n2 2\n255\n{values}\n", encoding="ascii")


@unittest.skipIf(visual_quality is None, "numpy is required for visual quality tests")
class SfmVisualQualityTest(unittest.TestCase):
    def test_exact_pair_produces_psnr_ssim_and_panel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.ppm"
            render = root / "render.ppm"
            pixels = [(0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255)]
            write_ppm(source, pixels)
            write_ppm(render, pixels)
            manifest = root / "pairs.json"
            manifest.write_text(
                json.dumps(
                    {
                        "model_uri": "s3://example/model",
                        "pairs": [
                            {
                                "id": "camera-1",
                                "source_image": str(source),
                                "rendered_image": str(render),
                                "lpips": 0.0,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            report = visual_quality.build_report(
                SimpleNamespace(
                    pairs_json=str(manifest),
                    panel_dir=str(root / "panels"),
                    output=str(root / "report.json"),
                    max_pairs=0,
                    allow_resize=False,
                    compute_lpips=False,
                )
            )
            self.assertTrue(Path(report["proof_panels"]["paths"][0]).exists())

        self.assertEqual(report["decision"], "pass")
        self.assertEqual(report["metrics"]["psnr"]["median"], 100.0)
        self.assertEqual(report["metrics"]["ssim"]["median"], 1.0)
        self.assertEqual(report["metrics"]["lpips"]["median"], 0.0)
        self.assertEqual(report["proof_panels"]["count"], 1)

    def test_missing_lpips_blocks_promotion_quality_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.ppm"
            render = root / "render.ppm"
            write_ppm(source, [(0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255)])
            write_ppm(render, [(0, 0, 0), (200, 0, 0), (0, 200, 0), (0, 0, 200)])
            manifest = root / "pairs.json"
            manifest.write_text(
                json.dumps({"pairs": [{"id": "camera-2", "source_image": str(source), "rendered_image": str(render)}]}),
                encoding="utf-8",
            )

            report = visual_quality.build_report(
                SimpleNamespace(
                    pairs_json=str(manifest),
                    panel_dir=str(root / "panels"),
                    output=str(root / "report.json"),
                    max_pairs=0,
                    allow_resize=False,
                    compute_lpips=False,
                )
            )

        self.assertEqual(report["decision"], "fail")
        self.assertIn("lpips_not_computed_for_all_pairs", report["blockers"])
        self.assertLess(report["metrics"]["psnr"]["median"], 100.0)


if __name__ == "__main__":
    unittest.main()
