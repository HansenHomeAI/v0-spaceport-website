import importlib.util
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "sfm" / "run_colmap_sfm.py"
SPEC = importlib.util.spec_from_file_location("run_colmap_sfm_test_module", MODULE_PATH)
run_colmap_sfm = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = run_colmap_sfm
SPEC.loader.exec_module(run_colmap_sfm)


class ColmapGpsPriorTests(unittest.TestCase):
    def test_match_profile_picks_profile_defaults(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {
                "COLMAP_MATCH_PROFILE": "P2",
                "COLMAP_ENABLE_SEQUENTIAL_MATCHER": "1",
            },
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")

            self.assertEqual(pipeline.match_profile, "P2")
            self.assertEqual(pipeline.spatial_neighbors, 14)
            self.assertEqual(pipeline.spatial_distance_m, 140.0)
            self.assertEqual(pipeline.sequential_overlap, 8)

    def test_match_profile_marks_custom_when_overridden(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {
                "COLMAP_MATCH_PROFILE": "P1",
                "COLMAP_SPATIAL_MAX_NEIGHBORS": "16",
                "COLMAP_ENABLE_SEQUENTIAL_MATCHER": "0",
            },
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")

            self.assertEqual(pipeline.match_profile, "custom")
            self.assertEqual(pipeline.spatial_neighbors, 16)
            self.assertFalse(pipeline.enable_sequential_matcher)

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

    def test_gps_first_uses_sequential_first_pass_when_registration_is_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.dataset_image_count = 3
            pipeline.gps_image_count = 3
            pipeline.gps_prior_coverage = 1.0
            pipeline.enable_sequential_matcher = True

            calls: list[str] = []

            def record_call(name: str):
                def inner(*args, **kwargs):
                    calls.append(name)
                    return None

                return inner

            pipeline.run_spatial_matcher = record_call("spatial_matcher")
            pipeline.run_sequential_matcher = record_call("sequential_matcher")
            pipeline.run_vocab_matching = record_call("vocab_tree_matcher")
            pipeline.run_mapper = mock.Mock(
                return_value=run_colmap_sfm.ModelSummary(
                    stage="mapper_spatial_sequential_only",
                    text_dir=root,
                    cameras_registered=1,
                    images_registered=3,
                    points_3d=2500,
                )
            )

            best_model = pipeline.run_matching_and_mapping()

            self.assertEqual(best_model.images_registered, 3)
            self.assertEqual(calls, ["spatial_matcher", "sequential_matcher"])
            self.assertEqual(pipeline.final_matcher_mode, "spatial_sequential_only")
            self.assertFalse(pipeline.fallback_triggered)
            self.assertEqual(pipeline.fallback_reason, "not_needed")

    def test_gps_first_fails_fast_when_registration_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.dataset_image_count = 4
            pipeline.gps_image_count = 4
            pipeline.gps_prior_coverage = 1.0
            pipeline.enable_sequential_matcher = True

            calls: list[str] = []

            def record_call(name: str):
                def inner(*args, **kwargs):
                    calls.append(name)
                    return None

                return inner

            spatial_model = run_colmap_sfm.ModelSummary(
                stage="mapper_spatial_sequential_only",
                text_dir=root,
                cameras_registered=1,
                images_registered=3,
                points_3d=3000,
            )

            pipeline.run_spatial_matcher = record_call("spatial_matcher")
            pipeline.run_sequential_matcher = record_call("sequential_matcher")
            pipeline.run_vocab_matching = record_call("vocab_tree_matcher")
            pipeline.run_mapper = mock.Mock(return_value=spatial_model)

            with self.assertRaisesRegex(RuntimeError, "below 98.00% threshold"):
                pipeline.run_matching_and_mapping()

            self.assertEqual(calls, ["spatial_matcher", "sequential_matcher"])
            self.assertFalse(pipeline.fallback_triggered)
            self.assertEqual(pipeline.fallback_reason, "not_needed")
            self.assertEqual(pipeline.failure_stage, "mapper_spatial_sequential_plus_vocab")

    def test_gps_first_fails_fast_when_mapper_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.dataset_image_count = 4
            pipeline.gps_image_count = 4
            pipeline.gps_prior_coverage = 1.0
            pipeline.enable_sequential_matcher = True

            calls: list[str] = []

            def record_call(name: str):
                def inner(*args, **kwargs):
                    calls.append(name)
                    return None

                return inner

            pipeline.run_spatial_matcher = record_call("spatial_matcher")
            pipeline.run_sequential_matcher = record_call("sequential_matcher")
            pipeline.run_vocab_matching = record_call("vocab_tree_matcher")
            pipeline.run_mapper = mock.Mock(side_effect=RuntimeError("mapper exploded"))

            with self.assertRaisesRegex(RuntimeError, "GPS-first mapper failed: mapper exploded"):
                pipeline.run_matching_and_mapping()

            self.assertEqual(calls, ["spatial_matcher", "sequential_matcher"])
            self.assertFalse(pipeline.fallback_triggered)
            self.assertEqual(pipeline.fallback_reason, "not_needed")
            self.assertEqual(pipeline.failure_stage, "mapper_spatial_sequential_only")

    def test_gps_first_accepts_ratio_threshold_without_vocab_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.dataset_image_count = 100
            pipeline.gps_image_count = 100
            pipeline.gps_prior_coverage = 1.0
            pipeline.enable_sequential_matcher = True
            pipeline.gps_min_registered_ratio = 0.98

            calls: list[str] = []

            def record_call(name: str):
                def inner(*args, **kwargs):
                    calls.append(name)
                    return None

                return inner

            spatial_model = run_colmap_sfm.ModelSummary(
                stage="mapper_spatial_sequential_only",
                text_dir=root,
                cameras_registered=1,
                images_registered=98,
                points_3d=5000,
            )

            pipeline.run_spatial_matcher = record_call("spatial_matcher")
            pipeline.run_sequential_matcher = record_call("sequential_matcher")
            pipeline.run_vocab_matching = record_call("vocab_tree_matcher")
            pipeline.run_mapper = mock.Mock(return_value=spatial_model)

            best_model = pipeline.run_matching_and_mapping()

            self.assertEqual(best_model.images_registered, 98)
            self.assertEqual(calls, ["spatial_matcher", "sequential_matcher"])
            self.assertFalse(pipeline.fallback_triggered)
            self.assertEqual(pipeline.fallback_reason, "not_needed")
            self.assertEqual(pipeline.final_matcher_mode, "spatial_sequential_only")

    def test_run_mapper_does_not_pass_image_list_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            sparse_root = root / "sparse_vocab_only"
            (sparse_root / "0").mkdir(parents=True, exist_ok=True)

            with mock.patch.object(run_colmap_sfm, "stream_command") as stream_command_mock, mock.patch.object(
                run_colmap_sfm, "count_text_rows", return_value=1
            ), mock.patch.object(run_colmap_sfm, "count_registered_images", return_value=3):
                model = pipeline.run_mapper(stage="mapper_vocab_only", sparse_root=sparse_root)

            mapper_args = stream_command_mock.call_args_list[0].kwargs["stage"]
            self.assertEqual(mapper_args, "mapper_vocab_only")
            mapper_command = stream_command_mock.call_args_list[0].args[0]
            self.assertNotIn("--image_list_path", mapper_command)
            self.assertEqual(model.images_registered, 3)

    def test_run_sequential_matcher_avoids_runtime_specific_matching_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")

            with mock.patch.object(run_colmap_sfm, "stream_command") as stream_command_mock, mock.patch.object(
                pipeline, "count_verified_pairs", side_effect=[10, 16]
            ):
                pipeline.run_sequential_matcher()

            command = stream_command_mock.call_args.args[0]
            self.assertIn("sequential_matcher", command)
            self.assertNotIn("--SiftMatching.use_gpu", command)
            self.assertNotIn("--SiftMatching.guided_matching", command)
            self.assertEqual(pipeline.matcher_pair_deltas["sequential_matcher"], 6)
            self.assertIn("sequential_matcher", pipeline.matchers_run)

    def test_run_feature_extraction_falls_back_to_sift_option_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")

            error = RuntimeError(
                "feature_extractor failed with exit code 1\n"
                "Failed to parse options - unrecognised option '--FeatureExtraction.use_gpu'."
            )
            with mock.patch.object(
                run_colmap_sfm,
                "stream_command",
                side_effect=[error, None],
            ) as stream_command_mock:
                pipeline.run_feature_extraction()

            first_command = stream_command_mock.call_args_list[0].args[0]
            second_command = stream_command_mock.call_args_list[1].args[0]
            self.assertIn("--FeatureExtraction.use_gpu", first_command)
            self.assertIn("--SiftExtraction.use_gpu", second_command)
            self.assertEqual(pipeline.feature_option_family, "SiftExtraction")

    def test_run_spatial_matcher_falls_back_to_sift_matching_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")

            error = RuntimeError(
                "spatial_matcher failed with exit code 1\n"
                "Failed to parse options - unrecognised option '--FeatureMatching.use_gpu'."
            )
            with mock.patch.object(
                run_colmap_sfm,
                "stream_command",
                side_effect=[error, None],
            ) as stream_command_mock, mock.patch.object(
                pipeline,
                "count_verified_pairs",
                side_effect=[10, 10],
            ):
                pipeline.run_spatial_matcher()

            first_command = stream_command_mock.call_args_list[0].args[0]
            second_command = stream_command_mock.call_args_list[1].args[0]
            self.assertIn("--FeatureMatching.use_gpu", first_command)
            self.assertIn("--SiftMatching.use_gpu", second_command)
            self.assertEqual(pipeline.matching_option_family, "SiftMatching")

    def test_run_matches_importer_falls_back_to_sift_matching_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            match_list_path = root / "match_list.txt"
            match_list_path.write_text("A.jpg B.jpg\n", encoding="utf-8")

            error = RuntimeError(
                "matches_importer failed with exit code 1\n"
                "Failed to parse options - unrecognised option '--FeatureMatching.use_gpu'."
            )
            with mock.patch.object(
                run_colmap_sfm,
                "stream_command",
                side_effect=[error, None],
            ) as stream_command_mock, mock.patch.object(
                pipeline,
                "count_verified_pairs",
                side_effect=[10, 12],
            ):
                pipeline.run_matches_importer(match_list_path=match_list_path)

            first_command = stream_command_mock.call_args_list[0].args[0]
            second_command = stream_command_mock.call_args_list[1].args[0]
            self.assertIn("--FeatureMatching.use_gpu", first_command)
            self.assertIn("--SiftMatching.use_gpu", second_command)
            self.assertEqual(pipeline.matching_option_family, "SiftMatching")

    def test_run_exhaustive_matcher_falls_back_to_sift_matching_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")

            error = RuntimeError(
                "exhaustive_matcher failed with exit code 1\n"
                "Failed to parse options - unrecognised option '--FeatureMatching.use_gpu'."
            )
            with mock.patch.object(
                run_colmap_sfm,
                "stream_command",
                side_effect=[error, None],
            ) as stream_command_mock, mock.patch.object(
                pipeline,
                "count_verified_pairs",
                side_effect=[10, 12],
            ):
                pipeline.run_exhaustive_matcher()

            first_command = stream_command_mock.call_args_list[0].args[0]
            second_command = stream_command_mock.call_args_list[1].args[0]
            self.assertIn("--FeatureMatching.use_gpu", first_command)
            self.assertIn("--SiftMatching.use_gpu", second_command)
            self.assertEqual(pipeline.matching_option_family, "SiftMatching")

    def test_run_bundle_adjuster_retries_without_gpu_flag_for_older_colmap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            input_path = root / "merged"
            input_path.mkdir(parents=True, exist_ok=True)
            summary = run_colmap_sfm.ModelSummary(
                stage="chunk_bundle_adjuster",
                text_dir=root / "text",
                cameras_registered=1,
                images_registered=10,
                points_3d=1000,
                binary_dir=root / "chunk_bundle_adjuster",
            )
            error = RuntimeError(
                "chunk_bundle_adjuster failed with exit code 1\n"
                "Failed to parse options - unrecognised option '--BundleAdjustment.use_gpu'."
            )
            with mock.patch.object(
                run_colmap_sfm,
                "stream_command",
                side_effect=[error, None],
            ) as stream_command_mock, mock.patch.object(
                pipeline,
                "summarize_model",
                return_value=summary,
            ):
                result = pipeline.run_bundle_adjuster(input_path=input_path, stage="chunk_bundle_adjuster")

            first_command = stream_command_mock.call_args_list[0].args[0]
            second_command = stream_command_mock.call_args_list[1].args[0]
            self.assertIn("--BundleAdjustment.use_gpu", first_command)
            self.assertNotIn("--BundleAdjustment.use_gpu", second_command)
            self.assertTrue((pipeline.work_dir / "chunk_bundle_adjuster").is_dir())
            self.assertEqual(result.images_registered, 10)

    def test_build_spatial_heading_chunks_groups_by_spatial_proximity_not_capture_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.chunk_target_images = 4
            pipeline.chunk_min_images = 2
            pipeline.chunk_overlap_images = 1
            pipeline.capture_ordered_names = [
                "A1.jpg",
                "B1.jpg",
                "A2.jpg",
                "B2.jpg",
            ]
            pipeline.exif_records = {
                "A1.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "A2.jpg": {"local_x_m": 2.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "B1.jpg": {"local_x_m": 500.0, "local_y_m": 0.0, "heading_deg": 180.0},
                "B2.jpg": {"local_x_m": 502.0, "local_y_m": 0.0, "heading_deg": 180.0},
            }

            chunks = pipeline.build_spatial_heading_chunks()

            self.assertEqual(len(chunks), 2)
            self.assertEqual(set(chunks[0].core_names), {"A1.jpg", "A2.jpg"})
            self.assertEqual(set(chunks[1].core_names), {"B1.jpg", "B2.jpg"})

    def test_build_spatial_heading_chunks_adds_overlap_between_adjacent_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.chunk_target_images = 3
            pipeline.chunk_min_images = 2
            pipeline.chunk_overlap_images = 2
            pipeline.capture_ordered_names = [
                "IMG_01.jpg",
                "IMG_02.jpg",
                "IMG_03.jpg",
                "IMG_04.jpg",
                "IMG_05.jpg",
                "IMG_06.jpg",
            ]
            pipeline.exif_records = {
                "IMG_01.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_02.jpg": {"local_x_m": 1.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_03.jpg": {"local_x_m": 2.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_04.jpg": {"local_x_m": 50.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_05.jpg": {"local_x_m": 51.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_06.jpg": {"local_x_m": 52.0, "local_y_m": 0.0, "heading_deg": 0.0},
            }

            chunks = pipeline.build_spatial_heading_chunks()

            self.assertGreaterEqual(len(chunks), 2)
            shared_names = set(chunks[0].image_names).intersection(chunks[1].image_names)
            self.assertTrue(shared_names)
            self.assertGreater(pipeline.chunk_overlap_image_count, 0)

    def test_build_spatial_heading_chunks_keeps_multiple_chunks_for_large_balanced_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.chunk_target_images = 200
            pipeline.chunk_min_images = 120
            pipeline.chunk_overlap_images = 30
            pipeline.chunk_max_radius_m = 300.0
            pipeline.capture_ordered_names = [f"IMG_{index:03d}.jpg" for index in range(250)]
            pipeline.exif_records = {
                image_name: {
                    "local_x_m": float(index * 8),
                    "local_y_m": 0.0,
                    "heading_deg": 0.0,
                }
                for index, image_name in enumerate(pipeline.capture_ordered_names)
            }

            chunks = pipeline.build_spatial_heading_chunks()

            self.assertEqual(len(chunks), 2)
            self.assertTrue(all(len(chunk.core_names) >= 120 for chunk in chunks))
            self.assertEqual(sum(len(chunk.core_names) for chunk in chunks), 250)

    def test_build_view_geometries_prefers_relative_altitude_and_camera_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.exif_records = {
                "IMG_001.jpg": {
                    "local_x_m": 0.0,
                    "local_y_m": 0.0,
                    "local_z_m": 4.0,
                    "relative_altitude": 42.0,
                    "absolute_altitude": 980.0,
                    "heading_deg": 30.0,
                    "pitch_deg": -35.0,
                    "focal_length_mm": 10.3,
                    "focal_length_35mm_mm": 24.0,
                    "image_width_px": 4000,
                    "image_height_px": 3000,
                }
            }

            geometries = pipeline.build_view_geometries()

            self.assertIn("IMG_001.jpg", geometries)
            self.assertEqual(geometries["IMG_001.jpg"].effective_altitude_m, 42.0)
            self.assertGreater(geometries["IMG_001.jpg"].horizontal_fov_deg, 0.0)
            self.assertFalse(geometries["IMG_001.jpg"].is_shallow_view)

    def test_build_footprint_graph_chunks_creates_probe_subsets(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_CHUNK_PLANNER": "footprint_graph_v1"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.chunk_target_images = 3
            pipeline.chunk_min_images = 2
            pipeline.chunk_hard_max_images = 4
            pipeline.leaf_target_images = 3
            pipeline.leaf_hard_cap_images = 4
            pipeline.capture_ordered_names = [
                "A1.jpg",
                "A2.jpg",
                "A3.jpg",
                "B1.jpg",
                "B2.jpg",
                "B3.jpg",
            ]
            pipeline.colmap_capabilities["supports_matches_importer"] = False
            pipeline.exif_records = {
                "A1.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "local_z_m": 0.0, "relative_altitude": 30.0, "heading_deg": 5.0, "pitch_deg": -25.0, "capture_time_s": 1.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
                "A2.jpg": {"local_x_m": 2.0, "local_y_m": 1.0, "local_z_m": 0.0, "relative_altitude": 32.0, "heading_deg": 15.0, "pitch_deg": -45.0, "capture_time_s": 2.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
                "A3.jpg": {"local_x_m": 4.0, "local_y_m": 1.0, "local_z_m": 0.0, "relative_altitude": 34.0, "heading_deg": 20.0, "pitch_deg": -6.0, "capture_time_s": 3.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
                "B1.jpg": {"local_x_m": 120.0, "local_y_m": 0.0, "local_z_m": 0.0, "relative_altitude": 28.0, "heading_deg": 182.0, "pitch_deg": -20.0, "capture_time_s": 4.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
                "B2.jpg": {"local_x_m": 122.0, "local_y_m": 1.0, "local_z_m": 0.0, "relative_altitude": 29.0, "heading_deg": 190.0, "pitch_deg": -40.0, "capture_time_s": 5.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
                "B3.jpg": {"local_x_m": 124.0, "local_y_m": 1.0, "local_z_m": 0.0, "relative_altitude": 31.0, "heading_deg": 195.0, "pitch_deg": -8.0, "capture_time_s": 6.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
            }

            chunks = pipeline.build_chunk_plans()

            self.assertGreaterEqual(len(chunks), 2)
            self.assertEqual(pipeline.chunk_matcher_strategy, "exhaustive")
            self.assertEqual(set(pipeline.probe_subsets), {"geometry_mix", "cross_pass", "horizon_context"})
            self.assertEqual(set(pipeline.ladder_subsets), {"ladder_1000", "ladder_2000"})
            self.assertTrue(all(pipeline.probe_subsets.values()))
            self.assertTrue(all(pipeline.ladder_subsets.values()))
            self.assertTrue(
                any(
                    len(details.get("source_chunk_indexes", [])) >= 2
                    for details in pipeline.probe_subset_details.values()
                )
            )

    def test_build_retry_chunk_plan_footprint_graph_adds_graph_neighbors(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_CHUNK_PLANNER": "footprint_graph_v1"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.capture_ordered_names = ["A.jpg", "B.jpg", "C.jpg"]
            pipeline.image_group_indices = {"A.jpg": 0, "B.jpg": 1, "C.jpg": 2}
            pipeline.graph_neighbors = {
                "A.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="A.jpg",
                        second_name="C.jpg",
                        score=0.9,
                        footprint_overlap=0.9,
                        scale_similarity=0.9,
                        viewpoint_complementarity=0.9,
                        distance_consistency=0.9,
                        temporal_bonus=0.0,
                        xy_distance_m=5.0,
                        xyz_distance_m=5.0,
                        view_delta_deg=15.0,
                    )
                ]
            }
            chunk_plan = run_colmap_sfm.ChunkPlan(
                index=0,
                core_names=["A.jpg", "B.jpg"],
                image_names=["A.jpg", "B.jpg"],
                overlap_names=[],
                core_group_indices=[0, 1],
                group_indices=[0, 1],
                overlap_group_indices=[],
                segment_indices=[],
            )

            retry_chunk = pipeline.build_retry_chunk_plan(chunk_plan, ["A.jpg"])

            self.assertEqual(retry_chunk.core_names, ["A.jpg", "B.jpg"])
            self.assertIn("C.jpg", retry_chunk.image_names)

    def test_build_footprint_graph_chunks_expands_small_tail_chunk_with_support_images(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_CHUNK_PLANNER": "footprint_graph_v1"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.chunk_target_images = 3
            pipeline.chunk_min_images = 3
            pipeline.chunk_hard_max_images = 4
            pipeline.leaf_target_images = 3
            pipeline.leaf_hard_cap_images = 4
            pipeline.capture_ordered_names = ["A1.jpg", "A2.jpg", "A3.jpg", "B1.jpg"]
            pipeline.exif_records = {
                "A1.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "local_z_m": 0.0, "heading_deg": 0.0, "pitch_deg": -30.0},
                "A2.jpg": {"local_x_m": 1.0, "local_y_m": 0.0, "local_z_m": 0.0, "heading_deg": 0.0, "pitch_deg": -30.0},
                "A3.jpg": {"local_x_m": 2.0, "local_y_m": 0.0, "local_z_m": 0.0, "heading_deg": 0.0, "pitch_deg": -30.0},
                "B1.jpg": {"local_x_m": 8.0, "local_y_m": 0.0, "local_z_m": 0.0, "heading_deg": 5.0, "pitch_deg": -30.0},
            }
            pipeline.graph_neighbors = {
                "A1.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="A1.jpg",
                        second_name="A2.jpg",
                        score=0.9,
                        footprint_overlap=0.9,
                        scale_similarity=0.9,
                        viewpoint_complementarity=0.9,
                        distance_consistency=0.9,
                        temporal_bonus=0.0,
                        xy_distance_m=1.0,
                        xyz_distance_m=1.0,
                        view_delta_deg=5.0,
                    )
                ],
                "A2.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="A2.jpg",
                        second_name="A3.jpg",
                        score=0.9,
                        footprint_overlap=0.9,
                        scale_similarity=0.9,
                        viewpoint_complementarity=0.9,
                        distance_consistency=0.9,
                        temporal_bonus=0.0,
                        xy_distance_m=1.0,
                        xyz_distance_m=1.0,
                        view_delta_deg=5.0,
                    )
                ],
                "A3.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="A3.jpg",
                        second_name="B1.jpg",
                        score=0.6,
                        footprint_overlap=0.6,
                        scale_similarity=0.6,
                        viewpoint_complementarity=0.6,
                        distance_consistency=0.6,
                        temporal_bonus=0.0,
                        xy_distance_m=6.0,
                        xyz_distance_m=6.0,
                        view_delta_deg=10.0,
                    )
                ],
                "B1.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="B1.jpg",
                        second_name="A3.jpg",
                        score=0.6,
                        footprint_overlap=0.6,
                        scale_similarity=0.6,
                        viewpoint_complementarity=0.6,
                        distance_consistency=0.6,
                        temporal_bonus=0.0,
                        xy_distance_m=6.0,
                        xyz_distance_m=6.0,
                        view_delta_deg=10.0,
                    )
                ],
            }

            with mock.patch.object(pipeline, "build_view_geometries"), mock.patch.object(
                pipeline, "build_candidate_graph"
            ), mock.patch.object(
                pipeline,
                "classify_graph_roles",
                return_value={name: "geometry_anchor" for name in pipeline.capture_ordered_names},
            ):
                chunks = pipeline.build_footprint_graph_chunks()

            self.assertGreaterEqual(len(chunks), 2)
            self.assertTrue(all(len(chunk.image_names) >= 3 for chunk in chunks))
            self.assertTrue(
                any("B1.jpg" in chunk.image_names and len(chunk.image_names) >= 3 for chunk in chunks)
            )

    def test_build_footprint_graph_chunks_connects_isolated_chunks_with_bridge_overlap(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_CHUNK_PLANNER": "footprint_graph_v1"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.chunk_target_images = 2
            pipeline.chunk_min_images = 2
            pipeline.chunk_hard_max_images = 3
            pipeline.leaf_target_images = 2
            pipeline.leaf_hard_cap_images = 3
            pipeline.capture_ordered_names = [
                "A1.jpg",
                "A2.jpg",
                "B1.jpg",
                "B2.jpg",
                "C1.jpg",
                "C2.jpg",
            ]
            pipeline.exif_records = {
                "A1.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "local_z_m": 0.0, "relative_altitude": 30.0, "heading_deg": 0.0, "pitch_deg": -30.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
                "A2.jpg": {"local_x_m": 1.0, "local_y_m": 0.0, "local_z_m": 0.0, "relative_altitude": 30.0, "heading_deg": 5.0, "pitch_deg": -32.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
                "B1.jpg": {"local_x_m": 60.0, "local_y_m": 0.0, "local_z_m": 0.0, "relative_altitude": 32.0, "heading_deg": 8.0, "pitch_deg": -28.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
                "B2.jpg": {"local_x_m": 61.0, "local_y_m": 0.0, "local_z_m": 0.0, "relative_altitude": 32.0, "heading_deg": 10.0, "pitch_deg": -30.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
                "C1.jpg": {"local_x_m": 120.0, "local_y_m": 0.0, "local_z_m": 0.0, "relative_altitude": 34.0, "heading_deg": 12.0, "pitch_deg": -26.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
                "C2.jpg": {"local_x_m": 121.0, "local_y_m": 0.0, "local_z_m": 0.0, "relative_altitude": 34.0, "heading_deg": 14.0, "pitch_deg": -28.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
            }
            pipeline.graph_neighbors = {
                "A1.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="A1.jpg",
                        second_name="A2.jpg",
                        score=0.95,
                        footprint_overlap=0.95,
                        scale_similarity=0.95,
                        viewpoint_complementarity=0.95,
                        distance_consistency=0.95,
                        temporal_bonus=0.0,
                        xy_distance_m=1.0,
                        xyz_distance_m=1.0,
                        view_delta_deg=5.0,
                    )
                ],
                "A2.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="A2.jpg",
                        second_name="A1.jpg",
                        score=0.95,
                        footprint_overlap=0.95,
                        scale_similarity=0.95,
                        viewpoint_complementarity=0.95,
                        distance_consistency=0.95,
                        temporal_bonus=0.0,
                        xy_distance_m=1.0,
                        xyz_distance_m=1.0,
                        view_delta_deg=5.0,
                    )
                ],
                "B1.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="B1.jpg",
                        second_name="B2.jpg",
                        score=0.95,
                        footprint_overlap=0.95,
                        scale_similarity=0.95,
                        viewpoint_complementarity=0.95,
                        distance_consistency=0.95,
                        temporal_bonus=0.0,
                        xy_distance_m=1.0,
                        xyz_distance_m=1.0,
                        view_delta_deg=4.0,
                    )
                ],
                "B2.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="B2.jpg",
                        second_name="B1.jpg",
                        score=0.95,
                        footprint_overlap=0.95,
                        scale_similarity=0.95,
                        viewpoint_complementarity=0.95,
                        distance_consistency=0.95,
                        temporal_bonus=0.0,
                        xy_distance_m=1.0,
                        xyz_distance_m=1.0,
                        view_delta_deg=4.0,
                    )
                ],
                "C1.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="C1.jpg",
                        second_name="C2.jpg",
                        score=0.95,
                        footprint_overlap=0.95,
                        scale_similarity=0.95,
                        viewpoint_complementarity=0.95,
                        distance_consistency=0.95,
                        temporal_bonus=0.0,
                        xy_distance_m=1.0,
                        xyz_distance_m=1.0,
                        view_delta_deg=4.0,
                    )
                ],
                "C2.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="C2.jpg",
                        second_name="C1.jpg",
                        score=0.95,
                        footprint_overlap=0.95,
                        scale_similarity=0.95,
                        viewpoint_complementarity=0.95,
                        distance_consistency=0.95,
                        temporal_bonus=0.0,
                        xy_distance_m=1.0,
                        xyz_distance_m=1.0,
                        view_delta_deg=4.0,
                    )
                ],
            }

            with mock.patch.object(
                pipeline,
                "classify_graph_roles",
                return_value={name: "geometry_anchor" for name in pipeline.capture_ordered_names},
            ):
                chunks = pipeline.build_footprint_graph_chunks()

            self.assertEqual(len(chunks), 3)
            self.assertTrue(all(len(chunk.image_names) <= 3 for chunk in chunks))
            chunk_sets = [set(chunk.image_names) for chunk in chunks]
            self.assertTrue(
                all(
                    any(chunk_sets[index].intersection(chunk_sets[other_index]) for other_index in range(len(chunk_sets)) if other_index != index)
                    for index in range(len(chunk_sets))
                )
            )

    def test_build_footprint_graph_chunks_caps_overlap_growth_per_leaf(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_CHUNK_PLANNER": "footprint_graph_v1"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.chunk_target_images = 2
            pipeline.chunk_min_images = 2
            pipeline.chunk_hard_max_images = 3
            pipeline.leaf_target_images = 2
            pipeline.leaf_hard_cap_images = 3
            pipeline.chunk_cross_edge_min_count = 1
            pipeline.capture_ordered_names = [
                "A1.jpg",
                "A2.jpg",
                "B1.jpg",
                "B2.jpg",
                "C1.jpg",
                "C2.jpg",
            ]
            pipeline.exif_records = {
                "A1.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "local_z_m": 0.0, "relative_altitude": 30.0, "heading_deg": 0.0, "pitch_deg": -30.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
                "A2.jpg": {"local_x_m": 1.0, "local_y_m": 0.0, "local_z_m": 0.0, "relative_altitude": 30.0, "heading_deg": 5.0, "pitch_deg": -30.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
                "B1.jpg": {"local_x_m": 60.0, "local_y_m": 0.0, "local_z_m": 0.0, "relative_altitude": 31.0, "heading_deg": 8.0, "pitch_deg": -30.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
                "B2.jpg": {"local_x_m": 61.0, "local_y_m": 0.0, "local_z_m": 0.0, "relative_altitude": 31.0, "heading_deg": 10.0, "pitch_deg": -30.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
                "C1.jpg": {"local_x_m": 120.0, "local_y_m": 0.0, "local_z_m": 0.0, "relative_altitude": 32.0, "heading_deg": 12.0, "pitch_deg": -30.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
                "C2.jpg": {"local_x_m": 121.0, "local_y_m": 0.0, "local_z_m": 0.0, "relative_altitude": 32.0, "heading_deg": 14.0, "pitch_deg": -30.0, "focal_length_mm": 10.0, "focal_length_35mm_mm": 24.0, "image_width_px": 4000, "image_height_px": 3000},
            }
            pipeline.graph_neighbors = {
                "A1.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="A1.jpg",
                        second_name="A2.jpg",
                        score=0.95,
                        footprint_overlap=0.95,
                        scale_similarity=0.95,
                        viewpoint_complementarity=0.95,
                        distance_consistency=0.95,
                        temporal_bonus=0.0,
                        xy_distance_m=1.0,
                        xyz_distance_m=1.0,
                        view_delta_deg=5.0,
                    )
                ],
                "A2.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="A2.jpg",
                        second_name="A1.jpg",
                        score=0.95,
                        footprint_overlap=0.95,
                        scale_similarity=0.95,
                        viewpoint_complementarity=0.95,
                        distance_consistency=0.95,
                        temporal_bonus=0.0,
                        xy_distance_m=1.0,
                        xyz_distance_m=1.0,
                        view_delta_deg=5.0,
                    ),
                    run_colmap_sfm.CandidateEdge(
                        first_name="A2.jpg",
                        second_name="B1.jpg",
                        score=0.7,
                        footprint_overlap=0.7,
                        scale_similarity=0.7,
                        viewpoint_complementarity=0.7,
                        distance_consistency=0.7,
                        temporal_bonus=0.0,
                        xy_distance_m=10.0,
                        xyz_distance_m=10.0,
                        view_delta_deg=10.0,
                    ),
                ],
                "B1.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="B1.jpg",
                        second_name="B2.jpg",
                        score=0.95,
                        footprint_overlap=0.95,
                        scale_similarity=0.95,
                        viewpoint_complementarity=0.95,
                        distance_consistency=0.95,
                        temporal_bonus=0.0,
                        xy_distance_m=1.0,
                        xyz_distance_m=1.0,
                        view_delta_deg=4.0,
                    ),
                    run_colmap_sfm.CandidateEdge(
                        first_name="B1.jpg",
                        second_name="A2.jpg",
                        score=0.7,
                        footprint_overlap=0.7,
                        scale_similarity=0.7,
                        viewpoint_complementarity=0.7,
                        distance_consistency=0.7,
                        temporal_bonus=0.0,
                        xy_distance_m=10.0,
                        xyz_distance_m=10.0,
                        view_delta_deg=10.0,
                    ),
                ],
                "B2.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="B2.jpg",
                        second_name="B1.jpg",
                        score=0.95,
                        footprint_overlap=0.95,
                        scale_similarity=0.95,
                        viewpoint_complementarity=0.95,
                        distance_consistency=0.95,
                        temporal_bonus=0.0,
                        xy_distance_m=1.0,
                        xyz_distance_m=1.0,
                        view_delta_deg=4.0,
                    ),
                    run_colmap_sfm.CandidateEdge(
                        first_name="B2.jpg",
                        second_name="C1.jpg",
                        score=0.7,
                        footprint_overlap=0.7,
                        scale_similarity=0.7,
                        viewpoint_complementarity=0.7,
                        distance_consistency=0.7,
                        temporal_bonus=0.0,
                        xy_distance_m=10.0,
                        xyz_distance_m=10.0,
                        view_delta_deg=10.0,
                    ),
                ],
                "C1.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="C1.jpg",
                        second_name="C2.jpg",
                        score=0.95,
                        footprint_overlap=0.95,
                        scale_similarity=0.95,
                        viewpoint_complementarity=0.95,
                        distance_consistency=0.95,
                        temporal_bonus=0.0,
                        xy_distance_m=1.0,
                        xyz_distance_m=1.0,
                        view_delta_deg=4.0,
                    ),
                    run_colmap_sfm.CandidateEdge(
                        first_name="C1.jpg",
                        second_name="B2.jpg",
                        score=0.7,
                        footprint_overlap=0.7,
                        scale_similarity=0.7,
                        viewpoint_complementarity=0.7,
                        distance_consistency=0.7,
                        temporal_bonus=0.0,
                        xy_distance_m=10.0,
                        xyz_distance_m=10.0,
                        view_delta_deg=10.0,
                    ),
                ],
                "C2.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="C2.jpg",
                        second_name="C1.jpg",
                        score=0.95,
                        footprint_overlap=0.95,
                        scale_similarity=0.95,
                        viewpoint_complementarity=0.95,
                        distance_consistency=0.95,
                        temporal_bonus=0.0,
                        xy_distance_m=1.0,
                        xyz_distance_m=1.0,
                        view_delta_deg=4.0,
                    )
                ],
            }

            with mock.patch.object(
                pipeline,
                "classify_graph_roles",
                return_value={name: "geometry_anchor" for name in pipeline.capture_ordered_names},
            ):
                chunks = pipeline.build_footprint_graph_chunks()

            self.assertEqual(len(chunks), 3)
            self.assertTrue(all(len(chunk.image_names) <= 3 for chunk in chunks))
            chunk_sets = [set(chunk.image_names) for chunk in chunks]
            self.assertTrue(chunk_sets[0].intersection(chunk_sets[1]))
            self.assertTrue(chunk_sets[1].intersection(chunk_sets[2]))

    def test_run_chunk_matchers_uses_matches_importer_for_footprint_graph(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_CHUNK_PLANNER": "footprint_graph_v1"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.colmap_capabilities["supports_matches_importer"] = True
            pipeline.graph_neighbors = {
                "A.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="A.jpg",
                        second_name="B.jpg",
                        score=0.9,
                        footprint_overlap=0.9,
                        scale_similarity=0.9,
                        viewpoint_complementarity=0.9,
                        distance_consistency=0.9,
                        temporal_bonus=0.0,
                        xy_distance_m=5.0,
                        xyz_distance_m=5.0,
                        view_delta_deg=15.0,
                    )
                ],
                "B.jpg": [],
            }
            chunk_plan = run_colmap_sfm.ChunkPlan(
                index=0,
                core_names=["A.jpg", "B.jpg"],
                image_names=["A.jpg", "B.jpg"],
                overlap_names=[],
            )
            chunk_dir = root / "chunk"
            chunk_dir.mkdir(parents=True, exist_ok=True)

            with mock.patch.object(pipeline, "run_matches_importer") as importer_mock, mock.patch.object(
                pipeline, "run_exhaustive_matcher"
            ) as exhaustive_mock:
                pipeline.run_chunk_matchers(
                    chunk_plan,
                    chunk_database_path=root / "chunk.db",
                    chunk_dir=chunk_dir,
                    stage_prefix="chunk_00",
                )

            importer_mock.assert_called_once()
            exhaustive_mock.assert_not_called()

    def test_write_chunk_match_list_adds_bridge_target_pairs(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_CHUNK_PLANNER": "footprint_graph_v1"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.capture_ordered_names = ["A.jpg", "B.jpg", "C.jpg", "D.jpg", "E.jpg"]
            pipeline.exif_records = {
                name: {"local_x_m": float(index), "local_y_m": 0.0, "heading_deg": 0.0}
                for index, name in enumerate(pipeline.capture_ordered_names)
            }
            pipeline.graph_neighbors = {
                "A.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="A.jpg",
                        second_name="B.jpg",
                        score=0.9,
                        footprint_overlap=0.9,
                        scale_similarity=0.9,
                        viewpoint_complementarity=0.9,
                        distance_consistency=0.9,
                        temporal_bonus=0.0,
                        xy_distance_m=5.0,
                        xyz_distance_m=5.0,
                        view_delta_deg=10.0,
                    )
                ],
                "B.jpg": [],
                "C.jpg": [
                    run_colmap_sfm.CandidateEdge(
                        first_name="C.jpg",
                        second_name="D.jpg",
                        score=0.9,
                        footprint_overlap=0.9,
                        scale_similarity=0.9,
                        viewpoint_complementarity=0.9,
                        distance_consistency=0.9,
                        temporal_bonus=0.0,
                        xy_distance_m=5.0,
                        xyz_distance_m=5.0,
                        view_delta_deg=10.0,
                    )
                ],
                "D.jpg": [],
                "E.jpg": [],
            }
            chunk_plan = run_colmap_sfm.ChunkPlan(
                index=1,
                core_names=["A.jpg", "B.jpg", "C.jpg", "D.jpg"],
                image_names=["A.jpg", "B.jpg", "C.jpg", "D.jpg", "E.jpg"],
                overlap_names=["E.jpg"],
            )
            chunk_dir = root / "chunk"
            chunk_dir.mkdir(parents=True, exist_ok=True)

            def candidate_edge(first_name: str, second_name: str) -> run_colmap_sfm.CandidateEdge:
                pair_key = tuple(sorted((first_name, second_name)))
                score_map = {
                    ("A.jpg", "C.jpg"): 0.82,
                    ("A.jpg", "D.jpg"): 0.76,
                    ("B.jpg", "C.jpg"): 0.78,
                    ("B.jpg", "D.jpg"): 0.74,
                    ("C.jpg", "E.jpg"): 0.71,
                    ("D.jpg", "E.jpg"): 0.69,
                    ("A.jpg", "E.jpg"): 0.68,
                    ("B.jpg", "E.jpg"): 0.67,
                }
                score = score_map.get(pair_key, 0.2)
                return run_colmap_sfm.CandidateEdge(
                    first_name=pair_key[0],
                    second_name=pair_key[1],
                    score=score,
                    footprint_overlap=score,
                    scale_similarity=score,
                    viewpoint_complementarity=score,
                    distance_consistency=score,
                    temporal_bonus=0.0,
                    xy_distance_m=5.0,
                    xyz_distance_m=5.0,
                    view_delta_deg=15.0,
                )

            with mock.patch.object(
                pipeline,
                "classify_graph_roles",
                return_value={name: "geometry_anchor" for name in pipeline.capture_ordered_names},
            ), mock.patch.object(
                pipeline,
                "candidate_edge_for_names",
                side_effect=candidate_edge,
            ):
                pair_list_path = pipeline.write_chunk_match_list(
                    chunk_plan,
                    chunk_dir=chunk_dir,
                    bridge_target_name_sets=[{"A.jpg", "B.jpg"}, {"C.jpg", "D.jpg"}],
                )

            pair_lines = set(pair_list_path.read_text().splitlines())
            self.assertIn("A.jpg B.jpg", pair_lines)
            self.assertIn("C.jpg D.jpg", pair_lines)
            self.assertTrue(
                {"A.jpg C.jpg", "A.jpg D.jpg", "B.jpg C.jpg", "B.jpg D.jpg"}.intersection(pair_lines)
            )
            self.assertTrue(
                {"A.jpg E.jpg", "B.jpg E.jpg", "C.jpg E.jpg", "D.jpg E.jpg"}.intersection(pair_lines)
            )

    def test_run_chunk_matchers_uses_matches_importer_for_bridge_chunks_under_footprint_graph(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_CHUNK_PLANNER": "footprint_graph_v1"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.colmap_capabilities["supports_matches_importer"] = True
            chunk_plan = run_colmap_sfm.ChunkPlan(
                index=1,
                core_names=["A.jpg", "B.jpg"],
                image_names=["A.jpg", "B.jpg"],
                overlap_names=[],
            )
            chunk_dir = root / "chunk"
            chunk_dir.mkdir(parents=True, exist_ok=True)

            with mock.patch.object(pipeline, "run_matches_importer") as importer_mock, mock.patch.object(
                pipeline, "run_exhaustive_matcher"
            ) as exhaustive_mock:
                pipeline.run_chunk_matchers(
                    chunk_plan,
                    chunk_database_path=root / "chunk.db",
                    chunk_dir=chunk_dir,
                    stage_prefix="chunk_01_02_merge_bridge",
                    bridge_target_name_sets=[{"A.jpg"}, {"B.jpg"}],
                )

            importer_mock.assert_called_once()
            exhaustive_mock.assert_not_called()

    def test_run_chunk_pipeline_triggers_boundary_recovery_for_weak_chunk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.enable_sequential_matcher = True
            pipeline.exif_records = {
                "IMG_01.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_02.jpg": {"local_x_m": 1.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_03.jpg": {"local_x_m": 2.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_04.jpg": {"local_x_m": 3.0, "local_y_m": 0.0, "heading_deg": 0.0},
            }
            chunk = run_colmap_sfm.ChunkPlan(
                index=0,
                core_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                image_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                overlap_names=["IMG_03.jpg", "IMG_04.jpg"],
            )
            initial_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_mapper_initial",
                text_dir=root,
                cameras_registered=1,
                images_registered=2,
                points_3d=1000,
                binary_dir=root,
                image_count=4,
            )
            recovered_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_mapper_recovery",
                text_dir=root,
                cameras_registered=1,
                images_registered=4,
                points_3d=1400,
                binary_dir=root,
                image_count=4,
            )

            with mock.patch.object(
                pipeline,
                "prepare_chunk_database",
                return_value=root / "chunk.db",
            ), mock.patch.object(pipeline, "run_spatial_matcher") as spatial_mock, mock.patch.object(
                pipeline, "run_sequential_matcher"
            ) as sequential_mock, mock.patch.object(
                pipeline,
                "run_mapper",
                side_effect=[initial_model, recovered_model],
            ) as mapper_mock:
                pipeline.timings["chunk_00_mapper_initial_seconds"] = 10.0
                pipeline.timings["chunk_00_mapper_recovery_seconds"] = 8.0
                best_model = pipeline.run_chunk_pipeline(chunk)

            self.assertEqual(best_model.images_registered, 4)
            self.assertTrue(pipeline.boundary_recovery_triggered)
            self.assertEqual(spatial_mock.call_count, 2)
            self.assertEqual(sequential_mock.call_count, 2)
            self.assertEqual(mapper_mock.call_count, 2)

    def test_run_chunk_pipeline_skips_boundary_recovery_when_core_images_are_registered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.enable_sequential_matcher = True
            pipeline.exif_records = {
                "IMG_01.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_02.jpg": {"local_x_m": 1.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_03.jpg": {"local_x_m": 2.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_04.jpg": {"local_x_m": 3.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_05.jpg": {"local_x_m": 4.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_06.jpg": {"local_x_m": 5.0, "local_y_m": 0.0, "heading_deg": 0.0},
            }
            chunk = run_colmap_sfm.ChunkPlan(
                index=0,
                core_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                image_names=[
                    "IMG_01.jpg",
                    "IMG_02.jpg",
                    "IMG_03.jpg",
                    "IMG_04.jpg",
                    "IMG_05.jpg",
                    "IMG_06.jpg",
                ],
                overlap_names=["IMG_05.jpg", "IMG_06.jpg"],
            )
            (root / "images.txt").write_text(
                "\n".join(
                    [
                        "1 1 0 0 0 0 0 0 1 IMG_01.jpg",
                        "0 0 -1",
                        "2 1 0 0 0 0 0 0 1 IMG_02.jpg",
                        "0 0 -1",
                        "3 1 0 0 0 0 0 0 1 IMG_03.jpg",
                        "0 0 -1",
                        "4 1 0 0 0 0 0 0 1 IMG_04.jpg",
                        "0 0 -1",
                    ]
                ),
                encoding="utf-8",
            )
            initial_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_mapper_initial",
                text_dir=root,
                cameras_registered=1,
                images_registered=4,
                points_3d=1200,
                binary_dir=root,
                image_count=6,
            )

            with mock.patch.object(
                pipeline,
                "prepare_chunk_database",
                return_value=root / "chunk.db",
            ), mock.patch.object(pipeline, "run_spatial_matcher") as spatial_mock, mock.patch.object(
                pipeline, "run_sequential_matcher"
            ), mock.patch.object(
                pipeline,
                "run_vocab_matching",
            ) as vocab_mock, mock.patch.object(
                pipeline,
                "run_mapper",
                return_value=initial_model,
            ) as mapper_mock:
                pipeline.timings["chunk_00_mapper_initial_seconds"] = 10.0
                best_model = pipeline.run_chunk_pipeline(chunk)

            self.assertEqual(best_model.images_registered, 4)
            self.assertFalse(pipeline.boundary_recovery_triggered)
            self.assertEqual(spatial_mock.call_count, 1)
            self.assertEqual(vocab_mock.call_count, 0)
            self.assertEqual(mapper_mock.call_count, 1)

    def test_run_chunk_pipeline_skips_boundary_recovery_when_core_ratio_meets_relaxed_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.enable_sequential_matcher = True
            pipeline.chunk_min_core_registered_ratio = 0.75
            pipeline.exif_records = {
                "IMG_01.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_02.jpg": {"local_x_m": 1.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_03.jpg": {"local_x_m": 2.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_04.jpg": {"local_x_m": 3.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_05.jpg": {"local_x_m": 4.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_06.jpg": {"local_x_m": 5.0, "local_y_m": 0.0, "heading_deg": 0.0},
            }
            chunk = run_colmap_sfm.ChunkPlan(
                index=0,
                core_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                image_names=[
                    "IMG_01.jpg",
                    "IMG_02.jpg",
                    "IMG_03.jpg",
                    "IMG_04.jpg",
                    "IMG_05.jpg",
                    "IMG_06.jpg",
                ],
                overlap_names=["IMG_05.jpg", "IMG_06.jpg"],
            )
            (root / "images.txt").write_text(
                "\n".join(
                    [
                        "1 1 0 0 0 0 0 0 1 IMG_01.jpg",
                        "0 0 -1",
                        "2 1 0 0 0 0 0 0 1 IMG_02.jpg",
                        "0 0 -1",
                        "3 1 0 0 0 0 0 0 1 IMG_03.jpg",
                        "0 0 -1",
                    ]
                ),
                encoding="utf-8",
            )
            initial_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_mapper_initial",
                text_dir=root,
                cameras_registered=1,
                images_registered=3,
                points_3d=900,
                binary_dir=root,
                image_count=6,
            )

            with mock.patch.object(
                pipeline,
                "prepare_chunk_database",
                return_value=root / "chunk.db",
            ), mock.patch.object(pipeline, "run_spatial_matcher") as spatial_mock, mock.patch.object(
                pipeline, "run_sequential_matcher"
            ), mock.patch.object(
                pipeline,
                "run_vocab_matching",
            ) as vocab_mock, mock.patch.object(
                pipeline,
                "run_mapper",
                return_value=initial_model,
            ) as mapper_mock:
                pipeline.timings["chunk_00_mapper_initial_seconds"] = 10.0
                best_model = pipeline.run_chunk_pipeline(chunk)

            self.assertEqual(best_model.images_registered, 3)
            self.assertFalse(pipeline.boundary_recovery_triggered)
            self.assertEqual(spatial_mock.call_count, 1)
            self.assertEqual(vocab_mock.call_count, 0)
            self.assertEqual(mapper_mock.call_count, 1)

    def test_run_chunk_pipeline_fails_fast_when_prior_retry_stays_below_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.enable_sequential_matcher = True
            pipeline.exif_records = {
                "IMG_01.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_02.jpg": {"local_x_m": 1.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_03.jpg": {"local_x_m": 2.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_04.jpg": {"local_x_m": 3.0, "local_y_m": 0.0, "heading_deg": 0.0},
            }
            chunk = run_colmap_sfm.ChunkPlan(
                index=0,
                core_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                image_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                overlap_names=["IMG_03.jpg", "IMG_04.jpg"],
            )
            initial_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_mapper_initial",
                text_dir=root,
                cameras_registered=1,
                images_registered=2,
                points_3d=1000,
                binary_dir=root,
                image_count=4,
            )
            recovered_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_mapper_recovery",
                text_dir=root,
                cameras_registered=1,
                images_registered=2,
                points_3d=1100,
                binary_dir=root,
                image_count=4,
            )

            with mock.patch.object(
                pipeline,
                "prepare_chunk_database",
                return_value=root / "chunk.db",
            ), mock.patch.object(pipeline, "run_spatial_matcher"), mock.patch.object(
                pipeline, "run_sequential_matcher"
            ), mock.patch.object(
                pipeline,
                "run_mapper",
                side_effect=[initial_model, recovered_model],
            ) as mapper_mock:
                pipeline.timings["chunk_00_mapper_initial_seconds"] = 10.0
                pipeline.timings["chunk_00_mapper_recovery_seconds"] = 6.0
                with self.assertRaises(RuntimeError):
                    pipeline.run_chunk_pipeline(chunk)

            self.assertTrue(pipeline.boundary_recovery_triggered)
            self.assertEqual(mapper_mock.call_count, 2)
            self.assertEqual(pipeline.failed_chunk_index, 0)
            self.assertEqual(pipeline.failure_stage, "chunk_00_recovery_failed")

    def test_run_chunk_pipeline_returns_partial_bridge_result_for_connector_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.enable_sequential_matcher = True
            pipeline.exif_records = {
                "IMG_01.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_02.jpg": {"local_x_m": 1.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_03.jpg": {"local_x_m": 2.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_04.jpg": {"local_x_m": 3.0, "local_y_m": 0.0, "heading_deg": 0.0},
            }
            chunk = run_colmap_sfm.ChunkPlan(
                index=0,
                core_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                image_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                overlap_names=["IMG_03.jpg", "IMG_04.jpg"],
            )
            initial_dir = root / "initial_text"
            initial_dir.mkdir()
            (initial_dir / "images.txt").write_text(
                "\n".join(
                    [
                        "1 1 0 0 0 0 0 0 1 IMG_01.jpg",
                        "0 0 -1",
                        "2 1 0 0 0 0 0 0 1 IMG_02.jpg",
                        "0 0 -1",
                    ]
                ),
                encoding="utf-8",
            )
            recovered_dir = root / "recovered_text"
            recovered_dir.mkdir()
            (recovered_dir / "images.txt").write_text(
                "\n".join(
                    [
                        "1 1 0 0 0 0 0 0 1 IMG_02.jpg",
                        "0 0 -1",
                        "2 1 0 0 0 0 0 0 1 IMG_03.jpg",
                        "0 0 -1",
                    ]
                ),
                encoding="utf-8",
            )
            initial_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_mapper_initial",
                text_dir=initial_dir,
                cameras_registered=1,
                images_registered=2,
                points_3d=1000,
                binary_dir=root / "initial_bin",
                image_count=4,
            )
            recovered_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_mapper_recovery",
                text_dir=recovered_dir,
                cameras_registered=1,
                images_registered=2,
                points_3d=1100,
                binary_dir=root / "recovered_bin",
                image_count=4,
            )

            with mock.patch.object(
                pipeline,
                "prepare_chunk_database",
                return_value=root / "chunk.db",
            ), mock.patch.object(pipeline, "run_spatial_matcher"), mock.patch.object(
                pipeline, "run_sequential_matcher"
            ), mock.patch.object(
                pipeline,
                "run_mapper",
                side_effect=[initial_model, recovered_model],
            ) as mapper_mock:
                pipeline.timings["chunk_00_mapper_initial_seconds"] = 10.0
                pipeline.timings["chunk_00_mapper_recovery_seconds"] = 6.0
                best_model = pipeline.run_chunk_pipeline(
                    chunk,
                    allow_partial_result=True,
                    bridge_target_name_sets=[{"IMG_02.jpg"}, {"IMG_03.jpg"}],
                )

            self.assertIs(best_model, recovered_model)
            self.assertEqual(mapper_mock.call_count, 2)
            self.assertTrue(pipeline.boundary_recovery_triggered)
            self.assertEqual(pipeline.failure_stage, "")
            self.assertEqual(pipeline.failure_reason_detail, "")
            self.assertIsNone(pipeline.failed_chunk_index)
            self.assertTrue(pipeline.chunk_run_metrics[-1]["partial_result_accepted"])

    def test_run_chunk_pipeline_accepts_partial_leaf_result_in_seam_only_mode(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {
                "COLMAP_CHUNK_PLANNER": "footprint_graph_v1",
                "COLMAP_PARENT_MERGE_MODE": "seam_only_v1",
            },
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.exif_records = {
                "IMG_01.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_02.jpg": {"local_x_m": 1.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_03.jpg": {"local_x_m": 2.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_04.jpg": {"local_x_m": 3.0, "local_y_m": 0.0, "heading_deg": 0.0},
            }
            chunk = run_colmap_sfm.ChunkPlan(
                index=0,
                core_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                image_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                overlap_names=[],
            )
            recovered_dir = root / "recovered_text"
            recovered_dir.mkdir()
            (recovered_dir / "images.txt").write_text(
                "\n".join(
                    [
                        "1 1 0 0 0 0 0 0 1 IMG_01.jpg",
                        "0 0 -1",
                        "2 1 0 0 0 0 0 0 1 IMG_02.jpg",
                        "0 0 -1",
                    ]
                ),
                encoding="utf-8",
            )
            initial_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_mapper_initial",
                text_dir=root / "initial_text",
                cameras_registered=1,
                images_registered=1,
                points_3d=1000,
                binary_dir=root / "initial_bin",
                image_count=4,
            )
            recovered_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_mapper_recovery",
                text_dir=recovered_dir,
                cameras_registered=1,
                images_registered=2,
                points_3d=1100,
                binary_dir=root / "recovered_bin",
                image_count=4,
            )

            with mock.patch.object(
                pipeline,
                "prepare_chunk_database",
                return_value=root / "chunk.db",
            ), mock.patch.object(pipeline, "run_chunk_matchers"), mock.patch.object(
                pipeline, "run_chunk_recovery_matchers"
            ), mock.patch.object(
                pipeline,
                "run_mapper",
                side_effect=[initial_model, recovered_model],
            ):
                pipeline.timings["chunk_00_mapper_initial_seconds"] = 10.0
                pipeline.timings["chunk_00_mapper_recovery_seconds"] = 6.0
                best_model = pipeline.run_chunk_pipeline(chunk)

            self.assertIs(best_model, recovered_model)
            self.assertEqual(pipeline.chunk_recovery_mode, "seam_only_leaf_partial")
            self.assertTrue(pipeline.chunk_run_metrics[-1]["partial_result_accepted"])
            self.assertEqual(
                pipeline.chunk_run_metrics[-1]["partial_result_reason"],
                "seam_only_leaf_seed",
            )

    def test_run_chunk_pipeline_accepts_good_enough_initial_leaf_in_seam_only_mode(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {
                "COLMAP_CHUNK_PLANNER": "footprint_graph_v1",
                "COLMAP_PARENT_MERGE_MODE": "seam_only_v1",
                "COLMAP_SEAM_ONLY_LEAF_MIN_REGISTERED_RATIO": "0.70",
                "COLMAP_SEAM_ONLY_LEAF_MIN_CORE_RATIO": "0.70",
            },
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.exif_records = {
                "IMG_01.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_02.jpg": {"local_x_m": 1.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_03.jpg": {"local_x_m": 2.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_04.jpg": {"local_x_m": 3.0, "local_y_m": 0.0, "heading_deg": 0.0},
            }
            chunk = run_colmap_sfm.ChunkPlan(
                index=0,
                core_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                image_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                overlap_names=[],
            )
            initial_dir = root / "initial_text"
            initial_dir.mkdir()
            (initial_dir / "images.txt").write_text(
                "\n".join(
                    [
                        "1 1 0 0 0 0 0 0 1 IMG_01.jpg",
                        "0 0 -1",
                        "2 1 0 0 0 0 0 0 1 IMG_02.jpg",
                        "0 0 -1",
                        "3 1 0 0 0 0 0 0 1 IMG_03.jpg",
                        "0 0 -1",
                    ]
                ),
                encoding="utf-8",
            )
            initial_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_mapper_initial",
                text_dir=initial_dir,
                cameras_registered=1,
                images_registered=3,
                points_3d=1000,
                binary_dir=root / "initial_bin",
                image_count=4,
            )

            with mock.patch.object(
                pipeline,
                "prepare_chunk_database",
                return_value=root / "chunk.db",
            ), mock.patch.object(pipeline, "run_chunk_matchers"), mock.patch.object(
                pipeline, "run_chunk_recovery_matchers"
            ), mock.patch.object(
                pipeline,
                "run_mapper",
                return_value=initial_model,
            ) as mapper_mock:
                pipeline.timings["chunk_00_mapper_initial_seconds"] = 10.0
                best_model = pipeline.run_chunk_pipeline(chunk)

            self.assertIs(best_model, initial_model)
            self.assertEqual(mapper_mock.call_count, 1)
            self.assertEqual(pipeline.chunk_recovery_mode, "seam_only_leaf_initial")
            self.assertTrue(pipeline.chunk_run_metrics[-1]["partial_result_accepted"])
            self.assertEqual(
                pipeline.chunk_run_metrics[-1]["partial_result_reason"],
                "seam_only_initial_seed",
            )

    def test_run_mapper_salvages_partial_sparse_model_after_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            sparse_root = root / "sparse"
            candidate_dir = sparse_root / "0"
            candidate_dir.mkdir(parents=True, exist_ok=True)
            partial_model = run_colmap_sfm.ModelSummary(
                stage="chunk_01_02_merge_bridge_mapper_initial",
                text_dir=root / "text",
                cameras_registered=1,
                images_registered=5,
                points_3d=1500,
                binary_dir=candidate_dir,
                image_count=10,
            )

            with mock.patch.object(
                run_colmap_sfm,
                "stream_command",
                side_effect=RuntimeError("chunk_01_02_merge_bridge_mapper_initial timed out after 2700s"),
            ), mock.patch.object(
                pipeline,
                "summarize_model",
                return_value=partial_model,
            ):
                result = pipeline.run_mapper(
                    stage="chunk_01_02_merge_bridge_mapper_initial",
                    sparse_root=sparse_root,
                    image_count=10,
                    allow_partial_timeout_result=True,
                )

            self.assertIs(result, partial_model)
            self.assertTrue(result.partial_result)
            self.assertTrue(result.timed_out)
            self.assertEqual(pipeline.failure_stage, "")
            self.assertFalse(pipeline.timed_out)

    def test_run_mapper_uses_extended_timeout_for_bridge_stage(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {
                "COLMAP_CHUNK_MAPPER_TIMEOUT_SECONDS": "2700",
                "COLMAP_BRIDGE_MAPPER_TIMEOUT_SECONDS": "3600",
            },
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            sparse_root = root / "sparse"
            candidate_dir = sparse_root / "0"
            candidate_dir.mkdir(parents=True, exist_ok=True)
            captured_timeout_seconds: list[float | None] = []

            def fake_stream_command(command, *, stage, env=None, timeout_seconds=None, heartbeat_seconds=None):
                captured_timeout_seconds.append(timeout_seconds)

            with mock.patch.object(
                run_colmap_sfm,
                "stream_command",
                side_effect=fake_stream_command,
            ), mock.patch.object(
                pipeline,
                "summarize_model",
                return_value=run_colmap_sfm.ModelSummary(
                    stage="chunk_01_02_merge_bridge_mapper_initial",
                    text_dir=root / "text",
                    cameras_registered=1,
                    images_registered=5,
                    points_3d=1500,
                    binary_dir=candidate_dir,
                    image_count=10,
                ),
            ):
                pipeline.run_mapper(
                    stage="chunk_01_02_merge_bridge_mapper_initial",
                    sparse_root=sparse_root,
                    image_count=10,
                )

        self.assertEqual(captured_timeout_seconds, [3600.0])

    def test_run_chunk_pipeline_returns_timed_out_initial_bridge_result_without_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.enable_sequential_matcher = True
            pipeline.exif_records = {
                "IMG_01.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_02.jpg": {"local_x_m": 1.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_03.jpg": {"local_x_m": 2.0, "local_y_m": 0.0, "heading_deg": 0.0},
                "IMG_04.jpg": {"local_x_m": 3.0, "local_y_m": 0.0, "heading_deg": 0.0},
            }
            chunk = run_colmap_sfm.ChunkPlan(
                index=0,
                core_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                image_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                overlap_names=["IMG_03.jpg", "IMG_04.jpg"],
            )
            initial_dir = root / "initial_text"
            initial_dir.mkdir()
            (initial_dir / "images.txt").write_text(
                "\n".join(
                    [
                        "1 1 0 0 0 0 0 0 1 IMG_02.jpg",
                        "0 0 -1",
                        "2 1 0 0 0 0 0 0 1 IMG_03.jpg",
                        "0 0 -1",
                    ]
                ),
                encoding="utf-8",
            )
            initial_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_mapper_initial",
                text_dir=initial_dir,
                cameras_registered=1,
                images_registered=2,
                points_3d=1000,
                binary_dir=root / "initial_bin",
                image_count=4,
                partial_result=True,
                timed_out=True,
            )

            with mock.patch.object(
                pipeline,
                "prepare_chunk_database",
                return_value=root / "chunk.db",
            ), mock.patch.object(pipeline, "run_spatial_matcher"), mock.patch.object(
                pipeline, "run_sequential_matcher"
            ), mock.patch.object(
                pipeline,
                "run_mapper",
                return_value=initial_model,
            ) as mapper_mock:
                pipeline.timings["chunk_00_mapper_initial_seconds"] = 10.0
                best_model = pipeline.run_chunk_pipeline(
                    chunk,
                    allow_partial_result=True,
                    bridge_target_name_sets=[{"IMG_02.jpg"}, {"IMG_03.jpg"}],
                )

            self.assertIs(best_model, initial_model)
            self.assertEqual(mapper_mock.call_count, 1)
            self.assertFalse(pipeline.boundary_recovery_triggered)
            self.assertEqual(pipeline.chunk_run_metrics[-1]["partial_result_stage"], "initial")
            self.assertTrue(pipeline.chunk_run_metrics[-1]["partial_result_timed_out"])

    def test_prepare_chunk_database_prunes_global_features_without_reextracting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.database_path = root / "database.db"
            chunk = run_colmap_sfm.ChunkPlan(
                index=0,
                core_names=["IMG_01.jpg", "IMG_02.jpg"],
                image_names=["IMG_01.jpg", "IMG_02.jpg"],
                overlap_names=[],
            )

            with sqlite3.connect(pipeline.database_path) as connection:
                connection.execute(
                    "CREATE TABLE cameras(camera_id INTEGER PRIMARY KEY, model INTEGER, width INTEGER, height INTEGER, params BLOB, prior_focal_length INTEGER)"
                )
                connection.execute("INSERT INTO cameras(camera_id, model, width, height, params, prior_focal_length) VALUES (1, 0, 100, 100, X'00', 1)")
                connection.execute("INSERT INTO cameras(camera_id, model, width, height, params, prior_focal_length) VALUES (2, 0, 100, 100, X'00', 1)")
                connection.execute("CREATE TABLE images(image_id INTEGER PRIMARY KEY, name TEXT, camera_id INTEGER)")
                connection.execute("CREATE TABLE keypoints(image_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB)")
                connection.execute("CREATE TABLE descriptors(image_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB)")
                connection.execute(
                    "CREATE TABLE pose_priors(image_id INTEGER PRIMARY KEY, position BLOB, coordinate_system INTEGER, position_covariance BLOB)"
                )
                connection.execute("CREATE TABLE matches(pair_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB)")
                connection.execute(
                    "CREATE TABLE two_view_geometries(pair_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB, config INTEGER, F BLOB, E BLOB, H BLOB, qvec BLOB, tvec BLOB)"
                )
                connection.executemany(
                    "INSERT INTO images(image_id, name, camera_id) VALUES (?, ?, ?)",
                    [(1, "IMG_01.jpg", 1), (2, "IMG_02.jpg", 1), (3, "IMG_03.jpg", 2)],
                )
                connection.executemany(
                    "INSERT INTO keypoints(image_id, rows, cols, data) VALUES (?, 1, 1, X'00')",
                    [(1,), (2,), (3,)],
                )
                connection.executemany(
                    "INSERT INTO descriptors(image_id, rows, cols, data) VALUES (?, 1, 1, X'00')",
                    [(1,), (2,), (3,)],
                )
                connection.executemany(
                    "INSERT INTO pose_priors(image_id, position, coordinate_system, position_covariance) VALUES (?, X'00', 0, X'00')",
                    [(1,), (2,), (3,)],
                )
                connection.execute("INSERT INTO matches(pair_id, rows, cols, data) VALUES (1, 1, 1, X'00')")
                connection.execute(
                    "INSERT INTO two_view_geometries(pair_id, rows, cols, data, config, F, E, H, qvec, tvec) VALUES (1, 1, 1, X'00', 1, X'00', X'00', X'00', X'00', X'00')"
                )
                connection.commit()

            chunk_db = pipeline.prepare_chunk_database(chunk)

            with sqlite3.connect(chunk_db) as connection:
                image_names = [row[0] for row in connection.execute("SELECT name FROM images ORDER BY image_id").fetchall()]
                camera_ids = [row[0] for row in connection.execute("SELECT camera_id FROM cameras ORDER BY camera_id").fetchall()]
                keypoint_ids = [row[0] for row in connection.execute("SELECT image_id FROM keypoints ORDER BY image_id").fetchall()]
                descriptor_ids = [row[0] for row in connection.execute("SELECT image_id FROM descriptors ORDER BY image_id").fetchall()]
                pose_prior_ids = [row[0] for row in connection.execute("SELECT image_id FROM pose_priors ORDER BY image_id").fetchall()]
                matches_count = connection.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
                geometry_count = connection.execute("SELECT COUNT(*) FROM two_view_geometries").fetchone()[0]

            self.assertEqual(image_names, ["IMG_01.jpg", "IMG_02.jpg"])
            self.assertEqual(camera_ids, [1])
            self.assertEqual(keypoint_ids, [1, 2])
            self.assertEqual(descriptor_ids, [1, 2])
            self.assertEqual(pose_prior_ids, [1, 2])
            self.assertEqual(matches_count, 0)
            self.assertEqual(geometry_count, 0)

    def test_prepare_chunk_database_rebuilds_clean_copy_when_retry_dir_has_stale_sqlite_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.database_path = root / "database.db"
            chunk = run_colmap_sfm.ChunkPlan(
                index=1,
                core_names=["IMG_01.jpg", "IMG_02.jpg"],
                image_names=["IMG_01.jpg", "IMG_02.jpg"],
                overlap_names=[],
            )

            with sqlite3.connect(pipeline.database_path) as connection:
                connection.execute(
                    "CREATE TABLE cameras(camera_id INTEGER PRIMARY KEY, model INTEGER, width INTEGER, height INTEGER, params BLOB, prior_focal_length INTEGER)"
                )
                connection.execute("INSERT INTO cameras(camera_id, model, width, height, params, prior_focal_length) VALUES (1, 0, 100, 100, X'00', 1)")
                connection.execute("INSERT INTO cameras(camera_id, model, width, height, params, prior_focal_length) VALUES (2, 0, 100, 100, X'00', 1)")
                connection.execute("CREATE TABLE images(image_id INTEGER PRIMARY KEY, name TEXT, camera_id INTEGER)")
                connection.execute("CREATE TABLE keypoints(image_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB)")
                connection.execute("CREATE TABLE descriptors(image_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB)")
                connection.execute(
                    "CREATE TABLE pose_priors(image_id INTEGER PRIMARY KEY, position BLOB, coordinate_system INTEGER, position_covariance BLOB)"
                )
                connection.execute("CREATE TABLE matches(pair_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB)")
                connection.execute(
                    "CREATE TABLE two_view_geometries(pair_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB, config INTEGER, F BLOB, E BLOB, H BLOB, qvec BLOB, tvec BLOB)"
                )
                connection.executemany(
                    "INSERT INTO images(image_id, name, camera_id) VALUES (?, ?, ?)",
                    [(1, "IMG_01.jpg", 1), (2, "IMG_02.jpg", 1), (3, "IMG_03.jpg", 2)],
                )
                connection.executemany(
                    "INSERT INTO keypoints(image_id, rows, cols, data) VALUES (?, 1, 1, X'00')",
                    [(1,), (2,), (3,)],
                )
                connection.executemany(
                    "INSERT INTO descriptors(image_id, rows, cols, data) VALUES (?, 1, 1, X'00')",
                    [(1,), (2,), (3,)],
                )
                connection.executemany(
                    "INSERT INTO pose_priors(image_id, position, coordinate_system, position_covariance) VALUES (?, X'00', 0, X'00')",
                    [(1,), (2,), (3,)],
                )
                connection.commit()

            first_chunk_db = pipeline.prepare_chunk_database(chunk, dir_name="chunk_retry")
            Path(f"{first_chunk_db}-wal").write_bytes(b"stale wal")
            Path(f"{first_chunk_db}-shm").write_bytes(b"stale shm")

            second_chunk_db = pipeline.prepare_chunk_database(chunk, dir_name="chunk_retry")

            with sqlite3.connect(second_chunk_db) as connection:
                image_names = [row[0] for row in connection.execute("SELECT name FROM images ORDER BY image_id").fetchall()]
                keypoint_ids = [row[0] for row in connection.execute("SELECT image_id FROM keypoints ORDER BY image_id").fetchall()]

            self.assertEqual(image_names, ["IMG_01.jpg", "IMG_02.jpg"])
            self.assertEqual(keypoint_ids, [1, 2])
            self.assertFalse(Path(f"{second_chunk_db}-wal").exists())
            self.assertFalse(Path(f"{second_chunk_db}-shm").exists())

    def test_clone_database_for_chunk_handles_wal_source_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.database_path = root / "database.db"

            with sqlite3.connect(pipeline.database_path) as connection:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("CREATE TABLE images(image_id INTEGER PRIMARY KEY, name TEXT, camera_id INTEGER)")
                connection.execute("INSERT INTO images(image_id, name, camera_id) VALUES (1, 'IMG_01.jpg', 1)")
                connection.commit()

            destination_path = root / "chunk_00" / "database.db"
            pipeline.clone_database_for_chunk(destination_path)

            with sqlite3.connect(pipeline.database_path) as source_connection:
                source_rows = source_connection.execute("SELECT image_id, name FROM images").fetchall()
            with sqlite3.connect(destination_path) as destination_connection:
                journal_mode = destination_connection.execute("PRAGMA journal_mode").fetchone()[0]
                destination_rows = destination_connection.execute("SELECT image_id, name FROM images").fetchall()

            self.assertEqual(str(journal_mode).lower(), "delete")
            self.assertEqual(source_rows, [(1, "IMG_01.jpg")])
            self.assertEqual(destination_rows, [(1, "IMG_01.jpg")])
            self.assertFalse(Path(f"{destination_path}-wal").exists())
            self.assertFalse(Path(f"{destination_path}-shm").exists())

    def test_prepare_chunk_database_retries_transient_sqlite_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.database_path = root / "database.db"
            pipeline.sqlite_lock_retry_count = 1
            pipeline.sqlite_lock_retry_sleep_seconds = 0.0
            chunk = run_colmap_sfm.ChunkPlan(
                index=0,
                core_names=["IMG_01.jpg", "IMG_02.jpg"],
                image_names=["IMG_01.jpg", "IMG_02.jpg"],
                overlap_names=[],
            )

            with sqlite3.connect(pipeline.database_path) as connection:
                connection.execute(
                    "CREATE TABLE cameras(camera_id INTEGER PRIMARY KEY, model INTEGER, width INTEGER, height INTEGER, params BLOB, prior_focal_length INTEGER)"
                )
                connection.execute("INSERT INTO cameras(camera_id, model, width, height, params, prior_focal_length) VALUES (1, 0, 100, 100, X'00', 1)")
                connection.execute("INSERT INTO cameras(camera_id, model, width, height, params, prior_focal_length) VALUES (2, 0, 100, 100, X'00', 1)")
                connection.execute("CREATE TABLE images(image_id INTEGER PRIMARY KEY, name TEXT, camera_id INTEGER)")
                connection.execute("CREATE TABLE keypoints(image_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB)")
                connection.execute("CREATE TABLE descriptors(image_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB)")
                connection.execute(
                    "CREATE TABLE pose_priors(image_id INTEGER PRIMARY KEY, position BLOB, coordinate_system INTEGER, position_covariance BLOB)"
                )
                connection.execute("CREATE TABLE matches(pair_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB)")
                connection.execute(
                    "CREATE TABLE two_view_geometries(pair_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB, config INTEGER, F BLOB, E BLOB, H BLOB, qvec BLOB, tvec BLOB)"
                )
                connection.executemany(
                    "INSERT INTO images(image_id, name, camera_id) VALUES (?, ?, ?)",
                    [(1, "IMG_01.jpg", 1), (2, "IMG_02.jpg", 1), (3, "IMG_03.jpg", 2)],
                )
                connection.executemany(
                    "INSERT INTO keypoints(image_id, rows, cols, data) VALUES (?, 1, 1, X'00')",
                    [(1,), (2,), (3,)],
                )
                connection.executemany(
                    "INSERT INTO descriptors(image_id, rows, cols, data) VALUES (?, 1, 1, X'00')",
                    [(1,), (2,), (3,)],
                )
                connection.executemany(
                    "INSERT INTO pose_priors(image_id, position, coordinate_system, position_covariance) VALUES (?, X'00', 0, X'00')",
                    [(1,), (2,), (3,)],
                )
                connection.commit()

            real_prune = pipeline.prune_chunk_database
            prune_attempts = 0

            def flaky_prune(*args, **kwargs):
                nonlocal prune_attempts
                prune_attempts += 1
                if prune_attempts == 1:
                    raise sqlite3.OperationalError("database is locked")
                return real_prune(*args, **kwargs)

            with mock.patch.object(pipeline, "prune_chunk_database", side_effect=flaky_prune):
                chunk_db = pipeline.prepare_chunk_database(chunk)

            with sqlite3.connect(chunk_db) as connection:
                image_names = [row[0] for row in connection.execute("SELECT name FROM images ORDER BY image_id").fetchall()]

            self.assertEqual(prune_attempts, 2)
            self.assertEqual(image_names, ["IMG_01.jpg", "IMG_02.jpg"])

    def test_prepare_chunk_database_checks_pose_prior_schema_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.database_path = root / "database.db"
            chunk = run_colmap_sfm.ChunkPlan(
                index=0,
                core_names=["IMG_01.jpg", "IMG_02.jpg"],
                image_names=["IMG_01.jpg", "IMG_02.jpg"],
                overlap_names=[],
            )

            with sqlite3.connect(pipeline.database_path) as connection:
                connection.execute(
                    "CREATE TABLE cameras(camera_id INTEGER PRIMARY KEY, model INTEGER, width INTEGER, height INTEGER, params BLOB, prior_focal_length INTEGER)"
                )
                connection.execute("INSERT INTO cameras(camera_id, model, width, height, params, prior_focal_length) VALUES (1, 0, 100, 100, X'00', 1)")
                connection.execute("INSERT INTO cameras(camera_id, model, width, height, params, prior_focal_length) VALUES (2, 0, 100, 100, X'00', 1)")
                connection.execute("CREATE TABLE images(image_id INTEGER PRIMARY KEY, name TEXT, camera_id INTEGER)")
                connection.execute("CREATE TABLE keypoints(image_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB)")
                connection.execute("CREATE TABLE descriptors(image_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB)")
                connection.execute(
                    "CREATE TABLE pose_priors(image_id INTEGER PRIMARY KEY, position BLOB, coordinate_system INTEGER, position_covariance BLOB)"
                )
                connection.execute("CREATE TABLE matches(pair_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB)")
                connection.execute(
                    "CREATE TABLE two_view_geometries(pair_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB, config INTEGER, F BLOB, E BLOB, H BLOB, qvec BLOB, tvec BLOB)"
                )
                connection.executemany(
                    "INSERT INTO images(image_id, name, camera_id) VALUES (?, ?, ?)",
                    [(1, "IMG_01.jpg", 1), (2, "IMG_02.jpg", 1), (3, "IMG_03.jpg", 2)],
                )
                connection.executemany(
                    "INSERT INTO keypoints(image_id, rows, cols, data) VALUES (?, 1, 1, X'00')",
                    [(1,), (2,), (3,)],
                )
                connection.executemany(
                    "INSERT INTO descriptors(image_id, rows, cols, data) VALUES (?, 1, 1, X'00')",
                    [(1,), (2,), (3,)],
                )
                connection.executemany(
                    "INSERT INTO pose_priors(image_id, position, coordinate_system, position_covariance) VALUES (?, X'00', 0, X'00')",
                    [(1,), (2,), (3,)],
                )
                connection.commit()

            expected_chunk_db = (pipeline.work_dir / "chunk_00" / "database.db").resolve()
            real_connect = run_colmap_sfm.sqlite3.connect
            write_started = False

            class RecordingConnection:
                def __init__(self, connection, database):
                    self._connection = connection
                    self._database = database

                def __enter__(self):
                    self._connection.__enter__()
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return self._connection.__exit__(exc_type, exc, tb)

                def execute(self, sql, parameters=()):
                    nonlocal write_started
                    normalized_sql = sql.lstrip().upper()
                    if self._database == expected_chunk_db and normalized_sql.startswith("DELETE "):
                        write_started = True
                    return self._connection.execute(sql, parameters)

                def backup(self, target, *args, **kwargs):
                    if isinstance(target, RecordingConnection):
                        target = target._connection
                    return self._connection.backup(target, *args, **kwargs)

                def __getattr__(self, name):
                    return getattr(self._connection, name)

            def recording_connect(database, *args, **kwargs):
                connection = real_connect(database, *args, **kwargs)
                if isinstance(database, (str, os.PathLike)) and not str(database).startswith("file:"):
                    database = Path(database).resolve()
                return RecordingConnection(connection, database)

            original_supports = pipeline.supports_pose_prior_image_backfill

            def wrapped_supports(*, database_path=None):
                self.assertFalse(write_started)
                return original_supports(database_path=database_path)

            with mock.patch.object(run_colmap_sfm.sqlite3, "connect", side_effect=recording_connect):
                with mock.patch.object(
                    pipeline,
                    "supports_pose_prior_image_backfill",
                    side_effect=wrapped_supports,
                ) as supports_mock:
                    chunk_db = pipeline.prepare_chunk_database(chunk)

            self.assertTrue(chunk_db.exists())
            self.assertGreaterEqual(supports_mock.call_count, 1)
            self.assertTrue(write_started)

    def test_merge_chunk_models_creates_output_directory_before_merger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.parent_merge_mode = "legacy_rerun"
            first_model_dir = root / "chunk_00" / "sparse_initial" / "0"
            second_model_dir = root / "chunk_01" / "sparse_initial" / "0"
            first_text_dir = root / "text_00"
            second_text_dir = root / "text_01"
            merged_text_dir = root / "merged_text"
            first_model_dir.mkdir(parents=True, exist_ok=True)
            second_model_dir.mkdir(parents=True, exist_ok=True)
            first_text_dir.mkdir(parents=True, exist_ok=True)
            second_text_dir.mkdir(parents=True, exist_ok=True)
            merged_text_dir.mkdir(parents=True, exist_ok=True)
            (first_text_dir / "images.txt").write_text(
                "1 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n2 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (second_text_dir / "images.txt").write_text(
                "3 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n4 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (merged_text_dir / "images.txt").write_text(
                "5 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n6 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n7 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            chunk_models = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_00_mapper_initial",
                    text_dir=first_text_dir,
                    cameras_registered=1,
                    images_registered=10,
                    points_3d=1000,
                    binary_dir=first_model_dir,
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_01_mapper_initial",
                    text_dir=second_text_dir,
                    cameras_registered=1,
                    images_registered=10,
                    points_3d=1000,
                    binary_dir=second_model_dir,
                ),
            ]
            output_path = pipeline.work_dir / "merged_chunk_model_01_attempt_01"
            merged_candidate = run_colmap_sfm.ModelSummary(
                stage="chunk_model_merger_01_output_attempt_01",
                text_dir=merged_text_dir,
                cameras_registered=1,
                images_registered=3,
                points_3d=1500,
                binary_dir=output_path,
            )
            adjusted_model = run_colmap_sfm.ModelSummary(
                stage="chunk_bundle_adjuster",
                text_dir=merged_text_dir,
                cameras_registered=1,
                images_registered=20,
                points_3d=2000,
                binary_dir=output_path,
            )

            with mock.patch.object(run_colmap_sfm, "stream_command") as stream_command_mock, mock.patch.object(
                pipeline,
                "summarize_model",
                return_value=merged_candidate,
            ), mock.patch.object(
                pipeline,
                "run_bundle_adjuster",
                return_value=adjusted_model,
            ):
                result = pipeline.merge_chunk_models(chunk_models)

            self.assertTrue(output_path.is_dir())
            merger_command = stream_command_mock.call_args.args[0]
            self.assertIn("model_merger", merger_command)
            self.assertIn(str(output_path), merger_command)
            self.assertEqual(result.images_registered, 20)
            self.assertEqual(pipeline.chunk_merge_proof["pre_merge_unique_registered_images"], 3)
            self.assertEqual(pipeline.chunk_merge_proof["final_merged_registered_images"], 3)
            self.assertEqual(pipeline.chunk_merge_proof["pre_merge_retention_ratio"], 1.0)

    def test_merge_chunk_models_retries_with_swapped_inputs_after_partial_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.parent_merge_mode = "legacy_rerun"
            first_model_dir = root / "chunk_00" / "sparse_initial" / "0"
            second_model_dir = root / "chunk_01" / "sparse_initial" / "0"
            first_text_dir = root / "text_00"
            second_text_dir = root / "text_01"
            failed_merge_text_dir = root / "failed_merge_text"
            swapped_merge_text_dir = root / "swapped_merge_text"
            first_model_dir.mkdir(parents=True, exist_ok=True)
            second_model_dir.mkdir(parents=True, exist_ok=True)
            first_text_dir.mkdir(parents=True, exist_ok=True)
            second_text_dir.mkdir(parents=True, exist_ok=True)
            failed_merge_text_dir.mkdir(parents=True, exist_ok=True)
            swapped_merge_text_dir.mkdir(parents=True, exist_ok=True)
            (first_text_dir / "images.txt").write_text(
                "1 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n2 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (second_text_dir / "images.txt").write_text(
                "3 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n4 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (failed_merge_text_dir / "images.txt").write_text(
                "5 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n6 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (swapped_merge_text_dir / "images.txt").write_text(
                "7 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n8 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n9 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            chunk_models = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_00_mapper_initial",
                    text_dir=first_text_dir,
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=1000,
                    binary_dir=first_model_dir,
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_01_mapper_initial",
                    text_dir=second_text_dir,
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=1000,
                    binary_dir=second_model_dir,
                ),
            ]
            final_output_path = pipeline.work_dir / "merged_chunk_model_01_attempt_02"
            merged_model = run_colmap_sfm.ModelSummary(
                stage="chunk_bundle_adjuster",
                text_dir=swapped_merge_text_dir,
                cameras_registered=1,
                images_registered=3,
                points_3d=2000,
                binary_dir=final_output_path,
            )

            summarize_side_effects = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_model_merger_01_output_attempt_01",
                    text_dir=failed_merge_text_dir,
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=1100,
                    binary_dir=pipeline.work_dir / "merged_chunk_model_01_attempt_01",
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_model_merger_01_output_attempt_02",
                    text_dir=swapped_merge_text_dir,
                    cameras_registered=1,
                    images_registered=3,
                    points_3d=1500,
                    binary_dir=final_output_path,
                ),
            ]

            with mock.patch.object(run_colmap_sfm, "stream_command") as stream_command_mock, mock.patch.object(
                pipeline,
                "summarize_model",
                side_effect=summarize_side_effects,
            ), mock.patch.object(
                pipeline,
                "run_bundle_adjuster",
                return_value=merged_model,
            ):
                result = pipeline.merge_chunk_models(chunk_models)

            merger_commands = [call.args[0] for call in stream_command_mock.call_args_list]
            self.assertEqual(len(merger_commands), 2)
            self.assertEqual(merger_commands[0][3], str(first_model_dir))
            self.assertEqual(merger_commands[0][5], str(second_model_dir))
            self.assertEqual(merger_commands[1][3], str(second_model_dir))
            self.assertEqual(merger_commands[1][5], str(first_model_dir))
            self.assertEqual(result.images_registered, 3)
            self.assertEqual(pipeline.chunk_merge_proof["pre_merge_unique_registered_images"], 3)
            self.assertEqual(pipeline.chunk_merge_proof["final_merged_registered_images"], 3)

    def test_merge_chunk_models_prefers_highest_overlap_pair_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.parent_merge_mode = "legacy_rerun"
            first_model_dir = root / "chunk_00" / "sparse_initial" / "0"
            second_model_dir = root / "chunk_01" / "sparse_initial" / "0"
            third_model_dir = root / "chunk_02" / "sparse_initial" / "0"
            first_text_dir = root / "text_00"
            second_text_dir = root / "text_01"
            third_text_dir = root / "text_02"
            merged_first_text_dir = root / "merged_first_text"
            merged_final_text_dir = root / "merged_final_text"
            for directory in (
                first_model_dir,
                second_model_dir,
                third_model_dir,
                first_text_dir,
                second_text_dir,
                third_text_dir,
                merged_first_text_dir,
                merged_final_text_dir,
            ):
                directory.mkdir(parents=True, exist_ok=True)
            (first_text_dir / "images.txt").write_text(
                "1 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n2 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (second_text_dir / "images.txt").write_text(
                "3 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n4 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (third_text_dir / "images.txt").write_text(
                "5 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n6 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n7 1 0 0 0 0 0 0 1 IMG_04.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (merged_first_text_dir / "images.txt").write_text(
                "8 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n9 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n10 1 0 0 0 0 0 0 1 IMG_04.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (merged_final_text_dir / "images.txt").write_text(
                "11 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n12 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n13 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n14 1 0 0 0 0 0 0 1 IMG_04.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            chunk_models = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_00_mapper_initial",
                    text_dir=first_text_dir,
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=1000,
                    binary_dir=first_model_dir,
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_01_mapper_initial",
                    text_dir=second_text_dir,
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=1000,
                    binary_dir=second_model_dir,
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_02_mapper_initial",
                    text_dir=third_text_dir,
                    cameras_registered=1,
                    images_registered=3,
                    points_3d=1200,
                    binary_dir=third_model_dir,
                ),
            ]
            summarize_side_effects = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_model_merger_01_output_attempt_01",
                    text_dir=merged_first_text_dir,
                    cameras_registered=1,
                    images_registered=3,
                    points_3d=1600,
                    binary_dir=pipeline.work_dir / "merged_chunk_model_01_attempt_01",
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_model_merger_02_output_attempt_01",
                    text_dir=merged_final_text_dir,
                    cameras_registered=1,
                    images_registered=4,
                    points_3d=2000,
                    binary_dir=pipeline.work_dir / "merged_chunk_model_02_attempt_01",
                ),
            ]
            adjusted_model = run_colmap_sfm.ModelSummary(
                stage="chunk_bundle_adjuster",
                text_dir=merged_final_text_dir,
                cameras_registered=1,
                images_registered=4,
                points_3d=2200,
                binary_dir=pipeline.work_dir / "merged_chunk_model_02_attempt_01",
            )

            with mock.patch.object(run_colmap_sfm, "stream_command") as stream_command_mock, mock.patch.object(
                pipeline,
                "summarize_model",
                side_effect=summarize_side_effects,
            ), mock.patch.object(
                pipeline,
                "run_bundle_adjuster",
                return_value=adjusted_model,
            ):
                result = pipeline.merge_chunk_models(chunk_models)

            merger_commands = [call.args[0] for call in stream_command_mock.call_args_list]
            self.assertEqual(merger_commands[0][3], str(second_model_dir))
            self.assertEqual(merger_commands[0][5], str(third_model_dir))
            self.assertEqual(result.images_registered, 4)
            self.assertEqual(pipeline.chunk_merge_proof["pre_merge_unique_registered_images"], 4)
            self.assertEqual(pipeline.chunk_merge_proof["final_merged_registered_images"], 4)

    def test_merge_chunk_models_prefers_contiguous_chunk_pair_when_balanced_tree_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.parent_merge_mode = "legacy_rerun"
            pipeline.hierarchy_mode = "balanced_tree_v1"
            first_model_dir = root / "chunk_00" / "sparse_initial" / "0"
            second_model_dir = root / "chunk_01" / "sparse_initial" / "0"
            third_model_dir = root / "chunk_02" / "sparse_initial" / "0"
            first_text_dir = root / "text_00"
            second_text_dir = root / "text_01"
            third_text_dir = root / "text_02"
            merged_first_text_dir = root / "merged_first_text"
            merged_final_text_dir = root / "merged_final_text"
            for directory in (
                first_model_dir,
                second_model_dir,
                third_model_dir,
                first_text_dir,
                second_text_dir,
                third_text_dir,
                merged_first_text_dir,
                merged_final_text_dir,
            ):
                directory.mkdir(parents=True, exist_ok=True)
            (first_text_dir / "images.txt").write_text(
                "1 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n2 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n3 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (second_text_dir / "images.txt").write_text(
                "4 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n5 1 0 0 0 0 0 0 1 IMG_04.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (third_text_dir / "images.txt").write_text(
                "6 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n7 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n8 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n9 1 0 0 0 0 0 0 1 IMG_05.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (merged_first_text_dir / "images.txt").write_text(
                "10 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n11 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n12 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n13 1 0 0 0 0 0 0 1 IMG_04.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (merged_final_text_dir / "images.txt").write_text(
                "14 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n15 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n16 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n17 1 0 0 0 0 0 0 1 IMG_04.jpg\n0 0 -1\n18 1 0 0 0 0 0 0 1 IMG_05.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            chunk_models = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_00_mapper_initial",
                    text_dir=first_text_dir,
                    cameras_registered=1,
                    images_registered=3,
                    points_3d=1000,
                    binary_dir=first_model_dir,
                    source_chunk_indexes=[0],
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_01_mapper_initial",
                    text_dir=second_text_dir,
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=1000,
                    binary_dir=second_model_dir,
                    source_chunk_indexes=[1],
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_02_mapper_initial",
                    text_dir=third_text_dir,
                    cameras_registered=1,
                    images_registered=4,
                    points_3d=1200,
                    binary_dir=third_model_dir,
                    source_chunk_indexes=[2],
                ),
            ]
            summarize_side_effects = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_model_merger_01_output_attempt_01",
                    text_dir=merged_first_text_dir,
                    cameras_registered=1,
                    images_registered=4,
                    points_3d=1600,
                    binary_dir=pipeline.work_dir / "merged_chunk_model_01_attempt_01",
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_model_merger_02_output_attempt_01",
                    text_dir=merged_final_text_dir,
                    cameras_registered=1,
                    images_registered=5,
                    points_3d=2200,
                    binary_dir=pipeline.work_dir / "merged_chunk_model_02_attempt_01",
                ),
            ]
            adjusted_model = run_colmap_sfm.ModelSummary(
                stage="chunk_bundle_adjuster",
                text_dir=merged_final_text_dir,
                cameras_registered=1,
                images_registered=5,
                points_3d=2400,
                binary_dir=pipeline.work_dir / "merged_chunk_model_02_attempt_01",
            )

            with mock.patch.object(run_colmap_sfm, "stream_command") as stream_command_mock, mock.patch.object(
                pipeline,
                "summarize_model",
                side_effect=summarize_side_effects,
            ), mock.patch.object(
                pipeline,
                "run_bundle_adjuster",
                return_value=adjusted_model,
            ):
                result = pipeline.merge_chunk_models(chunk_models)

            merger_commands = [call.args[0] for call in stream_command_mock.call_args_list]
            self.assertEqual(merger_commands[0][3], str(first_model_dir))
            self.assertEqual(merger_commands[0][5], str(second_model_dir))
            self.assertEqual(result.images_registered, 5)

    def test_merge_chunk_models_accepts_connector_merge_with_partial_bridge_retention(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.parent_merge_mode = "legacy_rerun"
            first_model_dir = root / "chunk_00" / "sparse_initial" / "0"
            second_model_dir = root / "chunk_01" / "sparse_initial" / "0"
            bridge_model_dir = root / "bridge" / "sparse_initial" / "0"
            first_text_dir = root / "text_00"
            second_text_dir = root / "text_01"
            bridge_text_dir = root / "bridge_text"
            merged_first_text_dir = root / "merged_bridge_text"
            merged_final_text_dir = root / "merged_final_text"
            for directory in (
                first_model_dir,
                second_model_dir,
                bridge_model_dir,
                first_text_dir,
                second_text_dir,
                bridge_text_dir,
                merged_first_text_dir,
                merged_final_text_dir,
            ):
                directory.mkdir(parents=True, exist_ok=True)
            (first_text_dir / "images.txt").write_text(
                "1 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n2 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n3 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n4 1 0 0 0 0 0 0 1 IMG_04.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (second_text_dir / "images.txt").write_text(
                "5 1 0 0 0 0 0 0 1 IMG_05.jpg\n0 0 -1\n6 1 0 0 0 0 0 0 1 IMG_06.jpg\n0 0 -1\n7 1 0 0 0 0 0 0 1 IMG_07.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (bridge_text_dir / "images.txt").write_text(
                "8 1 0 0 0 0 0 0 1 IMG_04.jpg\n0 0 -1\n9 1 0 0 0 0 0 0 1 IMG_05.jpg\n0 0 -1\n10 1 0 0 0 0 0 0 1 IMG_06.jpg\n0 0 -1\n11 1 0 0 0 0 0 0 1 IMG_08.jpg\n0 0 -1\n12 1 0 0 0 0 0 0 1 IMG_09.jpg\n0 0 -1\n13 1 0 0 0 0 0 0 1 IMG_10.jpg\n0 0 -1\n14 1 0 0 0 0 0 0 1 IMG_11.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (merged_first_text_dir / "images.txt").write_text(
                "15 1 0 0 0 0 0 0 1 IMG_04.jpg\n0 0 -1\n16 1 0 0 0 0 0 0 1 IMG_05.jpg\n0 0 -1\n17 1 0 0 0 0 0 0 1 IMG_06.jpg\n0 0 -1\n18 1 0 0 0 0 0 0 1 IMG_07.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (merged_final_text_dir / "images.txt").write_text(
                "19 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n20 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n21 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n22 1 0 0 0 0 0 0 1 IMG_04.jpg\n0 0 -1\n23 1 0 0 0 0 0 0 1 IMG_05.jpg\n0 0 -1\n24 1 0 0 0 0 0 0 1 IMG_06.jpg\n0 0 -1\n25 1 0 0 0 0 0 0 1 IMG_07.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            chunk_models = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_00_mapper_initial",
                    text_dir=first_text_dir,
                    cameras_registered=1,
                    images_registered=4,
                    points_3d=1000,
                    binary_dir=first_model_dir,
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_01_mapper_initial",
                    text_dir=second_text_dir,
                    cameras_registered=1,
                    images_registered=3,
                    points_3d=1000,
                    binary_dir=second_model_dir,
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_00_01_merge_bridge_mapper_initial",
                    text_dir=bridge_text_dir,
                    cameras_registered=1,
                    images_registered=7,
                    points_3d=1200,
                    binary_dir=bridge_model_dir,
                ),
            ]
            summarize_side_effects = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_model_merger_01_output_attempt_01",
                    text_dir=merged_first_text_dir,
                    cameras_registered=1,
                    images_registered=4,
                    points_3d=1600,
                    binary_dir=pipeline.work_dir / "merged_chunk_model_01_attempt_01",
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_model_merger_02_output_attempt_01",
                    text_dir=merged_final_text_dir,
                    cameras_registered=1,
                    images_registered=7,
                    points_3d=2200,
                    binary_dir=pipeline.work_dir / "merged_chunk_model_02_attempt_01",
                ),
            ]
            adjusted_model = run_colmap_sfm.ModelSummary(
                stage="chunk_bundle_adjuster",
                text_dir=merged_final_text_dir,
                cameras_registered=1,
                images_registered=7,
                points_3d=2400,
                binary_dir=pipeline.work_dir / "merged_chunk_model_02_attempt_01",
            )

            with mock.patch.object(run_colmap_sfm, "stream_command") as stream_command_mock, mock.patch.object(
                pipeline,
                "summarize_model",
                side_effect=summarize_side_effects,
            ), mock.patch.object(
                pipeline,
                "run_bundle_adjuster",
                return_value=adjusted_model,
            ):
                result = pipeline.merge_chunk_models(chunk_models)

            merger_commands = [call.args[0] for call in stream_command_mock.call_args_list]
            self.assertEqual(merger_commands[0][3], str(second_model_dir))
            self.assertEqual(merger_commands[0][5], str(bridge_model_dir))
            self.assertEqual(result.images_registered, 7)
            self.assertEqual(pipeline.chunk_merge_proof["pre_merge_unique_registered_images"], 11)
            self.assertEqual(pipeline.chunk_merge_proof["final_merged_registered_images"], 7)
            self.assertEqual(pipeline.chunk_merge_proof["pre_merge_retention_ratio"], 0.6364)

    def test_merge_chunk_models_runs_parent_seam_refinement_in_default_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.capture_ordered_names = ["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"]
            pipeline.exif_records = {name: {} for name in pipeline.capture_ordered_names}
            first_model_dir = root / "chunk_00" / "sparse_initial" / "0"
            second_model_dir = root / "chunk_01" / "sparse_initial" / "0"
            first_text_dir = root / "text_00"
            second_text_dir = root / "text_01"
            merged_text_dir = root / "merged_text"
            refined_text_dir = root / "refined_text"
            for directory in (
                first_model_dir,
                second_model_dir,
                first_text_dir,
                second_text_dir,
                merged_text_dir,
                refined_text_dir,
            ):
                directory.mkdir(parents=True, exist_ok=True)
            (first_text_dir / "images.txt").write_text(
                "1 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n2 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (second_text_dir / "images.txt").write_text(
                "3 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n4 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (merged_text_dir / "images.txt").write_text(
                "5 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n6 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n7 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (refined_text_dir / "images.txt").write_text(
                "8 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n9 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n10 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            chunk_models = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_00_mapper_initial",
                    text_dir=first_text_dir,
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=1000,
                    binary_dir=first_model_dir,
                    image_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_04.jpg"],
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_01_mapper_initial",
                    text_dir=second_text_dir,
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=1000,
                    binary_dir=second_model_dir,
                    image_names=["IMG_02.jpg", "IMG_03.jpg"],
                ),
            ]
            merged_candidate = run_colmap_sfm.ModelSummary(
                stage="chunk_model_merger_01_output_attempt_01",
                text_dir=merged_text_dir,
                cameras_registered=1,
                images_registered=3,
                points_3d=1500,
                binary_dir=pipeline.work_dir / "merged_chunk_model_01_attempt_01",
            )
            seam_model = run_colmap_sfm.ModelSummary(
                stage="chunk_model_seam_01_point_triangulator_01",
                text_dir=refined_text_dir,
                cameras_registered=1,
                images_registered=3,
                points_3d=1700,
                binary_dir=pipeline.work_dir / "merged_chunk_model_01_seam",
                image_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg"],
            )
            adjusted_model = run_colmap_sfm.ModelSummary(
                stage="chunk_bundle_adjuster",
                text_dir=refined_text_dir,
                cameras_registered=1,
                images_registered=3,
                points_3d=1800,
                binary_dir=pipeline.work_dir / "merged_chunk_model_01_seam",
                image_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg"],
            )

            with mock.patch.object(run_colmap_sfm, "stream_command"), mock.patch.object(
                pipeline,
                "summarize_model",
                return_value=merged_candidate,
            ), mock.patch.object(
                pipeline,
                "run_parent_seam_registration",
                return_value=seam_model,
            ) as seam_mock, mock.patch.object(
                pipeline,
                "run_bundle_adjuster",
                return_value=adjusted_model,
            ):
                result = pipeline.merge_chunk_models(chunk_models)

            self.assertEqual(result.images_registered, 3)
            self.assertEqual(seam_mock.call_count, 1)
            self.assertFalse(seam_mock.call_args.kwargs["run_final_bundle_adjustment"])
            self.assertEqual(seam_mock.call_args.kwargs["stage_prefix"], "chunk_model_seam_01")

    def test_merge_chunk_models_skips_parent_seam_when_raw_merge_retains_all_source_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.capture_ordered_names = ["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg"]
            pipeline.exif_records = {name: {} for name in pipeline.capture_ordered_names}
            first_model_dir = root / "chunk_00" / "sparse_initial" / "0"
            second_model_dir = root / "chunk_01" / "sparse_initial" / "0"
            first_text_dir = root / "text_00"
            second_text_dir = root / "text_01"
            merged_text_dir = root / "merged_text"
            refined_text_dir = root / "refined_text"
            for directory in (
                first_model_dir,
                second_model_dir,
                first_text_dir,
                second_text_dir,
                merged_text_dir,
                refined_text_dir,
            ):
                directory.mkdir(parents=True, exist_ok=True)
            (first_text_dir / "images.txt").write_text(
                "1 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n2 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (second_text_dir / "images.txt").write_text(
                "3 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n4 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (merged_text_dir / "images.txt").write_text(
                "5 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n6 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n7 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            chunk_models = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_00_mapper_initial",
                    text_dir=first_text_dir,
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=1000,
                    binary_dir=first_model_dir,
                    image_names=["IMG_01.jpg", "IMG_02.jpg"],
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_01_mapper_initial",
                    text_dir=second_text_dir,
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=1000,
                    binary_dir=second_model_dir,
                    image_names=["IMG_02.jpg", "IMG_03.jpg"],
                ),
            ]
            merged_candidate = run_colmap_sfm.ModelSummary(
                stage="chunk_model_merger_01_output_attempt_01",
                text_dir=merged_text_dir,
                cameras_registered=1,
                images_registered=3,
                points_3d=1500,
                binary_dir=pipeline.work_dir / "merged_chunk_model_01_attempt_01",
            )
            adjusted_model = run_colmap_sfm.ModelSummary(
                stage="chunk_bundle_adjuster",
                text_dir=refined_text_dir,
                cameras_registered=1,
                images_registered=3,
                points_3d=1800,
                binary_dir=pipeline.work_dir / "merged_chunk_model_01_attempt_01",
                image_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg"],
            )

            with mock.patch.object(run_colmap_sfm, "stream_command"), mock.patch.object(
                pipeline,
                "summarize_model",
                return_value=merged_candidate,
            ), mock.patch.object(
                pipeline,
                "run_parent_seam_registration",
            ) as seam_mock, mock.patch.object(
                pipeline,
                "run_bundle_adjuster",
                return_value=adjusted_model,
            ):
                result = pipeline.merge_chunk_models(chunk_models)

            self.assertEqual(result.images_registered, 3)
            seam_mock.assert_not_called()

    def test_merge_chunk_models_retries_parent_seam_with_expanded_frontier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.capture_ordered_names = ["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"]
            pipeline.exif_records = {
                name: {"local_x_m": float(index), "local_y_m": 0.0}
                for index, name in enumerate(pipeline.capture_ordered_names)
            }
            pipeline.seam_frontier_max_images = 1
            pipeline.seam_frontier_retry_max_images = 3
            pipeline.parent_seam_retry_pair_cap = 9
            first_model_dir = root / "chunk_00" / "sparse_initial" / "0"
            second_model_dir = root / "chunk_01" / "sparse_initial" / "0"
            first_text_dir = root / "text_00"
            second_text_dir = root / "text_01"
            merged_text_dir = root / "merged_text"
            refined_text_dir = root / "refined_text"
            for directory in (
                first_model_dir,
                second_model_dir,
                first_text_dir,
                second_text_dir,
                merged_text_dir,
                refined_text_dir,
            ):
                directory.mkdir(parents=True, exist_ok=True)
            (first_text_dir / "images.txt").write_text(
                "1 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n2 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (second_text_dir / "images.txt").write_text(
                "3 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n4 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (merged_text_dir / "images.txt").write_text(
                "5 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n6 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n7 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (refined_text_dir / "images.txt").write_text(
                "8 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n9 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n10 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n11 1 0 0 0 0 0 0 1 IMG_04.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            chunk_models = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_00_mapper_initial",
                    text_dir=first_text_dir,
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=1000,
                    binary_dir=first_model_dir,
                    image_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_04.jpg", "IMG_05.jpg"],
                    source_chunk_indexes=[0],
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_01_mapper_initial",
                    text_dir=second_text_dir,
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=1000,
                    binary_dir=second_model_dir,
                    image_names=["IMG_02.jpg", "IMG_03.jpg"],
                    source_chunk_indexes=[1],
                ),
            ]
            merged_candidate = run_colmap_sfm.ModelSummary(
                stage="chunk_model_merger_01_output_attempt_01",
                text_dir=merged_text_dir,
                cameras_registered=1,
                images_registered=3,
                points_3d=1500,
                binary_dir=pipeline.work_dir / "merged_chunk_model_01_attempt_01",
            )
            seam_model = run_colmap_sfm.ModelSummary(
                stage="chunk_model_seam_01_retry_point_triangulator_01",
                text_dir=refined_text_dir,
                cameras_registered=1,
                images_registered=4,
                points_3d=1800,
                binary_dir=pipeline.work_dir / "merged_chunk_model_01_seam_retry",
                image_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
            )
            adjusted_model = run_colmap_sfm.ModelSummary(
                stage="chunk_bundle_adjuster",
                text_dir=refined_text_dir,
                cameras_registered=1,
                images_registered=4,
                points_3d=1900,
                binary_dir=pipeline.work_dir / "merged_chunk_model_01_seam_retry",
                image_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
            )

            with mock.patch.object(run_colmap_sfm, "stream_command"), mock.patch.object(
                pipeline,
                "summarize_model",
                return_value=merged_candidate,
            ), mock.patch.object(
                pipeline,
                "run_parent_seam_registration",
                side_effect=[RuntimeError("seed seam failed"), seam_model],
            ) as seam_mock, mock.patch.object(
                pipeline,
                "run_bundle_adjuster",
                return_value=adjusted_model,
            ):
                result = pipeline.merge_chunk_models(chunk_models)

            self.assertEqual(result.images_registered, 4)
            self.assertEqual(seam_mock.call_count, 2)
            self.assertEqual(seam_mock.call_args_list[1].kwargs["stage_prefix"], "chunk_model_seam_01_retry")
            self.assertEqual(seam_mock.call_args_list[1].kwargs["frontier_pair_cap"], 9)
            self.assertEqual(
                seam_mock.call_args_list[1].kwargs["chunk_plan"].image_names,
                ["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
            )

    def test_merge_chunk_models_skips_final_bundle_adjustment_above_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.parent_merge_mode = "legacy_rerun"
            pipeline.top_level_ba_mode = "below_threshold"
            pipeline.top_level_ba_image_threshold = 2
            first_model_dir = root / "chunk_00" / "sparse_initial" / "0"
            second_model_dir = root / "chunk_01" / "sparse_initial" / "0"
            first_text_dir = root / "text_00"
            second_text_dir = root / "text_01"
            merged_text_dir = root / "merged_text"
            for directory in (
                first_model_dir,
                second_model_dir,
                first_text_dir,
                second_text_dir,
                merged_text_dir,
            ):
                directory.mkdir(parents=True, exist_ok=True)
            (first_text_dir / "images.txt").write_text(
                "1 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n2 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (second_text_dir / "images.txt").write_text(
                "3 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n4 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            (merged_text_dir / "images.txt").write_text(
                "5 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 -1\n6 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 -1\n7 1 0 0 0 0 0 0 1 IMG_03.jpg\n0 0 -1\n",
                encoding="utf-8",
            )
            chunk_models = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_00_mapper_initial",
                    text_dir=first_text_dir,
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=1000,
                    binary_dir=first_model_dir,
                    image_names=["IMG_01.jpg", "IMG_02.jpg"],
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_01_mapper_initial",
                    text_dir=second_text_dir,
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=1000,
                    binary_dir=second_model_dir,
                    image_names=["IMG_02.jpg", "IMG_03.jpg"],
                ),
            ]
            merged_candidate = run_colmap_sfm.ModelSummary(
                stage="chunk_model_merger_01_output_attempt_01",
                text_dir=merged_text_dir,
                cameras_registered=1,
                images_registered=3,
                points_3d=1500,
                binary_dir=pipeline.work_dir / "merged_chunk_model_01_attempt_01",
                image_names=["IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg"],
            )

            with mock.patch.object(run_colmap_sfm, "stream_command"), mock.patch.object(
                pipeline,
                "summarize_model",
                return_value=merged_candidate,
            ), mock.patch.object(
                pipeline,
                "run_bundle_adjuster",
            ) as ba_mock:
                result = pipeline.merge_chunk_models(chunk_models)

            ba_mock.assert_not_called()
            self.assertEqual(result.images_registered, 3)
            self.assertFalse(pipeline.chunk_merge_proof["top_level_ba_ran"])
            self.assertEqual(pipeline.chunk_merge_proof["top_level_ba_reason"], "above_threshold:2")

    def test_parent_seam_helpers_omit_fix_existing_images_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.images_dir.mkdir(parents=True, exist_ok=True)
            input_model_dir = root / "seed_model"
            input_model_dir.mkdir(parents=True, exist_ok=True)
            summarized = run_colmap_sfm.ModelSummary(
                stage="seed",
                text_dir=root / "text",
                cameras_registered=1,
                images_registered=1,
                points_3d=1,
                binary_dir=root / "binary",
            )

            with mock.patch.object(run_colmap_sfm, "stream_command") as stream_command_mock, mock.patch.object(
                pipeline,
                "summarize_model",
                return_value=summarized,
            ):
                pipeline.run_image_registrator(
                    database_path=root / "db.db",
                    input_path=input_model_dir,
                    stage="parent_seam_image_registrator_01",
                    image_count=10,
                )
                pipeline.run_point_triangulator(
                    database_path=root / "db.db",
                    input_path=input_model_dir,
                    stage="parent_seam_point_triangulator_01",
                    image_count=10,
                    clear_points=False,
                )

            registrator_command = stream_command_mock.call_args_list[0].args[0]
            triangulator_command = stream_command_mock.call_args_list[1].args[0]
            self.assertIn("image_registrator", registrator_command)
            self.assertIn("point_triangulator", triangulator_command)
            self.assertNotIn("--Mapper.fix_existing_images", registrator_command)
            self.assertNotIn("--Mapper.fix_existing_images", triangulator_command)
            triangulator_clear_points_index = triangulator_command.index("--clear_points")
            self.assertEqual(triangulator_command[triangulator_clear_points_index + 1], "0")

    def test_repair_disconnected_chunk_model_components_reruns_best_bridge_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.chunk_planner = "footprint_graph_v1"
            pipeline.parent_merge_mode = "legacy_rerun"
            pipeline.chunk_bridge_recovery_max_images = 500
            pipeline.capture_ordered_names = [
                "IMG_00.jpg",
                "IMG_01.jpg",
                "IMG_02.jpg",
                "IMG_03.jpg",
                "IMG_04.jpg",
                "IMG_05.jpg",
                "IMG_06.jpg",
                "IMG_07.jpg",
                "IMG_08.jpg",
            ]
            chunk_plans = [
                run_colmap_sfm.ChunkPlan(
                    index=0,
                    core_names=["IMG_00.jpg", "IMG_01.jpg"],
                    image_names=["IMG_00.jpg", "IMG_01.jpg", "IMG_02.jpg"],
                    overlap_names=["IMG_02.jpg"],
                ),
                run_colmap_sfm.ChunkPlan(
                    index=1,
                    core_names=["IMG_02.jpg", "IMG_03.jpg"],
                    image_names=["IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                    overlap_names=["IMG_04.jpg"],
                ),
                run_colmap_sfm.ChunkPlan(
                    index=2,
                    core_names=["IMG_04.jpg", "IMG_05.jpg"],
                    image_names=["IMG_04.jpg", "IMG_05.jpg", "IMG_06.jpg"],
                    overlap_names=["IMG_06.jpg"],
                ),
                run_colmap_sfm.ChunkPlan(
                    index=3,
                    core_names=["IMG_06.jpg", "IMG_07.jpg"],
                    image_names=["IMG_06.jpg", "IMG_07.jpg", "IMG_08.jpg"],
                    overlap_names=[],
                ),
            ]
            chunk_models = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_00_mapper_initial",
                    text_dir=root / "chunk0_text",
                    cameras_registered=1,
                    images_registered=3,
                    points_3d=100,
                    binary_dir=root / "chunk0_bin",
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_01_mapper_initial",
                    text_dir=root / "chunk1_text",
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=100,
                    binary_dir=root / "chunk1_bin",
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_02_mapper_initial",
                    text_dir=root / "chunk2_text",
                    cameras_registered=1,
                    images_registered=3,
                    points_3d=100,
                    binary_dir=root / "chunk2_bin",
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_03_mapper_initial",
                    text_dir=root / "chunk3_text",
                    cameras_registered=1,
                    images_registered=3,
                    points_3d=100,
                    binary_dir=root / "chunk3_bin",
                ),
            ]
            bridge_model = run_colmap_sfm.ModelSummary(
                stage="chunk_01_02_merge_bridge_mapper_initial",
                text_dir=root / "bridge_text",
                cameras_registered=1,
                images_registered=5,
                points_3d=200,
                binary_dir=root / "bridge_bin",
            )
            registered_names_by_stage = {
                "chunk_00_mapper_initial": {"IMG_00.jpg", "IMG_01.jpg", "IMG_02.jpg"},
                "chunk_01_mapper_initial": {"IMG_02.jpg", "IMG_03.jpg"},
                "chunk_02_mapper_initial": {"IMG_04.jpg", "IMG_05.jpg", "IMG_06.jpg"},
                "chunk_03_mapper_initial": {"IMG_05.jpg", "IMG_06.jpg", "IMG_07.jpg"},
                "chunk_01_02_merge_bridge_mapper_initial": {
                    "IMG_02.jpg",
                    "IMG_03.jpg",
                    "IMG_04.jpg",
                    "IMG_05.jpg",
                    "IMG_06.jpg",
                },
            }

            with mock.patch.object(
                pipeline,
                "merged_image_names",
                side_effect=lambda model: registered_names_by_stage[model.stage],
            ), mock.patch.object(
                pipeline,
                "run_chunk_pipeline",
                return_value=bridge_model,
            ) as run_chunk_mock:
                repaired_plans, repaired_models = pipeline.repair_disconnected_chunk_model_components(
                    chunk_plans=chunk_plans,
                    chunk_models=chunk_models,
                )

            bridge_plan = run_chunk_mock.call_args.args[0]
            self.assertEqual(bridge_plan.index, 1)
            self.assertEqual(set(bridge_plan.image_names), {"IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg", "IMG_05.jpg", "IMG_06.jpg"})
            self.assertEqual(run_chunk_mock.call_args.kwargs["stage_prefix"], "chunk_01_02_merge_bridge")
            self.assertTrue(run_chunk_mock.call_args.kwargs["allow_partial_result"])
            self.assertEqual(
                run_chunk_mock.call_args.kwargs["bridge_target_name_sets"],
                [
                    {"IMG_00.jpg", "IMG_01.jpg", "IMG_02.jpg", "IMG_03.jpg"},
                    {"IMG_04.jpg", "IMG_05.jpg", "IMG_06.jpg", "IMG_07.jpg"},
                ],
            )
            self.assertTrue(pipeline.merge_bridge_recovery_triggered)
            self.assertEqual(pipeline.chunk_recovery_mode, "prior_aware_retry_merge_bridge_no_vocab")
            self.assertEqual(len(repaired_plans), 5)
            self.assertEqual([plan.index for plan in repaired_plans], [0, 1, 2, 3, 1])
            self.assertEqual(len(repaired_models), 5)
            self.assertIs(repaired_models[-1], bridge_model)
            self.assertEqual(pipeline.merged_component_count, 1)

    def test_repair_disconnected_chunk_model_components_uses_seam_registration_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.chunk_planner = "footprint_graph_v1"
            pipeline.chunk_bridge_recovery_max_images = 500
            pipeline.capture_ordered_names = [
                "IMG_00.jpg",
                "IMG_01.jpg",
                "IMG_02.jpg",
                "IMG_03.jpg",
                "IMG_04.jpg",
                "IMG_05.jpg",
                "IMG_06.jpg",
                "IMG_07.jpg",
                "IMG_08.jpg",
            ]
            pipeline.exif_records = {name: {} for name in pipeline.capture_ordered_names}
            chunk_plans = [
                run_colmap_sfm.ChunkPlan(
                    index=0,
                    core_names=["IMG_00.jpg", "IMG_01.jpg"],
                    image_names=["IMG_00.jpg", "IMG_01.jpg", "IMG_02.jpg"],
                    overlap_names=["IMG_02.jpg"],
                ),
                run_colmap_sfm.ChunkPlan(
                    index=1,
                    core_names=["IMG_02.jpg", "IMG_03.jpg"],
                    image_names=["IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                    overlap_names=["IMG_04.jpg"],
                ),
                run_colmap_sfm.ChunkPlan(
                    index=2,
                    core_names=["IMG_04.jpg", "IMG_05.jpg"],
                    image_names=["IMG_04.jpg", "IMG_05.jpg", "IMG_06.jpg"],
                    overlap_names=["IMG_06.jpg"],
                ),
                run_colmap_sfm.ChunkPlan(
                    index=3,
                    core_names=["IMG_06.jpg", "IMG_07.jpg"],
                    image_names=["IMG_06.jpg", "IMG_07.jpg", "IMG_08.jpg"],
                    overlap_names=[],
                ),
            ]
            chunk_models = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_00_mapper_initial",
                    text_dir=root / "chunk0_text",
                    cameras_registered=1,
                    images_registered=3,
                    points_3d=100,
                    binary_dir=root / "chunk0_bin",
                    image_names=chunk_plans[0].image_names,
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_01_mapper_initial",
                    text_dir=root / "chunk1_text",
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=100,
                    binary_dir=root / "chunk1_bin",
                    image_names=chunk_plans[1].image_names,
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_02_mapper_initial",
                    text_dir=root / "chunk2_text",
                    cameras_registered=1,
                    images_registered=3,
                    points_3d=100,
                    binary_dir=root / "chunk2_bin",
                    image_names=chunk_plans[2].image_names,
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_03_mapper_initial",
                    text_dir=root / "chunk3_text",
                    cameras_registered=1,
                    images_registered=3,
                    points_3d=100,
                    binary_dir=root / "chunk3_bin",
                    image_names=chunk_plans[3].image_names,
                ),
            ]
            bridge_model = run_colmap_sfm.ModelSummary(
                stage="chunk_01_02_merge_bridge_bundle_adjuster",
                text_dir=root / "bridge_text",
                cameras_registered=1,
                images_registered=5,
                points_3d=200,
                binary_dir=root / "bridge_bin",
                image_names=["IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg", "IMG_05.jpg", "IMG_06.jpg"],
            )
            registered_names_by_stage = {
                "chunk_00_mapper_initial": {"IMG_00.jpg", "IMG_01.jpg", "IMG_02.jpg"},
                "chunk_01_mapper_initial": {"IMG_02.jpg", "IMG_03.jpg"},
                "chunk_02_mapper_initial": {"IMG_04.jpg", "IMG_05.jpg", "IMG_06.jpg"},
                "chunk_03_mapper_initial": {"IMG_05.jpg", "IMG_06.jpg", "IMG_07.jpg"},
                "chunk_01_02_merge_bridge_bundle_adjuster": {
                    "IMG_02.jpg",
                    "IMG_03.jpg",
                    "IMG_04.jpg",
                    "IMG_05.jpg",
                    "IMG_06.jpg",
                },
            }

            with mock.patch.object(
                pipeline,
                "merged_image_names",
                side_effect=lambda model: registered_names_by_stage[model.stage],
            ), mock.patch.object(
                pipeline,
                "run_parent_seam_registration",
                return_value=bridge_model,
            ) as seam_mock, mock.patch.object(
                pipeline,
                "run_chunk_pipeline",
            ) as run_chunk_mock:
                repaired_plans, repaired_models = pipeline.repair_disconnected_chunk_model_components(
                    chunk_plans=chunk_plans,
                    chunk_models=chunk_models,
                )

            self.assertEqual(len(repaired_plans), 5)
            self.assertEqual(len(repaired_models), 5)
            self.assertIs(repaired_models[-1], bridge_model)
            self.assertEqual(seam_mock.call_count, 1)
            self.assertEqual(seam_mock.call_args.kwargs["stage_prefix"], "chunk_01_02_merge_bridge")
            self.assertTrue(seam_mock.call_args.kwargs.get("run_final_bundle_adjustment", True))
            run_chunk_mock.assert_not_called()

    def test_run_spatial_heading_chunked_path_uses_seam_registration_for_adjacent_retry(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {
                "COLMAP_CHUNK_PLANNER": "footprint_graph_v1",
                "COLMAP_PARENT_MERGE_MODE": "seam_only_v1",
            },
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.capture_ordered_names = [
                "IMG_00.jpg",
                "IMG_01.jpg",
                "IMG_02.jpg",
                "IMG_03.jpg",
                "IMG_04.jpg",
            ]
            pipeline.gps_min_registered_ratio = 0.8
            chunk_plan_0 = run_colmap_sfm.ChunkPlan(
                index=0,
                core_names=["IMG_00.jpg", "IMG_01.jpg"],
                image_names=["IMG_00.jpg", "IMG_01.jpg", "IMG_02.jpg"],
                overlap_names=["IMG_02.jpg"],
            )
            chunk_plan_1 = run_colmap_sfm.ChunkPlan(
                index=1,
                core_names=["IMG_02.jpg", "IMG_03.jpg"],
                image_names=["IMG_02.jpg", "IMG_03.jpg", "IMG_04.jpg"],
                overlap_names=["IMG_04.jpg"],
            )
            seed_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_mapper_initial",
                text_dir=root / "chunk0_text",
                cameras_registered=1,
                images_registered=3,
                points_3d=100,
                binary_dir=root / "chunk0_bin",
                image_names=chunk_plan_0.image_names,
            )
            merged_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_01_adjacent_merge_point_triangulator_01",
                text_dir=root / "adjacent_text",
                cameras_registered=1,
                images_registered=4,
                points_3d=120,
                binary_dir=root / "adjacent_bin",
                image_names=chunk_plan_0.image_names + ["IMG_03.jpg"],
            )
            run_chunk_results = iter([seed_model, RuntimeError("chunk 1 remained below threshold")])

            def fake_run_chunk_pipeline(chunk_plan, *args, **kwargs):
                result = next(run_chunk_results)
                if isinstance(result, Exception):
                    pipeline.failure_stage = "chunk_01_recovery_failed"
                    pipeline.failure_reason_detail = str(result)
                    pipeline.failed_chunk_index = chunk_plan.index
                    raise result
                return result

            with mock.patch.object(
                pipeline,
                "build_chunk_plans",
                return_value=[chunk_plan_0, chunk_plan_1],
            ), mock.patch.object(
                pipeline,
                "run_chunk_pipeline",
                side_effect=fake_run_chunk_pipeline,
            ) as run_chunk_mock, mock.patch.object(
                pipeline,
                "cross_chunk_edge_count",
                side_effect=[5, 5],
            ), mock.patch.object(
                pipeline,
                "run_parent_seam_registration",
                return_value=merged_model,
            ) as seam_mock, mock.patch.object(
                pipeline,
                "merged_image_names",
                side_effect=lambda model: {
                    "chunk_00_mapper_initial": {"IMG_00.jpg", "IMG_01.jpg", "IMG_02.jpg"},
                    "chunk_00_01_adjacent_merge_point_triangulator_01": {
                        "IMG_00.jpg",
                        "IMG_01.jpg",
                        "IMG_02.jpg",
                        "IMG_03.jpg",
                    },
                }[model.stage],
            ), mock.patch.object(
                pipeline,
                "repair_disconnected_chunk_model_components",
                return_value=([chunk_plan_0], [merged_model]),
            ) as repair_mock, mock.patch.object(
                pipeline,
                "merge_chunk_models",
                return_value=merged_model,
            ) as merge_mock:
                pipeline.dataset_image_count = 5
                pipeline.run_spatial_heading_chunked_path()

            self.assertEqual(run_chunk_mock.call_count, 2)
            seam_mock.assert_called_once()
            self.assertEqual(seam_mock.call_args.kwargs["stage_prefix"], "chunk_00_01_adjacent_merge")
            self.assertFalse(seam_mock.call_args.kwargs["run_final_bundle_adjustment"])
            repair_mock.assert_called_once()
            merge_mock.assert_called_once()
            self.assertEqual(pipeline.chunk_recovery_mode, "seam_only_adjacent_registration")

    def test_repair_disconnected_chunk_model_components_keeps_auxiliary_bridge_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.chunk_planner = "footprint_graph_v1"
            pipeline.parent_merge_mode = "legacy_rerun"
            pipeline.chunk_bridge_recovery_max_attempts = 1
            pipeline.chunk_bridge_recovery_max_images = 500
            pipeline.capture_ordered_names = [
                "IMG_00.jpg",
                "IMG_01.jpg",
                "IMG_02.jpg",
                "IMG_03.jpg",
                "IMG_04.jpg",
                "IMG_05.jpg",
                "IMG_06.jpg",
            ]
            chunk_plans = [
                run_colmap_sfm.ChunkPlan(
                    index=0,
                    core_names=["IMG_00.jpg", "IMG_01.jpg"],
                    image_names=["IMG_00.jpg", "IMG_01.jpg", "IMG_02.jpg"],
                    overlap_names=[],
                ),
                run_colmap_sfm.ChunkPlan(
                    index=1,
                    core_names=["IMG_03.jpg", "IMG_04.jpg"],
                    image_names=["IMG_03.jpg", "IMG_04.jpg", "IMG_05.jpg"],
                    overlap_names=[],
                ),
                run_colmap_sfm.ChunkPlan(
                    index=2,
                    core_names=["IMG_05.jpg", "IMG_06.jpg"],
                    image_names=["IMG_05.jpg", "IMG_06.jpg"],
                    overlap_names=[],
                ),
            ]
            chunk_models = [
                run_colmap_sfm.ModelSummary(
                    stage="chunk_00_mapper_initial",
                    text_dir=root / "chunk0_text",
                    cameras_registered=1,
                    images_registered=3,
                    points_3d=100,
                    binary_dir=root / "chunk0_bin",
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_01_mapper_initial",
                    text_dir=root / "chunk1_text",
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=100,
                    binary_dir=root / "chunk1_bin",
                ),
                run_colmap_sfm.ModelSummary(
                    stage="chunk_02_mapper_initial",
                    text_dir=root / "chunk2_text",
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=100,
                    binary_dir=root / "chunk2_bin",
                ),
            ]
            bridge_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_01_merge_bridge_mapper_initial",
                text_dir=root / "bridge_text",
                cameras_registered=1,
                images_registered=4,
                points_3d=200,
                binary_dir=root / "bridge_bin",
            )
            registered_names_by_stage = {
                "chunk_00_mapper_initial": {"IMG_00.jpg", "IMG_01.jpg", "IMG_02.jpg"},
                "chunk_01_mapper_initial": {"IMG_03.jpg", "IMG_04.jpg"},
                "chunk_02_mapper_initial": {"IMG_05.jpg", "IMG_06.jpg"},
                "chunk_00_01_merge_bridge_mapper_initial": {
                    "IMG_00.jpg",
                    "IMG_01.jpg",
                    "IMG_02.jpg",
                    "IMG_05.jpg",
                },
            }

            with mock.patch.object(
                pipeline,
                "merged_image_names",
                side_effect=lambda model: registered_names_by_stage[model.stage],
            ), mock.patch.object(
                pipeline,
                "run_chunk_pipeline",
                return_value=bridge_model,
            ):
                repaired_plans, repaired_models = pipeline.repair_disconnected_chunk_model_components(
                    chunk_plans=chunk_plans,
                    chunk_models=chunk_models,
                )

            self.assertEqual(len(repaired_plans), 4)
            self.assertEqual(len(repaired_models), 4)
            self.assertIs(repaired_models[-1], bridge_model)
            self.assertEqual(pipeline.merged_component_count, 2)

    def test_write_filtered_sparse_model_keeps_far_context_and_drops_absurd_outlier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.exif_records = {
                "IMG_01.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "local_z_m": 0.0},
                "IMG_02.jpg": {"local_x_m": 20.0, "local_y_m": 0.0, "local_z_m": 0.0},
            }
            source_dir = root / "source_model"
            filtered_dir = root / "filtered_model"
            source_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / "cameras.txt").write_text("# cameras\n", encoding="utf-8")
            (source_dir / "images.txt").write_text(
                "1 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 1 1 1 2 2 2 3 3 3 4\n"
                "2 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 1 1 1 2 2 2 3 3 3 4\n",
                encoding="utf-8",
            )
            (source_dir / "points3D.txt").write_text(
                "# points\n"
                "1 0 0 0 255 255 255 1.0 1 0 2 0 3 0\n"
                "2 20 0 0 255 255 255 0.8 1 1 2 1\n"
                "3 5 0 0 255 255 255 2.5 1 2 2 2\n"
                "4 100000 0 0 255 255 255 0.1 1 3 2 3\n",
                encoding="utf-8",
            )

            summary = pipeline.write_filtered_sparse_model(
                source_text_dir=source_dir,
                output_dir=filtered_dir,
            )

            filtered_points = (filtered_dir / "points3D.txt").read_text(encoding="utf-8")
            filtered_images = (filtered_dir / "images.txt").read_text(encoding="utf-8")
            self.assertEqual(summary["core_filtered_points_3d"], 1)
            self.assertEqual(summary["far_context_points_3d"], 1)
            self.assertEqual(summary["absurd_outlier_points_removed"], 1)
            self.assertIn("1 0 0 0 255 255 255 1.0", filtered_points)
            self.assertIn("2 20 0 0 255 255 255 0.8", filtered_points)
            self.assertNotIn("3 5 0 0 255 255 255 2.5", filtered_points)
            self.assertNotIn("4 100000 0 0 255 255 255 0.1", filtered_points)
            self.assertIn("0 0 1 1 1 2 2 2 -1 3 3 -1", filtered_images)

    def test_write_filtered_sparse_model_rejects_weak_far_context_without_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.filtered_sparse_far_context_min_baseline_m = 12.0
            pipeline.exif_records = {
                "IMG_01.jpg": {"local_x_m": 0.0, "local_y_m": 0.0, "local_z_m": 0.0},
                "IMG_02.jpg": {"local_x_m": 5.0, "local_y_m": 0.0, "local_z_m": 0.0},
            }
            source_dir = root / "source_model"
            filtered_dir = root / "filtered_model"
            source_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / "cameras.txt").write_text("# cameras\n", encoding="utf-8")
            (source_dir / "images.txt").write_text(
                "1 1 0 0 0 0 0 0 1 IMG_01.jpg\n0 0 1 1\n"
                "2 1 0 0 0 0 0 0 1 IMG_02.jpg\n0 0 1 1\n",
                encoding="utf-8",
            )
            (source_dir / "points3D.txt").write_text(
                "# points\n"
                "1 20 0 0 255 255 255 0.8 1 1 2 1\n",
                encoding="utf-8",
            )

            summary = pipeline.write_filtered_sparse_model(
                source_text_dir=source_dir,
                output_dir=filtered_dir,
            )

            filtered_points = (filtered_dir / "points3D.txt").read_text(encoding="utf-8")
            self.assertEqual(summary["far_context_points_3d"], 0)
            self.assertEqual(summary["weak_far_context_points_rejected"], 1)
            self.assertNotIn("1 20 0 0 255 255 255 0.8", filtered_points)

    def test_extract_images_respects_manifest_selected_subset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir(parents=True, exist_ok=True)
            archive_path = input_dir / "images.zip"
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("IMG_01.jpg", b"one")
                archive.writestr("IMG_02.jpg", b"two")
                archive.writestr("IMG_03.jpg", b"three")
            manifest_path = root / "probe_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "input": "s3://example/dataset.zip",
                        "probe_subsets": {
                            "geometry_mix": {
                                "image_count": 2,
                                "images": ["IMG_01.jpg", "IMG_03.jpg"],
                            }
                        },
                        "ladder_subsets": {},
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.dict(
                os.environ,
                {
                    "COLMAP_INPUT_SUBSET_MANIFEST_URI": str(manifest_path),
                    "COLMAP_INPUT_SUBSET_NAME": "geometry_mix",
                },
                clear=False,
            ):
                pipeline = run_colmap_sfm.ColmapPipeline(input_dir, output_dir)
                pipeline.extract_images()

            self.assertEqual(pipeline.dataset_image_count, 2)
            self.assertEqual(
                sorted(path.name for path in pipeline.images_dir.iterdir()),
                ["IMG_01.jpg", "IMG_03.jpg"],
            )
            self.assertTrue(pipeline.selected_input_images_requested)

    def test_extract_images_respects_s3_manifest_selected_subset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir(parents=True, exist_ok=True)
            archive_path = input_dir / "images.zip"
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("IMG_01.jpg", b"one")
                archive.writestr("IMG_02.jpg", b"two")
                archive.writestr("IMG_03.jpg", b"three")
            manifest_payload = {
                "input": "s3://example/dataset.zip",
                "probe_subsets": {
                    "geometry_mix": {
                        "image_count": 2,
                        "images": ["IMG_02.jpg", "IMG_03.jpg"],
                    }
                },
                "ladder_subsets": {},
            }
            s3_client = mock.Mock()
            s3_client.get_object.return_value = {
                "Body": io.BytesIO(json.dumps(manifest_payload).encode("utf-8"))
            }

            fake_boto3 = mock.Mock()
            fake_boto3.client.return_value = s3_client

            with mock.patch.dict(
                os.environ,
                {
                    "COLMAP_INPUT_SUBSET_MANIFEST_URI": "s3://bucket/probe_manifest.json",
                    "COLMAP_INPUT_SUBSET_NAME": "geometry_mix",
                },
                clear=False,
            ), mock.patch.dict(sys.modules, {"boto3": fake_boto3}):
                pipeline = run_colmap_sfm.ColmapPipeline(input_dir, output_dir)
                pipeline.extract_images()

            s3_client.get_object.assert_called_once_with(
                Bucket="bucket",
                Key="probe_manifest.json",
            )
            self.assertEqual(pipeline.dataset_image_count, 2)
            self.assertEqual(
                sorted(path.name for path in pipeline.images_dir.iterdir()),
                ["IMG_02.jpg", "IMG_03.jpg"],
            )

    def test_extract_images_fails_when_manifest_selected_subset_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir(parents=True, exist_ok=True)
            archive_path = input_dir / "images.zip"
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("IMG_01.jpg", b"one")
            manifest_path = root / "probe_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "probe_subsets": {
                            "geometry_mix": {
                                "image_count": 2,
                                "images": ["IMG_01.jpg", "IMG_02.jpg"],
                            }
                        },
                        "ladder_subsets": {},
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.dict(
                os.environ,
                {
                    "COLMAP_INPUT_SUBSET_MANIFEST_URI": str(manifest_path),
                    "COLMAP_INPUT_SUBSET_NAME": "geometry_mix",
                },
                clear=False,
            ):
                pipeline = run_colmap_sfm.ColmapPipeline(input_dir, output_dir)
                with self.assertRaisesRegex(RuntimeError, "Requested subset images were missing"):
                    pipeline.extract_images()

    def test_run_spatial_heading_chunked_path_accepts_merged_ratio_at_gps_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.dataset_image_count = 250
            pipeline.gps_min_registered_ratio = 0.98
            pipeline.chunk_plans = [
                run_colmap_sfm.ChunkPlan(index=0, core_names=["a"], image_names=["a"], overlap_names=[]),
                run_colmap_sfm.ChunkPlan(index=1, core_names=["b"], image_names=["b"], overlap_names=[]),
            ]
            merged_model = run_colmap_sfm.ModelSummary(
                stage="chunk_bundle_adjuster",
                text_dir=root / "merged_text",
                cameras_registered=1,
                images_registered=247,
                points_3d=202435,
                binary_dir=root / "merged_chunk_model_01",
            )

            with mock.patch.object(
                pipeline,
                "build_spatial_heading_chunks",
                return_value=pipeline.chunk_plans,
            ), mock.patch.object(
                pipeline,
                "run_chunk_pipeline",
                side_effect=[
                    run_colmap_sfm.ModelSummary(
                        stage="chunk_00_mapper_initial",
                        text_dir=root / "chunk0",
                        cameras_registered=1,
                        images_registered=134,
                        points_3d=100000,
                        binary_dir=root / "chunk0",
                    ),
                    run_colmap_sfm.ModelSummary(
                        stage="chunk_01_mapper_initial",
                        text_dir=root / "chunk1",
                        cameras_registered=1,
                        images_registered=138,
                        points_3d=100000,
                        binary_dir=root / "chunk1",
                    ),
                ],
            ), mock.patch.object(
                pipeline,
                "merge_chunk_models",
                return_value=merged_model,
            ):
                result = pipeline.run_spatial_heading_chunked_path()

            self.assertEqual(result.images_registered, 247)
            self.assertEqual(pipeline.final_matcher_mode, "spatial_heading_chunked")

    def test_build_vocab_tree_retries_without_max_num_images_for_older_colmap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.database_path = root / "database.db"
            pipeline.generated_vocab_tree_path = root / "vocab_tree_faiss.bin"

            with sqlite3.connect(pipeline.database_path) as connection:
                connection.execute("CREATE TABLE images(image_id INTEGER PRIMARY KEY, name TEXT)")
                connection.executemany(
                    "INSERT INTO images(image_id, name) VALUES (?, ?)",
                    [(1, "a.jpg"), (2, "b.jpg")],
                )
                connection.commit()

            command_calls: list[list[str]] = []

            def fake_stream_command(command, *, stage, env=None, timeout_seconds=None, heartbeat_seconds=None):
                command_calls.append(command)
                if "--max_num_images" in command:
                    raise RuntimeError("vocab_tree_builder failed with exit code 1\nFailed to parse options - unrecognised option '--max_num_images'.")
                pipeline.generated_vocab_tree_path.write_bytes(b"faiss")

            with mock.patch.object(run_colmap_sfm, "stream_command", side_effect=fake_stream_command):
                pipeline.build_vocab_tree()

            self.assertEqual(len(command_calls), 2)
            self.assertIn("--max_num_images", command_calls[0])
            self.assertNotIn("--max_num_images", command_calls[1])
            self.assertEqual(pipeline.active_vocab_tree_path, pipeline.generated_vocab_tree_path)

    def test_run_matching_and_mapping_fails_when_chunked_path_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")

            with mock.patch.object(
                pipeline,
                "should_attempt_spatial_chunking",
                return_value=True,
            ), mock.patch.object(
                pipeline,
                "run_spatial_heading_chunked_path",
                side_effect=RuntimeError("merge failed"),
            ):
                with self.assertRaises(RuntimeError):
                    pipeline.run_matching_and_mapping()

            self.assertFalse(pipeline.fallback_triggered)

    def test_run_spatial_heading_chunked_path_supports_selected_chunk_indexes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.dict(os.environ, {"COLMAP_ONLY_CHUNK_INDEXES": "1"}, clear=False):
                pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.dataset_image_count = 8
            chunk_plans = [
                run_colmap_sfm.ChunkPlan(index=0, core_names=["a", "b"], image_names=["a", "b"], overlap_names=[]),
                run_colmap_sfm.ChunkPlan(index=1, core_names=["c", "d"], image_names=["c", "d"], overlap_names=[]),
            ]
            merged_model = run_colmap_sfm.ModelSummary(
                stage="chunk_bundle_adjuster",
                text_dir=root / "merged_text",
                cameras_registered=1,
                images_registered=2,
                points_3d=100,
                binary_dir=root / "merged_chunk_model_01",
            )

            with mock.patch.object(
                pipeline,
                "build_spatial_heading_chunks",
                return_value=chunk_plans,
            ), mock.patch.object(
                pipeline,
                "run_chunk_pipeline",
                return_value=run_colmap_sfm.ModelSummary(
                    stage="chunk_01_mapper_initial",
                    text_dir=root / "chunk1",
                    cameras_registered=1,
                    images_registered=2,
                    points_3d=100,
                    binary_dir=root / "chunk1",
                ),
            ) as run_chunk_mock, mock.patch.object(
                pipeline,
                "merge_chunk_models",
                return_value=merged_model,
            ):
                result = pipeline.run_spatial_heading_chunked_path()

            self.assertEqual(result.images_registered, 2)
            self.assertEqual(run_chunk_mock.call_count, 1)
            self.assertEqual(pipeline.chunk_execution_image_count, 2)
            self.assertEqual(pipeline.final_matcher_mode, "spatial_heading_chunked_subset")

    def test_stream_command_times_out(self):
        started = time.time()
        with self.assertRaises(RuntimeError) as raised:
            run_colmap_sfm.stream_command(
                [sys.executable, "-c", "import time; time.sleep(2)"],
                stage="timeout_test",
                timeout_seconds=0.2,
                heartbeat_seconds=0.1,
            )

        self.assertIn("timed out", str(raised.exception).lower())
        self.assertLess(time.time() - started, 2.0)

    def test_stream_command_timeout_does_not_block_on_post_kill_wait(self):
        class BlockingStdout:
            def __iter__(self):
                return self

            def __next__(self):
                time.sleep(60)
                raise StopIteration

        class HungProcess:
            def __init__(self):
                self.pid = 12345
                self.stdout = BlockingStdout()

            def wait(self, timeout=None):
                if timeout is None:
                    raise AssertionError("stream_command should not call wait() without a timeout after SIGKILL")
                raise subprocess.TimeoutExpired(cmd="fake-colmap", timeout=timeout)

            def poll(self):
                return None

        monotonic_values = iter([0.0, 1.0])

        with mock.patch.object(
            run_colmap_sfm.subprocess,
            "Popen",
            return_value=HungProcess(),
        ), mock.patch.object(
            run_colmap_sfm.os,
            "killpg",
        ), mock.patch.object(
            run_colmap_sfm.time,
            "monotonic",
            side_effect=lambda: next(monotonic_values, 1.0),
        ):
            with self.assertRaises(RuntimeError) as raised:
                run_colmap_sfm.stream_command(
                    ["fake-colmap"],
                    stage="timeout_post_kill_test",
                    timeout_seconds=0.1,
                    heartbeat_seconds=0.1,
                )

        message = str(raised.exception)
        self.assertIn("timed out", message.lower())
        self.assertIn("required SIGKILL after timeout", message)

    def test_orientation_source_selection_prefers_flight_when_gimbal_is_degenerate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            exif_records = {
                "a.jpg": {
                    "gimbal_yaw_deg": 0.0,
                    "flight_yaw_deg": 12.0,
                    "gps_img_direction_deg": None,
                    "gimbal_pitch_deg": 0.0,
                    "flight_pitch_deg": -8.0,
                },
                "b.jpg": {
                    "gimbal_yaw_deg": 0.0,
                    "flight_yaw_deg": 94.0,
                    "gps_img_direction_deg": None,
                    "gimbal_pitch_deg": 0.0,
                    "flight_pitch_deg": -21.0,
                },
                "c.jpg": {
                    "gimbal_yaw_deg": 0.0,
                    "flight_yaw_deg": 188.0,
                    "gps_img_direction_deg": None,
                    "gimbal_pitch_deg": 0.0,
                    "flight_pitch_deg": -3.0,
                },
            }

            pipeline.apply_orientation_prior_sources(exif_records)

            self.assertEqual(pipeline.heading_prior_source, "flight_yaw")
            self.assertEqual(pipeline.pitch_prior_source, "flight_pitch")
            self.assertEqual(exif_records["a.jpg"]["heading_deg"], 12.0)
            self.assertEqual(exif_records["b.jpg"]["pitch_deg"], -21.0)

    def test_orientation_source_selection_keeps_gimbal_when_it_has_real_dispersion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            exif_records = {
                "a.jpg": {
                    "gimbal_yaw_deg": 10.0,
                    "flight_yaw_deg": 13.0,
                    "gps_img_direction_deg": None,
                    "gimbal_pitch_deg": -20.0,
                    "flight_pitch_deg": -18.0,
                },
                "b.jpg": {
                    "gimbal_yaw_deg": 82.0,
                    "flight_yaw_deg": 85.0,
                    "gps_img_direction_deg": None,
                    "gimbal_pitch_deg": -8.0,
                    "flight_pitch_deg": -7.0,
                },
                "c.jpg": {
                    "gimbal_yaw_deg": 174.0,
                    "flight_yaw_deg": 176.0,
                    "gps_img_direction_deg": None,
                    "gimbal_pitch_deg": 2.0,
                    "flight_pitch_deg": 3.0,
                },
            }

            pipeline.apply_orientation_prior_sources(exif_records)

            self.assertEqual(pipeline.heading_prior_source, "gimbal_yaw")
            self.assertEqual(pipeline.pitch_prior_source, "gimbal_pitch")
            self.assertEqual(exif_records["c.jpg"]["heading_deg"], 174.0)
            self.assertEqual(exif_records["a.jpg"]["pitch_deg"], -20.0)


if __name__ == "__main__":
    unittest.main()
