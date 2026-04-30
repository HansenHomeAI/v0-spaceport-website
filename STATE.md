reason: building the mature-branch distributed SfM production spine from origin/agent-31459027-sfm-final-bridge-fallback without mutating the mature branch.
last_step: Launched R3 1000-image ladder job r3lad1000a739-1777554908 on distributed_chunked_v1 from the recovered ladder_1000.zip input.
next_unblocked_step: monitor R3 job r3lad1000a739-1777554908 to completion, fetch metadata/sparse proof, then gate R3 before any R4 launch.
owner_action_needed: none
active_jobs:
  - r3lad1000a739-1777554908 -> InProgress, R3 1000-image ladder, s3://spaceport-ml-processing-staging/manual-validations/r3lad1000a739-1777554852/colmap
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
  - s3://spaceport-ml-processing-staging/manual-validations/r3lad1000a739-1777554852/colmap
  - https://agent-73948216-sfm-productio.v0-spaceport-website-preview2.pages.dev
branch: agent-73948216-sfm-production-spine
head: 9f7bd89637c60f930eca1c14f1de340a14edfdf9
updated: 2026-04-30T13:15:32Z
