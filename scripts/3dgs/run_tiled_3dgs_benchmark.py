#!/usr/bin/env python3
"""Launch cheap, resumable tiled 3DGS benchmark ladders against the current branch stack."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
MERGE_SCRIPT_PATH = REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "merge_gaussian_tiles.py"
DEFAULT_SCAFFOLD_MAX_ITERATIONS = 4000
DEFAULT_TILE_MAX_ITERATIONS = 12000
DEFAULT_INSTANCE_TYPE = "ml.g5.2xlarge"
DEFAULT_VOLUME_SIZE_GB = 100
UNSUPPORTED_BILATERAL_VARIANTS = {"splatfacto-w-light", "splatfacto-w"}


def run_command(command: Sequence[str], *, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        check=True,
        text=True,
        capture_output=capture_output,
    )


def aws_json(*args: str) -> dict:
    result = run_command(["aws", *args, "--output", "json"], capture_output=True)
    return json.loads(result.stdout)


def parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Expected s3:// URI, got: {uri}")
    bucket, _, key = uri[5:].partition("/")
    if not bucket:
        raise ValueError(f"Invalid S3 URI missing bucket: {uri}")
    return bucket, key


def load_s3_json(s3_uri: str) -> dict:
    result = run_command(["aws", "s3", "cp", s3_uri, "-"], capture_output=True)
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
    outputs: Dict[str, str] = {}
    for entry in stack.get("Outputs", []):
        outputs[entry["OutputKey"]] = entry["OutputValue"]
    return outputs


def find_branch_ml_stack(branch_name: str) -> tuple[str, Dict[str, str]]:
    response = aws_json("cloudformation", "describe-stacks")
    for stack in response.get("Stacks", []):
        outputs = stack_outputs(stack)
        if outputs.get("BranchName") != branch_name:
            continue
        if "MLBucketName" not in outputs or "GaussianRepositoryUri" not in outputs:
            continue
        return stack["StackName"], outputs
    raise RuntimeError(f"Could not find an ML stack deployment for branch {branch_name}")


def get_stack_outputs(stack_name: str) -> tuple[str, Dict[str, str]]:
    response = aws_json("cloudformation", "describe-stacks", "--stack-name", stack_name)
    stacks = response.get("Stacks", [])
    if not stacks:
        raise RuntimeError(f"Could not describe stack {stack_name}")
    stack = stacks[0]
    return stack["StackName"], stack_outputs(stack)


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


def parse_env(values: Sequence[str]) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Environment override must look like KEY=VALUE: {value}")
        key, raw_value = value.split("=", 1)
        env[key] = raw_value
    return env


def normalize_s3_prefix(uri: str) -> str:
    return uri.rstrip("/")


def supports_bilateral_processing(model_variant: str) -> bool:
    return model_variant not in UNSUPPORTED_BILATERAL_VARIANTS


def select_tile_ids(
    manifest: dict,
    *,
    explicit_tile_ids: Sequence[str] | None = None,
    max_tiles: int | None = None,
) -> list[str]:
    tile_ids = [str(tile["tile_id"]) for tile in manifest.get("tiles", [])]
    if explicit_tile_ids:
        requested = [tile_id.strip() for tile_id in explicit_tile_ids if tile_id.strip()]
        missing = [tile_id for tile_id in requested if tile_id not in tile_ids]
        if missing:
            raise ValueError(f"Unknown tile ids requested: {', '.join(missing)}")
        tile_ids = requested
    if max_tiles is not None and max_tiles > 0:
        tile_ids = tile_ids[:max_tiles]
    return tile_ids


def sanitize_sagemaker_job_name(raw_name: str, *, max_length: int = 63) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9-]+", "-", raw_name).strip("-")
    sanitized = re.sub(r"-{2,}", "-", sanitized)
    if not sanitized:
        sanitized = "spaceport-3dgs-job"
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip("-")
    return sanitized or "spaceport-3dgs-job"


@dataclass
class BenchmarkStage:
    stage_name: str
    stage_type: str
    training_mode: str
    output_s3_uri: str
    job_name: str | None = None
    tile_id: str | None = None
    depends_on: list[str] | None = None
    environment: Dict[str, str] | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["depends_on"] = self.depends_on or []
        payload["environment"] = self.environment or {}
        return payload


@dataclass
class ExecutionContext:
    stack_name: str | None
    outputs: Dict[str, str]
    role_arn: str
    image_uri: str
    output_root_s3_uri: str


def build_training_environment(
    *,
    training_mode: str,
    tile_manifest_name: str,
    view_bucket_manifest_name: str,
    tile_id: str | None,
    max_iterations: int,
    extra_env: Dict[str, str],
    scaffold_max_iterations: int | None = None,
    max_tiles: int | None = None,
    selected_tile_ids: Sequence[str] | None = None,
    include_scaffold: bool = True,
    include_merge: bool = True,
) -> Dict[str, str]:
    env = {
        "AWS_DEFAULT_REGION": "us-west-2",
        "PYTHONUNBUFFERED": "1",
        "SAGEMAKER_PROGRAM": "train.py",
        "TORCH_CUDA_ARCH_LIST": "8.0 8.6",
        "CUDA_HOME": "/usr/local/cuda",
        "LD_LIBRARY_PATH": "/usr/local/cuda/lib64:/usr/local/cuda/lib",
        "LIBRARY_PATH": "/usr/local/cuda/lib64:/usr/local/cuda/lib",
        "MAX_ITERATIONS": str(max_iterations),
        "TRAINING_MODE": training_mode,
        "TILE_MANIFEST_PATH": tile_manifest_name,
        "VIEW_BUCKET_MANIFEST_PATH": view_bucket_manifest_name,
        "MODEL_VARIANT": "splatfacto-w-light",
        "BILATERAL_PROCESSING": "false",
        "ENABLE_BG_MODEL": "true",
        "ENABLE_ALPHA_LOSS": "true",
        "ENABLE_ROBUST_MASK": "true",
        "OUTPUT_FORMAT": "ply",
        "SOGS_COMPATIBLE": "true",
        "COMMERCIAL_LICENSE": "true",
        "FRAMEWORK": "nerfstudio",
        "METHODOLOGY": "spaceport_splatfacto_w_light_skybox",
    }
    if training_mode == "global_scaffold":
        env["GLOBAL_SCAFFOLD_MAX_ITERATIONS"] = str(max_iterations)
    if training_mode == "tiled_pipeline":
        if scaffold_max_iterations is not None and scaffold_max_iterations > 0:
            env["GLOBAL_SCAFFOLD_MAX_ITERATIONS"] = str(scaffold_max_iterations)
        if max_tiles is not None and max_tiles > 0:
            env["TILED_MAX_TILES"] = str(max_tiles)
        if selected_tile_ids:
            env["TILED_TILE_IDS"] = ",".join(selected_tile_ids)
        env["TILED_INCLUDE_SCAFFOLD"] = "true" if include_scaffold else "false"
        env["TILED_INCLUDE_MERGE"] = "true" if include_merge else "false"
    if tile_id:
        env["TILE_ID"] = tile_id
    env.update(extra_env)
    model_variant = env.get("MODEL_VARIANT", "splatfacto-w-light")
    bilateral_requested = env.get("BILATERAL_PROCESSING", "false").lower() in {"1", "true", "yes", "on"}
    if bilateral_requested and not supports_bilateral_processing(model_variant):
        env["BILATERAL_PROCESSING"] = "false"
    return env


def build_benchmark_stages(
    *,
    manifest: dict,
    branch_name: str,
    output_root_s3_uri: str,
    job_prefix: str,
    include_monolithic: bool,
    include_scaffold: bool,
    include_merge: bool,
    orchestration_mode: str,
    tile_ids: Sequence[str],
    monolithic_max_iterations: int,
    scaffold_max_iterations: int,
    tile_max_iterations: int,
    extra_env: Dict[str, str],
    timestamp: int,
) -> list[BenchmarkStage]:
    output_root = normalize_s3_prefix(output_root_s3_uri)
    tile_manifest_name = "3dgs_tile_manifest.json"
    view_bucket_manifest_name = "3dgs_view_buckets.json"
    stages: list[BenchmarkStage] = []

    if include_monolithic:
        stages.append(
            BenchmarkStage(
                stage_name="M0_monolithic",
                stage_type="train",
                training_mode="monolithic",
                job_name=sanitize_sagemaker_job_name(f"{job_prefix}-{timestamp}-m0"),
                output_s3_uri=f"{output_root}/M0_monolithic",
                environment=build_training_environment(
                    training_mode="monolithic",
                    tile_manifest_name=tile_manifest_name,
                    view_bucket_manifest_name=view_bucket_manifest_name,
                    tile_id=None,
                    max_iterations=monolithic_max_iterations,
                    extra_env=extra_env,
                ),
            )
        )

    if orchestration_mode == "single_job":
        stages.append(
            BenchmarkStage(
                stage_name="T2_tiled_pipeline",
                stage_type="train",
                training_mode="tiled_pipeline",
                job_name=sanitize_sagemaker_job_name(f"{job_prefix}-{timestamp}-tiled"),
                output_s3_uri=f"{output_root}/T2_tiled_pipeline",
                environment=build_training_environment(
                    training_mode="tiled_pipeline",
                    tile_manifest_name=tile_manifest_name,
                    view_bucket_manifest_name=view_bucket_manifest_name,
                    tile_id=None,
                    max_iterations=tile_max_iterations,
                    extra_env=extra_env,
                    scaffold_max_iterations=scaffold_max_iterations,
                    max_tiles=len(tile_ids),
                    selected_tile_ids=tile_ids,
                    include_scaffold=include_scaffold,
                    include_merge=include_merge,
                ),
            )
        )
        return stages

    scaffold_stage_name = "S0_scaffold"
    if include_scaffold:
        stages.append(
            BenchmarkStage(
                stage_name=scaffold_stage_name,
                stage_type="train",
                training_mode="global_scaffold",
                job_name=sanitize_sagemaker_job_name(f"{job_prefix}-{timestamp}-scaffold"),
                output_s3_uri=f"{output_root}/{scaffold_stage_name}",
                environment=build_training_environment(
                    training_mode="global_scaffold",
                    tile_manifest_name=tile_manifest_name,
                    view_bucket_manifest_name=view_bucket_manifest_name,
                    tile_id=None,
                    max_iterations=scaffold_max_iterations,
                    extra_env=extra_env,
                ),
            )
        )

    selected_tiles = list(tile_ids)
    for tile_id in selected_tiles:
        stages.append(
            BenchmarkStage(
                stage_name=f"T0_{tile_id}",
                stage_type="train",
                training_mode="leaf_tile",
                job_name=sanitize_sagemaker_job_name(f"{job_prefix}-{timestamp}-{tile_id}"),
                tile_id=tile_id,
                output_s3_uri=f"{output_root}/tiles/{tile_id}",
                depends_on=[scaffold_stage_name] if include_scaffold else [],
                environment=build_training_environment(
                    training_mode="leaf_tile",
                    tile_manifest_name=tile_manifest_name,
                    view_bucket_manifest_name=view_bucket_manifest_name,
                    tile_id=tile_id,
                    max_iterations=tile_max_iterations,
                    extra_env=extra_env,
                ),
            )
        )

    if include_merge and selected_tiles:
        stages.append(
            BenchmarkStage(
                stage_name="MERGE_strict_core",
                stage_type="merge",
                training_mode="strict_core",
                output_s3_uri=f"{output_root}/merged",
                depends_on=[f"T0_{tile_id}" for tile_id in selected_tiles],
            )
        )

    return stages


def create_training_job_payload(
    *,
    branch_name: str,
    job_name: str,
    image_uri: str,
    role_arn: str,
    input_s3_uri: str,
    output_s3_uri: str,
    environment: Dict[str, str],
    instance_type: str,
    volume_size_gb: int,
) -> dict:
    return {
        "TrainingJobName": job_name,
        "AlgorithmSpecification": {
            "TrainingImage": image_uri,
            "TrainingInputMode": "File",
        },
        "RoleArn": role_arn,
        "InputDataConfig": [
            {
                "ChannelName": "training",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": input_s3_uri,
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
                "CompressionType": "None",
                "RecordWrapperType": "None",
            }
        ],
        "OutputDataConfig": {
            "S3OutputPath": output_s3_uri,
        },
        "ResourceConfig": {
            "InstanceType": instance_type,
            "InstanceCount": 1,
            "VolumeSizeInGB": volume_size_gb,
        },
        "StoppingCondition": {
            "MaxRuntimeInSeconds": 14400,
        },
        "Environment": environment,
        "Tags": [
            {"Key": "Project", "Value": "Spaceport"},
            {"Key": "Component", "Value": "3DGS"},
            {"Key": "Benchmark", "Value": "true"},
            {"Key": "Branch", "Value": branch_name},
        ],
    }


def wait_for_training_job(job_name: str, *, poll_seconds: int) -> dict:
    while True:
        status = aws_json("sagemaker", "describe-training-job", "--training-job-name", job_name)
        current_status = status["TrainingJobStatus"]
        if current_status == "Completed":
            return status
        if current_status in {"Failed", "Stopped"}:
            reason = status.get("FailureReason", current_status)
            raise RuntimeError(f"Training job {job_name} ended with {current_status}: {reason}")
        time.sleep(max(15, poll_seconds))


def download_and_extract_model_artifact(*, s3_uri: str, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    tar_path = target_dir / "model.tar.gz"
    run_command(["aws", "s3", "cp", s3_uri, str(tar_path)])
    with tarfile.open(tar_path, "r:gz") as archive:
        archive.extractall(target_dir)
    return target_dir


def summarize_training_metadata(stage_name: str, extracted_dir: Path, describe_payload: dict) -> dict:
    metadata_path = extracted_dir / "training_metadata.json"
    selection_path = extracted_dir / "training_selection.json"
    tiled_summary_path = extracted_dir / "tiled_pipeline_summary.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    selection = json.loads(selection_path.read_text(encoding="utf-8")) if selection_path.exists() else {}
    tiled_summary = json.loads(tiled_summary_path.read_text(encoding="utf-8")) if tiled_summary_path.exists() else {}
    return {
        "stage_name": stage_name,
        "training_mode": metadata.get("training_mode") or selection.get("training_mode"),
        "billable_time_seconds": describe_payload.get("BillableTimeInSeconds"),
        "training_time_seconds": describe_payload.get("TrainingTimeInSeconds"),
        "model_artifacts_s3_uri": describe_payload.get("ModelArtifacts", {}).get("S3ModelArtifacts"),
        "output_file": metadata.get("output_file"),
        "file_size_mb": metadata.get("file_size_mb"),
        "background_skybox": metadata.get("background_skybox"),
        "training_selection": selection or metadata.get("training_selection"),
        "tiled_pipeline_summary": tiled_summary or metadata.get("stages"),
    }


def run_merge_stage(
    *,
    tile_manifest: dict[str, object],
    tile_stage_dirs: Dict[str, Path],
    output_dir: Path,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    tile_manifest_path = output_dir / "selected_tile_manifest.json"
    tile_manifest_path.write_text(json.dumps(tile_manifest, indent=2), encoding="utf-8")
    command = [
        "python3",
        str(MERGE_SCRIPT_PATH),
        "--tile-manifest",
        str(tile_manifest_path),
        "--tiles-root",
        str(output_dir / "tile_outputs"),
        "--output-dir",
        str(output_dir),
    ]
    tile_root = output_dir / "tile_outputs"
    tile_root.mkdir(parents=True, exist_ok=True)
    for tile_id, extracted_dir in tile_stage_dirs.items():
        stage_link = tile_root / tile_id
        if stage_link.exists():
            if stage_link.is_symlink() or stage_link.is_file():
                stage_link.unlink()
            else:
                shutil.rmtree(stage_link)
        shutil.copytree(extracted_dir, stage_link)
    result = run_command(command, capture_output=True)
    return json.loads(result.stdout)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch", default="", help="Git branch to benchmark. Defaults to current branch.")
    parser.add_argument(
        "--stack-name",
        default="",
        help="Optional CloudFormation ML stack name override. Use this when the current branch has no deployed ML stack.",
    )
    parser.add_argument(
        "--role-arn",
        default="",
        help="Optional SageMaker execution role ARN. Requires --image-uri and --output-root-s3-uri when no ML stack is available.",
    )
    parser.add_argument("--colmap-s3-uri", required=True, help="S3 prefix for SfM/colmap output.")
    parser.add_argument(
        "--output-root-s3-uri",
        default="",
        help="S3 prefix for benchmark outputs. Defaults to the branch ML bucket manual-validations prefix.",
    )
    parser.add_argument("--job-prefix", default="3dgs-tiled", help="Training job name prefix.")
    parser.add_argument("--instance-type", default=DEFAULT_INSTANCE_TYPE)
    parser.add_argument("--volume-size-gb", type=int, default=DEFAULT_VOLUME_SIZE_GB)
    parser.add_argument("--monolithic-max-iterations", type=int, default=DEFAULT_TILE_MAX_ITERATIONS)
    parser.add_argument("--scaffold-max-iterations", type=int, default=DEFAULT_SCAFFOLD_MAX_ITERATIONS)
    parser.add_argument("--tile-max-iterations", type=int, default=DEFAULT_TILE_MAX_ITERATIONS)
    parser.add_argument("--max-tiles", type=int, default=4, help="Cap leaf-tile jobs for cheap ladder runs.")
    parser.add_argument("--tile-id", action="append", default=[], help="Repeatable tile_id filter.")
    parser.add_argument("--env", action="append", default=[], help="Repeatable KEY=VALUE environment overrides.")
    parser.add_argument("--image-tag", default="", help="Override the ECR image tag. Defaults to current branch tag.")
    parser.add_argument("--image-uri", default="", help="Fully qualified training image URI override.")
    parser.add_argument("--wait", action="store_true", help="Wait for submitted jobs and collect summaries.")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--submit", action="store_true", help="Submit the generated training jobs.")
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved benchmark plan without submitting jobs.")
    parser.add_argument("--include-monolithic", action="store_true", help="Include the monolithic baseline rung.")
    parser.add_argument(
        "--orchestration-mode",
        choices=["single_job", "fanout"],
        default="single_job",
        help="Run one tiled job that orchestrates scaffold+tiles locally, or fan out one SageMaker job per stage.",
    )
    parser.add_argument("--skip-scaffold", action="store_true", help="Skip the scaffold rung.")
    parser.add_argument("--skip-merge", action="store_true", help="Skip the local merge stage.")
    parser.add_argument("--summary-json-output", default="", help="Optional local path for the benchmark summary JSON.")
    parser.add_argument(
        "--local-merge-output-dir",
        default="",
        help="Optional local directory for downloaded tile artifacts and merged output when --wait is used.",
    )
    return parser.parse_args()


def resolve_execution_context(
    *,
    branch_name: str,
    timestamp: int,
    args: argparse.Namespace,
) -> ExecutionContext:
    branch_tag = get_branch_ecr_tag(branch_name) or "latest"
    resolved_stack_name: str | None = None
    outputs: Dict[str, str] = {}

    if args.stack_name:
        resolved_stack_name, outputs = get_stack_outputs(args.stack_name)
    else:
        try:
            resolved_stack_name, outputs = find_branch_ml_stack(branch_name)
        except RuntimeError:
            if not (args.role_arn and args.image_uri and args.output_root_s3_uri):
                raise RuntimeError(
                    "Could not find a branch ML stack. Provide --stack-name, or provide "
                    "--role-arn, --image-uri, and --output-root-s3-uri explicitly."
                ) from None

    role_arn = args.role_arn or (get_sagemaker_role_arn(resolved_stack_name) if resolved_stack_name else "")
    if not role_arn:
        raise RuntimeError("Could not resolve a SageMaker role ARN for the benchmark run")

    if args.image_uri:
        image_uri = args.image_uri
    else:
        gaussian_repo_uri = outputs.get("GaussianRepositoryUri")
        if not gaussian_repo_uri:
            raise RuntimeError("Missing GaussianRepositoryUri; provide --image-uri explicitly")
        selected_tag = args.image_tag or branch_tag
        image_uri = f"{gaussian_repo_uri}:{selected_tag}"

    if args.output_root_s3_uri:
        output_root_s3_uri = args.output_root_s3_uri
    else:
        bucket_name = outputs.get("MLBucketName")
        if not bucket_name:
            raise RuntimeError("Missing MLBucketName; provide --output-root-s3-uri explicitly")
        output_root_s3_uri = f"s3://{bucket_name}/manual-validations/{args.job_prefix}-{timestamp}/3dgs"

    return ExecutionContext(
        stack_name=resolved_stack_name,
        outputs=outputs,
        role_arn=role_arn,
        image_uri=image_uri,
        output_root_s3_uri=output_root_s3_uri,
    )


def main() -> int:
    args = parse_args()
    branch_name = args.branch or get_current_branch()
    timestamp = int(time.time())
    context = resolve_execution_context(
        branch_name=branch_name,
        timestamp=timestamp,
        args=args,
    )

    colmap_s3_uri = normalize_s3_prefix(args.colmap_s3_uri)
    tile_manifest_s3_uri = f"{colmap_s3_uri}/3dgs_tile_manifest.json"
    view_bucket_s3_uri = f"{colmap_s3_uri}/3dgs_view_buckets.json"
    tile_manifest = load_s3_json(tile_manifest_s3_uri)
    _ = load_s3_json(view_bucket_s3_uri)

    selected_tiles = select_tile_ids(
        tile_manifest,
        explicit_tile_ids=args.tile_id,
        max_tiles=args.max_tiles,
    )
    stages = build_benchmark_stages(
        manifest=tile_manifest,
        branch_name=branch_name,
        output_root_s3_uri=context.output_root_s3_uri,
        job_prefix=args.job_prefix,
        include_monolithic=args.include_monolithic,
        include_scaffold=not args.skip_scaffold,
        include_merge=not args.skip_merge,
        orchestration_mode=args.orchestration_mode,
        tile_ids=selected_tiles,
        monolithic_max_iterations=args.monolithic_max_iterations,
        scaffold_max_iterations=args.scaffold_max_iterations,
        tile_max_iterations=args.tile_max_iterations,
        extra_env=parse_env(args.env),
        timestamp=timestamp,
    )

    summary: dict = {
        "branch": branch_name,
        "stack_name": context.stack_name,
        "image_uri": context.image_uri,
        "input_colmap_s3_uri": colmap_s3_uri,
        "tile_manifest_s3_uri": tile_manifest_s3_uri,
        "view_bucket_s3_uri": view_bucket_s3_uri,
        "selected_tile_ids": selected_tiles,
        "stages": [stage.to_dict() for stage in stages],
        "submitted_jobs": [],
        "completed_jobs": [],
    }

    if args.dry_run or not args.submit:
        print(json.dumps(summary, indent=2))
        if args.summary_json_output:
            Path(args.summary_json_output).write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return 0

    if args.orchestration_mode == "fanout" and not args.wait:
        raise RuntimeError("Fanout submission requires --wait so scaffold and tile dependencies can be enforced safely")

    sagemaker = aws_json  # alias for consistency with lambda/test patterns
    submitted_stage_to_job: Dict[str, str] = {}
    completed_stage_outputs: Dict[str, dict] = {}

    merge_summary = None
    merge_root = Path(args.local_merge_output_dir) if args.local_merge_output_dir else None
    extracted_stage_dirs: Dict[str, Path] = {}

    for stage in stages:
        if stage.stage_type != "train":
            continue
        payload = create_training_job_payload(
            branch_name=branch_name,
            job_name=stage.job_name or stage.stage_name,
            image_uri=context.image_uri,
            role_arn=context.role_arn,
            input_s3_uri=colmap_s3_uri,
            output_s3_uri=stage.output_s3_uri,
            environment=stage.environment or {},
            instance_type=args.instance_type,
            volume_size_gb=args.volume_size_gb,
        )
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(payload, handle, indent=2)
            handle.flush()
            payload_path = Path(handle.name)
        try:
            run_command(["aws", "sagemaker", "create-training-job", "--cli-input-json", f"file://{payload_path}"])
        finally:
            payload_path.unlink(missing_ok=True)
        submitted_stage_to_job[stage.stage_name] = stage.job_name or stage.stage_name
        summary["submitted_jobs"].append(
            {
                "stage_name": stage.stage_name,
                "job_name": stage.job_name,
                "output_s3_uri": stage.output_s3_uri,
            }
        )

        if args.orchestration_mode == "fanout" and args.wait:
            describe_payload = wait_for_training_job(submitted_stage_to_job[stage.stage_name], poll_seconds=args.poll_seconds)
            model_artifacts_s3_uri = describe_payload.get("ModelArtifacts", {}).get("S3ModelArtifacts")
            if not model_artifacts_s3_uri:
                raise RuntimeError(f"Training job {stage.job_name} completed without model artifacts")
            extracted_dir = None
            if merge_root is not None:
                stage_dir = merge_root / stage.stage_name
                extracted_dir = download_and_extract_model_artifact(
                    s3_uri=model_artifacts_s3_uri,
                    target_dir=stage_dir,
                )
            if stage.tile_id and extracted_dir is not None:
                extracted_stage_dirs[stage.tile_id] = extracted_dir
            completed = summarize_training_metadata(stage.stage_name, extracted_dir or Path("/nonexistent"), describe_payload)
            summary["completed_jobs"].append(completed)
            completed_stage_outputs[stage.stage_name] = completed

    if args.wait and args.orchestration_mode != "fanout":
        merge_root = Path(args.local_merge_output_dir) if args.local_merge_output_dir else None
        for stage in stages:
            if stage.stage_type != "train":
                continue
            describe_payload = wait_for_training_job(submitted_stage_to_job[stage.stage_name], poll_seconds=args.poll_seconds)
            model_artifacts_s3_uri = describe_payload.get("ModelArtifacts", {}).get("S3ModelArtifacts")
            if not model_artifacts_s3_uri:
                raise RuntimeError(f"Training job {stage.job_name} completed without model artifacts")
            extracted_dir = None
            if merge_root is not None:
                stage_dir = merge_root / stage.stage_name
                extracted_dir = download_and_extract_model_artifact(
                    s3_uri=model_artifacts_s3_uri,
                    target_dir=stage_dir,
                )
            if stage.tile_id and extracted_dir is not None:
                extracted_stage_dirs[stage.tile_id] = extracted_dir
            completed = summarize_training_metadata(stage.stage_name, extracted_dir or Path("/nonexistent"), describe_payload)
            summary["completed_jobs"].append(completed)
            completed_stage_outputs[stage.stage_name] = completed

        if merge_root is not None and not args.skip_merge and extracted_stage_dirs:
            local_tile_manifest_path = merge_root / "3dgs_tile_manifest.json"
            run_command(["aws", "s3", "cp", tile_manifest_s3_uri, str(local_tile_manifest_path)])
            merge_summary = run_merge_stage(
                tile_manifest={
                    **tile_manifest,
                    "tiles": [
                        dict(tile)
                        for tile in tile_manifest.get("tiles", [])
                        if str(tile.get("tile_id")) in set(selected_tiles)
                    ],
                },
                tile_stage_dirs=extracted_stage_dirs,
                output_dir=merge_root / "merged",
            )
            summary["merge"] = merge_summary
    elif args.wait and merge_root is not None and not args.skip_merge and extracted_stage_dirs:
        local_tile_manifest_path = merge_root / "3dgs_tile_manifest.json"
        run_command(["aws", "s3", "cp", tile_manifest_s3_uri, str(local_tile_manifest_path)])
        merge_summary = run_merge_stage(
            tile_manifest={
                **tile_manifest,
                "tiles": [
                    dict(tile)
                    for tile in tile_manifest.get("tiles", [])
                    if str(tile.get("tile_id")) in set(selected_tiles)
                ],
            },
            tile_stage_dirs=extracted_stage_dirs,
            output_dir=merge_root / "merged",
        )
        summary["merge"] = merge_summary

    print(json.dumps(summary, indent=2))
    if args.summary_json_output:
        Path(args.summary_json_output).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
