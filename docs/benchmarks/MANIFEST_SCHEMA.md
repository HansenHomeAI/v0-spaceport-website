# Benchmark Manifest Schema

Phase 1 introduces a machine-readable schema at `docs/benchmarks/manifest.schema.json` and a concrete example at `docs/benchmarks/manifest.example.json`.

## Schema Intent

The schema validates scene-level provenance and reproducibility metadata:

- identity: `dataset`, `scene`
- provenance: `source_url`, `license_url`, `download_timestamp`
- normalization contract: `expected_image_dirs`, local path metadata
- reproducibility: file checksums, aggregate checksum, file/byte counts, image counts, and resolution histograms

## Validation Example

```bash
# Requires a JSON Schema validator such as ajv-cli.
# npm i -g ajv-cli
ajv validate \
  -s docs/benchmarks/manifest.schema.json \
  -d docs/benchmarks/manifest.example.json
```

## Notes

- `source_url` and `license_url` may remain placeholders during early planning.
- `schema_version` is pinned at `1.0.0` for Phase 1 and should be bumped with breaking changes.
