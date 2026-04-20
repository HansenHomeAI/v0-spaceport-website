import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "sfm" / "run_colmap_sfm.py"
SPEC = importlib.util.spec_from_file_location("run_colmap_sfm_global_test_module", MODULE_PATH)
run_colmap_sfm = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = run_colmap_sfm
SPEC.loader.exec_module(run_colmap_sfm)


class ColmapGlobalMapperTests(unittest.TestCase):
    def test_monolithic_mapper_mode_defaults_incremental(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")

            self.assertEqual(pipeline.monolithic_mapper_mode, "incremental")
            self.assertFalse(pipeline.global_mapper_use_view_graph_calibrator)
            self.assertIsNone(pipeline.matching_max_num_matches)
            self.assertIsNone(pipeline.feature_max_image_size)
            self.assertEqual(pipeline.chunk_leaf_mapper_mode, "incremental")
            self.assertEqual(pipeline.chunk_recovery_mapper_mode, "inherit")
            self.assertEqual(pipeline.chunk_merge_strategy, "serial")
            self.assertEqual(pipeline.chunk_hierarchical_merge_fanin, 2)

    def test_global_mapper_mode_enables_view_graph_calibrator_by_default(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_MONOLITHIC_MAPPER_MODE": "global"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")

            self.assertEqual(pipeline.monolithic_mapper_mode, "global")
            self.assertTrue(pipeline.global_mapper_use_view_graph_calibrator)

    def test_chunk_global_leaf_defaults_recovery_to_incremental(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_CHUNK_LEAF_MAPPER_MODE": "global"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")

            self.assertEqual(pipeline.chunk_leaf_mapper_mode, "global")
            self.assertEqual(pipeline.chunk_recovery_mapper_mode, "incremental")

    def test_run_mapper_uses_global_mapper_command_without_incremental_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            sparse_root = root / "sparse_global"
            (sparse_root / "0").mkdir(parents=True, exist_ok=True)

            with mock.patch.object(run_colmap_sfm, "stream_command") as stream_command_mock, mock.patch.object(
                run_colmap_sfm, "count_text_rows", return_value=1
            ), mock.patch.object(run_colmap_sfm, "count_registered_images", return_value=3):
                model = pipeline.run_mapper(
                    stage="mapper_global_spatial_only",
                    sparse_root=sparse_root,
                    mapper_command="global_mapper",
                )

            command = stream_command_mock.call_args_list[0].args[0]
            self.assertEqual(command[1], "global_mapper")
            self.assertNotIn("--Mapper.num_threads", command)
            self.assertNotIn("--Mapper.ba_refine_principal_point", command)
            self.assertEqual(model.images_registered, 3)

    def test_run_mapper_uses_gpu_bundle_adjustment_flags_for_incremental_mapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            sparse_root = root / "sparse_incremental"
            (sparse_root / "0").mkdir(parents=True, exist_ok=True)

            with mock.patch.object(run_colmap_sfm, "stream_command") as stream_command_mock, mock.patch.object(
                run_colmap_sfm, "count_text_rows", return_value=1
            ), mock.patch.object(run_colmap_sfm, "count_registered_images", return_value=3):
                pipeline.run_mapper(
                    stage="mapper_spatial_only",
                    sparse_root=sparse_root,
                    mapper_command="mapper",
                )

            command = stream_command_mock.call_args_list[0].args[0]
            self.assertIn("--Mapper.num_threads", command)
            self.assertIn("--Mapper.ba_refine_principal_point", command)
    def test_run_global_mapper_clones_database_and_runs_calibrator(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_MONOLITHIC_MAPPER_MODE": "global"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.colmap_capabilities["supports_global_mapper"] = True

            def mapper_side_effect(**kwargs):
                pipeline.timings["mapper_global_spatial_only_seconds"] = 12.5
                return run_colmap_sfm.ModelSummary(
                    stage="mapper_global_spatial_only",
                    text_dir=root,
                    cameras_registered=1,
                    images_registered=10,
                    points_3d=1000,
                )

            with mock.patch.object(pipeline, "clone_database") as clone_mock, mock.patch.object(
                pipeline, "run_view_graph_calibrator"
            ) as calibrator_mock, mock.patch.object(
                pipeline,
                "run_mapper",
                side_effect=mapper_side_effect,
            ) as mapper_mock:
                model = pipeline.run_global_mapper(
                    stage="mapper_global_spatial_only",
                    sparse_root=root / "sparse",
                    image_count=10,
                )

            global_database_path = pipeline.work_dir / "database_global.db"
            clone_mock.assert_called_once_with(
                pipeline.database_path,
                global_database_path,
                operation_label="clone_database_for_global_mapper",
            )
            calibrator_mock.assert_called_once_with(
                database_path=global_database_path,
                stage="view_graph_calibrator_mapper_global_spatial_only",
            )
            mapper_mock.assert_called_once_with(
                database_path=global_database_path,
                stage="mapper_global_spatial_only",
                sparse_root=root / "sparse",
                image_count=10,
                mapper_command="global_mapper",
            )
            self.assertTrue(pipeline.global_mapper_used)
            self.assertEqual(pipeline.global_mapper_seconds, 12.5)
            self.assertEqual(model.images_registered, 10)

    def test_run_global_mapper_skips_calibrator_when_disabled(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {
                "COLMAP_MONOLITHIC_MAPPER_MODE": "global",
                "COLMAP_GLOBAL_MAPPER_USE_VIEW_GRAPH_CALIBRATOR": "0",
            },
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.colmap_capabilities["supports_global_mapper"] = True

            with mock.patch.object(pipeline, "clone_database"), mock.patch.object(
                pipeline, "run_view_graph_calibrator"
            ) as calibrator_mock, mock.patch.object(
                pipeline,
                "run_mapper",
                return_value=run_colmap_sfm.ModelSummary(
                    stage="mapper_global_spatial_only",
                    text_dir=root,
                    cameras_registered=1,
                    images_registered=4,
                    points_3d=400,
                ),
            ):
                pipeline.run_global_mapper(
                    stage="mapper_global_spatial_only",
                    sparse_root=root / "sparse",
                    image_count=4,
                )

            calibrator_mock.assert_not_called()

    def test_run_chunk_pipeline_dispatches_global_initial_and_incremental_recovery(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_CHUNK_LEAF_MAPPER_MODE": "global"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            chunk_plan = run_colmap_sfm.ChunkPlan(
                index=0,
                core_names=["IMG_01.jpg"],
                image_names=["IMG_01.jpg", "IMG_02.jpg"],
                overlap_names=["IMG_02.jpg"],
                source_chunk_indexes=[0],
            )
            chunk_database_path = root / "chunk.db"
            initial_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_mapper_initial",
                text_dir=root,
                cameras_registered=1,
                images_registered=1,
                points_3d=100,
                binary_dir=root / "chunk_initial",
            )
            recovered_model = run_colmap_sfm.ModelSummary(
                stage="chunk_00_mapper_recovery",
                text_dir=root,
                cameras_registered=1,
                images_registered=2,
                points_3d=200,
                binary_dir=root / "chunk_recovery",
            )

            def global_mapper_side_effect(**kwargs):
                pipeline.timings["chunk_00_mapper_initial_seconds"] = 12.5
                return initial_model

            def incremental_mapper_side_effect(**kwargs):
                pipeline.timings["chunk_00_mapper_recovery_seconds"] = 3.0
                return recovered_model

            with mock.patch.object(
                pipeline,
                "prepare_chunk_database",
                return_value=chunk_database_path,
            ), mock.patch.object(
                pipeline,
                "run_chunk_matchers",
            ), mock.patch.object(
                pipeline,
                "run_chunk_recovery_matchers",
            ), mock.patch.object(
                pipeline,
                "build_retry_chunk_plan",
                return_value=chunk_plan,
            ), mock.patch.object(
                pipeline,
                "run_global_mapper",
                side_effect=global_mapper_side_effect,
            ) as run_global_mapper_mock, mock.patch.object(
                pipeline,
                "run_mapper",
                side_effect=incremental_mapper_side_effect,
            ) as run_mapper_mock, mock.patch.object(
                pipeline,
                "chunk_core_registered_ratio",
                side_effect=[
                    (0.0, 0, set()),
                    (1.0, 1, {"IMG_01.jpg", "IMG_02.jpg"}),
                ],
            ):
                model = pipeline.run_chunk_pipeline(chunk_plan)

            self.assertEqual(model.images_registered, 2)
            run_global_mapper_mock.assert_called_once_with(
                stage="chunk_00_mapper_initial",
                sparse_root=pipeline.work_dir / "chunk_00" / "sparse_initial",
                image_count=2,
                source_database_path=chunk_database_path,
                database_path=pipeline.work_dir / "chunk_00" / "database_global_initial.db",
            )
            run_mapper_mock.assert_called_once_with(
                database_path=chunk_database_path,
                stage="chunk_00_mapper_recovery",
                sparse_root=pipeline.work_dir / "chunk_00" / "sparse_recovery",
                image_count=2,
            )
            self.assertEqual(pipeline.chunk_global_mapper_seconds, 12.5)
            self.assertEqual(pipeline.chunk_incremental_mapper_seconds, 3.0)
            self.assertEqual(pipeline.chunk_mapper_seconds, 15.5)
            self.assertEqual(pipeline.chunk_leaf_global_count, 1)
            self.assertEqual(pipeline.chunk_leaf_incremental_count, 1)
            self.assertEqual(pipeline.chunk_leaf_recovery_fallback_count, 1)

    def test_run_matching_and_mapping_uses_global_mapper_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_MONOLITHIC_MAPPER_MODE": "global"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.dataset_image_count = 5
            pipeline.gps_image_count = 5
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
            pipeline.run_global_mapper = mock.Mock(
                return_value=run_colmap_sfm.ModelSummary(
                    stage="mapper_global_spatial_sequential_only",
                    text_dir=root,
                    cameras_registered=1,
                    images_registered=5,
                    points_3d=2500,
                )
            )
            pipeline.run_mapper = mock.Mock()

            best_model = pipeline.run_matching_and_mapping()

            self.assertEqual(best_model.images_registered, 5)
            self.assertEqual(calls, ["spatial_matcher", "sequential_matcher"])
            self.assertEqual(pipeline.final_matcher_mode, "global_spatial_sequential_only")
            pipeline.run_global_mapper.assert_called_once()
            pipeline.run_mapper.assert_not_called()

    def test_run_matching_and_mapping_reports_missing_global_mapper_support(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_MONOLITHIC_MAPPER_MODE": "global"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.dataset_image_count = 5
            pipeline.gps_image_count = 5
            pipeline.gps_prior_coverage = 1.0
            pipeline.enable_sequential_matcher = True
            pipeline.run_spatial_matcher = mock.Mock()
            pipeline.run_sequential_matcher = mock.Mock()
            pipeline.run_global_mapper = mock.Mock(
                side_effect=RuntimeError("COLMAP runtime does not support global_mapper")
            )

            with self.assertRaisesRegex(RuntimeError, "GPS-first mapper failed"):
                pipeline.run_matching_and_mapping()

            self.assertEqual(pipeline.failure_stage, "mapper_global_spatial_sequential_only")

    def test_build_metadata_reports_global_mapper_fields(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_MONOLITHIC_MAPPER_MODE": "global"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.global_mapper_used = True
            pipeline.global_mapper_seconds = 12.5
            pipeline.view_graph_calibrator_ran = True
            pipeline.view_graph_calibrator_seconds = 2.25
            model = run_colmap_sfm.ModelSummary(
                stage="mapper_global_spatial_only",
                text_dir=root,
                cameras_registered=1,
                images_registered=5,
                points_3d=250,
            )

            metadata = pipeline.build_metadata(best_model=model, quality_check_passed=True)

            self.assertEqual(metadata["monolithic_mapper_mode"], "global")
            self.assertTrue(metadata["global_mapper_used"])
            self.assertEqual(metadata["global_mapper_seconds"], 12.5)
            self.assertTrue(metadata["view_graph_calibrator_ran"])
            self.assertEqual(metadata["view_graph_calibrator_seconds"], 2.25)

    def test_build_metadata_reports_chunk_hybrid_fields(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {
                "COLMAP_CHUNK_LEAF_MAPPER_MODE": "global",
                "COLMAP_CHUNK_MERGE_STRATEGY": "hierarchical",
            },
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            pipeline.chunk_global_mapper_seconds = 12.5
            pipeline.chunk_incremental_mapper_seconds = 3.0
            pipeline.chunk_mapper_seconds = 15.5
            pipeline.chunk_leaf_global_count = 2
            pipeline.chunk_leaf_incremental_count = 1
            pipeline.chunk_leaf_recovery_fallback_count = 1
            pipeline.merge_tree_depth = 2
            pipeline.merge_tree_node_count = 5
            pipeline.merge_tree_level_summaries = [{"level": 0, "input_component_count": 3}]
            model = run_colmap_sfm.ModelSummary(
                stage="chunk_bundle_adjuster_l01_g00",
                text_dir=root,
                cameras_registered=1,
                images_registered=5,
                points_3d=250,
            )

            metadata = pipeline.build_metadata(best_model=model, quality_check_passed=True)

            self.assertEqual(metadata["chunk_leaf_mapper_mode"], "global")
            self.assertEqual(metadata["chunk_recovery_mapper_mode"], "incremental")
            self.assertEqual(metadata["chunk_merge_strategy"], "hierarchical")
            self.assertEqual(metadata["chunk_global_mapper_seconds"], 12.5)
            self.assertEqual(metadata["chunk_incremental_mapper_seconds"], 3.0)
            self.assertEqual(metadata["chunk_leaf_global_count"], 2)
            self.assertEqual(metadata["chunk_leaf_incremental_count"], 1)
            self.assertEqual(metadata["chunk_leaf_recovery_fallback_count"], 1)
            self.assertEqual(metadata["merge_tree_depth"], 2)
            self.assertEqual(metadata["merge_tree_node_count"], 5)
            self.assertEqual(metadata["merge_tree_level_summaries"], [{"level": 0, "input_component_count": 3}])

    def test_matchers_include_matching_max_num_matches_when_configured(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {"COLMAP_MATCHING_MAX_NUM_MATCHES": "2048"},
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")

            with mock.patch.object(run_colmap_sfm, "stream_command") as stream_command_mock, mock.patch.object(
                pipeline,
                "count_verified_pairs",
                side_effect=[0, 12, 12, 20],
            ):
                pipeline.run_spatial_matcher()
                pipeline.run_sequential_matcher()

            spatial_command = stream_command_mock.call_args_list[0].args[0]
            sequential_command = stream_command_mock.call_args_list[1].args[0]
            self.assertIn("--FeatureMatching.max_num_matches", spatial_command)
            self.assertIn("2048", spatial_command)
            self.assertIn("--FeatureMatching.max_num_matches", sequential_command)
            self.assertIn("2048", sequential_command)

    def test_build_metadata_reports_matching_and_feature_size_fields(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {
                "COLMAP_MATCHING_MAX_NUM_MATCHES": "2048",
                "COLMAP_FEATURE_MAX_IMAGE_SIZE": "3200",
            },
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            model = run_colmap_sfm.ModelSummary(
                stage="mapper_spatial_only",
                text_dir=root,
                cameras_registered=1,
                images_registered=5,
                points_3d=250,
            )

            metadata = pipeline.build_metadata(best_model=model, quality_check_passed=True)

            self.assertEqual(metadata["matching_max_num_matches"], 2048)
            self.assertEqual(metadata["feature_max_image_size"], "3200")

    def test_gpu_bundle_adjustment_preflight_rejects_missing_build_support(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ,
            {
                "COLMAP_MONOLITHIC_MAPPER_MODE": "global",
                "COLMAP_REQUIRE_GPU_BUNDLE_ADJUSTMENT": "1",
            },
            clear=False,
        ):
            root = Path(tmp)
            pipeline = run_colmap_sfm.ColmapPipeline(root / "input", root / "output")
            if not hasattr(pipeline, "ensure_gpu_bundle_adjustment_preflight"):
                self.skipTest("GPU bundle-adjustment preflight is not shipped on this branch")
            pipeline.colmap_build_info = {"build_info_present": False}
            pipeline.colmap_capabilities = pipeline.build_colmap_capabilities()

            with self.assertRaisesRegex(RuntimeError, "build info marker is missing"):
                pipeline.ensure_gpu_bundle_adjustment_preflight()

if __name__ == "__main__":
    unittest.main()
