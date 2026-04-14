from __future__ import annotations

import io
import json
import math
import struct
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image


SH_C0 = 0.28209479177387814
DEFAULT_PREVIEW_MAX_POINTS = 50_000
DEFAULT_PREVIEW_MIN_ALPHA = 0.12


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _sigmoid(value: float) -> float:
    if value >= 0:
        exponent = math.exp(-value)
        return 1.0 / (1.0 + exponent)
    exponent = math.exp(value)
    return exponent / (1.0 + exponent)


def _unlog(value: float) -> float:
    return math.copysign(math.exp(abs(value)) - 1.0, value)


def _lerp(minimum: float, maximum: float, t: float) -> float:
    return minimum + (maximum - minimum) * t


def _is_http_path(raw_value: str) -> bool:
    return raw_value.startswith("http://") or raw_value.startswith("https://")


class BundleAssetSource:
    def __init__(self, bundle_root: str | Path):
        raw_value = str(bundle_root).strip()
        if not raw_value:
            raise ValueError("bundle_root must be a non-empty path or URL")

        if _is_http_path(raw_value):
            parsed = urllib.parse.urlparse(raw_value)
            if parsed.path.endswith(".json"):
                self.meta_relative_path = Path(parsed.path).name
                root_path = parsed.path[: -len(self.meta_relative_path)]
                self.root = urllib.parse.urlunparse(parsed._replace(path=root_path, query="", fragment=""))
            else:
                self.meta_relative_path = "meta.json"
                self.root = raw_value if raw_value.endswith("/") else f"{raw_value}/"
            self.is_remote = True
            self.root_path = None
            return

        path = Path(raw_value)
        if path.is_file():
            self.meta_relative_path = path.name
            self.root_path = path.parent.resolve()
        else:
            self.meta_relative_path = "meta.json"
            self.root_path = path.resolve()
        self.root = None
        self.is_remote = False

    def _resolve(self, relative_path: str) -> str | Path:
        normalized = relative_path.lstrip("/")
        if self.is_remote:
            return urllib.parse.urljoin(self.root, normalized)
        return self.root_path / normalized

    def read_bytes(self, relative_path: str) -> bytes:
        target = self._resolve(relative_path)
        if self.is_remote:
            with urllib.request.urlopen(str(target), timeout=120) as response:
                return response.read()
        return Path(target).read_bytes()

    def read_json(self, relative_path: str) -> dict[str, Any]:
        return json.loads(self.read_bytes(relative_path).decode("utf-8"))

    def resolve_asset_reference(self, relative_path: str) -> str:
        target = self._resolve(relative_path)
        return str(target)


def _decode_image_rgba(image_bytes: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(image_bytes))
    image.load()
    return image.convert("RGBA")


def _decode_position(
    meta: dict[str, Any],
    means_low: tuple[int, int, int, int],
    means_high: tuple[int, int, int, int],
    *,
    legacy_format: bool,
) -> tuple[float, float, float]:
    mins = meta["means"]["mins"]
    maxs = meta["means"]["maxs"]
    components = []
    for channel in range(3):
        quantized = (int(means_high[channel]) << 8) | int(means_low[channel])
        decoded = _lerp(float(mins[channel]), float(maxs[channel]), quantized / 65535.0)
        components.append(decoded if legacy_format else _unlog(decoded))
    return (components[0], components[1], components[2])


def _decode_legacy_sh0(meta: dict[str, Any], pixel: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    mins = meta["sh0"]["mins"]
    maxs = meta["sh0"]["maxs"]
    coeffs = [
        _lerp(float(mins[channel]), float(maxs[channel]), int(pixel[channel]) / 255.0) for channel in range(3)
    ]
    opacity_logit = _lerp(float(mins[3]), float(maxs[3]), int(pixel[3]) / 255.0)
    alpha = _sigmoid(opacity_logit)
    rgb = [int(round(_clamp01(0.5 + coefficient * SH_C0) * 255.0)) for coefficient in coeffs]
    return rgb[0], rgb[1], rgb[2], int(round(_clamp01(alpha) * 255.0))


def _decode_modern_sh0(meta: dict[str, Any], pixel: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    codebook = meta["sh0"]["codebook"]
    rgb = [
        int(round(_clamp01(0.5 + float(codebook[int(pixel[channel])]) * SH_C0) * 255.0)) for channel in range(3)
    ]
    return rgb[0], rgb[1], rgb[2], int(pixel[3])


def _evenly_spaced_indices(count: int, sample_count: int) -> list[int]:
    if sample_count >= count:
        return list(range(count))

    indices: list[int] = []
    last_index = -1
    for i in range(sample_count):
        index = math.floor(((i + 0.5) * count) / sample_count)
        index = max(0, min(count - 1, index))
        if index <= last_index:
            index = min(count - 1, last_index + 1)
        indices.append(index)
        last_index = index
    return indices


def _sample_points_from_meta(
    source: BundleAssetSource,
    meta: dict[str, Any],
    meta_relative_path: str,
    sample_count: int,
    point_alpha_floor: int,
) -> list[tuple[float, float, float, int, int, int, int]]:
    legacy_format = meta.get("version") != 2
    if legacy_format:
        count = int(meta["means"]["shape"][0])
    else:
        count = int(meta["count"])
    if count <= 0 or sample_count <= 0:
        return []

    base_dir = Path(meta_relative_path).parent
    means_low = _decode_image_rgba(source.read_bytes(str(base_dir / meta["means"]["files"][0])))
    means_high = _decode_image_rgba(source.read_bytes(str(base_dir / meta["means"]["files"][1])))
    sh0_image = _decode_image_rgba(source.read_bytes(str(base_dir / meta["sh0"]["files"][0])))

    if means_low.size != means_high.size or means_low.size != sh0_image.size:
        raise ValueError(f"preview sidecar requires matching image dimensions for {meta_relative_path}")

    width, height = means_low.size
    if width * height < count:
        raise ValueError(f"decoded image size {width}x{height} does not cover {count} splats for {meta_relative_path}")

    means_low_px = means_low.load()
    means_high_px = means_high.load()
    sh0_px = sh0_image.load()

    points: list[tuple[float, float, float, int, int, int, int]] = []
    for source_index in _evenly_spaced_indices(count, min(count, sample_count)):
        x = source_index % width
        y = source_index // width
        position = _decode_position(
            meta,
            means_low_px[x, y],
            means_high_px[x, y],
            legacy_format=legacy_format,
        )
        color = _decode_legacy_sh0(meta, sh0_px[x, y]) if legacy_format else _decode_modern_sh0(meta, sh0_px[x, y])
        points.append(
            (
                float(position[0]),
                float(position[1]),
                float(position[2]),
                int(color[0]),
                int(color[1]),
                int(color[2]),
                max(point_alpha_floor, int(color[3])),
            )
        )
    return points


def _choose_chunk_sample_counts(chunk_counts: list[int], max_points: int) -> list[int]:
    if not chunk_counts:
        return []
    if max_points <= 0:
        return [0] * len(chunk_counts)

    total = sum(chunk_counts)
    if total <= 0:
        return [0] * len(chunk_counts)

    allocations = [0] * len(chunk_counts)
    fractions: list[tuple[float, int]] = []
    assigned = 0
    for index, count in enumerate(chunk_counts):
        raw = max_points * (count / total)
        whole = min(count, int(math.floor(raw)))
        allocations[index] = whole
        assigned += whole
        fractions.append((raw - whole, index))

    remaining = max_points - assigned
    for _, index in sorted(fractions, reverse=True):
        if remaining <= 0:
            break
        if allocations[index] >= chunk_counts[index]:
            continue
        allocations[index] += 1
        remaining -= 1

    return allocations


def _write_preview_payload(
    points: list[tuple[float, float, float, int, int, int, int]],
    output_dir: Path,
    *,
    source_meta: str,
    source_count: int,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = bytearray(len(points) * 16)
    bounds_min = [math.inf, math.inf, math.inf]
    bounds_max = [-math.inf, -math.inf, -math.inf]

    for output_index, point in enumerate(points):
        for axis in range(3):
            bounds_min[axis] = min(bounds_min[axis], point[axis])
            bounds_max[axis] = max(bounds_max[axis], point[axis])

        struct.pack_into(
            "<fffBBBB",
            payload,
            output_index * 16,
            point[0],
            point[1],
            point[2],
            point[3],
            point[4],
            point[5],
            point[6],
        )

    preview_asset_name = "preview-points.bin"
    preview_meta_name = "preview-meta.json"
    (output_dir / preview_asset_name).write_bytes(payload)

    preview_meta = {
        "version": 1,
        "encoding": "position-f32-color-rgba8",
        "stride": 16,
        "count": len(points),
        "sourceCount": source_count,
        "sampleMode": "spatial-step",
        "asset": preview_asset_name,
        "bounds": {
            "min": bounds_min,
            "max": bounds_max,
        },
        "sourceMeta": source_meta,
    }
    (output_dir / preview_meta_name).write_text(json.dumps(preview_meta, indent=2), encoding="utf-8")

    return {
        "meta": preview_meta_name,
        "asset": preview_asset_name,
        "count": len(points),
        "sourceCount": source_count,
        "bounds": preview_meta["bounds"],
        "outputDir": str(output_dir),
    }


def generate_preview_sidecar(
    bundle_root: str | Path,
    output_dir: str | Path,
    *,
    max_points: int = DEFAULT_PREVIEW_MAX_POINTS,
    min_alpha: float = DEFAULT_PREVIEW_MIN_ALPHA,
) -> dict[str, Any]:
    source = BundleAssetSource(bundle_root)
    meta = source.read_json(source.meta_relative_path)
    point_alpha_floor = int(round(_clamp01(min_alpha) * 255.0))
    output_dir_path = Path(output_dir)

    if isinstance(meta.get("filenames"), list):
        chunk_files = [entry for entry in meta["filenames"] if isinstance(entry, str)]
        if not chunk_files:
            raise ValueError("lod-meta.json preview generation requires chunk filenames")
        chunk_metas = [(relative_path, source.read_json(relative_path)) for relative_path in chunk_files]
        chunk_counts = [int(chunk_meta["count"]) for _, chunk_meta in chunk_metas]
        sample_counts = _choose_chunk_sample_counts(chunk_counts, max(1, int(max_points)))
        points: list[tuple[float, float, float, int, int, int, int]] = []
        for (relative_path, chunk_meta), sample_count in zip(chunk_metas, sample_counts, strict=False):
            if sample_count <= 0:
                continue
            points.extend(_sample_points_from_meta(source, chunk_meta, relative_path, sample_count, point_alpha_floor))
        return {
            **_write_preview_payload(
                points,
                output_dir_path,
                source_meta=source.resolve_asset_reference(source.meta_relative_path),
                source_count=sum(chunk_counts),
            ),
            "bundleRoot": str(bundle_root),
        }

    points = _sample_points_from_meta(
        source,
        meta,
        source.meta_relative_path,
        min(max(1, int(max_points)), int(meta["means"]["shape"][0] if meta.get("version") != 2 else meta["count"])),
        point_alpha_floor,
    )
    source_count = int(meta["means"]["shape"][0]) if meta.get("version") != 2 else int(meta["count"])
    return {
        **_write_preview_payload(
            points,
            output_dir_path,
            source_meta=source.resolve_asset_reference(source.meta_relative_path),
            source_count=source_count,
        ),
        "bundleRoot": str(bundle_root),
    }
