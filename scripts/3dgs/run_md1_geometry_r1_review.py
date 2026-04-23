#!/usr/bin/env python3
"""Stage and run the md1 R1 render-backed tiled merge review."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_3DGS_ROOT = REPO_ROOT / "scripts" / "3dgs"
if str(SCRIPTS_3DGS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_3DGS_ROOT))

from run_tiled_3dgs_benchmark import (  # noqa: E402
    create_quality_review_processing_payload,
    create_quality_review_training_payload,
    find_branch_ml_stack,
    get_branch_ecr_tag,
    get_current_branch,
    get_sagemaker_role_arn,
    get_stack_outputs,
    normalize_s3_prefix,
    run_command,
    sanitize_sagemaker_job_name,
    wait_for_processing_job,
    wait_for_training_job,
)


DEFAULT_COLMAP_S3_URI = "s3://spaceport-ml-processing-staging/manual-validations/md1p27eba1k-1776107310/colmap"
DEFAULT_SHARED_ML_STACK_NAME = "SpaceportMLPipelineStagingStack"
DEFAULT_VARIANTS = ("strict_core", "support_weighted_overlap", "raw_union")
TOP_LEVEL_METADATA_FILES = (
    "training_metadata.json",
    "tiled_pipeline_summary.json",
)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def aws_cp(source: str | Path, target: str | Path) -> None:
    run_command(["aws", "s3", "cp", str(source), str(target)])


def resolve_stack_and_outputs(branch_name: str, *, stack_name: str = "") -> tuple[str, dict[str, str], str]:
    if stack_name:
        resolved_stack_name, outputs = get_stack_outputs(stack_name)
        return resolved_stack_name, outputs, "explicit_stack"
    try:
        resolved_stack_name, outputs = find_branch_ml_stack(branch_name)
        return resolved_stack_name, outputs, "branch_stack"
    except RuntimeError:
        resolved_stack_name, outputs = get_stack_outputs(DEFAULT_SHARED_ML_STACK_NAME)
        return resolved_stack_name, outputs, "shared_staging_fallback"


def add_path_to_tar(archive: tarfile.TarFile, source_path: Path, arcname: str) -> None:
    if not source_path.exists():
        return
    archive.add(source_path, arcname=arcname, recursive=True)


def create_variant_model_tarball(
    *,
    extracted_model_dir: Path,
    merge_dir: Path,
    output_tarball: Path,
    force: bool,
) -> Path:
    if output_tarball.exists() and output_tarball.stat().st_size > 0 and not force:
        return output_tarball
    output_tarball.parent.mkdir(parents=True, exist_ok=True)
    temp_tarball = output_tarball.with_suffix(output_tarball.suffix + ".tmp")
    temp_tarball.unlink(missing_ok=True)
    with tarfile.open(temp_tarball, "w:gz", compresslevel=6) as archive:
        for file_name in TOP_LEVEL_METADATA_FILES:
            add_path_to_tar(archive, extracted_model_dir / file_name, file_name)
        add_path_to_tar(archive, extracted_model_dir / "tiles", "tiles")
        add_path_to_tar(archive, merge_dir / "merged_splat.ply", "merged/merged_splat.ply")
        add_path_to_tar(archive, merge_dir / "merge_report.json", "merged/merge_report.json")
        add_path_to_tar(archive, merge_dir / "background_skybox.webp", "merged/background_skybox.webp")
        add_path_to_tar(archive, merge_dir / "background_manifest.json", "merged/background_manifest.json")
    temp_tarball.replace(output_tarball)
    return output_tarball


def s3_prefix_join(prefix: str, *parts: str) -> str:
    cleaned = [part.strip("/") for part in parts if part.strip("/")]
    return "/".join([normalize_s3_prefix(prefix), *cleaned])


def upload_manifest_from_training_artifact(
    *,
    artifact_uri: str,
    output_root_s3_uri: str,
    variant: str,
) -> str:
    if not artifact_uri:
        raise RuntimeError("Training job completed without a model artifact URI")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        tarball = tmp_root / "model.tar.gz"
        aws_cp(artifact_uri, tarball)
        with tarfile.open(tarball, "r:gz") as archive:
            archive.extract("quality_review_manifest.json", tmp_root)
        baseline_prefix = s3_prefix_join(output_root_s3_uri, "baselines", variant)
        aws_cp(tmp_root / "quality_review_manifest.json", f"{baseline_prefix}/quality_review_manifest.json")
    return baseline_prefix


def stage_review_inputs(
    *,
    audit_root: Path,
    output_root_s3_uri: str,
    variants: Sequence[str],
    force_tarballs: bool,
    keep_local_tarballs: bool,
) -> dict[str, Any]:
    extracted_model_dir = audit_root / "model" / "extracted"
    if not extracted_model_dir.exists():
        raise FileNotFoundError(f"Missing extracted model dir: {extracted_model_dir}")
    review_camera_manifest = audit_root / "review_camera_manifest.json"
    if not review_camera_manifest.exists():
        raise FileNotFoundError(f"Missing frozen camera manifest: {review_camera_manifest}")

    staged_root = audit_root / "r1_review_inputs"
    review_manifest_s3_prefix = s3_prefix_join(output_root_s3_uri, "review-input")
    aws_cp(review_camera_manifest, f"{review_manifest_s3_prefix}/review_camera_manifest.json")

    staged_variants: dict[str, Any] = {}
    for variant in variants:
        merge_dir = audit_root / "offline_merges" / variant
        if not (merge_dir / "merged_splat.ply").exists():
            raise FileNotFoundError(f"Missing merged splat for {variant}: {merge_dir}")
        tarball = create_variant_model_tarball(
            extracted_model_dir=extracted_model_dir,
            merge_dir=merge_dir,
            output_tarball=staged_root / variant / "model.tar.gz",
            force=force_tarballs or not keep_local_tarballs,
        )
        model_s3_prefix = s3_prefix_join(output_root_s3_uri, "inputs", variant)
        aws_cp(tarball, f"{model_s3_prefix}/model.tar.gz")
        retained_local_tarball = str(tarball) if keep_local_tarballs else None
        if not keep_local_tarballs:
            tarball.unlink(missing_ok=True)
            try:
                tarball.parent.rmdir()
            except OSError:
                pass
        staged_variants[variant] = {
            "local_model_tarball": retained_local_tarball,
            "model_s3_uri": f"{model_s3_prefix}/model.tar.gz",
            "merge_report": str(merge_dir / "merge_report.json"),
        }

    return {
        "review_camera_manifest_s3_uri": review_manifest_s3_prefix,
        "variants": staged_variants,
    }


def run_review_jobs(
    *,
    branch_name: str,
    image_uri: str,
    role_arn: str,
    colmap_s3_uri: str,
    output_root_s3_uri: str,
    review_camera_manifest_s3_uri: str,
    staged_variants: dict[str, Any],
    variants: Sequence[str],
    max_images_per_bucket: int,
    camera_set: str,
    instance_type: str,
    volume_size_gb: int,
    max_runtime_seconds: int,
    poll_seconds: int,
    submit: bool,
    wait: bool,
    execution_mode: str,
    render_scale: float,
    max_gaussians_per_view: int,
    cull_margin: float,
    min_gaussians_on_oom: int,
    tile_ids: str,
) -> dict[str, Any]:
    jobs: dict[str, Any] = {}
    strict_output_uri = ""
    strict_baseline_manifest_uri = ""
    for variant in variants:
        model_s3_uri = staged_variants[variant]["model_s3_uri"]
        output_s3_uri = s3_prefix_join(output_root_s3_uri, "outputs", variant)
        baseline_s3_uri = strict_baseline_manifest_uri if strict_baseline_manifest_uri and variant != "strict_core" else ""
        job_name = sanitize_sagemaker_job_name(f"md1-r1-{variant}-{int(time.time())}-quality")
        environment = {
            "QUALITY_REVIEW_MAX_IMAGES_PER_BUCKET": str(max_images_per_bucket),
            "QUALITY_REVIEW_CAMERA_SET": camera_set,
            "QUALITY_REVIEW_RENDER_SCALE": str(render_scale),
            "QUALITY_REVIEW_MAX_GAUSSIANS_PER_VIEW": str(max_gaussians_per_view),
            "QUALITY_REVIEW_CULL_MARGIN": str(cull_margin),
            "QUALITY_REVIEW_MIN_GAUSSIANS_ON_OOM": str(min_gaussians_on_oom),
            "PYTHONUNBUFFERED": "1",
        }
        if tile_ids:
            environment["QUALITY_REVIEW_TILE_IDS"] = tile_ids
        if execution_mode == "training":
            payload = create_quality_review_training_payload(
                branch_name=branch_name,
                job_name=job_name,
                image_uri=image_uri,
                role_arn=role_arn,
                model_artifact_s3_uri=model_s3_uri,
                colmap_s3_uri=colmap_s3_uri,
                output_s3_uri=output_s3_uri,
                environment=environment,
                instance_type=instance_type,
                volume_size_gb=volume_size_gb,
                max_runtime_seconds=max_runtime_seconds,
                review_camera_manifest_s3_uri=review_camera_manifest_s3_uri,
                baseline_review_manifest_s3_uri=baseline_s3_uri,
            )
        else:
            payload = create_quality_review_processing_payload(
                branch_name=branch_name,
                job_name=job_name,
                image_uri=image_uri,
                role_arn=role_arn,
                model_artifact_s3_uri=model_s3_uri,
                colmap_s3_uri=colmap_s3_uri,
                output_s3_uri=output_s3_uri,
                environment=environment,
                instance_type=instance_type,
                volume_size_gb=volume_size_gb,
                max_runtime_seconds=max_runtime_seconds,
                review_camera_manifest_s3_uri=review_camera_manifest_s3_uri,
                baseline_review_manifest_s3_uri=baseline_s3_uri,
            )
        jobs[variant] = {
            "job_name": job_name,
            "execution_mode": execution_mode,
            "model_s3_uri": model_s3_uri,
            "output_s3_uri": output_s3_uri,
            "baseline_review_manifest_s3_uri": baseline_s3_uri,
            "payload": payload,
        }
        if not submit:
            continue
        payload_path = Path("/tmp") / f"{job_name}.json"
        write_json(payload_path, payload)
        try:
            if execution_mode == "training":
                run_command(["aws", "sagemaker", "create-training-job", "--cli-input-json", f"file://{payload_path}"])
            else:
                run_command(["aws", "sagemaker", "create-processing-job", "--cli-input-json", f"file://{payload_path}"])
        finally:
            payload_path.unlink(missing_ok=True)
        jobs[variant]["submitted"] = True
        if wait:
            if execution_mode == "training":
                status = wait_for_training_job(job_name, poll_seconds=poll_seconds)
                jobs[variant]["status"] = {
                    "TrainingJobStatus": status.get("TrainingJobStatus"),
                    "TrainingStartTime": str(status.get("TrainingStartTime")),
                    "TrainingEndTime": str(status.get("TrainingEndTime")),
                }
                jobs[variant]["model_artifacts_s3_uri"] = status.get("ModelArtifacts", {}).get("S3ModelArtifacts", "")
            else:
                status = wait_for_processing_job(job_name, poll_seconds=poll_seconds)
                jobs[variant]["status"] = {
                    "ProcessingJobStatus": status.get("ProcessingJobStatus"),
                    "ProcessingStartTime": str(status.get("ProcessingStartTime")),
                    "ProcessingEndTime": str(status.get("ProcessingEndTime")),
                }
            if variant == "strict_core":
                strict_output_uri = output_s3_uri
                if execution_mode == "training":
                    artifact_uri = jobs[variant].get("model_artifacts_s3_uri", "")
                    strict_baseline_manifest_uri = upload_manifest_from_training_artifact(
                        artifact_uri=artifact_uri,
                        output_root_s3_uri=output_root_s3_uri,
                        variant=variant,
                    )
                else:
                    strict_baseline_manifest_uri = strict_output_uri
    return jobs


def download_review_outputs(*, audit_root: Path, jobs: dict[str, Any]) -> None:
    output_root = audit_root / "r1_review_outputs"
    for variant, job in jobs.items():
        variant_output = output_root / variant
        variant_output.mkdir(parents=True, exist_ok=True)
        artifact_uri = job.get("model_artifacts_s3_uri")
        if artifact_uri:
            tarball = variant_output / "model.tar.gz"
            aws_cp(str(artifact_uri), tarball)
            with tarfile.open(tarball, "r:gz") as archive:
                for file_name in ("quality_review_manifest.json", "review_comparison.json"):
                    try:
                        archive.extract(file_name, variant_output)
                    except KeyError:
                        if file_name == "quality_review_manifest.json":
                            raise RuntimeError(f"Training artifact missing {file_name}: {artifact_uri}")
            tarball.unlink(missing_ok=True)
            continue
        for file_name in ("quality_review_manifest.json", "review_comparison.json"):
            source_uri = f"{normalize_s3_prefix(job['output_s3_uri'])}/{file_name}"
            result = subprocess.run(
                ["aws", "s3", "cp", source_uri, str(variant_output / file_name)],
                check=False,
                text=True,
                capture_output=True,
            )
            if result.returncode != 0 and file_name == "quality_review_manifest.json":
                raise RuntimeError(f"Could not download {source_uri}: {result.stderr}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-root", type=Path, default=REPO_ROOT / "logs" / "audit" / "md1-1k-full-r2")
    parser.add_argument("--branch", default="")
    parser.add_argument("--stack-name", default="")
    parser.add_argument("--colmap-s3-uri", default=DEFAULT_COLMAP_S3_URI)
    parser.add_argument("--output-root-s3-uri", default="")
    parser.add_argument("--variant", action="append", choices=DEFAULT_VARIANTS, default=[])
    parser.add_argument("--max-images-per-bucket", type=int, default=4)
    parser.add_argument("--camera-set", default="smoke")
    parser.add_argument("--execution-mode", choices=("processing", "training"), default="processing")
    parser.add_argument("--instance-type", default="ml.g5.2xlarge")
    parser.add_argument("--volume-size-gb", type=int, default=100)
    parser.add_argument("--max-runtime-seconds", type=int, default=7200)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--render-scale", type=float, default=0.25)
    parser.add_argument("--max-gaussians-per-view", type=int, default=500_000)
    parser.add_argument("--cull-margin", type=float, default=0.5)
    parser.add_argument("--min-gaussians-on-oom", type=int, default=75_000)
    parser.add_argument("--tile-ids", default="tile_02,tile_05")
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--force-tarballs", action="store_true")
    parser.add_argument("--keep-local-tarballs", action="store_true")
    parser.add_argument("--skip-output-download", action="store_true")
    parser.add_argument("--summary-json-output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    branch_name = args.branch or get_current_branch()
    variants = args.variant or list(DEFAULT_VARIANTS)
    timestamp = int(time.time())
    stack_name, outputs, stack_resolution = resolve_stack_and_outputs(branch_name, stack_name=args.stack_name)
    role_arn = get_sagemaker_role_arn(stack_name)
    image_uri = f"{outputs['GaussianRepositoryUri']}:{get_branch_ecr_tag(branch_name)}"
    output_root_s3_uri = args.output_root_s3_uri or (
        f"s3://{outputs['MLBucketName']}/manual-validations/md1-geometry-r1-review-{timestamp}"
    )

    staged = stage_review_inputs(
        audit_root=args.audit_root,
        output_root_s3_uri=output_root_s3_uri,
        variants=variants,
        force_tarballs=args.force_tarballs,
        keep_local_tarballs=args.keep_local_tarballs,
    )
    jobs = run_review_jobs(
        branch_name=branch_name,
        image_uri=image_uri,
        role_arn=role_arn,
        colmap_s3_uri=args.colmap_s3_uri,
        output_root_s3_uri=output_root_s3_uri,
        review_camera_manifest_s3_uri=staged["review_camera_manifest_s3_uri"],
        staged_variants=staged["variants"],
        variants=variants,
        max_images_per_bucket=args.max_images_per_bucket,
        camera_set=args.camera_set,
        instance_type=args.instance_type,
        volume_size_gb=args.volume_size_gb,
        max_runtime_seconds=args.max_runtime_seconds,
        poll_seconds=args.poll_seconds,
        submit=args.submit,
        wait=args.wait,
        execution_mode=args.execution_mode,
        render_scale=args.render_scale,
        max_gaussians_per_view=args.max_gaussians_per_view,
        cull_margin=args.cull_margin,
        min_gaussians_on_oom=args.min_gaussians_on_oom,
        tile_ids=args.tile_ids,
    )
    if args.submit and args.wait and not args.skip_output_download:
        download_review_outputs(audit_root=args.audit_root, jobs=jobs)

    summary = {
        "branch": branch_name,
        "stack_name": stack_name,
        "stack_resolution": stack_resolution,
        "image_uri": image_uri,
        "role_arn": role_arn,
        "colmap_s3_uri": args.colmap_s3_uri,
        "output_root_s3_uri": output_root_s3_uri,
        "review_camera_manifest_s3_uri": staged["review_camera_manifest_s3_uri"],
        "execution_mode": args.execution_mode,
        "render_settings": {
            "render_scale": args.render_scale,
            "max_gaussians_per_view": args.max_gaussians_per_view,
            "cull_margin": args.cull_margin,
            "min_gaussians_on_oom": args.min_gaussians_on_oom,
            "tile_ids": args.tile_ids,
        },
        "variants": variants,
        "staged_inputs": staged["variants"],
        "jobs": jobs,
    }
    output_path = args.summary_json_output or (args.audit_root / "r1_review_summary.json")
    write_json(output_path, summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
