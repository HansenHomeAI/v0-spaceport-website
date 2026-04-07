#!/usr/bin/env python3
"""Launch a direct SageMaker SfM benchmark job against the current branch stack."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List


REPO_ROOT = Path(__file__).resolve().parents[2]


def run_command(command: List[str], *, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        capture_output=capture_output,
    )


def aws_json(*args: str) -> dict:
    result = run_command(["aws", *args, "--output", "json"], capture_output=True)
    return json.loads(result.stdout)


def get_current_branch() -> str:
    result = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True)
    return result.stdout.strip()


def get_branch_ecr_tag(branch_name: str) -> str:
    result = run_command(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "get_branch_suffix.py"),
            branch_name,
            "--mode",
            "ecr",
        ],
        capture_output=True,
    )
    return result.stdout.strip()


def stack_outputs(stack: dict) -> Dict[str, str]:
    outputs = {}
    for entry in stack.get("Outputs", []):
        outputs[entry["OutputKey"]] = entry["OutputValue"]
    return outputs


def find_branch_ml_stack(branch_name: str) -> tuple[str, Dict[str, str]]:
    response = aws_json("cloudformation", "describe-stacks")
    for stack in response.get("Stacks", []):
        outputs = stack_outputs(stack)
        if outputs.get("BranchName") != branch_name:
            continue
        if "MLBucketName" not in outputs or "SfMRepositoryUri" not in outputs:
            continue
        return stack["StackName"], outputs
    raise RuntimeError(f"Could not find an ML stack deployment for branch {branch_name}")


def get_sagemaker_role_arn(stack_name: str) -> str:
    resources = aws_json("cloudformation", "list-stack-resources", "--stack-name", stack_name)
    for resource in resources.get("StackResourceSummaries", []):
        logical_id = resource.get("LogicalResourceId", "")
        physical_id = resource.get("PhysicalResourceId", "")
        if not (
            logical_id.startswith("SageMakerExecutionRole")
            or physical_id.startswith("Spaceport-SageMaker-Role-")
        ):
            continue
        role_name = physical_id
        role = aws_json("iam", "get-role", "--role-name", role_name)
        return role["Role"]["Arn"]
    raise RuntimeError(f"Could not resolve SageMakerExecutionRole from stack {stack_name}")


def load_s3_json(s3_uri: str) -> dict | None:
    try:
        result = run_command(["aws", "s3", "cp", s3_uri, "-"], capture_output=True)
    except subprocess.CalledProcessError:
        return None
    return json.loads(result.stdout)


def parse_env(values: List[str]) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Environment override must look like KEY=VALUE: {value}")
        key, raw_value = value.split("=", 1)
        env[key] = raw_value
    return env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch", default="", help="Git branch to benchmark. Defaults to current branch.")
    parser.add_argument("--input-s3-uri", required=True, help="S3 URI for the SfM input ZIP")
    parser.add_argument(
        "--output-s3-uri",
        default="",
        help="S3 URI prefix for outputs. Defaults to the branch ML bucket manual-validations prefix.",
    )
    parser.add_argument("--job-prefix", default="sfm-bench", help="Processing job name prefix")
    parser.add_argument("--instance-type", default="ml.g4dn.xlarge")
    parser.add_argument("--volume-size-gb", default="100")
    parser.add_argument(
        "--image-tag",
        default="",
        help="Override the ECR image tag. Defaults to the current branch tag.",
    )
    parser.add_argument(
        "--image-uri",
        default="",
        help="Fully qualified ECR image URI override. Takes precedence over --image-tag.",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        help="Repeatable KEY=VALUE environment overrides for the container",
    )
    parser.add_argument(
        "--mode",
        choices=["monolithic", "chunked"],
        default="monolithic",
        help="Benchmark the current monolithic path or the spatial-heading chunked path.",
    )
    parser.add_argument(
        "--subset-strategy",
        default="first_portion_by_exif_datetime_else_filename",
        help="Benchmark subset strategy label written into container metadata.",
    )
    parser.add_argument(
        "--summary-json-output",
        default="",
        help="Optional local path for the compact benchmark summary JSON.",
    )
    parser.add_argument(
        "--only-chunk-indexes",
        default="",
        help="Optional comma-separated chunk indexes to run when --mode=chunked.",
    )
    parser.add_argument("--wait", action="store_true", help="Wait for job completion and print metadata")
    parser.add_argument("--poll-seconds", type=int, default=60)
    return parser.parse_args()


def build_summary_row(
    *,
    job_name: str,
    mode: str,
    input_s3_uri: str,
    metadata: dict,
) -> dict:
    return {
        "job_name": job_name,
        "mode": mode,
        "input_s3_uri": input_s3_uri,
        "processing_time_seconds": metadata.get("processing_time_seconds"),
        "chunk_mapper_seconds": metadata.get("chunk_mapper_seconds"),
        "mapper_seconds_per_registered_image": metadata.get("mapper_seconds_per_registered_image"),
        "images_registered": metadata.get("images_registered"),
        "dataset_image_count": metadata.get("dataset_image_count"),
        "points_3d": metadata.get("points_3d"),
        "final_points_per_registered_image": metadata.get("final_points_per_registered_image"),
        "final_matcher_mode": metadata.get("final_matcher_mode"),
        "fallback_reason": metadata.get("fallback_reason"),
        "merged_component_count": metadata.get("merged_component_count"),
        "chunk_count": metadata.get("chunk_count"),
        "chunk_sizes": metadata.get("chunk_sizes"),
    }


def main() -> int:
    args = parse_args()
    branch_name = args.branch or get_current_branch()
    stack_name, outputs = find_branch_ml_stack(branch_name)
    role_arn = get_sagemaker_role_arn(stack_name)
    branch_tag = get_branch_ecr_tag(branch_name) or "latest"
    selected_tag = args.image_tag or branch_tag
    image_uri = args.image_uri or f"{outputs['SfMRepositoryUri']}:{selected_tag}"

    timestamp = int(time.time())
    job_name = f"{args.job_prefix}-{timestamp}"
    output_s3_uri = args.output_s3_uri or (
        f"s3://{outputs['MLBucketName']}/manual-validations/{job_name}/colmap"
    )

    environment = {
        "AWS_DEFAULT_REGION": "us-west-2",
        "PYTHONUNBUFFERED": "1",
        "SFM_BENCHMARK_SUBSET_STRATEGY": args.subset_strategy,
        **parse_env(args.env),
    }
    if args.mode == "chunked":
        environment.setdefault("COLMAP_ENABLE_SPATIAL_CHUNKING", "1")
        if args.only_chunk_indexes:
            environment["COLMAP_ONLY_CHUNK_INDEXES"] = args.only_chunk_indexes
    else:
        environment.setdefault("COLMAP_ENABLE_SPATIAL_CHUNKING", "0")

    payload = {
        "ProcessingJobName": job_name,
        "AppSpecification": {
            "ImageUri": image_uri,
            "ContainerEntrypoint": ["/opt/ml/code/run_sfm.sh"],
        },
        "ProcessingResources": {
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": args.instance_type,
                "VolumeSizeInGB": int(args.volume_size_gb),
            }
        },
        "ProcessingInputs": [
            {
                "InputName": "sfm-input",
                "S3Input": {
                    "S3Uri": args.input_s3_uri,
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
                        "S3Uri": output_s3_uri,
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                }
            ]
        },
        "Environment": environment,
        "Tags": [
            {"Key": "Project", "Value": "Spaceport"},
            {"Key": "Component", "Value": "SfM"},
            {"Key": "Benchmark", "Value": "true"},
            {"Key": "Branch", "Value": branch_name},
        ],
        "RoleArn": role_arn,
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(payload, handle, indent=2)
        handle.flush()
        payload_path = Path(handle.name)

    try:
        run_command(
            [
                "aws",
                "sagemaker",
                "create-processing-job",
                "--cli-input-json",
                f"file://{payload_path}",
            ]
        )
    finally:
        payload_path.unlink(missing_ok=True)

    summary = {
        "branch": branch_name,
        "stack_name": stack_name,
        "job_name": job_name,
        "mode": args.mode,
        "image_uri": image_uri,
        "selected_tag": selected_tag if not args.image_uri else "",
        "input_s3_uri": args.input_s3_uri,
        "output_s3_uri": output_s3_uri,
        "instance_type": args.instance_type,
        "role_arn": role_arn,
    }
    print(json.dumps(summary, indent=2))

    if not args.wait:
        return 0

    while True:
        status = aws_json(
            "sagemaker",
            "describe-processing-job",
            "--processing-job-name",
            job_name,
        )
        job_status = status["ProcessingJobStatus"]
        print(
            json.dumps(
                {
                    "job_name": job_name,
                    "status": job_status,
                    "failure_reason": status.get("FailureReason", ""),
                },
                indent=2,
            )
        )
        if job_status in {"Completed", "Failed", "Stopped"}:
            break
        time.sleep(max(args.poll_seconds, 15))

    metadata = load_s3_json(f"{output_s3_uri.rstrip('/')}/sfm_metadata.json")
    if metadata:
        print(json.dumps({"sfm_metadata": metadata}, indent=2))
        summary_row = build_summary_row(
            job_name=job_name,
            mode=args.mode,
            input_s3_uri=args.input_s3_uri,
            metadata=metadata,
        )
        print(json.dumps({"benchmark_summary": summary_row}, indent=2))
        if args.summary_json_output:
            output_path = Path(args.summary_json_output).expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(summary_row, indent=2) + "\n", encoding="utf-8")

    if job_status != "Completed":
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
