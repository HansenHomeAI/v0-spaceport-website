import importlib.util
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "diagnose_heldout_panels.py"
SPEC = importlib.util.spec_from_file_location("diagnose_heldout_panels_test_module", MODULE_PATH)
diagnostics = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = diagnostics
SPEC.loader.exec_module(diagnostics)


def chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def write_png(path: Path, image: np.ndarray) -> None:
    image_u8 = np.asarray(np.clip(image * 255, 0, 255), dtype=np.uint8)
    height, width, channels = image_u8.shape
    assert channels == 3
    scanlines = b"".join(b"\x00" + image_u8[row].tobytes() for row in range(height))
    payload = b"\x89PNG\r\n\x1a\n"
    payload += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    payload += chunk(b"IDAT", zlib.compress(scanlines))
    payload += chunk(b"IEND", b"")
    path.write_bytes(payload)


class HeldoutPanelDiagnosticsTest(unittest.TestCase):
    def test_exact_side_by_side_panel_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = np.zeros((4, 4, 3), dtype=np.float32)
            source[:, 2:] = 1.0
            panel = np.concatenate([source, source], axis=1)
            write_png(root / "eval_img_0000.png", panel)

            report = diagnostics.build_report(
                diagnostics.argparse.Namespace(
                    panel_dir=str(root),
                    output="",
                    glob="eval_img_*.png",
                    panel_columns=2,
                    baseline_report="",
                    max_panel_rmse_median=1.0,
                    min_panel_psnr_median=0.0,
                    min_edge_retention=0.92,
                    max_top_band_rmse=0.20,
                    max_top_brightness_delta=0.12,
                    max_top_dark_on_bright_fraction=0.02,
                    max_bottom_band_rmse_p90=0.22,
                )
            )

        self.assertEqual(report["decision"], "pass")
        self.assertEqual(report["panel_count"], 1)
        self.assertEqual(report["metrics"]["rmse"]["median"], 0.0)
        self.assertEqual(report["metrics"]["edge_retention_ratio"]["median"], 1.0)

    def test_soft_render_warns_on_detail_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checker = np.indices((8, 8)).sum(axis=0) % 2
            source = np.repeat(checker[..., None].astype(np.float32), 3, axis=2)
            render = np.full_like(source, 0.5)
            panel = np.concatenate([source, render], axis=1)
            write_png(root / "eval_img_0000.png", panel)

            report = diagnostics.build_report(
                diagnostics.argparse.Namespace(
                    panel_dir=str(root),
                    output="",
                    glob="eval_img_*.png",
                    panel_columns=2,
                    baseline_report="",
                    max_panel_rmse_median=1.0,
                    min_panel_psnr_median=0.0,
                    min_edge_retention=0.92,
                    max_top_band_rmse=0.20,
                    max_top_brightness_delta=0.12,
                    max_top_dark_on_bright_fraction=0.02,
                    max_bottom_band_rmse_p90=0.22,
                )
            )

        self.assertEqual(report["decision"], "warning")
        categories = {finding["category"] for finding in report["findings"]}
        self.assertIn("fine_detail_softness", categories)


if __name__ == "__main__":
    unittest.main()
