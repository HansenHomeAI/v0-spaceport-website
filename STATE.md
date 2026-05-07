reason: project-level continuation after stable MD1 SfM artifact proof; automation remains active because the owner has not confirmed the final project is done and project-level caveats remain.
last_step: 2026-05-07T16:41Z two-leaf canary reached terminal state. Chunk 2 job md1-fanout-20260507T1429Z-c02-1778167770 completed with 167/167 registered and sparse/0 present. Chunk 1 job md1-fanout-20260507T1429Z-c01-1778167770 failed because matches_importer imported 0 verified pairs and mapper had no images with matches. Root cause found: the immutable planner-manifest path loaded selected chunk plans but did not rebuild view geometries/candidate graph before writing the footprint pair list. I fixed that locally and unit verification passed.
next_unblocked_step: Commit/push the candidate-graph fix, wait for sfm container build from the new head, then relaunch only the failed chunk-1 canary retry from logs/sfm-production-spine/md1_fanout_canary_retry_plan_20260507T1641Z.json.
owner_action_needed: none
active_jobs: []
branch: agent-73948216-sfm-production-spine
head: 2d1649cbc70d29804e9e1d22893ac746e2c84381
updated: 2026-05-07T16:41:45Z
project_status: not_final_project_closed
md1_artifact_status: stable_promotable_md1_sfm_artifact
md1_result:
  decision: promote_md1_sfm_artifact_not_close_entire_project
  job: r4exact739s1-1777612249
  input_uri: s3://spaceport-uploads/1775750905123-vg76vr-md1-dji-images.zip
  output_uri: s3://spaceport-ml-processing-staging/manual-validations/r4exact739s1-1777612249/colmap
  sparse0_uri: s3://spaceport-ml-processing-staging/manual-validations/r4exact739s1-1777612249/colmap/sparse/0/
  registered: 2157
  total: 2157
  raw_points: 1708813
  filtered_points: 1222473
  runtime_sec: 26614.34
  mature_baseline_runtime_sec: 36033.85
  speedup_percent: 26.14
  mature_baseline_job: md1p24e752k-1776314974
project_level_caveats:
  - true multi-instance SageMaker leaf fanout canary partially failed: chunk 2 succeeded, chunk 1 needs retry after candidate-graph fix
  - reducer-from-independent-leaf-prefixes has not been proven because both canary leaves are not successful yet
  - filtered point count is 6.88% below the mature baseline even though raw points and registration pass
  - downstream 3DGS/splat training quality is not proven by the SfM sparse/0 proof packet
latest_artifacts:
  - logs/sfm-production-spine/md1_fanout_canary_failure_analysis_20260507T1641Z.json
  - logs/sfm-production-spine/md1_fanout_canary_retry_plan_20260507T1641Z.json
  - logs/sfm-production-spine/fanout-runtime-support-tests-20260507T1639Z.log
  - logs/sfm-production-spine/md1-fanout-c01-cloudwatch-tail-20260507T1639Z.json
  - logs/sfm-production-spine/md1-fanout-c02-cloudwatch-tail-20260507T1639Z.json
  - logs/sfm-production-spine/leaf-01-sfm_metadata-20260507T1639Z.json
  - logs/sfm-production-spine/leaf-02-sfm_metadata-20260507T1639Z.json
  - logs/sfm-production-spine/fanout_canary_progress_20260507T1531Z.json
  - logs/sfm-production-spine/md1_fanout_canary_submit_20260507T1517Z.json
  - logs/sfm-production-spine/md1-fanout-20260507T1429Z-c01-1778167770-sagemaker-describe-submit.json
  - logs/sfm-production-spine/md1-fanout-20260507T1429Z-c02-1778167770-sagemaker-describe-submit.json
  - logs/sfm-production-spine/codebuild-be6a6ead-poll6.json
  - logs/sfm-production-spine/github-runs-2d1649cb-poll6.json
  - logs/sfm-production-spine/project_level_gap_assessment_20260507T1351Z.json
  - logs/sfm-production-spine/project_level_gap_assessment_20260507T1351Z.md
  - logs/sfm-production-spine/md1_fanout_contract_20260507T1351Z.json
  - logs/sfm-production-spine/fanout_runtime_support_20260507T1429Z.json
  - logs/sfm-production-spine/md1_fanout_contract_20260507T1429Z.json
  - logs/sfm-production-spine/md1_two_leaf_canary_plan_20260507T1429Z.json
  - logs/sfm-production-spine/fanout-runtime-support-tests-20260507T1429Z.log
  - infrastructure/containers/sfm/run_colmap_sfm.py
  - scripts/sfm/build_sfm_fanout_contract.py
  - tests/unit/test_sfm_fanout_contract.py
  - tests/unit/test_colmap_gps_priors.py
  - logs/sfm-production-spine/active-processing-jobs-20260507T1429Z.json
  - logs/sfm-production-spine/r4exact739s1-1777612249-sagemaker-describe-20260507T1429Z.json
  - logs/sfm-production-spine/r4exact739s1-1777612249-sparse0-list-20260507T1429Z.txt
  - logs/sfm-production-spine/r4exact739s1-1777612249-pipeline-viewer-api-20260507T1429Z.json
  - logs/sfm-production-spine/active-processing-jobs-20260507T1351Z.json
  - logs/sfm-production-spine/r4exact739s1-1777612249-sagemaker-describe-20260507T1351Z.json
  - logs/sfm-production-spine/r4exact739s1-1777612249-sparse0-list-20260507T1351Z.txt
  - logs/sfm-production-spine/r4exact739s1-1777612249-pipeline-viewer-api-20260507T1351Z.json
  - logs/sfm-production-spine/final_promotion_packet.json
  - logs/sfm-production-spine/md1_speed_proof_audit.json
  - logs/sfm-production-spine/comparison_report.json
  - s3://spaceport-ml-processing-staging/manual-validations/r4exact739s1-1777612249/colmap/sparse/0/
