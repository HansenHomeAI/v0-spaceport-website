#!/usr/bin/env python3
"""Tests for the tiled 3DGS visual QA promotion gate."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "evaluate_md1_visual_qa_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("evaluate_md1_visual_qa_gate_test_module", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_args(
    visual_manifest: Path,
    *,
    quality_manifest: Path | None = None,
    asset_root: Path | None = None,
    require_local_assets: bool = True,
    ai_review_json: Path | None = None,
):
    return SimpleNamespace(
        visual_qa_manifest=str(visual_manifest),
        quality_review_manifest=str(quality_manifest) if quality_manifest else None,
        baseline_review_manifest=None,
        asset_root=str(asset_root) if asset_root else None,
        require_local_assets=require_local_assets,
        ai_review_json=str(ai_review_json) if ai_review_json else None,
        min_median_psnr=18.0,
        min_median_ssim=0.55,
        max_median_lpips=0.55,
        min_single_psnr=14.0,
        min_single_ssim=0.45,
        max_single_lpips=0.75,
        max_mean_abs_rgb_error=0.22,
    )


def make_view(bucket: str, *, psnr: float, ssim: float, lpips: float):
    return {
        "bucket": bucket,
        "image_name": f"{bucket}.JPG",
        "metrics": {"psnr": psnr, "ssim": ssim, "lpips": lpips},
        "difference_stats": {"mean_abs_rgb_error": 0.04},
    }


def write_manifests(root: Path, views: list[dict], *, asset_root: Path | None = None):
    quality_path = root / "quality_review_manifest.json"
    visual_path = root / "visual_qa_manifest.json"
    quality_path.write_text(
        json.dumps(
            {
                "views": views,
                "bucket_medians": {
                    bucket: views[index]["metrics"]
                    for index, bucket in enumerate(("near_detail", "boundary", "horizon"))
                },
                "render_sanity": {"status": "ok", "blank_view_count": 0},
                "promotion_readiness": {
                    "status": "ready_for_comparison",
                    "review_buckets_complete": True,
                    "retain_all_tile_count": 0,
                    "fallback_tile_count": 0,
                    "render_sanity": {"status": "ok", "blank_view_count": 0},
                },
            }
        ),
        encoding="utf-8",
    )

    visual_views = []
    for view in views:
        assets = {}
        for asset_name in (
            "reference_image",
            "merged_render",
            "merged_no_background_render",
            "diff_heatmap",
            "side_by_side_panel",
        ):
            relative = f"quality_review/{asset_name}/{view['bucket']}/{view['image_name']}.png"
            assets[asset_name] = {
                "path": f"/opt/ml/processing/output/{relative}",
                "artifact_relative_path": relative,
            }
            if asset_root is not None:
                target = asset_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"asset")
        visual_views.append(
            {
                "bucket": view["bucket"],
                "image_name": view["image_name"],
                "assets": assets,
                "metrics": view["metrics"],
                "difference_stats": view["difference_stats"],
            }
        )

    visual_path.write_text(
        json.dumps(
            {
                "quality_review_manifest": {
                    "path": str(quality_path),
                    "artifact_relative_path": quality_path.name,
                },
                "view_count": len(visual_views),
                "panel_count": len(visual_views),
                "bucket_counts": {"near_detail": 1, "boundary": 1, "horizon": 1},
                "views": visual_views,
            }
        ),
        encoding="utf-8",
    )
    return visual_path, quality_path


class VisualQaGateTest(unittest.TestCase):
    def test_blocks_low_input_vs_render_metrics(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            visual_path, quality_path = write_manifests(
                root,
                [
                    make_view("near_detail", psnr=9.5, ssim=0.38, lpips=0.93),
                    make_view("boundary", psnr=9.6, ssim=0.39, lpips=0.94),
                    make_view("horizon", psnr=10.9, ssim=0.42, lpips=0.89),
                ],
            )

            report = module.build_report(
                make_args(visual_path, quality_manifest=quality_path, require_local_assets=False)
            )

            self.assertEqual(report["status"], "blocked")
            self.assertIn(
                "near_detail_median_psnr_below_threshold",
                report["block_reasons"],
            )
            self.assertIn(
                "boundary_median_lpips_above_threshold",
                report["block_reasons"],
            )

    def test_passes_when_metrics_and_local_assets_are_complete(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            asset_root = root / "assets"
            visual_path, quality_path = write_manifests(
                root,
                [
                    make_view("near_detail", psnr=24.5, ssim=0.74, lpips=0.28),
                    make_view("boundary", psnr=23.6, ssim=0.71, lpips=0.31),
                    make_view("horizon", psnr=22.9, ssim=0.68, lpips=0.34),
                ],
                asset_root=asset_root,
            )

            report = module.build_report(
                make_args(visual_path, quality_manifest=quality_path, asset_root=asset_root)
            )

            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["asset_check"]["missing_file_count"], 0)

    def test_blocks_ai_review_defects(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            asset_root = root / "assets"
            visual_path, quality_path = write_manifests(
                root,
                [
                    make_view("near_detail", psnr=24.5, ssim=0.74, lpips=0.28),
                    make_view("boundary", psnr=23.6, ssim=0.71, lpips=0.31),
                    make_view("horizon", psnr=22.9, ssim=0.68, lpips=0.34),
                ],
                asset_root=asset_root,
            )
            ai_review = root / "ai_review.json"
            ai_review.write_text(
                json.dumps({"decision": "blocked", "blocking_defects": ["texture_blur_or_smear"]}),
                encoding="utf-8",
            )

            report = module.build_report(
                make_args(
                    visual_path,
                    quality_manifest=quality_path,
                    asset_root=asset_root,
                    ai_review_json=ai_review,
                )
            )

            self.assertEqual(report["status"], "blocked")
            self.assertIn("ai_review_blocking_defects", report["block_reasons"])


if __name__ == "__main__":
    unittest.main()
