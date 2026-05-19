#!/usr/bin/env python3
"""Monitor CV-HR upload and run the Montana-era training stack.

This runner intentionally launches SageMaker jobs directly instead of using the
current Step Functions stack. The historical Montana SfM jobs depended on
container environment variables that the deployed state machine does not pass
through.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
ACCOUNT_ID = "975050048887"
REGION = "us-west-2"
ML_BUCKET = "spaceport-ml-processing-staging"
UPLOAD_BUCKET = "spaceport-uploads-staging"
SAGEMAKER_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/Spaceport-SageMaker-Role-staging"

MONTANA_3DGS_IMAGE = (
    f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/spaceport/3dgs"
    "@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db"
)
MONTANA_COMPRESSOR_IMAGE = (
    f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/spaceport/compressor"
    "@sha256:a0784727da1870ce9caa4774dc831a32fb96cd1574df389cf9093fbf18f4f4ab"
)


@dataclass(frozen=True)
class StackProfile:
    name: str
    sfm_image: str
    sfm_environment: dict[str, str]
    note: str


PROFILES: dict[str, StackProfile] = {
    "brass-chunked": StackProfile(
        name="brass-chunked",
        sfm_image=(
            f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/spaceport/sfm"
            "@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811"
        ),
        sfm_environment={
            "COLMAP_ENABLE_SPATIAL_CHUNKING": "1",
            "COLMAP_CHUNK_MIN_CORE_REGISTERED_RATIO": "0.90",
        },
        note="Exact Brass Lantern chunked SfM image; default reproducible Montana profile.",
    ),
    "horsetail-gps": StackProfile(
        name="horsetail-gps",
        sfm_image=(
            f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/spaceport/sfm"
            "@sha256:a7e2553455ad8ca7988256f4b0d38395e1770b2522532c41c6f535fc8a49f157"
        ),
        sfm_environment={
            "COLMAP_ENABLE_SEQUENTIAL_MATCHER": "1",
            "COLMAP_FORCE_GPS_FIRST": "1",
            "COLMAP_MATCH_PROFILE": "P1",
            "COLMAP_SIFT_MAX_NUM_FEATURES": "9216",
        },
        note="Exact Horsetail GPS-prior SfM image; fallback if chunked profile fails.",
    ),
    "meadow-tag-only": StackProfile(
        name="meadow-tag-only",
        sfm_image=(
            f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/spaceport/sfm:"
            "agent70148362investigatesfmrecovery"
        ),
        sfm_environment={"COLMAP_ENABLE_SPATIAL_CHUNKING": "1"},
        note=(
            "Meadow SfM tag recorded by SageMaker, but the exact runtime digest is not "
            "time-safe. Use only for forensics, not exact reproduction."
        ),
    ),
}


MONTANA_3DGS_ENV: dict[str, str] = {
    "AWS_DEFAULT_REGION": REGION,
    "PYTHONUNBUFFERED": "1",
    "SAGEMAKER_PROGRAM": "train.py",
    "MAX_ITERATIONS": "30000",
    "TARGET_PSNR": "35.0",
    "MODEL_VARIANT": "splatfacto-w-light",
    "SH_DEGREE": "3",
    "BILATERAL_PROCESSING": "false",
    "LOG_INTERVAL": "100",
    "RASTERIZE_MODE": "classic",
    "USE_SCALE_REGULARIZATION": "true",
    "CULL_ALPHA_THRESH": "0.12",
    "CULL_SCALE_THRESH": "0.35",
    "ENABLE_BG_MODEL": "true",
    "ENABLE_ALPHA_LOSS": "true",
    "ENABLE_ROBUST_MASK": "true",
    "BG_SH_DEGREE": "8",
    "APPEARANCE_EMBED_DIM": "64",
    "NEVER_MASK_UPPER": "0.4",
    "BACKGROUND_APPEARANCE_MODE": "auto_camera",
    "BACKGROUND_SKYBOX_WIDTH": "2048",
    "BACKGROUND_SKYBOX_HEIGHT": "1024",
    "BACKGROUND_SKYBOX_QUALITY": "95",
    "BACKGROUND_SELECTION_STRIDE": "5",
    "BACKGROUND_SELECTION_MAX_FRAMES": "32",
    "FLOATER_PRUNING_ENABLED": "true",
    "FLOATER_PRUNING_MIN_VIEWS": "6",
    "FLOATER_PRUNING_TOP_REGION_RATIO": "0.35",
    "FLOATER_PRUNING_TOP_VIEW_FRACTION": "0.9",
    "FLOATER_PRUNING_MIN_SKY_VIEWS": "2",
    "FLOATER_PRUNING_SKY_MIN_LUMINANCE": "0.3",
    "FLOATER_PRUNING_SKY_MIN_SATURATION": "0.08",
    "FLOATER_PRUNING_SKY_BLUE_DOMINANCE_MARGIN": "0.02",
    "FLOATER_PRUNING_MAX_OPACITY": "0.75",
    "FLOATER_PRUNING_MAX_COLOR_DISTANCE": "0.18",
    "FLOATER_PRUNING_MIN_EDGE_SUPPORT": "1",
    "TRAINING_TIMEOUT_SECONDS": "14400",
    "FRAMEWORK": "nerfstudio",
    "METHODOLOGY": "spaceport_splatfacto_w_light_skybox",
    "LICENSE": "apache_2_0",
    "COMMERCIAL_LICENSE": "true",
    "OUTPUT_FORMAT": "ply",
    "SOGS_COMPATIBLE": "true",
    "MAX_NUM_GAUSSIANS": "1500000",
    "MEMORY_OPTIMIZATION": "true",
    "TORCH_CUDA_ARCH_LIST": "8.0 8.6",
    "CUDA_HOME": "/usr/local/cuda",
    "LD_LIBRARY_PATH": "/usr/local/cuda/lib64:/usr/local/cuda/lib",
    "LIBRARY_PATH": "/usr/local/cuda/lib64:/usr/local/cuda/lib",
}


IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".dng")


class AwsCliPaginator:
    def __init__(self, client: "AwsCliClient", operation: str):
        self.client = client
        self.operation = operation

    def paginate(self, **kwargs: Any):
        if self.operation != "list_objects_v2":
            raise NotImplementedError(self.operation)
        token = ""
        while True:
            args = [
                "s3api",
                "list-objects-v2",
                "--bucket",
                kwargs["Bucket"],
                "--prefix",
                kwargs.get("Prefix", ""),
                "--max-keys",
                "1000",
            ]
            if token:
                args.extend(["--continuation-token", token])
            page = self.client.run_json(args)
            yield page
            token = page.get("NextContinuationToken", "")
            if not token:
                break


class AwsCliClient:
    def __init__(self, service: str, region_name: str):
        self.service = service
        self.region_name = region_name

    def run_json(self, args: list[str]) -> dict[str, Any]:
        env = {**os.environ, "AWS_PAGER": ""}
        result = subprocess.run(
            ["aws", *args, "--region", self.region_name, "--output", "json"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        return json.loads(result.stdout or "{}")

    def get_paginator(self, operation: str) -> AwsCliPaginator:
        return AwsCliPaginator(self, operation)

    def get_object(self, *, Bucket: str, Key: str, Range: str) -> dict[str, Any]:  # noqa: N803 - boto3 shape
        with tempfile.NamedTemporaryFile() as output:
            metadata = self.run_json(
                [
                    "s3api",
                    "get-object",
                    "--bucket",
                    Bucket,
                    "--key",
                    Key,
                    "--range",
                    Range,
                    output.name,
                ]
            )
            output.seek(0)
            return {**metadata, "Body": io.BytesIO(output.read())}

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:  # noqa: N803 - boto3 shape
        return self.run_json(["s3api", "head-object", "--bucket", Bucket, "--key", Key])

    def create_processing_job(self, **payload: Any) -> dict[str, Any]:
        with tempfile.NamedTemporaryFile("w", suffix=".json") as payload_file:
            json.dump(payload, payload_file)
            payload_file.flush()
            return self.run_json(
                ["sagemaker", "create-processing-job", "--cli-input-json", f"file://{payload_file.name}"]
            )

    def create_training_job(self, **payload: Any) -> dict[str, Any]:
        with tempfile.NamedTemporaryFile("w", suffix=".json") as payload_file:
            json.dump(payload, payload_file)
            payload_file.flush()
            return self.run_json(["sagemaker", "create-training-job", "--cli-input-json", f"file://{payload_file.name}"])

    def describe_processing_job(self, *, ProcessingJobName: str) -> dict[str, Any]:  # noqa: N803 - boto3 shape
        return self.run_json(["sagemaker", "describe-processing-job", "--processing-job-name", ProcessingJobName])

    def describe_training_job(self, *, TrainingJobName: str) -> dict[str, Any]:  # noqa: N803 - boto3 shape
        return self.run_json(["sagemaker", "describe-training-job", "--training-job-name", TrainingJobName])


def aws_client(service: str, *, region_name: str) -> Any:
    try:
        import boto3
    except ModuleNotFoundError:
        return AwsCliClient(service, region_name)
    return boto3.client(service, region_name=region_name)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_id_now() -> str:
    return datetime.now(timezone.utc).strftime("cvhr-mtc-%Y%m%dT%H%MZ")


def git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def s3_uri(bucket: str, key: str) -> str:
    return f"s3://{bucket}/{key}"


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = utc_now()
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def s3_range(s3: Any, bucket: str, key: str, start: int, end: int) -> bytes:
    response = s3.get_object(Bucket=bucket, Key=key, Range=f"bytes={start}-{end}")
    return response["Body"].read()


def parse_zip_image_count(s3: Any, *, bucket: str, key: str, size: int) -> dict[str, Any]:
    if size < 22:
        raise ValueError("object is too small to be a ZIP archive")
    tail_size = min(size, 65557)
    tail_start = size - tail_size
    tail = s3_range(s3, bucket, key, tail_start, size - 1)
    eocd_index = tail.rfind(b"PK\x05\x06")
    if eocd_index < 0:
        raise ValueError("ZIP end-of-central-directory was not found; upload may be incomplete")

    eocd = tail[eocd_index : eocd_index + 22]
    if len(eocd) < 22:
        raise ValueError("truncated ZIP end-of-central-directory")
    total_entries = struct.unpack_from("<H", eocd, 10)[0]
    central_dir_size = struct.unpack_from("<I", eocd, 12)[0]
    central_dir_offset = struct.unpack_from("<I", eocd, 16)[0]

    if total_entries == 0xFFFF or central_dir_size == 0xFFFFFFFF or central_dir_offset == 0xFFFFFFFF:
        locator_index = tail.rfind(b"PK\x06\x07", 0, eocd_index)
        if locator_index < 0:
            raise ValueError("ZIP64 locator was not found")
        locator = tail[locator_index : locator_index + 20]
        zip64_eocd_offset = struct.unpack_from("<Q", locator, 8)[0]
        zip64 = s3_range(s3, bucket, key, zip64_eocd_offset, zip64_eocd_offset + 72)
        if not zip64.startswith(b"PK\x06\x06"):
            raise ValueError("ZIP64 end-of-central-directory was not found")
        total_entries = struct.unpack_from("<Q", zip64, 32)[0]
        central_dir_size = struct.unpack_from("<Q", zip64, 40)[0]
        central_dir_offset = struct.unpack_from("<Q", zip64, 48)[0]

    if central_dir_size > 64 * 1024 * 1024:
        raise ValueError(f"central directory is unexpectedly large: {central_dir_size} bytes")
    central_dir = s3_range(
        s3,
        bucket,
        key,
        int(central_dir_offset),
        int(central_dir_offset + central_dir_size - 1),
    )
    offset = 0
    filenames: list[str] = []
    while offset + 46 <= len(central_dir):
        if central_dir[offset : offset + 4] != b"PK\x01\x02":
            raise ValueError(f"invalid central directory signature at offset {offset}")
        name_len = struct.unpack_from("<H", central_dir, offset + 28)[0]
        extra_len = struct.unpack_from("<H", central_dir, offset + 30)[0]
        comment_len = struct.unpack_from("<H", central_dir, offset + 32)[0]
        name_start = offset + 46
        name_end = name_start + name_len
        raw_name = central_dir[name_start:name_end]
        filenames.append(raw_name.decode("utf-8", errors="replace"))
        offset = name_end + extra_len + comment_len

    image_names = [name for name in filenames if name.lower().endswith(IMAGE_EXTENSIONS)]
    return {
        "zip_entries": int(total_entries),
        "central_directory_entries": len(filenames),
        "image_count": len(image_names),
        "first_images": image_names[:5],
        "last_images": image_names[-5:],
    }


def candidate_objects(
    s3: Any,
    *,
    bucket: str,
    prefixes: list[str],
    max_scan_objects: int,
) -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    wanted = {"cvhr", "cvhrupload", "cvhrphotos"}
    for prefix in prefixes:
        paginator = s3.get_paginator("list_objects_v2")
        scanned = 0
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                scanned += 1
                key = item["Key"]
                normalized = normalize_key(key)
                if key.lower().endswith(".zip") and any(token in normalized for token in wanted):
                    candidates[key] = item
                if scanned >= max_scan_objects:
                    break
            if scanned >= max_scan_objects:
                break
    return sorted(candidates.values(), key=lambda item: item["LastModified"], reverse=True)


def find_ready_upload(args: argparse.Namespace, s3: Any) -> dict[str, Any] | None:
    if args.input_s3_uri:
        match = re.match(r"^s3://([^/]+)/(.+)$", args.input_s3_uri)
        if not match:
            raise ValueError("--input-s3-uri must be an s3:// URI")
        bucket, key = match.groups()
        head = s3.head_object(Bucket=bucket, Key=key)
        item = {
            "Bucket": bucket,
            "Key": key,
            "Size": head["ContentLength"],
            "ETag": head.get("ETag", "").strip('"'),
            "LastModified": head["LastModified"],
        }
        candidates = [item]
    else:
        candidates = candidate_objects(
            s3,
            bucket=args.upload_bucket,
            prefixes=args.search_prefix,
            max_scan_objects=args.max_scan_objects,
        )
        for item in candidates:
            item["Bucket"] = args.upload_bucket
            item["ETag"] = item.get("ETag", "").strip('"')

    checked: list[dict[str, Any]] = []
    for item in candidates:
        try:
            zip_summary = parse_zip_image_count(
                s3,
                bucket=item["Bucket"],
                key=item["Key"],
                size=int(item["Size"]),
            )
        except Exception as exc:  # upload may still be in progress
            checked.append(
                {
                    "s3_uri": s3_uri(item["Bucket"], item["Key"]),
                    "size": item["Size"],
                    "etag": item.get("ETag", ""),
                    "ready": False,
                    "reason": str(exc),
                }
            )
            continue
        ready = zip_summary["image_count"] == args.expected_image_count
        checked.append(
            {
                "s3_uri": s3_uri(item["Bucket"], item["Key"]),
                "size": item["Size"],
                "etag": item.get("ETag", ""),
                "ready": ready,
                **zip_summary,
            }
        )
        if ready:
            return checked[-1]

    return {"ready": False, "checked": checked}


def create_sfm_job(
    sm: Any,
    *,
    state: dict[str, Any],
    args: argparse.Namespace,
    profile: StackProfile,
) -> None:
    branch = git_value("rev-parse", "--abbrev-ref", "HEAD")
    head = git_value("rev-parse", "HEAD")
    run_id = state["run_id"]
    job_name = f"{run_id}-sfm"
    output_uri = f"s3://{ML_BUCKET}/manual-validations/{run_id}/colmap"
    environment = {
        "AWS_DEFAULT_REGION": REGION,
        "PYTHONUNBUFFERED": "1",
        "SFM_BENCHMARK_SUBSET_STRATEGY": "cv_hr_full_1710_montana_time_capsule",
        "SFM_BRANCH_NAME": branch,
        "SFM_GIT_HEAD": head,
        "SFM_INPUT_URI": state["input_s3_uri"],
        "SFM_OUTPUT_URI": output_uri,
        "SFM_JOB_NAME": job_name,
        **profile.sfm_environment,
    }
    payload = {
        "ProcessingJobName": job_name,
        "AppSpecification": {
            "ImageUri": profile.sfm_image,
            "ContainerEntrypoint": ["/opt/ml/code/run_sfm.sh"],
        },
        "ProcessingResources": {
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": args.sfm_instance_type,
                "VolumeSizeInGB": args.sfm_volume_size_gb,
            }
        },
        "ProcessingInputs": [
            {
                "InputName": "sfm-input",
                "S3Input": {
                    "S3Uri": state["input_s3_uri"],
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
                    "AppManaged": False,
                    "S3Output": {
                        "S3Uri": output_uri,
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                }
            ]
        },
        "Environment": environment,
        "StoppingCondition": {"MaxRuntimeInSeconds": args.sfm_max_runtime_seconds},
        "Tags": [
            {"Key": "Project", "Value": "Spaceport"},
            {"Key": "Component", "Value": "SfM"},
            {"Key": "Profile", "Value": "montana-time-capsule"},
            {"Key": "Dataset", "Value": "CV-HR"},
        ],
        "RoleArn": args.role_arn,
    }
    sm.create_processing_job(**payload)
    state.update(
        {
            "sfm_job_name": job_name,
            "sfm_output_s3_uri": output_uri,
            "sfm_image_uri": profile.sfm_image,
            "sfm_environment": environment,
            "status": "sfm_started",
            "sfm_payload": payload,
        }
    )


def create_3dgs_job(sm: Any, *, state: dict[str, Any], args: argparse.Namespace) -> None:
    run_id = state["run_id"]
    job_name = f"{run_id}-3dgs"
    output_uri = f"s3://{ML_BUCKET}/3dgs/{run_id}/"
    payload = {
        "TrainingJobName": job_name,
        "AlgorithmSpecification": {
            "TrainingImage": MONTANA_3DGS_IMAGE,
            "TrainingInputMode": "File",
        },
        "InputDataConfig": [
            {
                "ChannelName": "training",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": state["sfm_output_s3_uri"],
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
            }
        ],
        "OutputDataConfig": {"S3OutputPath": output_uri},
        "ResourceConfig": {
            "InstanceCount": 1,
            "InstanceType": args.gaussian_instance_type,
            "VolumeSizeInGB": args.gaussian_volume_size_gb,
        },
        "StoppingCondition": {"MaxRuntimeInSeconds": args.gaussian_max_runtime_seconds},
        "RoleArn": args.role_arn,
        "Tags": [
            {"Key": "Project", "Value": "Spaceport"},
            {"Key": "Component", "Value": "3DGS"},
            {"Key": "Profile", "Value": "montana-time-capsule"},
            {"Key": "Dataset", "Value": "CV-HR"},
        ],
        "Environment": MONTANA_3DGS_ENV,
    }
    sm.create_training_job(**payload)
    state.update(
        {
            "3dgs_job_name": job_name,
            "gaussian_output_s3_uri": output_uri,
            "gaussian_model_artifact_s3_uri": f"{output_uri}{job_name}/output/model.tar.gz",
            "3dgs_image_uri": MONTANA_3DGS_IMAGE,
            "3dgs_environment": MONTANA_3DGS_ENV,
            "status": "3dgs_started",
            "3dgs_payload": payload,
        }
    )


def create_compression_job(sm: Any, *, state: dict[str, Any], args: argparse.Namespace) -> None:
    run_id = state["run_id"]
    job_name = f"{run_id}-compression"
    output_uri = f"s3://{ML_BUCKET}/compressed/{run_id}/"
    payload = {
        "ProcessingJobName": job_name,
        "AppSpecification": {
            "ImageUri": MONTANA_COMPRESSOR_IMAGE,
            "ContainerEntrypoint": ["python3", "compress.py"],
        },
        "ProcessingResources": {
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": args.compression_instance_type,
                "VolumeSizeInGB": args.compression_volume_size_gb,
            }
        },
        "ProcessingInputs": [
            {
                "InputName": "gaussian-model",
                "AppManaged": False,
                "S3Input": {
                    "S3Uri": state["gaussian_model_artifact_s3_uri"],
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
                    "OutputName": "compressed-model",
                    "AppManaged": False,
                    "S3Output": {
                        "S3Uri": output_uri,
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                }
            ]
        },
        "Environment": {"AWS_DEFAULT_REGION": REGION, "PYTHONUNBUFFERED": "1"},
        "StoppingCondition": {"MaxRuntimeInSeconds": args.compression_max_runtime_seconds},
        "Tags": [
            {"Key": "Project", "Value": "Spaceport"},
            {"Key": "Component", "Value": "Compression"},
            {"Key": "Profile", "Value": "montana-time-capsule"},
            {"Key": "Dataset", "Value": "CV-HR"},
        ],
        "RoleArn": args.role_arn,
    }
    sm.create_processing_job(**payload)
    state.update(
        {
            "compression_job_name": job_name,
            "compressed_output_s3_uri": output_uri,
            "compressor_image_uri": MONTANA_COMPRESSOR_IMAGE,
            "status": "compression_started",
            "compression_payload": payload,
        }
    )


def processing_status(sm: Any, name: str) -> str:
    return sm.describe_processing_job(ProcessingJobName=name)["ProcessingJobStatus"]


def training_status(sm: Any, name: str) -> str:
    return sm.describe_training_job(TrainingJobName=name)["TrainingJobStatus"]


def advance_pipeline(args: argparse.Namespace, state: dict[str, Any], profile: StackProfile) -> str:
    sm = aws_client("sagemaker", region_name=args.region)
    if "sfm_job_name" not in state:
        if args.launch:
            create_sfm_job(sm, state=state, args=args, profile=profile)
            return "launched_sfm"
        return "ready_to_launch_sfm"

    if state.get("sfm_output_verified"):
        sfm_status = "Completed"
    else:
        sfm_status = processing_status(sm, state["sfm_job_name"])
    state["sfm_status"] = sfm_status
    if sfm_status in {"Failed", "Stopped"}:
        state["status"] = "sfm_failed"
        return "sfm_failed"
    if sfm_status != "Completed":
        state["status"] = "sfm_running"
        return "sfm_running"

    if "3dgs_job_name" not in state:
        if args.launch:
            create_3dgs_job(sm, state=state, args=args)
            return "launched_3dgs"
        state["status"] = "ready_for_3dgs"
        return "ready_to_launch_3dgs"

    gs_status = training_status(sm, state["3dgs_job_name"])
    state["3dgs_status"] = gs_status
    if gs_status in {"Failed", "Stopped"}:
        state["status"] = "3dgs_failed"
        return "3dgs_failed"
    if gs_status != "Completed":
        state["status"] = "3dgs_running"
        return "3dgs_running"

    if "compression_job_name" not in state:
        if args.launch:
            create_compression_job(sm, state=state, args=args)
            return "launched_compression"
        state["status"] = "ready_for_compression"
        return "ready_to_launch_compression"

    compression_status = processing_status(sm, state["compression_job_name"])
    state["compression_status"] = compression_status
    if compression_status in {"Failed", "Stopped"}:
        state["status"] = "compression_failed"
        return "compression_failed"
    if compression_status != "Completed":
        state["status"] = "compression_running"
        return "compression_running"

    state["status"] = "completed"
    state["viewer_bundle_s3_uri"] = f"{state['compressed_output_s3_uri'].rstrip('/')}/supersplat_bundle/meta.json"
    return "completed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--launch", action="store_true", help="Create the next SageMaker job when ready.")
    parser.add_argument("--input-s3-uri", default=os.environ.get("CV_HR_INPUT_S3_URI", ""))
    parser.add_argument("--upload-bucket", default=UPLOAD_BUCKET)
    parser.add_argument(
        "--search-prefix",
        action="append",
        default=["CV-HR", "cv-hr", "cv_hr", "cvhr"],
        help="Repeatable S3 prefix to scan for the CV-HR zip.",
    )
    parser.add_argument("--max-scan-objects", type=int, default=5000)
    parser.add_argument("--expected-image-count", type=int, default=1710)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="brass-chunked")
    parser.add_argument("--state-file", default="logs/montana-time-capsule/cv-hr-state.json")
    parser.add_argument("--region", default=REGION)
    parser.add_argument("--role-arn", default=SAGEMAKER_ROLE_ARN)
    parser.add_argument("--sfm-instance-type", default="ml.g4dn.xlarge")
    parser.add_argument("--sfm-volume-size-gb", type=int, default=100)
    parser.add_argument("--sfm-max-runtime-seconds", type=int, default=86400)
    parser.add_argument("--gaussian-instance-type", default="ml.g5.2xlarge")
    parser.add_argument("--gaussian-volume-size-gb", type=int, default=100)
    parser.add_argument("--gaussian-max-runtime-seconds", type=int, default=14400)
    parser.add_argument("--compression-instance-type", default="ml.g4dn.xlarge")
    parser.add_argument("--compression-volume-size-gb", type=int, default=50)
    parser.add_argument("--compression-max-runtime-seconds", type=int, default=86400)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state_path = Path(args.state_file)
    profile = PROFILES[args.profile]
    s3 = aws_client("s3", region_name=args.region)
    state = load_state(state_path)

    if not state.get("input_s3_uri"):
        upload = find_ready_upload(args, s3)
        if not upload or not upload.get("ready"):
            result = {
                "status": "waiting_for_upload",
                "profile": profile.name,
                "profile_note": profile.note,
                "checked": upload.get("checked", []) if isinstance(upload, dict) else [],
                "expected_image_count": args.expected_image_count,
                "updated_at": utc_now(),
            }
            save_state(state_path, result)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        state = {
            "status": "upload_ready",
            "run_id": run_id_now(),
            "dataset": "CV-HR",
            "profile": profile.name,
            "profile_note": profile.note,
            "input_s3_uri": upload["s3_uri"],
            "input_size_bytes": upload["size"],
            "input_etag": upload["etag"],
            "input_image_count": upload["image_count"],
            "zip_entries": upload["zip_entries"],
            "first_images": upload["first_images"],
            "last_images": upload["last_images"],
            "created_at": utc_now(),
        }

    action = advance_pipeline(args, state, profile)
    state["last_action"] = action
    save_state(state_path, state)
    print(json.dumps(state, indent=2, sort_keys=True))
    if action.endswith("_failed"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
