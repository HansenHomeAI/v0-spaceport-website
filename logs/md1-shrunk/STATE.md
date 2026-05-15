# MD1-Shrunk E2E State

updated: 2026-05-15T15:21:20-0600
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
- Added explicit role override support to:
  - `scripts/sfm/run_sfm_benchmark.py --role-arn ...`
  - reason: the branch preview stack was discoverable but did not expose a
    resolvable SageMaker execution role; the direct SfM launch now pins the
    known staging role instead of guessing from CloudFormation.

## Validation So Far

- `python3 -m py_compile scripts/sfm/prepare_colmap_spatial_subset_zip.py`
- `python3 -m py_compile scripts/sfm/run_sfm_benchmark.py scripts/sfm/prepare_colmap_spatial_subset_zip.py`
- `python3 -m unittest tests.unit.test_colmap_spatial_subset_zip tests.unit.test_spatial_heading_benchmark_subset`
- `git diff --check`
- Commit/push:
  - `98556e5595a15a0c2675fbe0753fedf1bbb88fdf` (`chore: prepare md1 shrunk spatial subset`)
  - exact-head `CDK Deploy` run `25931581976` -> success

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

1. Launched exactly one MD1-Shrunk SfM processing job with chunked SfM settings
   matching the largest Montana path:
   - `COLMAP_ENABLE_SPATIAL_CHUNKING=1`
   - `COLMAP_CHUNK_PLANNER=legacy_spatial_heading`
   - `COLMAP_MATCH_PROFILE=P1`
   - source ZIP: `s3://spaceport-uploads/md1-shrunk-20260515T1641Z-1456-images.zip`
   - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`
   - job: `md1-shrunk-1456-sfm-1778866088`
   - ARN: `arn:aws:sagemaker:us-west-2:975050048887:processing-job/md1-shrunk-1456-sfm-1778866088`
   - image pinned by digest: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:05e85850abcfd623e8ec7f3debc70ce2dcd9861548311290db901e0c661d4940`
   - role: `arn:aws:iam::975050048887:role/Spaceport-SageMaker-Role-staging`
   - payload: `logs/md1-shrunk/md1-shrunk-20260515T1641Z-sfm-payload.json`
   - start proof: `logs/md1-shrunk/md1-shrunk-20260515T1641Z-sfm-start.json`
   - first describe snapshot: `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260515T1728Z.json`
   - startup describe snapshot: `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260515T1730Z.json`
   - log stream: `/aws/sagemaker/ProcessingJobs` / `md1-shrunk-1456-sfm-1778866088/algo-1-1778866129`
   - first CloudWatch snapshot: `logs/md1-shrunk/cloudwatch-md1-shrunk-1456-sfm-1778866088-20260515T1732Z.json`
   - observed startup: downloaded the `6063352899` byte ZIP, extracted `1456` images, detected GPS/orientation on `1456` images, prepared a `1456` entry image list, and started GPU feature extraction.
   - latest poll snapshot:
     - SageMaker: `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260515T1738Z.json`
     - CloudWatch: `logs/md1-shrunk/cloudwatch-md1-shrunk-1456-sfm-1778866088-20260515T1738Z.json`
     - S3 output listing: `logs/md1-shrunk/s3-colmap-md1-shrunk-20260515T1641Z-20260515T1738Z.txt`
   - latest observed progress:
     - `ProcessingJobStatus=InProgress`, `FailureReason=null`
     - GPU feature extraction reached `Processed file [160/1456]`
     - S3 output still empty as expected because output upload is `EndOfJob`.
   - 2026-05-15T11:47:16-0600 resume verification:
     - branch/head/status commands:
       - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
       - `git rev-parse HEAD` -> `e9cbf71c56420ce386b028e7f4af33163ce4dcc2`
       - `git status --short` -> clean before polling snapshots
     - AWS identity command:
       - `aws sts get-caller-identity --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
     - Step Functions command:
       - `aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --max-results 10 --region us-west-2 --output json` -> no running executions
     - SageMaker commands:
       - `aws sagemaker describe-processing-job --processing-job-name md1-shrunk-1456-sfm-1778866088 --region us-west-2 --output json > logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260515T1747Z.json`
       - `aws sagemaker list-processing-jobs --status-equals InProgress --sort-by CreationTime --sort-order Descending --max-results 20 --region us-west-2 --output json` -> only `md1-shrunk-1456-sfm-1778866088`
       - `aws sagemaker list-training-jobs --status-equals InProgress --sort-by CreationTime --sort-order Descending --max-results 20 --region us-west-2 --output json` -> external/not owned `md1-worst447-ds1000-r29-1778860601`, left untouched
     - GitHub workflow command:
       - `gh run list --branch agent-113647-md1-baseline-e2e --limit 10 --json databaseId,workflowName,headSha,status,conclusion,createdAt,updatedAt,url` -> exact-head `CDK Deploy` run `25932325504` succeeded for `e9cbf71c56420ce386b028e7f4af33163ce4dcc2`
     - CloudWatch command:
       - `aws logs get-log-events --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name md1-shrunk-1456-sfm-1778866088/algo-1-1778866129 --start-from-head --region us-west-2 --output json > logs/md1-shrunk/cloudwatch-md1-shrunk-1456-sfm-1778866088-20260515T1747Z.json`
     - S3 output listing command:
       - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap --recursive --summarize --human-readable --region us-west-2 > logs/md1-shrunk/s3-colmap-md1-shrunk-20260515T1641Z-20260515T1747Z.txt`
     - latest observed progress:
       - `ProcessingJobStatus=InProgress`, `FailureReason=null`
       - GPU feature extraction reached `Processed file [404/1456]`
       - S3 output: `Total Objects: 0`, `Total Size: 0 Bytes`; expected while `S3UploadMode=EndOfJob`
   - 2026-05-15T11:52:55-0600 poll:
     - SageMaker snapshot: `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260515T1752Z.json`
     - CloudWatch snapshot: `logs/md1-shrunk/cloudwatch-md1-shrunk-1456-sfm-1778866088-20260515T1752Z.json`
     - S3 output listing: `logs/md1-shrunk/s3-colmap-md1-shrunk-20260515T1641Z-20260515T1752Z.txt`
     - `ProcessingJobStatus=InProgress`, `FailureReason=null`
     - GPU feature extraction reached `Processed file [558/1456]`
     - S3 output still empty as expected until `EndOfJob`.
   - 2026-05-15T11:58:37-0600 poll:
     - SageMaker snapshot: `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260515T1758Z.json`
     - CloudWatch paged snapshot: `logs/md1-shrunk/cloudwatch-md1-shrunk-1456-sfm-1778866088-20260515T1758Z.json`
     - CloudWatch latest tail snapshot: `logs/md1-shrunk/cloudwatch-tail-md1-shrunk-1456-sfm-1778866088-20260515T1758Z.txt`
     - S3 output listing: `logs/md1-shrunk/s3-colmap-md1-shrunk-20260515T1641Z-20260515T1758Z.txt`
     - `ProcessingJobStatus=InProgress`, `FailureReason=null`
     - GPU feature extraction reached `Processed file [730/1456]`
     - S3 output still empty as expected until `EndOfJob`.
   - 2026-05-15T12:24:56-0600 resume verification:
     - branch/head/status:
       - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
       - `git rev-parse HEAD` -> `5eef154ce29605c6fb55c8954263b60fe167033c`
       - `git status --porcelain=v1` -> clean
     - AWS identity:
       - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
     - Step Functions state:
       - `aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --max-results 10 --region us-west-2` -> no InProgress executions
     - GitHub workflow (exact-head):
       - `gh run list --branch agent-113647-md1-baseline-e2e --limit 20 --json databaseId,workflowName,headSha,status,conclusion,createdAt,updatedAt,url` -> head `5eef154c...` has `CDK Deploy` run `25935463867` succeeded
     - SageMaker snapshot:
       - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260515T1823Z.json`
     - CloudWatch snapshots:
       - `logs/md1-shrunk/cloudwatch-tailonly-md1-shrunk-1456-sfm-1778866088-20260515T1822Z.json` -> feature extraction reached `Processed file [1392/1456]`
       - `logs/md1-shrunk/cloudwatch-tailonly-md1-shrunk-1456-sfm-1778866088-20260515T1823Z.json`
       - `logs/md1-shrunk/cloudwatch-tailonly-md1-shrunk-1456-sfm-1778866088-20260515T1823Z.txt` -> feature extraction reached `Processed file [1400/1456]`
     - S3 output listing:
       - `logs/md1-shrunk/s3-colmap-md1-shrunk-20260515T1641Z-20260515T1823Z.txt`
     - latest observed status:
       - `ProcessingJobStatus=InProgress`, `FailureReason=null`
   - 2026-05-15T12:43:40-0600 poll:
     - SageMaker snapshot: `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260515T1843Z.json`
     - CloudWatch tail snapshot: `logs/md1-shrunk/cloudwatch-tailonly-md1-shrunk-1456-sfm-1778866088-20260515T1843Z.txt`
       - mapper progress: `last_num_reg_frames=248` (from `SUMMARY` line)
     - S3 output listing: `logs/md1-shrunk/s3-colmap-md1-shrunk-20260515T1641Z-20260515T1843Z.txt`
     - `ProcessingJobStatus=InProgress`, `FailureReason=null`
   - 2026-05-15T13:03:36-0600 poll:
     - branch/head/status:
       - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
       - `git rev-parse HEAD` -> `7df1a21171774e2bbc04a4824fd2ed5eb0f45543`
       - `git status --porcelain=v1` -> new untracked poll artifacts under `logs/md1-shrunk/`
     - GitHub workflow (exact-head):
       - `gh run view 25935887777 --json databaseId,workflowName,headSha,status,conclusion,createdAt,updatedAt,url > logs/md1-shrunk/gh-run-view-25935887777.json` -> `CDK Deploy` succeeded for head `7df1a211...`
       - `gh run watch 25935887777 --interval 10 --exit-status > logs/md1-shrunk/gh-run-watch-25935887777.txt`
       - prior run `25935881055` was cancelled due to GitHub workflow concurrency:
         - `logs/md1-shrunk/gh-run-view-25935881055.json`
         - `logs/md1-shrunk/gh-run-watch-25935881055.txt`
     - SageMaker snapshot: `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260515T185321Z.json`
     - CloudWatch tail snapshot: `logs/md1-shrunk/cloudwatch-tail-md1-shrunk-1456-sfm-1778866088-20260515T185321Z.txt`
       - mapper progress: observed `num_reg_frames=172` (from `Registering image ... (num_reg_frames=172)`)
     - S3 output listing: `logs/md1-shrunk/s3-colmap-md1-shrunk-20260515T1641Z-20260515T185321Z.txt` -> still empty as expected with `S3UploadMode=EndOfJob`
       - note: `aws s3 ls ... --summarize` returns exit status `1` when the prefix is empty
     - attempted `SUMMARY` CloudWatch filter produced no hits:
       - `logs/md1-shrunk/cloudwatch-filter-summary-md1-shrunk-1456-sfm-1778866088-20260515T184933Z.json`
       - `logs/md1-shrunk/cloudwatch-filter-summary-md1-shrunk-1456-sfm-1778866088-20260515T184957Z.json`
   - 2026-05-15T13:10:38-0600 GitHub exact-head verification:
     - branch/head:
       - `git rev-parse HEAD` -> `6f28df7528a830c540e989cea025d4a61d6521b7`
     - `CDK Deploy` succeeded for head `6f28df75...`:
       - `logs/md1-shrunk/gh-run-view-25936245460.json`
       - `logs/md1-shrunk/gh-run-watch-25936245460.txt`
   - 2026-05-15T13:15:55-0600 poll:
     - branch/head:
       - `git rev-parse HEAD` -> `01e267a8f21f2cc0bca2862da6a2e68a7c53d0ca`
     - GitHub workflow (exact-head):
       - `CDK Deploy` succeeded for head `01e267a8...`:
         - `logs/md1-shrunk/gh-run-view-25936455479.json`
         - `logs/md1-shrunk/gh-run-watch-25936455479.txt`
     - Step Functions snapshot:
       - `logs/md1-shrunk/stepfunctions-list-state-machines-20260515T191506Z.json`
       - `logs/md1-shrunk/stepfunctions-running-SpaceportMLPipeline-staging-20260515T191506Z.json` -> `RUNNING=0`
     - SageMaker snapshot:
       - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260515T191506Z.json`
       - `ProcessingJobStatus=InProgress`, `FailureReason=null`
     - CloudWatch tail snapshot:
       - `logs/md1-shrunk/cloudwatch-tail-md1-shrunk-1456-sfm-1778866088-20260515T191506Z.txt`
       - mapper progress: `chunk_01_mapper_initial model 1 registered 383/383 images and 276594 points`
     - S3 output listing:
       - `logs/md1-shrunk/s3-colmap-md1-shrunk-20260515T1641Z-20260515T191506Z.txt` -> still empty as expected with `S3UploadMode=EndOfJob`
   - 2026-05-15T13:47:36-0600 poll:
     - branch/head/status:
       - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
       - `git rev-parse HEAD` -> `fa0b3d8e1ec48e4b4415aec65577b8b27c9f3d02`
       - `git status --porcelain=v1` -> `logs/md1-shrunk/STATE.md` modified + new poll artifacts under `logs/md1-shrunk/`
     - GitHub workflow (exact-head):
       - `CDK Deploy` succeeded for head `fa0b3d8e...` (run `25936681548`):
         - `logs/md1-shrunk/gh-run-view-25936681548.json`
         - `logs/md1-shrunk/gh-run-watch-25936681548.txt`
       - full branch workflow list snapshot:
         - `logs/md1-shrunk/gh-run-list-20260515T194506Z.json`
     - Step Functions snapshot:
       - `logs/md1-shrunk/stepfunctions-list-executions-20260515T194506Z.json` -> no `RUNNING` executions in the latest page
     - SageMaker snapshot:
       - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260515T194607Z.json`
       - `ProcessingJobStatus=InProgress`, `FailureReason=null`
     - CloudWatch tail snapshot:
       - `logs/md1-shrunk/cloudwatch-tail-md1-shrunk-1456-sfm-1778866088-20260515T194607Z.txt`
       - observed progress moved into `chunk_04_sequential_matcher` (`Processing image [153/307]`)
     - S3 output listing:
       - `logs/md1-shrunk/s3-colmap-md1-shrunk-20260515T1641Z-20260515T194607Z.txt` -> still empty as expected with `S3UploadMode=EndOfJob`
       - note: `aws s3 ls ... --summarize` returns exit status `1` when the prefix is empty
   - 2026-05-15T14:58:06-0600 poll:
     - branch/head/status:
       - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
       - `git rev-parse HEAD` -> `a87c305d7bd916dd74389de96e019cc751ec656b`
       - `git status --porcelain=v1` -> new untracked poll artifacts under `logs/md1-shrunk/`
     - AWS identity:
       - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
     - Step Functions snapshot:
       - `logs/md1-shrunk/stepfunctions-running-SpaceportMLPipeline-staging-20260515T204603Z.json` -> `RUNNING=0`
     - GitHub workflow (exact-head):
       - `CDK Deploy` succeeded for head `a87c305d...` (run `25938096579`):
         - `logs/md1-shrunk/gh-run-list-20260515T204603Z.json`
     - SageMaker snapshots:
       - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260515T204603Z.json` -> `ProcessingJobStatus=InProgress`, `FailureReason=null`
       - `logs/md1-shrunk/sagemaker-list-processing-InProgress-20260515T204603Z.json` -> only `md1-shrunk-1456-sfm-1778866088`
       - `logs/md1-shrunk/sagemaker-list-training-InProgress-20260515T204603Z.json` -> external/non-owned: `md1-tile00-ds1000-r30-1778869168`, `md1-tile01-ds1000-r30-1778869169` (left untouched)
     - CloudWatch tail snapshots (last ~10 minutes per poll):
       - `logs/md1-shrunk/cloudwatch-tail-md1-shrunk-1456-sfm-1778866088-20260515T204635Z.txt` -> seam model triangulation reached image `#1456` then `Extracting colors`
       - `logs/md1-shrunk/cloudwatch-tail-md1-shrunk-1456-sfm-1778866088-20260515T205545Z.txt` -> `chunk_model_seam_05_point_triangulator_02` in `Retriangulation and Global bundle adjustment` (still running)
     - S3 output listings:
       - `logs/md1-shrunk/s3-colmap-md1-shrunk-20260515T1641Z-20260515T205545Z.txt` -> still empty as expected with `S3UploadMode=EndOfJob`
       - note: `aws s3 ls ... --summarize` returns exit status `1` when the prefix is empty
   - 2026-05-15T15:19:19-0600 SfM terminal + 3DGS launch attempt:
     - GitHub workflow (exact-head):
       - `CDK Deploy` succeeded for head `29b35ce2...` (run `25941171160`):
         - `logs/md1-shrunk/gh-run-view-25941171160.json`
         - `logs/md1-shrunk/gh-run-watch-25941171160.txt`
     - SageMaker SfM terminal status:
       - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260515T211530Z.json` -> `ProcessingJobStatus=Completed`, `FailureReason=null`
       - CloudWatch completion proof:
         - `logs/md1-shrunk/cloudwatch-tail-md1-shrunk-1456-sfm-1778866088-20260515T210614Z.txt` includes `🎉 SPACEPORT COLMAP GPU SfM COMPLETED SUCCESSFULLY!`
     - S3 output listing (post EndOfJob upload):
       - `logs/md1-shrunk/s3-colmap-md1-shrunk-20260515T1641Z-20260515T210920Z.txt` -> `Total Objects: 1468`, `Total Size: 9915165134`
       - `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap/sparse/0/` present; no other sparse components (`sparse/` only has `0/`)
     - Montana gates from the uploaded COLMAP TXT:
       - registered images: `1456` (stream-counted from `sparse/0/images.txt`)
       - points3D: `1020913` (stream-counted from `sparse/0/points3D.txt`)
       - merged component count: `1` (`sparse/` only has `0/`)
     - Pre-launch cost gate:
       - `logs/md1-shrunk/stepfunctions-running-SpaceportMLPipeline-staging-20260515T211617Z.json` -> `RUNNING=0`
       - `logs/md1-shrunk/sagemaker-list-processing-InProgress-20260515T211617Z.json` -> `InProgress=0`
       - `logs/md1-shrunk/sagemaker-list-training-InProgress-20260515T211617Z.json` -> `InProgress=2` (external/not owned)
     - Downstream (3DGS+compression) start attempt (blocked by quota):
       - Payload: `logs/md1-shrunk/md1-shrunk-1456-vsfm-w-light-202605152116-payload.json`
       - Start: `logs/md1-shrunk/md1-shrunk-1456-vsfm-w-light-202605152116-start.json`
       - Step Functions describe: `logs/md1-shrunk/stepfunctions-describe-md1-shrunk-1456-vsfm-w-light-202605152116-20260515T211724Z.json` -> execution ended immediately after a `SageMaker.ResourceLimitExceededException`
       - Step Functions history: `logs/md1-shrunk/stepfunctions-history-md1-shrunk-1456-vsfm-w-light-202605152116-20260515T211751Z.json`
         - failure: `ml.g5.2xlarge for training job usage` limit `2` already fully utilized
       - Blocking training jobs (ml.g5.2xlarge, not owned by this run):
         - `logs/md1-shrunk/sagemaker-describe-training-md1-tile02-ds1000-r30-1778869170-20260515T212248Z.json`
         - `logs/md1-shrunk/sagemaker-describe-training-md1-tile03-ds1000-r30-1778869171-20260515T212248Z.json`
     - Next step:
       - Wait for one of the two external `ml.g5.2xlarge` training jobs to finish, then re-run the 3DGS step with the same COLMAP output (do not stop external jobs unless clearly orphaned).
   - Current downstream image facts for the post-SfM stage:
     - `aws ecr describe-images --repository-name spaceport/3dgs --image-ids imageTag=agent113647md1baselinee2e --region us-west-2 --output json > logs/md1-shrunk/ecr-3dgs-agent113647md1baselinee2e-20260515T1758Z.json`
       - digest `sha256:6b3b2492af7a268cfc5f233e87bdce51c47492ada4c3630f723114ffa464fd0c`
       - pushed `2026-05-14T13:37:06.875000-0600`
     - `aws ecr describe-images --repository-name spaceport/compressor --image-ids imageTag=agent113647md1baselinee2e --region us-west-2 --output json > logs/md1-shrunk/ecr-compressor-agent113647md1baselinee2e-20260515T1758Z.json`
       - digest `sha256:c667899d7e844083e8d50b04329edd3841bbfb26f8876c917ade78be8f27d603`
       - pushed `2026-05-15T03:44:31.581000-0600`
     - `aws ecr describe-images --repository-name spaceport/sfm --image-ids imageTag=agent113647md1baselinee2e --region us-west-2 --output json` returned `ImageNotFoundException`; the active SfM job is therefore intentionally using the pinned digest recorded above, not a branch SFM tag.
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
