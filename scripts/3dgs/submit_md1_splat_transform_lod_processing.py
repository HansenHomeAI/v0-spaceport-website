#!/usr/bin/env python3
"""Build or submit the MD1 V18 SuperSplat LOD Processing job payload.

This intentionally uses the validated PlayCanvas `splat-transform` compressor
image. It does not use the removed bespoke MD1 chunk builder.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


DEFAULT_IMAGE_URI = (
    "975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor"
    "@sha256:645fd74b9217fc8441f242d8b89aefb36ef9c88192bf006ade3cfeb355bd4de3"
)
DEFAULT_ROLE_ARN = "arn:aws:iam::975050048887:role/Spaceport-SageMaker-Role-staging"
DEFAULT_INPUT_PREFIX = "s3://spaceport-ml-processing/compressed/md1-r5-v18-raw-1777498999/"
DEFAULT_OUTPUT_BASE = "s3://spaceport-ml-processing/compressed"
DEFAULT_DIRECT_SCRIPT_PATH = Path(__file__).with_name("md1_splat_transform_direct_lod.sh")
DEFAULT_PROJECT_TAG = "md1-production-viewer"
DEFAULT_SOURCE_LINEAGE_LABEL = "md1-v18-promoted-raw-ply"
DEFAULT_SOURCE_PLY = "/opt/ml/processing/input/merged_splat.ply"
DEFAULT_SOURCE_SKYBOX = "/opt/ml/processing/input/background_skybox.webp"


def build_payload(args: argparse.Namespace) -> dict:
    job_name = args.job_name or f"md1-v18-splat-lod-{int(time.time())}"
    output_prefix = args.output_prefix or f"{DEFAULT_OUTPUT_BASE}/{job_name.replace('md1-v18-splat-lod-', 'md1-r5-v18-splattransform-lod-')}/"
    direct_script_s3_prefix = (
        args.direct_script_s3_prefix
        or f"{output_prefix.rstrip('/')}/entrypoint/"
    )
    app_specification = {"ImageUri": args.image_uri}
    if args.direct_lod_only:
        app_specification["ContainerEntrypoint"] = [
            "/bin/bash",
            f"/opt/ml/processing/script/{Path(args.direct_script_path).name}",
        ]

    inputs = [
        {
            "InputName": "source-ply",
            "S3Input": {
                "S3Uri": args.input_prefix,
                "LocalPath": "/opt/ml/processing/input",
                "S3DataType": "S3Prefix",
                "S3InputMode": "File",
                "S3DataDistributionType": "FullyReplicated",
                "S3CompressionType": "None",
            },
        }
    ]
    if args.direct_lod_only:
        inputs.append(
            {
                "InputName": "direct-lod-entrypoint",
                "S3Input": {
                    "S3Uri": direct_script_s3_prefix,
                    "LocalPath": "/opt/ml/processing/script",
                    "S3DataType": "S3Prefix",
                    "S3InputMode": "File",
                    "S3DataDistributionType": "FullyReplicated",
                    "S3CompressionType": "None",
                },
            }
        )

    payload = {
        "ProcessingJobName": job_name,
        "RoleArn": args.role_arn,
        "AppSpecification": app_specification,
        "ProcessingInputs": inputs,
        "ProcessingOutputConfig": {
            "Outputs": [
                {
                    "OutputName": "supersplat-bundle",
                    "S3Output": {
                        "S3Uri": output_prefix,
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                }
            ]
        },
        "ProcessingResources": {
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": args.instance_type,
                "VolumeSizeInGB": args.volume_size_gb,
            }
        },
        "StoppingCondition": {"MaxRuntimeInSeconds": args.max_runtime_seconds},
        "Environment": {
            "MD1_SOURCE_LINEAGE_LABEL": args.source_label,
            "MD1_SOURCE_PLY": args.source_ply,
            "MD1_SOURCE_SKYBOX": args.source_skybox,
            "SOGS_DEVICE": args.device,
            "SOGS_LOD_DECIMATION": args.lod_decimation,
            "SOGS_LOD_CHUNK_COUNT": str(args.lod_chunk_count),
            "SOGS_LOD_CHUNK_EXTENT": str(args.lod_chunk_extent),
        },
        "Tags": [
            {"Key": "project", "Value": args.project_tag},
            {
                "Key": "source",
                "Value": "validated-splat-transform-lod-compressor"
                + ("-direct-lod" if args.direct_lod_only else ""),
            },
            {"Key": "source-lineage", "Value": args.source_label[:256]},
            {"Key": "branch", "Value": args.branch},
        ],
    }
    if args.direct_lod_only:
        payload["DirectScriptS3Prefix"] = direct_script_s3_prefix
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-name")
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--role-arn", default=DEFAULT_ROLE_ARN)
    parser.add_argument("--image-uri", default=DEFAULT_IMAGE_URI)
    parser.add_argument("--input-prefix", default=DEFAULT_INPUT_PREFIX)
    parser.add_argument("--output-prefix")
    parser.add_argument("--instance-type", default="ml.m5.4xlarge")
    parser.add_argument("--volume-size-gb", type=int, default=200)
    parser.add_argument("--max-runtime-seconds", type=int, default=21600)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--lod-decimation", default="30%,10%,3%")
    parser.add_argument("--lod-chunk-count", type=int, default=256)
    parser.add_argument("--lod-chunk-extent", type=int, default=32)
    parser.add_argument("--source-label", default=DEFAULT_SOURCE_LINEAGE_LABEL)
    parser.add_argument("--source-ply", default=DEFAULT_SOURCE_PLY)
    parser.add_argument("--source-skybox", default=DEFAULT_SOURCE_SKYBOX)
    parser.add_argument("--project-tag", default=DEFAULT_PROJECT_TAG)
    parser.add_argument("--branch", default="agent-90742618-md1-geometry-consistency")
    parser.add_argument("--payload-out", default="")
    parser.add_argument("--direct-lod-only", action="store_true")
    parser.add_argument("--direct-script-path", default=str(DEFAULT_DIRECT_SCRIPT_PATH))
    parser.add_argument("--direct-script-s3-prefix", default="")
    parser.add_argument("--submit", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    direct_script_s3_prefix = payload.pop("DirectScriptS3Prefix", "")
    payload_json = json.dumps(payload, indent=2)
    if args.payload_out:
        output_path = Path(args.payload_out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload_json + "\n", encoding="utf-8")
        cli_input = f"file://{output_path}"
    else:
        cli_input = payload_json
    print(payload_json)

    if args.submit:
        if args.direct_lod_only:
            script_path = Path(args.direct_script_path)
            target = f"{direct_script_s3_prefix.rstrip('/')}/{script_path.name}"
            subprocess.run(["aws", "s3", "cp", str(script_path), target], check=True)
        cmd = [
            "aws",
            "sagemaker",
            "create-processing-job",
            "--region",
            args.region,
            "--cli-input-json",
            cli_input,
        ]
        subprocess.run(cmd, check=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
