#!/usr/bin/env python3
"""Compute deterministic held-out render metrics and proof panels.

Input is a JSON manifest:
{
  "artifact_kind": "splat_render_pair_manifest",
  "model_uri": "s3://...",
  "baseline_metrics": {"psnr": {"median": 28.0}},
  "pairs": [
    {
      "id": "camera-001",
      "source_image": "/path/to/source.ppm",
      "rendered_image": "/path/to/render.ppm",
      "lpips": 0.18
    }
  ]
}

PNG/JPEG loading uses Pillow when available. PPM and NPY are supported without
extra packages so this validator stays unit-testable in minimal environments.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any

import numpy as np


def load_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


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


def _read_token(data: bytes, start: int) -> tuple[str, int]:
    index = start
    while index < len(data):
        char = data[index]
        if char == 35:
            while index < len(data) and data[index] not in (10, 13):
                index += 1
        elif chr(char).isspace():
            index += 1
        else:
            break
    end = index
    while end < len(data) and not chr(data[end]).isspace():
        end += 1
    return data[index:end].decode("ascii"), end


def read_ppm(path: Path) -> np.ndarray:
    data = path.read_bytes()
    magic, index = _read_token(data, 0)
    if magic not in {"P3", "P6"}:
        raise ValueError(f"unsupported PPM magic {magic}")
    width_token, index = _read_token(data, index)
    height_token, index = _read_token(data, index)
    max_token, index = _read_token(data, index)
    width = int(width_token)
    height = int(height_token)
    max_value = int(max_token)
    if max_value <= 0:
        raise ValueError("invalid PPM max value")

    if magic == "P3":
        text = data[index:].decode("ascii", errors="replace")
        values = [int(token) for token in text.split() if not token.startswith("#")]
        array = np.asarray(values, dtype=np.float32).reshape((height, width, 3))
    else:
        while index < len(data) and chr(data[index]).isspace():
            index += 1
        raw = data[index : index + width * height * 3]
        array = np.frombuffer(raw, dtype=np.uint8).astype(np.float32).reshape((height, width, 3))
    return np.clip(array / float(max_value), 0.0, 1.0)


def load_image(path_text: str) -> np.ndarray:
    path = Path(path_text)
    if path.suffix.lower() == ".npy":
        array = np.load(path).astype(np.float32)
        if array.max(initial=0.0) > 1.0:
            array = array / 255.0
        return np.clip(array[..., :3], 0.0, 1.0)
    if path.suffix.lower() in {".ppm", ".pnm"}:
        return read_ppm(path)
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(f"Pillow is required to read {path.suffix} images: {path}") from exc
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0


def save_image(path: Path, image: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    image_u8 = np.clip(image * 255.0, 0, 255).astype(np.uint8)
    try:
        from PIL import Image
    except ImportError:
        ppm_path = path.with_suffix(".ppm")
        header = f"P6\n{image_u8.shape[1]} {image_u8.shape[0]}\n255\n".encode("ascii")
        ppm_path.write_bytes(header + image_u8.tobytes())
        return str(ppm_path)
    Image.fromarray(image_u8, mode="RGB").save(path)
    return str(path)


def psnr(reference: np.ndarray, rendered: np.ndarray) -> float:
    mse = float(np.mean((reference - rendered) ** 2))
    if mse <= 1e-12:
        return 100.0
    return round(-10.0 * math.log10(mse), 4)


def ssim(reference: np.ndarray, rendered: np.ndarray) -> float:
    c1 = 0.01**2
    c2 = 0.03**2
    channel_scores: list[float] = []
    for channel in range(3):
        left = reference[..., channel]
        right = rendered[..., channel]
        mu_left = float(left.mean())
        mu_right = float(right.mean())
        var_left = float(((left - mu_left) ** 2).mean())
        var_right = float(((right - mu_right) ** 2).mean())
        covariance = float(((left - mu_left) * (right - mu_right)).mean())
        numerator = (2 * mu_left * mu_right + c1) * (2 * covariance + c2)
        denominator = (mu_left**2 + mu_right**2 + c1) * (var_left + var_right + c2)
        channel_scores.append(numerator / denominator if denominator else 1.0)
    return round(float(np.clip(np.mean(channel_scores), -1.0, 1.0)), 4)


def make_panel(reference: np.ndarray, rendered: np.ndarray) -> np.ndarray:
    diff = np.clip(np.abs(reference - rendered) * 4.0, 0.0, 1.0)
    return np.concatenate([reference, rendered, diff], axis=1)


def load_lpips_state(enabled: bool) -> dict[str, Any] | None:
    if not enabled:
        return None
    try:
        import lpips
        import torch
    except ImportError as exc:
        raise RuntimeError("LPIPS computation requires torch and lpips packages") from exc
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = lpips.LPIPS(net="alex").to(device).eval()
    return {"torch": torch, "model": model, "device": device}


def compute_lpips(reference: np.ndarray, rendered: np.ndarray, state: dict[str, Any] | None) -> float | None:
    if not state:
        return None
    torch = state["torch"]
    with torch.no_grad():
        left = torch.from_numpy(reference.transpose(2, 0, 1)).unsqueeze(0).float().to(state["device"]) * 2.0 - 1.0
        right = torch.from_numpy(rendered.transpose(2, 0, 1)).unsqueeze(0).float().to(state["device"]) * 2.0 - 1.0
        return round(float(state["model"](left, right).item()), 4)


def evaluate_pair(
    pair: dict[str, Any],
    panel_dir: Path,
    allow_resize: bool,
    lpips_state: dict[str, Any] | None,
) -> tuple[dict[str, Any], str | None]:
    reference = load_image(str(pair["source_image"]))
    rendered = load_image(str(pair["rendered_image"]))
    pair_id = str(pair.get("id") or pair.get("camera_id") or Path(str(pair["source_image"])).stem)

    if reference.shape != rendered.shape:
        if not allow_resize:
            return {
                "id": pair_id,
                "source_image": pair.get("source_image"),
                "rendered_image": pair.get("rendered_image"),
                "status": "failed",
                "error": f"shape_mismatch reference={list(reference.shape)} rendered={list(rendered.shape)}",
            }, None
        try:
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("Pillow is required for --allow-resize") from exc
        resized = Image.fromarray(np.clip(rendered * 255.0, 0, 255).astype(np.uint8)).resize(
            (reference.shape[1], reference.shape[0]),
            Image.Resampling.LANCZOS,
        )
        rendered = np.asarray(resized, dtype=np.float32) / 255.0

    metrics = {
        "psnr": psnr(reference, rendered),
        "ssim": ssim(reference, rendered),
    }
    if pair.get("lpips") is not None:
        metrics["lpips"] = round(float(pair["lpips"]), 4)
    else:
        lpips_value = compute_lpips(reference, rendered, lpips_state)
        if lpips_value is not None:
            metrics["lpips"] = lpips_value

    panel_path = save_image(panel_dir / f"{pair_id}.png", make_panel(reference, rendered))
    return {
        "id": pair_id,
        "camera_id": pair.get("camera_id"),
        "image_name": pair.get("image_name"),
        "source_image": pair.get("source_image"),
        "rendered_image": pair.get("rendered_image"),
        "proof_panel": panel_path,
        "status": "pass",
        "metrics": metrics,
    }, panel_path


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.pairs_json)
    pair_entries = manifest.get("pairs") or []
    panel_dir = Path(args.panel_dir)
    per_image: list[dict[str, Any]] = []
    blockers: list[str] = []
    panel_paths: list[str] = []
    try:
        lpips_state = load_lpips_state(args.compute_lpips)
    except Exception as exc:
        lpips_state = None
        blockers.append(str(exc))

    for pair in pair_entries[: args.max_pairs or None]:
        try:
            result, panel_path = evaluate_pair(pair, panel_dir, args.allow_resize, lpips_state)
            per_image.append(result)
            if panel_path:
                panel_paths.append(panel_path)
            if result.get("status") != "pass":
                blockers.append(f"{result.get('id')}: {result.get('error')}")
        except Exception as exc:
            pair_id = str(pair.get("id") or pair.get("camera_id") or pair.get("source_image") or len(per_image))
            per_image.append({"id": pair_id, "status": "failed", "error": str(exc)})
            blockers.append(f"{pair_id}: {exc}")

    passed = [item for item in per_image if item.get("status") == "pass"]
    psnr_values = [float(item["metrics"]["psnr"]) for item in passed if item.get("metrics", {}).get("psnr") is not None]
    ssim_values = [float(item["metrics"]["ssim"]) for item in passed if item.get("metrics", {}).get("ssim") is not None]
    lpips_values = [float(item["metrics"]["lpips"]) for item in passed if item.get("metrics", {}).get("lpips") is not None]
    if passed and len(lpips_values) != len(passed):
        blockers.append("lpips_not_computed_for_all_pairs")

    report = {
        "schema_version": 1,
        "artifact_kind": "splat_heldout_render_metrics",
        "decision": "fail" if blockers else "pass",
        "model_uri": manifest.get("model_uri"),
        "source_artifact_uri": manifest.get("source_artifact_uri"),
        "render_artifact_uri": manifest.get("render_artifact_uri"),
        "baseline_metrics": manifest.get("baseline_metrics") or {},
        "holdout_count": len(per_image),
        "successful_render_count": len(passed),
        "metrics": {
            "psnr": summarize(psnr_values),
            "ssim": summarize(ssim_values),
            "lpips": summarize(lpips_values),
        },
        "proof_panels": {
            "panel_dir": str(panel_dir),
            "count": len(panel_paths),
            "paths": panel_paths,
        },
        "per_image": per_image,
        "blockers": blockers,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs-json", required=True)
    parser.add_argument("--panel-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-pairs", type=int, default=0)
    parser.add_argument("--allow-resize", action="store_true")
    parser.add_argument("--compute-lpips", action="store_true")
    args = parser.parse_args()

    report = build_report(args)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "holdout_count": report["holdout_count"],
                "successful_render_count": report["successful_render_count"],
                "output": str(output_path),
            },
            indent=2,
        )
    )
    return 1 if report["decision"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
