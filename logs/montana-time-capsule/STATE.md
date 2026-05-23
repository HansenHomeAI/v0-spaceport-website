# Montana Time Capsule CV-HR State

## Branch

- Branch: `agent-40136728-montana-time-capsule`
- Purpose: preserve and run the exact Montana-era training stack for CV-HR without inheriting later pipeline/container changes.

## 2026-05-23T19:29:43Z HEARTBEAT monitor (HMC) - no-spend reconfirm: git clean + AWS identity + canonical SageMaker jobs still Completed + S3 supersplat bundle still present + viewer skybox/no-sky HTTP 200 + signed meta.json via `/api/sogs-proxy` HTTP 200 (exact-head empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ c333b7af32a84e2a1b2d91a6dea1110aa7c341a6 ([skip ci]) (clean)
- AWS (us-west-2; aws=/opt/homebrew/bin/aws):
  - identity: logs/montana-time-capsule/aws-sts-20260523T192253Z.json
  - region: logs/montana-time-capsule/aws-region-20260523T192253Z.txt
  - version: logs/montana-time-capsule/aws-version-20260523T192253Z.txt (binary=logs/montana-time-capsule/aws-binary-20260523T192253Z.txt)
- SageMaker (canonical HMC jobs still Completed; do not launch duplicate HMC jobs; do not stop other automations):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T192253Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T192253Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T192253Z.json
  - InProgress processing jobs (non-HMC): logs/montana-time-capsule/sagemaker-list-processing-inprogress-20260523T192253Z.json
  - InProgress training jobs: logs/montana-time-capsule/sagemaker-list-training-inprogress-20260523T192253Z.json
- S3 (supersplat bundle present): logs/montana-time-capsule/s3-ls-recursive-supersplat_bundle-20260523T192838Z.txt (meta head=logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260523T192838Z.json; skybox head=logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260523T192838Z.json)
- Hosted preview viewer reachability (HTTP 200):
  - skybox: logs/montana-time-capsule/curlI-viewer-skybox-20260523T192838Z.headers (url=logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T192838Z.txt)
  - no-sky: logs/montana-time-capsule/curlI-viewer-nosky-20260523T192838Z.headers (url=logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T192838Z.txt)
- Signed bundle meta.json reachability (canonical; `/api/sogs-proxy`; HTTP 200; A-C-A-Origin=*): logs/montana-time-capsule/curlI-sogs-proxy-meta-20260523T192838Z.headers (url=logs/montana-time-capsule/heartbeat-sogs-proxy-meta-url-20260523T192838Z.txt; body-head=logs/montana-time-capsule/curl-sogs-proxy-meta-head-20260523T192838Z.txt; origin-check=logs/montana-time-capsule/curlI-sogs-proxy-meta-origin-20260523T192922Z.headers)
- CI snapshot:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T192943Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T192943Z.json

## 2026-05-23T19:34:17Z postpush CI snapshot (exact-head expected empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ a21096859f9b1047604044e4d194b09ea0fd533f ([skip ci]) (pushed)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T193417Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T193417Z.json

## 2026-05-23T19:02:50Z HEARTBEAT monitor (HMC) - no-spend reconfirm: AWS identity + SageMaker terminal (HMC jobs Completed) + S3 bundle present + viewer skybox/no-sky HTTP 200 + signed meta.json via `/api/sogs-proxy` HTTP 200 (exact-head empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ 6bea9fb6046ddcf1fdcf9d7048db8b0f73d12d11 ([skip ci]) (clean)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T190250Z.json (region=logs/montana-time-capsule/aws-region-20260523T190250Z.txt; cli=logs/montana-time-capsule/aws-version-20260523T190250Z.txt)
- SageMaker (canonical HMC jobs Completed; do not stop other automations):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T190250Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T190250Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T190250Z.json
  - InProgress processing jobs (non-HMC): logs/montana-time-capsule/sagemaker-list-processing-inprogress-20260523T190250Z.json
  - InProgress training jobs: logs/montana-time-capsule/sagemaker-list-training-inprogress-20260523T190250Z.json
- S3 (supersplat bundle present): logs/montana-time-capsule/s3-ls-recursive-supersplat_bundle-20260523T190250Z.txt (meta head=logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260523T190250Z.json; skybox head=logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260523T190250Z.json)
- Hosted preview viewer reachability (Origin header set; HTTP 200):
  - skybox: logs/montana-time-capsule/curlI-viewer-skybox-20260523T190250Z.headers (url=logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T190250Z.txt)
  - no-sky: logs/montana-time-capsule/curlI-viewer-nosky-20260523T190250Z.headers (url=logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T190250Z.txt)
- Signed bundle meta.json reachability (canonical; `/api/sogs-proxy`; HTTP 200): logs/montana-time-capsule/curlI-sogs-proxy-meta-20260523T190250Z.headers (url=logs/montana-time-capsule/heartbeat-sogs-proxy-meta-url-20260523T190250Z.txt; body-head=logs/montana-time-capsule/curl-sogs-proxy-meta-head-20260523T190250Z.txt)
- CI snapshot:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T190250Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T190250Z.json

## 2026-05-23T19:04:56Z postpush CI snapshot (exact-head expected empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ 73b545c7c6d2a1d2a3d521b95d1f8df73c4e6914 ([skip ci]) (pushed)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T190456Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T190456Z.json

## 2026-05-23T19:05:53Z postpush CI snapshot (exact-head expected empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ 584c795ccef9b2fdb2fa1655c1e498b44df33161 ([skip ci]) (pushed)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T190553Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T190553Z.json

## 2026-05-23T18:23:52Z HEARTBEAT monitor (HMC) - no-spend reconfirm: AWS identity + SageMaker terminal (HMC jobs Completed) + S3 bundle present + viewer skybox/no-sky HTTP 200 + signed meta.json via `/api/sogs-proxy` HTTP 200 (exact-head empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ a6e8fb6a58f09a9927e900839ab5daa07b2e0f5d ([skip ci]) (dirty=untracked logs only)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T182352Z.json (region=logs/montana-time-capsule/aws-region-20260523T182352Z.txt; cli=logs/montana-time-capsule/aws-version-20260523T182352Z.txt)
- SageMaker (canonical HMC jobs Completed; do not stop other automations):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T182352Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T182352Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T182352Z.json
  - InProgress processing jobs (non-HMC): logs/montana-time-capsule/sagemaker-list-processing-inprogress-20260523T182352Z.json
  - InProgress training jobs: logs/montana-time-capsule/sagemaker-list-training-inprogress-20260523T182352Z.json
- S3 (supersplat bundle present): logs/montana-time-capsule/s3-ls-recursive-supersplat_bundle-20260523T182352Z.txt (meta head=logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260523T182352Z.json; skybox head=logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260523T182352Z.json)
- Hosted preview viewer reachability (Origin header set; HTTP 200):
  - skybox: logs/montana-time-capsule/curlI-viewer-skybox-20260523T182352Z.headers (url=logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T182352Z.txt)
  - no-sky: logs/montana-time-capsule/curlI-viewer-nosky-20260523T182352Z.headers (url=logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T182352Z.txt)
- Signed bundle meta.json reachability (canonical; `/api/sogs-proxy`; HTTP 200): logs/montana-time-capsule/curlI-sogs-proxy-meta-20260523T182352Z.headers (url=logs/montana-time-capsule/heartbeat-sogs-proxy-meta-url-20260523T182352Z.txt; body-head=logs/montana-time-capsule/curl-sogs-proxy-meta-head-20260523T182352Z.txt)
- CI snapshot:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T182352Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T182352Z.json

## 2026-05-23T18:25:50Z postpush CI snapshot (exact-head expected empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ 7bea439a28ab11a52d77f131fd7f13eadcd18b80 ([skip ci]) (pushed)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T182550Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T182550Z.json

## 2026-05-23T18:04:37Z HEARTBEAT monitor (HMC) - no-spend reconfirm: AWS identity + SageMaker terminal (HMC jobs Completed) + S3 bundle present + viewer skybox/no-sky HTTP 200 + signed meta.json via `/api/sogs-proxy` HTTP 200 (exact-head empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ 863661d5fd6722641e1e88d6a2b56a6841adfe36 ([skip ci]) (dirty=untracked logs only)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T180303Z.json (region=logs/montana-time-capsule/aws-region-20260523T180303Z.txt; cli=logs/montana-time-capsule/aws-version-20260523T180303Z.txt)
- SageMaker (canonical HMC jobs Completed; do not stop other automations):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T180303Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T180303Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T180303Z.json
  - InProgress processing jobs (non-HMC): logs/montana-time-capsule/sagemaker-list-processing-inprogress-20260523T180303Z.json (cvhr-globalprior-full-l03/l04)
- S3 (supersplat bundle present): logs/montana-time-capsule/s3-ls-recursive-supersplat_bundle-20260523T180323Z.txt (meta head=logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260523T180323Z.json; skybox head=logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260523T180323Z.json)
- Hosted preview viewer reachability (Origin header set; HTTP 200):
  - skybox: logs/montana-time-capsule/curlI-viewer-skybox-20260523T180337Z.headers (url=logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T180337Z.txt)
  - no-sky: logs/montana-time-capsule/curlI-viewer-nosky-20260523T180337Z.headers (url=logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T180337Z.txt)
- Signed bundle meta.json reachability (canonical; `/api/sogs-proxy`; HTTP 200): logs/montana-time-capsule/curlI-sogs-proxy-meta-20260523T180421Z.headers (url=logs/montana-time-capsule/heartbeat-sogs-proxy-meta-url-20260523T180421Z.txt; body-head=logs/montana-time-capsule/curl-sogs-proxy-meta-head-20260523T180437Z.txt)
- Note: legacy `/api/proxy/...` path is not a valid route in this branch preview (404): logs/montana-time-capsule/curlI-proxy-meta-20260523T180337Z.headers (url=logs/montana-time-capsule/heartbeat-proxy-meta-url-20260523T180337Z.txt)

## 2026-05-23T17:00:38Z HEARTBEAT monitor (HMC) - no-spend reconfirm: AWS identity + SageMaker terminal + S3 bundle present + viewer/proxy HTTP 200 + Pages deploy preview URL evidence + CI snapshot (exact-head empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ d96f9303749b7dcd6d1e736345ffd1363964de1c ([skip ci]) (clean; pushed)
- AWS (us-west-2):
  - cli: logs/montana-time-capsule/aws-binary-20260523T165821Z.txt (region=logs/montana-time-capsule/aws-configure-get-region-20260523T165821Z.txt)
  - identity: logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T165821Z.json
- SageMaker (canonical jobs expected Completed; no new HMC launches):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260523T165821Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T165821Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260523T165821Z.json
  - job lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260523T165832Z.json; logs/montana-time-capsule/sagemaker-list-training-jobs-hmc-mtc-20260520T2015Z-20260523T165832Z.json
- S3 (supersplat bundle present; SSE-KMS):
  - listing: logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-20260523T165856Z.txt
  - meta head: logs/montana-time-capsule/s3api-head-meta-json-hmc-mtc-20260520T2015Z-20260523T165856Z.json
  - skybox head: logs/montana-time-capsule/s3api-head-background-skybox-webp-hmc-mtc-20260520T2015Z-20260523T165856Z.json
- Proxy meta.json reachability (signed via preview; HTTP 200): logs/montana-time-capsule/curlI-proxy-meta-json-20260523T165903Z.headers (body=logs/montana-time-capsule/curl-proxy-meta-json-20260523T165903Z.body.json; url=logs/montana-time-capsule/heartbeat-proxy-meta-json-url-20260523T165903Z.txt)
- Hosted preview viewer reachability (Origin header set; HTTP 200):
  - skybox headers: logs/montana-time-capsule/curlI-viewer-skybox-20260523T165920Z.headers (url=logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T165920Z.txt)
  - no-sky headers: logs/montana-time-capsule/curlI-viewer-nosky-20260523T165920Z.headers (url=logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T165920Z.txt)
- Cloudflare Pages preview evidence (from last non-skip deploy run 26200368328):
  - preview lines extract: logs/montana-time-capsule/gh-run-view-deploy-pages-26200368328-20260523T170033Z.preview-lines.txt
- CI snapshot:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T165945Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T165945Z.json

## 2026-05-23T17:03:03Z postpush CI snapshot (exact-head expected empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ 1c9cb822635a1528466e32ef2424e221a44496fb ([skip ci]) (pushed)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T170259Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T170259Z.json

## 2026-05-23T13:04:40Z HEARTBEAT monitor (HMC) - terminal reconfirmed (awscli) + S3 bundle present + Pages deploy log reconfirmed + viewer/proxy HTTP 200 (Origin/CORS) (no launches)

- Git: agent-40136728-montana-time-capsule @ 535a873ba4377a29168a1bff987bb84e0a18e28e ([skip ci]) (clean)
- AWS (us-west-2):
  - cli: logs/montana-time-capsule/aws-version-20260523T130227Z.txt (region=logs/montana-time-capsule/aws-configure-get-region-20260523T130227Z.txt)
  - identity: logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T130227Z.json
- SageMaker (canonical jobs expected Completed; no new HMC launches):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T130227Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T130227Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T130227Z.json
  - InProgress processing list: logs/montana-time-capsule/sagemaker-list-processing-jobs-InProgress-20260523T130227Z.json
  - InProgress training list: logs/montana-time-capsule/sagemaker-list-training-jobs-InProgress-20260523T130227Z.json
- S3 (supersplat bundle present): logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-20260523T130249Z.txt (meta head=logs/montana-time-capsule/s3api-head-meta-json-hmc-mtc-20260520T2015Z-20260523T130249Z.json; skybox head=logs/montana-time-capsule/s3api-head-background-skybox-webp-hmc-mtc-20260520T2015Z-20260523T130249Z.json)
- Cloudflare Pages preview evidence (from last non-skip deploy; alias URL appears in extracted log lines):
  - extract: logs/montana-time-capsule/gh-run-view-pages-26200368328-20260523T130414Z.preview-grep.txt
  - alias URL (from extract): https://agent-40136728-montana-time.v0-spaceport-website-preview2.pages.dev
- Hosted preview viewer reachability (Origin header set; HTTP 200):
  - skybox headers: logs/montana-time-capsule/curlI-viewer-skybox-20260523T130440Z.headers
  - no-sky headers: logs/montana-time-capsule/curlI-viewer-nosky-20260523T130440Z.headers
  - proxy meta.json GET works (signed; HTTP 200): logs/montana-time-capsule/curlI-proxy-meta-json-20260523T130440Z.headers (body=logs/montana-time-capsule/curl-proxy-meta-json-20260523T130440Z.body.json)
- CI snapshot:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T130353Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T130353Z.json

## 2026-05-23T13:06:43Z postpush CI snapshot (exact-head expected empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ e1043379f24cfb54d7797386e9eea5bf56ef0a58 ([skip ci]) (clean)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T130643Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T130643Z.json

## 2026-05-23T13:23:28Z HEARTBEAT monitor (HMC) - reconfirm terminal + S3 bundle present + viewer/proxy HTTP 200 + CI snapshot (no launches)

- Git: agent-40136728-montana-time-capsule @ 18049559b54044c541b24c2808eb4dec15fea98e ([skip ci]) (clean)
- AWS (us-west-2):
  - cli: logs/montana-time-capsule/aws-version-20260523T132209Z.txt (region=logs/montana-time-capsule/aws-configure-get-region-20260523T132209Z.txt)
  - identity: logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T132209Z.json
- SageMaker (canonical jobs expected Completed; InProgress expected 0):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T132209Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T132209Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T132209Z.json
  - InProgress processing list: logs/montana-time-capsule/sagemaker-list-processing-jobs-InProgress-20260523T132209Z.json
  - InProgress training list: logs/montana-time-capsule/sagemaker-list-training-jobs-InProgress-20260523T132209Z.json
- S3 (supersplat bundle present): logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-20260523T132209Z.txt (meta head=logs/montana-time-capsule/s3api-head-meta-json-hmc-mtc-20260520T2015Z-20260523T132209Z.json; skybox head=logs/montana-time-capsule/s3api-head-background-skybox-webp-hmc-mtc-20260520T2015Z-20260523T132209Z.json)
- Hosted preview viewer reachability (Origin header set; HTTP 200):
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T132241Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T132241Z.headers)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T132241Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T132241Z.headers)
  - proxy meta.json GET works (HTTP 200): logs/montana-time-capsule/heartbeat-proxy-meta-json-url-20260523T132241Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-json-20260523T132241Z.headers; body=logs/montana-time-capsule/curl-proxy-meta-json-20260523T132241Z.body.json)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T132300Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T132300Z.json

## 2026-05-23T13:25:12Z postpush CI snapshot (exact-head expected empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ b93057ead32fbd3839c6cf1a726f1bdbe638cb78 ([skip ci]) (clean)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T132512Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T132512Z.json

## 2026-05-23T18:44:30Z HEARTBEAT monitor (HMC) - no-spend reconfirm + terminal canonical jobs + S3 supersplat bundle + Pages preview URL re-derived from deploy log + viewer/proxy HTTP 200 (Origin) + CI snapshot (exact-head empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ 2c245d908cfa10c21a1c0db6397d8338d0b6daad ([skip ci]) (clean)
- AWS (us-west-2; aws=/opt/homebrew/bin/aws):
  - identity: logs/montana-time-capsule/aws-sts-20260523T184235Z.json
  - region: logs/montana-time-capsule/aws-region-20260523T184235Z.txt
  - version: logs/montana-time-capsule/aws-version-20260523T184235Z.txt (binary=logs/montana-time-capsule/aws-binary-20260523T184235Z.txt)
- SageMaker (canonical jobs expected Completed; no HMC launches):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260523T184235Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T184253Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260523T184235Z.json
  - HMC processing list snapshot: logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260523T184235Z.json
  - HMC training list snapshot: logs/montana-time-capsule/sagemaker-list-training-jobs-hmc-mtc-20260520T2015Z-20260523T184253Z.json
  - InProgress processing list (expected non-HMC; do not stop): logs/montana-time-capsule/sagemaker-list-processing-jobs-InProgress-20260523T184253Z.json
  - InProgress training list: logs/montana-time-capsule/sagemaker-list-training-jobs-InProgress-20260523T184253Z.json
- S3 (supersplat bundle present):
  - bundle listing: logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-20260523T184235Z.txt
  - meta head-object: logs/montana-time-capsule/s3api-head-meta-json-hmc-mtc-20260520T2015Z-20260523T184430Z.json
  - skybox head-object: logs/montana-time-capsule/s3api-head-background-skybox-webp-hmc-mtc-20260520T2015Z-20260523T184430Z.json
- Cloudflare Pages preview (deterministic from deploy log):
  - deploy log: logs/montana-time-capsule/gh-run-view-pages-26200368328-20260523T184336Z.log
  - preview URLs: logs/montana-time-capsule/pages-preview-url-20260523T184336Z.txt
  - root headers (Origin set; HTTP 200): logs/montana-time-capsule/curlI-pages-root-20260523T184330Z.headers
- Hosted preview viewer reachability (Origin set; HTTP 200):
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T184330Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T184330Z.headers)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T184330Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T184330Z.headers)
  - proxy meta.json GET works (HTTP 200): logs/montana-time-capsule/heartbeat-proxy-meta-json-url-20260523T184330Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-json-20260523T184330Z.headers; body=logs/montana-time-capsule/curl-proxy-meta-json-20260523T184330Z.body.json)
- CI (gh=/opt/homebrew/bin/gh; head is `[skip ci]` so exact-head expected empty):
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-agent-40136728-20260523T184235Z.json
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260523T184235Z.json

## 2026-05-23T18:45:28Z postpush CI snapshot (exact-head expected empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ f5c4f529cafad970052ed229e3b2f8ee674c5f77 ([skip ci]) (clean)
- CI:
  - git head: logs/montana-time-capsule/git-head-20260523T184528Z.txt
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T184528Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T184528Z.json

## 2026-05-23T12:54:20Z HEARTBEAT monitor (HMC) - terminal reconfirmed + AWS identity + S3 bundle + viewer HTTP 200 (skybox/no-sky) + proxy meta HTTP 200 (+CORS) + viewer screenshots + CI snapshot (no launches)

- Git: agent-40136728-montana-time-capsule @ 9a0d9ccebdab557f16f2ef2fbfc27988512c600b ([skip ci]) (clean)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T124209Z.json (region=logs/montana-time-capsule/aws-configure-get-region-20260523T124209Z.txt; cli=logs/montana-time-capsule/aws-binary-20260523T124209Z.txt)
- SageMaker (canonical jobs expected Completed; no new HMC launches):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260523T124217Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T124230Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260523T124217Z.json
  - InProgress processing list (expected non-HMC; do not stop): logs/montana-time-capsule/sagemaker-list-processing-jobs-InProgress-20260523T124209Z.json
- S3 (supersplat bundle present): logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-20260523T124244Z.txt (meta head=logs/montana-time-capsule/s3api-head-meta-json-hmc-mtc-20260520T2015Z-20260523T124244Z.json; meta head60=logs/montana-time-capsule/s3-cat-meta-json-hmc-mtc-20260520T2015Z-20260523T124244Z.head60.txt)
- Hosted preview viewer reachability (Origin header set; HTTP 200) + screenshots:
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T124307Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T124307Z.headers; screenshot=logs/montana-time-capsule/heartbeat-viewer-skybox-20260523T124458Z.png; run=logs/montana-time-capsule/heartbeat-viewer-skybox-screenshot-20260523T124458Z.txt)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T124307Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T124307Z.headers; screenshot=logs/montana-time-capsule/heartbeat-viewer-nosky-20260523T124458Z.png; run=logs/montana-time-capsule/heartbeat-viewer-nosky-screenshot-20260523T124458Z.txt)
  - direct S3 meta.json GET fails (expected for SSE-KMS without signing): logs/montana-time-capsule/curl-meta-json-20260523T124326Z.headers (body=logs/montana-time-capsule/curl-meta-json-20260523T124326Z.body.xml)
  - proxy meta.json GET works (signed): logs/montana-time-capsule/heartbeat-proxy-meta-json-url-20260523T125402Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-json-20260523T125402Z.headers; body=logs/montana-time-capsule/curl-proxy-meta-json-20260523T125402Z.body.json)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T124733Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T124733Z.json

## 2026-05-23T11:43:42Z HEARTBEAT monitor (HMC) - terminal reconfirmed + AWS identity + S3 bundle + viewer HTTP 200 (skybox/no-sky) + CI snapshot (no launches)

- Git: agent-40136728-montana-time-capsule @ 2b2663a4f0a57708fdc2d543c5397ad07ff86726 ([skip ci]) (clean)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T114214Z.json (region=logs/montana-time-capsule/aws-region-20260523T114214Z.txt; cli=logs/montana-time-capsule/aws-version-20260523T114214Z.txt)
- SageMaker (canonical jobs expected Completed; InProgress expected 0):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T114214Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T114214Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T114214Z.json
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-inprogress-20260523T114214Z.json (0); logs/montana-time-capsule/sagemaker-list-training-inprogress-20260523T114214Z.json (0)
- S3 (supersplat bundle present): logs/montana-time-capsule/s3-ls-recursive-supersplat_bundle-20260523T114244Z.txt (meta head=logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260523T114244Z.json; skybox head=logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260523T114244Z.json)
- Hosted preview viewer reachability (Origin header set; HTTP 200):
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T114258Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T114258Z.headers)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T114258Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T114258Z.headers)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260523T114258Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260523T114258Z.headers)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T114322Z.json (latest CDK Deploy success on 0e48d07a; latest Pages success on 88b1848f)
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T114322Z.json

## 2026-05-23T11:44:56Z POST-PUSH monitor (HMC) - git head advanced + exact-head GH runs recorded (no launches)

- Git: agent-40136728-montana-time-capsule @ 1af653345abb2c597d7bcf32674a9b1fa5464439 ([skip ci]) (pushed)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T114451Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T114451Z.json

## 2026-05-23T11:24:17Z HEARTBEAT monitor (HMC) - terminal reconfirmed + AWS identity + S3 bundle + viewer HTTP 200 (skybox/no-sky) + CI snapshot (no launches)

- Git: agent-40136728-montana-time-capsule @ a7aca00f3f19ad778a27f0c7b23e1b353cf68d35 ([skip ci]) (head=logs/montana-time-capsule/git-head-20260523T112417Z.txt; status=logs/montana-time-capsule/git-status-20260523T112417Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T112218Z.json (region=logs/montana-time-capsule/aws-region-20260523T112218Z.txt; cli=logs/montana-time-capsule/aws-version-20260523T112218Z.txt)
- SageMaker (canonical jobs expected Completed; InProgress expected 0):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T112218Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T112218Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T112218Z.json
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-inprogress-20260523T112218Z.json (0); logs/montana-time-capsule/sagemaker-list-training-inprogress-20260523T112218Z.json (0)
- S3 (supersplat bundle present): logs/montana-time-capsule/s3-ls-recursive-supersplat_bundle-20260523T112328Z.txt (meta head=logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260523T112328Z.json; skybox head=logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260523T112328Z.json)
- Hosted preview viewer reachability (Origin header set; HTTP 200):
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T112328Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T112328Z.headers)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T112328Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T112328Z.headers)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260523T112328Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260523T112328Z.headers)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T112358Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T112358Z.json

## 2026-05-23T11:25:27Z POST-PUSH monitor (HMC) - git head + exact-head GH runs recorded (no launches)

- Git: agent-40136728-montana-time-capsule @ 067efc72173a0484e125ef85a142031021ec0260 ([skip ci]) (head=logs/montana-time-capsule/git-head-20260523T112527Z.txt; status=logs/montana-time-capsule/git-status-20260523T112527Z.txt)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T112527Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T112527Z.json

## 2026-05-23T11:01:52Z HEARTBEAT monitor (HMC) - terminal reconfirmed + AWS identity + S3 bundle + viewer HTTP 200 (skybox/no-sky) + CI snapshot (no launches)

- Git: agent-40136728-montana-time-capsule @ d1b4565f9ffd8866e39750afd940b0d2cf48940e ([skip ci])
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T110152Z.json (region=logs/montana-time-capsule/aws-region-20260523T110152Z.txt; cli=logs/montana-time-capsule/aws-version-20260523T110152Z.txt)
- SageMaker (canonical jobs expected Completed; InProgress expected 0):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T110152Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T110152Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T110152Z.json
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-inprogress-20260523T110152Z.json (0); logs/montana-time-capsule/sagemaker-list-training-inprogress-20260523T110152Z.json (0)
  - HMC list snapshots: logs/montana-time-capsule/sagemaker-list-processing-hmc-mtc-20260520T2015Z-20260523T110152Z.json ; logs/montana-time-capsule/sagemaker-list-training-hmc-mtc-20260520T2015Z-20260523T110152Z.json
- S3 (supersplat bundle present): logs/montana-time-capsule/s3-ls-recursive-supersplat_bundle-20260523T110152Z.txt (meta head=logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260523T110152Z.json; skybox head=logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260523T110152Z.json)
- Hosted preview viewer reachability:
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T110152Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T110152Z.headers; HTTP 200)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T110152Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T110152Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260523T110152Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260523T110152Z.headers; HTTP 200)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T110152Z.json (latest CDK Deploy success at 2026-05-21T11:38:18Z)
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T110152Z.json

## 2026-05-23T11:04:06Z POST-PUSH monitor (HMC) - git head + exact-head GH runs recorded (no launches)

- Git: agent-40136728-montana-time-capsule @ 42ebe312a2df7e5ceccb1c0a64513b9d1f3dd6a2 ([skip ci]) (head=logs/montana-time-capsule/git-head-20260523T110406Z.txt; status=logs/montana-time-capsule/git-status-20260523T110406Z.txt)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T110406Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T110406Z.json

## 2026-05-23T10:31:23Z POST-HEARTBEAT monitor (HMC) - git head + exact-head GH runs recorded (no launches)

- Git: agent-40136728-montana-time-capsule @ 649c0eec ([skip ci]) (head=logs/montana-time-capsule/git-head-20260523T103123Z.txt; status=logs/montana-time-capsule/git-status-20260523T103123Z.txt)
- CI:
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T103101Z.json

## 2026-05-23T10:26:30Z HEARTBEAT monitor (HMC) - terminal reconfirmed + AWS identity + S3 bundle + viewer HTTP 200 (skybox/no-sky) (no launches)

- Git: agent-40136728-montana-time-capsule @ dd7bed82 ([skip ci]) (head=logs/montana-time-capsule/git-head-20260523T100322Z.txt; status=logs/montana-time-capsule/git-status-20260523T100322Z.txt)
- AWS STS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T102600Z.json
- SageMaker (canonical jobs expected Completed):
  - SfM describe: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260523T102600Z.json
  - 3DGS describe: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260523T102641Z.json
  - compression describe: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260523T102600Z.json
  - InProgress list snapshot (non-HMC observed; do not stop): logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260523T102600Z.json
  - list snapshots: logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260523T102600Z.json ; logs/montana-time-capsule/sagemaker-list-training-jobs-hmc-mtc-20260520T2015Z-20260523T102641Z.json
- S3 (supersplat bundle): logs/montana-time-capsule/s3-ls-supersplat_bundle-20260523T102600Z.txt (meta head=logs/montana-time-capsule/s3api-head-object-supersplat-meta.json-20260523T102600Z.json; skybox head=logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox.webp-20260523T102600Z.json)
- Hosted preview viewer reachability:
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T102614Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T102614Z.headers; HTTP 200)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T102614Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T102614Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260523T102652Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260523T102652Z.headers; HTTP 200)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T102622Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T102622Z.json

## 2026-05-23T14:04:11Z HEARTBEAT monitor (HMC) - no-spend reconfirm (awscli) + terminal canonical jobs + S3 supersplat bundle + preview viewer/proxy HTTP 200 + CI snapshot

- Git: agent-40136728-montana-time-capsule @ 941fb560312039fb45c547b61dae285d73de5c55 ([skip ci]) (clean)
- AWS (us-west-2):
  - identity: logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T140411Z.json
  - region: logs/montana-time-capsule/aws-configure-get-region-20260523T140411Z.txt
- SageMaker (canonical jobs expected Completed; no HMC launches):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T140411Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T140411Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T140411Z.json
  - InProgress processing list: logs/montana-time-capsule/sagemaker-list-processing-jobs-InProgress-20260523T140411Z.json (non-HMC may appear; do not stop)
  - InProgress training list: logs/montana-time-capsule/sagemaker-list-training-jobs-InProgress-20260523T140411Z.json
- S3 (supersplat bundle present):
  - bundle listing: logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-20260523T140411Z.txt
  - meta head: logs/montana-time-capsule/s3api-head-meta-json-hmc-mtc-20260520T2015Z-20260523T140411Z.json
  - skybox head: logs/montana-time-capsule/s3api-head-background-skybox-webp-hmc-mtc-20260520T2015Z-20260523T140411Z.json
- Cloudflare Pages preview:
  - URL: logs/montana-time-capsule/pages-preview-url-20260523T140411Z.txt
  - root headers (Origin set; HTTP 200): logs/montana-time-capsule/curlI-pages-root-20260523T140411Z.headers
- Hosted preview viewer reachability (Origin set; HTTP 200):
  - skybox headers: logs/montana-time-capsule/curlI-viewer-skybox-20260523T140411Z.headers
  - no-sky headers: logs/montana-time-capsule/curlI-viewer-nosky-20260523T140411Z.headers
  - proxy meta.json GET works (HTTP 200): logs/montana-time-capsule/curlI-proxy-meta-json-20260523T140411Z.headers (body=logs/montana-time-capsule/curl-proxy-meta-json-20260523T140411Z.body.json)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T140411Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T140411Z.json

## 2026-05-23T14:05:08Z postpush CI snapshot (exact-head expected empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ 09826b902a6c38c3f5dfaa04b622295c18e4ce51 ([skip ci]) (clean)
- CI:
  - git head: logs/montana-time-capsule/git-head-20260523T140508Z.txt
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T140508Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T140508Z.json

## 2026-05-23T14:26:18Z HEARTBEAT monitor (HMC) - no-spend reconfirm (awscli) + terminal canonical jobs + S3 supersplat bundle + preview viewer/proxy HTTP 200 + Pages alias URL re-derived from deploy log + CI snapshot (exact-head empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ d9db7b9b1389ba97746d8722b14de660f9ef90ce ([skip ci]) (clean)
- AWS (us-west-2):
  - version: logs/montana-time-capsule/aws-version-20260523T142311Z.txt
  - region: logs/montana-time-capsule/aws-configure-get-region-20260523T142311Z.txt
  - identity: logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T142311Z.json
- SageMaker (canonical jobs expected Completed; InProgress may include non-HMC; do not stop):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T142311Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T142311Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T142311Z.json
  - InProgress processing list: logs/montana-time-capsule/sagemaker-list-processing-jobs-InProgress-20260523T142311Z.json
  - InProgress training list: logs/montana-time-capsule/sagemaker-list-training-jobs-InProgress-20260523T142311Z.json
- S3 (supersplat bundle present):
  - bundle listing: logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-20260523T142342Z.txt
  - meta head: logs/montana-time-capsule/s3api-head-meta-json-hmc-mtc-20260520T2015Z-20260523T142342Z.json
  - skybox head: logs/montana-time-capsule/s3api-head-background-skybox-webp-hmc-mtc-20260520T2015Z-20260523T142342Z.json
- Cloudflare Pages preview:
  - alias URL: logs/montana-time-capsule/pages-preview-url-20260523T142536Z.txt
  - determinism extract (from deploy log): logs/montana-time-capsule/gh-run-view-pages-26200368328-20260523T142536Z.preview-grep.txt (log=logs/montana-time-capsule/gh-run-view-pages-26200368328-20260523T142500Z.log.txt)
  - root headers (Origin set; HTTP 200): logs/montana-time-capsule/curlI-pages-root-20260523T142409Z.headers
- Hosted preview viewer reachability (Origin set; HTTP 200):
  - skybox headers: logs/montana-time-capsule/curlI-viewer-skybox-20260523T142409Z.headers
  - no-sky headers: logs/montana-time-capsule/curlI-viewer-nosky-20260523T142409Z.headers
  - proxy meta.json GET works (HTTP 200): logs/montana-time-capsule/curlI-proxy-meta-json-20260523T142409Z.headers (body=logs/montana-time-capsule/curl-proxy-meta-json-20260523T142409Z.body.json)
- CI (exact-head runs expected empty due to `[skip ci]`; last-known green Pages/CDK are on 2026-05-21):
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T142439Z.json
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260523T142439Z.json
  - Pages runs: logs/montana-time-capsule/gh-run-list-pages-20260523T142439Z.json
  - CDK runs: logs/montana-time-capsule/gh-run-list-cdk-20260523T142439Z.json
- Monitor state:
  - updated: logs/montana-time-capsule/hmc-state.json

## 2026-05-23T10:14:00Z HEARTBEAT monitor (HMC) - terminal reconfirmed + AWS identity + S3 bundle + viewer HTTP 200 (skybox/no-sky/proxy) + CI proof (no launches)

- Git: agent-40136728-montana-time-capsule @ b2486b4e58334475562f77f7d7d3cf8f446d75f7 ([skip ci]) (head=logs/montana-time-capsule/git-head-20260523T100322Z.txt; status=logs/montana-time-capsule/git-status-20260523T100322Z.txt)
- AWS (us-west-2; aws=/opt/homebrew/bin/aws): logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T101350Z.json (region=logs/montana-time-capsule/aws-region-20260523T101350Z.txt; cli=logs/montana-time-capsule/aws-version-20260523T101350Z.txt; binary=logs/montana-time-capsule/aws-binary-20260523T101350Z.txt)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T101350Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T101350Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T101350Z.json)
  - InProgress lists (HMC expectation=0; unrelated jobs may appear): logs/montana-time-capsule/sagemaker-list-processing-inprogress-20260523T101350Z.json ; logs/montana-time-capsule/sagemaker-list-training-inprogress-20260523T101350Z.json
  - non-HMC InProgress observed (do not stop): cvhr-gpsalign-l06-1779528901 ; cvhr-gpsalign-l02-1779528900 (see logs/montana-time-capsule/sagemaker-list-processing-jobs-20260523T101350Z.json)
- S3 (supersplat bundle present):
  - bundle listing: logs/montana-time-capsule/s3-ls-recursive-supersplat_bundle-20260523T101350Z.txt
  - objects: logs/montana-time-capsule/s3api-list-objects-supersplat_bundle-20260523T101350Z.json
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta_json-20260523T101350Z.json
  - bundle background skybox head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox_webp-20260523T101350Z.json
- Hosted preview viewer reachability (canonical route):
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T101352Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T101352Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T101352Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T101352Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260523T101352Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260523T101352Z.headers; HTTP 200)
- CI (gh=/opt/homebrew/bin/gh):
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T101419Z.txt (json=logs/montana-time-capsule/gh-run-list-branch-20260523T101419Z.json)
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T101419Z.txt (json=logs/montana-time-capsule/gh-run-list-exact-head-20260523T101419Z.json)

## 2026-05-23T09:23:31Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer HTTP 200 + GH branch workflows confirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ 65c2e2cef711fab4522a8bb9f08e9fb08dbd0db7 ([skip ci]) (head=logs/montana-time-capsule/git-head-20260523T092331Z.txt; status=logs/montana-time-capsule/git-status-20260523T092331Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-20260523T092210Z.json (region=logs/montana-time-capsule/aws-config-region-20260523T092210Z.txt; cli=logs/montana-time-capsule/aws-version-20260523T092210Z.txt; binary=logs/montana-time-capsule/aws-binary-20260523T092210Z.txt)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260523T092210Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260523T092210Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260523T092210Z.json)
  - InProgress lists (expect 0): logs/montana-time-capsule/sagemaker-list-processing-inprogress-20260523T092210Z.json ; logs/montana-time-capsule/sagemaker-list-training-inprogress-20260523T092210Z.json
- S3 (supersplat bundle):
  - bundle listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260523T092241Z.txt
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260523T092241Z.json
  - bundle background skybox head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260523T092241Z.json
- Hosted preview viewer reachability (canonical route):
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T092303Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T092303Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T092303Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T092303Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260523T092303Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260523T092303Z.headers; HTTP 200)
- CI (binary=logs/montana-time-capsule/gh-binary-20260523T092317Z.txt):
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T092317Z.txt
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260523T092317Z.txt (expected empty due to `[skip ci]`)

## 2026-05-23T09:03:35Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer/proxy/S3 HTTP 200 + GH branch workflows confirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ 444947b4ab2817005c95a8f7e61122d2169eb202 ([skip ci]) (head=logs/montana-time-capsule/git-head-20260523T090335Z.txt; status=logs/montana-time-capsule/git-status-20260523T090335Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-20260523T090335Z.json (region=logs/montana-time-capsule/aws-region-20260523T090335Z.txt; cli=logs/montana-time-capsule/aws-version-20260523T090335Z.txt; binary=/opt/homebrew/bin/aws)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260523T090335Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260523T090335Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260523T090335Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-inprogress-20260523T090335Z.json ; logs/montana-time-capsule/sagemaker-list-training-inprogress-20260523T090335Z.json
- S3 (supersplat bundle): logs/montana-time-capsule/s3-ls-supersplat_bundle-20260523T090335Z.txt
- Hosted preview viewer reachability (canonical route):
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T090335Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T090335Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T090335Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T090335Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260523T090335Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260523T090335Z.headers; HTTP 200)
  - direct S3 meta+skybox (HTTP 200): logs/montana-time-capsule/curlI-s3-meta-20260523T090335Z.headers ; logs/montana-time-capsule/curlI-s3-skybox-20260523T090335Z.headers
- CI (binary=/opt/homebrew/bin/gh):
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T090335Z.txt
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260523T090335Z.txt (expected empty due to `[skip ci]`)

Post-push sanity: Git HEAD is now 746a1c8abd8414b746b2f1cc0bc5a4ad2d5347c4 ([skip ci]) (head=logs/montana-time-capsule/git-head-postpush-20260523T090425Z.txt; exact-head runs=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T090425Z.txt; branch runs=logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T090425Z.txt).

Next: remain idle unless a new acceptance gate is requested (browser screenshots / input-vs-render camera checks); do not launch or stop any jobs.

## 2026-05-23T08:44:07Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer/proxy reachable + exact-head CI reconfirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ e03d2a02aef82f5b46ea8b6b6591ac4b3f27942a (status=logs/montana-time-capsule/git-status-20260523T084246Z.txt; head=logs/montana-time-capsule/git-head-status-20260523T084246Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T084246Z.json (region=logs/montana-time-capsule/aws-config-region-20260523T084246Z.txt; cli=/opt/homebrew/bin/aws)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260523T084246Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260523T084246Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260523T084246Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260523T084246Z.json (count=0); logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260523T084246Z.json (count=0)
- S3 (supersplat bundle):
  - bundle listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260523T084246Z.txt
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260523T084246Z.json
  - bundle background skybox head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260523T084246Z.json
- Hosted preview viewer reachability (canonical route):
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T084406Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T084406Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T084406Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T084406Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260523T084406Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260523T084406Z.headers; HTTP 200)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260523T084303Z.json (count=logs/montana-time-capsule/gh-exact-head-run-count-20260523T084303Z.txt; expected 0 due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T084303Z.json (count=logs/montana-time-capsule/gh-branch-run-count-20260523T084303Z.txt)

Post-push sanity: Git HEAD is now afe057d446e8ee8a38c59d40d96deb9e8dfffeb2 ([skip ci]) (head=logs/montana-time-capsule/git-head-status-20260523T084618Z.txt; status=logs/montana-time-capsule/git-status-20260523T084618Z.txt; exact-head runs=logs/montana-time-capsule/gh-exact-head-run-count-20260523T084618Z.txt).

Next: remain idle unless a new acceptance gate is requested (browser screenshots / input-vs-render camera checks); do not launch or stop any jobs.

## 2026-05-22T16:18:12Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer/proxy reachable + exact-head CI confirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ 913ace0bae5c908a5680e39f4db724aa71ffb7d5 ([skip ci]) (status=logs/montana-time-capsule/git-status-20260522T161714Z.txt; head=logs/montana-time-capsule/git-head-status-20260522T161714Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T161714Z.json (region=logs/montana-time-capsule/aws-config-region-20260522T161714Z.txt; cli=/opt/homebrew/bin/aws)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T161714Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260522T161714Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T161714Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T161714Z.json (non-HMC includes `cvhr-wcrepair-l08-1779464068`); logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T161714Z.json
- S3 (supersplat bundle):
  - bundle listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T161726Z.txt
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260522T161726Z.json
  - bundle background skybox head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260522T161726Z.json
- Hosted preview viewer reachability:
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T161748Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T161748Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T161748Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T161748Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T161748Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T161748Z.headers; HTTP 200)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T161812Z.json (count=logs/montana-time-capsule/gh-exact-head-run-count-20260522T161812Z.txt; expected 0 due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T161812Z.json (count=logs/montana-time-capsule/gh-branch-run-count-20260522T161812Z.txt)

Post-push sanity: Git HEAD is now 0090a4a8a2f7b2639e7e4b66800b4ad3ab14dc1a ([skip ci]) (head=logs/montana-time-capsule/git-head-status-20260522T162104Z.txt; status=logs/montana-time-capsule/git-status-20260522T162104Z.txt; exact-head runs=logs/montana-time-capsule/gh-exact-head-run-count-20260522T162104Z.txt).

Next: remain idle unless a new acceptance gate is requested (visual screenshots/skybox/no-sky in browser); do not launch or stop any jobs.

## 2026-05-22T15:40:12Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer/proxy reachable + non-HMC in-progress job observed (no launches)

- Git: agent-40136728-montana-time-capsule @ 41bcccb2655e5046ca8a2d0acd8366b6cae4c1d0 ([skip ci]) (upstream=ae85927ee9d1a12ce18c9f2228f9867858ce04da) (status=logs/montana-time-capsule/git-status-20260522T154012Z.txt; head=logs/montana-time-capsule/git-head-status-20260522T154012Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T154012Z.json (acct 975050048887) (region=logs/montana-time-capsule/aws-config-region-20260522T154012Z.txt)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T154012Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260522T154012Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T154012Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T154012Z.json (non-HMC includes `cvhr-wcrepair-l08-1779464068`; describe=logs/montana-time-capsule/sagemaker-describe-cvhr-wcrepair-l08-1779464068-20260522T154012Z.json); logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T154012Z.json
- S3 (supersplat bundle):
  - bundle listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T154012Z.txt
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260522T154012Z.json
  - bundle background skybox head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260522T154012Z.json
- Hosted preview viewer reachability:
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T154012Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T154012Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T154012Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T154012Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T154012Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T154012Z.headers; HTTP 200)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T154012Z.json (count=logs/montana-time-capsule/gh-exact-head-run-count-20260522T154012Z.txt; expected 0 due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T154012Z.json

Next: push logs-only heartbeat commit; do not stop or modify non-HMC jobs; remain idle unless a new acceptance gate is requested.

## 2026-05-22T15:34:30Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer/proxy reachable + screenshots captured + exact-head CI confirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ 65f85de6d3c0363d8999c3993d663c57b7033036 ([skip ci]) (dirty=logs only) (status=logs/montana-time-capsule/git-status-20260522T153430Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T153430Z.json (acct 975050048887; cli=/opt/homebrew/bin/aws) (region=logs/montana-time-capsule/aws-config-region-20260522T153430Z.txt)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T153430Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260522T153430Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T153430Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T153430Z.json (0); logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T153430Z.json (0)
- S3 (supersplat bundle):
  - bundle listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T153430Z.txt (13 objects)
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260522T153430Z.json (ContentLength=1359)
  - bundle background skybox head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260522T153430Z.json (ContentLength=47786)
- Hosted preview viewer reachability:
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T153430Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T153430Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T153430Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T153430Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T153430Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T153430Z.headers; HTTP 200)
- Visual proof (Playwright Python screenshots):
  - logs/montana-time-capsule/screenshots/viewer-skybox-20260522T153430Z.png
  - logs/montana-time-capsule/screenshots/viewer-nosky-20260522T153430Z.png
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T153430Z.json (0; expected if head commit is [skip ci]) (cli=/opt/homebrew/bin/gh)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T153430Z.json

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-22T15:39:52Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer/proxy reachable + exact-head CI confirmed (no launches)

- Repo: /Users/gabrielhansen/worktrees/md1-baseline-montana-time-capsule
- Git: agent-40136728-montana-time-capsule @ 3da2e582b275cf2360edcda4dfe8e83c9e9b508c ([skip ci])
  - status: logs/montana-time-capsule/git-status-20260522T145736Z.txt
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T145758Z.json (acct 975050048887)
- SageMaker (terminal reconfirmed):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T145758Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T145758Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260522T145758Z.json
  - InProgress lists (expect 0): logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T145758Z.json; logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T145758Z.json
- S3 bundle outputs (supersplat bundle present):
  - recursive listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T153647Z.txt (13 objects; 7,124,745 bytes)
  - meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260522T153647Z.json (ContentLength=1359)
  - skybox head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260522T153647Z.json
- Hosted viewer reachability (alias):
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T153645Z.txt (headers=logs/montana-time-capsule/curlI-hosted-viewer-skybox-20260522T153722Z.headers; HTTP 200)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T153645Z.txt (headers=logs/montana-time-capsule/curlI-hosted-viewer-nosky-20260522T153722Z.headers; HTTP 200)
- Proxy reachability (expected path for KMS/SigV4 staging S3):
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T153834Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T153906Z.headers; HTTP 200)
  - direct staging S3 meta.json remains non-public (SigV4/KMS): logs/montana-time-capsule/curlI-s3-supersplat-meta-20260522T153722Z.headers (HTTP 400); logs/montana-time-capsule/curl-s3-supersplat-meta-20260522T153742Z.body.xml
- CI:
  - exact-head runs (expect 0 due to [skip ci]): logs/montana-time-capsule/gh-run-list-exact-head-20260522T153939Z.json (head=logs/montana-time-capsule/gh-exact-head-sha-20260522T153939Z.txt)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T153939Z.json

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested (e.g., public bundle promotion outside staging/proxy, or full visual screenshot proof request).

## 2026-05-22T15:39:40Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 bundle present + viewer/proxy HTTP 200 + exact-head CI confirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ 3da2e582b275cf2360edcda4dfe8e83c9e9b508c ([skip ci])
- AWS (us-west-2): logs/montana-time-capsule/aws-version-20260522T153914Z.txt; logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T153914Z.json
- SageMaker (terminal; no in-progress): logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260522T153908Z.json; logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260522T153908Z.json; logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260522T153908Z.json; in-progress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T153914Z.json (0); logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T153914Z.json (0)
- S3 (supersplat bundle): logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T153910Z.txt; meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta.json-20260522T153910Z.json; skybox head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox.webp-20260522T153908Z.json
- Hosted reachability (HTTP 200): logs/montana-time-capsule/curlI-viewer-skybox-20260522T153910Z.headers; logs/montana-time-capsule/curlI-viewer-nosky-20260522T153910Z.headers; logs/montana-time-capsule/curlI-proxy-meta-20260522T153910Z.headers
- CI: logs/montana-time-capsule/gh-run-list-exact-head-20260522T153910Z.json (0; expected due to [skip ci] head); logs/montana-time-capsule/gh-run-list-branch-20260522T153910Z.json

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-22T15:48:37Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 bundle present + viewer/proxy HTTP 200 + exact-head CI confirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ 3da2e582b275cf2360edcda4dfe8e83c9e9b508c ([skip ci]) (head=logs/montana-time-capsule/git-head-20260522T154837Z.txt; status=logs/montana-time-capsule/git-status-porcelain-20260522T154837Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-version-20260522T154837Z.txt; logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T154837Z.json
- SageMaker (terminal; no in-progress): logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260522T154837Z.json; logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260522T154837Z.json; logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260522T154837Z.json; in-progress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T154837Z.json (0); logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T154837Z.json (0)
- S3 (supersplat bundle): logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T154837Z.txt; meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta.json-20260522T154837Z.json; skybox head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox.webp-20260522T154837Z.json
- Hosted reachability (HTTP 200): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T154837Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T154837Z.headers); logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T154837Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T154837Z.headers); logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T154837Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T154837Z.headers)
- CI: logs/montana-time-capsule/gh-run-list-exact-head-20260522T154837Z.json (0; expected due to [skip ci] head); logs/montana-time-capsule/gh-run-list-branch-20260522T154837Z.json

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-22T15:50:04Z Post-push CI proof (HMC)

- Git head pushed: e1cb51d3a64d1c6681d878f16c24e8ad5f4fb3bd ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260522T155004Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260522T155004Z.json)

## 2026-05-22T14:57:58Z Post-push CI proof (HMC)

- Git head pushed: 38b2b50385b09b51e0765d34f40264476a263b80 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260522T145758Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260522T145758Z.json)

## 2026-05-22T15:34:19Z HEARTBEAT monitor (HMC) - terminal reconfirmed + viewer still HTTP 200 (no launches)

- Git: agent-40136728-montana-time-capsule @ 028449b5b04925f636665c1c68b2499a0d6bcaac ([skip ci]) (status=logs/montana-time-capsule/git-status-20260522T153419Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T103118Z.json (acct 975050048887)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T141516Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260522T141516Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T141516Z.json)
  - InProgress lists (expect 0): logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T103118Z.json; logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T103118Z.json
- S3:
  - supersplat bundle listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T153349Z.txt
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260522T153349Z.json
  - bundle background_skybox.webp head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260522T153349Z.json
- Hosted preview viewer reachability:
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T153407Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T153407Z.headers; HTTP 200)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T153407Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T153407Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T153407Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T153407Z.headers; HTTP 200)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T153419Z.json
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T153419Z.json (0; expected due to [skip ci] head)

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-22T14:45:45Z HEARTBEAT monitor (HMC) - terminal reconfirmed + viewer/proxy HTTP 200; direct S3 public access fails due SSE-KMS (no launches)

- AWS (us-west-2): logs/montana-time-capsule/aws-version-20260522T144443Z.txt; logs/montana-time-capsule/aws-config-region-20260522T144443Z.txt; logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T144443Z.json (acct 975050048887; cli=/opt/homebrew/bin/aws)
- SageMaker (terminal; no in-progress):
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T110255Z.json (0); logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T110255Z.json (0)
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T110255Z.json) (Completed)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs (describe=logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260522T110312Z.json) (Completed)
  - compression processing job: hmc-mtc-20260520T2015Z-compression (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T110255Z.json) (Completed)
- S3 (supersplat bundle present):
  - listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T110326Z.txt (13 objects)
  - meta + background_skybox.webp head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260522T144439Z.txt; logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260522T144439Z.txt
  - direct public S3 URL is NOT reachable (SSE-KMS requires SigV4): logs/montana-time-capsule/curlI-s3-meta-20260522T144502Z.headers; logs/montana-time-capsule/curl-s3-meta-head40-20260522T144520Z.txt
- Hosted preview viewer reachability (HTTP 200):
  - viewer no-sky: logs/montana-time-capsule/curlI-viewer-nosky-20260522T144502Z.headers
  - viewer skybox: logs/montana-time-capsule/curlI-viewer-skybox-20260522T144502Z.headers
  - proxy meta (browser-compatible path): logs/montana-time-capsule/curlI-proxy-meta-20260522T144540Z.headers
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T153554Z.json (latest Pages/CDK green are earlier non-[skip ci] commits)
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T153545Z.json (0; expected due to [skip ci] head)

Next: remain idle; if “public bundle reachability” is required without proxy, bucket/object policy must change (do not adjust without explicit instruction).

## 2026-05-22T14:14:48Z HEARTBEAT monitor (HMC) - terminal reconfirmed + viewer still HTTP 200 (no launches)

- Git: agent-40136728-montana-time-capsule @ 028449b5b04925f636665c1c68b2499a0d6bcaac ([skip ci]) (status=logs/montana-time-capsule/git-status-20260522T141448Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T141448Z.json (acct 975050048887)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T141448Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260522T141448Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T141448Z.json)
  - InProgress lists (expect 0): logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T141448Z.json; logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T141448Z.json
- S3:
  - supersplat bundle listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T141448Z.txt
  - meta.json head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260522T141448Z.json
- Hosted preview viewer reachability:
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T141448Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T141448Z.headers; HTTP 200)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T141448Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T141448Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T141448Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T141448Z.headers; HTTP 200; content-length=1359)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T141448Z.json (still 0 expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T141448Z.json

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-22T14:13:38Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer/proxy reachable + exact-head CI recorded (no launches)

- Git: agent-40136728-montana-time-capsule @ 028449b5b04925f636665c1c68b2499a0d6bcaac ([skip ci]) (status=logs/montana-time-capsule/git-head-status-20260522T141338Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T141338Z.json (acct 975050048887) (region=logs/montana-time-capsule/aws-config-region-20260522T141338Z.txt)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T141338Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260522T141338Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T141338Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T141338Z.json (0); logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T141338Z.json (0)
- S3 (supersplat bundle):
  - bundle listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T141338Z.txt
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260522T141338Z.json
  - bundle background skybox head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260522T141338Z.json
- Hosted preview viewer reachability:
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T141338Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T141338Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T141338Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T141338Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T141338Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T141338Z.headers; HTTP 200)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T141338Z.json (0; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T141338Z.json

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-22T14:58:10Z Post-push CI proof (HMC)

- Git head pushed: 6a0dbb0f6b52968705289ca8a7696db25351d2d1 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260522T145812Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-20260522T145812Z.json)

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-22T14:44:54Z HEARTBEAT monitor (HMC) - terminal reconfirmed + viewer still reachable + Playwright proof (no launches)

- Git: agent-40136728-montana-time-capsule @ 028449b5b04925f636665c1c68b2499a0d6bcaac ([skip ci]) (status=logs/montana-time-capsule/git-status-porcelain-20260522T052551Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T144405Z.json (acct 975050048887)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T144419Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260522T144438Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T144419Z.json)
  - InProgress lists (expect 0): logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T144419Z.json; logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T144419Z.json
- S3 supersplat bundle (staging):
  - listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T141458Z.txt
  - head-object meta.json: logs/montana-time-capsule/s3api-head-object-supersplat-meta.json-20260522T144454Z.json
  - head-object background_skybox.webp: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox.webp-20260522T144454Z.json
- Hosted preview viewer reachability:
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T144408Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T144408Z.headers; HTTP 200)
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T144408Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T144408Z.headers; HTTP 200)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T144408Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T144408Z.headers; HTTP 200)
- Playwright visual proof (preview hosted viewer):
  - skybox smoke: logs/montana-time-capsule/sogs-migrated-viewer-skybox-smoke-20260522T141442Z.png (runner=logs/montana-time-capsule/playwright-sogs-skybox-20260522T141442Z.txt)
  - no-sky smoke: logs/montana-time-capsule/sogs-migrated-viewer-nosky-smoke-20260522T141442Z.png (runner=logs/montana-time-capsule/playwright-sogs-nosky-20260522T141442Z.txt)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T144424Z.json ([]; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T144424Z.json (recent Pages + CDK runs green on earlier non-[skip ci] heads)

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-22T14:45:09Z HEARTBEAT monitor (HMC) - terminal reconfirmed + viewer OK + screenshots captured (no launches)

- Git: agent-40136728-montana-time-capsule @ 028449b5b04925f636665c1c68b2499a0d6bcaac ([skip ci])
- AWS (us-west-2):
  - version: logs/montana-time-capsule/aws-version-20260522T144405Z.txt
  - sts: logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T144405Z.json (acct 975050048887)
- SageMaker (expect terminal + no in-progress jobs):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T144419Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260522T141516Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T144419Z.json
  - InProgress lists (expect 0): logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T144419Z.json; logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T144419Z.json
- S3 (compressed supersplat bundle):
  - listing (13 objects): logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T144502Z.txt
  - meta.json head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta.json-20260522T144502Z.json
  - background_skybox.webp head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox.webp-20260522T144502Z.json
- Hosted preview viewer reachability (alias + proxy meta):
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T144408Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T144408Z.headers; HTTP 200)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T144408Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T144408Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T144408Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T144408Z.headers; HTTP 200)
  - screenshots: logs/montana-time-capsule/screenshots/sogs-migrated-viewer-smoke-20260522T141416Z.png; logs/montana-time-capsule/screenshots/sogs-migrated-viewer-nosky-20260522T141416Z.png
- CI:
  - exact-head runs (0 expected due to [skip ci]): logs/montana-time-capsule/gh-run-list-exact-head-20260522T144424Z.json
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T144424Z.json
  - last Pages preview alias proof (ALIAS_URL/HASH_URL): logs/montana-time-capsule/gh-job-log-pages-77088830130-20260522T141511Z.log

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-22T06:02:15Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer/proxy reachable + screenshots captured + CI baseline still green (no launches)

- Git: agent-40136728-montana-time-capsule @ 028449b5b04925f636665c1c68b2499a0d6bcaac (dirty=logs only) (status=logs/montana-time-capsule/git-status-20260522T052501Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T052529Z.json (acct 975050048887; cli=/opt/homebrew/bin/aws)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T052529Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260522T052529Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T052529Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T052529Z.json (0); logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T052529Z.json (0)
- S3 (supersplat bundle):
  - bundle listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T052550Z.txt (13 objects)
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260522T052550Z.json (ContentLength=1359)
  - bundle background skybox head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260522T052550Z.json (ContentLength=47786)
- Hosted preview viewer reachability:
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T055237Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T055237Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T055237Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T055237Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T055237Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T055237Z.headers; HTTP 200)
- Visual proof (Playwright Python screenshots):
  - logs/montana-time-capsule/screenshots/viewer-skybox-20260522T060156Z.png
  - logs/montana-time-capsule/screenshots/viewer-nosky-20260522T060156Z.png
  - install logs: logs/montana-time-capsule/playwright-py/pip-install-20260522T055320Z.log; logs/montana-time-capsule/playwright-py/playwright-install-chromium-20260522T055320Z.log
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T055545Z.json (0; expected if head commit is [skip ci])
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T055545Z.json (latest success still 2026-05-21)

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-22T14:45:00Z HEARTBEAT monitor (HMC) - no-spend reconfirm: AWS identity ok, no in-progress jobs, supersplat bundle still present, viewer/proxy still HTTP 200, exact-head GH runs=0 ([skip ci])

- Git: agent-40136728-montana-time-capsule @ 41bcccb2655e5046ca8a2d0acd8366b6cae4c1d0 ([skip ci]) (dirty=logs only)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T144532Z.json; logs/montana-time-capsule/aws-config-region-20260522T144532Z.txt
- SageMaker terminal state:
  - InProgress processing jobs=0 (logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T144522Z.json)
  - InProgress training jobs=0 (logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T144522Z.json)
  - SfM: Completed (logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T144522Z.json)
  - 3DGS: Completed (logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260522T144522Z.json)
  - compression: Completed (logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T144522Z.json)
- S3 (supersplat bundle): logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T144503Z.txt (13 objects); meta ContentLength=1359 (logs/montana-time-capsule/s3api-head-object-supersplat-meta.json-20260522T144503Z.json)
- Hosted viewer reachability:
  - skybox: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T144508Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T144508Z.headers; HTTP 200)
  - no-sky: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T144508Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T144508Z.headers; HTTP 200)
  - proxy meta: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T144508Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T144508Z.headers; HTTP 200)
- CI:
  - exact-head runs=0 (logs/montana-time-capsule/gh-run-list-exact-head-20260522T145741Z.json)
  - branch runs latest success still 2026-05-21 (logs/montana-time-capsule/gh-run-list-branch-20260522T145741Z.json)

Next: remain idle (no re-launches) unless a new explicit acceptance gate is requested.

## 2026-05-22T06:02:08Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer/proxy reachable + exact-head CI confirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ 028449b5b04925f636665c1c68b2499a0d6bcaac ([skip ci]) (status=logs/montana-time-capsule/git-status-20260522T060208Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T060208Z.json (acct 975050048887) (region=logs/montana-time-capsule/aws-config-region-20260522T060208Z.txt)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T060208Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260522T060208Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T060208Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T060208Z.json; logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T060208Z.json
- S3 (supersplat bundle):
  - bundle listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T060208Z.txt
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260522T060208Z.json
  - bundle background skybox head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260522T060208Z.json
- Hosted preview viewer reachability:
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T060208Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T060208Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T060208Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T060208Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T060208Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T060208Z.headers; HTTP 200)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T060208Z.json (0; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T060208Z.json

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-21T23:57:53Z HEARTBEAT monitor (HMC) - terminal reconfirmed + bundle + viewer still reachable (no launches)

- Git: agent-40136728-montana-time-capsule @ c53b8e0dadaa59b796713584f36bb01a3c373230 (clean) ([skip ci])
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T235533Z.json (acct 975050048887)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T235533Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T235533Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260521T235533Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260521T235533Z.json; logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260521T235533Z.json (0 each)
- S3 (supersplat bundle):
  - bundle listing: logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-20260521T235607Z-head200.txt
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-hmc-mtc-20260520T2015Z-meta-20260521T235607Z.json
  - bundle background skybox head-object: logs/montana-time-capsule/s3api-head-object-hmc-mtc-20260520T2015Z-background_skybox-webp-20260521T235635Z.json
- Hosted preview viewer reachability:
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260521T235655Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260521T235655Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260521T235655Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260521T235655Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260521T235655Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260521T235655Z.headers; HTTP 200)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T235753Z.json (0; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T235753Z.json (latest Pages success sha=88b1848f5700cae039c8ea4dbda31a6790b6dc69)

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-22T02:47:52Z Post-push CI proof (HMC)

- Git head pushed: 59f9d8fdca3a4e08871b23a26acb286e804419d8 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260522T024752Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260522T024752Z.json)

## 2026-05-22T02:31:39Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer/proxy reachable + exact-head CI confirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ cba2c9a50804beaaa5f16ddbbaa5d386dfe2e3c6 ([skip ci]) (status=logs/montana-time-capsule/git-status-20260522T023139Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T023139Z.json (acct 975050048887)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T023139Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260522T023139Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T023139Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T023139Z.json (0); logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T023139Z.json (0)
- S3 (supersplat bundle):
  - bundle listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T023139Z.txt (13 objects)
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260522T023139Z.json (ContentLength=1359)
  - bundle background skybox head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260522T023139Z.json (ContentLength=47786)
- Hosted preview viewer reachability:
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T023139Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T023139Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T023139Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T023139Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T023139Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T023139Z.headers; HTTP 200)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T023139Z.json (0; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T023139Z.json

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-22T01:04:58Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer/proxy reachable + exact-head CI confirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ cba2c9a50804beaaa5f16ddbbaa5d386dfe2e3c6 ([skip ci]) (status=logs/montana-time-capsule/git-status-20260522T010458Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T010331Z.json (acct 975050048887)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T010331Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260522T010331Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T010331Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T010331Z.json; logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T010331Z.json
- S3 (supersplat bundle):
  - bundle listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T010350Z.txt
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260522T010350Z.json
  - bundle background skybox head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox-webp-20260522T010350Z.json
- Hosted preview viewer reachability:
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T010420Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T010420Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T010420Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T010420Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T010420Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T010420Z.headers; HTTP 200)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T010458Z.json (0; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T010458Z.json

Next: commit/push this tick's evidence logs; no further stage is unblocked without an explicit new acceptance gate.

## 2026-05-22T02:04:33Z Post-push CI proof (HMC)

- Git head pushed: 91b41796d06a248960d2e6a798c281b6539c4967 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260522T020433Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260522T020433Z.json)

## 2026-05-22T00:23:35Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer/proxy reachable + exact-head CI confirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ a7e242db6fbcdbb04f357c43c9d1b9b6bb84ac17 (clean) ([skip ci])
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T002156Z.json (acct 975050048887)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T002210Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260522T002210Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T002210Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T002210Z.json (2; not HMC); logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T002210Z.json (0)
- S3 (supersplat bundle):
  - bundle listing: logs/montana-time-capsule/s3-ls-spaceport-ml-processing-staging-compressed_hmc-mtc-20260520T2015Z_supersplat_bundle_-20260522T002250Z-head200.txt
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-spaceport-ml-processing-staging-20260522T002250Z-meta.json
  - bundle background skybox head-object: logs/montana-time-capsule/s3api-head-object-spaceport-ml-processing-staging-20260522T002250Z-background_skybox-webp.json
- Hosted preview viewer reachability:
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T002319Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T002319Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T002319Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T002319Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T002319Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T002319Z.headers; HTTP 200)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T002333Z.json (0; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T002333Z.json (latest CDK Deploy success sha=0e48d07ae2c60cbe606070887c60989660f48c74)

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-22T00:00:24Z Post-push CI proof (HMC)

- Git head pushed: 748bd3d481a832e3ba56ca366c835d05c45ebd4a ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260522T000024Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260522T000024Z.json)

## 2026-05-22T00:24:52Z Post-push CI proof (HMC)

- Git head pushed: 84f10827bdaa1bc06d42ee9af9d6daad8be84003 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260522T002452Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260522T002452Z.json)

## 2026-05-21T23:18:33Z HEARTBEAT monitor (HMC) - terminal reconfirmed + proxy/meta reachable (no launches)

- Git: agent-40136728-montana-time-capsule @ bd7c48289e40eb4aee30e07ad6293ca72144452e (clean) ([skip ci])
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T231616Z.json (acct 975050048887)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T231616Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T231616Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260521T231616Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260521T231616Z.json; logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260521T231616Z.json (0 each)
- S3:
  - bundle listing: logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-20260521T231647Z.txt
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-hmc-mtc-20260520T2015Z-meta-20260521T231647Z.json
  - bundle skybox head-object: logs/montana-time-capsule/s3api-head-object-hmc-mtc-20260520T2015Z-skybox-20260521T231647Z.json
- Hosted preview viewer reachability (alias):
  - base: logs/montana-time-capsule/heartbeat-preview-base-20260521T231715Z.txt
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260521T231715Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260521T231715Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260521T231715Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260521T231715Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url2-20260521T231804Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta2-20260521T231804Z.headers; HTTP 200)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T231833Z.json ([]; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T231833Z.json (latest Pages success sha=88b1848f5700cae039c8ea4dbda31a6790b6dc69 runId=26200368328)

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-21T23:37:11Z Post-push CI proof (HMC)

- Git head pushed: c8ab97c6f9c9b868d1d28af0d720ff1b142cfc02 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T233711Z.txt; branch=logs/montana-time-capsule/gh-run-list-postpush-20260521T233711Z.json)

## 2026-05-21T23:20:30Z Post-push CI proof (HMC)

- Git head pushed: b7fcaa5bcfdbca5f43b31ed39e8a33df464d2fdf ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T232030Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260521T232030Z.json)

## 2026-05-21T22:36:00Z HEARTBEAT monitor (HMC) - terminal state reconfirmed + viewer still HTTP 200 (no launches)

- Git: agent-40136728-montana-time-capsule @ 275f8449f728f5b197b014ba6fece05d7d7307b6 ([skip ci]) (status=logs/montana-time-capsule/git-status-20260521T223600Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T223600Z.json (acct 975050048887)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T223600Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T223600Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260521T223600Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-inprogress-hmc-mtc-20260520T2015Z-20260521T223600Z.json; logs/montana-time-capsule/sagemaker-list-training-inprogress-hmc-mtc-20260520T2015Z-20260521T223600Z.json (0 each)
- S3:
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-hmc-mtc-20260520T2015Z-supersplat-meta-20260521T223600Z.json
  - bundle listing: logs/montana-time-capsule/s3-ls-hmc-mtc-20260520T2015Z-supersplat_bundle-20260521T223600Z-head200.txt
- Hosted preview viewer reachability (alias):
  - skybox+no-sky URLs: logs/montana-time-capsule/heartbeat-viewer-urls-20260521T223600Z.txt
  - HTTP 200 headers: logs/montana-time-capsule/curlI-hosted-viewer-skybox-20260521T223600Z.headers; logs/montana-time-capsule/curlI-hosted-viewer-nosky-20260521T223600Z.headers
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T223600Z.json ([]; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T223600Z.json

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-21T22:38:22Z Post-push CI proof (HMC)

- Git head pushed: e0ef40ca5c2a8b9c83d6ab151dfb5db15f7d91ab ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T223822Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260521T223822Z.json)

## 2026-05-21T21:56:52Z HEARTBEAT monitor (HMC) - terminal state reconfirmed (no new launches)

- Git: agent-40136728-montana-time-capsule @ 33eb078bb2e7fdbbd1730c43b2cd7fa18cd296d1 (clean) ([skip ci])
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T215516Z.json (acct 975050048887)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T215516Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T215516Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260521T215516Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-inprogress-20260521T215516Z.json; logs/montana-time-capsule/sagemaker-list-training-jobs-hmc-mtc-20260520T2015Z-inprogress-20260521T215516Z.json (0 each)
- S3:
  - SfM output tail: logs/montana-time-capsule/s3-ls-colmap-tail50-20260521T215614Z.txt
  - compressed supersplat bundle listing: logs/montana-time-capsule/s3-ls-supersplat-bundle-head200-20260521T215614Z.txt
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260521T215614Z.json
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T215630Z.json ([]; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T215630Z.json (latest success shows CDK Deploy on sha=0e48d07)

Next: remain idle; only proceed if a new explicit acceptance gate is requested (promotion/registry, etc.).

## 2026-05-21T21:58:06Z Post-push CI proof (HMC)

- Git head pushed: 83f7f13f9b2c3315193d59c123b330f08b2c05b1 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T215806Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260521T215806Z.json)
- Follow-up exact-head check after CI-proof commit: logs/montana-time-capsule/gh-run-list-exact-head-postpush2-20260521T215836Z.json ([]; expected)

## 2026-05-21T22:17:08Z HEARTBEAT monitor (HMC) - viewer + bundle still reachable (no launches)

- Git: agent-40136728-montana-time-capsule @ 5238a375453f111b86b8cd850b10b42079a5367c (clean) ([skip ci])
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T221534Z.json (acct 975050048887)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T221534Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T221534Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260521T221534Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-inprogress-20260521T221534Z.json; logs/montana-time-capsule/sagemaker-list-training-jobs-hmc-mtc-20260520T2015Z-inprogress-20260521T221534Z.json (0 each)
- S3:
  - compressed supersplat bundle listing: logs/montana-time-capsule/s3-ls-supersplat-bundle-head200-20260521T221640Z.txt
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260521T221640Z.json
- Hosted preview viewer reachability (alias):
  - skybox URL: logs/montana-time-capsule/heartbeat-skybox-url-20260521T221640Z.txt (headers=logs/montana-time-capsule/curlI-hosted-viewer-skybox-20260521T221640Z.headers; HTTP 200)
  - no-sky URL: logs/montana-time-capsule/heartbeat-nosky-url-20260521T221640Z.txt (headers=logs/montana-time-capsule/curlI-hosted-viewer-nosky-20260521T221640Z.headers; HTTP 200)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T221708Z.json ([]; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T221708Z.json

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-21T22:18:59Z Post-push CI proof (HMC)

- Git head pushed: fac5e2bb5bc062351b559a8fef99a9ad4394e442 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T221859Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260521T221859Z.json)

## 2026-05-21T20:39:50Z Monitor tick (HMC) - 3DGS+compression Completed; hosted viewer validated (skybox + no-sky)

- Git: agent-40136728-montana-time-capsule @ 274e9112fd7fcc7a9d414c18f07fc6041c623535 (clean)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T203507Z.json (acct 975050048887)
- SageMaker:
  - 3DGS job (training): hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T203520Z.json)
  - compression job (processing): hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260521T203524Z.json)
  - runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T203812Z.log (state-file=logs/montana-time-capsule/hmc-state.json; status=completed; viewer_bundle_s3_uri=s3://spaceport-ml-processing-staging/compressed/hmc-mtc-20260520T2015Z/supersplat_bundle/meta.json)
- S3:
  - compressed outputs present (includes `supersplat_bundle/meta.json` + `background_skybox.webp`): logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-20260521T203552Z-head200.txt
- Hosted preview viewer (alias): https://agent-40136728-montana-time.v0-spaceport-website-preview2.pages.dev
  - proxy meta: logs/montana-time-capsule/hosted-proxy-url-hmc-meta-20260521T203633Z.txt (curl=logs/montana-time-capsule/curl-hosted-proxy-hmc-meta-20260521T203633Z.json)
  - proxy skybox: logs/montana-time-capsule/hosted-proxy-url-hmc-skybox-20260521T203633Z.txt (headers=logs/montana-time-capsule/curl-hosted-proxy-hmc-skybox-20260521T203633Z.headers)
  - viewer URL (skybox): logs/montana-time-capsule/hosted-viewer-url-hmc-skybox-20260521T203643Z.txt
  - viewer URL (no-sky): logs/montana-time-capsule/hosted-viewer-url-hmc-nosky-20260521T203643Z.txt
  - automated smoke (skybox): logs/montana-time-capsule/test-sogs-migrated-viewer-hmc-skybox-20260521T203730Z.txt (screenshot=logs/montana-time-capsule/sogs-migrated-viewer-smoke.png)
  - automated smoke (no-sky): logs/montana-time-capsule/test-sogs-migrated-viewer-hmc-nosky-20260521T203744Z.txt (screenshot=logs/montana-time-capsule/sogs-migrated-viewer-nosky.png)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T203618Z.json ([]; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T203612Z.json (last Pages deploy success sha=88b1848)

Next: HMC is at terminal output (compressed bundle + hosted viewer validated). If/when a new acceptance gate requires public promotion or publishing to a canonical bundle registry, do that as a separate, explicit stage.

## 2026-05-22T00:41:25Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer/proxy reachable + exact-head CI confirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ 813bc3f26644808ba676008234e8758f44c6a160 (clean) ([skip ci])
- AWS (us-west-2; /opt/homebrew/bin/aws): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T004125Z.json (acct 975050048887)
- SageMaker (/opt/homebrew/bin/aws):
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260522T004125Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260522T004125Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260522T004125Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T004125Z.json (2; not HMC); logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T004125Z.json (0)
- S3 (supersplat bundle; /opt/homebrew/bin/aws):
  - bundle listing: logs/montana-time-capsule/s3-ls-spaceport-ml-processing-staging-compressed_hmc-mtc-20260520T2015Z_supersplat_bundle_-20260522T004125Z-head200.txt (Total Objects: 13; Total Size: 6.8 MiB)
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-spaceport-ml-processing-staging-20260522T004125Z-meta.json
- Hosted preview viewer reachability:
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T004125Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T004125Z.headers; HTTP 200)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T004125Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T004125Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T004125Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T004125Z.headers; HTTP 200)
- CI (/opt/homebrew/bin/gh):
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T004125Z.json (0; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T004125Z.json (latest success sha=0e48d07)

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-22T00:43:20Z Post-push CI proof (HMC)

- Git head pushed: d9ea1dcd00fe24fa5a7c4709126a2f3ced17f82c ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260522T004320Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260522T004320Z.json)

## 2026-05-21T20:41:22Z Post-push CI proof (HMC)

- Git head pushed: 03df0096ba1175c4b3524eb0cb50c6e66e7a9b63 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T204113Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260521T204118Z.json)

## 2026-05-21T20:56:51Z Monitor tick (HMC) - terminal state reconfirmed (no new launches)

- Git: agent-40136728-montana-time-capsule @ 7fd899318c6d0fab44a9acb65640ef34d25c421d (clean)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T205505Z.json (acct 975050048887)
- SageMaker:
  - 3DGS job (training): hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T205515Z.json)
  - compression job (processing): hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260521T205515Z.json)
  - runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T205651Z.log (state-file=logs/montana-time-capsule/hmc-state.json; status=completed; viewer_bundle_s3_uri=s3://spaceport-ml-processing-staging/compressed/hmc-mtc-20260520T2015Z/supersplat_bundle/meta.json)
- S3:
  - compressed outputs present: logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-20260521T205515Z-head200.txt
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260521T205530Z.json
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T205551Z.json ([]; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T205551Z.json (latest shows CDK Deploy success sha=0e48d07)

Next: HMC remains at terminal output (compressed bundle + hosted viewer previously validated). No further stage is unblocked without an explicit new acceptance gate (e.g., promotion/publishing).

## 2026-05-21T19:58:16Z Post-push CI proof (HMC)

- Git head pushed: 0882a830377a3cb26b6bca6dc975d0e838788545 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T195812Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260521T195812Z.json)

## 2026-05-21T19:56:41Z Monitor tick (HMC) - 3DGS still InProgress (no new CloudWatch events)

- Git: agent-40136728-montana-time-capsule @ e270efb69758977fe67d1b5a8ad1959c9770a3a1
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T195501Z.json (acct 975050048887)
- SageMaker:
  - SfM job (processing): hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T195506Z.json)
  - 3DGS job (training): hmc-mtc-20260520T2015Z-3dgs status=InProgress (SecondaryStatus=Training; LastModifiedTime=2026-05-21T10:40:55-06:00) (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T195506Z.json; summary=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T195621Z-summary.json)
- CloudWatch:
  - Streams: logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-3dgs-20260521T195550Z.json (best=logs/montana-time-capsule/cloudwatch-best-stream-hmc-mtc-20260520T2015Z-3dgs-20260521T195550Z.txt)
  - Tail: logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-3dgs-20260521T195550Z-tail200.json (last event timestamp ms=1779382018947; last message head shows 2026-05-21 16:46:58)
- S3:
  - 3DGS output prefix still empty: logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-3dgs-20260521T195612Z-maxkeys50.json (KeyCount=0)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T195636Z.json (0 runs; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T195636Z.json (latest Pages deploy success is older head sha=88b1848)

Next: keep polling until `describe-training-job` is Completed; do not launch compression until 3DGS is Completed.

## 2026-05-21T19:40:35Z Post-push CI proof (HMC)

- Git head pushed: 786d645ab665c9b9b48f8c5bfe313b8b211fe2f9 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T193954Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260521T193954Z.json)

## 2026-05-21T19:38:46Z Monitor tick (HMC) - 3DGS still InProgress (no new logs since 16:46Z)

- Git: agent-40136728-montana-time-capsule @ 4da631d681793d3857f52e9455a592921d2af940 (status=logs/montana-time-capsule/git-status-20260521T194011Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T193532Z.json (acct 975050048887)
- SageMaker:
  - SfM job (processing): hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T193640Z.json)
  - 3DGS job (training): hmc-mtc-20260520T2015Z-3dgs status=InProgress (SecondaryStatus=Training; LastModifiedTime unchanged since 2026-05-21T10:40:55-06:00) (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T193722Z.json)
  - CloudWatch streams: logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-3dgs-20260521T193724Z.json (best=logs/montana-time-capsule/cloudwatch-best-stream-hmc-mtc-20260520T2015Z-3dgs-20260521T193724Z.txt)
  - CloudWatch tail: logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-3dgs-20260521T193724Z-tail200.json (last event timestamp ms=1779382018947; last message head shows 2026-05-21 16:46:58)
- S3:
  - 3DGS output prefix still empty: logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-3dgs-20260521T193722Z-maxkeys50.json (KeyCount=0)
- Runner:
  - State refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T193846Z.log (updated_at=2026-05-21T19:38:46Z; status=3dgs_running)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T193812Z.json (0 runs; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T193812Z.json (latest Pages deploy success is older head sha=88b1848)

Next: keep polling until `describe-training-job` is Completed; do not launch compression until 3DGS is Completed.

## 2026-05-21T18:59:11Z Post-push CI proof (HMC)

- Git head pushed: bf33d0e2ea4a07e47449c3c8ef1c27cf666e8229 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T185911Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260521T185911Z.json)

## 2026-05-21T19:18:43Z Post-push CI proof (HMC)

- Git head pushed: daded081f4fc8c21601ae010df6fae693de0ff58 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T191843Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260521T191843Z.json)

## 2026-05-21T19:16:59Z Monitor tick (HMC) - 3DGS still InProgress

- Git: agent-40136728-montana-time-capsule @ 3ff7c291a30f7c4ea87352cbd48e93046e48c20b (status=logs/montana-time-capsule/git-status-20260521T191454Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T191454Z.json (acct 975050048887)
- SageMaker:
  - SfM job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T191620Z.json)
  - 3DGS job: hmc-mtc-20260520T2015Z-3dgs status=InProgress (SecondaryStatus=Training) (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T191620Z.json)
  - CloudWatch streams: logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-3dgs-20260521T191610Z.json (best=logs/montana-time-capsule/cloudwatch-best-stream-hmc-mtc-20260520T2015Z-3dgs-20260521T191610Z.txt)
  - CloudWatch tail: logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-3dgs-20260521T191610Z-tail200.json (last event timestamp ms=1779382018947; last message head shows 2026-05-21 16:46:58)
- S3:
  - SfM prefix non-empty: logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T191620Z-max20.json
  - 3DGS output prefix still empty: logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-3dgs-20260521T191641Z-maxkeys50.json (KeyCount=0)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T191659Z.json
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T191659Z.json

Next: keep polling until `describe-training-job` is Completed; do not launch compression until 3DGS is Completed.

## 2026-05-21T18:56:34Z Monitor tick (HMC) - 3DGS still InProgress

- Git: agent-40136728-montana-time-capsule @ 2546cd1456240efc218c032565e9852ad09bf55a (status=logs/montana-time-capsule/git-status-20260521T185634Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T185634Z.json (acct 975050048887)
- SageMaker:
  - SfM job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T185634Z.json)
  - 3DGS job: hmc-mtc-20260520T2015Z-3dgs status=InProgress (SecondaryStatus=Training) (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T185634Z.json)
  - CloudWatch streams: logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-3dgs-20260521T185634Z.json (best=logs/montana-time-capsule/cloudwatch-best-stream-hmc-mtc-20260520T2015Z-3dgs-20260521T185634Z.txt)
  - CloudWatch tail: logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-3dgs-20260521T185634Z-tail160.json (last event appears 2026-05-21T16:46:58.947Z)
- S3:
  - SfM prefix non-empty: logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T185634Z-max20.json
  - 3DGS output prefix still empty: logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-3dgs-20260521T185634Z-max50.json (KeyCount=0)
- CI:
  - exact-head runs: 0 (expected due to no push) logs/montana-time-capsule/gh-run-list-exact-head-20260521T185655Z.json
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T185655Z.json

Next: keep polling until `describe-training-job` is Completed; do not launch compression until 3DGS is Completed.

## 2026-05-21T18:39:17Z Post-push CI proof (HMC)

- Git head pushed: a3da53fbb91990b815217c894ccb4884f34fdd0f ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T183909Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260521T183909Z.json)

## 2026-05-21T18:37:57Z Monitor tick (HMC) - 3DGS still InProgress

- Git: agent-40136728-montana-time-capsule @ 8252b2f21781ccd35e0c4d9b97214a91c5067c83 (status=logs/montana-time-capsule/git-status-20260521T183757Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T183556Z.json (acct 975050048887)
- SageMaker:
  - SfM job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T183556Z.json)
  - 3DGS job: hmc-mtc-20260520T2015Z-3dgs status=InProgress (SecondaryStatus=Training) (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T183556Z.json)
  - CloudWatch streams: logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-3dgs-20260521T183612Z.json (best=hmc-mtc-20260520T2015Z-3dgs/algo-1-1779381402)
  - CloudWatch tail: logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-3dgs-20260521T183612Z-tail120.json (last event appears 2026-05-21T16:46:58Z)
- S3:
  - SfM prefix non-empty: logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T183648Z-max20.json (KeyCount=20; truncated)
  - 3DGS output prefix still empty: logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-3dgs-20260521T183648Z-max50.json (KeyCount=0)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T183747Z.log (state file logs/montana-time-capsule/hmc-state.json; status=3dgs_running; sfm_status=Completed; 3dgs_status=InProgress)
- CI:
  - exact-head runs: 0 (expected due to [skip ci]) logs/montana-time-capsule/gh-run-list-exact-head-20260521T183718Z.json
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T183718Z.json

Next: keep polling until `describe-training-job` is Completed; do not launch compression until 3DGS is Completed.

## 2026-05-21T17:36:40Z Monitor tick (HMC) - 3DGS still InProgress

- Git: agent-40136728-montana-time-capsule @ 8b199e9b4c07c2020a7da0b7a00488856fcf9032 (status=logs/montana-time-capsule/git-status-20260521T173640Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T173439Z.json (acct 975050048887)
- SageMaker:
  - SfM job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T173439Z.json)
  - 3DGS job: hmc-mtc-20260520T2015Z-3dgs status=InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T173439Z.json)
  - CloudWatch stream discovery: logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-3dgs-20260521T173640Z.json (best=logs/montana-time-capsule/cloudwatch-best-stream-hmc-mtc-20260520T2015Z-3dgs-20260521T173640Z.txt)
  - CloudWatch tail (since2h): logs/montana-time-capsule/cloudwatch-filter-log-events-hmc-mtc-20260520T2015Z-3dgs-20260521T173640Z-since2h-limit120.json
- S3:
  - 3DGS output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-3dgs-20260521T173439Z-maxkeys10.json
  - 3DGS s3 ls: logs/montana-time-capsule/s3-ls-ml-processing-staging-3dgs-hmc-mtc-20260520T2015Z-20260521T173439Z-tail20.txt
- CI:
  - exact-head runs: 0 (expected due to [skip ci]) logs/montana-time-capsule/gh-run-list-exact-head-20260521T173602Z.json
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T173602Z.json

Next: keep polling until `describe-training-job` is Completed; do not launch compression until 3DGS is Completed.

## 2026-05-21T17:38:10Z Post-push CI proof (HMC)

- Git head pushed: 921c33e45c380c92ac2956e9cfba798f3455d94d ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T173810Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260521T173810Z.json)

## 2026-05-21T17:18:00Z Monitor tick (HMC) - 3DGS still InProgress

- Git: agent-40136728-montana-time-capsule @ 3489fef6ec6d32fa983d755d12259e2e26685e08 (status=logs/montana-time-capsule/git-status-20260521T171800Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T171456Z.json (acct 975050048887)
- SageMaker 3DGS:
  - job: hmc-mtc-20260520T2015Z-3dgs (pinned image sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db)
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T171456Z.json)
  - CloudWatch stream discovery: logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-3dgs-20260521T171609Z.json (best=logs/montana-time-capsule/cloudwatch-best-stream-hmc-mtc-20260520T2015Z-3dgs-20260521T171609Z.txt)
  - CloudWatch tail (no-start-from-head): logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-3dgs-20260521T171632Z-tail120.json (last log message timestamp appears 2026-05-21 16:46:58 UTC)
  - output prefix currently empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-3dgs-20260521T171456Z-max10.json (ls=logs/montana-time-capsule/s3-ls-ml-processing-staging-3dgs-hmc-mtc-20260520T2015Z-20260521T171456Z-tail20.txt)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T171748Z.log (state file logs/montana-time-capsule/hmc-state.json; 3dgs_status=InProgress)
- CI:
  - exact-head runs: 0 (expected due to [skip ci]) logs/montana-time-capsule/gh-run-list-exact-head-20260521T171738Z.json
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T171738Z.json

Next: keep polling until `describe-training-job` is Completed; do not launch compression until 3DGS is Completed.

## 2026-05-21T16:36:10Z Monitor tick (HMC) - launched 3DGS

- Git: agent-40136728-montana-time-capsule @ 8fea5bef9ac498f49137311f5bd7774507194c39 (`chore: record post-push proof 20260521T1617Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T163428Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T163428Z.json)
  - output prefix non-empty: logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T163428Z-max5.json (KeyCount=5); logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T163428Z-tail5.txt (Total Objects: 2070; Total Size: 12.0 GiB)
- CI:
  - exact-head runs: 0 (expected due to [skip ci]) logs/montana-time-capsule/gh-run-list-exact-head-20260521T163442Z.json
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T163442Z.json
- SageMaker 3DGS:
  - runner launch: logs/montana-time-capsule/hmc-launch-20260521T163544Z.log
  - job: hmc-mtc-20260520T2015Z-3dgs (pinned image sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db)
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T163601Z.json)
  - output prefix currently empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-3dgs-20260521T163601Z-max5.json

Next: poll until 3DGS becomes Completed; do not launch compression until `describe-training-job` is Completed.

## 2026-05-21T16:38:28Z Post-push CI proof (HMC)

- Git head pushed: a0e92de04cb7816aa4e7c18e4320ce40f55995db ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T163814Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260521T163814Z.json)

## 2026-05-21T16:14:37Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ dbbdbbcdeaaf6eab47441127dcb17663e683a801 (`chore: record post-push proof 20260521T1557Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T161437Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T161437Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T161437Z.json)
  - CloudWatch best stream: logs/montana-time-capsule/cloudwatch-best-stream-hmc-mtc-20260520T2015Z-sfm-20260521T161437Z.txt (tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T161437Z-tail50.json; message shows `Completed at: Thu May 21 16:02:11 UTC 2026`)
  - output prefix now non-empty (Total Objects: 2070; Total Size: 12.0 GiB): logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T161437Z.txt (list-objects=logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T161437Z-max50.json)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T161437Z.txt
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T161437Z.txt ([skip ci] expected)

Next: keep polling until `describe-processing-job` reports Completed; do not launch 3DGS until SageMaker status flips.

## 2026-05-21T16:17:19Z Post-push CI proof (HMC)

- Git head pushed: cc7b05110e20019927eb069f1c6b1d07c4bd6a13 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T161719Z.txt; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T161719Z.txt)

## 2026-05-21T15:36:52Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 7a416db7052f1e6c8f116b66a25e0d88a26d9595 (`chore: record post-push ci proof 20260521T1519Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T153446Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T153446Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T153446Z.json)
  - CloudWatch newest tail still shows COLMAP linear solver failure warning at 2026-05-21T15:29:56Z: logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T153518Z-tail50.json (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T153506Z.json; best=logs/montana-time-capsule/cloudwatch-best-stream-hmc-mtc-20260520T2015Z-sfm-20260521T153506Z.txt)
  - output prefix still empty (S3UploadMode=EndOfJob; KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T153506Z-max5.json (ls=logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T153506Z-tail50.txt)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T153550Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress; last_cloudwatch_event_at=2026-05-21T15:29:56.196Z)
- CI: exact head is [skip ci] (branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T153423Z.json; exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T153423Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 20260521T181746Z Monitor tick (HMC) - 3DGS still InProgress

- Git: agent-40136728-montana-time-capsule @ 08258b12f691d0714a89453fcd4dc6b652befe28 (status=logs/montana-time-capsule/git-status-20260521T181451Z.txt; `[skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T181451Z.json (acct 975050048887)
- SageMaker:
  - 3DGS job: hmc-mtc-20260520T2015Z-3dgs status=InProgress (SecondaryStatus=Training) (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T181523Z.json)
  - CloudWatch best stream: logs/montana-time-capsule/cloudwatch-best-stream-hmc-mtc-20260520T2015Z-3dgs-20260521T181551Z.txt (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-3dgs-20260521T181551Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-3dgs-20260521T181551Z-tail80.json)
- S3:
  - 3DGS output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-3dgs-hmc-mtc-20260520T2015Z--20260521T181534Z-maxkeys10.json (ls=logs/montana-time-capsule/s3-ls-spaceport-ml-processing-staging-3dgs-hmc-mtc-20260520T2015Z--20260521T181534Z-recursive-head200.txt)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T181746Z.log (state file logs/montana-time-capsule/hmc-state.json; status=3dgs_running)
- CI:
  - exact-head runs: 0 (expected due to `[skip ci]`) logs/montana-time-capsule/gh-run-list-exact-head-20260521T181640Z.json
  - branch runs: logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T181640Z.json

Next: keep polling until 3DGS is Completed and the S3 output prefix becomes non-empty; then run exactly one guarded `--launch` to start compression (pinned sha256:a0784727da1870ce9caa4774dc831a32fb96cd1574df389cf9093fbf18f4f4ab).

## 20260521T182000Z Post-push CI proof (HMC)

- Git head pushed: 271f29f2b95c2337e2b2f7d0e2d1afadf57a5cd1 ([skip ci])
- Exact-head workflow runs: 0 (expected due to `[skip ci]`) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T182000Z.json)

## 2026-05-21T17:58:35Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ c438fc7a83f75ff84a43cef925c89c44063c773a (`chore: record post-push proof 20260521T1738Z [skip ci]`)
  - status: logs/montana-time-capsule/git-status-20260521T175835Z.txt
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T175459Z.json (acct 975050048887)
- Input archive (no re-upload):
  - s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip (head=logs/montana-time-capsule/s3api-head-object-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260521T175645Z.json; ContentLength=8646557673; ETag=ed86661a82b28856997a09f129ce6bec-1031)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T175534Z.json)
  - output prefix non-empty: logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T175459Z-tail50.txt (database.db + sfm_metadata.json + images/ + sparse/)
- SageMaker 3DGS (pinned sha256:482c1789…):
  - job: hmc-mtc-20260520T2015Z-3dgs
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T175541Z.json)
  - CloudWatch tail: logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-3dgs-20260521T175621Z-tail80.json (training started; COLMAP->transforms validated; 2022/2063 images have poses)
  - S3 output prefix still empty (expected while InProgress): logs/montana-time-capsule/s3-ls-ml-processing-staging-3dgs-hmc-mtc-20260520T2015Z-20260521T175628Z-recursive-head200.txt
- Runner state updated: logs/montana-time-capsule/hmc-state.json (status=3dgs_running; sfm_status=Completed; 3dgs_status=InProgress; updated_at=2026-05-21T17:58:05Z)
- CI:
  - exact head is [skip ci] -> no exact-head workflow runs (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T175459Z.json)
  - last known successful runs on this branch: Pages run 26200368328 (headSha 88b1848) + CDK run 26223584298 (headSha 0e48d07) (branch list=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T175459Z.json)

Next: keep polling until 3DGS becomes Completed and output artifacts appear; then launch compression (pinned sha256:a0784727…).

## 2026-05-21T18:00:33Z Post-push CI proof (HMC)

- Git head pushed: 047afeabcb8c7e90313c1dc05c8799b3f1fa384e ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T180021Z.json)

## 20260521T155623Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 2eceea3a6897f40e31bd02964aaeb9da665bca2b (`chore: record post-push ci proof 20260521T1538Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T155452Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T155503Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T155509Z.json)
  - CloudWatch best stream: logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T155515Z.json (tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T155525Z-tail50.json; last event 2026-05-21T15:54:16Z is linear solver failure warning)
  - output prefix still empty (S3UploadMode=EndOfJob; KeyCount=0): logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T155543Z-max20.json (ls=logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T155535Z-tail50.txt)
- Input zip head: logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat-20260521T155623Z.json (etag=ed86661a82b28856997a09f129ce6bec-1031; size=8646557673)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T155552Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T155623Z.json (latest Pages + CDK green are on non-[skip ci] heads; see gh-run-26200368328-pages.txt for PREVIEW_URL)
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T155623Z.json (count=0; [skip ci] expected)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 20260521T155740Z Post-push CI proof (HMC)

- Git head pushed: e56ec5010af90f7f97448c9530579426d39484ab ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T155623Z.json; exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T155623Z.json)

## 2026-05-21T15:37:59Z Post-push CI proof (HMC)

- Git head pushed: 58ccf7af2e1f219cc5d184724fa5b6d497f54582 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T153751Z.json)

## 2026-05-21T15:16:53Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 85126f21be33b571e3904dc09a2d31027f254b35 (`chore: record post-push ci proof 20260521T143613Z [skip ci]`)
  - status: logs/montana-time-capsule/git-status-20260521T151504Z.txt
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T151504Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T151504Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T151504Z.json)
  - CloudWatch tail shows COLMAP linear solver failure warning at 2026-05-21T15:09:52Z: logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T151504Z-tail50.json (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T151504Z.json; best=logs/montana-time-capsule/cloudwatch-best-stream-hmc-mtc-20260520T2015Z-sfm-20260521T151504Z.txt)
  - output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T151535Z-max5.json (ls=logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T151504Z-tail50.txt)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T151652Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress; updated_at=2026-05-21T15:16:53Z)
- CI: exact head is [skip ci] (branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T151504Z.json; exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T151504Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T15:19:33Z Post-push CI proof (HMC)

- Git head pushed: 2cfcbf01e3ac4c2d0c0a704145f2b842082eeb9b ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T151933Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T151933Z.json)

## 2026-05-21T12:14:10Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 5a769d84ad64fb19a85eeb0da00f2cfe2f72cf90 (`chore: record post-push ci proof 20260521T1158Z [skip ci]`)
  - status: logs/montana-time-capsule/git-status-20260521T121410Z.txt
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T121410Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T121410Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T121410Z.json)
  - CloudWatch newest stream last event still 2026-05-21T00:01:36Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T121410Z.json; best=logs/montana-time-capsule/cloudwatch-best-stream-hmc-mtc-20260520T2015Z-sfm-20260521T121410Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T121410Z-tail50.json; last=logs/montana-time-capsule/cloudwatch-last-event-hmc-mtc-20260520T2015Z-sfm-20260521T121410Z.txt)
  - output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T121410Z.json (ls=logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T121410Z-tail50.txt)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T121410Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress)
- CI: exact head is [skip ci] (branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T121410Z.json; exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T121410Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.


## 20260521T143613Z Post-push CI proof (HMC)

- Git head pushed: 24dd7c63c41bd61dc36b069251cbcef976fb73e5 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T143613Z.json)
- Branch run list: logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T143613Z.json

## 2026-05-21T13:57:02Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ b4bbfecebe2ed8c8c32a71779820db076ab44ef9 (`chore: record post-push ci proof 20260521T1338Z [skip ci]`)
  - status: logs/montana-time-capsule/git-status-20260521T135502Z.txt
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T135502Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-status-20260521T135502Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T135502Z.json)
  - CloudWatch last tail message at ~2026-05-21T13:50:08Z: logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T135502Z-tail50.json
  - output prefix still empty (S3UploadMode=EndOfJob; KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T135502Z.json (ls=logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T135502Z-tail25.txt)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T135502Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress; updated_at=2026-05-21T13:56:05Z)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T135502Z.json
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T135502Z.json ([skip ci] expected)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T13:59:11Z Post-push CI proof (HMC)

- Git head pushed: 2d331e6049dc291da2f3302a40bf6140bdb69192 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T135911Z.json)

## 2026-05-21T13:38:27Z Post-push CI proof (HMC)

- Git head pushed: ec13ae76c4f88e286c18d7670bf9c951c469c80b ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T133819Z.json)

## 2026-05-21T13:36:51Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ e490877f5a14e2be38aeb4e9455a890b38fdd4bc (`chore: record post-push ci proof 20260521T1316Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T133410Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-status-20260521T133411Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T133412Z.json)
  - CloudWatch newest stream last event at 2026-05-21T13:33:35Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T133435Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T133435Z-tail50.json)
  - output prefix still empty (S3UploadMode=EndOfJob; KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T133643Z.json
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T133635Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress; updated_at=2026-05-21T13:36:36Z)
- CI: exact head is [skip ci] (branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T133559Z.json; exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T133559Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T13:14:52Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 4754064be4c0f3d508f4528b8afa434eb387bf63 (`chore: montana time capsule sfm tick 20260521T1257Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T131434Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T131434Z.json)
  - CloudWatch last event: 2026-05-21T12:39:32Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T131452Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T131452Z-tail80.json)
  - output prefix still empty (KeyCount=0; S3UploadMode=EndOfJob): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T131434Z.json
- CI: exact head is [skip ci] (branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T131452Z.json; exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T131452Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; only then run ONE guarded runner invocation with `--launch` to advance to pinned 3DGS sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db.

## 2026-05-21T13:16:08Z Post-push CI proof (HMC)

- Git head pushed: 4206fb91b17c631f501dbb57b5be1b9a3ff7b697 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T131608Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T131608Z.json)

## 2026-05-21T12:34:07Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ d4640c2d4e564145741200940c4b725b4591154b (`chore: record post-push ci proof 20260521T1217Z (2) [skip ci]`)
  - status: logs/montana-time-capsule/git-status-20260521T123407Z.txt
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T123407Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T123407Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T123407Z.json)
  - CloudWatch last event now 2026-05-21T12:33:25Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T123407Z.json; best=logs/montana-time-capsule/cloudwatch-best-stream-hmc-mtc-20260520T2015Z-sfm-20260521T123407Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T123407Z-tail50.json; last=logs/montana-time-capsule/cloudwatch-last-event-hmc-mtc-20260520T2015Z-sfm-20260521T123407Z.txt)
  - output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T123407Z.json (ls=logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T123407Z-tail50.txt)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T123407Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress)
- CI: exact head is [skip ci] (branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T123407Z.json; exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T123407Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T12:34:07Z Post-push CI proof (HMC)

- Git head pushed: 95a8457e1bb5c1c317172fae09a4d707b053a7bc ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T123450Z.json)

## 2026-05-21T12:17:09Z Post-push CI proof (HMC)

- Git head pushed: 89d6ed70767ba61bdeac519e52576f3df82f3348 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T121709Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T121709Z.json)

## 2026-05-21T12:17:55Z Post-push CI proof (HMC)

- Git head pushed: f94987d73e615a963714d6b369d6f5177bcc873b ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T121755Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T121755Z.json)

## 2026-05-21T10:16:01Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 682c76791c4ec34365ada433a203193d245ca151 (`chore: record post-push ci proof 20260521T0957Z [skip ci]`)
  - status: logs/montana-time-capsule/git-status-20260521T101403Z.txt
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T101403Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T101403Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T101403Z.json)
  - CloudWatch newest stream last event still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T101403Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T101403Z-tail.json; last=logs/montana-time-capsule/cloudwatch-last-event-hmc-mtc-20260520T2015Z-sfm-20260521T101403Z.tsv)
  - output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T101403Z.json
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T101403Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress; updated_at=2026-05-21T10:16:01Z)
- CI: exact head is [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T101403Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T101403Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T11:58:43Z Post-push CI proof (HMC)

- Git head pushed: 906770a4511f57c3d61122fb9c9426a0f926259c ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T115837Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T115837Z.json)

## 2026-05-21T11:57:26Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ c9836342b95844382868539d4694fa46baef330a (`chore: record CI success 20260521T1142Z [skip ci]`)
  - status: (see `git status --porcelain` in working tree; logs added below)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T115444Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T115444Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T115444Z.json)
  - CloudWatch newest stream last event still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T115617Z.json; best=logs/montana-time-capsule/cloudwatch-best-stream-hmc-mtc-20260520T2015Z-sfm-20260521T115617Z.json; since6h=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T115617Z-since6h.json; last=logs/montana-time-capsule/cloudwatch-last-event-hmc-mtc-20260520T2015Z-sfm-20260521T115617Z.tsv)
  - output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T115444Z.json (ls=logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T115444Z-tail50.txt)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T115628Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress; updated_at=2026-05-21T11:56:29Z)
- CI: exact head is [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T115444Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T115444Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T11:16:36Z Post-push CI proof (HMC)

- Git head pushed: 25bd3c0fa299e53c68a69f4ac5cbfa58c6dcae74 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T111636Z.txt; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T111636Z.txt)

## 2026-05-21T10:56:20Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ da4ef63c9a5bbe26ca0d05066172125c304dce01 (`chore: record post-push ci proof 20260521T1037Z [skip ci]`)
  - status: logs/montana-time-capsule/git-status-20260521T105617Z.txt
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T105416Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T105416Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T105416Z.json)
  - CloudWatch newest stream last event timestamp still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T105453Z.json; around_last=logs/montana-time-capsule/cloudwatch-filter-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T105522Z-around-last.json)
  - output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T105538Z.json (ls=logs/montana-time-capsule/s3-ls-spaceport-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T105538Z.txt)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T105612Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress; updated_at=2026-05-21T10:56:13Z)
- CI: exact head is [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T105555Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T105555Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T10:58:20Z Post-push CI proof (HMC)

- Git head pushed: 2c4a247f51b2df1cf36a8377d918f8b24890db5d ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T105811Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T105811Z.json)

## 2026-05-21T10:17:31Z Post-push CI proof (HMC)

- Git head pushed: 7068a12a3f72c30d0cc469d09d5d8b8b614baa4b ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T101731Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T101731Z.json)

## 2026-05-21T08:53:52Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 734cea93965e920f4364186dd23c1f1a52576224 (`chore: record post-push ci proof 20260521T0837Z [skip ci]`)
  - status: logs/montana-time-capsule/git-status-20260521T085352Z.txt
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T085352Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T085352Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T085352Z.json)
  - CloudWatch last event still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T085352Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T085352Z-tail.json; last=logs/montana-time-capsule/cloudwatch-last-event-hmc-mtc-20260520T2015Z-sfm-20260521T085352Z.tsv)
  - output prefix still empty: logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T085352Z.json
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T085352Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress; updated_at=2026-05-21T08:55:13Z)
- CI: exact head is [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T085352Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T085352Z.json)
- Post-push CI proof: head is [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T085822Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T085822Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T09:56:35Z Post-push CI proof (HMC)

- Git head pushed: 5701caeb0ffabd35e13538d9ac83db3d72def135 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T095732Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T095732Z.json)

## 2026-05-21T09:16:09Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 428c20a46b1ba2e7ec32ea81ce51d62942adf8a1 (`chore: update HMC heartbeat ledger 20260521T0858Z [skip ci]`)
  - status: logs/montana-time-capsule/git-status-20260521T091609Z.txt
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T091609Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T091609Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T091609Z.json)
  - CloudWatch newest stream last event still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T091609Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T091609Z-tail.json; last=logs/montana-time-capsule/cloudwatch-last-event-from-streams-hmc-mtc-20260520T2015Z-sfm-20260521T091609Z.txt)
  - output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T091609Z.json
- CI: exact head is [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T091609Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T091609Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T09:18:02Z Post-push CI proof (HMC)

- Git: agent-40136728-montana-time-capsule @ 594a4056c2ced069b853567bb08fac070d6e7494 (`chore: monitor HMC sfm heartbeat 20260521T0916Z [skip ci]`)
- Push: `git push origin agent-40136728-montana-time-capsule` (updated `428c20a4..594a4056`)
- CI: exact head is [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T091802Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T091802Z.json)
- CI: verified current exact head is also [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T091833Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T091833Z.json)

## 2026-05-21T09:38:31Z Post-push CI proof (HMC)

- Git: agent-40136728-montana-time-capsule @ fbdfbd824ac24c8b3d67730ec3c242cf4a1df720 (`chore: monitor HMC sfm heartbeat 20260521T0936Z [skip ci]`)
- Push: `git push origin agent-40136728-montana-time-capsule` (updated `980465cb..fbdfbd82`)
- CI: exact head is [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T093831Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T093831Z.json)

## 2026-05-21T09:36:33Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 980465cb31fe3be8b273ae722ede2e9bdd3c4b92 (`chore: update ci proof 20260521T0918Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T093519Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T093430Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T093430Z.json)
  - CloudWatch newest stream still lastEvent=2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T093440Z.json; newest=logs/montana-time-capsule/cloudwatch-newest-stream-hmc-mtc-20260520T2015Z-sfm-20260521T093440Z.txt; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T093440Z-tail.json)
  - output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T093431Z.json
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T093610Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress; updated_at=2026-05-21T09:36:11Z)
- CI: exact head is [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T093624Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T093624Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T08:14:10Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ b632f75e6554e0664525b189ada46127492a763f (`chore: monitor HMC Montana SfM 20260521T0754Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T081410Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T081410Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T081410Z.json)
  - CloudWatch newest event still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T081410Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T081410Z-head.json)
  - output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T081410Z.json
- CI: exact head is [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T081410Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T081410Z.json)
- Post-push CI proof: head is [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T081756Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T081756Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T07:54:35Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ e4a789abe6d03a56f2ffdaac18fd81b873aebb77 (`chore: record post-push ci proof 20260521T0738Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T075435Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T075435Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T075435Z.json)
  - CloudWatch lastEvent still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T075435Z-retry.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T075435Z-tail2.json)
  - output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T075435Z.json
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T075435Z.json (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress)
- CI: exact head is [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T075435Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T075435Z.json)

Next: keep polling until SfM becomes Completed and S3 output exists; do not launch 3DGS yet.

## 2026-05-21T06:16:15Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 8ba09babe25fb55982c6ac64767b1f1feb4856d7 (`chore: record post-push ci proof 20260521T0557Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T061427Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T061427Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T061427Z.json)
  - CloudWatch lastEvent still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T061427Z-retry.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm_algo-1-1779308230-20260521T061427Z-tail.json)
  - output prefix still empty (EndOfJob upload): logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T061427Z.txt (Total Objects: 0)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T061615Z.json (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress)
- CI: exact head is [skip ci]; latest branch run list refreshed at logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T061810Z.json (last green Pages+CDK unchanged).

Next: keep polling until SfM becomes Completed and S3 output exists; do not launch 3DGS yet.

## 2026-05-21T07:37:20Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 4d2530b697e0c4e0d47e4ee18e2a13b9f176614d (`chore: record post-push CI check 20260521T0716Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T073600Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T073600Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T073600Z.json)
  - CloudWatch lastEvent still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T073630Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T073630Z-tail.json)
  - output prefix still empty (EndOfJob upload): KeyCount=0 (logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T073600Z.json)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T073703Z.json (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress)
- CI: exact head is [skip ci]; run lists refreshed (branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T073703Z.json; exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T073703Z.json)
- Post-push CI check: exact head is [skip ci] so no workflow runs for this commit (branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T073822Z.json; exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T073822Z.json)

Next: keep polling until SfM becomes Completed and S3 output exists; do not launch 3DGS yet.

## 2026-05-21T06:55:45Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 6e3a166657bc04e01699127f18fb8fd4860a11e2 (`chore: monitor HMC Montana SfM 20260521T0637Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T065401Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T065401Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T065401Z.json)
  - CloudWatch lastEvent still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T065429Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T065429Z-aroundLastEvent.json)
  - output prefix still empty (EndOfJob upload): logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T065510Z.txt (Total Objects: 0; KeyCount=0 in logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T065534Z.json)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T065604Z.json (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress)
- CI: exact head is [skip ci] so no workflow runs for 6e3a1666; latest branch run list at logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T065545Z.json (last green Pages+CDK still 88b1848f).

Next: keep polling until SfM becomes Completed and S3 output exists; do not launch 3DGS yet.

## 2026-05-21T07:15:21Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ fbd7541f82848f77692734d98264a71f3bc90340 (`chore: record HMC poll artifacts 20260521T0655Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T071412Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T071412Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T071412Z.json)
  - CloudWatch lastEvent still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T071412Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T071412Z-tail.json)
  - output prefix still empty (EndOfJob upload): logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T071412Z.txt (KeyCount=0 in logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T071412Z.json)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T071503Z.json (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress)
- CI: exact head is [skip ci] so no workflow runs for fbd7541f; refreshed run lists:
  - branch: logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T071412Z.json
  - exact: logs/montana-time-capsule/gh-run-list-exact-head-20260521T071412Z.json
  - post-push branch: logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T071640Z.json
  - post-push exact: logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T071640Z.json

Next: keep polling until SfM becomes Completed and S3 output exists; do not launch 3DGS yet.

## Runner

- Command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --launch`
- Idempotent state: `logs/montana-time-capsule/cv-hr-state.json`
- Dataset: `CV-HR`
- Required upload: one CV-HR zip with exactly `1710` image files.
- Upload search bucket: `s3://spaceport-uploads-staging/`
- Current archive: `s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
- Current archive proof: `1710` images, `6,931,098,350` bytes, ETag `3a18e20f13027204f59bd6f1df77b983-827`, VersionId `FwGuzoiTEKNT8SodLXu7Zrkg_b96qhOx`.
- Output bucket: `s3://spaceport-ml-processing-staging/`

## Default Time Capsule Stack

Default profile: `brass-chunked`

- SfM image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`
- SfM env: `COLMAP_ENABLE_SPATIAL_CHUNKING=1`, `COLMAP_CHUNK_MIN_CORE_REGISTERED_RATIO=0.90`
- 3DGS image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`
- Compression image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor@sha256:a0784727da1870ce9caa4774dc831a32fb96cd1574df389cf9093fbf18f4f4ab`

Fallback profile: `horsetail-gps`, only after a proven default-profile failure.

## Resume Rules

1. Verify git branch/head/status and AWS identity first.
2. Do not launch duplicate CV-HR jobs. Read `cv-hr-state.json` before `--launch`.
3. Let the runner advance exactly one stage at a time: upload check, SfM, 3DGS, compression.
4. On a SageMaker failure, capture describe output, CloudWatch logs, S3 listings, and exact failure reason before patching.
5. Patch only a proven blocker and rerun the smallest failed stage.
6. Final acceptance requires the compressed bundle to load in the viewer with skybox and no-sky modes, plus visual quality evidence.

## 2026-05-18T17:29Z SfM Launch

- Archive validated by ZIP central-directory range reads: `1710` image entries, first `DJI_00001.JPG`, last `DJI_01710.JPG`.
- Command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
- Run id: `cvhr-mtc-20260518T1729Z`
- SfM job: `cvhr-mtc-20260518T1729Z-sfm`
- SfM ARN: `arn:aws:sagemaker:us-west-2:975050048887:processing-job/cvhr-mtc-20260518T1729Z-sfm`
- SfM status at launch verification: `InProgress`
- SfM input: `s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
- SfM output: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap`
- SfM image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`
- SfM instance: `ml.g4dn.xlarge`, volume `100` GB, max runtime `86400` seconds.
- SfM env: `COLMAP_ENABLE_SPATIAL_CHUNKING=1`, `COLMAP_CHUNK_MIN_CORE_REGISTERED_RATIO=0.90`.
- Log stream: `cvhr-mtc-20260518T1729Z-sfm/algo-1-1779125429`
- First live log proof: COLMAP feature extraction accepted the archive and was processing `4000 x 2250` images with GPS/gravity metadata; latest sampled progress at `2026-05-18T17:37Z` was `Processed file [56/1710]`.

## 2026-05-18T17:56Z Monitor Pass

- Branch/head/status command:
  - `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `31c5765c6227eaa6483f7e66758e9815c0d69ee1`, status clean (`## agent-40136728-montana-time-capsule...origin/agent-40136728-montana-time-capsule`).
- AWS identity command: `/opt/homebrew/bin/aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- SageMaker status command: `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress` for job `cvhr-mtc-20260518T1729Z-sfm` using pinned SfM image `sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CloudWatch stream command: `/opt/homebrew/bin/aws logs tail /aws/sagemaker/ProcessingJobs --since 20m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - Result: live COLMAP feature extraction progress observed through `Processed file [491/1710]`.
- Duplicate-job guard command: `/opt/homebrew/bin/aws sagemaker list-processing-jobs --name-contains cvhr-mtc-20260518T1729Z --max-results 10`
  - Result: only one matching processing job exists: `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`).
- Advance-one-stage command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: state now reports `last_action=sfm_running`, `status=sfm_running`, `sfm_status=InProgress`; no new stage launched and no duplicate job created.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260518T1756Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T1756Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-mtc-20260518T1729Z-20260518T1756Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T1756Z.log`
  - `logs/montana-time-capsule/launch-20260518T1755Z.log`
- Next unblocked step: wait for `cvhr-mtc-20260518T1729Z-sfm` to complete, then rerun `--launch` once to advance exactly one stage (3DGS launch).

## 2026-05-18T18:00Z Ledger Commit + Push

- Commit: `dfd66f0591b45bf2881c72ea27b098edcf828a0a`
- Commit message: `chore: record cv-hr montana sfm monitor evidence [skip ci]`
- Push command: `git push origin agent-40136728-montana-time-capsule`
- Push result: branch updated on origin (`31c5765c..dfd66f05`).
- Exact-head workflow check command:
  - `/opt/homebrew/bin/gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` (no exact-head workflows, expected for `[skip ci]` ledger-only commit).
- Branch workflow evidence (latest on branch): `logs/montana-time-capsule/gh-run-list-agent-40136728-20260518T1800Z.json`
- Exact-head workflow evidence: `logs/montana-time-capsule/gh-run-list-exact-head-20260518T1800Z.json`
- Next unblocked step: continue polling SfM `cvhr-mtc-20260518T1729Z-sfm`; when it reaches `Completed`, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to launch 3DGS.

## 2026-05-18T18:13Z Monitor Pass

- Branch/head/status command:
  - `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short --branch`
  - Result before this pass: branch `agent-40136728-montana-time-capsule`, head `f30edce52753ad59709711d5dbbdc6f9a430af18`, status clean (`## agent-40136728-montana-time-capsule...origin/agent-40136728-montana-time-capsule`).
- AWS identity command: `/opt/homebrew/bin/aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- SageMaker status command: `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress` for `cvhr-mtc-20260518T1729Z-sfm`; pinned SfM image unchanged (`sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`).
- CloudWatch stream command: `/opt/homebrew/bin/aws logs tail /aws/sagemaker/ProcessingJobs --since 20m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - Result: live COLMAP feature extraction observed through `Processed file [1011/1710]` at `2026-05-18T18:13:58Z`.
- Duplicate-job guard command: `/opt/homebrew/bin/aws sagemaker list-processing-jobs --name-contains cvhr-mtc-20260518T1729Z --max-results 20`
  - Result: still only one matching job (`cvhr-mtc-20260518T1729Z-sfm`, `InProgress`).
- Advance-one-stage command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: state remains `status=sfm_running`, `sfm_status=InProgress`; no new stage launched and no duplicate job created.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260518T181357Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T181357Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-mtc-20260518T1729Z-20260518T181357Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T181357Z.log`
  - `logs/montana-time-capsule/launch-20260518T181357Z.log`
- Next unblocked step: wait for `cvhr-mtc-20260518T1729Z-sfm` to complete, then run the same `--launch` command exactly once to launch 3DGS with the pinned Montana 3DGS image.

## 2026-05-18T18:17Z Monitor Pass

- SageMaker status command: `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`.
- CloudWatch stream command: `/opt/homebrew/bin/aws logs tail /aws/sagemaker/ProcessingJobs --since 20m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - Result: latest observed feature extraction progress `Processed file [1099/1710]`.
- Duplicate-job guard command: `/opt/homebrew/bin/aws sagemaker list-processing-jobs --name-contains cvhr-mtc-20260518T1729Z --max-results 20`
  - Result: still one matching processing job (`cvhr-mtc-20260518T1729Z-sfm`), no duplicates.
- Advance-one-stage command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: `status=sfm_running`; runner held position correctly and did not launch 3DGS early.
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T181722Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-mtc-20260518T1729Z-20260518T181722Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T181722Z.log`
  - `logs/montana-time-capsule/launch-20260518T181722Z.log`
- Next unblocked step: continue polling until SfM reaches `Completed`, then run `--launch` once to start 3DGS.

## 2026-05-18T18:18Z Ledger Commit + Push

- Commit: `483efaeb3c05d1f8647da38f73e98584d43b0807`
- Commit message: `chore: record cv-hr montana monitor poll [skip ci]`
- Push command: `git push origin agent-40136728-montana-time-capsule`
- Push result: branch updated on origin (`eed8727c..483efaeb`).
- Exact-head workflow check command:
  - `/opt/homebrew/bin/gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url`
  - Exact-head selection result for `483efaeb3c05d1f8647da38f73e98584d43b0807`: `[]` (no exact-head workflows, expected for `[skip ci]`).
- Branch workflow evidence: `logs/montana-time-capsule/gh-run-list-agent-40136728-20260518T181809Z.json`
- Exact-head workflow evidence: `logs/montana-time-capsule/gh-run-list-exact-head-20260518T181809Z.json`
- Next unblocked step: keep polling SfM until `Completed`, then run `--launch` exactly once to advance to 3DGS.

## 2026-05-18T18:33Z Monitor Pass

- Branch/head/status command:
  - `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `1281188169eed19054fcb6ae370c9e102e28b560`, status clean before this pass.
- AWS identity command: `/opt/homebrew/bin/aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- SageMaker status command: `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress` for `cvhr-mtc-20260518T1729Z-sfm`; pinned SfM image unchanged (`sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`).
- Duplicate-job guard command: `/opt/homebrew/bin/aws sagemaker list-processing-jobs --name-contains cvhr-mtc-20260518T1729Z --max-results 20`
  - Result: one matching processing job (`cvhr-mtc-20260518T1729Z-sfm`, `InProgress`); no duplicate jobs launched.
- Advance-one-stage command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: state held at `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`; runner did not launch 3DGS early.
- CloudWatch proof command: `/opt/homebrew/bin/aws logs tail /aws/sagemaker/ProcessingJobs --since 20m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - Result: live SfM feature extraction progressed through `Processed file [1522/1710]` at `2026-05-18T18:33:44Z`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260518T183327Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T183327Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-mtc-20260518T1729Z-20260518T183327Z.json`
  - `logs/montana-time-capsule/launch-20260518T183334Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T183346Z.log`
- Next unblocked step: continue polling until `cvhr-mtc-20260518T1729Z-sfm` reaches `Completed`, then run the same `--launch` command exactly once to launch 3DGS with the pinned Montana 3DGS image.

## 2026-05-18T18:34Z Ledger Commit + Push

- Commit: `ec78016b85165431f7487738ff00f39f5479aa56`
- Commit message: `chore: record montana sfm monitor pass [skip ci]`
- Push command: `git push origin agent-40136728-montana-time-capsule`
- Push result: branch updated on origin (`12811881..ec78016b`).
- Exact-head workflow check command:
  - `/opt/homebrew/bin/gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` (no exact-head workflows, expected for `[skip ci]` ledger-only commit).
- Branch workflow evidence (latest on branch):
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260518T183450Z.json`
- Exact-head workflow evidence:
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260518T183450Z.json`
- Last meaningful non-skip workflow proof retained:
  - `CDK Deploy` success on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442` run `26049509375`.
- Next unblocked step: continue polling SfM job `cvhr-mtc-20260518T1729Z-sfm` until `Completed`; immediately run the same `--launch` command once to advance to pinned Montana 3DGS.

## 2026-05-18T18:35Z-18:47Z Timed Poll Pass

- Timed polling command:
  - `for i in 1..6; do aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --query ProcessingJobStatus --output text; sleep 120; done`
  - Evidence: `logs/montana-time-capsule/sfm-poll-20260518T183539Z.log`
  - Result: all six polls returned `InProgress` at `18:35:39Z`, `18:37:40Z`, `18:39:41Z`, `18:41:42Z`, `18:43:43Z`, `18:45:44Z`.
- Post-poll duplicate guard command: `/opt/homebrew/bin/aws sagemaker list-processing-jobs --name-contains cvhr-mtc-20260518T1729Z --max-results 20`
  - Result: only one matching processing job remains (`cvhr-mtc-20260518T1729Z-sfm`, `InProgress`).
- Post-poll advance-one-stage command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: runner held at `status=sfm_running`; no 3DGS job launched early.
- Post-poll describe confirmation command: `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress` as of `2026-05-18T18:48Z`.
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T183516Z-postpush.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-mtc-20260518T1729Z-20260518T183516Z-postpush.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-mtc-20260518T1729Z-20260518T184753Z-postpoll.json`
  - `logs/montana-time-capsule/launch-20260518T184753Z-postpoll.log`

## 2026-05-20T21:03Z HMC Monitor Pass

- Branch/head/status command:
  - `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `d07bb6af43b6d0652ee035221c1be3572862ae0a`, status clean (`## agent-40136728-montana-time-capsule...origin/agent-40136728-montana-time-capsule`).
- Exact-head workflows command:
  - `gh run list --branch agent-40136728-montana-time-capsule --commit d07bb6af --json ...`
  - Result: `[]` (expected for `[skip ci]` head); evidence saved under `logs/montana-time-capsule/gh-run-list-exact-head-*-postpush.json`.
- AWS identity command: `/opt/homebrew/bin/aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- HMC archive proof (no re-upload):
  - `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip` (LastModified `2026-05-16T17:35:27Z`, size `8646557673`, ETag `ed86661a82b28856997a09f129ce6bec-1031`).
  - Manifest: `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.manifest.json`.
  - Confirmed missing in staging uploads bucket: `s3://spaceport-uploads-staging/` (`404` HeadObject; empty list by `prefix=1778952912508`).
- SageMaker status command: `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name hmc-mtc-20260520T2015Z-sfm`
  - Result: `ProcessingJobStatus=InProgress` using pinned SfM image `sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CloudWatch progress sample:
  - Latest sampled: `Processed file [831/2063]` (feature extraction); log captured in `logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260520T205433Z.log`.
- S3 outputs:
  - (SfM uses `S3UploadMode=EndOfJob`; prefix is empty while `InProgress`.)

## 2026-05-21T01:35Z Monitor Pass (HMC)

- Branch/head/status:
  - `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `15774b8e377c749455feeec68b3d269458d9795b`, status clean.
- AWS identity:
  - `/opt/homebrew/bin/aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- GitHub workflows (exact-head):
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 20`
  - Result: latest `CDK Deploy` run `26187619621` succeeded for `chore: launch hmc time capsule sfm`.
- HMC input archive proof (do not upload):
  - `/opt/homebrew/bin/aws s3api head-object --bucket spaceport-uploads --key 1778952912508-hmc-high-mountain-camp-images-flat.zip`
  - Proof: `ContentLength=8646557673` (~8.65 GB), `ETag="ed86661a82b28856997a09f129ce6bec-1031"`, `LastModified=2026-05-16T17:35:27Z` (Saturday May 16, 2026). Evidence: `logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260521T001534Z.json`.
  - Staging upload bucket check: `aws s3api list-objects-v2 --bucket spaceport-uploads-staging --prefix 1778952912508-hmc-high-mountain-camp-images-flat.zip` returned no objects.
- SageMaker status:
  - `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name hmc-mtc-20260520T2015Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`. Evidence: `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T013435Z.json`.
  - Duplicate-job guard: `aws sagemaker list-processing-jobs --name-contains hmc-mtc-20260520T2015Z` returned only `hmc-mtc-20260520T2015Z-sfm` (`InProgress`).
- CloudWatch progress snapshot (most recent within last 6h window):
  - `aws logs tail /aws/sagemaker/ProcessingJobs --since 6h --log-stream-name-prefix hmc-mtc-20260520T2015Z-sfm --format short`
  - Last captured lines show chunk matcher recovery finishing and vocab tree build continuing; includes expected retry when `colmap vocab_tree_builder` rejects `--max_num_images`. Evidence: `logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260521T013456Z-since6h.log`.
- S3 outputs:
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/hmc-mtc-20260520T2015Z/ --recursive`
  - Result: empty (expected until end-of-job upload).

### Next unblocked step

Poll `hmc-mtc-20260520T2015Z-sfm` until `Completed`, then run the time-capsule runner once to advance exactly one stage to 3DGS (using pinned 3DGS image sha256 `482c1789...`).

### Preview URL (exact-head Pages deploy)

- Pages run log: `logs/montana-time-capsule/gh-run-26200368328-pages.txt`
- Preview alias URL: `https://agent-40136728-montana-time.v0-spaceport-website-preview2.pages.dev`
- Preview hash URL: `https://9480e9f2.v0-spaceport-website-preview2.pages.dev`
  - Prefix currently empty (EndOfJob upload): `s3://spaceport-ml-processing-staging/manual-validations/hmc-mtc-20260520T2015Z/colmap/`.
- Next unblocked step:
  - Keep polling until `hmc-mtc-20260520T2015Z-sfm` becomes `Completed`, then run `python3 scripts/montana_time_capsule/hmc_time_capsule.py --launch` once to launch pinned 3DGS.
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T184808Z-postpoll.json`
  - `logs/montana-time-capsule/sfm-poll-20260518T183539Z.log`
- Next unblocked step: keep polling `cvhr-mtc-20260518T1729Z-sfm` to completion; run the same `--launch` command once immediately after completion to launch pinned Montana 3DGS.

## 2026-05-20T21:46Z HMC Monitor Pass (SfM Mapping Phase)

- Branch/head/status command:
  - `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `a14d874f38d6914a4b0f4cfee46befa54afb2a57` (`[skip ci]`), status clean.
- AWS identity command: `aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- HMC archive proof (no re-upload):
  - `aws s3api head-object --bucket spaceport-uploads --key 1778952912508-hmc-high-mountain-camp-images-flat.zip`
  - Result: LastModified `2026-05-16T17:35:27Z`, size `8646557673`, ETag `ed86661a82b28856997a09f129ce6bec-1031`.
  - Object metadata (from `head-object`): `sha256=8ac35927d5c90969f5e10f1fa011333e6065140924986c75f18fc81f899b1df2`, `dataset=hmc`, `source=dropbox`, `photo-count=2063`.
- SageMaker status command: `aws sagemaker describe-processing-job --processing-job-name hmc-mtc-20260520T2015Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`; pinned SfM image `sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CloudWatch progress samples:
  - Feature extraction reached `Processed file [2063/2063]` and reported GPS priors coverage `2063/2063` (100%).
  - Mapping moved into `chunk_00_mapper_initial`, registering images (sampled `num_reg_frames=95`) and running bundle adjustment/retriangulation.
  - Evidence logs captured (gitignored): `logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260520T214101Z.log`, `logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260520T214615Z.log`.
- S3 outputs:
  - Prefix still empty (EndOfJob upload): `s3://spaceport-ml-processing-staging/manual-validations/hmc-mtc-20260520T2015Z/colmap/`.
- Next unblocked step:
  - Keep polling until `hmc-mtc-20260520T2015Z-sfm` becomes `Completed`, then run `python3 scripts/montana_time_capsule/hmc_time_capsule.py --launch` exactly once to launch pinned 3DGS.

## 2026-05-21T01:19Z HMC Monitor Pass (SfM Still Running)

- Branch/head/status:
  - `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `b5c5ea0bd3b41b56dd09128a14c190c304dadfc5`, clean.
- Exact-head workflow list (branch-level evidence only; recent commits are `[skip ci]`):
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 20`
  - Result: most recent `CDK Deploy` run id `26187619621` `success` (2026-05-20T20:19:47Z).
  - Post-push run list evidence: `logs/montana-time-capsule/gh-run-list-agent-40136728-20260521T012106Z.json` (exact head `e2b73877…` has 0 runs, expected for `[skip ci]`).
- AWS identity: `aws sts get-caller-identity` (evidence: `logs/montana-time-capsule/aws-sts-20260521T011412Z.json`)
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- HMC archive proof (no re-upload):
  - ZIP: `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip`
    - `LastModified=2026-05-16T17:35:27Z`, `ContentLength=8646557673`, ETag `"ed86661a82b28856997a09f129ce6bec-1031"` (evidence: `logs/montana-time-capsule/s3-head-spaceport-uploads-hmc-20260521T011510Z.json`).
  - Manifest: `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.manifest.json`
    - `LastModified=2026-05-16T17:49:54Z`, `ContentLength=352691` (evidence: `logs/montana-time-capsule/s3-head-spaceport-uploads-hmc-manifest-20260521T011558Z.json`).
- SageMaker status: `aws sagemaker describe-processing-job --processing-job-name hmc-mtc-20260520T2015Z-sfm`
  - Result: `ProcessingJobStatus=InProgress` (evidence: `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T011412Z.json`, `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T011843Z.json`).
  - CloudWatch tail proof: chunked COLMAP advanced into `chunk_15_spatial_matcher_recovery` and vocab-tree build retries (evidence: `logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260521T011437Z.log`).
- S3 outputs (EndOfJob upload still pending):
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/hmc-mtc-20260520T2015Z/ --recursive --summarize`
  - Result: 0 objects (evidence: `logs/montana-time-capsule/s3-ls-hmc-mtc-20260520T2015Z-20260521T011551Z.log`).
- Runner poll (no launch):
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --dataset-id HMC --run-prefix hmc-mtc --subset-strategy hmc_full_2063_montana_time_capsule --input-s3-uri s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip --expected-image-count 2063 --state-file logs/montana-time-capsule/hmc-state.json --search-prefix HMC --search-token hmc`
  - Result: `status=sfm_running`, `sfm_status=InProgress`, updated state at `2026-05-21T01:19:08Z` (evidence: `logs/montana-time-capsule/hmc-runner-20260521T011908Z.json`).
- Next unblocked step: continue 60–300s polling until SfM becomes `Completed`; once `Completed`, verify the SfM output prefix is populated, then run the same runner command with `--launch` exactly once to start pinned Montana 3DGS.

## 2026-05-18T18:49Z Ledger Commit + Push

- Commit: `4cd3ed8be671d9f1b6796375c5df67ac9250722d`
- Commit message: `chore: record montana timed sfm poll [skip ci]`
- Push command: `git push origin agent-40136728-montana-time-capsule`
- Push result: branch updated on origin (`6a87d029..4cd3ed8b`).
- Exact-head workflow check:
  - Branch workflows: `logs/montana-time-capsule/gh-run-list-agent-40136728-20260518T184900Z.json`
  - Exact-head workflows: `logs/montana-time-capsule/gh-run-list-exact-head-20260518T184900Z.json`
  - Exact-head result: `[]` (expected for `[skip ci]` logs-only commit).
- Current stage gate status: SfM job `cvhr-mtc-20260518T1729Z-sfm` still `InProgress`; no duplicate job exists; 3DGS not launched yet.
- Next unblocked step: continue polling until SfM `Completed`, then run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to launch pinned Montana 3DGS.

## 2026-05-18T19:13Z Monitor Pass

- Branch/head/status command:
  - `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short --branch`
  - Result before this pass: branch `agent-40136728-montana-time-capsule`, head `4260fd94b3b19b61196b10a987043f315326930c`, dirty only from new monitor evidence/state updates under `logs/montana-time-capsule/`.
- AWS identity command: `/opt/homebrew/bin/aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- SageMaker status command: `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress` for `cvhr-mtc-20260518T1729Z-sfm`; pinned SfM image unchanged (`sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`).
- Duplicate-job guard command: `/opt/homebrew/bin/aws sagemaker list-processing-jobs --name-contains cvhr-mtc-20260518T1729Z --max-results 20`
  - Result: still one matching processing job (`cvhr-mtc-20260518T1729Z-sfm`, `InProgress`); no duplicate jobs launched.
- CloudWatch stream command: `/opt/homebrew/bin/aws logs tail /aws/sagemaker/ProcessingJobs --since 25m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - Result: live SfM progress continued into chunked COLMAP steps (`chunk_00_mapper_initial` registration/BA and `chunk_02_sequential_matcher` processing through `image [134/186]`).
- Advance-one-stage command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: runner remained at `status=sfm_running`, `sfm_status=InProgress`; no 3DGS launched early.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260518T191341Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T191341Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-mtc-20260518T1729Z-20260518T191341Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T191356Z.log`
  - `logs/montana-time-capsule/launch-20260518T191356Z.log`
- Next unblocked step: keep polling SfM until `Completed`; run the same `--launch` command exactly once immediately after completion to launch pinned Montana 3DGS.

## 2026-05-18T19:14Z Ledger Commit + Push

- Commit: `8370c2ec35e3186bc7509664b2bbbcca283779ce`
- Commit message: `chore: record montana sfm monitor pass [skip ci]`
- Push command: `git push origin agent-40136728-montana-time-capsule`
- Push result: branch updated on origin (`4260fd94..8370c2ec`).
- Exact-head workflow check command:
  - `/opt/homebrew/bin/gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url`
  - Exact-head selection result for `8370c2ec35e3186bc7509664b2bbbcca283779ce`: `[]` (expected for `[skip ci]` logs-only commit).
- Branch workflow evidence: `logs/montana-time-capsule/gh-run-list-agent-40136728-20260518T191457Z.json`
- Exact-head workflow evidence: `logs/montana-time-capsule/gh-run-list-exact-head-20260518T191457Z.json`

## 2026-05-18T19:15Z Post-Push Monitor Pass

- SageMaker status command: `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`.
- Advance-one-stage command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: state remained `status=sfm_running`, `sfm_status=InProgress`; no duplicate/new stage launched.
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T191513Z-postpush.json`
  - `logs/montana-time-capsule/launch-20260518T191519Z-postpush.log`
- Next unblocked step: continue 60-300s polling until SfM completes; run one guarded `--launch` immediately after completion to start pinned Montana 3DGS.

## 2026-05-18T19:53Z Extended Timed Poll Pass

- Branch/head/status command:
  - `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short --branch`
  - Result before this pass: branch `agent-40136728-montana-time-capsule`, head `4260fd94b3b19b61196b10a987043f315326930c`, dirty only from newly captured monitor evidence under `logs/montana-time-capsule/`.
- AWS identity command: `/opt/homebrew/bin/aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- SageMaker status command: `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress` for `cvhr-mtc-20260518T1729Z-sfm`; pinned SfM image still `sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- Duplicate-job guard command: `/opt/homebrew/bin/aws sagemaker list-processing-jobs --name-contains cvhr-mtc-20260518T1729Z --max-results 20`
  - Result: one matching processing job only (`cvhr-mtc-20260518T1729Z-sfm`, `InProgress`); no duplicate CV-HR jobs launched.
- CloudWatch progress proof command: `/opt/homebrew/bin/aws logs tail /aws/sagemaker/ProcessingJobs --since 20m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - Result: feature extraction reached `Processed file [1710/1710]` during this pass, then job remained `InProgress` while later SfM steps continued.
- Advance-one-stage command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: `status=sfm_running`, `sfm_status=InProgress`; guard held and 3DGS was not launched early.
- Timed terminal-poll loop command:
  - `for i in 1..20; do aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --query ProcessingJobStatus --output text; sleep 120; done`
  - Result: all 20 polls from `2026-05-18T18:54:42Z` to `2026-05-18T19:33:02Z` returned `InProgress`.
- Evidence files:
  - `logs/montana-time-capsule/git-status-20260518T185343Z.txt`
  - `logs/montana-time-capsule/aws-sts-20260518T185343Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T185343Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-mtc-20260518T1729Z-20260518T185343Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T185343Z.log`
  - `logs/montana-time-capsule/launch-20260518T185343Z.log`
  - `logs/montana-time-capsule/sfm-terminal-poll-20260518T185442Z.log`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T193503Z-postpoll.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-mtc-20260518T1729Z-20260518T193503Z-postpoll.json`
- Next unblocked step: continue polling until SfM `Completed`; immediately run one guarded `--launch` command to advance exactly one stage into pinned Montana 3DGS.

## 2026-05-18T19:36Z Ledger Commit + Push

- Commit: `b8c77ada182cb098ed65277f5691e9128fcb4081`
- Commit message: `chore: record montana extended sfm polling [skip ci]`
- Push command: `git push origin agent-40136728-montana-time-capsule`
- Push result: branch updated on origin (`2d7e21ea..b8c77ada`).
- Exact-head workflow check command:
  - `/opt/homebrew/bin/gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Exact-head result for `b8c77ada182cb098ed65277f5691e9128fcb4081`: `[]` (expected for `[skip ci]` logs-only commit).
- Branch workflow evidence: `logs/montana-time-capsule/gh-run-list-agent-40136728-20260518T193645Z.json`
- Exact-head workflow evidence: `logs/montana-time-capsule/gh-run-list-exact-head-20260518T193645Z.json`
- Last meaningful non-skip workflow proof retained: `CDK Deploy` success on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442` run `26049509375`.
- Next unblocked step: continue polling SfM `cvhr-mtc-20260518T1729Z-sfm`; run one guarded `--launch` immediately when SfM reaches `Completed` to launch pinned Montana 3DGS.

## 2026-05-18T19:39Z Post-Ledger Exact-Head Check

- Latest branch head after evidence commit: `f482381bce501a07881b91c61da602bd06dc5d61`.
- Exact-head workflow check command:
  - `/opt/homebrew/bin/gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` (expected for logs-only `[skip ci]` commit).
- Stage gate unchanged: `cvhr-mtc-20260518T1729Z-sfm` remains `InProgress` with no duplicate jobs.
- Next unblocked step: continue polling SfM to `Completed`, then run one guarded `--launch` to advance exactly one stage into pinned Montana 3DGS.

## 2026-05-18T21:04Z Active-Thread Monitor Pass

- Automation binding:
  - Active heartbeat automation: `montana-twin-cv-hr-monitor`
  - Cadence: `FREQ=MINUTELY;INTERVAL=20`
  - Target thread: `019e3bf1-e2d1-7453-b4cd-4383b888b1b3`
  - Old detached cron `cv-hr-montana-time-capsule-monitor` is paused.
- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `d384615d003f71bdc6c324c3bb1a9295b9812880`; dirty only from newly captured monitor evidence under `logs/montana-time-capsule/`.
- AWS identity command: `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- SageMaker status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --region us-west-2 --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`, `FailureReason=null`, `ExitMessage=null`; pinned SfM image unchanged (`sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`).
- Duplicate-job guard command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --region us-west-2 --name-contains cvhr-mtc-20260518T1729Z --max-results 20`
  - Result: exactly one matching CV-HR processing job, `cvhr-mtc-20260518T1729Z-sfm`, still `InProgress`; no duplicate CV-HR job exists.
- Other active SageMaker processing jobs observed and left untouched:
  - `md1-viscell-leaf-08-1779136078`
  - `md1-viscell-leaf-01-1779136049`
  - `md1-shrunk-prodspine-sfm-1779128752`
  - `cvhr-mtc-20260518T1729Z-sfm`
- CloudWatch proof command:
  - `AWS_PAGER= aws logs get-log-events --region us-west-2 --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name cvhr-mtc-20260518T1729Z-sfm/algo-1-1779125429 --limit 80 --output text`
  - Result: latest log event remains `COLMAP[vocab_tree_builder] ... Building index for visual words...` at `2026-05-18T19:43:03Z` after loading `1904336` descriptors. No OOM, timeout, or SageMaker failure is visible.
- S3 output command:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --human-readable --summarize`
  - Result: `Total Objects: 0`, expected while SageMaker output upload mode is `EndOfJob`.
- Guarded advance command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: runner returned `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`; no 3DGS launched early.
- GitHub workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result for current logs-only head `d384615d003f71bdc6c324c3bb1a9295b9812880`: `[]` (expected for `[skip ci]` commits). Last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/manual-sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T210332Z.json`
  - `logs/montana-time-capsule/manual-sagemaker-list-cvhr-mtc-20260518T1729Z-20260518T210332Z.json`
  - `logs/montana-time-capsule/manual-logstreams-cvhr-mtc-20260518T1729Z-sfm-20260518T210333Z.json`
  - `logs/montana-time-capsule/manual-cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T210344Z.log`
  - `logs/montana-time-capsule/manual-s3-colmap-cvhr-mtc-20260518T1729Z-20260518T210333Z.txt`
  - `logs/montana-time-capsule/manual-launch-20260518T210445Z.log`
  - `logs/montana-time-capsule/manual-gh-run-list-agent-40136728-20260518T210437Z-exactcheck.json`
  - `logs/montana-time-capsule/manual-gh-run-list-exact-head-20260518T210437Z.json`
- Next unblocked step: let SfM continue until terminal. If it reaches `Completed`, run the guarded `--launch` command once to start pinned Montana 3DGS. If it reaches `Failed` or `Stopped`, capture exact SageMaker describe, CloudWatch, and S3 evidence before any patch or retry.

## 2026-05-18T21:20Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `a3cc97e42b7b07a5ebb071f5d4b71385e8df130f`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --region us-west-2 --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`; `FailureReason` absent; `ExitMessage` absent; pinned SfM image remains `sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- Canonical CV-HR duplicate guard command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --region us-west-2 --name-contains cvhr-mtc-20260518T1729Z --max-results 20`
  - Result: exactly one canonical job, `cvhr-mtc-20260518T1729Z-sfm`, still `InProgress`.
- S3 output command:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --human-readable --summarize`
  - Result: `Total Objects: 0`, still expected while this SageMaker job uses `S3UploadMode=EndOfJob`.
- CloudWatch command:
  - `AWS_PAGER= aws logs get-log-events --region us-west-2 --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name cvhr-mtc-20260518T1729Z-sfm/algo-1-1779125429 --limit 60 --output text`
  - Result: latest canonical log remains `COLMAP[vocab_tree_builder] ... Building index for visual words...` at `2026-05-18T19:43:03Z` after `1904336` descriptors loaded. No SageMaker failure, OOM, or timeout is visible.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `a3cc97e42b7b07a5ebb071f5d4b71385e8df130f`. Last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --region us-west-2 --status-equals InProgress --max-results 50`
  - Result includes four active processing jobs:
    - `cvhr-secondary-20260518t2113z-sfm`
    - `md1-viscell-leaf-01-1779136049`
    - `md1-shrunk-prodspine-sfm-1779128752`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Important non-canonical CV-HR job observed:
  - Job: `cvhr-secondary-20260518t2113z-sfm`
  - Branch/head env: `agent-73910482-cvhr-parallel-splat` / `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`
  - Input: `s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
  - Output: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - Image: same pinned SfM digest `sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`
  - Status: `InProgress`; no CloudWatch stream yet at this poll.
  - Action taken: none. This job appears owned by another branch/automation, so it was not stopped.
- Evidence files:
  - `logs/montana-time-capsule/heartbeat-sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T212045Z.json`
  - `logs/montana-time-capsule/heartbeat-sagemaker-list-cvhr-mtc-20260518T1729Z-20260518T212045Z.json`
  - `logs/montana-time-capsule/heartbeat-logstreams-cvhr-mtc-20260518T1729Z-sfm-20260518T212045Z.json`
  - `logs/montana-time-capsule/heartbeat-s3-colmap-cvhr-mtc-20260518T1729Z-20260518T212045Z.txt`
  - `logs/montana-time-capsule/heartbeat-cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T212101Z.log`
  - `logs/montana-time-capsule/heartbeat-gh-run-list-agent-40136728-20260518T212045Z.json`
  - `logs/montana-time-capsule/heartbeat-gh-run-list-exact-head-20260518T212045Z.json`
  - `logs/montana-time-capsule/heartbeat-sagemaker-list-all-inprogress-20260518T212129Z.json`
  - `logs/montana-time-capsule/heartbeat-sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260518T212146Z.json`
  - `logs/montana-time-capsule/heartbeat-sagemaker-list-cvhr-all-20260518T212146Z.json`
  - `logs/montana-time-capsule/heartbeat-logstreams-cvhr-secondary-20260518t2113z-sfm-20260518T212146Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run the guarded `--launch` once to start pinned Montana 3DGS. Also keep recording the non-canonical `cvhr-secondary-20260518t2113z-sfm`; do not stop it unless it is clearly proven orphaned.

## 2026-05-18T21:40Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `4e64f2256d4288c221b801dffba95c24b740cc50`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --region us-west-2 --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --region us-west-2 --name-contains cvhr --max-results 50`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`)
- S3 output command:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --human-readable --summarize`
  - Result: canonical SfM output still `Total Objects: 0`, expected until SageMaker `EndOfJob` upload.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `4e64f2256d4288c221b801dffba95c24b740cc50`. Last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Canonical CloudWatch command:
  - `AWS_PAGER= aws logs get-log-events --region us-west-2 --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name cvhr-mtc-20260518T1729Z-sfm/algo-1-1779125429 --limit 60 --output text`
  - Result: no new canonical log after `COLMAP[vocab_tree_builder] ... Building index for visual words...` at `2026-05-18T19:43:03Z`; log stream last event timestamp remains `1779133383674`. SageMaker still reports `InProgress`, with no visible OOM, timeout, or failure.
- Non-canonical CV-HR observation:
  - `cvhr-secondary-20260518t2113z-sfm` now has log stream `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`.
  - Tail showed active feature extraction through `Processed file [428/1710]` at `2026-05-18T21:41:03Z`.
  - Action taken: none. It appears owned by branch `agent-73910482-cvhr-parallel-splat` and is not clearly orphaned.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --region us-west-2 --status-equals InProgress --max-results 50`
  - Result includes three active processing jobs:
    - `cvhr-secondary-20260518t2113z-sfm`
    - `md1-shrunk-prodspine-sfm-1779128752`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Guarded advance command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: runner returned `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`, `updated_at=2026-05-18T21:41:31Z`; no 3DGS launched early.
- Evidence files:
  - `logs/montana-time-capsule/heartbeat-sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T214042Z.json`
  - `logs/montana-time-capsule/heartbeat-sagemaker-list-cvhr-all-20260518T214042Z.json`
  - `logs/montana-time-capsule/heartbeat-s3-colmap-cvhr-mtc-20260518T1729Z-20260518T214042Z.txt`
  - `logs/montana-time-capsule/heartbeat-gh-run-list-agent-40136728-20260518T214042Z.json`
  - `logs/montana-time-capsule/heartbeat-gh-run-list-exact-head-20260518T214042Z.json`
  - `logs/montana-time-capsule/heartbeat-logstreams-cvhr-mtc-20260518T1729Z-sfm-20260518T214107Z.json`
  - `logs/montana-time-capsule/heartbeat-cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T214107Z.log`
  - `logs/montana-time-capsule/heartbeat-sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260518T214107Z.json`
  - `logs/montana-time-capsule/heartbeat-logstreams-cvhr-secondary-20260518t2113z-sfm-20260518T214107Z.json`
  - `logs/montana-time-capsule/heartbeat-cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260518T214120Z.log`
  - `logs/montana-time-capsule/heartbeat-sagemaker-list-all-inprogress-20260518T214120Z.json`
  - `logs/montana-time-capsule/heartbeat-launch-20260518T214130Z.log`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run the guarded `--launch` once to start pinned Montana 3DGS. Keep recording the non-canonical secondary job but do not stop it unless clearly proven orphaned.

## 2026-05-18T22:00Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `176399b8777d9d45d867ba5797e51c430f57c351`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --region us-west-2 --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --region us-west-2 --name-contains cvhr --max-results 50`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`)
- S3 output command:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --human-readable --summarize`
  - Result: canonical SfM output still `Total Objects: 0`, expected until SageMaker `EndOfJob` upload.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `176399b8777d9d45d867ba5797e51c430f57c351`. Last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Canonical CloudWatch command:
  - `AWS_PAGER= aws logs get-log-events --region us-west-2 --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name cvhr-mtc-20260518T1729Z-sfm/algo-1-1779125429 --limit 40 --output text`
  - Result: no new canonical log after `COLMAP[vocab_tree_builder] ... Building index for visual words...` at `2026-05-18T19:43:03Z`; log stream last event timestamp remains `1779133383674`. SageMaker still reports `InProgress`, with no visible OOM, timeout, or failure.
- Non-canonical CV-HR observation:
  - `cvhr-secondary-20260518t2113z-sfm` remains active and owned by branch `agent-73910482-cvhr-parallel-splat`.
  - Tail showed active feature extraction through `Processed file [944/1710]` at `2026-05-18T22:00:57Z`.
  - Action taken: none. It is not clearly orphaned.
- Guarded advance command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: runner returned `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`, `updated_at=2026-05-18T22:01:13Z`; no 3DGS launched early.
- Evidence files:
  - `logs/montana-time-capsule/heartbeat-sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T220041Z.json`
  - `logs/montana-time-capsule/heartbeat-sagemaker-list-cvhr-all-20260518T220041Z.json`
  - `logs/montana-time-capsule/heartbeat-s3-colmap-cvhr-mtc-20260518T1729Z-20260518T220041Z.txt`
  - `logs/montana-time-capsule/heartbeat-gh-run-list-agent-40136728-20260518T220041Z.json`
  - `logs/montana-time-capsule/heartbeat-gh-run-list-exact-head-20260518T220041Z.json`
  - `logs/montana-time-capsule/heartbeat-logstreams-cvhr-mtc-20260518T1729Z-sfm-20260518T220053Z.json`
  - `logs/montana-time-capsule/heartbeat-cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T220053Z.log`
  - `logs/montana-time-capsule/heartbeat-cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260518T220053Z.log`
  - `logs/montana-time-capsule/heartbeat-launch-20260518T220112Z.log`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run the guarded `--launch` once to start pinned Montana 3DGS. Keep recording the non-canonical secondary job but do not stop it unless clearly proven orphaned.

## 2026-05-18T22:22Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `c0f493f71890765a0e7d1f46406fbd70971f9502`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --region us-west-2 --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --region us-west-2 --name-contains cvhr --max-results 50`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`)
- S3 output command:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --human-readable --summarize`
  - Result: canonical SfM output still `Total Objects: 0`, expected until SageMaker `EndOfJob` upload.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `c0f493f71890765a0e7d1f46406fbd70971f9502`. Last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Canonical CloudWatch command:
  - `AWS_PAGER= aws logs get-log-events --region us-west-2 --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name cvhr-mtc-20260518T1729Z-sfm/algo-1-1779125429 --limit 40 --output text`
  - Result: no new canonical log after `COLMAP[vocab_tree_builder] ... Building index for visual words...` at `2026-05-18T19:43:03Z`; log stream last event timestamp remains `1779133383674`. SageMaker still reports `InProgress`, with no visible OOM, timeout, or failure.
- Non-canonical CV-HR observation:
  - `cvhr-secondary-20260518t2113z-sfm` remains active and owned by branch `agent-73910482-cvhr-parallel-splat`.
  - Tail showed active feature extraction through `Processed file [1517/1710]` at `2026-05-18T22:23:03Z`.
  - Action taken: none. It is not clearly orphaned.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --region us-west-2 --status-equals InProgress --max-results 50`
  - Result includes five active processing jobs:
    - `md1-viscell-full-l01-1779141986`
    - `md1-viscell-full-l00-1779141981`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `md1-shrunk-prodspine-sfm-1779128752`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Guarded advance command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: runner returned `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`, `updated_at=2026-05-18T22:23:19Z`; no 3DGS launched early.
- Evidence files:
  - `logs/montana-time-capsule/heartbeat-sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T222242Z.json`
  - `logs/montana-time-capsule/heartbeat-sagemaker-list-cvhr-all-20260518T222242Z.json`
  - `logs/montana-time-capsule/heartbeat-s3-colmap-cvhr-mtc-20260518T1729Z-20260518T222243Z.txt`
  - `logs/montana-time-capsule/heartbeat-gh-run-list-agent-40136728-20260518T222243Z.json`
  - `logs/montana-time-capsule/heartbeat-gh-run-list-exact-head-20260518T222243Z.json`
  - `logs/montana-time-capsule/heartbeat-logstreams-cvhr-mtc-20260518T1729Z-sfm-20260518T222256Z.json`
  - `logs/montana-time-capsule/heartbeat-cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T222256Z.log`
  - `logs/montana-time-capsule/heartbeat-cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260518T222309Z.log`
  - `logs/montana-time-capsule/heartbeat-sagemaker-list-all-inprogress-20260518T222309Z.json`
  - `logs/montana-time-capsule/heartbeat-launch-20260518T222318Z.log`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run the guarded `--launch` once to start pinned Montana 3DGS. Keep recording the non-canonical secondary job but do not stop it unless clearly proven orphaned.

## 2026-05-18T22:42Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `9bbaec871ed87735813748b815a40f027194b275`, clean before this heartbeat pass.
- AWS identity command:
  - `aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20 --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap --recursive --summarize`
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap --recursive --summarize`
  - Result: both prefixes still `Total Objects: 0`, expected until SageMaker `EndOfJob` upload.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `9bbaec871ed87735813748b815a40f027194b275`. Last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Canonical CloudWatch commands:
  - `aws logs tail /aws/sagemaker/ProcessingJobs --since 40m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - `aws logs tail /aws/sagemaker/ProcessingJobs --since 4h --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - Result: no canonical log in the last 40 minutes; the 4h tail confirms the latest visible canonical event is still `COLMAP[vocab_tree_builder] ... Building index for visual words...` at `2026-05-18T19:43:03Z`. SageMaker still reports `InProgress`; no visible OOM, timeout, or failure.
- Non-canonical CV-HR observation:
  - `cvhr-secondary-20260518t2113z-sfm` remains active and owned by branch `agent-73910482-cvhr-parallel-splat`.
  - Tail showed active chunked COLMAP progress through `chunk_00_mapper_initial model 0 registered 172/172 images and 111407 points` at `2026-05-18T22:44:23Z`.
  - Action taken: none. It is not clearly orphaned.
- Active SageMaker processing sweep:
  - `aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes five active processing jobs:
    - `md1-viscell-full-l02-1779143476`
    - `md1-viscell-full-l01-1779141986`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `md1-shrunk-prodspine-sfm-1779128752`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T2242Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260518T2242Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260518T2242Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260518T2242Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260518T2242Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260518T2242Z.txt`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T2242Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T2242Z-4h.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260518T2242Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260518T2242Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260518T2242Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. Keep recording the non-canonical secondary job but do not stop it unless clearly proven orphaned.

## 2026-05-19T23:23Z Compression Complete, Hosted Viewer Verified

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short && git status --branch --short`
  - Result before this pass: branch `agent-40136728-montana-time-capsule`, head `4659864d4478963a49d4e4fc922d4ab687efff99`; local status had only current heartbeat evidence files plus `logs/montana-time-capsule/cv-hr-state.json`.
- AWS identity command:
  - `aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Pinned Montana compression status command:
  - `aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-secondary-20260518t2113z-compression --output json`
  - Result: `ProcessingJobStatus=Completed`, `ProcessingStartTime=2026-05-19T17:05:49.683000-06:00`, `ProcessingEndTime=2026-05-19T17:14:10.174000-06:00`, no `FailureReason`, no `ExitMessage`.
  - Image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor@sha256:a0784727da1870ce9caa4774dc831a32fb96cd1574df389cf9093fbf18f4f4ab`.
  - Input: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/cvhr-mtc-secondary-20260518t2113z-3dgs/output/model.tar.gz`.
  - Output: `s3://spaceport-ml-processing-staging/compressed/cvhr-mtc-secondary-20260518t2113z/`.
- Compression output listing:
  - `aws s3 ls s3://spaceport-ml-processing-staging/compressed/cvhr-mtc-secondary-20260518t2113z/ --recursive --summarize`
  - Result: `22` objects, `15,238,835` bytes, including `supersplat_bundle/meta.json`, seven WebP SOGS files, `background_skybox.webp`, `background_manifest.json`, `export_manifest.json`, and `training_metadata.json`.
  - SOGS metadata: `461041` gaussians in `meta.json`; original PLY `109.3503 MB`, compressed SOGS payload `7.2373 MB`, compression ratio `15.109x`.
  - Skybox metadata: `background_skybox.webp`, `2048x1024`, selected from `/tmp/nerfstudio_training/converted_data/images/frame_01660.JPG`, score `0.7296118806998818`.
- Guarded runner advancement command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: no duplicate job launched; state advanced to `status=completed`, `last_action=completed`, `sfm_status=Completed`, `3dgs_status=Completed`, `compression_status=Completed`.
  - Final bundle state: `s3://spaceport-ml-processing-staging/compressed/cvhr-mtc-secondary-20260518t2113z/supersplat_bundle/meta.json`.
- Direct public S3 reachability:
  - Direct staging URLs for `meta.json` and `background_skybox.webp` returned HTTP `400` because this bucket/object path requires signed SigV4/KMS access.
  - Non-staging public URLs returned HTTP `403`.
  - Resolution: hosted viewer uses `/api/sogs-proxy` on the branch preview, which signs the allowed staging S3 origin.
- Hosted proxy reachability:
  - `curl -fsS https://agent-40136728-montana-time.v0-spaceport-website-preview2.pages.dev/api/sogs-proxy/https:/spaceport-ml-processing-staging.s3.us-west-2.amazonaws.com/compressed/cvhr-mtc-secondary-20260518t2113z/supersplat_bundle/meta.json`
  - Result: HTTP `200`, `meta.json` loaded with `means.shape=[461041,3]`.
  - `background_skybox.webp` through the same hosted proxy returned HTTP `200` and decoded as WebP `2048x1024`.
- Hosted Pages deploy:
  - Command: `gh workflow run deploy-cloudflare-pages.yml --ref agent-40136728-montana-time-capsule`
  - Run: `https://github.com/HansenHomeAI/v0-spaceport-website/actions/runs/26131478855`
  - Result: success for exact head `4659864d4478963a49d4e4fc922d4ab687efff99`.
  - Preview alias: `https://agent-40136728-montana-time.v0-spaceport-website-preview2.pages.dev`.
  - Hash URL: `https://2e89a848.v0-spaceport-website-preview2.pages.dev`.
- Hosted viewer verification:
  - Skybox URL: `https://agent-40136728-montana-time.v0-spaceport-website-preview2.pages.dev/sogs-migrated-viewer?url=https%3A%2F%2Fspaceport-ml-processing-staging.s3.us-west-2.amazonaws.com%2Fcompressed%2Fcvhr-mtc-secondary-20260518t2113z%2Fsupersplat_bundle%2Fmeta.json&skybox=background_skybox.webp`
  - No-sky URL: `https://agent-40136728-montana-time.v0-spaceport-website-preview2.pages.dev/sogs-migrated-viewer?url=https%3A%2F%2Fspaceport-ml-processing-staging.s3.us-west-2.amazonaws.com%2Fcompressed%2Fcvhr-mtc-secondary-20260518t2113z%2Fsupersplat_bundle%2Fmeta.json&skybox=off`
  - Skybox smoke command: `cd web && SOGS_MIGRATED_URL=https://agent-40136728-montana-time.v0-spaceport-website-preview2.pages.dev SOGS_BUNDLE_URL=https://spaceport-ml-processing-staging.s3.us-west-2.amazonaws.com/compressed/cvhr-mtc-secondary-20260518t2113z/supersplat_bundle/meta.json SOGS_SKYBOX_OVERRIDE=background_skybox.webp SOGS_EXPECT_SKYBOX_SUBSTRING=background_skybox.webp SOGS_EXPECT_BUNDLED_SKYBOX=1 node scripts/test-sogs-migrated-viewer.mjs`
  - Skybox result: passed; iframe rendered visible content (`1280x800`, `bright=1014142`, `alpha=1024000`), camera finite, bundled skybox proxy request returned HTTP `200`.
  - No-sky smoke command: `cd web && SOGS_MIGRATED_URL=https://agent-40136728-montana-time.v0-spaceport-website-preview2.pages.dev SOGS_BUNDLE_URL=https://spaceport-ml-processing-staging.s3.us-west-2.amazonaws.com/compressed/cvhr-mtc-secondary-20260518t2113z/supersplat_bundle/meta.json SOGS_DISABLE_SKYBOX=1 SOGS_EXPECT_SKYBOX_SUBSTRING=background_skybox.webp node scripts/test-sogs-migrated-viewer.mjs`
  - No-sky result: passed; iframe rendered visible content (`1280x800`, `bright=975370`, `alpha=1024000`) and made no `background_skybox.webp` request.
  - Visual proof screenshots:
    - `logs/montana-time-capsule/cvhr-hosted-sogs-skybox-smoke-20260519T2323Z.png`
    - `logs/montana-time-capsule/cvhr-hosted-sogs-nosky-smoke-20260519T2323Z.png`
- Active CV-HR SageMaker sweep after completion:
  - `aws sagemaker list-training-jobs --status-equals InProgress --name-contains cvhr --max-results 20`: no active CV-HR training jobs.
  - `aws sagemaker list-processing-jobs --status-equals InProgress --name-contains cvhr --max-results 20`: only unrelated `cvhr-viscell-full-l09-1779233441` and `cvhr-viscell-full-l08-1779230706` remained active; no action taken because they are not owned by this automation.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T2323Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-compression-20260519T2323Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-compression-summary-20260519T2337Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-secondary-20260518t2113z-compression-20260519T2323Z.log`
  - `logs/montana-time-capsule/s3-compressed-cvhr-mtc-secondary-20260518t2113z-20260519T2323Z.txt`
  - `logs/montana-time-capsule/runner-status-compression-complete-20260519T2323Z.log`
  - `logs/montana-time-capsule/cvhr-super-splat-meta-20260519T2323Z.json`
  - `logs/montana-time-capsule/cvhr-sogs-compression-summary-20260519T2323Z.json`
  - `logs/montana-time-capsule/cvhr-background-manifest-20260519T2323Z.json`
  - `logs/montana-time-capsule/cvhr-training-metadata-20260519T2323Z.json`
  - `logs/montana-time-capsule/pages-deploy-26131478855-20260519T2323Z.log`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T2323Z-postdeploy.json`
  - `logs/montana-time-capsule/cvhr-hosted-sogs-skybox-smoke-20260519T2323Z.log`
  - `logs/montana-time-capsule/cvhr-hosted-sogs-skybox-smoke-20260519T2323Z.png`
  - `logs/montana-time-capsule/cvhr-hosted-sogs-nosky-smoke-20260519T2323Z.log`
  - `logs/montana-time-capsule/cvhr-hosted-sogs-nosky-smoke-20260519T2323Z.png`
  - `logs/montana-time-capsule/hosted-proxy-head-cvhr-meta-20260519T2323Z.headers`
  - `logs/montana-time-capsule/hosted-proxy-head-cvhr-skybox-20260519T2323Z.headers`
- Current status: CV-HR Montana time capsule SfM, 3DGS, compression, hosted proxy reachability, and hosted skybox/no-sky viewer verification are complete for run `cvhr-mtc-secondary-20260518t2113z`.

## 2026-05-19T18:03Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `b73dec45fb87b8607b8f85adfb504cf0cbfe6f80`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=Stopped`, `ProcessingEndTime=2026-05-19T11:36:11.271000-0600`, no `FailureReason`, no `ExitMessage`; pinned SfM image was `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`; `MaxRuntimeInSeconds=86400`.
- Failure evidence:
  - CloudWatch latest canonical logs show `chunk_model_merger_10` successfully produced a merged reconstruction with `Images: 1694`, `Points: 1325268`, then `chunk_bundle_adjuster` entered global bundle adjustment and repeatedly logged `Linear solver failure. Failed to compute a finite step.` through `2026-05-19T17:34:23Z`.
  - S3 output remained empty (`Total Objects: 0`, `Total Size: 0`), so no trainable COLMAP handoff exists for `s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/`.
  - Runner status command after capture: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
  - Runner result: `status=sfm_failed`, `sfm_status=Stopped`, `last_action=sfm_failed`, exit code `2`; no launch occurred.
- Active CV-HR job guard:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result: no active canonical job remains; one non-canonical CV-HR SfM job remains active: `cvhr-secondary-20260518t2113z-sfm`, owner branch env `agent-73910482-cvhr-parallel-splat`, same input archive and same pinned Brass chunked SfM digest. It is not owned by this automation and was not stopped.
- Non-canonical secondary observation:
  - Secondary log tail shows it reached the same final chunk merge path and started `chunk_bundle_adjuster` global bundle adjustment at `2026-05-19T17:57:00Z`; its S3 output is still empty. Action taken: none.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `b73dec45fb87b8607b8f85adfb504cf0cbfe6f80`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T1803Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1803Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1803Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1803Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-active-filtered-20260519T1803Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T1803Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T1803Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T1803Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T1803Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T1803Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T1803Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T1803Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T1803Z.json`
  - `logs/montana-time-capsule/runner-status-cvhr-mtc-20260518T1729Z-20260519T1803Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1803Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T1803Z.json`
- Next unblocked step: do not launch 3DGS from the stopped canonical run. To keep cost bounded, continue monitoring the active secondary exact-Brass SfM job instead of starting another duplicate Brass job. If the secondary job completes, verify its image/input/env/output and adopt the COLMAP output for the pinned Montana 3DGS handoff. If the secondary job also stops or fails, launch exactly one full-SfM fallback retry using the pinned `horsetail-gps` profile (`sha256:a7e2553455ad8ca7988256f4b0d38395e1770b2522532c41c6f535fc8a49f157`) in a new state/run id, then continue stage-by-stage.

## 2026-05-19T18:23Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `4252ef79d053e69dc97da39bd1f3b48988804c2f`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: still terminal `ProcessingJobStatus=Stopped`, `ProcessingEndTime=2026-05-19T11:36:11.271000-0600`, no `FailureReason`, no `ExitMessage`; canonical S3 COLMAP prefix remains empty (`Total Objects: 0`, `Total Size: 0`).
- Active CV-HR job guard:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result after recheck: one active CV-HR processing job remains, `cvhr-secondary-20260518t2113z-sfm` (`InProgress`). The earlier planner/report-only job `cvhr-viscell-plan-v1-1779214624` is `Completed` and belongs to branch env `agent-73948216-sfm-production-spine`.
- Non-canonical secondary observation:
  - Job: `cvhr-secondary-20260518t2113z-sfm`
  - Owner branch env: `agent-73910482-cvhr-parallel-splat`; input `s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`; output `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`; image `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`; `MaxRuntimeInSeconds=86400`.
  - Status: `InProgress`, no `FailureReason` or `ExitMessage`; S3 output remains empty (`Total Objects: 0`, `Total Size: 0`).
  - CloudWatch: latest sampled log still shows it crossed all chunk merges, `chunk_model_merger_10` merged to `Images: 1693`, `Points: 1329830`, then `chunk_bundle_adjuster` entered global bundle adjustment at `2026-05-19T17:57:00Z`. No OOM, timeout, terminal error, or EndOfJob upload is visible.
  - Action taken: none. It is not owned by this automation, but it is the only active exact-Brass CV-HR SfM attempt, so this automation is monitoring it instead of launching a duplicate.
- Other CV-HR processing observation:
  - `cvhr-viscell-plan-v1-1779214624` describes as `Completed`, report-only planner env `SFM_PLANNER_REPORT_ONLY=1`, output `s3://spaceport-ml-processing-staging/manual-validations/cvhr-visibility-cell-v1-planner-20260519T1749Z/colmap`; action taken: none because it is not the Montana time-capsule stack and is not this automation's job.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 20 --json databaseId,workflowName,headSha,status,conclusion,createdAt,updatedAt,url`
  - Result: `[]` for exact logs-only `[skip ci]` head `4252ef79d053e69dc97da39bd1f3b48988804c2f`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T1823Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1823Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1823Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-viscell-plan-v1-1779214624-20260519T1823Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1823Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1828Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T1823Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T1823Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T1823Z.json`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T1823Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T1823Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T1823Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1823Z.json`
- Next unblocked step: continue monitoring `cvhr-secondary-20260518t2113z-sfm` without launching a duplicate. If it completes, verify the pinned image/input/env/S3 output and adopt its COLMAP output for the pinned Montana 3DGS handoff. If it also stops or fails, capture describe/log/S3 proof and launch exactly one fallback SfM run using the pinned `horsetail-gps` profile in a separate state file/run id.

## 2026-05-19T18:43Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `363809e9056fd46f364fba13d67a74ab9edfacec`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: still terminal `ProcessingJobStatus=Stopped`, `ProcessingEndTime=2026-05-19T11:36:11.271000-0600`, no `FailureReason`, no `ExitMessage`; canonical S3 COLMAP prefix remains empty (`Total Objects: 0`, `Total Size: 0`).
- Active CV-HR job guard:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result: active CV-HR processing jobs are `cvhr-secondary-20260518t2113z-sfm`, `cvhr-viscell-c03-1779215211`, and `cvhr-viscell-c04-1779215211`. No new CV-HR job was launched from this heartbeat and no job was stopped.
- Non-canonical secondary exact-Brass SfM observation:
  - Job: `cvhr-secondary-20260518t2113z-sfm`
  - Owner branch env: `agent-73910482-cvhr-parallel-splat`; input `s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`; output `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`; image `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`; `MaxRuntimeInSeconds=86400`.
  - Status: `InProgress`, `ProcessingStartTime=2026-05-18T15:20:32.428000-0600`, no `FailureReason` or `ExitMessage`; S3 output remains empty (`Total Objects: 0`, `Total Size: 0`).
  - CloudWatch: 45-minute tail had no new lines; 120-minute tail still shows `chunk_model_merger_10` merged to `Images: 1693`, `Points: 1329830`, then `chunk_bundle_adjuster` entered global bundle adjustment at `2026-05-19T17:57:00Z`. Log stream metadata reports latest event timestamp epoch `1779213175453`. No OOM, timeout, terminal error, or EndOfJob upload is visible.
  - Action taken: none. It is not owned by this automation, but it is still the only active exact-Brass CV-HR SfM attempt, so this automation continues to monitor it instead of launching a duplicate.
- Other CV-HR processing observation:
  - `cvhr-viscell-c03-1779215211` and `cvhr-viscell-c04-1779215211` are `InProgress` on image `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:agent73948216sfmproductionspine`, branch env `agent-73948216-sfm-production-spine`, planner `visibility_cell_v1`, match profile `P3`, only chunk indexes `3` and `4`. These are not Montana time-capsule jobs and were left alone.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 20 --json databaseId,workflowName,headSha,status,conclusion,createdAt,updatedAt,url`
  - Result: `[]` for exact logs-only `[skip ci]` head `363809e9056fd46f364fba13d67a74ab9edfacec`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T1843Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1843Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1843Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-viscell-c03-1779215211-20260519T1843Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-viscell-c04-1779215211-20260519T1843Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1843Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T1843Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T1843Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T1843Z.json`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T1843Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T1843Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T1843Z-120m.log`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T1843Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1843Z.json`
- Next unblocked step: keep monitoring `cvhr-secondary-20260518t2113z-sfm` until terminal without launching a duplicate. If it completes, verify the pinned image/input/env/S3 output and adopt its COLMAP output for the pinned Montana 3DGS handoff. If it stops or fails, capture describe/log/S3 proof and launch exactly one fallback SfM run using the pinned `horsetail-gps` profile in a separate state file/run id.

## 2026-05-19T19:03Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `0029c821c486d41331a877c73bf343007d82cee8`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: still terminal `ProcessingJobStatus=Stopped`, `ProcessingEndTime=2026-05-19T11:36:11.271000-0600`, no `FailureReason`, no `ExitMessage`; canonical S3 COLMAP prefix remains empty (`Total Objects: 0`, `Total Size: 0`).
- Active CV-HR job guard:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result: active CV-HR processing jobs remain `cvhr-secondary-20260518t2113z-sfm`, `cvhr-viscell-c03-1779215211`, and `cvhr-viscell-c04-1779215211`. No new CV-HR job was launched from this heartbeat and no job was stopped.
- Non-canonical secondary exact-Brass SfM observation:
  - Job: `cvhr-secondary-20260518t2113z-sfm`
  - Owner branch env: `agent-73910482-cvhr-parallel-splat`; input `s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`; output `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`; image `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`; `MaxRuntimeInSeconds=86400`.
  - Status: `InProgress`, `ProcessingStartTime=2026-05-18T15:20:32.428000-0600`, no `FailureReason` or `ExitMessage`; S3 output remains empty (`Total Objects: 0`, `Total Size: 0`).
  - CloudWatch: 60-minute tail had no new lines; 140-minute tail still shows `chunk_model_merger_10` merged to `Images: 1693`, `Points: 1329830`, then `chunk_bundle_adjuster` entered global bundle adjustment at `2026-05-19T17:57:00Z`. Log stream metadata latest event timestamp is epoch `1779213420765` (`2026-05-19T17:57:00Z`). No OOM, timeout, terminal error, or EndOfJob upload is visible.
  - Action taken: none. It is not owned by this automation, but it is still the only active exact-Brass CV-HR SfM attempt, so this automation continues to monitor it instead of launching a duplicate.
- Other CV-HR processing observation:
  - `cvhr-viscell-c03-1779215211`: `InProgress`, branch env `agent-73948216-sfm-production-spine`, image `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:agent73948216sfmproductionspine`, `COLMAP_ONLY_CHUNK_INDEXES=3`, output `s3://spaceport-ml-processing-staging/manual-validations/cvhr-visibility-cell-v1-canary-20260519T1758Z/leaves/leaf-03/colmap`.
  - `cvhr-viscell-c04-1779215211`: `InProgress`, branch env `agent-73948216-sfm-production-spine`, image `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:agent73948216sfmproductionspine`, `COLMAP_ONLY_CHUNK_INDEXES=4`, output `s3://spaceport-ml-processing-staging/manual-validations/cvhr-visibility-cell-v1-canary-20260519T1758Z/leaves/leaf-04/colmap`.
  - Action taken: none. These are not Montana time-capsule jobs.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 20 --json databaseId,workflowName,headSha,status,conclusion,createdAt,updatedAt,url`
  - Result: `[]` for exact logs-only `[skip ci]` head `0029c821c486d41331a877c73bf343007d82cee8`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T1903Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1903Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1903Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-viscell-c03-1779215211-20260519T1903Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-viscell-c04-1779215211-20260519T1903Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1903Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T1903Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T1903Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T1903Z.json`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T1903Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T1903Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T1903Z-140m.log`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T1903Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1903Z.json`
- Next unblocked step: keep monitoring `cvhr-secondary-20260518t2113z-sfm` until terminal without launching a duplicate. If it completes, verify the pinned image/input/env/S3 output and adopt its COLMAP output for the pinned Montana 3DGS handoff. If it stops or fails, capture describe/log/S3 proof and launch exactly one fallback SfM run using the pinned `horsetail-gps` profile in a separate state file/run id.

## 2026-05-19T19:23Z Heartbeat Monitor Pass + 3DGS Launch

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `b7ac2ecc3c2e4543a40826422bb6447dfb831cb7`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: still terminal `ProcessingJobStatus=Stopped`, no trainable output (`Total Objects: 0`, `Total Size: 0`).
- Secondary exact-Brass SfM adoption proof:
  - SageMaker status at adoption was still `InProgress`, but the container log and S3 handoff were complete.
  - CloudWatch proof: `SPACEPORT COLMAP GPU SfM COMPLETED SUCCESSFULLY!`, COLMAP validation passed, `Images registered: 1693`, `Images copied for 3DGS: 1710`, `3D points: 1329830`, processing time `78924.24` seconds.
  - S3 proof: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap/` contains `1717` objects, `10,379,523,417` bytes, including `database.db`, `1710` copied images, `sfm_metadata.json`, and sparse TXT files `cameras.txt`, `images.txt`, `points3D.txt`, `frames.txt`, and `rigs.txt`.
  - Adopted SfM output: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - Adopted run id: `cvhr-mtc-secondary-20260518t2113z`
- Proven runner gap patched:
  - `scripts/montana_time_capsule/cv_hr_time_capsule.py` now honors `sfm_output_verified=true` in the state file so a hard-verified external/adopted SfM handoff can advance without waiting on a stale SageMaker processing status.
  - Validation: `python3 -m py_compile scripts/montana_time_capsule/cv_hr_time_capsule.py`
- Duplicate training guard:
  - `AWS_PAGER= aws sagemaker list-training-jobs --name-contains cvhr --max-results 20 --output json`
  - Result before launch: no CV-HR training jobs (`[]`).
- 3DGS launch command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: launched exactly one pinned Montana 3DGS training job: `cvhr-mtc-secondary-20260518t2113z-3dgs`.
- 3DGS verification:
  - Training job: `cvhr-mtc-secondary-20260518t2113z-3dgs`
  - Status: `InProgress`
  - Input: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - Output: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/`
  - Model artifact target: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/cvhr-mtc-secondary-20260518t2113z-3dgs/output/model.tar.gz`
  - Image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`
  - Instance: `ml.g5.2xlarge`, volume `100` GB, max runtime `14400` seconds.
  - Montana skybox environment confirmed: `MODEL_VARIANT=splatfacto-w-light`, `ENABLE_BG_MODEL=true`, `ENABLE_ALPHA_LOSS=true`, `ENABLE_ROBUST_MASK=true`, `BACKGROUND_APPEARANCE_MODE=auto_camera`, `BACKGROUND_SKYBOX_WIDTH=2048`, `BACKGROUND_SKYBOX_HEIGHT=1024`.
  - Current 3DGS S3 output is empty (`Total Objects: 0`, expected until EndOfJob upload); no log stream existed at immediate post-launch describe time.
- State runner verification:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
  - Result: `status=3dgs_running`, `last_action=3dgs_running`, `3dgs_status=InProgress`; no duplicate training job was launched.
- Other active CV-HR jobs:
  - `cvhr-viscell-c03-1779215211` and `cvhr-viscell-c04-1779215211` remain owned by branch env `agent-73948216-sfm-production-spine`; action taken: none.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 20 --json databaseId,workflowName,headSha,status,conclusion,createdAt,updatedAt,url`
  - Result before this ledger commit: `[]` for exact logs-only `[skip ci]` head `b7ac2ecc3c2e4543a40826422bb6447dfb831cb7`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T1923Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1923Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1923Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1923Z-posts3.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1923Z-afterwait.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T1923Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T1923Z.json`
  - `logs/montana-time-capsule/s3api-colmap-sparse-cvhr-secondary-20260518t2113z-20260519T1923Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T1923Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T1923Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-before-3dgs-20260519T1923Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-after-3dgs-attempt-20260519T1923Z.json`
  - `logs/montana-time-capsule/launch-3dgs-from-secondary-20260519T1923Z.log`
  - `logs/montana-time-capsule/runner-status-after-3dgs-launch-20260519T1923Z.log`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T1923Z.json`
  - `logs/montana-time-capsule/s3-3dgs-cvhr-mtc-secondary-20260518t2113z-20260519T1923Z.txt`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T1923Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1923Z.json`
- Next unblocked step: monitor `cvhr-mtc-secondary-20260518t2113z-3dgs` to terminal. If it completes, run the same runner once with `--launch` to create pinned Montana compression. If it fails, capture describe/log/S3 proof before patching or retrying the smallest stage.

## 2026-05-19T19:31Z Live 3DGS Gate Check

- 3DGS status command:
  - `AWS_PAGER= aws sagemaker describe-training-job --training-job-name cvhr-mtc-secondary-20260518t2113z-3dgs --output json`
  - Result: `TrainingJobStatus=InProgress`, no `FailureReason`; `TrainingStartTime=2026-05-19T13:29:17.980000-06:00`, `TrainingTimeInSeconds=114`; current secondary status is `Downloading`; image remains pinned Montana 3DGS digest `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`.
- 3DGS handoff verification:
  - Input: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - Output: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/`
  - S3 output still empty: `Total Objects: 0`, `Total Size: 0`, expected before SageMaker EndOfJob upload.
  - Training log stream query returned no streams yet, consistent with the job still starting/downloading.
- Secondary exact-Brass SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-secondary-20260518t2113z-sfm --output json`
  - Result: SageMaker still reports `ProcessingJobStatus=InProgress`, no `FailureReason` or `ExitMessage`; the S3/COLMAP handoff remains adopted only because it was independently proven complete by container logs and S3 object listings.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result before this commit: `[]` for head `b7ac2ecc3c2e4543a40826422bb6447dfb831cb7`; this pending commit includes a runner code patch, so it will be pushed without `[skip ci]` and exact-head workflows will be watched.
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T1931Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1931Z.json`
  - `logs/montana-time-capsule/s3-3dgs-cvhr-mtc-secondary-20260518t2113z-20260519T1931Z.txt`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T1931Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T1931Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1931Z.json`
- Next unblocked step: continue monitoring `cvhr-mtc-secondary-20260518t2113z-3dgs` until terminal. Do not rerun launch while this job exists. On completion, run the runner once with `--launch` to start pinned Montana compression.

## 2026-05-19T19:38Z Post-Push Workflow + 3DGS Training Check

- Exact-head workflow proof for code commit:
  - Commit: `7b38bd43b956fbfa92700ae513c3b64afee62ec1`
  - `CDK Deploy` run: `26120469998`
  - Result: `completed` / `success`, updated `2026-05-19T19:37:26Z`.
- 3DGS status command:
  - `AWS_PAGER= aws sagemaker describe-training-job --training-job-name cvhr-mtc-secondary-20260518t2113z-3dgs --output json`
  - Result: `TrainingJobStatus=InProgress`, no `FailureReason`; `TrainingTimeInSeconds=519`; stage advanced from `Downloading` to `Training` at `2026-05-19T13:33:20.429000-06:00`.
- CloudWatch proof:
  - Log stream exists: `cvhr-mtc-secondary-20260518t2113z-3dgs/algo-1-1779218957`.
  - Logs prove the pinned Montana skybox 3DGS stack is active: `NerfStudio with splatfacto-w-light`, `enable_bg_model=True`, `enable_alpha_loss=True`, `enable_robust_mask=True`, `output.background_skybox.width=2048`, `output.background_skybox.height=1024`.
  - COLMAP validation inside 3DGS passed again: `Cameras: 1`, `Images registered: 1693`, `Image files: 1710`, `3D points: 1329830`.
  - TXT-to-BIN conversion succeeded with `cameras.bin`, `images.bin`, and `points3D.bin`; latest visible command is `ns-process-data images --data /opt/ml/input/data/training/images --output-dir /tmp/nerfstudio_training/converted_data --skip-colmap --colmap-model-path /tmp/nerfstudio_training/colmap_bin/0`.
- S3 output status:
  - `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/` still `Total Objects: 0`, `Total Size: 0`, expected until SageMaker EndOfJob upload.
- Evidence files:
  - `logs/montana-time-capsule/gh-run-view-cdk-deploy-26120469998-20260519T1938Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T1938Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T1938Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T1938Z.log`
  - `logs/montana-time-capsule/s3-3dgs-cvhr-mtc-secondary-20260518t2113z-20260519T1938Z.txt`
- Next unblocked step: continue monitoring `cvhr-mtc-secondary-20260518t2113z-3dgs` through training completion. If it succeeds, run the runner exactly once with `--launch` to start pinned Montana compression. If it fails, capture the exact SageMaker failure, CloudWatch tail, and S3 prefix before any patch or retry.

## 2026-05-19T19:43Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `103327e4f98993783277908899a32678b1513098`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Current 3DGS status command:
  - `AWS_PAGER= aws sagemaker describe-training-job --training-job-name cvhr-mtc-secondary-20260518t2113z-3dgs --output json`
  - Result: `TrainingJobStatus=InProgress`, no `FailureReason`; `TrainingStartTime=2026-05-19T13:29:17.980000-06:00`, `TrainingTimeInSeconds=889`; active phase remains `Training`.
  - Pinned image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`.
  - Input: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`.
  - Output: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/`.
- Duplicate guard:
  - `AWS_PAGER= aws sagemaker list-training-jobs --name-contains cvhr --max-results 20 --output json`
  - Result: exactly one CV-HR training job exists, `cvhr-mtc-secondary-20260518t2113z-3dgs` (`InProgress`).
- Other CV-HR processing jobs:
  - `cvhr-mtc-20260518T1729Z-sfm` remains `Stopped` with no output.
  - `cvhr-secondary-20260518t2113z-sfm` still reports `InProgress` in SageMaker, but its COLMAP output remains complete and adopted: `1717` objects, `10,379,523,417` bytes.
  - New unrelated CV-HR processing jobs `cvhr-viscell-full-l00-1779219568` and `cvhr-viscell-full-l01-1779219573` are `InProgress`; action taken: none.
- 3DGS log proof:
  - Log stream: `cvhr-mtc-secondary-20260518t2113z-3dgs/algo-1-1779218957`.
  - Latest useful logs show `ns-process-data` matched `1693` images, found poses for `99.01%` of images, `transforms.json` validation passed with `1693` frames, and `ns-train splatfacto-w-light ... --pipeline.model.enable_bg_model True --pipeline.model.enable_alpha_loss True --pipeline.model.enable_robust_mask True` started with `Training timeout: 14400 seconds`.
- S3 output status:
  - `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/` still `Total Objects: 0`, `Total Size: 0`, expected until SageMaker EndOfJob upload.
- No-launch runner status command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
  - Result: state remains `status=3dgs_running`, `last_action=3dgs_running`, `3dgs_status=InProgress`; no duplicate launch.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `103327e4f98993783277908899a32678b1513098`; prior exact-head code commit `7b38bd43b956fbfa92700ae513c3b64afee62ec1` has green `CDK Deploy` run `26120469998`.
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T1943Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-20260519T1943Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-20260519T1943Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1943Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1943Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T1943Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T1943Z.log`
  - `logs/montana-time-capsule/s3-3dgs-cvhr-mtc-secondary-20260518t2113z-20260519T1943Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T1943Z.txt`
  - `logs/montana-time-capsule/runner-status-3dgs-20260519T1943Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1943Z.json`
- Next unblocked step: continue monitoring `cvhr-mtc-secondary-20260518t2113z-3dgs` through terminal state. Do not rerun the launcher while this job exists. On success, run the runner once with `--launch` to start pinned Montana compression; on failure, capture exact SageMaker describe, CloudWatch tail, and S3 output before patching.

## 2026-05-19T20:03Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `28e704617d43b7505464d19f33dd8f9583c49c06`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Current 3DGS status command:
  - `AWS_PAGER= aws sagemaker describe-training-job --training-job-name cvhr-mtc-secondary-20260518t2113z-3dgs --output json`
  - Result: `TrainingJobStatus=InProgress`, no `FailureReason`; `TrainingStartTime=2026-05-19T13:29:17.980000-06:00`, `TrainingTimeInSeconds=2088`; active phase remains `Training`.
  - Pinned image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`.
  - Input: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`.
  - Output: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/`.
- CV-HR training job sweep:
  - `AWS_PAGER= aws sagemaker list-training-jobs --name-contains cvhr --max-results 20 --output json`
  - Result: two CV-HR training jobs are active:
    - canonical time-capsule job `cvhr-mtc-secondary-20260518t2113z-3dgs` (`InProgress`)
    - separate non-mtc job `cvhr-secondary-20260518t2113z-3dgs` (`InProgress`, same input/pinned image but output `s3://spaceport-ml-processing-staging/3dgs/cvhr-secondary-20260518t2113z/`); action taken: none.
- 3DGS log/S3 status:
  - Log stream still exists: `cvhr-mtc-secondary-20260518t2113z-3dgs/algo-1-1779218957`.
  - A 20-minute CloudWatch tail returned no new lines after the earlier `ns-train splatfacto-w-light ...` launch; this is expected while the trainer subprocess is running because iteration logs may not flush until subprocess exit.
  - S3 output remains empty: `Total Objects: 0`, `Total Size: 0`, expected until SageMaker EndOfJob upload.
- No-launch runner status command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
  - Result: state remains `status=3dgs_running`, `last_action=3dgs_running`, `3dgs_status=InProgress`; no duplicate launch.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `28e704617d43b7505464d19f33dd8f9583c49c06`; prior exact-head code commit `7b38bd43b956fbfa92700ae513c3b64afee62ec1` has green `CDK Deploy` run `26120469998`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T2003Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2003Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-3dgs-20260519T2003Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-20260519T2003Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2003Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2003Z.log`
  - `logs/montana-time-capsule/s3-3dgs-cvhr-mtc-secondary-20260518t2113z-20260519T2003Z.txt`
  - `logs/montana-time-capsule/runner-status-3dgs-20260519T2003Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T2003Z.json`
- Next unblocked step: continue monitoring `cvhr-mtc-secondary-20260518t2113z-3dgs` through terminal state. Do not rerun the launcher while this job exists. On success, run the runner once with `--launch` to start pinned Montana compression; on failure, capture exact SageMaker describe, CloudWatch tail, and S3 output before patching.

## 2026-05-19T20:23Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `3a95b34cae1a2a3ef99a2acc2bed3398f1c0657c`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Current canonical 3DGS status command:
  - `AWS_PAGER= aws sagemaker describe-training-job --training-job-name cvhr-mtc-secondary-20260518t2113z-3dgs --output json`
  - Result: `TrainingJobStatus=InProgress`, no `FailureReason`; `TrainingStartTime=2026-05-19T13:29:17.980000-06:00`, `TrainingTimeInSeconds=3289`; active phase remains `Training`.
  - Pinned image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`.
  - Input: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`.
  - Output: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/`.
- CV-HR training job sweep:
  - `AWS_PAGER= aws sagemaker list-training-jobs --name-contains cvhr --max-results 20 --output json`
  - Result: two CV-HR training jobs are active:
    - canonical time-capsule job `cvhr-mtc-secondary-20260518t2113z-3dgs` (`InProgress`)
    - separate non-mtc job `cvhr-secondary-20260518t2113z-3dgs` (`InProgress`, same input/pinned image but output `s3://spaceport-ml-processing-staging/3dgs/cvhr-secondary-20260518t2113z/`); action taken: none.
- CV-HR processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20 --output json`
  - Result: unrelated CV-HR viscell processing jobs continue; action taken: none.
- 3DGS log/S3 status:
  - Log stream still exists: `cvhr-mtc-secondary-20260518t2113z-3dgs/algo-1-1779218957`; latest stream event timestamp remains `2026-05-19T19:38:17Z`.
  - A 25-minute CloudWatch tail returned no new lines after the earlier `ns-train splatfacto-w-light ...` launch; this is expected while the trainer subprocess is running because iteration logs may not flush until subprocess exit.
  - S3 output remains empty: `Total Objects: 0`, `Total Size: 0`, expected until SageMaker EndOfJob upload.
- No-launch runner status command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
  - Result: state remains `status=3dgs_running`, `last_action=3dgs_running`, `3dgs_status=InProgress`; no duplicate launch.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `3a95b34cae1a2a3ef99a2acc2bed3398f1c0657c`; prior exact-head code commit `7b38bd43b956fbfa92700ae513c3b64afee62ec1` has green `CDK Deploy` run `26120469998`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T2023Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2023Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-20260519T2023Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-20260519T2023Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2023Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2023Z.log`
  - `logs/montana-time-capsule/s3-3dgs-cvhr-mtc-secondary-20260518t2113z-20260519T2023Z.txt`
  - `logs/montana-time-capsule/runner-status-3dgs-20260519T2023Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T2023Z.json`
- Next unblocked step: continue monitoring `cvhr-mtc-secondary-20260518t2113z-3dgs` through terminal state. Do not rerun the launcher while this job exists. On success, run the runner once with `--launch` to start pinned Montana compression; on failure, capture exact SageMaker describe, CloudWatch tail, and S3 output before patching.

## 2026-05-19T20:43Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current`, `git rev-parse HEAD`, `git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `2c43d06a9f18290561a7092393600ea389cf0751`; status had only current-pass evidence after the pre-compaction AWS identity capture (`?? logs/montana-time-capsule/aws-sts-20260519T2043Z.json`) before this monitor pass added new evidence files.
- AWS identity command:
  - `aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Current canonical 3DGS status command:
  - `aws sagemaker describe-training-job --training-job-name cvhr-mtc-secondary-20260518t2113z-3dgs`
  - Result: `TrainingJobStatus=InProgress`, no `FailureReason`; `TrainingStartTime=2026-05-19T13:29:17.980000-06:00`, `TrainingTimeInSeconds=4542`; active phase remains `Training`.
  - Pinned image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`.
  - Input: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`.
  - Output: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/`.
- CV-HR active SageMaker sweep:
  - `aws sagemaker list-training-jobs --name-contains cvhr --status-equals InProgress --max-results 100`
  - Result: two active CV-HR training jobs:
    - canonical time-capsule job `cvhr-mtc-secondary-20260518t2113z-3dgs` (`InProgress`)
    - separate non-mtc job `cvhr-secondary-20260518t2113z-3dgs` (`InProgress`, same input/pinned image, output `s3://spaceport-ml-processing-staging/3dgs/cvhr-secondary-20260518t2113z/`); action taken: none.
  - `aws sagemaker list-processing-jobs --name-contains cvhr --status-equals InProgress --max-results 100`
  - Result: only unrelated viscell processing jobs are active: `cvhr-viscell-full-l01-1779219573` and `cvhr-viscell-full-l02-1779220672`; action taken: none.
- SfM source-state correction:
  - `cvhr-secondary-20260518t2113z-sfm` now describes as `Completed` with `ProcessingEndTime=2026-05-19T13:21:07.265000-06:00`; `cv-hr-state.json` was updated from stale `secondary_sfm_status=InProgress` to `Completed`.
  - Original canonical SfM `cvhr-mtc-20260518T1729Z-sfm` remains `Stopped` with no adopted output.
- 3DGS log/S3 status:
  - Log stream exists: `cvhr-mtc-secondary-20260518t2113z-3dgs/algo-1-1779218957`; latest stream event timestamp remains `2026-05-19T19:38:17Z`.
  - A 25-minute CloudWatch tail returned `0` lines after the earlier `ns-train splatfacto-w-light ...` launch; this remains consistent with captured subprocess output while training is active.
  - S3 output remains empty: `Total Objects: 0`, `Total Size: 0`, expected until SageMaker EndOfJob upload.
- No-launch runner status command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
  - Result: state remains `status=3dgs_running`, `last_action=3dgs_running`, `3dgs_status=InProgress`; no duplicate launch.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `2c43d06a9f18290561a7092393600ea389cf0751`; prior exact-head code commit `7b38bd43b956fbfa92700ae513c3b64afee62ec1` has green `CDK Deploy` run `26120469998`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T2043Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2043Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-3dgs-20260519T2043Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T2043Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T2043Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-20260519T2043Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-active-20260519T2043Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-20260519T2043Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-active-20260519T2043Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2043Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2043Z.log`
  - `logs/montana-time-capsule/s3-3dgs-cvhr-mtc-secondary-20260518t2113z-20260519T2043Z.txt`
  - `logs/montana-time-capsule/runner-status-3dgs-20260519T2043Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T2043Z.json`
- Next unblocked step: continue monitoring `cvhr-mtc-secondary-20260518t2113z-3dgs` through terminal state. Do not rerun the launcher while this job exists. On success, run the runner once with `--launch` to start pinned Montana compression; on failure, capture exact SageMaker describe, CloudWatch tail, and S3 output before patching.

## 2026-05-19T21:03Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current`, `git rev-parse HEAD`, `git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `cfee526a414f1dc2c1d74833daf5faae27f14183`; status only showed current-pass evidence after the AWS identity capture (`?? logs/montana-time-capsule/aws-sts-20260519T2103Z.json`) before this monitor pass added new evidence files.
- AWS identity command:
  - `aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Current canonical 3DGS status command:
  - `aws sagemaker describe-training-job --training-job-name cvhr-mtc-secondary-20260518t2113z-3dgs`
  - Result: `TrainingJobStatus=InProgress`, no `FailureReason`; `TrainingStartTime=2026-05-19T13:29:17.980000-06:00`, `TrainingTimeInSeconds=5679`; active phase remains `Training`.
  - Pinned image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`.
  - Input: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`.
  - Output: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/`.
- CV-HR active SageMaker sweep:
  - `aws sagemaker list-training-jobs --name-contains cvhr --status-equals InProgress --max-results 100`
  - Result: two active CV-HR training jobs:
    - canonical time-capsule job `cvhr-mtc-secondary-20260518t2113z-3dgs` (`InProgress`)
    - separate non-mtc job `cvhr-secondary-20260518t2113z-3dgs` (`InProgress`, same input/pinned image, output `s3://spaceport-ml-processing-staging/3dgs/cvhr-secondary-20260518t2113z/`); action taken: none.
  - `aws sagemaker list-processing-jobs --name-contains cvhr --status-equals InProgress --max-results 100`
  - Result: only unrelated viscell processing jobs are active: `cvhr-viscell-full-l02-1779220672` and `cvhr-viscell-full-l05-1779224497`; action taken: none.
- 3DGS log/S3 status:
  - Log stream exists: `cvhr-mtc-secondary-20260518t2113z-3dgs/algo-1-1779218957`; latest stream event timestamp remains `2026-05-19T19:38:17Z`.
  - A 25-minute CloudWatch tail returned `0` lines after the earlier `ns-train splatfacto-w-light ...` launch; still consistent with captured subprocess output while training is active.
  - S3 output remains empty: `Total Objects: 0`, `Total Size: 0`, expected until SageMaker EndOfJob upload.
- No-launch runner status command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
  - Result: state remains `status=3dgs_running`, `last_action=3dgs_running`, `3dgs_status=InProgress`; no duplicate launch.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `cfee526a414f1dc2c1d74833daf5faae27f14183`; prior exact-head code commit `7b38bd43b956fbfa92700ae513c3b64afee62ec1` has green `CDK Deploy` run `26120469998`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T2103Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2103Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-20260519T2103Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-active-20260519T2103Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-20260519T2103Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-active-20260519T2103Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2103Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2103Z.log`
  - `logs/montana-time-capsule/s3-3dgs-cvhr-mtc-secondary-20260518t2113z-20260519T2103Z.txt`
  - `logs/montana-time-capsule/runner-status-3dgs-20260519T2103Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T2103Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T2103Z.json`
- Next unblocked step: continue monitoring `cvhr-mtc-secondary-20260518t2113z-3dgs` through terminal state. Do not rerun the launcher while this job exists. On success, run the runner once with `--launch` to start pinned Montana compression; on failure, capture exact SageMaker describe, CloudWatch tail, and S3 output before patching.

## 2026-05-19T21:23Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current`, `git rev-parse HEAD`, `git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `de0a23b3d12afd1ea202645d95a2b4485d887f17`; status only showed current-pass evidence after the AWS identity capture (`?? logs/montana-time-capsule/aws-sts-20260519T2123Z.json`) before this monitor pass added new evidence files.
- AWS identity command:
  - `aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Current canonical 3DGS status command:
  - `aws sagemaker describe-training-job --training-job-name cvhr-mtc-secondary-20260518t2113z-3dgs`
  - Result: `TrainingJobStatus=InProgress`, no `FailureReason`; `TrainingStartTime=2026-05-19T13:29:17.980000-06:00`, `TrainingTimeInSeconds=6890`; active phase remains `Training`.
  - Pinned image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`.
  - Input: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`.
  - Output: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/`.
- CV-HR active SageMaker sweep:
  - `aws sagemaker list-training-jobs --name-contains cvhr --status-equals InProgress --max-results 100`
  - Result: two active CV-HR training jobs:
    - canonical time-capsule job `cvhr-mtc-secondary-20260518t2113z-3dgs` (`InProgress`)
    - separate non-mtc job `cvhr-secondary-20260518t2113z-3dgs` (`InProgress`, same input/pinned image, output `s3://spaceport-ml-processing-staging/3dgs/cvhr-secondary-20260518t2113z/`); action taken: none.
  - `aws sagemaker list-processing-jobs --name-contains cvhr --status-equals InProgress --max-results 100`
  - Result: only unrelated viscell processing jobs are active: `cvhr-viscell-full-l05-1779224497` and `cvhr-viscell-full-l06-1779225051`; action taken: none.
- 3DGS log/S3 status:
  - Log stream exists: `cvhr-mtc-secondary-20260518t2113z-3dgs/algo-1-1779218957`; latest stream event timestamp remains `2026-05-19T19:38:17Z`.
  - A 25-minute CloudWatch tail returned `0` lines after the earlier `ns-train splatfacto-w-light ...` launch; still consistent with captured subprocess output while training is active.
  - S3 output remains empty: `Total Objects: 0`, `Total Size: 0`, expected until SageMaker EndOfJob upload.
- No-launch runner status command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
  - Result: state remains `status=3dgs_running`, `last_action=3dgs_running`, `3dgs_status=InProgress`; no duplicate launch.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `de0a23b3d12afd1ea202645d95a2b4485d887f17`; prior exact-head code commit `7b38bd43b956fbfa92700ae513c3b64afee62ec1` has green `CDK Deploy` run `26120469998`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T2123Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2123Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-20260519T2123Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-active-20260519T2123Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-20260519T2123Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-active-20260519T2123Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2123Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2123Z.log`
  - `logs/montana-time-capsule/s3-3dgs-cvhr-mtc-secondary-20260518t2113z-20260519T2123Z.txt`
  - `logs/montana-time-capsule/runner-status-3dgs-20260519T2123Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T2123Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T2123Z.json`
- Next unblocked step: continue monitoring `cvhr-mtc-secondary-20260518t2113z-3dgs` through terminal state. Do not rerun the launcher while this job exists. On success, run the runner once with `--launch` to start pinned Montana compression; on failure, capture exact SageMaker describe, CloudWatch tail, and S3 output before patching.

## 2026-05-19T21:43Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current`, `git rev-parse HEAD`, `git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `fa993cb9f191ac869f2212d4277c13c5058b1c68`; status only showed current-pass evidence after the AWS identity capture (`?? logs/montana-time-capsule/aws-sts-20260519T2143Z.json`) before this monitor pass added new evidence files.
- AWS identity command:
  - `aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Current canonical 3DGS status command:
  - `aws sagemaker describe-training-job --training-job-name cvhr-mtc-secondary-20260518t2113z-3dgs`
  - Result: `TrainingJobStatus=InProgress`, no `FailureReason`; `TrainingStartTime=2026-05-19T13:29:17.980000-06:00`, `TrainingTimeInSeconds=8081`; active phase remains `Training`.
  - Pinned image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`.
  - Input: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`.
  - Output: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/`.
- CV-HR active SageMaker sweep:
  - `aws sagemaker list-training-jobs --name-contains cvhr --status-equals InProgress --max-results 100`
  - Result: two active CV-HR training jobs:
    - canonical time-capsule job `cvhr-mtc-secondary-20260518t2113z-3dgs` (`InProgress`)
    - separate non-mtc job `cvhr-secondary-20260518t2113z-3dgs` (`InProgress`, same input/pinned image, output `s3://spaceport-ml-processing-staging/3dgs/cvhr-secondary-20260518t2113z/`); action taken: none.
  - `aws sagemaker list-processing-jobs --name-contains cvhr --status-equals InProgress --max-results 100`
  - Result: only unrelated viscell processing jobs are active: `cvhr-viscell-full-l05-1779224497` and `cvhr-viscell-full-l06-1779225051`; action taken: none.
- 3DGS log/S3 status:
  - Log stream exists: `cvhr-mtc-secondary-20260518t2113z-3dgs/algo-1-1779218957`; latest stream event timestamp remains `2026-05-19T19:38:17Z`.
  - A 25-minute CloudWatch tail returned `0` lines after the earlier `ns-train splatfacto-w-light ...` launch; still consistent with captured subprocess output while training is active.
  - S3 output remains empty: `Total Objects: 0`, `Total Size: 0`, expected until SageMaker EndOfJob upload.
- No-launch runner status command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
  - Result: state remains `status=3dgs_running`, `last_action=3dgs_running`, `3dgs_status=InProgress`; no duplicate launch.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `fa993cb9f191ac869f2212d4277c13c5058b1c68`; prior exact-head code commit `7b38bd43b956fbfa92700ae513c3b64afee62ec1` has green `CDK Deploy` run `26120469998`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T2143Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2143Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-20260519T2143Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-active-20260519T2143Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-20260519T2143Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-active-20260519T2143Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2143Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2143Z.log`
  - `logs/montana-time-capsule/s3-3dgs-cvhr-mtc-secondary-20260518t2113z-20260519T2143Z.txt`
  - `logs/montana-time-capsule/runner-status-3dgs-20260519T2143Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T2143Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T2143Z.json`
- Next unblocked step: continue monitoring `cvhr-mtc-secondary-20260518t2113z-3dgs` through terminal state. Do not rerun the launcher while this job exists. On success, run the runner once with `--launch` to start pinned Montana compression; on failure, capture exact SageMaker describe, CloudWatch tail, and S3 output before patching.

## 2026-05-19T22:03Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current`, `git rev-parse HEAD`, `git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `ede011ba0ffb1043a5d3bed96117d95ae015ed07`, clean before this heartbeat pass.
- AWS identity command:
  - `aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Current canonical 3DGS status command:
  - `aws sagemaker describe-training-job --training-job-name cvhr-mtc-secondary-20260518t2113z-3dgs`
  - Result: `TrainingJobStatus=InProgress`, no `FailureReason`; `TrainingStartTime=2026-05-19T13:29:17.980000-06:00`, `TrainingTimeInSeconds=9280`; active phase remains `Training`.
  - Pinned image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`.
  - Input: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`.
  - Output: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/`.
- CV-HR active SageMaker sweep:
  - `aws sagemaker list-training-jobs --name-contains cvhr --status-equals InProgress --max-results 100`
  - Result: two active CV-HR training jobs:
    - canonical time-capsule job `cvhr-mtc-secondary-20260518t2113z-3dgs` (`InProgress`)
    - separate non-mtc job `cvhr-secondary-20260518t2113z-3dgs` (`InProgress`, same input/pinned image, output `s3://spaceport-ml-processing-staging/3dgs/cvhr-secondary-20260518t2113z/`); action taken: none.
  - `aws sagemaker list-processing-jobs --name-contains cvhr --status-equals InProgress --max-results 100`
  - Result: only unrelated viscell processing jobs are active: `cvhr-viscell-full-l05-1779224497` and `cvhr-viscell-full-l06-1779225051`; action taken: none.
- 3DGS log/S3 status:
  - Log stream exists: `cvhr-mtc-secondary-20260518t2113z-3dgs/algo-1-1779218957`; latest stream event timestamp remains `2026-05-19T19:38:17Z`.
  - A 25-minute CloudWatch tail returned `0` lines after the earlier `ns-train splatfacto-w-light ...` launch; still consistent with captured subprocess output while training is active.
  - S3 output remains empty: `Total Objects: 0`, `Total Size: 0`, expected until SageMaker EndOfJob upload.
- No-launch runner status command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
  - Result: state remains `status=3dgs_running`, `last_action=3dgs_running`, `3dgs_status=InProgress`; no duplicate launch.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `ede011ba0ffb1043a5d3bed96117d95ae015ed07`; prior exact-head code commit `7b38bd43b956fbfa92700ae513c3b64afee62ec1` has green `CDK Deploy` run `26120469998`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T2203Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2203Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-20260519T2203Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-active-20260519T2203Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-20260519T2203Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-active-20260519T2203Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2203Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2203Z.log`
  - `logs/montana-time-capsule/s3-3dgs-cvhr-mtc-secondary-20260518t2113z-20260519T2203Z.txt`
  - `logs/montana-time-capsule/runner-status-3dgs-20260519T2203Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T2203Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T2203Z.json`
- Next unblocked step: continue monitoring `cvhr-mtc-secondary-20260518t2113z-3dgs` through terminal state. Do not rerun the launcher while this job exists. On success, run the runner once with `--launch` to start pinned Montana compression; on failure, capture exact SageMaker describe, CloudWatch tail, and S3 output before patching.

## 2026-05-19T22:23Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current`, `git rev-parse HEAD`, `git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `1d187651b6d28f17f429b6db485ead2a82272651`; status only showed current-pass evidence after the AWS identity capture (`?? logs/montana-time-capsule/aws-sts-20260519T2223Z.json`) before this monitor pass added new evidence files.
- AWS identity command:
  - `aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Current canonical 3DGS status command:
  - `aws sagemaker describe-training-job --training-job-name cvhr-mtc-secondary-20260518t2113z-3dgs`
  - Result: `TrainingJobStatus=InProgress`, no `FailureReason`; `TrainingStartTime=2026-05-19T13:29:17.980000-06:00`, `TrainingTimeInSeconds=10480`; active phase remains `Training`.
  - Pinned image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`.
  - Input: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`.
  - Output: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/`.
- CV-HR active SageMaker sweep:
  - `aws sagemaker list-training-jobs --name-contains cvhr --status-equals InProgress --max-results 100`
  - Result: two active CV-HR training jobs:
    - canonical time-capsule job `cvhr-mtc-secondary-20260518t2113z-3dgs` (`InProgress`)
    - separate non-mtc job `cvhr-secondary-20260518t2113z-3dgs` (`InProgress`, same input/pinned image, output `s3://spaceport-ml-processing-staging/3dgs/cvhr-secondary-20260518t2113z/`); action taken: none.
  - `aws sagemaker list-processing-jobs --name-contains cvhr --status-equals InProgress --max-results 100`
  - Result: only unrelated viscell processing jobs are active: `cvhr-viscell-full-l05-1779224497` and `cvhr-viscell-full-l07-1779229061`; action taken: none.
- 3DGS log/S3 status:
  - Log stream exists: `cvhr-mtc-secondary-20260518t2113z-3dgs/algo-1-1779218957`; latest stream event timestamp remains `2026-05-19T19:38:17Z`.
  - A 25-minute CloudWatch tail returned `0` lines after the earlier `ns-train splatfacto-w-light ...` launch; still consistent with captured subprocess output while training is active.
  - S3 output remains empty: `Total Objects: 0`, `Total Size: 0`, expected until SageMaker EndOfJob upload.
- No-launch runner status command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
  - Result: state remains `status=3dgs_running`, `last_action=3dgs_running`, `3dgs_status=InProgress`; no duplicate launch.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `1d187651b6d28f17f429b6db485ead2a82272651`; prior exact-head code commit `7b38bd43b956fbfa92700ae513c3b64afee62ec1` has green `CDK Deploy` run `26120469998`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T2223Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2223Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-20260519T2223Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-active-20260519T2223Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-20260519T2223Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-active-20260519T2223Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2223Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2223Z.log`
  - `logs/montana-time-capsule/s3-3dgs-cvhr-mtc-secondary-20260518t2113z-20260519T2223Z.txt`
  - `logs/montana-time-capsule/runner-status-3dgs-20260519T2223Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T2223Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T2223Z.json`
- Next unblocked step: continue monitoring `cvhr-mtc-secondary-20260518t2113z-3dgs` through terminal state. Do not rerun the launcher while this job exists. On success, run the runner once with `--launch` to start pinned Montana compression; on failure, capture exact SageMaker describe, CloudWatch tail, and S3 output before patching.

## 2026-05-19T22:43Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current`, `git rev-parse HEAD`, `git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `e375da6358d0d9de8d4361fd582baec8fcff6f6f`; status only showed current-pass evidence after the AWS identity capture (`?? logs/montana-time-capsule/aws-sts-20260519T2243Z.json`) before this monitor pass added new evidence files.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Current canonical 3DGS status command:
  - `AWS_PAGER= aws sagemaker describe-training-job --training-job-name cvhr-mtc-secondary-20260518t2113z-3dgs --output json`
  - Result: `TrainingJobStatus=InProgress`, no `FailureReason`; `TrainingStartTime=2026-05-19T13:29:17.980000-06:00`, `TrainingTimeInSeconds=11760`; active phase remains `Training`.
  - Pinned image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`.
  - Input: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`.
  - Output: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/`.
- CV-HR active SageMaker sweep:
  - `AWS_PAGER= aws sagemaker list-training-jobs --name-contains cvhr --status-equals InProgress --max-results 100 --output json`
  - Result: two active CV-HR training jobs:
    - canonical time-capsule job `cvhr-mtc-secondary-20260518t2113z-3dgs` (`InProgress`)
    - separate non-mtc job `cvhr-secondary-20260518t2113z-3dgs` (`InProgress`, same input/pinned image, output `s3://spaceport-ml-processing-staging/3dgs/cvhr-secondary-20260518t2113z/`, `TrainingTimeInSeconds=9989`); action taken: none.
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --status-equals InProgress --max-results 100 --output json`
  - Result: only unrelated viscell processing jobs are active: `cvhr-viscell-full-l08-1779230706` and `cvhr-viscell-full-l07-1779229061`; action taken: none.
- 3DGS log/S3 status:
  - Log stream exists: `cvhr-mtc-secondary-20260518t2113z-3dgs/algo-1-1779218957`; latest stream event timestamp remains `2026-05-19T19:38:17Z`.
  - A 25-minute CloudWatch tail returned `0` lines after the earlier `ns-train splatfacto-w-light ...` launch; still consistent with captured subprocess output while training is active.
  - S3 output remains empty: `Total Objects: 0`, `Total Size: 0`, expected until SageMaker EndOfJob upload.
- No-launch runner status command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
  - Result: state remains `status=3dgs_running`, `last_action=3dgs_running`, `3dgs_status=InProgress`, `updated_at=2026-05-19T22:45:56Z`; no duplicate launch.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `e375da6358d0d9de8d4361fd582baec8fcff6f6f`; prior exact-head code commit `7b38bd43b956fbfa92700ae513c3b64afee62ec1` has green `CDK Deploy` run `26120469998`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T2243Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2243Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-3dgs-20260519T2243Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-20260519T2243Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-active-20260519T2243Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-20260519T2243Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-active-20260519T2243Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2243Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2243Z.log`
  - `logs/montana-time-capsule/s3-3dgs-cvhr-mtc-secondary-20260518t2113z-20260519T2243Z.txt`
  - `logs/montana-time-capsule/runner-status-3dgs-20260519T2243Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T2243Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T2243Z.json`
- Next unblocked step: continue monitoring `cvhr-mtc-secondary-20260518t2113z-3dgs` through terminal state. Do not rerun the launcher while this job exists. On success, run the runner once with `--launch` to start pinned Montana compression; on failure, capture exact SageMaker describe, CloudWatch tail, and S3 output before patching.

## 2026-05-19T23:03Z Heartbeat Monitor Pass + Compression Launch

- Branch/head/status command:
  - `git branch --show-current`, `git rev-parse HEAD`, `git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `96f28c696a2bc0113e0bf30360e49d8e5c144b46`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Stale instruction reconciliation:
  - Original canonical SfM `cvhr-mtc-20260518T1729Z-sfm` remains `Stopped`, not active; no action taken against it.
  - Adopted secondary exact-Brass SfM remains the validated input source for downstream stages.
- Current canonical 3DGS status command:
  - `AWS_PAGER= aws sagemaker describe-training-job --training-job-name cvhr-mtc-secondary-20260518t2113z-3dgs --output json`
  - Result: `TrainingJobStatus=Completed`, no `FailureReason`; `TrainingStartTime=2026-05-19T13:29:17.980000-06:00`, `TrainingEndTime=2026-05-19T16:49:14.107000-06:00`, `TrainingTimeInSeconds=11997`, `BillableTimeInSeconds=11997`.
  - Pinned image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`.
  - Input: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`.
  - Output artifact: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/cvhr-mtc-secondary-20260518t2113z-3dgs/output/model.tar.gz`, size `104128001` bytes.
- 3DGS quality/artifact log proof:
  - CloudWatch tail showed `training_completed: True`, `output_file: splat.ply`, `file_size_mb: 109.35029888153076`, `background_skybox: background_skybox.webp`, `background_skybox_size_mb: 0.05258941650390625`.
  - Background selection used `frame_01660.JPG` with `score=0.7296118806998818`.
  - Floater pruning left `462341` gaussians after removing `7`; `evaluated_gaussians=462348`, `candidate_gaussians=190045`.
  - Final log lines: training pipeline completed successfully, SOGS-compatible PLY generated, background skybox baked.
- CV-HR active SageMaker sweep before launch:
  - `AWS_PAGER= aws sagemaker list-training-jobs --name-contains cvhr --status-equals InProgress --max-results 100 --output json`
  - Result: only separate non-mtc job `cvhr-secondary-20260518t2113z-3dgs` remains active; action taken: none.
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --status-equals InProgress --max-results 100 --output json`
  - Result: only unrelated viscell jobs were active before compression launch; action taken against those jobs: none.
- Exact-head workflow command before launch:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `96f28c696a2bc0113e0bf30360e49d8e5c144b46`; prior exact-head code commit `7b38bd43b956fbfa92700ae513c3b64afee62ec1` has green `CDK Deploy` run `26120469998`.
- Compression launch command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: launched exactly one compression job: `cvhr-mtc-secondary-20260518t2113z-compression`.
  - Pinned compressor image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor@sha256:a0784727da1870ce9caa4774dc831a32fb96cd1574df389cf9093fbf18f4f4ab`.
  - Compression input: `s3://spaceport-ml-processing-staging/3dgs/cvhr-mtc-secondary-20260518t2113z/cvhr-mtc-secondary-20260518t2113z-3dgs/output/model.tar.gz`.
  - Compression output: `s3://spaceport-ml-processing-staging/compressed/cvhr-mtc-secondary-20260518t2113z/`.
- Compression verification command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-secondary-20260518t2113z-compression --output json`
  - Result: `ProcessingJobStatus=InProgress`, no `FailureReason`, no `ExitMessage`; `ProcessingStartTime` not yet populated in the immediate post-launch describe.
  - Instance: `ml.g4dn.xlarge`, volume `50` GB, max runtime `86400` seconds.
  - Immediate S3 output remains empty: `Total Objects: 0`, `Total Size: 0`, expected until EndOfJob upload.
  - Immediate CloudWatch stream list was empty and 10-minute tail returned `0` lines, expected immediately after launch.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T2303Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2303Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-3dgs-20260519T2303Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T2303Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T2303Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-20260519T2303Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-active-20260519T2303Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-20260519T2303Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-active-20260519T2303Z.json`
  - `logs/montana-time-capsule/s3-3dgs-cvhr-mtc-secondary-20260518t2113z-20260519T2303Z.txt`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2303Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-secondary-20260518t2113z-3dgs-20260519T2303Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T2303Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T2303Z.json`
  - `logs/montana-time-capsule/launch-compression-20260519T2303Z.log`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-secondary-20260518t2113z-compression-20260519T2305Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-active-20260519T2305Z.json`
  - `logs/montana-time-capsule/s3-compressed-cvhr-mtc-secondary-20260518t2113z-20260519T2305Z.txt`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-secondary-20260518t2113z-compression-20260519T2305Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-secondary-20260518t2113z-compression-20260519T2305Z.log`
- Next unblocked step: monitor `cvhr-mtc-secondary-20260518t2113z-compression`. Do not relaunch compression while this job exists. On success, verify public bundle reachability and hosted viewer with skybox/no-sky modes; on failure, capture exact SageMaker describe, CloudWatch tail, S3 listing, and failure reason before patching.

## 2026-05-19T17:43Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `d08683c7b4cbaedfc61c6dfc094e5958c67ecee1`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`; `ProcessingStartTime=2026-05-18T11:30:29.702000-0600`; `MaxRuntimeInSeconds=86400`. A post-log recheck still returned `InProgress`, so no 3DGS launch was allowed.
- Active CV-HR job guard:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result: canonical `cvhr-mtc-20260518T1729Z-sfm` and non-canonical `cvhr-secondary-20260518t2113z-sfm` both remain active; secondary job env still identifies owner branch `agent-73910482-cvhr-parallel-splat`; no new CV-HR jobs launched from this heartbeat and no jobs stopped.
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - Result: canonical prefix still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker is `InProgress` with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 260m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: canonical SfM remains inside `chunk_bundle_adjuster` global bundle adjustment after merged reconstruction `Images: 1694`, `Points: 1325268`. Repeated COLMAP warnings continued: `Linear solver failure. Failed to compute a finite step.` at `2026-05-19T17:14:17Z`, `17:17:23Z`, `17:20:31Z`, `17:23:55Z`, `17:27:05Z`, `17:30:23Z`, and `17:34:23Z`. No terminal SageMaker failure, OOM, timeout reason, or S3 EndOfJob upload is visible yet.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `d08683c7b4cbaedfc61c6dfc094e5958c67ecee1`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T1743Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1743Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1743Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1743Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-active-filtered-20260519T1743Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T1743Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T1743Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T1743Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T1743Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1743Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T1743Z.json`
- Next unblocked step: continue monitoring the final bundle adjustment and SageMaker terminal status. If SfM reaches `Completed`, immediately run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to launch pinned Montana 3DGS. If SfM reaches `Failed` or times out, capture exact failure describe/log/S3 output before any patch or smallest-stage retry.

## 2026-05-19T17:23Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `9ace293b640fec8265dca43994c354ca8bed5e92`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`; max runtime remains `86400` seconds. A post-tail recheck also remained `InProgress`.
- Active CV-HR job guard:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result: canonical `cvhr-mtc-20260518T1729Z-sfm` and non-canonical `cvhr-secondary-20260518t2113z-sfm` both remain active; secondary job env still identifies owner branch `agent-73910482-cvhr-parallel-splat`; no new CV-HR jobs launched from this heartbeat and no jobs stopped.
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - Result: canonical prefix still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker is `InProgress` with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 220m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 360`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: canonical SfM progressed past chunk merge and remains inside `chunk_bundle_adjuster` global bundle adjustment. New log events now show repeated COLMAP warnings `Linear solver failure. Failed to compute a finite step.` at `2026-05-19T17:14:17Z`, `17:17:23Z`, `17:20:31Z`, and `17:23:55Z`. These are warnings, not a terminal SageMaker failure yet; no OOM, timeout, `FailureReason`, or S3 EndOfJob upload is visible.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `9ace293b640fec8265dca43994c354ca8bed5e92`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T1723Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1723Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1723Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1723Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-active-filtered-20260519T1723Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T1723Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T1723Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T1723Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T1723Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T1723Z-posttail.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1723Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T1723Z.json`
- Next unblocked step: continue monitoring final bundle adjustment and EndOfJob S3 upload. If SfM reaches `Completed`, immediately run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to launch pinned Montana 3DGS. If SfM fails at max runtime, capture exact failure describe/log/S3 output before patching or retrying any smaller stage.

## 2026-05-19T17:03Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `841e78b8243687984b22bdfdbe9b6dc45a59599e`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`; max runtime remains `86400` seconds.
- Active CV-HR job guard:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result: canonical `cvhr-mtc-20260518T1729Z-sfm` and non-canonical `cvhr-secondary-20260518t2113z-sfm` both remain active; secondary job env still identifies owner branch `agent-73910482-cvhr-parallel-splat`; no new CV-HR jobs launched from this heartbeat and no jobs stopped.
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - Result: canonical prefix still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker is `InProgress` with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 210m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 360`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: latest visible canonical log remains `chunk_bundle_adjuster` global bundle adjustment start at `2026-05-19T14:26:28Z`, after `chunk_model_merger_10` succeeded with `Images: 1694`, `Points: 1325268`; log stream last event timestamp remains `1779200788575`. No OOM, timeout, failure, or S3 EndOfJob upload visible yet.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `841e78b8243687984b22bdfdbe9b6dc45a59599e`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T1703Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1703Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1703Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1703Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-active-filtered-20260519T1703Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T1703Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T1703Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T1703Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T1703Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1703Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T1703Z.json`
- Next unblocked step: continue monitoring final bundle adjustment and EndOfJob S3 upload. If SfM reaches `Completed`, immediately run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to launch pinned Montana 3DGS. If SfM fails at max runtime, capture exact failure describe/log/S3 output before patching or retrying any smaller stage.

## 2026-05-19T16:43Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `353608983470f8218ea295cf6f0ddc75b421687b`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`; max runtime remains `86400` seconds.
- Active CV-HR job guard:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result: canonical `cvhr-mtc-20260518T1729Z-sfm` and non-canonical `cvhr-secondary-20260518t2113z-sfm` both remain active; secondary job env still identifies owner branch `agent-73910482-cvhr-parallel-splat`; no new CV-HR jobs launched from this heartbeat and no jobs stopped.
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - Result: canonical prefix still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker is `InProgress` with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 180m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 320`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: latest visible canonical log remains `chunk_bundle_adjuster` global bundle adjustment start at `2026-05-19T14:26:28Z`, after `chunk_model_merger_10` succeeded with `Images: 1694`, `Points: 1325268`; log stream last event timestamp remains `1779200788575`. No OOM, timeout, failure, or S3 EndOfJob upload visible yet.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `353608983470f8218ea295cf6f0ddc75b421687b`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T1643Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1643Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1643Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1643Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-active-filtered-20260519T1643Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T1643Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T1643Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T1643Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T1643Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1643Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T1643Z.json`
- Next unblocked step: continue monitoring final bundle adjustment and EndOfJob S3 upload. If SfM reaches `Completed`, immediately run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to launch pinned Montana 3DGS. If SfM fails at max runtime, capture exact failure describe/log/S3 output before patching or retrying any smaller stage.

## 2026-05-19T16:23Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `3fd772e3781bdc312929cbc2195df1ffe1244db5`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- Active CV-HR job guard:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result: canonical `cvhr-mtc-20260518T1729Z-sfm` and non-canonical `cvhr-secondary-20260518t2113z-sfm` both remain active; secondary job env still identifies owner branch `agent-73910482-cvhr-parallel-splat`; no new CV-HR jobs launched from this heartbeat and no jobs stopped.
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - Result: canonical prefix still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker is `InProgress` with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 150m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 300`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: latest visible canonical log remains `chunk_bundle_adjuster` global bundle adjustment start at `2026-05-19T14:26:28Z`, after `chunk_model_merger_10` succeeded with `Images: 1694`, `Points: 1325268`; log stream last event timestamp remains `1779200788575`. No OOM, timeout, failure, or S3 EndOfJob upload visible yet.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `3fd772e3781bdc312929cbc2195df1ffe1244db5`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T1623Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1623Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1623Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1623Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-active-filtered-20260519T1623Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T1623Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T1623Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T1623Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T1623Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1623Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T1623Z.json`
- Next unblocked step: continue monitoring final bundle adjustment and EndOfJob S3 upload. If SfM reaches `Completed`, immediately run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to launch pinned Montana 3DGS.

## 2026-05-19T16:03Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `54cdb019400de1cf6af06ecfe29aa86fdb2d5bad`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- Active CV-HR job guard:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result: canonical `cvhr-mtc-20260518T1729Z-sfm` and non-canonical `cvhr-secondary-20260518t2113z-sfm` both remain active; secondary job env still identifies owner branch `agent-73910482-cvhr-parallel-splat`; no new CV-HR jobs launched from this heartbeat and no jobs stopped.
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - Result: canonical prefix still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker is `InProgress` with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 120m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 260`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: latest visible canonical log remains `chunk_bundle_adjuster` global bundle adjustment start at `2026-05-19T14:26:28Z`, after `chunk_model_merger_10` succeeded with `Images: 1694`, `Points: 1325268`; log stream last event timestamp remains `1779200788575`. No OOM, timeout, failure, or S3 EndOfJob upload visible yet.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `54cdb019400de1cf6af06ecfe29aa86fdb2d5bad`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T1603Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1603Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1603Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1603Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-active-filtered-20260519T1603Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T1603Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T1603Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T1603Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T1603Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1603Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T1603Z.json`
- Next unblocked step: continue monitoring final bundle adjustment and EndOfJob S3 upload. If SfM reaches `Completed`, immediately run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to launch pinned Montana 3DGS.

## 2026-05-19T15:43Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `bfad2575625621050d0d59150ade80f84fedf578`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- Active CV-HR job guard:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result: canonical `cvhr-mtc-20260518T1729Z-sfm` and non-canonical `cvhr-secondary-20260518t2113z-sfm` both remain active; secondary job env still identifies owner branch `agent-73910482-cvhr-parallel-splat`; no new CV-HR jobs launched from this heartbeat and no jobs stopped.
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - Result: canonical prefix still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker is `InProgress` with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 50m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 260`
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 120m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 260`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: no canonical log lines appeared inside the last 50 minutes; 120-minute evidence still shows `chunk_model_merger_10` succeeded (`Images: 1694`, `Points: 1325268`) and `chunk_bundle_adjuster` began global bundle adjustment at `2026-05-19T14:26:28Z`; log stream last event timestamp is `1779200788575`. No OOM, timeout, failure, or S3 EndOfJob upload visible yet.
- Non-canonical secondary observation:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 50m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 160`
  - Result: secondary job remains active and is still producing COLMAP recovery matcher logs for `chunk_05_vocab_tree_matcher_recovery`; latest sampled progress was `Processing image [120/177]` at `2026-05-19T15:44:49Z`. Action taken: none, because it is owned by another branch and not clearly orphaned.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `bfad2575625621050d0d59150ade80f84fedf578`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T1543Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1543Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1543Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1543Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-active-filtered-20260519T1543Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T1543Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T1543Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T1543Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T1543Z-120m.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T1543Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T1543Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T1543Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1543Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T1543Z.json`
- Next unblocked step: continue monitoring final bundle adjustment and EndOfJob S3 upload. If SfM reaches `Completed`, immediately run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to launch pinned Montana 3DGS.

## 2026-05-19T15:23Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `aedad91173878071497029844ad3c386118a103b`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- Active CV-HR job guard:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result: canonical `cvhr-mtc-20260518T1729Z-sfm` and non-canonical `cvhr-secondary-20260518t2113z-sfm` both remain active; secondary job env still identifies owner branch `agent-73910482-cvhr-parallel-splat`; no new CV-HR jobs launched from this heartbeat.
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - Result: canonical prefix still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker is `InProgress` with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 90m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 260`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: latest visible canonical log remains the final merged-model bundle adjustment start after `chunk_model_merger_10` succeeded (`Images: 1694`, `Points: 1325268`); `chunk_bundle_adjuster` began global bundle adjustment at `2026-05-19T14:26:28Z`; no OOM, timeout, failure, or S3 EndOfJob upload visible yet.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `aedad91173878071497029844ad3c386118a103b`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260519T1523Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1523Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1523Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1523Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-active-filtered-20260519T1523Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T1523Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T1523Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T1523Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T1523Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1523Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T1523Z.json`
- Next unblocked step: continue monitoring final bundle adjustment and EndOfJob S3 upload. If SfM reaches `Completed`, immediately run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to launch pinned Montana 3DGS.

## 2026-05-19T15:02Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `3ab110b4e01eb0117a6d503174814dfadb1e8c2a`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- Active CV-HR job guard:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result: canonical `cvhr-mtc-20260518T1729Z-sfm` and non-canonical `cvhr-secondary-20260518t2113z-sfm` both remain active; no new CV-HR jobs launched from this heartbeat.
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - Result: canonical prefix still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker is `InProgress` with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 45m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: latest visible canonical log remains the final merged-model bundle adjustment start after `chunk_model_merger_10` succeeded (`Images: 1694`, `Points: 1325268`); no OOM, timeout, failure, or S3 EndOfJob upload visible yet.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `3ab110b4e01eb0117a6d503174814dfadb1e8c2a`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1502Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1502Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1502Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-active-filtered-20260519T1502Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T1502Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T1502Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T1502Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T1502Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T1502Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T1502Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1502Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T1502Z.json`
- Next unblocked step: continue monitoring final bundle adjustment and EndOfJob S3 upload. If SfM reaches `Completed`, immediately run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to launch pinned Montana 3DGS.

## 2026-05-19T14:42Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `8bafbe5e294a92b9886b75e51ef013cc9a520941`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- Active CV-HR job guard:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result: canonical `cvhr-mtc-20260518T1729Z-sfm` and non-canonical `cvhr-secondary-20260518t2113z-sfm` both remain active; no new CV-HR jobs launched from this heartbeat.
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - Result: canonical prefix still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker is `InProgress` with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 25m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: latest visible canonical log remains the final merged-model bundle adjustment step after `chunk_model_merger_10` succeeded (`Images: 1694`, `Points: 1325268`); no OOM, timeout, failure, or S3 EndOfJob upload visible yet.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `8bafbe5e294a92b9886b75e51ef013cc9a520941`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1442Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T1442Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1442Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-active-filtered-20260519T1442Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T1442Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T1442Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T1442Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T1442Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T1442Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T1442Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1442Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T1442Z.json`
- Next unblocked step: continue monitoring final bundle adjustment and EndOfJob S3 upload. If SfM reaches `Completed`, immediately run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to launch pinned Montana 3DGS.

## 2026-05-19T14:26Z Interactive Progress Check

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `431422ce535f507398ff8cd37a3d76cb3550aedd`, clean before this check.
- Automation config check:
  - `sed -n '1,220p' /Users/gabrielhansen/.codex/automations/montana-twin-cv-hr-monitor/automation.toml`
  - Result: active heartbeat automation `montana-twin-cv-hr-monitor`, target thread `019e3bf1-e2d1-7453-b4cd-4383b888b1b3`, local cwd `/Users/gabrielhansen/worktrees/md1-baseline-montana-time-capsule`, schedule `FREQ=MINUTELY;INTERVAL=20`.
  - Prior cron automation `cv-hr-montana-time-capsule-monitor` is `PAUSED`, so the active progress keeper is the thread-attached heartbeat automation.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- Material SfM progress:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 20m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 200`
  - Result: canonical SfM is no longer stuck at vocab-tree logging. It completed chunked reconstruction merging through chunk 10. Latest proof:
    - `chunk_model_merger_10` merge succeeded at `2026-05-19T14:26:22Z`.
    - merged reconstruction: `Images: 1694`, `Points: 1325268`.
    - final `chunk_bundle_adjuster` started at `2026-05-19T14:26:28Z`.
    - `--BundleAdjustment.use_gpu` was rejected by this older COLMAP build, then retried with older-compatible flags; this is a compatibility fallback, not a terminal failure.
- Active CV-HR job guard:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result: canonical `cvhr-mtc-20260518T1729Z-sfm` and non-canonical `cvhr-secondary-20260518t2113z-sfm` both remain active; no new CV-HR jobs launched from this check.
- S3 output command:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - Result: still `Total Objects: 0`, `Total Size: 0`; expected while SageMaker is still `InProgress` with `S3UploadMode=EndOfJob`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `431422ce535f507398ff8cd37a3d76cb3550aedd`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T1426Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T1426Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T1426Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T1426Z.txt`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T1426Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-active-filtered-20260519T1426Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T1426Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T1426Z.json`
- Next unblocked step: wait for final bundle adjustment and EndOfJob S3 upload. If SfM reaches `Completed`, immediately run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to launch pinned Montana 3DGS.

## 2026-05-19T06:14Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `3f1ace99d1def55af2ad109f8069dede095cee6e`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- Active CV-HR job guard commands:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - `jq '{ProcessingJobSummaries: [.ProcessingJobSummaries[] | select(.ProcessingJobName | contains("cvhr"))]}' logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0614Z.json`
  - Result: two CV-HR SfM jobs are active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
  - Note: `aws sagemaker list-processing-jobs --name-contains cvhr --status-equals InProgress --max-results 20` returned an empty first page with a `NextToken`; direct describes plus the in-progress filtered sweep above are the authoritative active-state evidence for this pass.
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-secondary-20260518t2113z/colmap/ --output json`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker jobs are running with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 760m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 760m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --output json`
  - Canonical result: latest visible event remains `2026-05-18T19:43:03Z`, at `COLMAP[vocab_tree_builder] ... Building index for visual words...`; SageMaker still reports `InProgress`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `3f1ace99d1def55af2ad109f8069dede095cee6e`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes four active jobs:
    - `md1-viscell-full-l18-1779170653`
    - `md1-viscell-full-l17-1779168816`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0614Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0614Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0614Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-active-filtered-20260519T0614Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-inprogress-20260519T0614Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-all-20260519T0614Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0614Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0614Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T0614Z.json`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T0614Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0614Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0614Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0614Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0614Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0614Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0614Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T05:54Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `2c36864be9fa6ce53fc2be140d317e3c0610c214`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-secondary-20260518t2113z/colmap/ --output json`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker jobs are running with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 640m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 640m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --output json`
  - Canonical result: latest visible event remains `2026-05-18T19:43:03Z`, at `COLMAP[vocab_tree_builder] ... Building index for visual words...`; SageMaker still reports `InProgress`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `2c36864be9fa6ce53fc2be140d317e3c0610c214`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes four active jobs:
    - `md1-viscell-full-l17-1779168816`
    - `md1-viscell-full-l16-1779167589`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0554Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0554Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-all-20260519T0554Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0554Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0554Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0554Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T0554Z.json`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T0554Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0554Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0554Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0554Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0554Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0554Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0554Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T05:34Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `c7e8539581c6d6bc6562d24c2c9492369a2b72d8`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-secondary-20260518t2113z/colmap/ --output json`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker jobs are running with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 620m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 620m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --output json`
  - Canonical result: latest visible event remains `2026-05-18T19:43:03Z`, at `COLMAP[vocab_tree_builder] ... Building index for visual words...`; SageMaker still reports `InProgress`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `c7e8539581c6d6bc6562d24c2c9492369a2b72d8`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes four active jobs:
    - `md1-viscell-full-l17-1779168816`
    - `md1-viscell-full-l16-1779167589`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0534Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0534Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-all-20260519T0534Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0534Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0534Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0534Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T0534Z.json`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T0534Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0534Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0534Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0534Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0534Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0534Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0534Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T05:14Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `81d9922d1b3af1dcd13eb52e009911b50379a864`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-secondary-20260518t2113z/colmap/ --output json`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker jobs are running with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 600m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 600m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --output json`
  - Canonical result: latest visible event remains `2026-05-18T19:43:03Z`, at `COLMAP[vocab_tree_builder] ... Building index for visual words...`; SageMaker still reports `InProgress`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `81d9922d1b3af1dcd13eb52e009911b50379a864`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes four active jobs:
    - `md1-viscell-full-l16-1779167589`
    - `md1-viscell-full-l15-1779167214`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0514Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0514Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-all-20260519T0514Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0514Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0514Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0514Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T0514Z.json`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T0514Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0514Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0514Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0514Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0514Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0514Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0514Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T04:54Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `9875cc471370d001b173061ce711c01b7fa9ad43`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-secondary-20260518t2113z/colmap/ --output json`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker jobs are running with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 580m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 580m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --output json`
  - Canonical result: latest visible event remains `2026-05-18T19:43:03Z`, at `COLMAP[vocab_tree_builder] ... Building index for visual words...`; SageMaker still reports `InProgress`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `9875cc471370d001b173061ce711c01b7fa9ad43`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes four active jobs:
    - `md1-viscell-full-l14-1779164403`
    - `md1-viscell-full-l13-1779164027`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0454Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0454Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-all-20260519T0454Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0454Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0454Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0454Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T0454Z.json`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T0454Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0454Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0454Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0454Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0454Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0454Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0454Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T04:34Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `65a718e8eda3888a6a56cc80ad1703841853e1b3`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-secondary-20260518t2113z/colmap/ --output json`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker jobs are running with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 560m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 560m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --output json`
  - Canonical result: latest visible event remains `2026-05-18T19:43:03Z`, at `COLMAP[vocab_tree_builder] ... Building index for visual words...`; SageMaker still reports `InProgress`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `65a718e8eda3888a6a56cc80ad1703841853e1b3`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes four active jobs:
    - `md1-viscell-full-l14-1779164403`
    - `md1-viscell-full-l13-1779164027`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0434Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0434Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-all-20260519T0434Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0434Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0434Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0434Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T0434Z.json`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T0434Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0434Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0434Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0434Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0434Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0434Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0434Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T04:14Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `89fdb60d44601e0db9a3b8faf3e0c2b73e0e4c93`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep commands:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20 --output json`
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-secondary-20260518t2113z/colmap/ --output json`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still expected while SageMaker jobs are running with `S3UploadMode=EndOfJob`.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 540m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 540m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 220`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --output json`
  - Canonical result: latest visible event remains `2026-05-18T19:43:03Z`, at `COLMAP[vocab_tree_builder] ... Building index for visual words...`; SageMaker still reports `InProgress`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `89fdb60d44601e0db9a3b8faf3e0c2b73e0e4c93`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes four active jobs:
    - `md1-viscell-full-l13-1779164027`
    - `md1-viscell-full-l11-1779161085`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0414Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0414Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260519T0414Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-all-20260519T0414Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0414Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0414Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0414Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T0414Z.json`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T0414Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0414Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0414Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0414Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0414Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0414Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0414Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T03:54Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `a8a0ef5e41b2a5c8f26145c80bcf6e6b580b3148`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20 --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-secondary-20260518t2113z/colmap/ --output json`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still consistent with SageMaker `EndOfJob` output upload while jobs are running.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 320m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 200`
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 320m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 200`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --output json`
  - Canonical result: no canonical events in the last 320 minutes; log stream metadata still reports last event timestamp `1779133383674` (`2026-05-18T19:43:03Z`), at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `a8a0ef5e41b2a5c8f26145c80bcf6e6b580b3148`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes four active jobs:
    - `md1-viscell-full-l12-1779161215`
    - `md1-viscell-full-l11-1779161085`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0354Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0354Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260519T0354Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0354Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0354Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0354Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T0354Z.json`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T0354Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0354Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0354Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0354Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0354Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0354Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0354Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T03:34Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `2211f3bf39d90c1ba7a53b656bfe33cc7d5b0755`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20 --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-secondary-20260518t2113z/colmap/ --output json`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still consistent with SageMaker `EndOfJob` output upload while jobs are running.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 300m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 200`
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 300m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 200`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --output json`
  - Canonical result: no canonical events in the last 300 minutes; log stream metadata still reports last event timestamp `1779133383674` (`2026-05-18T19:43:03Z`), at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `2211f3bf39d90c1ba7a53b656bfe33cc7d5b0755`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes four active jobs:
    - `md1-viscell-full-l12-1779161215`
    - `md1-viscell-full-l11-1779161085`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0334Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0334Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260519T0334Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0334Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0334Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0334Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T0334Z.json`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T0334Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0334Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0334Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0334Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0334Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0334Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0334Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T03:14Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `1faeb092a21c4b1a8b494518ed0f9697a8e3e7e2`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20 --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-secondary-20260518t2113z/colmap/ --output json`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still consistent with SageMaker `EndOfJob` output upload while jobs are running.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 280m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 200`
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 280m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 200`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --output json`
  - Canonical result: no canonical events in the last 280 minutes; log stream metadata still reports last event timestamp `1779133383674` (`2026-05-18T19:43:03Z`), at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `1faeb092a21c4b1a8b494518ed0f9697a8e3e7e2`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes four active jobs:
    - `md1-viscell-full-l10-1779158398`
    - `md1-viscell-full-l09-1779157902`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0314Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0314Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260519T0314Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0314Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0314Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0314Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T0314Z.json`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T0314Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0314Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0314Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0314Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0314Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0314Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0314Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T02:54Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `15bac779546d817900f67ddd46f63a31cf6bea4e`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20 --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-secondary-20260518t2113z/colmap/ --output json`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still consistent with SageMaker `EndOfJob` output upload while jobs are running.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 260m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 200`
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 260m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 200`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --output json`
  - Canonical result: no canonical events in the last 260 minutes; log stream metadata still reports last event timestamp `1779133383674` (`2026-05-18T19:43:03Z`), at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `15bac779546d817900f67ddd46f63a31cf6bea4e`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes five active jobs:
    - `md1-shrunk-prodspine-wlight-202605190027-compression`
    - `md1-viscell-full-l10-1779158398`
    - `md1-viscell-full-l09-1779157902`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0254Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0254Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260519T0254Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0254Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0254Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0254Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T0254Z.json`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T0254Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0254Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0254Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0254Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0254Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0254Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0254Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T02:34Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `92dd7a6c931cbcaca89de6f57e341eb2d6d50bfa`, clean before this heartbeat pass.
- AWS identity command:
  - `aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20 --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap/ --recursive --summarize`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-mtc-20260518T1729Z/colmap/ --output json`
  - `AWS_PAGER= aws s3api list-objects-v2 --bucket spaceport-ml-processing-staging --prefix manual-validations/cvhr-secondary-20260518t2113z/colmap/ --output json`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still consistent with SageMaker `EndOfJob` output upload while jobs are running.
- CloudWatch proof commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 240m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 200`
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 240m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 200`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --output json`
  - Canonical result: no canonical events in the last 240 minutes; log stream metadata still reports last event timestamp `1779133383674` (`2026-05-18T19:43:03Z`), at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `92dd7a6c931cbcaca89de6f57e341eb2d6d50bfa`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes four active jobs:
    - `md1-viscell-full-l09-1779157902`
    - `md1-viscell-full-l08-1779155211`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0234Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0234Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260519T0234Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0234Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0234Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0234Z.txt`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-mtc-20260518T1729Z-20260519T0234Z.json`
  - `logs/montana-time-capsule/s3api-colmap-cvhr-secondary-20260518t2113z-20260519T0234Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0234Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0234Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0234Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0234Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0234Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0234Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T00:30Z Post-Compaction Verification Pass

- Branch/head/status command:
  - `git branch --show-current`
  - `git rev-parse HEAD`
  - `git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `a29f5b011aac85b8db601a3ba4ed665cecc29245`, dirty only from new `logs/montana-time-capsule/` heartbeat evidence.
- AWS identity command:
  - `aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`, no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- S3 output commands:
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap --recursive --summarize`
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap --recursive --summarize`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; this remains expected while SageMaker output upload mode is `EndOfJob`.
- CloudWatch proof commands:
  - `aws logs tail /aws/sagemaker/ProcessingJobs --since 8h --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 200`
  - `aws logs tail /aws/sagemaker/ProcessingJobs --since 8h --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 200`
  - Canonical result: latest visible event remains `2026-05-18T19:43:03Z`, `COLMAP[vocab_tree_builder] ... Loaded a total of 1904336 descriptors` followed by `Building index for visual words...`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, `COLMAP[vocab_tree_builder] ... Loaded a total of 1893703 descriptors` followed by `Building index for visual words...`.
- CV-HR job sweep command:
  - `aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20`
  - Result: two CV-HR jobs remain `InProgress`: canonical `cvhr-mtc-20260518T1729Z-sfm` and non-canonical `cvhr-secondary-20260518t2113z-sfm`. No action taken on the non-canonical job because it is owned by branch `agent-73910482-cvhr-parallel-splat` and is not clearly orphaned.
- Active SageMaker processing sweep:
  - `aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50`
  - Result includes four active jobs:
    - `md1-viscell-full-l06-1779150311`
    - `md1-viscell-full-l05-1779147527`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `a29f5b011aac85b8db601a3ba4ed665cecc29245`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0030Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0030Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260519T0030Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0030Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0030Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0030Z.txt`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0030Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0030Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0030Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0030Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0030Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0030Z.json`
- Next unblocked step: keep monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture the exact describe output, CloudWatch logs, S3 listing, and failure reason before patching or relaunching.

## 2026-05-19T00:49Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `f08d88744bc31dcb87d934951287947aed8bf2e2`, clean before this heartbeat pass.
- AWS identity command:
  - `aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap --recursive --summarize`
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap --recursive --summarize`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still consistent with SageMaker `EndOfJob` output upload while jobs are running.
- CloudWatch proof commands:
  - `aws logs tail /aws/sagemaker/ProcessingJobs --since 90m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 200`
  - `aws logs tail /aws/sagemaker/ProcessingJobs --since 90m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 200`
  - `aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm`
  - `aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm`
  - Canonical result: no canonical events in the last 90 minutes; log stream metadata still reports last event timestamp `1779133383674` (`2026-05-18T19:43:03Z`), at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `f08d88744bc31dcb87d934951287947aed8bf2e2`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50`
  - Result includes four active jobs:
    - `md1-viscell-full-l07-1779151432`
    - `md1-viscell-full-l06-1779150311`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0049Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0049Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260519T0049Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0049Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0049Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0049Z.txt`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0049Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0049Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0049Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0049Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0049Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0049Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T02:12Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `ae57a756b154e4e32fc35952c3f8f593b3a5e5ad`, clean before this heartbeat pass.
- AWS identity command:
  - `aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap --recursive --summarize`
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap --recursive --summarize`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still consistent with SageMaker `EndOfJob` output upload while jobs are running.
- CloudWatch proof commands:
  - `aws logs tail /aws/sagemaker/ProcessingJobs --since 210m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 200`
  - `aws logs tail /aws/sagemaker/ProcessingJobs --since 210m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 200`
  - `aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm`
  - `aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm`
  - Canonical result: no canonical events in the last 210 minutes; log stream metadata still reports last event timestamp `1779133383674` (`2026-05-18T19:43:03Z`), at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `ae57a756b154e4e32fc35952c3f8f593b3a5e5ad`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50`
  - Result includes four active jobs:
    - `md1-viscell-full-l08-1779155211`
    - `md1-viscell-full-l06r2-1779154798`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0212Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0212Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260519T0212Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0212Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0212Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0212Z.txt`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0212Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0212Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0212Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0212Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0212Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0212Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T01:52Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `2264f05528c03106dd2f00d6ac30c736d5c55dab`, clean before this heartbeat pass.
- AWS identity command:
  - `aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap --recursive --summarize`
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap --recursive --summarize`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still consistent with SageMaker `EndOfJob` output upload while jobs are running.
- CloudWatch proof commands:
  - `aws logs tail /aws/sagemaker/ProcessingJobs --since 180m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 200`
  - `aws logs tail /aws/sagemaker/ProcessingJobs --since 180m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 200`
  - `aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm`
  - `aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm`
  - Canonical result: no canonical events in the last 180 minutes; log stream metadata still reports last event timestamp `1779133383674` (`2026-05-18T19:43:03Z`), at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `2264f05528c03106dd2f00d6ac30c736d5c55dab`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50`
  - Result includes four active jobs:
    - `md1-viscell-full-l08-1779155211`
    - `md1-viscell-full-l06r2-1779154798`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0152Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0152Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260519T0152Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0152Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0152Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0152Z.txt`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0152Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0152Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0152Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0152Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0152Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0152Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T01:32Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `9920d0c84e3d3c1e3b94cdbe23ecb78775a65830`, clean before this heartbeat pass.
- AWS identity command:
  - `aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap --recursive --summarize`
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap --recursive --summarize`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still consistent with SageMaker `EndOfJob` output upload while jobs are running.
- CloudWatch proof commands:
  - `aws logs tail /aws/sagemaker/ProcessingJobs --since 150m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 200`
  - `aws logs tail /aws/sagemaker/ProcessingJobs --since 150m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 200`
  - `aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm`
  - `aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm`
  - Canonical result: no canonical events in the last 150 minutes; log stream metadata still reports last event timestamp `1779133383674` (`2026-05-18T19:43:03Z`), at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `9920d0c84e3d3c1e3b94cdbe23ecb78775a65830`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50`
  - Result includes three active jobs:
    - `md1-viscell-full-l07-1779151432`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0132Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0132Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260519T0132Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0132Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0132Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0132Z.txt`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0132Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0132Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0132Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0132Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0132Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0132Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-19T01:09Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `f938443beeac2f39425f76538a76974ae8413876`, clean before this heartbeat pass.
- AWS identity command:
  - `aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap --recursive --summarize`
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap --recursive --summarize`
  - Result: both prefixes still `Total Objects: 0`, `Total Size: 0`; still consistent with SageMaker `EndOfJob` output upload while jobs are running.
- CloudWatch proof commands:
  - `aws logs tail /aws/sagemaker/ProcessingJobs --since 120m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short | tail -n 200`
  - `aws logs tail /aws/sagemaker/ProcessingJobs --since 120m --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm --format short | tail -n 200`
  - `aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm`
  - `aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-secondary-20260518t2113z-sfm`
  - Canonical result: no canonical events in the last 120 minutes; log stream metadata still reports last event timestamp `1779133383674` (`2026-05-18T19:43:03Z`), at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
  - Secondary result: latest visible event remains `2026-05-18T23:31:39Z`, also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `f938443beeac2f39425f76538a76974ae8413876`; last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Active SageMaker processing sweep:
  - `aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50`
  - Result includes four active jobs:
    - `md1-viscell-full-l07-1779151432`
    - `md1-viscell-full-l06-1779150311`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0109Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0109Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260519T0109Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0109Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0109Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0109Z.txt`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0109Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0109Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0109Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0109Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0109Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0109Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. If it fails, capture exact failure artifacts before patching.

## 2026-05-18T23:02Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `9e2a7dd6cd83a3bc362377b1b9b88bcbca3b05f5`; status showed only the newly created `20260518T2302Z` evidence file while the snapshot commands were running.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20 --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap --recursive --summarize`
  - Result: both prefixes still `Total Objects: 0`, expected until SageMaker `EndOfJob` upload.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `9e2a7dd6cd83a3bc362377b1b9b88bcbca3b05f5`. Last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Canonical CloudWatch command:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 30m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - Result: no canonical log in the last 30 minutes. The latest visible canonical event remains the prior `COLMAP[vocab_tree_builder] ... Building index for visual words...` at `2026-05-18T19:43:03Z`; SageMaker still reports `InProgress`.
- Non-canonical CV-HR observation:
  - `cvhr-secondary-20260518t2113z-sfm` remains active and owned by branch `agent-73910482-cvhr-parallel-splat`.
  - Tail showed active chunked COLMAP progress through `chunk_02_mapper_initial` registering `num_reg_frames=50` at `2026-05-18T23:03:10Z`.
  - Action taken: none. It is not clearly orphaned.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes five active processing jobs:
    - `md1-viscell-full-l02-1779143476`
    - `md1-viscell-full-l01-1779141986`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `md1-shrunk-prodspine-sfm-1779128752`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T2302Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260518T2302Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260518T2302Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260518T2302Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260518T2302Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260518T2302Z.txt`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T2302Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260518T2302Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260518T2302Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260518T2302Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. Keep recording the non-canonical secondary job but do not stop it unless clearly proven orphaned.

## 2026-05-18T23:23Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `6022822676b6a4531ca54b06f7fcaacada0c5455`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20 --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap --recursive --summarize`
  - Result: both prefixes still `Total Objects: 0`, expected until SageMaker `EndOfJob` upload.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `6022822676b6a4531ca54b06f7fcaacada0c5455`. Last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Canonical CloudWatch command:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 30m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - Result: no canonical log in the last 30 minutes. The latest visible canonical event remains the prior `COLMAP[vocab_tree_builder] ... Building index for visual words...` at `2026-05-18T19:43:03Z`; SageMaker still reports `InProgress`.
- Non-canonical CV-HR observation:
  - `cvhr-secondary-20260518t2113z-sfm` remains active and owned by branch `agent-73910482-cvhr-parallel-splat`.
  - Tail showed active chunked COLMAP progress through `chunk_03_mapper_initial` registration and BA, including structure-less fallback attempts, at `2026-05-18T23:22:47Z`.
  - Action taken: none. It is not clearly orphaned.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes five active processing jobs:
    - `md1-viscell-full-l02-1779143476`
    - `md1-viscell-full-l01-1779141986`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `md1-shrunk-prodspine-sfm-1779128752`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T2323Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260518T2323Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260518T2323Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260518T2323Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260518T2323Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260518T2323Z.txt`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T2323Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260518T2323Z.log`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260518T2323Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260518T2323Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. Keep recording the non-canonical secondary job but do not stop it unless clearly proven orphaned.

## 2026-05-18T23:43Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `00a49132c4fd5d0bcf9b5a7954b3643272413477`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20 --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap --recursive --summarize`
  - Result: both prefixes still `Total Objects: 0`, expected until SageMaker `EndOfJob` upload.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `00a49132c4fd5d0bcf9b5a7954b3643272413477`. Last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Canonical CloudWatch commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 30m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: no canonical log in the last 30 minutes. Log stream metadata still reports last event timestamp `1779133383674` (`2026-05-18T19:43:03Z`), matching the prior `COLMAP[vocab_tree_builder] ... Building index for visual words...` event; SageMaker still reports `InProgress`.
- Non-canonical CV-HR observation:
  - `cvhr-secondary-20260518t2113z-sfm` remains active and owned by branch `agent-73910482-cvhr-parallel-splat`.
  - Tail showed chunk `chunk_03_spatial_matcher_recovery` finishing verified image pair recovery, then the same vocab-tree step starting with `Loaded a total of 1893703 descriptors` and `Building index for visual words...` at `2026-05-18T23:31:39Z`.
  - Action taken: none. It is not clearly orphaned.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes five active processing jobs:
    - `md1-viscell-full-l02-1779143476`
    - `md1-viscell-full-l01-1779141986`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `md1-shrunk-prodspine-sfm-1779128752`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T2343Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260518T2343Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260518T2343Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260518T2343Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260518T2343Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260518T2343Z.txt`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T2343Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260518T2343Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260518T2343Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260518T2343Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260518T2343Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260518T2343Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. Keep recording the non-canonical secondary job but do not stop it unless clearly proven orphaned.

## 2026-05-19T00:03Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `24af25bcd254708f0f4ec89be203710530f0164c`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20 --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap --recursive --summarize`
  - Result: both prefixes still `Total Objects: 0`, expected until SageMaker `EndOfJob` upload.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `24af25bcd254708f0f4ec89be203710530f0164c`. Last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Canonical CloudWatch commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 30m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: no canonical log in the last 30 minutes. Log stream metadata still reports last event timestamp `1779133383674` (`2026-05-18T19:43:03Z`), matching `COLMAP[vocab_tree_builder] ... Building index for visual words...`; SageMaker still reports `InProgress`.
- Non-canonical CV-HR observation:
  - `cvhr-secondary-20260518t2113z-sfm` remains active and owned by branch `agent-73910482-cvhr-parallel-splat`.
  - Its log stream metadata now reports last event timestamp `1779147099156` (`2026-05-18T23:31:39Z`), also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
  - Action taken: none. It is not clearly orphaned.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes five active processing jobs:
    - `md1-viscell-full-l05-1779147527`
    - `md1-viscell-full-l04-1779146968`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `md1-shrunk-prodspine-sfm-1779128752`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0003Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0003Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260519T0003Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0003Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0003Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0003Z.txt`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0003Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0003Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0003Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0003Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0003Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0003Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. Keep recording the non-canonical secondary job but do not stop it unless clearly proven orphaned.

## 2026-05-19T00:29Z Heartbeat Monitor Pass

- Branch/head/status command:
  - `git branch --show-current && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `a29f5b011aac85b8db601a3ba4ed665cecc29245`, clean before this heartbeat pass.
- AWS identity command:
  - `AWS_PAGER= aws sts get-caller-identity --output json`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Canonical CV-HR SfM status command:
  - `AWS_PAGER= aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: `ProcessingJobStatus=InProgress`, `ProcessingStartTime=2026-05-18T11:30:29.702000-06:00`; no `FailureReason` or `ExitMessage`; pinned SfM image remains `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CV-HR job sweep command:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --name-contains cvhr --max-results 20 --output json`
  - Result: two CV-HR SfM jobs remain active:
    - canonical `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`)
    - non-canonical `cvhr-secondary-20260518t2113z-sfm` (`InProgress`, owner branch env `agent-73910482-cvhr-parallel-splat`, same pinned SfM digest)
- S3 output commands:
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap --recursive --summarize`
  - `AWS_PAGER= aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap --recursive --summarize`
  - Result: both prefixes still `Total Objects: 0`, expected until SageMaker `EndOfJob` upload.
- GitHub exact-head workflow command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` for logs-only `[skip ci]` head `a29f5b011aac85b8db601a3ba4ed665cecc29245`. Last meaningful non-skip `CDK Deploy` remains green on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442`, run `26049509375`.
- Canonical CloudWatch commands:
  - `AWS_PAGER= aws logs tail /aws/sagemaker/ProcessingJobs --since 35m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - `AWS_PAGER= aws logs describe-log-streams --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --output json`
  - Result: no canonical log in the last 35 minutes. Log stream metadata still reports last event timestamp `1779133383674` (`2026-05-18T19:43:03Z`), matching `COLMAP[vocab_tree_builder] ... Building index for visual words...`; SageMaker still reports `InProgress`.
- Non-canonical CV-HR observation:
  - `cvhr-secondary-20260518t2113z-sfm` remains active and owned by branch `agent-73910482-cvhr-parallel-splat`.
  - Its log stream metadata still reports last event timestamp `1779147099156` (`2026-05-18T23:31:39Z`), also at `COLMAP[vocab_tree_builder] ... Building index for visual words...`.
  - Action taken: none. It is not clearly orphaned.
- Active SageMaker processing sweep:
  - `AWS_PAGER= aws sagemaker list-processing-jobs --status-equals InProgress --max-results 50 --output json`
  - Result includes four active processing jobs:
    - `md1-viscell-full-l06-1779150311`
    - `md1-viscell-full-l05-1779147527`
    - `cvhr-secondary-20260518t2113z-sfm`
    - `cvhr-mtc-20260518T1729Z-sfm`
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260519T0029Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0029Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-20260519T0029Z.json`
  - `logs/montana-time-capsule/sagemaker-list-all-inprogress-20260519T0029Z.json`
  - `logs/montana-time-capsule/s3-colmap-cvhr-mtc-20260518T1729Z-20260519T0029Z.txt`
  - `logs/montana-time-capsule/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0029Z.txt`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260519T0029Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0029Z.log`
  - `logs/montana-time-capsule/logstreams-cvhr-mtc-20260518T1729Z-sfm-20260519T0029Z.json`
  - `logs/montana-time-capsule/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0029Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T0029Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T0029Z.json`
- Next unblocked step: continue monitoring canonical `cvhr-mtc-20260518T1729Z-sfm` to terminal. If it completes, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to start pinned Montana 3DGS. Keep recording the non-canonical secondary job but do not stop it unless clearly proven orphaned.

## 2026-05-19T23:40Z Current Final State

- Current canonical completed run: `cvhr-mtc-secondary-20260518t2113z`.
- Final state file: `logs/montana-time-capsule/cv-hr-state.json` reports `status=completed`, `last_action=completed`, `sfm_status=Completed`, `3dgs_status=Completed`, and `compression_status=Completed`.
- Final hosted viewer with skybox:
  - `https://agent-40136728-montana-time.v0-spaceport-website-preview2.pages.dev/sogs-migrated-viewer?url=https%3A%2F%2Fspaceport-ml-processing-staging.s3.us-west-2.amazonaws.com%2Fcompressed%2Fcvhr-mtc-secondary-20260518t2113z%2Fsupersplat_bundle%2Fmeta.json&skybox=background_skybox.webp`
- Final hosted viewer without skybox:
  - `https://agent-40136728-montana-time.v0-spaceport-website-preview2.pages.dev/sogs-migrated-viewer?url=https%3A%2F%2Fspaceport-ml-processing-staging.s3.us-west-2.amazonaws.com%2Fcompressed%2Fcvhr-mtc-secondary-20260518t2113z%2Fsupersplat_bundle%2Fmeta.json&skybox=off`
- Branch Pages deploy proof: run `26131478855` succeeded for exact head `4659864d4478963a49d4e4fc922d4ab687efff99`; preview alias `https://agent-40136728-montana-time.v0-spaceport-website-preview2.pages.dev`, hash URL `https://2e89a848.v0-spaceport-website-preview2.pages.dev`.
- Hosted viewer proof:
  - Skybox smoke passed with finite camera, visible render (`1280x800`, `bright=1014142`, `alpha=1024000`), and HTTP `200` bundled skybox proxy request. Screenshot: `logs/montana-time-capsule/cvhr-hosted-sogs-skybox-smoke-20260519T2323Z.png`.
  - No-sky smoke passed with finite camera, visible render (`1280x800`, `bright=975370`, `alpha=1024000`), and no `background_skybox.webp` request. Screenshot: `logs/montana-time-capsule/cvhr-hosted-sogs-nosky-smoke-20260519T2323Z.png`.
- Artifact facts:
  - Bundle: `s3://spaceport-ml-processing-staging/compressed/cvhr-mtc-secondary-20260518t2113z/supersplat_bundle/meta.json`.
  - SOGS `meta.json`: `461041` gaussians.
  - Compression: source PLY `109.3503 MB`, compressed payload `7.2373 MB`, ratio `15.109x`.
  - Skybox: `background_skybox.webp`, `2048x1024`.
- Active CV-HR SageMaker state at final sweep:
  - No active CV-HR training jobs owned by this automation.
  - Only unrelated active processing jobs matched `cvhr`: `cvhr-viscell-full-l09-1779233441` and `cvhr-viscell-full-l08-1779230706`; no action taken.
- Detailed evidence is in the `2026-05-19T23:23Z Compression Complete, Hosted Viewer Verified` section above and in the `logs/montana-time-capsule/*20260519T2323Z*` artifacts.

## 2026-05-19T23:46Z Post-Push Status Check

- Commit/push completed:
  - Commit: `ff6ed90e82cda1c723abbb9828a84e199a21c5af`
  - Message: `chore: verify cv-hr time capsule viewer [skip ci]`
  - Push: `git push origin agent-40136728-montana-time-capsule`
- Exact-head workflow check:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 20 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]`, expected because the commit is `[skip ci]`. The manual Pages deploy for prior exact head `4659864d4478963a49d4e4fc922d4ab687efff99` remains the hosted viewer proof.
- Current git status after push:
  - `git rev-parse HEAD && git status --short --branch`
  - Result: head `ff6ed90e82cda1c723abbb9828a84e199a21c5af`, branch up to date with origin, with only the post-push evidence files pending when this line was written.
- Current active CV-HR SageMaker sweep:
  - `aws sagemaker list-training-jobs --status-equals InProgress --name-contains cvhr --max-results 20`: no active CV-HR training jobs.
  - `aws sagemaker list-processing-jobs --status-equals InProgress --name-contains cvhr --max-results 20`: active jobs are `cvhr-secondary-20260518t2113z-compression`, `cvhr-viscell-full-l09-1779233441`, and `cvhr-viscell-full-l08-1779230706`.
  - Action taken: none. These are not the canonical completed time-capsule run `cvhr-mtc-secondary-20260518t2113z`; `cvhr-secondary-20260518t2113z-compression` writes to `s3://spaceport-ml-processing-staging/compressed/cvhr-secondary-20260518t2113z/`, while the verified hosted output uses `s3://spaceport-ml-processing-staging/compressed/cvhr-mtc-secondary-20260518t2113z/`.
- Evidence files:
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260519T2345Z-postpush.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260519T2345Z-postpush.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-cvhr-active-20260519T2346Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-cvhr-active-20260519T2346Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-secondary-20260518t2113z-compression-20260519T2346Z.json`

## 2026-05-20T20:16Z HMC Cloud Object Found + SfM Launched

- User clarification: HMC should already be in the cloud, likely uploaded Friday/Saturday. No new HMC upload was performed.
- Branch/head/status preflight:
  - Branch: `agent-40136728-montana-time-capsule`
  - Head at launch: `c6e9377759144d46d4b4ee74b75bcf35b30eb3e1`
  - AWS identity: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Existing cloud object found:
  - ZIP: `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip`
  - Manifest: `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.manifest.json`
  - Upload proof from S3 head: ZIP `LastModified=2026-05-16T17:35:27+00:00`, `ContentLength=8646557673`, ETag `"ed86661a82b28856997a09f129ce6bec-1031"`, metadata `dataset=hmc`, `photo-count=2063`, SHA-256 `8ac35927d5c90969f5e10f1fa011333e6065140924986c75f18fc81f899b1df2`.
  - Manifest proof: `photoCount=2063`, `flatZipBytes=8646557673`, same SHA-256, first flat image `hmc_0001_DJI_0661.JPG`, last flat image `hmc_2063_DJI_0717.JPG`.
  - Runner ZIP central-directory validation: `2063` entries, `2063` images, first five `hmc_0001_DJI_0661.JPG` through `hmc_0005_DJI_0665.JPG`, last five `hmc_2059_DJI_0715.JPG` through `hmc_2063_DJI_0717.JPG`.
- Duplicate-job guards before launch:
  - `aws sagemaker list-processing-jobs --name-contains hmc --max-results 50`: no matching processing jobs.
  - `aws sagemaker list-training-jobs --name-contains hmc --max-results 50`: no matching training jobs.
  - `aws sagemaker list-processing-jobs --name-contains hmc-mtc --max-results 50`: no matching processing jobs.
  - `aws sagemaker list-training-jobs --name-contains hmc-mtc --max-results 50`: no matching training jobs.
- Runner change:
  - `scripts/montana_time_capsule/cv_hr_time_capsule.py` is now dataset-parameterized while preserving CV-HR defaults.
  - Validation: `python3 -m py_compile scripts/montana_time_capsule/cv_hr_time_capsule.py`.
- Dry run/state init:
  - Command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --dataset-id HMC --run-prefix hmc-mtc --subset-strategy hmc_full_2063_montana_time_capsule --input-s3-uri s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip --expected-image-count 2063 --state-file logs/montana-time-capsule/hmc-state.json --search-prefix HMC --search-token hmc`
  - Result: `last_action=ready_to_launch_sfm`, run id `hmc-mtc-20260520T2015Z`.
- Launch command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --dataset-id HMC --run-prefix hmc-mtc --subset-strategy hmc_full_2063_montana_time_capsule --input-s3-uri s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip --expected-image-count 2063 --state-file logs/montana-time-capsule/hmc-state.json --search-prefix HMC --search-token hmc --launch`
- Current active stage:
  - SfM processing job: `hmc-mtc-20260520T2015Z-sfm`
  - SfM ARN: `arn:aws:sagemaker:us-west-2:975050048887:processing-job/hmc-mtc-20260520T2015Z-sfm`
  - Status at launch verification: `InProgress`
  - Input: `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip`
  - Output: `s3://spaceport-ml-processing-staging/manual-validations/hmc-mtc-20260520T2015Z/colmap`
  - Image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`
  - Environment: `COLMAP_ENABLE_SPATIAL_CHUNKING=1`, `COLMAP_CHUNK_MIN_CORE_REGISTERED_RATIO=0.90`, `SFM_BENCHMARK_SUBSET_STRATEGY=hmc_full_2063_montana_time_capsule`.
  - Instance: `ml.g4dn.xlarge`, volume `100` GB, max runtime `86400` seconds.
  - Initial CloudWatch tail: no log events yet immediately after launch.
  - Initial S3 output listing: empty as expected until EndOfJob upload.
- Post-launch duplicate guard:
  - Re-running the HMC runner with the same `--launch` command at `2026-05-20T20:18Z` returned `last_action=sfm_running`, `sfm_status=InProgress`, and did not create a second job.
- Automation:
  - Existing monitor `cv-hr-montana-time-capsule-monitor` was repointed to HMC and remains active every 20 minutes in this chat/worktree.
- Evidence files:
  - `logs/montana-time-capsule/hmc-head-zip-20260520T0025Z.json`
  - `logs/montana-time-capsule/hmc-head-manifest-20260520T0025Z.json`
  - `logs/montana-time-capsule/hmc-manifest-summary-20260520T0026Z.txt`
  - `logs/montana-time-capsule/hmc-state.json`
  - `logs/montana-time-capsule/hmc-launch-20260520T0028Z.log`
  - `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260520T0029Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260520T0029Z.log`
  - `logs/montana-time-capsule/s3-sfm-output-hmc-mtc-20260520T2015Z-20260520T0029Z.txt`
  - `logs/montana-time-capsule/hmc-runner-hold-20260520T0032Z.json`
- Next unblocked step: poll `hmc-mtc-20260520T2015Z-sfm` until it reaches `Completed`; then run the same HMC runner command with `--launch` exactly once to launch the pinned Montana 3DGS job.

## 2026-05-20T20:23Z HMC Post-Push + First SfM Logs

- Commit/push:
  - Commit: `8a536ba434cfb0b771a9967c531de364128ec0e6`
  - Message: `chore: launch hmc time capsule sfm`
  - Push: `git push origin agent-40136728-montana-time-capsule`
- Exact-head workflow check:
  - `CDK Deploy` run `26187619621` completed successfully for exact head `8a536ba434cfb0b771a9967c531de364128ec0e6`.
  - Exact-head workflow list contains only that `CDK Deploy` run; no Pages run was triggered for this script/log launch commit.
- Current HMC SfM state:
  - Job `hmc-mtc-20260520T2015Z-sfm` remains `InProgress`.
  - Latest describe snapshot still uses pinned SfM image `sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
  - CloudWatch log stream is live. The job started the Montana COLMAP GPU processor, downloaded the `8646557673` byte HMC ZIP, extracted `2063` images, detected GPS EXIF priors and orientation priors on `2063` images, prepared a `2063` image list ordered by capture time then filename, and started GPU SIFT feature extraction.
  - Latest sampled feature extraction progress: processed file `[4/2063]` by `2026-05-20T20:23:03Z`.
  - S3 output remains empty as expected until EndOfJob upload.
- Evidence files:
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-hmc-postpush-20260520T0035Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-hmc-postpush-20260520T0035Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-hmc-postcdk-20260520T0040Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-hmc-postcdk-20260520T0040Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260520T0036Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260520T0040Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260520T0040Z.log`
- Next unblocked step: continue polling feature extraction and later mapping/chunk output for `hmc-mtc-20260520T2015Z-sfm`; do not launch 3DGS until SfM is `Completed`.

## 2026-05-20T20:42Z HMC SfM Monitor Pass (No Duplicate Launch)

- Branch/head/status:
  - Branch: `agent-40136728-montana-time-capsule`
  - Head: `0a57250d0d8824bd1dc61f3787c0e807ebd44e8d` (`[skip ci]`)
  - Status: clean (plus 2 untracked local viewer screenshots pending commit).
- AWS identity:
  - Account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- HMC upload object proof (user expected Friday/Saturday May 15-16, 2026):
  - Found at `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip` with `8646557673` bytes, ETag `"ed86661a82b28856997a09f129ce6bec-1031"`, LastModified `2026-05-16T17:35:27Z`.
  - Confirmed missing at `s3://spaceport-uploads-staging/1778952912508-hmc-high-mountain-camp-images-flat.zip` (`404 Not Found`), so no re-upload was attempted.
- SageMaker state:
  - `hmc-mtc-20260520T2015Z-sfm`: `InProgress`
  - Duplicate-job guard: `aws sagemaker list-processing-jobs --name-contains hmc-mtc --status-equals InProgress` still shows only the single SfM job.
- Output S3 state:
  - `s3://spaceport-ml-processing-staging/manual-validations/hmc-mtc-20260520T2015Z/colmap/` lists `0` objects while SfM is running (`S3UploadMode=EndOfJob`).
- Guarded advance:
  - Re-running the same HMC runner `--launch` command held at `status=sfm_running` and did not create a second job.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260520T203433Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260520T203442Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-hmc-20260520T203442Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-hmc-active-20260520T203442Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-hmc-20260520T203442Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-hmc-active-20260520T203442Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260520T203450Z.log`
  - `logs/montana-time-capsule/hmc-sfm-poll-20260520T203613Z.log`
  - `logs/montana-time-capsule/s3-head-spaceport-uploads-20260520T203520Z.json`
  - `logs/montana-time-capsule/s3-head-spaceport-uploads-staging-20260520T203520Z.err`
  - `logs/montana-time-capsule/s3-list-spaceport-uploads-prefix-177895-20260520T203520Z.json`
  - `logs/montana-time-capsule/s3-list-spaceport-uploads-staging-prefix-177895-20260520T203520Z.json`
  - `logs/montana-time-capsule/s3-list-hmc-sfm-output-20260520T203606Z.txt`
  - `logs/montana-time-capsule/hmc-launch-20260520T204232Z.cmd.txt`
  - `logs/montana-time-capsule/hmc-launch-20260520T204232Z.log`
- Next unblocked step: keep polling `hmc-mtc-20260520T2015Z-sfm` until `Completed`; then run the same HMC runner command with `--launch` once to launch pinned Montana 3DGS.

## 2026-05-20T20:46Z Ledger Commit + Push

- Commit: `73c34cb362ce0a780c3f2c2310f7c0bd680cbe95`
- Message: `chore: record hmc sfm monitor pass [skip ci]`
- Push: `git push origin agent-40136728-montana-time-capsule`
- Exact-head workflow check:
  - `gh run list --branch agent-40136728-montana-time-capsule ...` filtered to exact head returned `[]` (expected for `[skip ci]`).
- Evidence files:
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260520T204452Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260520T204452Z.json`

## 2026-05-20T21:16Z HMC Monitor Pass

- Branch/head/status:
  - `agent-40136728-montana-time-capsule` @ `f8ae947ae5d821758a78e52c4041a3da0028522f` (clean).
- Exact-head workflows:
  - Exact-head `gh run list ... --commit f8ae947a` returned `[]` (expected for `[skip ci]` head).
- AWS identity:
  - `/opt/homebrew/bin/aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- SageMaker SfM status:
  - `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name hmc-mtc-20260520T2015Z-sfm` -> `ProcessingJobStatus=InProgress`, pinned SfM image `sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- HMC archive proof (no upload):
  - `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip` `LastModified=2026-05-16T17:35:27Z`, size `8646557673`, ETag `ed86661a82b28856997a09f129ce6bec-1031`.
  - Manifest `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.manifest.json` `LastModified=2026-05-16T17:49:54Z`.
  - Confirmed absent in `s3://spaceport-uploads-staging/` (404 HeadObject + empty prefix list).
- Runner status:
  - `logs/montana-time-capsule/hmc-state.json`: `status=sfm_running`, `sfm_status=InProgress` (no downstream jobs yet).
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-get-caller-identity-20260520T211424Z.json`
  - `logs/montana-time-capsule/sagemaker-list-hmc-mtc-20260520T2015Z-20260520T211424Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260520T211424Z.json`
  - `logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260520T211505Z.json`
  - `logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.manifest.json-20260520T211505Z.json`
  - `logs/montana-time-capsule/s3-head-spaceport-uploads-staging-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260520T211505Z.json`
  - `logs/montana-time-capsule/s3-head-spaceport-uploads-staging-1778952912508-hmc-high-mountain-camp-images-flat.manifest.json-20260520T211505Z.json`
  - `logs/montana-time-capsule/s3-list-spaceport-uploads-prefix-1778952912508-20260520T211505Z.json`
  - `logs/montana-time-capsule/s3-list-spaceport-uploads-staging-prefix-1778952912508-20260520T211505Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260520T211520Z.json`
  - `logs/montana-time-capsule/hmc-advance-nolaunch-20260520T211604Z.json`
  - `logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260520T211617Z.json`
  - `logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260520T211627Z.json`
- Next unblocked step: keep polling `hmc-mtc-20260520T2015Z-sfm` until `Completed`; then run the same HMC runner command with `--launch` once to create pinned Montana 3DGS.

## 2026-05-20T21:18Z Ledger Commit + Push

- Commit: `a1c549ce19f01400f6c1f1350e4d183e4b9a0d33`
- Message: `chore: record hmc sfm poll evidence [skip ci]`
- Push: `git push origin agent-40136728-montana-time-capsule`
- Exact-head workflow check:
  - Exact-head `gh run list ... --commit a1c549ce` returned `[]` (expected for `[skip ci]` head).
- Evidence files:
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260520T211854Z-postpush.json`

## 2026-05-20T21:55Z Monitor Pass (HMC Archive Proven; SfM Still Running)

- Git:
  - Branch: `agent-40136728-montana-time-capsule`
  - Head: `edbd99f36618102e1917ed2e34a00fb02d0dc661` (`[skip ci]`)
- AWS identity:
  - `arn:aws:iam::975050048887:root` (account `975050048887`, region `us-west-2`)
- HMC archive proof (no upload performed):
  - S3 URI: `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip`
  - LastModified: `2026-05-16T17:35:27Z`
  - Size: `8,646,557,673` bytes
  - ETag: `ed86661a82b28856997a09f129ce6bec-1031`
  - Metadata: `sha256=8ac35927d5c90969f5e10f1fa011333e6065140924986c75f18fc81f899b1df2`, `photo-count=2063`, `source=dropbox`
  - Manifest: `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.manifest.json` (LastModified `2026-05-16T17:49:54Z`, size `352,691` bytes)
- SageMaker:
  - Job: `hmc-mtc-20260520T2015Z-sfm`
  - Status: `InProgress` (output is `EndOfJob`, so S3 prefix stays empty until completion)
  - Pinned image: `.../spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`
  - CloudWatch proof: chunk mapper is actively registering images (see tail log)
- Evidence files:
  - `logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260520T215420Z.log`
  - `logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260520T215452Z.json`
- Next unblocked step: keep polling until SfM `Completed` (or `Failed`); if `Completed`, launch the pinned Montana 3DGS stage exactly once (no duplicates).

## 2026-05-20T22:17Z Ledger Commit + Push

- Commit: `785799d68827fe7ff3737a95c1d5a7aa6bc932c3`
- Message: `chore: record hmc monitor evidence [skip ci]`
- Push: `git push origin agent-40136728-montana-time-capsule`
- Exact-head workflow check:
  - Exact-head `gh run list` returned `[]` (expected for `[skip ci]` head).
- Evidence files:
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260520T221728Z-postpush.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260520T221728Z-postpush.json`

## 2026-05-20T22:18Z Exact-Head Workflow Check (Current Head)

- Branch/head: `agent-40136728-montana-time-capsule` @ `2924a24568eb9b81b44afce26f8163ab80be99b7` (`[skip ci]`)
- Exact-head `gh run list` result: `[]` (expected for `[skip ci]` head).
- Evidence files:
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260520T221812Z-postpush2.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260520T221812Z-postpush2.json`

## 2026-05-20T21:56Z Ledger Commit + Push

- Commit: `7de8797425f1d703b5dfe071cf74d228ee0754cc`
- Message: `chore: record hmc sfm poll evidence [skip ci]`
- Push: `git push origin agent-40136728-montana-time-capsule`
- Exact-head workflow check:
  - Exact-head `gh run list ... --commit 7de87974` returned `[]` (expected for `[skip ci]` head).
- Evidence files:
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260520T215605Z-postpush.json`

## 2026-05-20T22:15Z HMC Monitor Pass

- Branch/head/status:
  - Branch: `agent-40136728-montana-time-capsule`
  - Head: `92c842b7f4483988356d9ce5e0db32376e7dc4d4` (`[skip ci]`)
- AWS identity:
  - `arn:aws:iam::975050048887:root` (account `975050048887`, region `us-west-2`)
- HMC archive proof (no upload performed):
  - ZIP: `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip`
  - LastModified: `2026-05-16T17:35:27Z`
  - Size: `8,646,557,673` bytes
  - ETag: `ed86661a82b28856997a09f129ce6bec-1031`
  - Manifest: `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.manifest.json`
  - Staging upload bucket negative: list prefix in `s3://spaceport-uploads-staging/` returned empty.
- SageMaker:
  - Job: `hmc-mtc-20260520T2015Z-sfm`
  - Status: `InProgress`
  - Pinned image: `.../spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`
  - CloudWatch proof: chunked mapper is actively producing models (e.g. `chunk_03_mapper_initial model 0 registered 142/142 images and 103107 points` at `2026-05-20T22:13:28Z`).
  - Output: `EndOfJob` (S3 prefix remains empty until completion).
- S3 output prefix: `s3://spaceport-ml-processing-staging/manual-validations/hmc-mtc-20260520T2015Z/`
  - Result: still empty as of this pass.
- GitHub workflows:
  - Exact-head `gh run list` returned `[]` (expected for `[skip ci]` head).
  - Latest branch workflow: `CDK Deploy` completed success on head `8a536ba434cfb0b771a9967c531de364128ec0e6`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-get-caller-identity-20260520T221411Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260520T221411Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-hmc-mtc-20260520T2015Z-20260520T221411Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-hmc-active-20260520T221411Z.json`
  - `logs/montana-time-capsule/sagemaker-list-training-hmc-active-20260520T221411Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260520T221421Z.log`
  - `logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260520T221439Z.json`
  - `logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.manifest.json-20260520T221439Z.json`
  - `logs/montana-time-capsule/s3-list-spaceport-uploads-1778952912508-hmc-high-mountain-camp-20260520T221439Z.json`
  - `logs/montana-time-capsule/s3-list-spaceport-uploads-staging-hmc-20260520T221439Z.json`
  - `logs/montana-time-capsule/s3-list-ml-processing-hmc-mtc-20260520T2015Z-20260520T221447Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260520T221506Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260520T221506Z.json`
- Next unblocked step: keep polling until SfM `Completed` (or `Failed`); if `Completed`, launch the pinned Montana 3DGS stage exactly once (no duplicates).

## 2026-05-20T22:45Z HMC Monitor Pass (No Duplicate Uploads/Jobs)

- Branch/head/status:
  - Branch: `agent-40136728-montana-time-capsule`
  - Head: `7cff0084de5d4bd39b9546814dd1e2b2faeeb503` (`[skip ci]`)
- AWS identity:
  - `arn:aws:iam::975050048887:root` (account `975050048887`, region `us-west-2`)
- HMC archive proof (no upload performed; staging search exhausted by prefix evidence):
  - ZIP exists in: `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip` (LastModified `2026-05-16T17:35:27Z`, size `8,646,557,673`, ETag `ed86661a82b28856997a09f129ce6bec-1031`)
  - Manifest exists in: `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.manifest.json`
  - Negative in staging uploads bucket: `aws s3api head-object` and `list-objects-v2 --prefix 1778952912508` both returned empty/404 for `spaceport-uploads-staging`.
  - Negative in all other `spaceport-uploads*` buckets: prefix search for `1778952912508` hit only `spaceport-uploads` (no staging/branch upload buckets contained the key/prefix).
- SageMaker:
  - Job: `hmc-mtc-20260520T2015Z-sfm`
  - Status: `InProgress` (3 polls at `22:36:46Z`, `22:38:47Z`, `22:40:48Z`)
  - CloudWatch proof: SfM is in mapping phase (e.g. `chunk_07_mapper_initial` registering images) as of `2026-05-20T22:42:50Z`.
  - Output: `EndOfJob` (S3 prefix still empty as expected).
- S3 output prefix:
  - `s3://spaceport-ml-processing-staging/manual-validations/hmc-mtc-20260520T2015Z/colmap/`
  - Result: empty as of this pass.
- GitHub workflows:
  - Exact-head `gh run list` returned `[]` (expected for `[skip ci]` head); evidence saved.
- Evidence files (this pass):
  - `logs/montana-time-capsule/aws-sts-get-caller-identity-20260520T2219Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260520T2219Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260520T2241Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260520T2219Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260520T2241Z.log`
  - `logs/montana-time-capsule/hmc-sfm-poll-20260520T223646Z.log`
  - `logs/montana-time-capsule/s3-list-buckets-20260520T2220Z.json`
  - `logs/montana-time-capsule/s3-head-spaceport-uploads-staging-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260520T2221Z.json`
  - `logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260520T2221Z.json`
  - `logs/montana-time-capsule/s3-list-spaceport-uploads-staging-prefix-1778952912508-20260520T2221Z.json`
  - `logs/montana-time-capsule/s3-list-spaceport-uploads-prefix-1778952912508-20260520T2221Z.json`
  - `logs/montana-time-capsule/s3-search-uploads-buckets-prefix-1778952912508-20260520T2222Z.txt`
  - `logs/montana-time-capsule/gh-run-list-exact-head-7cff0084-20260520T2223Z.json`
- Next unblocked step: keep polling until SfM becomes `Completed`; immediately after completion, run `python3 scripts/montana_time_capsule/hmc_time_capsule.py --launch` once to start pinned 3DGS (avoid duplicates).

## 2026-05-20T22:46Z Post-Push Exact-Head Workflow Proof

- Branch head after ledger push: `ebffa1eea7d6c9a83c2e2fc8785b2cb15be8f2b4` (`[skip ci]`)
- Exact-head `gh run list` result: `[]` (no workflows triggered by this logs-only push).
- Latest successful branch workflows (for reference): `CDK Deploy` success on `8a536ba4`, and Pages deploy success on `4659864d` (see evidence JSON).
- Evidence files:
  - `logs/montana-time-capsule/gh-run-list-exact-head-ebffa1ee-20260520T2246Z.json`
  - `logs/montana-time-capsule/gh-run-list-branch-latest-20260520T2246Z.json`

## 2026-05-20T23:16Z HMC Monitor Pass (No Launch)

- Git:
  - Branch head: `6268e3e7d01c4a54a7e2ad5f7e0f1472cc40e895` (`[skip ci]`)
- AWS identity:
  - `arn:aws:iam::975050048887:root` (account `975050048887`, region `us-west-2`)
- Proven HMC archive (do not re-upload):
  - `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip` (`LastModified=2026-05-16T17:35:27Z`, `Size=8646557673`)
  - `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.manifest.json` (`LastModified=2026-05-16T17:49:54Z`)
  - Confirmed missing in `s3://spaceport-uploads-staging/` (`404` HeadObject; empty prefix list).
- SageMaker:
  - `hmc-mtc-20260520T2015Z-sfm` remains `InProgress` (pinned SfM image sha256: `8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`).
  - Output remains `EndOfJob` (S3 prefix still empty as expected while job is running).
- GitHub workflows:
  - Exact-head `gh run list` returned `[]` (expected for `[skip ci]` head); evidence saved.
- Runner:
  - Refreshed `logs/montana-time-capsule/hmc-state.json` using `cv_hr_time_capsule.py` without `--launch` (no new jobs created).
- Evidence files (this pass):
  - `logs/montana-time-capsule/aws-sts-get-caller-identity-20260520T231643Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260520T231643Z.json`
  - `logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260520T231643Z.json`
  - `logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.manifest.json-20260520T231643Z.json`
  - `logs/montana-time-capsule/s3-list-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-20260520T231643Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-6268e3e7-20260520T231643Z.json`
  - `logs/montana-time-capsule/gh-run-list-branch-latest-20260520T231643Z.json`
  - `logs/montana-time-capsule/runner-hmc-20260520T231547Z.log`
- Next unblocked step: keep polling until SfM becomes `Completed`; immediately after completion, run `python3 scripts/montana_time_capsule/hmc_time_capsule.py --launch` once to start pinned 3DGS (avoid duplicates).

## 2026-05-20T23:34Z Monitor Pass (HMC)

- Repo/worktree: /Users/gabrielhansen/worktrees/md1-baseline-montana-time-capsule
- Git head check command:
  - `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --porcelain=v1 -b`
  - Result: branch `agent-40136728-montana-time-capsule`, head `851d3228b1d3ac84d11f8709c2832b55e3357ac2`, status clean.
- AWS identity command: `aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.

### HMC archive proof (do not re-upload)

- Zip head-object command: `aws s3api head-object --bucket spaceport-uploads --key 1778952912508-hmc-high-mountain-camp-images-flat.zip`
  - Result: LastModified `2026-05-16T17:35:27Z`, Size `8646557673` (~8.65GB), ETag `ed86661a82b28856997a09f129ce6bec-1031`.
- Manifest head-object command: `aws s3api head-object --bucket spaceport-uploads --key 1778952912508-hmc-high-mountain-camp-images-flat.manifest.json`
  - Result: LastModified `2026-05-16T17:49:54Z`, Size `352691`, ETag `1e0ee825159077dc4e1781ba75cd3386`.
- Evidence files:
  - logs/montana-time-capsule/s3-head-spaceport-uploads-hmc-zip-20260520T233435Z.json
  - logs/montana-time-capsule/s3-head-spaceport-uploads-hmc-manifest-20260520T233435Z.json

### SageMaker (SfM)

- Describe command: `aws sagemaker describe-processing-job --processing-job-name hmc-mtc-20260520T2015Z-sfm`
  - Result: `ProcessingJobStatus=InProgress` (LastModified `2026-05-20T20:18:53Z`).
- Duplicate guard command: `aws sagemaker list-processing-jobs --name-contains hmc-mtc-20260520T2015Z --max-results 20`
  - Result: only one matching job (`hmc-mtc-20260520T2015Z-sfm`, `InProgress`).
- CloudWatch tail command: `aws logs tail /aws/sagemaker/ProcessingJobs --since 20m --log-stream-name-prefix hmc-mtc-20260520T2015Z-sfm --format short`
  - Result: chunked sequential matcher actively progressing (chunk_13). No failure indicators.
- Output S3 listing command: `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/hmc-mtc-20260520T2015Z/ --recursive --human-readable --summarize`
  - Result: empty (expected until `S3UploadMode=EndOfJob`).
- Evidence files:
  - logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260520T233401Z.json
  - logs/montana-time-capsule/sagemaker-list-hmc-mtc-20260520T2015Z-20260520T233402Z.json
  - logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260520T233402Z.log

### Runner state refresh (no launch)

- Refresh command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --dataset-id HMC --run-prefix hmc-mtc-20260520T2015Z --profile brass-chunked --input-s3-uri s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip --state-file logs/montana-time-capsule/hmc-state.json`
  - Result: state remains `status=sfm_running`, `sfm_status=InProgress`.
- Evidence file:
  - logs/montana-time-capsule/runner-refresh-20260520T233435Z.log

### GitHub Actions (exact-head)

- Workflow list command:
  - `gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url`
  - Exact-head filter: `.[] | select(.headSha=="$(git rev-parse HEAD)")`
  - Result: `[]` (expected for `[skip ci]` ledger-only head).
- Evidence files:
  - logs/montana-time-capsule/gh-run-list-agent-40136728-20260520T233402Z.json
  - logs/montana-time-capsule/gh-run-list-exact-head-20260520T233402Z.json

## Next unblocked step

- Keep polling `hmc-mtc-20260520T2015Z-sfm` until `Completed`.

## 2026-05-20T23:55Z Monitor Pass (HMC)

- Branch/head/status:
  - `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `76803c8ed74224e6b1aa3eb7431d8ff7ca1cbdf5`, status clean.
- AWS identity:
  - `aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Proven HMC archive (do not re-upload):
  - `aws s3api head-object --bucket spaceport-uploads --key 1778952912508-hmc-high-mountain-camp-images-flat.zip`
  - Result: `LastModified=2026-05-16T17:35:27Z`, `ContentLength=8646557673`, `ETag=ed86661a82b28856997a09f129ce6bec-1031`.
- SageMaker SfM state:
  - `aws sagemaker describe-processing-job --processing-job-name hmc-mtc-20260520T2015Z-sfm`
  - Result: `ProcessingJobStatus=InProgress` (no failure).
  - CloudWatch tail (mapping still active): `aws logs tail /aws/sagemaker/ProcessingJobs --since 20m --log-stream-name-prefix hmc-mtc-20260520T2015Z-sfm --format short`
    - Sample: `chunk_14_mapper_initial` registering images; retriangulation + global bundle adjustment observed.
- Output S3 prefix (EndOfJob upload; still empty):
  - `aws s3 ls s3://spaceport-ml-processing-staging/manual-validations/hmc-mtc-20260520T2015Z/ --recursive --human-readable --summarize`
  - Result: `Total Objects: 0` (expected until job completion).
- Runner refresh (NO launch):
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --dataset-id HMC --run-prefix hmc-mtc-20260520T2015Z --profile brass-chunked --input-s3-uri s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip --state-file logs/montana-time-capsule/hmc-state.json --search-prefix HMC --search-token hmc`
  - Result: `status=sfm_running`, `sfm_status=InProgress` (no new jobs created).
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260520T235433Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260520T235438Z.log`
  - `logs/montana-time-capsule/s3-list-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-20260520T235457Z.txt`
  - `logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260520T235502Z.json`
  - `logs/montana-time-capsule/sagemaker-list-hmc-mtc-20260520T2015Z-20260520T235507Z.json`
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260520T235521Z.json`
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260520T235526Z.json`
  - `logs/montana-time-capsule/refresh-hmc-state-20260520T235539Z.log`
- Next unblocked step: keep polling until `hmc-mtc-20260520T2015Z-sfm` becomes `Completed`, then run the same runner command with `--launch` exactly once to launch pinned Montana 3DGS.
- Then run the runner exactly once with `--launch` to start the pinned Montana 3DGS stage.

## 2026-05-21T00:17:10Z monitor
- git head: d2529186a46363719592367ff5671b47c8f0d7f7 (branch agent-40136728-montana-time-capsule)
- aws sts: (missing)
- sfm job: hmc-mtc-20260520T2015Z-sfm status=unknown (region us-west-2)
- sagemaker describe: (missing)
- cloudwatch tail: (missing)
- proven input zip head: (missing)
- proven manifest head: (missing)
- s3 outputs listing: (missing)
- gh runs branch list: (missing)
- gh runs exact-head list: (missing) (expected empty due to [skip ci])
- note: ListProcessingJobs throttled earlier; see logs/montana-time-capsule/aws-throttle-20260521T001438Z.log
- next: wait for SFM Completed; then launch pinned 3DGS (sha256:482c1789...)

## 2026-05-21T00:17:31Z monitor (corrected file pointers)
- git head: d2529186a46363719592367ff5671b47c8f0d7f7 (branch agent-40136728-montana-time-capsule)
- aws sts: logs/montana-time-capsule/aws-sts-20260521T001418Z.json
- sfm job: hmc-mtc-20260520T2015Z-sfm status=InProgress (region us-west-2)
- sagemaker describe: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T001418Z.json
- cloudwatch tail: logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260521T001418Z.log
- proven input zip head: logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260521T001534Z.json
- proven manifest head: logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.manifest.json-20260521T001534Z.json
- s3 outputs listing: logs/montana-time-capsule/s3-ls-spaceport-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-20260521T001534Z.txt
- gh runs branch list: logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T001608Z.json
- gh runs exact-head list: logs/montana-time-capsule/gh-run-list-exact-head-d2529186a46363719592367ff5671b47c8f0d7f7-20260521T001608Z.json (expected empty due to [skip ci])
- next: wait for SFM Completed; then launch pinned 3DGS (sha256:482c1789...)

## 2026-05-21T00:36:37Z monitor (HMC)
- git head: f5abcf8bc918b6e96166396fa102ffef499e6821 (branch agent-40136728-montana-time-capsule)
- aws sts: (live) account 975050048887 arn arn:aws:iam::975050048887:root
- proven input zip head: logs/montana-time-capsule/s3-head-spaceport-uploads-hmc-20260521T003533Z.json
  - proof: spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip LastModified=2026-05-16T17:35:27Z ContentLength=8646557673 ETag=ed86661a82b28856997a09f129ce6bec-1031
- staging upload-bucket sample scan (no hmc keys in first page): logs/montana-time-capsule/s3-list-spaceport-uploads-staging-sample-20260521T003533Z.json
- sfm job: hmc-mtc-20260520T2015Z-sfm status=InProgress (region us-west-2)
- sagemaker describe: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T003533Z.json
- cloudwatch stream evidence: logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T003539Z.json
  - sample: chunk_15_spatial_matcher_recovery + vocab_tree_builder started at 2026-05-21T00:01:34Z
- runner refresh (NO launch): logs/montana-time-capsule/hmc-runner-20260521T003636Z.json
  - result: status=sfm_running sfm_status=InProgress
- gh runs branch list (last meaningful): `gh run list --branch agent-40136728-montana-time-capsule --limit 20`
  - latest CDK Deploy success 2026-05-20T20:19:47Z; no exact-head runs expected for [skip ci] commit f5abcf8b
- gh run list evidence: logs/montana-time-capsule/gh-run-list-agent-40136728-20260521T003731Z.json
- next: wait for SFM Completed; then run runner once with `--launch` to start pinned Montana 3DGS (sha256:482c1789...)

## 2026-05-21T00:56:13Z monitor (HMC)
- git head: bd49d09871ae7454163b442c044964320f0e02aa (branch agent-40136728-montana-time-capsule)
- aws sts: account 975050048887 arn arn:aws:iam::975050048887:root (region us-west-2)
- proven input zip head: logs/montana-time-capsule/s3-head-hmc-spaceport-uploads-20260521T005400Z.json
  - proof: spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip LastModified=2026-05-16T17:35:27Z ContentLength=8646557673 ETag=ed86661a82b28856997a09f129ce6bec-1031
- proven manifest list: aws s3api list-objects-v2 --bucket spaceport-uploads --prefix 177895 (shows .manifest.json + .zip)
- sfm job: hmc-mtc-20260520T2015Z-sfm status=InProgress
- sagemaker describe: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T005450Z.json
- cloudwatch tail (last 20m): empty (no new events observed in this window)
- s3 outputs listing: s3://spaceport-ml-processing-staging/manual-validations/hmc-mtc-20260520T2015Z/colmap/ empty (expected until EndOfJob)
- gh run list evidence: logs/montana-time-capsule/gh-run-list-20260521T005449Z.txt (latest CDK Deploy success 2026-05-20T20:19:47Z)
- next: wait for SFM Completed; then run runner once with `--launch` to start pinned Montana 3DGS (sha256:482c1789...)

## 2026-05-21T01:58Z Monitor Pass (HMC)

- Repo/worktree: /Users/gabrielhansen/worktrees/md1-baseline-montana-time-capsule
- Git branch/head/status:
  - `agent-40136728-montana-time-capsule`
  - head `81f08fbcbf1b32713cf040ae8cbbc79c6b9076ba`
  - status clean (`## agent-40136728-montana-time-capsule...origin/agent-40136728-montana-time-capsule`)
- AWS identity: account `975050048887`, arn `arn:aws:iam::975050048887:root` (region `us-west-2`)

### HMC archive proof (do not re-upload; staging search exhausted)

- Confirmed object exists in staging account in bucket `spaceport-uploads`:
  - `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip`
  - Head proof: LastModified `2026-05-16T17:35:27Z`, Size `8646557673` (~8.65GB), ETag `ed86661a82b28856997a09f129ce6bec-1031`
  - Timestamp proof: key prefix `1778952912508` decodes to `2026-05-16T17:35:12.508Z`
- Confirmed manifest exists and matches the zip:
  - `s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.manifest.json`
  - Manifest proof: `photoCount=2063`, `flatZipBytes=8646557673`, `flatZipSha256=8ac35927d5c90969f5e10f1fa011333e6065140924986c75f18fc81f899b1df2`
  - Source zip size (original Dropbox zip): `8831871811` (~8.83GB) recorded in the manifest.
- Exhaustive search result (by name tokens + May epoch prefixes): no matching HMC artifacts discovered in `spaceport-uploads-staging`.

### SageMaker (SfM)

- Job: `hmc-mtc-20260520T2015Z-sfm`
- Status: `InProgress` (pinned image sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811)
- CloudWatch evidence (last 6h): spatial matcher recovery + vocab tree builder fallback observed at ~`2026-05-21T00:01Z`.
- Output prefix still empty (expected until `S3UploadMode=EndOfJob`):
  - `s3://spaceport-ml-processing-staging/manual-validations/hmc-mtc-20260520T2015Z/colmap`

### GitHub Actions (exact head)

- Latest branch runs are green:
  - Deploy Next.js to Cloudflare Pages run `26200368328` succeeded (alias + hash URLs captured in log).
  - CDK Deploy run `26200368245` succeeded.
- Preview URLs (from the Pages job log):
  - Alias: `https://agent-40136728-montana-time.v0-spaceport-website-preview2.pages.dev`
  - Hash: `https://9480e9f2.v0-spaceport-website-preview2.pages.dev`

### Runner refresh (no launch)

- Refreshed `logs/montana-time-capsule/hmc-state.json` using `cv_hr_time_capsule.py` without `--launch` (no new jobs created).

### Evidence files (this pass)

- `logs/montana-time-capsule/verify-basics-20260521T015341Z.log`
- `logs/montana-time-capsule/gh-run-26200368328-pages.log`
- `logs/montana-time-capsule/gh-run-26200368245-cdk.log`
- `logs/montana-time-capsule/s3-search-hmc-20260521T015611Z.json`
- `logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260521T015611Z.json`
- `logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.manifest.json-20260521T015611Z.json`
- `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T015445Z.json`
- `logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260521T015510Z-since6h.log`
- `logs/montana-time-capsule/hmc-state-refresh-20260521T015726Z.json`

### Next unblocked step

- Keep polling until SfM becomes `Completed`; immediately after completion, run once (and only once) to launch pinned 3DGS:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --dataset-id HMC --run-prefix hmc-mtc --subset-strategy hmc_full_2063_montana_time_capsule --expected-image-count 2063 --state-file logs/montana-time-capsule/hmc-state.json --launch`

## 2026-05-21T02:02Z CI confirmation (post-ledger push)

- Head: `ea326957ebd0f742be6628b9bb2e4dda35b80256`
- CDK Deploy: run `26200937278` succeeded (triggered by push of the ledger/evidence commit).
- Pages: latest branch deploy run remains green: `26200368328` (no web changes in the ledger commit, so no new Pages run expected).
- Evidence:
  - `logs/montana-time-capsule/gh-run-26200937278-cdk.json`
  - `logs/montana-time-capsule/gh-run-list-branch-20260521T020329Z.txt`

## 2026-05-21T02:19Z HMC monitor pass (SfM still running)

- Branch/head/status:
  - `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short --branch`
  - Result: `agent-40136728-montana-time-capsule` @ `46b06e996fad0d106e95097eac905d7dd4bf216f` (clean; tracking origin).
- AWS identity:
  - `/opt/homebrew/bin/aws sts get-caller-identity`
  - Result: account `975050048887` (staging), ARN `arn:aws:iam::975050048887:root`.
- SageMaker:
  - `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name hmc-mtc-20260520T2015Z-sfm`
  - Result: `ProcessingJobStatus=InProgress` (no FailureReason).
  - Duplicate-job guard: only one `InProgress` job matching `hmc|mtc`: `hmc-mtc-20260520T2015Z-sfm`.
- HMC archive proof (no re-upload):
  - `/opt/homebrew/bin/aws s3api head-object --bucket spaceport-uploads --key 1778952912508-hmc-high-mountain-camp-images-flat.zip`
  - Result: `LastModified=2026-05-16T17:35:27Z`, `ContentLength=8646557673`, `ETag=ed86661a82b28856997a09f129ce6bec-1031`.
  - Confirmed **not** present in `spaceport-uploads-staging` (404).
- CloudWatch:
  - Latest log event observed at `2026-05-21T00:01:36Z` (no newer events in the `hmc-mtc-20260520T2015Z-sfm` stream during this pass).
- Output S3:
  - `s3://spaceport-ml-processing-staging/manual-validations/hmc-mtc-20260520T2015Z/` currently empty (upload mode is `EndOfJob`).

### Evidence files (this pass)

- Canonical (UTC-stamped):
  - `logs/montana-time-capsule/aws-sts-20260521T022041Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T022041Z.json`
  - `logs/montana-time-capsule/sagemaker-list-processing-inprogress-20260521T022041Z.json`
  - `logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260521T022041Z.json`
  - `logs/montana-time-capsule/s3-list-processing-hmc-mtc-20260520T2015Z-20260521T022041Z.json`
  - `logs/montana-time-capsule/cloudwatch-streams-hmc-mtc-20260520T2015Z-sfm-20260521T022041Z.json`
- `logs/montana-time-capsule/aws-sts-20260521T1930Z.json`
- `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T1930Z.json`
- `logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T1939Z.json`
- `logs/montana-time-capsule/sagemaker-list-processing-inprogress-20260521T1930Z.json`
- `logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260521T1931Z.json`
- `logs/montana-time-capsule/s3-head-spaceport-uploads-staging-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260521T1931Z.json`
- `logs/montana-time-capsule/cloudwatch-streams-hmc-mtc-20260520T2015Z-sfm-20260521T1936Z.json`
- `logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260521T1932Z-since6h.log`
- `logs/montana-time-capsule/s3-list-processing-hmc-mtc-20260520T2015Z-20260521T1934Z.json`

### Next unblocked step

- Poll until `hmc-mtc-20260520T2015Z-sfm` reaches `Completed` (or `Failed/Stopped`); if `Completed`, run exactly once to launch pinned 3DGS via:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --dataset-id HMC --run-prefix hmc-mtc --subset-strategy hmc_full_2063_montana_time_capsule --expected-image-count 2063 --state-file logs/montana-time-capsule/hmc-state.json --launch`

## 2026-05-21T02:25Z CI confirmation (post-monitor commit)

- Head: `a2b8f4fb6e8ebe88d704c87f827b18510bd198cd`
- CDK Deploy: run `26201626086` succeeded (triggered by push of `chore: monitor HMC time capsule SfM`).
- Evidence:
  - `logs/montana-time-capsule/gh-run-26201626086-cdk.json`
# 2026-05-21T02:36Z monitor tick
- git: agent-40136728-montana-time-capsule @ 71d2f2fae3b00c99e4d6d336321dc817e0adba2a (clean)
- aws sts: logs/montana-time-capsule/aws-sts-20260521T023409Z.json (Account=975050048887, region=us-west-2)
- gh runs (exact head): logs/montana-time-capsule/gh-run-list-agent-40136728-20260521T023544Z.json (CDK Deploy + Pages green)
- post-push CDK Deploy proof (7422efd9): logs/montana-time-capsule/gh-run-26202111411-cdk-20260521T024119Z.json
- s3 HMC zip HEAD: logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260521T023726Z.json (8,646,557,673 bytes; LastModified=2026-05-16T17:35:27Z)
- s3 HMC manifest HEAD: logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.manifest.json-20260521T023726Z.json (photoCount=2063; flatZipSha256=8ac35927...)
- sagemaker describe: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T023423Z.json (InProgress)
- cloudwatch lastEvent: logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T023511Z.json (2026-05-21T00:01:36Z)
- runner (NO launch): logs/montana-time-capsule/runner-hmc-20260521T023622Z.log (state refreshed; still sfm_running)
- followup poll (NO launch): logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T024358Z.json + logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T024358Z.json (still stalled @ 2026-05-21T00:01:36Z)

# 2026-05-21T02:56Z monitor tick
- git: agent-40136728-montana-time-capsule @ 2456f84f811f723d6653b789b0b3314eb012ee99 (clean)
- aws sts: logs/montana-time-capsule/aws-sts-20260521T025641Z.json (Account=975050048887, region=us-west-2)
- gh runs (exact head): logs/montana-time-capsule/gh-run-list-exact-head-20260521T030000Z.json (expected empty for [skip ci])
- s3 HMC zip HEAD: logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260521T025641Z.json (8,646,557,673 bytes; LastModified=2026-05-16T17:35:27Z; Metadata.sha256=8ac35927...)
- sagemaker describe: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T025641Z.json (InProgress)
- cloudwatch streams: logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T025641Z.json (lastEventTimestamp => 2026-05-21T00:01:36Z)
- cloudwatch filter: logs/montana-time-capsule/cloudwatch-filter-hmc-mtc-20260520T2015Z-sfm-20260521T025641Z.json (latest log events; no new progress past 00:01:36Z)
- output S3: logs/montana-time-capsule/s3-ls-processing-hmc-mtc-20260520T2015Z-20260521T025641Z.txt (Total Objects: 0; upload mode is EndOfJob)

# 2026-05-21T03:16Z monitor tick
- git: agent-40136728-montana-time-capsule @ 52b387126f5a0b1d45abe074bcb400859e1177f7 (clean; tracking origin)
- aws sts: logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T031420Z.json (Account=975050048887, region=us-west-2)
- gh run list (branch): logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T031548Z.json (no runs for head=52b38712; last non-skip green remains 88b1848f)
- s3 HMC archive list: logs/montana-time-capsule/s3-list-spaceport-uploads-1778952912508-hmc-flat-20260521T031605Z.json (zip+manifest only; LastModified 2026-05-16)
- sagemaker describe: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T031422Z.json (InProgress; LastModifiedTime still 2026-05-20T20:18Z; no FailureReason)
- cloudwatch tail: logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T031535Z.json (still stalled at 2026-05-21T00:01:36Z: vocab_tree_builder building index)
- output S3: logs/montana-time-capsule/s3-list-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T031424Z.json (0 objects; EndOfJob upload)
- runner refresh (NO launch): logs/montana-time-capsule/runner-hmc-20260521T031629Z.log (state refreshed; still sfm_running)

# 2026-05-21T03:18Z post-push workflow check
- git: agent-40136728-montana-time-capsule @ c656f775a22cf750801a4d04caf0bb57a8a33d1d
- gh run list evidence (no runs for this [skip ci] head): logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T031745Z.json

## 2026-05-21T03:36Z monitor tick
- git head: agent-40136728-montana-time-capsule @ 5a94a67162623694262de7b2483d92a402b22863 ([skip ci] head; no new GH runs expected)
- AWS: sts=logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T033426Z.json (acct 975050048887, us-west-2)
- Input proven (no re-upload):
  - s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip head=logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260521T033557Z.json
  - manifest head=logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.manifest.json-20260521T033557Z.json
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T033432Z.json; re-poll=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T033818Z.json)
  - CloudWatch stream lastEventTimestamp still 2026-05-21T00:01:36Z (logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T033432Z.json)
  - last log lines (vocab_tree_builder building index) captured: logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260521T033939Z-window15m.txt (raw JSON: logs/montana-time-capsule/cloudwatch-filter-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T033939Z-window15m.json)
  - output prefix still empty (EndOfJob upload): logs/montana-time-capsule/s3-ls-colmap-output-hmc-mtc-20260520T2015Z-20260521T033608Z.txt
- CI proof remains from last non-[skip ci] heads: gh run list (CDK success + Pages success) captured previously; no new run for 5a94a671.
- Next: continue polling until SfM completes; only then run pinned 3DGS stage once.

## 2026-05-21T03:41Z CI proof (post-push)
- head pushed: 0e4faf83f05eb49a22d8864b2bbb0441c9abcdb6 ([skip ci])
- gh run list: logs/montana-time-capsule/gh-run-list-agent-40136728-20260521T034108Z.json
- runs for head: 0 (expected due to [skip ci]); last relevant green runs remain Pages 26200368328 + CDK 26202111411.

## 2026-05-21T03:42Z CI proof (latest head)
- head pushed: fa44a59d60422e5eb86b17a324108b35c62121a0 ([skip ci])
- gh run list: logs/montana-time-capsule/gh-run-list-agent-40136728-20260521T034219Z.json
- runs for head: 0 (expected due to [skip ci])

## 2026-05-21T03:42Z CI proof (latest head)
- head pushed: fa44a59d60422e5eb86b17a324108b35c62121a0 ([skip ci])
- gh run list: logs/montana-time-capsule/gh-run-list-agent-40136728-20260521T034129Z.json
- runs for head: 0 (expected due to [skip ci])

## 2026-05-21T03:43Z CI proof (exact head)
- head pushed: 373b0996c4c1612732d31935f0b32a90e752fd01 ([skip ci])
- gh run list: logs/montana-time-capsule/gh-run-list-agent-40136728-postpush-20260521T034210Z.json
- runs for head: 0 (expected due to [skip ci])

## 2026-05-21T04:20:05Z Monitor Tick

- Git head: 03b6c57b08ce1e2e26b8f2708e4b1b9f1d748c53
- AWS identity: arn:aws:iam::975050048887:root
- HMC input: s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip (LastModified 2026-05-16T17:35:27Z, size 8646557673)
- SageMaker job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress
  - lastModified: 2026-05-20T14:18:53.916000-06:00
- CloudWatch latest event: 2026-05-21T00:01:36.365000Z
- Evidence:
  - logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T041940Z.json
  - logs/montana-time-capsule/cloudwatch-streams-hmc-mtc-20260520T2015Z-sfm-20260521T041940Z.json
  - logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260521T041450Z-since12h.log
  - logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260521T041605Z.json
  - logs/montana-time-capsule/hmc-input-manifest-20260521T041617Z.json

## 2026-05-21T04:36:51Z Monitor Tick

- Git: agent-40136728-montana-time-capsule @ 70edc8c1c3410eab935f8ca5e6e7f2e3c80ba2f4 ([skip ci])
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T043416Z.json (acct 975050048887)
- Input proven (no re-upload):
  - s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip head=logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260521T043540Z.json
  - s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.manifest.json head=logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.manifest.json-20260521T043540Z.json
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T043428Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T043428Z.json)
  - CloudWatch stream lastEventTimestamp still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T043506Z.json; summary=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T043506Z.summary.txt)
  - Last log line captured: `Building index for visual words...` (events=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T043610Z-since2355Z.json; summary=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T043610Z-since2355Z.summary.txt)
  - output prefix still empty (EndOfJob upload): logs/montana-time-capsule/s3-ls-colmap-output-hmc-mtc-20260520T2015Z-20260521T043540Z.txt (raw list=logs/montana-time-capsule/s3-list-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T043540Z.json)
- Runner refresh (NO launch): logs/montana-time-capsule/runner-hmc-20260521T043651Z.json (still sfm_running)
- CI (exact head): no runs for 70edc8c due to [skip ci] (head runs=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-head-20260521T043555Z.json). Latest branch green runs remain:
  - Pages: 26200368328 (gh run list=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T043555Z.json)
  - CDK: 26202111411 (gh run list=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T043555Z.json)

Next: continue polling until SfM becomes Completed; only then run pinned 3DGS stage once.

## 2026-05-21T04:38:47Z Post-push CI proof

- Git head pushed: 4f706585b411dac50d3db3d8078570dcddbba4ff ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-head-postpush-20260521T043810Z.json)

## 2026-05-21T04:56:20Z Monitor Tick

- Git: agent-40136728-montana-time-capsule @ 791f4684b586dacb8d742c10f9e445a72d81a520 ([skip ci])
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T045418Z.json (acct 975050048887)
- Input proven (no re-upload):
  - s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip head=logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260521T045510Z.json
  - s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.manifest.json head=logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.manifest.json-20260521T045510Z.json
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T045430Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-20260521T045520Z.json)
  - CloudWatch lastEventTimestamp still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T045458Z.json; events=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T045458Z-since6h.json)
  - output prefix still empty (EndOfJob upload): logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T045430Z.txt
- CI (exact head): no runs for 791f4684 due to [skip ci] (runs list=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T045542Z.json). Latest green runs on branch remain:
  - Pages: 26200368328 (sha 88b1848f5700cae039c8ea4dbda31a6790b6dc69)
  - CDK: 26202111411 (sha 7422efd9f9c9e1de23f82a09f991435839a6c365)

Next: continue polling until SfM becomes Completed; do not launch 3DGS until SfM output exists.

## 2026-05-21T09:55:32Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 26c74bced88c04a6a402da692e1852a2ee626016
  - status: logs/montana-time-capsule/git-status-20260521T095413Z.txt
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T095413Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T095413Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T095413Z.json)
  - CloudWatch newest stream last event still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T095413Z.json; last=logs/montana-time-capsule/cloudwatch-last-event-hmc-mtc-20260520T2015Z-sfm-20260521T095413Z.txt; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T095413Z-tail.json)
  - output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T095413Z.json
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T095531Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress; updated_at=2026-05-21T09:55:32Z)
- CI: exact head is [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T095413Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T095413Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T08:34:42Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ c78a1168e41d107bc7b6425f7e65a7743ca11aee (`chore: record post-push ci proof 20260521T0818Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T083442Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T083442Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T083442Z.json)
  - CloudWatch newest event still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T083442Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T083442Z-tail.json)
  - output prefix still empty (EndOfJob upload): logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T083442Z.txt (Total Objects: 0)
- CI (exact head): 0 runs for this [skip ci] head (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T083534Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T083534Z.json)

Next: continue polling until SfM becomes Completed and the colmap output prefix is non-empty; do not launch 3DGS until SfM output exists.

## 2026-05-21T08:37:10Z Post-push CI proof

- Git head pushed: 292eaecae258202b9976fee57da94dab1ee380a4 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T083710Z.json)

## 2026-05-21T05:57:07Z Post-push CI proof

- Git head pushed: 640f02f4ade38eb6665448997a7705a984226bab ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T055707Z.json)

## 2026-05-21T05:56:01Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 6ed27b4db887bf4ff2c3a8a3f3fb5828a36f5f39 (`chore: record sfm poll 20260521T0539Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T055407Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T055420Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T055420Z.json)
  - CloudWatch newest event still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T055427Z.json; events=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm_algo-1-1779308230-20260521T055435Z.json)
  - output prefix still empty (EndOfJob upload): logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T055505Z.txt (Total Objects: 0)
- CI: exact head is [skip ci]; latest branch run list refreshed at logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T055517Z.json (last green Pages+CDK are unchanged).

Next: continue polling until SfM becomes Completed; do not launch 3DGS until SfM output exists.

### 2026-05-21T05:39:05Z quick re-poll (120s later)
- SageMaker describe: logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T053844Z.json (still InProgress; LastModifiedTime unchanged)
- CloudWatch (since 2h): logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T053844Z-since2h.json (0 events)

## 2026-05-21T06:37:09Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ f8a56b1330aeafc3a9f86d114b4b49012c1abe8d (`chore: record post-push ci proof 20260521T0618Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T063423Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T063423Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T063423Z.json)
  - CloudWatch newest event still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T063450Z.json; events=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm_algo-1-20260521T063720Z-tail.json)
  - output prefix still empty (EndOfJob upload): logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T063423Z.txt (Total Objects: 0)
- CI: exact head is [skip ci]; refreshed branch run list at logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T063705Z.json (latest green Pages+CDK unchanged).

Next: continue polling until SfM becomes Completed; do not launch 3DGS until SfM output exists.

## 2026-05-21T05:34:14Z Monitor tick

- Git: agent-40136728-montana-time-capsule @ c752d273cd3b5ef683a527debdd0a009c938d148 ([skip ci])
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T053414Z.json (acct 975050048887)
- Input proven (no re-upload):
  - s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip head=logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260521T053504Z.json
  - s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.manifest.json head=logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.manifest.json-20260521T053504Z.json
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T053414Z.json)
  - CloudWatch latest event still 2026-05-21T00:01:36.365Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T053439Z.json; events=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T053439Z-since6h.json)
  - output prefix still empty (EndOfJob upload): s3://spaceport-ml-processing-staging/manual-validations/hmc-mtc-20260520T2015Z/colmap
- CI (exact head): 0 runs for this [skip ci] head (runs list=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T053511Z.json). Latest branch green runs remain:
  - Pages: 26200368328 (sha 88b1848f5700cae039c8ea4dbda31a6790b6dc69)
  - CDK: 26202111411 (sha 7422efd9f9c9e1de23f82a09f991435839a6c365)

Next: continue polling until SfM becomes Completed; do not launch 3DGS until SfM output exists.

## 2026-05-21T05:19:05Z Post-push CI proof

- Git head pushed: a690f2c1f102d523227ea1c6b008ef6bd1a75843 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-head-postpush-20260521T051858Z.json)

## 2026-05-21T04:58:11Z Post-push CI proof

- Git head pushed: 95016bdafbe2a494c60cd656c44af1a498904ded ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-head-postpush-20260521T045724Z.json)

## 2026-05-21T05:17:30Z Monitor tick

- Git: agent-40136728-montana-time-capsule @ 83b5cbac5960d26b1d8a26c9d2ac26fdff3b3818 ([skip ci])
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T051438Z.json (acct 975050048887)
- Input proven (no re-upload):
  - s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip head=logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.zip-20260521T051623Z.json (8,646,557,673 bytes; LastModified=2026-05-16T17:35:27Z; ETag ed86661a...-1031)
  - s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.manifest.json head=logs/montana-time-capsule/s3-head-spaceport-uploads-1778952912508-hmc-high-mountain-camp-images-flat.manifest.json-20260521T051623Z.json
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T051438Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T051438Z.json)
  - CloudWatch latest logs still end at 2026-05-21T00:01:36Z (tail=logs/montana-time-capsule/cloudwatch-tail-hmc-mtc-20260520T2015Z-sfm-20260521T051523Z-since12h.log; last line: Building index for visual words...)
  - output prefix still empty (EndOfJob upload): logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T051623Z.txt (Total Objects: 0)
- CI (exact head): 0 runs for this [skip ci] head (logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-head-20260521T051650Z.json)

Next: continue polling until SfM becomes Completed; do not launch 3DGS until SfM output exists.

## 2026-05-21T10:36:24Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 931c6a3c1cbd1dd28aa0fc1ed555dd9f9c8caace ()
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T103405Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T103405Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T103405Z.json)
  - CloudWatch newest stream last event still  (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T103405Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T103405Z-tail.json; last=logs/montana-time-capsule/cloudwatch-last-event-hmc-mtc-20260520T2015Z-sfm-20260521T103405Z.tsv)
  - output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T103405Z.json
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T103405Z.log (state file logs/montana-time-capsule/hmc-state.json)
- CI: exact head is [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T103405Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T103405Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T10:36:43Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 931c6a3c1cbd1dd28aa0fc1ed555dd9f9c8caace
  - status: logs/montana-time-capsule/git-status-20260521T103405Z.txt
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T103405Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T103405Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T103405Z.json)
  - CloudWatch newest stream last event still 2026-05-21T00:01:36.365000Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T103405Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T103405Z-tail.json; last=logs/montana-time-capsule/cloudwatch-last-event-hmc-mtc-20260520T2015Z-sfm-20260521T103405Z.tsv)
  - output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T103405Z.json
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T103405Z.log (state file logs/montana-time-capsule/hmc-state.json)
- CI: exact head is [skip ci] (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T103405Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T103405Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T10:37:39Z Post-push CI proof (HMC)

- Git head pushed: f1505ef9c5f33ba00d0a75f3454ddcefb3e678ba ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T103730Z.json; branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-postpush-20260521T103730Z.json)

## 2026-05-21T11:14:40Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ a1c7c851eaafd8e03682e77bec1ae72e673b9185 (`chore: record post-push ci proof 20260521T1058Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T111440Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T111440Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T111440Z.json)
  - CloudWatch newest stream last event still 2026-05-21T00:01:36.365000Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T111440Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T111440Z-tail.json)
  - output prefix still empty (Total Objects: 0): logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T111440Z.txt (KeyCount=0 in logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T111440Z.json)
- Runner state refreshed (no launch): logs/montana-time-capsule/runner-refresh-20260521T111420Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress)
- CI:
  - exact head: 0 runs for this [skip ci] head (logs/montana-time-capsule/gh-run-list-exact-head-20260521T111440Z.txt)
  - branch list: logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T111440Z.txt

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T11:37:08Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ aade9698c82633f3721384ffc5267c05d056384a ()
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T113416Z.json
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T113416Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T113416Z.json)
  - CloudWatch newest stream last event still 2026-05-21T00:01:36.365000Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T113515Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T113515Z-tail50.json)
  - output prefix still empty (S3UploadMode=EndOfJob): logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T113438Z-tail50.txt
- CI:
  - exact head: 0 runs for this [skip ci] head (logs/montana-time-capsule/gh-run-list-exact-head-20260521T113542Z.json)
  - branch list: logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T113542Z.json

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.


## 2026-05-21T11:37:26Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ aade9698c82633f3721384ffc5267c05d056384a (skip ci)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T113416Z.json
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T113416Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T113416Z.json)
  - CloudWatch newest stream last event still 2026-05-21T00:01:36.365000Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T113515Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T113515Z-tail50.json)
  - output prefix still empty (S3UploadMode=EndOfJob): logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T113438Z-tail50.txt
- CI:
  - exact head: 0 runs for this skip-ci head (logs/montana-time-capsule/gh-run-list-exact-head-20260521T113542Z.json)
  - branch list: logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T113542Z.json

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T11:42:22Z Post-push CI proof (HMC)

- Git head pushed: 0e48d07a38f1576910eb23cc4c36d5c27f6f5a2d
- CDK Deploy: success (run 26223584298)
- Pages: no run for this commit (logs-only change)

## 2026-05-21T12:57:33Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ 1060a1161e173acf3770d38ac6cf049896340e69 (`chore: record post-push ci proof 20260521T1234Z (2) [skip ci]`)
  - status: logs/montana-time-capsule/git-status-20260521T125359Z.txt
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T125359Z.json (acct 975050048887)
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T125359Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T125359Z.json)
  - CloudWatch last event now 2026-05-21T12:39:32Z (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T125359Z.json; best=logs/montana-time-capsule/cloudwatch-best-stream-hmc-mtc-20260520T2015Z-sfm-20260521T125359Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T125359Z-tail50.json; last=logs/montana-time-capsule/cloudwatch-last-event-hmc-mtc-20260520T2015Z-sfm-20260521T125359Z.txt)
  - output prefix still empty (KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T125359Z.json (ls=logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T125359Z-tail50.txt)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T125642Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress)
- CI: exact head is [skip ci] (branch=logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T125359Z.json; exact-head=logs/montana-time-capsule/gh-run-list-exact-head-20260521T125359Z.json)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 20260521T141645Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ fd5693e88186e2161459579ed1d4b73445d491c1 (status=logs/montana-time-capsule/git-status-20260521T141645Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T141425Z.json
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-status-20260521T141425Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T141425Z.json)
  - CloudWatch best stream: logs/montana-time-capsule/cloudwatch-best-stream-hmc-mtc-20260520T2015Z-sfm-20260521T141514Z.txt (streams=logs/montana-time-capsule/cloudwatch-describe-log-streams-hmc-mtc-20260520T2015Z-sfm-20260521T141514Z.json; tail=logs/montana-time-capsule/cloudwatch-get-log-events-hmc-mtc-20260520T2015Z-sfm-20260521T141514Z-tail50.json; last=logs/montana-time-capsule/cloudwatch-last-event-hmc-mtc-20260520T2015Z-sfm-20260521T141514Z.txt -> 2026-05-21T13:56:20Z)
  - output prefix still empty (S3UploadMode=EndOfJob; KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T141546Z.json (ls=logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T141531Z-tail25.txt)
- Runner state refreshed (no launch): logs/montana-time-capsule/hmc-state-refresh-20260521T141614Z.log (state file logs/montana-time-capsule/hmc-state.json; sfm_status=InProgress; updated_at=2026-05-21T14:16:15Z)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T141555Z.json
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T141555Z.json (count=0; [skip ci] expected)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 20260521T141752Z Post-push CI proof (HMC)

- Git head pushed: 9197f0d89b98c376d2f96061ed8f93a51d202b32 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T141752Z.json)

## 20260521T143442Z Monitor tick (HMC)

- Git: agent-40136728-montana-time-capsule @ f4f73fbbb1f43772a5a634f59f374195fd865fed (`chore: record post-push ci proof 20260521T141752Z [skip ci]`)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T143442Z.json
- SageMaker SfM:
  - job: hmc-mtc-20260520T2015Z-sfm
  - status: InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T143442Z.json; list=logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260521T143442Z.json)
  - CloudWatch last event: logs/montana-time-capsule/cloudwatch-last-event-hmc-mtc-20260520T2015Z-sfm-20260521T143442Z.txt (contains linear solver failure line @ ~2026-05-21T14:33:40Z)
  - output prefix still empty (S3UploadMode=EndOfJob; KeyCount=0): logs/montana-time-capsule/s3api-list-objects-spaceport-ml-processing-staging-hmc-mtc-20260520T2015Z-colmap-20260521T143442Z.json (ls=logs/montana-time-capsule/s3-ls-ml-processing-staging-manual-validations-hmc-mtc-20260520T2015Z-colmap-20260521T143442Z-tail50.txt)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T143454Z.json
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T143454Z.json (count=0; [skip ci] expected)

Next: keep polling until SfM becomes Completed and the S3 output prefix is non-empty; do not launch 3DGS yet.

## 2026-05-21T20:17:42Z Monitor tick (HMC) - 3DGS Completed; compression launched

- Repo: /Users/gabrielhansen/worktrees/md1-baseline-montana-time-capsule
- Git: agent-40136728-montana-time-capsule @ c1c71fe7
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T201512Z.json (acct 975050048887)
- SageMaker 3DGS:
  - job: hmc-mtc-20260520T2015Z-3dgs
  - status: Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T201512Z.json)
  - output object present: logs/montana-time-capsule/s3-ls-spaceport-ml-processing-staging-3dgs-hmc-mtc-20260520T2015Z--20260521T201529Z-recursive-head200.txt
- Runner:
  - refreshed: logs/montana-time-capsule/hmc-state-refresh-20260521T201630Z.log (state=logs/montana-time-capsule/hmc-state.json; status=ready_for_compression)
  - launched compression: logs/montana-time-capsule/hmc-launch-compress-20260521T201655Z.log (state status=compression_started)
- SageMaker compression:
  - job: hmc-mtc-20260520T2015Z-compression status=InProgress (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260521T201711Z.json)
  - output prefix still empty (expected while InProgress): logs/montana-time-capsule/s3api-list-objects-v2-spaceport-ml-processing-staging-compressed-hmc-mtc-20260520T2015Z--20260521T201718Z-maxkeys20.json
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T201553Z.json
  - exact-head runs: 0 (expected due to [skip ci]) logs/montana-time-capsule/gh-run-list-exact-head-20260521T201553Z.json

Next: poll `aws sagemaker describe-processing-job --processing-job-name hmc-mtc-20260520T2015Z-compression` until Completed and the compressed S3 prefix is non-empty; then advance to public bundle + viewer gates.

## 2026-05-21T21:15:54Z Monitor tick (HMC) - terminal state reconfirmed (no new launches)

- Repo: /Users/gabrielhansen/worktrees/md1-baseline-montana-time-capsule
- Git: agent-40136728-montana-time-capsule @ ddc172b5d5a36a581b7f392c1b9509a43b0e22f5 (clean)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T211554Z.json (acct 975050048887)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T211554Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T211554Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260521T211554Z.json)
  - no active HMC jobs: logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-inprogress-20260521T211554Z.json + logs/montana-time-capsule/sagemaker-list-training-jobs-hmc-mtc-20260520T2015Z-inprogress-20260521T211554Z.json
- S3:
  - SfM output prefix non-empty: logs/montana-time-capsule/s3-ls-sfm-output-hmc-mtc-20260520T2015Z-20260521T211554Z-head200.txt
  - compressed supersplat bundle present: logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-20260521T211554Z-head200.txt
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260521T211554Z.json
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T211521Z.json ([]; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T211521Z.json

Next: HMC remains at terminal output (compressed bundle + hosted viewer previously validated). No new stage is unblocked without an explicit new acceptance gate (e.g., public promotion / canonical registry entry).

## 2026-05-21T21:17:33Z Post-push CI proof (HMC)

- Git head pushed: 5cfd21b0 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T211733Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260521T211733Z.json)

## 2026-05-21T21:38:40Z Monitor tick (HMC) - terminal state reconfirmed (no new launches)

- Repo: /Users/gabrielhansen/worktrees/md1-baseline-montana-time-capsule
- Git: agent-40136728-montana-time-capsule @ f4088db972fa03bcda71c69704146d1db97a505d (dirty; refreshed state + new poll logs)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T213536Z.json (acct 975050048887)
- Runner:
  - refreshed: logs/montana-time-capsule/hmc-state-refresh-20260521T213818Z.log (state=logs/montana-time-capsule/hmc-state.json; status=completed)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T213536Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T213536Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260521T213536Z.json)
  - no active HMC jobs: logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-inprogress-20260521T213536Z.json + logs/montana-time-capsule/sagemaker-list-training-jobs-hmc-mtc-20260520T2015Z-inprogress-20260521T213536Z.json
- S3:
  - SfM output prefix non-empty: logs/montana-time-capsule/s3-ls-sfm-output-hmc-mtc-20260520T2015Z-20260521T213536Z-head200.txt
  - 3DGS output prefix non-empty: logs/montana-time-capsule/s3-ls-3dgs-output-hmc-mtc-20260520T2015Z-20260521T213536Z-head200.txt
  - compressed supersplat bundle present (recursive listing): logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-20260521T213536Z-recursive-head200.txt
  - supersplat bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-bundle-meta-20260521T213536Z.json
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T213727Z.json ([]; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T213727Z.json

Next: commit/push this tick's evidence logs; no further stage is unblocked without an explicit new acceptance gate (e.g., public promotion / canonical registry entry).

## 2026-05-21T21:40:18Z Post-push CI proof (HMC)

- Git head pushed: a1cd822d ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T214010Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260521T214010Z.json)

## 2026-05-21T22:55:22Z HEARTBEAT monitor (HMC) - terminal reconfirmed + viewer still HTTP 200 (no launches)

- Git: agent-40136728-montana-time-capsule @ a1d987bf434ce4e0758261c8937a1b5f195d8c28 ([skip ci]) (status=logs/montana-time-capsule/git-status-20260521T225522Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T225522Z.json (acct 975050048887)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T225522Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T225522Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260521T225522Z.json)
  - InProgress lists (expect 0): logs/montana-time-capsule/sagemaker-list-processing-inprogress-hmc-mtc-20260520T2015Z-20260521T225522Z.json; logs/montana-time-capsule/sagemaker-list-training-inprogress-hmc-mtc-20260520T2015Z-20260521T225522Z.json
- S3:
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-hmc-mtc-20260520T2015Z-supersplat-meta-20260521T225522Z.json
  - bundle listing (head): logs/montana-time-capsule/s3-ls-hmc-mtc-20260520T2015Z-supersplat_bundle-20260521T225522Z-head200.txt
  - colmap listing (head): logs/montana-time-capsule/s3-ls-hmc-mtc-20260520T2015Z-colmap-20260521T225522Z-head200.txt
  - 3dgs listing (head): logs/montana-time-capsule/s3-ls-hmc-mtc-20260520T2015Z-3dgs-20260521T225522Z-head200.txt
  - public meta.json HTTP 200: logs/montana-time-capsule/curlI-s3-supersplat-meta-20260521T225522Z.headers
- Hosted preview viewer reachability (alias):
  - skybox+no-sky URLs: logs/montana-time-capsule/heartbeat-viewer-urls-20260521T225522Z.txt
  - HTTP 200 headers: logs/montana-time-capsule/curlI-hosted-viewer-skybox-20260521T225522Z.headers; logs/montana-time-capsule/curlI-hosted-viewer-nosky-20260521T225522Z.headers
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260521T225522Z.json
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260521T225522Z.json

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-21T22:57:25Z Post-push CI proof (HMC)

- Git head pushed: 533dc970a2b408c7e938b6ebcb30c8d8c6d85be5 ([skip ci])
- Exact-head workflow runs: 0 (expected due to [skip ci]) (exact-head=logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260521T225724Z.json; branch=logs/montana-time-capsule/gh-run-list-branch-postpush-20260521T225724Z.json)

## 2026-05-21T23:35:37Z HEARTBEAT monitor (HMC) - terminal reconfirmed + viewer still HTTP 200 (no launches)

- Git: agent-40136728-montana-time-capsule @ 5288521fec868bf7788d9ba6234c6302afad2825 ([skip ci]) (status=logs/montana-time-capsule/git-status-20260521T233537Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260521T233537Z.json (acct 975050048887)
- SageMaker:
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-sfm-20260521T233537Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-3dgs-20260521T233537Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-hmc-mtc-20260520T2015Z-compression-20260521T233537Z.json)
- S3:
  - supersplat bundle listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260521T233537Z.txt
- Hosted preview viewer reachability:
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260521T233537Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260521T233537Z.headers; HTTP 200)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260521T233537Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260521T233537Z.headers; HTTP 200)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-agent-40136728-montana-time-capsule-20260521T233537Z.json
  - exact-head run count: logs/montana-time-capsule/gh-exact-head-run-count-20260521T233537Z.txt (0; expected due to [skip ci] head)

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## 2026-05-22T15:36:23Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer/proxy reachable + exact-head CI confirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ 41bcccb2655e5046ca8a2d0acd8366b6cae4c1d0 (dirty=logs only; status=logs/montana-time-capsule/git-status-20260522T144457Z.txt)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T144508Z.json (region=logs/montana-time-capsule/aws-config-region-20260522T144508Z.txt)
- SageMaker (terminal):
  - SfM processing job: hmc-mtc-20260520T2015Z-sfm status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260522T144504Z.json)
  - 3DGS training job: hmc-mtc-20260520T2015Z-3dgs status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260522T144504Z.json)
  - compression processing job: hmc-mtc-20260520T2015Z-compression status=Completed (describe=logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260522T144504Z.json)
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T144501Z.json (0); logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T144501Z.json (0)
- S3 (supersplat bundle):
  - bundle listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T144501Z.txt (13 objects; 7,124,745 bytes)
  - bundle meta head-object: logs/montana-time-capsule/s3api-head-object-supersplat-meta.json-20260522T144503Z.json (ContentLength=1359)
  - skybox head-object: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox.webp-20260522T144503Z.json
- Hosted viewer reachability (HTTP 200):
  - viewer skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T153623Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T153623Z.headers)
  - viewer no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T153623Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T153623Z.headers)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T153623Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T153623Z.headers)
- CI:
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T153554Z.json (0; expected due to [skip ci] head)
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T153554Z.json

Next: remain idle; do not re-launch HMC unless a new explicit acceptance gate is requested.

## Heartbeat 2026-05-22T15:37Z
- git head: e7d1111e81ec4afe5a4c32b04a1da24bdd0eff43 (branch=agent-40136728-montana-time-capsule)
- aws sts: logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T144534Z.json
- sagemaker in-progress processing jobs: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T144534Z.json (count=0)
- sagemaker in-progress training jobs: logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T144534Z.json (count=0)
- canonical jobs: sfm=Completed 3dgs=Completed compression=Completed (see logs/montana-time-capsule/sagemaker-describe-*-20260522T153743Z.json)
- supersplat bundle: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T153642Z.txt (objects=13 bytes=7124745)
- viewer reachability: logs/montana-time-capsule/curlI-viewer-skybox-20260522T153642Z.headers ; logs/montana-time-capsule/curlI-viewer-nosky-20260522T153642Z.headers ; logs/montana-time-capsule/curlI-proxy-meta-20260522T153642Z.headers ; logs/montana-time-capsule/curlI-s3-meta-20260522T153645Z.headers (all HTTP 200)
- gh runs (exact head): logs/montana-time-capsule/gh-run-list-exact-head-20260522T153642Z.json (0; head is [skip ci])
- gh runs (branch): logs/montana-time-capsule/gh-run-list-branch-20260522T153735Z.json (latest non-skip-ci runs include CDK Deploy success)

## 2026-05-22T15:37:53Z HEARTBEAT monitor (HMC) - superseded

This entry referenced non-existent artifact filenames (timestamp mismatch). Use the later heartbeats below (15:38Z and 15:40Z) for correct evidence paths.

- Git:
  - branch: agent-40136728-montana-time-capsule
  - head: e7d1111e81ec4afe5a4c32b04a1da24bdd0eff43
  - status: 7 changed paths (logs/ evidence)
- AWS:
  - sts: logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T153753Z.json
  - region: unknown
  - SageMaker in-progress processing jobs: 0 (logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T153753Z.json)
  - SageMaker in-progress training jobs: 0 (logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T153753Z.json)
  - describe sfm: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260522T153753Z.json
  - describe 3dgs: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260522T153753Z.json
- S3 supersplat bundle (staging):
  - listing: logs/montana-time-capsule/s3-ls-supersplat_bundle-20260522T153753Z.txt
  - head-object meta.json: logs/montana-time-capsule/s3api-head-object-supersplat-meta.json-20260522T153753Z.json
  - head-object background_skybox.webp: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox.webp-20260522T153753Z.json
- Hosted preview viewer reachability (curl -I):
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T153753Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T153753Z.headers; HTTP 200)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T153753Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T153753Z.headers; HTTP 200)
- GitHub Actions:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T153753Z.json (latest green Pages+CDK on 2026-05-21)
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T153753Z.json (0; head commit is [skip ci])

## 2026-05-22T15:40:21Z HEARTBEAT monitor (HMC) - terminal reconfirmed; unrelated SageMaker InProgress observed (no action)

- HMC canonical jobs remain Completed:
  - sfm: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260522T153740Z.json
  - 3dgs: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260522T153940Z.json
  - compression: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260522T153740Z.json
- SageMaker InProgress processing jobs list includes 1 unrelated job:
  - list: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T153940Z.json
  - describe: logs/montana-time-capsule/sagemaker-describe-cvhr-wcrepair-l08-1779464068-20260522T154012Z.json

Next: remain idle for HMC; do not stop unrelated jobs.

## 2026-05-22T15:38:34Z HEARTBEAT monitor (HMC) - fresh reconfirm (no launches)
## 2026-05-22T15:49:00Z HEARTBEAT monitor (HMC) - terminal reconfirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ 2768757a0336acd182d52e718afc2a2cfe3671a5 ([skip ci])
- AWS (us-west-2):
  - sts: logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T153705Z.json
  - SageMaker in-progress processing jobs: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T153656Z.json (expect 0)
  - SageMaker in-progress training jobs: logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T153656Z.json (expect 0)
  - describe sfm: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260522T153740Z.json (Completed)
  - describe 3dgs: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260522T153656Z.json (Completed)
  - describe compression: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260522T153656Z.json (Completed)
- S3 supersplat bundle (staging):
  - head-object meta.json: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260522T153844Z.json
  - head-object background_skybox.webp: logs/montana-time-capsule/s3api-head-object-supersplat-background_skybox.webp-20260522T153735Z.json
  - list-objects (13 keys): logs/montana-time-capsule/s3api-list-objects-supersplat_bundle-20260522T153747Z.json
- Hosted preview viewer reachability (curl -I):
  - skybox: logs/montana-time-capsule/curlI-viewer-skybox-20260522T153834Z.headers (HTTP 200)
  - no-sky: logs/montana-time-capsule/curlI-viewer-nosky-20260522T153834Z.headers (HTTP 200)
  - proxy meta: logs/montana-time-capsule/curlI-proxy-meta-20260522T153834Z.headers (HTTP 200)
- GitHub Actions:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T153834Z.json
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T153834Z.json (0; head commit is [skip ci])

## 2026-05-22T16:00:34Z HEARTBEAT monitor (HMC) - terminal reconfirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ 34687c672db332bf3a09afc231249907942ff355 ([skip ci])
  - status: logs/montana-time-capsule/heartbeat-git-20260522T160034Z.txt (dirty due to new evidence artifacts)
- AWS (us-west-2):
  - sts: logs/montana-time-capsule/aws-sts-get-caller-identity-20260522T160034Z.json
  - SageMaker in-progress processing jobs: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260522T160034Z.json (1 unrelated job; no action)
  - SageMaker in-progress training jobs: logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260522T160034Z.json (0)
  - describe sfm: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260522T160034Z.json (Completed)
  - describe 3dgs: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260522T160034Z.json (Completed)
  - describe compression: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260522T160034Z.json (Completed)
- S3 supersplat bundle (staging):
  - head-object meta.json: logs/montana-time-capsule/s3api-head-object-supersplat-meta-20260522T160034Z.json
  - list-objects: logs/montana-time-capsule/s3api-list-objects-supersplat_bundle-20260522T160034Z.json (13 keys)
- Hosted preview viewer reachability (curl -I):
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260522T160034Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260522T160034Z.headers; HTTP 200)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260522T160034Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260522T160034Z.headers; HTTP 200)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260522T160034Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-20260522T160034Z.headers; HTTP 200)
- GitHub Actions:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260522T160034Z.json (latest green Pages+CDK on 2026-05-21)
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260522T160034Z.json (0; head commit is [skip ci])

Next: remain idle for HMC; do not stop unrelated jobs; no launches.

## 2026-05-23T12:03:12Z HEARTBEAT monitor (HMC) - terminal reconfirmed + S3 + viewer reachable + exact-head CI confirmed (no launches)

- Git: agent-40136728-montana-time-capsule @ c5c4aeff08898985cb349869228538180019ab40 ([skip ci])
- AWS (us-west-2):
  - aws version: logs/montana-time-capsule/aws-version-20260523T120217Z.txt
  - sts: logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T120217Z.json
  - describe sfm (processing): logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T120242Z.json (Completed)
  - describe 3dgs (training): logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T120242Z.json (Completed)
  - describe compression (processing): logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T120242Z.json (Completed)
- S3 supersplat bundle (staging):
  - listing: logs/montana-time-capsule/s3-ls-recursive-supersplat_bundle-20260523T120259Z.txt (objects=13 bytes=7124745)
  - head-object meta.json: logs/montana-time-capsule/s3api-head-meta-json-20260523T120259Z.json (ContentLength=1359; LastModified=2026-05-21T20:25:10Z)
- Hosted preview viewer reachability (curl -I; HTTP 200):
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T120312Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T120312Z.headers)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T120312Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T120312Z.headers)
- GitHub Actions:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T120341Z.json (latest green Pages+CDK on 2026-05-21)
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260523T120341Z.json (0; head commit is [skip ci])
  - exact-head post-push: logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T120540Z.json (0; head commit is [skip ci])

Next: remain idle for HMC; no launches; acceptance gates remaining are visual proof screenshots (skybox + no-sky) beyond HTTP reachability.

## 2026-05-23T12:23:12Z HEARTBEAT monitor (HMC) - no-spend reconfirmed via boto3 + viewer/proxy HTTP 200 + GitHub Actions REST snapshot (no launches)

- Git: agent-40136728-montana-time-capsule @ 6a17a0fd6fe4d8a339c9ce0e236fb7e8aaf7d6a9 ([skip ci]) (clean)
- AWS (boto3; region us-west-2):
  - sts: logs/montana-time-capsule/boto3-sts-get-caller-identity-20260523T122227Z.json
  - SageMaker describes (canonical jobs Completed): logs/montana-time-capsule/boto3-sagemaker-describe-processing-hmc-mtc-20260520T2015Z-20260523T122227Z.json; logs/montana-time-capsule/boto3-sagemaker-describe-training-hmc-mtc-20260520T2015Z-20260523T122227Z.json
  - InProgress lists (no HMC jobs; 2 unrelated processing InProgress): logs/montana-time-capsule/boto3-sagemaker-list-processing-inprogress-20260523T122227Z.json; logs/montana-time-capsule/boto3-sagemaker-list-training-inprogress-20260523T122227Z.json
- S3 supersplat bundle (staging):
  - list-objects: logs/montana-time-capsule/boto3-s3-list-objects-supersplat_bundle-20260523T122300Z.json
  - head meta.json: logs/montana-time-capsule/boto3-s3-head-meta-json-20260523T122300Z.json
  - head background_skybox.webp: logs/montana-time-capsule/boto3-s3-head-background-skybox-webp-20260523T122300Z.json
- Hosted preview viewer reachability (curl -I with Origin header; HTTP 200):
  - skybox URL: logs/montana-time-capsule/heartbeat-skybox-url-20260523T122312Z.txt (headers=logs/montana-time-capsule/curlI-skybox-20260523T122312Z.headers)
  - no-sky URL: logs/montana-time-capsule/heartbeat-nosky-url-20260523T122312Z.txt (headers=logs/montana-time-capsule/curlI-nosky-20260523T122312Z.headers)
  - proxy meta URL: logs/montana-time-capsule/heartbeat-proxy-url-20260523T122312Z.txt (headers=logs/montana-time-capsule/curlI-proxy-20260523T122312Z.headers; includes `access-control-allow-origin: *`)
- GitHub Actions (no `gh`; REST API snapshot):
  - branch runs: logs/montana-time-capsule/github-actions-runs-branch-20260523T122402Z.json (latest Pages success 88b1848f; latest CDK Deploy success 0e48d07a)
  - exact-head runs (expected 0 due to `[skip ci]`): logs/montana-time-capsule/github-actions-runs-exact-head-20260523T122402Z.json

Next: remain idle for HMC; do not launch duplicate jobs. Next acceptance gate (if requested) is visual screenshots in skybox + no-sky modes (not just HTTP reachability).

## 2026-05-23T13:43:54Z HEARTBEAT monitor (HMC) - no-spend reconfirmed (aws+gh via /opt/homebrew/bin PATH) + canonical jobs Completed + bundle present + viewer/proxy HTTP 200 (no launches)

- Git: agent-40136728-montana-time-capsule @ 343fe5a69a2bf3d9a7c1d1c1b0f1878d019d2072 ([skip ci]) (clean)
- AWS CLI (region us-west-2; PATH=/opt/homebrew/bin:$PATH):
  - aws version: logs/montana-time-capsule/aws-version-20260523T134218Z.txt
  - sts: logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T134218Z.json (Account=975050048887)
  - InProgress lists (no HMC jobs): logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260523T134218Z.json; logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260523T134218Z.json
  - describe sfm (processing): logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T134218Z.json (Completed)
  - describe 3dgs (training): logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T134218Z.json (Completed)
  - describe compression (processing): logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T134218Z.json (Completed)
- S3 supersplat bundle (staging):
  - listing: logs/montana-time-capsule/s3-ls-recursive-supersplat_bundle-20260523T134256Z.txt
  - list-objects: logs/montana-time-capsule/s3api-list-objects-supersplat_bundle-20260523T134256Z.json
  - head meta.json: logs/montana-time-capsule/s3api-head-meta-json-20260523T134256Z.json
  - head background_skybox.webp: logs/montana-time-capsule/s3api-head-background_skybox-webp-20260523T134256Z.json
- Hosted preview viewer reachability (curl -I with Origin header; HTTP 200):
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T134315Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T134315Z.headers)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T134315Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T134315Z.headers)
  - proxy meta JSON URL: logs/montana-time-capsule/heartbeat-proxy-meta-json-url-20260523T134315Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-json-20260523T134315Z.headers; includes `access-control-allow-origin: *`)
- GitHub Actions (PATH=/opt/homebrew/bin:$PATH):
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T134340Z.json (latest Pages+CDK successes on 2026-05-21)
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260523T134340Z.json (0; head commit is `[skip ci]`)

Next: remain idle for HMC; do not launch duplicate jobs. Acceptance gate still remaining (if requested) is visual screenshots (skybox + no-sky), beyond HTTP reachability.

## 2026-05-23T13:45:25Z HEARTBEAT monitor (HMC) - ledger push recorded; post-push exact-head CI snapshot captured (no launches)

- Git: agent-40136728-montana-time-capsule @ 67b93f63615cf747d4031eec6d97d74f13f0c27a ([skip ci]) (pushed)
- GitHub Actions:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T134508Z.json
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T134508Z.json (0; head commit is `[skip ci]`)

Next: remain idle for HMC; do not launch duplicate jobs. Next acceptance gate (if requested) remains visual screenshots in skybox + no-sky modes.

## 2026-05-23T14:44:00Z HEARTBEAT monitor (HMC) - no-spend reconfirm (aws+gh) + canonical jobs Completed + bundle present + viewer/proxy HTTP 200 + Playwright screenshots (no launches)

- Git: agent-40136728-montana-time-capsule @ e0b29791f0025c82dc36a58ef505d72d22c576bc ([skip ci]) (clean): logs/montana-time-capsule/heartbeat-git-20260523T144400Z.txt
- AWS CLI (region us-west-2; PATH=/opt/homebrew/bin:$PATH):
  - aws version: logs/montana-time-capsule/aws-version-20260523T144400Z.txt
  - sts: logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T144400Z.json
  - InProgress lists: logs/montana-time-capsule/sagemaker-list-processing-jobs-inprogress-20260523T144400Z.json (1 unrelated job; no action); logs/montana-time-capsule/sagemaker-list-training-jobs-inprogress-20260523T144400Z.json (0)
  - describe sfm (processing): logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T144400Z.json (Completed)
  - describe 3dgs (training): logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T144400Z.json (Completed)
  - describe compression (processing): logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T144400Z.json (Completed)
- S3 supersplat bundle (staging):
  - listing: logs/montana-time-capsule/s3-ls-recursive-supersplat_bundle-20260523T144400Z.txt
  - list-objects (13 keys): logs/montana-time-capsule/s3api-list-objects-supersplat_bundle-20260523T144400Z.json
  - head meta.json: logs/montana-time-capsule/s3api-head-meta-json-20260523T144400Z.json
  - head background_skybox.webp: logs/montana-time-capsule/s3api-head-background-skybox-webp-20260523T144400Z.json
- Hosted preview viewer reachability (curl -I with Origin header; HTTP 200):
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T144400Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T144400Z.headers)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T144400Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T144400Z.headers)
  - proxy meta JSON URL: logs/montana-time-capsule/heartbeat-proxy-meta-json-url-20260523T144400Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-json-20260523T144400Z.headers)
- Playwright visual proof (preview hosted viewer):
  - skybox screenshot: logs/montana-time-capsule/screenshots/viewer-skybox-20260523T144400Z.png (run log: logs/montana-time-capsule/playwright-screenshot-skybox-20260523T144400Z.txt)
  - no-sky screenshot: logs/montana-time-capsule/screenshots/viewer-nosky-20260523T144400Z.png (run log: logs/montana-time-capsule/playwright-screenshot-nosky-20260523T144400Z.txt)
  - mcp ensure log: logs/montana-time-capsule/playwright-mcp-ensure-20260523T144400Z.txt
- GitHub Actions (PATH=/opt/homebrew/bin:$PATH):
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T144400Z.json (latest Pages+CDK successes on 2026-05-21)
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-20260523T144400Z.json (0; head commit is `[skip ci]`)
  - Pages determinism extract: logs/montana-time-capsule/gh-run-view-pages-26200368328-20260523T144400Z.preview-grep.txt (log=logs/montana-time-capsule/gh-run-view-pages-26200368328-20260523T144400Z.log.txt)

Next: remain idle; do not upload/launch duplicate HMC jobs; no action on unrelated in-progress jobs.

### 2026-05-23T14:48:18Z post-push CI snapshot

- Git: agent-40136728-montana-time-capsule @ d97609ad5f191424e52b21be9bbf0f9ca5c5e4da ([skip ci])
- GitHub Actions:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T144818Z.json
  - exact-head runs: logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T144818Z.json (expected 0 due to `[skip ci]`)

## 2026-05-23T15:03:53Z HEARTBEAT monitor (HMC) - no-spend reconfirm (awscli module + gh) + canonical jobs Completed + supersplat bundle present + preview viewer/proxy HTTP 200 + CI snapshot (no launches)

- Git: agent-40136728-montana-time-capsule @ 18d210863765f33a938e1c90b3c2b690817a0ff8 (clean)
  - head: logs/montana-time-capsule/git-head-20260523T150353Z.txt
  - status: logs/montana-time-capsule/git-status-20260523T150353Z.txt
  - status porcelain: logs/montana-time-capsule/git-status-porcelain-20260523T150353Z.txt
- AWS (us-west-2):
  - region: logs/montana-time-capsule/aws-configure-get-region-20260523T150353Z.txt
  - identity: logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T150353Z.json
- SageMaker (canonical jobs expected Completed; InProgress expected 0):
  - SfM processing job: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T150353Z.json (Completed)
  - 3DGS training job: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T150353Z.json (Completed)
  - compression processing job: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T150353Z.json (Completed)
  - InProgress processing list: logs/montana-time-capsule/sagemaker-list-processing-jobs-InProgress-20260523T150353Z.json
  - InProgress training list: logs/montana-time-capsule/sagemaker-list-training-jobs-InProgress-20260523T150353Z.json
- S3 supersplat bundle (staging):
  - listing: logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-20260523T150353Z.txt
  - head meta.json: logs/montana-time-capsule/s3api-head-meta-json-hmc-mtc-20260520T2015Z-20260523T150353Z.json
  - head background_skybox.webp: logs/montana-time-capsule/s3api-head-background-skybox-webp-hmc-mtc-20260520T2015Z-20260523T150353Z.json
- Cloudflare Pages preview:
  - URL: logs/montana-time-capsule/pages-preview-url-20260523T150353Z.txt
  - root headers (Origin set; HTTP 200): logs/montana-time-capsule/curlI-pages-root-20260523T150353Z.headers
- Hosted preview viewer reachability (Origin set; HTTP 200):
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T150353Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T150353Z.headers)
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T150353Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T150353Z.headers)
  - proxy meta.json URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260523T150353Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-json-20260523T150353Z.headers; body=logs/montana-time-capsule/curl-proxy-meta-json-20260523T150353Z.body.json)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T150353Z.json
  - exact-head runs (expected empty if head commit is `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T150353Z.json

Next: remain idle; do not upload/launch duplicate HMC jobs; acceptance gates remain visual proof + public/proxy reachability (currently passing).

### 2026-05-23T15:06:33Z post-push CI snapshot

- Git: agent-40136728-montana-time-capsule @ 4f8572b2fe4d1e4d09bd8aa8f32fe802a5ab763c ([skip ci])
- GitHub Actions:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T150633Z.json
  - exact-head runs (expected 0 due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T150633Z.json

### 2026-05-23T15:25:30Z heartbeat acceptance re-check (no-spend)

- Git: agent-40136728-montana-time-capsule @ 5025bd1975f97292d0aba3d4fcded380c64ef6c8 ([skip ci])
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T152324Z.json (region=logs/montana-time-capsule/aws-configure-get-region-20260523T152324Z.txt; cli=logs/montana-time-capsule/aws-version-20260523T152324Z.txt)
- SageMaker:
  - HMC canonical (expected Completed):
    - processing list (name-contains): logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260523T152324Z.json
    - training list (name-contains): logs/montana-time-capsule/sagemaker-list-training-jobs-hmc-mtc-20260520T2015Z-20260523T152436Z.json
    - 3DGS describe: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T152436Z.json
  - InProgress (do not stop; unrelated):
    - processing list: logs/montana-time-capsule/sagemaker-list-processing-jobs-InProgress-20260523T152530Z.json
    - cvhr-globalprior-full-l00-1779549073 describe: logs/montana-time-capsule/sagemaker-describe-processing-cvhr-globalprior-full-l00-1779549073-20260523T152530Z.json
    - cvhr-globalprior-full-l01-1779549138 describe: logs/montana-time-capsule/sagemaker-describe-processing-cvhr-globalprior-full-l01-1779549138-20260523T152530Z.json
    - training list: logs/montana-time-capsule/sagemaker-list-training-jobs-InProgress-20260523T152530Z.json
- S3 supersplat bundle (HMC staging):
  - listing: logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-20260523T152324Z.txt
  - head meta.json: logs/montana-time-capsule/s3api-head-object-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-meta.json-20260523T152324Z.json
  - meta.json head (first 2000 bytes): logs/montana-time-capsule/s3-cp-meta.json-head2000-20260523T152324Z.txt
- Public/proxy reachability (Origin set; HTTP 200):
  - direct meta.json headers: logs/montana-time-capsule/curlI-bundle-direct-20260523T152530Z.headers
  - proxy meta.json URL: logs/montana-time-capsule/heartbeat-proxy-meta-url-20260523T152530Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-json-20260523T152530Z.headers; body=logs/montana-time-capsule/curl-proxy-meta-json-20260523T152530Z.body.json)
- Hosted preview viewer reachability (Origin set; HTTP 200):
  - pages root headers: logs/montana-time-capsule/curlI-pages-root-20260523T152530Z.headers
  - no-sky URL: logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T152530Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T152530Z.headers)
  - skybox URL: logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T152530Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T152530Z.headers)
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T152405Z.json (most recent Pages/CDK success not at exact-head due to `[skip ci]`)
  - exact-head runs (expected 0 due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T152405Z.json

Next: remain idle; do not launch duplicate HMC jobs; next acceptance gate is visual screenshot proof in browser (skybox + off).

### 2026-05-23T15:27:11Z post-push CI snapshot

- Git: agent-40136728-montana-time-capsule @ bc6db5d1dadb915f68e84a76ce78b111ea2b0994 ([skip ci])
- GitHub Actions:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T152711Z.json
  - exact-head runs (expected 0 due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T152711Z.json

### 2026-05-23T15:45:54Z heartbeat acceptance re-check (no-spend)

- Git: agent-40136728-montana-time-capsule @ 250e9ba535e8ddd11650e0d71823c42e21a0a55e ([skip ci]) (clean)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T154307Z.json (region=logs/montana-time-capsule/aws-configure-get-region-20260523T154307Z.txt; cli=logs/montana-time-capsule/aws-version-20260523T154307Z.txt)
- SageMaker (canonical jobs expected Completed; do not launch duplicates):
  - SfM processing describe: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T154307Z.json
  - 3DGS training describe: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T154307Z.json
  - compression processing describe: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T154307Z.json
  - InProgress processing list (unrelated; recorded only): logs/montana-time-capsule/sagemaker-list-processing-jobs-InProgress-20260523T154307Z.json
  - InProgress training list: logs/montana-time-capsule/sagemaker-list-training-jobs-InProgress-20260523T154307Z.json
- S3 supersplat bundle (HMC staging):
  - object list (13 keys): logs/montana-time-capsule/s3api-list-objects-supersplat_bundle-20260523T154307Z.json
  - head meta.json: logs/montana-time-capsule/s3api-head-meta-json-20260523T154307Z.json
  - head background_skybox.webp: logs/montana-time-capsule/s3api-head-background-skybox-webp-20260523T154307Z.json
- Hosted preview URL (previously resolved from deploy logs; unchanged): logs/montana-time-capsule/preview-url-20260523T154331Z.txt
- Viewer reachability (use `/md1-viewer` + `/api/sogs-proxy`, not `/viewer/*`):
  - md1-viewer HTML (HTTP 200): logs/montana-time-capsule/curlI-md1-viewer-20260523T154554Z.headers (url=logs/montana-time-capsule/viewer-url-20260523T154554Z.txt)
  - sogs-proxy meta.json (HTTP 200): logs/montana-time-capsule/curlI-sogs-proxy-meta-20260523T154554Z.headers (body=logs/montana-time-capsule/curl-sogs-proxy-meta-20260523T154554Z.body.json)
  - sogs-proxy skybox (HTTP 200): logs/montana-time-capsule/curlI-sogs-proxy-skybox-20260523T154554Z.headers
- CI snapshot:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T154331Z.json
  - exact-head runs (expected 0 due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T154331Z.json

Next: remain idle; do not launch duplicate HMC jobs; next acceptance gate is visual screenshot proof in browser (skybox + none) for `/md1-viewer`.

### 2026-05-23T15:47:01Z post-push CI snapshot

- Git: agent-40136728-montana-time-capsule @ b0e307c0e3ed7386bfc010b6e82f8a58e4effd40 ([skip ci]) (clean)
- GitHub Actions:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T154701Z.json
  - exact-head runs (expected 0 due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T154701Z.json

### 2026-05-23T16:05:22Z heartbeat acceptance re-check (no-spend)

- Git: agent-40136728-montana-time-capsule @ c7874b5250f315a22f400b8278e147f8d156262a ([skip ci]) (clean)
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T160246Z.json (region=logs/montana-time-capsule/aws-configure-get-region-20260523T160246Z.txt; cli=logs/montana-time-capsule/aws-version-20260523T160246Z.txt)
- SageMaker (canonical jobs expected Completed; do not launch duplicates):
  - SfM processing describe: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T160305Z.json
  - 3DGS training describe: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T160305Z.json
  - compression processing describe: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T160305Z.json
  - InProgress processing list (unrelated; recorded only): logs/montana-time-capsule/sagemaker-list-processing-jobs-InProgress-20260523T160305Z.json
  - InProgress training list: logs/montana-time-capsule/sagemaker-list-training-jobs-InProgress-20260523T160305Z.json
- S3 supersplat bundle (HMC staging):
  - s3 ls: logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-20260523T160305Z.txt
  - object list (13 keys): logs/montana-time-capsule/s3api-list-objects-supersplat_bundle-20260523T160305Z.json
  - head meta.json: logs/montana-time-capsule/s3api-head-meta-json-hmc-mtc-20260520T2015Z-20260523T160305Z.json
  - head background_skybox.webp: logs/montana-time-capsule/s3api-head-background-skybox-webp-hmc-mtc-20260520T2015Z-20260523T160305Z.json
- Viewer/proxy reachability (Origin/CORS):
  - proxy meta.json URL (HTTP 200): logs/montana-time-capsule/heartbeat-proxy-meta-url-20260523T160522Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-json-20260523T160522Z.headers; body=logs/montana-time-capsule/curl-proxy-meta-json-20260523T160522Z.body.json; includes `access-control-allow-origin: *`)
  - md1-viewer HTML (HTTP 200): logs/montana-time-capsule/curlI-viewer-skybox-20260523T160522Z.headers (skybox=1)
  - md1-viewer HTML (HTTP 200): logs/montana-time-capsule/curlI-viewer-nosky-20260523T160522Z.headers (skybox=0)
  - Note: an invalid proxy path check returned 400 at logs/montana-time-capsule/curlI-proxy-meta-json-20260523T160350Z.headers; use the recorded `heartbeat-proxy-meta-url-*.txt` format for this acceptance gate.
- CI snapshot:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T160350Z.json
  - exact-head runs (expected 0 due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T160350Z.json

Next: remain idle; do not launch duplicate HMC jobs; next acceptance gate remains visual screenshot proof in browser (skybox + none) for `/md1-viewer`.

### 2026-05-23T17:24:45Z heartbeat acceptance re-check (no-spend)

- Git: agent-40136728-montana-time-capsule @ 9f8547160eb3df42f8cf9a628bded725881840b2 ([skip ci]) (pre-ledger commit)
- AWS (us-west-2; aws=/opt/homebrew/bin/aws): logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T172228Z.json (region=logs/montana-time-capsule/aws-configure-get-region-20260523T172228Z.txt; cli=logs/montana-time-capsule/aws-version-20260523T172228Z.txt)
- SageMaker (canonical jobs expected Completed; do not launch duplicates):
  - SfM processing describe: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T172429Z.json
  - 3DGS training describe: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T172429Z.json
  - compression processing describe: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T172429Z.json
  - processing list (name contains run id): logs/montana-time-capsule/sagemaker-list-processing-jobs-hmc-mtc-20260520T2015Z-20260523T172228Z.json (summary=logs/montana-time-capsule/processing-jobs-summary-hmc-mtc-20260520T2015Z-20260523T172228Z.txt)
  - training list (name contains run id): logs/montana-time-capsule/sagemaker-list-training-jobs-hmc-mtc-20260520T2015Z-20260523T172254Z.json
- S3 supersplat bundle (HMC staging):
  - s3 ls: logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-20260523T172228Z.txt
- Viewer/proxy reachability (Origin/CORS; HTTP 200):
  - pages root headers: logs/montana-time-capsule/curlI-pages-root-20260523T172335Z.headers
  - direct meta.json headers: logs/montana-time-capsule/curlI-bundle-direct-20260523T172335Z.headers
  - proxy meta.json URL: logs/montana-time-capsule/heartbeat-proxy-meta-json-url-20260523T172335Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-json-20260523T172335Z.headers; body=logs/montana-time-capsule/curl-proxy-meta-json-20260523T172335Z.body.json; json=logs/montana-time-capsule/jq-validate-proxy-meta-json-20260523T172335Z.txt)
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T172335Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T172335Z.headers)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T172335Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T172335Z.headers)
- CI snapshot:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T172352Z.json
  - exact-head runs (expected 0 due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T172352Z.json

Next: remain idle; do not launch duplicate HMC jobs; next acceptance gate remains visual screenshot proof in browser (skybox + off).

### 2026-05-23T17:25:47Z post-push CI snapshot

- Git: agent-40136728-montana-time-capsule @ 895792f3c7be48c1aa7a8ccf37ab5b1694f2a19e ([skip ci]) (clean)
- GitHub Actions:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T172543Z.json
  - exact-head runs (expected 0 due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T172543Z.json

### 2026-05-23T17:26:20Z post-push CI snapshot

- Git: agent-40136728-montana-time-capsule @ a02800d6caea4598ccf87b0bfde800b61d937c80 ([skip ci]) (clean)
- GitHub Actions:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T172616Z.json
  - exact-head runs (expected 0 due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T172616Z.json

### 2026-05-23T16:06:56Z post-push CI snapshot

- Git: agent-40136728-montana-time-capsule @ 5b27297ad997e854093ce920516b9cad7f1673a8 ([skip ci]) (clean)
- GitHub Actions:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T160656Z.json
  - exact-head runs (expected 0 due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T160656Z.json

### 2026-05-23T16:31:12Z heartbeat acceptance re-check (no-spend)

- Git: agent-40136728-montana-time-capsule @ 8b122ddec05f34454afa899dd7f87d11ef57b35a ([skip ci]) (clean)
- GitHub Actions:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T162828Z.json
  - exact-head runs (expected 0 due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-20260523T162828Z.json
  - Pages runs: logs/montana-time-capsule/gh-run-list-pages-20260523T162828Z.json
  - CDK runs: logs/montana-time-capsule/gh-run-list-cdk-20260523T162828Z.json
- Cloudflare Pages preview (re-derived from deploy run 26200368328):
  - extract: logs/montana-time-capsule/gh-run-view-pages-26200368328-20260523T162837Z.preview-grep.txt
  - alias URL: https://agent-40136728-montana-time.v0-spaceport-website-preview2.pages.dev
- AWS (us-west-2): logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T162931Z.json
- SageMaker (canonical jobs Completed; do not launch duplicates):
  - SfM processing describe: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T162931Z.json
  - 3DGS training describe: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T162931Z.json
  - compression processing describe: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T162931Z.json
  - InProgress processing list (unrelated; recorded only): logs/montana-time-capsule/sagemaker-list-processing-jobs-InProgress-20260523T162931Z.json (contains `cvhr-globalprior-full-l01-1779549138`)
  - InProgress training list: logs/montana-time-capsule/sagemaker-list-training-jobs-InProgress-20260523T162931Z.json
- S3 supersplat bundle (HMC staging):
  - s3 ls: logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-20260523T163020Z.txt
  - head meta.json: logs/montana-time-capsule/s3api-head-meta-json-hmc-mtc-20260520T2015Z-20260523T163020Z.json
  - head background_skybox.webp: logs/montana-time-capsule/s3api-head-background-skybox-webp-hmc-mtc-20260520T2015Z-20260523T163020Z.json
- Viewer/proxy reachability (Origin/CORS; HTTP 200):
  - viewer URL (skybox): logs/montana-time-capsule/heartbeat-viewer-skybox-url-20260523T163040Z.txt (headers=logs/montana-time-capsule/curlI-viewer-skybox-20260523T163040Z.headers)
  - viewer URL (no-sky): logs/montana-time-capsule/heartbeat-viewer-nosky-url-20260523T163040Z.txt (headers=logs/montana-time-capsule/curlI-viewer-nosky-20260523T163040Z.headers)
  - proxy meta.json URL: logs/montana-time-capsule/heartbeat-proxy-meta-json-url-20260523T163040Z.txt (headers=logs/montana-time-capsule/curlI-proxy-meta-json-20260523T163040Z.headers; body=logs/montana-time-capsule/curl-proxy-meta-json-20260523T163040Z.body.json; jq=logs/montana-time-capsule/jq-validate-proxy-meta-json-20260523T163040Z.txt)

## 2026-05-23T17:44:42Z HEARTBEAT monitor (HMC) - no-spend reconfirm (awscli) + terminal canonical jobs + S3 supersplat bundle present + hosted preview viewer HTTP 200 + sogs-proxy meta/skybox HTTP 200 + CI snapshot

- Git:
  - status: logs/montana-time-capsule/git-status-20260523T174229Z.txt
- AWS (us-west-2):
  - identity: logs/montana-time-capsule/aws-sts-get-caller-identity-20260523T174229Z.json
  - region: logs/montana-time-capsule/aws-configure-get-region-20260523T174229Z.txt
  - version: logs/montana-time-capsule/aws-version-20260523T174229Z.txt
- SageMaker (canonical jobs; expected Completed; no new HMC launches):
  - SfM processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-sfm-20260523T174229Z.json
  - 3DGS training job Completed: logs/montana-time-capsule/sagemaker-describe-training-hmc-mtc-20260520T2015Z-3dgs-20260523T174229Z.json
  - compression processing job Completed: logs/montana-time-capsule/sagemaker-describe-processing-hmc-mtc-20260520T2015Z-compression-20260523T174229Z.json
  - InProgress processing list (do not stop non-HMC): logs/montana-time-capsule/sagemaker-list-processing-jobs-InProgress-20260523T174229Z.json
  - InProgress training list: logs/montana-time-capsule/sagemaker-list-training-jobs-InProgress-20260523T174229Z.json
- S3 (supersplat bundle present):
  - bundle listing: logs/montana-time-capsule/s3-ls-compressed-hmc-mtc-20260520T2015Z-supersplat_bundle-20260523T174229Z.txt
  - meta head: logs/montana-time-capsule/s3api-head-meta-json-hmc-mtc-20260520T2015Z-20260523T174229Z.json
  - skybox head note: logs/montana-time-capsule/s3api-head-background-skybox-webp-hmc-mtc-20260520T2015Z-20260523T174229Z.json (404 from head-object call; object still present per S3 listing above; viewer access validated via sogs-proxy below)
- Cloudflare Pages preview:
  - URL: logs/montana-time-capsule/pages-preview-url-20260523T174229Z.txt
  - root headers (Origin set; HTTP 200): logs/montana-time-capsule/curlI-pages-root-20260523T174229Z.headers
- Hosted preview viewer reachability (Origin set; HTTP 200):
  - skybox headers: logs/montana-time-capsule/curlI-viewer-skybox-20260523T174229Z.headers
  - no-sky headers: logs/montana-time-capsule/curlI-viewer-nosky-20260523T174229Z.headers
- Public bundle reachability gate (signed/proxied through viewer; expected 200):
  - NOTE: `/api/proxy/...` was a wrong path (returned HTML/404): logs/montana-time-capsule/curlI-proxy-meta-json-20260523T174229Z.headers (body=logs/montana-time-capsule/curl-proxy-meta-json-20260523T174229Z.body.json)
  - sogs-proxy meta.json (HTTP 200): logs/montana-time-capsule/curlI-sogs-proxy-meta-20260523T174442Z.headers (body=logs/montana-time-capsule/curl-sogs-proxy-meta-20260523T174442Z.body.json; validate=logs/montana-time-capsule/validate-sogs-proxy-meta-20260523T174442Z.txt)
  - sogs-proxy skybox (HTTP 200): logs/montana-time-capsule/curlI-sogs-proxy-skybox-20260523T174442Z.headers
  - URLs:
    - sogs-proxy meta URL: logs/montana-time-capsule/heartbeat-sogs-proxy-meta-url-20260523T174442Z.txt
    - sogs-proxy skybox URL: logs/montana-time-capsule/heartbeat-sogs-proxy-skybox-url-20260523T174442Z.txt
- CI:
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-20260523T174442Z.json
  - exact-head runs (may be empty due to `[skip ci]` on HEAD): logs/montana-time-capsule/gh-run-list-exact-head-20260523T174442Z.json

## 2026-05-23T17:46:03Z postpush CI snapshot (exact-head expected empty due to )

- Git: agent-40136728-montana-time-capsule @ bf95fe61ca381c091c95b2aedc94428c86140dcf ([skip ci])
- CI:
  - git head: logs/montana-time-capsule/git-head-20260523T174603Z.txt
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T174603Z.json
  - exact-head runs (expected empty due to ): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T174603Z.json

## 2026-05-23T17:45:52Z postpush CI snapshot (exact-head expected empty due to `[skip ci]`)

- Git: agent-40136728-montana-time-capsule @ bf95fe61bdff0d5348945dfebdc127d3b82b105f ([skip ci])
- CI:
  - git head: logs/montana-time-capsule/git-head-20260523T174552Z.txt
  - branch runs: logs/montana-time-capsule/gh-run-list-branch-postpush-20260523T174552Z.json
  - exact-head runs (expected empty due to `[skip ci]`): logs/montana-time-capsule/gh-run-list-exact-head-postpush-20260523T174552Z.json
