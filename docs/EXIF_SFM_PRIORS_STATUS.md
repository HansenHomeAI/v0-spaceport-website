# EXIF SfM Priors (OpenSfM) - Status / Resume Guide

This repo contains an SfM container (`infrastructure/containers/sfm/`) that runs OpenSfM and exports COLMAP outputs for downstream 3DGS. The current goal is to use drone image metadata (EXIF GPS and best-effort gimbal fields) as **priors** to improve orientation/origin consistency and reconstruction robustness, especially when no external GPS flight-path CSV is available.

## Current Branch

- Working branch: `agent-60210437-exif-sfm-exifonly`
- Cloudflare preview (branch): `https://agent-60210437-exif-sfm-exif.v0-spaceport-website-preview2.pages.dev`

## What Was Implemented (Key Points)

### 1) EXIF-only priors fallback (SfM container)

When **no GPS CSV** is present, the SfM container attempts an **EXIF-only prior build**:

- Reads EXIF GPS (lat/lon and altitude when present) from input images
- Orders images by EXIF timestamp when available
- Generates OpenSfM priors files into the OpenSfM workspace (e.g. `gps_priors.json`, `reference_lla.json`, etc.)
- Writes `sfm_metadata.json` fields so the pipeline can confirm priors were used:
  - `gps_enhanced: true`
  - `priors_source: "exif"`
  - `priors_summary: { ... }`

Primary files:

- `infrastructure/containers/sfm/gps_processor_3d.py`
- `infrastructure/containers/sfm/run_opensfm_gps.py`
- `infrastructure/containers/sfm/run_sfm.sh`

### 2) SfM-only pipeline termination (`pipelineStopAfter`)

We kept the existing meaning of `pipelineStep` (start-at semantics), and added **`pipelineStopAfter`** to allow early termination:

- `pipelineStopAfter="sfm"` ends after SfM completes (`SfmOnlyComplete`)
- `pipelineStopAfter="3dgs"` ends after 3DGS completes (`GaussianOnlyComplete`)

Primary files:

- `infrastructure/spaceport_cdk/lambda/start_ml_job/lambda_function.py`
- `infrastructure/spaceport_cdk/spaceport_cdk/ml_pipeline_stack.py`

### 3) Container build reliability

Changes were made to ensure the SfM container rebuild path works via GitHub Actions -> CodeBuild:

- Container build workflow triggers on `agent-*` branches
- CodeBuild DockerHub login is conditional (won't fail when creds are unset)
- SfM Dockerfile base image moved to ECR Public to avoid DockerHub pull rate limits

Primary files:

- `.github/workflows/build-containers.yml`
- `buildspec.yml`
- `infrastructure/containers/sfm/Dockerfile`

## Running / Verifying an SfM-only EXIF Job

### Most recent execution (staging)

Successful validation run:

- Job ID:
  - `a1ae35f1-d56e-464d-8d2a-b3b5e4152c8a`
- Step Functions execution:
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-a1ae35f1-d56e-464d-8d2a-b3b5e4152c8a`
- SageMaker processing job:
  - `ml-job-20260210-064635-a1ae35f1-sfm`
- Output prefix:
  - `s3://spaceport-ml-processing-staging/colmap/a1ae35f1-d56e-464d-8d2a-b3b5e4152c8a/`

Outcome:

- Step Functions ended at `SfmOnlyComplete` (validating `pipelineStopAfter="sfm"`).
- `sfm_metadata.json` confirms `priors_source: "exif"` and `gps_enhanced: true` (97/97 images had EXIF GPS).

Prior attempt (same dataset) produced correct SfM outputs but the processing job was marked failed due to a bash quoting bug after SfM completed; this was fixed in `infrastructure/containers/sfm/run_sfm.sh`.

### Verification checklist (after completion)

1. Confirm Step Functions ended where expected (no 3DGS/compression):

```bash
EXEC_ARN='arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-2fcf68f2-2fa3-4ba7-953b-1c7afc55d75b'
aws stepfunctions describe-execution --execution-arn "$EXEC_ARN" --region us-west-2 --query status --output text
```

2. Confirm output exists, then inspect metadata:

```bash
OUT='s3://spaceport-ml-processing-staging/colmap/2fcf68f2-2fa3-4ba7-953b-1c7afc55d75b/'
aws s3 ls "$OUT"
aws s3 cp "${OUT}sfm_metadata.json" - | jq .
```

Expect:

- `gps_enhanced == true`
- `priors_source == "exif"`
- `priors_summary.ok == true`

## Notes / Known Risks

- OpenSfM `reconstruct` can be the longest stage; if it stalls, add more visibility (streaming stdout/stderr) or per-step timeouts in `infrastructure/containers/sfm/run_opensfm_gps.py`.
- EXIF gimbal fields are parsed best-effort (DJI XMP variants) and currently stored mainly for debugging, not as hard constraints.
