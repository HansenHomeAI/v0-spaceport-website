#!/usr/bin/env python3
"""Automate Spaceport model delivery deployment.

This CLI ingests a generated viewer bundle (single HTML file or directory),
uploads it to the public S3 bucket used for client deliveries, ensures caching
headers are optimized, optionally provisions the bucket, warms Cloudflare, and
prints the canonical public URL (`https://spcprt.com/model/<slug>` by default).

Usage example:
    python3 scripts/deployment/deploy_model.py ./viewer.html "Rooftop Scan"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import mimetypes
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import boto3
from botocore.exceptions import ClientError
import requests

LOG = logging.getLogger(__name__)
DEFAULT_REGION = os.environ.get("SPACEPORT_MODEL_REGION", "us-west-2")
DEFAULT_BUCKET = os.environ.get("SPACEPORT_MODEL_BUCKET", "spaceport-model-delivery-prod")
DEFAULT_PREFIX = os.environ.get("SPACEPORT_MODEL_PREFIX", "models")
DEFAULT_DOMAIN = os.environ.get("SPACEPORT_MODEL_DOMAIN", "https://spcprt.com/model")
DEFAULT_HASH_LENGTH = int(os.environ.get("SPACEPORT_MODEL_HASH_LENGTH", "8"))
DEFAULT_HTML_CACHE_SECONDS = int(os.environ.get("SPACEPORT_MODEL_HTML_CACHE", "60"))
DEFAULT_ASSET_CACHE_SECONDS = int(os.environ.get("SPACEPORT_MODEL_ASSET_CACHE", str(30 * 24 * 3600)))

ENV_CLOUDFLARE_ZONE = os.environ.get("SPACEPORT_MODEL_CLOUDFLARE_ZONE_ID")
ENV_CLOUDFLARE_TOKEN = os.environ.get("SPACEPORT_MODEL_CLOUDFLARE_TOKEN")


@dataclass(frozen=True)
class UploadItem:
    """File slated for upload."""

    source: Path
    dest_key: str

    @property
    def extension(self) -> str:
        return self.source.suffix.lower()


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def slugify_project(name: str, *, max_length: int = 48) -> str:
    """Convert project name to filesystem-safe slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("- ")
    if not cleaned:
        cleaned = "model"
    slug = cleaned.lower()
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "model"


def build_hash(sources: Sequence[Path], hash_length: int) -> str:
    """Compute a deterministic short hash from the provided files."""
    hasher = hashlib.sha256()
    for path in sorted(sources, key=lambda p: p.as_posix()):
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
    return hasher.hexdigest()[:hash_length]


def collect_upload_items(input_path: Path, prefix: str, slug: str, *, entrypoint: Optional[str]) -> Tuple[List[UploadItem], Path]:
    """Return files to upload and the resolved root directory."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    target_root: Path
    items: List[UploadItem] = []
    safe_prefix = prefix.strip("/")

    if input_path.is_file():
        root = input_path.parent
        entry_name = entrypoint or input_path.name
        if not entry_name.lower().endswith(".html"):
            LOG.warning("Entrypoint %s is not an HTML file", entry_name)
        key = f"{safe_prefix}/{slug}/{entry_name}"
        items.append(UploadItem(source=input_path, dest_key=key))
        target_root = root
    elif input_path.is_dir():
        target_root = input_path
        index_name = entrypoint or "index.html"
        index_path = target_root / index_name
        if not index_path.exists():
            raise FileNotFoundError(f"Expected entrypoint '{index_name}' inside {input_path}")
        for path in sorted(target_root.rglob("*")):
            if path.is_dir():
                continue
            rel_path = path.relative_to(target_root)
            dest_key = f"{safe_prefix}/{slug}/{rel_path.as_posix()}"
            items.append(UploadItem(source=path, dest_key=dest_key))
    else:
        raise ValueError(f"Unsupported input path type: {input_path}")

    return items, target_root


def ensure_bucket(client, bucket: str, region: str, *, create: bool = False) -> None:
    """Verify the target bucket exists and is public; optionally create it."""
    try:
        client.head_bucket(Bucket=bucket)
        LOG.debug("Bucket %s already exists", bucket)
        return
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code not in ("404", "NoSuchBucket"):
            raise
        if not create:
            raise RuntimeError(f"Bucket {bucket} does not exist. Pass --create-bucket to provision it.")

    params: Dict[str, object] = {"Bucket": bucket}
    if region != "us-east-1":
        params["CreateBucketConfiguration"] = {"LocationConstraint": region}
    LOG.info("Creating bucket %s in %s", bucket, region)
    client.create_bucket(**params)
    client.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowPublicRead",
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"],
            }
        ],
    }
    client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))


def upload_files(
    s3_client,
    bucket: str,
    items: Sequence[UploadItem],
    *,
    html_cache_seconds: int,
    asset_cache_seconds: int,
) -> List[Dict[str, str]]:
    """Upload collection of items; return manifest describing uploads."""
    manifest: List[Dict[str, str]] = []
    for item in items:
        extra_args: Dict[str, str] = {}
        content_type, _ = mimetypes.guess_type(item.source.name)
        if content_type:
            extra_args["ContentType"] = content_type
        else:
            extra_args["ContentType"] = "application/octet-stream"

        if item.source.suffix.lower() in {".html", ".htm"}:
            extra_args["CacheControl"] = f"public, max-age={html_cache_seconds}, must-revalidate"
        else:
            extra_args["CacheControl"] = f"public, max-age={asset_cache_seconds}, immutable"

        extra_args["ACL"] = "public-read"

        LOG.debug("Uploading %s -> s3://%s/%s", item.source, bucket, item.dest_key)
        s3_client.upload_file(str(item.source), bucket, item.dest_key, ExtraArgs=extra_args)

        manifest.append(
            {
                "key": item.dest_key,
                "content_type": extra_args["ContentType"],
                "cache_control": extra_args["CacheControl"],
                "size_bytes": str(item.source.stat().st_size),
            }
        )
    return manifest


def purge_cloudflare(zone_id: Optional[str], token: Optional[str], urls: Sequence[str]) -> Optional[Dict[str, object]]:
    if not zone_id or not token or not urls:
        LOG.debug("Skipping Cloudflare purge (missing zone/token or urls)")
        return None

    endpoint = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"files": list(urls)}
    LOG.debug("Purging Cloudflare cache for %s", urls)
    response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
    if response.ok:
        LOG.info("Cloudflare purge accepted (%s)", response.status_code)
    else:
        LOG.warning("Cloudflare purge failed: %s - %s", response.status_code, response.text)
    return {"status": response.status_code, "body": response.json() if response.text else {}}


def verify_http_access(url: str, *, timeout: float = 10.0) -> Dict[str, object]:
    start = time.time()
    try:
        response = requests.get(url, timeout=timeout)
        latency = time.time() - start
        return {
            "status": response.status_code,
            "latency_seconds": round(latency, 3),
            "content_length": int(response.headers.get("content-length", "0")),
        }
    except requests.RequestException as exc:
        return {
            "status": None,
            "error": str(exc),
        }


def compose_live_url(domain_base: str, slug: str) -> str:
    trimmed = domain_base.rstrip("/")
    if trimmed.endswith("/model"):
        return f"{trimmed}/{slug}"
    return f"{trimmed.rstrip('/')}/{slug}"


def build_s3_https_url(bucket: str, region: str, key: str) -> str:
    base = f"https://{bucket}.s3.amazonaws.com" if region == "us-east-1" else f"https://{bucket}.s3.{region}.amazonaws.com"
    return f"{base}/{key}"


def parse_metadata(items: Sequence[str]) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    for entry in items:
        if "=" not in entry:
            raise ValueError(f"Invalid metadata entry '{entry}'. Expected key=value format.")
        key, value = entry.split("=", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def write_metadata_file(
    s3_client,
    bucket: str,
    manifest: Dict[str, object],
    *,
    key: str,
) -> None:
    payload = json.dumps(manifest, indent=2)
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=payload.encode("utf-8"),
        ContentType="application/json",
        CacheControl="public, max-age=300, must-revalidate",
        ACL="public-read",
    )


def run(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Deploy a Spaceport model viewer bundle")
    parser.add_argument("input", type=str, help="Path to HTML file or directory")
    parser.add_argument("project_name", type=str, help="Human-readable project name")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--domain", default=DEFAULT_DOMAIN, help="Base domain for live URL (eg. https://spcprt.com/model)")
    parser.add_argument("--hash-length", type=int, default=DEFAULT_HASH_LENGTH)
    parser.add_argument("--entrypoint", type=str, default=None, help="Override HTML entrypoint filename")
    parser.add_argument("--create-bucket", action="store_true", help="Create the bucket if it does not exist")
    parser.add_argument("--metadata", nargs="*", default=[], help="Additional metadata entries (key=value)")
    parser.add_argument("--html-cache-seconds", type=int, default=DEFAULT_HTML_CACHE_SECONDS)
    parser.add_argument("--asset-cache-seconds", type=int, default=DEFAULT_ASSET_CACHE_SECONDS)
    parser.add_argument("--skip-http-check", action="store_true", help="Skip verifying the live URL after upload")
    parser.add_argument("--purge-cloudflare", action="store_true", help="Purge Cloudflare cache for the new URL")
    parser.add_argument("--cloudflare-zone-id", default=ENV_CLOUDFLARE_ZONE)
    parser.add_argument("--cloudflare-token", default=ENV_CLOUDFLARE_TOKEN)
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs without uploading")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    configure_logging(args.verbose)

    input_path = Path(args.input).resolve()
    slug_root = slugify_project(args.project_name)
    LOG.debug("Derived slug root: %s", slug_root)

    # Determine slug by hashing content
    if input_path.is_file():
        source_paths = [input_path]
    elif input_path.is_dir():
        source_paths = [p for p in input_path.rglob("*") if p.is_file()]
        if not source_paths:
            raise RuntimeError(f"Directory {input_path} is empty")
    else:
        raise RuntimeError(f"Unsupported input path: {input_path}")

    short_hash = build_hash(source_paths, args.hash_length)
    slug = f"{slug_root}-{short_hash}"
    LOG.info("Using slug %s", slug)

    items, root_dir = collect_upload_items(input_path, args.prefix, slug, entrypoint=args.entrypoint)
    LOG.info("Prepared %d files for upload (root=%s)", len(items), root_dir)

    if args.dry_run:
        print(json.dumps({
            "slug": slug,
            "files": [item.dest_key for item in items],
            "bucket": args.bucket,
            "region": args.region,
            "domain": args.domain,
        }, indent=2))
        return 0

    session = boto3.session.Session(region_name=args.region)
    s3_client = session.client("s3")

    ensure_bucket(s3_client, args.bucket, args.region, create=args.create_bucket)

    manifest = upload_files(
        s3_client,
        args.bucket,
        items,
        html_cache_seconds=args.html_cache_seconds,
        asset_cache_seconds=args.asset_cache_seconds,
    )

    s3_base_key = f"{args.prefix.strip('/')}/{slug}"
    metadata = parse_metadata(args.metadata)
    metadata_payload = {
        "project": args.project_name,
        "slug": slug,
        "bucket": args.bucket,
        "region": args.region,
        "prefix": args.prefix,
        "domain": args.domain,
        "uploaded_at": int(time.time()),
        "files": manifest,
        "metadata": metadata,
    }

    metadata_key = f"{s3_base_key}/manifest.json"
    write_metadata_file(s3_client, args.bucket, metadata_payload, key=metadata_key)

    live_url = compose_live_url(args.domain, slug)
    origin_html_url = build_s3_https_url(args.bucket, args.region, f"{s3_base_key}/index.html")

    purge_result = None
    if args.purge_cloudflare:
        purge_result = purge_cloudflare(args.cloudflare_zone_id, args.cloudflare_token, [live_url])

    http_check: Optional[Dict[str, object]] = None
    if not args.skip_http_check:
        http_check = verify_http_access(origin_html_url)

    result = {
        "slug": slug,
        "live_url": live_url,
        "s3_bucket": args.bucket,
        "s3_region": args.region,
        "s3_prefix": args.prefix,
        "s3_index_url": origin_html_url,
        "metadata_key": metadata_key,
        "cloudflare_purge": purge_result,
        "http_check": http_check,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run())
