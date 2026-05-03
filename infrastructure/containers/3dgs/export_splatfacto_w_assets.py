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
from typing import Any, Mapping, Optional

import numpy as np
import torch
from PIL import Image
from gsplat.cuda._wrapper import spherical_harmonics
from nerfstudio.utils.eval_utils import eval_setup


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


def appearance_embedding_count(model) -> Optional[int]:
    appearance_embeds = getattr(model, "appearance_embeds", None)
    if appearance_embeds is None:
        return None

    count = getattr(appearance_embeds, "num_embeddings", None)
    if count is None:
        weight = getattr(appearance_embeds, "weight", None)
        shape = getattr(weight, "shape", None)
        if shape:
            count = shape[0]

    try:
        count = int(count)
    except (TypeError, ValueError):
        return None
    return count if count > 0 else None


def resolve_appearance_camera_idx(model, camera_idx: int) -> tuple[int, dict[str, Any]]:
    requested_idx = int(camera_idx)
    count = appearance_embedding_count(model)
    if count is None:
        return requested_idx, {
            "requested_camera_idx": requested_idx,
            "appearance_camera_idx": requested_idx,
            "appearance_num_embeddings": None,
            "appearance_camera_clamped": False,
        }

    safe_idx = min(max(requested_idx, 0), count - 1)
    return safe_idx, {
        "requested_camera_idx": requested_idx,
        "appearance_camera_idx": safe_idx,
        "appearance_num_embeddings": count,
        "appearance_camera_clamped": safe_idx != requested_idx,
    }


def tensor_to_numpy(value) -> Optional[np.ndarray]:
    if value is None:
        return None
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    try:
        return np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError):
        return None


def resolve_dataparser_original_transform(pipeline) -> tuple[Optional[np.ndarray], float, str]:
    datamanager = getattr(pipeline, "datamanager", None)
    outputs = getattr(datamanager, "train_dataparser_outputs", None)
    if outputs is None:
        outputs = getattr(datamanager, "dataparser_outputs", None)
    if outputs is None:
        return None, 1.0, "missing_dataparser_outputs"

    transform = tensor_to_numpy(getattr(outputs, "dataparser_transform", None))
    if transform is None:
        transform = tensor_to_numpy(getattr(outputs, "transform", None))
    if transform is None:
        return None, 1.0, "missing_dataparser_transform"
    if transform.shape == (3, 4):
        affine = np.eye(4, dtype=np.float64)
        affine[:3, :4] = transform
    elif transform.shape == (4, 4):
        affine = transform
    else:
        return None, 1.0, f"unsupported_dataparser_transform_shape_{transform.shape}"

    scale_value = getattr(outputs, "dataparser_scale", 1.0)
    scale_array = tensor_to_numpy(scale_value)
    if scale_array is None or scale_array.size == 0:
        scale = 1.0
    else:
        scale = float(scale_array.reshape(-1)[0])
    if not np.isfinite(scale) or abs(scale) <= 1e-9:
        scale = 1.0
    return affine, scale, "train_dataparser_outputs"


def positions_to_original_space(positions: np.ndarray, pipeline) -> tuple[np.ndarray, dict]:
    affine, scale, source = resolve_dataparser_original_transform(pipeline)
    metadata = {
        "coordinate_frame": "original",
        "dataparser_transform_source": source,
        "dataparser_scale": scale,
        "applied": False,
        "position_transform_applied": False,
        "scale_transform_applied": False,
        "rotation_transform_applied": False,
    }
    if affine is None:
        return positions, metadata
    inverse = np.linalg.inv(affine)
    homogeneous = np.concatenate(
        [positions.astype(np.float64) / scale, np.ones((positions.shape[0], 1), dtype=np.float64)],
        axis=1,
    )
    transformed = (inverse @ homogeneous.T).T[:, :3].astype(np.float32)
    metadata["applied"] = True
    metadata["position_transform_applied"] = True
    metadata["dataparser_transform"] = affine[:3, :4].tolist()
    metadata["model_to_output_linear"] = (inverse[:3, :3] / scale).tolist()
    return transformed, metadata


def resolve_pipeline_transforms_payload(pipeline) -> tuple[Mapping[str, Any] | None, str]:
    datamanager = getattr(pipeline, "datamanager", None)
    candidates = [
        getattr(datamanager, "dataparser", None),
        getattr(datamanager, "train_dataparser", None),
        getattr(datamanager, "_dataparser", None),
    ]
    for candidate in candidates:
        config = getattr(candidate, "config", None)
        data_dir = getattr(config, "data", None)
        if not data_dir:
            continue
        data_path = Path(data_dir)
        for file_name in ("transforms.json", "transforms.full.json"):
            transforms_path = data_path / file_name
            if not transforms_path.exists():
                continue
            with open(transforms_path, "r", encoding="utf-8") as handle:
                return json.load(handle), str(transforms_path)
    return None, "missing_transforms_payload"


def resolve_planner_frame_transform(pipeline) -> tuple[Optional[np.ndarray], float, np.ndarray, str]:
    transforms_payload, source = resolve_pipeline_transforms_payload(pipeline)
    if transforms_payload is None:
        return None, 1.0, np.zeros(3, dtype=np.float64), source
    applied_transform_payload = transforms_payload.get("applied_transform")
    if not isinstance(applied_transform_payload, list):
        return None, 1.0, np.zeros(3, dtype=np.float64), f"{source}:missing_applied_transform"
    applied_transform = np.asarray(applied_transform_payload, dtype=np.float64)
    if applied_transform.shape == (3, 4):
        affine = np.eye(4, dtype=np.float64)
        affine[:3, :4] = applied_transform
    elif applied_transform.shape == (4, 4):
        affine = applied_transform
    else:
        return None, 1.0, np.zeros(3, dtype=np.float64), f"{source}:unsupported_applied_transform_shape_{applied_transform.shape}"

    scale_value = transforms_payload.get("scale", 1.0)
    try:
        scale = float(scale_value)
    except (TypeError, ValueError):
        scale = 1.0
    if not np.isfinite(scale) or abs(scale) <= 1e-9:
        scale = 1.0

    offset_payload = transforms_payload.get("offset", [0.0, 0.0, 0.0])
    try:
        offset = np.asarray(offset_payload, dtype=np.float64).reshape(3)
    except (TypeError, ValueError):
        offset = np.zeros(3, dtype=np.float64)
    return affine, scale, offset, source


def positions_to_planner_space(positions: np.ndarray, pipeline) -> tuple[np.ndarray, dict]:
    original_positions, metadata = positions_to_original_space(positions, pipeline)
    metadata["coordinate_frame"] = "planner"
    metadata["planner_transform_applied"] = False
    planner_affine, planner_scale, planner_offset, planner_source = resolve_planner_frame_transform(pipeline)
    metadata["planner_transform_source"] = planner_source
    metadata["planner_scale"] = planner_scale
    metadata["planner_offset"] = planner_offset.tolist()
    if planner_affine is None:
        return original_positions, metadata

    homogeneous = np.concatenate(
        [original_positions.astype(np.float64), np.ones((original_positions.shape[0], 1), dtype=np.float64)],
        axis=1,
    )
    transformed = (planner_affine @ homogeneous.T).T[:, :3]
    transformed = transformed * planner_scale + planner_offset[None, :]
    metadata["applied"] = True
    metadata["planner_transform_applied"] = True
    metadata["planner_transform"] = planner_affine[:3, :4].tolist()

    output_linear = np.asarray(metadata.get("model_to_output_linear"), dtype=np.float64)
    if output_linear.shape == (3, 3):
        metadata["model_to_output_linear"] = (planner_scale * planner_affine[:3, :3] @ output_linear).tolist()
    return transformed.astype(np.float32), metadata


def log_scales_to_original_space(raw_scales: np.ndarray, transform_metadata: Mapping[str, Any]) -> np.ndarray:
    if not transform_metadata.get("position_transform_applied"):
        return raw_scales
    scale = float(transform_metadata.get("dataparser_scale") or 1.0)
    if not np.isfinite(scale) or scale <= 1e-9:
        return raw_scales
    transform_metadata["scale_transform_applied"] = True
    return (raw_scales.astype(np.float32) - np.float32(np.log(scale))).astype(np.float32)


def log_scales_to_output_space(raw_scales: np.ndarray, transform_metadata: Mapping[str, Any]) -> np.ndarray:
    transformed = log_scales_to_original_space(raw_scales, transform_metadata)
    if transform_metadata.get("coordinate_frame") != "planner" or not transform_metadata.get("planner_transform_applied"):
        return transformed
    planner_scale = float(transform_metadata.get("planner_scale") or 1.0)
    if not np.isfinite(planner_scale) or planner_scale <= 1e-9:
        return transformed
    transform_metadata["planner_scale_transform_applied"] = True
    return (transformed.astype(np.float32) + np.float32(np.log(planner_scale))).astype(np.float32)


def _normalize_quaternions(quats: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(quats, axis=1, keepdims=True)
    norms = np.where(norms > 1e-9, norms, 1.0)
    return (quats / norms).astype(np.float32)


def _quaternions_to_rotation_matrices(quats: np.ndarray) -> np.ndarray:
    normalized = _normalize_quaternions(quats.astype(np.float64))
    w = normalized[:, 0]
    x = normalized[:, 1]
    y = normalized[:, 2]
    z = normalized[:, 3]
    matrices = np.empty((len(normalized), 3, 3), dtype=np.float64)
    matrices[:, 0, 0] = 1.0 - 2.0 * (y * y + z * z)
    matrices[:, 0, 1] = 2.0 * (x * y - z * w)
    matrices[:, 0, 2] = 2.0 * (x * z + y * w)
    matrices[:, 1, 0] = 2.0 * (x * y + z * w)
    matrices[:, 1, 1] = 1.0 - 2.0 * (x * x + z * z)
    matrices[:, 1, 2] = 2.0 * (y * z - x * w)
    matrices[:, 2, 0] = 2.0 * (x * z - y * w)
    matrices[:, 2, 1] = 2.0 * (y * z + x * w)
    matrices[:, 2, 2] = 1.0 - 2.0 * (x * x + y * y)
    return matrices


def _rotation_matrices_to_quaternions(matrices: np.ndarray) -> np.ndarray:
    quats = np.empty((matrices.shape[0], 4), dtype=np.float64)
    trace = matrices[:, 0, 0] + matrices[:, 1, 1] + matrices[:, 2, 2]

    positive = trace > 0.0
    s = np.sqrt(np.maximum(trace[positive] + 1.0, 1e-12)) * 2.0
    quats[positive, 0] = 0.25 * s
    quats[positive, 1] = (matrices[positive, 2, 1] - matrices[positive, 1, 2]) / s
    quats[positive, 2] = (matrices[positive, 0, 2] - matrices[positive, 2, 0]) / s
    quats[positive, 3] = (matrices[positive, 1, 0] - matrices[positive, 0, 1]) / s

    remaining = ~positive
    case_x = remaining & (matrices[:, 0, 0] > matrices[:, 1, 1]) & (matrices[:, 0, 0] > matrices[:, 2, 2])
    s = np.sqrt(np.maximum(1.0 + matrices[case_x, 0, 0] - matrices[case_x, 1, 1] - matrices[case_x, 2, 2], 1e-12)) * 2.0
    quats[case_x, 0] = (matrices[case_x, 2, 1] - matrices[case_x, 1, 2]) / s
    quats[case_x, 1] = 0.25 * s
    quats[case_x, 2] = (matrices[case_x, 0, 1] + matrices[case_x, 1, 0]) / s
    quats[case_x, 3] = (matrices[case_x, 0, 2] + matrices[case_x, 2, 0]) / s

    case_y = remaining & ~case_x & (matrices[:, 1, 1] > matrices[:, 2, 2])
    s = np.sqrt(np.maximum(1.0 + matrices[case_y, 1, 1] - matrices[case_y, 0, 0] - matrices[case_y, 2, 2], 1e-12)) * 2.0
    quats[case_y, 0] = (matrices[case_y, 0, 2] - matrices[case_y, 2, 0]) / s
    quats[case_y, 1] = (matrices[case_y, 0, 1] + matrices[case_y, 1, 0]) / s
    quats[case_y, 2] = 0.25 * s
    quats[case_y, 3] = (matrices[case_y, 1, 2] + matrices[case_y, 2, 1]) / s

    case_z = remaining & ~case_x & ~case_y
    s = np.sqrt(np.maximum(1.0 + matrices[case_z, 2, 2] - matrices[case_z, 0, 0] - matrices[case_z, 1, 1], 1e-12)) * 2.0
    quats[case_z, 0] = (matrices[case_z, 1, 0] - matrices[case_z, 0, 1]) / s
    quats[case_z, 1] = (matrices[case_z, 0, 2] + matrices[case_z, 2, 0]) / s
    quats[case_z, 2] = (matrices[case_z, 1, 2] + matrices[case_z, 2, 1]) / s
    quats[case_z, 3] = 0.25 * s
    return _normalize_quaternions(quats)


def quaternions_to_original_space(quats: np.ndarray, transform_metadata: Mapping[str, Any]) -> np.ndarray:
    if not transform_metadata.get("position_transform_applied"):
        return quats
    transform_payload = transform_metadata.get("dataparser_transform")
    if not transform_payload:
        return quats
    transform = np.asarray(transform_payload, dtype=np.float64)
    if transform.shape != (3, 4):
        return quats
    try:
        model_to_original_linear = np.linalg.inv(transform[:, :3])
    except np.linalg.LinAlgError:
        return quats
    model_to_original_rotation = linear_to_rotation(model_to_original_linear)
    gaussian_rotations = _quaternions_to_rotation_matrices(quats)
    transformed = np.einsum("ij,njk->nik", model_to_original_rotation, gaussian_rotations)
    transform_metadata["rotation_transform_applied"] = True
    transform_metadata["model_to_original_rotation"] = model_to_original_rotation.tolist()
    return _rotation_matrices_to_quaternions(transformed)


def linear_to_rotation(linear: np.ndarray) -> np.ndarray:
    u, _singular_values, vh = np.linalg.svd(linear)
    rotation = u @ vh
    if np.linalg.det(rotation) < 0.0:
        u[:, -1] *= -1.0
        rotation = u @ vh
    return rotation


def quaternions_to_output_space(quats: np.ndarray, transform_metadata: Mapping[str, Any]) -> np.ndarray:
    if transform_metadata.get("coordinate_frame") != "planner" or not transform_metadata.get("planner_transform_applied"):
        return quaternions_to_original_space(quats, transform_metadata)
    output_linear = np.asarray(transform_metadata.get("model_to_output_linear"), dtype=np.float64)
    if output_linear.shape != (3, 3):
        return quaternions_to_original_space(quats, transform_metadata)
    output_rotation = linear_to_rotation(output_linear)
    gaussian_rotations = _quaternions_to_rotation_matrices(quats)
    transformed = np.einsum("ij,njk->nik", output_rotation, gaussian_rotations)
    transform_metadata["rotation_transform_applied"] = True
    transform_metadata["model_to_output_rotation"] = output_rotation.tolist()
    return _rotation_matrices_to_quaternions(transformed)


def build_foreground_ply(model, output_dir: Path, camera_idx: int, *, pipeline=None, coordinate_frame: str = "model") -> tuple[Path, dict]:
    appearance_camera_idx, appearance_metadata = resolve_appearance_camera_idx(model, camera_idx)
    model.set_camera_idx(appearance_camera_idx)

    positions = model.means.detach().cpu().numpy()
    transform_metadata = {"coordinate_frame": "model", "applied": False}
    if coordinate_frame == "original":
        if pipeline is None:
            transform_metadata = {
                "coordinate_frame": "original",
                "applied": False,
                "dataparser_transform_source": "missing_pipeline",
            }
        else:
            positions, transform_metadata = positions_to_original_space(positions, pipeline)
    elif coordinate_frame == "planner":
        if pipeline is None:
            transform_metadata = {
                "coordinate_frame": "planner",
                "applied": False,
                "dataparser_transform_source": "missing_pipeline",
                "planner_transform_source": "missing_pipeline",
            }
        else:
            positions, transform_metadata = positions_to_planner_space(positions, pipeline)
    transform_metadata["appearance"] = appearance_metadata
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
    if coordinate_frame in {"original", "planner"}:
        scales = log_scales_to_output_space(scales, transform_metadata)
    for axis in range(3):
        tensors[f"scale_{axis}"] = scales[:, axis, None]

    quats = model.quats.detach().cpu().numpy()
    if coordinate_frame in {"original", "planner"}:
        quats = quaternions_to_output_space(quats, transform_metadata)
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
    return ply_path, transform_metadata


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
        return embedding, {
            "appearance_mode": "average",
            "appearance_num_embeddings": appearance_embedding_count(model),
        }

    appearance_camera_idx, metadata = resolve_appearance_camera_idx(model, camera_idx)
    embedding = model.appearance_embeds(torch.tensor(appearance_camera_idx, device=model.device))
    return embedding, {
        "appearance_mode": "camera",
        "camera_idx": int(camera_idx),
        **metadata,
    }


def build_background_skybox(
    model,
    output_dir: Path,
    width: int,
    height: int,
    quality: int,
    appearance_mode: str,
    camera_idx: int,
) -> Optional[Path]:
    if not getattr(model.config, "enable_bg_model", False) or getattr(model, "bg_model", None) is None:
        return None

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

    rgb = (colors.detach().cpu().numpy() * 255.0).round().astype(np.uint8)
    skybox_path = output_dir / "background_skybox.webp"
    Image.fromarray(rgb, mode="RGB").save(skybox_path, format="WEBP", quality=quality, method=6)

    manifest = {
        "version": 1,
        "asset": skybox_path.name,
        "width": width,
        "height": height,
        "bg_sh_degree": int(model.config.bg_sh_degree),
        **metadata,
    }
    (output_dir / "background_manifest.json").write_text(json.dumps(manifest, indent=2))
    return skybox_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Splatfacto-W assets")
    parser.add_argument("--load-config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--camera-idx", type=int, default=0)
    parser.add_argument("--background-width", type=int, default=2048)
    parser.add_argument("--background-height", type=int, default=1024)
    parser.add_argument("--background-quality", type=int, default=95)
    parser.add_argument(
        "--background-appearance-mode",
        choices=("average", "camera", "auto_camera"),
        default="auto_camera",
    )
    parser.add_argument("--skip-background", action="store_true")
    parser.add_argument(
        "--foreground-coordinate-frame",
        choices=("model", "original", "planner"),
        default="model",
        help="Export foreground Gaussian positions in model, inverse dataparser original, or planner manifest space.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    _, pipeline, _, _ = eval_setup(args.load_config)
    model = pipeline.model

    if not hasattr(model, "set_camera_idx") or not hasattr(model, "bg_model"):
        raise RuntimeError("Loaded model is not compatible with Splatfacto-W asset export")

    _, foreground_transform = build_foreground_ply(
        model,
        args.output_dir,
        args.camera_idx,
        pipeline=pipeline,
        coordinate_frame=args.foreground_coordinate_frame,
    )
    skybox_path = None
    if not args.skip_background:
        skybox_path = build_background_skybox(
            model=model,
            output_dir=args.output_dir,
            width=args.background_width,
            height=args.background_height,
            quality=args.background_quality,
            appearance_mode="camera" if args.background_appearance_mode == "auto_camera" else args.background_appearance_mode,
            camera_idx=args.camera_idx,
        )

    summary = {
        "ply": "splat.ply",
        "skybox": skybox_path.name if skybox_path else None,
        "camera_idx": args.camera_idx,
        "background_appearance_mode": args.background_appearance_mode,
        "background_skipped": bool(args.skip_background),
        "foreground_coordinate_frame": args.foreground_coordinate_frame,
        "foreground_transform": foreground_transform,
    }
    (args.output_dir / "export_manifest.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
