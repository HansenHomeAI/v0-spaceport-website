import mimetypes
import os
from typing import Dict, List, Tuple

import boto3


s3 = boto3.client("s3")

# Immutable assets let the CDN keep cold-path fetches predictable once published.
CACHE_CONTROL = "public, max-age=31536000, s-maxage=31536000, immutable"


def parse_s3_uri(uri: str) -> Tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {uri}")
    without_scheme = uri[len("s3://") :]
    bucket, _, key = without_scheme.partition("/")
    if not bucket:
        raise ValueError(f"Invalid S3 URI: {uri}")
    return bucket, key.rstrip("/")


def content_type_for_key(key: str) -> str:
    guessed_type, _ = mimetypes.guess_type(key)
    return guessed_type or "application/octet-stream"


def copy_bundle_objects(
    *,
    source_bucket: str,
    source_prefix: str,
    destination_bucket: str,
    destination_prefix: str,
) -> Tuple[List[str], bool]:
    paginator = s3.get_paginator("list_objects_v2")
    copied_keys: List[str] = []
    found_meta = False
    found_lod_meta = False

    for page in paginator.paginate(Bucket=source_bucket, Prefix=source_prefix):
        for entry in page.get("Contents", []):
            source_key = entry["Key"]
            relative_key = source_key[len(source_prefix) :].lstrip("/")
            if not relative_key:
                continue

            if relative_key == "meta.json":
                found_meta = True
            elif relative_key == "lod-meta.json":
                found_lod_meta = True

            destination_key = f"{destination_prefix}/{relative_key}"
            s3.copy_object(
                Bucket=destination_bucket,
                Key=destination_key,
                CopySource={"Bucket": source_bucket, "Key": source_key},
                CacheControl=CACHE_CONTROL,
                ContentType=content_type_for_key(relative_key),
                MetadataDirective="REPLACE",
            )
            copied_keys.append(destination_key)

    if not found_meta:
        raise ValueError(f"Missing {source_prefix}/meta.json in {source_bucket}")

    return copied_keys, found_lod_meta


def lambda_handler(event: Dict, context) -> Dict:
    job_id = (event.get("jobId") or "").strip()
    compressed_output_s3_uri = (event.get("compressedOutputS3Uri") or "").strip()
    delivery_bucket = os.environ["DELIVERY_BUCKET"]
    edge_distribution_domain = os.environ["EDGE_DISTRIBUTION_DOMAIN"].strip()

    if not job_id:
        raise ValueError("Missing required field: jobId")
    if not compressed_output_s3_uri:
        raise ValueError("Missing required field: compressedOutputS3Uri")

    source_bucket, source_root_prefix = parse_s3_uri(compressed_output_s3_uri)
    source_bundle_prefix = f"{source_root_prefix}/supersplat_bundle".strip("/")
    destination_prefix = f"models/{job_id}/supersplat_bundle"

    copied_keys, found_lod_meta = copy_bundle_objects(
        source_bucket=source_bucket,
        source_prefix=f"{source_bundle_prefix}/",
        destination_bucket=delivery_bucket,
        destination_prefix=destination_prefix,
    )

    edge_bundle_url = f"https://{edge_distribution_domain}/{destination_prefix}/meta.json"
    result = {
        "jobId": job_id,
        "sourceBundleS3Uri": f"s3://{source_bucket}/{source_bundle_prefix}/",
        "deliveryBucket": delivery_bucket,
        "deliveryPrefix": f"{destination_prefix}/",
        "edgeBundleUrl": edge_bundle_url,
        "copiedObjectCount": len(copied_keys),
    }
    if found_lod_meta:
        result["edgeLodBundleUrl"] = f"https://{edge_distribution_domain}/{destination_prefix}/lod-meta.json"
    return result
