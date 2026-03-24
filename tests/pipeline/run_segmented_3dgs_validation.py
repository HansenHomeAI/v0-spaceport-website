#!/usr/bin/env python3
"""
Launch and monitor monolithic or segmented 3DGS validation jobs.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime

import boto3


REGION = "us-west-2"
ACCOUNT_ID = "975050048887"
DEFAULT_ROLE = "arn:aws:iam::975050048887:role/SpaceportMLPipelineStack-SageMakerExecutionRole7843-A4BBnjJAXLs8"
DEFAULT_3DGS_REPO = f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/spaceport/3dgs"
DEFAULT_COMPRESSOR_REPO = f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/spaceport/compressor:latest"
INSTANCE_HOURLY_USD = {
    "ml.g5.xlarge": 1.006,
    "ml.g5.2xlarge": 1.212,
    "ml.g4dn.xlarge": 0.526,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 3DGS validation jobs")
    parser.add_argument("--colmap-uri", required=True, help="S3 prefix containing COLMAP output")
    parser.add_argument("--output-prefix", required=True, help="Base S3 prefix for training outputs")
    parser.add_argument("--compressed-output-prefix", help="Optional S3 prefix for compressed outputs")
    parser.add_argument("--image-tag", default="latest", help="3DGS ECR image tag to use")
    parser.add_argument("--training-mode", choices=["monolithic", "segmented"], default="segmented")
    parser.add_argument("--target-gaussians", default="15000000")
    parser.add_argument("--max-tiles", default="6")
    parser.add_argument("--tile-max-iterations", default="8000")
    parser.add_argument("--max-iterations", default="30000")
    parser.add_argument("--instance-type", default="ml.g5.xlarge")
    parser.add_argument("--role-arn", default=DEFAULT_ROLE)
    parser.add_argument("--compress", action="store_true")
    parser.add_argument("--write-proof-artifacts", default="true")
    return parser.parse_args()


def wait_for_training_job(sagemaker, job_name: str) -> dict:
    while True:
        response = sagemaker.describe_training_job(TrainingJobName=job_name)
        status = response["TrainingJobStatus"]
        print(f"[training] {job_name}: {status}")
        if status in {"Completed", "Failed", "Stopped"}:
            return response
        time.sleep(30)


def wait_for_processing_job(sagemaker, job_name: str) -> dict:
    while True:
        response = sagemaker.describe_processing_job(ProcessingJobName=job_name)
        status = response["ProcessingJobStatus"]
        print(f"[processing] {job_name}: {status}")
        if status in {"Completed", "Failed", "Stopped"}:
            return response
        time.sleep(30)


def start_compression_job(sagemaker, output_prefix: str, compressed_output_prefix: str, job_name_root: str) -> dict:
    job_name = f"{job_name_root}-compression"
    sagemaker.create_processing_job(
        ProcessingJobName=job_name,
        AppSpecification={
            "ImageUri": DEFAULT_COMPRESSOR_REPO,
            "ContainerEntrypoint": ["python3", "compress.py"],
        },
        RoleArn=DEFAULT_ROLE,
        ProcessingResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.g4dn.xlarge",
                "VolumeSizeInGB": 50,
            }
        },
        ProcessingInputs=[
            {
                "InputName": "gaussian-model",
                "AppManaged": False,
                "S3Input": {
                    "S3Uri": output_prefix,
                    "LocalPath": "/opt/ml/processing/input",
                    "S3DataType": "S3Prefix",
                    "S3InputMode": "File",
                },
            }
        ],
        ProcessingOutputConfig={
            "Outputs": [
                {
                    "OutputName": "compressed-model",
                    "AppManaged": False,
                    "S3Output": {
                        "S3Uri": compressed_output_prefix,
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                }
            ]
        },
        StoppingCondition={"MaxRuntimeInSeconds": 3600},
    )
    return wait_for_processing_job(sagemaker, job_name)


def main() -> None:
    args = parse_args()
    sagemaker = boto3.client("sagemaker", region_name=REGION)

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    job_name_root = f"seg3dgs-{args.training_mode}-{timestamp}"
    training_job_name = f"{job_name_root}-3dgs"
    output_prefix = f"{args.output_prefix.rstrip('/')}/{job_name_root}/"

    environment = {
        "AWS_DEFAULT_REGION": REGION,
        "PYTHONUNBUFFERED": "1",
        "SAGEMAKER_PROGRAM": "train.py",
        "TORCH_CUDA_ARCH_LIST": "8.0 8.6",
        "CUDA_HOME": "/usr/local/cuda",
        "LD_LIBRARY_PATH": "/usr/local/cuda/lib64:/usr/local/cuda/lib",
        "LIBRARY_PATH": "/usr/local/cuda/lib64:/usr/local/cuda/lib",
        "MAX_ITERATIONS": str(args.max_iterations),
        "TARGET_PSNR": "35.0",
        "MODEL_VARIANT": "splatfacto-big",
        "SH_DEGREE": "3",
        "BILATERAL_PROCESSING": "true",
        "LOG_INTERVAL": "100",
        "FRAMEWORK": "nerfstudio",
        "METHODOLOGY": "vincent_woo_sutro_tower",
        "LICENSE": "apache_2_0",
        "COMMERCIAL_LICENSE": "true",
        "OUTPUT_FORMAT": "ply",
        "SOGS_COMPATIBLE": "true",
        "TRAINING_MODE": args.training_mode,
        "SEGMENTED_PROFILE": "landscape_v1",
        "SEG_TARGET_TOTAL_GAUSSIANS": str(args.target_gaussians),
        "SEG_MAX_TILES": str(args.max_tiles),
        "SEG_TILE_MAX_ITERATIONS": str(args.tile_max_iterations),
        "WRITE_PROOF_ARTIFACTS": str(args.write_proof_artifacts).lower(),
        "MODEL_OUTPUT_S3_URI": output_prefix,
        "TRAINING_JOB_NAME": training_job_name,
        "INSTANCE_TYPE": args.instance_type,
    }
    if args.compressed_output_prefix:
        environment["COMPRESSED_OUTPUT_S3_URI"] = (
            f"{args.compressed_output_prefix.rstrip('/')}/{job_name_root}/"
        )

    training_image = f"{DEFAULT_3DGS_REPO}:{args.image_tag}"
    print(f"starting training job {training_job_name}")
    sagemaker.create_training_job(
        TrainingJobName=training_job_name,
        AlgorithmSpecification={
            "TrainingImage": training_image,
            "TrainingInputMode": "File",
        },
        RoleArn=args.role_arn,
        InputDataConfig=[
            {
                "ChannelName": "training",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": args.colmap_uri,
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
                "CompressionType": "None",
                "RecordWrapperType": "None",
            }
        ],
        OutputDataConfig={"S3OutputPath": output_prefix},
        ResourceConfig={
            "InstanceType": args.instance_type,
            "InstanceCount": 1,
            "VolumeSizeInGB": 100,
        },
        StoppingCondition={"MaxRuntimeInSeconds": 7200},
        Environment=environment,
    )

    training_result = wait_for_training_job(sagemaker, training_job_name)
    if training_result["TrainingJobStatus"] != "Completed":
        print(json.dumps(training_result, indent=2, default=str))
        raise SystemExit(1)

    billable_seconds = training_result.get("BillableTimeInSeconds", 0)
    hourly_rate = INSTANCE_HOURLY_USD[args.instance_type]
    training_cost = billable_seconds * hourly_rate / 3600.0

    summary = {
        "training_job_name": training_job_name,
        "training_image": training_image,
        "training_mode": args.training_mode,
        "output_prefix": output_prefix,
        "model_artifact": training_result["ModelArtifacts"]["S3ModelArtifacts"],
        "billable_time_seconds": billable_seconds,
        "estimated_cost_usd": round(training_cost, 4),
    }

    if args.compress:
        if not args.compressed_output_prefix:
            raise SystemExit("--compress requires --compressed-output-prefix")
        compression_result = start_compression_job(
            sagemaker,
            output_prefix=output_prefix,
            compressed_output_prefix=f"{args.compressed_output_prefix.rstrip('/')}/{job_name_root}/",
            job_name_root=job_name_root,
        )
        summary["compression_job_name"] = compression_result["ProcessingJobName"]
        summary["compression_status"] = compression_result["ProcessingJobStatus"]
        summary["compressed_output_prefix"] = f"{args.compressed_output_prefix.rstrip('/')}/{job_name_root}/"

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
