#!/usr/bin/env python3
"""Build a subset ZIP from an image archive using image basenames from a manifest."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Sequence


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
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
        run_command(["aws", "s3", "cp", source, str(local_path)])
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
        run_command(["aws", "s3", "cp", str(local_path), output])
        return output
    raise ValueError(f"Unsupported output URI scheme for {output}")


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_manifest_node(manifest: Any, subset_key: str) -> Any:
    if not subset_key or not subset_key.strip():
        raise ValueError("subset_key must not be empty")

    node = manifest
    traversed_segments: list[str] = []
    for segment in subset_key.split("."):
        if not segment:
            raise ValueError(f"subset_key contains an empty segment: {subset_key}")
        traversed_segments.append(segment)
        if isinstance(node, dict):
            if segment not in node:
                raise KeyError(
                    f"Manifest path {'/'.join(traversed_segments)} was not found while resolving {subset_key}"
                )
            node = node[segment]
            continue
        if isinstance(node, list):
            try:
                index = int(segment)
            except ValueError as exc:
                raise KeyError(
                    f"Manifest path {'/'.join(traversed_segments[:-1])} is a list; segment {segment!r} "
                    f"must be a numeric index"
                ) from exc
            try:
                node = node[index]
            except IndexError as exc:
                raise KeyError(
                    f"Manifest list index {index} is out of range while resolving {subset_key}"
                ) from exc
            continue
        raise KeyError(
            f"Manifest path {'/'.join(traversed_segments[:-1])} does not contain child segment {segment!r}"
        )
    return node


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


def resolve_subset_basenames(manifest: Any, subset_key: str) -> list[str]:
    node = resolve_manifest_node(manifest, subset_key)
    entries: Sequence[Any]
    if isinstance(node, list):
        entries = node
    elif isinstance(node, dict):
        for key in IMAGE_LIST_KEYS:
            candidate = node.get(key)
            if isinstance(candidate, list):
                entries = candidate
                break
        else:
            raise ValueError(
                f"Manifest node at {subset_key} must be a list or contain one of {IMAGE_LIST_KEYS}"
            )
    else:
        raise ValueError(f"Manifest node at {subset_key} must resolve to a list-like image collection")

    basenames: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        basename = extract_image_basename(entry)
        if not basename:
            raise ValueError(f"Could not resolve an image basename from manifest entry: {entry!r}")
        if basename in seen:
            continue
        basenames.append(basename)
        seen.add(basename)

    if not basenames:
        raise ValueError(f"Manifest subset {subset_key} did not contain any image basenames")
    return basenames


def parse_chunk_indexes(value: str) -> list[int]:
    indexes: list[int] = []
    for segment in value.split(","):
        cleaned = segment.strip()
        if not cleaned:
            continue
        try:
            indexes.append(int(cleaned))
        except ValueError as exc:
            raise ValueError(f"Chunk index {cleaned!r} is not an integer") from exc
    if not indexes:
        raise ValueError("chunk_indexes must contain at least one integer index")
    return indexes


def resolve_chunk_basenames(manifest: Any, chunk_indexes: Sequence[int]) -> list[str]:
    chunks = manifest.get("chunks")
    if not isinstance(chunks, list):
        raise ValueError("Manifest must contain a top-level chunks list to resolve chunk indexes")
    chunks_by_index = {}
    for chunk in chunks:
        if not isinstance(chunk, dict) or "index" not in chunk:
            continue
        chunks_by_index[int(chunk["index"])] = chunk

    basenames: list[str] = []
    seen: set[str] = set()
    missing_indexes = [chunk_index for chunk_index in chunk_indexes if chunk_index not in chunks_by_index]
    if missing_indexes:
        raise KeyError(f"Manifest is missing chunk indexes: {missing_indexes}")

    for chunk_index in chunk_indexes:
        chunk = chunks_by_index[chunk_index]
        image_entries = chunk.get("image_names")
        if not isinstance(image_entries, list):
            raise ValueError(f"Manifest chunk {chunk_index} does not contain an image_names list")
        for entry in image_entries:
            basename = extract_image_basename(entry)
            if not basename:
                raise ValueError(
                    f"Could not resolve an image basename from chunk {chunk_index} entry: {entry!r}"
                )
            if basename in seen:
                continue
            basenames.append(basename)
            seen.add(basename)

    if not basenames:
        raise ValueError(f"Manifest chunk indexes {list(chunk_indexes)} did not contain any image basenames")
    return basenames


def build_member_lookup(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    members: dict[str, zipfile.ZipInfo] = {}
    for member in archive.infolist():
        if member.is_dir():
            continue
        basename = Path(member.filename).name
        if not basename or Path(basename).suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if basename in members:
            raise ValueError(f"Input archive contains duplicate image basename: {basename}")
        members[basename] = member
    return members


def create_subset_zip(input_zip: Path, subset_basenames: Sequence[str], output_zip: Path) -> list[str]:
    if not subset_basenames:
        raise ValueError("subset_basenames must not be empty")

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    written_names: list[str] = []
    with zipfile.ZipFile(input_zip, "r") as source_archive:
        members = build_member_lookup(source_archive)
        missing = [basename for basename in subset_basenames if basename not in members]
        if missing:
            raise ValueError(
                "Subset references images missing from archive: " + ", ".join(sorted(set(missing)))
            )
        with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as subset_archive:
            for basename in subset_basenames:
                with source_archive.open(members[basename], "r") as source_handle, subset_archive.open(
                    basename, "w"
                ) as output_handle:
                    shutil.copyfileobj(source_handle, output_handle)
                written_names.append(basename)
    return written_names


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Local path, file:// URI, s3:// URI, or http(s):// URL for the source ZIP")
    parser.add_argument(
        "--manifest-uri",
        required=True,
        help="Local path, file:// URI, s3:// URI, or http(s):// URL for the manifest JSON",
    )
    selection_group = parser.add_mutually_exclusive_group(required=True)
    selection_group.add_argument(
        "--subset-key",
        help="Manifest key or dotted path resolving to the image subset, for example probe_subsets.geometry_mix",
    )
    selection_group.add_argument(
        "--chunk-indexes",
        help="Comma-separated manifest chunk indexes whose image_names should be unioned in order, for example 8,13",
    )
    parser.add_argument("--output", required=True, help="Local path, file:// URI, or s3:// URI for the subset ZIP")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="manifest_subset_zip_") as temp_dir:
        workspace = Path(temp_dir)
        input_zip = materialize_input(args.input, workspace, default_name="input.zip")
        manifest_path = materialize_input(args.manifest_uri, workspace, default_name="manifest.json")
        manifest = load_json(manifest_path)
        if args.subset_key:
            selection_descriptor = {"subset_key": args.subset_key}
            subset_basenames = resolve_subset_basenames(manifest, args.subset_key)
        else:
            chunk_indexes = parse_chunk_indexes(args.chunk_indexes)
            selection_descriptor = {"chunk_indexes": chunk_indexes}
            subset_basenames = resolve_chunk_basenames(manifest, chunk_indexes)
        local_output = workspace / "subset.zip"
        written_names = create_subset_zip(input_zip, subset_basenames, local_output)
        published_output = publish_output(local_output, args.output)
        summary = {
            "input": args.input,
            "manifest_uri": args.manifest_uri,
            "requested_image_count": len(subset_basenames),
            "selected_image_count": len(written_names),
            "first_image": written_names[0] if written_names else "",
            "last_image": written_names[-1] if written_names else "",
            "output": str(published_output),
        }
        summary.update(selection_descriptor)
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
