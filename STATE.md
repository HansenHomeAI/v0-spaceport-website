reason: building the mature-branch distributed SfM production spine from origin/agent-31459027-sfm-final-bridge-fallback without mutating the mature branch; sfm-reality-check heartbeat stays active until full verified end-goal proof or explicit owner stop.
last_step: R4 exact retry r4exact739x2-1777587765 stayed InProgress after the runtime had already logged the merge failure and uploaded failure metadata without sparse/0, so a stop was requested at 2026-05-01T05:01:20Z to avoid burning the ml.g4dn.xlarge; SageMaker status is Stopping with no FailureReason yet.
next_unblocked_step: wait for r4exact739x2-1777587765 terminal Stopped/Failed status, then launch the next R4 exact retry with seam-only parent merge enabled instead of the legacy rerun override so bridge/seam recovery can preserve merge overlap; do not run R5 until R4 exact is green and recorded.
owner_action_needed: none
active_jobs:
  - r4exact739x2-1777587765 -> runtime failed at merge: chunk_07 completed 320/320 with 255192 points and balanced merge reached 1828 images/1356837 points, but final merge could not connect chunk_00_mapper_initial with chunk_model_merger_05_output_attempt_01; S3 has sfm_metadata, leaf_metadata, reducer_metadata, planner_static_report, and chunk_planner_manifest but no sparse/0; stop requested after stale InProgress control-plane state; current SageMaker status Stopping/no FailureReason; output s3://spaceport-ml-processing-staging/manual-validations/r4exact739x2-1777587765/colmap
  - r4exact739t-1777588010 -> duplicate full exact retry submitted after handoff confusion; terminal Stopped at 2026-04-30T22:29:24.397Z; not canonical
  - r4c0t739-1777579549 -> Completed; output s3://spaceport-ml-processing-staging/manual-validations/r4c0t739-1777579549/colmap has sparse/0, sfm_metadata, leaf_metadata, reducer_metadata; 320/320 registered, 238876 raw points, 746.49 pts/image, standard_sparse0_exists=true, promotion_blockers=[]
  - r4c0retry739-1777579567 -> duplicate retry, Stopped at 2026-04-30T20:08:44.193Z; do not monitor as canonical
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
  - logs/sfm-production-spine/r4_exact_2157_timeout_retry_submit.json
  - logs/sfm-production-spine/r4exact739x2-1777587765-sfm_metadata.json
  - logs/sfm-production-spine/r4exact739x2-1777587765-leaf_metadata.json
  - logs/sfm-production-spine/r4exact739x2-1777587765-reducer_metadata.json
  - logs/sfm-production-spine/r4exact739x2-1777587765-planner_static_report.json
  - logs/sfm-production-spine/r4exact739x2-1777587765-chunk_planner_manifest.json
  - s3://spaceport-ml-processing-staging/manual-validations/r4c0t739-1777579549/colmap
  - s3://spaceport-ml-processing-staging/manual-validations/r4c0t739-1777579549/colmap/sparse/0/
  - logs/sfm-production-spine/r4c0t739-1777579549-sfm_metadata.json
  - logs/sfm-production-spine/r4c0t739-1777579549-leaf_metadata.json
  - logs/sfm-production-spine/r4c0t739-1777579549-reducer_metadata.json
  - logs/sfm-production-spine/r4c0t739-1777579549-planner_static_report.json
  - s3://spaceport-ml-processing-staging/manual-validations/r4exact739x2-1777587765/colmap
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
head: f7a5c017ad79bfa2fd008cc8ff9f10271dec0492
updated: 2026-05-01T05:01:20Z
