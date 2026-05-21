import argparse
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "build_sfm_fanout_contract.py"
SPEC = importlib.util.spec_from_file_location("build_sfm_fanout_contract_test_module", MODULE_PATH)
fanout_contract = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = fanout_contract
SPEC.loader.exec_module(fanout_contract)


class SfmFanoutContractTests(unittest.TestCase):
    def test_build_contract_generates_disjoint_leaf_specs(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "chunk_planner_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "planner": "footprint_graph_v1",
                        "pipeline_mode": "distributed_chunked_v1",
                        "chunks": [
                            {
                                "index": 0,
                                "core_names": ["A.JPG", "B.JPG"],
                                "overlap_names": ["C.JPG"],
                                "image_names": ["A.JPG", "B.JPG", "C.JPG"],
                            },
                            {
                                "index": 1,
                                "core_names": ["D.JPG"],
                                "overlap_names": ["C.JPG"],
                                "image_names": ["C.JPG", "D.JPG"],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                planner_manifest=str(manifest_path),
                planner_manifest_uri="s3://bucket/chunk_planner_manifest.json",
                input_s3_uri="s3://bucket/input.zip",
                output_s3_uri="s3://bucket/fanout/",
                branch="agent-73948216-sfm-production-spine",
                head="abc123",
                job_prefix="md1-fanout-canary",
                image_uri="repo/sfm:tag",
                instance_type="ml.g4dn.xlarge",
                volume_size_gb=120,
                summary_json_output=str(Path(tmp) / "contract.json"),
            )

            contract = fanout_contract.build_contract(args)

            self.assertEqual(contract["status"], "dry_run_contract_ready")
            self.assertEqual(contract["chunk_count"], 2)
            self.assertEqual(contract["coverage"]["selected_chunk_indexes"], [0, 1])
            self.assertEqual(contract["coverage"]["unique_core_images"], 3)
            self.assertEqual(contract["coverage"]["duplicate_core_images"], 0)
            self.assertEqual(contract["leaf_jobs"][1]["job_name"], "md1-fanout-canary-leaf-01")
            self.assertEqual(
                contract["leaf_jobs"][1]["processing_job_spec"]["Environment"]["COLMAP_ONLY_CHUNK_INDEXES"],
                "1",
            )
            self.assertEqual(
                contract["reducer_contract"]["final_output_uri"],
                "s3://bucket/fanout/merged/colmap",
            )

    def test_build_contract_requires_uploaded_immutable_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "chunk_planner_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "chunks": [
                            {
                                "index": 0,
                                "core_names": ["A.JPG"],
                                "overlap_names": [],
                                "image_names": ["A.JPG"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                planner_manifest=str(manifest_path),
                planner_manifest_uri="",
                input_s3_uri="s3://bucket/input.zip",
                output_s3_uri="s3://bucket/fanout",
                branch="branch",
                head="head",
                job_prefix="prefix",
                image_uri="repo/sfm:tag",
                instance_type="ml.g4dn.xlarge",
                volume_size_gb=120,
                summary_json_output=str(Path(tmp) / "contract.json"),
            )

            contract = fanout_contract.build_contract(args)

            self.assertEqual(contract["status"], "dry_run_contract_needs_fix")
            self.assertIn("immutable planner manifest must be uploaded to S3 before launching leaves", contract["gaps"])

    def test_visibility_cell_contract_preserves_planner_and_jurisdictions(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "chunk_planner_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "planner": "visibility_cell_v1",
                        "pipeline_mode": "distributed_chunked_v1",
                        "seam_overlap_percent": 15.0,
                        "primary_cell_id_by_image": {"A.JPG": 0, "B.JPG": 0, "C.JPG": 1},
                        "overlap_cell_ids_by_image": {"B.JPG": [1]},
                        "chunk_jurisdictions": {
                            "0": {"jurisdiction_bounds": {"min_x": 0, "max_x": 10, "min_y": 0, "max_y": 10}},
                            "1": {"jurisdiction_bounds": {"min_x": 8, "max_x": 18, "min_y": 0, "max_y": 10}},
                        },
                        "visibility_cell_manifest": {
                            "cells": [
                                {
                                    "index": 0,
                                    "cell_id": "cell-000",
                                    "image_names": [
                                        "A.JPG",
                                        "B.JPG",
                                        "S00.JPG",
                                        "S01.JPG",
                                        "S02.JPG",
                                        "S03.JPG",
                                        "S04.JPG",
                                        "S05.JPG",
                                        "S06.JPG",
                                        "S07.JPG",
                                        "S08.JPG",
                                        "S09.JPG",
                                    ],
                                    "adjacency": [1],
                                },
                                {
                                    "index": 1,
                                    "cell_id": "cell-001",
                                    "image_names": [
                                        "B.JPG",
                                        "C.JPG",
                                        "S00.JPG",
                                        "S01.JPG",
                                        "S02.JPG",
                                        "S03.JPG",
                                        "S04.JPG",
                                        "S05.JPG",
                                        "S06.JPG",
                                        "S07.JPG",
                                        "S08.JPG",
                                        "S09.JPG",
                                    ],
                                    "adjacency": [0],
                                },
                            ]
                        },
                        "chunks": [
                            {
                                "index": 0,
                                "core_names": ["A.JPG", "B.JPG"],
                                "overlap_names": [],
                                "image_names": ["A.JPG", "B.JPG"],
                            },
                            {
                                "index": 1,
                                "core_names": ["C.JPG"],
                                "overlap_names": ["B.JPG"],
                                "image_names": ["B.JPG", "C.JPG"],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                planner_manifest=str(manifest_path),
                planner_manifest_uri="s3://bucket/chunk_planner_manifest.json",
                input_s3_uri="s3://bucket/input.zip",
                output_s3_uri="s3://bucket/fanout/",
                branch="agent-73948216-sfm-production-spine",
                head="abc123",
                job_prefix="md1-visibility-canary",
                image_uri="repo/sfm:tag",
                instance_type="ml.g4dn.xlarge",
                volume_size_gb=120,
                max_concurrency=4,
                max_attempts_per_leaf=3,
                min_core_images=1,
                summary_json_output=str(Path(tmp) / "contract.json"),
            )

            contract = fanout_contract.build_contract(args)

            self.assertEqual(contract["status"], "dry_run_contract_ready")
            self.assertTrue(contract["visibility_cell_contract"]["enabled"])
            self.assertEqual(contract["visibility_cell_contract"]["cell_count"], 2)
            self.assertEqual(contract["visibility_cell_contract"]["chunk_jurisdiction_count"], 2)
            self.assertEqual(contract["visibility_cell_contract"]["min_adjacent_shared_images"], 11)
            self.assertEqual(contract["visibility_cell_contract"]["weak_adjacent_seams_under_10"], [])
            self.assertEqual(contract["max_concurrency"], 4)
            self.assertEqual(contract["retry_policy"]["max_attempts_per_leaf"], 3)
            self.assertEqual(
                contract["leaf_jobs"][0]["processing_job_spec"]["Environment"]["COLMAP_CHUNK_PLANNER"],
                "visibility_cell_v1",
            )

    def test_visibility_cell_contract_blocks_weak_adjacent_seams(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "chunk_planner_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "planner": "visibility_cell_v1",
                        "pipeline_mode": "distributed_chunked_v1",
                        "seam_overlap_percent": 15.0,
                        "primary_cell_id_by_image": {"A.JPG": 0, "B.JPG": 1},
                        "overlap_cell_ids_by_image": {},
                        "chunk_jurisdictions": {
                            "0": {"jurisdiction_bounds": {"min_x": 0, "max_x": 10, "min_y": 0, "max_y": 10}},
                            "1": {"jurisdiction_bounds": {"min_x": 8, "max_x": 18, "min_y": 0, "max_y": 10}},
                        },
                        "visibility_cell_manifest": {
                            "cells": [
                                {"index": 0, "cell_id": "cell-000", "image_names": ["A.JPG"], "adjacency": [1]},
                                {"index": 1, "cell_id": "cell-001", "image_names": ["B.JPG"], "adjacency": [0]},
                            ]
                        },
                        "chunks": [
                            {
                                "index": 0,
                                "core_names": ["A.JPG"],
                                "overlap_names": [],
                                "image_names": ["A.JPG"],
                            },
                            {
                                "index": 1,
                                "core_names": ["B.JPG"],
                                "overlap_names": [],
                                "image_names": ["B.JPG"],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                planner_manifest=str(manifest_path),
                planner_manifest_uri="s3://bucket/chunk_planner_manifest.json",
                input_s3_uri="s3://bucket/input.zip",
                output_s3_uri="s3://bucket/fanout/",
                branch="agent-73948216-sfm-production-spine",
                head="abc123",
                job_prefix="md1-visibility-canary",
                image_uri="repo/sfm:tag",
                instance_type="ml.g4dn.xlarge",
                volume_size_gb=120,
                max_concurrency=4,
                max_attempts_per_leaf=3,
                summary_json_output=str(Path(tmp) / "contract.json"),
            )

            contract = fanout_contract.build_contract(args)

            self.assertEqual(contract["status"], "dry_run_contract_needs_fix")
            self.assertIn(
                "visibility_cell_v1 adjacent seams must have at least 10 shared images or an explicit targeted seam proof",
                contract["gaps"],
            )
            self.assertEqual(contract["visibility_cell_contract"]["min_adjacent_shared_images"], 0)

    def test_visibility_cell_contract_blocks_weak_core_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "chunk_planner_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "planner": "visibility_cell_v1",
                        "pipeline_mode": "distributed_chunked_v1",
                        "seam_overlap_percent": 15.0,
                        "primary_cell_id_by_image": {"A.JPG": 0},
                        "overlap_cell_ids_by_image": {"B.JPG": [0]},
                        "chunk_jurisdictions": {
                            "0": {"jurisdiction_bounds": {"min_x": 0, "max_x": 10, "min_y": 0, "max_y": 10}},
                        },
                        "visibility_cell_manifest": {
                            "cells": [
                                {"index": 0, "cell_id": "cell-000", "image_names": ["A.JPG", "B.JPG"], "adjacency": []},
                            ]
                        },
                        "chunks": [
                            {
                                "index": 0,
                                "core_names": ["A.JPG"],
                                "overlap_names": ["B.JPG"],
                                "image_names": ["A.JPG", "B.JPG"],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                planner_manifest=str(manifest_path),
                planner_manifest_uri="s3://bucket/chunk_planner_manifest.json",
                input_s3_uri="s3://bucket/input.zip",
                output_s3_uri="s3://bucket/fanout/",
                branch="agent-73948216-sfm-production-spine",
                head="abc123",
                job_prefix="cvhr-visibility-canary",
                image_uri="repo/sfm:tag",
                instance_type="ml.g4dn.xlarge",
                volume_size_gb=120,
                max_concurrency=4,
                max_attempts_per_leaf=3,
                min_core_images=20,
                summary_json_output=str(Path(tmp) / "contract.json"),
            )

            contract = fanout_contract.build_contract(args)

            self.assertEqual(contract["status"], "dry_run_contract_needs_fix")
            self.assertIn(
                "visibility_cell_v1 leaf chunks must have at least 20 core images or be merged before fanout",
                contract["gaps"],
            )
            self.assertEqual(
                contract["visibility_cell_contract"]["weak_core_chunks"],
                [{"chunk_index": 0, "core_image_count": 1, "min_core_images": 20}],
            )


if __name__ == "__main__":
    unittest.main()
