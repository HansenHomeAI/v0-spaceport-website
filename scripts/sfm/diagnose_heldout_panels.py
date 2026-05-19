#!/usr/bin/env python3
"""Diagnose side-by-side held-out render proof panels.

The NerfStudio quality canaries emit PNG panels that place the source image and
rendered image side by side. This tool reads those panels without Pillow and
adds deterministic diagnostics for the human-visible failure modes we keep
seeing: softened detail, sky/horizon haze, and foreground smear.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import struct
import zlib
from pathlib import Path
from typing import Any

import numpy as np

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(max(math.ceil(q * len(ordered)) - 1, 0), len(ordered) - 1)
    return round(ordered[index], 4)


def summarize(values: list[float]) -> dict[str, float | int | None]:
    numbers = [float(value) for value in values if math.isfinite(float(value))]
    if not numbers:
        return {"count": 0, "min": None, "p10": None, "median": None, "p90": None, "p95": None, "max": None}
    return {
        "count": len(numbers),
        "min": round(min(numbers), 4),
        "p10": quantile(numbers, 0.10),
        "median": round(statistics.median(numbers), 4),
        "p90": quantile(numbers, 0.90),
        "p95": quantile(numbers, 0.95),
        "max": round(max(numbers), 4),
    }


def _paeth_byte(left: int, above: int, upper_left: int) -> int:
    prediction = left + above - upper_left
    left_distance = abs(prediction - left)
    above_distance = abs(prediction - above)
    upper_left_distance = abs(prediction - upper_left)
    if left_distance <= above_distance and left_distance <= upper_left_distance:
        return left
    if above_distance <= upper_left_distance:
        return above
    return upper_left


def read_png_rgb(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"{path} is not a PNG file")

    index = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = interlace = None
    idat_parts: list[bytes] = []
    palette: bytes | None = None
    while index < len(data):
        if index + 8 > len(data):
            raise ValueError(f"truncated PNG chunk header in {path}")
        length = struct.unpack(">I", data[index : index + 4])[0]
        chunk_type = data[index + 4 : index + 8]
        chunk_data = data[index + 8 : index + 8 + length]
        index += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _compression, _filter, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
        elif chunk_type == b"PLTE":
            palette = chunk_data
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width is None or height is None or bit_depth is None or color_type is None or interlace is None:
        raise ValueError(f"missing PNG IHDR in {path}")
    if bit_depth != 8 or interlace != 0:
        raise ValueError(f"unsupported PNG bit_depth/interlace in {path}: {bit_depth}/{interlace}")

    channels_by_type = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    if color_type not in channels_by_type:
        raise ValueError(f"unsupported PNG color type {color_type} in {path}")
    channels = channels_by_type[color_type]
    stride = width * channels
    raw = zlib.decompress(b"".join(idat_parts))
    expected = (stride + 1) * height
    if len(raw) < expected:
        raise ValueError(f"truncated PNG IDAT data in {path}: got {len(raw)}, expected {expected}")

    rows = np.zeros((height, stride), dtype=np.uint8)
    cursor = 0
    for y in range(height):
        filter_type = raw[cursor]
        cursor += 1
        row = np.frombuffer(raw[cursor : cursor + stride], dtype=np.uint8).copy()
        cursor += stride
        above = rows[y - 1] if y else np.zeros_like(row)
        if filter_type not in {0, 1, 2, 3, 4}:
            raise ValueError(f"unsupported PNG filter {filter_type} in {path}")
        if filter_type:
            reconstructed = row.copy()
            for offset in range(stride):
                left = int(reconstructed[offset - channels]) if offset >= channels else 0
                up = int(above[offset])
                upper_left = int(above[offset - channels]) if offset >= channels else 0
                if filter_type == 1:
                    predictor = left
                elif filter_type == 2:
                    predictor = up
                elif filter_type == 3:
                    predictor = (left + up) // 2
                else:
                    predictor = _paeth_byte(left, up, upper_left)
                reconstructed[offset] = (int(reconstructed[offset]) + predictor) & 0xFF
            row = reconstructed
        rows[y] = row

    if color_type == 3:
        if palette is None:
            raise ValueError(f"palette PNG without PLTE in {path}")
        lut = np.frombuffer(palette, dtype=np.uint8).reshape((-1, 3))
        return lut[rows.reshape((height, width))].astype(np.float32) / 255.0

    pixels = rows.reshape((height, width, channels))
    if color_type == 0:
        rgb = np.repeat(pixels, 3, axis=2)
    else:
        rgb = pixels[..., :3]
    return rgb.astype(np.float32) / 255.0


def split_panel(panel: np.ndarray, columns: int) -> tuple[np.ndarray, np.ndarray]:
    height, width, _channels = panel.shape
    if width % columns != 0:
        raise ValueError(f"panel width {width} is not divisible by {columns} columns")
    tile_width = width // columns
    if columns < 2:
        raise ValueError("panel must contain at least source and rendered columns")
    return panel[:, :tile_width, :3], panel[:, tile_width : tile_width * 2, :3]


def gray(image: np.ndarray) -> np.ndarray:
    return image[..., 0] * 0.299 + image[..., 1] * 0.587 + image[..., 2] * 0.114


def gradient_energy(image: np.ndarray) -> float:
    luminance = gray(image)
    dx = np.diff(luminance, axis=1)
    dy = np.diff(luminance, axis=0)
    return float(np.mean(np.abs(dx)) + np.mean(np.abs(dy)))


def rmse(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.sqrt(np.mean((left - right) ** 2)))


def psnr(left: np.ndarray, right: np.ndarray) -> float:
    mse = float(np.mean((left - right) ** 2))
    if mse <= 1e-12:
        return 100.0
    return -10.0 * math.log10(mse)


def band(image: np.ndarray, start: float, end: float) -> np.ndarray:
    top = int(round(image.shape[0] * start))
    bottom = max(top + 1, int(round(image.shape[0] * end)))
    return image[top:bottom]

def fraction_true(mask: np.ndarray) -> float:
    total = int(mask.size)
    if total <= 0:
        return 0.0
    return float(np.count_nonzero(mask)) / float(total)


def diagnose_panel(path: Path, columns: int) -> dict[str, Any]:
    source, rendered = split_panel(read_png_rgb(path), columns)
    source_edges = gradient_energy(source)
    render_edges = gradient_energy(rendered)
    diff = np.abs(source - rendered)
    top_source = band(source, 0.0, 0.2)
    top_render = band(rendered, 0.0, 0.2)
    bottom_source = band(source, 0.75, 1.0)
    bottom_render = band(rendered, 0.75, 1.0)
    top_source_luma = gray(top_source)
    top_render_luma = gray(top_render)
    # Catch black horizon bands in no-sky mode: source sky is bright but render becomes near-black.
    top_dark_on_bright_fraction = fraction_true((top_source_luma > 0.65) & (top_render_luma < 0.25))
    return {
        "panel": str(path),
        "width": int(source.shape[1]),
        "height": int(source.shape[0]),
        "rmse": round(rmse(source, rendered), 4),
        "mae": round(float(np.mean(diff)), 4),
        "psnr": round(psnr(source, rendered), 4),
        "source_edge_energy": round(source_edges, 6),
        "render_edge_energy": round(render_edges, 6),
        "edge_retention_ratio": round(render_edges / source_edges, 4) if source_edges > 1e-9 else None,
        "top_band_rmse": round(rmse(top_source, top_render), 4),
        "top_band_brightness_delta": round(float(np.mean(gray(top_render)) - np.mean(gray(top_source))), 4),
        "top_dark_on_bright_fraction": round(top_dark_on_bright_fraction, 6),
        "bottom_band_rmse": round(rmse(bottom_source, bottom_render), 4),
        "bottom_band_brightness_delta": round(float(np.mean(gray(bottom_render)) - np.mean(gray(bottom_source))), 4),
    }


def load_baseline(path_text: str) -> dict[str, Any] | None:
    if not path_text:
        return None
    with open(path_text, "r", encoding="utf-8") as handle:
        return json.load(handle)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    panel_dir = Path(args.panel_dir)
    paths = sorted(panel_dir.glob(args.glob))
    per_panel = [diagnose_panel(path, args.panel_columns) for path in paths]
    metrics = {
        key: summarize([float(item[key]) for item in per_panel if item.get(key) is not None])
        for key in [
            "rmse",
            "mae",
            "psnr",
            "edge_retention_ratio",
            "top_band_rmse",
            "top_band_brightness_delta",
            "top_dark_on_bright_fraction",
            "bottom_band_rmse",
            "bottom_band_brightness_delta",
        ]
    }
    findings: list[dict[str, Any]] = []
    rmse_median = metrics["rmse"]["median"]
    if rmse_median is not None and rmse_median > args.max_panel_rmse_median:
        findings.append(
            {
                "severity": "warning",
                "category": "camera_pose_mismatch",
                "evidence": f"median RMSE {rmse_median} > {args.max_panel_rmse_median}",
            }
        )
    psnr_median = metrics["psnr"]["median"]
    if psnr_median is not None and psnr_median < args.min_panel_psnr_median:
        findings.append(
            {
                "severity": "warning",
                "category": "camera_pose_mismatch",
                "evidence": f"median PSNR {psnr_median} < {args.min_panel_psnr_median}",
            }
        )
    edge_median = metrics["edge_retention_ratio"]["median"]
    if edge_median is not None and edge_median < args.min_edge_retention:
        findings.append(
            {
                "severity": "warning",
                "category": "fine_detail_softness",
                "evidence": f"median edge retention {edge_median} < {args.min_edge_retention}",
            }
        )
    top_rmse = metrics["top_band_rmse"]["median"]
    top_brightness = metrics["top_band_brightness_delta"]["median"]
    if top_rmse is not None and top_rmse > args.max_top_band_rmse:
        findings.append(
            {
                "severity": "warning",
                "category": "sky_horizon_instability",
                "evidence": f"median top-band RMSE {top_rmse} > {args.max_top_band_rmse}",
            }
        )
    if top_brightness is not None and abs(top_brightness) > args.max_top_brightness_delta:
        findings.append(
            {
                "severity": "warning",
                "category": "sky_horizon_brightness_shift",
                "evidence": f"median top-band brightness delta {top_brightness} exceeds +/-{args.max_top_brightness_delta}",
            }
        )
    top_dark_on_bright = metrics["top_dark_on_bright_fraction"]["median"]
    if top_dark_on_bright is not None and top_dark_on_bright > args.max_top_dark_on_bright_fraction:
        findings.append(
            {
                "severity": "warning",
                "category": "horizon_black_band",
                "evidence": f"median top_dark_on_bright_fraction {top_dark_on_bright} > {args.max_top_dark_on_bright_fraction}",
            }
        )
    bottom_rmse = metrics["bottom_band_rmse"]["p90"]
    if bottom_rmse is not None and bottom_rmse > args.max_bottom_band_rmse_p90:
        findings.append(
            {
                "severity": "warning",
                "category": "foreground_smear",
                "evidence": f"p90 bottom-band RMSE {bottom_rmse} > {args.max_bottom_band_rmse_p90}",
            }
        )

    comparison = None
    baseline = load_baseline(args.baseline_report)
    if baseline:
        comparison = {}
        baseline_metrics = baseline.get("metrics") or {}
        for key, summary in metrics.items():
            current = summary.get("median")
            previous = (baseline_metrics.get(key) or {}).get("median")
            if current is not None and previous is not None:
                comparison[key] = {
                    "current_median": current,
                    "baseline_median": previous,
                    "delta": round(float(current) - float(previous), 4),
                }

    report = {
        "artifact_kind": "heldout_panel_diagnostics",
        "schema_version": 1,
        "decision": "warning" if findings else "pass",
        "panel_dir": str(panel_dir),
        "panel_count": len(per_panel),
        "panel_columns": args.panel_columns,
        "thresholds": {
            "max_panel_rmse_median": args.max_panel_rmse_median,
            "min_panel_psnr_median": args.min_panel_psnr_median,
            "min_edge_retention": args.min_edge_retention,
            "max_top_band_rmse": args.max_top_band_rmse,
            "max_top_brightness_delta": args.max_top_brightness_delta,
            "max_top_dark_on_bright_fraction": args.max_top_dark_on_bright_fraction,
            "max_bottom_band_rmse_p90": args.max_bottom_band_rmse_p90,
        },
        "metrics": metrics,
        "findings": findings,
        "comparison": comparison,
        "per_panel": per_panel,
    }
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-dir", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--glob", default="eval_img_*.png")
    parser.add_argument("--panel-columns", type=int, default=2)
    parser.add_argument("--baseline-report", default="")
    parser.add_argument(
        "--max-panel-rmse-median",
        type=float,
        default=1.0,
        help="Warn if median RMSE between source/render exceeds this threshold (proxy for camera pose mismatch).",
    )
    parser.add_argument(
        "--min-panel-psnr-median",
        type=float,
        default=0.0,
        help="Warn if median PSNR between source/render drops below this threshold (proxy for camera pose mismatch).",
    )
    parser.add_argument("--min-edge-retention", type=float, default=0.92)
    parser.add_argument("--max-top-band-rmse", type=float, default=0.20)
    parser.add_argument("--max-top-brightness-delta", type=float, default=0.12)
    parser.add_argument("--max-top-dark-on-bright-fraction", type=float, default=0.02)
    parser.add_argument("--max-bottom-band-rmse-p90", type=float, default=0.22)
    return parser.parse_args()


def main() -> int:
    report = build_report(parse_args())
    print(json.dumps({"decision": report["decision"], "panel_count": report["panel_count"], "findings": report["findings"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
