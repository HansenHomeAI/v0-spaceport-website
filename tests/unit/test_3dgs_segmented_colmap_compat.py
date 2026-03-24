import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
THREEDGS_ROOT = REPO_ROOT / "infrastructure" / "containers" / "3dgs"
if str(THREEDGS_ROOT) not in sys.path:
    sys.path.insert(0, str(THREEDGS_ROOT))

from utils.colmap_loader import load_colmap_data


class ThreeDgsCompatibilityTests(unittest.TestCase):
    def test_segmented_colmap_output_stays_loader_compatible(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sparse_dir = root / "sparse" / "0"
            images_dir = root / "images"
            sparse_dir.mkdir(parents=True)
            images_dir.mkdir(parents=True)

            (sparse_dir / "cameras.txt").write_text(
                "# cameras\n1 SIMPLE_RADIAL 4000 3000 2000 2000 1500 0.01\n",
                encoding="utf-8",
            )
            (sparse_dir / "images.txt").write_text(
                "# images\n"
                "1 1 0 0 0 0 0 0 1 DJI_0001.JPG\n10 10 1\n"
                "2 1 0 0 0 1 0 0 1 DJI_0002.JPG\n20 20 1\n",
                encoding="utf-8",
            )
            (sparse_dir / "points3D.txt").write_text(
                "# points\n1 0 0 0 255 255 255 0.2 1 0 2 0\n",
                encoding="utf-8",
            )
            (root / "segment_manifest.json").write_text(
                json.dumps({"segments": [{"segmentId": "segment-000"}]}),
                encoding="utf-8",
            )
            (images_dir / "DJI_0001.JPG").write_bytes(b"fake")
            (images_dir / "DJI_0002.JPG").write_bytes(b"fake")

            cameras, images, points = load_colmap_data(sparse_dir)

            self.assertEqual(len(cameras), 1)
            self.assertEqual(len(images), 2)
            self.assertEqual(len(points), 1)


if __name__ == "__main__":
    unittest.main()
