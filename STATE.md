reason: building the mature-branch distributed SfM production spine from origin/agent-31459027-sfm-final-bridge-fallback without mutating the mature branch.
last_step: R4 exact 2157-image proof launched as SageMaker job r4exact739-1777570477 using full input s3://spaceport-uploads/1775750905123-vg76vr-md1-dji-images.zip plus mature ladder_2000 manifest subset s3://spaceport-ml-processing-staging/manual-validations/md1p2dd70full-1776233149/colmap/chunk_planner_manifest.json. Compute image tag agent73948216sfmproductionspine resolves to sha256:9714d61c9219166a626462e84857ca6a326b1e21fa4ce9c80d2f433dd47352b3 and SFM_GIT_HEAD is pinned to 9f7bd89637c60f930eca1c14f1de340a14edfdf9. SageMaker status is InProgress; ProcessingStartTime is 2026-04-30T17:35:24.315Z; no FailureReason and no EndOfJob S3 output yet.
next_unblocked_step: monitor R4 job r4exact739-1777570477 through planner, leaf chunks, bridge/merge, S3 upload, metadata parsing, sparse/0 proof, and pipeline-viewer proof.
owner_action_needed: none
active_jobs:
  - r4exact739-1777570477 -> InProgress, ProcessingStartTime 2026-04-30T17:35:24.315Z, no FailureReason, no EndOfJob S3 output yet; input s3://spaceport-uploads/1775750905123-vg76vr-md1-dji-images.zip; subset ladder_2000 from s3://spaceport-ml-processing-staging/manual-validations/md1p2dd70full-1776233149/colmap/chunk_planner_manifest.json; output s3://spaceport-ml-processing-staging/manual-validations/r4exact739-1777570477/colmap
latest_artifacts:
  - logs/sfm-production-spine/port_inventory.md
  - logs/sfm-production-spine/frontier.json
  - logs/sfm-production-spine/comparison_report.json
  - logs/sfm-production-spine/r0_planner_fixture/output/planner_static_report.json
  - logs/sfm-production-spine/r1-geometry_mix-sfm_metadata.json
  - logs/sfm-production-spine/r1-horizon_context-sfm_metadata.json
  - logs/sfm-production-spine/r1-cross_pass-failed-sfm_metadata.json
  - logs/sfm-production-spine/r1-cross_pass-rerun1-sfm_metadata.json
  - logs/sfm-production-spine/r1cross739x2-1777513705-sfm_metadata.json
  - s3://spaceport-ml-processing-staging/manual-validations/r1cross739x2-1777513705/colmap/sparse/0/
  - s3://spaceport-ml-processing-staging/manual-validations/r2leaf739c0-1777517712/colmap
  - s3://spaceport-ml-processing-staging/manual-validations/r2leaf739c1-1777517712/colmap
  - logs/sfm-production-spine/r2leaf739c1-1777517712-sfm_metadata.json
  - logs/sfm-production-spine/r2leaf739c1-1777517712-leaf_metadata.json
  - logs/sfm-production-spine/r2leaf739c1-1777517712-reducer_metadata.json
  - logs/sfm-production-spine/r2leaf739c1-1777517712-planner_static_report.json
  - s3://spaceport-ml-processing-staging/manual-validations/r2leaf739c1-1777517712/colmap/sparse/0/
  - logs/sfm-production-spine/r2leaf739c0-1777517712-sfm_metadata.json
  - logs/sfm-production-spine/r2leaf739c0-1777517712-leaf_metadata.json
  - logs/sfm-production-spine/r2leaf739c0-1777517712-reducer_metadata.json
  - logs/sfm-production-spine/r2leaf739c0-1777517712-planner_static_report.json
  - logs/sfm-production-spine/r2_leaf_fanout_summary.json
  - s3://spaceport-ml-processing-staging/manual-validations/r2leaf739c0-1777517712/colmap/sparse/0/
  - logs/sfm-production-spine/r3_ladder_1000_submit.json
  - logs/sfm-production-spine/r4_exact_2157_submit.json
  - logs/sfm-production-spine/r3_ladder_1000_summary.json
  - logs/sfm-production-spine/r3lad1000a739-1777554908-sfm_metadata.json
  - logs/sfm-production-spine/r3lad1000a739-1777554908-leaf_metadata.json
  - logs/sfm-production-spine/r3lad1000a739-1777554908-reducer_metadata.json
  - logs/sfm-production-spine/r3lad1000a739-1777554908-planner_static_report.json
  - logs/sfm-production-spine/r3lad1000a739-1777554908-chunk_planner_manifest.json
  - logs/sfm-production-spine/pipeline-viewer-r3-dom-snapshot.md
  - logs/sfm-production-spine/pipeline-viewer-r3-desktop.png
  - logs/sfm-production-spine/pipeline-viewer-preview-r3-desktop.png
  - logs/sfm-production-spine/pipeline-viewer-preview-r3-canvas.png
  - s3://spaceport-ml-processing-staging/manual-validations/r3lad1000a739-1777554852/colmap/sparse/0/
  - logs/sfm-production-spine/pipeline-viewer-r1-desktop.png
  - logs/sfm-production-spine/pipeline-viewer-r1-mobile.png
  - logs/sfm-production-spine/pipeline-viewer-preview-r1-desktop.png
  - s3://spaceport-ml-processing-staging/manual-validations/r3lad1000a739-1777554852/colmap
  - https://agent-73948216-sfm-productio.v0-spaceport-website-preview2.pages.dev
  - https://9b941756.v0-spaceport-website-preview2.pages.dev
branch: agent-73948216-sfm-production-spine
head: d991bbf5234eaf40d6f6d965ee4ffe28b03f5957
updated: 2026-04-30T17:41:27Z
