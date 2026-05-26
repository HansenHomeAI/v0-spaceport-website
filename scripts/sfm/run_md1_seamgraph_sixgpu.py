#!/usr/bin/env python3
"""Manage the MD1 seam-graph SfM six-GPU proof run.

The script is intentionally resumable. It records every launched SageMaker job
in a status JSON so a heartbeat can continue without relaunching duplicates.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_TS = "20260526T1620Z"
BRANCH = "agent-29861473-md1-sixgpu-sfm"
SOURCE_IMAGE_URI = (
    "975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:"
    "agent73948216sfmproductionspine"
)
ROLE_ARN = "arn:aws:iam::975050048887:role/Spaceport-SageMaker-Role-staging"
INPUT_URI = "s3://spaceport-uploads/1775750905123-vg76vr-md1-dji-images.zip"
OUTPUT_ROOT = (
    f"s3://spaceport-ml-processing-staging/manual-validations/"
    f"md1-seamgraph-sixgpu-{RUN_TS}"
)
STATUS_PATH = REPO_ROOT / "logs" / "sfm-production-spine" / f"md1_sg6_status_{RUN_TS}.json"
LOCAL_MANIFEST_PATH = (
    REPO_ROOT / "logs" / "sfm-production-spine" / f"md1_sg6_planner_manifest_{RUN_TS}.json"
)
MAX_CONCURRENCY = 6
INSTANCE_TYPE = "ml.g4dn.xlarge"
VOLUME_SIZE_GB = 120


PLANNER_ENV = {
    "AWS_DEFAULT_REGION": "us-west-2",
    "PYTHONUNBUFFERED": "1",
    "COLMAP_ENABLE_SPATIAL_CHUNKING": "1",
    "COLMAP_PIPELINE_MODE": "distributed_chunked_v1",
    "COLMAP_CHUNK_PLANNER": "visibility_cell_v1",
    "COLMAP_CHUNK_TARGET_IMAGES": "220",
    "COLMAP_CHUNK_MIN_IMAGES": "120",
    "COLMAP_CHUNK_HARD_MAX_IMAGES": "360",
    "COLMAP_LEAF_TARGET_IMAGES": "220",
    "COLMAP_LEAF_HARD_CAP": "360",
    "COLMAP_MATCH_PROFILE": "P3",
    "COLMAP_PAIR_CAP_LOCAL": "28",
    "COLMAP_PAIR_CAP_REVISIT": "12",
    "COLMAP_PAIR_CAP_SEAM": "14",
    "COLMAP_GRAPH_XY_NEIGHBOR_LIMIT": "80",
    "COLMAP_CHUNK_OVERLAP_ANCHOR_COUNT": "20",
    "COLMAP_VISIBILITY_CELL_OVERLAP_RATIO": "0.15",
    "COLMAP_VISIBILITY_CELL_MAX_OVERLAP_CELLS": "4",
    "COLMAP_VISIBILITY_CELL_MIN_SCORE": "0.08",
    "COLMAP_VISIBILITY_CELL_MIN_CORE_IMAGES": "20",
    "SFM_PLANNER_REPORT_ONLY": "1",
    "SFM_BENCHMARK_SUBSET_STRATEGY": "md1_seamgraph_sixgpu_planner",
}


LEAF_ENV = {
    key: value
    for key, value in PLANNER_ENV.items()
    if key not in {"SFM_PLANNER_REPORT_ONLY", "SFM_BENCHMARK_SUBSET_STRATEGY"}
}
LEAF_ENV.update(
    {
        "COLMAP_GPS_ALIGN_OUTPUT": "1",
        "COLMAP_GPS_ALIGN_OUTPUT_REQUIRED": "1",
        "COLMAP_GPS_ALIGN_MIN_COMMON_IMAGES": "20",
        "COLMAP_GPS_ALIGN_MAX_ERROR_METERS": "25",
        "COLMAP_VISIBILITY_TRACK_OWNER_FALLBACK": "1",
        "COLMAP_CHUNK_MAPPER_TIMEOUT_SECONDS": "7200",
        "COLMAP_BRIDGE_MAPPER_TIMEOUT_SECONDS": "7200",
    }
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=check)


def aws_json(*args: str) -> dict[str, Any]:
    result = run(["aws", *args, "--output", "json"])
    return json.loads(result.stdout or "{}")


def git_head() -> str:
    return run(["git", "rev-parse", "HEAD"]).stdout.strip()


def load_status() -> dict[str, Any]:
    if STATUS_PATH.exists():
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    return {
        "run_id": f"md1-seamgraph-sixgpu-{RUN_TS}",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "scope": "SfM-only latest seam_graph_sim3_v1 MD1 six-GPU timing and quality proof",
        "branch": BRANCH,
        "head": git_head(),
        "source_image_uri": SOURCE_IMAGE_URI,
        "input_uri": INPUT_URI,
        "output_root": OUTPUT_ROOT,
        "max_concurrency": MAX_CONCURRENCY,
        "instance_type": INSTANCE_TYPE,
        "quota": {
            "quota_code": "L-2F1EB012",
            "name": "ml.g4dn.xlarge for processing job usage",
            "value": 6,
            "increase_needed_for_requested_run": False,
        },
        "planner": {
            "job_name": f"md1-sg6-plan-1779812400",
            "output_uri": f"{OUTPUT_ROOT}/planner/colmap",
            "manifest_uri": f"{OUTPUT_ROOT}/planner/colmap/chunk_planner_manifest.json",
            "status": "not_launched",
        },
        "leaves": [],
        "reducer": {"status": "not_started"},
        "quality": {"status": "not_started"},
        "notes": [
            "No quota raise needed for six concurrent ml.g4dn.xlarge processing jobs; account quota is exactly six.",
            "Leaf jobs must not launch until planner manifest has global pose priors, >=20 core images per chunk, and jurisdiction data.",
        ],
    }


def save_status(status: dict[str, Any]) -> None:
    status["updated_at"] = utc_now()
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")


def processing_payload(
    *,
    job_name: str,
    output_uri: str,
    environment: dict[str, str],
) -> dict[str, Any]:
    env = {
        **environment,
        "SFM_BRANCH_NAME": BRANCH,
        "SFM_GIT_HEAD": git_head(),
        "SFM_INPUT_URI": INPUT_URI,
        "SFM_OUTPUT_URI": output_uri,
        "SFM_JOB_NAME": job_name,
    }
    return {
        "ProcessingJobName": job_name,
        "AppSpecification": {
            "ImageUri": SOURCE_IMAGE_URI,
            "ContainerEntrypoint": ["/opt/ml/code/run_sfm.sh"],
        },
        "ProcessingResources": {
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": INSTANCE_TYPE,
                "VolumeSizeInGB": VOLUME_SIZE_GB,
            }
        },
        "ProcessingInputs": [
            {
                "InputName": "sfm-input",
                "S3Input": {
                    "S3Uri": INPUT_URI,
                    "LocalPath": "/opt/ml/processing/input",
                    "S3DataType": "S3Prefix",
                    "S3InputMode": "File",
                    "S3DataDistributionType": "FullyReplicated",
                    "S3CompressionType": "None",
                },
            }
        ],
        "ProcessingOutputConfig": {
            "Outputs": [
                {
                    "OutputName": "colmap-output",
                    "S3Output": {
                        "S3Uri": output_uri,
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                    "AppManaged": False,
                }
            ]
        },
        "Environment": env,
        "Tags": [
            {"Key": "Project", "Value": "Spaceport"},
            {"Key": "Component", "Value": "SfM"},
            {"Key": "Branch", "Value": BRANCH},
            {"Key": "ProofRun", "Value": f"md1-seamgraph-sixgpu-{RUN_TS}"},
        ],
        "RoleArn": ROLE_ARN,
    }


def create_processing_job(payload: dict[str, Any]) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload_path = STATUS_PATH.parent / f"{payload['ProcessingJobName']}_create_payload.json"
    payload_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    run(
        [
            "aws",
            "sagemaker",
            "create-processing-job",
            "--cli-input-json",
            f"file://{payload_path}",
        ]
    )


def describe_job(job_name: str) -> dict[str, Any]:
    return aws_json("sagemaker", "describe-processing-job", "--processing-job-name", job_name)


def summarize_describe(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": raw.get("ProcessingJobStatus"),
        "failure_reason": raw.get("FailureReason", ""),
        "creation_time": str(raw.get("CreationTime", "")),
        "start_time": str(raw.get("ProcessingStartTime", "")),
        "end_time": str(raw.get("ProcessingEndTime", "")),
        "max_runtime_seconds": (
            (raw.get("StoppingCondition") or {}).get("MaxRuntimeInSeconds")
        ),
    }


def launch_planner(args: argparse.Namespace) -> None:
    status = load_status()
    planner = status["planner"]
    if planner.get("status") not in {"not_launched", ""}:
        print(json.dumps({"planner": planner, "already_launched": True}, indent=2))
        return
    payload = processing_payload(
        job_name=planner["job_name"],
        output_uri=planner["output_uri"],
        environment=PLANNER_ENV,
    )
    payload["StoppingCondition"] = {"MaxRuntimeInSeconds": args.max_runtime_seconds}
    create_processing_job(payload)
    planner.update({"status": "InProgress", "launched_at": utc_now()})
    save_status(status)
    print(json.dumps({"launched_planner": planner}, indent=2))


def poll_planner(_: argparse.Namespace) -> None:
    status = load_status()
    planner = status["planner"]
    raw = describe_job(planner["job_name"])
    planner.update(summarize_describe(raw))
    if planner["status"] == "Completed":
        validate_planner_manifest(status)
    save_status(status)
    print(json.dumps({"planner": planner}, indent=2))


def copy_s3_to_local(s3_uri: str, local_path: Path) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    run(["aws", "s3", "cp", s3_uri, str(local_path), "--only-show-errors"])


def validate_planner_manifest(status: dict[str, Any]) -> dict[str, Any]:
    planner = status["planner"]
    copy_s3_to_local(planner["manifest_uri"], LOCAL_MANIFEST_PATH)
    manifest = json.loads(LOCAL_MANIFEST_PATH.read_text(encoding="utf-8"))
    chunks = manifest.get("chunks") or []
    weak_core = [
        {
            "index": int(chunk.get("index", i)),
            "core": len(chunk.get("core_names") or []),
            "total": len(chunk.get("image_names") or []),
        }
        for i, chunk in enumerate(chunks)
        if len(chunk.get("core_names") or []) < 20
    ]
    jurisdictions = manifest.get("chunk_jurisdictions") or {}
    validation = {
        "checked_at": utc_now(),
        "manifest_local_path": str(LOCAL_MANIFEST_PATH),
        "planner": manifest.get("planner"),
        "pipeline_mode": manifest.get("pipeline_mode"),
        "chunk_count": len(chunks),
        "has_image_pose_priors_local": isinstance(manifest.get("image_pose_priors_local"), dict)
        and bool(manifest.get("image_pose_priors_local")),
        "image_pose_priors_local_count": len(manifest.get("image_pose_priors_local") or {}),
        "jurisdiction_count": len(jurisdictions),
        "weak_core_chunks": weak_core,
        "passes_leaf_fanout_contract": False,
        "blockers": [],
    }
    if manifest.get("planner") != "visibility_cell_v1":
        validation["blockers"].append("planner_not_visibility_cell_v1")
    if not validation["has_image_pose_priors_local"]:
        validation["blockers"].append("missing_image_pose_priors_local")
    if validation["jurisdiction_count"] != len(chunks):
        validation["blockers"].append("jurisdiction_count_mismatch")
    if weak_core:
        validation["blockers"].append("weak_core_chunks")
    validation["passes_leaf_fanout_contract"] = not validation["blockers"]
    planner["validation"] = validation
    if validation["passes_leaf_fanout_contract"] and not status.get("leaves"):
        output_root = status["output_root"].rstrip("/")
        status["leaves"] = [
            {
                "chunk_index": int(chunk.get("index", i)),
                "job_name": f"md1-sg6-l{int(chunk.get('index', i)):02d}-1779812400",
                "output_uri": f"{output_root}/leaves/leaf-{int(chunk.get('index', i)):02d}/colmap",
                "core_image_count": len(chunk.get("core_names") or []),
                "image_count": len(chunk.get("image_names") or []),
                "status": "not_launched",
            }
            for i, chunk in enumerate(chunks)
        ]
    return validation


def active_jobs(leaves: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        leaf
        for leaf in leaves
        if leaf.get("status") in {"InProgress", "Stopping", "Starting"}
    ]


def launch_leaves(args: argparse.Namespace) -> None:
    status = load_status()
    planner = status["planner"]
    if planner.get("status") != "Completed":
        raise SystemExit("planner must be Completed before launching leaves")
    validation = planner.get("validation") or validate_planner_manifest(status)
    if not validation.get("passes_leaf_fanout_contract"):
        save_status(status)
        raise SystemExit(f"planner contract failed: {validation.get('blockers')}")
    launched: list[str] = []
    leaves = status["leaves"]
    slots = max(0, int(args.max_concurrency) - len(active_jobs(leaves)))
    for leaf in leaves:
        if slots <= 0:
            break
        if leaf.get("status") != "not_launched":
            continue
        leaf_env = {
            **LEAF_ENV,
            "COLMAP_INPUT_CHUNK_PLANNER_MANIFEST_URI": planner["manifest_uri"],
            "COLMAP_ONLY_CHUNK_INDEXES": str(leaf["chunk_index"]),
            "SFM_BENCHMARK_SUBSET_STRATEGY": f"md1_sg6_leaf_{leaf['chunk_index']:02d}",
        }
        payload = processing_payload(
            job_name=leaf["job_name"],
            output_uri=leaf["output_uri"],
            environment=leaf_env,
        )
        payload["StoppingCondition"] = {"MaxRuntimeInSeconds": args.max_runtime_seconds}
        create_processing_job(payload)
        leaf.update({"status": "InProgress", "launched_at": utc_now()})
        launched.append(leaf["job_name"])
        slots -= 1
        time.sleep(max(0, args.create_sleep_seconds))
    save_status(status)
    print(json.dumps({"launched": launched, "active": [l["job_name"] for l in active_jobs(leaves)]}, indent=2))


def poll_leaves(_: argparse.Namespace) -> None:
    status = load_status()
    for leaf in status.get("leaves") or []:
        if leaf.get("status") in {"not_launched", "Completed", "Failed", "Stopped"}:
            continue
        try:
            raw = describe_job(leaf["job_name"])
        except subprocess.CalledProcessError as exc:
            leaf["describe_error"] = exc.stderr[-1000:]
            continue
        leaf.update(summarize_describe(raw))
    counts: dict[str, int] = {}
    for leaf in status.get("leaves") or []:
        counts[leaf.get("status", "unknown")] = counts.get(leaf.get("status", "unknown"), 0) + 1
    save_status(status)
    print(json.dumps({"leaf_status_counts": counts, "active": [l["job_name"] for l in active_jobs(status.get("leaves") or [])]}, indent=2))


def show_status(_: argparse.Namespace) -> None:
    print(json.dumps(load_status(), indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["init", "launch-planner", "poll-planner", "launch-leaves", "poll-leaves", "status"],
    )
    parser.add_argument("--max-concurrency", type=int, default=MAX_CONCURRENCY)
    parser.add_argument("--max-runtime-seconds", type=int, default=21600)
    parser.add_argument("--create-sleep-seconds", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "init":
        status = load_status()
        save_status(status)
        print(json.dumps(status, indent=2))
    elif args.command == "launch-planner":
        launch_planner(args)
    elif args.command == "poll-planner":
        poll_planner(args)
    elif args.command == "launch-leaves":
        launch_leaves(args)
    elif args.command == "poll-leaves":
        poll_leaves(args)
    elif args.command == "status":
        show_status(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
