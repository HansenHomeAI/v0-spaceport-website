import importlib.util
import math
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "derive_viewer_camera_poses_from_colmap.py"
SPEC = importlib.util.spec_from_file_location("derive_viewer_camera_poses_from_colmap_test_module", MODULE_PATH)
poses_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = poses_module
SPEC.loader.exec_module(poses_module)


def write_images_txt(path: Path) -> None:
    payload = """# Image list with two lines per image.
# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
1 1 0 0 0 0.0 0.0 0.0 1 DJI_0001.JPG
0 0
2 1 0 0 0 1.0 0.0 0.0 1 DJI_0002.JPG
0 0
3 1 0 0 0 2.0 0.0 0.0 1 DJI_0003.JPG
0 0
4 1 0 0 0 3.0 0.0 0.0 1 DJI_0004.JPG
0 0
"""
    path.write_text(payload, encoding="utf-8")

def write_frames_txt(path: Path) -> None:
    payload = """# Frame list with one line of data per frame:
# FRAME_ID, RIG_ID, QW QX QY QZ TX TY TZ, NUM_DATA_IDS, (SENSOR_TYPE SENSOR_ID DATA_ID)...
1 1 1 0 0 0 0.0 0.0 0.0 1 CAMERA 1 1
2 1 1 0 0 0 1.0 0.0 0.0 1 CAMERA 1 2
3 1 1 0 0 0 2.0 0.0 0.0 1 CAMERA 1 3
"""
    path.write_text(payload, encoding="utf-8")


class ViewerCameraPoseDerivationTest(unittest.TestCase):
    def test_parses_images_txt(self):
        with tempfile.TemporaryDirectory() as tmp:
            images_path = Path(tmp) / "images.txt"
            write_images_txt(images_path)
            images = poses_module.parse_colmap_images_txt(images_path)
        self.assertEqual(len(images), 4)
        self.assertEqual(images[0].image_id, 1)
        self.assertEqual(images[-1].name, "DJI_0004.JPG")

    def test_derives_up_aligned_pose_strings(self):
        with tempfile.TemporaryDirectory() as tmp:
            images_path = Path(tmp) / "images.txt"
            write_images_txt(images_path)
            images = poses_module.parse_colmap_images_txt(images_path)
            normalization = poses_module.derive_normalization(images)
            center_list = normalization["center"]
            center = (float(center_list[0]), float(center_list[1]), float(center_list[2]))
            orient = poses_module.reshape_orient_row_major([float(x) for x in normalization["orient_row_major"]])
            scale = float(normalization["scale"])

            pose = poses_module.derive_pose(
                images[0],
                center=center,
                orient=orient,
                scale=scale,
                distance=0.3,
            )

        self.assertIn("camPos", pose)
        self.assertEqual(pose["name"], "DJI_0001.JPG")
        self.assertRegex(pose["camPos"], r"^-?\d+\.\d{6},-?\d+\.\d{6},-?\d+\.\d{6}$")
        self.assertRegex(pose["camTarget"], r"^-?\d+\.\d{6},-?\d+\.\d{6},-?\d+\.\d{6}$")
        self.assertRegex(pose["camUp"], r"^-?\d+\.\d{6},-?\d+\.\d{6},-?\d+\.\d{6}$")

        up = tuple(float(v) for v in pose["camUp"].split(","))
        up_norm = math.sqrt(sum(v * v for v in up))
        self.assertGreater(up_norm, 0.99)
        self.assertLess(abs(up_norm - 1.0), 1e-5)
        self.assertGreater(up[2], 0.98)

    def test_parses_frames_txt_with_explicit_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames_path = Path(tmp) / "frames.txt"
            write_frames_txt(frames_path)
            image_names = ["DJI_01000.JPG", "DJI_01001.JPG", "DJI_01002.JPG"]
            images = poses_module.parse_colmap_frames_txt(frames_path, image_names)
        self.assertEqual([img.name for img in images], image_names)

    def test_choose_samples_even_spacing(self):
        images = [poses_module.ParsedImage(image_id=i + 1, name=f"DJI_{i:04}.JPG", qvec=(1.0, 0.0, 0.0, 0.0), tvec=(0.0, 0.0, 0.0)) for i in range(10)]
        picked = poses_module.choose_samples(images, 3)
        self.assertEqual([img.image_id for img in picked], [1, 5, 10])


if __name__ == "__main__":
    unittest.main()
