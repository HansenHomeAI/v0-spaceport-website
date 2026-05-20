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
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = REPO_ROOT / "web"
HOMEBREW_PYTHON = Path("/opt/homebrew/bin/python3")
HOMEBREW_AWS = Path("/opt/homebrew/bin/aws")


def resolve_python() -> str:
    return str(HOMEBREW_PYTHON) if HOMEBREW_PYTHON.exists() else "python3"


def resolve_aws() -> str:
    return str(HOMEBREW_AWS) if HOMEBREW_AWS.exists() else "aws"

def parse_vector(value: object) -> tuple[float, float, float] | None:
    raw = str(value or "").strip()
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if len(parts) != 3:
        return None
    try:
        numbers = tuple(float(part) for part in parts)
    except ValueError:
        return None
    if not all(number == number for number in numbers):
        return None
    return numbers  # type: ignore[return-value]

def vector_delta(left: str, right: str) -> float | None:
    a = parse_vector(left)
    b = parse_vector(right)
    if a is None or b is None:
        return None
    return float(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5)

def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )

def build_viewer_url(
    base_url: str,
    *,
    bundle_url: str,
    cam_pos: str,
    cam_target: str,
    cam_up: str,
    skybox: str,
) -> str:
    params: dict[str, str] = {"url": bundle_url, "camPos": cam_pos, "camTarget": cam_target, "panel": "collapsed"}
    if cam_up:
        params["camUp"] = cam_up
    if skybox:
        params["skybox"] = skybox
    query = urlencode(params, safe=",:/")  # keep comma-separated vectors readable
    return f"{base_url.rstrip('/')}/md1-viewer?{query}"

def write_html_report(
    *,
    out_dir: Path,
    viewer_url: str,
    bundle_url: str,
    poses: list[dict[str, Any]],
    diagnostics: dict[str, Any],
    failures: list[dict[str, Any]],
    decision: str,
    baseline_suite_dir: str,
    pose_verification: dict[str, Any] | None,
    include_panel_links: bool,
) -> Path:
    def rel(path: Path) -> str:
        return path.relative_to(out_dir).as_posix()

    baseline_html = "<p><strong>baseline suite</strong>: <code>none</code></p>"
    if baseline_suite_dir:
        baseline_html = f"<p><strong>baseline suite</strong>: <code>{escape_html(baseline_suite_dir)}</code></p>"

    pose_verify_html = "<p><strong>pose verification</strong>: <code>none</code></p>"
    if pose_verification:
        max_delta = pose_verification.get("max_delta")
        max_field = pose_verification.get("max_delta_field")
        max_name = pose_verification.get("max_delta_name")
        tol = pose_verification.get("tolerance")
        missing_current = len(pose_verification.get("missing_in_current") or [])
        missing_baseline = len(pose_verification.get("missing_in_baseline") or [])
        pose_verify_html = (
            "<p><strong>pose verification</strong>: "
            f"tolerance=<code>{escape_html(str(tol))}</code> "
            f"max_delta=<code>{escape_html(str(max_delta))}</code> "
            f"field=<code>{escape_html(str(max_field))}</code> "
            f"name=<code>{escape_html(str(max_name))}</code> "
            f"missing_current=<code>{missing_current}</code> "
            f"missing_baseline=<code>{missing_baseline}</code>"
            "</p>"
        )

    rows: list[str] = []
    for pose in poses:
        name = str(pose.get("name") or "")
        stem = Path(name).stem
        cam_pos = str(pose.get("camPos") or "")
        cam_target = str(pose.get("camTarget") or "")
        cam_up = str(pose.get("camUp") or "")
        panel_sky = out_dir / "panels" / "skybox" / f"panel-skybox-{stem}.png"
        panel_no = out_dir / "panels" / "nosky" / f"panel-nosky-{stem}.png"
        url_sky = build_viewer_url(
            viewer_url,
            bundle_url=bundle_url,
            cam_pos=cam_pos,
            cam_target=cam_target,
            cam_up=cam_up,
            skybox="background_skybox.webp",
        )
        url_no = build_viewer_url(
            viewer_url,
            bundle_url=bundle_url,
            cam_pos=cam_pos,
            cam_target=cam_target,
            cam_up=cam_up,
            skybox="none",
        )
        panel_sky_html = f"<a href=\"{escape_html(rel(panel_sky))}\">panel</a>"
        panel_no_html = f"<a href=\"{escape_html(rel(panel_no))}\">panel</a>"
        if not include_panel_links:
            panel_sky_html = "<code>pruned</code>"
            panel_no_html = "<code>pruned</code>"
        rows.append(
            "<tr>"
            f"<td>{escape_html(name)}</td>"
            f"<td><a href=\"{escape_html(url_sky)}\">viewer(skybox)</a> · <a href=\"{escape_html(url_no)}\">viewer(nosky)</a></td>"
            f"<td>{panel_sky_html}</td>"
            f"<td>{panel_no_html}</td>"
            "</tr>"
        )

    findings_html: list[str] = []
    for variant in ["skybox", "nosky"]:
        report = diagnostics.get(variant) or {}
        findings = report.get("findings") or []
        findings_html.append(f"<h3>{escape_html(variant)} findings</h3>")
        if not findings:
            findings_html.append("<p>none</p>")
        else:
            findings_html.append("<ul>")
            for item in findings:
                category = str(item.get("category") or "")
                evidence = str(item.get("evidence") or "")
                findings_html.append(f"<li><code>{escape_html(category)}</code>: {escape_html(evidence)}</li>")
            findings_html.append("</ul>")

        comparison = report.get("comparison") or {}
        if comparison:
            findings_html.append("<details><summary>baseline comparison</summary><ul>")
            for key, entry in comparison.items():
                findings_html.append(f"<li><code>{escape_html(str(key))}</code>: {escape_html(json.dumps(entry))}</li>")
            findings_html.append("</ul></details>")

    failures_html = "<p>none</p>"
    if failures:
        failures_html = "<ul>" + "".join(f"<li>{escape_html(json.dumps(item))}</li>" for item in failures) + "</ul>"

    html = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>MD1-Shrunk camera suite</title>
    <style>
      body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif; margin: 24px; }}
      code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
      table {{ border-collapse: collapse; width: 100%; }}
      th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
      th {{ background: #f6f6f6; text-align: left; }}
    </style>
  </head>
  <body>
    <h1>MD1-Shrunk camera suite</h1>
    <p><strong>decision</strong>: <code>{escape_html(decision)}</code></p>
    <p><strong>viewer</strong>: <a href="{escape_html(viewer_url)}">{escape_html(viewer_url)}</a></p>
    <p><strong>bundle</strong>: <a href="{escape_html(bundle_url)}">{escape_html(bundle_url)}</a></p>
    {baseline_html}
    {pose_verify_html}
    <h2>Poses</h2>
    <table>
      <thead>
        <tr>
          <th>name</th>
          <th>viewer links</th>
          <th>skybox panel</th>
          <th>nosky panel</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
    <h2>Diagnostics</h2>
    {''.join(findings_html)}
    <h2>Failures</h2>
    {failures_html}
  </body>
</html>
"""
    report_path = out_dir / "report.html"
    report_path.write_text(html, encoding="utf-8")
    return report_path

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
        default="",
        help="Path or S3 URI to COLMAP sparse/0/images.txt for the job",
    )
    parser.add_argument(
        "--colmap-images-s3-prefix",
        required=True,
        help="S3 prefix to COLMAP images/ directory (s3://bucket/.../images)",
    )
    parser.add_argument("--poses-json", default="", help="Optional precomputed camera poses JSON (skips COLMAP derive).")
    parser.add_argument(
        "--include-names",
        default="",
        help="Comma-separated list of image base names (e.g. DJI_01029.JPG) to render (overrides sampling)",
    )
    parser.add_argument(
        "--baseline-suite-dir",
        default="",
        help="Optional prior suite output dir used for baseline diagnostics + camera-pose verification.",
    )
    parser.add_argument(
        "--pose-diff-tolerance",
        type=float,
        default=0.01,
        help="Warn when baseline pose vectors drift more than this L2 distance (normalized viewer coordinates).",
    )
    parser.add_argument("--out-dir", default="", help="Defaults to logs/md1-shrunk/polls/<timestamp>/suite")
    parser.add_argument("--sample-count", type=int, default=6)
    parser.add_argument("--distance-to-target", type=float, default=0.3)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when diagnostics report warnings")
    parser.add_argument(
        "--prune-artifacts",
        action="store_true",
        help="Delete large inputs/renders/panels outputs on PASS (keeps JSON summaries + logs).",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "logs" / "md1-shrunk" / "polls" / f"{timestamp}-camera-suite"
    if not out_dir.is_absolute():
        out_dir = (REPO_ROOT / out_dir).resolve()
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
            "--require-browser-headers",
            "--html-report",
            str(out_dir / "publish-edge.report.html"),
        ]
        publish_log = out_dir / "publish-edge.log.txt"
        publish_log.write_text(run(publish_cmd), encoding="utf-8")
        bundle_url = load_json(publish_out).get("edgeBundleUrl", "").strip()
        if not bundle_url:
            raise RuntimeError(f"publish output missing edgeBundleUrl: {publish_out}")

    poses_out = out_dir / "camera-poses.json"
    python = resolve_python()
    if args.poses_json.strip():
        poses_src = Path(args.poses_json)
        if not poses_src.is_absolute():
            poses_src = (REPO_ROOT / poses_src).resolve()
        poses_out.write_text(poses_src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        if not args.colmap_images_txt.strip():
            raise RuntimeError("--colmap-images-txt is required when --poses-json is not set")
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

    validated_poses: list[dict[str, Any]] = []
    for pose in poses:
        if not isinstance(pose, dict):
            failures.append({"error": "pose payload is not an object"})
            continue
        name = str(pose.get("name") or "")
        if not name:
            failures.append({"name": name, "error": "pose missing image name"})
            continue
        cam_pos = str(pose.get("camPos") or "")
        cam_target = str(pose.get("camTarget") or "")
        cam_up = str(pose.get("camUp") or "")
        if parse_vector(cam_pos) is None or parse_vector(cam_target) is None:
            failures.append({"name": name, "error": "pose missing/invalid camPos/camTarget"})
            continue
        if cam_up and parse_vector(cam_up) is None:
            failures.append({"name": name, "error": "pose has invalid camUp"})
            continue
        validated_poses.append(pose)

    baseline_suite_dir = args.baseline_suite_dir.strip()
    baseline_pose_verification: dict[str, Any] | None = None
    baseline_sky_report: Path | None = None
    baseline_no_report: Path | None = None
    baseline_pose_path: Path | None = None
    if baseline_suite_dir:
        baseline_dir = Path(baseline_suite_dir)
        if not baseline_dir.is_absolute():
            baseline_dir = (REPO_ROOT / baseline_dir).resolve()
        baseline_suite_dir = str(baseline_dir)
        maybe_sky = baseline_dir / "diagnostics-skybox.json"
        maybe_no = baseline_dir / "diagnostics-nosky.json"
        if maybe_sky.exists():
            baseline_sky_report = maybe_sky
        if maybe_no.exists():
            baseline_no_report = maybe_no
        maybe_pose = baseline_dir / "camera-poses.json"
        if maybe_pose.exists():
            baseline_pose_path = maybe_pose

    if baseline_pose_path is not None:
        baseline_payload = load_json(baseline_pose_path)
        baseline_poses = baseline_payload.get("poses") or []
        base_map = {str(item.get("name") or ""): item for item in baseline_poses if isinstance(item, dict) and item.get("name")}
        curr_map = {str(item.get("name") or ""): item for item in validated_poses if item.get("name")}
        missing_in_current = sorted([name for name in base_map.keys() if name not in curr_map])
        missing_in_baseline = sorted([name for name in curr_map.keys() if name not in base_map])
        max_delta: float = 0.0
        max_delta_name = ""
        max_delta_field = ""
        per_pose: list[dict[str, Any]] = []
        for name in sorted(set(base_map.keys()) & set(curr_map.keys())):
            base = base_map[name]
            curr = curr_map[name]
            for field in ["camPos", "camTarget", "camUp"]:
                base_value = str(base.get(field) or "")
                curr_value = str(curr.get(field) or "")
                if not base_value or not curr_value:
                    continue
                delta = vector_delta(base_value, curr_value)
                if delta is None:
                    continue
                per_pose.append({"name": name, "field": field, "delta": round(delta, 6)})
                if delta > max_delta:
                    max_delta = delta
                    max_delta_name = name
                    max_delta_field = field
        baseline_pose_verification = {
            "baseline_camera_poses": str(baseline_pose_path),
            "tolerance": args.pose_diff_tolerance,
            "max_delta": round(max_delta, 6),
            "max_delta_name": max_delta_name,
            "max_delta_field": max_delta_field,
            "missing_in_current": missing_in_current,
            "missing_in_baseline": missing_in_baseline,
            "per_pose_deltas": per_pose,
        }

    for pose in validated_poses:
        name = str(pose.get("name") or "")
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
                "max_panel_rmse_median": "0.35",
                "min_panel_psnr_median": "10.0",
                "min_edge_retention": "0.21",
                "max_top_band_rmse": "0.60",
                "max_top_brightness_delta": "0.50",
                "max_bottom_band_rmse_p90": "0.28",
            }
        else:
            # No-sky should stay stable at the horizon. Gate on top-band instability.
            thresholds = {
                "max_panel_rmse_median": "0.35",
                "min_panel_psnr_median": "10.0",
                "min_edge_retention": "0.21",
                "max_top_band_rmse": "0.35",
                "max_top_brightness_delta": "0.25",
                "max_top_dark_on_bright_fraction": "0.03",
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
            "--max-panel-rmse-median",
            thresholds["max_panel_rmse_median"],
            "--min-panel-psnr-median",
            thresholds["min_panel_psnr_median"],
            "--min-edge-retention",
            thresholds["min_edge_retention"],
            "--max-top-band-rmse",
            thresholds["max_top_band_rmse"],
            "--max-top-brightness-delta",
            thresholds["max_top_brightness_delta"],
            "--max-top-dark-on-bright-fraction",
            thresholds.get("max_top_dark_on_bright_fraction", "1.0"),
            "--max-bottom-band-rmse-p90",
            thresholds["max_bottom_band_rmse_p90"],
        ]
        baseline_report = baseline_sky_report if variant == "skybox" else baseline_no_report
        if baseline_report is not None:
            diag_cmd += ["--baseline-report", str(baseline_report)]
        diag_log_path = out_dir / f"diagnostics-{variant}.log.txt"
        diag_log_path.write_text(run(diag_cmd), encoding="utf-8")
        report = load_json(report_path)
        diagnostics[variant] = report
        if report.get("decision") != "pass":
            decision = "warning"

    if baseline_pose_verification and baseline_pose_verification["max_delta"] > args.pose_diff_tolerance:
        decision = "warning"
    if baseline_pose_verification and (
        baseline_pose_verification["missing_in_current"] or baseline_pose_verification["missing_in_baseline"]
    ):
        decision = "warning"

    summary_path = out_dir / "suite-summary.json"
    panel_count = len(list(panels_dir.rglob("panel-*.png")))
    summary_payload: dict[str, Any] = {
        "decision": "fail" if failures else decision,
        "artifacts_pruned": False,
        "camera_poses": {
            "path": str(poses_out),
            "selected_count": len(validated_poses),
            "names": [str(pose.get("name") or "") for pose in validated_poses if pose.get("name")],
        },
        "failures": failures,
        "baseline_suite_dir": baseline_suite_dir,
        "pose_verification": baseline_pose_verification,
        **diagnostics,
    }
    summary_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")
    report_path = write_html_report(
        out_dir=out_dir,
        viewer_url=args.viewer_url.rstrip("/"),
        bundle_url=bundle_url,
        poses=validated_poses,
        diagnostics=diagnostics,
        failures=failures,
        decision=str(summary_payload["decision"]),
        baseline_suite_dir=baseline_suite_dir,
        pose_verification=baseline_pose_verification,
        include_panel_links=not args.prune_artifacts,
    )
    final_decision = summary_payload["decision"]
    if args.prune_artifacts and final_decision == "pass":
        pruned_dirs: list[Path] = []
        for leaf in ["inputs", "renders", "panels"]:
            candidate = out_dir / leaf
            if candidate.exists():
                shutil.rmtree(candidate)
                pruned_dirs.append(candidate)
        summary_payload["artifacts_pruned"] = True
        summary_payload["artifacts_pruned_dirs"] = [str(path) for path in pruned_dirs]
        summary_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")
    print(f"OK {summary_path} decision={final_decision} panels={panel_count} failures={len(failures)} report={report_path}")
    if args.strict and final_decision != "pass":
        raise SystemExit(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
