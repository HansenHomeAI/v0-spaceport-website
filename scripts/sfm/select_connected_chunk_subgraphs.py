#!/usr/bin/env python3
"""Rank connected chunk subgraphs from a chunk planner manifest."""

from __future__ import annotations

import argparse
import itertools
import json
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Sequence


AWS_CLI = shutil.which("aws") or (
    "/opt/homebrew/bin/aws" if Path("/opt/homebrew/bin/aws").exists() else "aws"
)
IMAGE_LIST_KEYS = ("image_names", "images", "file_names", "files", "entries", "items")
IMAGE_VALUE_KEYS = ("file_name", "image_name", "name", "path", "uri", "key", "basename")


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def parse_reference(value: str) -> urllib.parse.ParseResult:
    return urllib.parse.urlparse(value)


def resolve_local_path(value: str) -> Path:
    parsed = parse_reference(value)
    if parsed.scheme == "file":
        return Path(urllib.parse.unquote(parsed.path)).expanduser().resolve()
    if parsed.scheme:
        raise ValueError(f"Expected a local path or file:// URI, got {value}")
    return Path(value).expanduser().resolve()


def materialize_input(source: str, workspace: Path, *, default_name: str) -> Path:
    parsed = parse_reference(source)
    if parsed.scheme in ("", "file"):
        return resolve_local_path(source)

    file_name = Path(urllib.parse.unquote(parsed.path)).name or default_name
    local_path = workspace / file_name
    if parsed.scheme == "s3":
        run_command([AWS_CLI, "s3", "cp", source, str(local_path)])
        return local_path
    if parsed.scheme in ("http", "https"):
        with urllib.request.urlopen(source) as response, open(local_path, "wb") as output_handle:
            shutil.copyfileobj(response, output_handle)
        return local_path
    raise ValueError(f"Unsupported input URI scheme for {source}")


def publish_output(local_path: Path, output: str) -> Path | str:
    parsed = parse_reference(output)
    if parsed.scheme in ("", "file"):
        destination = resolve_local_path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if local_path.resolve() != destination:
            shutil.copy2(local_path, destination)
        return destination
    if parsed.scheme == "s3":
        run_command([AWS_CLI, "s3", "cp", str(local_path), output])
        return output
    raise ValueError(f"Unsupported output URI scheme for {output}")


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def basename_from_reference(value: str) -> str:
    parsed = parse_reference(value)
    candidate = parsed.path if parsed.scheme else value
    return Path(urllib.parse.unquote(candidate)).name


def extract_image_basename(value: Any) -> str | None:
    if isinstance(value, str):
        basename = basename_from_reference(value)
        return basename or None
    if isinstance(value, dict):
        for key in IMAGE_VALUE_KEYS:
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                basename = basename_from_reference(candidate)
                if basename:
                    return basename
    return None


def resolve_manifest_chunks(manifest: Any) -> list[dict[str, Any]]:
    if isinstance(manifest, dict):
        chunks = manifest.get("chunks")
        if isinstance(chunks, list):
            return chunks
        footprint_manifest = manifest.get("footprint_graph_manifest")
        if isinstance(footprint_manifest, dict) and isinstance(footprint_manifest.get("chunks"), list):
            return footprint_manifest["chunks"]
    raise ValueError("Manifest must contain a top-level chunks list or footprint_graph_manifest.chunks")


def extract_chunk_image_basenames(chunk: dict[str, Any]) -> list[str]:
    entries = None
    for key in IMAGE_LIST_KEYS:
        candidate = chunk.get(key)
        if isinstance(candidate, list):
            entries = candidate
            if key == "image_names":
                break
    if not isinstance(entries, list):
        raise ValueError(f"Chunk {chunk.get('index')} does not contain a list-like image collection")
    basenames: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        basename = extract_image_basename(entry)
        if not basename:
            raise ValueError(
                f"Could not resolve an image basename from chunk {chunk.get('index')} entry: {entry!r}"
            )
        if basename in seen:
            continue
        basenames.append(basename)
        seen.add(basename)
    return basenames


def build_chunk_records(manifest: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for chunk in resolve_manifest_chunks(manifest):
        index = int(chunk["index"])
        image_names = extract_chunk_image_basenames(chunk)
        image_name_set = set(image_names)
        overlap_entries = chunk.get("overlap_names", [])
        overlap_names = []
        overlap_name_set: set[str] = set()
        if isinstance(overlap_entries, list):
            for entry in overlap_entries:
                basename = extract_image_basename(entry)
                if basename and basename not in overlap_name_set:
                    overlap_names.append(basename)
                    overlap_name_set.add(basename)
        records.append(
            {
                "index": index,
                "image_names": image_names,
                "image_name_set": image_name_set,
                "overlap_name_set": overlap_name_set,
                "image_count": len(image_names),
                "predicted_pair_count": int(chunk.get("predicted_pair_count", 0)),
            }
        )
    return sorted(records, key=lambda record: record["index"])


def build_shared_image_edges(chunk_records: Sequence[dict[str, Any]]) -> dict[tuple[int, int], int]:
    edges: dict[tuple[int, int], int] = {}
    for left_record, right_record in itertools.combinations(chunk_records, 2):
        shared_images = len(left_record["image_name_set"].intersection(right_record["image_name_set"]))
        if shared_images <= 0:
            continue
        edges[(left_record["index"], right_record["index"])] = shared_images
    return edges


def is_connected_subset(chunk_indexes: Sequence[int], shared_edges: dict[tuple[int, int], int]) -> bool:
    if len(chunk_indexes) <= 1:
        return True
    remaining = set(chunk_indexes)
    frontier = [remaining.pop()]
    seen = set(frontier)
    while frontier:
        current = frontier.pop()
        for candidate in list(remaining):
            pair_key = (min(current, candidate), max(current, candidate))
            if shared_edges.get(pair_key, 0) <= 0:
                continue
            remaining.remove(candidate)
            frontier.append(candidate)
            seen.add(candidate)
    return len(seen) == len(chunk_indexes)


def score_candidate(
    chunk_indexes: Sequence[int],
    *,
    record_by_index: dict[int, dict[str, Any]],
    shared_edges: dict[tuple[int, int], int],
    target_images: int,
) -> dict[str, Any]:
    sorted_indexes = sorted(chunk_indexes)
    edge_details = []
    total_shared_images = 0
    min_shared_images: int | None = None
    max_shared_images = 0
    total_predicted_pairs = 0
    image_union: set[str] = set()
    for chunk_index in sorted_indexes:
        record = record_by_index[chunk_index]
        image_union.update(record["image_name_set"])
        total_predicted_pairs += int(record["predicted_pair_count"])
    for left_index, right_index in itertools.combinations(sorted_indexes, 2):
        shared_images = shared_edges.get((left_index, right_index), 0)
        if shared_images <= 0:
            continue
        edge_details.append(
            {
                "left_chunk_index": left_index,
                "right_chunk_index": right_index,
                "shared_image_count": shared_images,
            }
        )
        total_shared_images += shared_images
        max_shared_images = max(max_shared_images, shared_images)
        min_shared_images = (
            shared_images if min_shared_images is None else min(min_shared_images, shared_images)
        )
    unique_image_count = len(image_union)
    return {
        "chunk_indexes": sorted_indexes,
        "chunk_count": len(sorted_indexes),
        "unique_image_count": unique_image_count,
        "target_image_delta": abs(unique_image_count - target_images),
        "total_shared_images": total_shared_images,
        "min_shared_images": min_shared_images or 0,
        "max_shared_images": max_shared_images,
        "edge_count": len(edge_details),
        "shared_image_edges": edge_details,
        "total_predicted_pairs": total_predicted_pairs,
    }


def rank_connected_candidates(
    manifest: Any,
    *,
    min_size: int,
    max_size: int,
    target_images: int,
) -> list[dict[str, Any]]:
    chunk_records = build_chunk_records(manifest)
    record_by_index = {record["index"]: record for record in chunk_records}
    shared_edges = build_shared_image_edges(chunk_records)
    candidates: list[dict[str, Any]] = []
    chunk_indexes = [record["index"] for record in chunk_records]
    for size in range(min_size, max_size + 1):
        for candidate_indexes in itertools.combinations(chunk_indexes, size):
            if not is_connected_subset(candidate_indexes, shared_edges):
                continue
            candidates.append(
                score_candidate(
                    candidate_indexes,
                    record_by_index=record_by_index,
                    shared_edges=shared_edges,
                    target_images=target_images,
                )
            )
    candidates.sort(
        key=lambda candidate: (
            -candidate["total_shared_images"],
            -candidate["min_shared_images"],
            candidate["target_image_delta"],
            candidate["chunk_indexes"],
        )
    )
    return candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Local path or URI to chunk_planner_manifest.json")
    parser.add_argument("--output", default="", help="Optional local path or URI to write ranked candidates JSON")
    parser.add_argument("--min-size", type=int, default=4, help="Minimum connected chunk count to consider")
    parser.add_argument("--max-size", type=int, default=6, help="Maximum connected chunk count to consider")
    parser.add_argument("--target-images", type=int, default=900, help="Preferred unique image count for ranking")
    parser.add_argument("--top-k", type=int, default=10, help="Limit output to the top K ranked candidates")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.min_size < 1:
        raise ValueError("--min-size must be >= 1")
    if args.max_size < args.min_size:
        raise ValueError("--max-size must be >= --min-size")
    if args.top_k < 1:
        raise ValueError("--top-k must be >= 1")

    with tempfile.TemporaryDirectory(prefix="connected_chunk_subgraphs_") as temp_dir:
        workspace = Path(temp_dir)
        manifest_path = materialize_input(args.manifest, workspace, default_name="chunk_planner_manifest.json")
        manifest = load_json(manifest_path)
        ranked_candidates = rank_connected_candidates(
            manifest,
            min_size=args.min_size,
            max_size=args.max_size,
            target_images=args.target_images,
        )
        output_payload = {
            "manifest": args.manifest,
            "min_size": args.min_size,
            "max_size": args.max_size,
            "target_images": args.target_images,
            "candidate_count": len(ranked_candidates),
            "candidates": ranked_candidates[: args.top_k],
        }
        output_text = json.dumps(output_payload, indent=2) + "\n"
        if args.output:
            local_output = workspace / "connected_chunk_subgraphs.json"
            local_output.write_text(output_text, encoding="utf-8")
            publish_output(local_output, args.output)
        print(output_text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
