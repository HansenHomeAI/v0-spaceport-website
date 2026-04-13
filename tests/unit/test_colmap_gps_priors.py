import importlib.util
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
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

    def test_gps_first_falls_back_once_when_registration_is_incomplete(self):
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
            fallback_model = run_colmap_sfm.ModelSummary(
                stage="mapper_spatial_sequential_plus_vocab",
                text_dir=root,
                cameras_registered=1,
                images_registered=4,
                points_3d=3400,
            )

            pipeline.run_spatial_matcher = record_call("spatial_matcher")
            pipeline.run_sequential_matcher = record_call("sequential_matcher")
            pipeline.run_vocab_matching = record_call("vocab_tree_matcher")
            pipeline.run_mapper = mock.Mock(side_effect=[spatial_model, fallback_model])

            best_model = pipeline.run_matching_and_mapping()

            self.assertEqual(best_model.images_registered, 4)
            self.assertEqual(
                calls,
                ["spatial_matcher", "sequential_matcher", "vocab_tree_matcher"],
            )
            self.assertTrue(pipeline.fallback_triggered)
            self.assertEqual(pipeline.fallback_reason, "below_registered_ratio_threshold")
            self.assertEqual(pipeline.final_matcher_mode, "spatial_sequential_plus_vocab")

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
            ), mock.patch.object(pipeline, "run_vocab_matching") as vocab_mock, mock.patch.object(
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
            self.assertEqual(vocab_mock.call_count, 1)
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

    def test_run_chunk_pipeline_keeps_initial_model_when_boundary_recovery_fails(self):
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

            with mock.patch.object(
                pipeline,
                "prepare_chunk_database",
                return_value=root / "chunk.db",
            ), mock.patch.object(pipeline, "run_spatial_matcher"), mock.patch.object(
                pipeline, "run_sequential_matcher"
            ), mock.patch.object(
                pipeline,
                "run_vocab_matching",
                side_effect=RuntimeError("legacy builder flags unsupported"),
            ), mock.patch.object(
                pipeline,
                "run_mapper",
                return_value=initial_model,
            ) as mapper_mock:
                pipeline.timings["chunk_00_mapper_initial_seconds"] = 10.0
                best_model = pipeline.run_chunk_pipeline(chunk)

            self.assertEqual(best_model.images_registered, 2)
            self.assertTrue(pipeline.boundary_recovery_triggered)
            self.assertEqual(mapper_mock.call_count, 1)

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

            def fake_stream_command(command, *, stage, env=None):
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

    def test_run_matching_and_mapping_falls_back_to_monolithic_when_chunked_path_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            fallback_model = run_colmap_sfm.ModelSummary(
                stage="mapper_spatial_sequential_only",
                text_dir=root,
                cameras_registered=1,
                images_registered=10,
                points_3d=2000,
                binary_dir=root,
                image_count=10,
            )

            with mock.patch.object(
                pipeline,
                "should_attempt_spatial_chunking",
                return_value=True,
            ), mock.patch.object(
                pipeline,
                "run_spatial_heading_chunked_path",
                side_effect=RuntimeError("merge failed"),
            ), mock.patch.object(
                pipeline,
                "should_attempt_gps_first",
                return_value=True,
            ), mock.patch.object(
                pipeline,
                "run_monolithic_gps_first_path",
                return_value=fallback_model,
            ):
                best_model = pipeline.run_matching_and_mapping()

            self.assertEqual(best_model.images_registered, 10)
            self.assertTrue(pipeline.fallback_triggered)
            self.assertEqual(pipeline.fallback_reason, "chunked_path_failed")
            self.assertEqual(pipeline.final_matcher_mode, "chunked_fallback_to_monolithic")


if __name__ == "__main__":
    unittest.main()
