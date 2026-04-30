reason: building the mature-branch distributed SfM production spine from origin/agent-31459027-sfm-final-bridge-fallback without mutating the mature branch.
last_step: R4 first exact attempt r4exact739-1777570477 reached terminal SageMaker Failed with AlgorithmError exit code 1 after the chunk_00 timeout; bounded R4 chunk_00 retry r4c0t739-1777579549 was submitted with COLMAP_CHUNK_MAPPER_TIMEOUT_SECONDS=7200 and COLMAP_BRIDGE_MAPPER_TIMEOUT_SECONDS=7200.
next_unblocked_step: monitor r4c0t739-1777579549 startup, logs, chunk_00 mapper progress, leaf metadata, sparse/0, and whether the raised timeout clears the 171/320 frame failure.
owner_action_needed: none
active_jobs:
  - r4c0t739-1777579549 -> InProgress startup pending ProcessingStartTime; targeted chunk_00 retry for exact ladder_2000 using same input/manifest, --only-chunk-indexes 0, COLMAP_CHUNK_MAPPER_TIMEOUT_SECONDS=7200, COLMAP_BRIDGE_MAPPER_TIMEOUT_SECONDS=7200; output s3://spaceport-ml-processing-staging/manual-validations/r4c0t739-1777579549/colmap
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
  - logs/sfm-production-spine/r4exact739-1777570477-sfm_metadata.json
  - logs/sfm-production-spine/r4exact739-1777570477-planner_static_report.json
  - logs/sfm-production-spine/r4exact739-1777570477-reducer_metadata.json
  - logs/sfm-production-spine/r4exact739-1777570477-chunk_planner_manifest.json
  - logs/sfm-production-spine/r4_chunk0_timeout_retry_submit.json
  - s3://spaceport-ml-processing-staging/manual-validations/r4c0t739-1777579549/colmap
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
head: 1c3dcbdb5f1ec5705e31ec12dadf0c3ce09bf39e
updated: 2026-04-30T20:05:49Z
