#!/usr/bin/env python3
"""Gate MD1 visual QA bundles before spending on promotion or the next candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


REQUIRED_VIEW_ASSETS = (
    "reference_image",
    "merged_render",
    "merged_no_background_render",
    "diff_heatmap",
    "side_by_side_panel",
)


def load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def asset_path(asset_root: Path, asset: Mapping[str, Any]) -> Path:
    relative = asset.get("artifact_relative_path")
    if relative:
        return asset_root / str(relative)
    return Path(str(asset.get("path", "")))


def evaluate_visual_qa_gate(
    *,
    visual_qa_manifest: Mapping[str, Any],
    asset_root: Path | None = None,
    ai_review: Mapping[str, Any] | None = None,
    min_panel_ratio: float = 1.0,
) -> dict[str, Any]:
    block_reasons: list[str] = []
    warnings: list[str] = []
    views = visual_qa_manifest.get("views", [])
    if not isinstance(views, list) or not views:
        block_reasons.append("visual_qa_views_missing")
        views = []

    missing_assets: list[dict[str, Any]] = []
    missing_files: list[dict[str, Any]] = []
    for view in views:
        if not isinstance(view, Mapping):
            block_reasons.append("visual_qa_view_not_object")
            continue
        assets = view.get("assets", {})
        if not isinstance(assets, Mapping):
            assets = {}
        for asset_key in REQUIRED_VIEW_ASSETS:
            asset = assets.get(asset_key)
            if not isinstance(asset, Mapping):
                missing_assets.append(
                    {
                        "bucket": view.get("bucket"),
                        "image_name": view.get("image_name"),
                        "asset": asset_key,
                    }
                )
                continue
            if asset_root is not None and not asset_path(asset_root, asset).exists():
                missing_files.append(
                    {
                        "bucket": view.get("bucket"),
                        "image_name": view.get("image_name"),
                        "asset": asset_key,
                        "path": str(asset_path(asset_root, asset)),
                    }
                )

    if missing_assets:
        block_reasons.append("visual_qa_required_assets_missing")
    if missing_files:
        block_reasons.append("visual_qa_asset_files_missing")

    view_count = int(visual_qa_manifest.get("view_count", len(views)) or 0)
    panel_count = int(visual_qa_manifest.get("panel_count", 0) or 0)
    panel_ratio = 0.0 if view_count == 0 else panel_count / float(view_count)
    if panel_ratio < min_panel_ratio:
        block_reasons.append("visual_qa_panel_coverage_below_threshold")

    ai_review_summary = None
    if ai_review is not None:
        overall_status = str(ai_review.get("overall_status", "")).strip().lower()
        blocking_defects = ai_review.get("blocking_defects", [])
        per_view_findings = ai_review.get("per_view_findings", [])
        blocking_view_findings = [
            finding
            for finding in per_view_findings
            if isinstance(finding, Mapping) and str(finding.get("severity", "")).lower() == "blocking"
        ]
        ai_review_summary = {
            "overall_status": overall_status,
            "blocking_defect_count": len(blocking_defects) if isinstance(blocking_defects, list) else 0,
            "blocking_view_finding_count": len(blocking_view_findings),
            "confidence": ai_review.get("confidence"),
            "recommended_next_action": ai_review.get("recommended_next_action"),
        }
        if overall_status == "block":
            block_reasons.append("ai_visual_review_status_block")
        if isinstance(blocking_defects, list) and blocking_defects:
            block_reasons.append("ai_visual_review_blocking_defects")
        if blocking_view_findings:
            block_reasons.append("ai_visual_review_blocking_view_findings")
        if overall_status not in {"pass", "conditional_pass", "block"}:
            warnings.append("ai_visual_review_status_unknown")
    else:
        warnings.append("ai_visual_review_not_provided")

    return {
        "decision": "visual_qa_ready" if not block_reasons else "visual_qa_blocked",
        "block_reasons": sorted(set(block_reasons)),
        "warnings": warnings,
        "view_count": view_count,
        "panel_count": panel_count,
        "panel_ratio": panel_ratio,
        "missing_assets": missing_assets[:50],
        "missing_files": missing_files[:50],
        "ai_review_summary": ai_review_summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--visual-qa-manifest", required=True, type=Path)
    parser.add_argument("--asset-root", type=Path, help="Optional extracted bundle root for file existence checks")
    parser.add_argument("--ai-review-json", type=Path, help="Optional AI visual review verdict JSON")
    parser.add_argument("--min-panel-ratio", type=float, default=1.0)
    parser.add_argument("--summary-json-output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = evaluate_visual_qa_gate(
        visual_qa_manifest=load_json(args.visual_qa_manifest),
        asset_root=args.asset_root,
        ai_review=load_json(args.ai_review_json) if args.ai_review_json else None,
        min_panel_ratio=args.min_panel_ratio,
    )
    if args.summary_json_output:
        args.summary_json_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if summary["decision"] != "visual_qa_ready":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
