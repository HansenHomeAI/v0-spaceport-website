#!/usr/bin/env python3
"""
Export Splatfacto-W foreground gaussians and a baked background skybox.

The foreground is written as a SOGS-compatible PLY. When the background model
is enabled, we also bake the learned SH background into an equirectangular WebP
that the hosted viewer can load as a skybox.
"""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from PIL import Image
from gsplat.cuda._wrapper import spherical_harmonics
from nerfstudio.utils.eval_utils import eval_setup
from projected_skybox import ProjectedSkyboxSettings, build_projected_photo_skybox


def write_ply(filename: Path, count: int, tensors: OrderedDict[str, np.ndarray]) -> None:
    with open(filename, "wb") as ply_file:
        ply_file.write(b"ply\n")
        ply_file.write(b"format binary_little_endian 1.0\n")
        ply_file.write(f"element vertex {count}\n".encode())
        for key, tensor in tensors.items():
            data_type = "float" if tensor.dtype.kind == "f" else "uchar"
            ply_file.write(f"property {data_type} {key}\n".encode())
        ply_file.write(b"end_header\n")

        for index in range(count):
            for tensor in tensors.values():
                value = tensor[index]
                if tensor.dtype.kind == "f":
                    ply_file.write(np.float32(value).tobytes())
                else:
                    ply_file.write(value.tobytes())


def build_foreground_ply(model, output_dir: Path, camera_idx: int) -> Path:
    model.set_camera_idx(camera_idx)

    positions = model.means.detach().cpu().numpy()
    count = positions.shape[0]
    tensors: OrderedDict[str, np.ndarray] = OrderedDict()

    tensors["x"] = positions[:, 0]
    tensors["y"] = positions[:, 1]
    tensors["z"] = positions[:, 2]
    tensors["nx"] = np.zeros(count, dtype=np.float32)
    tensors["ny"] = np.zeros(count, dtype=np.float32)
    tensors["nz"] = np.zeros(count, dtype=np.float32)

    shs_0 = model.shs_0.contiguous().detach().cpu().numpy()
    for channel in range(shs_0.shape[1]):
        tensors[f"f_dc_{channel}"] = shs_0[:, channel, None]

    shs_rest = model.shs_rest.transpose(1, 2).contiguous().detach().cpu().numpy()
    shs_rest = shs_rest.reshape((count, -1))
    for channel in range(shs_rest.shape[-1]):
        tensors[f"f_rest_{channel}"] = shs_rest[:, channel, None]

    tensors["opacity"] = model.opacities.detach().cpu().numpy()

    scales = model.scales.detach().cpu().numpy()
    for axis in range(3):
        tensors[f"scale_{axis}"] = scales[:, axis, None]

    quats = model.quats.detach().cpu().numpy()
    for axis in range(4):
        tensors[f"rot_{axis}"] = quats[:, axis, None]

    finite_mask = np.ones(count, dtype=bool)
    for tensor in tensors.values():
        finite_mask &= np.isfinite(tensor).all(axis=-1)

    if not finite_mask.all():
        for key, tensor in tensors.items():
            tensors[key] = tensor[finite_mask]
        count = int(finite_mask.sum())

    ply_path = output_dir / "splat.ply"
    write_ply(ply_path, count, tensors)
    return ply_path


def build_equirect_directions(width: int, height: int, device: torch.device) -> torch.Tensor:
    xs = (torch.arange(width, device=device, dtype=torch.float32) + 0.5) / width
    ys = (torch.arange(height, device=device, dtype=torch.float32) + 0.5) / height
    u, v = torch.meshgrid(xs, ys, indexing="xy")

    theta = (u - 0.5) * (2.0 * torch.pi)
    phi = (0.5 - v) * torch.pi

    cos_phi = torch.cos(phi)
    directions = torch.stack(
        (
            cos_phi * torch.sin(theta),
            torch.sin(phi),
            cos_phi * torch.cos(theta),
        ),
        dim=-1,
    )
    return directions.reshape(-1, 3)


def resolve_appearance_embedding(model, appearance_mode: str, camera_idx: int) -> tuple[torch.Tensor, dict]:
    if appearance_mode == "average":
        embedding = model.appearance_embeds.weight.mean(dim=0)
        return embedding, {"appearance_mode": "average"}

    embedding = model.appearance_embeds(torch.tensor(camera_idx, device=model.device))
    return embedding, {
        "appearance_mode": "camera",
        "camera_idx": int(camera_idx),
    }


def render_learned_background(
    model,
    width: int,
    height: int,
    appearance_mode: str,
    camera_idx: int,
) -> tuple[Optional[np.ndarray], dict]:
    if not getattr(model.config, "enable_bg_model", False) or getattr(model, "bg_model", None) is None:
        return None, {"background_model_enabled": False}

    appearance_embedding, metadata = resolve_appearance_embedding(model, appearance_mode, camera_idx)
    directions = build_equirect_directions(width, height, model.device)

    with torch.no_grad():
        sh_coeffs = model.bg_model.get_sh_coeffs(appearance_embedding=appearance_embedding).float()
        colors = spherical_harmonics(
            degrees_to_use=model.config.bg_sh_degree,
            coeffs=sh_coeffs.expand(directions.shape[0], -1, -1),
            dirs=directions,
        )
        colors = torch.clamp(colors.reshape(height, width, 3), 0.0, 1.0)

    return colors.detach().cpu().numpy().astype(np.float32), {
        "background_model_enabled": True,
        "bg_sh_degree": int(model.config.bg_sh_degree),
        **metadata,
    }


def build_background_skybox(
    model,
    output_dir: Path,
    data_dir: Optional[Path],
    width: int,
    height: int,
    quality: int,
    appearance_mode: str,
    camera_idx: int,
    projected_skybox_settings: ProjectedSkyboxSettings,
) -> Optional[Path]:
    learned_fill_rgb, learned_background_metadata = render_learned_background(
        model=model,
        width=width,
        height=height,
        appearance_mode=appearance_mode,
        camera_idx=camera_idx,
    )
    if learned_fill_rgb is None:
        learned_fill_rgb = np.zeros((height, width, 3), dtype=np.float32)

    if projected_skybox_settings.enabled and data_dir is not None:
        manifest = build_projected_photo_skybox(
            data_dir=data_dir,
            output_dir=output_dir,
            width=width,
            height=height,
            quality=quality,
            fill_rgb=learned_fill_rgb,
            settings=projected_skybox_settings,
        )
        manifest.update(learned_background_metadata)
        (output_dir / "background_manifest.json").write_text(json.dumps(manifest, indent=2))
        return output_dir / "background_skybox.webp"

    rgb = (np.clip(learned_fill_rgb, 0.0, 1.0) * 255.0).round().astype(np.uint8)
    skybox_path = output_dir / "background_skybox.webp"
    Image.fromarray(rgb, mode="RGB").save(skybox_path, format="WEBP", quality=quality, method=6)
    manifest = {
        "version": 2,
        "asset": skybox_path.name,
        "width": width,
        "height": height,
        "background_skybox_generation_method": "projected_photo_low_frequency",
        "projection_mode": "projected_photo_low_frequency",
        "observed_coverage_ratio": 0.0,
        "filled_coverage_ratio": 1.0,
        **learned_background_metadata,
    }
    (output_dir / "background_manifest.json").write_text(json.dumps(manifest, indent=2))
    return skybox_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Splatfacto-W assets")
    parser.add_argument("--load-config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--camera-idx", type=int, default=0)
    parser.add_argument("--background-width", type=int, default=2048)
    parser.add_argument("--background-height", type=int, default=1024)
    parser.add_argument("--background-quality", type=int, default=95)
    parser.add_argument(
        "--background-appearance-mode",
        choices=("average", "camera", "auto_camera"),
        default="auto_camera",
    )
    parser.add_argument("--enable-projected-photo-skybox", choices=("true", "false"), default="true")
    parser.add_argument("--skybox-composition-mode", default="projected_photo_low_frequency")
    parser.add_argument("--skybox-world-up-source", default="colmap_pose_consensus")
    parser.add_argument("--skybox-min-sky-mask-ratio", type=float, default=0.01)
    parser.add_argument("--skybox-min-observations-per-pixel", type=int, default=1)
    parser.add_argument("--skybox-blend-edge-feather-px", type=int, default=24)
    parser.add_argument("--skybox-low-frequency-fill", choices=("true", "false"), default="true")
    parser.add_argument("--skybox-projection-max-long-side", type=int, default=1024)
    parser.add_argument("--skybox-projection-mask-mode", default="semantic_horizon_fill")
    parser.add_argument("--skybox-projection-confidence-threshold", type=float, default=0.25)
    parser.add_argument("--skybox-projection-horizon-smoothing-px", type=int, default=31)
    parser.add_argument("--training-mask-mode", choices=("exclude_sky", "keep_sky"), default="exclude_sky")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    _, pipeline, _, _ = eval_setup(args.load_config)
    model = pipeline.model

    if not hasattr(model, "set_camera_idx") or not hasattr(model, "bg_model"):
        raise RuntimeError("Loaded model is not compatible with Splatfacto-W asset export")

    build_foreground_ply(model, args.output_dir, args.camera_idx)
    projected_skybox_settings = ProjectedSkyboxSettings(
        enabled=args.enable_projected_photo_skybox == "true",
        composition_mode=str(args.skybox_composition_mode),
        world_up_source=str(args.skybox_world_up_source),
        min_sky_mask_ratio=float(args.skybox_min_sky_mask_ratio),
        min_observations_per_pixel=int(args.skybox_min_observations_per_pixel),
        blend_edge_feather_px=int(args.skybox_blend_edge_feather_px),
        low_frequency_fill=args.skybox_low_frequency_fill == "true",
        training_mask_mode=str(args.training_mask_mode),
        projection_max_long_side=int(args.skybox_projection_max_long_side),
        projection_mask_mode=str(args.skybox_projection_mask_mode),
        projection_confidence_threshold=float(args.skybox_projection_confidence_threshold),
        projection_horizon_smoothing_px=int(args.skybox_projection_horizon_smoothing_px),
    )
    skybox_path = build_background_skybox(
        model=model,
        output_dir=args.output_dir,
        data_dir=args.data_dir,
        width=args.background_width,
        height=args.background_height,
        quality=args.background_quality,
        appearance_mode="camera" if args.background_appearance_mode == "auto_camera" else args.background_appearance_mode,
        camera_idx=args.camera_idx,
        projected_skybox_settings=projected_skybox_settings,
    )

    summary = {
        "ply": "splat.ply",
        "skybox": skybox_path.name if skybox_path else None,
        "camera_idx": args.camera_idx,
        "background_appearance_mode": args.background_appearance_mode,
        "projected_photo_skybox": args.enable_projected_photo_skybox == "true",
        "skybox_composition_mode": args.skybox_composition_mode,
        "training_mask_mode": args.training_mask_mode,
    }
    (args.output_dir / "export_manifest.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
