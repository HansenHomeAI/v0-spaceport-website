import importlib.util
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "sfm" / "run_colmap_sfm.py"
SPEC = importlib.util.spec_from_file_location("run_colmap_sfm_test_module", MODULE_PATH)
run_colmap_sfm = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = run_colmap_sfm
SPEC.loader.exec_module(run_colmap_sfm)


class ColmapGpsPriorTests(unittest.TestCase):
    def test_get_pose_prior_image_names_uses_schema_tolerant_join(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.database_path = root / "database.db"

            with sqlite3.connect(pipeline.database_path) as connection:
                connection.execute("CREATE TABLE images(image_id INTEGER PRIMARY KEY, name TEXT)")
                connection.execute(
                    """
                    CREATE TABLE pose_priors(
                        image_id INTEGER PRIMARY KEY,
                        position BLOB,
                        coordinate_system INTEGER,
                        position_covariance BLOB
                    )
                    """
                )
                connection.execute("INSERT INTO images(image_id, name) VALUES (1, 'a.jpg'), (2, 'b.jpg')")
                connection.execute(
                    """
                    INSERT INTO pose_priors(image_id, position, coordinate_system, position_covariance)
                    VALUES (2, X'00', 0, X'00')
                    """
                )
                connection.commit()

            self.assertEqual(pipeline.get_pose_prior_image_names(), {"b.jpg"})

    def test_validate_pose_priors_skips_backfill_for_newer_schema_variant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.database_path = root / "database.db"
            pipeline.gps_image_count = 2

            with sqlite3.connect(pipeline.database_path) as connection:
                connection.execute("CREATE TABLE images(image_id INTEGER PRIMARY KEY, name TEXT)")
                connection.execute(
                    """
                    CREATE TABLE pose_priors(
                        pose_prior_id INTEGER PRIMARY KEY,
                        position BLOB,
                        coordinate_system INTEGER,
                        position_covariance BLOB,
                        gravity BLOB,
                        corr_sensor_id INTEGER,
                        corr_sensor_type INTEGER
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO pose_priors(
                        pose_prior_id,
                        position,
                        coordinate_system,
                        position_covariance,
                        gravity,
                        corr_sensor_id,
                        corr_sensor_type
                    ) VALUES
                        (1, X'00', 0, X'00', NULL, NULL, NULL),
                        (2, X'00', 0, X'00', NULL, NULL, NULL)
                    """
                )
                connection.commit()

            pipeline.validate_or_backfill_pose_priors()

            self.assertEqual(pipeline.pose_priors_written_count, 2)
            self.assertEqual(pipeline.gps_prior_coverage, 1.0)
            self.assertEqual(pipeline.pose_priors_source, "feature_extractor")

    def test_backfill_pose_priors_restores_missing_wgs84_priors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            images_dir = root / "images"
            input_dir.mkdir()
            output_dir.mkdir()
            images_dir.mkdir()

            for name, latitude in [("a.jpg", 40.1001), ("b.jpg", 40.2002)]:
                image_path = images_dir / name
                subprocess.run(
                    [
                        "ffmpeg",
                        "-f",
                        "lavfi",
                        "-i",
                        "testsrc=size=512x512:rate=1",
                        "-frames:v",
                        "1",
                        str(image_path),
                        "-y",
                        "-loglevel",
                        "error",
                    ],
                    check=True,
                )
                subprocess.run(
                    [
                        "exiftool",
                        "-overwrite_original",
                        f"-GPSLatitude={latitude}",
                        "-GPSLongitude=-105.1234",
                        "-GPSAltitude=1500.5",
                        str(image_path),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                )

            pipeline = run_colmap_sfm.ColmapPipeline(input_dir, output_dir)
            pipeline.images_dir = images_dir
            pipeline.database_path = root / "database.db"
            pipeline.exif_records = pipeline.load_exif_records()
            pipeline.gps_image_count = len(pipeline.exif_records)

            subprocess.run(
                [
                    "colmap",
                    "feature_extractor",
                    "--database_path",
                    str(pipeline.database_path),
                    "--image_path",
                    str(images_dir),
                    "--ImageReader.single_camera",
                    "1",
                    "--ImageReader.camera_model",
                    "SIMPLE_RADIAL",
                    "--SiftExtraction.use_gpu",
                    "0",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            with sqlite3.connect(pipeline.database_path) as connection:
                connection.execute("DELETE FROM pose_priors")
                connection.commit()

            pipeline.validate_or_backfill_pose_priors()

            self.assertEqual(pipeline.pose_priors_source, "backfilled_from_exif")
            self.assertEqual(pipeline.pose_priors_written_count, 2)
            self.assertEqual(pipeline.gps_prior_coverage, 1.0)

            with sqlite3.connect(pipeline.database_path) as connection:
                rows = connection.execute(
                    "SELECT coordinate_system, length(position), length(position_covariance) "
                    "FROM pose_priors ORDER BY image_id"
                ).fetchall()

            self.assertEqual(rows, [(0, 24, 72), (0, 24, 72)])

    def test_should_attempt_gps_first_requires_prior_coverage_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.gps_image_count = 10
            pipeline.gps_prior_coverage = 0.94
            self.assertFalse(pipeline.should_attempt_gps_first())
            self.assertEqual(pipeline.gps_first_skipped_reason, "insufficient_pose_prior_coverage")

            pipeline.gps_prior_coverage = 0.95
            self.assertTrue(pipeline.should_attempt_gps_first())
            self.assertEqual(pipeline.gps_first_skipped_reason, "eligible")


if __name__ == "__main__":
    unittest.main()
