import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SFM_SCRIPT_DIR = REPO_ROOT / "scripts" / "sfm"
if str(SFM_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SFM_SCRIPT_DIR))
MODULE_PATH = SFM_SCRIPT_DIR / "prepare_colmap_training_sample.py"
SPEC = importlib.util.spec_from_file_location("prepare_colmap_training_sample_test_module", MODULE_PATH)
sample = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = sample
SPEC.loader.exec_module(sample)


def write_model(path: Path) -> None:
    sparse = path / "sparse" / "0"
    sparse.mkdir(parents=True)
    (sparse / "cameras.txt").write_text(
        "\n".join(
            [
                "# Camera list with one line of data per camera:",
                "#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]",
                "# Number of cameras: 2",
                "1 PINHOLE 100 100 50 50 50 50",
                "2 PINHOLE 100 100 50 50 50 50",
                "",
            ]
        ),
        encoding="utf-8",
    )
    image_lines = [
        "# Image list with two lines of data per image:\n",
        "#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n",
        "#   POINTS2D[] as (X, Y, POINT3D_ID)\n",
    ]
    for image_id, camera_id in ((1, 1), (2, 1), (3, 2), (4, 2)):
        image_lines.append(f"{image_id} 1 0 0 0 0 0 0 {camera_id} image_{image_id}.jpg\n")
        image_lines.append(f"1 1 10 2 2 11 3 3 99\n")
    (sparse / "images.txt").write_text("".join(image_lines), encoding="utf-8")
    (sparse / "points3D.txt").write_text(
        "\n".join(
            [
                "# 3D point list with one line of data per point:",
                "#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)",
                "# Number of points: 3",
                "10 0 0 0 1 2 3 0.1 1 0 2 0",
                "11 1 0 0 4 5 6 0.1 3 1 4 1",
                "99 2 0 0 7 8 9 0.1 2 2 4 2",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (sparse / "frames.txt").write_text(
        "\n".join(
            [
                "# Frame list with one line of data per frame:",
                "#   FRAME_ID, RIG_ID, RIG_FROM_WORLD[QW, QX, QY, QZ, TX, TY, TZ], NUM_DATA_IDS, DATA_IDS[] as (SENSOR_TYPE, SENSOR_ID, DATA_ID)",
                "# Number of frames: 4",
                "1 1 1 0 0 0 0 0 0 1 CAMERA 1 1",
                "2 1 1 0 0 0 0 0 0 1 CAMERA 1 2",
                "3 1 1 0 0 0 0 0 0 1 CAMERA 2 3",
                "4 1 1 0 0 0 0 0 0 1 CAMERA 2 4",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (sparse / "rigs.txt").write_text("# rigs\n1 1 CAMERA 1\n", encoding="utf-8")


class ColmapTrainingSampleTest(unittest.TestCase):
    def test_camera_stratified_sample_keeps_both_cameras_and_rewrites_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            output = root / "sample"
            write_model(source)

            report = sample.prepare_sample(
                input_colmap_dir=source,
                output_colmap_dir=output,
                max_images=2,
                selection="camera-stratified-contiguous",
                min_track_length=1,
            )

            self.assertEqual(report["decision"], "pass")
            self.assertEqual(report["selected_camera_counts"], {"1": 1, "2": 1})
            images = (output / "sparse" / "0" / "images.txt").read_text(encoding="utf-8")
            self.assertIn("1 1 10", images)
            self.assertIn("2 2 11", images)
            self.assertIn("3 3 -1", images)
            frames = (output / "sparse" / "0" / "frames.txt").read_text(encoding="utf-8")
            self.assertIn("# Number of frames: 2", frames)

    def test_evenly_spaced_selection_includes_ends(self):
        records = [
            sample.ImageRecord(i, 1, f"image_{i}.jpg", f"{i} 1 0 0 0 0 0 0 1 image_{i}.jpg", "")
            for i in range(1, 11)
        ]

        selected = sample.select_evenly_spaced(records, 3)

        self.assertEqual([record.image_id for record in selected], [1, 5, 10])

    def test_image_max_width_scales_camera_intrinsics(self):
        line = "1 SIMPLE_RADIAL 4000 2250 3031.6234657742921 2000 1125 0.0011838781410337805"

        scaled, scale = sample.scale_camera_line(line, 1000)

        self.assertEqual(scale, 0.25)
        self.assertEqual(scaled, "1 SIMPLE_RADIAL 1000 562 757.905866444 500 281.25 0.0011838781410337805")

    def test_image_max_width_matches_pillow_fractional_height(self):
        line = "1 SIMPLE_RADIAL 4000 2250 3031.6234657742921 2000 1125 0.0011838781410337805"

        scaled, scale = sample.scale_camera_line(line, 1500)

        self.assertEqual(scale, 0.375)
        self.assertEqual(scaled.split()[2:4], ["1500", "843"])

    def test_prepare_sample_writes_scaled_cameras_without_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            output = root / "sample"
            write_model(source)

            report = sample.prepare_sample(
                input_colmap_dir=source,
                output_colmap_dir=output,
                max_images=2,
                selection="camera-stratified-contiguous",
                min_track_length=1,
                image_max_width=50,
            )

            cameras = (output / "sparse" / "0" / "cameras.txt").read_text(encoding="utf-8")
            self.assertEqual(report["scaled_camera_count"], 2)
            self.assertEqual(report["camera_scales"], {"1": 0.5, "2": 0.5})
            self.assertIn("1 PINHOLE 50 50 25 25 25 25", cameras)
            self.assertIn("2 PINHOLE 50 50 25 25 25 25", cameras)
            self.assertEqual(cameras.count("# Number of cameras:"), 1)
            self.assertIn("# Number of cameras: 2", cameras)

    def test_prepare_sample_scales_points2d_when_images_are_downscaled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            output = root / "sample"
            write_model(source)

            report = sample.prepare_sample(
                input_colmap_dir=source,
                output_colmap_dir=output,
                max_images=2,
                selection="camera-stratified-contiguous",
                min_track_length=1,
                image_max_width=50,
            )

            images = (output / "sparse" / "0" / "images.txt").read_text(encoding="utf-8")
            points = (output / "sparse" / "0" / "points3D.txt").read_text(encoding="utf-8")
            self.assertEqual(report["decision"], "pass")
            self.assertIn("0.5 0.5 10 1 1 11 1.5 1.5 -1", images)
            self.assertEqual(images.count("# Number of images:"), 1)
            self.assertEqual(points.count("# Number of points:"), 1)


if __name__ == "__main__":
    unittest.main()
