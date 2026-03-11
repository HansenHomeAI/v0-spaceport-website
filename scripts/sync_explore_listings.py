#!/usr/bin/env python3
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple

import boto3


DEFAULT_TABLE_NAME = "Spaceport-ExploreListings-staging"
DEFAULT_THUMBNAIL_TRIGGER_URL = "https://spaces-thumbnail.hello-462.workers.dev/thumbnail"
DEFAULT_THUMBNAIL_BASE_URL = "https://spcprt.com/spaces"
DEFAULT_THUMBNAIL_RETRY_COUNT = 5
DEFAULT_THUMBNAIL_DELAY_SECONDS = 12


def load_manifest(path: Path) -> List[Dict[str, str]]:
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise ValueError("Manifest must be a JSON array")
    return data


def normalize_url(url: str) -> str:
    return url.strip().rstrip("/")


def build_expected_item(entry: Dict[str, str], thumbnail_base_url: str) -> Dict[str, Any]:
    slug = entry["viewerSlug"].strip()
    title = entry["title"].strip()
    location = entry.get("location", "").strip()
    viewer_url = normalize_url(entry["viewerUrl"])
    thumb_base = thumbnail_base_url.rstrip("/")
    thumbnail_url = f"{thumb_base}/{slug}/thumb.jpg"
    now = int(time.time())
    return {
        "listingId": slug,
        "viewerSlug": slug,
        "viewerTitle": title,
        "viewerUrl": viewer_url,
        "visibility": "public",
        "thumbnailUrl": thumbnail_url,
        "city": "",
        "state": location,
        "cityState": location,
        "projectId": "",
        "userSub": "",
        "createdAt": now,
        "updatedAt": now,
        "thumbnailStatus": "ready",
    }


def current_matches(existing: Dict[str, Any], expected: Dict[str, Any]) -> bool:
    for key in (
        "viewerSlug",
        "viewerTitle",
        "viewerUrl",
        "visibility",
        "thumbnailUrl",
        "city",
        "state",
        "cityState",
    ):
        if (existing.get(key) or "") != (expected.get(key) or ""):
            return False
    return True


def fetch_existing_items(table) -> Dict[str, Dict[str, Any]]:
    items: Dict[str, Dict[str, Any]] = {}
    scan_start_key = None
    while True:
        params: Dict[str, Any] = {}
        if scan_start_key:
            params["ExclusiveStartKey"] = scan_start_key
        response = table.scan(**params)
        for item in response.get("Items", []):
            listing_id = item.get("listingId")
            if listing_id:
                items[listing_id] = item
        scan_start_key = response.get("LastEvaluatedKey")
        if not scan_start_key:
            return items


def head_thumbnail(url: str) -> Tuple[bool, str]:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = response.headers.get("Content-Type", "")
            return response.status == 200 and content_type.lower().startswith("image/"), content_type
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # pragma: no cover - operational path
        return False, str(exc)


def trigger_thumbnail(trigger_url: str, token: str, slug: str, viewer_url: str) -> Dict[str, Any]:
    payload = json.dumps({
        "slug": slug,
        "viewerUrl": viewer_url,
        "force": True,
    }).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    if token:
        headers["X-Spaces-Token"] = token
    request = urllib.request.Request(trigger_url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def generate_thumbnail_with_retries(
    *,
    thumbnail_trigger_url: str,
    thumbnail_token: str,
    slug: str,
    viewer_url: str,
    thumbnail_url: str,
    retry_count: int,
    delay_seconds: int,
) -> Tuple[bool, Dict[str, Any]]:
    attempt = 0
    last_reason = "not attempted"
    last_trigger: Dict[str, Any] = {}
    while attempt < retry_count:
        attempt += 1
        try:
            last_trigger = trigger_thumbnail(
                thumbnail_trigger_url,
                thumbnail_token,
                slug,
                viewer_url,
            )
            thumb_ok, thumb_meta = head_thumbnail(thumbnail_url)
            if thumb_ok:
                return True, {
                    "attempt": attempt,
                    "trigger": last_trigger,
                    "contentType": thumb_meta,
                }
            last_reason = thumb_meta
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_reason = f"HTTP {exc.code}: {body[:400]}"
        except Exception as exc:  # pragma: no cover - operational path
            last_reason = str(exc)

        if attempt < retry_count:
            time.sleep(delay_seconds)

    return False, {
        "attempt": attempt,
        "reason": last_reason,
        "trigger": last_trigger,
    }


def sync_manifest(
    *,
    manifest_path: Path,
    table_name: str,
    thumbnail_trigger_url: str,
    thumbnail_token: str,
    thumbnail_base_url: str,
    thumbnail_retry_count: int,
    thumbnail_delay_seconds: int,
) -> Dict[str, Any]:
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)
    manifest = load_manifest(manifest_path)
    existing_items = fetch_existing_items(table)
    desired_listing_ids = set()
    results = {
        "created": [],
        "updated": [],
        "unchanged": [],
        "deleted": [],
        "thumbnailGenerated": [],
        "thumbnailVerified": [],
        "thumbnailFailed": [],
    }

    for entry in manifest:
        expected = build_expected_item(entry, thumbnail_base_url)
        listing_id = expected["listingId"]
        desired_listing_ids.add(listing_id)
        existing = existing_items.get(listing_id)

        if existing and current_matches(existing, expected):
            expected["createdAt"] = existing.get("createdAt", expected["createdAt"])
            expected["updatedAt"] = existing.get("updatedAt", expected["updatedAt"])
            results["unchanged"].append(listing_id)
        else:
            if existing:
                expected["createdAt"] = existing.get("createdAt", expected["createdAt"])
            table.put_item(Item=expected)
            results["updated" if existing else "created"].append(listing_id)

        thumb_ok, thumb_meta = head_thumbnail(expected["thumbnailUrl"])
        if thumb_ok:
            results["thumbnailVerified"].append({"listingId": listing_id, "contentType": thumb_meta})
            continue

        generated, detail = generate_thumbnail_with_retries(
            thumbnail_trigger_url=thumbnail_trigger_url,
            thumbnail_token=thumbnail_token,
            slug=expected["viewerSlug"],
            viewer_url=expected["viewerUrl"],
            thumbnail_url=expected["thumbnailUrl"],
            retry_count=thumbnail_retry_count,
            delay_seconds=thumbnail_delay_seconds,
        )
        if generated:
            results["thumbnailGenerated"].append({
                "listingId": listing_id,
                **detail,
            })
        else:
            results["thumbnailFailed"].append({
                "listingId": listing_id,
                **detail,
            })

    for listing_id in sorted(existing_items):
        if listing_id not in desired_listing_ids:
            table.delete_item(Key={"listingId": listing_id})
            results["deleted"].append(listing_id)

    return {
        "tableName": table_name,
        "manifestPath": str(manifest_path),
        "desiredCount": len(desired_listing_ids),
        **results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync curated Explore listings into DynamoDB.")
    parser.add_argument(
        "--manifest",
        default="scripts/explore_listings_manifest.json",
        help="Path to the manifest JSON file.",
    )
    parser.add_argument(
        "--table-name",
        default=DEFAULT_TABLE_NAME,
        help="DynamoDB table name for Explore listings.",
    )
    parser.add_argument(
        "--thumbnail-trigger-url",
        default=DEFAULT_THUMBNAIL_TRIGGER_URL,
        help="Thumbnail worker endpoint used to generate screenshots.",
    )
    parser.add_argument(
        "--thumbnail-token",
        default="",
        help="Optional thumbnail worker auth token.",
    )
    parser.add_argument(
        "--thumbnail-base-url",
        default=DEFAULT_THUMBNAIL_BASE_URL,
        help="Base URL used when storing thumbnailUrl in the listing records.",
    )
    parser.add_argument(
        "--thumbnail-retry-count",
        type=int,
        default=DEFAULT_THUMBNAIL_RETRY_COUNT,
        help="How many times to retry generating a missing thumbnail.",
    )
    parser.add_argument(
        "--thumbnail-delay-seconds",
        type=int,
        default=DEFAULT_THUMBNAIL_DELAY_SECONDS,
        help="Delay between sequential thumbnail retries.",
    )
    args = parser.parse_args()

    result = sync_manifest(
        manifest_path=Path(args.manifest),
        table_name=args.table_name,
        thumbnail_trigger_url=args.thumbnail_trigger_url,
        thumbnail_token=args.thumbnail_token,
        thumbnail_base_url=args.thumbnail_base_url,
        thumbnail_retry_count=args.thumbnail_retry_count,
        thumbnail_delay_seconds=args.thumbnail_delay_seconds,
    )
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
