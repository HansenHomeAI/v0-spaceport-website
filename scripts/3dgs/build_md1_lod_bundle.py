#!/usr/bin/env python3
"""Build an MD1 V18 SuperSplat LOD input bundle from the full promoted PLY."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np


REQUIRED_FLOAT_FIELDS = {
    "x",
    "y",
    "z",
    "f_dc_0",
    "f_dc_1",
    "f_dc_2",
    "opacity",
    "scale_0",
    "scale_1",
    "scale_2",
    "rot_0",
    "rot_1",
    "rot_2",
    "rot_3",
}


@dataclass(frozen=True)
class PlyHeader:
    vertex_count: int
    properties: tuple[str, ...]
    data_offset: int
    row_size: int


@dataclass(frozen=True)
class LeafPartition:
    indices: np.ndarray
    bound: dict[str, list[float]]
    metadata: dict


def parse_int_list(value: str) -> list[int]:
    parsed = [int(part.strip()) for part in value.split(",") if part.strip()]
    if not parsed or any(part <= 0 for part in parsed):
        raise argparse.ArgumentTypeError("expected positive comma-separated integers")
    return parsed


def parse_ply_header(path: Path) -> PlyHeader:
    with path.open("rb") as handle:
        header_bytes = bytearray()
        while True:
            line = handle.readline()
            if not line:
                raise ValueError("PLY header ended before end_header")
            header_bytes.extend(line)
            if line == b"end_header\n":
                break

    lines = header_bytes.decode("ascii").splitlines()
    if not lines or lines[0] != "ply":
        raise ValueError("source is not a PLY file")
    if "format binary_little_endian 1.0" not in lines:
        raise ValueError("only binary_little_endian PLY is supported")

    vertex_count: int | None = None
    properties: list[str] = []
    in_vertex = False
    for line in lines:
        if line.startswith("element "):
            parts = line.split()
            in_vertex = parts[1] == "vertex"
            if in_vertex:
                vertex_count = int(parts[2])
            continue
        if in_vertex and line.startswith("property "):
            parts = line.split()
            if len(parts) != 3 or parts[1] != "float":
                raise ValueError(f"unsupported vertex property line: {line}")
            properties.append(parts[2])

    if vertex_count is None:
        raise ValueError("PLY is missing element vertex")
    missing = sorted(REQUIRED_FLOAT_FIELDS.difference(properties))
    if missing:
        raise ValueError(f"PLY is missing required Gaussian fields: {missing}")

    return PlyHeader(
        vertex_count=vertex_count,
        properties=tuple(properties),
        data_offset=len(header_bytes),
        row_size=len(properties) * 4,
    )


def make_ply_header(properties: Iterable[str], vertex_count: int) -> bytes:
    lines = ["ply", "format binary_little_endian 1.0", f"element vertex {vertex_count}"]
    lines.extend(f"property float {name}" for name in properties)
    lines.append("end_header")
    return ("\n".join(lines) + "\n").encode("ascii")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def node_bounds(points: np.ndarray) -> dict[str, list[float]]:
    if points.size == 0:
        return {"min": [0.0, 0.0, 0.0], "max": [0.0, 0.0, 0.0]}
    mins = np.min(points[:, :3], axis=0)
    maxs = np.max(points[:, :3], axis=0)
    return {
        "min": [float(mins[0]), float(mins[1]), float(mins[2])],
        "max": [float(maxs[0]), float(maxs[1]), float(maxs[2])],
    }


def combine_bounds(nodes: list[dict]) -> dict[str, list[float]]:
    valid = [node["bound"] for node in nodes if node.get("bound")]
    if not valid:
        return {"min": [0.0, 0.0, 0.0], "max": [0.0, 0.0, 0.0]}
    return {
        "min": [min(bound["min"][axis] for bound in valid) for axis in range(3)],
        "max": [max(bound["max"][axis] for bound in valid) for axis in range(3)],
    }


def build_tree(grid_x: int, grid_y: int, leaf_nodes: list[dict]) -> dict:
    rows = []
    for y in range(grid_y):
        children = [leaf_nodes[y * grid_x + x] for x in range(grid_x)]
        rows.append({"bound": combine_bounds(children), "children": children})
    return {"bound": combine_bounds(rows), "children": rows}


def build_grid_partitions(coords: np.ndarray, grid_x: int, grid_y: int) -> tuple[list[LeafPartition], dict, dict]:
    global_min = np.min(coords, axis=0)
    global_max = np.max(coords, axis=0)
    xy_span = np.maximum(global_max[:2] - global_min[:2], 1e-9)
    ix = np.floor(((coords[:, 0] - global_min[0]) / xy_span[0]) * grid_x).astype(np.int16)
    iy = np.floor(((coords[:, 1] - global_min[1]) / xy_span[1]) * grid_y).astype(np.int16)
    ix = np.clip(ix, 0, grid_x - 1)
    iy = np.clip(iy, 0, grid_y - 1)
    node_ids = iy * grid_x + ix
    node_count = grid_x * grid_y

    partitions: list[LeafPartition] = []
    leaf_nodes = []
    for node_id in range(node_count):
        indices = np.flatnonzero(node_ids == node_id)
        bound = node_bounds(coords[indices] if indices.size else np.empty((0, 3)))
        metadata = {
            "nodeId": node_id,
            "grid": [int(node_id % grid_x), int(node_id // grid_x)],
            "sourceSplatCount": int(indices.size),
        }
        partitions.append(LeafPartition(indices=indices, bound=bound, metadata=metadata))
        leaf_nodes.append({"bound": bound, "lods": {}, "metadata": metadata})

    return (
        partitions,
        build_tree(grid_x, grid_y, leaf_nodes),
        {"mode": "grid", "x": grid_x, "y": grid_y, "leafNodes": node_count},
    )


def split_indices_balanced(coords: np.ndarray, indices: np.ndarray, leaf_count: int, depth: int) -> tuple[dict, list[LeafPartition]]:
    if leaf_count <= 1 or indices.size <= 1:
        sorted_indices = np.sort(indices, kind="mergesort")
        bound = node_bounds(coords[sorted_indices] if sorted_indices.size else np.empty((0, 3)))
        metadata = {
            "sourceSplatCount": int(sorted_indices.size),
            "depth": depth,
        }
        return {"bound": bound, "lods": {}, "metadata": metadata}, [
            LeafPartition(indices=sorted_indices, bound=bound, metadata=metadata)
        ]

    left_leaf_count = leaf_count // 2
    right_leaf_count = leaf_count - left_leaf_count
    mins = np.min(coords[indices], axis=0)
    maxs = np.max(coords[indices], axis=0)
    axis = int(np.argmax(maxs - mins))
    split_count = int(round(indices.size * (left_leaf_count / leaf_count)))
    split_count = max(1, min(indices.size - 1, split_count))
    values = np.asarray(coords[indices, axis])
    order = np.argpartition(values, split_count)
    left_indices = indices[order[:split_count]].copy()
    right_indices = indices[order[split_count:]].copy()

    left_node, left_partitions = split_indices_balanced(coords, left_indices, left_leaf_count, depth + 1)
    right_node, right_partitions = split_indices_balanced(coords, right_indices, right_leaf_count, depth + 1)
    node = {
        "bound": combine_bounds([left_node, right_node]),
        "children": [left_node, right_node],
        "metadata": {
            "splitAxis": axis,
            "splitCount": int(split_count),
            "depth": depth,
        },
    }
    return node, left_partitions + right_partitions


def build_balanced_kd_partitions(coords: np.ndarray, leaf_count: int) -> tuple[list[LeafPartition], dict, dict]:
    root_indices = np.arange(coords.shape[0], dtype=np.int64)
    tree, partitions = split_indices_balanced(coords, root_indices, leaf_count, 0)
    leaf_nodes: list[dict] = []
    for node_id, partition in enumerate(partitions):
        metadata = {
            **partition.metadata,
            "nodeId": node_id,
            "sourceSplatCount": int(partition.indices.size),
        }
        partition.metadata.update(metadata)
        leaf_nodes.append({"bound": partition.bound, "lods": {}, "metadata": metadata})

    # Rebuild the tree leaves with stable node ids while preserving the split shape.
    leaf_iter = iter(leaf_nodes)

    def replace_leaves(node: dict) -> dict:
        if "lods" in node:
            return next(leaf_iter)
        children = [replace_leaves(child) for child in node.get("children", [])]
        return {"bound": combine_bounds(children), "children": children, "metadata": node.get("metadata", {})}

    return (
        partitions,
        replace_leaves(tree),
        {"mode": "balanced-kd", "leafNodes": len(partitions), "targetLeafNodes": leaf_count},
    )


def trim_selected_to_square(selected_by_node: list[tuple[int, np.ndarray]], min_sogs_splats: int) -> tuple[list[tuple[int, np.ndarray]], int, int]:
    total_count = int(sum(indices.size for _, indices in selected_by_node))
    square_count = math.isqrt(total_count) ** 2
    if square_count < min_sogs_splats:
        return [], total_count, total_count

    remaining = square_count
    trimmed: list[tuple[int, np.ndarray]] = []
    for node_id, indices in selected_by_node:
        if remaining <= 0:
            trimmed.append((node_id, indices[:0]))
            continue
        take = min(int(indices.size), remaining)
        trimmed.append((node_id, indices[:take]))
        remaining -= take
    return trimmed, square_count, total_count - square_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ply", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--lod-strides", default="1,4,16,64", type=parse_int_list)
    parser.add_argument("--partition-mode", default="balanced-kd", choices=["balanced-kd", "grid"])
    parser.add_argument("--leaf-count", default=64, type=int)
    parser.add_argument("--grid-x", default=4, type=int)
    parser.add_argument("--grid-y", default=4, type=int)
    parser.add_argument("--groups-per-lod", default=32, type=int)
    parser.add_argument("--min-sogs-splats", default=16, type=int)
    parser.add_argument("--source-artifact-uri", default="")
    parser.add_argument("--source-ply-uri", default="")
    parser.add_argument("--sfm-url", default="")
    parser.add_argument("--bundle-s3-prefix", default="")
    parser.add_argument("--write-sha256", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.grid_x <= 0 or args.grid_y <= 0 or args.groups_per_lod <= 0 or args.leaf_count <= 0:
        raise SystemExit("partition and group counts must be positive")

    source_ply = args.source_ply.resolve()
    out_dir = args.output_dir.resolve()
    chunks_dir = out_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    header = parse_ply_header(source_ply)
    expected_size = header.data_offset + header.vertex_count * header.row_size
    actual_size = source_ply.stat().st_size
    if actual_size < expected_size:
        raise ValueError(f"PLY is truncated: expected at least {expected_size} bytes, found {actual_size}")

    vertices = np.memmap(
        source_ply,
        dtype="<f4",
        mode="r",
        offset=header.data_offset,
        shape=(header.vertex_count, len(header.properties)),
    )

    coords = np.asarray(vertices[:, :3])
    global_min = np.min(coords, axis=0)
    global_max = np.max(coords, axis=0)
    if args.partition_mode == "grid":
        partitions, tree, partition_manifest = build_grid_partitions(coords, args.grid_x, args.grid_y)
    else:
        partitions, tree, partition_manifest = build_balanced_kd_partitions(coords, args.leaf_count)
    node_count = len(partitions)
    node_indices = [partition.indices for partition in partitions]
    node_source_counts = [int(partition.indices.size) for partition in partitions]

    filenames: list[str] = []
    chunk_manifest: list[dict] = []
    lod_entries_by_node: list[dict[str, dict]] = [dict() for _ in range(node_count)]

    for lod_level, stride in enumerate(args.lod_strides):
        group_size = max(1, math.ceil(node_count / args.groups_per_lod))
        for group_id in range(args.groups_per_lod):
            start = group_id * group_size
            end = min(node_count, start + group_size)
            if start >= end:
                continue
            group_nodes = list(range(start, end))
            selected_by_node = [(node_id, node_indices[node_id][::stride]) for node_id in group_nodes]
            selected_by_node, total_count, square_trim_dropped = trim_selected_to_square(
                selected_by_node,
                args.min_sogs_splats,
            )
            if total_count == 0:
                continue

            stem = f"lod{lod_level}_g{group_id:02d}"
            ply_path = chunks_dir / f"{stem}.ply"
            file_index = len(filenames)
            filenames.append(f"compressed_{stem}/meta.json")

            with ply_path.open("wb") as handle:
                handle.write(make_ply_header(header.properties, total_count))
                offset = 0
                for node_id, indices in selected_by_node:
                    count = int(indices.size)
                    if count:
                        handle.write(np.asarray(vertices[indices]).astype("<f4", copy=False).tobytes(order="C"))
                        lod_entries_by_node[node_id][str(lod_level)] = {
                            "file": file_index,
                            "offset": offset,
                            "count": count,
                        }
                        offset += count

            chunk = {
                "file": ply_path.name,
                "compressedManifest": filenames[file_index],
                "lodLevel": lod_level,
                "stride": stride,
                "group": group_id,
                "nodeIds": group_nodes,
                "splatCount": total_count,
                "sourceSplatCountBeforeSquareTrim": total_count + square_trim_dropped,
                "squareTrimDropped": square_trim_dropped,
                "byteSize": ply_path.stat().st_size,
            }
            if args.write_sha256:
                chunk["sha256"] = sha256_file(ply_path)
            chunk_manifest.append(chunk)

    leaf_entries = iter(lod_entries_by_node)

    def attach_lods(node: dict) -> dict:
        if "lods" in node:
            return {**node, "lods": next(leaf_entries)}
        return {
            **node,
            "children": [attach_lods(child) for child in node.get("children", [])],
        }

    lod_meta = {
        "lodLevels": len(args.lod_strides),
        "environment": None,
        "filenames": filenames,
        "tree": attach_lods(tree),
    }

    production_manifest = {
        "schema": "spaceport/md1-production-lod/v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceArtifactUri": args.source_artifact_uri,
        "sourcePlyUri": args.source_ply_uri,
        "sfmUrl": args.sfm_url,
        "bundleS3Prefix": args.bundle_s3_prefix,
        "sourceVertexCount": header.vertex_count,
        "sourceByteSize": actual_size,
        "sourceSha256": sha256_file(source_ply) if args.write_sha256 else None,
        "rowSize": header.row_size,
        "properties": list(header.properties),
        "bounds": {
            "min": [float(global_min[0]), float(global_min[1]), float(global_min[2])],
            "max": [float(global_max[0]), float(global_max[1]), float(global_max[2])],
        },
        "partition": partition_manifest,
        "lodStrides": args.lod_strides,
        "groupsPerLod": args.groups_per_lod,
        "minSogsSplats": args.min_sogs_splats,
        "chunkCount": len(chunk_manifest),
        "chunks": chunk_manifest,
        "nodeSourceCounts": node_source_counts,
        "squareTrimDroppedByLod": {
            str(level): int(
                sum(chunk["squareTrimDropped"] for chunk in chunk_manifest if chunk["lodLevel"] == level)
            )
            for level in range(len(args.lod_strides))
        },
        "lodSplatCounts": {
            str(level): int(sum(entry[str(level)]["count"] for entry in lod_entries_by_node if str(level) in entry))
            for level in range(len(args.lod_strides))
        },
    }

    (out_dir / "lod-meta.json").write_text(json.dumps(lod_meta, separators=(",", ":")), encoding="utf-8")
    (out_dir / "production_manifest.json").write_text(
        json.dumps(production_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "sourceVertexCount": header.vertex_count,
                "chunkCount": len(chunk_manifest),
                "outputDir": str(out_dir),
                "lodSplatCounts": production_manifest["lodSplatCounts"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
