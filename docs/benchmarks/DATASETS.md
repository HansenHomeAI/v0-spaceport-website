# SOTA Benchmark Datasets (Phase 1)

This registry defines the canonical scene list for the FULL SOTA benchmark plan and the minimum metadata each scene must carry in its manifest.

## Dataset Coverage

| dataset | scene | source_url | license_url | expected_image_dirs |
|---|---|---|---|---|
| mipnerf360 | bicycle | `TBD_SOURCE_URL_MIPNERF360_BICYCLE` | `TBD_LICENSE_URL_MIPNERF360` | `images_4` |
| mipnerf360 | garden | `TBD_SOURCE_URL_MIPNERF360_GARDEN` | `TBD_LICENSE_URL_MIPNERF360` | `images_4` |
| mipnerf360 | stump | `TBD_SOURCE_URL_MIPNERF360_STUMP` | `TBD_LICENSE_URL_MIPNERF360` | `images_4` |
| mipnerf360 | bonsai | `TBD_SOURCE_URL_MIPNERF360_BONSAI` | `TBD_LICENSE_URL_MIPNERF360` | `images_2` |
| mipnerf360 | counter | `TBD_SOURCE_URL_MIPNERF360_COUNTER` | `TBD_LICENSE_URL_MIPNERF360` | `images_2` |
| mipnerf360 | kitchen | `TBD_SOURCE_URL_MIPNERF360_KITCHEN` | `TBD_LICENSE_URL_MIPNERF360` | `images_2` |
| mipnerf360 | room | `TBD_SOURCE_URL_MIPNERF360_ROOM` | `TBD_LICENSE_URL_MIPNERF360` | `images_2` |
| tanksandtemples | train | `TBD_SOURCE_URL_TNT_TRAIN` | `TBD_LICENSE_URL_TNT` | `images_2, images_4` |
| tanksandtemples | truck | `TBD_SOURCE_URL_TNT_TRUCK` | `TBD_LICENSE_URL_TNT` | `images_2, images_4` |
| deepblending | playroom | `TBD_SOURCE_URL_DB_PLAYROOM` | `TBD_LICENSE_URL_DEEPBLENDING` | `images_2, images_4` |
| deepblending | drjohnson | `TBD_SOURCE_URL_DB_DRJOHNSON` | `TBD_LICENSE_URL_DEEPBLENDING` | `images_2, images_4` |
| zipnerf | alameda | `TBD_SOURCE_URL_ZIPNERF_ALAMEDA` | `TBD_LICENSE_URL_ZIPNERF` | `images_4` |
| zipnerf | berlin | `TBD_SOURCE_URL_ZIPNERF_BERLIN` | `TBD_LICENSE_URL_ZIPNERF` | `images_4` |
| zipnerf | london | `TBD_SOURCE_URL_ZIPNERF_LONDON` | `TBD_LICENSE_URL_ZIPNERF` | `images_4` |
| zipnerf | nyc | `TBD_SOURCE_URL_ZIPNERF_NYC` | `TBD_LICENSE_URL_ZIPNERF` | `images_4` |

## Reproducibility Requirements

Each emitted scene manifest must include:

- `source_url`, `license_url`, `download_timestamp`
- `expected_image_dirs`
- `reproducibility.scene_sha256` over normalized scene files
- `reproducibility.total_files` and `reproducibility.total_bytes`
- per-file SHA256 records
- per-image-dir counts and resolution histogram

## Local Ingestion Stub

Use the Phase 1 local CLI to generate per-scene manifests without AWS credentials:

```bash
python3 scripts/bench/ingest_dataset.py \
  --dataset mipnerf360 \
  --scene garden \
  --source-url https://example.com/garden.zip \
  --license-url https://example.com/license \
  --expected-image-dirs images_4 \
  --output-dir benchmarks/sota_local
```

Outputs:

- normalized scene tree under `<output-dir>/normalized/<dataset>/<scene>/`
- manifest JSON under `<output-dir>/manifests/<dataset>/<scene>.manifest.json`
