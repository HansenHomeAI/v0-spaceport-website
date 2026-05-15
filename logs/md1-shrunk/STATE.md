# MD1-Shrunk E2E State

updated: 2026-05-15T11:23:10-0600
branch: agent-113647-md1-baseline-e2e
repo: HansenHomeAI/v0-spaceport-website

## Goal

Run a bounded MD1-Shrunk proof: spatially downsample MD1 to the largest
Montana training dataset scale, then run SfM, Montana-profile 3DGS with
skybox, compression, artifact handoff, and visual gates.

## Hard Scale Facts

- Meadow/Incognito was the largest Montana training dataset:
  - image files under COLMAP handoff: `1456`
  - registered COLMAP images: `1452`
  - points3D: `940147`
  - SfM mode: `spatial_heading_chunked`
  - chunk count: `8`
  - SfM processing time: `26587.87s`
  - source: `s3://spaceport-ml-processing-staging/manual-validations/meadowfullpriorfixv2-nospace-20260410-084326/colmap`
- Brass Lantern:
  - image files: `1288`
  - registered images: `1285`
  - points3D: `959217`
  - SfM mode: `spatial_heading_chunked`
- Lightfell/Horsetail:
  - image files: `1375`
  - registered images: `1360`
  - points3D: `1025962`
  - SfM mode: `spatial_sequential_only`
- MD1 validated reference:
  - image files: `2157`
  - registered images: `2157`
  - points3D: `1633948`
  - SfM mode: `footprint_graph_chunked`
  - source: `s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap`

## MD1-Shrunk Dataset

- Target image count: `1456` to match Meadow/Incognito image-file scale.
- Selection strategy: densest COLMAP camera-center XY neighborhood from the
  validated MD1 reference.
- Source images:
  - `s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap/images/`
- Selection manifest:
  - local: `logs/md1-shrunk/md1-shrunk-20260515T1641Z-selection.json`
  - S3 sidecar target: `s3://spaceport-uploads/md1-shrunk-20260515T1641Z-1456-images.selection.json`
- Output ZIP target:
  - `s3://spaceport-uploads/md1-shrunk-20260515T1641Z-1456-images.zip`
- Dry-run selection result:
  - selected_count: `1456`
  - unique selected names: `1456`
  - seed: `DJI_02567.JPG`
  - source registered images: `2157`
  - max XY radius: `10.832138295969603`
  - mean XY radius: `7.031740641316656`

## Current Local / AWS State Before Launch

- Branch/head verified:
  - `agent-113647-md1-baseline-e2e`
  - `dd697e9a9b7ce3fd0e4b201aca447e73dcbd33f6`
- GitHub workflows:
  - exact-head `CDK Deploy` run `25922608744` succeeded for `dd697e9a9b7ce3fd0e4b201aca447e73dcbd33f6`.
- AWS identity:
  - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Running Step Functions executions:
  - none under `SpaceportMLPipeline-staging`.
- InProgress SageMaker processing jobs:
  - none.
- InProgress SageMaker training jobs:
  - external/not owned by this run: `md1-worst447-ds1000-r29-1778860601`; left untouched.

## Implementation Added

- New streaming subset builder:
  - `scripts/sfm/prepare_colmap_spatial_subset_zip.py`
  - It reads COLMAP `sparse/0/images.txt`, selects the spatial neighborhood,
    and streams selected S3 image objects into a ZIP uploaded to S3 without
    staging the full dataset locally.
- New unit tests:
  - `tests/unit/test_colmap_spatial_subset_zip.py`
- Added payload persistence support to:
  - `scripts/sfm/run_sfm_benchmark.py --payload-json-output ...`

## Validation So Far

- `python3 -m py_compile scripts/sfm/prepare_colmap_spatial_subset_zip.py`
- `python3 -m py_compile scripts/sfm/run_sfm_benchmark.py scripts/sfm/prepare_colmap_spatial_subset_zip.py`
- `python3 -m unittest tests.unit.test_colmap_spatial_subset_zip tests.unit.test_spatial_heading_benchmark_subset`

## Data Prep Completed

- Streaming ZIP command:
  - `python3 scripts/sfm/prepare_colmap_spatial_subset_zip.py --source-colmap-uri s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap --output-zip-uri s3://spaceport-uploads/md1-shrunk-20260515T1641Z-1456-images.zip --target-count 1456 --manifest-output logs/md1-shrunk/md1-shrunk-20260515T1641Z-selection.json --manifest-s3-uri s3://spaceport-uploads/md1-shrunk-20260515T1641Z-1456-images.selection.json --write-zip`
- Progress log:
  - `logs/md1-shrunk/md1-shrunk-20260515T1641Z-zip-progress.log`
- Summary log:
  - `logs/md1-shrunk/md1-shrunk-20260515T1641Z-zip-summary.txt`
- Completed progress:
  - `zipped 1456/1456 DJI_0999.JPG (4072309 bytes)`.
- S3 object verification:
  - command: `aws s3api head-object --bucket spaceport-uploads --key md1-shrunk-20260515T1641Z-1456-images.zip --region us-west-2 --output json`
  - `ContentLength=6063352899`
  - `ETag="f030d15ff0c71b3acdf78ab0ef6a2a4e-723"`
  - `ServerSideEncryption=AES256`
- S3 selection sidecar verification:
  - command: `aws s3api head-object --bucket spaceport-uploads --key md1-shrunk-20260515T1641Z-1456-images.selection.json --region us-west-2 --output json`
  - `ContentLength=31451`
  - `ETag="175c4827a787ca0206dd1470f9a39d44"`

## Launch Plan

1. Launch exactly one MD1-Shrunk SfM processing job with chunked SfM settings
   matching the largest Montana path:
   - `COLMAP_ENABLE_SPATIAL_CHUNKING=1`
   - `COLMAP_CHUNK_PLANNER=legacy_spatial_heading`
   - `COLMAP_MATCH_PROFILE=P1`
   - source ZIP: `s3://spaceport-uploads/md1-shrunk-20260515T1641Z-1456-images.zip`
   - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`
2. Gate SfM before 3DGS:
   - output files present
   - registered images close to the 1452 Meadow baseline
   - one merged component
   - points3D and points-per-image comparable to Montana
   - no mapper timeout/OOM
3. If SfM passes, launch the smallest downstream step: 3DGS+compression from
   this COLMAP output with the exact Montana 3DGS skybox image and compressor
   image, pinned by ECR digest.
4. Gate before visual acceptance:
   - training completes 30k iterations
   - exported skybox/background sidecars exist
   - gaussian count and PLY size comparable to Montana, not 31k/7MB collapse
   - compression succeeds and public bundle fetches anonymously
   - deployed viewer loads with skybox and no-sky modes
   - side-by-side source-vs-render camera checks pass for representative poses
   - manual camera sweep screenshots show recognizable property geometry
