#!/usr/bin/env python3
"""Evaluate MD1 LOD viewer evidence before any production promotion.

This gate intentionally separates "viewer ready" from "promotion ready".
An LOD bundle can be interactive and shippable for inspection while still
being blocked as a replacement candidate by frozen-camera quality review.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MAX_FIRST_FRAME_MS = 10_000


def read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def truthy(value: Any) -> bool:
    return value is True


def parse_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def bundle_gate(
    bundle_validation: dict[str, Any],
    *,
    min_lod_levels: int,
    min_chunk_files: int,
    expected_source: str,
) -> dict[str, Any]:
    gates = bundle_validation.get("gates") if isinstance(bundle_validation.get("gates"), dict) else {}
    lod_meta = bundle_validation.get("lod_meta") if isinstance(bundle_validation.get("lod_meta"), dict) else {}
    summary = bundle_validation.get("summary") if isinstance(bundle_validation.get("summary"), dict) else {}
    listing = (
        bundle_validation.get("s3_bundle_listing")
        if isinstance(bundle_validation.get("s3_bundle_listing"), dict)
        else {}
    )
    failures: list[str] = []
    for key in (
        "required_objects_present",
        "lod_meta_parse_ok",
        "sidecar_lineage_ok",
        "skybox_wired",
        "referenced_meta_present",
    ):
        if not truthy(gates.get(key)):
            failures.append(f"bundle_{key}_failed")

    lod_levels = int(lod_meta.get("lod_levels") or 0)
    chunk_files = int(lod_meta.get("filename_count") or 0)
    total_objects = int(listing.get("total_objects") or summary.get("fileCount") or 0)
    total_bytes = int(listing.get("total_size_bytes") or summary.get("bundleSizeBytes") or 0)
    source = str(summary.get("source") or "")
    if lod_levels < min_lod_levels:
        failures.append("bundle_lod_levels_below_minimum")
    if chunk_files < min_chunk_files:
        failures.append("bundle_chunk_files_below_minimum")
    if expected_source and expected_source not in source:
        failures.append("bundle_source_lineage_mismatch")
    if total_objects <= 0:
        failures.append("bundle_has_no_objects")
    if total_bytes <= 0:
        failures.append("bundle_has_no_bytes")

    return {
        "status": "passed" if not failures else "blocked",
        "failures": failures,
        "lod_levels": lod_levels,
        "chunk_files": chunk_files,
        "total_objects": total_objects,
        "total_size_bytes": total_bytes,
        "source": source,
        "lod_meta_uri": bundle_validation.get("lod_meta_uri"),
        "output_prefix": bundle_validation.get("output_prefix"),
    }


def smoke_result_gate(
    result: dict[str, Any],
    *,
    max_first_frame_ms: int,
) -> dict[str, Any]:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    interaction = result.get("interaction") if isinstance(result.get("interaction"), dict) else {}
    canvas = result.get("canvasProbe") if isinstance(result.get("canvasProbe"), dict) else {}
    console_messages = result.get("consoleMessages") if isinstance(result.get("consoleMessages"), list) else []
    page_errors = result.get("pageErrors") if isinstance(result.get("pageErrors"), list) else []

    first_frame_ms = parse_number(metrics.get("firstFrameMs"))
    chunk_meta_requests = int(parse_number(metrics.get("chunkMetaRequests")) or 0)
    chunk_files = int(parse_number(metrics.get("chunkFiles")) or 0)
    failures: list[str] = []
    if result.get("pass") is not True:
        failures.append("scenario_marked_failed")
    if metrics.get("bundleKind") != "lod-streaming":
        failures.append("scenario_not_lod_streaming")
    if metrics.get("rootFile") != "lod-meta.json":
        failures.append("scenario_root_file_not_lod_meta")
    if chunk_files <= 0:
        failures.append("scenario_missing_chunk_file_count")
    if chunk_meta_requests <= 0:
        failures.append("scenario_missing_chunk_telemetry")
    if first_frame_ms is None or first_frame_ms <= 0:
        failures.append("scenario_missing_first_frame")
    elif first_frame_ms > max_first_frame_ms:
        failures.append("scenario_first_frame_over_budget")
    if interaction.get("ok") is not True:
        failures.append("scenario_interaction_failed")
    if canvas.get("ok") is not True or canvas.get("nonBlankProbe") is not True:
        failures.append("scenario_canvas_blank_or_failed")
    if console_messages:
        failures.append("scenario_console_messages_present")
    if page_errors:
        failures.append("scenario_page_errors_present")

    return {
        "name": result.get("name"),
        "status": "passed" if not failures else "blocked",
        "failures": failures,
        "url": result.get("url"),
        "manifest": result.get("manifest"),
        "transport": metrics.get("transport"),
        "bundle_kind": metrics.get("bundleKind"),
        "root_file": metrics.get("rootFile"),
        "chunk_meta_requests": chunk_meta_requests,
        "chunk_files": chunk_files,
        "first_frame_ms": first_frame_ms,
        "lod_min": parse_number(metrics.get("lodMin")),
        "lod_max": parse_number(metrics.get("lodMax")),
        "interaction_ok": interaction.get("ok") is True,
        "canvas_ok": canvas.get("ok") is True and canvas.get("nonBlankProbe") is True,
        "console_message_count": len(console_messages),
        "page_error_count": len(page_errors),
    }


def smoke_gate(
    smoke: dict[str, Any],
    *,
    max_first_frame_ms: int,
    require_health: bool,
) -> dict[str, Any]:
    failures: list[str] = []
    if smoke.get("pass") is not True:
        failures.append("smoke_marked_failed")
    health = smoke.get("health") if isinstance(smoke.get("health"), dict) else {}
    if require_health:
        if not health:
            failures.append("smoke_missing_health_checks")
        for url, result in health.items():
            if not isinstance(result, dict) or result.get("ok") is not True:
                failures.append(f"health_failed:{url}")

    result_gates = [
        smoke_result_gate(result, max_first_frame_ms=max_first_frame_ms)
        for result in smoke.get("results", [])
        if isinstance(result, dict)
    ]
    if not result_gates:
        failures.append("smoke_missing_scenarios")
    failures.extend(
        f"{result['name']}:{failure}"
        for result in result_gates
        for failure in result.get("failures", [])
    )

    return {
        "status": "passed" if not failures else "blocked",
        "failures": failures,
        "checked_at": smoke.get("checkedAt"),
        "scenario_count": len(result_gates),
        "scenarios": result_gates,
        "health": health,
    }


def quality_gate(review_comparison: dict[str, Any]) -> dict[str, Any]:
    decision = (
        review_comparison.get("promotion_decision")
        if isinstance(review_comparison.get("promotion_decision"), dict)
        else {}
    )
    status = str(decision.get("status") or "unknown")
    block_reasons = decision.get("block_reasons") if isinstance(decision.get("block_reasons"), list) else []
    camera_coverage = (
        decision.get("camera_coverage")
        if isinstance(decision.get("camera_coverage"), dict)
        else {}
    )
    render_sanity = (
        decision.get("render_sanity")
        if isinstance(decision.get("render_sanity"), dict)
        else {}
    )
    return {
        "status": "passed" if status == "promoted" else "blocked",
        "promotion_decision_status": status,
        "block_reasons": block_reasons,
        "camera_coverage_status": camera_coverage.get("status"),
        "render_sanity_status": render_sanity.get("status"),
        "fallback_tile_count": decision.get("fallback_tile_count"),
        "retain_all_tile_count": decision.get("retain_all_tile_count"),
    }


def evaluate_readiness(
    *,
    bundle_validation: dict[str, Any],
    local_smoke: dict[str, Any],
    preview_smoke: dict[str, Any],
    review_comparison: dict[str, Any],
    min_lod_levels: int,
    min_chunk_files: int,
    expected_source: str,
    max_first_frame_ms: int,
) -> dict[str, Any]:
    bundle = bundle_gate(
        bundle_validation,
        min_lod_levels=min_lod_levels,
        min_chunk_files=min_chunk_files,
        expected_source=expected_source,
    )
    local = smoke_gate(
        local_smoke,
        max_first_frame_ms=max_first_frame_ms,
        require_health=False,
    )
    preview = smoke_gate(
        preview_smoke,
        max_first_frame_ms=max_first_frame_ms,
        require_health=True,
    )
    quality = quality_gate(review_comparison)
    viewer_failures = {
        "bundle": bundle["failures"],
        "local_smoke": local["failures"],
        "preview_smoke": preview["failures"],
    }
    viewer_ready = all(not failures for failures in viewer_failures.values())
    promotion_ready = viewer_ready and quality["status"] == "passed"
    status = "production_promotion_ready" if promotion_ready else "blocked"
    if viewer_ready and not promotion_ready:
        status = "viewer_ready_quality_blocked"

    return {
        "checked_at": now_iso(),
        "status": status,
        "viewer_ready": viewer_ready,
        "promotion_ready": promotion_ready,
        "bundle_gate": bundle,
        "local_viewer_gate": local,
        "preview_viewer_gate": preview,
        "quality_gate": quality,
        "next_required_action": (
            "promotion may proceed after normal deployment approval"
            if promotion_ready
            else "quality promotion remains blocked; keep this LOD bundle as an inspection/viewer candidate only"
            if viewer_ready
            else "fix bundle or viewer gates before any promotion discussion"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-validation-json", required=True)
    parser.add_argument("--local-viewer-smoke-json", required=True)
    parser.add_argument("--preview-viewer-smoke-json", required=True)
    parser.add_argument("--review-comparison-json", required=True)
    parser.add_argument("--expected-source", default="")
    parser.add_argument("--min-lod-levels", type=int, default=4)
    parser.add_argument("--min-chunk-files", type=int, default=1)
    parser.add_argument("--max-first-frame-ms", type=int, default=DEFAULT_MAX_FIRST_FRAME_MS)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    report = evaluate_readiness(
        bundle_validation=read_json(args.bundle_validation_json),
        local_smoke=read_json(args.local_viewer_smoke_json),
        preview_smoke=read_json(args.preview_viewer_smoke_json),
        review_comparison=read_json(args.review_comparison_json),
        min_lod_levels=args.min_lod_levels,
        min_chunk_files=args.min_chunk_files,
        expected_source=args.expected_source,
        max_first_frame_ms=args.max_first_frame_ms,
    )

    output = Path(args.output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["viewer_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
