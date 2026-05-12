import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "run_sfm_reducer_canary.py"
SPEC = importlib.util.spec_from_file_location("run_sfm_reducer_canary_test_module", MODULE_PATH)
reducer_canary = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = reducer_canary
SPEC.loader.exec_module(reducer_canary)


class SfmReducerCanaryTest(unittest.TestCase):
    def test_rewrite_model_text_normalizes_image_camera_and_track_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            (source / "cameras.txt").write_text(
                "# Camera list\n7 PINHOLE 100 100 1 2 3 4\n",
                encoding="utf-8",
            )
            (source / "images.txt").write_text(
                "# Image list\n"
                "34 1 0 0 0 0 0 0 7 A.JPG\n"
                "0 0 1\n"
                "88 1 0 0 0 1 0 0 7 B.JPG\n"
                "0 0 2\n",
                encoding="utf-8",
            )
            (source / "points3D.txt").write_text(
                "# Point list\n"
                "9 0 0 0 255 0 0 0.7 34 0 88 1\n"
                "10 0 0 1 255 0 0 0.9 34 0\n",
                encoding="utf-8",
            )
            (source / "frames.txt").write_text(
                "# Frame list\n1 1 1 0 0 0 0 0 0 1 1 7 34\n",
                encoding="utf-8",
            )
            reducer_canary.rewrite_model_text(
                input_dir=source,
                output_dir=target,
                image_ids_by_name={"A.JPG": 1, "B.JPG": 2},
                camera_ids_by_old_id={7: 3},
                global_camera_records={3: ["PINHOLE", "100", "100", "1", "2", "3", "4"]},
            )

            images = (target / "images.txt").read_text(encoding="utf-8")
            points = (target / "points3D.txt").read_text(encoding="utf-8")
            frames = (target / "frames.txt").read_text(encoding="utf-8")

        self.assertIn("1 1 0 0 0 0 0 0 3 A.JPG", images)
        self.assertIn("2 1 0 0 0 1 0 0 3 B.JPG", images)
        self.assertIn("9 0 0 0 255 0 0 0.7 1 0 2 1", points)
        self.assertNotIn("10 0 0 1", points)
        self.assertIn("1 1 1 0 0 0 0 0 0 1 1 7 1", frames)


if __name__ == "__main__":
    unittest.main()
