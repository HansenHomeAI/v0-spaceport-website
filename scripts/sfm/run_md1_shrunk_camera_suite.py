#!/usr/bin/env python3
"""Run MD1-Shrunk multi-camera input-vs-render gates against a deployed viewer.

This is a bounded, read-only production-readiness check:
  - derives camera poses from COLMAP `images.txt`
  - downloads a small sample of source images
  - renders corresponding viewer screenshots (skybox + no-sky)
  - builds side-by-side panels (input | render)
  - runs deterministic sky/horizon diagnostics over the panels

It does not launch or stop any SageMaker / Step Functions jobs.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = REPO_ROOT / "web"
HOMEBREW_PYTHON = Path("/opt/homebrew/bin/python3")
HOMEBREW_AWS = Path("/opt/homebrew/bin/aws")


def resolve_python() -> str:
    return str(HOMEBREW_PYTHON) if HOMEBREW_PYTHON.exists() else "python3"


def resolve_aws() -> str:
    return str(HOMEBREW_AWS) if HOMEBREW_AWS.exists() else "aws"

def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.stdout


def aws_cp(uri: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    run([resolve_aws(), "s3", "cp", uri, str(destination)])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--viewer-url", required=True, help="Deployed base URL (e.g. https://...pages.dev)")
    parser.add_argument("--bundle-url", default="", help="Public bundle meta.json URL (defaults to published edge url)")
    parser.add_argument("--publish-function", default="Spaceport-MLPublishBundle-brc908ce627c")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--compressed-output-s3-uri", required=True, help="s3://.../compressed/<job-id>/")
    parser.add_argument(
        "--colmap-images-txt",
        required=True,
        help="Path or S3 URI to COLMAP sparse/0/images.txt for the job",
    )
    parser.add_argument(
        "--colmap-images-s3-prefix",
        required=True,
        help="S3 prefix to COLMAP images/ directory (s3://bucket/.../images)",
    )
    parser.add_argument(
        "--include-names",
        default="",
        help="Comma-separated list of image base names (e.g. DJI_01029.JPG) to render (overrides sampling)",
    )
    parser.add_argument("--out-dir", default="", help="Defaults to logs/md1-shrunk/polls/<timestamp>/suite")
    parser.add_argument("--sample-count", type=int, default=6)
    parser.add_argument("--distance-to-target", type=float, default=0.3)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when diagnostics report warnings")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "logs" / "md1-shrunk" / "polls" / f"{timestamp}-camera-suite"
    out_dir.mkdir(parents=True, exist_ok=True)

    publish_out = out_dir / "publish-edge.json"
    bundle_url = args.bundle_url.strip()
    if not bundle_url:
        python = resolve_python()
        publish_cmd = [
            python,
            str(REPO_ROOT / "scripts" / "publish_ml_bundle_to_edge.py"),
            "--function-name",
            args.publish_function,
            "--job-id",
            args.job_id,
            "--compressed-output-s3-uri",
            args.compressed_output_s3_uri,
            "--output",
            str(publish_out),
            "--validate-http",
        ]
        publish_log = out_dir / "publish-edge.log.txt"
        publish_log.write_text(run(publish_cmd), encoding="utf-8")
        bundle_url = load_json(publish_out).get("edgeBundleUrl", "").strip()
        if not bundle_url:
            raise RuntimeError(f"publish output missing edgeBundleUrl: {publish_out}")

    poses_out = out_dir / "camera-poses.json"
    python = resolve_python()
    derive_cmd = [
        python,
        str(REPO_ROOT / "scripts" / "sfm" / "derive_viewer_camera_poses_from_colmap.py"),
        "--images-txt",
        args.colmap_images_txt,
        "--output",
        str(poses_out),
        "--distance-to-target",
        str(args.distance_to_target),
        "--sample-count",
        str(args.sample_count),
    ]
    if args.colmap_images_txt.rstrip().endswith("frames.txt"):
        derive_cmd += ["--image-names-s3-prefix", args.colmap_images_s3_prefix]
    if args.include_names.strip():
        derive_cmd += ["--include-names", args.include_names.strip()]
    derive_log = out_dir / "derive-camera-poses.log.txt"
    derive_log.write_text(run(derive_cmd), encoding="utf-8")

    pose_payload = load_json(poses_out)
    poses = pose_payload.get("poses") or []
    if not isinstance(poses, list) or not poses:
        raise RuntimeError(f"no poses in {poses_out}")

    inputs_dir = out_dir / "inputs"
    renders_dir = out_dir / "renders"
    panels_dir = out_dir / "panels"
    panels_sky_dir = panels_dir / "skybox"
    panels_no_dir = panels_dir / "nosky"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    renders_dir.mkdir(parents=True, exist_ok=True)
    panels_sky_dir.mkdir(parents=True, exist_ok=True)
    panels_no_dir.mkdir(parents=True, exist_ok=True)

    failures: list[dict[str, Any]] = []

    for pose in poses:
        name = str(pose.get("name") or "")
        if not name:
            continue
        try:
            input_uri = f"{args.colmap_images_s3_prefix.rstrip('/')}/{name}"
            input_path = inputs_dir / f"input-{name}"
            aws_cp(input_uri, input_path)

            for variant, skybox_value, panel_subdir in [
                ("skybox", "background_skybox.webp", panels_sky_dir),
                ("nosky", "none", panels_no_dir),
            ]:
                render_path = renders_dir / f"render-{variant}-{Path(name).stem}.png"
                render_log = renders_dir / f"render-{variant}-{Path(name).stem}.log.txt"
                env = {
                    "MD1_VIEWER_URL": args.viewer_url.rstrip("/"),
                    "MD1_BUNDLE_URL": bundle_url,
                    "MD1_CAM_POS": str(pose.get("camPos") or ""),
                    "MD1_CAM_TARGET": str(pose.get("camTarget") or ""),
                    "MD1_CAM_UP": str(pose.get("camUp") or ""),
                    "MD1_SKYBOX": skybox_value,
                    "MD1_COLLAPSE_PANEL": "1",
                    "MD1_SCREENSHOT_TARGET": "iframe",
                    "MD1_OUT": str(render_path),
                }
                cmd = ["node", "scripts/render-md1-camera-check.mjs"]
                output = run(cmd, cwd=WEB_DIR, env={**dict(os.environ), **env})
                render_log.write_text(output, encoding="utf-8")

                panel_path = panel_subdir / f"panel-{variant}-{Path(name).stem}.png"
                panel_log = panel_subdir / f"panel-{variant}-{Path(name).stem}.log.txt"
                panel_env = {
                    "MD1_LEFT_IMAGE": str(input_path),
                    "MD1_RIGHT_IMAGE": str(render_path),
                    "MD1_PANEL_OUT": str(panel_path),
                }
                panel_output = run(
                    ["node", "scripts/make-md1-side-by-side-panel.mjs"],
                    cwd=WEB_DIR,
                    env={**dict(os.environ), **panel_env},
                )
                panel_log.parent.mkdir(parents=True, exist_ok=True)
                panel_log.write_text(panel_output, encoding="utf-8")
        except subprocess.CalledProcessError as exc:
            failures.append({"name": name, "exit_code": exc.returncode, "output": exc.stdout[-4000:] if exc.stdout else ""})
        except Exception as exc:  # noqa: BLE001
            failures.append({"name": name, "error": str(exc)})

    # Diagnose panels.
    diagnostics: dict[str, Any] = {"bundle_url": bundle_url, "viewer_url": args.viewer_url}
    decision = "pass"
    for variant, panel_dir in [("skybox", panels_sky_dir), ("nosky", panels_no_dir)]:
        if variant == "skybox":
            # Skybox replaces most of the top band; keep thresholds loose and focus on reachability.
            thresholds = {
                "min_edge_retention": "0.25",
                "max_top_band_rmse": "0.60",
                "max_top_brightness_delta": "0.50",
                "max_bottom_band_rmse_p90": "0.28",
            }
        else:
            # No-sky should stay stable at the horizon. Gate on top-band instability.
            thresholds = {
                "min_edge_retention": "0.25",
                "max_top_band_rmse": "0.35",
                "max_top_brightness_delta": "0.25",
                "max_bottom_band_rmse_p90": "0.28",
            }
        report_path = out_dir / f"diagnostics-{variant}.json"
        diag_cmd = [
            python,
            str(REPO_ROOT / "scripts" / "sfm" / "diagnose_heldout_panels.py"),
            "--panel-dir",
            str(panel_dir),
            "--glob",
            "panel-*.png",
            "--output",
            str(report_path),
            "--min-edge-retention",
            thresholds["min_edge_retention"],
            "--max-top-band-rmse",
            thresholds["max_top_band_rmse"],
            "--max-top-brightness-delta",
            thresholds["max_top_brightness_delta"],
            "--max-bottom-band-rmse-p90",
            thresholds["max_bottom_band_rmse_p90"],
        ]
        diag_log_path = out_dir / f"diagnostics-{variant}.log.txt"
        diag_log_path.write_text(run(diag_cmd), encoding="utf-8")
        report = load_json(report_path)
        diagnostics[variant] = report
        if report.get("decision") != "pass":
            decision = "warning"

    summary_path = out_dir / "suite-summary.json"
    panel_count = len(list(panels_dir.rglob("panel-*.png")))
    summary_payload: dict[str, Any] = {
        "decision": "fail" if failures else decision,
        "camera_poses": {
            "path": str(poses_out),
            "selected_count": len(poses),
            "names": [str(pose.get("name") or "") for pose in poses if pose.get("name")],
        },
        "failures": failures,
        **diagnostics,
    }
    summary_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")
    final_decision = summary_payload["decision"]
    print(f"OK {summary_path} decision={final_decision} panels={panel_count} failures={len(failures)}")
    if args.strict and final_decision != "pass":
        raise SystemExit(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
