reason: project-level continuation toward production-ready huge-scene tiled SfM; automation is active and must remain active until final proof has no unresolved caveats or owner explicitly stops it.
last_step: 2026-05-12T18:38Z implemented schema-first heldout render metrics and AI visual review gate ingestion; added deterministic source/render pair evaluator with PSNR/SSIM/proof-panel output and LPIPS-required blocking semantics; re-ran quality gate on the two-leaf reducer proof and it correctly remains needs_more_proof until real splat render pairs exist.
next_unblocked_step: Wire the active NerfStudio/3DGS path to preserve or regenerate deterministic heldout renders, emit splat_heldout_render_metrics with PSNR/SSIM/LPIPS plus proof panels, run AI visual review on those panels, then execute this cheaply on the two-leaf reducer artifact before any full 8-leaf MD1 rerun.
owner_action_needed: none
active_jobs: []
branch: agent-73948216-sfm-production-spine
head: 677f55090f4ec8b76c3622f8fd1371a8610d809f
updated: 2026-05-12T18:38:48Z
project_status: not_final_project_closed
automation:
  id: sfm-reality-check
  status: ACTIVE
  cadence: FREQ=MINUTELY;INTERVAL=30
md1_artifact_status: stable_same_md1_sfm_artifact_needs_downstream_visual_splat_quality_proof
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
quality_report:
  artifact: logs/sfm-production-spine/r4exact739s1-1777612249-sfm_quality_report.json
  decision: needs_more_proof
  passed:
    - registration_coverage
    - point_count
    - reducer_blockers
    - single_component
    - merge_retention
    - reprojection_error_sample
    - viewer_axis_sanity
  warnings:
    - seam_overlap: one merge node has only 4 shared registered images
  not_run:
    - heldout_render_metrics
    - ai_visual_review
fanout_canary:
  leaf_01_retry:
    job: md1-fanout-20260507T1639Z-c01r2-1778173164
    status: Completed
    output_uri: s3://spaceport-ml-processing-staging/manual-validations/md1-fanout-canary-20260507T1639Z/leaves/leaf-01-r2/colmap
    registered: 320
    total: 320
    points: 235216
    runtime_sec: 2494.31
    verified_pairs: 2491
  leaf_02:
    job: md1-fanout-20260507T1429Z-c02-1778167770
    status: Completed
    output_uri: s3://spaceport-ml-processing-staging/manual-validations/md1-fanout-canary-20260507T1429Z/leaves/leaf-02/colmap
    registered: 167
    total: 167
    points: 126462
    runtime_sec: 1170.86
    verified_pairs: 2196
reducer_canary:
  decision: pass
  strategy: pose_aligned_text_merge_after_stock_colmap_model_merger_failed_on_independent_keypoints
  stock_model_merger_returncode: -6
  local_report: logs/sfm-production-spine/md1_two_leaf_reducer_canary_20260512.json
  quality_report: logs/sfm-production-spine/md1_two_leaf_reducer_canary_quality_20260512.json
  viewer_api_summary: logs/sfm-production-spine/md1_two_leaf_reducer_canary_viewer_api_summary_20260512.json
  viewer_screenshot: logs/sfm-production-spine/md1-two-leaf-reducer-canary-viewer-20260512.png
  s3_uri: s3://spaceport-ml-processing-staging/manual-validations/md1-fanout-canary-20260512/merged-pose-aligned/colmap
  registered: 447
  exact_points: 336701
  sampled_points_viewer: 80000
  shared_registered_images: 40
  alignment_error_p95_m: 0.0139
  leaf_retention_ratios:
    - 1.0
    - 1.0
production_fanout_reducer_proof:
  decision: pass
  code_head: e6e7fccfa0eac5ee3b396772bfa3ef049b423559
  report: logs/sfm-production-spine/md1_fanout_reducer_proof_20260512T1803Z.json
  quality_report: logs/sfm-production-spine/md1_fanout_reducer_proof_quality_20260512T1803Z.json
  output_uri: s3://spaceport-ml-processing-staging/manual-validations/md1-fanout-reducer-proof-20260512T1803Z/merged/colmap
  registered: 447
  exact_points: 336701
  leaf_retention_ratios:
    - 1.0
    - 1.0
  promotion_blockers: []
  viewer_api_summary: logs/sfm-production-spine/md1_fanout_reducer_proof_viewer_api_summary_20260512T1803Z.json
  browser_render_proof: logs/sfm-production-spine/md1_fanout_reducer_proof_playwright_20260512T1803Z.json
  viewer_screenshot: logs/sfm-production-spine/md1-fanout-reducer-proof-viewer-20260512T1803Z.png
visual_quality_gate_contract:
  status: implemented_not_run_on_real_splat
  heldout_pair_evaluator: scripts/sfm/evaluate_visual_quality.py
  integrated_quality_gate: scripts/sfm/evaluate_sfm_quality.py
  tests:
    - tests/unit/test_sfm_visual_quality.py
    - tests/unit/test_sfm_quality_eval.py
  latest_quality_report: logs/sfm-production-spine/md1_fanout_reducer_proof_quality_20260512T1803Z.json
  expected_render_report_kind: splat_heldout_render_metrics
  expected_ai_report_kind: ai_visual_review_report
  current_decision_without_render_pairs: needs_more_proof
project_level_caveats:
  - full 8-leaf multi-instance MD1 fanout plus reducer has not been run on the production reducer path
  - active NerfStudio/3DGS path does not yet emit deterministic heldout render pairs with PSNR/SSIM/LPIPS
  - AI visual defect review has not been run on source/render/diff proof panels from a real splat artifact
  - filtered point count is 6.88% below the mature baseline even though raw points and registration pass
latest_artifacts:
  - scripts/sfm/evaluate_sfm_quality.py
  - scripts/sfm/run_sfm_reducer_canary.py
  - tests/unit/test_sfm_quality_eval.py
  - tests/unit/test_sfm_reducer_canary.py
  - logs/sfm-production-spine/r4exact739s1-1777612249-sfm_quality_report.json
  - logs/sfm-production-spine/md1_two_leaf_reducer_canary_20260512.json
  - logs/sfm-production-spine/md1_two_leaf_reducer_canary_quality_20260512.json
  - logs/sfm-production-spine/md1_two_leaf_reducer_canary_viewer_api_summary_20260512.json
  - logs/sfm-production-spine/md1-two-leaf-reducer-canary-viewer-20260512.png
  - logs/sfm-production-spine/md1_two_leaf_reducer_canary_s3_20260512.txt
  - scripts/sfm/run_sfm_fanout_reducer.py
  - tests/unit/test_sfm_fanout_reducer.py
  - logs/sfm-production-spine/md1_fanout_reducer_proof_20260512T1803Z.json
  - logs/sfm-production-spine/md1_fanout_reducer_proof_quality_20260512T1803Z.json
  - logs/sfm-production-spine/md1_fanout_reducer_proof_viewer_api_summary_20260512T1803Z.json
  - logs/sfm-production-spine/md1_fanout_reducer_proof_playwright_20260512T1803Z.json
  - logs/sfm-production-spine/md1-fanout-reducer-proof-viewer-20260512T1803Z.png
  - logs/sfm-production-spine/md1_fanout_reducer_proof_s3_20260512T1803Z.txt
  - scripts/sfm/evaluate_visual_quality.py
  - tests/unit/test_sfm_visual_quality.py
  - s3://spaceport-ml-processing-staging/manual-validations/md1-fanout-canary-20260512/merged-pose-aligned/colmap
  - s3://spaceport-ml-processing-staging/manual-validations/md1-fanout-reducer-proof-20260512T1803Z/merged/colmap
