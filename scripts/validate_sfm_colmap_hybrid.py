#!/usr/bin/env python3
"""Launch and monitor COLMAP hybrid SfM validation jobs on SageMaker."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


REGION = "us-west-2"
ACCOUNT_ID = "975050048887"
ROLE_ARN = (
    "arn:aws:iam::975050048887:role/"
    "SpaceportMLPipelineStack-SageMakerExecutionRole7843-A4BBnjJAXLs8"
)
ECR_REPO = f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/spaceport/sfm"
DEFAULT_OUTPUT_ROOT = "s3://spaceport-ml-processing-staging/colmap-validation"

PRESETS = {
    "smoke": {
        "input_uri": "s3://spaceport-uploads/1748664812459-5woqcu-Archive.zip",
        "instance_type": "ml.c6i.2xlarge",
        "max_runtime_seconds": 3600,
        "profile_override": "auto",
        "baseline_output_uri": None,
    },
    "mid": {
        "input_uri": "s3://spaceport-uploads/pipeline/full-dataset-20251203-190854/Archive.zip",
        "instance_type": "ml.c6i.4xlarge",
        "max_runtime_seconds": 5400,
        "profile_override": "auto",
        "baseline_output_uri": "s3://spaceport-ml-processing-staging/colmap/2e4049c9-de03-47f8-b895-251986ebb6dc/",
    },
    "full": {
        "input_uri": "s3://spaceport-uploads/1771003523-red-arrow-ranch-archive/Archive.zip",
        "instance_type": "ml.c6i.4xlarge",
        "max_runtime_seconds": 7200,
        "profile_override": "auto",
        "baseline_output_uri": "s3://spaceport-ml-processing-staging/colmap/cc6a2ad7-2dd4-4dc2-904b-8999738b6647/",
    },
}


def run_command(args: list[str], *, capture_output: bool = True) -> str:
    result = subprocess.run(
        args,
        check=True,
        text=True,
        capture_output=capture_output,
    )
    return result.stdout.strip() if capture_output else ""


def aws_json(*args: str) -> Dict[str, object]:
    output = run_command(["aws", *args])
    return json.loads(output) if output else {}


def branch_tag(branch: str) -> str:
    repo_root = Path(__file__).resolve().parent.parent
    output = run_command(
        [
            "python3",
            str(repo_root / "scripts" / "get_branch_suffix.py"),
            branch,
            "--mode",
            "ecr",
        ]
    )
    if not output:
        raise RuntimeError(f"Could not derive ECR branch tag for {branch!r}")
    return output


def parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Unsupported S3 URI: {uri}")
    bucket, _, key = uri[5:].partition("/")
    return bucket, key


def ensure_trailing_slash(uri: str) -> str:
    return uri if uri.endswith("/") else f"{uri}/"


def s3_exists(uri: str) -> bool:
    bucket, key = parse_s3_uri(uri)
    try:
        run_command(["aws", "s3", "ls", f"s3://{bucket}/{key}"])
        return True
    except subprocess.CalledProcessError:
        return False


def load_s3_json(uri: str) -> Optional[Dict[str, object]]:
    try:
        output = run_command(["aws", "s3", "cp", uri, "-"])
    except subprocess.CalledProcessError:
        return None
    return json.loads(output)


def iso8601_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def build_processing_job_request(
    *,
    job_name: str,
    image_uri: str,
    input_uri: str,
    output_uri: str,
    instance_type: str,
    max_runtime_seconds: int,
    sfm_only: bool,
    profile_override: str,
) -> Dict[str, object]:
    return {
        "ProcessingJobName": job_name,
        "RoleArn": ROLE_ARN,
        "AppSpecification": {
            "ImageUri": image_uri,
            "ContainerEntrypoint": ["/opt/ml/code/run_sfm.sh"],
        },
        "ProcessingResources": {
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": instance_type,
                "VolumeSizeInGB": 100,
            }
        },
        "ProcessingInputs": [
            {
                "InputName": "input-data",
                "AppManaged": False,
                "S3Input": {
                    "S3Uri": input_uri,
                    "LocalPath": "/opt/ml/processing/input",
                    "S3DataType": "S3Prefix",
                    "S3InputMode": "File",
                },
            }
        ],
        "ProcessingOutputConfig": {
            "Outputs": [
                {
                    "OutputName": "colmap-output",
                    "AppManaged": False,
                    "S3Output": {
                        "S3Uri": ensure_trailing_slash(output_uri),
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                }
            ]
        },
        "Environment": {
            "AWS_DEFAULT_REGION": REGION,
            "PYTHONUNBUFFERED": "1",
            "SPACEPORT_SFM_ONLY": "true" if sfm_only else "false",
            "SPACEPORT_SFM_PROFILE_OVERRIDE": profile_override,
            "SPACEPORT_SFM_INSTANCE_TYPE": instance_type,
        },
        "StoppingCondition": {"MaxRuntimeInSeconds": max_runtime_seconds},
        "Tags": [
            {"Key": "Project", "Value": "Spaceport"},
            {"Key": "Component", "Value": "SfM"},
            {"Key": "Validation", "Value": "colmap-hybrid"},
        ],
    }


def create_processing_job(request: Dict[str, object]) -> Dict[str, object]:
    return aws_json(
        "sagemaker",
        "create-processing-job",
        "--cli-input-json",
        json.dumps(request),
        "--region",
        REGION,
    )


def describe_processing_job(job_name: str) -> Dict[str, object]:
    return aws_json(
        "sagemaker",
        "describe-processing-job",
        "--processing-job-name",
        job_name,
        "--region",
        REGION,
    )


def wait_for_processing_job(job_name: str, poll_seconds: int) -> Dict[str, object]:
    while True:
        description = describe_processing_job(job_name)
        status = description["ProcessingJobStatus"]
        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"{job_name}: {status}",
            flush=True,
        )
        if status in {"Completed", "Failed", "Stopped", "Stopping"}:
            return description
        time.sleep(poll_seconds)


def compare_metrics(
    baseline: Optional[Dict[str, object]],
    candidate: Optional[Dict[str, object]],
) -> Dict[str, Dict[str, object]]:
    keys = [
        "processing_time_seconds",
        "images_registered",
        "cameras_registered",
        "points_3d",
        "mean_observations_per_image",
        "mean_track_length",
        "mean_reprojection_error",
    ]
    comparison: Dict[str, Dict[str, object]] = {}
    if not baseline or not candidate:
        return comparison

    for key in keys:
        baseline_value = baseline.get(key)
        candidate_value = candidate.get(key)
        if baseline_value is None or candidate_value is None:
            continue
        delta = None
        if isinstance(baseline_value, (int, float)) and isinstance(candidate_value, (int, float)):
            delta = candidate_value - baseline_value
        comparison[key] = {
            "baseline": baseline_value,
            "candidate": candidate_value,
            "delta": delta,
        }
    return comparison


def summarize(
    *,
    job_name: str,
    image_uri: str,
    output_uri: str,
    description: Dict[str, object],
    metadata: Optional[Dict[str, object]],
    cost_report: Optional[Dict[str, object]],
    baseline_metadata: Optional[Dict[str, object]],
) -> Dict[str, object]:
    summary = {
        "job_name": job_name,
        "processing_job_arn": description.get("ProcessingJobArn"),
        "image_uri": image_uri,
        "output_uri": ensure_trailing_slash(output_uri),
        "status": description.get("ProcessingJobStatus"),
        "failure_reason": description.get("FailureReason"),
        "log_group": "/aws/sagemaker/ProcessingJobs",
        "metadata": metadata,
        "cost_report": cost_report,
        "baseline_comparison": compare_metrics(baseline_metadata, metadata),
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", choices=sorted(PRESETS), default="smoke")
    parser.add_argument("--branch", default="agent-68423157-sfm-colmap-hybrid")
    parser.add_argument("--job-name")
    parser.add_argument("--input-uri")
    parser.add_argument("--output-uri")
    parser.add_argument("--instance-type")
    parser.add_argument("--profile-override")
    parser.add_argument("--baseline-output-uri")
    parser.add_argument("--max-runtime-seconds", type=int)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--sfm-only", action="store_true", default=True)
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument("--summary-file")
    args = parser.parse_args()

    preset = PRESETS[args.preset]
    branch = args.branch
    tag = branch_tag(branch)
    image_uri = f"{ECR_REPO}:{tag}"
    input_uri = args.input_uri or preset["input_uri"]
    instance_type = args.instance_type or preset["instance_type"]
    max_runtime_seconds = args.max_runtime_seconds or preset["max_runtime_seconds"]
    profile_override = args.profile_override or preset["profile_override"]
    baseline_output_uri = args.baseline_output_uri or preset["baseline_output_uri"]
    job_name = args.job_name or f"sfm-{args.preset}-{iso8601_now()}"
    output_uri = args.output_uri or f"{DEFAULT_OUTPUT_ROOT}/{args.preset}/{job_name}/"

    if not s3_exists(input_uri):
        raise RuntimeError(f"Input S3 object or prefix does not exist: {input_uri}")

    request = build_processing_job_request(
        job_name=job_name,
        image_uri=image_uri,
        input_uri=input_uri,
        output_uri=output_uri,
        instance_type=instance_type,
        max_runtime_seconds=max_runtime_seconds,
        sfm_only=args.sfm_only,
        profile_override=profile_override,
    )

    print(f"JOB_NAME={job_name}")
    print(f"IMAGE_URI={image_uri}")
    print(f"INPUT_URI={input_uri}")
    print(f"OUTPUT_URI={ensure_trailing_slash(output_uri)}")
    print(f"INSTANCE_TYPE={instance_type}")
    print(f"PROFILE_OVERRIDE={profile_override}")
    print(f"BASELINE_OUTPUT_URI={baseline_output_uri or '<none>'}")
    print("Creating SageMaker processing job...", flush=True)
    create_processing_job(request)

    description = describe_processing_job(job_name)
    if args.no_wait:
        print(json.dumps({"job_name": job_name, "output_uri": ensure_trailing_slash(output_uri)}, indent=2))
        return 0

    description = wait_for_processing_job(job_name, args.poll_seconds)
    metadata = load_s3_json(f"{ensure_trailing_slash(output_uri)}sfm_metadata.json")
    cost_report = load_s3_json(f"{ensure_trailing_slash(output_uri)}cost_report.json")
    baseline_metadata = (
        load_s3_json(f"{ensure_trailing_slash(baseline_output_uri)}sfm_metadata.json")
        if baseline_output_uri
        else None
    )
    summary = summarize(
        job_name=job_name,
        image_uri=image_uri,
        output_uri=output_uri,
        description=description,
        metadata=metadata,
        cost_report=cost_report,
        baseline_metadata=baseline_metadata,
    )

    if args.summary_file:
        Path(args.summary_file).write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))

    if description["ProcessingJobStatus"] != "Completed":
        return 1
    if metadata is None:
        print("Missing sfm_metadata.json in output prefix.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
