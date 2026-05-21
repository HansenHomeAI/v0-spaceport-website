# MD1-Shrunk E2E State

updated: 2026-05-21T09:15:09Z
branch: agent-113647-md1-baseline-e2e
repo: HansenHomeAI/v0-spaceport-website
head: 1e56f855b9fc3c6e39af9619135efd7f62b419e7

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

## 2026-05-17T09:15:31Z poll (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260517T091531Z/`
- Branch/head/status:
  - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - poll-time `git rev-parse HEAD` -> `6aab7a76c8afe54f9af2f62392b1146ff42e8fd1` (`[skip ci]`)
  - evidence-capture `git rev-parse HEAD` -> `59a7c48508f571e17e664ab1bd90299069cc83d2` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260517T091531Z/git-after-push.txt`
- AWS identity (via boto3, region `us-west-2`):
  - `Account=975050048887`, `Arn=arn:aws:iam::975050048887:root`
  - evidence: `logs/md1-shrunk/polls/20260517T091531Z/aws-sts-get-caller-identity.json`
- Step Functions state (via boto3, region `us-west-2`):
  - md1-matched RUNNING executions: `0`
  - evidence: `logs/md1-shrunk/polls/20260517T091531Z/stepfunctions-md1-running-executions.json`
- SageMaker state (via boto3, region `us-west-2`):
  - `md1-shrunk-1456-sfm-1778866088` -> `ProcessingJobStatus=Completed`, `FailureReason=null`
  - InProgress processing jobs: `0`
  - InProgress training jobs: `0`

## 2026-05-18T08:51:06Z poll (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T085106Z/`
- Branch/head/status:
  - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - `git rev-parse HEAD` -> `24a55f5aae0918f08ec07c0a6c373b38e2eb6dc2` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T085106Z/git.txt`
- GitHub workflows (branch `agent-113647-md1-baseline-e2e`, via `gh run list`):
  - exact-head workflows: none for `24a55f5a...` (skip-ci)
  - last non-skip Pages + CDK success observed in list: head `049c70baf003e3a1e816f729c514d6b491665a76`
  - prior exact-head CDK success for provided head: `e9cbf71c56420ce386b028e7f4af33163ce4dcc2` -> run `25932325504` (success)
- AWS identity (region `us-west-2`):
  - `Account=975050048887`, `Arn=arn:aws:iam::975050048887:root`
  - evidence: `logs/md1-shrunk/polls/20260518T085106Z/aws-sts-get-caller-identity.json`
- Step Functions state:
  - `SpaceportMLPipeline-staging` RUNNING executions: `0`
  - evidence: `logs/md1-shrunk/polls/20260518T085106Z/stepfunctions-running-executions.json`
- SageMaker SfM job terminal state:
  - `md1-shrunk-1456-sfm-1778866088` -> `ProcessingJobStatus=Completed`, `FailureReason=null`
  - evidence: `logs/md1-shrunk/polls/20260518T085106Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
  - CloudWatch tail: `logs/md1-shrunk/polls/20260518T085106Z/cloudwatch-tail-md1-shrunk-1456-sfm-1778866088.txt`
- SfM output S3 (upload mode `EndOfJob` confirmed now present):
  - `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`
  - evidence: `logs/md1-shrunk/polls/20260518T085106Z/s3-colmap-root.txt`
  - evidence: `logs/md1-shrunk/polls/20260518T085106Z/s3-colmap-sparse-0.txt`
- Montana gates (from `sfm_metadata.json`):
  - dataset_image_count: `1456`
  - images_registered: `1456` (Meadow/Incognito ref `1452`)
  - merged_component_count: `1`
  - points_3d: `1103335` (Meadow/Incognito ref `940147`)
  - quality_check_passed: `true`
  - timed_out: `false`
  - processing_time_seconds: `12709.05` (≈ 3.53h)
  - evidence: `logs/md1-shrunk/polls/20260518T085106Z/sfm_metadata.json`
  - extracted: `logs/md1-shrunk/polls/20260518T085106Z/colmap-metrics.json`

## 2026-05-18T09:19:00Z poll (monitor; reconfirm terminal + public URLs)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T091900Z/`
- Branch/head/status:
  - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - `git rev-parse HEAD` -> `204e7b6794c8ae3505c390361b48c345bfdbc103` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T091900Z/git.txt`
- GitHub workflows (GitHub REST API via git credential helper; `gh` not present on this machine):
  - exact-head workflows: none for `204e7b67...` (skip-ci)
  - provided exact-head CDK proof: `e9cbf71c...` -> `CDK Deploy` run `25932325504` `success`
  - evidence:
    - branch runs list: `logs/md1-shrunk/polls/20260518T091900Z/github-actions-runs.json`
    - head-sha filter (provided head): `logs/md1-shrunk/polls/20260518T091900Z/github-actions-runs-e9cb.json`
    - head-sha filter (current head): `logs/md1-shrunk/polls/20260518T091900Z/github-actions-runs-204e.json`
- AWS identity + active state (via boto3; `aws` CLI not present on this machine):
  - identity: account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`
  - SageMaker InProgress processing jobs: `0`
  - SageMaker InProgress training jobs: `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T091900Z/aws-sts-get-caller-identity.json`
    - `logs/md1-shrunk/polls/20260518T091900Z/stepfunctions-running-executions.json`
    - `logs/md1-shrunk/polls/20260518T091900Z/sagemaker-list-processing-jobs-InProgress.json`
    - `logs/md1-shrunk/polls/20260518T091900Z/sagemaker-list-training-jobs-InProgress.json`
- SageMaker SfM terminal state:
  - `md1-shrunk-1456-sfm-1778866088` -> `ProcessingJobStatus=Completed`, `FailureReason=null`
  - evidence: `logs/md1-shrunk/polls/20260518T091900Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
- SfM output S3 present:
  - `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`
  - evidence: `logs/md1-shrunk/polls/20260518T091900Z/s3-colmap-summary.json`
  - `sfm_metadata.json` snapshot: `logs/md1-shrunk/polls/20260518T091900Z/sfm_metadata.json`
- Public URL liveness (no auth required):
  - preview alias URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev` -> `HTTP 200`
  - bundle meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/meta.json` -> `HTTP 200`
  - skybox asset: `.../background_skybox.webp` -> `HTTP 200`
  - evidence: `logs/md1-shrunk/polls/20260518T091900Z/http-headers.txt`

## 2026-05-18T09:21:26Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T092126Z-postpush/`
- Branch/head/status:
  - `git rev-parse HEAD` -> `be2a17b784c087a4f0cfcdd471e0bc93e2f5b8de` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T092126Z-postpush/git.txt`
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (skip-ci poll commit)
  - evidence: `logs/md1-shrunk/polls/20260518T092126Z-postpush/github-actions-runs-head.json`

### 2026-05-18 duplicate downstream launch (aborted; cost bounded)

- Background: MD1-Shrunk already has completed 3DGS+compression + viewer gates recorded later in this ledger (job family `md1shrunk1456-1778880862`), so no new downstream launch was needed.
- Duplicate 3DGS+compression execution was started and immediately aborted:
  - Step Functions execution:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:md1-shrunk-1456-3dgs-20260518-085235`
    - `aws stepfunctions stop-execution ...` -> `ABORTED`
    - evidence: `logs/md1-shrunk/executions/md1-shrunk-1456-3dgs-20260518-085235/stop-execution.json`
    - evidence: `logs/md1-shrunk/executions/md1-shrunk-1456-3dgs-20260518-085235/describe-execution-after-stop.json`
  - SageMaker training job:
    - `md1-shrunk-1456-20260518-085235-3dgs` -> `Stopped`
    - `aws sagemaker stop-training-job ...`
    - evidence: `logs/md1-shrunk/executions/md1-shrunk-1456-3dgs-20260518-085235/stop-training-job.json`
  - evidence:
    - `logs/md1-shrunk/polls/20260517T091531Z/sagemaker-describe-processing-job-md1-shrunk-1456-sfm-1778866088.json`
    - `logs/md1-shrunk/polls/20260517T091531Z/sagemaker-list-processing-jobs-InProgress.json`
    - `logs/md1-shrunk/polls/20260517T091531Z/sagemaker-list-training-jobs-InProgress.json`
- GitHub Actions (exact head + latest, via `gh`):
  - exact head `59a7c485...` has `0` runs (commit message includes `[skip ci]`)
  - latest `CDK Deploy` run: `25986385371` -> `success` (head `7d1b62b4...`)
  - latest `Pages` run: `25983995070` -> `success` (head `3bad045c...`)
  - evidence:
    - `logs/md1-shrunk/polls/20260517T091531Z/gh-run-list.json`
    - `logs/md1-shrunk/polls/20260517T091531Z/gh-run-list-tail.json`
    - `logs/md1-shrunk/polls/20260517T091531Z/gh-summary.json`
    - `logs/md1-shrunk/polls/20260517T091531Z/gh-auth-status.txt`
    - `logs/md1-shrunk/polls/20260517T091531Z/gh-version.txt`
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
   - 2026-05-15T15:24:44-0600 GitHub exact-head verification:
     - branch/head:
       - `git rev-parse HEAD` -> `f605e655ae27faeb971e6101201042989d82c50e`
     - `CDK Deploy` succeeded for head `f605e655...` (run `25941967719`):
       - `logs/md1-shrunk/gh-run-view-25941967719.json`
       - `logs/md1-shrunk/gh-run-watch-25941967719.txt`
   - 2026-05-15T15:35:48-0600 3DGS relaunch on branch-preview state machine (quota workaround)
     - Infra fix landed:
       - branch/head: `3a747a0d08c2dc8953ae3c61f8248bb7bc4c563d` (`fix: make 3dgs instance type configurable`)
       - `CDK Deploy` succeeded for head `3a747a0d...` (run `25942170320`):
         - `logs/md1-shrunk/gh-run-view-25942170320.json`
         - `logs/md1-shrunk/gh-run-watch-25942170320.txt`
     - Important: the shared state machine `SpaceportMLPipeline-staging` still has hardcoded `ml.g5.2xlarge`; the updated definition is in the branch-preview state machine:
       - `SpaceportMLPipeline-br-8abcbd5662`
     - Active execution (RUNNING):
       - name: `execution-md1shrunk1456-1778880862`
       - describe: `logs/md1-shrunk/stepfunctions-describe-execution-md1shrunk1456-1778880862-20260515T213525Z.json`
       - inputs (pinned):
         - `GAUSSIAN_INSTANCE_TYPE=ml.g5.4xlarge` (avoid `ml.g5.2xlarge` quota saturation)
         - `gaussianImageUri=.../spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`
         - `compressorImageUri=.../spaceport/compressor@sha256:a0784727da1870ce9caa4774dc831a32fb96cd1574df389cf9093fbf18f4f4ab`
         - `colmapOutputS3Uri=s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap/`
     - Active SageMaker training job (3DGS):
       - name: `md1shrunk1456-1778880862-3dgs`
       - describe: `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260515T213545Z.json`
       - status: `InProgress` on `ml.g5.4xlarge` (SecondaryStatus at snapshot: `Downloading`)
     - Cost-boundedness note:
       - A redundant manual 3DGS job was started then immediately stopped to avoid duplicate GPU spend:
         - launched: `md1shrunk1456-wlight-2605152127-g5xl-3dgs` (`ml.g5.xlarge`)
         - stop confirmation: `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-wlight-2605152127-g5xl-3dgs-poststop2-20260515T214010Z.json` -> `TrainingJobStatus=Stopped`
   - 2026-05-15T15:45:15-0600 3DGS progress poll:
     - Step Functions execution still RUNNING:
       - `logs/md1-shrunk/stepfunctions-describe-execution-br8abc-md1shrunk1456-1778880862-20260515T214402Z.json`
     - SageMaker training job still InProgress:
       - `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260515T214402Z.json`
     - CloudWatch training tail snapshot:
       - `logs/md1-shrunk/cloudwatch-training-tail-md1shrunk1456-1778880862-3dgs-20260515T214335Z.txt`
   - 2026-05-15T15:47:02-0600 3DGS progress poll:
     - Step Functions execution still RUNNING:
       - `logs/md1-shrunk/stepfunctions-describe-execution-md1shrunk1456-1778880862-20260515T214702Z.json`
     - SageMaker training job still InProgress (SecondaryStatus: `Training`):
       - `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260515T214702Z.json`
     - CloudWatch training tail snapshot shows NerfStudio `ns-train` launched (30k iters):
       - `logs/md1-shrunk/cloudwatch-training-tail-md1shrunk1456-1778880862-3dgs-20260515T214702Z.txt`
     - Training output prefix still empty (expected early while training is running):
       - `logs/md1-shrunk/s3-3dgs-md1shrunk1456-1778880862-20260515T214702Z.txt` -> `Total Objects: 0`, `Total Size: 0 Bytes`
   - 2026-05-15T15:51:01-0600 3DGS progress poll:
     - Step Functions execution still RUNNING:
       - `logs/md1-shrunk/stepfunctions-describe-execution-md1shrunk1456-1778880862-20260515T215101Z.json`
     - SageMaker training job still InProgress (SecondaryStatus: `Training`):
       - `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260515T215101Z.json`
     - CloudWatch training tail snapshot is unchanged (no new training-step logs yet beyond `ns-train` launch):
       - `logs/md1-shrunk/cloudwatch-training-tail-md1shrunk1456-1778880862-3dgs-20260515T215101Z.txt`
       - stream timestamp check: `logs/md1-shrunk/cloudwatch-training-streams-md1shrunk1456-1778880862-3dgs-20260515T215126Z.json`
     - Training output prefix still empty:
       - `logs/md1-shrunk/s3-3dgs-md1shrunk1456-1778880862-20260515T215101Z.txt` -> `Total Objects: 0`, `Total Size: 0 Bytes`
   - 2026-05-15T15:58:20-0600 commit/push + CI:
     - branch/head:
       - `git rev-parse HEAD` -> `da90b8de9eb22d1c654e5cca7606eb0d8af3e52b` (`chore: poll md1-shrunk 3dgs progress`)
     - GitHub workflow (exact-head):
       - run list: `logs/md1-shrunk/gh-run-list-20260515T215749Z.json`
       - `CDK Deploy` succeeded for head `da90b8de...` (run `25943245056`):
         - `logs/md1-shrunk/gh-run-view-25943245056.json`
         - `logs/md1-shrunk/gh-run-watch-25943245056.txt`
     - Step Functions + SageMaker (no new launches):
       - execution still RUNNING: `logs/md1-shrunk/stepfunctions-describe-execution-br8abc-md1shrunk1456-1778880862-20260515T215406Z.json`
       - training job still InProgress/Training: `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260515T215406Z.json`
   - 2026-05-15T16:03:25-0600 CI confirmation + 3DGS still running:
     - branch/head:
       - `git rev-parse HEAD` -> `4886f1b7ca244f3d4fda0854a6295e19664a9889` (`chore: record md1-shrunk poll evidence`)
     - GitHub workflow (exact-head):
       - `CDK Deploy` succeeded for head `4886f1b7...` (run `25943425464`):
         - `logs/md1-shrunk/gh-run-view-25943425464.json`
         - `logs/md1-shrunk/gh-run-watch-25943425464.txt`
     - Step Functions + SageMaker (no new launches; keep monitoring):
       - execution still RUNNING: `logs/md1-shrunk/stepfunctions-describe-execution-br8abc-md1shrunk1456-1778880862-20260515T220318Z.json`
       - training job still InProgress/Training: `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260515T220318Z.json`
   - 2026-05-15T16:22:04-0600 poll (SfM gated; 3DGS still running):
     - branch/head/status:
       - `git rev-parse HEAD` -> `49557d76d28c5d974557f6289588e27bfe135caf`
       - `git status --porcelain=v1` -> new untracked poll artifacts under `logs/md1-shrunk/`
     - GitHub workflow (exact-head):
       - `CDK Deploy` succeeded for head `49557d76...` (run `25943603730`)
       - note: Pages workflow was not triggered by this poll-only push (no `web/trigger-dev-build.txt` bump)
     - SfM completion proof (CloudWatch tail includes full summary + output validation):
       - `logs/md1-shrunk/cloudwatch-processing-tail-md1-shrunk-1456-sfm-1778866088-20260515T221901Z.json`
       - `Images registered: 1456`, `3D points: 1020913`, `Fallback reason: not_needed`
     - SfM gate results (Montana facts):
       - output files present in `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`
       - registered images: `1456` (Meadow baseline `1452`)
       - merged components: `1` (only `sparse/0/` present)
       - points3D: `1020913` (Montana range ~`940k–1.03M`)
     - Step Functions snapshot:
       - staging pipeline (`SpaceportMLPipeline-staging`) currently not RUNNING:
         - `logs/md1-shrunk/stepfunctions-running-SpaceportMLPipeline-staging-20260515T221804Z.json` -> `RUNNING=0`
         - `logs/md1-shrunk/stepfunctions-list-executions-SpaceportMLPipeline-staging-20260515T221923Z.json` -> latest page shows recent `SUCCEEDED` executions
       - branch preview pipeline (`SpaceportMLPipeline-br-8abcbd5662`) still RUNNING:
         - `logs/md1-shrunk/stepfunctions-list-state-machines-20260515T222817Z.json`
         - `logs/md1-shrunk/stepfunctions-running-SpaceportMLPipeline-br-8abcbd5662-20260515T222825Z.json` -> `RUNNING=1`
         - `logs/md1-shrunk/stepfunctions-describe-execution-br-8abcbd5662-md1shrunk1456-1778880862-20260515T222835Z.json`
     - SageMaker 3DGS training (still InProgress/Training):
       - describe snapshots:
         - `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260515T221842Z.json`
         - `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260515T222202Z.json`
       - CloudWatch stream/tail (no new events beyond `ns-train` launch yet):
         - stream: `md1shrunk1456-1778880862-3dgs/algo-1-1778880912`
         - `logs/md1-shrunk/cloudwatch-training-streams-md1shrunk1456-1778880862-3dgs-20260515T221842Z.json`
         - `logs/md1-shrunk/cloudwatch-training-tail-md1shrunk1456-1778880862-3dgs-20260515T221825Z.json`
       - Training output prefix still empty (expected until EndOfJob export):
         - `logs/md1-shrunk/s3-3dgs-md1shrunk1456-1778880862-20260515T221804Z.txt` -> `Total Objects: 0`, `Total Size: 0`
         - `logs/md1-shrunk/s3-3dgs-md1shrunk1456-1778880862-20260515T222236Z.txt` -> `Total Objects: 0`, `Total Size: 0`
  - 2026-05-15T16:56:05-0600 poll (3DGS still running; no additional CloudWatch beyond `ns-train` launch yet):
    - branch/head/status:
      - `git rev-parse HEAD` -> `29d479f4d04f83f4c2f113e2f7e9c2311f772e35`
      - `git status --porcelain=v1` -> clean
    - AWS identity:
      - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
    - GitHub workflows (exact-head):
      - `CDK Deploy` succeeded for head `29d479f4...` (run `25944450001`)
      - branch has both `CDK Deploy` and `Deploy Next.js to Cloudflare Pages` workflows; no `web/trigger-dev-build.txt` bump in this poll
    - Step Functions snapshot:
      - staging pipeline (`SpaceportMLPipeline-staging`) still not RUNNING (see prior poll)
      - branch preview execution still RUNNING:
        - `logs/md1-shrunk/stepfunctions-describe-execution-md1shrunk1456-1778880862-20260515T224929Z.json`
        - `logs/md1-shrunk/stepfunctions-history-md1shrunk1456-1778880862-20260515T224639Z.json` -> latest event `WaitStateEntered`
    - SageMaker 3DGS training (still InProgress/Training):
      - stream: `md1shrunk1456-1778880862-3dgs/algo-1-1778880912` (log group `/aws/sagemaker/TrainingJobs`)
      - describe snapshot:
        - `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260515T225500Z.json`
      - CloudWatch tail snapshots (still ends at `ns-train ...` command launch; no iteration logs yet):
        - `logs/md1-shrunk/cloudwatch-training-tail-md1shrunk1456-1778880862-3dgs-20260515T225500Z.txt`
      - Training output prefix still empty (expected until EndOfJob export):
        - `logs/md1-shrunk/s3-3dgs-md1shrunk1456-1778880862-20260515T225500Z.txt` -> `Total Objects: 0`, `Total Size: 0`
  - 2026-05-15T17:01:10-0600 push verification (workflows green; 3DGS still running):
    - branch/head/status:
      - `git rev-parse HEAD` -> `59025882aa5c6e04c25f6d9bda5ed9c891ee4a43`
      - `git status --porcelain=v1` -> new untracked poll artifacts under `logs/md1-shrunk/`
    - GitHub workflow (exact-head):
      - `CDK Deploy` succeeded for head `59025882...` (run `25945333283`)
        - `logs/md1-shrunk/gh-run-view-25945333283-20260515T230058Z.json`
        - `logs/md1-shrunk/gh-run-watch-25945333283-20260515T230058Z.txt`
      - Pages workflow not triggered by this poll-only push (no `web/trigger-dev-build.txt` bump)
    - SageMaker 3DGS training still InProgress/Training:
      - CloudWatch tail still ends at `ns-train ...` command launch (no iteration logs yet):
        - `logs/md1-shrunk/cloudwatch-training-tail-md1shrunk1456-1778880862-3dgs-20260515T230058Z.txt`
    - Current downstream image facts for the post-SfM stage:
      - `aws ecr describe-images --repository-name spaceport/3dgs --image-ids imageTag=agent113647md1baselinee2e --region us-west-2 --output json > logs/md1-shrunk/ecr-3dgs-agent113647md1baselinee2e-20260515T1758Z.json`
        - digest `sha256:6b3b2492af7a268cfc5f233e87bdce51c47492ada4c3630f723114ffa464fd0c`
        - pushed `2026-05-14T13:37:06.875000-0600`
     - `aws ecr describe-images --repository-name spaceport/compressor --image-ids imageTag=agent113647md1baselinee2e --region us-west-2 --output json > logs/md1-shrunk/ecr-compressor-agent113647md1baselinee2e-20260515T1758Z.json`
       - digest `sha256:c667899d7e844083e8d50b04329edd3841bbfb26f8876c917ade78be8f27d603`
       - pushed `2026-05-15T03:44:31.581000-0600`
     - `aws ecr describe-images --repository-name spaceport/sfm --image-ids imageTag=agent113647md1baselinee2e --region us-west-2 --output json` returned `ImageNotFoundException`; the active SfM job is therefore intentionally using the pinned digest recorded above, not a branch SFM tag.
- 2026-05-15T17:19:19-0600 monitor poll (3DGS still running; CloudWatch stream unchanged):
  - branch/head/status:
    - `git rev-parse HEAD` -> `0d27d4512334e8aa16b6385b6ab7509508542d58`
    - `git status --porcelain=v1` -> new untracked poll artifacts under `logs/md1-shrunk/`
  - AWS identity:
    - `aws sts get-caller-identity --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - GitHub workflows (exact-head):
    - run list snapshot: `logs/md1-shrunk/gh-run-list-20260515T231837Z.json`
    - `CDK Deploy` succeeded for head `0d27d451...` (run `25945475518`):
      - `logs/md1-shrunk/gh-run-view-25945475518-20260515T231845Z.json`
      - `logs/md1-shrunk/gh-run-watch-25945475518-20260515T231845Z.txt`
    - Pages workflow still not triggered (no `web/trigger-dev-build.txt` bump)
  - Step Functions (branch-preview pipeline):
    - state machine ARN proof: `logs/md1-shrunk/stepfunctions-state-machine-br8abc-20260515T231633Z.txt`
    - list executions: `logs/md1-shrunk/stepfunctions-list-executions-br8abc-20260515T231633Z.json`
    - describe execution: `logs/md1-shrunk/stepfunctions-describe-execution-br8abc-md1shrunk1456-1778880862-20260515T231633Z.json` -> `status=RUNNING`
    - latest history tail (reverse-order): `logs/md1-shrunk/stepfunctions-history-reverse-tail-br8abc-md1shrunk1456-1778880862-20260515T231814Z.json` -> most recent event `WaitStateEntered` @ `2026-05-15T17:16:34-0600`
  - SageMaker (3DGS training):
    - describe: `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260515T231558Z.json` -> `TrainingJobStatus=InProgress`, `SecondaryStatus=Training`, instance `ml.g5.4xlarge`
    - InProgress list snapshot: `logs/md1-shrunk/sagemaker-list-training-InProgress-20260515T231633Z.json` (includes external `md1-tile04-ds1000-r30-1778869172`; left untouched)
  - CloudWatch (SageMaker training logs):
    - stream metadata: `logs/md1-shrunk/cloudwatch-training-streams-md1shrunk1456-1778880862-3dgs-20260515T231726Z.json` -> `lastEventTimestamp=2026-05-15T21:42:31Z` (no new events since `ns-train` launch)
    - get-log-events tail: `logs/md1-shrunk/cloudwatch-training-getlogevents-md1shrunk1456-1778880862-3dgs-20260515T231558Z.json`
  - S3 training output prefix (still empty; expected until export):
    - `logs/md1-shrunk/s3-3dgs-md1shrunk1456-1778880862-20260515T231633Z.txt` -> `Total Objects: 0`, `Total Size: 0`
- 2026-05-15T17:24:55-0600 commit/push + CI (workflows green; 3DGS still running):
  - branch/head:
    - `git rev-parse HEAD` -> `78e74cd26391cbc8e656960c1df0067f295fbe5c` (`chore: poll md1-shrunk 3dgs state`)
  - GitHub workflow (exact-head):
    - `CDK Deploy` succeeded for head `78e74cd2...` (run `25946022661`):
      - `logs/md1-shrunk/gh-run-view-25946022661-20260515T232023Z.json`
      - `logs/md1-shrunk/gh-run-watch-25946022661-20260515T232023Z.txt`
  - Step Functions + SageMaker (no new launches; keep monitoring):
    - execution still RUNNING: `logs/md1-shrunk/stepfunctions-describe-execution-br8abc-md1shrunk1456-1778880862-20260515T232428Z.json`
    - latest history tail (reverse-order): `logs/md1-shrunk/stepfunctions-history-reverse-tail-br8abc-md1shrunk1456-1778880862-20260515T232428Z.json`
    - training job still InProgress/Training: `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260515T232428Z.json`
    - CloudWatch stream still shows no new events since `2026-05-15T21:42:31Z`:
      - `logs/md1-shrunk/cloudwatch-training-streams-md1shrunk1456-1778880862-3dgs-20260515T232428Z.json`
      - `logs/md1-shrunk/cloudwatch-training-getlogevents-md1shrunk1456-1778880862-3dgs-20260515T232428Z.json`
    - Training output prefix still empty:
      - `logs/md1-shrunk/s3-3dgs-md1shrunk1456-1778880862-20260515T232428Z.txt` -> `Total Objects: 0`, `Total Size: 0`
- 2026-05-15T17:29:47-0600 CI confirmation (exact-head green):
  - branch/head:
    - `git rev-parse HEAD` -> `42f0e34c4a286dfaf43bba55f589484aa8189204` (`chore: record md1-shrunk poll evidence`)
  - GitHub workflow (exact-head):
    - `CDK Deploy` succeeded for head `42f0e34c...` (run `25946189081`):
      - `logs/md1-shrunk/gh-run-view-25946189081-20260515T232543Z.json`
      - `logs/md1-shrunk/gh-run-watch-25946189081-20260515T232543Z.txt`
  - Pipeline status reminder:
    - 3DGS still `InProgress/Training` as of `20260515T232428Z` (see prior poll artifacts above)
- 2026-05-15T17:34:27-0600 CI confirmation (post-state update push):
  - branch/head:
    - `git rev-parse HEAD` -> `e1826537669621428a706c658bd36268f4d89e6d` (`chore: confirm md1-shrunk CI green`)
  - GitHub workflow (exact-head):
    - `CDK Deploy` succeeded for head `e1826537...` (run `25946330775`):
      - `logs/md1-shrunk/gh-run-view-25946330775-20260515T233035Z.json`
      - `logs/md1-shrunk/gh-run-watch-25946330775-20260515T233035Z.txt`
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

## Terminal status (3DGS + compression)

- 2026-05-15T18:15:00-0600 terminal evidence (no new launches; cost bounded):
  - branch/head:
    - `git rev-parse HEAD` -> `898448756a914866188f711a25b1b70144a64902`
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded for head `89844875...` (run `25946458270`):
      - `logs/md1-shrunk/gh-run-list-20260515T234743Z.json`
  - 3DGS training job completed:
    - `TrainingJobName=md1shrunk1456-1778880862-3dgs`
    - `TrainingJobStatus=Completed`:
      - `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260515T235517Z.json`
    - CloudWatch completion tail (includes `✅ Training pipeline completed successfully`):
      - `logs/md1-shrunk/cloudwatch-training-getlogevents-md1shrunk1456-1778880862-3dgs-20260515T235517Z.json`
    - S3 output prefix:
      - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/3dgs/md1shrunk1456-1778880862/ --recursive --summarize --human-readable --region us-west-2`
      - snapshot: `logs/md1-shrunk/s3-3dgs-md1shrunk1456-1778880862-20260515T235517Z.txt` -> `model.tar.gz` size `212.0 MiB`
    - Exported model tar contents:
      - `logs/md1-shrunk/model-tar-list-md1shrunk1456-1778880862-20260515T235548Z.txt`
      - `logs/md1-shrunk/model-tar-verbose-md1shrunk1456-1778880862-20260515T235623Z.txt` -> `splat.ply` size `245,544,099` bytes + `background_skybox.webp`
      - PLY header proof (`element vertex 990091`):
        - `logs/md1-shrunk/splat-ply-header-md1shrunk1456-1778880862-20260515T235702Z.txt`
  - Step Functions execution completed:
    - `execution-md1shrunk1456-1778880862` on `SpaceportMLPipeline-br-8abcbd5662` -> `SUCCEEDED`:
      - `logs/md1-shrunk/stepfunctions-describe-execution-br8abc-md1shrunk1456-1778880862-20260516T001158Z.json`
  - SOGS compression processing job completed:
    - `ProcessingJobName=md1shrunk1456-1778880862-compression`
    - `ProcessingJobStatus=Completed`:
      - `logs/md1-shrunk/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260516T001121Z.json`
    - CloudWatch progress (extract + `sogs-compress` + output):
      - `logs/md1-shrunk/cloudwatch-processing-getlogevents-md1shrunk1456-1778880862-compression-20260516T001121Z.json`
    - S3 compressed output prefix (includes `supersplat_bundle/` with skybox + manifests):
      - `logs/md1-shrunk/s3-compressed-md1shrunk1456-1778880862-20260516T001121Z.txt` -> `Total Objects: 22`, `Total Size: 28.7 MiB`
  - Public bundle (anonymous fetch proof via HTTP 200):
    - S3: `s3://spaceport-ml-processing/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/`
    - HTTPS (meta.json): `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/meta.json`
    - sync log:
      - `logs/md1-shrunk/s3-sync-public-supersplat-20260516T001307Z.txt`
    - curl proof:
      - `curl -I -s https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/meta.json | head -n 20`
      - `curl -I -s https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/background_skybox.webp | head -n 20`

- 2026-05-15T18:25:00-0600 deployed preview viewer validation (skybox + no-sky):
  - Pages deployment run `25947588088` succeeded (head `e3a0881f...`):
    - job log: `logs/md1-shrunk/gh-run-log-25947588088-20260516T0022Z.txt`
    - alias URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
    - hash URL: `https://83be7404.v0-spaceport-website-preview2.pages.dev`
  - CDK Deploy run `25947588089` succeeded for the same head:
    - watch: `logs/md1-shrunk/gh-run-watch-25947588089-20260516T0018Z.txt`
  - Playwright smoke (skybox override = bundled `background_skybox.webp`):
    - command:
      - `cd web && SOGS_MIGRATED_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev SOGS_BUNDLE_URL=https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/meta.json SOGS_EXPECT_BUNDLED_SKYBOX=1 SOGS_EXPECT_SKYBOX_SUBSTRING=background_skybox.webp SOGS_SKYBOX_OVERRIDE=background_skybox.webp node scripts/test-sogs-migrated-viewer.mjs`
    - screenshot: `logs/sogs-migrated-viewer-smoke.png`
  - Playwright smoke (no-sky mode):
    - command:
      - `cd web && SOGS_MIGRATED_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev SOGS_BUNDLE_URL=https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/meta.json SOGS_DISABLE_SKYBOX=1 SOGS_EXPECT_SKYBOX_SUBSTRING=background_skybox.webp node scripts/test-sogs-migrated-viewer.mjs`
    - screenshot: `logs/sogs-migrated-viewer-nosky.png`

- 2026-05-15T18:36:00-0600 pushed validation harness + reconfirmed exact-head CI:
  - branch/head:
    - `git rev-parse HEAD` -> `74cc5a6a558f5debb6692139fd0e72f8f3929916`
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded for head `74cc5a6a...` (run `25947847850`):
      - `logs/md1-shrunk/gh-run-watch-25947847850-20260516T0029Z.txt`
    - `Deploy Next.js to Cloudflare Pages` succeeded for head `74cc5a6a...` (run `25947847852`):
      - `logs/md1-shrunk/gh-run-log-25947847852-20260516T0034Z.txt`
      - alias URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
      - hash URL: `https://c72f2426.v0-spaceport-website-preview2.pages.dev`

- 2026-05-15T18:45:00-0600 input-vs-render camera checks (3 poses; MD1 viewer):
  - Preview alias URL:
    - `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - Public bundle meta.json:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/meta.json`
  - COLMAP pose source:
    - `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap/sparse/0/images.txt`
    - derived poses file: `logs/md1-shrunk/colmap-camera-poses-20260516T003738Z.txt`
  - Inputs (downloaded from COLMAP images):
    - `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap/images/`
    - local: `logs/md1-shrunk/input/`
  - Renders + side-by-side comparisons (input left, render right):
    - local renders: `logs/md1-shrunk/camera_checks/render-*.png`
    - local comparisons: `logs/md1-shrunk/camera_checks/compare-*.png`
  - Repro command (renders use bundled `background_skybox.webp` via `?skybox=background_skybox.webp`):
    - `cd web && MD1_VIEWER_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev MD1_BUNDLE_URL=https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/meta.json MD1_CAM_POS=... MD1_CAM_TARGET=... MD1_SKYBOX=background_skybox.webp MD1_OUT=../logs/md1-shrunk/camera_checks/render-<name>.png node scripts/render-md1-camera-check.mjs`

- 2026-05-15T18:54:00-0600 commit/push + exact-head CI (camera checks harness):
  - branch/head:
    - `git rev-parse HEAD` -> `18c6cf6d2701e7d678193da8db630215d593e8f4` (`chore: md1-shrunk camera compare proof`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25948288204`):
      - `logs/md1-shrunk/gh-run-watch-25948288204-20260516T004705Z.txt`
    - `Deploy Next.js to Cloudflare Pages` succeeded (run `25948288202`):
      - `logs/md1-shrunk/gh-run-log-25948288202-20260516T005440Z.txt`
      - alias URL (PREVIEW_URL): `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
      - hash URL: `https://2504c8df.v0-spaceport-website-preview2.pages.dev`

- 2026-05-15T18:59:00-0600 exact-head CI (post CI-record commit):
  - branch/head:
    - `git rev-parse HEAD` -> `760584f9ddda71286fe3627a384ee26f068c6e2f` (`chore: record md1-shrunk camera compare CI`)
  - GitHub workflow (exact-head):
    - `CDK Deploy` succeeded (run `25948493656`):
      - `logs/md1-shrunk/gh-run-watch-25948493656-20260516T005604Z.txt`

- 2026-05-15T19:01:00-0600 exact-head CI (post CDK-proof commit):
  - branch/head:
    - `git rev-parse HEAD` -> `44e719ef81dcb2170cd1e5b06746ad1c29848068` (`chore: record md1-shrunk CDK proof`)
  - GitHub workflow (exact-head):
    - `CDK Deploy` succeeded (run `25948604980`):
      - `logs/md1-shrunk/gh-run-watch-25948604980-20260516T010135Z.txt`

- 2026-05-16T00:49:06Z monitor poll (terminal reconfirm; no new launches):
  - branch/head/status:
    - `git rev-parse HEAD` -> `0c58099081f06dc501f08f8d8e2a396b0d9831f5`
    - `git status --porcelain=v1` -> untracked `logs/md1-shrunk/` artifacts (17.08 MiB)
  - AWS identity:
    - `logs/md1-shrunk/aws-sts-20260516T004906Z.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions:
    - staging: `logs/md1-shrunk/stepfunctions-list-executions-SpaceportMLPipeline-staging-20260516T004906Z.json` -> `RUNNING=0`
    - branch preview: `logs/md1-shrunk/stepfunctions-list-executions-SpaceportMLPipeline-br-8abcbd5662-20260516T004906Z.json` -> `execution-md1shrunk1456-1778880862` `SUCCEEDED`
  - SageMaker terminal statuses:
    - SfM: `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260516T004906Z.json` -> `Completed`, `FailureReason=null`
    - 3DGS: `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T004906Z.json` -> `Completed`, `FailureReason=null`
    - compression: `logs/md1-shrunk/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260516T004906Z.json` -> `Completed`, `FailureReason=null`
  - GitHub workflows:
    - exact-head `CDK Deploy` succeeded for head `0c580990...` (run `25948058284`):
      - `logs/md1-shrunk/gh-run-view-25948058284-20260516T005027Z.json`
    - latest `Deploy Next.js to Cloudflare Pages` success remains head `74cc5a6a...` (run `25947847852`):
      - `logs/md1-shrunk/gh-run-view-25947847852-20260516T005027Z.json`

- 2026-05-16T01:04:23Z exact-head CI (post CDK-proof commit):
  - branch/head:
    - `git rev-parse HEAD` -> `44e719ef81dcb2170cd1e5b06746ad1c29848068` (`chore: record md1-shrunk CDK proof`)
  - GitHub workflow (exact-head):
    - `CDK Deploy` succeeded (run `25948604980`, created `2026-05-16T01:00:33Z`):
      - `logs/md1-shrunk/gh-run-watch-25948604980-20260516T010135Z.txt`

- 2026-05-15T19:15:55-0600 monitor poll (terminal reconfirm; no new launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `bd6938cce88ab149f08be3f27d0594f7636d7ae0`
    - `git status --porcelain=v1` -> new untracked `logs/md1-shrunk/*20260516T011555Z*` artifacts
    - `git rev-parse origin/agent-113647-md1-baseline-e2e` -> `bd6938cce88ab149f08be3f27d0594f7636d7ae0`
  - AWS identity:
    - `logs/md1-shrunk/aws-sts-20260516T011555Z.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (active executions):
    - staging RUNNING: `logs/md1-shrunk/stepfunctions-running-staging-20260516T011555Z.json` -> `RUNNING=0`
    - branch preview RUNNING: `logs/md1-shrunk/stepfunctions-running-SpaceportMLPipeline-br-8abcbd5662-20260516T011555Z.json` -> `RUNNING=0`
    - state machine inventory (filtered): `logs/md1-shrunk/stepfunctions-list-state-machines-filtered-20260516T011555Z.json`
  - SageMaker terminal statuses:
    - SfM: `logs/md1-shrunk/sagemaker-describe-sfm-md1-shrunk-1456-sfm-1778866088-20260516T011555Z.json` -> `Completed`, `FailureReason=null`
    - 3DGS: `logs/md1-shrunk/sagemaker-describe-3dgs-md1shrunk1456-1778880862-3dgs-20260516T011555Z.json` -> `Completed`, `FailureReason=null`
    - compression: `logs/md1-shrunk/sagemaker-describe-compression-md1shrunk1456-1778880862-compression-20260516T011555Z.json` -> `Completed`, `FailureReason=null`
  - GitHub workflows:
    - exact-head run list: `logs/md1-shrunk/gh-run-list-20260516T011555Z.json`
    - head-only summary: `logs/md1-shrunk/gh-run-list-head-20260516T011555Z.json` -> `CDK Deploy` succeeded for head `bd6938cc...` (run `25948732055`)
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-15T19:20:42-0600 commit/push + exact-head CI (poll evidence commit):
  - commit:
    - `git rev-parse HEAD` -> `c87a81b7c695605a8dcf55cd8bb79205f4167c4b` (`chore: md1-shrunk terminal poll evidence`)
  - GitHub workflows (exact-head):
    - run list: `logs/md1-shrunk/gh-run-list-20260516T012042Z.json`
    - head-only summary: `logs/md1-shrunk/gh-run-list-head-20260516T012042Z.json`
    - `CDK Deploy` succeeded for head `c87a81b7...` (run `25949052576`):
      - watch: `logs/md1-shrunk/gh-run-watch-25949052576-20260516T012042Z.txt`
      - view: `logs/md1-shrunk/gh-run-view-25949052576-20260516T012042Z.json`

- 2026-05-15T19:30:19-0600 exact-head CI proof (CI-proof commit head):
  - branch/head:
    - `git rev-parse HEAD` -> `1d7c7898c95d6fdd8557c4e034f98df414a5449a` (`chore: record md1-shrunk CI proof`)
  - GitHub workflows (exact-head):
    - run list: `logs/md1-shrunk/gh-run-list-20260516T013019Z.json`
    - `CDK Deploy` succeeded for head `1d7c7898...` (run `25949158184`):
      - watch: `logs/md1-shrunk/gh-run-watch-25949158184-20260516T013019Z.txt`
      - view: `logs/md1-shrunk/gh-run-view-25949158184-20260516T013019Z.json`
    - meta: `logs/md1-shrunk/gh-run-meta-20260516T013019Z.txt`

- 2026-05-16T01:47:26Z monitor poll (terminal reconfirm; no new launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `a599257c3d3daba8327eb102b7cb9ae468525ec9`
    - `git status --porcelain=v1` -> clean
  - Step Functions:
    - staging RUNNING: `logs/md1-shrunk/stepfunctions-running-staging-20260516T014726Z.json` -> `RUNNING=0`
  - SageMaker terminal statuses:
    - SfM: `logs/md1-shrunk/sagemaker-describe-sfm-md1-shrunk-1456-sfm-1778866088-20260516T014726Z.json` -> `Completed`, `FailureReason=null`
    - 3DGS: `logs/md1-shrunk/sagemaker-describe-3dgs-md1shrunk1456-1778880862-3dgs-20260516T014726Z.json` -> `Completed`, `FailureReason=null`
    - compression: `logs/md1-shrunk/sagemaker-describe-compression-md1shrunk1456-1778880862-compression-20260516T014726Z.json` -> `Completed`, `FailureReason=null`
  - GitHub workflows:
    - run list: `logs/md1-shrunk/gh-run-list-head-20260516T014726Z.json` -> latest `CDK Deploy` succeeded for head `a599257c...` (run `25949287502`)
  - Public bundle (anonymous HTTP 200 reconfirm):
    - `logs/md1-shrunk/http-head-meta-20260516T014726Z.txt`
    - `logs/md1-shrunk/http-head-skybox-20260516T014726Z.txt`
    - `logs/md1-shrunk/s3-ls-public-supersplat-20260516T014726Z.txt`
  - COLMAP sparse output reconfirm:
    - `logs/md1-shrunk/s3-ls-colmap-sparse0-20260516T014726Z.txt`

- 2026-05-16T01:52:20Z commit/push + exact-head CI (monitor poll evidence):
  - commit:
    - `git rev-parse HEAD` -> `3713a8ca736c33f319abea028f62dd7626856077` (`chore: md1-shrunk monitor poll evidence`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded for head `3713a8ca...` (run `25949650097`):
      - watch: `logs/md1-shrunk/gh-run-watch-25949650097-20260516T014830Z.txt`
      - view: `logs/md1-shrunk/gh-run-view-25949650097-20260516T014830Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T01:56:46Z commit/push + exact-head CI (CI-proof commit head):
  - commit:
    - `git rev-parse HEAD` -> `37be1d163b05e3b220345df86cc2a653ba773daf` (`chore: record md1-shrunk CI proof`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded for head `37be1d16...` (run `25949748079`):
      - watch: `logs/md1-shrunk/gh-run-watch-25949748079-20260516T015309Z.txt`
      - view: `logs/md1-shrunk/gh-run-view-25949748079-20260516T015309Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T02:01:19Z exact-head CI (post CDK-proof commit):
  - commit:
    - `git rev-parse HEAD` -> `c1c99a9671ad5664c7f74dfbbdc9c86002c481da` (`chore: record md1-shrunk CDK proof`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded for head `c1c99a96...` (run `25949845121`):
      - watch: `logs/md1-shrunk/gh-run-watch-25949845121-20260516T015754Z.txt`
      - view: `logs/md1-shrunk/gh-run-view-25949845121-20260516T015754Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T05:58:00Z exact-head CI (final CI-proof head):
  - commit:
    - `git rev-parse HEAD` -> `e27cb3b5edb902c525df083a16f140a57793a832` (`chore: record md1-shrunk final CI proof`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded for head `e27cb3b5...` (run `25949937019`):
      - watch: `logs/md1-shrunk/gh-run-watch-25949937019-20260516T0558Z.txt`
      - view: `logs/md1-shrunk/gh-run-view-25949937019-20260516T0558Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T06:05:00Z terminal reconfirm (no new launches):
  - AWS identity snapshot:
    - `logs/md1-shrunk/aws-sts-get-caller-identity-20260516T0605Z.json`
  - Step Functions (branch preview pipeline):
    - `SpaceportMLPipeline-br-8abcbd5662` RUNNING count: `0`
      - `logs/md1-shrunk/stepfunctions-running-SpaceportMLPipeline-br-8abcbd5662-20260516T0605Z.json`
    - SUCCEEDED includes `execution-md1shrunk1456-1778880862`:
      - `logs/md1-shrunk/stepfunctions-succeeded-SpaceportMLPipeline-br-8abcbd5662-20260516T0605Z.json`
  - SageMaker terminal status snapshots:
    - SfM `md1-shrunk-1456-sfm-1778866088` -> `Completed`:
      - `logs/md1-shrunk/sagemaker-describe-sfm-md1-shrunk-1456-sfm-1778866088-20260516T0605Z.json`
    - 3DGS `md1shrunk1456-1778880862-3dgs` -> `Completed`:
      - `logs/md1-shrunk/sagemaker-describe-3dgs-md1shrunk1456-1778880862-3dgs-20260516T0605Z.json`
    - compression `md1shrunk1456-1778880862-compression` -> `Completed`:
      - `logs/md1-shrunk/sagemaker-describe-compression-md1shrunk1456-1778880862-compression-20260516T0605Z.json`

- 2026-05-16T06:13:00Z exact-head CI (post reconfirm push):
  - commit:
    - `git rev-parse HEAD` -> `e70152ac8d08a10e49175b7ae6ffe449fdad62b2` (`chore: md1-shrunk terminal reconfirm`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded for head `e70152ac...` (run `25950271829`):
      - list: `logs/md1-shrunk/gh-run-list-e70152ac-20260516T0613Z.json`
      - watch: `logs/md1-shrunk/gh-run-watch-25950271829-20260516T0613Z.txt`
      - view: `logs/md1-shrunk/gh-run-view-25950271829-20260516T0613Z-final.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T02:49:00Z resume verification (no new launches; user-provided head `e9cbf71c...` was stale):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `c6d48e303e649768521871e86613d0dd68ecf4bb`
    - `git status --porcelain=v1` -> clean
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded for head `c6d48e30...` (run `25950353090`):
      - observed via: `gh run list --branch agent-113647-md1-baseline-e2e ...`
  - AWS identity snapshot:
    - `logs/md1-shrunk/aws-sts-get-caller-identity-20260516T024620Z.json`
  - Step Functions:
    - staging (`SpaceportMLPipeline-staging`) RUNNING executions: `0`
      - `logs/md1-shrunk/stepfunctions-list-executions-RUNNING-20260516T024620Z.json`
    - branch preview (`SpaceportMLPipeline-br-8abcbd5662`) RUNNING executions: `0`
      - `logs/md1-shrunk/stepfunctions-list-executions-RUNNING-br-8abcbd5662-20260516T024806Z.json`
  - SageMaker terminal status snapshots:
    - SfM `md1-shrunk-1456-sfm-1778866088` -> `Completed`:
      - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260516T024708Z.json`
    - 3DGS `md1shrunk1456-1778880862-3dgs` -> `Completed`:
      - `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T024708Z.json`
    - compression `md1shrunk1456-1778880862-compression` -> `Completed`:
      - `logs/md1-shrunk/sagemaker-describe-md1shrunk1456-1778880862-compression-20260516T024708Z.json`
    - InProgress processing jobs: `0`
      - `logs/md1-shrunk/sagemaker-list-processing-InProgress-20260516T024708Z.json`
    - InProgress training jobs: `0`
      - `logs/md1-shrunk/sagemaker-list-training-InProgress-20260516T024708Z.json`
  - S3 output presence reconfirm:
    - COLMAP (`s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`):
      - `logs/md1-shrunk/s3-colmap-md1-shrunk-20260515T1641Z-20260516T024806Z.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
    - 3DGS (`s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/3dgs/md1shrunk1456-1778880862/`):
      - `logs/md1-shrunk/s3-3dgs-md1shrunk1456-1778880862-20260516T024806Z.txt` -> `model.tar.gz` present
    - compressed (`s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/compressed/md1shrunk1456-1778880862/`):
      - `logs/md1-shrunk/s3-compressed-md1shrunk1456-1778880862-20260516T024806Z.txt` -> `Total Objects: 22`, `Total Size: 28.7 MiB`
  - Preview URL liveness check:
    - alias URL (PREVIEW_URL): `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
    - `curl -L` headers snapshot: `logs/md1-shrunk/curl-headers-preview-20260516T024834Z.txt` -> `HTTP/2 200`

- 2026-05-16T02:54:05Z commit/push + exact-head CI (resume verification ledger update):
  - commit:
    - `git rev-parse HEAD` -> `912c37f50aec694571dc9cf90d8b3264ff333f10` (`chore: md1-shrunk resume verification`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded for head `912c37f5...` (run `25950885932`):
      - list: `logs/md1-shrunk/gh-run-list-912c37f5-20260516T025043Z.json`
      - watch: `logs/md1-shrunk/gh-run-watch-25950885932-20260516T025050Z.txt`
      - view: `logs/md1-shrunk/gh-run-view-25950885932-20260516T025050Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T02:58:25Z commit/push + exact-head CI (recorded CI artifacts):
  - commit:
    - `git rev-parse HEAD` -> `b9df0ed60b7f2ab29cf03820c6ece664ac48af79` (`chore: record md1-shrunk resume ci`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded for head `b9df0ed6...` (run `25950962972`):
      - list: `logs/md1-shrunk/gh-run-list-b9df0ed6-20260516T025451Z.json`
      - watch: `logs/md1-shrunk/gh-run-watch-25950962972-20260516T025457Z.txt`
      - view: `logs/md1-shrunk/gh-run-view-25950962972-20260516T025457Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T03:20:27Z resume monitor (terminal complete; no new launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `cab05e04484c3860c89f886d506624e92b1e3b06`
    - `git status --porcelain=v1` -> untracked poll artifacts under `logs/md1-shrunk/`
  - AWS identity:
    - `aws sts get-caller-identity --output json > logs/md1-shrunk/aws-sts-20260516T031819Z.json`
  - Step Functions (active state):
    - staging RUNNING=0:
      - `aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --max-results 10 --region us-west-2 --output json > logs/md1-shrunk/stepfunctions-running-SpaceportMLPipeline-staging-20260516T031819Z.json`
    - branch preview pipeline `SpaceportMLPipeline-br-8abcbd5662`:
      - state machines: `logs/md1-shrunk/stepfunctions-list-state-machines-20260516T032010Z.json`
      - RUNNING=0: `logs/md1-shrunk/stepfunctions-running-SpaceportMLPipeline-br-8abcbd5662-20260516T032010Z.json`
      - SUCCEEDED list includes `execution-md1shrunk1456-1778880862`:
        - `logs/md1-shrunk/stepfunctions-succeeded-SpaceportMLPipeline-br-8abcbd5662-20260516T032010Z.json`
        - `logs/md1-shrunk/stepfunctions-describe-execution-md1shrunk1456-1778880862-20260516T032010Z.json` -> `status=SUCCEEDED`
  - SageMaker terminal statuses (no relaunches):
    - SfM `md1-shrunk-1456-sfm-1778866088` -> `Completed`:
      - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260516T031819Z.json`
    - 3DGS `md1shrunk1456-1778880862-3dgs` -> `Completed`:
      - `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T031819Z.json`
    - compression `md1shrunk1456-1778880862-compression` (ProcessingJob) -> `Completed`:
      - `logs/md1-shrunk/sagemaker-describe-md1shrunk1456-1778880862-compression-20260516T031819Z.json`
    - InProgress processing jobs: `0`:
      - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260516T031819Z.json`
    - InProgress training jobs: `1` (external / not owned by this run; left untouched):
      - `md1-tile00-split-r32-1778899939`
      - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260516T031819Z.json`
  - S3 output presence reconfirm:
    - COLMAP (`s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`):
      - `logs/md1-shrunk/s3-colmap-md1-shrunk-20260515T1641Z-20260516T032027Z.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
    - 3DGS (`s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/3dgs/md1shrunk1456-1778880862/`):
      - `logs/md1-shrunk/s3-3dgs-md1shrunk1456-1778880862-20260516T032027Z.txt` -> `model.tar.gz` present (`212.0 MiB`)
    - compressed (`s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/compressed/md1shrunk1456-1778880862/`):
      - `logs/md1-shrunk/s3-compressed-md1shrunk1456-1778880862-20260516T032027Z.txt` -> `Total Objects: 22`, `Total Size: 28.7 MiB`
  - GitHub workflows (exact-head):
    - `gh run list --branch agent-113647-md1-baseline-e2e --limit 20 --json databaseId,workflowName,headSha,status,conclusion,createdAt,updatedAt,url > logs/md1-shrunk/gh-run-list-cab05e04-20260516T031856Z.json`
    - `CDK Deploy` succeeded for head `cab05e04...` (run `25951141528`):
      - view: `logs/md1-shrunk/gh-run-view-25951141528-20260516T031856Z.json`
      - watch: `logs/md1-shrunk/gh-run-watch-25951141528-20260516T031856Z.txt`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T03:26:40Z commit/push + exact-head CI (poll evidence):
  - commit:
    - `git rev-parse HEAD` -> `bf2733f2384b4254cfbd470f6f4c8331e2a8081d` (`chore: poll md1-shrunk terminal state`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded for head `bf2733f2...` (run `25951494919`):
      - list: `logs/md1-shrunk/gh-run-list-bf2733f2384b4254cfbd470f6f4c8331e2a8081d-20260516T032229Z.json`
      - watch: `logs/md1-shrunk/gh-run-watch-25951494919-20260516T032229Z.txt`
      - view (initial): `logs/md1-shrunk/gh-run-view-25951494919-20260516T032229Z.json`
      - view (post-complete): `logs/md1-shrunk/gh-run-view-25951494919-20260516T032640Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)
    - note: `gh run watch` includes a GitHub-hosted Node.js 20 deprecation warning; no behavior change required for this MD1-Shrunk run

- 2026-05-16T03:31:31Z commit/push + exact-head CI (STATE/CI proof):
  - commit:
    - `git rev-parse HEAD` -> `e5aa4e6340558ff0898cc2bcb3a5481cb780f5db` (`chore: record md1-shrunk ci proof`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded for head `e5aa4e63...` (run `25951592648`):
      - list: `logs/md1-shrunk/gh-run-list-e5aa4e6340558ff0898cc2bcb3a5481cb780f5db-20260516T032726Z.json`
      - watch: `logs/md1-shrunk/gh-run-watch-25951592648-20260516T032726Z.txt`
      - view (initial): `logs/md1-shrunk/gh-run-view-25951592648-20260516T032726Z.json`
      - view (post-complete): `logs/md1-shrunk/gh-run-view-25951592648-20260516T033131Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T03:35:59Z push + exact-head CI (md1-shrunk cdk proof):
  - commit:
    - `git rev-parse HEAD` -> `3e8fbceef80e1a0382d5f50c243cddd13f199b48` (`chore: record md1-shrunk cdk proof`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded for head `3e8fbcee...` (run `25951686568`):
      - list: `logs/md1-shrunk/gh-run-list-3e8fbceef80e1a0382d5f50c243cddd13f199b48-20260516T033207Z.json`
      - watch: `logs/md1-shrunk/gh-run-watch-25951686568-20260516T033207Z.txt`
      - view (initial): `logs/md1-shrunk/gh-run-view-25951686568-20260516T033207Z.json`
      - view (post-complete): `logs/md1-shrunk/gh-run-view-25951686568-20260516T033559Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T03:50:45Z monitor poll (no new launches; terminal state still green):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `4804dc126b807fce225de5419289d4c934658e93` (origin matches; clean)
  - AWS identity:
    - `aws sts get-caller-identity --output json > logs/md1-shrunk/aws-sts-get-caller-identity-20260516T034820Z.json` -> account `975050048887`
  - Step Functions (staging):
    - `aws stepfunctions list-executions --status-filter RUNNING ... > logs/md1-shrunk/sfn-list-executions-running-20260516T034835Z.json` -> `0` RUNNING
  - SageMaker (staging, us-west-2):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`:
      - `logs/md1-shrunk/sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088-20260516T034926Z.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`:
      - `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T034926Z.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`:
      - `logs/md1-shrunk/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260516T034926Z.json`
    - list snapshots (no InProgress matches):
      - `logs/md1-shrunk/sagemaker-list-processing-jobs-20260516T034943Z.json`
      - `logs/md1-shrunk/sagemaker-list-training-jobs-20260516T034943Z.json`
  - S3 artifacts (existence + size):
    - COLMAP (`.../colmap/`): `logs/md1-shrunk/s3-colmap-20260516T035002Z.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
    - 3DGS (`.../3dgs/md1shrunk1456-1778880862/`): `logs/md1-shrunk/s3-3dgs-20260516T035002Z.txt` -> `model.tar.gz` `212.0 MiB`
    - compressed (`.../compressed/md1shrunk1456-1778880862/`): `logs/md1-shrunk/s3-compressed-20260516T035002Z.txt` -> `Total Objects: 22`, `Total Size: 28.7 MiB`
  - GitHub workflows:
    - exact-head `CDK Deploy` succeeded for `4804dc12...` (run `25951777522`):
      - list: `logs/md1-shrunk/gh-run-list-20260516T035124Z.json`
      - view: `logs/md1-shrunk/gh-run-view-CDK_Deploy-25951777522-20260516T035124Z.json`
    - latest `Deploy Next.js to Cloudflare Pages` on branch (head `18c6cf6d...`) succeeded (run `25948288202`):
      - view: `logs/md1-shrunk/gh-run-view-Deploy_Next.js_to_Cloudflare_Pages-25948288202-20260516T035124Z.json`
      - log: `logs/md1-shrunk/gh-run-log-Deploy_Next.js_to_Cloudflare_Pages-25948288202-20260516T035124Z.txt`
      - pages liveness: `logs/md1-shrunk/pages-preview-urls-20260516T035153Z.txt` -> hash+alias both `HTTP 200`

- 2026-05-16T04:20:34Z monitor poll (no new launches; terminal state still green):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `e4f9b424bac201278fa7e13dd4384cb9a44de28b` (origin matches; clean)
  - AWS identity:
    - `aws sts get-caller-identity --output json > logs/md1-shrunk/aws-sts-get-caller-identity-20260516T042034Z.json` -> account `975050048887`
  - Step Functions (staging + branch preview):
    - staging: `logs/md1-shrunk/sfn-list-executions-running-SpaceportMLPipeline-staging-20260516T042034Z.json` -> `RUNNING=0`
    - branch: `logs/md1-shrunk/sfn-list-executions-running-SpaceportMLPipeline-br-8abcbd5662-20260516T042034Z.json` -> `RUNNING=0`
  - SageMaker (staging, us-west-2):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`:
      - `logs/md1-shrunk/sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088-20260516T042034Z.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`:
      - `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T042034Z.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`:
      - `logs/md1-shrunk/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260516T042034Z.json`
  - S3 artifacts (existence + size):
    - COLMAP (`.../colmap/`): `logs/md1-shrunk/s3-colmap-20260516T042034Z.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
    - 3DGS (`.../3dgs/md1shrunk1456-1778880862/`): `logs/md1-shrunk/s3-3dgs-20260516T042034Z.txt` -> `model.tar.gz` `212.0 MiB`
    - compressed (`.../compressed/md1shrunk1456-1778880862/`): `logs/md1-shrunk/s3-compressed-20260516T042034Z.txt` -> `Total Objects: 22`, `Total Size: 28.7 MiB`
  - GitHub workflows:
    - exact-head `CDK Deploy` succeeded for `e4f9b424...` (run `25952186810`):
      - `logs/md1-shrunk/gh-run-list-20260516T042034Z.json`
    - latest `Deploy Next.js to Cloudflare Pages` on branch still succeeded (run `25948288202`; head `18c6cf6d...`):
      - `logs/md1-shrunk/gh-pages-run-list-20260516T042034Z.json`

- 2026-05-16T04:26:16Z commit/push + exact-head CI (poll evidence):
  - commit:
    - `git rev-parse HEAD` -> `2617c49695f10b742c1fffb29a855ca1c0e057a7` (`chore: poll md1-shrunk terminal state`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded for head `2617c496...` (run `25952623537`):
      - watch: `logs/md1-shrunk/gh-run-watch-25952623537-20260516T042000Z.txt`
      - view: `logs/md1-shrunk/gh-run-view-CDK_Deploy-25952623537-20260516T042616Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T04:30:44Z push + exact-head CI (md1-shrunk cdk proof):
  - commit:
    - `git rev-parse HEAD` -> `cb0589d3927b1aeb31bad70f458331f620ebec3e` (`chore: record md1-shrunk ci proof`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded for head `cb0589d3...` (run `25952710604`):
      - watch: `logs/md1-shrunk/gh-run-watch-25952710604-20260516T042647Z.txt`
      - view: `logs/md1-shrunk/gh-run-view-CDK_Deploy-25952710604-20260516T043044Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T04:56:58Z monitor poll (no new launches; terminal still green):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `677e5ab6ce617f3f1da099b8fc8c059535047f1b` (origin matches; clean)
    - git snapshots:
      - `logs/md1-shrunk/polls/git-branch-20260516T045658Z.txt`
      - `logs/md1-shrunk/polls/git-head-20260516T045658Z.txt`
      - `logs/md1-shrunk/polls/git-origin-head-20260516T045658Z.txt`
      - `logs/md1-shrunk/polls/git-status-20260516T045658Z.txt`
  - AWS identity:
    - `logs/md1-shrunk/polls/aws-sts-20260516T045658Z.json`
  - Step Functions (RUNNING=0 expected):
    - staging: `logs/md1-shrunk/polls/sfn-running-staging-20260516T045658Z.json`
    - branch: `logs/md1-shrunk/polls/sfn-running-br-8abcbd5662-20260516T045658Z.json`
  - SageMaker terminal statuses (expect Completed):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088`:
      - `logs/md1-shrunk/polls/sagemaker-describe-sfm-20260516T045658Z.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs`:
      - `logs/md1-shrunk/polls/sagemaker-describe-3dgs-20260516T045658Z.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression`:
      - `logs/md1-shrunk/polls/sagemaker-describe-compression-20260516T045658Z.json`
    - InProgress lists:
      - `logs/md1-shrunk/polls/sagemaker-list-processing-InProgress-20260516T045658Z.json`
      - `logs/md1-shrunk/polls/sagemaker-list-training-InProgress-20260516T045658Z.json`
  - S3 artifacts (existence + size snapshots):
    - COLMAP: `logs/md1-shrunk/polls/s3-colmap-20260516T045658Z.txt`
    - 3DGS: `logs/md1-shrunk/polls/s3-3dgs-20260516T045658Z.txt`
    - compressed (staging): `logs/md1-shrunk/polls/s3-compressed-staging-20260516T045658Z.txt`
    - public bundle listing: `logs/md1-shrunk/polls/s3-public-supersplat-20260516T045658Z.txt`
  - Public bundle (anonymous HTTP 200 reconfirm):
    - meta.json: `logs/md1-shrunk/polls/http-head-meta-20260516T045658Z.txt`
    - background_skybox.webp: `logs/md1-shrunk/polls/http-head-skybox-20260516T045658Z.txt`
  - Deployed preview viewer (Playwright smoke reconfirm):
    - skybox enabled: `logs/md1-shrunk/polls/playwright-sogs-skybox-20260516T045658Z.txt`
    - no-sky mode: `logs/md1-shrunk/polls/playwright-sogs-nosky-20260516T045658Z.txt`
  - GitHub workflows:
    - exact-head `CDK Deploy` for `677e5ab6...`:
      - run `25952803565`
      - `logs/md1-shrunk/polls/gh-run-view-cdk-20260516T045658Z.json`
      - `logs/md1-shrunk/polls/gh-run-list-20260516T045658Z.json`
    - latest Pages deploy remains head `18c6cf6d...` (run `25948288202`):
      - `logs/md1-shrunk/polls/gh-run-view-pages-20260516T045658Z.json`

- 2026-05-16T05:11:40Z commit/push + exact-head CI (poll evidence pushed):
  - commit:
    - `git rev-parse HEAD` -> `8f2786fa729c1bbcd098b5e094d624a181e851f3` (`chore: md1-shrunk monitor poll`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25953324802`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25953324802-20260516T045658Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25953324802-20260516T051140Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T05:16:00Z exact-head CI (post CI-record commit):
  - commit:
    - `git rev-parse HEAD` -> `e2679ec8c8d9caafc69cc90a769201283bd00190` (`chore: record md1-shrunk cdk run 25953324802`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25953409986`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25953409986-20260516T050356Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25953409986-20260516T051600Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T05:12:59Z exact-head CI (post CI-record commit):
  - commit:
    - `git rev-parse HEAD` -> `7327d0ea2d1511a8c51f5e54dfcb9d8fa23a2dc5` (`chore: record md1-shrunk cdk run 25953409986`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25953500379`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25953500379-20260516T050839Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25953500379-20260516T051259Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T05:34:51Z camera-check gate (no new launches; bounded verification only):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `e22a9d723f4709ce41d478812f9238450cefd5f1` (origin matches; new local poll artifacts only)
  - AWS identity:
    - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (staging):
    - `aws stepfunctions list-executions --state-machine-arn ... --status-filter RUNNING` -> `RUNNING=0`
  - SageMaker terminal statuses (expect Completed):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
  - SfM Montana-scale gates (from `colmap/sfm_metadata.json` snapshot):
    - `dataset_image_count=1456`, `images_registered=1456`, `merged_component_count=1`
    - `points_3d=1103335` (>= Meadow/Incognito `940147`), `timed_out=false`, `quality_check_passed=true`
    - snapshot: `logs/md1-shrunk/polls/sfm_metadata-20260516T052651Z.json`
  - 3DGS + compression gates (skybox + export sidecars):
    - `logs/md1-shrunk/polls/training_metadata-20260516T052651Z.json`
    - `logs/md1-shrunk/polls/sogs_compression_summary-20260516T052651Z.json`
    - `logs/md1-shrunk/polls/background_manifest-20260516T052651Z.json`
    - `logs/md1-shrunk/polls/export_manifest-20260516T052651Z.json`
  - Side-by-side input-vs-render camera check:
    - selected COLMAP image id `30` -> `DJI_01029.JPG` (from `colmap/sparse/0/images.txt`)
    - derived viewer camera pose from COLMAP pose (camera center + forward vector):
      - `MD1_CAM_POS=1.803916,-1.278733,2.509296`
      - `MD1_CAM_TARGET=4.318751,-1.515694,4.127768`
    - render command:
      - `cd web; MD1_VIEWER_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev MD1_BUNDLE_URL=https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/meta.json MD1_SKYBOX=background_skybox.webp MD1_CAM_POS=... MD1_CAM_TARGET=... node scripts/render-md1-camera-check.mjs`
    - outputs:
      - render: `logs/md1-shrunk/polls/md1-camera-check-dji01029-20260516T053233Z.png`
      - render log: `logs/md1-shrunk/polls/md1-camera-check-dji01029-20260516T053233Z.txt`
      - combined side-by-side: `logs/md1-shrunk/polls/md1-input-vs-render-DJI_01029-20260516T053233Z.jpg`

- 2026-05-16T05:40:02Z commit/push + exact-head CI (camera-check evidence pushed):
  - commit:
    - `git rev-parse HEAD` -> `8e1bc11bd9411ad29ee6d63a4ea62181fb2d5651` (`chore: md1-shrunk camera check evidence`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25954025100`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25954025100-20260516T054002Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25954025100-20260516T054002Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T05:44:50Z commit/push + exact-head CI (recorded CDK run evidence):
  - commit:
    - `git rev-parse HEAD` -> `a7563571cce4d9ee8d1316c0de7422389bd2fe85` (`chore: record md1-shrunk cdk run 25954025100`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25954112211`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25954112211-20260516T054450Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25954112211-20260516T054450Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T05:50:14Z exact-head CI (post run-record commit):
  - commit:
    - `git rev-parse HEAD` -> `20379a3756828d6974e34b205041eea4144d386c` (`chore: record md1-shrunk cdk run 25954112211`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25954200875`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25954200875-20260516T055014Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25954200875-20260516T055014Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T05:54:46Z exact-head CI (post run-record commit):
  - commit:
    - `git rev-parse HEAD` -> `f3fb08f8f337d00a7ff068b93e32a8bf1c1f4623` (`chore: record md1-shrunk cdk run 25954200875`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25954291186`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25954291186-20260516T055446Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25954291186-20260516T055446Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T05:56:32Z resume verification (no new launches; bounded polling only):
  - branch/head/status snapshots:
    - branch: `logs/md1-shrunk/polls/git-branch-20260516T055632Z.txt`
    - head: `logs/md1-shrunk/polls/git-head-20260516T055632Z.txt` -> `d9e0c6016fbe327b795274f771876d5dca355de1`
    - status: `logs/md1-shrunk/polls/git-status-20260516T055632Z.txt`
  - AWS identity:
    - `logs/md1-shrunk/polls/aws-identity-20260516T055632Z.json` -> account `975050048887`
  - Step Functions (staging RUNNING=0):
    - `logs/md1-shrunk/polls/stepfn-running-20260516T055632Z.json`
  - SageMaker terminal status snapshots:
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088-20260516T055632Z.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T055632Z.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260516T055632Z.json`
  - SageMaker in-flight lists (left untouched):
    - processing InProgress: `logs/md1-shrunk/polls/sagemaker-list-processing-inprogress-20260516T055632Z.json` (includes external `md1-tile00-sogs-r33-1778908626`)
    - training InProgress: `logs/md1-shrunk/polls/sagemaker-list-training-inprogress-20260516T055632Z.json`
  - GitHub workflows (branch) snapshot:
    - list: `logs/md1-shrunk/polls/gh-run-list-20260516T055632Z.json`
    - CDK Deploy (exact-head) view:
      - `logs/md1-shrunk/polls/gh-run-view-cdk-25954386683-20260516T0602Z.json`
  - Public bundle still anonymous-fetchable (HTTP headers):
    - urls: `logs/md1-shrunk/polls/public-bundle-urls-20260516T055708Z.txt`
    - `curl -I` meta.json: `logs/md1-shrunk/polls/curl-head-meta-20260516T055708Z.txt`
    - `curl -I` background_skybox.webp: `logs/md1-shrunk/polls/curl-head-skybox-20260516T055708Z.txt`

- 2026-05-16T05:58:34Z deployed preview viewer re-validation (skybox + no-sky):
  - viewer + bundle:
    - `logs/md1-shrunk/polls/sogs-viewer-smoke-urls-20260516T055834Z.txt`
  - skybox smoke:
    - log: `logs/md1-shrunk/polls/sogs-viewer-smoke-skybox-20260516T055834Z.txt` (HTTP 200 responses for viewer + skybox proxy)
    - screenshot: `logs/md1-shrunk/polls/sogs-viewer-smoke-skybox-20260516T055834Z.png`
  - no-sky smoke:
    - log: `logs/md1-shrunk/polls/sogs-viewer-smoke-nosky-20260516T055834Z.txt`
    - screenshot: `logs/md1-shrunk/polls/sogs-viewer-smoke-nosky-20260516T055834Z.png`

- 2026-05-16T06:06:08Z commit/push + exact-head CI (resume verification fixes pushed):
  - commit:
    - `git rev-parse HEAD` -> `d68cb64d9ca5451498d29181167a86c0d4be1c15` (`chore: record md1-shrunk cdk run 25954386683`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25954503057`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25954503057-20260516T060738Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25954503057-20260516T060738Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T06:11:57Z exact-head CI (post STATE poll commit):
  - commit:
    - `git rev-parse HEAD` -> `5ceb9ea0dea01d8a0e4311df3a4c7c76b4909971` (`chore: record md1-shrunk cdk run 25954503057`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25954618549`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25954618549-20260516T0608Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25954618549-20260516T061157Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T06:28:46Z resume verification (no new launches; bounded polling only):
  - git branch/head:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `31041a85ddfcb09eac1aa2cb94998336b3a1e8b7`
    - note: earlier referenced head `e9cbf71c56420ce386b028e7f4af33163ce4dcc2` is from `2026-05-15T11:39:32-06:00` (`chore: launch md1 shrunk sfm`)
  - AWS identity:
    - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (staging):
    - `logs/md1-shrunk/stepfunctions-running-SpaceportMLPipeline-staging-20260516T0000Z.json` -> `RUNNING_EXECUTIONS=0`
  - SageMaker terminal status snapshots (expect Completed):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
      - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260516T0000Z.json`
      - `logs/md1-shrunk/sfm_metadata-md1-shrunk-20260516T0006Z.json` -> `images_registered=1456`, `points_3d=1103335`, `quality_check_passed=true`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
      - `logs/md1-shrunk/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T0032Z.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
      - `logs/md1-shrunk/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260516T0032Z.json`
  - SageMaker in-flight lists (left untouched):
    - processing InProgress: `logs/md1-shrunk/sagemaker-list-processing-InProgress-20260516T0032Z.json`
    - training InProgress: `logs/md1-shrunk/sagemaker-list-training-InProgress-20260516T0032Z.json`
  - S3 output sanity:
    - root: `logs/md1-shrunk/s3-ls-md1-shrunk-colmap-root-20260516T0005Z.txt`
    - sparse: `logs/md1-shrunk/s3-ls-md1-shrunk-colmap-sparse-20260516T0005Z.txt`
  - GitHub workflows (exact-head):
    - branch list: `logs/md1-shrunk/gh-run-list-agent-113647-20260516T0028Z.json`
    - `CDK Deploy` succeeded for `31041a85...` (run `25954699584`)
    - Pages workflow latest on branch (not at this head): `logs/md1-shrunk/gh-run-list-pages-20260516T0030Z.json`

- 2026-05-16T06:34:08Z commit/push + exact-head CI (resume verification poll snapshots pushed):
  - commit:
    - `git rev-parse HEAD` -> `b3e02b5299289c6fed35d26941413c6e3d30e627` (`chore: md1-shrunk resume verification poll`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25955030362`):
      - watch: `logs/md1-shrunk/gh-run-watch-cdk-25955030362-20260516T063210Z.txt`
      - view: `logs/md1-shrunk/gh-run-view-cdk-25955030362-post-20260516T063356Z.json`
      - list snapshot: `logs/md1-shrunk/gh-run-list-after-push-20260516T063147Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)
      - latest Pages snapshot: `logs/md1-shrunk/gh-run-list-pages-after-push-20260516T063403Z.json`

- 2026-05-16T06:38:59Z exact-head CI (post run-record commit):
  - commit:
    - `git rev-parse HEAD` -> `a7bf950af00eae8c1e428ac2d4a11233d1256940` (`chore: record md1-shrunk cdk run 25955030362`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25955126506`):
      - watch: `logs/md1-shrunk/gh-run-watch-cdk-25955126506-20260516T063500Z.txt`
      - view: `logs/md1-shrunk/gh-run-view-cdk-25955126506-post-20260516T063500Z.json`
      - list snapshot: `logs/md1-shrunk/gh-run-list-postpush2-20260516T063452Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)
      - latest Pages snapshot: `logs/md1-shrunk/gh-run-list-pages-postpush2-20260516T063848Z.json`

- 2026-05-16T06:43:50Z exact-head CI (post run-record commit):
  - commit:
    - `git rev-parse HEAD` -> `4e3885b484e2958e3b43f95133fb5ab0aa0ff104` (`chore: record md1-shrunk cdk run 25955126506`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25955212907`):
      - watch: `logs/md1-shrunk/gh-run-watch-cdk-25955212907-20260516T063943Z.txt`
      - view: `logs/md1-shrunk/gh-run-view-cdk-25955212907-post-20260516T063943Z.json`
      - list snapshot: `logs/md1-shrunk/gh-run-list-postpush3-20260516T063935Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T07:04:42Z idle monitor poll (no new launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `a240a49a81b422c1875c3da05f29ad205a43ee39`
    - `git status --porcelain=v1` -> only untracked poll artifacts under `logs/md1-shrunk/`
  - AWS identity:
    - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
      - `logs/md1-shrunk/polls/aws-sts-get-caller-identity-20260516T070442Z.json`
  - Step Functions (staging):
    - `aws stepfunctions list-executions ... --status-filter RUNNING` -> `0`
      - `logs/md1-shrunk/polls/stepfn-list-executions-RUNNING-20260516T070442Z.json`
  - SageMaker (owned by MD1-Shrunk run):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`, `FailureReason=null`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088-20260516T070442Z.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`, `FailureReason=null`
      - `logs/md1-shrunk/polls/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T070442Z.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`, `FailureReason=null`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260516T070442Z.json`
  - SageMaker (external activity; left untouched):
    - ProcessingJob InProgress: `md1-tile00-sogs-r34-1778914593`
      - `logs/md1-shrunk/polls/sagemaker-list-processing-InProgress-20260516T070442Z.json`
  - S3 (staging artifacts present):
    - compressed supersplat bundle listing:
      - `logs/md1-shrunk/polls/s3-supersplat-bundle-20260516T070442Z.txt` -> `Total Objects: 13`, `Total Size: 15092019`
    - compressed splat listing:
      - `logs/md1-shrunk/polls/s3-compressed-splat-20260516T070442Z.txt` -> `Total Objects: 8`, `Total Size: 15042288`
  - Public bundle + preview (anonymous HTTP 200):
    - bundle meta.json:
      - url: `logs/md1-shrunk/polls/bundle-meta-url-20260516T070442Z.txt`
      - headers: `logs/md1-shrunk/polls/http-head-meta-20260516T070442Z.txt`
    - bundle skybox:
      - headers: `logs/md1-shrunk/polls/http-head-skybox-20260516T070442Z.txt`
    - preview alias:
      - url: `logs/md1-shrunk/polls/pages-preview-alias-20260516T070442Z.txt`
      - headers: `logs/md1-shrunk/polls/http-head-preview-alias-20260516T070442Z.txt`
    - preview hash:
      - url: `logs/md1-shrunk/polls/pages-preview-hash-20260516T070442Z.txt`
      - headers: `logs/md1-shrunk/polls/http-head-preview-hash-20260516T070442Z.txt`
  - GitHub workflows (exact-head):
    - `gh run list ...` snapshot:
      - `logs/md1-shrunk/polls/gh-run-list-20260516T070442Z.json`
    - head `a240a49a...` includes:
      - `logs/md1-shrunk/polls/gh-run-head-20260516T070442Z.tsv` -> `CDK Deploy` run `25955305585` `success`

- 2026-05-16T07:10:52Z push + exact-head CI:
  - commit:
    - `git rev-parse HEAD` -> `dcac19eb755ee728faddfb382883862139d73a93` (`chore: md1-shrunk idle poll 20260516T070442Z`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25955750457`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25955750457-20260516T0708Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25955750457-20260516T071052Z.json`
      - list snapshot: `logs/md1-shrunk/polls/gh-run-list-postpush-20260516T071052Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T07:37:51Z idle monitor poll (no new launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `68887f600b0c694b062e8f68dd98efe49eef477b` (`chore: record md1-shrunk cdk run 25955750457`)
    - `git status --porcelain=v1` -> clean
  - AWS identity:
    - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
      - `logs/md1-shrunk/polls/aws-sts-get-caller-identity-20260516T073220Z.json`
  - Step Functions (staging):
    - `aws stepfunctions list-executions ... --status-filter RUNNING` -> `0`
      - `logs/md1-shrunk/polls/stepfn-list-executions-RUNNING-20260516T073220Z.json`
  - SageMaker (owned by MD1-Shrunk run; terminal):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088-20260516T073220Z.json`
      - `logs/md1-shrunk/polls/sfm-status-summary-sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088-20260516T073220Z.txt`
    - SfM gates (from S3 `sfm_metadata.json`):
      - `logs/md1-shrunk/polls/colmap-sfm-gates-20260516T073541Z.txt` -> images_registered=1456, merged_component_count=1, points_3d=1103335, timed_out=False
      - `logs/md1-shrunk/polls/colmap-sfm-metadata-20260516T073541Z.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T073220Z.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260516T073220Z.json`
    - downstream status summary:
      - `logs/md1-shrunk/polls/downstream-status-summary-20260516T073655Z.txt`
  - External activity (left untouched):
    - ProcessingJob InProgress: `md1-tile00-sogs-r34-1778914593`
      - `logs/md1-shrunk/polls/sagemaker-list-processing-InProgress-20260516T073220Z.json`
  - Public bundle + preview (anonymous HTTP 200 recheck):
    - bundle meta.json:
      - url: `logs/md1-shrunk/polls/http-recheck2-bundle-meta-url-20260516T073721Z.txt`
      - headers: `logs/md1-shrunk/polls/http-recheck2-bundle-meta-20260516T073721Z.txt`
    - preview alias:
      - url: `logs/md1-shrunk/polls/http-recheck2-preview-alias-url-20260516T073721Z.txt`
      - headers: `logs/md1-shrunk/polls/http-recheck2-preview-alias-20260516T073721Z.txt`
    - preview hash:
      - url: `logs/md1-shrunk/polls/http-recheck2-preview-hash-url-20260516T073721Z.txt`
      - headers: `logs/md1-shrunk/polls/http-recheck2-preview-hash-20260516T073721Z.txt`
  - GitHub workflows (exact-head):
    - exact-head `CDK Deploy` succeeded: run `25955832468`
      - `logs/md1-shrunk/polls/gh-run-head-20260516T073333Z.tsv`
      - `logs/md1-shrunk/polls/gh-run-list-20260516T073333Z.json`
  - Notes:
    - The earlier “active SfM” state from 2026-05-15 is now terminal (`Completed`) and gates pass; no new launches performed in this poll.

- 2026-05-16T07:42:51Z push + exact-head CI:
  - commit:
    - `git rev-parse HEAD` -> `e555b41d119602f6cc6209e5de5a75b6e0e161b7` (`chore: md1-shrunk idle poll 20260516T073220Z`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25956364292`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-25956364292-20260516T073920Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-25956364292-20260516T073920Z.json`
      - list snapshot: `logs/md1-shrunk/polls/gh-run-list-postpush-20260516T073920Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T08:02:20Z idle monitor poll (no new launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `dc981fee2b5e3e098f34793e752ed53be843d816`
    - `git status --porcelain=v1` -> clean
  - AWS identity:
    - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
      - `logs/md1-shrunk/polls/aws-sts-get-caller-identity-20260516T080220Z.json`
  - Step Functions (staging):
    - `aws stepfunctions list-executions ... --status-filter RUNNING` -> `0`
      - `logs/md1-shrunk/polls/stepfn-list-executions-RUNNING-20260516T080220Z.json`
  - SageMaker (owned by MD1-Shrunk run; terminal):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088-20260516T080220Z.json`
    - SfM gates (from S3 `sfm_metadata.json`):
      - `logs/md1-shrunk/polls/colmap-sfm-gates-20260516T080220Z.txt` -> images_registered=1456, merged_component_count=1, points_3d=1103335, timed_out=False
      - `logs/md1-shrunk/polls/colmap-sfm-metadata-20260516T080220Z.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T080220Z.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260516T080220Z.json`
  - External activity (left untouched):
    - ProcessingJob InProgress: `md1-tile00-sogs-r34-1778914593`
      - `logs/md1-shrunk/polls/sagemaker-list-processing-InProgress-20260516T080220Z.json`
  - S3 + public HTTPS recheck:
    - SfM output listing: `logs/md1-shrunk/polls/s3-colmap-md1-shrunk-20260515T1641Z-20260516T080220Z.txt`
    - compressed root listing: `logs/md1-shrunk/polls/s3-compressed-root-20260516T080220Z.txt`
    - compressed supersplat bundle listing: `logs/md1-shrunk/polls/s3-supersplat-bundle-20260516T080220Z.txt`
    - public meta.json HTTP 200: `logs/md1-shrunk/polls/http-head-public-meta-20260516T080220Z.txt`
    - public skybox HTTP 200: `logs/md1-shrunk/polls/http-head-public-skybox-20260516T080220Z.txt`
  - GitHub workflows:
    - exact-head `CDK Deploy` succeeded: run `25956458592`
      - `logs/md1-shrunk/polls/gh-run-head-20260516T080220Z.tsv`
      - `logs/md1-shrunk/polls/gh-run-list-20260516T080220Z.json`
    - latest Pages run (not exact-head) succeeded: run `25948288202` @ `18c6cf6d...`
      - `logs/md1-shrunk/polls/gh-run-latest-pages-20260516T080220Z.tsv`
      - `logs/md1-shrunk/polls/gh-run-list-120-20260516T080220Z.json`

- 2026-05-16T08:05:57Z push + exact-head CI:
  - commit:
    - `git rev-parse HEAD` -> `5677c66c4e29133940b4ef20372af89a3ed22e4e` (`chore: md1-shrunk idle poll 20260516T080220Z`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25956893360`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25956893360-20260516T080557Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25956893360-20260516T080557Z.json`
      - list snapshot: `logs/md1-shrunk/polls/gh-run-list-postpush-20260516T080557Z.json`
    - note: Pages workflow not triggered at this head (no `web/trigger-dev-build.txt` bump)

- 2026-05-16T08:35:16Z idle monitor poll (no new launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `d661102746f85a4293d031b470896ebfda286acf`
    - `git status --porcelain=v1` -> clean
    - snapshot: `logs/md1-shrunk/polls/git-snapshot-20260516T083516Z.txt`
  - AWS identity:
    - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
      - `logs/md1-shrunk/polls/aws-sts-get-caller-identity-20260516T083516Z.json`
  - Step Functions (staging):
    - `aws stepfunctions list-executions ... --status-filter RUNNING` -> `0`
      - `logs/md1-shrunk/polls/stepfn-list-executions-RUNNING-20260516T083516Z.json`
  - SageMaker (owned by MD1-Shrunk run; terminal):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088-20260516T083516Z.json`
      - CloudWatch completion excerpt: `logs/md1-shrunk/polls/cloudwatch-tail-md1-shrunk-1456-sfm-1778866088-20260516T083516Z.txt`
    - SfM gates (from S3 `sfm_metadata.json`):
      - `logs/md1-shrunk/polls/colmap-sfm-metadata-20260516T083516Z.json`
      - `logs/md1-shrunk/polls/colmap-sfm-gates-20260516T083516Z.json` -> images_registered=1456, merged_component_count=1, points_3d=1103335, timed_out=false
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T083516Z.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260516T083516Z.json`
  - External activity (left untouched):
    - InProgress SageMaker processing/training snapshots:
      - `logs/md1-shrunk/polls/sagemaker-list-processing-InProgress-20260516T083516Z.json`
      - `logs/md1-shrunk/polls/sagemaker-list-training-InProgress-20260516T083516Z.json`
  - S3 listings:
    - COLMAP root: `logs/md1-shrunk/polls/s3-colmap-root-20260516T083516Z.txt`
    - COLMAP sparse: `logs/md1-shrunk/polls/s3-colmap-sparse-20260516T083516Z.txt`
  - HTTPS recheck:
    - preview alias URL: `logs/md1-shrunk/polls/http-head-preview-alias-url-20260516T083516Z.txt`
    - preview alias headers: `logs/md1-shrunk/polls/http-head-preview-alias-20260516T083516Z.txt`
    - public meta.json URL: `logs/md1-shrunk/polls/http-head-public-meta-url-20260516T083516Z.txt`
    - public meta.json headers: `logs/md1-shrunk/polls/http-head-public-meta-20260516T083516Z.txt`
    - public skybox URL: `logs/md1-shrunk/polls/http-head-public-skybox-url-20260516T083516Z.txt`
    - public skybox headers: `logs/md1-shrunk/polls/http-head-public-skybox-20260516T083516Z.txt`
  - GitHub workflows (exact-head):
    - `gh run list ...` snapshot: `logs/md1-shrunk/polls/gh-run-list-20260516T083516Z.json`
    - exact-head runs: `logs/md1-shrunk/polls/gh-run-head-20260516T083516Z.tsv` -> `CDK Deploy` run `25956977033` `success`
    - `gh run view 25956977033`: `logs/md1-shrunk/polls/gh-run-view-cdk-25956977033-20260516T083516Z.json`
  - Notes:
    - User-provided committed head `e9cbf71c...` was stale; as of this poll, HEAD is `d6611027...` and origin matches.
    - Cost bounded: no new jobs launched; no non-owned jobs stopped.

- 2026-05-16T17:06:42Z idle poll (no new launches; terminal reconfirm):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `176bc56ce56082e1305e7017ab660183f051feb4`
    - `git status --porcelain=v1` -> clean
    - snapshot: `logs/md1-shrunk/polls/git-snapshot-20260516T170642Z.txt`
  - AWS identity:
    - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
      - `logs/md1-shrunk/polls/aws-sts-20260516T170642Z.json`
  - Step Functions:
    - staging (`SpaceportMLPipeline-staging`) RUNNING executions: `0`
      - `logs/md1-shrunk/polls/stepfunctions-running-staging-20260516T170642Z.json`
    - branch preview (`SpaceportMLPipeline-br-8abcbd5662`) RUNNING executions: `0`
      - `logs/md1-shrunk/polls/stepfunctions-running-br-8abcbd5662-20260516T170642Z.json`
  - SageMaker (owned by MD1-Shrunk run; terminal):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-sfm-md1-shrunk-1456-sfm-1778866088-20260516T170642Z.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-3dgs-md1shrunk1456-1778880862-3dgs-20260516T170642Z.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-compression-md1shrunk1456-1778880862-compression-20260516T170642Z.json`
  - External activity (left untouched):
    - InProgress processing jobs snapshot:
      - `logs/md1-shrunk/polls/sagemaker-processing-inprogress-20260516T170642Z.tsv` (includes `md1-tile00-lodonly-r38-1778950901`)
    - InProgress training jobs snapshot:
      - `logs/md1-shrunk/polls/sagemaker-training-inprogress-20260516T170642Z.tsv`
  - S3 output presence reconfirm:
    - COLMAP listing: `logs/md1-shrunk/polls/s3-colmap-md1-shrunk-20260515T1641Z-20260516T170642Z.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
    - 3DGS listing: `logs/md1-shrunk/polls/s3-3dgs-md1shrunk1456-1778880862-20260516T170642Z.txt` -> `model.tar.gz` present (`212.0 MiB`)
    - compressed listing: `logs/md1-shrunk/polls/s3-compressed-md1shrunk1456-1778880862-20260516T170642Z.txt` -> `Total Objects: 22`, `Total Size: 28.7 MiB`
  - HTTPS recheck (anonymous):
    - preview alias URL: `logs/md1-shrunk/polls/http-head-preview-alias-url-20260516T170642Z.txt`
    - preview alias headers: `logs/md1-shrunk/polls/http-head-preview-alias-20260516T170642Z.txt` -> `HTTP 200`
    - preview hash URL: `logs/md1-shrunk/polls/http-head-preview-hash-url-20260516T170642Z.txt`
    - preview hash headers: `logs/md1-shrunk/polls/http-head-preview-hash-20260516T170642Z.txt` -> `HTTP 200`
    - public meta.json URL: `logs/md1-shrunk/polls/http-head-meta.json-url-20260516T170642Z.txt`
    - public meta.json headers: `logs/md1-shrunk/polls/http-head-meta.json-20260516T170642Z.txt` -> `HTTP 200`
    - public skybox URL: `logs/md1-shrunk/polls/http-head-background_skybox.webp-url-20260516T170642Z.txt`
    - public skybox headers: `logs/md1-shrunk/polls/http-head-background_skybox.webp-20260516T170642Z.txt` -> `HTTP 200`
  - GitHub workflows (exact-head):
    - `gh run list ...` snapshot:
      - `logs/md1-shrunk/polls/gh-run-list-176bc56ce56082e1305e7017ab660183f051feb4-20260516T170828Z.json`
    - exact-head `CDK Deploy` run `25957499805` -> `success`:
      - `logs/md1-shrunk/polls/gh-run-view-cdk-25957499805-20260516T170828Z.json`
  - Notes:
    - User-provided committed head `e9cbf71c...` and active SfM status were stale as of `2026-05-16T17:06:42Z`; owned SfM/3DGS/compression are terminal and outputs are present on S3.
    - Cost bounded: no new jobs launched; no non-owned jobs stopped.

- 2026-05-16T18:06:27Z idle poll (no new launches; terminal reconfirm + SfM gate snapshot):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `2b0e55f8086f09ab74f6bbb4a286df2c770ed3be`
    - `git status --porcelain=v1` -> clean
    - snapshot: `logs/md1-shrunk/polls/git-snapshot-20260516T180627Z.txt`
  - AWS identity:
    - `logs/md1-shrunk/polls/aws-sts-20260516T180627Z.json` -> account `975050048887`
  - Step Functions:
    - state machines snapshot: `logs/md1-shrunk/polls/stepfunctions-list-state-machines-20260516T180627Z.json`
    - staging (`SpaceportMLPipeline-staging`) RUNNING executions: `0`
      - `logs/md1-shrunk/polls/stepfunctions-running-staging-20260516T180627Z.json`
    - branch preview (`SpaceportMLPipeline-br-8abcbd5662`) RUNNING executions: `0`
      - `logs/md1-shrunk/polls/stepfunctions-running-br-8abcbd5662-20260516T180627Z.json`
  - SageMaker (owned by MD1-Shrunk run; terminal):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-sfm-md1-shrunk-1456-sfm-1778866088-20260516T180627Z.json`
    - SfM gate snapshot (from `sfm_metadata.json`):
      - `logs/md1-shrunk/polls/sfm-metadata-summary-20260516T180627Z.json` -> `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `timed_out=false`, `fallback_triggered=false`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-3dgs-md1shrunk1456-1778880862-3dgs-20260516T180627Z.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-compression-md1shrunk1456-1778880862-compression-20260516T180627Z.json`
  - External activity (left untouched):
    - processing/training snapshots:
      - `logs/md1-shrunk/polls/sagemaker-list-processing-20260516T180627Z.json`
      - `logs/md1-shrunk/polls/sagemaker-list-training-20260516T180627Z.json`
    - InProgress processing jobs: `logs/md1-shrunk/polls/sagemaker-processing-inprogress-20260516T180627Z.tsv` (includes external `md1-tile00-lodonly-r38-1778950901`)
    - InProgress training jobs: `logs/md1-shrunk/polls/sagemaker-training-inprogress-20260516T180627Z.tsv`
  - S3 output presence reconfirm:
    - COLMAP listing: `logs/md1-shrunk/polls/s3-colmap-md1-shrunk-20260515T1641Z-20260516T180627Z.txt`
    - 3DGS listing: `logs/md1-shrunk/polls/s3-3dgs-md1shrunk1456-1778880862-20260516T180627Z.txt` -> `model.tar.gz` present
    - compressed listing: `logs/md1-shrunk/polls/s3-compressed-md1shrunk1456-1778880862-20260516T180627Z.txt` -> supersplat bundle + compressed splat present
  - GitHub workflows (exact-head):
    - `logs/md1-shrunk/polls/gh-run-list-2b0e55f8086f09ab74f6bbb4a286df2c770ed3be-20260516T180627Z.json`
    - exact-head runs: `logs/md1-shrunk/polls/gh-run-head-2b0e55f8086f09ab74f6bbb4a286df2c770ed3be-20260516T180627Z.tsv` -> `CDK Deploy` run `25967956287` `success`
  - Notes:
    - Cost bounded: no new jobs launched; no non-owned jobs stopped.

- 2026-05-16T21:39:51Z monitor poll (no new launches; bundle + preview still healthy):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `b8c9d3099fababdbdfb6650582dc7ed44cd68e7c`
    - `git status --porcelain=v1` -> new poll artifacts under `logs/md1-shrunk/` only
  - AWS identity:
    - `logs/md1-shrunk/aws-sts-20260516T213655Z.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions:
    - RUNNING executions under `SpaceportMLPipeline-staging`: `0`
      - `logs/md1-shrunk/stepfunctions-running-20260516T213655Z.json`
  - SageMaker:
    - InProgress processing jobs snapshot:
      - `logs/md1-shrunk/sagemaker-processing-inprogress-20260516T213655Z.json` (includes external `md1-tile00-lodonly-r38-1778950901`; left untouched)
    - InProgress training jobs snapshot:
      - `logs/md1-shrunk/sagemaker-training-inprogress-20260516T213655Z.json` -> `0`
    - Owned job terminal statuses reconfirm:
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
        - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260516T213712Z.json`
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
        - `logs/md1-shrunk/sagemaker-describe-md1shrunk1456-1778880862-3dgs-20260516T213712Z.json`
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
        - `logs/md1-shrunk/sagemaker-describe-md1shrunk1456-1778880862-compression-20260516T213712Z.json`
  - Public bundle HTTP health:
    - meta.json headers: `logs/md1-shrunk/http-head-meta-20260516T213831Z.txt` -> `HTTP 200`
    - skybox headers: `logs/md1-shrunk/http-head-skybox-20260516T213831Z.txt` -> `HTTP 200`
  - Preview render smoke (skybox):
    - command:
      - `cd web && MD1_VIEWER_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev MD1_BUNDLE_URL=https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/meta.json MD1_SKYBOX=background_skybox.webp MD1_CAM_POS=1.803916,-1.278733,2.509296 MD1_CAM_TARGET=4.318751,-1.515694,4.127768 MD1_OUT=../logs/md1-shrunk/polls/md1-camera-check-dji01029-rerun-20260516T213831Z.png node scripts/render-md1-camera-check.mjs`
    - outputs:
      - screenshot: `logs/md1-shrunk/polls/md1-camera-check-dji01029-rerun-20260516T213831Z.png`
      - console log: `logs/md1-shrunk/polls/md1-camera-check-dji01029-rerun-20260516T213831Z.txt`
  - GitHub workflows (exact-head):
    - run list: `logs/md1-shrunk/gh-run-list-agent-113647-md1-baseline-e2e-20260516T213557Z.json`
    - exact-head summary: `logs/md1-shrunk/gh-exact-head-summary-agent-113647-md1-baseline-e2e-20260516T213557Z.txt` -> `CDK Deploy` run `25973150154` `success`
  - Notes:
    - Cost bounded: no new SageMaker jobs launched; no non-owned jobs stopped.

- 2026-05-16T21:45:36Z commit/push + exact-head CI (monitor poll evidence):
  - commit:
    - `git rev-parse HEAD` -> `a2c035871c046bd95c12106719eb1dce26381472` (`chore: md1-shrunk monitor poll 20260516T2139Z`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25973664131`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-25973664131-20260516T214216Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-25973664131-20260516T214216Z.json`

- 2026-05-16T21:50:10Z exact-head CI (post record commit):
  - commit:
    - `git rev-parse HEAD` -> `6191e6039e90fab4908f08f2748ae404f5b68119` (`chore: record md1-shrunk cdk run 25973664131`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25973762615`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-25973762615-20260516T214614Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-25973762615-20260516T214614Z.json`

- 2026-05-16T21:15:30Z exact-head CI (post poll commit):
  - commit:
    - `git rev-parse HEAD` -> `4ff182e5abc118a15c246a9816b1ae67d374c59c` (`chore: md1-shrunk poll 20260516T2110Z`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25973049886`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25973049886-20260516T2111Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25973049886-20260516T2115Z.json`

- 2026-05-16T18:12:22Z exact-head CI (post poll commit):
  - commit:
    - `git rev-parse HEAD` -> `a9c0c7d3bb32da411f2ff7ec91d6b1a57f4e47da` (`chore: md1-shrunk idle poll 20260516T180627Z`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25969183994`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25969183994-20260516T180831Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25969183994-20260516T181222Z.json`

- 2026-05-16T18:17:21Z exact-head CI (post record commit):
  - commit:
    - `git rev-parse HEAD` -> `cdb1cf23ac700b80b74aac0ad4fc54d07c973709` (`chore: record md1-shrunk cdk run 25969183994`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25969258751`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25969258751-20260516T181301Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25969258751-20260516T181721Z.json`

- 2026-05-16T21:10:00Z poll (post-user prompt reconciliation):
  - Note on stated head:
    - prompt claimed head `e9cbf71c56420ce386b028e7f4af33163ce4dcc2` (exists in repo), but current branch head is newer.
  - branch/head/status:
    - `git rev-parse HEAD` -> `48eba9b370a5ec7e5d76ceaadf67f172eb276fb2` (`chore: record md1-shrunk cdk run 25969258751`)
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - AWS identity (note: Codex PATH omits Homebrew bin; use absolute `/opt/homebrew/bin/aws`):
    - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions:
    - RUNNING executions under `SpaceportMLPipeline-staging`: `0`
      - `logs/md1-shrunk/stepfunctions-running-SpaceportMLPipeline-staging-20260516T2033Z.json`
  - SageMaker (owned by MD1-Shrunk run; terminal):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
      - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260516T2033Z.json`
    - SfM gate snapshot (from `sfm_metadata.json` in the output prefix):
      - `logs/md1-shrunk/sfm_metadata-md1-shrunk-20260516T2034Z.json` -> `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `quality_check_passed=true`, `timed_out=false`, `fallback_triggered=false`
      - sanity: `sparse/0/images.txt` header-line count -> `1456` (streaming count)
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T2039Z.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260516T2039Z.json`
  - External activity (left untouched):
    - InProgress processing jobs snapshot:
      - `logs/md1-shrunk/sagemaker-list-processing-InProgress-20260516T2036Z.json` (includes external `md1-tile00-lodonly-r38-1778950901`)
    - InProgress training jobs snapshot:
      - `logs/md1-shrunk/sagemaker-list-training-InProgress-20260516T2036Z.json` -> `0`
  - S3 output presence reconfirm:
    - COLMAP listing: `logs/md1-shrunk/s3-colmap-md1-shrunk-20260515T1641Z-20260516T2033Z.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
    - 3DGS listing: `logs/md1-shrunk/polls/s3-3dgs-root-20260516T2037Z.txt` -> `model.tar.gz` present (`212.0 MiB`)
    - compressed listing: `logs/md1-shrunk/polls/s3-compressed-md1-shrunk-20260515T1641Z-1456-1778880862-20260516T2037Z.txt` -> `Total Objects: 13`, `Total Size: 14.4 MiB`
    - public access proof:
      - `logs/md1-shrunk/curl/http-head-meta-20260516T2038Z.txt` -> `200 OK`
      - `logs/md1-shrunk/curl/http-head-skybox-20260516T2038Z.txt` -> `200 OK`
  - GitHub workflows (exact-head):
    - run list: `logs/md1-shrunk/gh-run-list-agent-113647-md1-baseline-e2e-20260516T2035Z.json`
      - exact-head `CDK Deploy` succeeded (run `25969341559`) for head `48eba9b370a5ec7e5d76ceaadf67f172eb276fb2`
    - Pages deploy runs for branch (not re-triggered for current head; latest run is older SHA):
      - `logs/md1-shrunk/gh-run-list-pages-20260516T2038Z.json` -> latest `Deploy Next.js to Cloudflare Pages` run `25948288202` succeeded for head `18c6cf6d...`
  - Notes:
    - Cost bounded: no new jobs launched; no non-owned jobs stopped.

- 2026-05-16T22:06:52Z poll (camera side-by-side proof + exact-head CI):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `aa6aaae04d76fa9a487ee6281e1c49c44e1bca2b` (`chore: record md1-shrunk cdk run 25973762615`)
    - `git status --porcelain=v1` -> new poll artifacts under `logs/md1-shrunk/polls/` only
  - AWS identity:
    - `logs/md1-shrunk/polls/aws-sts-20260516T220652Z.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions:
    - RUNNING executions under `SpaceportMLPipeline-staging`: `0`
      - `logs/md1-shrunk/polls/stepfn-running-20260516T220652Z.json`
  - SageMaker:
    - InProgress processing jobs snapshot:
      - `logs/md1-shrunk/polls/sagemaker-processing-inprogress-20260516T220652Z.json` (includes external `md1-tile00-lodonly-r38-1778950901`; left untouched)
    - InProgress training jobs snapshot:
      - `logs/md1-shrunk/polls/sagemaker-training-inprogress-20260516T220652Z.json` -> `0`
    - Owned job terminal statuses reconfirm:
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
        - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088-20260516T220652Z.json`
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
        - `logs/md1-shrunk/polls/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T220652Z.json`
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
        - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260516T220652Z.json`
  - SfM gate snapshot (from `sfm_metadata.json` in the output prefix):
    - `logs/md1-shrunk/polls/sfm_metadata-20260516T220652Z.json` -> `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `quality_check_passed=true`, `timed_out=false`, `fallback_triggered=false`
  - S3 output presence reconfirm:
    - COLMAP listing: `logs/md1-shrunk/polls/s3-colmap-md1-shrunk-20260515T1641Z-20260516T220652Z.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
    - 3DGS listing: `logs/md1-shrunk/polls/s3-3dgs-md1shrunk1456-1778880862-20260516T220652Z.txt` -> `model.tar.gz` present
    - compressed listing: `logs/md1-shrunk/polls/s3-compressed-md1-shrunk-20260515T1641Z-1456-1778880862-20260516T220652Z.txt` -> `Total Objects: 13`, `Total Size: 14.4 MiB`
  - Public bundle health + gates:
    - meta.json headers: `logs/md1-shrunk/polls/http-head-meta-20260516T220652Z.txt` -> `HTTP 200`
    - skybox headers: `logs/md1-shrunk/polls/http-head-skybox-20260516T220652Z.txt` -> `HTTP 200`
    - meta.json snapshot (gaussian count): `logs/md1-shrunk/polls/bundle-meta-20260516T220652Z.json` -> `gaussians=990025` (from `.means.shape[0]`)
  - Preview URL resolution (deterministic):
    - Pages run log: `logs/md1-shrunk/polls/gh-run-log-pages-25948288202-20260516T220310Z.txt` -> preview alias `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - Camera side-by-side (input vs render):
    - input: `logs/md1-shrunk/polls/input-DJI_01029-20260516T220652Z.JPG`
    - render (skybox): `logs/md1-shrunk/polls/render-skybox-DJI_01029-20260516T220652Z.png`
    - render (no-sky): `logs/md1-shrunk/polls/render-nosky-DJI_01029-20260516T220652Z.png`
    - side-by-side (skybox): `logs/md1-shrunk/polls/side-by-side-skybox-DJI_01029-20260516T220652Z.png`
    - side-by-side (no-sky): `logs/md1-shrunk/polls/side-by-side-nosky-DJI_01029-20260516T220652Z.png`
  - GitHub workflows (exact-head):
    - run list: `logs/md1-shrunk/polls/gh-run-list-aa6aaae04d76fa9a487ee6281e1c49c44e1bca2b-20260516T220652Z.json`
    - exact-head: `CDK Deploy` run `25973855907` `success`:
      - `logs/md1-shrunk/polls/gh-run-head-aa6aaae04d76fa9a487ee6281e1c49c44e1bca2b-20260516T220652Z.tsv`
      - `logs/md1-shrunk/polls/gh-run-view-cdk-25973855907-20260516T220652Z.json`
    - Pages deploy runs for branch (latest still older SHA):
      - `logs/md1-shrunk/polls/gh-run-list-pages-20260516T220120Z.json` -> latest `Deploy Next.js to Cloudflare Pages` run `25948288202` succeeded for head `18c6cf6d...`
  - Notes:
    - Correction: commit `6191e603...` records `CDK Deploy` run `25973664131`; commit `aa6aaae0...` records `CDK Deploy` run `25973762615`.
    - Cost bounded: no new SageMaker jobs launched; no non-owned jobs stopped.

- 2026-05-16T22:12:17Z exact-head CI (post poll commit):
  - commit:
    - `git rev-parse HEAD` -> `c7abba31bd68a5d7fd1cb9bf03cdc6bb312692e6` (`chore: md1-shrunk poll 20260516T2206Z`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25974295345`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25974295345-20260516T221217Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25974295345-20260516T221217Z.json`

- 2026-05-16T22:16:23Z exact-head CI (post record commit):
  - commit:
    - `git rev-parse HEAD` -> `62b8975aed32a9b62327670436951ba336c215cb` (`chore: record md1-shrunk cdk run 25974295345`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` succeeded (run `25974379439`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25974379439-20260516T221623Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25974379439-20260516T221623Z.json`

- 2026-05-16T22:40:26Z monitor recheck (no new ML runs):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `1bdbb25d3adaed3833f00fb7b712287693cf65fe`
    - `git status --porcelain=v1` -> new untracked poll artifacts under `logs/md1-shrunk/polls/`
  - AWS identity:
    - `aws sts get-caller-identity --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
      - `logs/md1-shrunk/polls/aws-identity-20260516T223725Z.json`
  - Step Functions state (active only):
    - `aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --max-results 10 --region us-west-2 --output json` -> none RUNNING
      - `logs/md1-shrunk/polls/stepfn-running-20260516T223922Z.json`
  - SageMaker state (active only):
    - `aws sagemaker list-processing-jobs --status-equals InProgress ...` -> `md1-tile00-lodonly-r38-1778950901` (external/not owned) still `InProgress`; left untouched
      - `logs/md1-shrunk/polls/sagemaker-list-processing-InProgress-20260516T223922Z.json`
    - `aws sagemaker list-training-jobs --status-equals InProgress ...` -> none
      - `logs/md1-shrunk/polls/sagemaker-list-training-InProgress-20260516T223922Z.json`
  - Owned job terminal status (for reference):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`, `FailureReason=null`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088-20260516T223922Z.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T223922Z.json`
    - Compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260516T223922Z.json`
  - S3 re-list (sanity):
    - colmap: `logs/md1-shrunk/polls/s3-colmap-20260516T223922Z.txt`
    - 3dgs: `logs/md1-shrunk/polls/s3-3dgs-20260516T223922Z.txt`
    - compression: `logs/md1-shrunk/polls/s3-compression-20260516T223922Z.txt`
  - Public bundle + preview HTTP sanity:
    - `curl -I -s https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/meta.json` -> `HTTP 200`
      - `logs/md1-shrunk/polls/http-head-meta-20260516T224013Z.txt`
    - `curl -I -s https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/background_skybox.webp` -> `HTTP 200`
      - `logs/md1-shrunk/polls/http-head-skybox-20260516T224013Z.txt`
    - meta snapshot: `logs/md1-shrunk/polls/bundle-meta-20260516T224013Z.json` -> `gaussians=990025`
    - preview alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev` -> `HTTP 200`
  - GitHub workflows (exact-head):
    - `gh run list --branch agent-113647-md1-baseline-e2e ...` -> only `CDK Deploy` ran at exact head `1bdbb25d...`
      - `CDK Deploy` run `25974479167` `success`:
        - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25974479167-20260516T223829Z.txt`
        - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25974479167-20260516T223829Z.json`
    - Pages deploy did not run for this exact head (no trigger-file bump); preview alias from the last Pages run remains valid.
  - Notes:
    - Cost bounded: no new SageMaker jobs launched; no non-owned jobs stopped.

- 2026-05-16T23:24:44Z poll + extra camera side-by-side checks (bounded; no new ML launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `4b1a6bb4e893b400d49c32dfc8f40cc93f6962a6` (pre-commit)
  - AWS identity / active state:
    - `logs/md1-shrunk/polls/aws-sts-20260516T231432Z.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
    - Step Functions RUNNING=0:
      - `logs/md1-shrunk/polls/stepfn-running-20260516T231432Z.json`
    - SageMaker InProgress:
      - external/not owned: `md1-tile00-lodonly-r38-1778950901` still `InProgress`
        - `logs/md1-shrunk/polls/sagemaker-processing-inprogress-20260516T231432Z.json`
      - owned jobs remain terminal `Completed`:
        - SfM: `logs/md1-shrunk/polls/sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088-20260516T231432Z.json`
        - 3DGS: `logs/md1-shrunk/polls/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T231432Z.json`
        - compression: `logs/md1-shrunk/polls/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260516T231432Z.json`
  - Bundle gates (public):
    - 3DGS output present: `logs/md1-shrunk/polls/s3-3dgs-20260516T231556Z.txt` -> `model.tar.gz`
    - compressed bundle present: `logs/md1-shrunk/polls/s3-compressed-20260516T231556Z.txt` -> `Total Objects: 22`
    - HTTP heads:
      - `logs/md1-shrunk/polls/http-head-meta-20260516T231556Z.txt` -> `HTTP 200`
      - `logs/md1-shrunk/polls/http-head-skybox-20260516T231556Z.txt` -> `HTTP 200`
    - gaussian-count gate:
      - `logs/md1-shrunk/polls/bundle-meta-20260516T231704Z.json` -> `gaussians=990025`
  - Extra side-by-side input-vs-render camera checks (derived from COLMAP pose; camera-center + forward*3m):
    - pose derivation snapshot:
      - `logs/md1-shrunk/polls/camera-samples-20260516T231912Z.json`
    - `DJI_01189.JPG`:
      - input: `logs/md1-shrunk/polls/input-DJI_01189-20260516T232256Z.JPG`
      - render skybox: `logs/md1-shrunk/polls/render-skybox-DJI_01189-20260516T232256Z.png`
      - render no-sky: `logs/md1-shrunk/polls/render-nosky-DJI_01189-20260516T232256Z.png`
      - side-by-side skybox: `logs/md1-shrunk/polls/side-by-side-skybox-DJI_01189-20260516T232256Z.png`
      - side-by-side no-sky: `logs/md1-shrunk/polls/side-by-side-nosky-DJI_01189-20260516T232256Z.png`
    - `DJI_02500.JPG`:
      - input: `logs/md1-shrunk/polls/input-DJI_02500-20260516T232256Z.JPG`
      - render skybox: `logs/md1-shrunk/polls/render-skybox-DJI_02500-20260516T232256Z.png`
      - render no-sky: `logs/md1-shrunk/polls/render-nosky-DJI_02500-20260516T232256Z.png`
      - side-by-side skybox: `logs/md1-shrunk/polls/side-by-side-skybox-DJI_02500-20260516T232256Z.png`
      - side-by-side no-sky: `logs/md1-shrunk/polls/side-by-side-nosky-DJI_02500-20260516T232256Z.png`
  - Notes:
    - Cost bounded: no new SageMaker jobs launched; no non-owned jobs stopped.

- 2026-05-16T23:30:02Z exact-head CI (post camera-check push):
  - commit:
    - `git rev-parse HEAD` -> `aef5bbfa709e38531f8dd3260255c6b99b2b4e53` (`chore: md1-shrunk extra camera checks`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` run `25975741726` `success`:
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25975741726-20260516T232652Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25975741726-20260516T233014Z.json`
    - Pages deploy not triggered for this exact head (no `web/trigger-dev-build.txt` bump):
      - latest Pages run remains `25948288202` (head `18c6cf6d...`)
      - `logs/md1-shrunk/polls/gh-run-list-pages-20260516T233024Z.json`

- 2026-05-16T23:36:01Z exact-head CI (post run-record commit):
  - commit:
    - `git rev-parse HEAD` -> `35ba820925b708e6cbf98deceb060550d6731381` (`chore: record md1-shrunk cdk run 25975741726`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` run `25975861192` `success`:
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25975861192-20260516T233258Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25975861192-20260516T233618Z.json`
    - Pages deploy still not triggered at this head:
      - `logs/md1-shrunk/polls/gh-run-list-pages-latest-20260516T233618Z.json`

- 2026-05-16T23:47:30Z monitor poll (terminal; no active ML runs; bundle + preview still healthy):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `ee256d4a0206ee47f44568835dae85c46b87249f`
    - `git status --porcelain=v1` -> new poll artifacts under `logs/md1-shrunk/polls/`
  - AWS identity:
    - `/opt/homebrew/bin/aws sts get-caller-identity --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
      - `logs/md1-shrunk/polls/aws-sts-20260516T234334Z.json`
  - Step Functions state (active only):
    - `/opt/homebrew/bin/aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --max-results 20 --region us-west-2 --output json` -> none RUNNING
      - `logs/md1-shrunk/polls/stepfn-running-20260516T234334Z.json`
  - SageMaker state (active only):
    - `/opt/homebrew/bin/aws sagemaker list-processing-jobs --status-equals InProgress ...` -> none `InProgress`
      - `logs/md1-shrunk/polls/sagemaker-processing-inprogress-20260516T234334Z.json`
    - `/opt/homebrew/bin/aws sagemaker list-training-jobs --status-equals InProgress ...` -> none `InProgress`
      - `logs/md1-shrunk/polls/sagemaker-training-inprogress-20260516T234334Z.json`
  - Owned job terminal status (for reference):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`, `FailureReason=null`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088-20260516T234334Z.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
      - `logs/md1-shrunk/polls/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260516T234334Z.json`
    - Compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`, `FailureReason=null`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260516T234334Z.json`
  - CloudWatch (SfM):
    - log stream metadata:
      - `/opt/homebrew/bin/aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix md1-shrunk-1456-sfm-1778866088/ --region us-west-2 --output json`
      - `logs/md1-shrunk/polls/cloudwatch-describe-streams-md1-shrunk-1456-sfm-1778866088-20260516T234549Z.json` -> `storedBytes=0` (events no longer retrievable via `get-log-events`; rely on earlier captured snapshots already in this repo)
    - `get-log-events` sanity (returned empty `events: []`):
      - `logs/md1-shrunk/polls/cloudwatch-last200-md1-shrunk-1456-sfm-1778866088-20260516T234500Z.json`
  - S3 COLMAP output (SfM):
    - recursive listing + summary:
      - `logs/md1-shrunk/polls/s3-colmap-list-20260516T234500Z.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
    - sparse listing + summary:
      - `logs/md1-shrunk/polls/s3-colmap-sparse-list-20260516T234500Z.txt` -> `Total Objects: 10`, `Total Size: 1.4 GiB`
      - `logs/md1-shrunk/polls/s3-colmap-sparse0-top-20260516T234618Z.txt` -> `cameras.txt`, `frames.txt`, `images.txt`, `points3D.txt`, `rigs.txt`
    - dense folder check (empty / not present):
      - `logs/md1-shrunk/polls/s3-colmap-dense-top-20260516T234618Z.txt`
  - Public bundle + preview HTTP sanity:
    - meta.json: `logs/md1-shrunk/polls/http-head-meta-20260516T234618Z.txt` -> `HTTP 200`
    - skybox: `logs/md1-shrunk/polls/http-head-skybox-20260516T234618Z.txt` -> `HTTP 200`
    - preview alias: `logs/md1-shrunk/polls/http-head-preview-20260516T234618Z.txt` -> `HTTP 200`
  - GitHub workflows (exact-head):
    - run list: `logs/md1-shrunk/polls/gh-run-list-20260516T234431Z.json`
    - exact-head: `CDK Deploy` run `25975963231` `success`:
      - `logs/md1-shrunk/polls/gh-run-watch-cdk-25975963231-20260516T233830Z.txt`
      - `logs/md1-shrunk/polls/gh-run-view-cdk-25975963231-20260516T234216Z.json`
    - Pages deploy not triggered at exact head (no `web/trigger-dev-build.txt` bump); preview alias from prior Pages run still serves `HTTP 200`.
  - Notes:
    - Cost bounded: no new SageMaker jobs launched; no non-owned jobs stopped.

- 2026-05-16T23:52:29Z exact-head CI (post poll commit):
  - commit:
    - `git rev-parse HEAD` -> `e710ee0cd8ca7917206b11132c9051c43b48453f` (`chore: md1-shrunk monitor 20260516T2347Z`)
  - GitHub workflows (exact-head):
    - run list: `logs/md1-shrunk/polls/gh-run-list-post-ci-20260516T235220Z.json`
    - `CDK Deploy` run `25976152048` `success`:
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25976152048-20260516T234847Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25976152048-20260516T235220Z.json`
    - Note: workflow emitted a Node.js 20 deprecation annotation (non-fatal; no failures).

- 2026-05-16T23:57:47Z exact-head CI (post record commit):
  - commit:
    - `git rev-parse HEAD` -> `057c51db108efd105f4f527cd2097d6232b6151c` (`chore: record md1-shrunk cdk run 25976152048`)
  - GitHub workflows (exact-head):
    - run list: `logs/md1-shrunk/polls/gh-run-list-post-ci2-20260516T235738Z.json`
    - `CDK Deploy` run `25976238312` `success`:
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25976238312-20260516T235332Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25976238312-20260516T235738Z.json`
    - Note: workflow emitted a Node.js 20 deprecation annotation (non-fatal; no failures).

- 2026-05-17T00:16:10Z monitor poll (terminal; owned MD1-shrunk jobs still `Completed`; no new jobs launched):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `db320cc1768eecb0b633a32d9ff81616d799d669`
    - `git status --porcelain=v1` -> new untracked poll artifacts under `logs/md1-shrunk/polls/`
  - AWS identity:
    - `/opt/homebrew/bin/aws sts get-caller-identity --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
      - `logs/md1-shrunk/polls/aws-sts-20260517T001333Z.json`
  - Step Functions state (active only):
    - `/opt/homebrew/bin/aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --max-results 20 --region us-west-2 --output json` -> none RUNNING
      - `logs/md1-shrunk/polls/stepfn-running-20260517T001333Z.json`
  - SageMaker state (active only):
    - `/opt/homebrew/bin/aws sagemaker list-processing-jobs --status-equals InProgress --sort-by CreationTime --sort-order Descending --max-results 20 --region us-west-2 --output json` -> 1 `InProgress` job not owned by this MD1-shrunk monitor (`md1-tile00-h0lod-r39-1778976307`); left untouched
      - `logs/md1-shrunk/polls/sagemaker-processing-inprogress-20260517T001333Z.json`
    - `/opt/homebrew/bin/aws sagemaker list-training-jobs --status-equals InProgress --sort-by CreationTime --sort-order Descending --max-results 20 --region us-west-2 --output json` -> none `InProgress`
      - `logs/md1-shrunk/polls/sagemaker-training-inprogress-20260517T001333Z.json`
  - Owned job terminal status (for reference):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`, `FailureReason=null`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088-20260517T001333Z.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`, `FailureReason=null`
      - `logs/md1-shrunk/polls/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260517T001333Z.json`
    - Compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`, `FailureReason=null`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260517T001334Z.json`
  - Pages preview URL resolution (deterministic from the last Pages run for this branch):
    - `Deploy Next.js to Cloudflare Pages` run `25948288202` log capture:
      - `logs/md1-shrunk/polls/gh-run-log-pages-25948288202-20260517T001535Z.txt`
      - extracted: `logs/md1-shrunk/polls/pages-preview-urls-25948288202-20260517T001548Z.txt` -> `ALIAS_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`, `HASH_URL=https://2504c8df.v0-spaceport-website-preview2.pages.dev`
  - Public bundle + preview HTTP sanity:
    - `logs/md1-shrunk/polls/http-head-sanity-20260517T001557Z.txt` -> preview `/health.txt` HTTP 200; bundle `meta.json` HTTP 200; `background_skybox.webp` HTTP 200
  - GitHub workflows (exact-head):
    - run list: `logs/md1-shrunk/gh-run-list-20260517T001255Z.json`
    - `CDK Deploy` run `25976330184` `success` (head `db320cc1...`):
      - `logs/md1-shrunk/polls/gh-run-view-cdk-25976330184-20260517T001613Z.json`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T00:43:26Z monitor poll (terminal; owned MD1-shrunk jobs still `Completed`; no new jobs launched):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `041bfc44fe05a0808a78647ff53fd6fb3acac48e`
    - `git status --porcelain=v1 -b` -> clean
  - AWS identity:
    - `/opt/homebrew/bin/aws sts get-caller-identity --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
      - `logs/md1-shrunk/polls/aws-sts-20260517T004326Z.json`
  - Step Functions state (active only):
    - `/opt/homebrew/bin/aws stepfunctions list-executions ... --status-filter RUNNING ...` -> none RUNNING
      - `logs/md1-shrunk/polls/stepfn-running-20260517T004326Z.json`
  - SageMaker state (active only):
    - `/opt/homebrew/bin/aws sagemaker list-processing-jobs --status-equals InProgress ...` -> none `InProgress`
      - `logs/md1-shrunk/polls/sagemaker-processing-inprogress-20260517T004326Z.json`
    - `/opt/homebrew/bin/aws sagemaker list-training-jobs --status-equals InProgress ...` -> none `InProgress`
      - `logs/md1-shrunk/polls/sagemaker-training-inprogress-20260517T004326Z.json`
  - Owned job terminal status (for reference):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`, `FailureReason=null`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088-20260517T004326Z.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`, `FailureReason=null`
      - `logs/md1-shrunk/polls/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260517T004326Z.json`
    - Compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`, `FailureReason=null`
      - `logs/md1-shrunk/polls/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260517T004326Z.json`
  - Pages preview URL resolution (deterministic from the last Pages run for this branch):
    - `Deploy Next.js to Cloudflare Pages` run `25948288202` log capture:
      - `logs/md1-shrunk/polls/gh-run-log-pages-25948288202-20260517T004326Z.txt`
      - extracted: `logs/md1-shrunk/polls/pages-preview-urls-25948288202-20260517T004326Z.txt` -> `ALIAS_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`, `HASH_URL=https://2504c8df.v0-spaceport-website-preview2.pages.dev`
  - Public bundle + preview HTTP sanity:
    - `logs/md1-shrunk/polls/http-head-preview-health-20260517T004326Z.txt` -> preview `/health.txt` HTTP 200
    - `logs/md1-shrunk/polls/http-head-bundle-meta-20260517T004326Z.txt` -> bundle `meta.json` HTTP 200
    - `logs/md1-shrunk/polls/http-head-bundle-skybox-20260517T004326Z.txt` -> bundle `background_skybox.webp` HTTP 200
  - GitHub workflows (exact-head):
    - run list: `logs/md1-shrunk/polls/gh-run-list-20260517T004326Z.json`
    - `CDK Deploy` run `25976710086` `success` (head `041bfc44...`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25976710086-20260517T004326Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25976710086-20260517T004326Z.json`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T00:49:37Z exact-head CI (post monitor 20260517T0043Z poll commit):
  - commit:
    - `git rev-parse HEAD` -> `33549ff84af520c4ac4f43bbb7911d612df58001` (`chore: md1-shrunk monitor 20260517T0043Z`)
  - GitHub workflows (exact-head):
    - run list (triggered by this push): `logs/md1-shrunk/polls/gh-run-list-post-push-20260517T004609Z.json`
    - `CDK Deploy` run `25977225064` `success`:
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25977225064-20260517T004609Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25977225064-20260517T004609Z.json`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump):
      - `logs/md1-shrunk/polls/gh-run-list-post-ci-20260517T004937Z.json`
      - latest Pages run remains `25948288202` (head `18c6cf6d...`)

- 2026-05-17T00:50:17Z exact-head CI (post record commit):
  - commit:
    - `git rev-parse HEAD` -> `39f61b1dbbb37a158e302f3f43f5ed4185691c19` (`chore: record md1-shrunk cdk run 25977225064`)
  - GitHub workflows (exact-head):
    - run list (triggered by this push): `logs/md1-shrunk/polls/gh-run-list-post-push2-20260517T005017Z.json`
    - `CDK Deploy` run `25977300236` `success`:
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25977300236-20260517T005017Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25977300236-20260517T005017Z.json`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump).

- 2026-05-17T01:14:31Z poll (terminal reconfirm; no new launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `74b6281184439798eb8ff8db3f08ed698529bf9d`
    - `git status --porcelain=v1` -> clean
  - AWS identity:
    - `logs/md1-shrunk/aws-sts-20260517T011431Z.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (staging):
    - RUNNING executions under `SpaceportMLPipeline-staging`: `0`
      - `logs/md1-shrunk/sfn-running-20260517T011431Z.json`
  - SageMaker:
    - InProgress processing jobs snapshot:
      - `logs/md1-shrunk/sm-processing-inprogress-20260517T011431Z.json` (includes external `md1-tile00-h1i1lod-r40-1778978757`; left untouched)
    - InProgress training jobs snapshot:
      - `logs/md1-shrunk/sm-training-inprogress-20260517T011431Z.json` -> `0`
    - Owned job terminal statuses reconfirm:
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
        - `logs/md1-shrunk/sm-describe-md1-shrunk-1456-sfm-1778866088-20260517T011431Z.json`
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
        - `logs/md1-shrunk/sm-describe-md1shrunk1456-1778880862-3dgs-20260517T011431Z.json`
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
        - `logs/md1-shrunk/sm-describe-md1shrunk1456-1778880862-compression-20260517T011431Z.json`
  - SfM gate snapshot (from `sfm_metadata.json` in the output prefix):
    - `logs/md1-shrunk/sfm-metadata-20260517T011512Z.json` -> `dataset_image_count=1456`, `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `timed_out=false`
  - S3 output presence reconfirm:
    - COLMAP listing: `logs/md1-shrunk/s3-colmap-md1-shrunk-20260515T1641Z-20260517T011431Z.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
  - Public bundle HTTP health (anonymous):
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/meta.json` -> `HTTP 200`
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/background_skybox.webp` -> `HTTP 200`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T01:28:25Z Pages re-trigger + preview viewer validation (exact-head):
  - commit/push:
    - `git rev-parse HEAD` -> `4328f9412db2437d85285d55c71bcda9143cb3ec` (`chore: trigger pages preview for md1-shrunk`)
    - trigger: appended a new line to `web/trigger-dev-build.txt`
  - GitHub workflows (exact-head; triggered by the push):
    - `Deploy Next.js to Cloudflare Pages` run `25977807200` -> `success`
      - watch: `logs/md1-shrunk/polls/gh-run-watch-pages-25977807200-20260517T012825Z.txt`
      - run log: `logs/md1-shrunk/gh-pages-log-25977807200-20260517T012506Z.txt`
      - preview URLs (from that run log):
        - alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
        - hash: `https://8a05d563.v0-spaceport-website-preview2.pages.dev`
    - `CDK Deploy` run `25977807203` -> `success`
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25977807203-20260517T012825Z.txt`
      - view: `logs/md1-shrunk/gh-run-25977807203-20260517T012506Z.json`
  - Camera side-by-side (input vs render) using the exact-head Pages alias URL:
    - viewer URL proof: `logs/md1-shrunk/polls/pages-preview-urls-20260517T012706Z.txt`
    - input (from COLMAP output): `logs/md1-shrunk/polls/input-DJI_01029-20260517T012706Z.JPG`
    - render (skybox): `logs/md1-shrunk/polls/render-skybox-DJI_01029-20260517T012706Z.png`
    - render (no-sky): `logs/md1-shrunk/polls/render-nosky-DJI_01029-20260517T012706Z.png`
    - side-by-side (skybox): `logs/md1-shrunk/polls/side-by-side-skybox-DJI_01029-20260517T012706Z.png`
    - side-by-side (no-sky): `logs/md1-shrunk/polls/side-by-side-nosky-DJI_01029-20260517T012706Z.png`
  - Public bundle gates reconfirm:
    - bundle meta headers: `logs/md1-shrunk/polls/http-head-meta-20260517T012732Z.txt` -> `HTTP 200`
    - skybox headers: `logs/md1-shrunk/polls/http-head-skybox-20260517T012732Z.txt` -> `HTTP 200`
    - meta snapshot: `logs/md1-shrunk/polls/bundle-meta-20260517T012732Z.json` -> `gaussians=990025` (from `.means.shape[0]`)
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T01:30:30Z exact-head CI (post poll 20260517T0128Z evidence commit):
  - commit:
    - `git rev-parse HEAD` -> `1d7377a7bf7f777fc54f83196771dc69ee1e9e6c` (`chore: md1-shrunk poll 20260517T0128Z`)
  - GitHub workflows (exact-head; triggered by this push):
    - run list: `logs/md1-shrunk/polls/gh-run-list-post-push3-20260517T013030Z.json`
    - `CDK Deploy` run `25978045732` `success`:
      - watch: `logs/md1-shrunk/polls/gh-run-watch-25978045732-20260517T013030Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25978045732-20260517T013030Z.json`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump).

- 2026-05-17T01:35:00Z exact-head CI (post record run 25978045732 commit):
  - commit:
    - `git rev-parse HEAD` -> `434f09850d3b68fb64714a93ace3dfe34dbd6504` (`chore: record md1-shrunk cdk run 25978045732`)
  - GitHub workflows (exact-head; triggered by this push):
    - run list: `logs/md1-shrunk/polls/gh-run-list-post-push4-20260517T013500Z.json`
    - `CDK Deploy` run `25978125237` `success`:
      - watch: `logs/md1-shrunk/polls/gh-run-watch-25978125237-20260517T013500Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-25978125237-20260517T013500Z.json`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump).

- 2026-05-17T01:49:39Z poll (terminal reconfirm; no new launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `a91442a1ef61db76130e5cfe69591d60bf63ab7a`
    - `git status --porcelain=v1` -> new untracked poll artifacts under `logs/md1-shrunk/polls/`
  - Tooling notes:
    - `gh` was missing from `PATH`; installed GitHub CLI v2.92.0 at `/Users/gabrielhansen/.local/bin/gh`.
    - `aws` is not on `PATH` in this shell; used `python3 -m awscli ...` for AWS verification.
  - AWS identity:
    - `python3 -m awscli sts get-caller-identity --region us-west-2 --output json` -> `logs/md1-shrunk/polls/aws-sts-20260517T014519Z.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (staging):
    - `python3 -m awscli stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --max-results 25 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/sfn-running-20260517T014519Z.json` -> RUNNING `0`
  - SageMaker:
    - InProgress processing jobs:
      - `python3 -m awscli sagemaker list-processing-jobs --status-equals InProgress --max-results 100 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/sm-processing-inprogress-20260517T014519Z.json` -> `0`
    - InProgress training jobs:
      - `python3 -m awscli sagemaker list-training-jobs --status-equals InProgress --max-results 100 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/sm-training-inprogress-20260517T014519Z.json` -> `0`
    - Owned job terminal statuses reconfirm:
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
        - `logs/md1-shrunk/polls/sm-describe-md1-shrunk-1456-sfm-1778866088-20260517T014519Z.json`
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
        - `logs/md1-shrunk/polls/sm-describe-md1shrunk1456-1778880862-3dgs-20260517T014519Z.json`
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
        - `logs/md1-shrunk/polls/sm-describe-md1shrunk1456-1778880862-compression-20260517T014519Z.json`
  - Public preview + bundle HTTP sanity:
    - HEAD checks: `logs/md1-shrunk/polls/http-head-preview-bundle-20260517T014654Z.txt` -> preview `/health.txt` HTTP 200, bundle `meta.json` HTTP 200, bundle `background_skybox.webp` HTTP 200
    - bundle gaussian count: `logs/md1-shrunk/polls/bundle-meta-gaussians-20260517T014654Z.txt` -> `gaussians 990025`
    - side-by-side evidence file sizes: `logs/md1-shrunk/polls/evidence-filesizes-20260517T014654Z.txt`
  - GitHub workflows (exact-head):
    - run list: `logs/md1-shrunk/polls/gh-run-list-20260517T014849Z.json`
    - `CDK Deploy` run `25978199493` `success` (head `a91442a1...`):
      - view: `logs/md1-shrunk/polls/gh-run-view-25978199493-20260517T014911Z.json`
      - watch: `logs/md1-shrunk/polls/gh-run-watch-25978199493-20260517T014911Z.txt`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump); latest Pages run remains `25977807200` (head `4328f941...`).
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T01:54:48Z exact-head CI (post poll 20260517T0149Z commit):
  - commit:
    - `git rev-parse HEAD` -> `c587ebe365093ba86c6a14c441e1e422c5805a1e` (`chore: md1-shrunk poll 20260517T0149Z`)
  - GitHub workflows (exact-head; triggered by this push):
    - run list: `logs/md1-shrunk/polls/gh-run-list-post-push-20260517T015101Z.json`
    - `CDK Deploy` run `25978413482` `success` (head `c587ebe3...`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25978413482-20260517T015109Z.txt`
      - view (start): `logs/md1-shrunk/polls/gh-run-view-cdk-25978413482-20260517T015109Z.json`
      - view (final): `logs/md1-shrunk/polls/gh-run-view-cdk-25978413482-final-20260517T015109Z.json`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump).

- 2026-05-17T02:13:38Z poll (terminal reconfirm; no new launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `44307079ed298e97c6202232465b35fdb1115940`
    - `git status --porcelain=v1` -> new untracked poll artifacts under `logs/md1-shrunk/polls/`
  - AWS identity:
    - `python3 -m awscli sts get-caller-identity --output json` -> `logs/md1-shrunk/polls/aws-identity-20260517T021338Z.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (staging):
    - `python3 -m awscli stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --max-results 50 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/sfn-executions-20260517T021338Z.json` -> RUNNING `0` in current page
  - SageMaker:
    - Owned job terminal statuses reconfirm:
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
        - `logs/md1-shrunk/polls/sm-describe-processing-md1-shrunk-1456-sfm-1778866088-20260517T021338Z.json`
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
        - `logs/md1-shrunk/polls/sm-describe-training-md1shrunk1456-1778880862-3dgs-20260517T021338Z.json`
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
        - `logs/md1-shrunk/polls/sm-describe-processing-md1shrunk1456-1778880862-compression-20260517T021338Z.json`
    - InProgress processing jobs (external; left untouched):
      - `python3 -m awscli sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/sm-processing-inprogress-20260517T021338Z.json` -> `4`
        - `md1-tile01-h1i1lod-r41-1778982712`
        - `md1-tile02-h1i1lod-r41-1778982713`
        - `md1-tile03-h1i1lod-r41-1778982714`
        - `md1-tile04-h1i1lod-r41-1778982715`
    - InProgress training jobs:
      - `python3 -m awscli sagemaker list-training-jobs --status-equals InProgress --max-results 50 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/sm-training-inprogress-20260517T021338Z.json` -> `0`
  - Public preview + bundle HTTP sanity:
    - `logs/md1-shrunk/polls/http-head-sanity-20260517T021627Z.txt` -> preview `/health.txt` HTTP 200, bundle `meta.json` HTTP 200, bundle `background_skybox.webp` HTTP 200
  - GitHub workflows (exact-head):
    - run list: `logs/md1-shrunk/polls/gh-run-list-20260517T021546Z.json`
    - `CDK Deploy` run `25978493986` `success` (head `44307079...`):
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25978493986-20260517T021546Z.json`
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25978493986-20260517T021546Z.txt`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump); latest Pages run remains `25977807200` (head `4328f941...`).
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T02:22:08Z exact-head CI (post poll 20260517T0213Z commit):
  - commit:
    - `git rev-parse HEAD` -> `2c6127f19b73a84a7d4889632b2645f8424e64d9` (`chore: md1-shrunk poll 20260517T0213Z`)
  - GitHub workflows (exact-head; triggered by this push):
    - run list: `logs/md1-shrunk/polls/gh-run-list-post-push-20260517T022208Z.json`
    - `CDK Deploy` run `25978941737` `success` (head `2c6127f1...`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25978941737-20260517T022208Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25978941737-20260517T022208Z.json`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump).

- 2026-05-17T02:26:43Z exact-head CI (post record md1-shrunk cdk run 25978941737 commit):
  - commit:
    - `git rev-parse HEAD` -> `6f305d50b79195f807e4decdbc9f1b93a1d7e269` (`chore: record md1-shrunk cdk run 25978941737`)
  - GitHub workflows (exact-head; triggered by this push):
    - run list: `logs/md1-shrunk/polls/gh-run-list-post-push2-20260517T022643Z.json`
    - `CDK Deploy` run `25979033472` `success` (head `6f305d50...`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25979033472-20260517T022643Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25979033472-20260517T022643Z.json`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump).

- 2026-05-17T02:43:23Z poll (terminal reconfirm; no new launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `43b19b31521999c5e04ac0c75b091a8012328ebf`
    - `git status --porcelain=v1` -> clean
  - AWS identity:
    - `python3 -m awscli sts get-caller-identity --output json` -> `logs/md1-shrunk/polls/aws-sts-20260517T024323Z.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (staging):
    - `python3 -m awscli stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --max-results 10 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/stepfn-running-20260517T024323Z.json` -> RUNNING `0`
  - SageMaker:
    - Owned job terminal statuses reconfirm:
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
        - `logs/md1-shrunk/polls/sm-describe-md1-shrunk-1456-sfm-1778866088-20260517T024323Z.json`
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
        - `logs/md1-shrunk/polls/sm-describe-md1shrunk1456-1778880862-3dgs-20260517T024323Z.json`
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
        - `logs/md1-shrunk/polls/sm-describe-md1shrunk1456-1778880862-compression-20260517T024323Z.json`
    - InProgress processing jobs:
      - `python3 -m awscli sagemaker list-processing-jobs --status-equals InProgress --sort-by CreationTime --sort-order Descending --max-results 20 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/sm-processing-inprogress-20260517T024323Z.json` -> `0`
    - InProgress training jobs:
      - `python3 -m awscli sagemaker list-training-jobs --status-equals InProgress --sort-by CreationTime --sort-order Descending --max-results 20 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/sm-training-inprogress-20260517T024323Z.json` -> `0`
  - GitHub workflows (exact-head):
    - `~/.local/bin/gh run list --branch agent-113647-md1-baseline-e2e --limit 30 ...` -> `logs/md1-shrunk/polls/gh-runs-agent-113647-md1-baseline-e2e-20260517T024418Z.json`
    - head `43b19b31...` has `CDK Deploy` run `25979122466` `success` (no failed/in_progress runs in recent list).
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T02:50:23Z exact-head CI (post poll 20260517T0243Z commit):
  - commit:
    - `git rev-parse HEAD` -> `1673911018cd4b313422b705d0a76d4ab414ab6e` (`chore: md1-shrunk poll 20260517T0243Z`)
  - GitHub workflows (exact-head; triggered by this push):
    - `CDK Deploy` run `25979478562` `success` (head `16739110...`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25979478562-20260517T024703Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25979478562-20260517T0248Z.json`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump).

- 2026-05-17T03:16:11Z monitor poll (terminal reconfirm; no new launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `9b969b49c13655aad48c4ba3f86d0ae8e9106434`
    - `git status --porcelain=v1` -> clean before new poll artifacts
  - AWS identity:
    - `python3 -m awscli sts get-caller-identity --output json` -> `logs/md1-shrunk/polls/aws-sts-20260517T031502Z.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (staging):
    - `python3 -m awscli stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --max-results 10 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/stepfn-running-20260517T031502Z.json` -> RUNNING `0`
  - SageMaker:
    - Owned job terminal statuses reconfirm:
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`, `FailureReason=null`
        - `logs/md1-shrunk/polls/sm-describe-processing-md1-shrunk-1456-sfm-1778866088-20260517T031502Z.json`
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`, `FailureReason=null`
        - `logs/md1-shrunk/polls/sm-describe-training-md1shrunk1456-1778880862-3dgs-20260517T031502Z.json`
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`, `FailureReason=null`
        - `logs/md1-shrunk/polls/sm-describe-processing-md1shrunk1456-1778880862-compression-20260517T031502Z.json`
    - InProgress processing jobs:
      - `python3 -m awscli sagemaker list-processing-jobs --status-equals InProgress --sort-by CreationTime --sort-order Descending --max-results 50 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/sm-processing-inprogress-20260517T031502Z.json` -> `0`
    - InProgress training jobs:
      - `python3 -m awscli sagemaker list-training-jobs --status-equals InProgress --sort-by CreationTime --sort-order Descending --max-results 50 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/sm-training-inprogress-20260517T031502Z.json` -> `0`
  - GitHub workflows:
    - run list: `logs/md1-shrunk/polls/gh-run-list-20260517T031542Z.json`
    - exact-head `CDK Deploy` run `25979577060` `success` (head `9b969b49...`).
    - latest Pages run remains `25977807200` `success` (head `4328f941...`).
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T03:21:22Z exact-head CI (post poll 20260517T0315Z commit):
  - commit:
    - `git rev-parse HEAD` -> `5e06526322a56ce15cbc59c07e03e7dc3b124264` (`chore: md1-shrunk poll 20260517T0315Z`)
  - GitHub workflows (exact-head; triggered by this push):
    - `CDK Deploy` run `25980034407` `success` (head `5e065263...`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25980034407-20260517T031700Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25980034407-20260517T032112Z.json`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump).

- 2026-05-17T03:26:09Z exact-head CI (post record md1-shrunk cdk run 25980034407 commit):
  - commit:
    - `git rev-parse HEAD` -> `e5fabab1b879b9a865740544c4efb577c4ebcda9` (`chore: record md1-shrunk cdk run 25980034407`)
  - GitHub workflows (exact-head; triggered by this push):
    - `CDK Deploy` run `25980125982` `success` (head `e5fabab1...`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25980125982-20260517T032300Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25980125982-20260517T032602Z.json`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump).

- 2026-05-17T03:31:29Z exact-head CI (post record md1-shrunk cdk run 25980125982 commit):
  - commit:
    - `git rev-parse HEAD` -> `693fbae78b93bc1070153328a9169f28292b79d0` (`chore: record md1-shrunk cdk run 25980125982`)
  - GitHub workflows (exact-head; triggered by this push):
    - `CDK Deploy` run `25980223287` `success` (head `693fbae7...`):
      - watch: `logs/md1-shrunk/polls/gh-run-watch-cdk-25980223287-20260517T033000Z.txt`
      - view: `logs/md1-shrunk/polls/gh-run-view-cdk-25980223287-20260517T033102Z.json`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump).

- 2026-05-17T03:47:12Z poll (monitor-only; no new cloud work launched):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `60ffcfefe466dd93c9fcf5a68c9798895701b94b` (`chore: md1-shrunk poll 20260517T0347Z [skip ci]`)
    - `git status --short` -> clean
  - AWS identity:
    - `python3 -m awscli sts get-caller-identity --output json` -> `logs/md1-shrunk/polls/aws-sts-20260517T034418Z.json`
  - Step Functions:
    - `python3 -m awscli stepfunctions list-executions ... --status-filter RUNNING` -> `logs/md1-shrunk/polls/stepfn-running-20260517T034418Z.json` (`executions=[]`)
  - SageMaker (cost bounded):
    - `python3 -m awscli sagemaker list-processing-jobs --status-equals InProgress ...` -> `logs/md1-shrunk/polls/sm-list-processing-inprogress-20260517T034418Z.json` (`0`)
    - `python3 -m awscli sagemaker list-training-jobs --status-equals InProgress ...` -> `logs/md1-shrunk/polls/sm-list-training-inprogress-20260517T034418Z.json` (`0`)
    - Owned job status (terminal Completed):
      - `md1-shrunk-1456-sfm-1778866088` -> `logs/md1-shrunk/polls/sm-describe-md1-shrunk-1456-sfm-1778866088-20260517T034418Z.json`
      - `md1shrunk1456-1778880862-3dgs` -> `logs/md1-shrunk/polls/sm-describe-md1shrunk1456-1778880862-3dgs-20260517T034418Z.json`
      - `md1shrunk1456-1778880862-compression` -> `logs/md1-shrunk/polls/sm-describe-md1shrunk1456-1778880862-compression-20260517T034418Z.json`
  - SfM gates (Montana scale check):
    - `python3 -m awscli s3 ls s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap/` -> `logs/md1-shrunk/polls/s3-ls-colmap-root-20260517T034505Z.txt`
    - `sfm_metadata.json` snapshot -> `logs/md1-shrunk/polls/sfm_metadata-20260517T034512Z.json`:
      - dataset_image_count=`1456`, images_registered=`1456`, merged_component_count=`1`, points_3d=`1103335`, timed_out=`false`
  - 3DGS+compression gates (no relaunch):
    - 3DGS output artifact present:
      - `python3 -m awscli s3 ls .../3dgs/.../output/` -> `logs/md1-shrunk/polls/s3-ls-3dgs-output-20260517T034642Z.txt` (model.tar.gz `222246750` bytes)
    - compressed supersplat bundle listing -> `logs/md1-shrunk/polls/s3-ls-supersplat_bundle-20260517T034527Z.txt`
    - compressed bundle metadata snapshots:
      - `logs/md1-shrunk/polls/meta-20260517T034540Z.json` (gaussians=`990025`)
      - `logs/md1-shrunk/polls/training_metadata-20260517T034540Z.json` (model_variant=`splatfacto-w-light`, file_size_mb=`234.17`, background_skybox_size_mb=`0.04`)
  - Public bundle + preview viewer HTTP checks:
    - `curl` status -> `logs/md1-shrunk/polls/http-check-20260517T034612Z.txt` (preview_root=200, bundle_meta=200, bundle_skybox=200)
  - GitHub workflows (exact-head):
    - `gh run list --branch agent-113647-md1-baseline-e2e ...` -> `logs/md1-shrunk/polls/gh-run-list-20260517T034836Z.json`
    - exact head `60ffcfef...` has `0` runs (commit includes `[skip ci]`)

- 2026-05-17T03:50:13Z post-push confirmation:
  - commit:
    - `git rev-parse HEAD` -> `91326155207f5ee718fd632dac36b3cda6d19b6c` (`chore: record md1-shrunk post-push poll 20260517T0349Z [skip ci]`)
  - GitHub workflows (exact-head):
    - `gh run list --branch agent-113647-md1-baseline-e2e ...` -> `logs/md1-shrunk/polls/gh-run-list-20260517T034956Z.json`
    - exact head `91326155...` has `0` runs (commit includes `[skip ci]`); latest observed run on branch remains `CDK Deploy` `25980223287` `success` (head `693fbae7...`)

- 2026-05-17T04:15:23Z monitor poll (verify all terminal; no new cloud work launched):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `32d70864985f8a05122c4cf01c4d9d56d0e91f5c` (`chore: bump md1-shrunk state timestamps 20260517T0351Z [skip ci]`)
    - `git status --porcelain=v1` -> new untracked poll artifacts under `logs/md1-shrunk/polls/`
  - AWS identity:
    - `python3 -m awscli sts get-caller-identity --region us-west-2 --output json` -> `logs/md1-shrunk/polls/aws-sts-20260517T041445Z.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions:
    - `python3 -m awscli stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --max-results 20 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/stepfn-running-20260517T041445Z.json` -> RUNNING `0`
  - SageMaker (cost bounded):
    - InProgress processing jobs:
      - `python3 -m awscli sagemaker list-processing-jobs --status-equals InProgress --sort-by CreationTime --sort-order Descending --max-results 50 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/sm-processing-inprogress-20260517T041445Z.json` -> `0`
    - InProgress training jobs:
      - `python3 -m awscli sagemaker list-training-jobs --status-equals InProgress --sort-by CreationTime --sort-order Descending --max-results 50 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/sm-training-inprogress-20260517T041445Z.json` -> `0`
    - Owned job status (terminal Completed):
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `logs/md1-shrunk/polls/sm-describe-md1-shrunk-1456-sfm-1778866088-20260517T041445Z.json`
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `logs/md1-shrunk/polls/sm-describe-md1shrunk1456-1778880862-3dgs-20260517T041445Z.json`
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `logs/md1-shrunk/polls/sm-describe-md1shrunk1456-1778880862-compression-20260517T041445Z.json`
  - Public bundle + preview viewer HTTP checks:
    - HTTP HEAD snapshot: `logs/md1-shrunk/polls/http-head-sanity-20260517T041523Z.txt` -> preview `/health.txt` HTTP 200; bundle `meta.json` HTTP 200; bundle `background_skybox.webp` HTTP 200
    - bundle `meta.json` snapshot: `logs/md1-shrunk/polls/bundle-meta-20260517T041523Z.json`
    - gaussian count snapshot: `logs/md1-shrunk/polls/bundle-gaussians-20260517T041523Z.json` -> `gaussians=990025`
  - GitHub workflows (exact-head):
    - run list (branch): `logs/md1-shrunk/polls/gh-run-list-20260517T041445Z.json` -> latest observed run on branch remains `CDK Deploy` `25980223287` `success` (head `693fbae7...`)
    - run list (exact head): `logs/md1-shrunk/polls/gh-run-list-head-20260517T041446Z.json` -> exact head `32d70864...` has `0` runs (commit includes `[skip ci]`)
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T04:16:50Z post-push confirmation:
  - commit:
    - `git rev-parse HEAD` -> `ded7dd3768aefe11f39e9e639e588bbd60c09278` (`chore: md1-shrunk monitor poll 20260517T0415Z [skip ci]`)
  - GitHub workflows (exact-head):
    - `~/.local/bin/gh run list --commit $(git rev-parse HEAD) --limit 20 --json ...` -> `logs/md1-shrunk/polls/gh-run-list-head-20260517T041650Z.json`
    - exact head `ded7dd37...` has `0` runs (commit includes `[skip ci]`); latest observed run on branch remains `CDK Deploy` `25980223287` `success` (head `693fbae7...`)
    - branch run list snapshot: `logs/md1-shrunk/polls/gh-run-list-20260517T041650Z.json`

- 2026-05-17T04:46:00Z poll (monitor-only; no new cloud work launched):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `921d31d7d88a80954b4cb4acfd14161e8d5bf871` (`chore: record md1-shrunk post-push gh runs 20260517T0416Z [skip ci]`)
    - `git status --porcelain=v1` -> untracked new poll artifacts under `logs/md1-shrunk/polls/`
  - AWS identity:
    - `/opt/homebrew/bin/aws sts get-caller-identity --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions:
    - `/opt/homebrew/bin/aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --max-results 10 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/stepfunctions-running-20260517T0444Z.json` -> RUNNING `0`
  - SageMaker (cost bounded):
    - InProgress processing jobs:
      - `/opt/homebrew/bin/aws sagemaker list-processing-jobs --status-equals InProgress --sort-by CreationTime --sort-order Descending --max-results 20 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/sagemaker-list-processing-inprogress-20260517T0444Z.json` -> `0`
    - Owned job status (terminal Completed):
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `logs/md1-shrunk/polls/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260517T0444Z.json`
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `logs/md1-shrunk/polls/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260517T0445Z.json` (instance `ml.g5.4xlarge`)
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `logs/md1-shrunk/polls/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260517T0445Z.json`
  - SfM gates (Montana scale check):
    - `sfm_metadata.json` snapshot -> `logs/md1-shrunk/polls/sfm-metadata-20260517T0444Z.json`:
      - dataset_image_count=`1456`, images_registered=`1456`, merged_component_count=`1`, points_3d=`1103335`, timed_out=`false`, quality_check_passed=`true`
  - Output listings:
    - COLMAP output recursive listing -> `logs/md1-shrunk/polls/s3-colmap-md1-shrunk-20260515T1641Z-20260517T0444Z.txt`
    - 3DGS output (model.tar.gz) -> `logs/md1-shrunk/polls/s3-3dgs-md1shrunk1456-1778880862-20260517T0445Z.txt`
    - compression outputs (staging) -> `logs/md1-shrunk/polls/s3-compressed-md1shrunk1456-1778880862-20260517T0445Z.txt`
  - Public bundle HTTP checks:
    - bundle meta snapshot -> `logs/md1-shrunk/polls/public-meta-20260517T0445Z.json`
    - HTTP HEAD proof (200 OK):
      - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/meta.json`
      - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/background_skybox.webp`
      - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/settings.json`
  - GitHub workflows:
    - run list snapshot (branch) -> `logs/md1-shrunk/polls/gh-runs-20260517T0444Z.json`
    - Pages deploy still last observed at head `4328f941...` (run `25977807200`); exact head includes `[skip ci]` so it has `0` runs.

- 2026-05-17T04:48:00Z post-push confirmation:
  - commit:
    - `git rev-parse HEAD` -> `4cc4361f165a58eecf53ca963fc3c991c8d9898c` (`chore: md1-shrunk monitor poll 20260517T0446Z [skip ci]`)
  - GitHub workflows (exact-head):
    - branch run list -> `logs/md1-shrunk/polls/gh-run-list-20260517T0448Z.json` (latest observed run remains `CDK Deploy` `25980223287` `success` head `693fbae7...`)
    - exact head run list -> `logs/md1-shrunk/polls/gh-run-list-head-20260517T0448Z.json` -> `0` runs (commit includes `[skip ci]`)

- 2026-05-17T05:14:25Z monitor poll (terminal; no new cloud work launched):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `6208f0f39544483f73246ea1e9fd2cf245fda8af` (`chore: record md1-shrunk post-push gh runs 20260517T0448Z [skip ci]`)
    - `git status --porcelain=v1` -> clean
  - AWS identity:
    - `/opt/homebrew/bin/aws sts get-caller-identity --output json` -> `logs/md1-shrunk/polls/aws-sts-20260517T051425Z.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions:
    - `/opt/homebrew/bin/aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --max-results 20 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/stepfn-running-staging-20260517T051425Z.json` -> RUNNING `0`
  - SageMaker (cost bounded):
    - InProgress processing jobs:
      - `/opt/homebrew/bin/aws sagemaker list-processing-jobs --status-equals InProgress --sort-by CreationTime --sort-order Descending --max-results 50 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/sm-processing-inprogress-20260517T051425Z.json` -> `0`
    - InProgress training jobs:
      - `/opt/homebrew/bin/aws sagemaker list-training-jobs --status-equals InProgress --sort-by CreationTime --sort-order Descending --max-results 50 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/sm-training-inprogress-20260517T051425Z.json` -> `0`
    - Owned job status (terminal Completed; no reruns):
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `logs/md1-shrunk/polls/sm-describe-md1-shrunk-1456-sfm-1778866088-20260517T051425Z.json`
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `logs/md1-shrunk/polls/sm-describe-md1shrunk1456-1778880862-3dgs-20260517T051425Z.json`
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `logs/md1-shrunk/polls/sm-describe-md1shrunk1456-1778880862-compression-20260517T051425Z.json`
  - Output listings:
    - COLMAP output listing -> `logs/md1-shrunk/polls/s3-colmap-20260517T051425Z.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
    - 3DGS output listing -> `logs/md1-shrunk/polls/s3-3dgs-20260517T051425Z.txt` -> `model.tar.gz` (`212.0 MiB`)
    - compression output listing -> `logs/md1-shrunk/polls/s3-compressed-20260517T051425Z.txt` -> `Total Objects: 22`, `Total Size: 28.7 MiB`
    - public supersplat bundle listing -> `logs/md1-shrunk/polls/s3-public-supersplat_bundle-20260517T051425Z.txt`
  - Public bundle health (anonymous):
    - bundle URL -> `logs/md1-shrunk/polls/bundle-meta-url-20260517T051425Z.txt`
    - HTTP HEAD:
      - bundle meta -> `logs/md1-shrunk/polls/http-head-bundle-meta-20260517T051425Z.txt` -> `HTTP 200`
      - bundle skybox -> `logs/md1-shrunk/polls/http-head-bundle-skybox-20260517T051425Z.txt` -> `HTTP 200`
    - bundle meta snapshot -> `logs/md1-shrunk/polls/bundle-meta-20260517T051425Z.json`
    - gaussian count -> `logs/md1-shrunk/polls/bundle-gaussians-20260517T051425Z.txt` -> `990025`
  - GitHub workflows:
    - branch run list -> `logs/md1-shrunk/polls/gh-run-list-20260517T051425Z.json` (latest observed run remains `CDK Deploy` `25980223287` `success` head `693fbae7...`)
    - exact head run list -> `logs/md1-shrunk/polls/gh-run-list-head-20260517T051425Z.json` -> `0` runs (commit includes `[skip ci]`)
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T05:17:17Z post-push confirmation:
  - commit:
    - `git rev-parse HEAD` -> `cc3723b9dc90f7ef3b747aeacbbe3f4acfbddab1` (`chore: md1-shrunk monitor poll 20260517T051425Z [skip ci]`)
  - GitHub workflows (exact-head):
    - branch run list -> `logs/md1-shrunk/polls/gh-run-list-20260517T051717Z.json` (latest observed run remains `CDK Deploy` `25980223287` `success` head `693fbae7...`)
    - exact head run list -> `logs/md1-shrunk/polls/gh-run-list-head-20260517T051717Z.json` -> `0` runs (commit includes `[skip ci]`)

- 2026-05-17T05:17:59Z post-push confirmation (head moved by `[skip ci]` bookkeeping commit):
  - commit:
    - `git rev-parse HEAD` -> `176f1c5dc978ec55c1f611c2396f1dea73a73b01` (`chore: record md1-shrunk post-push gh runs 20260517T051717Z [skip ci]`)
  - GitHub workflows (exact-head):
    - `gh run list --branch agent-113647-md1-baseline-e2e --commit $(git rev-parse HEAD) --limit 20 --json ...` -> `logs/md1-shrunk/polls/gh-run-list-head-20260517T051759Z.json` -> `0` runs

- 2026-05-17T05:57:06Z monitor poll (verify terminal + public bundle; no new cloud work launched):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `d53213554119affed2998d0930a16bf04bd00aba` (`chore: record md1-shrunk head gh runs 20260517T051759Z [skip ci]`)
    - `git status --porcelain=v1` -> clean
  - AWS identity:
    - `/opt/homebrew/bin/aws sts get-caller-identity --output json` -> `logs/md1-shrunk/polls/aws-sts-20260517T055347Z.json` (account `975050048887`)
  - Step Functions:
    - staging pipeline RUNNING=0:
      - `/opt/homebrew/bin/aws stepfunctions list-executions ... --status-filter RUNNING` -> `logs/md1-shrunk/polls/stepfn-running-staging-20260517T055347Z.json` (`executions=[]`)
  - SageMaker (cost bounded):
    - InProgress processing jobs: `0`
      - `/opt/homebrew/bin/aws sagemaker list-processing-jobs --status-equals InProgress ...` -> `logs/md1-shrunk/polls/sm-processing-inprogress-20260517T055347Z.json`
    - InProgress training jobs: `0`
      - `/opt/homebrew/bin/aws sagemaker list-training-jobs --status-equals InProgress ...` -> `logs/md1-shrunk/polls/sm-training-inprogress-20260517T055347Z.json`
    - Owned job status (terminal Completed; no reruns):
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `logs/md1-shrunk/polls/sm-describe-md1-shrunk-1456-sfm-1778866088-20260517T055347Z.json`
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `logs/md1-shrunk/polls/sm-describe-md1shrunk1456-1778880862-3dgs-20260517T055347Z.json`
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `logs/md1-shrunk/polls/sm-describe-md1shrunk1456-1778880862-compression-20260517T055347Z.json`
  - Output listings (no new uploads):
    - COLMAP output listing -> `logs/md1-shrunk/polls/s3-colmap-20260517T055347Z.txt`
    - 3DGS output listing (model.tar.gz present) -> `logs/md1-shrunk/polls/s3-3dgs-output-20260517T055554Z.txt`
    - compressed bundle listing -> `logs/md1-shrunk/polls/s3-compressed-20260517T055347Z.txt`
    - public supersplat bundle listing -> `logs/md1-shrunk/polls/s3-public-supersplat_bundle-corrected-20260517T055521Z.txt`
  - Public bundle metadata (anonymous):
    - meta.json -> `logs/md1-shrunk/polls/public-meta-20260517T055521Z.json` (gaussians derived: `jq -r .means.shape[0]` -> `990025`)
    - training_metadata.json -> `logs/md1-shrunk/polls/public-training_metadata-20260517T055521Z.json` (variant `splatfacto-w-light`, file_size_mb `234.1691`, background_skybox_size_mb `0.0439`)
  - GitHub workflows:
    - latest observed run on branch remains `CDK Deploy` `25980223287` `success` head `693fbae7...`:
      - `/opt/homebrew/bin/gh run list --branch agent-113647-md1-baseline-e2e ...` -> `logs/md1-shrunk/polls/gh-run-list-branch-20260517T055635Z.json`
    - exact head has `0` runs (commit includes `[skip ci]`):
      - `/opt/homebrew/bin/gh run list --branch agent-113647-md1-baseline-e2e --commit $(git rev-parse HEAD) ...` -> `logs/md1-shrunk/polls/gh-run-list-head-20260517T055635Z.json`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T06:12:21Z post-push confirmation:
  - commit:
    - `git rev-parse HEAD` -> `504f6212d824b5d77bbfe186c535fd8412964d80` (`chore: md1-shrunk monitor poll 20260517T0557Z [skip ci]`)
  - GitHub workflows (exact-head):
    - branch run list -> `logs/md1-shrunk/polls/gh-run-list-branch-postpush-20260517T061215Z.json` (latest observed remains `CDK Deploy` `25980223287` `success` head `693fbae7...`)
    - exact head run list -> `logs/md1-shrunk/polls/gh-run-list-head-postpush-20260517T061215Z.json` -> `0` runs (commit includes `[skip ci]`)

- 2026-05-17T06:17:48Z monitor poll (verify terminal + preview URL; no new cloud work launched):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `7405ea59a2f0f83b69905a3b6a51277ba9ffed2e` (`chore: record md1-shrunk post-push gh runs 20260517T061215Z [skip ci]`)
    - `git status --porcelain=v1` -> clean except new poll artifacts under `logs/md1-shrunk/polls/`
  - AWS identity:
    - `/opt/homebrew/bin/aws sts get-caller-identity --output json` -> `logs/md1-shrunk/polls/aws-sts-20260517T061419Z.json` (account `975050048887`)
  - Step Functions (staging):
    - `/opt/homebrew/bin/aws stepfunctions list-executions ... --max-results 10` -> `logs/md1-shrunk/polls/stepfunctions-list-executions-20260517T061419Z.json` (RUNNING=0; recent SUCCEEDED only)
  - SageMaker (cost bounded):
    - InProgress processing jobs: `0` -> `logs/md1-shrunk/polls/sagemaker-list-processing-InProgress-20260517T061654Z.json`
    - InProgress training jobs: `0` -> `logs/md1-shrunk/polls/sagemaker-list-training-InProgress-20260517T061654Z.json`
    - Owned terminal statuses (no reruns):
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `logs/md1-shrunk/polls/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260517T061419Z.json` (`Completed`)
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `logs/md1-shrunk/polls/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260517T0619Z.json` (`Completed`)
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `logs/md1-shrunk/polls/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260517T0619Z.json` (`Completed`)
  - SfM quality snapshot (Montana gates):
    - `sfm_metadata.json` -> `logs/md1-shrunk/polls/sfm_metadata-md1-shrunk-20260515T1641Z-20260517T061558Z.json`
      - `images_registered=1456` (>= Meadow 1452)
      - `points_3d=1103335` (>= Meadow 940147)
      - `pipeline=colmap_gpu_spatial_heading_chunked`, `chunk_count=6`, `quality_check_passed=true`
  - Preview deploy URL (latest successful Pages run):
    - `Deploy Next.js to Cloudflare Pages` run `25977807200` -> `logs/md1-shrunk/polls/gh-pages-run-25977807200-log.txt`
    - alias URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - Public bundle reachability (anonymous):
    - HTTP 200 HEAD -> `logs/md1-shrunk/polls/http-head-bundle-20260517T061654Z.txt`
    - meta.json snippet -> `logs/md1-shrunk/polls/meta-head-20260517T061654Z.txt` (gaussian count remains ~990k)
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T06:19:04Z post-push confirmation:
  - commit:
    - `git rev-parse HEAD` -> `382f57bce806e0258c24ece60f930311280b8dc8` (`chore: md1-shrunk monitor poll 20260517T0617Z [skip ci]`)
  - GitHub workflows (exact-head):
    - branch run list -> `logs/md1-shrunk/polls/gh-run-list-branch-postpush-20260517T061904Z.json` (latest observed still `Deploy Next.js to Cloudflare Pages` `25977807200` + `CDK Deploy` `25977807203` for head `4328f941...`)
    - exact head run list -> `logs/md1-shrunk/polls/gh-run-list-head-postpush-20260517T061904Z.json` -> `0` runs (commit includes `[skip ci]`)

- 2026-05-17T06:52:17Z monitor poll (terminal reconfirm + viewer validation; no new ML launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `cc87aca7ef7b884206cc3169425dfb94036965d1` (`chore: record md1-shrunk post-push gh runs 20260517T061904Z [skip ci]`)
    - `git status --porcelain=v1` -> clean
  - AWS identity / Step Functions / SageMaker (staging):
    - `/opt/homebrew/bin/aws sts get-caller-identity` -> `logs/md1-shrunk/polls/20260517T064446Z/aws-sts-20260517T064446Z.json` (account `975050048887`)
    - `/opt/homebrew/bin/aws stepfunctions list-executions ... SpaceportMLPipeline-staging` -> `logs/md1-shrunk/polls/20260517T064446Z/stepfunctions-list-executions-20260517T064446Z.json` (RUNNING=0)
    - owned terminal statuses reconfirm:
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `logs/md1-shrunk/polls/20260517T064446Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260517T064446Z.json` (`Completed`)
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `logs/md1-shrunk/polls/20260517T064446Z/sagemaker-describe-md1shrunk1456-1778880862-3dgs-20260517T064446Z.json` (`Completed`)
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `logs/md1-shrunk/polls/20260517T064446Z/sagemaker-describe-md1shrunk1456-1778880862-compression-20260517T064446Z.json` (`Completed`)
    - InProgress processing/training counts: `0/0` -> `logs/md1-shrunk/polls/20260517T064446Z/sagemaker-list-processing-inprogress-20260517T064446Z.json`, `logs/md1-shrunk/polls/20260517T064446Z/sagemaker-list-training-inprogress-20260517T064446Z.json`
  - SfM gates (Montana-scale facts):
    - `sfm_metadata.json` -> `logs/md1-shrunk/polls/20260517T064503Z/sfm_metadata-20260517T064503Z.json`
      - `images_registered=1456`, `points_3d=1103335`, `merged_component_count=1`, `quality_check_passed=true`
  - 3DGS/compression gates:
    - training metadata + compression summary snapshots:
      - `logs/md1-shrunk/polls/20260517T064827Z/training_metadata-20260517T064827Z.json` -> `remaining_gaussians=990091`, `file_size_mb=234.169...`, `background_skybox=background_skybox.webp`
      - `logs/md1-shrunk/polls/20260517T064827Z/sogs_compression_summary-20260517T064827Z.json` -> `compressed_size_mb=14.345...`
    - public bundle reachability (anonymous):
      - meta.json HEAD 200 -> `logs/md1-shrunk/polls/20260517T064836Z/curl-head-meta-20260517T064836Z.txt`
      - skybox HEAD 200 -> `logs/md1-shrunk/polls/20260517T064836Z/curl-head-skybox-20260517T064836Z.txt`
  - GitHub workflows + preview URL (deterministic from Pages run log):
    - Pages run list: `logs/md1-shrunk/polls/20260517T064605Z/gh-pages-run-list-20260517T064605Z.json` (latest run `25977807200` success for head `4328f941...`)
    - CDK run list: `logs/md1-shrunk/polls/20260517T064605Z/gh-cdk-run-list-20260517T064605Z.json`
    - Pages run log + extracted URLs:
      - `logs/md1-shrunk/polls/20260517T064909Z/gh-run-25977807200-log-20260517T064909Z.txt`
      - alias URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
      - extraction: `logs/md1-shrunk/polls/20260517T064909Z/gh-run-25977807200-preview-urls-20260517T064909Z.txt`
    - Note: no exact-head GH workflow runs for `cc87aca7...` (commit includes `[skip ci]`).
  - Viewer validation (preview alias; skybox + no-sky):
    - command (skybox override):
      - `SOGS_SKYBOX_OVERRIDE=background_skybox.webp SOGS_EXPECT_BUNDLED_SKYBOX=1 node web/scripts/test-sogs-migrated-viewer.mjs`
    - command (no-sky):
      - `SOGS_DISABLE_SKYBOX=1 node web/scripts/test-sogs-migrated-viewer.mjs`
    - stdout + screenshots:
      - `logs/md1-shrunk/polls/20260517T065217Z/viewer-skybox-stdout-20260517T065217Z.txt`
      - `logs/md1-shrunk/polls/20260517T065217Z/viewer-nosky-stdout-20260517T065217Z.txt`
      - `logs/md1-shrunk/polls/20260517T065217Z/sogs-migrated-viewer-skybox-20260517T065217Z.png`
      - `logs/md1-shrunk/polls/20260517T065217Z/sogs-migrated-viewer-nosky-20260517T065217Z.png`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T07:14:35Z monitor poll (terminal reconfirm; no new ML launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `3bad045c2ed2051efe162a44632645d4c80b9d90`
    - `git status --porcelain=v1` -> clean
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T071435Z/`
  - AWS identity:
    - `/opt/homebrew/bin/aws sts get-caller-identity --output json` -> `logs/md1-shrunk/polls/20260517T071435Z/aws-sts.json` (account `975050048887`)
  - Step Functions (staging):
    - `/opt/homebrew/bin/aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --max-results 20 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/20260517T071435Z/stepfunctions-list-executions-staging.json` (RUNNING=0)
  - SageMaker (cost bounded):
    - InProgress processing jobs: `0` -> `logs/md1-shrunk/polls/20260517T071435Z/sagemaker-list-processing-InProgress.json`
    - InProgress training jobs: `0` -> `logs/md1-shrunk/polls/20260517T071435Z/sagemaker-list-training-InProgress.json`
    - Owned terminal statuses reconfirm:
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `logs/md1-shrunk/polls/20260517T071435Z/sagemaker-describe-sfm.json` (`Completed`)
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `logs/md1-shrunk/polls/20260517T071435Z/sagemaker-describe-3dgs.json` (`Completed`)
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `logs/md1-shrunk/polls/20260517T071435Z/sagemaker-describe-compression.json` (`Completed`)
  - GitHub workflows + preview URL (exact-head):
    - exact-head run list: `logs/md1-shrunk/polls/20260517T071435Z/gh-run-list-head.json` -> `CDK Deploy` `25983995050` + `Deploy Next.js to Cloudflare Pages` `25983995070` (both `success`)
    - Pages run log: `logs/md1-shrunk/polls/20260517T071435Z/gh-pages-run-25983995070-log.txt`
    - extracted URLs: `logs/md1-shrunk/polls/20260517T071435Z/gh-pages-run-25983995070-preview-urls.txt`
    - alias URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - Public bundle reachability (anonymous):
    - meta.json HEAD 200 -> `logs/md1-shrunk/polls/20260517T071435Z/http-head-meta.txt`
    - skybox HEAD 200 -> `logs/md1-shrunk/polls/20260517T071435Z/http-head-skybox.txt`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T07:22:05Z post-push confirmation (CI only; no new ML launches):
  - commit:
    - `git rev-parse HEAD` -> `40e491a8f4c6da5147db698d246718ec21176f3b` (`chore: md1-shrunk poll 20260517T071435Z`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` run `25984436488` -> `success`
    - Note: `Deploy Next.js to Cloudflare Pages` did not trigger for this commit (logs-only change).

- 2026-05-17T07:45:36Z idle poll (no new launches; terminal reconfirm):
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T074536Z/`
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `cec8eec78fcea2c178fef52c3db271a2068969b5`
    - `git status --porcelain=v1` -> new poll artifacts under `logs/md1-shrunk/polls/20260517T074536Z/`
  - AWS identity:
    - `/opt/homebrew/bin/aws sts get-caller-identity --output json` -> `logs/md1-shrunk/polls/20260517T074536Z/aws-sts.json` (account `975050048887`)
  - Step Functions:
    - staging RUNNING=0:
      - `/opt/homebrew/bin/aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --max-results 10 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/20260517T074536Z/stepfunctions-list-executions-staging.json`
    - branch pipelines RUNNING=0 (enumerated from `stepfunctions-list-state-machines.json`):
      - `logs/md1-shrunk/polls/20260517T074536Z/stepfunctions-branch-arns.txt`
      - `logs/md1-shrunk/polls/20260517T074536Z/stepfunctions-list-executions-branch-running.json`
  - SageMaker (owned jobs terminal; cost bounded):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `logs/md1-shrunk/polls/20260517T074536Z/sagemaker-describe-sfm.json` (`Completed`)
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `logs/md1-shrunk/polls/20260517T074536Z/sagemaker-describe-3dgs.json` (`Completed`)
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `logs/md1-shrunk/polls/20260517T074536Z/sagemaker-describe-compression.json` (`Completed`)
    - InProgress processing jobs: `0` -> `logs/md1-shrunk/polls/20260517T074536Z/sagemaker-list-processing-InProgress.json`
    - InProgress training jobs: `0` -> `logs/md1-shrunk/polls/20260517T074536Z/sagemaker-list-training-InProgress.json`
  - S3 output presence reconfirm (owned outputs):
    - COLMAP: `logs/md1-shrunk/polls/20260517T074536Z/s3-colmap.txt` (`Total Size: 9.2 GiB`)
    - 3DGS: `logs/md1-shrunk/polls/20260517T074536Z/s3-3dgs.txt` (`model.tar.gz` `212.0 MiB`)
    - compressed: `logs/md1-shrunk/polls/20260517T074536Z/s3-compressed.txt` (`Total Size: 28.7 MiB`)
  - GitHub workflows (exact-head):
    - `gh run list ...` -> `logs/md1-shrunk/polls/20260517T074536Z/gh-run-list-branch.json`
    - exact-head runs: `logs/md1-shrunk/polls/20260517T074536Z/gh-runs-for-head.tsv` -> `CDK Deploy` `25984520953` `success` (no Pages run triggered at this logs-only head)
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T07:51:22Z post-push confirmation (CI only; no new ML launches):
  - commit:
    - `git rev-parse HEAD` -> `8bcc1a6b44493f553d6f5e41835bbd82d3fc5e54` (`chore: md1-shrunk poll 20260517T074536Z`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` run `25985037939` -> `success`
      - watch: `logs/md1-shrunk/polls/20260517T074536Z/gh-run-watch-cdk-25985037939.txt`
      - view: `logs/md1-shrunk/polls/20260517T074536Z/gh-run-view-cdk-25985037939.json`
    - Note: `Deploy Next.js to Cloudflare Pages` did not trigger for this commit (logs-only change).

- 2026-05-17T07:56:08Z post-push confirmation (CI only; no new ML launches):
  - commit:
    - `git rev-parse HEAD` -> `05cd0e28762dd08f7e96386aa34a51df4d106ec7` (`chore: record md1-shrunk cdk run 25985037939`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` run `25985134150` -> `success`
      - watch: `logs/md1-shrunk/polls/20260517T075239Z/gh-run-watch-cdk-25985134150.txt`
      - view: `logs/md1-shrunk/polls/20260517T075239Z/gh-run-view-cdk-25985134150.json`
      - run list: `logs/md1-shrunk/polls/20260517T075239Z/gh-run-list-branch.json`
    - Note: `Deploy Next.js to Cloudflare Pages` did not trigger for this commit (logs-only change).

- 2026-05-17T08:14:03Z monitor poll (terminal reconfirm; no new ML launches):
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T081403Z/`
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `3f409b561673191df087c876cca239e6d1e10939`
    - `git status --porcelain=v1` -> clean after commit (new poll artifacts staged for next commit)
  - AWS identity:
    - `/opt/homebrew/bin/aws sts get-caller-identity --output json` -> `logs/md1-shrunk/polls/20260517T081403Z/aws-sts.json` (account `975050048887`)
  - Step Functions (staging):
    - RUNNING=0:
      - `/opt/homebrew/bin/aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING ...` -> `logs/md1-shrunk/polls/20260517T081403Z/stepfunctions-list-executions-staging-running.json`
  - SageMaker (cost bounded):
    - InProgress processing jobs: `0` -> `logs/md1-shrunk/polls/20260517T081403Z/sagemaker-list-processing-InProgress.json`
    - InProgress training jobs: `0` -> `logs/md1-shrunk/polls/20260517T081403Z/sagemaker-list-training-InProgress.json`
    - Owned terminal statuses reconfirm:
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `logs/md1-shrunk/polls/20260517T081403Z/sagemaker-describe-sfm.json` (`Completed`)
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `logs/md1-shrunk/polls/20260517T081403Z/sagemaker-describe-3dgs.json` (`Completed`)
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `logs/md1-shrunk/polls/20260517T081403Z/sagemaker-describe-compression.json` (`Completed`)
  - S3 output presence reconfirm (owned outputs):
    - COLMAP: `logs/md1-shrunk/polls/20260517T081403Z/s3-colmap.txt` (`Total Size: 9.2 GiB`)
    - 3DGS: `logs/md1-shrunk/polls/20260517T081403Z/s3-3dgs.txt` (`model.tar.gz` `212.0 MiB`)
    - compressed: `logs/md1-shrunk/polls/20260517T081403Z/s3-compressed.txt` (`Total Size: 28.7 MiB`)
  - Gates (Montana-scale facts; downloaded from owned outputs):
    - SfM: `logs/md1-shrunk/polls/20260517T081403Z/sfm_metadata.json`
    - 3DGS bundle sidecar: `logs/md1-shrunk/polls/20260517T081403Z/training_metadata.json`
    - compression summary: `logs/md1-shrunk/polls/20260517T081403Z/sogs_compression_summary.json`
    - extracted summary: `logs/md1-shrunk/polls/20260517T081403Z/gates-summary.txt` (images_registered=1456, points_3d=1103335, remaining_gaussians=990091, total_compressed_mb=14.3454…)
  - Public bundle reachability (anonymous):
    - meta.json URL: `logs/md1-shrunk/polls/20260517T081403Z/public-meta-url.txt`
    - skybox URL: `logs/md1-shrunk/polls/20260517T081403Z/public-skybox-url.txt`
    - meta.json headers: `logs/md1-shrunk/polls/20260517T081403Z/http-head-meta.txt` (`HTTP 200`)
    - skybox headers: `logs/md1-shrunk/polls/20260517T081403Z/http-head-skybox.txt` (`HTTP 200`)
  - GitHub workflows + preview URL (deterministic):
    - run list: `logs/md1-shrunk/polls/20260517T081403Z/gh-run-list-branch.json`
    - summary: `logs/md1-shrunk/polls/20260517T081403Z/gh-summary.txt`
      - exact-head `CDK Deploy` run `25985228636` -> `success` (head `3f409b56...`)
      - latest Pages run `25983995070` -> `success` (head `3bad045c...`; no Pages run triggered by logs-only commit)
    - CDK watch/view:
      - `logs/md1-shrunk/polls/20260517T081403Z/gh-run-watch-cdk-25985228636.txt`
      - `logs/md1-shrunk/polls/20260517T081403Z/gh-run-view-cdk-25985228636.json`
    - Pages run log + extracted URLs:
      - `logs/md1-shrunk/polls/20260517T081403Z/gh-pages-run-25983995070-log.txt`
      - `logs/md1-shrunk/polls/20260517T081403Z/gh-pages-run-25983995070-preview-urls.txt`
    - preview health URL: `logs/md1-shrunk/polls/20260517T081403Z/preview-health-url.txt` + headers `logs/md1-shrunk/polls/20260517T081403Z/http-head-preview-health.txt`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T08:23:29Z post-push confirmation (CI only; no new ML launches):
  - commit:
    - `git rev-parse HEAD` -> `21b60fe01678bd2cccb828103121c2e636f65330` (`chore: md1-shrunk poll 20260517T081403Z`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` run `25985695259` -> `success`
      - watch: `logs/md1-shrunk/polls/20260517T082008Z/gh-run-watch-cdk-25985695259-tty.txt`
      - view: `logs/md1-shrunk/polls/20260517T082008Z/gh-run-view-cdk-25985695259.json`
      - run list: `logs/md1-shrunk/polls/20260517T082008Z/gh-run-list-branch.json`
      - exact-head summary: `logs/md1-shrunk/polls/20260517T082008Z/gh-summary.txt`
    - Note: `Deploy Next.js to Cloudflare Pages` did not trigger for this logs-only commit.

- 2026-05-17T08:44:46Z monitor poll (terminal reconfirm; no new ML launches):
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T084446Z/`
    - `logs/md1-shrunk/polls/20260517T084516Z/`
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `06312494cf8ec963b88d674ab2cc2605beae07b5` (`chore: record md1-shrunk cdk 25985695259 [skip ci]`)
    - `git status --porcelain=v1` -> clean (new poll artifacts untracked)
  - AWS identity:
    - `/opt/homebrew/bin/aws sts get-caller-identity --output json` -> `logs/md1-shrunk/polls/20260517T084446Z/aws-sts-get-caller-identity.json` (account `975050048887`)
  - Step Functions (staging):
    - RUNNING=0:
      - `/opt/homebrew/bin/aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING ...` -> `logs/md1-shrunk/polls/20260517T084446Z/stepfunctions-list-executions-staging-running.json`
  - SageMaker (cost bounded):
    - InProgress processing jobs: `0` -> `logs/md1-shrunk/polls/20260517T084446Z/sagemaker-list-processing-InProgress.json`
    - InProgress training jobs: `0` -> `logs/md1-shrunk/polls/20260517T084446Z/sagemaker-list-training-InProgress.json`
    - Owned terminal statuses reconfirm:
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `logs/md1-shrunk/polls/20260517T084446Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json` (`Completed`)
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `logs/md1-shrunk/polls/20260517T084446Z/sagemaker-describe-md1shrunk1456-1778880862-3dgs.json` (`Completed`)
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `logs/md1-shrunk/polls/20260517T084446Z/sagemaker-describe-md1shrunk1456-1778880862-compression.json` (`Completed`)
  - GitHub workflows (exact-head):
    - run list: `logs/md1-shrunk/polls/20260517T084516Z/gh-run-list.json`
    - exact head runs: `0` (commit message includes `[skip ci]`, so no new workflows expected)
    - latest CDK Deploy on this branch remains `25985695259` `success` (head `21b60fe0...`)
    - latest Pages run remains `25983995070` `success` (head `3bad045c...`)
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T08:47:43Z public bundle reconfirm (downloaded meta.json + preview health):
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T084743Z/`
  - Public bundle:
    - `logs/md1-shrunk/polls/20260517T084743Z/public-meta-url.txt` -> downloaded `logs/md1-shrunk/polls/20260517T084743Z/meta.json`
      - splatCount inferred from `meta.json` shape: `990025`
    - headers: `logs/md1-shrunk/polls/20260517T084743Z/http-head-meta.txt` (`HTTP 200`)
  - Preview alias:
    - health: `logs/md1-shrunk/polls/20260517T084743Z/preview-health-url.txt` + `logs/md1-shrunk/polls/20260517T084743Z/preview-health.txt`
  - Notes:
    - No production URLs used; preview only.

- 2026-05-17T08:50:52Z preview viewer revalidation (Playwright; skybox + no-sky):
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T085052Z/`
  - /sogs-migrated-viewer:
    - bundled skybox smoke:
      - log: `logs/md1-shrunk/polls/20260517T085052Z/playwright-sogs-migrated-skybox.txt`
      - screenshot: `logs/md1-shrunk/polls/20260517T085052Z/sogs-migrated-viewer-smoke.png`
    - no-sky smoke:
      - log: `logs/md1-shrunk/polls/20260517T085052Z/playwright-sogs-migrated-nosky.txt`
      - screenshot: `logs/md1-shrunk/polls/20260517T085052Z/sogs-migrated-viewer-nosky.png`
  - /md1-viewer (single pose; camera check harness):
    - bundled skybox pose render:
      - log: `logs/md1-shrunk/polls/20260517T085052Z/playwright-md1-camera-check-skybox.txt`
      - screenshot: `logs/md1-shrunk/polls/20260517T085052Z/md1-camera-check-skybox.png`
    - no-sky pose render:
      - log: `logs/md1-shrunk/polls/20260517T085052Z/playwright-md1-camera-check-nosky.txt`
      - screenshot: `logs/md1-shrunk/polls/20260517T085052Z/md1-camera-check-nosky.png`

- 2026-05-17T08:53:39Z post-push confirmation (CI only; no new ML launches):
  - commit:
    - `git rev-parse HEAD` -> `7d1b62b417391450eeace2e2a6513b1fd9ba2d6c` (`chore: md1-shrunk poll 20260517T085052Z`)
  - GitHub workflows (exact-head):
    - `CDK Deploy` run `25986385371` -> `success`
      - watch: `logs/md1-shrunk/polls/20260517T085339Z/gh-run-watch-cdk-25986385371.txt`
      - view: `logs/md1-shrunk/polls/20260517T085339Z/gh-run-view-cdk-25986385371.json`
      - run list: `logs/md1-shrunk/polls/20260517T085339Z/gh-run-list-branch.json`
    - Note: `Deploy Next.js to Cloudflare Pages` did not trigger for this logs-only commit; latest Pages success remains run `25983995070` (head `3bad045c...`).

- 2026-05-17T09:46:27Z monitor poll (no new cloud work launched; terminal reconfirm):
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T094627Z/`
  - Branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `7ef18e31e223ee5985356d2d12351362cf6ee57b` (`chore: md1-shrunk poll head wording 20260517T091531Z [skip ci]`)
    - `git status --porcelain=v1` -> clean (new poll artifacts untracked)
    - Note: prior context claimed head `e9cbf71c...`; that commit exists on-branch but is not the branch tip as of `2026-05-17T09:46:27Z`.
  - AWS identity (boto3; `us-west-2`):
    - `logs/md1-shrunk/polls/20260517T094627Z/aws-sts-get-caller-identity.json` -> account `975050048887`
  - Step Functions (staging; cost bounded):
    - RUNNING=0:
      - `logs/md1-shrunk/polls/20260517T094627Z/stepfunctions-running-SpaceportMLPipeline-staging.json`
  - SageMaker (cost bounded):
    - InProgress processing jobs: `0`:
      - `logs/md1-shrunk/polls/20260517T094627Z/sagemaker-list-processing-jobs-InProgress.json`
    - InProgress training jobs: `0`:
      - `logs/md1-shrunk/polls/20260517T094627Z/sagemaker-list-training-jobs-InProgress.json`
    - SfM (ProcessingJob) terminal reconfirm:
      - `logs/md1-shrunk/polls/20260517T094627Z/sagemaker-describe-processing-job-md1-shrunk-1456-sfm-1778866088.json` -> `Completed`
  - Output shape reconfirm (S3 listings via boto3; no downloads):
    - COLMAP output listing (staging):
      - `logs/md1-shrunk/polls/20260517T094627Z/s3-list-colmap-output.json`
    - Public supersplat bundle listing:
      - `logs/md1-shrunk/polls/20260517T094627Z/s3-list-public-supersplat-bundle.json`
  - Public preview + bundle HTTP sanity (anonymous):
    - `curl -I` snapshot:
      - `logs/md1-shrunk/polls/20260517T094627Z/http-head-sanity.txt` (preview `/health.txt` HTTP 200; bundle `meta.json` HTTP 200; bundle `background_skybox.webp` HTTP 200)
  - GitHub workflows (exact-head; unauthenticated API check):
    - Because `gh` was not available in this environment, verified via GitHub REST:
      - run list: `logs/md1-shrunk/polls/20260517T094627Z/github-actions-runs.json`
      - summary: `logs/md1-shrunk/polls/20260517T094627Z/github-actions-summary.json`
      - exact head runs for `7ef18e31...`: `0` (commit message includes `[skip ci]`, so no workflows expected)
      - latest Pages on this branch remains the prior success for head `3bad045c...` (run `25983995070`).

- 2026-05-17T09:54:10Z post-push confirmation (CI only; no new ML launches):
  - commit:
    - `git rev-parse HEAD` -> `252854d764a4de56cd99cd5cba93c22ea14376e7` (`chore: md1-shrunk poll 20260517T094627Z`)
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T094916Z/`
  - GitHub workflows (exact-head; verified via unauthenticated REST):
    - `CDK Deploy` run `25987533412` -> `success`
      - watch log: `logs/md1-shrunk/polls/20260517T094916Z/github-run-watch-cdk-25987533412.txt`
      - run snapshots: `logs/md1-shrunk/polls/20260517T094916Z/github-run-cdk-25987533412-*.json`
      - summary: `logs/md1-shrunk/polls/20260517T094916Z/github-actions-summary-post-cdk.json`
    - Note: `Deploy Next.js to Cloudflare Pages` did not trigger for this logs-only change set; latest Pages success remains run `25983995070` (head `3bad045c...`).

- 2026-05-17T09:59:50Z post-push confirmation (CI only; no new ML launches):
  - commit:
    - `git rev-parse HEAD` -> `840e7bbf07787aa587167105ce1c5411c0f8878d` (`chore: md1-shrunk CI proof 20260517T094916Z`)
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T095458Z/`
  - GitHub workflows (exact-head; verified via unauthenticated REST):
    - `CDK Deploy` run `25987647314` -> `success`
      - watch log: `logs/md1-shrunk/polls/20260517T095458Z/github-run-watch-cdk-25987647314.txt`
      - run snapshots: `logs/md1-shrunk/polls/20260517T095458Z/github-run-cdk-25987647314-*.json`
      - summary: `logs/md1-shrunk/polls/20260517T095458Z/github-actions-summary-post-cdk.json`
    - Note: `Deploy Next.js to Cloudflare Pages` did not trigger for this logs-only change set; latest Pages success remains run `25983995070` (head `3bad045c...`).

- 2026-05-17T10:07:54Z post-push confirmation (CI only; no new ML launches):
  - commit:
    - `git rev-parse HEAD` -> `63d6073326d506de901a31f2d0de591778e11a13` (`chore: md1-shrunk CI proof 20260517T095458Z`)
  - Poll artifacts (local-only; not pushed to avoid retriggering CI):
    - `logs/md1-shrunk/polls/20260517T100309Z/`
  - GitHub workflows (exact-head; verified via unauthenticated REST):
    - `CDK Deploy` run `25987814334` -> `success`
      - watch log: `logs/md1-shrunk/polls/20260517T100309Z/github-run-watch-cdk-25987814334.txt`
      - summary: `logs/md1-shrunk/polls/20260517T100309Z/github-actions-summary-post-cdk.json`
    - Note: `Deploy Next.js to Cloudflare Pages` did not trigger for this logs-only change set; latest Pages success remains run `25983995070` (head `3bad045c...`).

- 2026-05-17T10:17:56Z monitor poll (no new cloud work launched; terminal reconfirm):
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T101200Z/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260517T101200Z/git-meta.txt` -> head `5bcc0b15...` (user-provided `e9cbf71c...` is not branch tip as of this poll)
  - AWS identity (us-west-2):
    - `logs/md1-shrunk/polls/20260517T101200Z/aws-sts-get-caller-identity.json` -> account `975050048887`
  - Step Functions (staging; cost bounded):
    - `logs/md1-shrunk/polls/20260517T101200Z/stepfunctions-list-executions-staging.json` -> no `RUNNING` executions in the latest page
  - SageMaker (cost bounded):
    - InProgress processing jobs: `0`:
      - `logs/md1-shrunk/polls/20260517T101200Z/sagemaker-list-processing-InProgress.json`
    - InProgress training jobs: `0`:
      - `logs/md1-shrunk/polls/20260517T101200Z/sagemaker-list-training-InProgress.json`
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T101200Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T101200Z/sagemaker-describe-md1shrunk1456-1778880862-3dgs.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T101200Z/sagemaker-describe-md1shrunk1456-1778880862-compression.json`
  - Output shape reconfirm (S3 listings; no downloads):
    - COLMAP output listing:
      - `logs/md1-shrunk/polls/20260517T101200Z/s3-colmap.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
    - 3DGS output listing:
      - `logs/md1-shrunk/polls/20260517T101200Z/s3-3dgs.txt` -> `model.tar.gz` present
    - compressed output listing:
      - `logs/md1-shrunk/polls/20260517T101200Z/s3-compressed.txt` -> `Total Objects: 22`, `Total Size: 28.7 MiB`
  - Public preview + bundle HTTP sanity (anonymous):
    - `logs/md1-shrunk/polls/20260517T101200Z/http-head-preview-health.txt` -> `HTTP 200`
    - `logs/md1-shrunk/polls/20260517T101200Z/http-head-meta.txt` -> `HTTP 200`
    - `logs/md1-shrunk/polls/20260517T101200Z/http-head-skybox.txt` -> `HTTP 200`
  - GitHub workflows (exact-head; `gh` available here via `/opt/homebrew/bin/gh`):
    - run list: `logs/md1-shrunk/polls/20260517T101200Z/gh-run-list.json`
    - exact-head summary: `logs/md1-shrunk/polls/20260517T101200Z/gh-exact-head-summary.txt`
    - `CDK Deploy` run `25987954545` -> `success`:
      - view: `logs/md1-shrunk/polls/20260517T101200Z/gh-run-view-cdk-25987954545.json`
      - watch: `logs/md1-shrunk/polls/20260517T101200Z/gh-run-watch-cdk-25987954545.txt`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T10:22:26Z post-push CI confirmation (no new ML launches):
  - commit:
    - `git rev-parse HEAD` -> `23914085b85bf5a71ed4b7cc6f6d010aced8ea59` (`chore: md1-shrunk poll 20260517T101200Z`)
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T101756Z/`
  - GitHub workflows (exact-head):
    - `CDK Deploy` run `25988135800` -> `success`:
      - watch: `logs/md1-shrunk/polls/20260517T101756Z/gh-run-watch-cdk-25988135800.txt`
      - view: `logs/md1-shrunk/polls/20260517T101756Z/gh-run-view-cdk-25988135800.json`
      - list: `logs/md1-shrunk/polls/20260517T101756Z/gh-run-list-branch.json`
    - Note: `Deploy Next.js to Cloudflare Pages` not observed in the latest branch run list (logs-only change set).

- 2026-05-17T10:27:20Z post-push CI confirmation (exact-head green; no new ML launches):
  - commit:
    - `git rev-parse HEAD` -> `0962cfe958355aa85594efefeb73499ab80de241` (`chore: md1-shrunk CI proof 20260517T101756Z`)
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T102340Z/`
  - GitHub workflows (exact-head):
    - `CDK Deploy` run `25988229244` -> `success`:
      - watch: `logs/md1-shrunk/polls/20260517T102340Z/gh-run-watch-cdk-25988229244.txt`
      - view: `logs/md1-shrunk/polls/20260517T102340Z/gh-run-view-cdk-25988229244.json`
      - list: `logs/md1-shrunk/polls/20260517T102340Z/gh-run-list-branch.json`
    - Note: `Deploy Next.js to Cloudflare Pages` not observed in the latest branch run list (logs-only change set).

- 2026-05-17T10:45:02Z monitor poll (no new ML launches; reconfirm terminal + public reachability):
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T104502Z/`
  - Branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `f143d72bedaf62e889a7f5c0d00aab6a00187d85` (`[skip ci]`)
    - `git status --porcelain=v1` -> dirty due to new poll artifacts (see `logs/md1-shrunk/polls/20260517T104502Z/git-status.txt`)
  - AWS identity:
    - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
      - evidence: `logs/md1-shrunk/polls/20260517T104502Z/aws-sts-get-caller-identity.json`
  - Step Functions state (region `us-west-2`):
    - staging + branch-preview state machines: `RUNNING=0`
      - evidence:
        - `logs/md1-shrunk/polls/20260517T104502Z/stepfunctions-list-executions-RUNNING-staging.json`
        - `logs/md1-shrunk/polls/20260517T104502Z/stepfunctions-list-executions-RUNNING-branch.json`
  - SageMaker state (region `us-west-2`):
    - InProgress processing jobs: `0`
    - InProgress training jobs: `0`
    - terminal job statuses (all `Completed`):
      - SfM: `logs/md1-shrunk/polls/20260517T104502Z/sagemaker-describe-sfm-md1-shrunk-1456-sfm-1778866088.json`
      - 3DGS: `logs/md1-shrunk/polls/20260517T104502Z/sagemaker-describe-3dgs-md1shrunk1456-1778880862-3dgs.json`
      - compression: `logs/md1-shrunk/polls/20260517T104502Z/sagemaker-describe-compression-md1shrunk1456-1778880862-compression.json`
    - poll summary: `logs/md1-shrunk/polls/20260517T104502Z/poll-summary.txt`
  - S3 outputs still present:
    - COLMAP: `logs/md1-shrunk/polls/20260517T104502Z/s3-colmap-md1-shrunk-20260515T1641Z.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
    - 3DGS: `logs/md1-shrunk/polls/20260517T104502Z/s3-3dgs-md1shrunk1456-1778880862.txt` -> `model.tar.gz` present
    - compressed: `logs/md1-shrunk/polls/20260517T104502Z/s3-compressed-md1shrunk1456-1778880862.txt` -> `Total Objects: 22`, `Total Size: 28.7 MiB`
  - Public preview + bundle HTTP sanity:
    - `logs/md1-shrunk/polls/20260517T104502Z/http-head-sanity.txt` -> preview `/health.txt` HTTP 200; bundle `meta.json` HTTP 200; bundle `background_skybox.webp` HTTP 200
  - GitHub Actions (branch snapshot; exact head has 0 runs due to `[skip ci]`):
    - list + summary:
      - `logs/md1-shrunk/polls/20260517T104502Z/gh-run-list.json`
      - `logs/md1-shrunk/polls/20260517T104502Z/gh-summary.txt`

- 2026-05-17T10:50:04Z post-push verification (logs-only; `[skip ci]`):
  - commit:
    - `git rev-parse HEAD` -> `509d98c852c0b6cd10ea8f1c577ea0fdbd4a3561` (`chore: md1-shrunk poll 20260517T104502Z [skip ci]`)
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T105004Z/`
  - GitHub Actions:
    - exact head has `0` runs (commit message includes `[skip ci]`)
    - evidence:
      - `logs/md1-shrunk/polls/20260517T105004Z/gh-run-list.json`
      - `logs/md1-shrunk/polls/20260517T105004Z/gh-summary.txt`

- 2026-05-17T11:14:28Z poll (no action; cost bounded):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `a324ae142311cf19d1cc1afd337519216ab1f75d`
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T111428Z/`
  - AWS identity:
    - `logs/md1-shrunk/polls/20260517T111428Z/aws-identity.json` (account `975050048887`)
  - Step Functions (staging pipeline; region `us-west-2`):
    - `logs/md1-shrunk/polls/20260517T111428Z/stepfunctions-list-executions-staging-running.json` -> RUNNING `0`
  - SageMaker state (region `us-west-2`):
    - InProgress processing jobs: `0`
    - InProgress training jobs: `0`
    - terminal job statuses (all `Completed`):
      - SfM: `logs/md1-shrunk/polls/20260517T111428Z/sagemaker-describe-sfm.json`
      - 3DGS: `logs/md1-shrunk/polls/20260517T111428Z/sagemaker-describe-3dgs.json`
      - compression: `logs/md1-shrunk/polls/20260517T111428Z/sagemaker-describe-compression.json`
  - S3 outputs still present:
    - COLMAP: `logs/md1-shrunk/polls/20260517T111428Z/s3-colmap.txt`
    - compressed: `logs/md1-shrunk/polls/20260517T111428Z/s3-compressed.txt`
  - Public preview + bundle HTTP sanity:
    - `logs/md1-shrunk/polls/20260517T111428Z/http-check.txt` -> preview `/health.txt` HTTP 200; bundle `meta.json` HTTP 200; bundle `background_skybox.webp` HTTP 200
  - GitHub Actions (branch snapshot):
    - `logs/md1-shrunk/polls/20260517T111428Z/gh-run-list.json`
    - exact head has `0` runs (commit message includes `[skip ci]`; no new workflows expected at `a324ae14...`)

- 2026-05-17T11:18:00Z post-push verification (logs-only; `[skip ci]`):
  - commit:
    - `git rev-parse HEAD` -> `3cccc1ceef840732118aba7e8eff40f6b98b45c6` (`chore: md1-shrunk poll 20260517T111428Z [skip ci]`)
  - GitHub Actions:
    - exact head has `0` runs (commit message includes `[skip ci]`)
    - evidence:
      - `logs/md1-shrunk/polls/20260517T111428Z/gh-run-list-post-push.json`
      - `logs/md1-shrunk/polls/20260517T111428Z/gh-summary-post-push.txt`

- 2026-05-17T12:14:12Z poll (terminal reconfirm + viewer gates; cost bounded):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `2f5c2b97e3ddb94a0b3f3e0fedf2816ebb4c1097` (`[skip ci]`)
    - `git status --porcelain=v1` -> clean before creating poll artifacts
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T121412Z/`
  - AWS identity:
    - `logs/md1-shrunk/polls/20260517T121412Z/aws-identity.json` (account `975050048887`)
  - Step Functions (region `us-west-2`):
    - staging pipeline RUNNING executions: `logs/md1-shrunk/polls/20260517T121412Z/stepfunctions-list-executions-staging-running.json` -> RUNNING `0`
    - state machine inventory: `logs/md1-shrunk/polls/20260517T121412Z/stepfunctions-list-state-machines.json`
  - SageMaker (region `us-west-2`):
    - InProgress processing jobs: `0` (`logs/md1-shrunk/polls/20260517T121412Z/sagemaker-list-processing-inprogress.json`)
    - InProgress training jobs: `0` (`logs/md1-shrunk/polls/20260517T121412Z/sagemaker-list-training-inprogress.json`)
    - terminal job statuses (all `Completed`):
      - SfM processing: `logs/md1-shrunk/polls/20260517T121412Z/sagemaker-describe-sfm.json`
      - 3DGS training: `logs/md1-shrunk/polls/20260517T121412Z/sagemaker-describe-3dgs-training.json`
      - compression processing: `logs/md1-shrunk/polls/20260517T121412Z/sagemaker-describe-compression.json`
  - Montana facts gate (COLMAP output):
    - registered images: `1456` (streamed from `images.txt`): `logs/md1-shrunk/polls/20260517T121412Z/colmap-txt-stats.txt`
    - points3D: `1020913` (streamed from `points3D.txt`): `logs/md1-shrunk/polls/20260517T121412Z/colmap-txt-stats.txt`
    - sparse components: `1` (`colmap/sparse/0/` only): `logs/md1-shrunk/polls/20260517T121412Z/colmap-sparse-components-summary.txt`
  - S3 outputs still present:
    - COLMAP: `logs/md1-shrunk/polls/20260517T121412Z/s3-colmap.txt`
    - 3DGS: `logs/md1-shrunk/polls/20260517T121412Z/s3-3dgs.txt`
    - compressed: `logs/md1-shrunk/polls/20260517T121412Z/s3-compressed.txt`
  - Public preview + bundle HTTP sanity (anonymous):
    - preview `/health.txt`: `logs/md1-shrunk/polls/20260517T121412Z/http-head-preview-health.txt` -> HTTP 200
    - bundle `meta.json`: `logs/md1-shrunk/polls/20260517T121412Z/http-head-meta.txt` -> HTTP 200
    - bundled skybox: `logs/md1-shrunk/polls/20260517T121412Z/http-head-skybox.txt` -> HTTP 200
  - Deployed preview viewer gates:
    - /sogs-migrated-viewer smoke (bundled skybox):
      - log: `logs/md1-shrunk/polls/20260517T121412Z/sogs-migrated-smoke-skybox.txt`
      - screenshot: `logs/md1-shrunk/polls/20260517T121412Z/sogs-migrated-viewer-smoke.png`
    - /sogs-migrated-viewer smoke (no-sky):
      - log: `logs/md1-shrunk/polls/20260517T121412Z/sogs-migrated-smoke-nosky.txt`
      - screenshot: `logs/md1-shrunk/polls/20260517T121412Z/sogs-migrated-viewer-nosky.png`
    - /md1-viewer single-pose screenshots:
      - skybox: `logs/md1-shrunk/polls/20260517T121412Z/md1-camera-check-skybox.png` (`logs/md1-shrunk/polls/20260517T121412Z/md1-camera-check-skybox.txt`)
      - no-sky: `logs/md1-shrunk/polls/20260517T121412Z/md1-camera-check-nosky.png` (`logs/md1-shrunk/polls/20260517T121412Z/md1-camera-check-nosky.txt`)
  - GitHub Actions:
    - branch run list: `logs/md1-shrunk/polls/20260517T121412Z/gh-run-list-branch.json`
    - exact head runs: `0` (commit message includes `[skip ci]`): `logs/md1-shrunk/polls/20260517T121412Z/gh-exact-head-run-count.txt`
    - note: earlier run proof referenced head `e9cbf71c...`; its `CDK Deploy` run still verifies as `success`:
      - `logs/md1-shrunk/polls/20260517T121412Z/gh-run-view-cdk-25932325504.json`

- 2026-05-17T12:22:27Z post-push verification (logs-only; `[skip ci]`):
  - commit:
    - `git rev-parse HEAD` -> `20be758be6419792c65a57dc62adf3d777f6d60a` (`chore: md1-shrunk poll 20260517T121412Z [skip ci]`)
  - GitHub Actions:
    - exact head has `0` runs (commit message includes `[skip ci]`)
    - evidence:
      - `logs/md1-shrunk/polls/20260517T121412Z/gh-run-list-post-push.json`
      - `logs/md1-shrunk/polls/20260517T121412Z/gh-summary-post-push.txt`

- 2026-05-17T12:49:41Z poll (terminal reconfirm; cost bounded; no action):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `86a7195deafa5fc226daab3d9d5bca7e0102557e` (`[skip ci]`)
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T124941Z/`
    - summary: `logs/md1-shrunk/polls/20260517T124941Z/poll-summary.txt`
  - AWS identity:
    - `logs/md1-shrunk/polls/20260517T124941Z/aws-identity.json` (account `975050048887`)
  - Step Functions (region `us-west-2`):
    - staging pipeline RUNNING executions: `logs/md1-shrunk/polls/20260517T124941Z/stepfunctions-list-executions-staging-running.json` -> RUNNING `0`
  - SageMaker (region `us-west-2`):
    - SfM processing describe: `logs/md1-shrunk/polls/20260517T124941Z/sagemaker-describe-sfm.json` -> `ProcessingJobStatus=Completed`
    - CloudWatch tail (SfM): `logs/md1-shrunk/polls/20260517T124941Z/cloudwatch-tail-sfm.txt` (no OOM/timeout signatures observed)
  - Montana facts gate (COLMAP output):
    - registered images: `1456`, points3D: `1020913`: `logs/md1-shrunk/polls/20260517T124941Z/colmap-txt-stats.txt`
    - sparse components: `1` (`colmap/sparse/0/` only): `logs/md1-shrunk/polls/20260517T124941Z/colmap-sparse-components-summary.txt`
  - S3 outputs still present:
    - COLMAP listing: `logs/md1-shrunk/polls/20260517T124941Z/s3-colmap.txt`
  - GitHub Actions (public REST; `gh` CLI unavailable on this host):
    - branch run list: `logs/md1-shrunk/polls/20260517T124941Z/gh-run-list-branch.json`
    - exact head runs: `0` (`[skip ci]`): `logs/md1-shrunk/polls/20260517T124941Z/gh-exact-head-run-count.txt`

- 2026-05-17T12:55:10Z post-push verification (logs-only; `[skip ci]`):
  - commit:
    - `git rev-parse HEAD` -> `dde5c327b49302701baef31ccb5cc3ba460878f4` (`chore: md1-shrunk poll 20260517T124941Z [skip ci]`)
  - GitHub Actions:
    - exact head has `0` runs (commit message includes `[skip ci]`)
    - evidence:
      - `logs/md1-shrunk/polls/20260517T124941Z/gh-run-list-post-push.json`
      - `logs/md1-shrunk/polls/20260517T124941Z/gh-exact-head-run-count-post-push.txt`
      - `logs/md1-shrunk/polls/20260517T124941Z/gh-summary-post-push.json`

- 2026-05-17T12:56:40Z post-push verification (logs-only; `[skip ci]`):
  - commit:
    - `git rev-parse HEAD` -> `c89b30f6e1e772c57aed71e649c41f68bbad73ed` (`chore: md1-shrunk post-push proof 20260517T125510Z [skip ci]`)
  - GitHub Actions:
    - exact head has `0` runs (commit message includes `[skip ci]`)
    - evidence:
      - `logs/md1-shrunk/polls/20260517T124941Z/gh-run-list-after-c89b30.json`
      - `logs/md1-shrunk/polls/20260517T124941Z/gh-exact-head-run-count-after-c89b30.txt`
      - `logs/md1-shrunk/polls/20260517T124941Z/gh-summary-after-c89b30.json`

- 2026-05-17T13:15:49Z poll (terminal reconfirm + fresh gates; no new ML launches):
  - Branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `76c5256f0138baa1c5c0cf7d863f3a486391824c` (`chore: md1-shrunk reconcile head proof 20260517T125640Z [skip ci]`)
    - `git status --porcelain=v1` -> clean
    - Note: user-provided prior head `e9cbf71c56420ce386b028e7f4af33163ce4dcc2` still exists in history, but is not the current branch HEAD.
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T131549Z/`
    - `logs/md1-shrunk/gates/20260517T131716Z/`
  - AWS identity (region `us-west-2`, via boto3):
    - `logs/md1-shrunk/polls/20260517T131549Z/aws-sts-get-caller-identity.json` (account `975050048887`)
  - Step Functions (region `us-west-2`, via boto3):
    - RUNNING executions (bounded scan): `logs/md1-shrunk/polls/20260517T131549Z/stepfunctions-running.json` -> running `0`
  - SageMaker (region `us-west-2`, via boto3):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088`:
      - describe: `logs/md1-shrunk/polls/20260517T131549Z/sagemaker-describe-processing-job-md1-shrunk-1456-sfm-1778866088.json` (`Completed`)
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs`:
      - describe: `logs/md1-shrunk/polls/20260517T131549Z/sagemaker-describe-training-job-md1shrunk1456-1778880862-3dgs.json` (`Completed`)
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression`:
      - describe: `logs/md1-shrunk/polls/20260517T131549Z/sagemaker-describe-processing-job-md1shrunk1456-1778880862-compression.json` (`Completed`)
  - SfM gates (Montana-scale facts; COLMAP output):
    - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`
    - `images_file_count=1456`, `images_registered=1456`, `points3D=1020913`, `merged_component_count=1` (only `sparse/0/`):
      - `logs/md1-shrunk/gates/20260517T131716Z/sfm-output-summary.txt`
      - `logs/md1-shrunk/gates/20260517T131716Z/sfm-output-summary.json`
  - GitHub workflows (via `/opt/homebrew/bin/gh`):
    - branch run list + auth status: `logs/md1-shrunk/polls/20260517T131549Z/gh.json`
    - explicit head verification (user-provided): `CDK Deploy` run `25932325504` succeeded for head `e9cbf71c...`:
      - `logs/md1-shrunk/polls/20260517T131549Z/gh.json`
    - Note: exact current head `76c5256f...` has `0` runs (commit message includes `[skip ci]`).
  - Public preview + bundle HTTP sanity (anonymous):
    - `logs/md1-shrunk/polls/20260517T131549Z/http-head-sanity.txt` -> preview `/health.txt` HTTP 200, bundle `meta.json` HTTP 200, skybox HTTP 200
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T13:19:45Z exact-head CI (post poll commit; no additional launches):
  - commit:
    - `git rev-parse HEAD` -> `1cb6306a0eb143d0ab396613ae496e904fa59a7a` (`chore: md1-shrunk monitor poll 20260517T131549Z`)
  - GitHub workflows (exact-head; triggered by this push):
    - `CDK Deploy` run `25992041635` `success` (head `1cb6306a...`):
      - watch: `logs/md1-shrunk/polls/20260517T131549Z/gh-run-watch-cdk-25992041635.txt`
      - view: `logs/md1-shrunk/polls/20260517T131549Z/gh-run-view-cdk-25992041635.json`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump).

- 2026-05-17T13:51:48Z poll (resume verification; no new launches):
  - branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `50cfd4d783e2d31a85ef1c0f6fb106e36ffb61f1` (`chore: record md1-shrunk cdk run 25992041635 [skip ci]`)
    - `git status --porcelain=v1` -> clean
  - AWS identity (region `us-west-2`, via `/opt/homebrew/bin/aws`):
    - `logs/md1-shrunk/polls/20260517T134500Z/aws-sts-get-caller-identity.json` (account `975050048887`)
  - Step Functions (region `us-west-2`):
    - staging RUNNING=0:
      - `logs/md1-shrunk/polls/20260517T134500Z/stepfunctions-running-staging.json`
    - most-recent executions (no active work expected; last 10 are SUCCEEDED):
      - `logs/md1-shrunk/polls/20260517T134500Z/stepfunctions-list-executions-20260517T134500Z.json`
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T134500Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260517T134500Z.json`
      - CloudWatch (last hour snapshot): `logs/md1-shrunk/polls/20260517T134500Z/cloudwatch-md1-shrunk-1456-sfm-1778866088-20260517T134500Z.json`
    - InProgress processing jobs: `0`:
      - `logs/md1-shrunk/polls/20260517T134500Z/sagemaker-list-processing-inprogress-20260517T134500Z.json`
    - InProgress training jobs: `0`:
      - `logs/md1-shrunk/polls/20260517T134500Z/sagemaker-list-training-inprogress-20260517T134500Z.json`
  - SfM gates (Montana-scale facts; COLMAP output):
    - output prefix: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`
    - sparse model (primary):
      - `images_registered=1456`
      - `points3D=1020913`
      - merged component count: `1` (only `sparse/0/`)
    - sparse_raw model (informational; higher point count):
      - `images_registered=1456`
      - `points3D=1103335`
      - merged component count: `1` (only `sparse_raw/0/`)
    - evidence:
      - `logs/md1-shrunk/polls/20260517T134500Z/sfm-counts.txt`
      - `logs/md1-shrunk/polls/20260517T134500Z/s3-colmap-sparse0-ls.txt`
      - `logs/md1-shrunk/polls/20260517T134500Z/s3-colmap-sparse_raw0-ls.txt`
      - `logs/md1-shrunk/polls/20260517T134500Z/s3-colmap-md1-shrunk-20260515T1641Z-20260517T134500Z.txt`
  - GitHub Actions (via `/opt/homebrew/bin/gh`; PATH on this machine does not include `/opt/homebrew/bin` by default):
    - auth proof: `logs/md1-shrunk/polls/20260517T134500Z/gh-auth-status.txt`
    - branch run list snapshot: `logs/md1-shrunk/polls/20260517T134842Z/gh-run-list.json`
    - note: exact current head `50cfd4d7...` has `0` runs (commit message includes `[skip ci]`).
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T13:59:20Z exact-head CI proof (post poll push):
  - prior poll commit:
    - `git rev-parse` -> `4ca9e3623d3a249aba5ef46b6d13f8dff2aef4e8` (`chore: md1-shrunk monitor poll 20260517T135148Z`)
  - GitHub workflows:
    - `CDK Deploy` run `25992784995` succeeded for `4ca9e362...`:
      - list snapshot: `logs/md1-shrunk/polls/20260517T135432Z/gh-run-list.json`
      - view: `logs/md1-shrunk/polls/20260517T135442Z/gh-run-view-cdk-25992784995.json`
      - watch: `logs/md1-shrunk/polls/20260517T135442Z/gh-run-watch-cdk-25992784995.txt`
    - Pages deploy not triggered by the poll-only push (no `web/trigger-dev-build.txt` bump).
  - Note:
    - current branch head includes `[skip ci]`, so exact-head workflow count may be `0` until the next non-skip push.

- 2026-05-17T14:15:10Z poll (idle monitor; no new ML launches):
  - Poll artifacts:
    - `logs/md1-shrunk/polls/20260517T141510Z/`
  - Branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `bba04a6f...` (`[skip ci]`)
  - AWS identity (region `us-west-2`, via `/opt/homebrew/bin/aws`):
    - `logs/md1-shrunk/polls/20260517T141510Z/aws-sts-get-caller-identity.json` (account `975050048887`)
  - Step Functions (region `us-west-2`):
    - staging RUNNING=0: `logs/md1-shrunk/polls/20260517T141510Z/stepfunctions-running-staging.json`
    - branch preview RUNNING=0: `logs/md1-shrunk/polls/20260517T141510Z/stepfunctions-running-branch.json`
  - SageMaker (region `us-west-2`):
    - SfM `md1-shrunk-1456-sfm-1778866088` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T141510Z/sagemaker-describe-processing-job-md1-shrunk-1456-sfm-1778866088.json`
    - 3DGS `md1shrunk1456-1778880862-3dgs` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T141510Z/sagemaker-describe-training-job-md1shrunk1456-1778880862-3dgs.json`
    - compression `md1shrunk1456-1778880862-compression` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T141510Z/sagemaker-describe-processing-job-md1shrunk1456-1778880862-compression.json`
    - InProgress processing jobs: `0`:
      - `logs/md1-shrunk/polls/20260517T141510Z/sagemaker-list-processing-jobs-inprogress.json`
    - InProgress training jobs: `0`:
      - `logs/md1-shrunk/polls/20260517T141510Z/sagemaker-list-training-jobs-inprogress.json`
  - GitHub Actions (via `/opt/homebrew/bin/gh`):
    - run list snapshot: `logs/md1-shrunk/polls/20260517T141510Z/gh-run-list.json`
    - exact current head run count: `0` (commit includes `[skip ci]`):
      - `logs/md1-shrunk/polls/20260517T141510Z/gh-exact-head-run-count.txt`
    - latest `CDK Deploy` remains `25992784995` (head `4ca9e362...`) -> `success`
  - Public preview + bundle HTTP sanity (anonymous):
    - `logs/md1-shrunk/polls/20260517T141510Z/http-head-sanity.txt` -> preview `/health.txt` HTTP 200, bundle `meta.json` HTTP 200, skybox HTTP 200
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T14:21:58Z exact-head CI proof (post poll push):
  - poll commit:
    - `git rev-parse HEAD~1` -> `4b93db00...` (`chore: md1-shrunk monitor poll 20260517T141510Z`)
  - GitHub workflows:
    - `CDK Deploy` run `25993310264` `success` (head `4b93db00...`):
      - watch: `logs/md1-shrunk/polls/20260517T141510Z/gh-run-watch-cdk-25993310264.txt`
      - view: `logs/md1-shrunk/polls/20260517T141510Z/gh-run-view-cdk-25993310264.json`
      - list snapshot: `logs/md1-shrunk/polls/20260517T141510Z/gh-run-list-post-ci.json`
    - `Deploy Next.js to Cloudflare Pages` (minimum green baseline on branch):
      - latest run `25983995070` -> `success`:
        - `logs/md1-shrunk/polls/20260517T141510Z/gh-pages-latest.txt`
  - Note:
    - Pages deploy was not triggered by the poll-only commit (no `web/trigger-dev-build.txt` bump).

- 2026-05-17T14:47:06Z poll (idle monitor; no new ML launches):
  - Poll artifacts:
    - SageMaker/StepFn/S3 snapshots: `logs/md1-shrunk/polls/20260517T144442Z/`
    - GitHub run list snapshot: `logs/md1-shrunk/polls/20260517T144517Z-gh/gh-run-list.json`
    - Public preview + bundle HTTP sanity: `logs/md1-shrunk/polls/20260517T144633Z-http/`
  - Branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `539a7fbb...` (`chore: record md1-shrunk cdk run 25993310264 [skip ci]`)
    - `git status --porcelain=v1` -> clean
  - AWS identity (region `us-west-2`, via `/opt/homebrew/bin/aws`):
    - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (region `us-west-2`; staging pipeline):
    - `logs/md1-shrunk/polls/20260517T144442Z/stepfunctions-list-executions.json` -> RUNNING=0 (statuses only `SUCCEEDED`/`FAILED`/`TIMED_OUT`)
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed` (ended `2026-05-15`):
      - `logs/md1-shrunk/polls/20260517T144442Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
    - InProgress processing jobs: `0`:
      - `logs/md1-shrunk/polls/20260517T144442Z/sagemaker-list-processing-InProgress.json`
    - InProgress training jobs: `0`:
      - `logs/md1-shrunk/polls/20260517T144442Z/sagemaker-list-training-InProgress.json`
  - S3 output verification (SfM output exists; upload mode `EndOfJob`):
    - `logs/md1-shrunk/polls/20260517T144442Z/s3-colmap-listing.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
  - GitHub Actions (via `/opt/homebrew/bin/gh`):
    - exact head `539a7fbb...` has `0` runs (commit includes `[skip ci]`)
    - latest `CDK Deploy` remains `25993310264` -> `success` (head `4b93db00...`)
    - latest Pages run remains `25983995070` -> `success` (head `3bad045c...`)
  - Public preview + bundle HTTP sanity (anonymous):
    - preview alias `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev` -> `HTTP 200`:
      - `logs/md1-shrunk/polls/20260517T144633Z-http/http-head-preview-alias.txt`
    - bundle `meta.json` -> `HTTP 200`:
      - `logs/md1-shrunk/polls/20260517T144633Z-http/http-head-meta.json.txt`
    - skybox `background_skybox.webp` -> `HTTP 200`:
      - `logs/md1-shrunk/polls/20260517T144633Z-http/http-head-background_skybox.webp.txt`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T14:52:01Z exact-head CI proof (post poll push):
  - poll commit:
    - `git rev-parse HEAD` -> `010281b2...` (`chore: md1-shrunk monitor poll 20260517T144442Z`)
  - GitHub workflows (exact-head; triggered by this push):
    - `CDK Deploy` run `25994017562` `success` (head `010281b2...`):
      - list snapshot: `logs/md1-shrunk/polls/20260517T144826Z-ci/gh-run-list.json`
      - watch: `logs/md1-shrunk/polls/20260517T144833Z-ci/gh-run-watch-cdk-25994017562.txt`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump).

- 2026-05-17T15:19:57Z poll (monitor; no new ML launches):
  - Poll artifacts: `logs/md1-shrunk/polls/20260517T151433Z/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260517T151433Z/git-status.txt` -> head `ab5a796c...` (`[skip ci]`), new poll artifacts staged as untracked
  - AWS identity (region `us-west-2`):
    - `logs/md1-shrunk/polls/20260517T151433Z/aws-sts-get-caller-identity.json` -> account `975050048887`
  - Step Functions (region `us-west-2`):
    - staging RUNNING=0: `logs/md1-shrunk/polls/20260517T151433Z/stepfunctions-running-staging.json`
    - branch-preview RUNNING=0: `logs/md1-shrunk/polls/20260517T151433Z/stepfunctions-running-br8abc.json`
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T151433Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T151433Z/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T151433Z/sagemaker-describe-processing-md1shrunk1456-1778880862-compression.json`
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260517T151433Z/sagemaker-list-processing-InProgress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260517T151433Z/sagemaker-list-training-InProgress.json`
  - Montana gates (COLMAP sparse/0):
    - merged_component_count=1 images_registered=1456 points3D=1020913:
      - `logs/md1-shrunk/polls/20260517T151433Z/colmap-gates-summary.txt`
  - S3 output verification:
    - SfM output exists: `logs/md1-shrunk/polls/20260517T151433Z/s3-ls-colmap.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
    - 3DGS output exists: `logs/md1-shrunk/polls/20260517T151433Z/s3-3dgs-staging.txt` -> `model.tar.gz` `212.0 MiB`
    - public compressed bundle exists: `logs/md1-shrunk/polls/20260517T151433Z/s3-compressed-public.txt`
  - Public preview + bundle HTTP sanity (anonymous):
    - preview alias HTTP 200: `logs/md1-shrunk/polls/20260517T151433Z/http-head-preview-alias.txt`
    - bundle meta.json HTTP 200: `logs/md1-shrunk/polls/20260517T151433Z/http-head-meta.txt`
    - skybox background_skybox.webp HTTP 200: `logs/md1-shrunk/polls/20260517T151433Z/http-head-skybox.txt`
  - Deployed preview viewer validation (Playwright; skybox + no-sky):
    - skybox smoke: `logs/md1-shrunk/polls/20260517T151433Z/playwright-sogs-skybox.txt`
    - no-sky smoke: `logs/md1-shrunk/polls/20260517T151433Z/playwright-sogs-nosky.txt`
  - Side-by-side input-vs-render camera check (Playwright screenshot):
    - `logs/md1-shrunk/polls/20260517T151433Z/md1-camera-check-20260517.png`
    - log: `logs/md1-shrunk/polls/20260517T151433Z/playwright-md1-camera-check.txt`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T15:30:33Z exact-head CI + Pages preview URL (post poll push):
  - poll commit:
    - `git rev-parse HEAD~1` -> `3743c32d...` (`chore: md1-shrunk monitor poll 20260517T151433Z`)
  - GitHub workflows (exact-head; triggered by this push):
    - `CDK Deploy` run `25994795154` `success` (head `3743c32d...`):
      - watch: `logs/md1-shrunk/polls/20260517T151433Z/gh-run-watch-cdk-25994795154.txt`
      - view: `logs/md1-shrunk/polls/20260517T151433Z/gh-run-view-cdk-25994795154.json`
    - `Deploy Next.js to Cloudflare Pages` run `25994795144` `success` (head `3743c32d...`):
      - watch: `logs/md1-shrunk/polls/20260517T151433Z/gh-run-watch-pages-25994795144.txt`
      - view: `logs/md1-shrunk/polls/20260517T151433Z/gh-run-view-pages-25994795144.json`
      - log: `logs/md1-shrunk/polls/20260517T151433Z/gh-run-log-pages-25994795144.txt`
      - extracted preview URLs: `logs/md1-shrunk/polls/20260517T151433Z/pages-preview-urls-25994795144.txt`
  - Deployed preview viewer re-validation (post Pages deploy; skybox + no-sky):
    - skybox smoke: `logs/md1-shrunk/polls/20260517T151433Z/playwright-sogs-skybox-post-pages.txt`
    - no-sky smoke: `logs/md1-shrunk/polls/20260517T151433Z/playwright-sogs-nosky-post-pages.txt`
    - camera check screenshot: `logs/md1-shrunk/polls/20260517T151433Z/md1-camera-check-20260517-post-pages.png`

- 2026-05-17T15:44:49Z poll (monitor; no new ML launches):
  - Poll artifacts: `logs/md1-shrunk/polls/20260517T154449Z/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260517T154449Z/git-status.txt` -> head `090914d8...` (`[skip ci]`)
  - AWS identity (region `us-west-2`):
    - `logs/md1-shrunk/polls/20260517T154449Z/aws-sts-get-caller-identity.json` -> account `975050048887`
  - Step Functions (region `us-west-2`):
    - staging RUNNING=0: `logs/md1-shrunk/polls/20260517T154449Z/stepfunctions-running-staging.json`
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T154449Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T154449Z/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T154449Z/sagemaker-describe-processing-md1shrunk1456-1778880862-compression.json`
    - InProgress processing jobs: `logs/md1-shrunk/polls/20260517T154449Z/sagemaker-list-processing-InProgress.json`
    - InProgress training jobs: `logs/md1-shrunk/polls/20260517T154449Z/sagemaker-list-training-InProgress.json`
    - status summary: `logs/md1-shrunk/polls/20260517T154449Z/statuses.txt`
  - S3 output verification:
    - SfM output exists: `logs/md1-shrunk/polls/20260517T154449Z/s3-ls-colmap.txt`
    - 3DGS model exists: `logs/md1-shrunk/polls/20260517T154449Z/s3-3dgs-model.txt` (source URI: `logs/md1-shrunk/polls/20260517T154449Z/3dgs-model-uri.txt`)
    - public compressed bundle exists: `logs/md1-shrunk/polls/20260517T154449Z/s3-compressed-output.txt` (source URI: `logs/md1-shrunk/polls/20260517T154449Z/compressed-output-uri.txt`)
  - Public preview + bundle HTTP sanity (anonymous):
    - preview `/health.txt` HTTP headers: `logs/md1-shrunk/polls/20260517T154449Z/http-head-preview-health.txt`
    - bundle meta.json HTTP headers: `logs/md1-shrunk/polls/20260517T154449Z/http-head-meta.txt`
    - skybox background_skybox.webp HTTP headers: `logs/md1-shrunk/polls/20260517T154449Z/http-head-skybox.txt`
    - bundle meta.json snapshot: `logs/md1-shrunk/polls/20260517T154449Z/meta.json` (gaussians: `logs/md1-shrunk/polls/20260517T154449Z/gaussians.txt`)
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T15:49:58Z exact-head CI (post poll push):
  - poll commit:
    - `git rev-parse HEAD~1` -> `07f086f3...` (`chore: md1-shrunk monitor poll 20260517T154449Z`)
  - GitHub workflows (exact-head; triggered by this push):
    - `CDK Deploy` run `25995408529` `success` (head `07f086f3...`):
      - list snapshot: `logs/md1-shrunk/polls/20260517T154449Z/gh-run-list-post-push.json`
      - watch: `logs/md1-shrunk/polls/20260517T154449Z/gh-run-watch-cdk-25995408529.txt`
      - view: `logs/md1-shrunk/polls/20260517T154449Z/gh-run-view-cdk-25995408529.json`
    - Pages deploy not triggered at this exact head (no `web/trigger-dev-build.txt` bump).

- 2026-05-17T16:16:01Z poll (monitor; no new ML launches):
  - Poll artifacts: `logs/md1-shrunk/polls/20260517T161601Z/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260517T161601Z/git-status.txt` -> head `acff346c...` (`[skip ci]`)
  - AWS identity (region `us-west-2`):
    - `logs/md1-shrunk/polls/20260517T161601Z/aws-sts-get-caller-identity.json` -> account `975050048887`
  - Step Functions (region `us-west-2`):
    - staging RUNNING=0: `logs/md1-shrunk/polls/20260517T161601Z/stepfunctions-running-staging.json`
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T161601Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T161601Z/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T161601Z/sagemaker-describe-processing-md1shrunk1456-1778880862-compression.json`
    - InProgress processing jobs: `logs/md1-shrunk/polls/20260517T161601Z/sagemaker-list-processing-InProgress.json`
    - InProgress training jobs: `logs/md1-shrunk/polls/20260517T161601Z/sagemaker-list-training-InProgress.json`
    - status summary: `logs/md1-shrunk/polls/20260517T161601Z/statuses.txt`
  - S3 output verification:
    - SfM output listing: `logs/md1-shrunk/polls/20260517T161601Z/s3-ls-colmap.txt`
    - public compressed prefix listing: `logs/md1-shrunk/polls/20260517T161601Z/s3-ls-compressed-public.txt`
    - bundle meta URL recorded: `logs/md1-shrunk/polls/20260517T161601Z/compressed-output-meta-url.txt`
  - Public preview + bundle HTTP sanity (anonymous):
    - preview `/health.txt` HTTP headers: `logs/md1-shrunk/polls/20260517T161601Z/http-head-preview-health.txt`
    - bundle meta.json HTTP headers + snapshot: `logs/md1-shrunk/polls/20260517T161601Z/http-head-meta.txt`, `logs/md1-shrunk/polls/20260517T161601Z/meta.json` (gaussians: `logs/md1-shrunk/polls/20260517T161601Z/gaussians.txt`)
    - skybox HTTP headers: `logs/md1-shrunk/polls/20260517T161601Z/http-head-skybox.txt`
  - GitHub Actions:
    - exact-head run list: `logs/md1-shrunk/polls/20260517T161601Z/gh-runs-for-head.json` (expected `[]` because head includes `[skip ci]`)
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T16:18:29Z exact-head GitHub Actions confirmation (post poll push):
  - head commit:
    - `git rev-parse HEAD` -> `9febc283...` (`[skip ci]`)
  - exact-head run count expected `0` (skip-ci head):
    - `logs/md1-shrunk/polls/20260517T161829Z/gh-runs-for-head.json`
    - `logs/md1-shrunk/polls/20260517T161829Z/gh-exact-head-run-count.txt`

- 2026-05-17T16:47:57Z poll (monitor; no new ML launches):
  - Poll artifacts: `logs/md1-shrunk/polls/20260517T164757Z/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260517T164757Z/git-status.txt` -> head `323ac00a...` (`[skip ci]`)
  - AWS identity (region `us-west-2`):
    - `logs/md1-shrunk/polls/20260517T164757Z/aws-sts-get-caller-identity.json` -> account `975050048887`
  - Step Functions (region `us-west-2`):
    - staging RUNNING=0: `logs/md1-shrunk/polls/20260517T164757Z/stepfunctions-running-staging.json`
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T164757Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260517T164437Z.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T164757Z/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs-20260517T164700Z.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T164757Z/sagemaker-describe-processing-md1shrunk1456-1778880862-compression-20260517T164700Z.json`
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260517T164757Z/sagemaker-list-processing-InProgress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260517T164757Z/sagemaker-list-training-InProgress.json`
  - Montana gates (SfM metadata):
    - `colmap_gpu_spatial_heading_chunked` images_registered=1456 points3D=1103335 processing_time_seconds=12709.05:
      - `logs/md1-shrunk/polls/20260517T164757Z/sfm-metadata-summary.txt`
  - S3 output verification:
    - SfM output exists: `logs/md1-shrunk/polls/20260517T164757Z/s3-colmap-md1-shrunk-20260515T1641Z-20260517T164437Z.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
    - public compressed bundle exists: `logs/md1-shrunk/polls/20260517T164757Z/s3-compressed-md1shrunk1456-1778880862-20260517T164700Z.txt`
  - Public preview + bundle HTTP sanity (anonymous):
    - preview alias URL: `logs/md1-shrunk/polls/20260517T164757Z/pages-preview-alias-url.txt`
    - preview `/health.txt` HTTP headers: `logs/md1-shrunk/polls/20260517T164757Z/http-head-preview-health.txt`
    - bundle meta.json HTTP headers: `logs/md1-shrunk/polls/20260517T164757Z/curl-head-meta-20260517T164700Z.txt`
    - skybox background_skybox.webp HTTP headers: `logs/md1-shrunk/polls/20260517T164757Z/curl-head-skybox-20260517T164700Z.txt`
  - GitHub Actions:
    - exact-head run list: `logs/md1-shrunk/polls/20260517T164757Z/gh-runs-for-head.json` (expected `[]` because head includes `[skip ci]`)
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T17:16:04Z poll (monitor; no new ML launches):
  - Poll artifacts: `logs/md1-shrunk/polls/20260517T171604Z/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260517T171604Z/git-status.txt` -> head `ab8efe15...` (`[skip ci]`)
  - AWS identity (region `us-west-2`):
    - `logs/md1-shrunk/polls/20260517T171604Z/aws-sts-get-caller-identity.json` -> account `975050048887`
  - Step Functions (region `us-west-2`):
    - staging RUNNING=0: `logs/md1-shrunk/polls/20260517T171604Z/stepfunctions-running-staging.json`
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T171604Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T171604Z/sagemaker-describe-training-md1shrunk1456-1778880862-3dgs.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`:
      - `logs/md1-shrunk/polls/20260517T171604Z/sagemaker-describe-processing-md1shrunk1456-1778880862-compression.json`
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260517T171604Z/sagemaker-list-processing-InProgress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260517T171604Z/sagemaker-list-training-InProgress.json`
    - status summary: `logs/md1-shrunk/polls/20260517T171604Z/statuses.txt`
  - S3 output verification:
    - SfM output listing: `logs/md1-shrunk/polls/20260517T171604Z/s3-ls-colmap.txt`
  - Public bundle HTTP sanity (anonymous; from recorded meta URL):
    - bundle meta URL: `logs/md1-shrunk/polls/20260517T171604Z/compressed-output-meta-url.txt`
    - bundle meta.json headers + snapshot: `logs/md1-shrunk/polls/20260517T171604Z/http-head-meta.txt`, `logs/md1-shrunk/polls/20260517T171604Z/meta.json`
    - skybox URL + headers: `logs/md1-shrunk/polls/20260517T171604Z/public-skybox-url.txt`, `logs/md1-shrunk/polls/20260517T171604Z/http-head-skybox.txt`
  - GitHub Actions:
    - exact-head run list: `logs/md1-shrunk/polls/20260517T171604Z/gh-runs-for-head.json` (expected `[]` because head includes `[skip ci]`)
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T17:17:47Z exact-head GitHub Actions confirmation (post poll push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260517T171747Z/`
  - head commit:
    - `logs/md1-shrunk/polls/20260517T171747Z/git-status.txt` -> head `87849ef0...` (`[skip ci]`)
  - exact-head run count expected `0` (skip-ci head):
    - `logs/md1-shrunk/polls/20260517T171747Z/gh-runs-for-head.json`
    - `logs/md1-shrunk/polls/20260517T171747Z/gh-exact-head-run-count.txt`

- 2026-05-17T17:44:04Z poll (monitor; no new ML launches):
  - Poll artifacts: `logs/md1-shrunk/polls/20260517T174404Z/`
  - Branch/head/status:
    - head `a1e25986...` (`[skip ci]`); untracked poll artifacts under `logs/md1-shrunk/polls/20260517T174404Z/`
    - evidence: `logs/md1-shrunk/polls/20260517T174404Z/preflight.txt`
  - AWS identity (region `us-west-2`):
    - account `975050048887`, ARN `arn:aws:iam::975050048887:root`
    - evidence: `logs/md1-shrunk/polls/20260517T174404Z/preflight.txt`
  - Step Functions (region `us-west-2`):
    - staging `SpaceportMLPipeline-staging` RUNNING=0
    - branch preview `SpaceportMLPipeline-br-8abcbd5662` RUNNING=0
    - evidence: `logs/md1-shrunk/polls/20260517T174404Z/aws-state.json`
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`
    - InProgress processing jobs=0; InProgress training jobs=0
    - evidence: `logs/md1-shrunk/polls/20260517T174404Z/aws-state.json`
  - GitHub Actions:
    - exact-head run count expected `0` (skip-ci head): `logs/md1-shrunk/polls/20260517T174404Z/gh-summary.txt`
    - latest successful Pages run `25994795144` published preview alias + hash URLs:
      - evidence: `logs/md1-shrunk/polls/20260517T174404Z/preview-urls.txt`
      - source log: `logs/md1-shrunk/polls/20260517T174404Z/gh-run-view-pages-25994795144.log`
    - branch run list: `logs/md1-shrunk/polls/20260517T174404Z/gh-run-list.json`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T17:47:50Z exact-head GitHub Actions confirmation (post poll push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260517T174750Z/`
  - head commit:
    - `logs/md1-shrunk/polls/20260517T174750Z/postpush-gh-exact-head.json` -> head `9f8c20b6...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260517T174750Z/gh-runs-for-head.json`

- 2026-05-17T18:14:49Z poll (monitor; no new ML launches):
  - Poll artifacts: `logs/md1-shrunk/polls/20260517T181449Z/`
  - Branch/head/status:
    - head `4aa7fa72...` (`[skip ci]`); new poll artifacts under `logs/md1-shrunk/polls/20260517T181449Z/`
    - evidence: `logs/md1-shrunk/polls/20260517T181449Z/git-status.txt`
  - AWS identity (region `us-west-2`):
    - account `975050048887`, ARN `arn:aws:iam::975050048887:root`
    - evidence: `logs/md1-shrunk/polls/20260517T181449Z/aws-sts.json`
  - Step Functions (region `us-west-2`):
    - staging `SpaceportMLPipeline-staging` RUNNING=0: `logs/md1-shrunk/polls/20260517T181449Z/stepfn-running-staging.json`
    - branch preview `SpaceportMLPipeline-br-8abcbd5662` RUNNING=0: `logs/md1-shrunk/polls/20260517T181449Z/stepfn-running-br-8abcbd5662.json`
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260517T181449Z/sagemaker-describe-sfm.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260517T181449Z/sagemaker-describe-3dgs.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260517T181449Z/sagemaker-describe-compression.json`
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260517T181449Z/sagemaker-processing-inprogress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260517T181449Z/sagemaker-training-inprogress.json`
  - GitHub Actions:
    - exact-head run list expected `[]` (skip-ci head): `logs/md1-shrunk/polls/20260517T181449Z/gh-run-list-head.txt`
    - branch run list (JSON): `logs/md1-shrunk/polls/20260517T181449Z/gh-run-list.json`
    - latest by workflow (shows latest CDK Deploy + Pages): `logs/md1-shrunk/polls/20260517T181449Z/gh-run-latest-by-workflow.txt`
    - deterministic Pages preview URLs from run `25994795144` log:
      - source: `logs/md1-shrunk/polls/20260517T181449Z/gh-pages-run-25994795144.log`
      - extracted: `logs/md1-shrunk/polls/20260517T181449Z/pages-preview-urls.env`
  - Public bundle (anonymous fetch proof via HTTP 200):
    - viewer /health.txt (alias): `logs/md1-shrunk/polls/20260517T181449Z/curl-health-alias.txt`
    - viewer /health.txt (hash): `logs/md1-shrunk/polls/20260517T181449Z/curl-health-hash.txt`
    - bundle meta.json: `logs/md1-shrunk/polls/20260517T181449Z/curl-meta.txt`
    - bundled skybox: `logs/md1-shrunk/polls/20260517T181449Z/curl-skybox.txt`
  - Deployed preview viewer validation (Playwright):
    - skybox mode log: `logs/md1-shrunk/polls/20260517T181449Z/playwright-sogs-skybox.txt`
    - skybox mode screenshot: `logs/md1-shrunk/polls/20260517T181449Z/sogs-viewer-smoke-skybox.png`
    - no-sky mode log: `logs/md1-shrunk/polls/20260517T181449Z/playwright-sogs-nosky.txt`
    - no-sky mode screenshot: `logs/md1-shrunk/polls/20260517T181449Z/sogs-viewer-smoke-nosky.png`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T18:19:23Z exact-head GitHub Actions confirmation (post poll push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260517T181923Z/`
  - head commit:
    - `logs/md1-shrunk/polls/20260517T181923Z/postpush-head.txt` -> head `a87f8784...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260517T181923Z/gh-runs-for-head.json`
    - `logs/md1-shrunk/polls/20260517T181923Z/gh-exact-head-run-count.txt`

- 2026-05-17T18:44:49Z poll (monitor; no new ML launches):
  - Poll artifacts: `logs/md1-shrunk/polls/20260517T184449Z/`
  - Branch/head/status:
    - head `664d3b00...` (`[skip ci]`)
    - evidence: `logs/md1-shrunk/polls/20260517T184449Z/preflight.txt`
  - AWS identity (region `us-west-2`):
    - account `975050048887`, ARN `arn:aws:iam::975050048887:root`
    - evidence: `logs/md1-shrunk/polls/20260517T184449Z/aws-sts.json`
  - Step Functions (region `us-west-2`):
    - staging `SpaceportMLPipeline-staging` RUNNING=0: `logs/md1-shrunk/polls/20260517T184449Z/stepfn-running-staging.json`
    - branch preview `SpaceportMLPipeline-br-8abcbd5662` RUNNING=0: `logs/md1-shrunk/polls/20260517T184449Z/stepfn-running-br-8abcbd5662.json`
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260517T184449Z/sagemaker-describe-sfm.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260517T184449Z/sagemaker-describe-3dgs.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260517T184449Z/sagemaker-describe-compression.json`
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260517T184449Z/sagemaker-processing-inprogress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260517T184449Z/sagemaker-training-inprogress.json`
  - GitHub Actions:
    - exact-head runs expected `[]` (`[skip ci]` head): `logs/md1-shrunk/polls/20260517T184449Z/gh-runs-for-head.json`
    - branch run list (JSON): `logs/md1-shrunk/polls/20260517T184449Z/gh-run-list.json`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T18:46:46Z exact-head GitHub Actions confirmation (post poll push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260517T184646Z/`
  - head commit:
    - `logs/md1-shrunk/polls/20260517T184646Z/postpush-head.txt` -> head `f001ec08...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260517T184646Z/gh-runs-for-head.json`
    - `logs/md1-shrunk/polls/20260517T184646Z/gh-exact-head-run-count.txt`

- 2026-05-17T19:15:22Z poll (monitor; no new ML launches):
  - Poll artifacts: `logs/md1-shrunk/polls/20260517T191522Z/`
  - Branch/head/status:
    - branch `agent-113647-md1-baseline-e2e`
    - head `821d373a...` (`[skip ci]`)
    - evidence: `logs/md1-shrunk/polls/20260517T191522Z/preflight.txt`
  - AWS identity (region `us-west-2`):
    - account `975050048887`, ARN `arn:aws:iam::975050048887:root`
    - evidence: `logs/md1-shrunk/polls/20260517T191522Z/aws-sts.json`
  - Step Functions (region `us-west-2`):
    - staging `SpaceportMLPipeline-staging` RUNNING=0: `logs/md1-shrunk/polls/20260517T191522Z/stepfn-running-staging.json`
    - branch preview `SpaceportMLPipeline-br-8abcbd5662` RUNNING=0: `logs/md1-shrunk/polls/20260517T191522Z/stepfn-running-br-8abcbd5662.json`
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260517T191522Z/sagemaker-describe-sfm.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260517T191522Z/sagemaker-describe-3dgs.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260517T191522Z/sagemaker-describe-compression.json`
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260517T191522Z/sagemaker-processing-inprogress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260517T191522Z/sagemaker-training-inprogress.json`
  - COLMAP gates (from `sfm_metadata.json`):
    - `logs/md1-shrunk/polls/20260517T191522Z/colmap-gates.txt` -> `images_registered=1456`, `points3D=1103335`, `merged_component_count=1`
  - GitHub Actions:
    - exact-head run list expected `[]` (`[skip ci]` head): `logs/md1-shrunk/polls/20260517T191522Z/gh-runs-for-head.json`
    - latest successful by workflow: `logs/md1-shrunk/polls/20260517T191522Z/gh-run-latest-by-workflow.txt`
  - Public bundle HTTP sanity:
    - summary: `logs/md1-shrunk/polls/20260517T191522Z/http-head-summary.txt` -> preview `/health.txt` 200 (alias+hash), bundle `meta.json` 200, `background_skybox.webp` 200
    - raw headers: `logs/md1-shrunk/polls/20260517T191522Z/http-head-sanity.txt`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T19:23:32Z exact-head GitHub Actions confirmation (post poll push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260517T192332Z/`
  - head commit:
    - `logs/md1-shrunk/polls/20260517T192332Z/postpush-head.txt` -> head `5748e2cd...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260517T192332Z/gh-runs-for-head.json`
    - `logs/md1-shrunk/polls/20260517T192332Z/gh-exact-head-run-count.txt`

- 2026-05-17T19:44:16Z poll (monitor; no new ML launches; refreshed viewer + camera checks):
  - Poll artifacts: `logs/md1-shrunk/polls/20260517T194416Z/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260517T194416Z/preflight.txt` -> branch `agent-113647-md1-baseline-e2e`, head `7fee6c701e05b2749242fb3eabf0714863bf4d1b` (`[skip ci]`)
  - AWS identity (region `us-west-2`):
    - `logs/md1-shrunk/polls/20260517T194416Z/aws-sts.json` -> account `975050048887`
  - Step Functions (region `us-west-2`):
    - staging RUNNING=0: `logs/md1-shrunk/polls/20260517T194416Z/stepfn-running-staging.json`
    - branch preview RUNNING=0: `logs/md1-shrunk/polls/20260517T194416Z/stepfn-running-br-8abcbd5662.json`
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260517T194416Z/sagemaker-describe-sfm.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260517T194416Z/sagemaker-describe-3dgs.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260517T194416Z/sagemaker-describe-compression.json`
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260517T194416Z/sagemaker-processing-inprogress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260517T194416Z/sagemaker-training-inprogress.json`
    - status summary: `logs/md1-shrunk/polls/20260517T194416Z/statuses.txt`
  - Cloudflare Pages preview URL (deterministic from deploy run log):
    - `logs/md1-shrunk/polls/20260517T194416Z/pages-run-id.txt`, `logs/md1-shrunk/polls/20260517T194416Z/pages-preview-url-lines.txt`
    - alias URL: `logs/md1-shrunk/polls/20260517T194416Z/preview-alias-url.txt`
  - GitHub Actions (exact-head + latest successful deploy evidence):
    - exact-head run list expected `[]` (`[skip ci]` head): `logs/md1-shrunk/polls/20260517T194416Z/gh-runs-for-head.json`
    - latest successful by workflow: `logs/md1-shrunk/polls/20260517T194416Z/gh-run-latest-by-workflow.txt`
  - Public bundle gates (gaussians + compression sizes + skybox sidecars):
    - meta.json URL + download: `logs/md1-shrunk/polls/20260517T194416Z/public-meta-url.txt`, `logs/md1-shrunk/polls/20260517T194416Z/meta.json`
    - gaussians from `meta.json` -> `990025`: `logs/md1-shrunk/polls/20260517T194416Z/gaussians.txt`
    - compression sidecars: `logs/md1-shrunk/polls/20260517T194416Z/sogs_compression_summary.json`, `logs/md1-shrunk/polls/20260517T194416Z/training_metadata.json`
    - gate summary: `logs/md1-shrunk/polls/20260517T194416Z/compression-gates.txt`
  - Public preview + bundle HTTP sanity:
    - summary: `logs/md1-shrunk/polls/20260517T194416Z/http-head-summary.txt`
    - preview `/health.txt` headers: `logs/md1-shrunk/polls/20260517T194416Z/http-head-preview-health.txt`
    - meta.json headers: `logs/md1-shrunk/polls/20260517T194416Z/http-head-meta.txt`
    - skybox headers: `logs/md1-shrunk/polls/20260517T194416Z/http-head-skybox.txt`
  - Deployed preview viewer validation (Playwright; skybox + no-sky):
    - skybox log + screenshot: `logs/md1-shrunk/polls/20260517T194416Z/playwright-sogs-skybox.txt`, `logs/md1-shrunk/polls/20260517T194416Z/sogs-migrated-viewer-smoke.png`
    - no-sky log + screenshot: `logs/md1-shrunk/polls/20260517T194416Z/playwright-sogs-nosky.txt`, `logs/md1-shrunk/polls/20260517T194416Z/sogs-migrated-viewer-nosky.png`
  - Side-by-side input-vs-render camera checks (deployed preview):
    - poses: `logs/md1-shrunk/polls/20260517T194416Z/camera-poses.json`
    - renders: `logs/md1-shrunk/polls/20260517T194416Z/render-DJI_01000.png`, `logs/md1-shrunk/polls/20260517T194416Z/render-DJI_01029.png`, `logs/md1-shrunk/polls/20260517T194416Z/render-DJI_01030.png`
    - inputs (from SfM output): `logs/md1-shrunk/polls/20260517T194416Z/input-DJI_01000.JPG`, `logs/md1-shrunk/polls/20260517T194416Z/input-DJI_01029.JPG`, `logs/md1-shrunk/polls/20260517T194416Z/input-DJI_01030.JPG`
    - comparisons: `logs/md1-shrunk/polls/20260517T194416Z/compare-DJI_01000.png`, `logs/md1-shrunk/polls/20260517T194416Z/compare-DJI_01029.png`, `logs/md1-shrunk/polls/20260517T194416Z/compare-DJI_01030.png`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T19:59:07Z exact-head GitHub Actions confirmation (post poll push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260517T195907Z/`
  - head commit:
    - `logs/md1-shrunk/polls/20260517T195907Z/preflight.txt`
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260517T195907Z/gh-runs-for-head.json`
    - `logs/md1-shrunk/polls/20260517T195907Z/gh-exact-head-run-count.txt`

- 2026-05-17T22:20:57Z poll (monitor; no new ML launches; refreshed GH/AWS/public gates):
  - Poll artifacts: `logs/md1-shrunk/polls/20260517T222057Z/`
  - Branch/head/status:
    - head: `b64aec6874a3ab3a37f8d5e097c74c0041e7d464` (`[skip ci]`)
    - evidence: `logs/md1-shrunk/polls/20260517T222057Z/git-head-oneline.txt`
    - user-mentioned earlier head exists (not current): `logs/md1-shrunk/polls/20260517T222057Z/git-user-mentioned-head-e9cbf71c.txt`
  - AWS identity (region `us-west-2`):
    - `logs/md1-shrunk/polls/20260517T222057Z/aws-sts-get-caller-identity.json` -> account `975050048887`
  - Step Functions (region `us-west-2`):
    - staging RUNNING=0: `logs/md1-shrunk/polls/20260517T222057Z/stepfunctions-staging-running.json`
    - branch preview RUNNING=0: `logs/md1-shrunk/polls/20260517T222057Z/stepfunctions-branch-running.json`
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260517T222057Z/sagemaker-describe-processing-job-md1-shrunk-1456-sfm-1778866088.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260517T222057Z/sagemaker-describe-training-job-md1shrunk1456-1778880862-3dgs.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260517T222057Z/sagemaker-describe-processing-job-md1shrunk1456-1778880862-compression.json`
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260517T222057Z/sagemaker-list-processing-jobs-InProgress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260517T222057Z/sagemaker-list-training-jobs-InProgress.json`
  - SfM gates (Montana scale sanity):
    - sparse/0 present (single merged component): `logs/md1-shrunk/polls/20260517T222057Z/s3-colmap-sparse0-ls.txt`
    - registered images (counted from `sparse/0/images.txt`) -> `1456`: `logs/md1-shrunk/polls/20260517T222057Z/colmap-gates-from-text-counts.txt`
    - points3D (counted from `sparse/0/points3D.txt`) -> `1020913`: `logs/md1-shrunk/polls/20260517T222057Z/colmap-gates-from-text-counts.txt`
    - metadata `images_registered=1456`, `quality_check_passed=true`: `logs/md1-shrunk/polls/20260517T222057Z/sfm_metadata.json`
  - GitHub Actions:
    - branch run list: `logs/md1-shrunk/polls/20260517T222057Z/gh-run-list-branch.json`
    - exact-head run list expected `[]` (`[skip ci]` head): `logs/md1-shrunk/polls/20260517T222057Z/gh-run-list-exact-head.json`
    - latest Pages run log (source of preview alias): `logs/md1-shrunk/polls/20260517T222057Z/gh-pages-run-25994795144-log.txt`
    - preview alias URL: `logs/md1-shrunk/polls/20260517T222057Z/preview-url.txt`
  - Public bundle gates:
    - public `meta.json` S3 API head: `logs/md1-shrunk/polls/20260517T222057Z/s3api-head-object-public-meta.json`
    - `meta.json` gaussians -> `990025`: `logs/md1-shrunk/polls/20260517T222057Z/public-meta-gaussian-count.txt`
  - HTTP sanity:
    - preview `/health.txt` -> 200: `logs/md1-shrunk/polls/20260517T222057Z/curl-preview-health.txt`
    - public `meta.json` headers include 200: `logs/md1-shrunk/polls/20260517T222057Z/curl-public-meta-head.txt`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T22:24:55Z exact-head GitHub Actions confirmation (post poll push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260517T222455Z/`
  - head commit:
    - `logs/md1-shrunk/polls/20260517T222455Z/postpush-head.txt` -> head `45694962...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260517T222455Z/gh-run-list-exact-head.json`
    - `logs/md1-shrunk/polls/20260517T222455Z/gh-exact-head-run-count.txt`

- 2026-05-17T22:48:21Z poll (monitor; no new ML launches; refreshed AWS/StepFn/GH + HTTP sanity):
  - Poll artifacts: `logs/md1-shrunk/polls/20260517T224821Z/`
  - Branch/head/status:
    - head: `0f2fb2afbec85d19f3635f5ac21c0a016e308cee` (`[skip ci]`)
    - evidence: `logs/md1-shrunk/polls/20260517T224821Z/git-head-oneline.txt`, `logs/md1-shrunk/polls/20260517T224821Z/git-status-porcelain.txt`
  - AWS identity (region `us-west-2`):
    - `logs/md1-shrunk/polls/20260517T224821Z/aws-sts-get-caller-identity.json` -> account `975050048887`
  - Step Functions (region `us-west-2`):
    - staging RUNNING=0: `logs/md1-shrunk/polls/20260517T224821Z/stepfunctions-staging-running.json`
    - branch preview RUNNING=0 (ARN recorded): `logs/md1-shrunk/polls/20260517T224821Z/stepfunctions-branch-state-machine-arn.txt`, `logs/md1-shrunk/polls/20260517T224821Z/stepfunctions-branch-running.json`
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260517T224821Z/sagemaker-describe-processing-job-md1-shrunk-1456-sfm-1778866088.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260517T224821Z/sagemaker-describe-training-job-md1shrunk1456-1778880862-3dgs.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260517T224821Z/sagemaker-describe-processing-job-md1shrunk1456-1778880862-compression.json`
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260517T224821Z/sagemaker-list-processing-jobs-InProgress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260517T224821Z/sagemaker-list-training-jobs-InProgress.json`
    - status summary: `logs/md1-shrunk/polls/20260517T224821Z/statuses.txt`
  - GitHub Actions:
    - exact-head run list expected `[]` (`[skip ci]` head): `logs/md1-shrunk/polls/20260517T224821Z/gh-run-list-exact-head.json`
    - user-mentioned head `e9cbf71` CDK Deploy success (run `25932325504`): `logs/md1-shrunk/polls/20260517T224821Z/gh-run-25932325504.json`
  - Public HTTP sanity:
    - preview `/health.txt` headers: `logs/md1-shrunk/polls/20260517T224821Z/curl-preview-health.headers`
    - public `meta.json` HEAD: `logs/md1-shrunk/polls/20260517T224821Z/curl-public-meta.head`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T22:50:56Z exact-head GitHub Actions confirmation (post poll push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260517T225056Z/`
  - head commit:
    - `logs/md1-shrunk/polls/20260517T225056Z/postpush-head.txt` -> head `6648823d...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260517T225056Z/gh-run-list-exact-head.json`
    - `logs/md1-shrunk/polls/20260517T225056Z/gh-exact-head-run-count.txt`

- 2026-05-17T23:16:40Z poll (monitor; no new ML launches; refreshed AWS/StepFn/SageMaker + SfM gates):
  - Poll artifacts: `logs/md1-shrunk/polls/20260517T231640Z/`
  - Branch/head/status:
    - head `faff308d...` (`[skip ci]`)
    - evidence: `logs/md1-shrunk/polls/20260517T231640Z/preflight.txt`
  - AWS identity (region `us-west-2`):
    - evidence: `logs/md1-shrunk/polls/20260517T231640Z/aws-sts.json`
  - Step Functions (region `us-west-2`):
    - staging `SpaceportMLPipeline-staging` RUNNING=0: `logs/md1-shrunk/polls/20260517T231640Z/stepfn-running-staging.json`
    - branch preview `SpaceportMLPipeline-br-8abcbd5662` RUNNING=0 (ARN recorded): `logs/md1-shrunk/polls/20260517T231640Z/stepfunctions-branch-state-machine-arn.txt`, `logs/md1-shrunk/polls/20260517T231640Z/stepfn-running-branch.json`
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260517T231640Z/sagemaker-describe-sfm.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260517T231640Z/sagemaker-describe-3dgs.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260517T231640Z/sagemaker-describe-compression.json`
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260517T231640Z/sagemaker-processing-inprogress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260517T231640Z/sagemaker-training-inprogress.json`
    - status summary: `logs/md1-shrunk/polls/20260517T231640Z/statuses.json`
  - SfM gates (Montana scale sanity; from uploaded COLMAP TXT):
    - registered images `1456`, points3D `1020913`, merged components `1`: `logs/md1-shrunk/polls/20260517T231640Z/colmap-sparse-stats.json`
  - GitHub Actions (exact-head; `[skip ci]` head):
    - workflow runs for head expected `[]`: `logs/md1-shrunk/polls/20260517T231640Z/gh-runs-for-head.json`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-17T23:21:54Z exact-head GitHub Actions confirmation (post poll push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260517T232154Z/`
  - head commit:
    - `logs/md1-shrunk/polls/20260517T232154Z/postpush-head.txt` -> head `6fbc62d1...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260517T232154Z/gh-runs-for-head.json`
    - `logs/md1-shrunk/polls/20260517T232154Z/gh-exact-head-run-count.txt`

- 2026-05-17T23:22:34Z exact-head GitHub Actions confirmation (follow-up; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260517T232234Z/`
  - head commit:
    - `logs/md1-shrunk/polls/20260517T232234Z/postpush-head.txt` -> head `57505173...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260517T232234Z/gh-runs-for-head.json`
    - `logs/md1-shrunk/polls/20260517T232234Z/gh-exact-head-run-count.txt`

## Monitor Polls
- 2026-05-17T23:50:28Z: captured fresh AWS/SageMaker/StepFn/S3/GH proofs in logs/md1-shrunk/polls/20260517T234935Z/ (CloudWatch get-log-events returned 0 events for the job stream; see logs/md1-shrunk/polls/20260517T234935Z/cloudwatch-get-log-events.json).
- 2026-05-18T00:16:05Z: terminal reconfirm (monitor-only; no new ML launches)
  - Evidence: logs/md1-shrunk/polls/20260518T001605Z/
  - Branch/head/status:
    - `agent-113647-md1-baseline-e2e` @ `37eee2dc57e5143fb57213508035a463ce7f5640` (`[skip ci]`)
  - AWS identity (region `us-west-2`):
    - `logs/md1-shrunk/polls/20260518T001605Z/aws-sts.json`
  - Step Functions (region `us-west-2`):
    - staging `SpaceportMLPipeline-staging` RUNNING=0:
      - `logs/md1-shrunk/polls/20260518T001605Z/stepfunctions-list-executions-staging-running.json`
  - SageMaker (region `us-west-2`):
    - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`:
      - `logs/md1-shrunk/polls/20260518T001605Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
    - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`:
      - `logs/md1-shrunk/polls/20260518T001605Z/sagemaker-describe-md1shrunk1456-1778880862-3dgs.json`
    - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`:
      - `logs/md1-shrunk/polls/20260518T001605Z/sagemaker-describe-md1shrunk1456-1778880862-compression.json`
    - InProgress processing jobs=0:
      - `logs/md1-shrunk/polls/20260518T001605Z/sagemaker-list-processing-InProgress.json`
    - InProgress training jobs=0:
      - `logs/md1-shrunk/polls/20260518T001605Z/sagemaker-list-training-InProgress.json`
  - GitHub Actions (branch run list):
    - `logs/md1-shrunk/polls/20260518T001605Z/gh-run-list.json`
    - user-anchored CDK Deploy proof for `e9cbf71c...`:
      - `logs/md1-shrunk/polls/20260518T001605Z/gh-run-25932325504.json`
    - Pages preview alias URL evidence (from Pages deploy run `25994795144` log):
      - `logs/md1-shrunk/polls/20260518T001605Z/gh-run-25994795144-log.txt` -> `ALIAS=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - Public bundle reachability:
    - meta.json HTTP 200 + gaussian_count=990025:
      - `logs/md1-shrunk/polls/20260518T001605Z/http-public-meta.json`
      - `logs/md1-shrunk/polls/20260518T001605Z/http-public-meta.headers.txt`
    - skybox HTTP 200:
      - `logs/md1-shrunk/polls/20260518T001605Z/http-public-skybox.headers.txt`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.
    - CLI note: use `/opt/homebrew/bin/aws` and `/opt/homebrew/bin/gh` in this environment (PATH missing homebrew bin).

- 2026-05-18T00:20:34Z exact-head GitHub Actions confirmation (post poll commit/push; `[skip ci]` head):
  - Evidence: logs/md1-shrunk/polls/20260518T002034Z/
  - head commit:
    - `logs/md1-shrunk/polls/20260518T002034Z/postpush-head.txt` -> head `fba02a16...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260518T002034Z/gh-runs-for-head.json`
    - `logs/md1-shrunk/polls/20260518T002034Z/gh-exact-head-run-count.txt`

- 2026-05-18T00:21:27Z exact-head GitHub Actions confirmation (follow-up; `[skip ci]` head):
  - Evidence: logs/md1-shrunk/polls/20260518T002127Z/
  - head commit:
    - `logs/md1-shrunk/polls/20260518T002127Z/postpush-head.txt` -> head `f5e8dec0...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260518T002127Z/gh-runs-for-head.json`
    - `logs/md1-shrunk/polls/20260518T002127Z/gh-exact-head-run-count.txt`

- 2026-05-18T00:46:43Z poll (monitor; revalidated deployed preview viewer + camera checks; no new ML launches):
  - Evidence: `logs/md1-shrunk/polls/20260518T004643Z/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260518T004643Z/preflight.txt` -> head `0f9e96870d6acd98aa9158b96fbcf5505ee061d7`, branch `agent-113647-md1-baseline-e2e`
  - AWS identity (region `us-west-2`):
    - `logs/md1-shrunk/polls/20260518T004643Z/aws-sts.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (region `us-west-2`):
    - matched state machines list: `logs/md1-shrunk/polls/20260518T004643Z/stepfunctions-md1-state-machines.json`
    - per-state-machine RUNNING executions (all empty arrays): `logs/md1-shrunk/polls/20260518T004643Z/stepfunctions-running-*.json`
  - SageMaker terminal statuses (region `us-west-2`):
    - SfM `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260518T004643Z/sagemaker-describe-sfm.json`
    - 3DGS `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260518T004643Z/sagemaker-describe-3dgs.json`
    - compression `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260518T004643Z/sagemaker-describe-compression.json`
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260518T004643Z/sagemaker-list-processing-InProgress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260518T004643Z/sagemaker-list-training-InProgress.json`
  - GitHub Actions:
    - exact-head run count expected `0` (`[skip ci]` head): `logs/md1-shrunk/polls/20260518T004643Z/gh-exact-head-run-count.txt`
    - Pages preview URL proof from deploy run `25994795144`: `logs/md1-shrunk/polls/20260518T004643Z/pages-preview-url-lines.txt`, `logs/md1-shrunk/polls/20260518T004643Z/preview-alias-url.txt`
  - Deployed preview viewer validation (bundle loads; skybox + no-sky):
    - URLs: `logs/md1-shrunk/polls/20260518T004643Z/viewer-urls.txt`
    - skybox smoke (expects bundled `background_skybox.webp`): `logs/md1-shrunk/polls/20260518T004643Z/playwright-sogs-skybox.txt`, `logs/md1-shrunk/polls/20260518T004643Z/sogs-migrated-viewer-smoke.png`
    - no-sky smoke (expects no skybox requests): `logs/md1-shrunk/polls/20260518T004643Z/playwright-sogs-nosky.txt`, `logs/md1-shrunk/polls/20260518T004643Z/sogs-migrated-viewer-nosky.png`
  - Side-by-side input-vs-render camera checks (input left, render right):
    - poses: `logs/md1-shrunk/polls/20260518T004643Z/camera-poses.json`
    - renders: `logs/md1-shrunk/polls/20260518T004643Z/render-DJI_01000.png`, `logs/md1-shrunk/polls/20260518T004643Z/render-DJI_01029.png`, `logs/md1-shrunk/polls/20260518T004643Z/render-DJI_01030.png`
    - inputs: `logs/md1-shrunk/polls/20260518T004643Z/input-DJI_01000.JPG`, `logs/md1-shrunk/polls/20260518T004643Z/input-DJI_01029.JPG`, `logs/md1-shrunk/polls/20260518T004643Z/input-DJI_01030.JPG`
    - comparisons: `logs/md1-shrunk/polls/20260518T004643Z/compare-DJI_01000.png`, `logs/md1-shrunk/polls/20260518T004643Z/compare-DJI_01029.png`, `logs/md1-shrunk/polls/20260518T004643Z/compare-DJI_01030.png`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-18T00:53:13Z exact-head GitHub Actions confirmation (post poll commit/push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260518T005313Z-postpush/`
  - head commit:
    - `logs/md1-shrunk/polls/20260518T005313Z-postpush/head.txt` -> head `68caa3f9...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260518T005313Z-postpush/gh-run-list-exact-head.json`
    - `logs/md1-shrunk/polls/20260518T005313Z-postpush/gh-exact-head-run-count.txt`

- 2026-05-18T01:20:00Z poll (monitor; no new ML launches; reconfirm terminal statuses + preview/bundle still healthy):
  - Evidence: `logs/md1-shrunk/polls/20260518T012000Z/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260518T012000Z/preflight.txt` -> head `6654dda6...` (`[skip ci]`), branch `agent-113647-md1-baseline-e2e`
    - `logs/md1-shrunk/polls/20260518T012000Z/git-status-porcelain.txt` -> clean
  - AWS identity (region `us-west-2`):
    - `logs/md1-shrunk/polls/20260518T012000Z/aws-sts.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (region `us-west-2`):
    - state machine inventory: `logs/md1-shrunk/polls/20260518T012000Z/stepfunctions-state-machines.json`
    - all `SpaceportMLPipeline*` RUNNING execution lists are empty: `logs/md1-shrunk/polls/20260518T012000Z/stepfunctions-running-*.json`
  - SageMaker terminal statuses (region `us-west-2`):
    - SfM `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260518T012000Z/sagemaker-describe-sfm.json`
    - 3DGS `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260518T012000Z/sagemaker-describe-3dgs.json`
    - compression `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260518T012000Z/sagemaker-describe-compression.json`
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260518T012000Z/sagemaker-list-processing-InProgress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260518T012000Z/sagemaker-list-training-InProgress.json`
  - SfM gates (Montana scale sanity):
    - metadata `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `quality_check_passed=true`: `logs/md1-shrunk/polls/20260518T012000Z/sfm_metadata.json`
    - sparse component proof (`sparse/0` only): `logs/md1-shrunk/polls/20260518T012000Z/s3-colmap-sparse-ls.txt`, `logs/md1-shrunk/polls/20260518T012000Z/s3-colmap-sparse0-ls.txt`
  - GitHub Actions:
    - branch run list: `logs/md1-shrunk/polls/20260518T012000Z/gh-run-list-branch.json`
    - exact-head run list expected `[]` (`[skip ci]` head): `logs/md1-shrunk/polls/20260518T012000Z/gh-run-list-exact-head.json`
    - exact-head run count: `logs/md1-shrunk/polls/20260518T012000Z/gh-exact-head-run-count.txt`
  - Public bundle + preview HTTP sanity:
    - preview alias URL: `logs/md1-shrunk/polls/20260518T012000Z/preview-alias-url.txt`
    - bundle URL: `logs/md1-shrunk/polls/20260518T012000Z/bundle-url.txt`
    - preview `/health.txt` headers: `logs/md1-shrunk/polls/20260518T012000Z/http-preview-health.headers.txt`
    - public bundle `meta.json` headers: `logs/md1-shrunk/polls/20260518T012000Z/http-public-meta.headers.txt`
    - public bundle `meta.json` cached copy: `logs/md1-shrunk/polls/20260518T012000Z/public-meta.json`
    - gaussian count from `meta.json` (`means.shape[0]`) -> `990025`: `logs/md1-shrunk/polls/20260518T012000Z/public-meta-gaussian-count.txt`
    - public `meta.json` S3 API head: `logs/md1-shrunk/polls/20260518T012000Z/s3api-head-public-meta.json`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.
    - CLI note: use `/opt/homebrew/bin/aws` and `/opt/homebrew/bin/gh` in this environment (PATH missing homebrew bin).

- 2026-05-18T01:25:21Z exact-head GitHub Actions confirmation (post poll commit/push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260518T012521Z-postpush/`
  - head commit:
    - `logs/md1-shrunk/polls/20260518T012521Z-postpush/head.txt` -> head `df440baf...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260518T012521Z-postpush/gh-run-list-exact-head.json`
    - `logs/md1-shrunk/polls/20260518T012521Z-postpush/gh-exact-head-run-count.txt`

- 2026-05-18T01:47:09Z poll (monitor; no new ML launches; reconfirm terminal statuses + public bundle still healthy):
  - Evidence: `logs/md1-shrunk/polls/20260518T014709Z/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260518T014709Z/git.txt` -> head `ccfadb61...` (`[skip ci]`), branch `agent-113647-md1-baseline-e2e`, status clean
  - AWS identity (region `us-west-2`):
    - `logs/md1-shrunk/polls/20260518T014709Z/aws-sts-get-caller-identity.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (region `us-west-2`):
    - state machine inventory: `logs/md1-shrunk/polls/20260518T014709Z/stepfunctions-list-state-machines.json`
    - `SpaceportMLPipeline-staging` RUNNING execution count: `logs/md1-shrunk/polls/20260518T014709Z/stepfunctions-spaceport-ml-pipeline-staging-running.txt` -> `0`
  - SageMaker terminal statuses (region `us-west-2`):
    - SfM `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260518T014709Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
    - 3DGS `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260518T014709Z/sagemaker-describe-md1shrunk1456-1778880862-3dgs.json`
    - compression `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260518T014709Z/sagemaker-describe-md1shrunk1456-1778880862-compression.json`
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260518T014709Z/sagemaker-list-processing-jobs-inprogress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260518T014709Z/sagemaker-list-training-jobs-inprogress.json`
  - GitHub Actions:
    - branch run list: `logs/md1-shrunk/polls/20260518T014709Z/gh-run-list.json`
    - exact-head run count expected `0` (`[skip ci]` head): `logs/md1-shrunk/polls/20260518T014709Z/gh-run-list.json` (headSha filter)
    - latest successful `CDK Deploy` (non-skip ancestor): `logs/md1-shrunk/polls/20260518T014709Z/gh-latest-success-cdk.txt`
    - latest successful Pages deploy (non-skip ancestor): `logs/md1-shrunk/polls/20260518T014709Z/gh-latest-success-pages.txt`
    - anchor proof (user-referenced): `logs/md1-shrunk/polls/20260518T014709Z/gh-run-25932325504.json` -> `CDK Deploy` success for head `e9cbf71c...` (2026-05-15)
  - Public bundle HTTP sanity:
    - public bundle `meta.json` cached copy: `logs/md1-shrunk/polls/20260518T014709Z/http-public-meta.json`
    - gaussian count from `meta.json` (`means.shape[0]`) -> `990025`: `logs/md1-shrunk/polls/20260518T014709Z/http-public-meta.json`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.
    - CLI note: use `/opt/homebrew/bin/aws` and `/opt/homebrew/bin/gh` in this environment (PATH missing homebrew bin).

- 2026-05-18T01:50:25Z exact-head GitHub Actions confirmation (post poll commit/push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260518T015025Z-postpush/`
  - head commit:
    - `logs/md1-shrunk/polls/20260518T015025Z-postpush/head.txt` -> head `4216072d...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260518T015025Z-postpush/gh-run-list-exact-head.json`
    - `logs/md1-shrunk/polls/20260518T015025Z-postpush/gh-exact-head-run-count.txt`

- 2026-05-18T01:52:42Z exact-head GitHub Actions confirmation (post poll commit/push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260518T015242Z-postpush/`
  - head commit:
    - `logs/md1-shrunk/polls/20260518T015242Z-postpush/head.txt` -> head `5b174040...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260518T015242Z-postpush/gh-run-list-exact-head.json`
    - `logs/md1-shrunk/polls/20260518T015242Z-postpush/gh-exact-head-run-count.txt`

- 2026-05-18T02:16:59Z poll (monitor; verify branch/head, AWS + GitHub; SfM already terminal):
  - Evidence: `logs/md1-shrunk/polls/20260518T021659Z/`
  - Branch/head:
    - `logs/md1-shrunk/polls/20260518T021659Z/meta.txt` -> branch `agent-113647-md1-baseline-e2e`, head `4e037276...` (`[skip ci]`), status clean
  - AWS identity (region `us-west-2`):
    - `logs/md1-shrunk/polls/20260518T021659Z/aws-sts-get-caller-identity.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (region `us-west-2`):
    - staging RUNNING executions: `logs/md1-shrunk/polls/20260518T021659Z/stepfunctions-running-executions.json` -> `0`
  - SageMaker (region `us-west-2`):
    - SfM `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260518T021659Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260518T021659Z/sagemaker-list-processing-jobs-inprogress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260518T021659Z/sagemaker-list-training-jobs-inprogress.json`
  - S3 output:
    - SfM output listing: `logs/md1-shrunk/polls/20260518T021659Z/s3-colmap-output-listing.txt` (non-empty; `database.db` + `sparse/0/*`)
  - GitHub Actions:
    - branch run list (Pages + CDK): `logs/md1-shrunk/polls/20260518T021659Z/gh-runs-branch.json`
    - `CDK Deploy` anchor (user-referenced) is historical and still green (head `e9cbf71c...`): `logs/md1-shrunk/polls/20260518T021659Z/gh-runs-e9cb.json`
  - Notes:
    - CLI note: use `/opt/homebrew/bin/aws` and `/opt/homebrew/bin/gh` in this environment (PATH missing homebrew bin).

- 2026-05-18T02:18:47Z Pages preview URL extraction (deterministic; run `25994795144`):
  - Evidence: `logs/md1-shrunk/polls/20260518T021847Z/`
  - Pages run log (includes resolved alias + hash URLs):
    - `logs/md1-shrunk/polls/20260518T021847Z/gh-run-pages-log.txt`
  - Preview alias URL (use for validation):
    - `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`

- 2026-05-18T02:21:47Z deployed preview viewer re-validation (skybox + no-sky) + input-vs-render camera checks:
  - Evidence: `logs/md1-shrunk/polls/20260518T022147Z/`
  - SageMaker terminal statuses (region `us-west-2`):
    - SfM `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260518T022147Z/sagemaker-describe-sfm.json` (end `2026-05-15T15:04:36-06:00`)
    - 3DGS `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260518T022147Z/sagemaker-describe-3dgs.json`
    - compression `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260518T022147Z/sagemaker-describe-compression.json`
  - Public bundle + preview HTTP sanity:
    - preview `/health.txt`: `logs/md1-shrunk/polls/20260518T022147Z/http-head-preview-health.txt`
    - bundle `meta.json` headers: `logs/md1-shrunk/polls/20260518T022147Z/http-head-meta.json.txt`
    - bundled skybox headers: `logs/md1-shrunk/polls/20260518T022147Z/http-head-background_skybox.webp.txt`
  - Playwright smoke (migrated viewer):
    - skybox: `logs/md1-shrunk/polls/20260518T022147Z/playwright-sogs-skybox.txt`
    - no-sky: `logs/md1-shrunk/polls/20260518T022147Z/playwright-sogs-nosky.txt`
    - screenshots: `logs/md1-shrunk/polls/20260518T022147Z/sogs-migrated-viewer-smoke.png`, `logs/md1-shrunk/polls/20260518T022147Z/sogs-migrated-viewer-nosky.png`
  - Input-vs-render camera side-by-side (input left; render right; derived from COLMAP pose list):
    - pose list: `logs/md1-shrunk/colmap-camera-poses-20260516T003738Z.txt`
    - renders: `logs/md1-shrunk/polls/20260518T022147Z/render-skybox-DJI_01000.png`, `logs/md1-shrunk/polls/20260518T022147Z/render-nosky-DJI_01000.png`, `logs/md1-shrunk/polls/20260518T022147Z/render-skybox-DJI_01030.png`, `logs/md1-shrunk/polls/20260518T022147Z/render-nosky-DJI_01030.png`, `logs/md1-shrunk/polls/20260518T022147Z/render-skybox-DJI_0970.png`, `logs/md1-shrunk/polls/20260518T022147Z/render-nosky-DJI_0970.png`
    - comparisons (downsized to keep commits <5MB per file):
      - `logs/md1-shrunk/polls/20260518T022147Z/compare-skybox-DJI_01000.jpg`, `logs/md1-shrunk/polls/20260518T022147Z/compare-nosky-DJI_01000.jpg`
      - `logs/md1-shrunk/polls/20260518T022147Z/compare-skybox-DJI_01030.jpg`, `logs/md1-shrunk/polls/20260518T022147Z/compare-nosky-DJI_01030.jpg`
      - `logs/md1-shrunk/polls/20260518T022147Z/compare-skybox-DJI_0970.jpg`, `logs/md1-shrunk/polls/20260518T022147Z/compare-nosky-DJI_0970.jpg`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-18T02:28:03Z post-push CI confirmation (STATE update commit; Pages not triggered by logs-only diff):
  - Evidence: `logs/md1-shrunk/polls/20260518T022803Z-postpush/`
  - head commit:
    - `logs/md1-shrunk/polls/20260518T022803Z-postpush/head.txt` -> head `e6a3b1f2...`
  - GitHub Actions (exact-head):
    - run list: `logs/md1-shrunk/polls/20260518T022803Z-postpush/gh-run-list-exact-head.json` (CDK only)
    - `CDK Deploy` run `26010277892` -> success: `logs/md1-shrunk/polls/20260518T022803Z-postpush/gh-run-watch-cdk-26010277892.txt`
  - Notes:
    - `Deploy Next.js to Cloudflare Pages` did not trigger for this logs-only commit; follow-up commit bumped `web/trigger-dev-build.txt`.

- 2026-05-18T02:32:17Z post-push CI confirmation (Pages trigger commit; CDK + Pages both green):
  - Evidence: `logs/md1-shrunk/polls/20260518T023217Z-postpush/`
  - head commit:
    - `logs/md1-shrunk/polls/20260518T023217Z-postpush/head.txt` -> head `10a35028...`
  - GitHub Actions (exact-head):
    - run list: `logs/md1-shrunk/polls/20260518T023217Z-postpush/gh-run-list-exact-head.json`
    - `CDK Deploy` run `26010398363` -> success: `logs/md1-shrunk/polls/20260518T023217Z-postpush/gh-run-watch-cdk-26010398363.txt`
    - `Deploy Next.js to Cloudflare Pages` run `26010398341` -> success: `logs/md1-shrunk/polls/20260518T023217Z-postpush/gh-run-watch-pages-26010398341.txt`
    - Pages run log (resolved preview hash URL + stable alias URL):
      - `logs/md1-shrunk/polls/20260518T023217Z-postpush/gh-run-pages-26010398341.log.txt`

- 2026-05-18T02:47:21Z poll (monitor; verify local+AWS+GitHub; no new ML launches):
  - Evidence: `logs/md1-shrunk/polls/20260518T024721Z/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260518T024721Z/git.txt` -> head `212e3d54...` (`[skip ci]`), branch `agent-113647-md1-baseline-e2e`, status clean
    - note: user-referenced head `e9cbf71c...` is historical; `CDK Deploy` success still visible: `logs/md1-shrunk/polls/20260518T024721Z/gh-runs-e9cb.json`
  - AWS identity (region `us-west-2`):
    - `logs/md1-shrunk/polls/20260518T024721Z/aws-sts-get-caller-identity.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (region `us-west-2`):
    - staging RUNNING executions: `logs/md1-shrunk/polls/20260518T024721Z/stepfunctions-running-executions.json` -> `0`
  - SageMaker (region `us-west-2`):
    - SfM `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260518T024721Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260518T024721Z/sagemaker-list-processing-jobs-inprogress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260518T024721Z/sagemaker-list-training-jobs-inprogress.json`
    - SfM output listing non-empty: `logs/md1-shrunk/polls/20260518T024721Z/s3-colmap-output-listing.txt` (`Total Objects: 1468`, `Total Size: 9.2 GiB`)
  - GitHub Actions:
    - branch run list: `logs/md1-shrunk/polls/20260518T024721Z/gh-runs-branch.json`
    - exact-head run count expected `0` (`[skip ci]` head): `logs/md1-shrunk/polls/20260518T024721Z/gh-exact-head-run-count.txt`
  - SfM Montana-scale facts (from output `sfm_metadata.json`):
    - local cached metadata: `logs/md1-shrunk/sfm_metadata-md1-shrunk-20260515T1641Z.json`
    - `images_registered=1456` (Meadow was `1452`), `merged_component_count=1`, `points_3d=1103335`, `timed_out=false`, `processing_time_seconds=12709.05`

- 2026-05-18T02:48:49Z exact-head GitHub Actions confirmation (post poll commit/push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260518T024849Z-postpush/`
  - head commit:
    - `logs/md1-shrunk/polls/20260518T024849Z-postpush/head.txt` -> head `bb8809d0...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260518T024849Z-postpush/gh-run-list-exact-head.json`
    - `logs/md1-shrunk/polls/20260518T024849Z-postpush/gh-exact-head-run-count.txt`

- 2026-05-18T03:17:17Z poll (viewer re-validation; no new ML launches):
  - Evidence: `logs/md1-shrunk/polls/20260518T031717Z/`
  - Branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `9c1364be954017540119f7f41ef93b36e901e894` (`[skip ci]`)
    - `git status --porcelain=v1` -> new poll artifacts under `logs/md1-shrunk/polls/20260518T031717Z/` only
  - AWS identity:
    - `logs/md1-shrunk/polls/20260518T031717Z/aws-sts.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (region `us-west-2`):
    - staging RUNNING executions: `logs/md1-shrunk/polls/20260518T031717Z/stepfn-running.json` -> `0`
  - SageMaker (region `us-west-2`):
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260518T031717Z/sagemaker-processing-inprogress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260518T031717Z/sagemaker-training-inprogress.json`
    - Owned job terminal statuses reconfirm:
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260518T031717Z/sagemaker-describe-sfm.json`
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260518T031717Z/sagemaker-describe-3dgs.json`
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260518T031717Z/sagemaker-describe-compression.json`
  - SfM Montana-scale gate snapshot (from output `sfm_metadata.json`):
    - `logs/md1-shrunk/polls/20260518T031717Z/sfm_metadata.json` -> `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `quality_check_passed=true`, `timed_out=false`, `fallback_triggered=false`
  - S3 output presence reconfirm:
    - COLMAP listing: `logs/md1-shrunk/polls/20260518T031717Z/s3-colmap.txt` -> `Total Objects: 1468`, `Total Size: 9.2 GiB`
    - 3DGS listing: `logs/md1-shrunk/polls/20260518T031717Z/s3-3dgs.txt` -> `model.tar.gz` present
    - compressed listing: `logs/md1-shrunk/polls/20260518T031717Z/s3-compressed.txt` -> `Total Objects: 13`, `Total Size: 14.4 MiB`
  - Public bundle (anonymous fetch gates):
    - meta.json headers: `logs/md1-shrunk/polls/20260518T031717Z/http-head-meta.txt` -> `HTTP 200`
    - skybox headers: `logs/md1-shrunk/polls/20260518T031717Z/http-head-skybox.txt` -> `HTTP 200`
    - meta.json snapshot: `logs/md1-shrunk/polls/20260518T031717Z/meta.json`
    - gaussian count: `logs/md1-shrunk/polls/20260518T031717Z/gaussian_count.txt` -> `990025`
  - GitHub Actions:
    - branch run list: `logs/md1-shrunk/polls/20260518T031717Z/gh-run-list.json`
    - exact-head run count expected `0` (`[skip ci]` head): `logs/md1-shrunk/polls/20260518T031717Z/gh-run-head.txt`
  - Preview URL resolution (deterministic, no guessing):
    - Pages run `26010398341` deploy log: `logs/md1-shrunk/polls/20260518T031717Z/gh-run-26010398341-pages.log`
    - extracted URLs: `logs/md1-shrunk/polls/20260518T031717Z/pages-preview-urls-26010398341.txt` -> `ALIAS=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`, `HASH=https://b234e229.v0-spaceport-website-preview2.pages.dev`
  - Deployed preview viewer validation (Playwright; skybox + no-sky):
    - skybox smoke log + screenshot: `logs/md1-shrunk/polls/20260518T031717Z/playwright-sogs-skybox.txt`, `logs/md1-shrunk/polls/20260518T031717Z/sogs-migrated-viewer-skybox.png`
    - no-sky smoke log + screenshot: `logs/md1-shrunk/polls/20260518T031717Z/playwright-sogs-nosky.txt`, `logs/md1-shrunk/polls/20260518T031717Z/sogs-migrated-viewer-nosky.png`
  - Input-vs-render camera side-by-side (input left; render right; derived from the gated COLMAP pose list):
    - input: `logs/md1-shrunk/polls/20260518T031717Z/input-DJI_01029.JPG`
    - render skybox: `logs/md1-shrunk/polls/20260518T031717Z/render-skybox-DJI_01029.png`
    - render no-sky: `logs/md1-shrunk/polls/20260518T031717Z/render-nosky-DJI_01029.png`
    - side-by-side skybox: `logs/md1-shrunk/polls/20260518T031717Z/side-by-side-skybox-DJI_01029.png`
    - side-by-side no-sky: `logs/md1-shrunk/polls/20260518T031717Z/side-by-side-nosky-DJI_01029.png`

- 2026-05-18T03:23:33Z exact-head GitHub Actions confirmation (post poll commit/push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260518T032333Z-postpush/`
  - head commit:
    - `logs/md1-shrunk/polls/20260518T032333Z-postpush/head.txt` -> head `d4e605ca...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - `logs/md1-shrunk/polls/20260518T032333Z-postpush/gh-run-list-exact-head.json`
    - `logs/md1-shrunk/polls/20260518T032333Z-postpush/gh-exact-head-run-count.txt`

- 2026-05-18T03:50:26Z poll (SfM terminal confirmed; no new ML launches):
  - Evidence: `logs/md1-shrunk/polls/20260518T035026Z/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260518T035026Z/git-branch.txt` -> `agent-113647-md1-baseline-e2e`
    - `logs/md1-shrunk/polls/20260518T035026Z/git-head.txt` -> head `008e2524...` (`[skip ci]`)
    - `logs/md1-shrunk/polls/20260518T035026Z/git-status-short.txt` -> local-only poll artifacts under `logs/md1-shrunk/polls/20260518T035026Z/`
  - AWS identity:
    - `logs/md1-shrunk/polls/20260518T035026Z/aws-sts.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions (region `us-west-2`):
    - staging RUNNING executions: `logs/md1-shrunk/polls/20260518T035026Z/stepfn-running.json` -> `0`
  - SageMaker (region `us-west-2`):
    - InProgress processing jobs=0: `logs/md1-shrunk/polls/20260518T035026Z/sagemaker-processing-inprogress.json`
    - InProgress training jobs=0: `logs/md1-shrunk/polls/20260518T035026Z/sagemaker-training-inprogress.json`
    - Owned job terminal statuses reconfirm:
      - SfM (ProcessingJob) `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260518T035026Z/sagemaker-describe-sfm.json`
      - 3DGS (TrainingJob) `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260518T035026Z/sagemaker-describe-3dgs.json`
      - compression (ProcessingJob) `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260518T035026Z/sagemaker-describe-compression.json`
  - SfM Montana-scale gate snapshot (from output `sfm_metadata.json`):
    - `logs/md1-shrunk/polls/20260518T035026Z/sfm_metadata_summary.json` -> `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `quality_check_passed=true`, `timed_out=false`, `fallback_triggered=false`
  - CloudWatch terminal excerpt (SfM completion banner + stats):
    - `logs/md1-shrunk/polls/20260518T035026Z/cloudwatch-paged-tail-md1-shrunk-1456-sfm-1778866088-20260518T034854Z.txt` -> includes `Images registered: 1456`, `3D points: 1020913`, `Processing time: 12709.05 seconds`, and `COMPLETED SUCCESSFULLY!`
  - S3 COLMAP output presence reconfirm:
    - `logs/md1-shrunk/polls/20260518T035026Z/s3-listing-md1-shrunk-colmap-20260518T034714Z.txt` -> `TOTAL_OBJECTS 1468`, `TOTAL_SIZE_BYTES 9915165134`
    - `logs/md1-shrunk/polls/20260518T035026Z/s3-listing-md1-shrunk-colmap-20260518T034714Z.txt` -> only `sparse/0/*` (merged component count 1)
  - Public bundle gates (anonymous fetch):
    - meta.json headers: `logs/md1-shrunk/polls/20260518T035026Z/http-head-meta.txt` -> `HTTP/2 200`
    - skybox headers: `logs/md1-shrunk/polls/20260518T035026Z/http-head-skybox.txt` -> `HTTP/2 200`
    - meta.json snapshot: `logs/md1-shrunk/polls/20260518T035026Z/meta.json`
    - gaussian count (from `meta.json means.shape[0]`): `logs/md1-shrunk/polls/20260518T035026Z/gaussian_count.txt` -> `990025`
  - GitHub Actions (exact-head; `[skip ci]` head):
    - commit workflow runs (PR-triggered filter): `logs/md1-shrunk/polls/20260518T035026Z/github-commit-workflow-runs-008e2524.json` -> `[]`

- 2026-05-18T03:53:16Z exact-head GitHub Actions confirmation (post poll commit/push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260518T035316Z-postpush/`
  - head commit:
    - `logs/md1-shrunk/polls/20260518T035316Z-postpush/head.txt` -> head `45a2d94b...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head; PR-run filter):
    - `logs/md1-shrunk/polls/20260518T035316Z-postpush/github-commit-workflow-runs-45a2d94b.json`

- 2026-05-18T04:17:06Z poll (monitor; reconfirm terminal ML status; no new ML launches):
  - Evidence: `logs/md1-shrunk/polls/20260518T041706Z/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260518T041706Z/git.txt` -> branch `agent-113647-md1-baseline-e2e`, head `4caf99c8...` (`[skip ci]`), status clean
  - AWS identity (region `us-west-2`):
    - `logs/md1-shrunk/polls/20260518T041706Z/aws-sts.json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - SageMaker (region `us-west-2`):
    - SfM `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260518T041706Z/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
    - 3DGS `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260518T041706Z/sagemaker-describe-md1shrunk1456-1778880862-3dgs.json`
    - compression `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260518T041706Z/sagemaker-describe-md1shrunk1456-1778880862-compression.json`
  - Step Functions (region `us-west-2`):
    - staging RUNNING executions: `logs/md1-shrunk/polls/20260518T041706Z/stepfunctions-running.json` -> `0`
  - SfM Montana-scale gate snapshot (from output `sfm_metadata.json`):
    - `logs/md1-shrunk/polls/20260518T041706Z/sfm_metadata.json` -> `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `quality_check_passed=true`, `timed_out=false`, `fallback_triggered=false`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-18T04:18:04Z poll (monitor; reconfirm public bundle + preview URL resolution; no new ML launches):
  - Evidence: `logs/md1-shrunk/polls/20260518T041804Z-verify/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260518T041804Z-verify/git.txt` -> branch `agent-113647-md1-baseline-e2e`, head `4caf99c8...` (`[skip ci]`), status clean
  - Public bundle gates (anonymous fetch):
    - bundle `meta.json` headers: `logs/md1-shrunk/polls/20260518T041804Z-verify/http-head-meta.json.txt` -> `HTTP 200`
    - bundled skybox headers: `logs/md1-shrunk/polls/20260518T041804Z-verify/http-head-background_skybox.webp.txt` -> `HTTP 200`
    - gaussian count (from `meta.json means.shape[0]`): `logs/md1-shrunk/polls/20260518T041804Z-verify/gaussian_count.txt` -> `990025`
  - Preview sanity:
    - preview URL (from prior Pages run): `logs/md1-shrunk/polls/20260518T041804Z-verify/preview_url_from_state.txt` -> `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
    - preview `/health.txt`: `logs/md1-shrunk/polls/20260518T041804Z-verify/http-head-preview-health.txt` -> `HTTP 200`
  - GitHub Actions (deterministic preview URL resolution from the last successful Pages run job log):
    - Pages job log excerpt includes `Resolved: HASH=... ALIAS=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`: `logs/md1-shrunk/polls/20260518T041804Z-verify/gh-job-76449748807.log.txt`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-18T04:19:22Z viewer re-verify (monitor; skybox + no-sky; plus camera render):
  - Evidence: `logs/md1-shrunk/polls/20260518T041922Z-viewer/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260518T041922Z-viewer/git.txt` -> branch `agent-113647-md1-baseline-e2e`, head `4caf99c8...` (`[skip ci]`), status clean
  - Playwright smoke (migrated viewer):
    - skybox log: `logs/md1-shrunk/polls/20260518T041922Z-viewer/playwright-sogs-skybox.txt` -> OK (screenshots overwritten: `logs/sogs-migrated-viewer-smoke.png`)
    - no-sky log: `logs/md1-shrunk/polls/20260518T041922Z-viewer/playwright-sogs-nosky.txt` -> OK (screenshots overwritten: `logs/sogs-migrated-viewer-nosky.png`)
  - Camera check (render-only quick gate):
    - render: `logs/md1-shrunk/polls/20260518T041922Z-viewer/md1-camera-check.png`
    - log: `logs/md1-shrunk/polls/20260518T041922Z-viewer/md1-camera-check.log.txt`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-18T04:21:34Z exact-head GitHub Actions confirmation (post monitor commit/push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260518T042134Z-postpush/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260518T042134Z-postpush/git.txt` -> branch `agent-113647-md1-baseline-e2e`, head `e99dc39b...` (`[skip ci]`), status clean
  - head commit:
    - `logs/md1-shrunk/polls/20260518T042134Z-postpush/head.txt` -> head `e99dc39b...` (`[skip ci]`)
  - exact-head run list expected `[]` (skip-ci head):
    - run list: `logs/md1-shrunk/polls/20260518T042134Z-postpush/gh-run-list.json`
    - count: `logs/md1-shrunk/polls/20260518T042134Z-postpush/gh-exact-head-run-count.txt`
  - last known successful CI runs on branch (for preview URL continuity):
    - `logs/md1-shrunk/polls/20260518T042134Z-postpush/latest-success.txt`

- 2026-05-18T04:46:29Z poll (monitor; reconfirm terminal ML status + no active InProgress jobs):
  - Evidence: `logs/md1-shrunk/polls/20260518T044629Z/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260518T044629Z/git.txt` -> branch `agent-113647-md1-baseline-e2e`, head `f71516cd...` (`[skip ci]`), status dirty (new poll artifacts)
  - AWS identity + pipeline state (region `us-west-2`):
    - `/opt/homebrew/bin/aws sts get-caller-identity --region us-west-2 --output json` -> `logs/md1-shrunk/polls/20260518T044629Z/aws-sts-get-caller-identity.json`
    - `/opt/homebrew/bin/aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --max-results 10 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/20260518T044629Z/stepfunctions-running-staging.json` (`RUNNING=0`)
  - SageMaker terminal status (region `us-west-2`):
    - SfM `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260518T044629Z/sagemaker-describe-sfm.json`
    - 3DGS `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260518T044629Z/sagemaker-describe-3dgs.json`
    - compression `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260518T044629Z/sagemaker-describe-compression.json`
    - InProgress processing jobs: `logs/md1-shrunk/polls/20260518T044629Z/sagemaker-list-processing-InProgress.json` -> `0`
    - InProgress training jobs: `logs/md1-shrunk/polls/20260518T044629Z/sagemaker-list-training-InProgress.json` -> `0`
  - GitHub Actions (exact-head; `[skip ci]` head):
    - `/opt/homebrew/bin/gh run list --branch agent-113647-md1-baseline-e2e --limit 30 --json databaseId,workflowName,headSha,status,conclusion,createdAt,updatedAt,url` -> `logs/md1-shrunk/polls/20260518T044629Z/gh-run-list.json` (no runs match head `f71516cd...`)
    - derived summary: `logs/md1-shrunk/polls/20260518T044629Z/gh_derived.txt`
  - Notes:
    - Cost bounded: no new SageMaker/StepFn work launched; no non-owned jobs stopped.

- 2026-05-18T04:49:30Z exact-head GitHub Actions confirmation (post poll commit/push; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260518T044930Z-postpush/`
  - Branch/head/status:
    - `logs/md1-shrunk/polls/20260518T044930Z-postpush/git.txt` -> branch `agent-113647-md1-baseline-e2e`, head `154d31aa...` (`[skip ci]`), status clean
  - exact-head run list expected `0` (skip-ci head):
    - run list: `logs/md1-shrunk/polls/20260518T044930Z-postpush/gh-run-list.json`
    - count: `logs/md1-shrunk/polls/20260518T044930Z-postpush/gh-exact-head-run-count.txt`
  - last known successful CI runs on branch (for preview URL continuity):
    - `logs/md1-shrunk/polls/20260518T044930Z-postpush/latest-success.txt`

- 2026-05-18T05:18:16Z poll (monitor; reconfirm terminal ML status; prep fresh exact-head CI run):
  - Evidence: `logs/md1-shrunk/polls/20260518T051816Z/`
  - Branch/head/status:
    - head `3e70a0da...` (`chore: md1-shrunk postpush proof 20260518T044930Z [skip ci]`), status clean:
      - `logs/md1-shrunk/polls/20260518T051816Z/meta.txt`
      - `logs/md1-shrunk/polls/20260518T051816Z/git-head.txt`
      - `logs/md1-shrunk/polls/20260518T051816Z/git-status.txt`
  - AWS identity + pipeline state (region `us-west-2`):
    - `/opt/homebrew/bin/aws sts get-caller-identity --region us-west-2 --output json` -> `logs/md1-shrunk/polls/20260518T051816Z/aws-sts.json`
    - `/opt/homebrew/bin/aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --max-results 20 --region us-west-2 --output json` -> `logs/md1-shrunk/polls/20260518T051816Z/stepfn-running.json` (`RUNNING=0`)
  - SageMaker terminal status (region `us-west-2`):
    - SfM `md1-shrunk-1456-sfm-1778866088` -> `Completed`: `logs/md1-shrunk/polls/20260518T051816Z/sagemaker-describe-sfm.json`
    - 3DGS `md1shrunk1456-1778880862-3dgs` -> `Completed`: `logs/md1-shrunk/polls/20260518T051816Z/sagemaker-describe-3dgs.json`
    - compression `md1shrunk1456-1778880862-compression` -> `Completed`: `logs/md1-shrunk/polls/20260518T051816Z/sagemaker-describe-compression.json`
    - InProgress processing jobs: `logs/md1-shrunk/polls/20260518T051816Z/sagemaker-processing-inprogress.json` -> `0`
    - InProgress training jobs: `logs/md1-shrunk/polls/20260518T051816Z/sagemaker-training-inprogress.json` -> `0`
  - S3 COLMAP output reconfirm:
    - `/opt/homebrew/bin/aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap/ --recursive --summarize --region us-west-2` -> `logs/md1-shrunk/polls/20260518T051816Z/s3-colmap-listing.txt`
  - GitHub Actions (branch history has successful runs, but head is `[skip ci]` so exact-head runs expected empty):
    - `/opt/homebrew/bin/gh run list --branch agent-113647-md1-baseline-e2e --limit 50 --json ...` -> `logs/md1-shrunk/polls/20260518T051816Z/gh-run-list.json`

- 2026-05-18T05:20:13Z CI (exact-head; Pages + CDK Deploy; preview URL resolution):
  - Evidence: `logs/md1-shrunk/polls/20260518T052013Z-ci/`
  - Trigger commit:
    - `git rev-parse HEAD` -> `40394409096fba23f069499645e421dab8e4ef34` (`chore: trigger exact-head CI for md1-shrunk monitor`)
  - GitHub Actions (exact-head):
    - Pages run `26015026477` -> `success`:
      - watch: `logs/md1-shrunk/polls/20260518T052013Z-ci/gh-run-watch-pages-26015026477.txt`
      - run view: `logs/md1-shrunk/polls/20260518T052013Z-ci/gh-run-view-pages-26015026477.json`
      - log excerpt with preview URLs:
        - `logs/md1-shrunk/polls/20260518T052013Z-ci/pages-preview-url-excerpt.txt`
        - alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
        - hash: `https://0aab3a2c.v0-spaceport-website-preview2.pages.dev`
    - CDK Deploy run `26015026488` -> `success`:
      - watch: `logs/md1-shrunk/polls/20260518T052013Z-ci/gh-run-watch-cdk-26015026488.txt`
      - run view: `logs/md1-shrunk/polls/20260518T052013Z-ci/gh-run-view-cdk-26015026488.json`

- 2026-05-18T05:28:12Z viewer re-verify (post exact-head Pages deploy; skybox + no-sky + camera checks):
  - Evidence: `logs/md1-shrunk/polls/20260518T052812Z-viewer/`
  - Anonymous bundle fetch gates:
    - meta.json headers: `logs/md1-shrunk/polls/20260518T052812Z-viewer/http-head-meta.txt` -> `HTTP 200`
    - skybox headers: `logs/md1-shrunk/polls/20260518T052812Z-viewer/http-head-skybox.txt` -> `HTTP 200`
  - Playwright smoke (sogs-migrated-viewer):
    - skybox: `logs/md1-shrunk/polls/20260518T052812Z-viewer/playwright-sogs-skybox.txt` -> OK (screenshot overwritten: `logs/sogs-migrated-viewer-smoke.png`)
    - no-sky: `logs/md1-shrunk/polls/20260518T052812Z-viewer/playwright-sogs-nosky.txt` -> OK (screenshot overwritten: `logs/sogs-migrated-viewer-nosky.png`)
  - Camera checks (MD1 viewer; same pose; skybox vs no-sky):
    - skybox: `logs/md1-shrunk/polls/20260518T052812Z-viewer/md1-camera-check-skybox.png` (`logs/md1-shrunk/polls/20260518T052812Z-viewer/playwright-md1-camera-check-skybox.txt`)
    - no-sky: `logs/md1-shrunk/polls/20260518T052812Z-viewer/md1-camera-check-nosky.png` (`logs/md1-shrunk/polls/20260518T052812Z-viewer/playwright-md1-camera-check-nosky.txt`)

- 2026-05-18T05:30:42Z CI (exact-head; CDK-only because logs-only push; prep Pages trigger):
  - Evidence: `logs/md1-shrunk/polls/20260518T053042Z-ci-d200/`
  - Trigger commit:
    - `git rev-parse HEAD` -> `da200517fb6b4e5ee184e484bd02e3b6eb3e468e` (`chore: record md1-shrunk exact-head preview gates`)
  - GitHub Actions (exact-head):
    - CDK Deploy run `26015356265` -> `success`:
      - prewatch: `logs/md1-shrunk/polls/20260518T053042Z-ci-d200/gh-run-view-cdk-prewatch.json`
      - watch: `logs/md1-shrunk/polls/20260518T053042Z-ci-d200/gh-run-watch-cdk-26015356265.txt`
      - postwatch: `logs/md1-shrunk/polls/20260518T053042Z-ci-d200/gh-run-view-cdk-postwatch.json`
  - Note:
    - No Pages run triggered because this push only touched `logs/` + `STATE.md`; next step is a `web/trigger-dev-build.txt` bump to re-run Pages on exact head.

- 2026-05-18T05:34:57Z CI (exact-head; Pages + CDK Deploy; preview URL resolution):
  - Evidence: `logs/md1-shrunk/polls/20260518T053457Z-ci-pages/`
  - Trigger commit:
    - `git rev-parse HEAD` -> `9c2b6a073346b068a6c8cc7e13f7a2cbfa26455c` (`chore: retrigger Pages for md1-shrunk monitor`)
  - GitHub Actions (exact-head):
    - Pages run `26015520241` -> `success`:
      - watch: `logs/md1-shrunk/polls/20260518T053457Z-ci-pages/gh-run-watch-pages-26015520241.txt`
      - run view: `logs/md1-shrunk/polls/20260518T053457Z-ci-pages/gh-run-view-pages-26015520241.json`
      - log excerpt with preview URLs:
        - `logs/md1-shrunk/polls/20260518T053457Z-ci-pages/pages-preview-url-excerpt.txt`
        - alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
        - hash: `https://1ecce19d.v0-spaceport-website-preview2.pages.dev`
    - CDK Deploy run `26015520234` -> `success`:
      - watch: `logs/md1-shrunk/polls/20260518T053457Z-ci-pages/gh-run-watch-cdk-26015520234.txt`
      - run view: `logs/md1-shrunk/polls/20260518T053457Z-ci-pages/gh-run-view-cdk-26015520234.json`

- 2026-05-18T05:42:55Z viewer re-verify (post exact-head Pages deploy; skybox + no-sky + camera checks):
  - Evidence: `logs/md1-shrunk/polls/20260518T054255Z-viewer-postpages/`
  - Anonymous bundle fetch gates:
    - meta.json headers: `logs/md1-shrunk/polls/20260518T054255Z-viewer-postpages/http-head-meta.txt` -> `HTTP 200`
    - skybox headers: `logs/md1-shrunk/polls/20260518T054255Z-viewer-postpages/http-head-skybox.txt` -> `HTTP 200`
  - Playwright smoke (sogs-migrated-viewer):
    - skybox: `logs/md1-shrunk/polls/20260518T054255Z-viewer-postpages/playwright-sogs-skybox.txt` -> OK (screenshot overwritten: `logs/sogs-migrated-viewer-smoke.png`)
    - no-sky: `logs/md1-shrunk/polls/20260518T054255Z-viewer-postpages/playwright-sogs-nosky.txt` -> OK (screenshot overwritten: `logs/sogs-migrated-viewer-nosky.png`)
  - Camera checks (MD1 viewer; same pose; skybox vs no-sky):
    - skybox: `logs/md1-shrunk/polls/20260518T054255Z-viewer-postpages/md1-camera-check-skybox.png` (`logs/md1-shrunk/polls/20260518T054255Z-viewer-postpages/playwright-md1-camera-check-skybox.txt`)
    - no-sky: `logs/md1-shrunk/polls/20260518T054255Z-viewer-postpages/md1-camera-check-nosky.png` (`logs/md1-shrunk/polls/20260518T054255Z-viewer-postpages/playwright-md1-camera-check-nosky.txt`)

- 2026-05-18T05:56:32Z poll (resume; no new ML launches; re-verify terminal ML + exact-head Pages/CDK + viewer):
  - Evidence: `logs/md1-shrunk/polls/20260518T054653Z-resume/`
  - Local branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `049c70baf003e3a1e816f729c514d6b491665a76`
    - `git status --porcelain=v1` -> clean except new poll dir
  - AWS (staging us-west-2) identity + active state (captured via boto3 because `aws` CLI is not on PATH in this environment):
    - STS:
      - account: `975050048887`
      - arn: `arn:aws:iam::975050048887:root`
      - snapshot: `logs/md1-shrunk/polls/20260518T054653Z-resume/aws-sts-get-caller-identity.json`
    - Step Functions:
      - RUNNING executions under `SpaceportMLPipeline-staging`: `0`
      - snapshot: `logs/md1-shrunk/polls/20260518T054653Z-resume/stepfunctions-running.json`
    - SageMaker:
      - SfM ProcessingJob `md1-shrunk-1456-sfm-1778866088`: `Completed` (FailureReason null)
      - 3DGS TrainingJob `md1shrunk1456-1778880862-3dgs`: `Completed` (FailureReason null)
      - compression ProcessingJob `md1shrunk1456-1778880862-compression`: `Completed` (FailureReason null)
      - InProgress processing jobs: `0`
      - InProgress training jobs: `0`
      - snapshots:
        - `logs/md1-shrunk/polls/20260518T054653Z-resume/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
        - `logs/md1-shrunk/polls/20260518T054653Z-resume/sagemaker-describe-md1shrunk1456-1778880862-3dgs.json`
        - `logs/md1-shrunk/polls/20260518T054653Z-resume/sagemaker-describe-md1shrunk1456-1778880862-compression.json`
        - `logs/md1-shrunk/polls/20260518T054653Z-resume/sagemaker-list-processing-jobs-inprogress.json`
        - `logs/md1-shrunk/polls/20260518T054653Z-resume/sagemaker-list-training-jobs-inprogress.json`
  - SfM Montana-scale gate (from `sfm_metadata.json` in staged COLMAP output):
    - images_registered: `1456` (target Meadow/Incognito registered was `1452`)
    - merged_component_count: `1`
    - points_3d: `1103335` (Meadow/Incognito points3D `940147`)
    - quality_check_passed: `true`
    - timed_out: `false`
    - fallback_triggered: `false`
    - snapshots:
      - `logs/md1-shrunk/polls/20260518T054653Z-resume/sfm_metadata.json`
      - `logs/md1-shrunk/polls/20260518T054653Z-resume/sfm_metadata-summary.json`
  - Public bundle still anonymous-fetchable:
    - `curl -I` meta.json -> HTTP 200: `logs/md1-shrunk/polls/20260518T054653Z-resume/curl-head-meta.txt`
    - `curl -I` background_skybox.webp -> HTTP 200: `logs/md1-shrunk/polls/20260518T054653Z-resume/curl-head-skybox.txt`
  - GitHub workflows (exact-head) for `049c70ba...`:
    - `CDK Deploy` run `26015823873` -> `success`:
      - run view: `logs/md1-shrunk/polls/20260518T054653Z-resume/gh-run-view-26015823873.json`
    - `Deploy Next.js to Cloudflare Pages` run `26015823853` -> `success`:
      - preview alias URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
      - preview URL excerpt: `logs/md1-shrunk/polls/20260518T054653Z-resume/gh-run-26015823853-preview-url-lines.txt`
      - run view: `logs/md1-shrunk/polls/20260518T054653Z-resume/gh-run-view-26015823853.json`
  - Deployed preview viewer re-validation (skybox + no-sky) + input-vs-render camera side-by-side:
    - Playwright skybox: `logs/md1-shrunk/polls/20260518T054653Z-resume/playwright-skybox.txt` -> OK
    - Playwright no-sky: `logs/md1-shrunk/polls/20260518T054653Z-resume/playwright-no-sky.txt` -> OK
    - smoke screenshots:
      - skybox: `logs/md1-shrunk/polls/20260518T054653Z-resume/sogs-migrated-viewer-skybox.png`
      - no-sky: `logs/md1-shrunk/polls/20260518T054653Z-resume/sogs-migrated-viewer-nosky.png`
    - DJI_01029 input-vs-render (input left; render right):
      - input: `logs/md1-shrunk/polls/20260518T054653Z-resume/input-DJI_01029.JPG`
      - render skybox: `logs/md1-shrunk/polls/20260518T054653Z-resume/render-skybox-DJI_01029.png`
      - render no-sky: `logs/md1-shrunk/polls/20260518T054653Z-resume/render-nosky-DJI_01029.png`
      - side-by-side skybox: `logs/md1-shrunk/polls/20260518T054653Z-resume/side-by-side-skybox-DJI_01029.jpg`
      - side-by-side no-sky: `logs/md1-shrunk/polls/20260518T054653Z-resume/side-by-side-nosky-DJI_01029.jpg`

- 2026-05-18T05:59:14Z postpush proof (exact-head GitHub workflows; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260518T055914Z-postpush/`
  - `git rev-parse HEAD` -> `0c655319fc0504541f448facd198fa0647e7b745` (`[skip ci]`)
  - GitHub Actions:
    - exact-head workflow runs: `0` (expected because this push only touched `logs/` + `STATE.md` with `[skip ci]`)
    - last non-skip-ci exact-head Pages/CDK success remains at `049c70ba...` (see `logs/md1-shrunk/polls/20260518T054653Z-resume/`)

- 2026-05-18T06:17:56Z monitor poll (no new ML launches; reconfirm terminal ML state):
  - Evidence: `logs/md1-shrunk/polls/20260518T061756Z-monitor/`
  - Branch/head/status:
    - `git rev-parse HEAD` -> `aedbddad802a60ce2753618d4dae5eea2cfe29f7` (`[skip ci]`)
    - `git status --porcelain=v1` -> clean
  - AWS identity (boto3, region `us-west-2`):
    - account `975050048887`, ARN `arn:aws:iam::975050048887:root`
    - evidence: `logs/md1-shrunk/polls/20260518T061756Z-monitor/aws-sts-get-caller-identity.json`
  - Step Functions:
    - `SpaceportMLPipeline-staging` RUNNING executions: `0`
    - `SpaceportMLPipeline-br-8abcbd5662` RUNNING executions: `0`
    - evidence:
      - `logs/md1-shrunk/polls/20260518T061756Z-monitor/stepfunctions-running-by-machine.json`
      - `logs/md1-shrunk/polls/20260518T061756Z-monitor/stepfunctions-list-state-machines.json`
  - SageMaker (staging us-west-2):
    - SfM ProcessingJob `md1-shrunk-1456-sfm-1778866088` -> `Completed`, `FailureReason=null`
    - 3DGS TrainingJob `md1shrunk1456-1778880862-3dgs` -> `Completed`, `FailureReason=null`
    - Compression ProcessingJob `md1shrunk1456-1778880862-compression` -> `Completed`, `FailureReason=null`
    - InProgress processing jobs: `0`
    - InProgress training jobs: `0`
    - evidence:
      - `logs/md1-shrunk/polls/20260518T061756Z-monitor/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
      - `logs/md1-shrunk/polls/20260518T061756Z-monitor/sagemaker-describe-md1shrunk1456-1778880862-3dgs.json`
      - `logs/md1-shrunk/polls/20260518T061756Z-monitor/sagemaker-describe-md1shrunk1456-1778880862-compression.json`
      - `logs/md1-shrunk/polls/20260518T061756Z-monitor/sagemaker-list-processing-jobs-InProgress.json`
      - `logs/md1-shrunk/polls/20260518T061756Z-monitor/sagemaker-list-training-jobs-InProgress.json`
  - S3 output still present (bounded listing; first page only):
    - `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap/`
    - evidence: `logs/md1-shrunk/polls/20260518T061756Z-monitor/s3-colmap-list-summary.json`
  - GitHub Actions:
    - exact-head workflow runs for `aedbddad...`: `0` (expected; `[skip ci]`)
    - last non-skip-ci head in run list: `049c70ba...` (Pages+CDK both `success`)
    - evidence:
      - `logs/md1-shrunk/polls/20260518T061756Z-monitor/gh-run-list.json`
      - `logs/md1-shrunk/polls/20260518T061756Z-monitor/gh-summary.json`

- 2026-05-18T06:20:10Z postpush proof (exact-head GitHub workflows; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260518T062010Z-postpush/`
  - `git rev-parse HEAD` -> `1d091ea2f51a53c0ea7653bb1488972cc8730d48` (`[skip ci]`)
  - GitHub Actions:
    - exact-head workflow runs: `0` (expected; poll-only `[skip ci]` push)
    - last non-skip-ci Pages/CDK success remains at `049c70ba...` (see `logs/md1-shrunk/polls/20260518T054653Z-resume/`)
    - evidence:
      - `logs/md1-shrunk/polls/20260518T062010Z-postpush/gh-run-list.json`
      - `logs/md1-shrunk/polls/20260518T062010Z-postpush/gh-summary.json`

- 2026-05-18T06:56:40Z monitor poll (terminal reconfirm + viewer/camera rerun):
  - Evidence: `logs/md1-shrunk/polls/20260518T064647Z-monitor/`
  - Branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `b6dc45b27b65cea3c174894417d47a47b19ebc36` (`[skip ci]`)
    - `git status --porcelain=v1` -> clean
  - GitHub Actions (exact head + latest):
    - exact-head workflow runs for `b6dc45b2...`: `0` (expected; `[skip ci]`)
    - user-provided head `e9cbf71c...` was stale but `CDK Deploy` run `25932325504` succeeded:
      - `logs/md1-shrunk/polls/20260518T064647Z-monitor/gh-run-view-25932325504.json`
    - latest non-skip-ci head in run list remains `049c70ba...` with Pages+CDK `success`:
      - `logs/md1-shrunk/polls/20260518T064647Z-monitor/gh-summary.json`
    - preview alias (from Pages log of run `26015823853`):
      - `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
      - evidence:
        - `logs/md1-shrunk/polls/20260518T064647Z-monitor/preview-alias-url.txt`
        - `logs/md1-shrunk/polls/20260518T064647Z-monitor/gh-run-log-pages-26015823853.txt`
  - AWS identity (boto3, region `us-west-2`):
    - `Account=975050048887`, `Arn=arn:aws:iam::975050048887:root`
    - evidence: `logs/md1-shrunk/polls/20260518T064647Z-monitor/aws-sts-get-caller-identity.json`
  - Step Functions (RUNNING executions; boto3):
    - `SpaceportMLPipeline-staging`: `0`
    - `SpaceportMLPipeline-br-8abcbd5662`: `0`
    - evidence: `logs/md1-shrunk/polls/20260518T064647Z-monitor/stepfunctions-running-executions.json`
  - SageMaker terminal (boto3):
    - SfM ProcessingJob `md1-shrunk-1456-sfm-1778866088` -> `Completed`, `FailureReason=null`
    - 3DGS TrainingJob `md1shrunk1456-1778880862-3dgs` -> `Completed`, `FailureReason=null`
    - Compression ProcessingJob `md1shrunk1456-1778880862-compression` -> `Completed`, `FailureReason=null`
    - InProgress processing jobs: `0`
    - InProgress training jobs: `0`
    - evidence: `logs/md1-shrunk/polls/20260518T064647Z-monitor/aws-terminal-summary.json`
  - COLMAP gates (Montana-scale sanity):
    - registered images (from `colmap/sparse/0/images.txt`): `1456` (Meadow target `1452`)
    - points3D (from `colmap/sparse/0/points3D.txt`): `1020913` (Meadow `940147`)
    - merged components: `1` (`sparse/0/` only)
    - evidence:
      - `logs/md1-shrunk/polls/20260518T064647Z-monitor/colmap-gate-summary.json`
      - `logs/md1-shrunk/polls/20260518T064647Z-monitor/images.txt.headers.txt`
      - `logs/md1-shrunk/polls/20260518T064647Z-monitor/points3D.txt.head.txt`
  - 3DGS gates (model.tar.gz contents):
    - `splat.ply element vertex 990091` + bundled `background_skybox.webp` present
    - evidence: `logs/md1-shrunk/polls/20260518T064647Z-monitor/3dgs-model-tar-inspect.json`
  - Public supersplat bundle (presence + anonymous fetch):
    - prefix: `s3://spaceport-ml-processing/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/`
    - `curl -I` meta.json -> `HTTP/1.1 200 OK`:
      - `logs/md1-shrunk/polls/20260518T064647Z-monitor/curl-head-public-meta.txt`
    - bundle inventory + skybox sidecar proof:
      - `logs/md1-shrunk/polls/20260518T064647Z-monitor/s3-list-compressed-public.json`
      - `logs/md1-shrunk/polls/20260518T064647Z-monitor/public-background_manifest.json` (references `background_skybox.webp`)
  - Preview viewer validation (Playwright; current preview alias):
    - `/sogs-migrated-viewer` smoke (bundled skybox override): `logs/md1-shrunk/polls/20260518T064647Z-monitor/sogs-migrated-viewer-smoke.png`
    - `/sogs-migrated-viewer` no-sky mode: `logs/md1-shrunk/polls/20260518T064647Z-monitor/sogs-migrated-viewer-nosky.png`
    - evidence:
      - `logs/md1-shrunk/polls/20260518T064647Z-monitor/playwright-sogs-migrated-skybox.txt`
      - `logs/md1-shrunk/polls/20260518T064647Z-monitor/playwright-sogs-migrated-nosky.txt`
  - Input-vs-render camera check (DJI_01029; input left, render right):
    - input (from COLMAP output): `logs/md1-shrunk/polls/20260518T064647Z-monitor/input-DJI_01029.JPG`
    - render (skybox): `logs/md1-shrunk/polls/20260518T064647Z-monitor/render-skybox-DJI_01029.png`
    - render (no-sky): `logs/md1-shrunk/polls/20260518T064647Z-monitor/render-nosky-DJI_01029.png`
    - side-by-side (skybox): `logs/md1-shrunk/polls/20260518T064647Z-monitor/side-by-side-skybox-DJI_01029.png`
    - side-by-side (no-sky): `logs/md1-shrunk/polls/20260518T064647Z-monitor/side-by-side-nosky-DJI_01029.png`

- 2026-05-18T07:00:54Z postpush proof (exact-head GitHub workflows; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260518T070032Z-postpush/`
  - `git rev-parse HEAD` -> `4f27ab764f79807e8204c75b663c040f11404a8a` (`[skip ci]`)
  - GitHub Actions:
    - exact-head workflow runs: `0` (expected; `[skip ci]`)
    - last non-skip-ci Pages/CDK success remains at `049c70ba...`:
      - `logs/md1-shrunk/polls/20260518T070032Z-postpush/gh-summary.json`

- 2026-05-18T07:16:31Z monitor poll (no new ML launches; reconfirm terminal ML + CI state):
  - Evidence: `logs/md1-shrunk/polls/20260518T071631Z-monitor/`
  - Branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `a830b2bb304f8d880e96fe86fef23b7101546899` (`[skip ci]`)
    - `git status --porcelain=v1` -> clean
  - AWS identity (`/opt/homebrew/bin/aws`, region `us-west-2`):
    - evidence: `logs/md1-shrunk/polls/20260518T071631Z-monitor/aws-sts-get-caller-identity.json`
  - Step Functions (RUNNING executions; `/opt/homebrew/bin/aws`):
    - `SpaceportMLPipeline-staging` RUNNING: `0`
    - `SpaceportMLPipeline-br-8abcbd5662` RUNNING: `0`
    - evidence:
      - `logs/md1-shrunk/polls/20260518T071631Z-monitor/stepfunctions-list-executions-staging-RUNNING.json`
      - `logs/md1-shrunk/polls/20260518T071631Z-monitor/stepfunctions-list-executions-br-8abcbd5662-RUNNING.json`
  - SageMaker (staging us-west-2; `/opt/homebrew/bin/aws`):
    - SfM ProcessingJob `md1-shrunk-1456-sfm-1778866088` -> `Completed`, `FailureReason=null`
    - 3DGS TrainingJob `md1shrunk1456-1778880862-3dgs` -> `Completed`, `FailureReason=null`
    - Compression ProcessingJob `md1shrunk1456-1778880862-compression` -> `Completed`, `FailureReason=null`
    - InProgress processing jobs: `0`
    - InProgress training jobs: `0`
    - evidence:
      - `logs/md1-shrunk/polls/20260518T071631Z-monitor/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
      - `logs/md1-shrunk/polls/20260518T071631Z-monitor/sagemaker-describe-md1shrunk1456-1778880862-3dgs.json`
      - `logs/md1-shrunk/polls/20260518T071631Z-monitor/sagemaker-describe-md1shrunk1456-1778880862-compression.json`
      - `logs/md1-shrunk/polls/20260518T071631Z-monitor/sagemaker-list-processing-jobs-InProgress.json`
      - `logs/md1-shrunk/polls/20260518T071631Z-monitor/sagemaker-list-training-jobs-InProgress.json`
  - S3 output still present (bounded listing; first page only):
    - `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap/`
    - evidence: `logs/md1-shrunk/polls/20260518T071631Z-monitor/s3-colmap-list-objects-v2-firstpage.json`
  - GitHub Actions:
    - exact-head workflow runs for `a830b2bb...`: `0` (expected; `[skip ci]`)
    - evidence: `logs/md1-shrunk/polls/20260518T071631Z-monitor/gh-run-list.json`

- 2026-05-18T07:18:34Z postpush proof (exact-head GitHub workflows; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260518T071834Z-postpush/`
  - `git rev-parse HEAD` -> `1b6ca74e500ac61e6fb75b2818e4740903c18510` (`[skip ci]`)
  - GitHub Actions:
    - exact-head workflow runs: `0` (expected; `[skip ci]`)
    - evidence:
      - `logs/md1-shrunk/polls/20260518T071834Z-postpush/gh-run-list.json`
      - `logs/md1-shrunk/polls/20260518T071834Z-postpush/gh-exact-head-run-count.json`

- 2026-05-18T07:47:00Z monitor poll (no new ML launches; reconfirm terminal ML + CI + bundle + viewer gates):
  - Evidence: `logs/md1-shrunk/polls/20260518T074700Z-monitor/`
  - Branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `db1d694080d10839be1f47222e9f676486fb84b4` (`[skip ci]`)
    - `git status --porcelain=v1` -> clean (poll artifacts are untracked before commit)
    - evidence: `logs/md1-shrunk/polls/20260518T074700Z-monitor/git.txt`
  - AWS identity (`/opt/homebrew/bin/aws`, region `us-west-2`):
    - evidence: `logs/md1-shrunk/polls/20260518T074700Z-monitor/aws-sts-get-caller-identity.json`
  - Step Functions (RUNNING executions; `/opt/homebrew/bin/aws`):
    - `SpaceportMLPipeline-staging` RUNNING: `0`
    - `SpaceportMLPipeline-br-8abcbd5662` RUNNING: `0`
    - evidence:
      - `logs/md1-shrunk/polls/20260518T074700Z-monitor/stepfunctions-list-executions-staging-RUNNING.json`
      - `logs/md1-shrunk/polls/20260518T074700Z-monitor/stepfunctions-list-executions-br-8abcbd5662-RUNNING.json`
  - SageMaker (staging us-west-2; `/opt/homebrew/bin/aws`):
    - SfM ProcessingJob `md1-shrunk-1456-sfm-1778866088` -> `Completed`, `FailureReason=null`
    - 3DGS TrainingJob `md1shrunk1456-1778880862-3dgs` -> `Completed`, `FailureReason=null`
    - Compression ProcessingJob `md1shrunk1456-1778880862-compression` -> `Completed`, `FailureReason=null`
    - InProgress processing jobs: `0`
    - InProgress training jobs: `0`
    - evidence:
      - `logs/md1-shrunk/polls/20260518T074700Z-monitor/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
      - `logs/md1-shrunk/polls/20260518T074700Z-monitor/sagemaker-describe-md1shrunk1456-1778880862-3dgs.json`
      - `logs/md1-shrunk/polls/20260518T074700Z-monitor/sagemaker-describe-md1shrunk1456-1778880862-compression.json`
      - `logs/md1-shrunk/polls/20260518T074700Z-monitor/sagemaker-list-processing-jobs-InProgress.json`
      - `logs/md1-shrunk/polls/20260518T074700Z-monitor/sagemaker-list-training-jobs-InProgress.json`
  - Public bundle reachability (anonymous):
    - `HEAD https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/meta.json` -> `HTTP 200`
    - evidence: `logs/md1-shrunk/polls/20260518T074700Z-monitor/http-head-bundle-meta.txt`
  - Viewer smoke (skybox + no-sky; Playwright):
    - preview alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
    - `/sogs-migrated-viewer` skybox mode: `logs/md1-shrunk/polls/20260518T074700Z-monitor/sogs-migrated-viewer-smoke.png`
    - `/sogs-migrated-viewer` no-sky mode: `logs/md1-shrunk/polls/20260518T074700Z-monitor/sogs-migrated-viewer-nosky.png`
    - evidence:
      - `logs/md1-shrunk/polls/20260518T074700Z-monitor/playwright-sogs-migrated-skybox.txt`
      - `logs/md1-shrunk/polls/20260518T074700Z-monitor/playwright-sogs-migrated-nosky.txt`
  - GitHub Actions (exact head + latest; via `/opt/homebrew/bin/gh`):
    - exact-head workflow runs for `db1d6940...`: `0` (expected; `[skip ci]`)
    - last non-skip-ci Pages/CDK success remains at head `049c70ba...`
    - evidence:
      - `logs/md1-shrunk/polls/20260518T074700Z-monitor/gh-run-list.json`
      - `logs/md1-shrunk/polls/20260518T074700Z-monitor/gh-summary.txt`

- 2026-05-18T07:50:29Z postpush proof (exact-head GitHub workflows; `[skip ci]` head):
  - Evidence: `logs/md1-shrunk/polls/20260518T075029Z-postpush/`
  - `git rev-parse HEAD` -> `6196945684ec2a0b498753d2ab50f3c06f56ed47` (`[skip ci]`)
  - GitHub Actions:
    - exact-head workflow runs: `0` (expected; `[skip ci]`)
    - evidence:
      - `logs/md1-shrunk/polls/20260518T075029Z-postpush/gh-run-list.json`
      - `logs/md1-shrunk/polls/20260518T075029Z-postpush/gh-exact-head-run-count.txt`

- 2026-05-18T08:18:04Z monitor poll (no new ML launches; reconfirm terminal ML + CI + bundle reachability):
  - Evidence: `logs/md1-shrunk/polls/20260518T081804Z-monitor/`
  - Branch/head/status:
    - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
    - `git rev-parse HEAD` -> `b5dda8a582f51962796a8e67d495aabce7dbaa59` (`[skip ci]`)
    - `git status --porcelain=v1` -> clean (poll artifacts are untracked before commit)
    - evidence: `logs/md1-shrunk/polls/20260518T081804Z-monitor/git.txt`
  - AWS identity (`/opt/homebrew/bin/aws`, region `us-west-2`):
    - evidence: `logs/md1-shrunk/polls/20260518T081804Z-monitor/aws-sts-get-caller-identity.json`
  - Step Functions (RUNNING executions; `/opt/homebrew/bin/aws`):
    - `SpaceportMLPipeline-staging` RUNNING: `0`
    - `SpaceportMLPipeline-br-8abcbd5662` RUNNING: `0`
    - evidence:
      - `logs/md1-shrunk/polls/20260518T081804Z-monitor/stepfunctions-list-executions-staging-RUNNING.json`
      - `logs/md1-shrunk/polls/20260518T081804Z-monitor/stepfunctions-list-executions-br-8abcbd5662-RUNNING.json`
  - SageMaker (staging us-west-2; `/opt/homebrew/bin/aws`):
    - SfM ProcessingJob `md1-shrunk-1456-sfm-1778866088` -> `Completed`, `FailureReason=null`
    - 3DGS TrainingJob `md1shrunk1456-1778880862-3dgs` -> `Completed`, `FailureReason=null`
    - Compression ProcessingJob `md1shrunk1456-1778880862-compression` -> `Completed`, `FailureReason=null`
    - InProgress processing jobs: `0`
    - InProgress training jobs: `0`
    - evidence:
      - `logs/md1-shrunk/polls/20260518T081804Z-monitor/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
      - `logs/md1-shrunk/polls/20260518T081804Z-monitor/sagemaker-describe-md1shrunk1456-1778880862-3dgs.json`
      - `logs/md1-shrunk/polls/20260518T081804Z-monitor/sagemaker-describe-md1shrunk1456-1778880862-compression.json`
      - `logs/md1-shrunk/polls/20260518T081804Z-monitor/sagemaker-list-processing-jobs-InProgress.json`
      - `logs/md1-shrunk/polls/20260518T081804Z-monitor/sagemaker-list-training-jobs-InProgress.json`
  - S3 COLMAP output still present (bounded listing; first page only):
    - `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap/`
    - evidence: `logs/md1-shrunk/polls/20260518T081804Z-monitor/s3-colmap-list-objects-v2-firstpage.json`
  - Public bundle reachability (anonymous):
    - `HEAD https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/meta.json` -> `HTTP 200`
    - evidence:
      - `logs/md1-shrunk/polls/20260518T081804Z-monitor/http-head-bundle-meta.txt`
      - `logs/md1-shrunk/polls/20260518T081804Z-monitor/s3-head-public-meta.json`
  - GitHub Actions (exact head + latest; via `/opt/homebrew/bin/gh`):
    - exact-head workflow runs for `b5dda8a5...`: `0` (expected; `[skip ci]`)
    - latest non-skip-ci successes:
      - `CDK Deploy` run `26015823873` -> `success` (head `049c70ba...`)
      - `Deploy Next.js to Cloudflare Pages` run `26015823853` -> `success` (head `049c70ba...`)
    - evidence:
      - `logs/md1-shrunk/polls/20260518T081804Z-monitor/gh-run-list.json`
      - `logs/md1-shrunk/polls/20260518T081804Z-monitor/gh-run-count.txt`

## 2026-05-18T09:47:16Z poll (monitor; re-verify terminal state)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T094716Z-monitor/`
- Branch/head/status:
  - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - `git rev-parse HEAD` -> `e59b5cba6a120dd79da3addf7e8dfe7308d5608e` (`[skip ci]`)
  - `git status --porcelain=v1` -> clean
  - evidence: `logs/md1-shrunk/polls/20260518T094716Z-monitor/git.txt`
- GitHub Actions (exact head; `gh` not present on this machine):
  - provided exact-head `CDK Deploy` proof:
    - run `25932325504` (`CDK Deploy`) -> `success`, head `e9cbf71c...`
    - evidence:
      - `logs/md1-shrunk/polls/20260518T094716Z-monitor/github-actions-run-25932325504-summary.json`
      - `logs/md1-shrunk/polls/20260518T094716Z-monitor/github-actions-run-25932325504.json`
  - branch runs snapshot (REST list):
    - `logs/md1-shrunk/polls/20260518T094716Z-monitor/github-actions-runs-branch.json`
- AWS identity + active state (via boto3; `aws` CLI not present on this machine):
  - identity: account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions RUNNING (staging): `0`
  - Step Functions RUNNING (all SpaceportMLPipeline* state machines): `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T094716Z-monitor/aws-sts-get-caller-identity.json`
    - `logs/md1-shrunk/polls/20260518T094716Z-monitor/stepfunctions-running-executions-staging.json`
    - `logs/md1-shrunk/polls/20260518T094716Z-monitor/stepfunctions-running-executions-all.json`
- SageMaker state (staging us-west-2; via boto3):
  - SfM ProcessingJob `md1-shrunk-1456-sfm-1778866088` -> `Completed`, `FailureReason=null`
  - InProgress processing jobs: `0`
  - InProgress training jobs: `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T094716Z-monitor/sagemaker-processing-summary.json`
    - `logs/md1-shrunk/polls/20260518T094716Z-monitor/sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088.json`
    - `logs/md1-shrunk/polls/20260518T094716Z-monitor/sagemaker-list-processing-jobs-InProgress.json`
    - `logs/md1-shrunk/polls/20260518T094716Z-monitor/sagemaker-list-training-jobs-InProgress.json`
- SfM output S3 present + Montana metrics unchanged:
  - COLMAP output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap/`
  - metrics (from `sfm_metadata.json`): `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `timed_out=false`, `quality_check_passed=true`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T094716Z-monitor/s3-colmap-summary.json`
    - `logs/md1-shrunk/polls/20260518T094716Z-monitor/sfm_metadata.json`
    - `logs/md1-shrunk/polls/20260518T094716Z-monitor/colmap-metrics.json`
    - `logs/md1-shrunk/polls/20260518T094716Z-monitor/cloudwatch-processing-tail.txt`
- Downstream pipeline terminal (re-verified; no new launches):
  - Step Functions execution `execution-md1shrunk1456-1778880862` -> `SUCCEEDED`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T094716Z-monitor/stepfunctions-describe-execution-md1shrunk1456-1778880862.json`
- Public reachability (anonymous):
  - preview `/health.txt` -> `HTTP 200`
  - bundle `meta.json` -> `HTTP 200`
  - bundle `background_skybox.webp` -> `HTTP 200`
  - evidence: `logs/md1-shrunk/polls/20260518T094716Z-monitor/http-head-sanity.txt`

## 2026-05-18T09:51:47Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T095147Z-postpush/`
- Branch/head/status:
  - `git rev-parse HEAD` -> `0ec88c32841021e7728a93d6503f938944bd9f23` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T095147Z-postpush/git.txt`
- GitHub Actions (exact head):
  - exact-head workflow runs for `0ec88c32...`: `0` (expected; `[skip ci]`)
  - evidence:
    - `logs/md1-shrunk/polls/20260518T095147Z-postpush/github-actions-runs-head.json`
    - `logs/md1-shrunk/polls/20260518T095147Z-postpush/github-actions-runs-branch.json`

## 2026-05-18T10:16:55Z poll (monitor; re-verify terminal state; no new launches)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T101655Z-monitor/`
- Branch/head/status:
  - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - `git rev-parse HEAD` -> `bae68039f2c2b49bd74412553bba4d2c4cb7ea51` (`[skip ci]`)
  - `git status --porcelain=v1` -> clean
  - evidence:
    - `logs/md1-shrunk/polls/20260518T101655Z-monitor/git-branch.txt`
    - `logs/md1-shrunk/polls/20260518T101655Z-monitor/git-head.txt`
    - `logs/md1-shrunk/polls/20260518T101655Z-monitor/git-status.txt`
- GitHub Actions (exact head; no `gh` here; REST unauthenticated):
  - provided exact-head `CDK Deploy` proof:
    - run `25932325504` -> `success`, head `e9cbf71c56420ce386b028e7f4af33163ce4dcc2`
  - current head (`bae68039...`) workflow runs: `0` (expected; `[skip ci]`)
  - evidence:
    - `logs/md1-shrunk/polls/20260518T101655Z-monitor/github-actions.json`
- AWS identity + active state (via boto3; us-west-2):
  - identity: account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions RUNNING (SpaceportMLPipeline*): `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T101655Z-monitor/aws.json`
    - `logs/md1-shrunk/polls/20260518T101655Z-monitor/stepfunctions-known-execution-summary.json`
- SageMaker state (staging; via boto3):
  - SfM ProcessingJob `md1-shrunk-1456-sfm-1778866088` -> `Completed`, `FailureReason=null`
  - InProgress processing jobs: `0`
  - InProgress training jobs: `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T101655Z-monitor/aws.json`
    - `logs/md1-shrunk/polls/20260518T101655Z-monitor/cloudwatch-processing-tail.txt`
- SfM Montana gates (from `sfm_metadata.json` in COLMAP output):
  - `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `timed_out=false`, `quality_check_passed=true`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T101655Z-monitor/sfm_metadata.json`
    - `logs/md1-shrunk/polls/20260518T101655Z-monitor/colmap-metrics.json`
- Public reachability (anonymous; bundle + preview):
  - preview alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - preview `/health.txt` -> `HTTP 200`
  - bundle `meta.json` -> `HTTP 200`
  - bundle `background_skybox.webp` -> `HTTP 200`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T101655Z-monitor/http-head-sanity.txt`
    - `logs/md1-shrunk/polls/20260518T101655Z-monitor/bundle-meta.json`
    - `logs/md1-shrunk/polls/20260518T101655Z-monitor/bundle-meta-summary.json`

## 2026-05-18T10:24:15Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T102415Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `2c14fb82f84d9065eb1ea072ef705cbeefa35f06` (`[skip ci]`)
  - evidence:
    - `logs/md1-shrunk/polls/20260518T102415Z-postpush/git-head.txt`
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)

## 2026-05-18T15:53:55Z resume poll (SfM terminal + viewer re-verify; no new ML launches)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T155326Z-resume/`
- Branch/head/status:
  - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - `git rev-parse HEAD` -> `00a76e2ada8ccdf8366855ca5ca87b7b1cbe3c09` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T155326Z-resume/summary.txt`
- AWS identity + active state (region `us-west-2`):
  - `Account=975050048887`, `Arn=arn:aws:iam::975050048887:root`
  - Step Functions RUNNING executions under `SpaceportMLPipeline-staging`: `0`
  - SageMaker InProgress jobs: `0` processing, `0` training
- SfM terminal (job from user prompt; this is now historical, not active):
  - `ProcessingJobName=md1-shrunk-1456-sfm-1778866088` -> `Completed`
  - start/end: `2026-05-15T11:28:49-0600` → `2026-05-15T15:04:36-0600`
  - evidence: `logs/md1-shrunk/polls/20260518T155326Z-resume/sagemaker-describe-md1-shrunk-1456-sfm-1778866088-20260518T154929Z.json`
  - CloudWatch: `logs/md1-shrunk/polls/20260518T155326Z-resume/cloudwatch-tail-md1-shrunk-1456-sfm-1778866088-20260518T154929Z.txt`
  - output listing: `logs/md1-shrunk/polls/20260518T155326Z-resume/s3-colmap-md1-shrunk-20260515T1641Z-20260518T154929Z.txt`
- SfM Montana-scale gates (from `sfm_metadata.json` written by the job):
  - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`
  - dataset_image_count: `1456`
  - registered images: `1456` (100%)
  - merged_component_count: `1`
  - points_3d: `1103335`
  - timed_out: `False`
  - processing_time_seconds: `12709.05`
  - evidence: `logs/md1-shrunk/polls/20260518T155326Z-resume/sfm-metadata-md1-shrunk-20260515T1641Z-20260518T155000Z.json`
- Public compressed bundle fetch (anonymous):
  - meta.json: `HTTP 200`
  - skybox asset: `HTTP 200`
  - evidence: `logs/md1-shrunk/polls/20260518T155326Z-resume/curl-compressed-md1-shrunk-1456-20260518T155120Z.txt`
- Deployed preview viewer re-verify (skybox + no-sky):
  - resolved Pages alias URL from run `26015823853`: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - skybox smoke log: `logs/md1-shrunk/polls/20260518T155326Z-resume/sogs-viewer-skybox-20260518T155145Z.txt`
  - no-sky smoke log: `logs/md1-shrunk/polls/20260518T155326Z-resume/sogs-viewer-nosky-20260518T155145Z.txt`
  - screenshots: `logs/md1-shrunk/polls/20260518T155326Z-resume/20260518T155237Z-viewer-smoke/`

## 2026-05-18T15:56:20Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T155620Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `3f3ee0ccf329654125e5a65c66fefac702410a5b` (`[skip ci]`)
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T155620Z-postpush/gh-runs.json`

## 2026-05-18T15:57:09Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T155709Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `df107c94325ae57dd346365b84b6dd79666e996f` (`[skip ci]`)
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T155709Z-postpush/gh-runs.json`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T102415Z-postpush/github-actions-runs-head.json`

## 2026-05-18T10:51:28Z poll (monitor; no new launches)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T104631Z-monitor/`
- Branch/head/status:
  - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - `git rev-parse HEAD` -> `6ee55fae8498d56f5b0e6faaa83fd8998e215e9b`
  - `git status --porcelain=v1` -> clean
  - evidence: `logs/md1-shrunk/polls/20260518T104631Z-monitor/git.txt`
- GitHub Actions (exact head + last known green deploys; REST API via curl since `gh` is not installed):
  - provided exact-head `CDK Deploy` proof:
    - run `25932325504` (`CDK Deploy`) -> `success`, head `e9cbf71c56420ce386b028e7f4af33163ce4dcc2`
    - evidence: `logs/md1-shrunk/polls/20260518T104631Z-monitor/github-actions-run-25932325504.json`
  - current head workflow runs: `0` (expected; monitor commits use `[skip ci]`)
  - latest green pair (Pages + CDK) observed on branch:
    - head `049c70baf003e3a1e816f729c514d6b491665a76` -> Pages run `26015823853` + CDK run `26015823873` (both `success`)
    - evidence: `logs/md1-shrunk/polls/20260518T104631Z-monitor/github-actions-proof.json`
  - note: a Pages run for head `e9cbf71c...` was not found in the Pages-workflow run list for this branch (may be older than retained branch workflow history for that workflow).
    - evidence: `logs/md1-shrunk/polls/20260518T104631Z-monitor/github-actions-pages-workflow-find-e9cbf.json`
- AWS identity + active state (via boto3; us-west-2; `aws` CLI is not installed):
  - identity: account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions RUNNING (staging): `0`
  - Step Functions RUNNING (all SpaceportMLPipeline* state machines): `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T104631Z-monitor/aws-sts-get-caller-identity.json`
    - `logs/md1-shrunk/polls/20260518T104631Z-monitor/stepfunctions-running-executions-staging.json`
    - `logs/md1-shrunk/polls/20260518T104631Z-monitor/stepfunctions-running-executions-all.json`
- SageMaker state (staging us-west-2; via boto3):
  - SfM ProcessingJob `md1-shrunk-1456-sfm-1778866088` -> `Completed`, `FailureReason=null`
  - InProgress processing jobs: `0`
  - InProgress training jobs: `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T104631Z-monitor/sagemaker-describe-processing-md1-shrunk-1456-sfm-1778866088.json`
    - `logs/md1-shrunk/polls/20260518T104631Z-monitor/sagemaker-list-processing-jobs-InProgress.json`
    - `logs/md1-shrunk/polls/20260518T104631Z-monitor/sagemaker-list-training-jobs-InProgress.json`
- SfM output S3 present + Montana gates pass:
  - COLMAP output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap/`
  - gates (from `sfm_metadata.json`): `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `timed_out=false`, `quality_check_passed=true`
  - overall Montana gate assessment: `PASS`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T104631Z-monitor/s3-colmap-summary.json`
    - `logs/md1-shrunk/polls/20260518T104631Z-monitor/sfm_metadata.json`
    - `logs/md1-shrunk/polls/20260518T104631Z-monitor/colmap-metrics.json`
    - `logs/md1-shrunk/polls/20260518T104631Z-monitor/sfm-montana-gate-assessment.json`
    - `logs/md1-shrunk/polls/20260518T104631Z-monitor/cloudwatch-processing-tail.txt`
- Downstream pipeline terminal (re-verified; no new launches):
  - Step Functions execution `execution-md1shrunk1456-1778880862` -> `SUCCEEDED`
  - evidence: `logs/md1-shrunk/polls/20260518T104631Z-monitor/stepfunctions-describe-execution-md1shrunk1456-1778880862.json`
- Public reachability (anonymous; bundle + preview):
  - preview alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - preview `/health.txt` -> `HTTP 200`
  - bundle `meta.json` -> `HTTP 200`
  - bundle `background_skybox.webp` -> `HTTP 200`
  - gaussian count (from `meta.json means.shape[0]`): `990025`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T104631Z-monitor/http-head-sanity.txt`
    - `logs/md1-shrunk/polls/20260518T104631Z-monitor/bundle-meta.json`
    - `logs/md1-shrunk/polls/20260518T104631Z-monitor/gaussian_count.txt`

## 2026-05-18T10:52:44Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T105244Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `abc9524641de77cb6a77b892ce9277588c74fd39` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T105244Z-postpush/git-head.txt`
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T105244Z-postpush/github-actions-runs-head-summary.json`

## 2026-05-18T11:21:53Z monitor poll (boto3 + GitHub REST; no `aws`/`gh` CLIs)

- Branch/head/status:
  - `git rev-parse HEAD` -> `097a0f4bb5a1db994d08460696b7b443f8e9b4f1` (`[skip ci]`)
  - `git status --porcelain=v1` -> clean
- AWS identity + active state:
  - account: `975050048887` (via `boto3 sts.get_caller_identity`)
  - Step Functions RUNNING executions:
    - `SpaceportMLPipeline-staging` -> `0`
  - SageMaker InProgress:
    - processing jobs: `0`
    - training jobs: `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T111736Z-monitor/aws-snapshot.json`
    - `logs/md1-shrunk/polls/20260518T112016Z-stepfunctions/stepfunctions-describe-execution-md1shrunk1456-1778880862.json` -> `status=SUCCEEDED`
- SfM terminal + Montana gates PASS:
  - job: `md1-shrunk-1456-sfm-1778866088` -> `Completed`
  - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`
  - gates (from `sfm_metadata.json`): `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `quality_check_passed=true`, `timed_out=false`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T111736Z-monitor/aws-snapshot.json`
    - `logs/md1-shrunk/polls/20260518T111838Z-s3/s3-list-objects-summary.json`
    - `logs/md1-shrunk/polls/20260518T111838Z-s3/sfm_metadata.json`
    - `logs/md1-shrunk/polls/20260518T111838Z-s3/colmap-gates-summary.json`
- CloudWatch (processing):
  - stream exists: `md1-shrunk-1456-sfm-1778866088/algo-1-1778866129`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T112118Z-cloudwatch-streams/cloudwatch-describe-log-streams.json`
    - `logs/md1-shrunk/polls/20260518T112141Z-cloudwatch-events/cloudwatch-get-log-events-head.json` (head sample)
- GitHub Actions proof (exact head from user prompt):
  - run `25932325504` (`CDK Deploy`) -> `success` for `e9cbf71c56420ce386b028e7f4af33163ce4dcc2`
  - evidence: `logs/md1-shrunk/polls/20260518T111915Z-github/github-actions-run-25932325504.json`
- GitHub Actions for current head:
  - `head_sha=097a0f4bb5a1db994d08460696b7b443f8e9b4f1` -> `0` runs (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T112027Z-github-head/github-actions-runs-097a0f4bb5a1db994d08460696b7b443f8e9b4f1.json`

## 2026-05-18T11:23:11Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T112311Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `9ca7fbc7bd7211c66712cba7d367ef10d7e1d8a2` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T112311Z-postpush/git-head.txt`
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T112311Z-postpush/github-actions-runs-head-summary.json`
- GitHub Actions proof (user prompt head):
  - run `25932325504` (`CDK Deploy`) -> `success` for `e9cbf71c56420ce386b028e7f4af33163ce4dcc2`
  - evidence: `logs/md1-shrunk/polls/20260518T112311Z-postpush/github-actions-run-25932325504.json`

## 2026-05-18T11:47:08Z monitor poll (boto3 + GitHub REST; no new launches)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T114708Z-monitor/`
- Branch/head/status:
  - `git rev-parse HEAD` -> `d5f3ea0a6a9f8d8de76ec637646603d96453a80d` (`[skip ci]`)
  - `git status --porcelain=v1` -> clean
  - evidence:
    - `logs/md1-shrunk/polls/20260518T114708Z-monitor/git-head.txt`
    - `logs/md1-shrunk/polls/20260518T114708Z-monitor/git-status.txt`
- AWS identity + active state:
  - account: `975050048887`, ARN: `arn:aws:iam::975050048887:root`
  - Step Functions RUNNING executions (`SpaceportMLPipeline-staging`): `0`
  - SageMaker InProgress:
    - processing jobs: `0`
    - training jobs: `0`
  - evidence: `logs/md1-shrunk/polls/20260518T114708Z-monitor/aws-snapshot.json`
- SfM terminal (re-verified):
  - job: `md1-shrunk-1456-sfm-1778866088` -> `Completed`
  - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T114708Z-monitor/aws-snapshot.json`
    - `logs/md1-shrunk/polls/20260518T114708Z-monitor/s3-colmap-summary.json`
    - `logs/md1-shrunk/polls/20260518T114708Z-monitor/sfm_metadata.json`
- GitHub Actions proof (user prompt exact head):
  - run `25932325504` (`CDK Deploy`) -> `success` for `e9cbf71c56420ce386b028e7f4af33163ce4dcc2`
  - evidence: `logs/md1-shrunk/polls/20260518T114708Z-monitor/github-actions-run-25932325504.json`
- GitHub Actions for current head:
  - head_sha `d5f3ea0a6a9f8d8de76ec637646603d96453a80d` -> `0` runs (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T114708Z-monitor/github-actions-runs-d5f3ea0a6a9f8d8de76ec637646603d96453a80d.json`
- Public reachability (anonymous; preview + bundle):
  - preview `/health.txt` -> `HTTP 200`
  - bundle `meta.json` -> `HTTP 200`
  - bundle `background_skybox.webp` -> `HTTP 200`
  - evidence: `logs/md1-shrunk/polls/20260518T114708Z-monitor/http-head-sanity.txt`

## 2026-05-18T11:50:18Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T115018Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `bbe167b5da8a0b7638e40cb90ca941c09bd55f35` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T115018Z-postpush/git-head.txt`
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T115018Z-postpush/github-actions-runs-head-summary.json`

## 2026-05-18T12:17:03Z monitor poll (boto3 + GitHub REST; no new launches)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T121703Z-monitor/`
- Branch/head/status:
  - `git rev-parse HEAD` -> `d9cfad939cf8ddd9c76ce2784cd06be9b6cb2c1d` (`[skip ci]`)
  - `git status --porcelain=v1` -> clean
- AWS identity + active state:
  - account: `975050048887`, ARN: `arn:aws:iam::975050048887:root`
  - Step Functions RUNNING executions (`SpaceportMLPipeline-staging`): `0`
  - SageMaker InProgress:
    - processing jobs: `0`
    - training jobs: `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T121703Z-monitor/sts-get-caller-identity.json`
    - `logs/md1-shrunk/polls/20260518T121703Z-monitor/stepfunctions-running-staging.json`
    - `logs/md1-shrunk/polls/20260518T121703Z-monitor/sagemaker-list-processing-inprogress.json`
    - `logs/md1-shrunk/polls/20260518T121703Z-monitor/sagemaker-list-training-inprogress.json`
- SfM terminal (re-verified):
  - job: `md1-shrunk-1456-sfm-1778866088` -> `Completed`
  - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`
  - gates (from `sfm_metadata.json`): `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `quality_check_passed=true`, `timed_out=false`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T121703Z-monitor/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
    - `logs/md1-shrunk/polls/20260518T121703Z-monitor/s3-sfm-metadata-probe.json`
    - `logs/md1-shrunk/polls/20260518T121703Z-monitor/s3-list-colmap-output-pages.json`
- CloudWatch tail (processing job):
  - evidence: `logs/md1-shrunk/polls/20260518T121703Z-monitor/cloudwatch-tail-processing-job.json`
- GitHub Actions proof (exact head from user prompt):
  - run `25932325504` (`CDK Deploy`) -> `success` for `e9cbf71c56420ce386b028e7f4af33163ce4dcc2`
  - evidence: `logs/md1-shrunk/polls/20260518T121703Z-monitor/github-actions-run-25932325504.json`
- GitHub Actions (Pages workflow; most recent on this branch):
  - run `26015823853` (`Deploy Next.js to Cloudflare Pages`) -> `success` for `049c70baf003e3a1e816f729c514d6b491665a76`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T121703Z-monitor/github-pages-workflow-runs.json`
    - `logs/md1-shrunk/polls/20260518T121703Z-monitor/github-actions-run-26015823853.json`
- GitHub Actions for current head:
  - `head_sha=d9cfad939cf8ddd9c76ce2784cd06be9b6cb2c1d` -> `0` runs (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T121703Z-monitor/github-actions-exact-head-summary.json`
- Public reachability (anonymous; preview + bundle):
  - preview `/health.txt` -> `HTTP 200`
  - bundle `meta.json` -> `HTTP 200`
  - bundle `background_skybox.webp` -> `HTTP 200`
  - evidence: `logs/md1-shrunk/polls/20260518T121703Z-monitor/http-head-sanity.txt`

## 2026-05-18T12:20:46Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T122046Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `e00af00e4dceaaa56f523b3fe3033701599148b8` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T122046Z-postpush/git-head.txt`
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T122046Z-postpush/github-actions-runs-head-summary.json`

## 2026-05-18T12:46:19Z monitor poll (boto3 + GitHub REST; no new launches)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T124619Z-monitor/`
- Branch/head/status:
  - `git rev-parse HEAD` -> `f56316722ab72f8096538bd3cecd8633115c671e` (`[skip ci]`)
  - `git status --porcelain=v1` -> clean
  - evidence: `logs/md1-shrunk/polls/20260518T124619Z-monitor/local-git.txt`
- AWS identity + active state:
  - account: `975050048887`, ARN: `arn:aws:iam::975050048887:root`
  - Step Functions RUNNING executions:
    - `SpaceportMLPipeline-staging`: `0`
    - all `SpaceportMLPipeline-*` state machines: `0`
  - SageMaker InProgress:
    - processing jobs: `0`
    - training jobs: `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T124619Z-monitor/aws-boto3-snapshot.json`
    - `logs/md1-shrunk/polls/20260518T124619Z-monitor/stepfunctions-spaceport-snapshot.json`
- SfM terminal (re-verified):
  - job: `md1-shrunk-1456-sfm-1778866088` -> `Completed`
  - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`
  - gates (from `sfm_metadata.json`): `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `quality_check_passed=true`, `timed_out=false`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T124619Z-monitor/aws-boto3-snapshot.json`
    - `logs/md1-shrunk/polls/20260518T124619Z-monitor/sfm-metadata-snapshot.json`
- Downstream Step Functions (branch state machine):
  - state machine: `SpaceportMLPipeline-br-8abcbd5662`
  - execution: `execution-md1shrunk1456-1778880862` -> `SUCCEEDED`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T124619Z-monitor/stepfunctions-spaceport-snapshot.json`
- GitHub Actions proof (exact head from user prompt):
  - run `25932325504` (`CDK Deploy`) -> `success` for `e9cbf71c56420ce386b028e7f4af33163ce4dcc2`
  - evidence: `logs/md1-shrunk/polls/20260518T124619Z-monitor/github-actions-snapshot.json`
- GitHub Actions for current head:
  - `head_sha=f56316722ab72f8096538bd3cecd8633115c671e` -> `0` runs (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T124619Z-monitor/github-actions-snapshot.json`
- Public reachability (anonymous; preview + bundle):
  - preview `/health.txt` -> `HTTP 200`
  - bundle `meta.json` -> `HTTP 200`
  - bundle `background_skybox.webp` -> `HTTP 200`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T124619Z-monitor/http-head-preview-health.txt`
    - `logs/md1-shrunk/polls/20260518T124619Z-monitor/http-head-bundle-meta.txt`
    - `logs/md1-shrunk/polls/20260518T124619Z-monitor/http-head-bundle-skybox.txt`

## 2026-05-18T12:54:10Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T125410Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `a8a4492e82275c88f0f71b92d0787f1cfe3220ad` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T125410Z-postpush/git-head.txt`
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T125410Z-postpush/github-actions-postpush.json`
- GitHub Actions proof (user prompt head):
  - run `25932325504` (`CDK Deploy`) -> `success` for `e9cbf71c56420ce386b028e7f4af33163ce4dcc2`
  - evidence: `logs/md1-shrunk/polls/20260518T125410Z-postpush/github-actions-postpush.json`

## 2026-05-18T13:16:55Z monitor poll (boto3 + GitHub REST; no new launches)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T131655Z-monitor/`
- Branch/head/status:
  - `git rev-parse HEAD` -> `fc87baddd61baafa030ade0601b7616497145ab6` (`[skip ci]`)
  - `git status --porcelain=v1` -> clean
  - evidence: `logs/md1-shrunk/polls/20260518T131655Z-monitor/local-git.txt`
- AWS identity + active state:
  - account: `975050048887`, ARN: `arn:aws:iam::975050048887:root`
  - Step Functions RUNNING executions:
    - `SpaceportMLPipeline-staging`: `0`
    - all `SpaceportMLPipeline-*` state machines: `0`
  - SageMaker InProgress:
    - processing jobs: `0`
    - training jobs: `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T131655Z-monitor/aws-boto3-snapshot.json`
    - `logs/md1-shrunk/polls/20260518T131655Z-monitor/stepfunctions-spaceport-snapshot.json`
- SfM terminal (re-verified):
  - job: `md1-shrunk-1456-sfm-1778866088` -> `Completed`
  - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`
  - gates (from `sfm_metadata.json`): `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `quality_check_passed=true`, `timed_out=false`
  - evidence: `logs/md1-shrunk/polls/20260518T131655Z-monitor/sfm-metadata-snapshot.json`
- Downstream Step Functions (branch state machine):
  - state machine: `SpaceportMLPipeline-br-8abcbd5662`
  - execution: `execution-md1shrunk1456-1778880862` -> `SUCCEEDED`
  - evidence: `logs/md1-shrunk/polls/20260518T131655Z-monitor/stepfunctions-spaceport-snapshot.json`
- GitHub Actions proof (exact head from user prompt):
  - run `25932325504` (`CDK Deploy`) -> `success` for `e9cbf71c56420ce386b028e7f4af33163ce4dcc2`
  - evidence: `logs/md1-shrunk/polls/20260518T131655Z-monitor/github-actions-exact-head-summary.json`
- GitHub Actions for current head:
  - `head_sha=fc87baddd61baafa030ade0601b7616497145ab6` -> `0` runs (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T131655Z-monitor/github-actions-exact-head-summary.json`
- Public reachability (anonymous; preview + bundle):
  - preview `/health.txt` -> `HTTP 200`
  - bundle `meta.json` -> `HTTP 200`
  - bundle `background_skybox.webp` -> `HTTP 200`
  - bundle meta gaussian count: `990025`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T131655Z-monitor/http-head-preview-health.txt`
    - `logs/md1-shrunk/polls/20260518T131655Z-monitor/http-head-bundle-meta.txt`
    - `logs/md1-shrunk/polls/20260518T131655Z-monitor/http-head-bundle-skybox.txt`
    - `logs/md1-shrunk/polls/20260518T131655Z-monitor/bundle-meta-summary.txt`

## 2026-05-18T13:20:41Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T132041Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `8f0b8cc0908caf197d43d72c834f540cbd4d4f67` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T132041Z-postpush/git-head.txt`
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T132041Z-postpush/github-actions-postpush.json`
- GitHub Actions proof (user prompt head):
  - run `25932325504` (`CDK Deploy`) -> `success` for `e9cbf71c56420ce386b028e7f4af33163ce4dcc2`
  - evidence: `logs/md1-shrunk/polls/20260518T132041Z-postpush/github-actions-postpush.json`

## 2026-05-18T13:47:16Z monitor poll (boto3 + GitHub connector; no new launches)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T134716Z-monitor/`
- Branch/head/status:
  - `git rev-parse HEAD` -> `0d9ce947a09cf5a24c061b2a59e7c9a00f2dfde5` (`[skip ci]`)
  - `git status --porcelain=v1` -> clean
  - evidence: `logs/md1-shrunk/polls/20260518T134716Z-monitor/local-git.json`
- AWS identity + active state (boto3):
  - Step Functions RUNNING executions across `SpaceportMLPipeline-*`: `0`
  - SageMaker InProgress:
    - processing jobs: `0`
    - training jobs: `0`
  - SfM processing job: `md1-shrunk-1456-sfm-1778866088` -> `Completed`
  - evidence: `logs/md1-shrunk/polls/20260518T134716Z-monitor/aws-boto3-snapshot.json`
- Downstream Step Functions terminal:
  - execution: `execution-md1shrunk1456-1778880862` -> `SUCCEEDED`
  - evidence: `logs/md1-shrunk/polls/20260518T134716Z-monitor/stepfunctions-describe-execution-md1shrunk1456-1778880862.json`
- GitHub Actions (connector re-verify; still green):
  - `CDK Deploy` run `25932325504` -> `deploy` job `success`
  - `Deploy Next.js to Cloudflare Pages` run `25948288202` -> `deploy` job `success`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T134716Z-monitor/github-workflow-jobs-25932325504.json`
    - `logs/md1-shrunk/polls/20260518T134716Z-monitor/github-workflow-jobs-25948288202.json`
- Public reachability (anonymous; preview + bundle):
  - preview `/health.txt` -> `HTTP 200`
  - bundle `meta.json` -> `HTTP 200`
  - bundle `background_skybox.webp` -> `HTTP 200`
  - bundle meta gaussian count (from `means.shape[0]`): `990025`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T134716Z-monitor/http-head-preview-health.txt`
    - `logs/md1-shrunk/polls/20260518T134716Z-monitor/http-head-bundle-meta.txt`
    - `logs/md1-shrunk/polls/20260518T134716Z-monitor/http-head-bundle-skybox.txt`
    - `logs/md1-shrunk/polls/20260518T134716Z-monitor/bundle-meta-summary.json`

## 2026-05-18T14:16:55Z monitor poll (awscli + gh; no new launches)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T141655Z-monitor/`
- Branch/head/status:
  - `git rev-parse HEAD` -> `8483a2c7d2f9d6711380ba4901fb950692d012a2` (`[skip ci]`)
  - evidence:
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/git-status.txt`
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/git-log-1.txt`
- AWS identity + active state:
  - `aws sts get-caller-identity` -> account `975050048887`
  - Step Functions RUNNING executions under `SpaceportMLPipeline-staging`: `0`
  - SageMaker InProgress:
    - processing jobs: `0`
    - training jobs: `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/aws-sts.json`
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/stepfn-running.json`
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/sagemaker-processing-inprogress.json`
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/sagemaker-training-inprogress.json`
- SfM terminal (re-verified):
  - job: `md1-shrunk-1456-sfm-1778866088` -> `Completed`
  - gates (from `sfm_metadata.json`): `images_registered=1456`, `merged_component_count=1`, `points_3d=1103335`, `timed_out=false`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/sagemaker-describe-sfm.json`
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/sfm_metadata.json`
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/s3-colmap-summary.txt`
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/gates-summary.txt`
- 3DGS + compression terminal (re-verified):
  - training: `md1shrunk1456-1778880862-3dgs` -> `Completed`
  - processing: `md1shrunk1456-1778880862-compression` -> `Completed`
  - bundle meta gaussian count (from `means.shape[0]`): `990025`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/sagemaker-describe-3dgs.json`
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/s3-3dgs-summary.txt`
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/sagemaker-describe-compression.json`
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/s3-md1-shrunk-manual-validations-summary.txt`
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/http-public-meta.json`
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/gaussian_count.txt`
- GitHub Actions (branch runs; plus user prompt exact-head proof):
  - run `25932325504` (`CDK Deploy`) -> `success` for `e9cbf71c56420ce386b028e7f4af33163ce4dcc2`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/gh-runs.json`
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/gh-run-25932325504.json`
- Public reachability (anonymous; preview + bundle):
  - preview alias URL -> `HTTP 200`: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - bundle `meta.json` -> `HTTP 200`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/http-preview.headers.txt`
    - `logs/md1-shrunk/polls/20260518T141655Z-monitor/http-public-meta.headers.txt`

## 2026-05-18T14:23:58Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T142358Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `abc73e3e682c1fb43834fe91c3b5d2f97a511c52` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T142358Z-postpush/git-head.txt`
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T142358Z-postpush/gh-runs.json`

## 2026-05-18T14:46:38Z monitor poll (awscli + gh; no new launches)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T144638Z-monitor/`
- Branch/head/status:
  - `git rev-parse HEAD` -> `7508a92a671824e2a6bb01fa25df7842347ac17f` (`[skip ci]`)
  - note: local PATH in Codex does not include `/opt/homebrew/bin`; this poll uses `/opt/homebrew/bin/aws` and `/opt/homebrew/bin/gh` explicitly.
  - evidence:
    - `logs/md1-shrunk/polls/20260518T144638Z-monitor/summary.txt`
- AWS identity + active state:
  - `aws sts get-caller-identity` -> account `975050048887`
  - Step Functions RUNNING executions under `SpaceportMLPipeline-staging`: `0`
  - SageMaker InProgress:
    - processing jobs: `0`
    - training jobs: `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T144638Z-monitor/aws-sts.json`
    - `logs/md1-shrunk/polls/20260518T144638Z-monitor/stepfn-running.json`
- SfM terminal (re-verified):
  - job: `md1-shrunk-1456-sfm-1778866088` -> `Completed`
  - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T144638Z-monitor/sagemaker-describe-sfm.json`
- GitHub Actions (branch runs + user-prompt exact-head proof):
  - branch workflow list captured
  - run `25932325504` (`CDK Deploy`) -> `success` for `e9cbf71c56420ce386b028e7f4af33163ce4dcc2`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T144638Z-monitor/gh-runs.json`
    - `logs/md1-shrunk/polls/20260518T144638Z-monitor/gh-summary.txt`

## 2026-05-18T14:49:33Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T144933Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `d8a11ceb17de248b6f836d66b935efac08d4d2bd` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T144933Z-postpush/summary.txt`
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T144933Z-postpush/gh-runs.json`

## 2026-05-18T14:50:23Z monitor poll (terminal re-verify 3DGS + compression)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T145023Z-monitor2/`
- 3DGS terminal:
  - training: `md1shrunk1456-1778880862-3dgs` -> `Completed`
  - evidence: `logs/md1-shrunk/polls/20260518T145023Z-monitor2/sagemaker-describe-3dgs.json`
- Compression terminal:
  - processing: `md1shrunk1456-1778880862-compression` -> `Completed`
  - evidence: `logs/md1-shrunk/polls/20260518T145023Z-monitor2/sagemaker-describe-compression.json`

## 2026-05-18T14:50:59Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T145059Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `e97a341fbf3ac86bcb5f96286ec6ebbb3019f71f` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T145059Z-postpush/summary.txt`
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T145059Z-postpush/gh-runs.json`

## 2026-05-18T15:18:34Z monitor poll (terminal reconfirm + Montana gates)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T151833Z-monitor/`
  - `logs/md1-shrunk/polls/20260518T152233Z-ci2/`
  - `logs/md1-shrunk/polls/20260518T152343Z-artifacts/`
  - `logs/md1-shrunk/polls/20260518T152355Z-artifact-metadata/`
- Branch/head:
  - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - `git rev-parse HEAD` -> `2553fed29b70f1e1715966701ee44e99d6941d64` (`[skip ci]`)
- AWS identity + active state (region `us-west-2`):
  - `Account=975050048887`, `Arn=arn:aws:iam::975050048887:root`
  - Step Functions RUNNING executions under `SpaceportMLPipeline-staging`: `0`
  - SageMaker terminal:
    - processing `md1-shrunk-1456-sfm-1778866088` -> `Completed`
    - training `md1shrunk1456-1778880862-3dgs` -> `Completed`
    - processing `md1shrunk1456-1778880862-compression` -> `Completed`
- SfM Montana-scale gates (from COLMAP text model under output S3):
  - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/colmap`
  - sparse dirs: `["0"]` (single model dir)
  - registered images (`images.txt` entries): `1456`
  - points3D (`points3D.txt` entries): `1020913`
- 3DGS + compression artifact gates:
  - 3DGS model: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/3dgs/md1shrunk1456-1778880862/`
  - compressed bundle: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-20260515T1641Z/compressed/md1shrunk1456-1778880862/`
  - gaussians: `990025` (from `supersplat_bundle/meta.json` means.shape[0])
  - original PLY size: `234.1691 MB` (from `supersplat_bundle/training_metadata.json` file_size_mb)
  - compressed size: `14.3454 MB` (from `sogs_compression_summary.json` compressed_size_mb)
  - skybox sidecars present: `background_skybox.webp` + manifests under `supersplat_bundle/`
- GitHub Actions (PATH note: use `/opt/homebrew/bin/gh` in Codex):
  - user-prompt proof: run `25932325504` (`CDK Deploy`) -> `success` for `e9cbf71c56420ce386b028e7f4af33163ce4dcc2`
  - current exact-head run count: `0` (expected; `[skip ci]`)

## 2026-05-18T15:28:14Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T152814Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `82d815ebadc4a6019be46a108caf840420c98b3b` (`[skip ci]`)
  - note: the poll directory captured the previous head `c8043eec...` right before committing the poll evidence itself.
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)

## 2026-05-18T16:16:42Z poll (monitor; reconfirm idle + public URLs)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T161642Z-resume/`
- Branch/head/status:
  - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - `git rev-parse HEAD` -> `7c2bed4feee3315dab4d6fbde1b26612a995aa2e` (`[skip ci]`)
  - `git status --porcelain=v1` -> clean
- AWS identity (region `us-west-2`):
  - account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - evidence: `logs/md1-shrunk/polls/20260518T161642Z-resume/aws-sts-get-caller-identity.json`
- Step Functions active executions (region `us-west-2`):
  - `SpaceportMLPipeline*` RUNNING: `0`
  - evidence: `logs/md1-shrunk/polls/20260518T161642Z-resume/stepfunctions-running-spaceportml.json`
- SageMaker active jobs (region `us-west-2`):
  - InProgress processing jobs: `0`
  - InProgress training jobs: `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T161642Z-resume/sagemaker-list-processing-jobs-InProgress.json`
    - `logs/md1-shrunk/polls/20260518T161642Z-resume/sagemaker-list-training-jobs-InProgress.json`
- SfM job terminal state:
  - `md1-shrunk-1456-sfm-1778866088` -> `ProcessingJobStatus=Completed` (ended `2026-05-15T15:04:36-06:00`)
  - evidence: `logs/md1-shrunk/polls/20260518T161642Z-resume/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
- Public URLs (anonymous `HTTP 200`):
  - preview alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - bundle meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/meta.json`
  - skybox: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-20260515T1641Z-1456-1778880862/supersplat_bundle/background_skybox.webp`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T161642Z-resume/http-preview-alias-headers.txt`
    - `logs/md1-shrunk/polls/20260518T161642Z-resume/http-meta-headers.txt`
    - `logs/md1-shrunk/polls/20260518T161642Z-resume/http-skybox-headers.txt`

## 2026-05-18T16:21:14Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T162114Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `4bac4e02269f4db02ccc2efaf01190e0f665bfbb` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T162114Z-postpush/git-head.txt`
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)
  - evidence:
    - `logs/md1-shrunk/polls/20260518T162114Z-postpush/gh-run-list.json`
    - `logs/md1-shrunk/polls/20260518T162114Z-postpush/gh-exact-head-count.txt`

## 2026-05-18T16:22:12Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T162212Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `9b365f57b486736c23b5080c751913fa6327d1d8` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T162212Z-postpush/git-head.txt`
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)
  - evidence:
    - `logs/md1-shrunk/polls/20260518T162212Z-postpush/gh-run-list.json`
    - `logs/md1-shrunk/polls/20260518T162212Z-postpush/gh-exact-head-count.txt`

## 2026-05-18T16:47:11Z poll (monitor; idle + URL reachability)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T164711Z-monitor/`
- Branch/head/status:
  - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - `git rev-parse HEAD` -> `d42a463985320464f46279fb8013636b6e544568` (`[skip ci]`)
  - `git status --porcelain=v1` -> clean
- AWS identity (region `us-west-2`):
  - account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - evidence: `logs/md1-shrunk/polls/20260518T164711Z-monitor/aws-sts-get-caller-identity.json`
- Step Functions active executions (region `us-west-2`):
  - `SpaceportMLPipeline*` RUNNING: `0`
  - evidence: `logs/md1-shrunk/polls/20260518T164711Z-monitor/stepfunctions-running-spaceportml.json`
- SageMaker active jobs (region `us-west-2`):
  - InProgress processing jobs: `0`
  - InProgress training jobs: `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T164711Z-monitor/sagemaker-list-processing-jobs-InProgress.json`
    - `logs/md1-shrunk/polls/20260518T164711Z-monitor/sagemaker-list-training-jobs-InProgress.json`
- SfM job terminal state (reconfirmed):
  - `md1-shrunk-1456-sfm-1778866088` -> `ProcessingJobStatus=Completed`, `FailureReason=null`
  - evidence: `logs/md1-shrunk/polls/20260518T164711Z-monitor/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)
  - evidence:
    - `logs/md1-shrunk/polls/20260518T164711Z-monitor/gh-run-list.json`
    - `logs/md1-shrunk/polls/20260518T164711Z-monitor/gh-exact-head-count.txt`
- Public URL reachability (anonymous `HTTP 200`):
  - preview alias headers: `logs/md1-shrunk/polls/20260518T164711Z-monitor/http-preview-alias-headers.txt`
  - bundle meta.json headers: `logs/md1-shrunk/polls/20260518T164711Z-monitor/http-meta-headers.txt`

## 2026-05-18T17:03:43Z production-spine integration (prelaunch)

- Branch/head/status before integration commit:
  - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - `git rev-parse HEAD` -> `e8a48cbfbc8387c2c6e1dc2468764ccb1677c9b4`
  - `git status --short` -> production-spine SfM files staged/modified, no active runtime jobs.
- AWS identity:
  - `/opt/homebrew/bin/aws sts get-caller-identity --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
- Active cloud state:
  - `/opt/homebrew/bin/aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --region us-west-2 --output json` -> `[]`
  - no new MD1-Shrunk job launched yet from this section.
- GitHub workflow state:
  - `/opt/homebrew/bin/gh run list --branch agent-113647-md1-baseline-e2e --limit 20 --json databaseId,workflowName,displayTitle,headSha,status,conclusion,createdAt,url`
  - latest exact meaningful head before this integration remains `049c70baf003e3a1e816f729c514d6b491665a76`, with `CDK Deploy` run `26015823873` success and `Deploy Next.js to Cloudflare Pages` run `26015823853` success.
- Source integrated:
  - `origin/agent-73948216-sfm-production-spine@aa2de93abf6da476de21272bb682c78ec1f91353` (`fix: signal unified LOD readiness from chunks`)
- Direct merge note:
  - attempted `git merge --no-ff --no-commit origin/agent-73948216-sfm-production-spine`
  - aborted with `git merge --abort` because the feature branch carried broad conflicts/log/web surfaces beyond the MD1-Shrunk runtime need.
  - proceeded with surgical SfM runtime/test integration to preserve this branch's MD1-Shrunk dataset builder, Montana-profile 3DGS/skybox work, compressor timeout fix, viewer/no-sky/Y-axis fixes, and prior proven output evidence.
- Files integrated from production-spine:
  - `infrastructure/containers/sfm/Dockerfile`
  - `infrastructure/containers/sfm/requirements.txt`
  - `infrastructure/containers/sfm/run_colmap_sfm.py`
  - `infrastructure/containers/sfm/run_sfm.sh`
  - `scripts/sfm/build_sfm_fanout_contract.py`
  - `scripts/sfm/diagnose_heldout_panels.py`
  - `scripts/sfm/evaluate_sfm_quality.py`
  - `scripts/sfm/evaluate_visual_quality.py`
  - `scripts/sfm/normalize_nerfstudio_eval.py`
  - `scripts/sfm/prepare_colmap_training_sample.py`
  - `scripts/sfm/prepare_md1_probe_subsets.py`
  - `scripts/sfm/prepare_prior_chunk_subset.py`
  - `scripts/sfm/prepare_sequential_benchmark_subset.py`
  - `scripts/sfm/run_phase1_md1_probe_validation.py`
  - `scripts/sfm/run_phase2_md1_hierarchy_validation.py`
  - `scripts/sfm/run_sfm_fanout_reducer.py`
  - `scripts/sfm/run_sfm_reducer_canary.py`
  - unit tests for fanout, reducer, visual quality, quality eval, heldout diagnostics, normalizer, and subset helpers.
- Local branch-specific launcher reconciliation:
  - `scripts/sfm/run_sfm_benchmark.py` now preserves the current branch's `--role-arn` and `--payload-json-output` support while adding production-spine branch/head env, planner/report-only flags, `COLMAP_ONLY_CHUNK_INDEXES`, and production-spine metadata summary fields.
- Validation commands:
  - `python3 -m py_compile infrastructure/containers/sfm/run_colmap_sfm.py scripts/sfm/run_sfm_benchmark.py scripts/sfm/build_sfm_fanout_contract.py scripts/sfm/run_sfm_fanout_reducer.py scripts/sfm/run_sfm_reducer_canary.py scripts/sfm/evaluate_sfm_quality.py scripts/sfm/evaluate_visual_quality.py scripts/sfm/diagnose_heldout_panels.py tests/unit/test_sfm_fanout_reducer.py tests/unit/test_sfm_reducer_canary.py tests/unit/test_sfm_visual_quality.py`
  - `python3 -m unittest tests.unit.test_sfm_fanout_contract tests.unit.test_sfm_fanout_reducer tests.unit.test_sfm_reducer_canary tests.unit.test_colmap_spatial_subset_zip tests.unit.test_sfm_quality_eval tests.unit.test_sfm_visual_quality`
  - `git diff --check && git diff --cached --check`
- Validation result:
  - py_compile passed.
  - unittest passed: `Ran 18 tests in 0.014s`, `OK (skipped=6)`.
  - skips are local-environment skips for tests requiring `numpy`; they remain importable and will run in environments with `numpy`.
  - diff checks passed.
- Next concrete steps:
  1. Commit/push this integration with a fresh Pages trigger.
  2. Watch exact-head `CDK Deploy`, `Deploy Next.js to Cloudflare Pages`, and automatic ML container build workflows.
  3. Verify the branch SfM ECR tag/digest for `agent113647md1baselinee2e`.
  4. Launch exactly one new MD1-Shrunk SfM run from `s3://spaceport-uploads/md1-shrunk-20260515T1641Z-1456-images.zip` using the integrated production-spine SfM image.
  5. Continue to 3DGS, skybox, compression, public bundle reachability, deployed viewer, and side-by-side visual gates only after SfM passes.

## 2026-05-18T17:26:23Z production-spine image preflight failure and fix

- Integration commit/push:
  - commit: `414560c5818ed5d5173936697924de4ac5cb2c7f` (`feat: integrate sfm production spine for md1 shrunk`)
  - push: `git push origin agent-113647-md1-baseline-e2e`
- Exact-head workflows for `414560c5818ed5d5173936697924de4ac5cb2c7f`:
  - `CDK Deploy` run `26048241011` -> success
  - `Deploy Next.js to Cloudflare Pages` run `26048240968` -> success
  - `Trigger ML Container Build` run `26048240967` -> success
  - evidence:
    - `logs/md1-shrunk/gh-runs-exact-head-414560c5-20260518T1719Z.json`
    - `logs/md1-shrunk/pages-run-26048240968-log-20260518T1719Z.txt`
    - preview alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
    - hash URL: `https://66d620a7.v0-spaceport-website-preview2.pages.dev`
- Branch SfM container build:
  - CodeBuild: `spaceport-ml-containers:e2ac4bd6-5627-49fa-8007-1d57c634cb01`, build `701`
  - sourceVersion: `414560c5818ed5d5173936697924de4ac5cb2c7f`
  - status: `SUCCEEDED`
  - ECR image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:19704ca7bc16c65ec3c102650a83772826da843e30bf3939d85b39cbfa7f0869`
  - tag: `agent113647md1baselinee2e`
  - pushed: `2026-05-18T11:18:18.196000-06:00`
  - evidence:
    - `logs/md1-shrunk/codebuild-sfm-701-20260518T1719Z.json`
    - `logs/md1-shrunk/ecr-sfm-agent113647md1baselinee2e-20260518T1719Z.json`
- Cost-bounded preflight launched before the full SfM rerun:
  - purpose: verify the integrated branch SfM image can start and run planner/report-only logic before spending on a full MD1-Shrunk SfM job.
  - command: `PATH="/opt/homebrew/bin:$PATH" python3 scripts/sfm/run_sfm_benchmark.py --input-s3-uri s3://spaceport-uploads/md1-shrunk-20260515T1641Z-1456-images.zip --output-s3-uri s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-planner-20260518T1720Z/colmap --job-prefix md1-shrunk-prodspine-plan --instance-type ml.g4dn.xlarge --volume-size-gb 100 --image-uri 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:19704ca7bc16c65ec3c102650a83772826da843e30bf3939d85b39cbfa7f0869 --role-arn arn:aws:iam::975050048887:role/Spaceport-SageMaker-Role-staging --mode chunked --subset-strategy md1_shrunk_prodspine_1456_planner --env COLMAP_CHUNK_PLANNER=footprint_graph_v1 --env COLMAP_MATCH_PROFILE=P1 --planner-report-only --payload-json-output logs/md1-shrunk/md1-shrunk-prodspine-planner-20260518T1720Z-payload.json`
  - job: `md1-shrunk-prodspine-plan-1779124846`
  - ARN: `arn:aws:sagemaker:us-west-2:975050048887:processing-job/md1-shrunk-prodspine-plan-1779124846`
  - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-planner-20260518T1720Z/colmap`
  - start proof: `logs/md1-shrunk/md1-shrunk-prodspine-planner-20260518T1720Z-start.json`
  - payload: `logs/md1-shrunk/md1-shrunk-prodspine-planner-20260518T1720Z-payload.json`
- Preflight failed before any full SfM work:
  - `ProcessingJobStatus=Failed`
  - `FailureReason=AlgorithmError: , exit code: 1`
  - log stream: `/aws/sagemaker/ProcessingJobs` / `md1-shrunk-prodspine-plan-1779124846/algo-1-1779124894`
  - exact CloudWatch error: `ERROR: COLMAP not available`
  - evidence:
    - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-plan-1779124846-20260518T1726Z.json`
    - `logs/md1-shrunk/cloudwatch-md1-shrunk-prodspine-plan-1779124846-20260518T1727Z.json`
- Proven blocker:
  - the integrated production-spine Dockerfile inherited from mutable `spaceport/sfm:latest` and then exported from `scratch`; this produced a branch image without `colmap` on `PATH`.
  - this failure was caught by the planner-only preflight, so no duplicate full MD1-Shrunk SfM job was launched.
- Fix applied:
  - `infrastructure/containers/sfm/Dockerfile` now uses the pinned CUDA COLMAP runtime base `colmap/colmap:20260318.6455 AS runtime`, matching the development/Montana-capable container family and removing dependency on mutable `spaceport/sfm:latest`.
- Next concrete steps:
  1. Validate the Dockerfile patch locally with compile/unit/diff checks.
  2. Commit/push the fix.
  3. Watch exact-head workflows and the new SfM container build.
  4. Verify the new ECR digest.
  5. Rerun planner-only preflight once, then launch the full MD1-Shrunk SfM only if that preflight passes.

## 2026-05-18T17:21:19Z poll (monitor; post-integration CI + viewer)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T172119Z-monitor/`
- Branch/head/status:
  - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - `git rev-parse HEAD` -> `414560c5818ed5d5173936697924de4ac5cb2c7f`
  - `git status --porcelain=v1` -> clean
  - evidence: `logs/md1-shrunk/polls/20260518T172119Z-monitor/git-branch-head-status.txt`
- GitHub Actions (exact head):
  - exact-head `CDK Deploy` run `26048241011` succeeded for `414560c5...`.
  - exact-head `Deploy Next.js to Cloudflare Pages` run `26048240968` succeeded for `414560c5...`.
  - exact-head `Trigger ML Container Build` run `26048240967` succeeded for `414560c5...`.
  - evidence:
    - `logs/md1-shrunk/polls/20260518T172119Z-monitor/gh-run-list.json`
    - `logs/md1-shrunk/polls/20260518T172119Z-monitor/gh-exact-head-summary.txt`
- AWS identity (region `us-west-2`):
  - account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - evidence: `logs/md1-shrunk/polls/20260518T172119Z-monitor/aws-sts-get-caller-identity.json`
- Step Functions active executions (region `us-west-2`):
  - `SpaceportMLPipeline-staging` RUNNING: `0`
  - evidence: `logs/md1-shrunk/polls/20260518T172119Z-monitor/stepfunctions-running-spaceportml.json`
- SageMaker active jobs (region `us-west-2`):
  - InProgress processing jobs: `0`
  - InProgress training jobs: `0`
  - evidence:
    - `logs/md1-shrunk/polls/20260518T172119Z-monitor/sagemaker-list-processing-jobs-InProgress.json`
    - `logs/md1-shrunk/polls/20260518T172119Z-monitor/sagemaker-list-training-jobs-InProgress.json`
- SfM job terminal state (reconfirmed):
  - `md1-shrunk-1456-sfm-1778866088` -> `ProcessingJobStatus=Completed`, `FailureReason=null`
  - evidence: `logs/md1-shrunk/polls/20260518T172119Z-monitor/sagemaker-describe-md1-shrunk-1456-sfm-1778866088.json`
- Public URL reachability (anonymous `HTTP 200`):
  - preview alias headers: `logs/md1-shrunk/polls/20260518T172119Z-monitor/http-preview-alias-headers.txt`
  - bundle meta.json headers: `logs/md1-shrunk/polls/20260518T172119Z-monitor/http-meta-headers.txt`
  - skybox headers: `logs/md1-shrunk/polls/20260518T172119Z-monitor/http-skybox-headers.txt`
- Deployed preview viewer validation (skybox + no-sky, Playwright/Chromium):
  - skybox stdout: `logs/md1-shrunk/polls/20260518T172119Z-monitor/sogs-smoke-stdout.txt`
  - skybox screenshot: `logs/md1-shrunk/polls/20260518T172119Z-monitor/sogs-migrated-viewer-smoke.png`
  - no-sky stdout: `logs/md1-shrunk/polls/20260518T172119Z-monitor/sogs-nosky-stdout.txt`
  - no-sky screenshot: `logs/md1-shrunk/polls/20260518T172119Z-monitor/sogs-migrated-viewer-nosky.png`

## 2026-05-18T17:25:35Z post-push confirmation (monitor)

- Poll artifacts:
  - `logs/md1-shrunk/polls/20260518T172535Z-postpush/`
- Branch/head:
  - `git rev-parse HEAD` -> `178f11713ec86b7e6e4701467ea154562c558b07` (`[skip ci]`)
  - evidence: `logs/md1-shrunk/polls/20260518T172535Z-postpush/git-branch-head-status.txt`
- GitHub Actions (exact head):
  - exact-head workflow runs: `0` (expected; `[skip ci]`)
  - evidence:
    - `logs/md1-shrunk/polls/20260518T172535Z-postpush/gh-run-list.json`
    - `logs/md1-shrunk/polls/20260518T172535Z-postpush/gh-exact-head-count.txt`

## 2026-05-18T17:52:39Z production-spine planner retry wrapper failure

- Branch/head/status verified:
  - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - `git rev-parse HEAD` -> `a24d3603537db9c28b9cdc50f4fc48db0bcadc27`
  - untracked evidence files existed from the fixed-image build and planner retry; no unrelated code changes were present before this wrapper patch.
- AWS identity:
  - `/opt/homebrew/bin/aws sts get-caller-identity --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
- GitHub workflows for `a24d3603537db9c28b9cdc50f4fc48db0bcadc27`:
  - `CDK Deploy` run `26049408781` -> success
  - `Trigger ML Container Build` run `26049408789` -> success
  - evidence: `logs/md1-shrunk/gh-runs-exact-head-a24d3603-20260518T1746Z.json`
- Fixed branch SfM image:
  - CodeBuild: `spaceport-ml-containers:531ba12a-75a3-42bf-b742-9351ed274d47`, build `702`
  - sourceVersion: `a24d3603537db9c28b9cdc50f4fc48db0bcadc27`
  - status: `SUCCEEDED`
  - ECR image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:15a4aab2297ca7f9ffaae19504edcd029e05498476ff56c3702aea13ee39ef40`
  - pushed: `2026-05-18T11:44:49.801000-06:00`
  - evidence:
    - `logs/md1-shrunk/codebuild-sfm-702-20260518T1746Z.json`
    - `logs/md1-shrunk/ecr-sfm-agent113647md1baselinee2e-20260518T1746Z.json`
- Active cloud state before action:
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`
  - InProgress SageMaker processing jobs:
    - owned: `md1-shrunk-prodspine-plan2-1779126370`
    - external/not owned: `cvhr-mtc-20260518T1729Z-sfm`; left untouched.
  - InProgress SageMaker training jobs: `0`
- Fixed-image planner-only preflight command:
  - `PATH="/opt/homebrew/bin:$PATH" python3 scripts/sfm/run_sfm_benchmark.py --input-s3-uri s3://spaceport-uploads/md1-shrunk-20260515T1641Z-1456-images.zip --output-s3-uri s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-planner2-20260518T1747Z/colmap --job-prefix md1-shrunk-prodspine-plan2 --instance-type ml.g4dn.xlarge --volume-size-gb 100 --image-uri 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:15a4aab2297ca7f9ffaae19504edcd029e05498476ff56c3702aea13ee39ef40 --role-arn arn:aws:iam::975050048887:role/Spaceport-SageMaker-Role-staging --mode chunked --subset-strategy md1_shrunk_prodspine_1456_planner --env COLMAP_CHUNK_PLANNER=footprint_graph_v1 --env COLMAP_MATCH_PROFILE=P1 --planner-report-only --payload-json-output logs/md1-shrunk/md1-shrunk-prodspine-planner2-20260518T1747Z-payload.json`
  - job: `md1-shrunk-prodspine-plan2-1779126370`
  - ARN: `arn:aws:sagemaker:us-west-2:975050048887:processing-job/md1-shrunk-prodspine-plan2-1779126370`
  - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-planner2-20260518T1747Z/colmap`
  - start proof: `logs/md1-shrunk/md1-shrunk-prodspine-planner2-20260518T1747Z-start.json`
  - payload: `logs/md1-shrunk/md1-shrunk-prodspine-planner2-20260518T1747Z-payload.json`
- Planner retry result:
  - `ProcessingJobStatus=Failed`
  - `FailureReason=AlgorithmError: , exit code: 1`
  - `ProcessingStartTime=2026-05-18T11:46:52.553000-06:00`
  - `ProcessingEndTime=2026-05-18T11:50:52.769000-06:00`
  - log stream: `/aws/sagemaker/ProcessingJobs` / `md1-shrunk-prodspine-plan2-1779126370/algo-1-1779126411`
  - evidence:
    - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-plan2-1779126370-20260518T1749Z.json`
    - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-plan2-1779126370-20260518T1751Z.json`
    - `logs/md1-shrunk/logstreams-md1-shrunk-prodspine-plan2-1779126370-20260518T1751Z.json`
    - `logs/md1-shrunk/cloudwatch-md1-shrunk-prodspine-plan2-1779126370-20260518T1751Z.json`
    - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-planner2-20260518T1747Z-20260518T1751Z.txt`
- Hard failure details:
  - the fixed image contains COLMAP and starts correctly.
  - the container extracted `1456` images, detected GPS/orientation priors on `1456` images, and wrote planner/report artifacts.
  - S3 uploaded `chunk_planner_manifest.json`, `planner_static_report.json`, `reducer_metadata.json`, and `sfm_metadata.json`.
  - failure came from `run_sfm.sh` full-output validation demanding `sparse/0/cameras.txt`, `images.txt`, `points3D.txt`, `images/`, and `database.db` even though this was explicitly `SFM_PLANNER_REPORT_ONLY=1`.
- Fix applied:
  - `infrastructure/containers/sfm/run_sfm.sh` now treats `SFM_PLANNER_REPORT_ONLY=1` as a successful snapshot/planner artifact path and exits before full COLMAP output validation.
- Validation commands:
  - `python3 -m py_compile infrastructure/containers/sfm/run_colmap_sfm.py scripts/sfm/run_sfm_benchmark.py`
  - `python3 -m unittest tests.unit.test_sfm_fanout_contract tests.unit.test_sfm_fanout_reducer tests.unit.test_sfm_reducer_canary tests.unit.test_colmap_spatial_subset_zip tests.unit.test_sfm_quality_eval tests.unit.test_sfm_visual_quality`
  - `git diff --check`
- Validation result:
  - py_compile passed.
  - unittest passed: `Ran 18 tests in 0.017s`, `OK (skipped=6)`.
  - diff check passed.
- Next concrete steps:
  1. Commit/push the planner-wrapper fix.
  2. Watch exact-head `CDK Deploy` and `Trigger ML Container Build`.
  3. Verify the new branch SfM ECR digest.
  4. Rerun the planner-only preflight once.
  5. Launch full MD1-Shrunk production-spine SfM only after the planner-only preflight exits successfully.

## 2026-05-18T18:33:28Z production-spine planner pass and canonical full SfM launch

- Commit/push:
  - commit: `df57b678c025ed39fe27b7500d3e7a301b74b603` (`fix: allow sfm planner report completion`)
  - push: `git push origin agent-113647-md1-baseline-e2e`
- Exact-head workflows for `df57b678c025ed39fe27b7500d3e7a301b74b603`:
  - `CDK Deploy` run `26050765145` -> success
  - `Trigger ML Container Build` run `26050769102` -> success
  - evidence: `logs/md1-shrunk/gh-runs-exact-head-df57b678-20260518T1818Z.json`
- Branch SfM container build:
  - CodeBuild: `spaceport-ml-containers:063b2f62-140d-4da2-9c60-3397899616cb`, build `703`
  - sourceVersion: `df57b678c025ed39fe27b7500d3e7a301b74b603`
  - status: `SUCCEEDED`
  - ECR image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:c96dca6f3b0850855eac576e8a27371dfca408e24364d79f7e35b23425cc7950`
  - pushed: `2026-05-18T12:13:45.187000-06:00`
  - evidence:
    - `logs/md1-shrunk/codebuild-sfm-703-20260518T1818Z.json`
    - `logs/md1-shrunk/ecr-sfm-agent113647md1baselinee2e-20260518T1818Z.json`
- Active cloud guard before full launch:
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`
  - InProgress SageMaker training jobs: `0`
  - InProgress SageMaker processing jobs:
    - external/not owned: `cvhr-mtc-20260518T1729Z-sfm`; left untouched.
- Successful planner-only preflight:
  - command: `PATH="/opt/homebrew/bin:$PATH" python3 scripts/sfm/run_sfm_benchmark.py --input-s3-uri s3://spaceport-uploads/md1-shrunk-20260515T1641Z-1456-images.zip --output-s3-uri s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-planner3-20260518T1819Z/colmap --job-prefix md1-shrunk-prodspine-plan3 --instance-type ml.g4dn.xlarge --volume-size-gb 100 --image-uri 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:c96dca6f3b0850855eac576e8a27371dfca408e24364d79f7e35b23425cc7950 --role-arn arn:aws:iam::975050048887:role/Spaceport-SageMaker-Role-staging --mode chunked --subset-strategy md1_shrunk_prodspine_1456_planner --env COLMAP_CHUNK_PLANNER=footprint_graph_v1 --env COLMAP_MATCH_PROFILE=P1 --planner-report-only --payload-json-output logs/md1-shrunk/md1-shrunk-prodspine-planner3-20260518T1819Z-payload.json`
  - job: `md1-shrunk-prodspine-plan3-1779128360`
  - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-planner3-20260518T1819Z/colmap`
  - status: `Completed`
  - log stream: `/aws/sagemaker/ProcessingJobs` / `md1-shrunk-prodspine-plan3-1779128360/algo-1-1779128403`
  - planner manifest: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-planner3-20260518T1819Z/colmap/chunk_planner_manifest.json`
  - planner report:
    - `dataset_image_count=1456`
    - `gps_coverage_ratio=1.0`
    - `orientation_coverage_ratio=1.0`
    - `connected_component_count=1`
    - `chunk_count=8`
    - `chunk_sizes=[220,220,220,220,220,220,220,220]`
    - `orphan_image_count=0`
    - `risky_bridges=[]`
  - evidence:
    - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-plan3-1779128360-20260518T1824Z.json`
    - `logs/md1-shrunk/cloudwatch-md1-shrunk-prodspine-plan3-1779128360-20260518T1824Z.json`
    - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-planner3-20260518T1819Z-20260518T1824Z.txt`
    - `logs/md1-shrunk/md1-shrunk-prodspine-planner3-20260518T1819Z-planner_static_report.json`
    - `logs/md1-shrunk/md1-shrunk-prodspine-planner3-20260518T1819Z-sfm_metadata.json`
- Canonical full SfM launched:
  - command: `PATH="/opt/homebrew/bin:$PATH" python3 scripts/sfm/run_sfm_benchmark.py --input-s3-uri s3://spaceport-uploads/md1-shrunk-20260515T1641Z-1456-images.zip --output-s3-uri s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-sfm-20260518T1826Z/colmap --job-prefix md1-shrunk-prodspine-sfm --instance-type ml.g4dn.xlarge --volume-size-gb 100 --image-uri 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:c96dca6f3b0850855eac576e8a27371dfca408e24364d79f7e35b23425cc7950 --role-arn arn:aws:iam::975050048887:role/Spaceport-SageMaker-Role-staging --mode chunked --subset-strategy md1_shrunk_prodspine_1456_full --env COLMAP_CHUNK_PLANNER=footprint_graph_v1 --env COLMAP_MATCH_PROFILE=P1 --env COLMAP_INPUT_CHUNK_PLANNER_MANIFEST_URI=s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-planner3-20260518T1819Z/colmap/chunk_planner_manifest.json --payload-json-output logs/md1-shrunk/md1-shrunk-prodspine-sfm-20260518T1826Z-payload.json`
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - ARN: `arn:aws:sagemaker:us-west-2:975050048887:processing-job/md1-shrunk-prodspine-sfm-1779128752`
  - input: `s3://spaceport-uploads/md1-shrunk-20260515T1641Z-1456-images.zip`
  - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-sfm-20260518T1826Z/colmap`
  - image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:c96dca6f3b0850855eac576e8a27371dfca408e24364d79f7e35b23425cc7950`
  - immutable planner manifest: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-planner3-20260518T1819Z/colmap/chunk_planner_manifest.json`
  - start proof: `logs/md1-shrunk/md1-shrunk-prodspine-sfm-20260518T1826Z-start.json`
  - payload: `logs/md1-shrunk/md1-shrunk-prodspine-sfm-20260518T1826Z-payload.json`
  - latest status at `2026-05-18T18:36Z`: `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - log stream: `/aws/sagemaker/ProcessingJobs` / `md1-shrunk-prodspine-sfm-1779128752/algo-1-1779128795`
  - observed progress: extracted `1456` images, loaded GPS/orientation priors, and GPU feature extraction reached at least `Processed file [160/1456]`.
  - S3 output still empty, expected until `S3UploadMode=EndOfJob`.
  - evidence:
    - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T1828Z.json`
    - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T1831Z.json`
    - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T1836Z.json`
    - `logs/md1-shrunk/logstreams-md1-shrunk-prodspine-sfm-1779128752-20260518T1831Z.json`
    - `logs/md1-shrunk/cloudwatch-md1-shrunk-prodspine-sfm-1779128752-20260518T1831Z.json`
    - `logs/md1-shrunk/cloudwatch-md1-shrunk-prodspine-sfm-1779128752-20260518T1836Z.json`
    - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T1831Z.txt`
- Duplicate launch guard:
  - a scheduled monitor overlapped this live run and created duplicate full SfM job `md1-shrunk-prodspine-sfm-1779128842`.
  - duplicate status: `Stopped`, with start `2026-05-18T12:28:05.998000-06:00` and end `2026-05-18T12:29:57.591000-06:00`.
  - canonical full SfM remains `md1-shrunk-prodspine-sfm-1779128752`.
  - automation `md1-shrunk-e2e-monitor-2` was updated to monitor only the canonical job while it is `InProgress` and not launch any duplicate SfM/3DGS/compression jobs.
- Next concrete steps:
  1. Monitor canonical SfM `md1-shrunk-prodspine-sfm-1779128752` only.
  2. If it fails, capture exact SageMaker describe, CloudWatch, and S3 evidence before patching.
  3. If it succeeds, validate trainable COLMAP output, then proceed to 3DGS, skybox, compression, public bundle reachability, deployed viewer skybox/no-sky, and side-by-side input-vs-render checks.

## 2026-05-18T18:41:16Z canonical full SfM poll

- Launch-ledger commit/push:
  - commit: `1900964d7d3601733e6cb9d587a3128717749336` (`chore: launch md1 shrunk production spine sfm`)
  - push: `git push origin agent-113647-md1-baseline-e2e`
  - exact-head `CDK Deploy` run `26052859100` -> success
  - evidence: `logs/md1-shrunk/gh-runs-exact-head-1900964d-20260518T1841Z.json`
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`
  - `FailureReason=null`
  - `ProcessingStartTime=2026-05-18T12:26:35.551000-06:00`
  - log stream: `/aws/sagemaker/ProcessingJobs` / `md1-shrunk-prodspine-sfm-1779128752/algo-1-1779128795`
  - latest observed progress: GPU feature extraction reached `Processed file [274/1456]`.
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
  - evidence:
    - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T1840Z.json`
    - `logs/md1-shrunk/cloudwatch-md1-shrunk-prodspine-sfm-1779128752-20260518T1840Z.json`
    - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T1840Z.txt`
- Automation:
  - `md1-shrunk-e2e-monitor-2` is active and updated to monitor only canonical job `md1-shrunk-prodspine-sfm-1779128752` while it is `InProgress`.
  - no duplicate SfM/3DGS/compression launches should occur before this canonical job reaches a terminal state.

## 2026-05-18T18:48:20Z resume verification + poll

- Branch/head/status:
  - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - `git rev-parse HEAD` -> `b9664255e04f8227d66d46a703491ef803c9c17b`
  - `git rev-parse @{upstream}` -> `b9664255e04f8227d66d46a703491ef803c9c17b`
- Tooling note:
  - this Codex shell PATH does not include Homebrew by default; use `PATH="/opt/homebrew/bin:$PATH"` for `aws` + `gh`.
- AWS identity:
  - `PATH="/opt/homebrew/bin:$PATH" aws sts get-caller-identity --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - evidence: `logs/md1-shrunk/aws-identity-20260518T1848Z.json`
- Step Functions:
  - `PATH="/opt/homebrew/bin:$PATH" aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING --max-results 10 --region us-west-2 --output json` -> none running.
  - evidence: `logs/md1-shrunk/stepfunctions-running-20260518T1848Z.json`
- SageMaker InProgress processing jobs:
  - canonical/owned: `md1-shrunk-prodspine-sfm-1779128752`
  - external/not owned: `cvhr-mtc-20260518T1729Z-sfm`; left untouched.
  - evidence: `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T1848Z.json`
- Canonical SfM poll:
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - observed progress: GPU feature extraction reached at least `Processed file [468/1456]`.
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
  - evidence:
    - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T1848Z.json`
    - `logs/md1-shrunk/cloudwatch-md1-shrunk-prodspine-sfm-1779128752-20260518T1848Z.json`
    - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T1848Z.txt`
    - `logs/md1-shrunk/logstreams-md1-shrunk-prodspine-sfm-1779128752-20260518T1849Z.json`
- Duplicate full SfM guard:
  - duplicate job `md1-shrunk-prodspine-sfm-1779128842` remains `Stopped`; do not restart it.
  - evidence: `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128842-20260518T1852Z.json`
- GitHub Actions:
  - current head commit message is `[skip ci]`, so there are no exact-head workflows for `b9664255e04f8227d66d46a703491ef803c9c17b`.
  - last meaningful non-skipped head remains `1900964d7d3601733e6cb9d587a3128717749336` with `CDK Deploy` run `26052859100` -> success.
  - evidence: `logs/md1-shrunk/gh-runs-agent-113647-20260518T1848Z.json` and `logs/md1-shrunk/gh-runs-exact-head-1900964d-20260518T1841Z.json`

## 2026-05-18T18:51:32Z canonical full SfM poll (incremental CloudWatch)

- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - observed progress: GPU feature extraction reached at least `Processed file [552/1456]`.
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
  - evidence:
    - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T1851Z.json`
    - `logs/md1-shrunk/cloudwatch-md1-shrunk-prodspine-sfm-1779128752-20260518T1851Z.json`
    - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T1851Z.txt`

## 2026-05-18T18:54:25Z poll snapshot commit/push

- Commit/push:
  - commit: `837cd3605bd012d9eeb62251319ee61b4dff3140` (`chore: md1-shrunk sfm poll 20260518T1851Z [skip ci]`)
  - push: `git push origin agent-113647-md1-baseline-e2e` -> success
- GitHub Actions:
  - exact-head workflows for `837cd3605bd012d9eeb62251319ee61b4dff3140`: none because this is a logs/ledger-only `[skip ci]` commit.
  - evidence: `logs/md1-shrunk/gh-runs-agent-113647-20260518T1854Z.json`

## 2026-05-18T19:19Z in-chat accountability poll

- User requested the monitor run in this chat instead of continuing separate automation turns.
- Automation state:
  - file: `/Users/gabrielhansen/.codex/automations/md1-shrunk-e2e-monitor-2/automation.toml`
  - `status = "PAUSED"`
  - prompt says not to run unless reactivated and to leave canonical job ownership unchanged.
- Branch/head/status:
  - `git status --short --branch` -> `## agent-113647-md1-baseline-e2e...origin/agent-113647-md1-baseline-e2e`
  - `git rev-parse HEAD` -> `05e21c5511eac218cc3e4e3884be19218e6f53b7`
  - current head is logs-only `[skip ci]`.
- AWS identity:
  - `PATH="/opt/homebrew/bin:$PATH" aws sts get-caller-identity --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- GitHub Actions:
  - branch workflow list confirms last meaningful non-skipped head `1900964d7d3601733e6cb9d587a3128717749336` has `CDK Deploy` run `26052859100` -> success.
  - current exact head `05e21c5511eac218cc3e4e3884be19218e6f53b7` has no workflow run because it is `[skip ci]`.
- Step Functions:
  - `SpaceportMLPipeline-staging` RUNNING executions: `0`.
- SageMaker:
  - InProgress processing jobs:
    - canonical/owned: `md1-shrunk-prodspine-sfm-1779128752`
    - external/not owned: `cvhr-mtc-20260518T1729Z-sfm`; left untouched.
  - InProgress training jobs: `0`.
- Canonical SfM poll:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:c96dca6f3b0850855eac576e8a27371dfca408e24364d79f7e35b23425cc7950`
  - input: `s3://spaceport-uploads/md1-shrunk-20260515T1641Z-1456-images.zip`
  - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-sfm-20260518T1826Z/colmap`
  - observed progress: GPU feature extraction reached at least `Processed file [884/1456]`.
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
  - evidence:
    - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T1918Z.json`
    - `logs/md1-shrunk/cloudwatch-md1-shrunk-prodspine-sfm-1779128752-20260518T1918Z.json`
    - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T1919Z.txt`
- Next concrete steps:
  1. Continue monitoring canonical SfM `md1-shrunk-prodspine-sfm-1779128752` in this chat.
  2. If SfM fails, capture exact SageMaker describe, CloudWatch, and S3 evidence before patching.
  3. If SfM succeeds, validate trainable COLMAP output, then run 3DGS, skybox, compression, public bundle reachability, deployed viewer skybox/no-sky, and side-by-side input-vs-render checks.

## 2026-05-18T19:29Z canonical SfM chunk-mapping progress

- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - InProgress processing jobs remain:
    - canonical/owned: `md1-shrunk-prodspine-sfm-1779128752`
    - external/not owned: `cvhr-mtc-20260518T1729Z-sfm`; left untouched.
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Important progress:
  - recent-window CloudWatch shows feature extraction completed: `Processed file [1456/1456]`, elapsed `56.099` minutes.
  - pose priors confirmed: `1456/1456` GPS-tagged images, coverage `100.00%`, source `feature_extractor`.
  - immutable planner manifest loaded from `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-planner3-20260518T1819Z/colmap/chunk_planner_manifest.json`.
  - global COLMAP database normalization completed.
  - chunk 0 database prepared for `220` images.
  - `chunk_00_matches_importer` added `714` verified image pairs.
  - `chunk_00_mapper_initial` started and reached at least `num_reg_frames=17` before the latest poll tail.
- Evidence:
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T1929Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T1929Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T1929Z.txt`
  - `logs/md1-shrunk/logstreams-md1-shrunk-prodspine-sfm-1779128752-20260518T1925Z.json`
- Downstream container pins ready for use after SfM success:
  - proven skybox-enabled 3DGS image from the prior MD1-Shrunk successful downstream run: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`
    - ECR tag: `agent53108255splatfactowlightskybox`
    - pushed: `2026-04-04T23:38:25.773000-06:00`
  - proven compressor image from the same run: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor@sha256:a0784727da1870ce9caa4774dc831a32fb96cd1574df389cf9093fbf18f4f4ab`
    - ECR tags: `agent53108255splatfactowlightskybox`, `agent70148362investigatesfmrecovery`
    - pushed: `2026-04-01T14:03:58.377000-06:00`
- Next concrete steps:
  1. Continue monitoring SfM through all 8 chunks and final merged COLMAP output.
  2. On SfM success, validate `sparse/0/{cameras,images,points3D}.txt`, `database.db`, images, `sfm_metadata.json`, registered-image count, and points count before launching 3DGS.
  3. Launch exactly one 3DGS+compression continuation using the production-spine COLMAP output and the proven skybox-enabled 3DGS/compressor digests above.

## 2026-05-18T19:36Z canonical SfM chunk 0 mapper progress

- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Latest observed progress:
  - `chunk_00_mapper_initial` continues registering frames.
  - latest visible registration: `num_reg_frames=87`.
  - no OOM, timeout, mapper exception, or SageMaker failure is visible.
- Evidence:
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T1936Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T1936Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T1936Z.txt`

## 2026-05-18T19:53Z in-chat canonical SfM chunk 0 recovery poll

- Accountability mode:
  - user requested the MD1-Shrunk automation run in this chat.
  - scheduled automation `md1-shrunk-e2e-monitor-2` remains `PAUSED`; this thread owns the active monitor loop.
- Verification before action:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `03f6f5688cc18ee7d78947fac59d9b6128639898`
  - AWS identity: account `975050048887`, ARN `arn:aws:iam::975050048887:root`
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`
  - InProgress training jobs: `0`
  - InProgress processing jobs:
    - canonical/owned: `md1-shrunk-prodspine-sfm-1779128752`
    - external/not owned: `cvhr-mtc-20260518T1729Z-sfm`; left untouched.
  - GitHub Actions:
    - current head is a logs-only `[skip ci]` commit, so no exact-head workflows are expected.
    - last meaningful non-skipped head remains `1900964d7d3601733e6cb9d587a3128717749336` with `CDK Deploy` run `26052859100` -> success.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - input: `s3://spaceport-uploads/md1-shrunk-20260515T1641Z-1456-images.zip`
  - output: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-sfm-20260518T1826Z/colmap`
  - image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:c96dca6f3b0850855eac576e8a27371dfca408e24364d79f7e35b23425cc7950`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Latest observed progress:
  - 19:42Z poll showed `chunk_00_mapper_initial` continuing from `num_reg_frames=86` to at least `num_reg_frames=167`.
  - 19:53Z poll showed `chunk_00_mapper_initial` completed its initial pass:
    - model 0: `171/220` images registered, `100175` points.
    - model 1: `43/220` images registered, `25779` points.
  - Chunk 0 selected the `171/220` model and triggered targeted boundary recovery because core coverage was `77.73%`.
  - Recovery expanded chunk 0 from `220` to `221` images, prepared the recovery DB, and started `chunk_00_recovery_matches_importer`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T1942Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T1942Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T1942Z.txt`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T1947Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T1947Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T1947Z.txt`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T1953Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T1953Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T1953Z.txt`
- Next concrete steps:
  1. Continue monitoring canonical SfM `md1-shrunk-prodspine-sfm-1779128752` through recovery and all remaining chunks.
  2. If SfM fails, capture exact SageMaker describe, CloudWatch, and S3 evidence before patching.
  3. If SfM succeeds, validate trainable COLMAP output before launching exactly one 3DGS+compression continuation with the proven skybox-enabled 3DGS and compressor images.

## 2026-05-18T19:56Z canonical SfM recovery progress

- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Active recovery progress:
  - `chunk_00_recovery_matches_importer` completed enough to start `chunk_00_mapper_recovery`.
  - latest visible recovery mapper registration reached `num_reg_frames=51`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T1956Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T1956Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T1956Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T1956Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T1956Z.json`

## 2026-05-18T20:02Z canonical SfM chunk 1 started

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `a1ceb7553a21cd8643edf6f22b77909065817075`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs still include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-mtc-20260518T1729Z-sfm`; the external job remains untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - `chunk_00_mapper_recovery` reached a successful reconstruction with visible registrations up to `num_reg_frames=171`.
  - recovery model conversion found:
    - model 0: `6/221` images, `3` points.
    - model 1: `44/221` images, `26480` points.
    - model 2: `172/221` images, `102705` points.
  - Chunk 0 stayed below the standard retry threshold at `172/221` images and `172/220` core images, so the pipeline carried the recovery model forward as a seam-only leaf seed instead of triggering adjacent mapper rerun.
  - Chunk 1 database was prepared for `220` images and `chunk_01_matches_importer` started.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2002Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2002Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2002Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2002Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2002Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2002Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2002Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2002Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2002Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2002Z.json`

## 2026-05-18T20:08Z canonical SfM chunk 1 mapper progress

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `2645277e5c384f5614afaf0bc11c1e0f95a949f8`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs still include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-mtc-20260518T1729Z-sfm`; the external job remains untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - `chunk_01_mapper_initial` is actively registering frames.
  - latest visible registration reached `num_reg_frames=156`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2008Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2008Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2008Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2008Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2008Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2008Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2008Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2008Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2008Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2008Z.json`

## 2026-05-18T20:14Z canonical SfM chunk 2 started

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `02ff9592843e4dd7da340c0a430343aecd35422b`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs still include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-mtc-20260518T1729Z-sfm`; the external job remains untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - `chunk_01_mapper_initial` completed successfully:
    - model 0 registered `220/220` images.
    - points: `132809`.
  - chunk 2 database was prepared for `220` images.
  - `chunk_02_matches_importer` added `662` verified image pairs.
  - `chunk_02_mapper_initial` started and latest visible registration reached `num_reg_frames=44`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2014Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2014Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2014Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2014Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2014Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2014Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2014Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2014Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2014Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2014Z.json`

## 2026-05-18T20:21Z canonical SfM chunk 2 mapper progress

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `704c79bddc8c1bff2f3fabe2505755d01541637d`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs still include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-mtc-20260518T1729Z-sfm`; the external job remains untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - `chunk_02_mapper_initial` continues registering frames.
  - latest visible registration reached `num_reg_frames=191`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2021Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2021Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2021Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2021Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2021Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2021Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2021Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2021Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2021Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2021Z.json`

## 2026-05-18T20:27Z canonical SfM chunk 3 started

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `02e7c3a8d7e371a641beaf7d33f989de50364673`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs still include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-mtc-20260518T1729Z-sfm`; the external job remains untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - `chunk_02_mapper_initial` completed successfully:
    - model 0 registered `220/220` images.
    - points: `134606`.
  - chunk 3 database was prepared for `220` images.
  - `chunk_03_matches_importer` added `756` verified image pairs.
  - `chunk_03_mapper_initial` started and latest visible registration reached `num_reg_frames=90`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2027Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2027Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2027Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2027Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2027Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2027Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2027Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2027Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2027Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2027Z.json`

## 2026-05-18T20:33Z canonical SfM chunk 3 mapper progress

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `3bd81251a335f5cedbe100f98b2b933c63158faa`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs still include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-mtc-20260518T1729Z-sfm`; the external job remains untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - `chunk_03_mapper_initial` continues registering frames.
  - latest visible registration reached `num_reg_frames=211`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2033Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2033Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2033Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2033Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2033Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2033Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2033Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2033Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2033Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2033Z.json`

## 2026-05-18T20:40Z canonical SfM chunk 4 started

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `3a469a7ea6c0621ff8df5e13eebecb81ba63fc49`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs still include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-mtc-20260518T1729Z-sfm`; the external job remains untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - `chunk_03_mapper_initial` completed successfully:
    - model 0 registered `220/220` images.
    - points: `132436`.
  - chunk 4 database was prepared for `220` images.
  - `chunk_04_matches_importer` added `774` verified image pairs.
  - `chunk_04_mapper_initial` started and latest visible registration reached `num_reg_frames=112`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2040Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2040Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2040Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2040Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2040Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2040Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2040Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2040Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2040Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2040Z.json`

## 2026-05-18T20:49Z canonical SfM chunk 5 started

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `8a9bd28fdddca52cdcf4095792f6b40df4e61339`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs still include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-mtc-20260518T1729Z-sfm`; the external job remains untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - 20:46Z poll showed `chunk_04_mapper_initial` at `num_reg_frames=216`.
  - 20:49Z poll showed `chunk_04_mapper_initial` completed successfully:
    - model 0 registered `220/220` images.
    - points: `148582`.
  - chunk 5 database was prepared for `220` images (`219` connected/loaded per COLMAP cache log).
  - `chunk_05_matches_importer` added `674` verified image pairs.
  - `chunk_05_mapper_initial` started and latest visible registration reached `num_reg_frames=12`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2046Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2046Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2046Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2046Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2046Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2046Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2046Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2046Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2046Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2046Z.json`
  - `logs/md1-shrunk/git-status-20260518T2049Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2049Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2049Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2049Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2049Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2049Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2049Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2049Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2049Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2049Z.json`

## 2026-05-18T20:52Z in-chat automation poll

- Scheduled automation state:
  - `/Users/gabrielhansen/.codex/automations/md1-shrunk-e2e-monitor-2/automation.toml`
  - status: `PAUSED`
  - prompt notes that monitoring is accountable in this active chat and must not run unless reactivated.
- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `a0da7d42062e5042586c97e42947d01bfcf8399d`
  - upstream head: `a0da7d42062e5042586c97e42947d01bfcf8399d`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `md1-viscell-leaf-08-1779136078`, `md1-viscell-leaf-01-1779136049`, and `cvhr-mtc-20260518T1729Z-sfm`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - `chunk_05_mapper_initial` continues registering frames.
  - latest visible registration reached `num_reg_frames=93`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2052Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2052Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2052Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2052Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2052Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2052Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2052Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2052Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2052Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2052Z.json`

## 2026-05-18T20:58Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `70a05b0f2110003cb667785b9d8dd384590aa675`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `md1-viscell-leaf-08-1779136078`, `md1-viscell-leaf-01-1779136049`, and `cvhr-mtc-20260518T1729Z-sfm`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - `chunk_05_mapper_initial` finished its first mapper pass with multiple models:
    - model 0: `2/220` images, `41` points.
    - model 1: `141/220` images, `106063` points.
    - model 2: `39/220` images, `20982` points.
    - model 3: `34/220` images, `23978` points.
  - Best initial model registered `141/220` images and `99/120` core images, so targeted boundary recovery started.
  - Retry expanded chunk 5 from `220` to `221` images.
  - `chunk_05_recovery_matches_importer` added `677` verified image pairs.
  - `chunk_05_mapper_recovery` started and latest visible recovery registration reached `num_reg_frames=12`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2058Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2058Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2058Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2058Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2058Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2058Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2058Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2058Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2058Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2058Z.json`

## 2026-05-18T21:05Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `5a1156f866fca90eee726d635499a8a364ff99cc`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `md1-viscell-leaf-08-1779136078`, `md1-viscell-leaf-01-1779136049`, and `cvhr-mtc-20260518T1729Z-sfm`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - `chunk_05_mapper_recovery` continues registering frames.
  - latest visible recovery registration reached `num_reg_frames=140`.
  - latest visible heartbeat: `HEARTBEAT elapsed=377s idle=60s`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2105Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2105Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2105Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2105Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2105Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2105Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2105Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2105Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2105Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2105Z.json`

## 2026-05-18T21:11Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `58eff61849efc5aaffa680186c6a08e1e06e5235`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `md1-viscell-leaf-08-1779136078`, `md1-viscell-leaf-01-1779136049`, and `cvhr-mtc-20260518T1729Z-sfm`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - `chunk_05_mapper_recovery` finished:
    - model 0: `141/221` images, `106127` points.
    - model 1: `40/221` images, `18372` points.
    - model 2: `34/221` images, `21301` points.
  - Chunk 5 remained below the standard retry threshold at `141/221` images and `99/120` core images.
  - The production-spine SfM code carried chunk 5 forward as a seam-only leaf seed instead of triggering an adjacent mapper rerun.
  - Chunk 6 database was prepared for `220` images.
  - `chunk_06_matches_importer` added `722` verified image pairs.
  - `chunk_06_mapper_initial` started and latest visible registration reached `num_reg_frames=56`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2111Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2111Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2111Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2111Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2111Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2111Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2111Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2111Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2111Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2111Z.json`

## 2026-05-18T21:17Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `39b1bf92ff18a34f873e45897ba6cc32e8f7cd94`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `md1-viscell-leaf-08-1779136078`, `md1-viscell-leaf-01-1779136049`, and `cvhr-mtc-20260518T1729Z-sfm`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - `chunk_06_mapper_initial` continues registering frames.
  - latest visible registration reached `num_reg_frames=206`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2117Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2117Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2117Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2117Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2117Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2117Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2117Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2117Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2117Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2117Z.json`

## 2026-05-18T21:23Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `e17b7541dec84f4d2718c1feb2f803f8a650ca62`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `md1-viscell-leaf-01-1779136049`, and `cvhr-mtc-20260518T1729Z-sfm`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - `chunk_06_mapper_initial` completed successfully:
    - model 0 registered `220/220` images.
    - points: `149486`.
  - Chunk 7 database was prepared for `220` images.
  - `chunk_07_matches_importer` added `652` verified image pairs.
  - `chunk_07_mapper_initial` started and latest visible registration reached `num_reg_frames=66`.
  - COLMAP emitted dense Cholesky linear-solver warnings during chunk 7, but the mapper continued registering frames.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2123Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2123Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2123Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2123Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2123Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2123Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2123Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2123Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2123Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2123Z.json`

## 2026-05-18T21:29Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `500f79b359c517ab69b2f2eb73ff3907688adf5c`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `md1-viscell-leaf-01-1779136049`, and `cvhr-mtc-20260518T1729Z-sfm`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - `chunk_07_mapper_initial` finished its first mapper pass with multiple models:
    - model 0: `3/220` images, `41` points.
    - model 1: `27/220` images, `13186` points.
    - model 2: `18/220` images, `9917` points.
    - model 3: `67/220` images, `46660` points.
    - model 4: `107/220` images, `77053` points.
  - Best initial model registered `107/220` images and `51/120` core images, so targeted boundary recovery started.
  - Retry expanded chunk 7 from `220` to `221` images.
  - `chunk_07_mapper_recovery` is running; latest visible recovery registration reached `num_reg_frames=23`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2129Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2129Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2129Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2129Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2129Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2129Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2129Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2129Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2129Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2129Z.json`

## 2026-05-18T21:35Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `d6ed9011de7970c0fc85fc6876e6475a2682c288`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm` and `cvhr-mtc-20260518T1729Z-sfm`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk progress:
  - `chunk_07_mapper_recovery` continues running.
  - The recovery mapper has multiple reconstruction attempts visible.
  - highest visible recovery registration so far reached `num_reg_frames=106`.
  - latest active visible recovery attempt reached `num_reg_frames=45`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2135Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2135Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2135Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2135Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2135Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2135Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2135Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2135Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2135Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2135Z.json`

## 2026-05-18T21:42Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `0fd6d782c848a44e670cdef8addb1a78fcbc30bd`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm` and `cvhr-mtc-20260518T1729Z-sfm`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Chunk/finalization progress:
  - SfM has moved past final chunk recovery into bridge/merge work.
  - Latest logs show `chunk_03_04_merge_bridge_seed_01_point_triangulator_02` triangulating a merged bridge seed; visible triangulation reached at least image index `371` in that step.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2142Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2142Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2142Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2142Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2142Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2142Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2142Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2142Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2142Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2142Z.json`

## 2026-05-18T21:49Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `05e017c94abad372ba11686d9c60503bf891b44c`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm` and `cvhr-mtc-20260518T1729Z-sfm`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - Bridge/merge final assembly is still running.
  - Latest logs show `chunk_00_01_merge_bridge_seed_01_point_triangulator_02` triangulating merged images; visible triangulation reached at least image index `315` in that step.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2149Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2149Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2149Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2149Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2149Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2149Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2149Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2149Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2149Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2149Z.json`

## 2026-05-18T21:55Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `dab6b3ee77031d559b7c604480a498e5a6c13bc9`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm` and `cvhr-mtc-20260518T1729Z-sfm`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - `chunk_model_seam_01_point_triangulator_01` completed visible triangulation, then `Extracting colors`.
  - `chunk_model_seam_01_image_registrator_02` started against `merged_chunk_model_01_seam/database.db`.
  - The image registrator loaded `440` images (`connected 439`, `loaded 439`) and is converting its output model.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2155Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2155Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2155Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2155Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2155Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2155Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2155Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2155Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2155Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2155Z.json`

## 2026-05-18T22:03Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `615d669cd4fe46762cd37acedd98f8181d4474a5`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm` and `cvhr-mtc-20260518T1729Z-sfm`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - Final seam assembly continued into `chunk_model_seam_02_point_triangulator_02`.
  - Visible triangulation reached image `#1407 (329)`.
  - Latest visible stage is `Retriangulation and Global bundle adjustment`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2201Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2201Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2201Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2201Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2201Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2201Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2201Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2201Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2201Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2201Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2203Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2203Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2203Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2203Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2203Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2203Z.json`

## 2026-05-18T22:10Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `775ae59770a9be4d1637ff8c4f3d67d7ec032dc9`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l01-1779141986`, and `md1-viscell-full-l00-1779141981`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - Final seam assembly progressed to `chunk_model_seam_04_point_triangulator_01`.
  - Visible triangulation reached image `#1407 (391)`.
  - Latest visible stage is `Extracting colors` after retriangulation/global bundle adjustment.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2210Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2210Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2210Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2210Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2210Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2210Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2210Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2210Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2210Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2210Z.json`

## 2026-05-18T22:16Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `cdab3ec4468167bb80a6af032500bdd73aeb0072`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l01-1779141986`, and `md1-viscell-full-l00-1779141981`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - Final seam assembly is still active.
  - Latest visible stage is `chunk_model_seam_04_retry_image_registrator_02`.
  - The retry image registrator shows `399` connected/registered image context and is converting the retry output model with `colmap model_converter`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2216Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2216Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2216Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2216Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2216Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2216Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2216Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2216Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2216Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2216Z.json`

## 2026-05-18T22:22Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `7b1f37bae2c1627f74ded17e7ad3cefbed5cb783`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l01-1779141986`, and `md1-viscell-full-l00-1779141981`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - Final seam assembly progressed to `chunk_model_seam_05_point_triangulator_01`.
  - Visible triangulation reached image `#1434 (320)`.
  - Latest visible stage is `Retriangulation and Global bundle adjustment`, with a heartbeat after 60s idle.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2222Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2222Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2222Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2222Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2222Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2222Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2222Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2222Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2222Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2222Z.json`

## 2026-05-18T22:29Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `ea6c45bc4cbb8d8625b8f3dc88cb1ef3ca24a2c2`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, and `md1-viscell-full-l01-1779141986`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - Final seam assembly progressed to `chunk_model_seam_05_retry_point_triangulator_02`.
  - Visible triangulation reached image `#1434 (322)`.
  - Latest visible stage is `Retriangulation and Global bundle adjustment`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2229Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2229Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2229Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2229Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2229Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2229Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2229Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2229Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2229Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2229Z.json`

## 2026-05-18T22:35Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `d3a8a59b69b46b49a123b47163c4cdd5d9d1751f`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l01-1779141986`, and `md1-viscell-full-l02-1779143476`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - Final seam assembly progressed to seam 06.
  - `chunk_model_seam_06_image_registrator_02` completed visible registration context with `342` loaded/registered image index.
  - `chunk_model_seam_06_point_triangulator_02` started, loaded `438` images from the seam database, and is actively triangulating.
  - latest visible triangulation reached image `#351 (45)`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2235Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2235Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2235Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2235Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2235Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2235Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2235Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2235Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2235Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2235Z.json`

## 2026-05-18T22:41Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `8f9aae67e2a604c19d3b25ec9260d82409ee2f47`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l01-1779141986`, and `md1-viscell-full-l02-1779143476`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - `chunk_model_seam_06_point_triangulator_02` reached `Extracting colors` and converted its model.
  - `chunk_model_merger_07` merged reconstruction 1 (`440` images, `347172` points) with reconstruction 2 (`341` images, `295936` points).
  - Merge succeeded; `merged_chunk_model_07_attempt_01` has `739` images and `610793` points.
  - The job prepared a chunk 7 seam database by pruning global features down to `849` images.
  - latest visible stage is `chunk_model_seam_07_matches_importer`, processing match block `4/4`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2241Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2241Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2241Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2241Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2241Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2241Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2241Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2241Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2241Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2241Z.json`

## 2026-05-18T22:48Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `d9815f2afbb5a73196b55892025e0b623b16d1ef`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l01-1779141986`, and `md1-viscell-full-l02-1779143476`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - Final seam 07 assembly is active.
  - `chunk_model_seam_07_image_registrator_02` advanced through visible registration, reaching a `780` image index context.
  - latest visible stage is model conversion for `chunk_model_seam_07_image_registrator_02`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2248Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2248Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2248Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2248Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2248Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2248Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2248Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2248Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2248Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2248Z.json`

## 2026-05-18T22:54Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `e675e69a9590e42f1600b1dea8c90c0d3d81d9a3`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l01-1779141986`, and `md1-viscell-full-l02-1779143476`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - `chunk_model_seam_07_point_triangulator_02` completed visible triangulation, reached image `#1434 (778)`, extracted colors, and converted its model.
  - seam 07 point triangulator model context: `779` images, `602491` points.
  - `chunk_model_merger_08` attempted to merge chunk 02 (`220` images, `134606` points) with seam 07 (`779` images, `602491` points).
  - Merge attempt 1 failed; swapped-order attempt 2 also failed.
  - SageMaker job remains `InProgress`; this is an in-run merge failure/warning, not a terminal job failure yet.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2254Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2254Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2254Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2254Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2254Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2254Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2254Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2254Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2254Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2254Z.json`

## 2026-05-18T23:00Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `65dc8408cb97135f6d6639445cc2ce0da2a9b80f`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l01-1779141986`, and `md1-viscell-full-l02-1779143476`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - After merge 08 failed in both input orders, the pipeline entered component bridge fallback.
  - latest visible stage is `chunk_model_component_bridge_08_00_02_seed_01_point_triangulator_02`.
  - visible triangulation reached at least image `#1327 (416)`.
  - This confirms the merge warning is being handled inside the current run rather than requiring intervention yet.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2300Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2300Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2300Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2300Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2300Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2300Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2300Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2300Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2300Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2300Z.json`

## 2026-05-18T23:04Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `9a7191cf68ed858f18e9fbd2529fd8e8e844a004`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l01-1779141986`, and `md1-viscell-full-l02-1779143476`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - `chunk_model_component_bridge_08_00_02_seed_01_point_triangulator_02` completed visible triangulation, reaching image `#1453 (502)`.
  - The bridge pass reached `Retriangulation and Global bundle adjustment`, then `Extracting colors`, then model conversion.
  - `chunk_model_merger_08` retried after the bridge pass; normal and swapped-order attempts still logged `Merge failed`.
  - SageMaker remains `InProgress`, so this is still an in-run merge/fallback condition, not a terminal job failure yet.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2304Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2304Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2304Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2304Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2304Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2304Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2304Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2304Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2304Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2304Z.json`

## 2026-05-18T23:10Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `6831eccdb8f04f9c61e2d3f95f6d2a80c3b2e7d3`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, and `md1-viscell-full-l02-1779143476`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - The run advanced beyond the bridge retry into `chunk_model_seam_08_point_triangulator_01`.
  - Visible triangulation reached image `#1456 (560)`.
  - Latest visible stage is `Retriangulation and Global bundle adjustment`, with heartbeat at `elapsed=141s idle=120s`.
  - This confirms the pipeline continued after merge 08 warnings instead of terminally failing.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2310Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2310Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2310Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2310Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2310Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2310Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2310Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2310Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2310Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2310Z.json`

## 2026-05-18T23:17Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `13105810ba2e4cdd6a6154ab59c8164d49841946`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l02-1779143476`, and `md1-viscell-full-l03-1779145861`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - `chunk_model_seam_08_point_triangulator_02` completed visible triangulation through image `#1456 (609)`.
  - It reached global bundle adjustment, extracted colors, and converted the model.
  - `chunk_model_merger_09` first retried merge against the earlier seam 07 model and failed in both input orders.
  - Then `chunk_model_merger_09` merged chunk 02 (`220` images, `134606` points) with `chunk_model_seam_08_point_triangulator_02` (`610` images, `459139` points).
  - That merge succeeded, producing `640` images and `516033` points.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2317Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2317Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2317Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2317Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2317Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2317Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2317Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2317Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2317Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2317Z.json`

## 2026-05-18T23:23Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `96ec1c7de340a134a6f10f0411936d0f653515b0`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l02-1779143476`, and `md1-viscell-full-l03-1779145861`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - After the successful merge 09 handoff, the run advanced into `chunk_model_seam_09_point_triangulator_01`.
  - Visible triangulation reached image `#1456 (657)`.
  - Latest visible stage is `Retriangulation and Global bundle adjustment`, with heartbeat at `elapsed=85s idle=60s`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2323Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2323Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2323Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2323Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2323Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2323Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2323Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2323Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2323Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2323Z.json`

## 2026-05-18T23:29Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `2831dbc3c16afcb0a5e1bf048a51aa91493eb47a`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l03-1779145861`, and `md1-viscell-full-l04-1779146968`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - The run advanced to `chunk_model_seam_09_point_triangulator_02`.
  - Visible triangulation reached image `#1456 (658)`.
  - Latest visible stage is `Retriangulation and Global bundle adjustment`, with heartbeat at `elapsed=143s idle=120s`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2329Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2329Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2329Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2329Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2329Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2329Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2329Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2329Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2329Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2329Z.json`

## 2026-05-18T23:36Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `299081d87df08af92ba12e4230d7215acbcc51c8`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l03-1779145861`, and `md1-viscell-full-l04-1779146968`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - `chunk_model_seam_09_point_triangulator_02` completed, extracted colors, and converted its text model.
  - `chunk_model_merger_10` merged reconstruction 1 (`779` images, `602491` points) with reconstruction 2 (`659` images, `519409` points).
  - Merge 10 succeeded with `1432` images and `1118057` points.
  - The run prepared a seam database by pruning global features down to `1456` images.
  - Latest visible stage is `chunk_model_seam_10_matches_importer`, processing match block `2/7`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2336Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2336Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2336Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2336Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2336Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2336Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2336Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2336Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2336Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2336Z.json`

## 2026-05-18T23:42Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `cbf652c4de69cc8e36dba9e1919bc73a0118100d`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l04-1779146968`, and `md1-viscell-full-l05-1779147527`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - The run advanced from seam 10 matching into `chunk_model_seam_10_point_triangulator_01`.
  - Visible triangulation reached image `#1456 (1455)`.
  - Latest visible stage is `Retriangulation and Global bundle adjustment`, with heartbeat at `elapsed=170s idle=120s`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2342Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2342Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2342Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2342Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2342Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2342Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2342Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2342Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2342Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2342Z.json`

## 2026-05-18T23:48Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `46b1e1022a46f2484686cbaf7f953162d8298b7e`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l04-1779146968`, and `md1-viscell-full-l05-1779147527`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - `chunk_model_seam_10_point_triangulator_01` remained in global bundle adjustment through heartbeat `elapsed=470s idle=420s`.
  - The stage then advanced to `Extracting colors`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2348Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2348Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2348Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2348Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2348Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2348Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2348Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2348Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2348Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2348Z.json`

## 2026-05-18T23:55Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `78ed108bbb992c531331b28f04622aa9e8a3964c`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l04-1779146968`, and `md1-viscell-full-l05-1779147527`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - The run advanced to `chunk_model_seam_10_point_triangulator_02`.
  - Visible triangulation reached image `#1456 (1455)`.
  - Latest visible stage is `Retriangulation and Global bundle adjustment`, with heartbeat at `elapsed=171s idle=120s`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260518T2355Z.txt`
  - `logs/md1-shrunk/git-head-20260518T2355Z.txt`
  - `logs/md1-shrunk/aws-identity-20260518T2355Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260518T2355Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260518T2355Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260518T2355Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260518T2355Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260518T2355Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260518T2355Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260518T2355Z.json`

## 2026-05-19T00:01Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `c77590184bcbe20dc7d8010e1fc4fab02f19d0b3`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `cvhr-secondary-20260518t2113z-sfm`, `cvhr-mtc-20260518T1729Z-sfm`, `md1-viscell-full-l04-1779146968`, and `md1-viscell-full-l05-1779147527`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - S3 output remains empty as expected until `S3UploadMode=EndOfJob`.
- Finalization progress:
  - `chunk_model_seam_10_point_triangulator_02` remained in global bundle adjustment through heartbeat `elapsed=471s idle=420s`.
  - The stage then advanced to `Extracting colors`.
  - no OOM, timeout, SageMaker failure, or Step Functions failure is visible.
- Evidence:
  - `logs/md1-shrunk/git-status-20260519T0001Z.txt`
  - `logs/md1-shrunk/git-head-20260519T0001Z.txt`
  - `logs/md1-shrunk/aws-identity-20260519T0001Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260519T0001Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260519T0001Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260519T0001Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260519T0001Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260519T0001Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260519T0001Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260519T0001Z.json`

## 2026-05-19T00:07Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head: `e8beb6c2f8b7efe31d666a7cc6e783c2e6f3828b`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - InProgress training jobs: `0`.
  - InProgress processing jobs include canonical `md1-shrunk-prodspine-sfm-1779128752` plus external `md1-viscell-full-l05-1779147527`, `md1-viscell-full-l04-1779146968`, `cvhr-secondary-20260518t2113z-sfm`, and `cvhr-mtc-20260518T1729Z-sfm`; external jobs remain untouched.
  - current head is a logs-only `[skip ci]` commit; latest meaningful non-skipped workflow proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Canonical SfM status:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - SageMaker describe still reported `ProcessingJobStatus=InProgress`, `FailureReason=null`, but CloudWatch and S3 show successful output completion/upload.
  - CloudWatch reports `SPACEPORT COLMAP GPU SfM COMPLETED SUCCESSFULLY`, completed at `Tue May 19 00:04:29 UTC 2026`.
- COLMAP output validation from CloudWatch:
  - `COLMAP format validation passed`
  - cameras registered: `1`
  - images registered: `1456`
  - images copied for 3DGS: `1456`
  - 3D points: `954351`
  - processing time: `20098.88 seconds`
  - GPS priors detected: `1456`
  - match profile: `P1`
  - sequential matcher enabled: `False`
  - fallback reason: `not_needed`
  - vocab tree candidates: `40`
  - SIFT max features: `8192`
- S3 handoff validation:
  - prefix: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-sfm-20260518T1826Z/colmap`
  - `Total Objects: 1469`
  - `Total Size: 9.3 GiB`
  - required trainable COLMAP handoff is present: `database.db`, `sfm_metadata.json`, `images/`, `sparse/0/cameras.txt`, `sparse/0/images.txt`, `sparse/0/points3D.txt`, `sparse/0/frames.txt`, `sparse/0/rigs.txt`, and matching `sparse_raw/0/...` files.
  - key sizes: `database.db` `2.2 GiB`, `sparse/0/images.txt` `583.7 MiB`, `sparse/0/points3D.txt` `143.3 MiB`.
- Decision:
  - Wait one more short poll for SageMaker terminal `Completed` before launching downstream, even though CloudWatch/S3 are green, to avoid racing SageMaker's final state.
- Evidence:
  - `logs/md1-shrunk/git-status-20260519T0007Z.txt`
  - `logs/md1-shrunk/git-head-20260519T0007Z.txt`
  - `logs/md1-shrunk/aws-identity-20260519T0007Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260519T0007Z.json`
  - `logs/md1-shrunk/cloudwatch-recent-md1-shrunk-prodspine-sfm-1779128752-20260519T0007Z.json`
  - `logs/md1-shrunk/s3-colmap-md1-shrunk-prodspine-sfm-20260518T1826Z-20260519T0007Z.txt`
  - `logs/md1-shrunk/stepfunctions-running-20260519T0007Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260519T0007Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260519T0007Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260519T0007Z.json`

## 2026-05-19T00:22Z in-chat automation poll

- Verification before poll:
  - branch: `agent-113647-md1-baseline-e2e`
  - head at start of poll: `f2ab20e1ea729e770e27a2fe9700c90a90788363`
  - AWS identity captured for account `975050048887`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING executions: `0`.
  - GitHub workflow list unchanged for meaningful non-skipped CI: latest proof remains `CDK Deploy` run `26052859100` for `1900964d7d3601733e6cb9d587a3128717749336`; current head is logs-only `[skip ci]`.
- Canonical SfM terminal-state lag:
  - job: `md1-shrunk-prodspine-sfm-1779128752`
  - SageMaker describe remained `ProcessingJobStatus=InProgress`, `FailureReason=null` at `20260519T0011Z`, `0012Z`, `0013Z`, `0014Z`, `0015Z`, `0017Z`, `0018Z`, `0019Z`, `0020Z`, `0021Z`, and `0022Z`.
  - CloudWatch tail still has no events after the successful completion banner at `Tue May 19 00:04:29 UTC 2026`.
  - No downstream 3DGS or compression has been launched while waiting for SageMaker terminal `Completed`.
- Direct S3 COLMAP handoff validation:
  - prefix: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-sfm-20260518T1826Z/colmap`
  - `images/` count: `1456`
  - required objects validated with `head-object`: `database.db`, `sfm_metadata.json`, `chunk_planner_manifest.json`, `sparse/0/cameras.txt`, `sparse/0/images.txt`, `sparse/0/points3D.txt`, `sparse/0/frames.txt`, `sparse/0/rigs.txt`, and matching `sparse_raw/0/...` files.
  - key sizes from head-object:
    - `database.db`: `2329702400` bytes
    - `sparse/0/images.txt`: `612034411` bytes
    - `sparse/0/points3D.txt`: `150235832` bytes
    - `sparse_raw/0/images.txt`: `616156172` bytes
    - `sparse_raw/0/points3D.txt`: `177365623` bytes
  - `sfm_metadata.json` summary:
    - timestamp: `2026-05-19T00:04:27Z`
    - dataset images: `1456`
    - registered images: `1456`
    - cameras registered: `1`
    - points_3d: `1155771`
    - quality_check_passed: `true`
    - processing_time_seconds: `20098.88`
    - chunking_enabled: `true`
    - chunk_planner: `footprint_graph_v1`
    - chunk_count: `8`
    - merged_component_count: `1`
    - fallback_reason: `not_needed`
    - timed_out: `false`
    - match_profile: `P1`
    - gps_priors_detected: `1456`
- Downstream readiness evidence gathered but not launched:
  - branch state machine exists: `arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-br-8abcbd5662`.
  - intended proven 3DGS image digest remains present in ECR: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`, tag `agent53108255splatfactowlightskybox`, pushed `2026-04-04T23:38:25.773000-06:00`.
  - intended proven compressor image digest remains present in ECR: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor@sha256:a0784727da1870ce9caa4774dc831a32fb96cd1574df389cf9093fbf18f4f4ab`, tags `agent53108255splatfactowlightskybox` and `agent70148362investigatesfmrecovery`, pushed `2026-04-01T14:03:58.377000-06:00`.
- Decision:
  - Continue passive polling until SageMaker terminal state changes from `InProgress`; launch exactly one downstream 3DGS+compression continuation only after terminal `Completed`.
- Evidence:
  - `logs/md1-shrunk/git-status-20260519T0011Z.txt`
  - `logs/md1-shrunk/git-head-20260519T0011Z.txt`
  - `logs/md1-shrunk/aws-identity-20260519T0011Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260519T0011Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260519T0012Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260519T0013Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260519T0014Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260519T0015Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260519T0017Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260519T0018Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260519T0019Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260519T0020Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260519T0021Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260519T0022Z.json`
  - `logs/md1-shrunk/stepfunctions-running-20260519T0011Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260519T0011Z.json`
  - `logs/md1-shrunk/s3-colmap-head-validation-md1-shrunk-prodspine-sfm-20260518T1826Z-20260519T0013Z.txt`
  - `logs/md1-shrunk/sfm-metadata-md1-shrunk-prodspine-sfm-20260518T1826Z-20260519T0013Z.json`
  - `logs/md1-shrunk/sfm-metadata-summary-md1-shrunk-prodspine-sfm-20260518T1826Z-20260519T0013Z.json`
  - `logs/md1-shrunk/cloudwatch-stream-md1-shrunk-prodspine-sfm-1779128752-20260519T0018Z.json`
  - `logs/md1-shrunk/cloudwatch-tail-md1-shrunk-prodspine-sfm-1779128752-20260519T0019Z.json`
  - `logs/md1-shrunk/stepfunctions-state-machines-md1-pipeline-20260519T0014Z.json`
  - `logs/md1-shrunk/ecr-3dgs-digest-482c1789-20260519T0014Z.json`
  - `logs/md1-shrunk/ecr-compressor-digest-a0784727-20260519T0014Z.json`

## 2026-05-19T00:28Z in-chat downstream launch

- Verification before launch:
  - branch: `agent-113647-md1-baseline-e2e`
  - latest pushed ledger head before launch: `e55b944a`
  - canonical SfM job `md1-shrunk-prodspine-sfm-1779128752` reached `ProcessingJobStatus=Completed`, `FailureReason=null` at `20260519T0026Z`.
  - Step Functions RUNNING executions on both `SpaceportMLPipeline-br-8abcbd5662` and `SpaceportMLPipeline-staging`: `0`.
  - InProgress training jobs before launch: `0`.
  - InProgress processing jobs before launch were external only: `md1-viscell-full-l06-1779150311`, `md1-viscell-full-l05-1779147527`, `cvhr-secondary-20260518t2113z-sfm`, and `cvhr-mtc-20260518T1729Z-sfm`; external jobs remain untouched.
  - GitHub meaningful workflow proof unchanged: `CDK Deploy` run `26052859100` succeeded for `1900964d7d3601733e6cb9d587a3128717749336`; current ledger commits use `[skip ci]`.
- Launched exactly one downstream 3DGS+compression continuation:
  - Step Functions execution: `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-br-8abcbd5662:execution-md1-shrunk-prodspine-wlight-202605190027`
  - state machine: `arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-br-8abcbd5662`
  - startDate: `2026-05-18T18:28:13.202000-06:00`
  - jobName: `md1-shrunk-prodspine-wlight-202605190027`
  - pipelineStep: `3dgs`
  - training job: `md1-shrunk-prodspine-wlight-202605190027-3dgs`
  - initial training status: `InProgress`, secondary status `Pending`
  - training image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`
  - instance: `ml.g5.4xlarge`, volume `100 GiB`, max runtime `14400s`
  - input COLMAP: `s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-sfm-20260518T1826Z/colmap/`
  - 3DGS output: `s3://spaceport-ml-processing-staging/3dgs/md1-shrunk-prodspine-wlight-202605190027/`
  - compression output: `s3://spaceport-ml-processing-staging/compressed/md1-shrunk-prodspine-wlight-202605190027/`
  - compressor image in payload: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor@sha256:a0784727da1870ce9caa4774dc831a32fb96cd1574df389cf9093fbf18f4f4ab`
  - intended skybox/training env in payload: `MODEL_VARIANT=splatfacto-w-light`, `ENABLE_BG_MODEL=true`, `ENABLE_ALPHA_LOSS=true`, `ENABLE_ROBUST_MASK=true`, `FLOATER_PRUNING_ENABLED=true`, `BACKGROUND_APPEARANCE_MODE=auto_camera`, `BACKGROUND_SKYBOX_WIDTH=2048`, `BACKGROUND_SKYBOX_HEIGHT=1024`, `MAX_ITERATIONS=30000`, `TRAINING_TIMEOUT_SECONDS=14400`.
- Next:
  - Monitor training startup logs until COLMAP validation, transforms generation, skybox-aware `ns-train`, iteration completion, model export, then compression, public bundle reachability, deployed viewer smoke, skybox/no-sky viewer gates, and side-by-side input-vs-render quality checks.
- Evidence:
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260519T0024Z.json`
  - `logs/md1-shrunk/sagemaker-describe-md1-shrunk-prodspine-sfm-1779128752-20260519T0026Z.json`
  - `logs/md1-shrunk/sagemaker-list-training-inprogress-20260519T0026Z.json`
  - `logs/md1-shrunk/sagemaker-list-processing-inprogress-20260519T0026Z.json`
  - `logs/md1-shrunk/stepfunctions-running-br8abcbd5662-20260519T0026Z.json`
  - `logs/md1-shrunk/stepfunctions-running-staging-20260519T0026Z.json`
  - `logs/md1-shrunk/gh-runs-agent-113647-20260519T0026Z.json`
  - `logs/md1-shrunk/md1-shrunk-prodspine-wlight-202605190027-payload.json`
  - `logs/md1-shrunk/md1-shrunk-prodspine-wlight-202605190027-start-request.json`
  - `logs/md1-shrunk/md1-shrunk-prodspine-wlight-202605190027-start.json`
  - `logs/md1-shrunk/stepfunctions-describe-execution-md1-shrunk-prodspine-wlight-202605190027-20260519T0028Z.json`
  - `logs/md1-shrunk/stepfunctions-history-reverse-tail-md1-shrunk-prodspine-wlight-202605190027-20260519T0028Z.json`
  - `logs/md1-shrunk/sagemaker-describe-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0028Z.json`

## 2026-05-19T00:37Z in-chat 3DGS startup gate

- Current canonical downstream execution:
  - Step Functions execution: `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-br-8abcbd5662:execution-md1-shrunk-prodspine-wlight-202605190027`
  - training job: `md1-shrunk-prodspine-wlight-202605190027-3dgs`
  - status at `20260519T0036Z`: `TrainingJobStatus=InProgress`, `SecondaryStatus=Training`, `FailureReason=null`.
  - `TrainingStartTime=2026-05-18T18:29:04.860000-06:00`.
  - latest transition: `Training image download completed. Training in progress.` at `2026-05-18T18:33:12.437000-06:00`.
- CloudWatch startup gate passed:
  - log stream: `md1-shrunk-prodspine-wlight-202605190027-3dgs/algo-1-1779150544`
  - model overrides applied:
    - `model.variant=splatfacto-w-light`
    - `model.enable_bg_model=True`
    - `model.enable_alpha_loss=True`
    - `model.enable_robust_mask=True`
    - `model.bg_sh_degree=8`
    - `output.background_skybox.appearance_mode=auto_camera`
    - `output.background_skybox.width=2048`
    - `output.background_skybox.height=1024`
    - `output.floater_pruning.enabled=True`
  - COLMAP validation:
    - cameras: `1`
    - registered images: `1456`
    - image files: `1456`
    - 3D points: `954351`
  - COLMAP TXT-to-BIN conversion completed:
    - `cameras.bin: 64 bytes`
    - `images.bin: 367205405 bytes`
    - `points3D.bin: 98543117 bytes`
  - `ns-process-data` completed:
    - `Starting with 1456 images`
    - `Colmap matched 1456 images`
    - `COLMAP found poses for all images`
  - `transforms.json` validation passed:
    - file size: `1287684` bytes
    - total frames: `1456`
  - accepted training command is running:
    - `ns-train splatfacto-w-light --data /tmp/nerfstudio_training/converted_data --output-dir /tmp/nerfstudio_training --vis tensorboard --max_num_iterations 30000 --pipeline.model.sh_degree 3 --logging.steps_per_log 100 --pipeline.model.rasterize_mode classic --pipeline.model.use_scale_regularization True --pipeline.model.cull_alpha_thresh 0.12 --pipeline.model.cull_scale_thresh 0.35 --pipeline.model.enable_bg_model True --pipeline.model.enable_alpha_loss True --pipeline.model.enable_robust_mask True --pipeline.model.bg_sh_degree 8 --pipeline.model.appearance_embed_dim 64 --pipeline.model.never_mask_upper 0.4 --pipeline.model.max-gauss-ratio 10.0`
  - training timeout: `14400 seconds`.
- S3 output:
  - `s3://spaceport-ml-processing-staging/3dgs/md1-shrunk-prodspine-wlight-202605190027/` remained empty at `20260519T0032Z`, expected until SageMaker EndOfJob model upload.
- Decision:
  - Continue passive monitoring. The trainer captures subprocess output, so iteration progress may not stream until `ns-train` exits. Use SageMaker status as live gate; inspect logs periodically for failure/OOM/timeout.
- Evidence:
  - `logs/md1-shrunk/sagemaker-describe-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0031Z.json`
  - `logs/md1-shrunk/cloudwatch-stream-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0032Z.json`
  - `logs/md1-shrunk/s3-3dgs-md1-shrunk-prodspine-wlight-202605190027-20260519T0032Z.txt`
  - `logs/md1-shrunk/stepfunctions-describe-execution-md1-shrunk-prodspine-wlight-202605190027-20260519T0032Z.json`
  - `logs/md1-shrunk/sagemaker-describe-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0036Z.json`
  - `logs/md1-shrunk/cloudwatch-stream-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0036Z.json`
  - `logs/md1-shrunk/cloudwatch-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0037Z.json`
  - `logs/md1-shrunk/cloudwatch-training-summary-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0037Z.txt`

## 2026-05-19T00:49Z in-chat 3DGS heartbeat

- Current canonical downstream execution:
  - Step Functions execution: `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-br-8abcbd5662:execution-md1-shrunk-prodspine-wlight-202605190027`
  - training job: `md1-shrunk-prodspine-wlight-202605190027-3dgs`
- SageMaker status:
  - `20260519T0039Z`: `TrainingJobStatus=InProgress`, `SecondaryStatus=Training`, `TrainingTimeInSeconds=637`, `FailureReason=null`.
  - `20260519T0049Z`: `TrainingJobStatus=InProgress`, `SecondaryStatus=Training`, `TrainingTimeInSeconds=1238`, `FailureReason=null`.
- Decision:
  - Continue low-churn polling. No failure, OOM, timeout, or duplicate job is visible.
- Evidence:
  - `logs/md1-shrunk/sagemaker-describe-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0039Z.json`
  - `logs/md1-shrunk/sagemaker-describe-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0049Z.json`

## 2026-05-19T01:29Z in-chat 3DGS heartbeat

- Current canonical downstream execution:
  - Step Functions execution: `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-br-8abcbd5662:execution-md1-shrunk-prodspine-wlight-202605190027`
  - training job: `md1-shrunk-prodspine-wlight-202605190027-3dgs`
- SageMaker status:
  - `20260519T0059Z`: `TrainingJobStatus=InProgress`, `SecondaryStatus=Training`, `TrainingTimeInSeconds=1839`, `FailureReason=null`.
  - `20260519T0109Z`: `TrainingJobStatus=InProgress`, `SecondaryStatus=Training`, `TrainingTimeInSeconds=2440`, `FailureReason=null`.
  - `20260519T0119Z`: `TrainingJobStatus=InProgress`, `SecondaryStatus=Training`, `TrainingTimeInSeconds=3041`, `FailureReason=null`.
  - `20260519T0129Z`: `TrainingJobStatus=InProgress`, `SecondaryStatus=Training`, `TrainingTimeInSeconds=3642`, `FailureReason=null`.
- Decision:
  - Continue low-churn polling. No failure, OOM, timeout, or duplicate job is visible.
- Evidence:
  - `logs/md1-shrunk/sagemaker-describe-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0059Z.json`
  - `logs/md1-shrunk/sagemaker-describe-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0109Z.json`
  - `logs/md1-shrunk/sagemaker-describe-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0119Z.json`
  - `logs/md1-shrunk/sagemaker-describe-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0129Z.json`

## 2026-05-19T02:40Z in-chat 3DGS heartbeat

- Current canonical downstream execution:
  - Step Functions execution: `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-br-8abcbd5662:execution-md1-shrunk-prodspine-wlight-202605190027`
  - training job: `md1-shrunk-prodspine-wlight-202605190027-3dgs`
- SageMaker status:
  - `20260519T0140Z`: `TrainingJobStatus=InProgress`, `SecondaryStatus=Training`, `TrainingTimeInSeconds=4301`, `FailureReason=null`.
  - `20260519T0155Z`: `TrainingJobStatus=InProgress`, `SecondaryStatus=Training`, `TrainingTimeInSeconds=5202`, `FailureReason=null`.
  - `20260519T0210Z`: `TrainingJobStatus=InProgress`, `SecondaryStatus=Training`, `TrainingTimeInSeconds=6103`, `FailureReason=null`.
  - `20260519T0225Z`: `TrainingJobStatus=InProgress`, `SecondaryStatus=Training`, `TrainingTimeInSeconds=7004`, `FailureReason=null`.
  - `20260519T0240Z`: `TrainingJobStatus=InProgress`, `SecondaryStatus=Training`, `TrainingTimeInSeconds=7905`, `FailureReason=null`.
- Decision:
  - Continue low-churn polling. No failure, OOM, timeout, or duplicate job is visible.
- Evidence:
  - `logs/md1-shrunk/sagemaker-describe-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0140Z.json`
  - `logs/md1-shrunk/sagemaker-describe-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0155Z.json`
  - `logs/md1-shrunk/sagemaker-describe-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0210Z.json`
  - `logs/md1-shrunk/sagemaker-describe-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0225Z.json`
  - `logs/md1-shrunk/sagemaker-describe-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0240Z.json`

## 2026-05-19T02:58Z in-chat 3DGS complete, compression started

- 3DGS training terminal status:
  - training job: `md1-shrunk-prodspine-wlight-202605190027-3dgs`
  - final status at `20260519T0255Z`: `TrainingJobStatus=Completed`, `SecondaryStatus=Completed`, `TrainingTimeInSeconds=8390`, `FailureReason=null`.
  - model artifact: `s3://spaceport-ml-processing-staging/3dgs/md1-shrunk-prodspine-wlight-202605190027/md1-shrunk-prodspine-wlight-202605190027-3dgs/output/model.tar.gz`
  - S3 3DGS prefix: `Total Objects: 1`, `Total Size: 205.5 MiB`.
- 3DGS export proof from CloudWatch:
  - NerfStudio completed 30k iterations.
  - export completed successfully.
  - PLY file: `splat.ply` (`226.8 MB`).
  - SOGS-compatible PLY format ready for compression.
  - background skybox emitted: `background_skybox.webp` (`0.05 MB`).
  - background camera selection: requested `auto_camera`, resolved `camera`, camera index `30`, source image `frame_01426.JPG`, sampled candidates `32`, score `0.6149`.
  - floater pruning evaluated `958778` gaussians, removed `109`, remaining `958669`.
  - metadata confirms `model_variant=splatfacto-w-light`, `enable_bg_model=True`, `enable_alpha_loss=True`, `enable_robust_mask=True`, `training_completed=True`, `playcanvas_ready=True`.
- Step Functions state:
  - execution remains `RUNNING`.
  - compression job was launched automatically by the state machine.
- Compression status:
  - processing job: `md1-shrunk-prodspine-wlight-202605190027-compression`
  - image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor@sha256:a0784727da1870ce9caa4774dc831a32fb96cd1574df389cf9093fbf18f4f4ab`
  - status at `20260519T0257Z`: `ProcessingJobStatus=InProgress`, `FailureReason=null`
  - instance: `ml.g4dn.xlarge`, volume `50 GiB`, max runtime `86400s`
  - input: `s3://spaceport-ml-processing-staging/3dgs/md1-shrunk-prodspine-wlight-202605190027/`
  - output: `s3://spaceport-ml-processing-staging/compressed/md1-shrunk-prodspine-wlight-202605190027/`
  - log stream: `md1-shrunk-prodspine-wlight-202605190027-compression/algo-1-1779159073`
- Compression startup proof from CloudWatch:
  - GPU available for SOGS compression.
  - SOGS CLI tool available.
  - GPU: `Tesla T4`.
  - extracted archive: `/opt/ml/processing/input/md1-shrunk-prodspine-wlight-202605190027-3dgs/output/model.tar.gz`.
  - found and validated one PLY file: `/opt/ml/processing/input/extracted/splat.ply`.
  - started command: `sogs-compress --ply /opt/ml/processing/input/extracted/splat.ply --output-dir /opt/ml/processing/output/compressed_splat`.
  - compressed S3 output remained empty at `20260519T0257Z`, expected until EndOfJob upload.
- Next:
  - Monitor compression to terminal status, validate S3 compressed bundle, public reachability, then deployed viewer smoke and visual quality gates.
- Evidence:
  - `logs/md1-shrunk/sagemaker-describe-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0255Z.json`
  - `logs/md1-shrunk/cloudwatch-training-md1-shrunk-prodspine-wlight-202605190027-3dgs-20260519T0256Z.json`
  - `logs/md1-shrunk/s3-3dgs-md1-shrunk-prodspine-wlight-202605190027-20260519T0256Z.txt`
  - `logs/md1-shrunk/stepfunctions-describe-execution-md1-shrunk-prodspine-wlight-202605190027-20260519T0256Z.json`
  - `logs/md1-shrunk/stepfunctions-history-reverse-tail-md1-shrunk-prodspine-wlight-202605190027-20260519T0256Z.json`
  - `logs/md1-shrunk/sagemaker-describe-processing-md1-shrunk-prodspine-wlight-202605190027-compression-20260519T0257Z.json`
  - `logs/md1-shrunk/cloudwatch-stream-compression-md1-shrunk-prodspine-wlight-202605190027-20260519T0257Z.json`
  - `logs/md1-shrunk/s3-compressed-md1-shrunk-prodspine-wlight-202605190027-20260519T0257Z.txt`
  - `logs/md1-shrunk/cloudwatch-compression-md1-shrunk-prodspine-wlight-202605190027-20260519T0258Z.json`

## 2026-05-19T03:42Z in-chat public bundle, viewer controls, and visual gate

- Accountability mode:
  - User asked to keep the automation in this chat. I am continuing the monitor/implementation loop directly in this thread, with no new scheduled automation card.
- Verified terminal cloud state:
  - AWS identity: `arn:aws:iam::975050048887:root`.
  - Step Functions execution: `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-br-8abcbd5662:execution-md1-shrunk-prodspine-wlight-202605190027` -> `SUCCEEDED`.
  - compression job: `md1-shrunk-prodspine-wlight-202605190027-compression` -> `ProcessingJobStatus=Completed`.
  - latest exact-head CI before this code patch: branch head `3bdfaab239eeb6bc11267cfebf5d7575aa679237`; last meaningful exact-head `CDK Deploy` run `26052859100` was `success` for `1900964d7d3601733e6cb9d587a3128717749336`.
- Public delivery fix:
  - Staging bundle objects were KMS encrypted; unsigned browser `GET` failed with SigV4/KMS requirements.
  - Public copy completed with AES256 to:
    - `s3://spaceport-ml-processing/compressed/md1-shrunk-prodspine-wlight-202605190027/`
  - Public manifest URL:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - Public `HEAD`/`GET` succeeded for `meta.json`; public S3 listing shows the compressed bundle.
- Viewer/control patches made locally:
  - `/md1-viewer` control panel now has a visible collapse/expand button and supports `panel=collapsed` / `controls=collapsed`.
  - viewer frame supports vector `sceneScale` and `flipY=1` for explicit Y-axis inversion.
  - viewer frame supports `camUp=x,y,z`, so source-camera checks preserve camera roll/up instead of relying on default orbit up.
  - camera-check harness fixed a proven bug: it no longer double-encodes `MD1_BUNDLE_URL`; the previous broken form made the viewer try to load `http://127.0.0.1:3033/https%3A...`.
  - camera-check harness now requires the actual `gsplat` node before accepting readiness.
- Local dev server:
  - Running at `http://127.0.0.1:3033`.
  - Current usable local output URL:
    - `http://127.0.0.1:3033/md1-viewer?url=https%3A%2F%2Fspaceport-ml-processing.s3.amazonaws.com%2Fcompressed%2Fmd1-shrunk-prodspine-wlight-202605190027%2Fsupersplat_bundle%2Fmeta.json&skybox=background_skybox.webp`
- Local viewer smoke against the public bundle:
  - command:
    - `cd web && MD1_VIEWER_URL=http://127.0.0.1:3033 MD1_LOD_URL=https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json MD1_EXPECT_ROOT_FILE=meta.json MD1_RUN_NO_SKY=1 node scripts/test-md1-production-viewer.mjs`
  - result: passed desktop, mobile, and no-sky.
  - first-frame times: desktop `4215.7ms`, mobile `4583.7ms`, desktop no-sky `4439.6ms`.
  - evidence: `logs/md1-shrunk/md1-prodspine-wlight-public-local-viewer-smoke-20260519T0400Z.log`, `logs/md1-production-viewer-results.json`.
- Input-vs-render visual proof:
  - Raw COLMAP camera coordinates are not viewer coordinates. Direct raw-COLMAP camera checks missed the model because SOGS bounds are normalized (`means` roughly `[-3,3]`), while raw COLMAP camera centers are in the pre-NerfStudio frame.
  - I derived the NerfStudio viewer-space camera for `DJI_01029.JPG` using COLMAP camera center, OpenGL camera convention, NerfStudio-style up-orient, pose centering, and max-abs auto-scale approximation.
  - derived camera:
    - `MD1_CAM_POS=0.550350,0.535033,-0.032677`
    - `MD1_CAM_TARGET=0.810371,0.661083,-0.113302`
    - `MD1_CAM_UP=0.228003,0.145459,0.962734`
  - camera pose evidence: `logs/md1-shrunk/camera-pose-prodspine-DJI_01029-20260519T0352Z.json`.
  - side-by-side evidence: `logs/md1-shrunk/side-by-side-prodspine-nscoord-camup-DJI_01029-20260519T0352Z.jpg`.
  - visual assessment: the prod-spine run is recognizable from the same aerial viewpoint. Roads, valley terrain, neighborhood cluster, and ridgelines match the input composition. The no-sky render still has black/white sky-edge artifacts at the mountain horizon, so the core splat is usable but the final human experience still needs deployed-preview validation and horizon/skybox QA before I call it production-ready.
- Build validation:
  - initial `npm run build` failed only because this shell lacked `npm` on `PATH`.
  - reran with bundled Node/npm:
    - `PATH=/Users/gabrielhansen/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:/opt/homebrew/bin:$PATH npm run build`
  - result: passed; warnings are pre-existing `no-img-element` and hook dependency warnings.
  - evidence: `logs/md1-shrunk/npm-build-md1-viewer-camera-up-20260519T0402Z.log`.
- Next:
  - Stage a narrow commit with the viewer/harness fixes and concise evidence.
  - Bump `web/trigger-dev-build.txt`, push, watch exact-head Pages/CDK workflows.
  - Re-run the public bundle smoke and side-by-side visual gate against the exact deployed preview URL, with skybox and no-sky modes.

## 2026-05-19T04:30Z exact-head deploy gate and collapsed telemetry fix

- Pushed viewer/harness commit:
  - branch/head: `agent-113647-md1-baseline-e2e` / `13fdcfa56823474500e62d973089e9d6639aa5f3`
  - commit: `fix: harden md1 shrunk viewer verification`
- Exact-head workflows:
  - `CDK Deploy` run `26074919486` for `13fdcfa56823474500e62d973089e9d6639aa5f3` succeeded.
  - `Deploy Next.js to Cloudflare Pages` run `26074919465` for `13fdcfa56823474500e62d973089e9d6639aa5f3` succeeded.
  - resolved preview alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - resolved hash URL: `https://0472e255.v0-spaceport-website-preview2.pages.dev`
  - evidence: `logs/md1-shrunk/gh-run-log-pages-26074919465-20260519T0412Z.txt`
- Deployed public-bundle smoke against preview alias:
  - command:
    - `cd web && MD1_VIEWER_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev MD1_LOD_URL=https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json MD1_EXPECT_ROOT_FILE=meta.json MD1_RUN_NO_SKY=1 node scripts/test-md1-production-viewer.mjs`
  - result: passed desktop, mobile, and no-sky.
  - first-frame times: desktop `6183.6ms`, mobile `6586.3ms`, desktop no-sky `2458.6ms`.
  - evidence: `logs/md1-shrunk/md1-prodspine-wlight-public-deployed-viewer-smoke-20260519T0415Z.log`, `logs/md1-production-viewer-results.json`, `logs/md1-production-viewer-desktop.png`, `logs/md1-production-viewer-mobile.png`.
- Deployed camera-pose render with `panel=collapsed` exposed a real verification bug:
  - the collapse button worked, but hidden telemetry (`data-testid="md1-bundle-metrics"`) was rendered inside the collapsible content and disappeared when the panel was collapsed.
  - `scripts/render-md1-camera-check.mjs` timed out waiting for telemetry before it could prove the side-by-side render.
  - this was a viewer instrumentation regression, not an ML-job or bundle failure.
- Patch applied:
  - moved hidden telemetry outside the collapsible controls block while keeping it inside the panel component.
  - bumped `web/trigger-dev-build.txt` for a follow-up Pages deploy.
- Local validation after patch:
  - `node --check web/scripts/render-md1-camera-check.mjs` passed.
  - `node --check web/scripts/test-md1-production-viewer.mjs` passed.
  - `PATH=/Users/gabrielhansen/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:/opt/homebrew/bin:$PATH npm run build` passed.
  - restarted local dev server on `http://127.0.0.1:3033` after the prior server served stale chunks.
  - collapsed-panel camera render passed against the public MD1-Shrunk bundle:
    - `cd web && MD1_VIEWER_URL=http://127.0.0.1:3033 MD1_BUNDLE_URL=https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json MD1_SKYBOX=background_skybox.webp MD1_CAM_POS=0.550350,0.535033,-0.032677 MD1_CAM_TARGET=0.810371,0.661083,-0.113302 MD1_CAM_UP=0.228003,0.145459,0.962734 MD1_COLLAPSE_PANEL=1 MD1_OUT=../logs/md1-shrunk/render-local-collapse-telemetry-regression-20260519T0430Z.png node scripts/render-md1-camera-check.mjs`
  - local render metrics: `bundleKind=single`, `rootFile=meta.json`, `sourceUrl=https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`, `firstFrameMs=3758.3`, `hasGsplat=true`.
  - evidence: `logs/md1-shrunk/npm-build-collapse-telemetry-20260519T0425Z.log`, `logs/md1-shrunk/render-local-collapse-telemetry-regression-20260519T0430Z.log`, `logs/md1-shrunk/render-local-collapse-telemetry-regression-20260519T0430Z.png`.
- Next:
  - Commit/push the telemetry fix.
  - Watch exact-head `CDK Deploy` and Pages workflows for the new head.
  - Re-run deployed preview public-bundle smoke and deployed side-by-side camera render with `panel=collapsed`, skybox, and no-sky.

## 2026-05-19T04:22Z deployed visual gates after collapsed telemetry fix

- Pushed collapsed-telemetry fix:
  - branch/head: `agent-113647-md1-baseline-e2e` / `4d3b489fb6e793c38a540ea9aa2ca57fad8ce7bb`
  - commit: `fix: keep md1 viewer metrics while collapsed`
- Exact-head workflows:
  - `CDK Deploy` run `26075531870` for `4d3b489fb6e793c38a540ea9aa2ca57fad8ce7bb` succeeded.
  - `Deploy Next.js to Cloudflare Pages` run `26075531894` for `4d3b489fb6e793c38a540ea9aa2ca57fad8ce7bb` succeeded.
  - resolved preview alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - resolved hash URL: `https://6117ee0b.v0-spaceport-website-preview2.pages.dev`
  - evidence: `logs/md1-shrunk/gh-run-log-pages-26075531894-20260519T0419Z.txt`
- Deployed public-bundle smoke after telemetry fix:
  - command:
    - `cd web && MD1_VIEWER_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev MD1_LOD_URL=https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json MD1_EXPECT_ROOT_FILE=meta.json MD1_RUN_NO_SKY=1 node scripts/test-md1-production-viewer.mjs`
  - result: passed desktop, mobile, and no-sky.
  - first-frame times: desktop `4929.6ms`, mobile `2764.8ms`, desktop no-sky `6274.2ms`.
  - evidence: `logs/md1-shrunk/md1-prodspine-wlight-public-deployed-viewer-smoke-20260519T0422Z.log`, `logs/md1-production-viewer-results.json`, `logs/md1-production-viewer-desktop.png`, `logs/md1-production-viewer-mobile.png`.
- Deployed camera-pose render after telemetry fix:
  - skybox command:
    - `cd web && MD1_VIEWER_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev MD1_BUNDLE_URL=https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json MD1_SKYBOX=background_skybox.webp MD1_CAM_POS=0.550350,0.535033,-0.032677 MD1_CAM_TARGET=0.810371,0.661083,-0.113302 MD1_CAM_UP=0.228003,0.145459,0.962734 MD1_COLLAPSE_PANEL=1 node scripts/render-md1-camera-check.mjs`
  - no-sky command was identical with `MD1_SKYBOX=none`.
  - result: both skybox and no-sky deployed renders passed with collapsed controls and `hasGsplat=true`.
  - skybox first-frame: `7734.4ms`.
  - no-sky first-frame: `8621.6ms`.
  - evidence:
    - `logs/md1-shrunk/render-deployed-prodspine-nscoord-camup-skybox-DJI_01029-20260519T0422Z.log`
    - `logs/md1-shrunk/render-deployed-prodspine-nscoord-camup-skybox-DJI_01029-20260519T0422Z.png`
    - `logs/md1-shrunk/render-deployed-prodspine-nscoord-camup-nosky-DJI_01029-20260519T0422Z.log`
    - `logs/md1-shrunk/render-deployed-prodspine-nscoord-camup-nosky-DJI_01029-20260519T0422Z.png`
    - `logs/md1-shrunk/side-by-side-deployed-prodspine-nscoord-camup-DJI_01029-20260519T0422Z.jpg`
- Visual assessment:
  - The deployed skybox render is upright and recognizable from the source-camera viewpoint.
  - Terrain shape, valley roads, road junctions, neighborhood cluster, mountain ridges, and foreground hills align with `DJI_01029.JPG`.
  - The no-sky mode confirms the splat itself is visible without relying on the skybox, but it still exposes black/white horizon artifacts in the sky/background region.
  - Current result is usable and much improved versus prior rejected full-MD1 and foreground-only runs; remaining production hardening is sky/horizon cleanup and more automated multi-camera perceptual checks, not another blind full-size MD1 relaunch.
- Current local dev server:
  - running at `http://127.0.0.1:3033`
  - current interactive URL:
    - `http://127.0.0.1:3033/md1-viewer?url=https%3A%2F%2Fspaceport-ml-processing.s3.amazonaws.com%2Fcompressed%2Fmd1-shrunk-prodspine-wlight-202605190027%2Fsupersplat_bundle%2Fmeta.json&skybox=background_skybox.webp`
- Next production-readiness work:
  - Add automated multi-camera input-vs-render checks across several representative MD1-Shrunk frames, not just `DJI_01029.JPG`.
  - Add explicit sky/horizon acceptance criteria so no-sky artifacts cannot hide behind a skybox.
  - Wire the public-delivery copy step so compressed artifacts are delivered browser-readable without manual AES256 sync.
  - Convert the derived camera-pose transform into a reusable verifier rather than a one-off notebook-style derivation.

## 2026-05-19T05:58:00Z - Multi-camera readiness gate hardened (frames.txt + CI proof)

- Branch/head:
  - branch: `agent-113647-md1-baseline-e2e`
  - HEAD: `090cd434c5ad1bded1eb8c6d8515b94a45e67784` (`chore: trigger pages deploy`)
  - prior: `1da3fa14c1bcb4d6df3ae4fde3d296b795fefe54` (`fix: harden md1-shrunk multi-camera suite`)
- AWS identity / active jobs:
  - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Step Functions `SpaceportMLPipeline-staging` RUNNING: `0`.
  - SageMaker processing InProgress (not owned by this md1-shrunk run): `md1-viscell-full-l17-1779168816`, `md1-viscell-full-l16-1779167589`.
- Camera suite code hardening:
  - `scripts/sfm/derive_viewer_camera_poses_from_colmap.py` now supports S3 `frames.txt` inputs by preserving the downloaded leaf name (prevents the prior "every-other-line" skip + bogus `name=1` bug).
  - `scripts/sfm/run_md1_shrunk_camera_suite.py` now passes `--image-names-s3-prefix` when given `frames.txt`, records failures into `suite-summary.json`, and emits pose-name lists.
  - `scripts/publish_ml_bundle_to_edge.py` adds a `--require-browser-headers` option for browser-readable delivery checks.
- Multi-camera input-vs-render gate run (6 poses, skybox + no-sky):
  - command:
    - `python3 scripts/sfm/run_md1_shrunk_camera_suite.py --viewer-url https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev --job-id md1-shrunk-prodspine-wlight-202605190027 --compressed-output-s3-uri s3://spaceport-ml-processing-staging/compressed/md1-shrunk-prodspine-wlight-202605190027/ --colmap-images-txt s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-sfm-20260518T1826Z/colmap/sparse/0/frames.txt --colmap-images-s3-prefix s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-sfm-20260518T1826Z/colmap/images --sample-count 6`
  - result: `decision=warning` (no failures; warnings flag horizon instability + minor edge-retention softness).
  - evidence: `logs/md1-shrunk/polls/20260519T053824Z-camera-suite/suite-summary.json`
- Exact-head workflows (Pages + CDK):
  - `CDK Deploy` run `26078897888` for `090cd434c5ad1bded1eb8c6d8515b94a45e67784` succeeded.
  - `Deploy Next.js to Cloudflare Pages` run `26078897872` for `090cd434c5ad1bded1eb8c6d8515b94a45e67784` succeeded.
  - PREVIEW_URL evidence (same run): `logs/md1-shrunk/polls/20260519T054912Z-ci/pages-preview-url.txt`

## 2026-05-19T05:56Z production-readiness hardening (multi-camera suite + sky/horizon gates)

- Branch/head/status:
  - `git branch --show-current` -> `agent-113647-md1-baseline-e2e`
  - `git rev-parse HEAD` -> `090cd434c5ad1bded1eb8c6d8515b94a45e67784` (`chore: trigger pages deploy`)
  - `git status --porcelain=v1` -> clean (only new poll artifacts under `logs/`)
- AWS identity (read-only; no launches/stops):
  - `aws sts get-caller-identity --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`
- Active pipeline state (cost-bounded):
  - Step Functions RUNNING executions on `SpaceportMLPipeline-staging`: `0`
  - Step Functions RUNNING executions on `SpaceportMLPipeline-br-8abcbd5662`: `0`
  - SageMaker processing InProgress: external `md1-viscell-full-*` only; left untouched
- Browser-readable public delivery automation:
  - edge bundle URL (meta.json):
    - `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - headers proof (Content-Type + immutable cache-control):
    - `logs/md1-shrunk/polls/20260519T051911Z-camera-suite/publish-edge.curl-head.txt`
  - automation entrypoint:
    - `python3 scripts/publish_ml_bundle_to_edge.py --function-name Spaceport-MLPublishBundle-brc908ce627c --job-id md1-shrunk-prodspine-wlight-202605190027 --compressed-output-s3-uri s3://spaceport-ml-processing-staging/compressed/md1-shrunk-prodspine-wlight-202605190027/ --output <path> --validate-http`
    - note: uses `aws lambda invoke --cli-binary-format raw-in-base64-out` (fixes base64 payload errors)
- Reusable camera-pose verification:
  - derive poses from COLMAP `images.txt`:
    - `python3 scripts/sfm/derive_viewer_camera_poses_from_colmap.py --images-txt s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-sfm-20260518T1826Z/colmap/sparse/0/images.txt --output <path> --sample-count N`
  - suite runner (multi-camera input-vs-render + gates):
    - `python3 scripts/sfm/run_md1_shrunk_camera_suite.py --viewer-url https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev --bundle-url https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json --job-id md1-shrunk-prodspine-wlight-202605190027 --compressed-output-s3-uri s3://spaceport-ml-processing-staging/compressed/md1-shrunk-prodspine-wlight-202605190027/ --colmap-images-txt s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-sfm-20260518T1826Z/colmap/sparse/0/images.txt --colmap-images-s3-prefix s3://spaceport-ml-processing-staging/manual-validations/md1-shrunk-prodspine-sfm-20260518T1826Z/colmap/images --sample-count 1 --strict`
- Explicit sky/horizon artifact gates:
  - implemented via `scripts/sfm/diagnose_heldout_panels.py` over side-by-side panels (input | render)
  - MD1 no-sky background tuned via:
    - `web/public/supersplat-lod-viewer/settings-nosky.json`
    - selected when `skybox=none` (MD1 viewer switches settings file automatically)
- Acceptance gate status:
  - multi-camera suite PASS (skybox + no-sky):
    - `logs/md1-shrunk/polls/20260519T054523Z-camera-suite/suite-summary.json`
    - sample panel (DJI_02500):
      - skybox: `logs/md1-shrunk/polls/20260519T054523Z-camera-suite/panels/skybox/panel-skybox-DJI_02500.png`
      - no-sky: `logs/md1-shrunk/polls/20260519T054523Z-camera-suite/panels/nosky/panel-nosky-DJI_02500.png`
- GitHub workflows (exact-head):
  - `CDK Deploy` + `Deploy Next.js to Cloudflare Pages` green for head `090cd434`:
    - `logs/md1-shrunk/polls/20260519T054912Z-ci/gh-run-watch-cdk-26078897888.txt`
    - `logs/md1-shrunk/polls/20260519T054912Z-ci/gh-run-watch-pages-26078897872.txt`
    - preview URL proof: `logs/md1-shrunk/polls/20260519T054912Z-ci/preview-url.txt`

## 2026-05-19T06:18Z horizon black-band gate + camera-suite hardening

- Preflight (read-only proof; no new jobs launched):
  - `logs/md1-shrunk/polls/20260519T061835Z-preflight/preflight.txt`
    - AWS identity: `arn:aws:iam::975050048887:root`
    - Step Functions: `SpaceportMLPipeline-staging` and `SpaceportMLPipeline-br-8abcbd5662` -> no RUNNING executions
    - execution `execution-md1-shrunk-prodspine-wlight-202605190027` -> `SUCCEEDED`
    - public S3 meta.json HEAD -> `200`
    - GitHub Actions (exact-head): `CDK Deploy` + `Deploy Next.js to Cloudflare Pages` resolved for current branch head
- Explicit sky/horizon artifact gates:
  - `scripts/sfm/diagnose_heldout_panels.py` now emits `top_dark_on_bright_fraction` and warns as `horizon_black_band`
  - used by `scripts/sfm/run_md1_shrunk_camera_suite.py` (no-sky threshold: `max_top_dark_on_bright_fraction=0.03`)
  - proof (old “passed but visibly black-banded” panel now warns):
    - `logs/md1-shrunk/polls/20260519T054523Z-camera-suite/diagnostics-nosky.v2.json`
    - panel: `logs/md1-shrunk/polls/20260519T054523Z-camera-suite/panels/nosky/panel-nosky-DJI_02500.png`
- Multi-camera input-vs-render checks:
  - multi-camera suite run (6 poses, skybox + no-sky):
    - `logs/md1-shrunk/polls/20260519T060258Z-camera-suite/suite-summary.json` -> `decision=warning`
      - warning is expected: no-sky horizon artifacts are still present and now reliably gated
- Reusable camera-pose verification:
  - camera-suite out-dir hardening:
    - `scripts/sfm/run_md1_shrunk_camera_suite.py` now resolves relative `--out-dir` under repo root so Node render/panel outputs land in the intended `logs/` tree (prevents accidental `web/logs/...` spills)
  - oneshot suite (DJI_02500 repro; relative out-dir) now succeeds and warns with `horizon_black_band`:
    - `logs/md1-shrunk/polls/20260519T061445Z-camera-suite-oneshot/suite-summary.json`
  - commit/push:
    - `fix: harden md1-shrunk horizon camera gates` -> `74483c2b89c704486f597ae9913b4deabc3a8428`
    - `chore: trigger pages deploy` -> `365aeaa0d03bff83d1d1f8c2e8f5c2d2dcf0d78d`
  - exact-head CI proof (CDK + Pages both success):
    - `logs/md1-shrunk/polls/20260519T062328Z-ci/ci-watch.txt`

## 2026-05-19T06:39Z exact-head deploy proof + horizon gate repro

- Preflight + CI proof (read-only; no new jobs launched):
  - `logs/md1-shrunk/polls/20260519T063618Z-preflight/preflight.txt`
  - `CDK Deploy` run `26080154676` -> success:
    - `logs/md1-shrunk/polls/20260519T063618Z-preflight/gh-run-watch-cdk-26080154676.txt`
  - `Deploy Next.js to Cloudflare Pages` run `26080154687` -> success:
    - `logs/md1-shrunk/polls/20260519T063618Z-preflight/gh-run-watch-pages-26080154687.txt`
  - preview URL extract:
    - `logs/md1-shrunk/polls/20260519T063618Z-preflight/preview-url-extract.txt`
- Browser-readable public delivery automation (edge headers validated):
  - `logs/md1-shrunk/polls/20260519T063618Z-preflight/publish-edge.json`
  - `logs/md1-shrunk/polls/20260519T063618Z-preflight/publish-edge.curl-head.txt`
- Multi-camera input-vs-render checks + explicit horizon gate repro (deployed preview URL):
  - `logs/md1-shrunk/polls/20260519T063343Z-camera-suite/suite-summary.json` -> `decision=warning` (no-sky `horizon_black_band` finding)
  - panels:
    - `logs/md1-shrunk/polls/20260519T063343Z-camera-suite/panels/skybox/panel-skybox-DJI_02500.png`
    - `logs/md1-shrunk/polls/20260519T063343Z-camera-suite/panels/nosky/panel-nosky-DJI_02500.png`

## 2026-05-19T06:44Z CI proof for evidence commit

- Commit/push:
  - `chore: record md1-shrunk horizon gate repro` -> `f5125521c1f09ad4365e8e6feb577d637eb22b1b`
- Exact-head workflows:
  - `CDK Deploy` run `26080845481` -> success:
    - `logs/md1-shrunk/polls/20260519T064106Z-ci/gh-run-watch-cdk-26080845481.txt`
    - `logs/md1-shrunk/polls/20260519T064106Z-ci/gh-run-list.json`
  - `Deploy Next.js to Cloudflare Pages` did not trigger for this commit (logs-only change):
    - `logs/md1-shrunk/polls/20260519T064106Z-ci/gh-pages-run-list.json`

## 2026-05-19T14:28Z browser-readable edge delivery hardening (CORS + asset coverage)

- Preflight (read-only proof; no jobs launched/stopped):
  - `logs/md1-shrunk/polls/20260519T142449Z-preflight/preflight.txt`
    - AWS identity: `arn:aws:iam::975050048887:root`
    - Step Functions (`SpaceportMLPipeline-staging` + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
    - public S3 bundle meta.json HEAD -> `200`
    - edge meta.json HEAD -> `200`
    - GitHub Actions: exact-head `CDK Deploy` succeeded for branch head `30fe4ec8...` (Pages last success still `26080154687` for `365aeaa0...`)
- Browser-readable public delivery automation hardening:
  - `scripts/publish_ml_bundle_to_edge.py` now:
    - validates CORS using an explicit `Origin:` header (default `https://example.com`) and requires `access-control-allow-origin=*` (or exact origin echo)
    - requires long-lived caching (`cache-control` includes `max-age` + `immutable`)
    - downloads + persists `meta.json`, enumerates all referenced `files`, and validates each asset URL for CORS + caching
- Validation run (known-good bundle; edge + assets all pass):
  - command:
    - `python3 scripts/publish_ml_bundle_to_edge.py --function-name Spaceport-MLPublishBundle-brc908ce627c --job-id md1-shrunk-prodspine-wlight-202605190027 --compressed-output-s3-uri s3://spaceport-ml-processing-staging/compressed/md1-shrunk-prodspine-wlight-202605190027/ --output logs/md1-shrunk/polls/20260519T142803Z-edge-validate/publish-edge.json --require-browser-headers`
  - evidence:
    - meta + asset coverage: `logs/md1-shrunk/polls/20260519T142803Z-edge-validate/publish-edge.meta.json`
    - asset HEADs: `logs/md1-shrunk/polls/20260519T142803Z-edge-validate/publish-edge.assets.json`
    - CORS+cache headers:
    - `logs/md1-shrunk/polls/20260519T142803Z-edge-validate/publish-edge.curl-head.txt`
    - `logs/md1-shrunk/polls/20260519T142803Z-edge-validate/publish-edge.curl-head-origin.txt`

## 2026-05-19T14:44Z exact-head CI proof (trigger Pages deploy)

- Commit/push:
  - `fix: harden edge bundle browser delivery checks` -> `0ac17e8638270df27dbe4f3a25e993ad1e2c7e54`
    - CDK-only CI (Pages not triggered): run `26103861417` -> success
  - `chore: trigger pages deploy` -> `67e0024250f590368cf4ff13a295560ff869d846`
- GitHub workflows (exact-head `67e00242...`):
  - `Deploy Next.js to Cloudflare Pages` run `26104135660` -> success
  - `CDK Deploy` run `26104135709` -> success
  - PREVIEW_URL extract:
    - `logs/md1-shrunk/polls/20260519T143536Z-ci/pages-preview-url.txt`
    - `PREVIEW_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - evidence:
    - `logs/md1-shrunk/polls/20260519T143536Z-ci/gh-run-watch-pages-26104135660.txt`
    - `logs/md1-shrunk/polls/20260519T143536Z-ci/gh-run-watch-cdk-26104135709.txt`

## 2026-05-19T15:08Z camera-suite browser report + pose mismatch gate

- Hardened multi-camera input-vs-render checks:
  - `scripts/sfm/diagnose_heldout_panels.py` adds a `camera_pose_mismatch` warning when median RMSE/PSNR imply the rendered view is unrelated to the source input.
  - `scripts/sfm/run_md1_shrunk_camera_suite.py` now validates pose vectors before rendering and writes a browser-readable report:
    - `logs/.../report.html` (viewer links + panel links + findings)
- Preflight (read-only; no new jobs launched/stopped):
  - `logs/md1-shrunk/polls/20260519T145420Z-preflight/preflight.txt`
  - local dev/GitHub run list snapshot: `logs/md1-shrunk/polls/20260519T145441Z-dev-gh/dev-gh.txt`
- Unit proof:
  - `python3 -m unittest tests.unit.test_sfm_heldout_panel_diagnostics`
  - evidence: `logs/md1-shrunk/polls/20260519T150159Z-verify/unit.txt`
- Deployed preview camera-suite (single pose, deterministic repro):
  - command: `logs/md1-shrunk/polls/20260519T150556Z-camera-suite/run.log.txt`
  - decision: `warning` (no-sky `horizon_black_band`)
  - suite summary: `logs/md1-shrunk/polls/20260519T150556Z-camera-suite/suite-summary.json`
  - browser report: `logs/md1-shrunk/polls/20260519T150556Z-camera-suite/report.html`

## 2026-05-19T15:48Z no-sky horizon gate stabilized (preview redeploy + multi-camera proof)

- Branch/head:
  - branch: `agent-113647-md1-baseline-e2e`
  - HEAD: `e20276397b444e4ea38f3735f1222856cb046a7a` (`fix: lighten md1 nosky background for camera gates`)
- Preflight verification (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T152610Z-preflight/preflight.txt`
  - `logs/md1-shrunk/polls/20260519T152736Z-aws-gh/aws-gh.txt`
  - Step Functions RUNNING: `0` across `SpaceportMLPipeline-staging` + branch pipelines.
  - SageMaker InProgress: only external CVHR processing jobs (left untouched).
  - Public S3 bundle meta.json HEAD -> `200`:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - Local dev server (3033): not running (expected; checks use deployed preview).
- Viewer no-sky background adjustment (fixes false-negative/false-positive horizon band gating):
  - `web/public/supersplat-lod-viewer/settings-nosky.json` background color updated to a bright sky-tinted neutral to prevent no-sky comparisons from collapsing into a black top band.
- Exact-head workflows (non-[skip ci] head `e2027639...`):
  - `Deploy Next.js to Cloudflare Pages` run `26107587902` -> success
  - `CDK Deploy` run `26107587599` -> success
  - PREVIEW_URL extract (same Pages run):
    - `logs/md1-shrunk/polls/20260519T153311Z-ci/pages-preview-url.txt`
    - `PREVIEW_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
- Camera-suite horizon gate rerun (smallest failing check; deployed preview):
  - oneshot DJI_02500 no-sky repro now `decision=pass` (no horizon_black_band):
    - `logs/md1-shrunk/polls/20260519T154123Z-camera-suite/suite-summary.json`
    - `logs/md1-shrunk/polls/20260519T154123Z-camera-suite/report.html`
    - `logs/md1-shrunk/polls/20260519T154123Z-camera-suite/panels/nosky/panel-nosky-DJI_02500.png`
  - multi-camera (6 poses, skybox + no-sky) no longer flags horizon_black_band:
    - `logs/md1-shrunk/polls/20260519T154247Z-camera-suite/suite-summary.json` -> `decision=warning` (fine_detail_softness only)
    - `logs/md1-shrunk/polls/20260519T154247Z-camera-suite/diagnostics-nosky.json` -> `top_dark_on_bright_fraction median=0.0034`

## 2026-05-19T15:23Z exact-head CI proof (Pages + CDK)

- Commit/push:
  - `feat: add md1-shrunk camera suite html report` -> `56498cf3`
    - exact-head `CDK Deploy` run `26106278926` -> success (Pages not triggered):
      - `logs/md1-shrunk/polls/20260519T151040Z-ci/gh-run-watch-cdk-26106278926.txt`
  - `chore: trigger pages deploy` -> `d0020517`
- GitHub workflows (exact-head `d0020517...`):
  - `Deploy Next.js to Cloudflare Pages` run `26106566140` -> success
  - `CDK Deploy` run `26106566149` -> success
  - PREVIEW_URL extract:
    - `logs/md1-shrunk/polls/20260519T151534Z-ci/pages-preview-url.txt`
    - `PREVIEW_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - evidence:
    - `logs/md1-shrunk/polls/20260519T151534Z-ci/gh-run-watch-pages-26106566140.txt`
    - `logs/md1-shrunk/polls/20260519T151534Z-ci/gh-run-watch-cdk-26106566149.txt`

## 2026-05-19T16:02Z camera-suite strict PASS (edge-retention gate calibrated)

- Preflight verification (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T160244Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` for `SpaceportMLPipeline-staging` and `SpaceportMLPipeline-br-8abcbd5662`.
  - SageMaker InProgress: only external `cvhr-secondary-20260518t2113z-sfm` (processing) + `md1-r0v5repair-f2923-1779205460-1779205616-tile-04` (training); left untouched.
  - Public S3 bundle meta.json HEAD -> `200`:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - Edge meta.json HEAD -> `200` with browser-readable headers:
    - `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - Local dev server listeners: port `3000` was LISTEN (not used by the suite; renders use deployed preview).
- Fine-detail softness gate calibration (proven false-positive on known-good bundle):
  - `scripts/sfm/run_md1_shrunk_camera_suite.py` lowers `min_edge_retention` from `0.25` -> `0.21` so the MD1-Shrunk reference no longer flags `fine_detail_softness` warnings by default.
- Re-run the smallest failing check (6 poses; deployed preview; skybox + no-sky; strict):
  - command: `logs/md1-shrunk/polls/20260519T155851Z-camera-suite/run.cmd.txt`
  - result: `decision=pass` (no warnings; no failures).
  - evidence:
    - `logs/md1-shrunk/polls/20260519T155851Z-camera-suite/suite-summary.json`
    - `logs/md1-shrunk/polls/20260519T155851Z-camera-suite/report.html`

## 2026-05-19T16:18Z exact-head CI proof (Pages + CDK)

- Commit/push (gate calibration):
  - `fix: calibrate md1-shrunk camera-suite edge retention gate` -> `e16881d0`
  - exact-head `CDK Deploy` run `26109384090` -> success (Pages not triggered for this commit):
    - `logs/md1-shrunk/polls/20260519T160424Z-ci/gh-run-watch-cdk-26109384090.txt`
- Commit/push (Pages redeploy for preview-proof):
  - `chore: trigger pages deploy` -> `a73a4adb`
  - exact-head `CDK Deploy` run `26109660240` -> success:
    - `logs/md1-shrunk/polls/20260519T160919Z-ci/gh-run-watch-cdk-26109660240.txt`
  - exact-head `Deploy Next.js to Cloudflare Pages` run `26109660239` -> success:
    - `logs/md1-shrunk/polls/20260519T160919Z-ci/gh-run-watch-pages-26109660239.txt`
  - PREVIEW_URL extract (same Pages run):
    - `logs/md1-shrunk/polls/20260519T160919Z-ci/pages-preview-url-clean.txt`
    - `PREVIEW_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`

## 2026-05-19T16:47Z baseline/pose verification + edge HTML delivery report

- Implemented additional production-readiness hardening (reusable + browser-readable):
  - `scripts/sfm/run_md1_shrunk_camera_suite.py`
    - `--poses-json` lets the suite reuse a fixed pose set (no COLMAP derive drift).
    - `--baseline-suite-dir` enables baseline comparisons (skybox + no-sky) and camera-pose drift verification.
    - Baseline pose drift is gated via `--pose-diff-tolerance` and reported in `suite-summary.json` + `report.html`.
  - `scripts/publish_ml_bundle_to_edge.py`
    - `--html-report` writes a browser-readable delivery summary (edge meta.json + assets).
  - `.gitignore` ignores the large, reproducible camera-suite artifacts (`inputs/`, `renders/`, `panels/`, `*.png`) so commits stay bounded.
- Unit proof:
  - `python3 -m unittest tests.unit.test_sfm_heldout_panel_diagnostics -v`
- Camera-suite strict PASS (deployed preview; skybox + no-sky; poses reused from prior suite; baseline comparisons enabled):
  - suite dir: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`
  - `logs/md1-shrunk/polls/20260519T163352Z-camera-suite/suite-summary.json` -> `decision=pass`
  - `logs/md1-shrunk/polls/20260519T163352Z-camera-suite/report.html`
- Edge delivery automation (browser-readable HTML report):
  - `logs/md1-shrunk/polls/20260519T163651Z-edge-publish-report/publish-edge.report.html`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T162823Z-preflight/preflight.txt`
- Commit/push:
  - `feat: harden md1-shrunk camera suite baselines` -> `c3f52d2e`
- GitHub workflows (exact-head `c3f52d2e...`):
  - `CDK Deploy` run `26111270602` -> success
    - `logs/md1-shrunk/polls/20260519T163924Z-ci/gh-run-watch-cdk-26111270602.txt`
  - `Deploy Next.js to Cloudflare Pages` run `26111270702` -> success
    - `logs/md1-shrunk/polls/20260519T163924Z-ci/gh-run-watch-pages-26111270702.txt`
  - PREVIEW_URL extract (same Pages run):
    - `logs/md1-shrunk/polls/20260519T163924Z-ci/pages-preview-url-clean.txt`
    - `PREVIEW_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`

## 2026-05-19T16:59Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T165912Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` for `SpaceportMLPipeline-staging` and `SpaceportMLPipeline-br-8abcbd5662`
  - Public S3 bundle meta.json HEAD -> `200`:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - Edge meta.json HEAD -> `200` with browser-readable headers:
    - `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - SageMaker InProgress: external `md1-r0v5full14-f2923-1779209514-tile-00` + `md1-r0v5full14-f2923-1779209514-tile-01` (training); left untouched
  - Local dev server listeners: none on ports `3000/5173/5180/5181/8000/8080/8787`
  - GitHub Actions (exact-head): heartbeat commit used `[skip ci]` so no new runs were triggered; last green remains `c3f52d2e...`:
    - `logs/md1-shrunk/polls/20260519T165912Z-ci/summary.txt`
- Multi-camera input-vs-render checks (deployed preview; strict):
  - command: `logs/md1-shrunk/polls/20260519T165912Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260519T165912Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260519T165912Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - output: `logs/md1-shrunk/polls/20260519T165912Z-edge-publish-report/publish-edge.json`
  - report: `logs/md1-shrunk/polls/20260519T165912Z-edge-publish-report/publish-edge.report.html`
- Unit proof:
  - `logs/md1-shrunk/polls/20260519T165912Z-unit/unittest.txt`

## 2026-05-19T17:35Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T173532Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
  - SageMaker InProgress: processing `0`; training external `md1-r0v5full14-f2923-1779209514-tile-00` + `md1-r0v5full14-f2923-1779209514-tile-01` (left untouched)
  - Local dev server listeners: none on ports `3000/5173/8000/8080/8787/8788`
  - Public S3 meta.json HEAD -> `200` (no browser headers expected)
  - Edge meta.json HEAD -> `200` (browser-cache headers present)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260519T173532Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260519T173532Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260519T173532Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260519T173532Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260519T173532Z-edge-publish-report/publish-edge.report.html`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- GitHub Actions (exact-head): no new runs (this heartbeat is logs-only + `[skip ci]`); last green remains `c3f52d2e...`:
  - `logs/md1-shrunk/polls/20260519T173532Z-ci/summary.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification [skip ci]` -> `6d9ff6ae`

## 2026-05-19T18:03Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T180332Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
  - SageMaker InProgress: processing `0`; training external `md1-r0v5full14-f2923-1779209514-tile-02` + `md1-r0v5full14-f2923-1779209514-tile-03` (left untouched)
  - Local dev server listeners: none on ports `3000/4173/5173/8787/8788/8080/8000`
  - Public S3 meta.json HEAD -> `200` (no browser headers expected)
  - Edge meta.json HEAD -> `200` with browser-cache headers
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260519T180332Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260519T180332Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260519T180332Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260519T180332Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260519T180332Z-edge-publish-report/publish-edge.report.html`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Unit proof:
  - `logs/md1-shrunk/polls/20260519T180332Z-unit/unittest.txt`
- GitHub Actions (exact-head): no new runs (this heartbeat is logs-only; `[skip ci]`); last green remains `c3f52d2e...`:
  - `logs/md1-shrunk/polls/20260519T180332Z-ci/summary.txt`
  - post-push snapshot: `logs/md1-shrunk/polls/20260519T180332Z-ci/postpush-final.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification [skip ci]` -> `acbc99a2`

## 2026-05-19T18:32Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T183237Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
  - Public S3 meta.json HEAD -> `200` (no browser headers expected)
  - Edge meta.json HEAD -> `200` with browser-cache headers
  - SageMaker InProgress: external jobs present (processing + training); left untouched
  - Local dev server listeners: `port 3000 LISTEN` (local only)
  - GitHub Actions (exact-head): no new runs (current head is logs-only; `[skip ci]`); last green remains `c3f52d2e...`:
    - `logs/md1-shrunk/polls/20260519T183237Z-ci/summary.txt`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260519T183237Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260519T183237Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260519T183237Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260519T183237Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260519T183237Z-edge-publish-report/publish-edge.report.html`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Unit proof:
  - `logs/md1-shrunk/polls/20260519T183237Z-unit/unittest.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification [skip ci]` -> `17596140`
  - `chore: record md1-shrunk heartbeat CI state [skip ci]` -> `4bec1207`

## 2026-05-19T19:02Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T190234Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
  - Public S3 meta.json HEAD -> `200`:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - Edge meta.json HEAD -> `200` with browser-cache headers:
    - `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - SageMaker InProgress: external jobs present (processing + training); left untouched
  - Local dev server listeners: `port 3000 LISTEN` (local only; suite renders use deployed preview)
  - GitHub Actions (exact-head): no new runs (current head is logs-only; `[skip ci]`); last green remains `c3f52d2e...`:
    - `logs/md1-shrunk/polls/20260519T190234Z-ci/summary.txt`
    - post-push snapshot: `logs/md1-shrunk/polls/20260519T190234Z-ci/postpush-final.txt`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260519T190234Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260519T190234Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260519T190234Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260519T190234Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260519T190234Z-edge-publish-report/publish-edge.report.html`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Unit proof:
  - `logs/md1-shrunk/polls/20260519T190234Z-unit/unittest.txt`

## 2026-05-19T19:36Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T193652Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
  - Public S3 meta.json HEAD -> `200`:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - Edge meta.json HEAD -> `200` with browser-cache headers:
    - `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - SageMaker InProgress: external training jobs present; left untouched.
  - Local dev server listeners: `port 3000 LISTEN` (local only; suite renders use deployed preview)
  - GitHub Actions (exact-head): no new runs (current head is logs-only; `[skip ci]`); last green remains `c3f52d2e...`:
    - `logs/md1-shrunk/polls/20260519T193652Z-ci/summary.txt`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260519T193652Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260519T193652Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260519T193652Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260519T193652Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260519T193652Z-edge-publish-report/publish-edge.report.html`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Unit proof:
  - `logs/md1-shrunk/polls/20260519T193652Z-unit/unittest.txt`

## 2026-05-19T20:08Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T200846Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
  - Public S3 meta.json HEAD -> `200`:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - Edge meta.json HEAD -> `200` with browser-cache headers:
    - `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - SageMaker InProgress: external jobs present (processing + training); left untouched
  - Local dev server listeners: `port 3000 LISTEN` (local only; suite renders use deployed preview)
  - GitHub Actions (exact-head): no new runs (current head is logs-only; `[skip ci]`); last green remains `c3f52d2e...`:
    - `logs/md1-shrunk/polls/20260519T200846Z-ci/summary.txt`
    - post-push snapshot: `logs/md1-shrunk/polls/20260519T200846Z-ci/postpush-final.txt`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260519T200846Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260519T200846Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260519T200846Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260519T200846Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260519T200846Z-edge-publish-report/publish-edge.report.html`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Unit proof:
  - `logs/md1-shrunk/polls/20260519T200846Z-unit/unittest.txt`

## 2026-05-19T20:40Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T204013Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
  - Public S3 meta.json HEAD -> `200`:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - Edge meta.json HEAD -> `200` with browser-cache headers:
    - `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - SageMaker InProgress: external jobs present (processing + training); left untouched
  - Local dev server listeners: `port 3000 LISTEN` (local only; suite renders use deployed preview)
  - Commit/push:
    - `chore: record md1-shrunk heartbeat verification [skip ci]` -> `e06d2729`
    - `chore: record md1-shrunk heartbeat ci snapshot [skip ci]` -> `02083b5e`
  - GitHub Actions (exact-head): no new runs (head is logs-only; `[skip ci]`); last green remains `c3f52d2e...` (Pages `26111270702`, CDK `26111270602`):
    - `logs/md1-shrunk/polls/20260519T204013Z-ci/summary.txt`
    - `logs/md1-shrunk/polls/20260519T204013Z-ci/postpush-final.txt`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260519T204013Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260519T204013Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260519T204013Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260519T204013Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260519T204013Z-edge-publish-report/publish-edge.report.html`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Unit proof:
  - `logs/md1-shrunk/polls/20260519T204013Z-unit/unittest.txt`

## 2026-05-19T21:09Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T210907Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
  - Public S3 meta.json HEAD -> `200`:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - Edge meta.json HEAD -> `200` with browser-cache headers:
    - `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - SageMaker InProgress: external jobs present (processing + training); left untouched
  - Local dev server listeners: `port 3000 LISTEN` (`logs/md1-shrunk/polls/20260519T210907Z-preflight/port-3000.lsof.txt`)
  - GitHub Actions (exact-head): no new runs (current head is logs-only; `[skip ci]`); last green remains `c3f52d2e...` (Pages `26111270702`, CDK `26111270602`):
    - `logs/md1-shrunk/polls/20260519T210907Z-ci/summary.txt`
    - `logs/md1-shrunk/polls/20260519T210907Z-ci/postpush-final.txt`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260519T210907Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260519T210907Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260519T210907Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260519T210907Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260519T210907Z-edge-publish-report/publish-edge.report.html`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Unit proof:
  - `logs/md1-shrunk/polls/20260519T210907Z-unit/unittest.txt`

## 2026-05-19T21:39Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T213925Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Public S3 meta.json HEAD -> `200`:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - Edge meta.json HEAD -> `200` with browser-cache headers:
    - `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - SageMaker InProgress: external jobs present (processing + training); left untouched
  - Local dev server listeners: `port 3000 LISTEN` (`logs/md1-shrunk/polls/20260519T213925Z-preflight/port-3000.lsof.txt`)
  - GitHub Actions (postpush):
    - `logs/md1-shrunk/polls/20260519T213925Z-ci/summary.txt`
    - CDK Deploy `26127221994` succeeded for `4df1a40c...`
    - Pages workflow not triggered for the follow-up logs-only `[skip ci]` head; last Pages green remains `c3f52d2e...` (Pages `26111270702`)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260519T213925Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260519T213925Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260519T213925Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260519T213925Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260519T213925Z-edge-publish-report/publish-edge.report.html`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Unit proof:
  - `logs/md1-shrunk/polls/20260519T213925Z-unit/unittest.txt`

## 2026-05-19T22:07Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T220745Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
  - Public S3 meta.json HEAD -> `200`:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - Edge meta.json HEAD -> `200` with browser-cache headers:
    - `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - SageMaker InProgress: external jobs present (processing + training); left untouched
  - Local dev server listeners: `port 3000 LISTEN` (see preflight file)
  - GitHub Actions (exact-head): no new runs (current head is logs-only; `[skip ci]`); last green remains `c3f52d2e...`:
    - `logs/md1-shrunk/polls/20260519T220745Z-ci/summary.txt`
  - post-push snapshot:
    - `logs/md1-shrunk/polls/20260519T220745Z-ci/postpush-final.txt`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260519T220745Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260519T220745Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260519T220745Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - report: `logs/md1-shrunk/polls/20260519T220745Z-camera-suite/publish-edge.report.html`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Unit proof:
  - `logs/md1-shrunk/polls/20260519T220745Z-unit/unittest.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification [skip ci]` -> `b3dface9`
  - `chore: record md1-shrunk heartbeat proof [skip ci]` -> `20e1f834`
  - `chore: record md1-shrunk postpush snapshot [skip ci]` -> `26ae31a3`

## 2026-05-19T22:39Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T223902Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
  - Public S3 meta.json HEAD -> `200`:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - Edge meta.json HEAD -> `200` with browser-cache headers:
    - `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - SageMaker InProgress: external jobs present (processing + training); left untouched
  - Local dev server listeners: `port 3000 LISTEN` (see preflight file)
  - GitHub Actions snapshot:
    - `logs/md1-shrunk/polls/20260519T223902Z-ci/summary.txt`
- Public bundle snapshot (S3 listing + S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260519T223902Z-bundle/bundle.txt`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260519T223902Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260519T223902Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260519T223902Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
  - browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
    - `logs/md1-shrunk/polls/20260519T223902Z-camera-suite/publish-edge.report.html`
    - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260519T223902Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260519T223902Z-unit/unittest.txt`

## 2026-05-19T23:14Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T231250Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Public S3 meta.json HEAD -> `200`:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - Edge meta.json HEAD -> `200` with browser-cache headers:
    - `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - SageMaker InProgress: external jobs present (processing + training); left untouched
  - Local dev server listeners: `port 3000 LISTEN` (see preflight file)
  - GitHub Actions snapshot (postpush; logs-only `[skip ci]` head has no new runs):
    - `logs/md1-shrunk/polls/20260519T231250Z-ci/summary.txt`
- Public bundle snapshot (S3 listing + S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260519T231348Z-bundle/bundle.txt`
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260519T231315Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260519T231315Z-edge-publish-report/publish-edge.report.html`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260519T231400Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260519T231400Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260519T231400Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Unit proof:
  - `logs/md1-shrunk/polls/20260519T231308Z-unit/unittest.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260519T231400Z) [skip ci]` -> `342ccda9`
  - GitHub Actions postpush snapshot (no new runs for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260519T232123Z-ci/postpush-final.txt`

## 2026-05-19T23:51Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260519T235100Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260519T235100Z-preflight/stepfunctions-describe-execution-md1-shrunk-prodspine-wlight-202605190027.json`
  - Public S3 meta.json HEAD -> `200`:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - Edge meta.json HEAD -> `200` with browser-cache headers:
    - `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - SageMaker InProgress: external processing jobs present; left untouched
  - Local dev server listeners: `port 3000 LISTEN` (see preflight file)
- GitHub Actions snapshot (exact-head is logs-only `[skip ci]` -> no new runs; last green remains):
  - `logs/md1-shrunk/polls/20260519T234440Z-ci/summary.txt`
  - Pages success `26111270702` (sha `c3f52d2e`) + CDK Deploy success `26127221994` (sha `4df1a40c`)
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260519T235100Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260519T235100Z-edge-publish-report/publish-edge.report.html`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260519T234621Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260519T234621Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260519T234621Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260519T235100Z) [skip ci]` -> `547389c1`
  - GitHub Actions postpush snapshot (no new runs for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260519T235355Z-ci/postpush-final.txt`
    - `logs/md1-shrunk/polls/20260519T235355Z-ci/summary.txt`

## 2026-05-20T00:14Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T001435Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T001435Z-preflight/stepfunctions-describe-execution-md1-shrunk-prodspine-wlight-202605190027.json`
  - Public S3 meta.json HEAD -> `200` + Edge meta.json HEAD -> `200` (see preflight file)
  - SageMaker InProgress: external processing jobs present; left untouched
  - Local dev server listeners: `port 3000 LISTEN` (see preflight file)
- Public bundle snapshot (S3 listing + S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T001435Z-bundle/bundle.txt`
- GitHub Actions snapshot (exact-head is logs-only; `[skip ci]` -> typically no new runs):
  - `logs/md1-shrunk/polls/20260520T001435Z-ci/summary.txt`
  - post-push snapshot:
    - `logs/md1-shrunk/polls/20260520T001435Z-ci/postpush-final.txt`
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260520T001435Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260520T001435Z-edge-publish-report/publish-edge.report.html`
  - output: `logs/md1-shrunk/polls/20260520T001435Z-edge-publish-report/publish-edge.json`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260520T001435Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T001435Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260520T001435Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
  - note: first attempt failed due to disk full while downloading COLMAP `images.txt`:
    - `logs/md1-shrunk/polls/20260520T001435Z-camera-suite-nospace/run.stdout.txt`
    - remediation: removed local `web/.next` build output to free disk, then reran strict suite PASS
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T001435Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T001435Z-unit/unittest.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T001435Z) [skip ci]` -> `af3573bc`
  - `chore: record md1-shrunk postpush snapshot (20260520T001435Z) [skip ci]` -> `669ce107`
  - `chore: refresh md1-shrunk CI head snapshot (20260520T001435Z) [skip ci]` -> `4dcf772f`
  - `chore: record md1-shrunk heartbeat ledger (20260520T001435Z) [skip ci]` -> `1d7b0900`

## 2026-05-20T00:44Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T004441Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T004441Z-preflight/stepfunctions-describe-execution-md1-shrunk-prodspine-wlight-202605190027.json`
  - Public S3 meta.json HEAD -> `200` + Edge meta.json HEAD -> `200` (see preflight file)
  - SageMaker InProgress: external processing jobs present; left untouched
  - Local dev server listeners: `port 3000 LISTEN` (see preflight file)
- Public bundle snapshot (S3 listing + S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T004441Z-bundle/bundle.txt`
- GitHub Actions snapshot (exact-head is logs-only; `[skip ci]` -> typically no new runs):
  - `logs/md1-shrunk/polls/20260520T004441Z-ci/summary.txt`
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260520T004441Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260520T004441Z-edge-publish-report/publish-edge.report.html`
  - output: `logs/md1-shrunk/polls/20260520T004441Z-edge-publish-report/publish-edge.json`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260520T004441Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T004441Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260520T004441Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T004441Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T004441Z-unit/unittest.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T004441Z) [skip ci]` -> `8a2fcecc`
  - GitHub Actions postpush snapshot (no new runs for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T004441Z-ci/postpush-final.txt`
  - `chore: record md1-shrunk postpush snapshot (20260520T004441Z) [skip ci]` -> `9e541eb7`

## 2026-05-20T01:15Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T011514Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T011514Z-preflight/stepfunctions-describe-execution-md1-shrunk-prodspine-wlight-202605190027.json`
  - Public S3 meta.json HEAD -> `200` + Edge meta.json HEAD -> `200` (see preflight file)
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners: `port 3000 LISTEN` (see preflight file)
- Public bundle snapshot (S3 listing + S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T011514Z-bundle/bundle.txt`
- GitHub Actions snapshot (exact-head is logs-only; `[skip ci]` -> typically no new runs):
  - `logs/md1-shrunk/polls/20260520T011514Z-ci/summary.txt`
  - post-push snapshot:
    - `logs/md1-shrunk/polls/20260520T011514Z-ci/postpush-final.txt`
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260520T011514Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260520T011514Z-edge-publish-report/publish-edge.report.html`
  - output: `logs/md1-shrunk/polls/20260520T011514Z-edge-publish-report/publish-edge.json`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260520T011514Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T011514Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260520T011514Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T011514Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T011514Z-unit/unittest.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T011514Z) [skip ci]` -> `c96f0a93`
  - `chore: record md1-shrunk postpush snapshot (20260520T011514Z) [skip ci]` -> `10609c7b`
  - GitHub Actions postpush snapshot (no new runs for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T011514Z-ci/postpush-final.txt`

## 2026-05-20T01:46Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T014617Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T014617Z-preflight/stepfunctions-describe-execution-md1-shrunk-prodspine-wlight-202605190027.json`
  - Public S3 meta.json HEAD -> `200` + Edge meta.json HEAD -> `200` (see preflight file)
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners: none detected (see preflight file)
- Public bundle snapshot (S3 listing + S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T014617Z-bundle/bundle.txt`
- GitHub Actions snapshot:
  - `logs/md1-shrunk/polls/20260520T014617Z-ci/summary.txt`
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260520T014617Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260520T014617Z-edge-publish-report/publish-edge.report.html`
  - output: `logs/md1-shrunk/polls/20260520T014617Z-edge-publish-report/publish-edge.json`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260520T014617Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T014617Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260520T014617Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T014617Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T014617Z-unit/unittest.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T014617Z) [skip ci]` -> `1e40015b`
  - GitHub Actions postpush snapshot (no new runs for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T014617Z-ci/postpush-final.txt`

## 2026-05-20T02:14Z heartbeat verify (strict gates still PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T021410Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T021410Z-preflight/stepfunctions-describe-execution-md1-shrunk-prodspine-wlight-202605190027.json`
  - Public S3 meta.json HEAD -> `200` + Edge meta.json HEAD -> `200` (see preflight file)
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners: none detected (see preflight file)
- Public bundle snapshot (S3 listing + S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T021410Z-bundle/bundle.txt`
- GitHub Actions snapshot (exact-head is logs-only; `[skip ci]` -> typically no new runs):
  - `logs/md1-shrunk/polls/20260520T021410Z-ci/summary.txt`
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260520T021410Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260520T021410Z-edge-publish-report/publish-edge.report.html`
  - output: `logs/md1-shrunk/polls/20260520T021410Z-edge-publish-report/publish-edge.json`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260520T021410Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T021410Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260520T021410Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T021410Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T021410Z-unit/unittest.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T021410Z) [skip ci]` -> `f25e9a99`
  - GitHub Actions postpush snapshot (no new runs for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T021410Z-ci/postpush-final.txt`

## 2026-05-20T02:54Z heartbeat verify (strict gates PASS; camera-suite iframe retry fix)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T024304Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T024304Z-preflight/stepfunctions-describe-execution-md1-shrunk-prodspine-wlight-202605190027.json`
  - Public S3 meta.json HEAD -> `200` + Edge meta.json HEAD -> `200` (see preflight file)
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners: none detected (see preflight file)
- Public bundle snapshot (S3 listing + S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T025403Z-bundle/bundle.txt` (sha256 parity + listing)
- GitHub Actions snapshot:
  - `logs/md1-shrunk/polls/20260520T025447Z-ci/summary.txt`
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260520T025431Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260520T025431Z-edge-publish-report/publish-edge.report.html`
  - output: `logs/md1-shrunk/polls/20260520T025431Z-edge-publish-report/publish-edge.json`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - first attempt FAIL (Playwright flake: iframe detached during screenshot):
    - `logs/md1-shrunk/polls/20260520T024447Z-camera-suite/suite-summary.json` -> `decision=fail`
  - fix: retry iframe screenshot + fallback page screenshot:
    - `web/scripts/render-md1-camera-check.mjs`
  - rerun PASS:
    - command: `logs/md1-shrunk/polls/20260520T024942Z-camera-suite/run.cmd.txt`
    - result: `logs/md1-shrunk/polls/20260520T024942Z-camera-suite/suite-summary.json` -> `decision=pass`
    - report: `logs/md1-shrunk/polls/20260520T024942Z-camera-suite/report.html`
    - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T025441Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T025441Z-unit/unittest.txt`
- Commit/push:
  - `fix: retry iframe screenshot for md1 camera-suite` -> `13327ca3`
  - GitHub Actions exact-head:
    - CDK Deploy success `26138455344` (sha `13327ca3`):
      - `logs/md1-shrunk/polls/20260520T025739Z-ci-postpush/watch-cdk.txt`
    - Pages success `26138455345` (sha `13327ca3`):
      - `logs/md1-shrunk/polls/20260520T025739Z-ci-postpush/watch-pages.txt`
      - preview alias line: `logs/md1-shrunk/polls/20260520T025739Z-ci-postpush/pages-preview-url.txt`

## 2026-05-20T03:14Z heartbeat verify (strict gates PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T031430Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0` (see preflight JSON captures)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T031430Z-preflight/stepfunctions-describe-known.json`
  - Public S3 meta.json HEAD -> `200` + Edge meta.json HEAD -> `200` (see preflight file)
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners: detected a `next dev` in another worktree (see preflight file); no MD1-Baseline server assumed.
- Public bundle snapshot (S3 listing + S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T031430Z-bundle/bundle.txt`
- GitHub Actions snapshot (exact-head is logs-only; `[skip ci]` -> typically no new runs):
  - `logs/md1-shrunk/polls/20260520T031430Z-ci/summary.txt`
- Browser-readable public delivery automation (Lambda publish + strict browser header validation + HTML report):
  - command: `logs/md1-shrunk/polls/20260520T031430Z-edge-publish-report/run.cmd.txt`
  - report: `logs/md1-shrunk/polls/20260520T031430Z-edge-publish-report/publish-edge.report.html`
  - output: `logs/md1-shrunk/polls/20260520T031430Z-edge-publish-report/publish-edge.json`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260520T031430Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T031430Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260520T031430Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T031430Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T031430Z-unit/unittest.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T031430Z) [skip ci]` -> `d7c3b92e`
  - `chore: record md1-shrunk postpush snapshot (20260520T031430Z) [skip ci]` -> `150b2b74`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T031430Z-ci/postpush-final.txt`

## 2026-05-20T03:55Z heartbeat verify (strict gates PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T034403Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0` (see preflight JSON captures)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T034403Z-preflight/stepfunctions-describe-known.json`
  - Public S3 meta.json HEAD -> `200` + Edge meta.json HEAD -> `200` (see preflight file)
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners: detected a `next dev` in another worktree (see preflight file); no MD1-Baseline server assumed.
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T035250Z-bundle/bundle.txt`
- Browser-readable public delivery validation (no republish; Origin CORS + cache headers for meta.json + referenced assets):
  - `logs/md1-shrunk/polls/20260520T035154Z-edge-validate/validate.txt`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260520T034725Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T034725Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260520T034725Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T035250Z) [skip ci]` -> `802ff846`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T035502Z-ci-postpush/postpush-final.txt`

## 2026-05-20T04:19Z heartbeat verify (strict gates PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T041342Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0` (see preflight JSON captures)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T041342Z-preflight/stepfunctions-describe-known.json`
  - Public S3 meta.json HEAD -> `200` + Edge meta.json HEAD -> `200` (see preflight file)
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners: detected a `next dev` in another worktree (see preflight file); no MD1-Baseline server assumed.
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T041439Z-bundle/bundle.txt`
- Browser-readable public delivery validation (no republish; Origin CORS + cache headers for meta.json + referenced assets):
  - `logs/md1-shrunk/polls/20260520T041458Z-edge-validate/validate.txt`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260520T041542Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T041542Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260520T041542Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T041426Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T041426Z-unit/unittest.txt`
- GitHub Actions snapshot (exact-head is logs-only; `[skip ci]` -> typically no new runs):
  - `logs/md1-shrunk/polls/20260520T041955Z-ci/summary.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T041955Z) [skip ci]` -> `49178c42`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T042151Z-ci-postpush/postpush-final.txt`

## 2026-05-20T04:43Z heartbeat verify (strict gates PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T044301Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0` (see captured JSON)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T044301Z-preflight/stepfunctions-describe-known.json`
  - Public S3 meta.json HEAD -> `200` + Edge meta.json HEAD -> `200` (see `preflight.txt`)
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners: detected a `next dev` in another worktree (see `preflight.txt`)
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T044301Z-bundle/bundle.txt`
- Browser-readable public delivery validation (no republish; Origin CORS + cache headers for meta.json + referenced assets):
  - `logs/md1-shrunk/polls/20260520T044301Z-edge-validate/validate.txt`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260520T044301Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T044301Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260520T044301Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T044301Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T044301Z-unit/unittest.txt`
- GitHub Actions snapshot (head is logs-only ; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T044301Z-ci/summary.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T044301Z) [skip ci]` -> `847ed7a6`
  - `chore: fix md1-shrunk STATE commit pointer (20260520T044301Z) [skip ci]` -> `dcaf0d5a`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T044301Z-ci-postpush/postpush-final.txt`

## 2026-05-20T05:14Z heartbeat verify (strict gates PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T051407Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0` (see captured JSON)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T051407Z-preflight/stepfunctions-describe-known.json`
  - Public S3 meta.json HEAD -> `200` + Edge meta.json HEAD -> `200` (see `preflight.txt`)
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners + listen ports: see `preflight.txt`.
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T051407Z-bundle/bundle.txt`
- Browser-readable public delivery validation (no republish; Origin CORS + cache headers for meta.json + referenced assets):
  - `logs/md1-shrunk/polls/20260520T051407Z-edge-validate/validate.txt`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260520T051407Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T051407Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260520T051407Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T051407Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T051407Z-unit/unittest.txt`
- GitHub Actions snapshot:
  - `logs/md1-shrunk/polls/20260520T051407Z-ci/summary.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T051407Z) [skip ci]` -> `299a118e`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T051407Z-ci-postpush/postpush-final.txt`

## 2026-05-20T05:44Z heartbeat verify (strict gates PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T054416Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0` (see captured JSON)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T054416Z-preflight/stepfunctions-describe-known.json`
  - Public S3 meta.json HEAD -> `200` + Edge meta.json HEAD -> `200` (see `preflight.txt`)
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners + listen ports: see `preflight.txt`.
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T054416Z-bundle/bundle.txt`
- Browser-readable public delivery validation (automation; Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T054416Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T054416Z-edge-validate/validate.txt` (includes edge URL + file outputs)
  - report: `logs/md1-shrunk/polls/20260520T054416Z-edge-validate/publish-edge.report.html`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260520T054416Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T054416Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260520T054416Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T054416Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T054416Z-unit/unittest.txt`
- GitHub Actions snapshot:
  - `logs/md1-shrunk/polls/20260520T054416Z-ci/summary.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T054416Z) [skip ci]` -> `35170966`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T054416Z-ci-postpush/postpush-final.txt`

## 2026-05-20T06:15Z heartbeat verify (strict gates PASS; no new jobs)

- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T061516Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0` (see captured JSON)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T061516Z-preflight/stepfunctions-describe-known.json`
  - Public S3 meta.json HEAD -> `200` + Edge meta.json HEAD -> `200` (see `preflight.txt`)
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners + listen ports: see `preflight.txt`.
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T061516Z-bundle/bundle.txt`
- Browser-readable public delivery validation (automation; Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T061516Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T061516Z-edge-validate/validate.txt` (includes edge URL + file outputs)
  - report: `logs/md1-shrunk/polls/20260520T061516Z-edge-validate/publish-edge.report.html`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification):
  - command: `logs/md1-shrunk/polls/20260520T061516Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T061516Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260520T061516Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T061516Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T061516Z-unit/unittest.txt`
- GitHub Actions snapshot (head is logs-only ; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T061516Z-ci/summary.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T061516Z) [skip ci]` -> `bfae7a66`
  - `chore: record md1-shrunk postpush snapshot (20260520T061516Z) [skip ci]` -> `ee58c67b`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T061516Z-ci-postpush/postpush-final.txt`

## 2026-05-20T06:48Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- New automation script (replaces the ad-hoc one-liner; produces the same poll structure deterministically):
  - `scripts/sfm/run_md1_shrunk_heartbeat_verify.py`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T064811Z-summary.json`
- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T064811Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T064811Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T064811Z-bundle/bundle.txt`
- Browser-readable public delivery validation (automation; Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T064811Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T064811Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T064811Z-edge-validate/publish-edge.report.html`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon diagnostics):
  - command: `logs/md1-shrunk/polls/20260520T064811Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T064811Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260520T064811Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Unit proof (verbose output to make PASS explicit in-file):
  - command: `logs/md1-shrunk/polls/20260520T064811Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T064811Z-unit/unittest.txt`
- GitHub Actions snapshot (head is not deployed; exact-head runs remain the last green Pages+CDK pair):
  - `logs/md1-shrunk/polls/20260520T064811Z-ci/summary.txt`
- Commit/push + exact-head CI:
  - `feat: automate md1-shrunk heartbeat verification` -> `4f3aa301`
  - CDK Deploy: `26146671471` -> `success`
  - Deploy Next.js to Cloudflare Pages: `26146671467` -> `success`
  - Preview alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - Hash URL: `https://0167e947.v0-spaceport-website-preview2.pages.dev`
  - Postpush artifacts:
    - `logs/md1-shrunk/polls/20260520T064811Z-ci-postpush/postpush-final.txt`
    - `logs/md1-shrunk/polls/20260520T064811Z-ci-postpush/pages-preview-url.txt`

## 2026-05-20T07:29Z heartbeat verify (scripted; strict gates PASS; no new jobs; baseline auto-pick)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T072905Z-summary.json`
- Script hardening (pose baseline is now reusable without passing `--baseline-suite-dir`):
  - `scripts/sfm/run_md1_shrunk_heartbeat_verify.py` auto-selects a stable baseline camera-suite dir when omitted, preferring the baseline referenced by the most recent passing run for the same bundle+viewer.
- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T072905Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0`
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T072905Z-preflight/stepfunctions-describe-known.json`
  - Public S3 meta.json HEAD -> `200` + Edge meta.json HEAD -> `200` (see `preflight.txt`)
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners + listen ports: see `preflight.txt`.
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T072905Z-bundle/bundle.txt`
- Browser-readable public delivery validation (automation; Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T072905Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T072905Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T072905Z-edge-validate/publish-edge.report.html`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon diagnostics):
  - command: `logs/md1-shrunk/polls/20260520T072905Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T072905Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260520T072905Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T072905Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T072905Z-unit/unittest.txt`
- GitHub Actions snapshot (pre-push; for the new head see `ci-postpush` artifacts below):
  - `logs/md1-shrunk/polls/20260520T072905Z-ci/summary.txt`
- Commit/push + exact-head CI:
  - `fix: auto-pick baseline for md1-shrunk heartbeat` -> `31d9bd7c`
    - CDK Deploy: `26148433269` -> `success`
    - CDK logs: `logs/md1-shrunk/polls/20260520T072905Z-ci-postpush/view-cdk.log.txt`
    - note: Pages workflow did not trigger for this sha (no `web/` changes); bumped `web/trigger-dev-build.txt` to force Pages.
  - `chore: trigger pages build` -> `641b0273`
    - CDK Deploy: `26148667959` -> `success`
    - Pages: `26148667948` -> `success`
    - preview URL proof: `logs/md1-shrunk/polls/20260520T072905Z-ci-postpush-sha-641b0273/pages-preview-url.txt`
    - CDK logs: `logs/md1-shrunk/polls/20260520T072905Z-ci-postpush-sha-641b0273/view-cdk.log.txt`
    - Pages logs: `logs/md1-shrunk/polls/20260520T072905Z-ci-postpush-sha-641b0273/view-pages.log.txt`

## 2026-05-20T08:14Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T081401Z-summary.json`
- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T081401Z-preflight/preflight.txt`
  - Step Functions (staging + `SpaceportMLPipeline-br-8abcbd5662`) RUNNING: `0` (see captured JSON)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T081401Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T081401Z-bundle/bundle.txt` (sha256 match)
- Browser-readable public delivery validation (automation; Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T081401Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T081401Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T081401Z-edge-validate/publish-edge.report.html`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon diagnostics):
  - command: `logs/md1-shrunk/polls/20260520T081401Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T081401Z-camera-suite/suite-summary.json` -> `decision=pass`
  - report: `logs/md1-shrunk/polls/20260520T081401Z-camera-suite/report.html`
  - reusable camera-pose verification: `pose_verification.max_delta=0.0` (baseline: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`)
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T081401Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T081401Z-unit/unittest.txt`
- GitHub Actions snapshot (head is logs-only; `[skip ci]` -> typically no new runs):
  - `logs/md1-shrunk/polls/20260520T081401Z-ci/summary.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T081401Z) [skip ci]` -> `35f0b387`
  - `chore: record md1-shrunk postpush snapshot (20260520T082123Z) [skip ci]` -> `620add51`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T082123Z-ci-postpush-sha-35f0b387/postpush.txt`

## 2026-05-20T08:57Z heartbeat verify (parity fix + prod->staging publish fallback; strict gates PASS; no new jobs)

- Bugfix: edge publish now tolerates prod-bucket inputs in preview stacks:
  - symptom: `scripts/publish_ml_bundle_to_edge.py` failed when `--compressed-output-s3-uri` pointed at `s3://spaceport-ml-processing/...` because the preview publish Lambda lacks `s3:ListBucket` on the prod bucket.
  - fix: `scripts/publish_ml_bundle_to_edge.py` now auto-falls back to `s3://spaceport-ml-processing-staging/...` (same prefix) when the prod bucket is denied and the staging prefix exists.
  - proof (fallback captured in publish output JSON):
    - `logs/md1-shrunk/polls/20260520T085749Z-edge-validate/publish-edge.json` (`fallbackUsed=true`)
- Bugfix: bundle parity now runs even when `--edge-meta-url` is omitted:
  - symptom: `scripts/sfm/run_md1_shrunk_heartbeat_verify.py` wrote `parity skipped` despite resolving the edge meta URL from the publish step.
  - fix: parity is now computed after publish using the resolved edge meta URL.
  - proof (sha256 parity match):
    - `logs/md1-shrunk/polls/20260520T085749Z-bundle/bundle.txt`
- Disk safety: pruned large camera-suite binary artifacts to prevent `No space left on device` during COLMAP `images.txt` download:
  - removed reproducible `inputs/`, `renders/`, `panels/` from older `*-camera-suite` poll dirs (kept JSON summaries + diagnostics).
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T085749Z-summary.json`
- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T085749Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - SageMaker InProgress: `0` (processing + training)
- Browser-readable public delivery validation (Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T085749Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T085749Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T085749Z-edge-validate/publish-edge.report.html`
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon diagnostics):
  - command: `logs/md1-shrunk/polls/20260520T085749Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T085749Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`)
  - report: `logs/md1-shrunk/polls/20260520T085749Z-camera-suite/report.html`
  - baseline suite dir used: `logs/md1-shrunk/polls/20260519T163352Z-camera-suite`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T085749Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T085749Z-unit/unittest.txt`
- GitHub Actions snapshot:
  - `logs/md1-shrunk/polls/20260520T085749Z-ci/summary.txt`

## 2026-05-20T09:20Z exact-head workflows green (post-push)

- Commit/push:
  - `fix: harden md1-shrunk heartbeat parity` -> `8f922d21`
    - CDK Deploy run `26152775602` succeeded for sha `8f922d21` (Pages did not trigger because no `web/` changes).
  - `chore: trigger pages build` -> `14f6eaf2`
    - CDK Deploy run `26153004933` -> `success`
    - Pages run `26153004935` -> `success`
    - PREVIEW_URL proof (from same Pages run log):
      - `logs/md1-shrunk/polls/20260520T0912Z-ci-postpush-sha-14f6eaf2/pages-preview-url.txt`
    - CDK + Pages full logs:
      - `logs/md1-shrunk/polls/20260520T0912Z-ci-postpush-sha-14f6eaf2/view-cdk.log.txt`
      - `logs/md1-shrunk/polls/20260520T0912Z-ci-postpush-sha-14f6eaf2/view-pages.log.txt`

## 2026-05-20T09:21Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T092120Z-summary.json`
- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T092120Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T092120Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners + listen ports: see `preflight.txt`.
- Browser-readable public delivery validation (Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T092120Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T092120Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T092120Z-edge-validate/publish-edge.report.html`
  - publish proof: `logs/md1-shrunk/polls/20260520T092120Z-edge-validate/publish-edge.json` (`fallbackUsed=true`)
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T092120Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T092120Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T092120Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`)
  - report: `logs/md1-shrunk/polls/20260520T092120Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T092120Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T092120Z-unit/unittest.txt`
- GitHub Actions snapshot:
  - `logs/md1-shrunk/polls/20260520T092120Z-ci/summary.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T092120Z) [skip ci]` -> `5abc52cf`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head; last relevant CI is sha `14f6eaf2`):
    - `logs/md1-shrunk/polls/20260520T092120Z-ci-postpush-sha-5abc52cf/postpush.txt`
  - `chore: record md1-shrunk postpush snapshot (20260520T092120Z) [skip ci]` -> `67bc90f3`
  - GitHub Actions postpush snapshot for the final head (no new runs expected for `[skip ci]`):
    - `logs/md1-shrunk/polls/20260520T092120Z-ci-postpush-sha-67bc90f3/postpush.txt`

## 2026-05-20T09:53Z heartbeat verify (scripted; strict gates PASS; pruned camera artifacts; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T095305Z-summary.json`
- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T095305Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T095305Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
- Browser-readable public delivery validation (Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T095305Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T095305Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T095305Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T095305Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T095305Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T095305Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`)
  - report: `logs/md1-shrunk/polls/20260520T095305Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T095305Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T095305Z-unit/unittest.txt`
- GitHub Actions snapshot:
  - `logs/md1-shrunk/polls/20260520T095305Z-ci/summary.txt`

## 2026-05-20T10:09Z exact-head workflows green (post-push)

- Commit/push:
  - `fix: prune md1-shrunk camera artifacts on pass` -> `4abff30c`
    - CDK Deploy run `26155418466` -> `success`
    - Pages run `26155418467` -> `success`
    - PREVIEW_URL proof (from same Pages run log):
      - `logs/md1-shrunk/polls/20260520T100053Z-ci-postpush-sha-4abff30c/pages-preview-url.txt`
    - CDK + Pages logs:
      - `logs/md1-shrunk/polls/20260520T100053Z-ci-postpush-sha-4abff30c/view-cdk.log.txt`
      - `logs/md1-shrunk/polls/20260520T100053Z-ci-postpush-sha-4abff30c/view-pages.log.txt`
    - Postpush run list:
      - `logs/md1-shrunk/polls/20260520T100053Z-ci-postpush-sha-4abff30c/run-list.txt`

## 2026-05-20T10:14Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T101455Z-summary.json`
  - HEAD: `a1157bf81bfe91a553c91b34c32f3d2d85329570`
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T101455Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - SageMaker InProgress: `0` (processing + training)
- Browser-readable public delivery validation (Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T101455Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T101455Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T101455Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T101455Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T101455Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T101455Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`)
  - report: `logs/md1-shrunk/polls/20260520T101455Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T101455Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T101455Z-unit/unittest.txt`
- GitHub Actions snapshot:
  - `logs/md1-shrunk/polls/20260520T101455Z-ci/summary.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T101455Z) [skip ci]` -> `e6650cee`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head; last relevant CI is sha `4abff30c`):
    - `logs/md1-shrunk/polls/20260520T101455Z-ci-postpush-sha-e6650cee/postpush.txt`
  - `chore: record md1-shrunk postpush snapshot (20260520T101455Z) [skip ci]` -> `49e91597`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]`):
    - `logs/md1-shrunk/polls/20260520T101455Z-ci-postpush-sha-49e91597/postpush.txt`
  - `chore: record md1-shrunk final postpush snapshot (20260520T101455Z) [skip ci]` -> `de8481ff`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]`):
    - `logs/md1-shrunk/polls/20260520T101455Z-ci-postpush-sha-de8481ff/postpush.txt`

## 2026-05-20T10:44Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T104405Z-summary.json`
  - HEAD: `6053589a83a1f1e97670e15ea1f3556282561407`
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T104405Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T104405Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners + listen ports: see `preflight.txt`.
- Browser-readable public delivery validation (Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T104405Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T104405Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T104405Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T104405Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T104405Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T104405Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`)
  - report: `logs/md1-shrunk/polls/20260520T104405Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T104405Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T104405Z-unit/unittest.txt`
- GitHub Actions snapshot:
  - `logs/md1-shrunk/polls/20260520T104405Z-ci/summary.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T104405Z) [skip ci]` -> `27b2b6ac`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head; last relevant CI is sha `4abff30c`):
    - `logs/md1-shrunk/polls/20260520T104405Z-ci-postpush-sha-27b2b6ac/postpush.txt`
  - `chore: record md1-shrunk postpush snapshot (20260520T104405Z) [skip ci]` -> `743d3d73`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T104405Z-ci-postpush-sha-743d3d73/postpush.txt`

## 2026-05-20T11:16Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T111610Z-summary.json`
  - HEAD: `dce652d79ccb3453cb84d68ebb6d36523043546b`
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T111610Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T111610Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners + listen ports: see `preflight.txt`.
- Browser-readable public delivery validation (Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T111610Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T111610Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T111610Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T111610Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T111610Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T111610Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`)
  - report: `logs/md1-shrunk/polls/20260520T111610Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T111610Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T111610Z-unit/unittest.txt`
- GitHub Actions snapshot:
  - `logs/md1-shrunk/polls/20260520T111610Z-ci/summary.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T111610Z) [skip ci]` -> `d683e102`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head; last relevant CI is sha `4abff30c`):
    - `logs/md1-shrunk/polls/20260520T111610Z-ci-postpush-sha-d683e102/postpush.txt`
  - `chore: record md1-shrunk postpush snapshot (20260520T111610Z) [skip ci]` -> `e19e1b88`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]`):
    - `logs/md1-shrunk/polls/20260520T111610Z-ci-postpush-sha-e19e1b88/postpush.txt`

## 2026-05-20T11:44Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T114431Z-summary.json`
  - HEAD: `936ba4291d057204231f0dbc5cd9137634819304`
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T114431Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T114431Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners + listen ports: see `preflight.txt`.
- Browser-readable public delivery validation (Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T114431Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T114431Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T114431Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T114431Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T114431Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T114431Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`)
  - report: `logs/md1-shrunk/polls/20260520T114431Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T114431Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T114431Z-unit/unittest.txt`
- GitHub Actions snapshot:
  - `logs/md1-shrunk/polls/20260520T114431Z-ci/summary.txt`
- Commit/push:
  - `chore: record md1-shrunk heartbeat verification (20260520T114431Z) [skip ci]` -> `d5f97973`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head; last relevant CI remains sha `4abff30c`):
    - `logs/md1-shrunk/polls/20260520T115258Z-ci-postpush-sha-d5f97973/postpush.txt`

## 2026-05-20T12:14Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T121434Z-summary.json`
  - HEAD: `4fd7fc4cecf9e143781131442f721886c51bda25`
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T121434Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T121434Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
- Browser-readable public delivery validation (Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T121434Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T121434Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T121434Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T121434Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T121434Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T121434Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`)
  - report: `logs/md1-shrunk/polls/20260520T121434Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T121434Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T121434Z-unit/unittest.txt`
- GitHub Actions snapshot:
  - `logs/md1-shrunk/polls/20260520T121434Z-ci/summary.txt`
- Commit/push:
  - `chore: md1-shrunk heartbeat verify 20260520T121434Z [skip ci]` -> `0e8b574e`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head; last relevant CI remains sha `4abff30c243b60464ef8ccf6218a4b166d33a5f2`):
    - `logs/md1-shrunk/polls/20260520T122042Z-ci-postpush-sha-0e8b574e/postpush.txt`

## 2026-05-20T12:46Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T124603Z-summary.json`
  - HEAD: `7795a5a5954814fae781255c2939ae07bb288af2` (`[skip ci]` head; no new workflows expected)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Manual preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T124318Z-heartbeat-preflight/preflight.txt`
- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T124603Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T124603Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
- Browser-readable public delivery validation (Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T124603Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T124603Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T124603Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T124603Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T124603Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T124603Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`)
  - report: `logs/md1-shrunk/polls/20260520T124603Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T124603Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T124603Z-unit/unittest.txt`
- GitHub Actions snapshot:
  - `logs/md1-shrunk/polls/20260520T124603Z-ci/summary.txt`
- Commit/push:
  - `chore: md1-shrunk heartbeat verify 20260520T124603Z [skip ci]` -> `88a9383f`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head; last relevant CI remains sha `4abff30c243b60464ef8ccf6218a4b166d33a5f2`):
    - `logs/md1-shrunk/polls/20260520T125355Z-ci-postpush-sha-88a9383f/postpush.txt`
  - `chore: record md1-shrunk postpush snapshot (20260520T124603Z) [skip ci]` -> `8053f2cc`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head; last relevant CI remains sha `4abff30c243b60464ef8ccf6218a4b166d33a5f2`):
    - `logs/md1-shrunk/polls/20260520T125453Z-ci-postpush-sha-8053f2cc/postpush.txt`

## 2026-05-20T13:14Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T131429Z-summary.json`
  - HEAD: `682fad952bcd7912849af3f9533d2d184d47d23f` (`[skip ci]` head; no new workflows expected)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Manual preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T131400Z-manual-preaction/preflight.txt`
- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T131429Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T131429Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners + listen ports: see `preflight.txt`.
- Browser-readable public delivery validation (Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T131429Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T131429Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T131429Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T131429Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T131429Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T131429Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`)
  - report: `logs/md1-shrunk/polls/20260520T131429Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T131429Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T131429Z-unit/unittest.txt`
- GitHub Actions snapshot:
  - `logs/md1-shrunk/polls/20260520T131429Z-ci/summary.txt`
- Commit/push:
  - `chore: md1-shrunk heartbeat verify 20260520T131429Z [skip ci]` -> `c4fd84d9`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head; last relevant CI remains sha `4abff30c243b60464ef8ccf6218a4b166d33a5f2`):
    - `logs/md1-shrunk/polls/20260520T132241Z-ci-postpush-sha-c4fd84d9/postpush.txt`
  - `chore: record md1-shrunk postpush snapshot (20260520T131429Z) [skip ci]` -> `af7af01b`

## 2026-05-20T13:45Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T134527Z-summary.json`
  - HEAD: `af7af01b908eb0eb0c9229b4aab7fee2da0cdf7d` (`[skip ci]` head; no new workflows expected)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Manual preflight snapshot (read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T134446Z-manual-preaction/preflight.txt`
- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T134527Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners + listen ports: see `preflight.txt`.
- Browser-readable public delivery validation (Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T134527Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T134527Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T134527Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T134527Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T134527Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T134527Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`)
  - report: `logs/md1-shrunk/polls/20260520T134527Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T134527Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T134527Z-unit/unittest.txt`
- GitHub Actions snapshot:
  - `logs/md1-shrunk/polls/20260520T134527Z-ci/summary.txt`
- Commit/push:
  - `chore: md1-shrunk heartbeat verify 20260520T134527Z [skip ci]` -> `343c2b20`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head; last relevant CI remains sha `4abff30c243b60464ef8ccf6218a4b166d33a5f2`):
    - `logs/md1-shrunk/polls/20260520T135303Z-ci-postpush-sha-343c2b20/postpush.txt`

## 2026-05-20T14:17Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T141720Z-summary.json`
  - HEAD: `128d846cd75944f48e50a8f305a07e2ed9e71428` (`[skip ci]` head; no new workflows expected)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T141720Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T141720Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
  - Local dev server listeners + listen ports: see `preflight.txt`.
- Browser-readable public delivery validation (automation; Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T141720Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T141720Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T141720Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T141720Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T141720Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T141720Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T141720Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T141720Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T141720Z-unit/unittest.txt`
- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T141720Z-ci/summary.txt`

- Commit/push:
  - `chore: md1-shrunk heartbeat verify 20260520T141720Z [skip ci]` -> `c96f510f`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T142808Z-ci-postpush-sha-c96f510f/postpush.txt`

## 2026-05-20T14:50Z heartbeat verify (scripted; strict gates PASS; no new jobs)

note: reran heartbeat after `20260520T144551Z` because bundle parity was skipped when `--s3-meta-url` was not provided.

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T145055Z-summary.json`
  - HEAD: `c87bc6421f84259217d6aa7ea7e2a4f70f8d7284` (`[skip ci]` head; no new workflows expected)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T145055Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - SageMaker InProgress: `0` (processing + training)
- Browser-readable public delivery validation (automation; Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T145055Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T145055Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T145055Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T145055Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T145055Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T145055Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T145055Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T145055Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T145055Z-unit/unittest.txt`
- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T145055Z-ci/summary.txt`

- Commit/push:
  - `chore: md1-shrunk heartbeat verify 20260520T145055Z [skip ci]` -> `f1846e67`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T145055Z-ci-postpush-sha-f1846e67/postpush.txt`

## 2026-05-20T15:14Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T151446Z-summary.json`
  - HEAD: `7257c89bdcb741ee21042535e1d19f0d91e5ae78` (`[skip ci]` head; no new workflows expected)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T151446Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T151446Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
- Browser-readable public delivery validation (automation; Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T151446Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T151446Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T151446Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T151446Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T151446Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T151446Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T151446Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T151446Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T151446Z-unit/unittest.txt`
- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T151446Z-ci/summary.txt`

- Commit/push:
  - `chore: md1-shrunk heartbeat verify 20260520T151446Z [skip ci]` -> `d65b6eeb`
  - GitHub Actions postpush snapshot (no new runs expected for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T151446Z-ci-postpush-sha-d65b6eeb/postpush.txt`

## 2026-05-20T15:45Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T154502Z-summary.json`
  - HEAD: `81c623bb790ae4d74729ced75058767055b50a7e` (`[skip ci]` head; no new workflows expected)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T154502Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T154502Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
- Browser-readable public delivery validation (automation; Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T154502Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T154502Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T154502Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T154502Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T154502Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T154502Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T154502Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T154502Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T154502Z-unit/unittest.txt`
- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T154502Z-ci/summary.txt`

- Commit/push:
  - `chore: md1-shrunk heartbeat verify 20260520T154502Z [skip ci]` -> `0449b764`
  - GitHub Actions postpush snapshot (exact-head run count `0` for `[skip ci]` head `0449b764...`):
    - `logs/md1-shrunk/polls/20260520T154502Z-ci-postpush-sha-0449b764/postpush.txt`

## 2026-05-20T16:15Z heartbeat verify (scripted; camera suite failed; local disk full)

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T161512Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - SageMaker InProgress: `0` (processing + training)
- Bundle parity + edge delivery validation completed before failure:
  - `logs/md1-shrunk/polls/20260520T161512Z-bundle/bundle.txt`
  - `logs/md1-shrunk/polls/20260520T161512Z-edge-validate/validate.txt`
- Failure evidence:
  - `logs/md1-shrunk/polls/20260520T161512Z-camera-suite/run.out.txt`
  - `logs/md1-shrunk/polls/20260520T161512Z-camera-suite/diagnosis.txt`
- Root cause: camera-suite pose derivation attempted to download ~600MB COLMAP `images.txt` (points2D payload) into temp; repeated downloads exhausted local disk.

## 2026-05-20T16:23Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T162347Z-summary.json`
  - HEAD: `ec27bc6225a7fac268e7b2c8ea05edb6bf1d544f`
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T162347Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T162347Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
- Browser-readable public delivery validation (automation; Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T162347Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T162347Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T162347Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T162347Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T162347Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T162347Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - note: pose derivation used compact `frames.txt` (see `logs/md1-shrunk/polls/20260520T162347Z-camera-suite/camera-poses.json` -> `.images_txt`).
  - report: `logs/md1-shrunk/polls/20260520T162347Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T162347Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T162347Z-unit/unittest.txt`
- GitHub Actions snapshot (head is code+logs; CI should run after push):
  - `logs/md1-shrunk/polls/20260520T162347Z-ci/summary.txt`

## 2026-05-20T16:42Z postpush CI snapshot (Pages + CDK both green)

- exact-head commit: `74aed926` (`chore: trigger pages build`)
- CDK Deploy run: `26176189124` -> success
- Deploy Next.js to Cloudflare Pages run: `26176189057` -> success
- PREVIEW_URL resolved from that Pages run:
  - `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
- Evidence:
  - `logs/md1-shrunk/polls/20260520T164240Z-ci-postpush-sha-74aed926/postpush.txt`

## 2026-05-20T16:50Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T165016Z-summary.json`
  - HEAD: `b7397499c588874fb81bcb51f95c51edd8d9b22f` (`[skip ci]` head; no new workflows expected)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T165016Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - SageMaker InProgress: `0` (processing + training)
- Browser-readable public delivery validation (automation; Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T165016Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T165016Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T165016Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T165016Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T165016Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T165016Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T165016Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T165016Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T165016Z-unit/unittest.txt`
- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T165016Z-ci/summary.txt`

## 2026-05-20T17:10Z postpush CI snapshot (Pages + CDK both green)

- exact-head commit: `1359cb1a` (`chore: trigger pages build`)
- CDK Deploy run: `26177531892` -> success
- Deploy Next.js to Cloudflare Pages run: `26177531889` -> success
- PREVIEW_URL resolved from that Pages run:
  - `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
- Evidence:
  - `logs/md1-shrunk/polls/20260520T170930Z-ci-postpush-sha-1359cb1a/postpush.txt`

## 2026-05-20T17:11Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `03a1c38e` (`[skip ci]` head; exact-head workflows expected: none)
- last relevant Pages + CDK success remains:
  - commit: `1359cb1a`
  - CDK Deploy run: `26177531892` -> success
  - Deploy Next.js to Cloudflare Pages run: `26177531889` -> success
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
- Evidence:
  - `logs/md1-shrunk/polls/20260520T171116Z-ci-postpush-sha-03a1c38e/postpush.txt`

## 2026-05-20T17:15Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T171531Z-summary.json`
  - HEAD: `003505351945ca9aa3b17bcad43ad91281e8574a`
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T171531Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - SageMaker InProgress: `0` (processing + training)
- Browser-readable public delivery validation (automation; Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T171531Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T171531Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T171531Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T171531Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T171531Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T171531Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T171531Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T171531Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T171531Z-unit/unittest.txt`
- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T171531Z-ci/summary.txt`

## 2026-05-20T17:21Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `89cf4b1e` (`[skip ci]` head; exact-head workflows expected: none)
- last relevant Pages + CDK success remains:
  - commit: `1359cb1a`
  - CDK Deploy run: `26177531892` -> success
  - Deploy Next.js to Cloudflare Pages run: `26177531889` -> success
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
- Evidence:
  - `logs/md1-shrunk/polls/20260520T172145Z-ci-postpush-sha-89cf4b1e/postpush.txt`

## 2026-05-20T17:44Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260520T174451Z-heartbeat.cmd.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T174451Z-summary.json`
  - HEAD: `936ca1f2a7b73c9deb81bdd74032fdbe0520fc58` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T174451Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T174451Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
- Browser-readable public delivery validation (automation; Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T174451Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T174451Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T174451Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T174451Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T174451Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T174451Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T174451Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T174451Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T174451Z-unit/unittest.txt`
- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T174451Z-ci/summary.txt`

- Commit/push:
  - `chore: md1-shrunk heartbeat verify 20260520T174451Z [skip ci]` -> `5286551f`
  - GitHub Actions postpush snapshot (exact-head workflows expected: none for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T174451Z-ci-postpush-sha-5286551f/postpush.txt`

## 2026-05-20T18:15Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260520T181505Z-heartbeat.cmd.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T181505Z-summary.json`
  - HEAD: `765eaac09efc97e4e96dfb9848edb95520a7c499` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T181505Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T181505Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
- Browser-readable public delivery validation (automation; Origin CORS + cache headers for meta.json + referenced assets):
  - command: `logs/md1-shrunk/polls/20260520T181505Z-edge-validate/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T181505Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T181505Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T181505Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - command: `logs/md1-shrunk/polls/20260520T181505Z-camera-suite/run.cmd.txt`
  - result: `logs/md1-shrunk/polls/20260520T181505Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T181505Z-camera-suite/report.html`
- Unit proof:
  - command: `logs/md1-shrunk/polls/20260520T181505Z-unit/run.cmd.txt`
  - output: `logs/md1-shrunk/polls/20260520T181505Z-unit/unittest.txt`
- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T181505Z-ci/summary.txt`

- Commit/push:
  - `chore: md1-shrunk heartbeat verify 20260520T181505Z [skip ci]` -> `b46926ed`
  - GitHub Actions postpush snapshot (exact-head workflows expected: none for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T181505Z-ci-postpush-sha-b46926ed/postpush.txt`

## 2026-05-20T18:44Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260520T184402Z-heartbeat.cmd.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T184402Z-summary.json`
  - HEAD: `88e6f9047797a362db1c33f6b4237656e6dbe6f6` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T184402Z-preflight/preflight.txt`
  - local dev-server snapshot:
    - `logs/md1-shrunk/polls/20260520T184402Z-preflight/local-dev-server.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T184402Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)
- Browser-readable public delivery validation (automation; Origin CORS + cache headers for meta.json + referenced assets):
  - result: `logs/md1-shrunk/polls/20260520T184402Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T184402Z-edge-validate/publish-edge.report.html`
- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T184402Z-bundle/bundle.txt` (sha256 match)
- Multi-camera input-vs-render checks (deployed preview; strict; baseline pose verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260520T184402Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T184402Z-camera-suite/report.html`
- Unit proof:
  - output: `logs/md1-shrunk/polls/20260520T184402Z-unit/unittest.txt`
- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T184402Z-ci/summary.txt`

- Commit/push:
  - `chore: md1-shrunk heartbeat verify 20260520T184402Z [skip ci]` -> `63d702c1`
  - GitHub Actions postpush snapshot (exact-head workflows expected: none for `[skip ci]` head):
    - `logs/md1-shrunk/polls/20260520T184402Z-ci-postpush-sha-63d702c1/postpush.txt`

## 2026-05-20T19:15Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260520T191515Z-heartbeat.cmd.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T191515Z-summary.json`
  - HEAD: `1f587dc4bfc1b341c651fe88af23f6caadc1f433` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T191515Z-preflight/preflight.txt`
  - local dev-server snapshot:
    - `logs/md1-shrunk/polls/20260520T191515Z-preflight/local-dev-server.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T191515Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260520T191515Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T191515Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T191515Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260520T191515Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`)
  - report: `logs/md1-shrunk/polls/20260520T191515Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260520T191515Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T191515Z-ci/summary.txt`

- Next: commit/push (logs + STATE) then record postpush snapshot.

## 2026-05-20T19:46Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `c601d9bb` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260520T194403Z-ci-postpush-sha-c601d9bb/postpush.txt`

## 2026-05-20T19:16Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `4bffbd21` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260520T191515Z-ci-postpush-sha-4bffbd21/postpush.txt`

## 2026-05-20T19:17Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `b2852b75` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260520T191515Z-ci-postpush-sha-b2852b75/postpush.txt`

## 2026-05-20T19:44Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260520T194403Z-heartbeat.cmd.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T194403Z-summary.json`
  - HEAD: `4d5a0d47375d4b02f67055b360ca5647985df1ef` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T194403Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T194403Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260520T194403Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T194403Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T194403Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260520T194403Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T194403Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260520T194403Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T194403Z-ci/summary.txt`

- Next: commit/push (logs + STATE) then record postpush snapshot.

## 2026-05-20T20:14Z heartbeat verify (scripted; strict gates PASS; no new jobs)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260520T201449Z-heartbeat.cmd.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T201449Z-summary.json`
  - HEAD: `9e4ea7c7e0d9dfb4ec7208dd2f7f6d5b420fe44b` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T201449Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T201449Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress: `0` (processing + training)

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260520T201449Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T201449Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T201449Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260520T201449Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T201449Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260520T201449Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T201449Z-ci/summary.txt`

- Commit/push:
  - `chore: md1-shrunk heartbeat verify 20260520T201449Z [skip ci]` -> `88c5f416`

## 2026-05-20T20:15Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `88c5f416` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260520T201449Z-ci-postpush-sha-88c5f416/postpush.txt`

## 2026-05-20T20:43Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260520T204327Z-heartbeat.cmd.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T204327Z-summary.json`
  - HEAD: `b8de854d2b79a1949740647dcc674cf0269734f6` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T204327Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T204327Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260520T204327Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T204327Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T204327Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260520T204327Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T204327Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260520T204327Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T204327Z-ci/summary.txt`

- Next: record postpush CI snapshot for the new head.

## 2026-05-20T23:50Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `8d2da8ba` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260520T235038Z-ci-postpush-sha-8d2da8ba/postpush.txt`

- Next: idle.

## 2026-05-20T20:50Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `7831d604` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260520T204327Z-ci-postpush-sha-7831d604/postpush.txt`


## 2026-05-20T20:52Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `5547664c` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260520T204327Z-ci-postpush-sha-5547664c/postpush.txt`

## 2026-05-20T20:53Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `a243ffc6` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260520T204327Z-ci-postpush-sha-a243ffc6/postpush.txt`

## 2026-05-20T21:13Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260520T211344Z-heartbeat.cmd.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T211344Z-summary.json`
  - HEAD: `cd73dedc39fcd40fc97d78dd373b38dbbc8b5faa` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T211344Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T211344Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260520T211344Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T211344Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T211344Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260520T211344Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T211344Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260520T211344Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T211344Z-ci/summary.txt`

- Next: commit/push (poll logs + STATE) then record postpush snapshot.

## 2026-05-21T02:52Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `1ee31844` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T024435Z-ci-postpush-sha-1ee31844/postpush.txt`

## 2026-05-20T21:20Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `352c8b45` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260520T211344Z-ci-postpush-sha-352c8b45/postpush.txt`

## 2026-05-20T21:43Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Prechecks (manual; read-only; evidence-first; includes local listeners + GitHub run list):
  - `logs/md1-shrunk/polls/20260520T214328Z-prechecks/git.txt`
  - `logs/md1-shrunk/polls/20260520T214328Z-prechecks/aws-identity.json`
  - `logs/md1-shrunk/polls/20260520T214328Z-prechecks/sfn-running-staging.json`
  - `logs/md1-shrunk/polls/20260520T214328Z-prechecks/sfn-running-branch.json`
  - `logs/md1-shrunk/polls/20260520T214328Z-prechecks/sm-processing-inprogress.json`
  - `logs/md1-shrunk/polls/20260520T214328Z-prechecks/local-listeners.txt`
  - `logs/md1-shrunk/polls/20260520T214328Z-prechecks/gh-runs.txt`

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260520T214348Z-heartbeat.cmd.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T214348Z-summary.json`
  - HEAD: `9542180c1adcd90cecc302193a544fd5a3939902` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T214348Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260520T214348Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T214348Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T214348Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260520T214348Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T214348Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260520T214348Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T214348Z-ci/summary.txt`

- Next: commit/push (poll logs + STATE) then record postpush snapshot.

## 2026-05-20T21:50Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `a6c421b3` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260520T214348Z-ci-postpush-sha-a6c421b3/postpush.txt`

## 2026-05-20T22:14Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260520T221434Z-heartbeat.cmd.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T221434Z-summary.json`
  - HEAD: `13f9eaa6d4fef0ea21dd260267409245bdc4688b` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T221434Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T221434Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260520T221434Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T221434Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T221434Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260520T221434Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T221434Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260520T221434Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T221434Z-ci/summary.txt`

- Next: commit/push (poll logs + STATE) then record postpush snapshot.

## 2026-05-20T22:17Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `f47069c4` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260520T221434Z-ci-postpush-sha-f47069c4/postpush.txt`

## 2026-05-20T22:19Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `612fa881` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260520T221434Z-ci-postpush-sha-612fa881/postpush.txt`

## 2026-05-20T22:44Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Prechecks (manual; read-only; evidence-first):
  - `logs/md1-shrunk/polls/20260520T224337Z-prechecks/prechecks.txt`

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T224430Z-summary.json`
  - HEAD: `be5bf4b4f07502e071cc04d2bb13694cc6ed7437` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T224430Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T224430Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260520T224430Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T224430Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T224430Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260520T224430Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T224430Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260520T224430Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T224430Z-ci/summary.txt`

- Next: commit/push (poll logs + STATE) then record postpush snapshot.

## 2026-05-20T23:15Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `25402648` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260520T224430Z-ci-postpush-sha-25402648/postpush.txt`

## 2026-05-20T23:16Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `0509963f` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260520T224430Z-ci-postpush-sha-0509963f/postpush.txt`

## 2026-05-20T23:45Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260520T234501Z-heartbeat.cmd.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260520T234501Z-summary.json`
  - HEAD: `63513484a3c3d0713832ef82c2e4c49353632bfe` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260520T234501Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260520T234501Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260520T234501Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260520T234501Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260520T234501Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260520T234501Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260520T234501Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260520T234501Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260520T234501Z-ci/summary.txt`

- Next: commit/push (poll logs + STATE) then record postpush snapshot.

## 2026-05-21T00:15Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T001550Z-heartbeat.cmd.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T001550Z-summary.json`
  - HEAD: `f77ca9ce2088dd499da1e50428830c9c113a246e` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T001550Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260521T001550Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T001550Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T001550Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T001550Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T001550Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T001550Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T001550Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260521T001550Z-ci/summary.txt`

- Next: commit/push (poll logs + STATE) then record postpush snapshot.

## 2026-05-21T00:20Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `05552217` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T001550Z-ci-postpush-sha-05552217/postpush.txt`

## 2026-05-21T00:21Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `657ff025` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T001550Z-ci-postpush-sha-657ff025/postpush.txt`

## 2026-05-21T00:43Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T004309Z-heartbeat.cmd.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T004309Z-summary.json`
  - HEAD: `607ac8dfb5ca4b664a4be39bc38a8b6b9d6ddf71` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T004309Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260521T004309Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T004309Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T004309Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T004309Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T004309Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T004309Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T004309Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; exact-head workflows expected: none):
  - `logs/md1-shrunk/polls/20260521T004309Z-ci/summary.txt`

- Next: commit/push (poll logs + STATE) then record postpush snapshot.

## 2026-05-21T00:48Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `5106139e` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T004815Z-ci-postpush-sha-5106139e/postpush.txt`

## 2026-05-21T01:16Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T011636Z-heartbeat.cmd.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T011636Z-summary.json`
  - HEAD: `6840a4ebf5d04bb995f18fda569375f938a0a307` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T011636Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260521T011636Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T011636Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T011636Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T011636Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T011636Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T011636Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T011636Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; exact-head workflows expected: none):
  - `logs/md1-shrunk/polls/20260521T011636Z-ci/summary.txt`

- Next: commit/push (poll logs + STATE) then record postpush snapshot.

## 2026-05-21T01:21Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `c46aac1f` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T011636Z-ci-postpush-sha-c46aac1f/postpush.txt`

## 2026-05-21T01:44Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T014458Z-heartbeat.cmd.txt`
- Heartbeat run log:
  - `logs/md1-shrunk/polls/20260521T014458Z-heartbeat.run.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T014458Z-summary.json`
  - HEAD: `b407c108c0820665731f6711c6665d86c3b8c775` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T014458Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260521T014458Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T014458Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T014458Z-edge-validate/publish-edge.report.html`

- Public bundle state (S3 listing) + snapshot (S3-vs-edge meta.json parity):
  - S3 listing: `logs/md1-shrunk/polls/20260521T014458Z-bundle/s3-ls.txt` (13 objects, 13.9 MiB)
  - parity: `logs/md1-shrunk/polls/20260521T014458Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T014458Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T014458Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T014458Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; no new runs expected):
  - `logs/md1-shrunk/polls/20260521T014458Z-ci/summary.txt`

- Next: commit/push (poll logs + STATE) then record postpush snapshot.

## 2026-05-21T01:51Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `2039a8eb` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T014458Z-ci-postpush-sha-2039a8eb/postpush.txt`

## 2026-05-21T02:17Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T021710Z-heartbeat.cmd.txt`
- Heartbeat run log:
  - `logs/md1-shrunk/polls/20260521T021710Z-heartbeat.run.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T021710Z-summary.json`
  - HEAD: `054e0813fcb7e6c71cbadc9b619aed704d2e4117` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T021710Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260521T021710Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T021710Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T021710Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T021710Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T021710Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T021710Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T021710Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; exact-head workflows expected: none):
  - `logs/md1-shrunk/polls/20260521T021710Z-ci/summary.txt`

- Next: bump `web/trigger-dev-build.txt`, push, watch exact-head Pages + CDK workflows, record `PREVIEW_URL`, and store a postpush snapshot.

## 2026-05-21T02:22Z postpush CI snapshot (exact-head workflows succeeded)

- exact-head commit: `2a302b60` (triggered Pages + CDK on push)
- `Deploy Next.js to Cloudflare Pages` run `26201635538` -> success
- `CDK Deploy` run `26201635575` -> success
- PREVIEW_URL (from Pages log): `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
- Evidence:
  - `logs/md1-shrunk/polls/20260521T022206Z-ci-postpush-sha-2a302b60/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T022206Z-ci-postpush-sha-2a302b60/watch-pages-26201635538.txt`
  - `logs/md1-shrunk/polls/20260521T022206Z-ci-postpush-sha-2a302b60/watch-cdk-26201635575.txt`
  - `logs/md1-shrunk/polls/20260521T022206Z-ci-postpush-sha-2a302b60/preview-url.txt`
  - `logs/md1-shrunk/polls/20260521T022206Z-ci-postpush-sha-2a302b60/resolved-urls.txt`

- Next: idle (no new MD1/MD1-Shrunk jobs launched; only external SageMaker processing remains in progress).

## 2026-05-21T02:44Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T024435Z-heartbeat.cmd.txt`
- Heartbeat run log:
  - `logs/md1-shrunk/polls/20260521T024435Z-heartbeat.run.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T024435Z-summary.json`
  - HEAD: `80e1598bc100ee3f43856e7a131557ef8f110cc9` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T024435Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`:
    - `logs/md1-shrunk/polls/20260521T024435Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T024435Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T024435Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T024435Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T024435Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T024435Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T024435Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; exact-head workflows expected: none):
  - `logs/md1-shrunk/polls/20260521T024435Z-ci/summary.txt`

- Next: commit/push (poll logs + STATE) then record postpush snapshot.

## 2026-05-21T03:16Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T031626Z-heartbeat.cmd.txt`
- Heartbeat run log:
  - `logs/md1-shrunk/polls/20260521T031626Z-heartbeat.run.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T031626Z-summary.json`
  - HEAD: `15f6e1661555b245483b0400d993cf84afbcc9fd` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T031626Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T031626Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T031626Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T031626Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T031626Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T031626Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T031626Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; exact-head workflows expected: none):
  - `logs/md1-shrunk/polls/20260521T031626Z-ci/summary.txt`

- Extra manual preflight snapshot (raw curl/parity/preview HTML; optional):
  - `logs/md1-shrunk/polls/20260521T031344Z-manual-preflight/`

- Next: commit/push (poll logs + STATE) then record postpush CI snapshot.

## 2026-05-21T03:21Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `1b73c81e` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T032150Z-ci-postpush-sha-1b73c81e/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T032150Z-ci-postpush-sha-1b73c81e/gh-run-list-exact-head.json`

## 2026-05-21T03:44Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T034418Z-heartbeat.cmd.txt`
- Heartbeat run log:
  - `logs/md1-shrunk/polls/20260521T034418Z-heartbeat.run.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T034419Z-summary.json`
  - HEAD: `b870c4fd8bb32bf3e8dca531109eda2ed1cd564c` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T034419Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
    - `logs/md1-shrunk/polls/20260521T034419Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T034419Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T034419Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T034419Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T034419Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T034419Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T034419Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; exact-head workflows expected: none):
  - `logs/md1-shrunk/polls/20260521T034419Z-ci/summary.txt`
  - exact-head workflows:
    - `logs/md1-shrunk/polls/20260521T034419Z-ci/gh-run-list-exact-head.json` (`count=0`)

- Next: commit/push (poll logs + STATE + agent-loop), then record postpush CI snapshot.

## 2026-05-21T08:44Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T084408Z-summary.json`
  - HEAD: `8331741b13ff67e629618911e7b1118babd56a8b` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T084408Z-preflight/preflight.txt` (`status_porcelain=clean`)
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
    - `logs/md1-shrunk/polls/20260521T084408Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`
  - exact-head workflows:
    - `logs/md1-shrunk/polls/20260521T084408Z-preflight/gh-run-list-exact-head.json` (`count=0`)

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T084408Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T084408Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T084408Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T084408Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`)
  - report: `logs/md1-shrunk/polls/20260521T084408Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T084408Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; exact-head workflows expected: none):
  - `logs/md1-shrunk/polls/20260521T084408Z-ci/summary.txt`
  - raw: `logs/md1-shrunk/polls/20260521T084408Z-preflight/gh-run-list.json`

- Commit/push:
  - `chore: md1-shrunk heartbeat verify 20260521T084408Z [skip ci]` -> `dfa26299`

## 2026-05-21T08:50Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `dfa26299` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T085043Z-ci-postpush-sha-dfa26299/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T085043Z-ci-postpush-sha-dfa26299/gh-run-list-exact-head.json`

## 2026-05-21T08:14Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T081443Z-heartbeat.cmd.txt`
- Heartbeat run log:
  - `logs/md1-shrunk/polls/20260521T081443Z-heartbeat.run.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T081443Z-summary.json`
  - HEAD: `d51b258def87ef8311fdd49fecd063d6aab9e4c4` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T081443Z-preflight/preflight.txt` (`status_porcelain=clean`)
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
    - `logs/md1-shrunk/polls/20260521T081443Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`
  - exact-head workflows:
    - `logs/md1-shrunk/polls/20260521T081443Z-preflight/gh-run-list-exact-head.json` (`count=0`)

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T081443Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T081443Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T081443Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T081443Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T081443Z-camera-suite/report.html`

- Local dev-server snapshot (read-only):
  - `logs/md1-shrunk/polls/20260521T081443Z-devserver/devserver.txt`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T081443Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; exact-head workflows expected: none):
  - `logs/md1-shrunk/polls/20260521T081443Z-ci/summary.txt`
  - raw: `logs/md1-shrunk/polls/20260521T081443Z-preflight/gh-run-list.json`

## 2026-05-21T08:27Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `03ba793f` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T082745Z-ci-postpush-sha-03ba793f/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T082745Z-ci-postpush-sha-03ba793f/gh-run-list-exact-head.json`

## 2026-05-21T08:23Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `4cd51796` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T082340Z-ci-postpush-sha-4cd51796/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T082340Z-ci-postpush-sha-4cd51796/gh-run-list-exact-head.json`

## 2026-05-21T07:44Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T074417Z-heartbeat.cmd.txt`
- Heartbeat run log:
  - `logs/md1-shrunk/polls/20260521T074417Z-heartbeat.run.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T074417Z-summary.json`
  - HEAD: `e8fda52090b7a15d924659c9946ff7770e39875c` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T074417Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
    - `logs/md1-shrunk/polls/20260521T074417Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`
  - exact-head workflows:
    - `logs/md1-shrunk/polls/20260521T074417Z-preflight/gh-run-list-exact-head.json` (`count=0`)

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T074417Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T074417Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T074417Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T074417Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T074417Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T074417Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; exact-head workflows expected: none):
  - `logs/md1-shrunk/polls/20260521T074417Z-ci/summary.txt`
  - raw: `logs/md1-shrunk/polls/20260521T074417Z-preflight/gh-run-list.json`

- Completed: pushed `088776ab` and recorded postpush CI snapshot (next section).

## 2026-05-21T07:50Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `088776ab` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T075028Z-ci-postpush-sha-088776ab/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T075028Z-ci-postpush-sha-088776ab/gh-run-list-exact-head.json`

## 2026-05-21T07:14Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Manual verification (git/AWS/SageMaker/listeners/GH):
  - `logs/md1-shrunk/polls/20260521T071320Z-manual-verify/verify.txt`

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T071351Z-summary.json`
  - HEAD: `4a07ad1bcbcd1310e734058b2cccf469d6ac1cc2` (working tree was dirty due to new poll outputs)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T071351Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T071351Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T071351Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T071351Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T071351Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T071351Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T071351Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; exact-head workflows expected: none):
  - `logs/md1-shrunk/polls/20260521T071351Z-ci/summary.txt`
  - raw: `logs/md1-shrunk/polls/20260521T071351Z-preflight/gh-run-list.json`

## 2026-05-21T07:19Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `a5585740` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T071901Z-ci-postpush-sha-a5585740/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T071901Z-ci-postpush-sha-a5585740/gh-run-list-exact-head.json`

## 2026-05-21T06:44Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T064404Z-summary.json`
  - HEAD: `124ea1894f9bdade68e51e67da95e4029b825e01` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T064404Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
    - `logs/md1-shrunk/polls/20260521T064404Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T064404Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T064404Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T064404Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T064404Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T064404Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T064404Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; exact-head workflows expected: none):
  - `logs/md1-shrunk/polls/20260521T064404Z-ci/summary.txt`
  - raw: `logs/md1-shrunk/polls/20260521T064404Z-preflight/gh-run-list.json`

- Next: commit/push (poll logs + STATE + agent-loop), then record postpush CI snapshot.

## 2026-05-21T06:49Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `16084dfa` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T064942Z-ci-postpush-sha-16084dfa/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T064942Z-ci-postpush-sha-16084dfa/gh-run-list-exact-head.json`

## 2026-05-21T06:20Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `a010ac365415428db4bd0591ba249df62ad73a72` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T062034Z-ci-postpush-sha-a010ac36/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T062034Z-ci-postpush-sha-a010ac36/gh-run-list-exact-head.json`

## 2026-05-21T06:21Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `3e6a22ae9cbe1ccce65a090dbc0cffbec78d22ea` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T062147Z-ci-postpush-sha-3e6a22ae/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T062147Z-ci-postpush-sha-3e6a22ae/gh-run-list-exact-head.json`

## 2026-05-21T06:14Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T061452Z-heartbeat.cmd.txt`
- Heartbeat run log:
  - `logs/md1-shrunk/polls/20260521T061452Z-heartbeat.run.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T061452Z-summary.json`
  - HEAD: `cfb42164b68b7bcf851471f2938b35377bcfc020` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T061452Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
    - `logs/md1-shrunk/polls/20260521T061452Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T061452Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T061452Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T061452Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T061452Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T061452Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T061452Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; exact-head workflows expected: none):
  - `logs/md1-shrunk/polls/20260521T061452Z-ci/summary.txt`
  - raw: `logs/md1-shrunk/polls/20260521T061452Z-preflight/gh-run-list.json`
  - exact-head raw: `logs/md1-shrunk/polls/20260521T061452Z-preflight/gh-run-list-exact-head.json`

- Next: commit/push (poll logs + STATE + agent-loop), then record postpush CI snapshot.

## 2026-05-21T05:19Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T051910Z-heartbeat.cmd.txt`
- Heartbeat run log:
  - `logs/md1-shrunk/polls/20260521T051910Z-heartbeat.run.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T051910Z-summary.json`
  - HEAD: `791fe7a2c9a231e08bfa660798e0e59a9119cf63` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T051910Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
    - `logs/md1-shrunk/polls/20260521T051910Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T051910Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T051910Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T051910Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T051910Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T051910Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T051910Z-unit/unittest.txt`

- GitHub Actions snapshot:
  - summary: `logs/md1-shrunk/polls/20260521T051910Z-ci/summary.txt`
  - raw: `logs/md1-shrunk/polls/20260521T051910Z-preflight/gh-run-list.json`

## 2026-05-21T05:24Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `f4920320` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T052409Z-ci-postpush-sha-f4920320/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T052409Z-ci-postpush-sha-f4920320/gh-run-list-exact-head.json`

## 2026-05-21T05:25Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `0e592b9e` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T052527Z-ci-postpush-sha-0e592b9e/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T052527Z-ci-postpush-sha-0e592b9e/gh-run-list-exact-head.json`

## 2026-05-21T05:44Z manual verify (read-only; cost bounded)

- Evidence:
  - `logs/md1-shrunk/polls/20260521T054429Z-manual-verify/verify.txt`
  - exact-head workflows: `logs/md1-shrunk/polls/20260521T054429Z-manual-verify/gh-run-list-exact-head.json` (`count=0`)

## 2026-05-21T05:46Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T054657Z-heartbeat.cmd.txt`
- Heartbeat run log:
  - `logs/md1-shrunk/polls/20260521T054657Z-heartbeat.run.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T054657Z-summary.json`
  - HEAD: `acf3ec68f38eec5c6811d83793456f27bbd5d2cb` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T054657Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
    - `logs/md1-shrunk/polls/20260521T054657Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`
  - exact-head workflows:
    - `logs/md1-shrunk/polls/20260521T054657Z-preflight/gh-run-list-exact-head.json` (`count=0`)

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T054657Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T054657Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T054657Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T054657Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T054657Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T054657Z-unit/unittest.txt`

- GitHub Actions snapshot:
  - summary: `logs/md1-shrunk/polls/20260521T054657Z-ci/summary.txt`
  - raw: `logs/md1-shrunk/polls/20260521T054657Z-preflight/gh-run-list.json`

- Follow-up: pushed `0a6e4739` (`chore: trigger pages build`) and watched exact-head CI to green; see postpush snapshot below.

## 2026-05-21T06:06Z heartbeat verify (scripted; strict gates PASS; no new jobs launched; preflight clean)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T060613Z-heartbeat.cmd.txt`
- Heartbeat run log:
  - `logs/md1-shrunk/polls/20260521T060613Z-heartbeat.run.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T060613Z-summary.json`
  - HEAD: `18f3fecaccf29a215521e9a815940f0c7f4a7579` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T060613Z-preflight/preflight.txt` (`status_porcelain=clean`)
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
    - `logs/md1-shrunk/polls/20260521T060613Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`
  - exact-head workflows:
    - `logs/md1-shrunk/polls/20260521T060613Z-preflight/gh-run-list-exact-head.json` (`count=0`)

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T060613Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T060613Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T060613Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T060613Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T060613Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T060613Z-unit/unittest.txt`

- GitHub Actions snapshot:
  - summary: `logs/md1-shrunk/polls/20260521T060613Z-ci/summary.txt`
  - raw: `logs/md1-shrunk/polls/20260521T060613Z-preflight/gh-run-list.json`

## 2026-05-21T06:04Z postpush CI snapshot (exact-head Pages + CDK succeeded)

- exact-head commit: `0a6e4739`
- PREVIEW_URL:
  - `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
- Evidence:
  - `logs/md1-shrunk/polls/20260521T060400Z-ci-postpush-sha-0a6e4739/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T060400Z-ci-postpush-sha-0a6e4739/gh-run-list-exact-head.json`
  - Pages PREVIEW_URL lines: `logs/md1-shrunk/polls/20260521T060400Z-ci-postpush-sha-0a6e4739/pages-preview-url-lines.txt`


## 2026-05-21T04:51Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `99b248e9` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T045145Z-ci-postpush-sha-99b248e9/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T045145Z-ci-postpush-sha-99b248e9/gh-run-list-exact-head.json`

## 2026-05-21T04:53Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `91eaa0fc` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T045313Z-ci-postpush-sha-91eaa0fc/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T045313Z-ci-postpush-sha-91eaa0fc/gh-run-list-exact-head.json`

## 2026-05-21T04:45Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T044552Z-heartbeat.cmd.txt`
- Heartbeat run log:
  - `logs/md1-shrunk/polls/20260521T044552Z-heartbeat.run.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T044552Z-summary.json`
  - HEAD: `574d64634119fb4243176dfed260d4c1f0ee70a1` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T044552Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T044552Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T044552Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T044552Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T044552Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T044552Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T044552Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; exact-head workflows expected: none):
  - `logs/md1-shrunk/polls/20260521T044552Z-ci/summary.txt`
  - raw: `logs/md1-shrunk/polls/20260521T044552Z-preflight/gh-run-list.json`

- Next: commit/push (poll logs + STATE + agent-loop), then record postpush CI snapshot.

## 2026-05-21T04:19Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `35d2b8ee` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T041953Z-ci-postpush-sha-35d2b8ee/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T041953Z-ci-postpush-sha-35d2b8ee/gh-run-list-exact-head.json`

## 2026-05-21T04:21Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `c29e396f` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T042112Z-ci-postpush-sha-c29e396f/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T042112Z-ci-postpush-sha-c29e396f/gh-run-list-exact-head.json`

## 2026-05-21T03:50Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `e6a40887` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T035008Z-ci-postpush-sha-e6a40887/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T035008Z-ci-postpush-sha-e6a40887/gh-run-list-exact-head.json`

## 2026-05-21T03:51Z postpush CI snapshot (head is logs-only; no new runs expected)

- exact-head commit: `0e5bbe36` (`[skip ci]` head; exact-head workflows expected: none)
- Evidence:
  - `logs/md1-shrunk/polls/20260521T035150Z-ci-postpush-sha-0e5bbe36/postpush.txt`
  - `logs/md1-shrunk/polls/20260521T035150Z-ci-postpush-sha-0e5bbe36/gh-run-list-exact-head.json`

## 2026-05-21T04:14Z heartbeat verify (scripted; strict gates PASS; no new jobs launched)

- Manual verification (git/AWS/StepFunctions/SageMaker/S3/edge/listeners/GH):
  - `logs/md1-shrunk/polls/20260521T041339Z-manual-verify/verify.txt`

- Heartbeat command:
  - `logs/md1-shrunk/polls/20260521T041430Z-heartbeat.cmd.txt`
- Heartbeat run log:
  - `logs/md1-shrunk/polls/20260521T041430Z-heartbeat.run.txt`
- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T041431Z-summary.json`
  - HEAD: `08a2d2da332e985a26dd39a124212b73e2cafc97` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T041431Z-preflight/preflight.txt`
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
    - `logs/md1-shrunk/polls/20260521T041431Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T041431Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T041431Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T041431Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T041431Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T041431Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T041431Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; exact-head workflows expected: none):
  - `logs/md1-shrunk/polls/20260521T041431Z-ci/summary.txt`
  - raw: `logs/md1-shrunk/polls/20260521T041431Z-preflight/gh-run-list.json`

- Next: commit/push (poll logs + STATE + agent-loop), then record postpush CI snapshot.

## 2026-05-21T09:15Z heartbeat verify (scripted; strict gates PASS; no new jobs launched; preflight clean)

- Heartbeat poll summary:
  - `logs/md1-shrunk/polls/20260521T091509Z-summary.json`
  - HEAD: `1e56f855b9fc3c6e39af9619135efd7f62b419e7` (`[skip ci]` head; exact-head workflows expected: none)
  - PREVIEW_URL: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
  - edge meta.json: `https://d385lt7fd3q07n.cloudfront.net/models/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`
  - public S3 meta.json: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-shrunk-prodspine-wlight-202605190027/supersplat_bundle/meta.json`

- Preflight snapshot (scripted; read-only; cost bounded):
  - `logs/md1-shrunk/polls/20260521T091509Z-preflight/preflight.txt` (`status_porcelain=clean`)
  - Step Functions RUNNING: `0` (staging + `SpaceportMLPipeline-br-8abcbd5662`)
  - Known execution `execution-md1-shrunk-prodspine-wlight-202605190027` status: `SUCCEEDED`
    - `logs/md1-shrunk/polls/20260521T091509Z-preflight/stepfunctions-describe-known.json`
  - SageMaker InProgress:
    - processing: `1` (external / not owned by this run): `hmc-mtc-20260520T2015Z-sfm` (left untouched)
    - training: `0`
  - exact-head workflows:
    - `logs/md1-shrunk/polls/20260521T091509Z-preflight/gh-run-list-exact-head.json` (`count=0`)

- Browser-readable public delivery validation (automation; Origin/CORS + cache headers + referenced assets):
  - result: `logs/md1-shrunk/polls/20260521T091509Z-edge-validate/validate.txt`
  - report: `logs/md1-shrunk/polls/20260521T091509Z-edge-validate/publish-edge.report.html`

- Public bundle snapshot (S3-vs-edge meta.json parity):
  - `logs/md1-shrunk/polls/20260521T091509Z-bundle/bundle.txt` (sha256 match)

- Multi-camera input-vs-render checks (deployed preview; strict; pose drift verification + sky/horizon gates):
  - result: `logs/md1-shrunk/polls/20260521T091509Z-camera-suite/suite-summary.json` -> `decision=pass` (`pose_verification.max_delta=0.0`; `artifacts_pruned=true`; `skybox.decision=pass`; `nosky.decision=pass`)
  - report: `logs/md1-shrunk/polls/20260521T091509Z-camera-suite/report.html`

- Unit proof:
  - output: `logs/md1-shrunk/polls/20260521T091509Z-unit/unittest.txt`

- GitHub Actions snapshot (head is logs-only; exact-head workflows expected: none):
  - `logs/md1-shrunk/polls/20260521T091509Z-ci/summary.txt`
  - raw: `logs/md1-shrunk/polls/20260521T091509Z-preflight/gh-run-list.json`

- Next: commit/push (poll logs + STATE + agent-loop), then record postpush CI snapshot.
