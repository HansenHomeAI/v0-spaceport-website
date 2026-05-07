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


if __name__ == "__main__":
    unittest.main()
