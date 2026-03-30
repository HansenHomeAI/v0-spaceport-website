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
        if resource.get("LogicalResourceId") != "SageMakerExecutionRole":
            continue
        role_name = resource["PhysicalResourceId"]
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
        "--env",
        action="append",
        default=[],
        help="Repeatable KEY=VALUE environment overrides for the container",
    )
    parser.add_argument("--wait", action="store_true", help="Wait for job completion and print metadata")
    parser.add_argument("--poll-seconds", type=int, default=60)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    branch_name = args.branch or get_current_branch()
    stack_name, outputs = find_branch_ml_stack(branch_name)
    role_arn = get_sagemaker_role_arn(stack_name)
    branch_tag = get_branch_ecr_tag(branch_name) or "latest"
    image_uri = f"{outputs['SfMRepositoryUri']}:{branch_tag}"

    timestamp = int(time.time())
    job_name = f"{args.job_prefix}-{timestamp}"
    output_s3_uri = args.output_s3_uri or (
        f"s3://{outputs['MLBucketName']}/manual-validations/{job_name}/colmap"
    )

    environment = {
        "AWS_DEFAULT_REGION": "us-west-2",
        "PYTHONUNBUFFERED": "1",
        "SFM_BENCHMARK_SUBSET_STRATEGY": "first_portion_by_exif_datetime_else_filename",
        **parse_env(args.env),
    }

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
        "image_uri": image_uri,
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

    if job_status != "Completed":
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
