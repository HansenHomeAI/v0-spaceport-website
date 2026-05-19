#!/usr/bin/env python3
"""Publish a compressed SuperSplat bundle to the edge delivery bucket.

This is a thin wrapper around the deployed `ml_publish_bundle` Lambda:
  infrastructure/spaceport_cdk/lambda/ml_publish_bundle/lambda_function.py

It writes the Lambda JSON response and (optionally) validates that the returned
edgeBundleUrl is publicly reachable with browser-friendly headers. When strict
validation is enabled, this script checks:
  - the meta.json URL is readable cross-origin (CORS) with an Origin header
  - cache headers are long-lived (immutable) for public delivery
  - all `files` referenced by meta.json are also readable cross-origin
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


HOMEBREW_AWS = Path("/opt/homebrew/bin/aws")

def escape_html(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def resolve_aws() -> str:
    return str(HOMEBREW_AWS) if HOMEBREW_AWS.exists() else "aws"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--function-name", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--compressed-output-s3-uri", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--validate-http", action="store_true")
    parser.add_argument(
        "--require-browser-headers",
        action="store_true",
        help="Fail if the published meta.json is not browser-readable (HTTP 200, Content-Type JSON, CORS, caching).",
    )
    parser.add_argument(
        "--origin",
        default="https://example.com",
        help="Origin header value used for CORS validation when --require-browser-headers is set.",
    )
    parser.add_argument(
        "--html-report",
        default="",
        help="Optional path to write a browser-readable HTML summary of the published bundle and asset URLs.",
    )
    return parser.parse_args()

def parse_http_headers(raw: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.lower().startswith("http/"):
            headers["__status_line__"] = line.strip()
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    return headers


@dataclass(frozen=True)
class HttpHead:
    url: str
    raw: str
    headers: dict[str, str]

def curl_head(url: str, *, origin: str | None = None) -> str:
    cmd = ["curl", "-sS", "-I"]
    if origin is not None:
        cmd += ["-H", f"Origin: {origin}"]
    cmd.append(url)
    return subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ).stdout

def assert_browser_readable(head: HttpHead, *, expect_json: bool, origin: str) -> None:
    headers = head.headers
    status = headers.get("__status_line__", "")
    if " 200 " not in status and not status.endswith(" 200"):
        raise RuntimeError(f"edge bundle URL is not reachable (status={status or '<missing>'})")

    cache_control = (headers.get("cache-control") or "").lower()
    if not cache_control:
        raise RuntimeError("edge bundle response missing cache-control header")
    if "no-store" in cache_control:
        raise RuntimeError(f"edge bundle cache-control blocks caching: {cache_control}")
    if "immutable" not in cache_control:
        raise RuntimeError(f"edge bundle cache-control missing immutable: {cache_control}")
    if "max-age" not in cache_control:
        raise RuntimeError(f"edge bundle cache-control missing max-age: {cache_control}")

    cors = (headers.get("access-control-allow-origin") or "").strip()
    if cors not in {"*", origin}:
        raise RuntimeError(f"edge bundle missing/invalid CORS allow-origin for Origin={origin}: {cors or '<missing>'}")

    if expect_json:
        content_type = (headers.get("content-type") or "").lower()
        if "json" not in content_type:
            raise RuntimeError(f"edge bundle meta.json Content-Type not JSON: {content_type or '<missing>'}")

def iter_meta_files(meta: dict[str, object]) -> list[str]:
    files: list[str] = []
    for value in meta.values():
        if not isinstance(value, dict):
            continue
        maybe_files = value.get("files")
        if not isinstance(maybe_files, list):
            continue
        for item in maybe_files:
            if isinstance(item, str) and item.strip():
                files.append(item.strip())
    # preserve order but de-dupe
    seen: set[str] = set()
    unique: list[str] = []
    for item in files:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique

def build_asset_url(meta_url: str, filename: str) -> str:
    meta_url = meta_url.strip()
    if not meta_url.endswith("/meta.json"):
        raise ValueError(f"expected meta.json url, got: {meta_url}")
    return f"{meta_url[:-len('meta.json')]}{filename.lstrip('/')}"

def write_html_report(
    *,
    path: Path,
    edge_url: str,
    origin: str,
    meta: dict[str, object] | None,
    asset_urls: list[str],
    assets_heads: dict[str, str],
) -> None:
    rows: list[str] = []
    for url in asset_urls:
        head_raw = assets_heads.get(url, "")
        status_line = parse_http_headers(head_raw).get("__status_line__", "") if head_raw else ""
        rows.append(
            "<tr>"
            f"<td><a href=\"{escape_html(url)}\">{escape_html(url.split('/')[-1])}</a></td>"
            f"<td><code>{escape_html(status_line or '<missing>')}</code></td>"
            "</tr>"
        )

    meta_section = "<p>meta.json not captured (run with <code>--require-browser-headers</code> to download it)</p>"
    if meta is not None:
        keys = ", ".join(escape_html(key) for key in sorted(str(k) for k in meta.keys()))
        meta_section = f"<p><strong>meta keys</strong>: <code>{keys}</code></p>"

    html = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Edge bundle delivery report</title>
    <style>
      body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif; margin: 24px; }}
      code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
      table {{ border-collapse: collapse; width: 100%; }}
      th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
      th {{ background: #f6f6f6; text-align: left; }}
    </style>
  </head>
  <body>
    <h1>Edge bundle delivery report</h1>
    <p><strong>edge meta.json</strong>: <a href="{escape_html(edge_url)}">{escape_html(edge_url)}</a></p>
    <p><strong>origin probe</strong>: <code>{escape_html(origin)}</code></p>
    {meta_section}
    <h2>Assets</h2>
    <table>
      <thead>
        <tr>
          <th>file</th>
          <th>status</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows) if rows else '<tr><td colspan=\"2\">none</td></tr>'}
      </tbody>
    </table>
  </body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")

def main() -> int:
    args = parse_args()
    payload = {"jobId": args.job_id, "compressedOutputS3Uri": args.compressed_output_s3_uri}
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    aws = resolve_aws()

    invoke_out = output_path.with_suffix(".lambda-response.json")
    subprocess.run(
        [
            aws,
            "lambda",
            "invoke",
            "--cli-binary-format",
            "raw-in-base64-out",
            "--function-name",
            args.function_name,
            "--payload",
            json.dumps(payload),
            str(invoke_out),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    result = json.loads(invoke_out.read_text(encoding="utf-8"))
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    edge_url = (result.get("edgeBundleUrl") or "").strip()
    if not edge_url:
        raise RuntimeError(f"Lambda result missing edgeBundleUrl: {result}")

    print(f"OK edgeBundleUrl={edge_url}")

    meta: dict[str, object] | None = None
    asset_urls: list[str] = []
    assets_out: dict[str, dict[str, str]] = {}
    if args.validate_http or args.require_browser_headers:
        head_path = output_path.with_suffix(".curl-head.txt")
        head = curl_head(edge_url)
        head_path.write_text(head, encoding="utf-8")
        print(f"OK httpHead={head_path}")

        if args.require_browser_headers:
            origin_head_path = output_path.with_suffix(".curl-head-origin.txt")
            origin_head = curl_head(edge_url, origin=args.origin)
            origin_head_path.write_text(origin_head, encoding="utf-8")
            print(f"OK httpHeadOrigin={origin_head_path}")

            assert_browser_readable(
                HttpHead(url=edge_url, raw=origin_head, headers=parse_http_headers(origin_head)),
                expect_json=True,
                origin=args.origin,
            )

            meta = json.loads(
                subprocess.run(
                    ["curl", "-sS", edge_url],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                ).stdout
            )
            meta_path = output_path.with_suffix(".meta.json")
            meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
            print(f"OK metaJson={meta_path}")

            asset_urls = [build_asset_url(edge_url, filename) for filename in iter_meta_files(meta)]
            for url in asset_urls:
                asset_head = curl_head(url, origin=args.origin)
                assets_out[url] = {"head": asset_head}
                asset_headers = parse_http_headers(asset_head)
                assert_browser_readable(
                    HttpHead(url=url, raw=asset_head, headers=asset_headers),
                    expect_json=False,
                    origin=args.origin,
                )
            assets_path = output_path.with_suffix(".assets.json")
            assets_path.write_text(json.dumps(assets_out, indent=2) + "\n", encoding="utf-8")
            print(f"OK assetsHead={assets_path}")

    if args.html_report:
        report_path = Path(args.html_report)
        assets_heads = {url: item.get("head", "") for url, item in assets_out.items()}
        if meta is not None and not asset_urls:
            asset_urls = [build_asset_url(edge_url, filename) for filename in iter_meta_files(meta)]
        write_html_report(
            path=report_path,
            edge_url=edge_url,
            origin=args.origin,
            meta=meta,
            asset_urls=asset_urls,
            assets_heads=assets_heads,
        )
        print(f"OK htmlReport={report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
