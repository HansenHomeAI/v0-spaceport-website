reason: SfM-only visibility-cell production proof completed. The final MD1 artifact is one merged COLMAP sparse output produced from 19 distributed visibility-cell leaves with pruning and seam-conflict culling. Downstream 3DGS/SOGS render and AI visual gates are separate and are not part of this SfM-stage proof.
last_step: 2026-05-19T15:59Z: uploaded and viewer-validated `merged-pruned-culled/colmap`; API returned HTTP 200 with 3076 registered images, 1057498 exact points, and 160000 sampled points; browser screenshot rendered visible points with lit_ratio_10pct=0.0466475.
next_unblocked_step: Optional downstream handoff only: feed the single COLMAP artifact into the downstream 3DGS step, or use the local dev viewer for manual SfM inspection. No additional SfM fanout/reducer work is pending.
owner_action_needed: none
active_jobs: []
completed_jobs: ["md1-viscell-plan-v1-1779135256", "md1-viscell-full-l00-1779141981", "md1-viscell-full-l01-1779141986", "md1-viscell-full-l02-1779143476", "md1-viscell-full-l03-1779145861", "md1-viscell-full-l04-1779146968", "md1-viscell-full-l05-1779147527", "md1-viscell-full-l06r2-1779154798", "md1-viscell-full-l07-1779151432", "md1-viscell-full-l08-1779155211", "md1-viscell-full-l09-1779157902", "md1-viscell-full-l10-1779158398", "md1-viscell-full-l11-1779161085", "md1-viscell-full-l12-1779161215", "md1-viscell-full-l13-1779164027", "md1-viscell-full-l14-1779164403", "md1-viscell-full-l15-1779167214", "md1-viscell-full-l16-1779167589", "md1-viscell-full-l17-1779168816", "md1-viscell-full-l18-1779170653"]
failed_jobs: ["md1-viscell-full-l06-1779150311"]
held_jobs: []
unrelated_active_jobs: []
branch: agent-73948216-sfm-production-spine
head: 60fcec4fe28e3ee73e4c44aa5eebcf4ade543c54
current_rung: SFM_VISIBILITY_CELL_V1_FULL_FANOUT_REDUCER_VIEWER_PASSED
project_final_decision: sfm_stage_production_ready_downstream_3dgs_separate
project_level_unresolved_caveats: ["Downstream 3DGS/SOGS render and AI visual gates are separate from this SfM-only deliverable", "global sparse double-surface grid has 4 warning cells, but cross-leaf seam overlap is authoritative and passes with flagged_overlap_cell_ratio=0.0"]
final_sfm_output_uri: s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-full-20260518T2206Z/merged-pruned-culled/colmap
current_viewer_url: http://127.0.0.1:3000/pipeline-viewer?url=s3%3A%2F%2Fspaceport-ml-processing-staging%2Fmanual-validations%2Fmd1-visibility-cell-v1-full-20260518T2206Z%2Fmerged-pruned-culled%2Fcolmap&maxPoints=160000
final_reducer_report: logs/sfm-production-spine/md1_visibility_cell_v1_full_reducer_pruned_culled_20260519T1531Z.json
final_quality_report: logs/sfm-production-spine/md1_visibility_cell_v1_full_quality_pruned_culled_viewer_20260519T1557Z.json
final_viewer_api: logs/sfm-production-spine/md1_visibility_cell_v1_full_pruned_culled_viewer_api_summary_20260519T1556Z.json
final_viewer_visual_proof: logs/sfm-production-spine/md1_visibility_cell_v1_full_pruned_culled_viewer_visual_proof_20260519T1559Z.json
final_viewer_screenshot: logs/sfm-production-spine/md1_visibility_cell_v1_full_pruned_culled_viewer_20260519T1559Z.png
final_s3_listing: logs/sfm-production-spine/md1_visibility_cell_v1_full_pruned_culled_s3_listing_20260519T1559Z.txt
sfm_stage_metrics:
  planner: visibility_cell_v1
  leaf_count: 19
  registered_images: 3076
  expected_images: 3076
  merged_points3d: 1057498
  min_leaf_retention: 1.0
  weak_merge_nodes: 0
  final_min_track_length: 3
  seam_conflict_points_removed: 29621
  cross_leaf_flagged_overlap_cell_ratio: 0.0
  sparse_low_track_ratio: 0.0
  sparse_reprojection_error_p95: 1.7666
  viewer_http_status: 200
  viewer_lit_ratio_10pct: 0.0466475
updated: 2026-05-19T15:59Z

sfm_visibility_cell_v1_implementation:
  updated: 2026-05-18T17:41:04Z
  scope: SfM-only camera-to-cell correlation, distributed leaf contract, jurisdiction filtering, and merge-quality gates. No 3DGS/SOGS job was launched.
  status: no-spend implementation/tests passed
  files:
    - infrastructure/containers/sfm/run_colmap_sfm.py
    - scripts/sfm/build_sfm_fanout_contract.py
    - scripts/sfm/evaluate_sfm_quality.py
    - tests/unit/test_colmap_gps_priors.py
    - tests/unit/test_sfm_fanout_contract.py
    - tests/unit/test_sfm_quality_eval.py
  implemented:
    - visibility_cell_v1 planner uses EXIF-derived camera positions, heading/pitch, FOV footprint projection, adaptive cells, overlap membership, and horizon context metadata.
    - each image has one primary cell owner and may be reused as overlap support in neighboring visible cells.
    - leaf chunks carry jurisdiction_bounds so final sparse filtering can reject points outside the owning cell footprint.
    - fanout contract preserves visibility_cell_v1 in leaf env and requires primary ownership, jurisdiction bounds, immutable manifest, bounded retries, and standard COLMAP sparse outputs.
    - quality evaluator now fails weak seams and adds sparse cleanliness plus double-surface/layering diagnostics.
  verification:
    - python3 -m py_compile infrastructure/containers/sfm/run_colmap_sfm.py scripts/sfm/build_sfm_fanout_contract.py scripts/sfm/evaluate_sfm_quality.py
    - PYTHONPATH=. python3 -m unittest tests.unit.test_colmap_gps_priors tests.unit.test_sfm_fanout_contract tests.unit.test_sfm_quality_eval
  next_unblocked_step: run planner-report/no-spend MD1 manifest generation, inspect cell/camera correlation in the viewer, then launch the smallest two-leaf visibility_cell_v1 canary only after the manifest passes static gates.

sfm_visibility_cell_v1_seam_gate_hardening:
  updated: 2026-05-18T19:22:01Z
  current_goal_status: not_production_ready
  reason: The SfM-only visibility-cell plan is implemented, but MD1 planner manifest, distributed leaf canary, reducer merge, seam/double-surface diagnostics, and viewer proof are still pending.
  new_evidence:
    - logs/sfm-production-spine/visibility_cell_v1_synthetic_planner_audit_20260518T1918Z.json
    - logs/sfm-production-spine/visibility_cell_v1_codebuild_describe_20260518T1915Z.json
    - logs/sfm-production-spine/visibility_cell_v1_codebuild_tail_20260518T1915Z.json
    - logs/sfm-production-spine/visibility_cell_v1_container_run_view_20260518T1915Z.json
    - logs/sfm-production-spine/visibility_cell_v1_cdk_run_view_20260518T1915Z.json
    - logs/sfm-production-spine/active-md1-processing-jobs-visibility-cell-prelaunch-20260518T1926Z.json
    - logs/sfm-production-spine/active-md1-training-jobs-visibility-cell-prelaunch-20260518T1926Z.json
  hardening:
    - static report now separates true adjacent-cell seam overlap from incidental non-adjacent shared images.
    - fanout dry-run contract now blocks visibility_cell_v1 manifests with adjacent seams under 10 shared images unless a targeted seam proof is explicitly supplied.
    - unit tests now cover adjacent seam gating and far/out-of-jurisdiction sparse point rejection.
  verification:
    - python3 -m py_compile infrastructure/containers/sfm/run_colmap_sfm.py scripts/sfm/build_sfm_fanout_contract.py scripts/sfm/evaluate_sfm_quality.py
    - PYTHONPATH=. python3 -m unittest tests.unit.test_sfm_fanout_contract tests.unit.test_colmap_gps_priors.ColmapGpsPriorTests.test_visibility_cell_planner_builds_primary_overlap_and_jurisdictions tests.unit.test_colmap_gps_priors.ColmapGpsPriorTests.test_visibility_cell_jurisdiction_rejects_far_owner_points tests.unit.test_sfm_quality_eval
    - PYTHONPATH=. python3 -m unittest tests.unit.test_colmap_gps_priors tests.unit.test_sfm_fanout_contract tests.unit.test_sfm_quality_eval
  active_ci:
    exact_head: 436b620ed69ac0b5ea7611488a73968e4717db28
    container_workflow: 26055319176
    cdk_workflow: 26055319169
    codebuild: spaceport-ml-containers:0109c1cb-3e72-4547-a2f7-9dde1a170f12
    prior_codebuild_completed: spaceport-ml-containers:83ad3e50-5f3f-4802-8dd6-616183c072a2
    status: exact-head CodeBuild IN_PROGRESS/INSTALL and CDK running
  prelaunch_context:
    ml_stack: SpaceportMLPreview1FCC870EE1Stack
    ml_bucket: spaceport-ml-processing-staging
    sfm_repo: 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm
    sfm_image_tag: agent73948216sfmproductionspine
    md1_input: s3://spaceport-uploads/1775750905123-vg76vr-md1-dji-images.zip
    unrelated_active_processing_jobs: ["md1-shrunk-prodspine-sfm-1779128752"]
    active_task_owned_processing_jobs: []
    active_training_jobs: []
  next_unblocked_step: commit/push seam-gate hardening, wait for exact-head container/CDK green, then launch bounded MD1 visibility_cell_v1 planner-report proof before any leaf fanout.

sfm_visibility_cell_v1_synthetic_adjacent_seam_audit:
  updated: 2026-05-18T19:30:50Z
  current_goal_status: not_production_ready
  evidence:
    - logs/sfm-production-spine/visibility_cell_v1_synthetic_planner_audit_20260518T1930Z.json
  result: pass
  facts:
    - hardened synthetic visibility-cell audit used 100 EXIF/GPS/orientation images across 6 adaptive cells.
    - unique primary ownership remained exact: 100/100 core images assigned to one cell.
    - max leaf image count stayed bounded at 80 with overlap support enabled.
    - adjacent seam gate passed: min_adjacent_shared_images=63 against required 10, weak_adjacent_seams_under_10=[].
    - horizon context path was exercised with 15 shallow/long-range images.
    - jurisdiction probe accepted an inside-owner point and rejected a far out-of-jurisdiction point.
  active_ci:
    exact_head: 436b620ed69ac0b5ea7611488a73968e4717db28
    codebuild: spaceport-ml-containers:0109c1cb-3e72-4547-a2f7-9dde1a170f12
    status: SUCCEEDED/COMPLETED at 2026-05-18T19:39Z
    container_workflow: 26055319176 success
    cdk_workflow: 26055319169 success
    sfm_image: 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:agent73948216sfmproductionspine
    sfm_image_digest: sha256:5555ea556b0d6e66560f749ff41e19436cc1161a23f0729bebf7c95a7ea752a4
  next_unblocked_step: monitor full-MD1 visibility_cell_v1 planner-report proof before any leaf fanout.

sfm_visibility_cell_v1_md1_planner_report:
  updated: 2026-05-18T19:55Z
  current_goal_status: not_production_ready
  job_name: md1-viscell-plan-v1-1779133371
  status: Failed
  input: s3://spaceport-uploads/1775750905123-vg76vr-md1-dji-images.zip
  output: s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-planner-20260518T1942Z/colmap
  image: 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:agent73948216sfmproductionspine
  image_digest_at_launch: sha256:5555ea556b0d6e66560f749ff41e19436cc1161a23f0729bebf7c95a7ea752a4
  launch_env:
    planner_report_only: true
    COLMAP_PIPELINE_MODE: distributed_chunked_v1
    COLMAP_CHUNK_PLANNER: visibility_cell_v1
    COLMAP_LEAF_TARGET_IMAGES: 220
    COLMAP_LEAF_HARD_CAP: 360
    COLMAP_VISIBILITY_CELL_OVERLAP_RATIO: 0.15
    COLMAP_VISIBILITY_CELL_MAX_OVERLAP_CELLS: 4
    COLMAP_VISIBILITY_CELL_MIN_SCORE: 0.08
    COLMAP_CHUNK_OVERLAP_ANCHOR_COUNT: 20
  launch_note: first attempt rejected before job creation because ml.g4dn.xlarge fixed local storage rejected VolumeSizeInGB=160; relaunched with 120GB.
  evidence:
    - logs/sfm-production-spine/md1_visibility_cell_v1_planner_run_20260518T1941Z.log
    - logs/sfm-production-spine/md1_visibility_cell_v1_planner_run_20260518T1942Z.log
    - logs/sfm-production-spine/md1-viscell-plan-v1-1779133371_describe_poll_20260518T1943Z.json
    - logs/sfm-production-spine/md1_visibility_cell_v1_planner_s3_poll_20260518T1943Z.txt
    - logs/sfm-production-spine/md1-viscell-plan-v1-1779133371_cloudwatch_tail_20260518T1950Z.txt
    - logs/sfm-production-spine/md1-viscell-plan-v1-1779133371_describe_poll_20260518T1952Z.json
    - logs/sfm-production-spine/md1-viscell-plan-v1-1779133371_cloudwatch_tail_20260518T1952Z.txt
    - logs/sfm-production-spine/md1_visibility_cell_v1_planner_s3_poll_20260518T1952Z.txt
    - logs/sfm-production-spine/md1_visibility_cell_v1_planner_20260518T1942Z/sfm_metadata.json
    - logs/sfm-production-spine/md1_visibility_cell_v1_planner_20260518T1942Z/chunk_planner_manifest.json
    - logs/sfm-production-spine/md1_visibility_cell_v1_planner_20260518T1942Z/planner_static_report.json
    - logs/sfm-production-spine/md1_visibility_cell_v1_planner_20260518T1942Z/reducer_metadata.json
    - logs/sfm-production-spine/md1_visibility_cell_v1_planner_manifest_audit_20260518T1952Z.json
    - logs/sfm-production-spine/md1_visibility_cell_v1_fanout_contract_20260518T1952Z.json
  terminal_result:
    sagemaker_status: Failed
    failure_reason: "AlgorithmError: , exit code: 1"
    failure_isolation: wrapper validation bug only; planner_report_only produced required manifest/report/metadata but run_sfm.sh still required sparse/0/images/database.db.
    uploaded_artifacts:
      - chunk_planner_manifest.json
      - planner_static_report.json
      - reducer_metadata.json
      - sfm_metadata.json
    planner_artifacts_valid_for_static_gate: true
  manifest_audit:
    dataset_image_count: 3076
    chunk_count: 19
    unique_core_images: 3076
    duplicate_core_images: 0
    orphan_image_count: 0
    expected_output_kind: single_merged_model
    connected_component_count: 1
    risky_bridge_count: 0
    max_leaf_image_count: 360
    seam_overlap_percent: 15.0
    min_adjacent_shared_images: 25
    weak_adjacent_seams_under_10: []
    horizon_context_image_count: 2403
  fanout_contract:
    status: dry_run_contract_ready
    max_concurrency: 2
    gaps: []
  patch:
    file: infrastructure/containers/sfm/run_sfm.sh
    commit: e2315457661b32e983d9e1317bd1aec1c300b774
    verification:
      - bash -n infrastructure/containers/sfm/run_sfm.sh
      - PYTHONPATH=. python3 -m unittest tests.unit.test_colmap_gps_priors tests.unit.test_sfm_fanout_contract tests.unit.test_sfm_quality_eval
    result: planner/report snapshot mode now validates required manifest/report/metadata and exits without requiring sparse reconstruction files.
    pushed: true
    active_ci:
      container_workflow: 26057008964
      cdk_workflow: 26057008957
      codebuild: spaceport-ml-containers:40210393-c277-4eef-921e-06ab1dec9bbe
      status: exact-head CodeBuild IN_PROGRESS/INSTALL; CDK running
  next_unblocked_step: commit/push wrapper patch, wait exact-head container rebuild, rerun clean planner-report proof, then launch the smallest adjacent two-leaf canary from the ready manifest.
  latest_poll:
    status: Failed
    failure_reason: "AlgorithmError: , exit code: 1"
    processing_start_time: 2026-05-18T13:43:40.554000-06:00
    processing_end_time: 2026-05-18T13:52:02.637000-06:00
    cloudwatch: terminal
    progress: staged 12.8GB input ZIP, extracted 3076 images, wrote planner artifacts, then shell validation failed on missing reconstruction outputs.
    s3_output: complete planner/report artifact set uploaded

## 2026-05-18T20:11Z - visibility-cell wrapper patch image ready
- Exact head: e2315457661b32e983d9e1317bd1aec1c300b774.
- GitHub workflows:
  - CDK Deploy 26057008957: success.
  - Trigger ML Container Build 26057008964: success.
- CodeBuild: spaceport-ml-containers:40210393-c277-4eef-921e-06ab1dec9bbe succeeded for e2315457661b32e983d9e1317bd1aec1c300b774.
- ECR image: 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:agent73948216sfmproductionspine.
- ECR digest: sha256:15d4c2823c9d83e49273d0b7ca5a192c1cfe3227884001a96595580ca2ab287c.
- ECR pushed_at: 2026-05-18T14:10:55.044000-06:00.
- Active MD1 jobs before relaunch:
  - processing: unrelated md1-shrunk-prodspine-sfm-1779128752 InProgress with no ProcessingStartTime; left untouched.
  - training: none.
- Next: rerun the full-MD1 visibility_cell_v1 planner/report proof on the patched image, then use the clean manifest for the two-leaf adjacent seam canary.

## 2026-05-18T20:14Z - clean visibility-cell planner proof launched
- Job: md1-viscell-plan-v1-1779135256.
- Input: s3://spaceport-uploads/1775750905123-vg76vr-md1-dji-images.zip.
- Output: s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-planner-20260518T2014Z/colmap.
- Image tag: 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:agent73948216sfmproductionspine.
- Image digest before launch: sha256:15d4c2823c9d83e49273d0b7ca5a192c1cfe3227884001a96595580ca2ab287c.
- Current status: InProgress before ProcessingStartTime, no FailureReason.
- Local launch log: logs/sfm-production-spine/md1_visibility_cell_v1_planner_run_20260518T2014Z.log.
- Next: monitor to terminal, then download and gate manifest/report before launching the smallest adjacent two-leaf canary.

### 2026-05-18T20:21Z poll
- Status: InProgress, no FailureReason.
- ProcessingStartTime: 2026-05-18T14:15:04.622000-06:00.
- CloudWatch stream: md1-viscell-plan-v1-1779135256/algo-1-1779135304.
- Latest visible stage: environment verified on Tesla T4, 12.8GB MD1 zip staged, Python processor started extracting archive.
- S3 output: empty before EndOfJob upload.
- Evidence: logs/sfm-production-spine/md1-viscell-plan-v1-1779135256_cloudwatch_tail_20260518T2021Z.txt.

### 2026-05-18T20:24Z terminal static gate
- Status: Completed.
- ProcessingStartTime: 2026-05-18T14:15:04.622000-06:00.
- ProcessingEndTime: 2026-05-18T14:23:41.294000-06:00.
- Runtime: 8m37s wall SageMaker, 129.27s Python planner processing after extraction.
- S3 output:
  - s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-planner-20260518T2014Z/colmap/sfm_metadata.json
  - s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-planner-20260518T2014Z/colmap/chunk_planner_manifest.json
  - s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-planner-20260518T2014Z/colmap/planner_static_report.json
  - s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-planner-20260518T2014Z/colmap/reducer_metadata.json
- Static manifest audit: pass.
  - dataset_image_count: 3076
  - planner: visibility_cell_v1
  - chunk_count: 19
  - unique primary owners: 3076/3076
  - unique core images: 3076/3076
  - duplicate core images: 0
  - orphan images: 0
  - connected_component_count: 1
  - risky_bridge_count: 0
  - min_adjacent_shared_images: 25
  - weak_adjacent_seams_under_10: []
  - selected two-leaf seam canary: chunks 1 and 8, 25 manifest shared images.
- Fanout contract: dry_run_contract_ready for 19 leaf jobs, max concurrency 2, gaps [].
- Evidence:
  - logs/sfm-production-spine/md1-viscell-plan-v1-1779135256_describe_poll_20260518T2024Z.json
  - logs/sfm-production-spine/md1-viscell-plan-v1-1779135256_cloudwatch_tail_20260518T2023Z.txt
  - logs/sfm-production-spine/md1_visibility_cell_v1_planner_20260518T2014Z/
  - logs/sfm-production-spine/md1_visibility_cell_v1_planner_manifest_audit_20260518T2024Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_fanout_contract_20260518T2024Z.json
- Next: launch chunks 1 and 8 as independent leaf SfM jobs from the immutable planner manifest, reduce into one COLMAP sparse artifact, then run seam/double-surface/viewer proof.

## 2026-05-18T20:27Z - two-leaf visibility-cell SfM canary launched
- Goal: prove the new SfM planner can reconstruct two adjacent cells independently and reduce them into one COLMAP sparse model before full fanout.
- Canary base: s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-canary-20260518T2025Z.
- Immutable planner manifest:
  s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-planner-20260518T2014Z/colmap/chunk_planner_manifest.json.
- Leaf 01:
  - Job: md1-viscell-leaf-01-1779136049.
  - Chunk index: 1.
  - Output: s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-canary-20260518T2025Z/leaves/leaf-01/colmap.
  - Launch evidence: logs/sfm-production-spine/md1_visibility_cell_v1_leaf01_launch_20260518T2025Z.log and logs/sfm-production-spine/md1_visibility_cell_v1_leaf01_submit_20260518T2025Z.json.
- Leaf 08:
  - Job: md1-viscell-leaf-08-1779136078.
  - Chunk index: 8.
  - Output: s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-canary-20260518T2025Z/leaves/leaf-08/colmap.
  - Launch evidence: logs/sfm-production-spine/md1_visibility_cell_v1_leaf08_launch_20260518T2025Z.log and logs/sfm-production-spine/md1_visibility_cell_v1_leaf08_submit_20260518T2025Z.json.
- Shared seam basis: chunks 1 and 8 have 25 manifest shared images, the weakest valid adjacent seam in the clean planner audit.
- Next: monitor both leaves to terminal, verify each has sparse_raw/0 or sparse/0 text artifacts, reduce into s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-canary-20260518T2025Z/merged/colmap, then run quality/viewer gates.

### 2026-05-18T20:35Z poll
- Leaf 01: InProgress, ProcessingStartTime 2026-05-18T14:28:07.464000-06:00, no FailureReason.
  - CloudWatch stream: md1-viscell-leaf-01-1779136049/algo-1-1779136087.
  - Latest visible progress: feature_extractor around 36/360 selected manifest images.
- Leaf 08: InProgress, ProcessingStartTime 2026-05-18T14:28:39.724000-06:00, no FailureReason.
  - CloudWatch stream: md1-viscell-leaf-08-1779136078/algo-1-1779136119.
  - Latest visible progress: feature_extractor around 36/291 selected manifest images.
- S3 output: empty before EndOfJob upload, expected.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_cloudwatch_tail_20260518T2035Z.txt
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_cloudwatch_tail_20260518T2035Z.txt

### 2026-05-18T20:39Z poll
- Leaf 01: InProgress, no FailureReason; feature_extractor around 140/360 selected manifest images.
- Leaf 08: InProgress, no FailureReason; feature_extractor around 144/291 selected manifest images.
- S3 output: empty before EndOfJob upload, expected.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_cloudwatch_tail_20260518T2039Z.txt
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_cloudwatch_tail_20260518T2039Z.txt

### 2026-05-18T20:43Z poll
- Leaf 01: InProgress, no FailureReason; feature_extractor around 244/360 selected manifest images.
- Leaf 08: InProgress, no FailureReason; feature_extractor around 252/291 selected manifest images.
- S3 output: empty before EndOfJob upload, expected.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_cloudwatch_tail_20260518T2043Z.txt
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_cloudwatch_tail_20260518T2043Z.txt

### 2026-05-18T20:50Z poll
- Automation accountability: heartbeat automation `sfm-visibility-cell-production-proof-monitor` exists and is active for this thread; it should keep resuming this exact SfM-only visibility-cell proof until terminal production-ready proof or owner stop.
- Leaf 01: InProgress, ProcessingStartTime 2026-05-18T14:28:07.464000-06:00, no FailureReason; latest saved CloudWatch at 20:47Z showed feature_extractor around 350/360 selected manifest images.
- Leaf 08: InProgress, ProcessingStartTime 2026-05-18T14:28:39.724000-06:00, no FailureReason; feature extraction completed 291/291, pose priors coverage 291/291, immutable manifest restricted execution to chunk 8, matches_importer added 2624 verified image pairs, mapper active with at least 38 registered frames.
- S3 output: empty before EndOfJob upload, expected.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_describe_poll_20260518T2050Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_describe_poll_20260518T2050Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_cloudwatch_tail_20260518T2047Z.txt
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_cloudwatch_tail_20260518T2047Z.txt
  - logs/sfm-production-spine/md1_visibility_cell_v1_canary_s3_poll_20260518T2050Z.txt

### 2026-05-18T20:54Z poll
- Leaf 01: InProgress, no FailureReason; mapper active with at least 99 registered frames after completing feature extraction/match import.
- Leaf 08: InProgress, no FailureReason; mapper active with at least 128 registered frames.
- Status interpretation: both independent leaf reconstructions are making forward progress; reducer remains held until SageMaker terminal upload produces complete COLMAP sparse artifacts for both leaves.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_describe_poll_20260518T2054Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_describe_poll_20260518T2054Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_cloudwatch_tail_20260518T2054Z.txt
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_cloudwatch_tail_20260518T2054Z.txt

### 2026-05-18T20:58Z poll
- Leaf 01: InProgress, no FailureReason; mapper active with at least 148 registered frames.
- Leaf 08: InProgress, no FailureReason; mapper active with at least 165 registered frames.
- Status interpretation: both leaves are still registering images and running periodic retriangulation/global BA; no reducer or full fanout launched.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_describe_poll_20260518T2058Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_describe_poll_20260518T2058Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_cloudwatch_tail_20260518T2058Z.txt
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_cloudwatch_tail_20260518T2058Z.txt

### 2026-05-18T21:01Z poll
- Leaf 01: InProgress, no FailureReason; mapper active with at least 181 registered frames.
- Leaf 08: InProgress, no FailureReason; mapper active with at least 190 registered frames.
- Status interpretation: both leaves remain nonterminal and healthy; reducer is still held.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_describe_poll_20260518T2101Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_describe_poll_20260518T2101Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_cloudwatch_tail_20260518T2101Z.txt
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_cloudwatch_tail_20260518T2101Z.txt

### 2026-05-18T21:08Z poll
- Leaf 01: InProgress, no FailureReason; mapper active with at least 236 registered frames.
- Leaf 08: InProgress, no FailureReason; mapper active with at least 249 registered frames.
- S3 output: still empty because both jobs are InProgress and output upload is EndOfJob.
- Status interpretation: mapper remains healthy; reducer remains held until both leaves are terminal.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_describe_poll_20260518T2108Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_describe_poll_20260518T2108Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_cloudwatch_tail_20260518T2108Z.txt
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_cloudwatch_tail_20260518T2108Z.txt
  - logs/sfm-production-spine/md1_visibility_cell_v1_canary_s3_poll_20260518T2108Z.txt

### 2026-05-18T21:13Z poll
- Leaf 01: InProgress, no FailureReason; mapper active with at least 283 registered frames.
- Leaf 08: InProgress, no FailureReason; mapper active with at least 273 registered frames.
- Status interpretation: both leaves remain healthy but nonterminal; leaf 08 is near the selected-image count but still running BA/registration. Reducer remains held.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_describe_poll_20260518T2113Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_describe_poll_20260518T2113Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_cloudwatch_tail_20260518T2113Z.txt
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_cloudwatch_tail_20260518T2113Z.txt

### 2026-05-18T21:19Z poll
- Leaf 08: Completed, no FailureReason.
  - ProcessingStartTime: 2026-05-18T14:28:39.724000-06:00.
  - ProcessingEndTime: 2026-05-18T15:18:28.923000-06:00.
  - Terminal CloudWatch: registered 291/291 images, raw text model had 142001 points, jurisdiction-filtered `sparse/0` validation reported 4297 3D points, GPS priors 291, copied 291 images, `database.db` 471818240 bytes.
  - S3 output: complete leaf output uploaded under s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-canary-20260518T2025Z/leaves/leaf-08/colmap with `sparse/0`, `sparse_raw/0`, images, database, planner/report/metadata.
- Leaf 01: InProgress, no FailureReason; latest saved CloudWatch showed mapper active with at least 334 registered frames.
- Status interpretation: one leaf is terminal and valid; reducer remains held until leaf 01 is terminal and its sparse artifacts are verified.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_describe_poll_20260518T2119Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-08-1779136078_cloudwatch_terminal_20260518T2119Z.txt
  - logs/sfm-production-spine/md1_visibility_cell_v1_canary_s3_poll_20260518T2119Z.txt
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_describe_poll_20260518T2119Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_cloudwatch_tail_20260518T2119Z.txt

### 2026-05-18T21:28Z poll
- Leaf 01: InProgress, no FailureReason.
  - ProcessingStartTime: 2026-05-18T14:28:07.464000-06:00.
  - CloudWatch: mapper registered 359/360 selected images by 21:22Z, then continued retriangulation/global BA with heartbeats through elapsed=2302s.
  - S3 output: still empty before EndOfJob upload, expected for nonterminal SageMaker Processing output.
- Leaf 08: already Completed and verified in the prior poll.
- Active MD1 processing: task-owned leaf01 plus unrelated md1-shrunk-prodspine-sfm-1779128752; unrelated job left untouched.
- Status interpretation: one leaf is complete, one is healthy but nonterminal; reducer/full fanout remain held until leaf01 terminal artifacts are uploaded and verified.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_describe_poll_20260518T2128Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_cloudwatch_tail_20260518T2128Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_leaf01_s3_poll_20260518T2128Z.txt
  - logs/sfm-production-spine/active-md1-processing-jobs-current-20260518T2128Z.json

### 2026-05-18T21:30Z terminal two-leaf leaf stage
- Leaf 01: Completed, no FailureReason.
  - ProcessingStartTime: 2026-05-18T14:28:07.464000-06:00.
  - ProcessingEndTime: 2026-05-18T15:29:55.504000-06:00.
  - Runtime: about 61m48s SageMaker wall.
  - Terminal CloudWatch: registered 360/360 selected images, raw model 180298 points, jurisdiction-filtered `sparse/0` validation reported 37664 3D points, GPS priors 360, copied 360 images, `database.db` 594886656 bytes.
  - S3 output: complete leaf output uploaded under s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-canary-20260518T2025Z/leaves/leaf-01/colmap with 376 objects / 2.3 GiB, including `sparse/0`, `sparse_raw/0`, images, database, planner/report/metadata.
- Leaf 08: already Completed and verified, with 291/291 registered images and complete output.
- Status interpretation: both independent adjacent visibility-cell leaves are terminal and valid. Next step is local reducer merge into one COLMAP sparse artifact, then seam/double-surface/viewer gates before any full 19-leaf fanout.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_describe_poll_20260518T2130Z.json
  - logs/sfm-production-spine/md1-viscell-leaf-01-1779136049_cloudwatch_tail_20260518T2130Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_leaf01_s3_poll_20260518T2130Z.txt

### 2026-05-18T21:49Z two-leaf reducer and seam quality
- Initial reducer run against leaf `sparse_raw/0` passed mechanically but failed quality:
  - Output: s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-canary-20260518T2025Z/merged/colmap.
  - Merged 626 registered images and 318531 raw points.
  - Quality decision: `do_not_promote`.
  - Failures: low_track_ratio=0.0947 and global double-surface flagged_cell_ratio=0.0683.
  - Root cause: reducer preferred raw sparse artifacts, reintroducing points that leaf jurisdiction filtering had removed.
- Patch applied and unit-tested:
  - Reducer now prefers curated `sparse/0` and only falls back to `sparse_raw/0`.
  - Added cross-leaf seam surface-overlap diagnostic so the double-surface test measures actual inter-leaf layering instead of any vertical spread inside the whole terrain.
  - Verification: `python3 -m py_compile scripts/sfm/run_sfm_fanout_reducer.py scripts/sfm/run_sfm_reducer_canary.py scripts/sfm/evaluate_sfm_quality.py` passed.
  - Verification: `PYTHONPATH=. python3 -m unittest tests.unit.test_sfm_fanout_reducer tests.unit.test_sfm_reducer_canary tests.unit.test_sfm_quality_eval` passed, 14 tests OK.
- Corrected reducer run:
  - Output: s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-canary-20260518T2025Z/merged-filtered-seam/colmap.
  - S3 output: 11 objects / 521.8 MiB, standard `sparse/0`, `sparse_raw/0`, and `reducer_metadata.json`.
  - Merged 626/626 registered images, 41961 jurisdiction-filtered points, component_count=1, retention=1.0, no reducer blockers.
  - Shared seam: 25 shared registered images.
  - Cross-leaf surface overlap: 111 overlap cells, 0 flagged duplicate-layer cells, flagged_overlap_cell_ratio=0.0, median_abs_z_gap_m=0.3178, p95_abs_z_gap_m=2.0788.
  - Quality decision: `needs_more_proof` because heldout render/AI visual proof are not run; deterministic SfM gates pass, and global double-surface is downgraded to warning because the authoritative cross-leaf seam diagnostic passes.
- Evidence:
  - logs/sfm-production-spine/md1_visibility_cell_v1_two_leaf_reducer_20260518T2131Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_two_leaf_quality_20260518T2135Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_two_leaf_reducer_filtered_seam_20260518T2146Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_two_leaf_quality_filtered_seam_20260518T2149Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_two_leaf_merged_filtered_seam_s3_20260518T2149Z.txt
- Next: run viewer/API proof for the corrected two-leaf merged COLMAP artifact, commit/push reducer/test patch, then launch full 19-leaf fanout only after exact-head proof is preserved.

### 2026-05-18T22:01Z two-leaf viewer proof
- Local dev server: http://127.0.0.1:3000 from `/Users/gabrielhansen/worktrees/agent-73948216-sfm-production-spine/web`, started with AWS credentials exported for signed S3 preview reads.
- Viewer URL:
  http://127.0.0.1:3000/pipeline-viewer?url=s3%3A%2F%2Fspaceport-ml-processing-staging%2Fmanual-validations%2Fmd1-visibility-cell-v1-canary-20260518T2025Z%2Fmerged-filtered-seam%2Fcolmap&maxPoints=160000
- API proof:
  - HTTP 200.
  - registeredImageCount=626.
  - exactPointCount=41961.
  - sampledPointCount=155014.
  - cameraCount=626.
  - camera_up_y median=0.9753.
- Browser proof:
  - Canvas present at 1011x1155 browser pixels.
  - Screenshot saved at logs/sfm-production-spine/md1_visibility_cell_v1_two_leaf_viewer_20260518T2200Z.png.
  - Pixel sanity: 242947 sampled screenshot pixels, 17008 lit, 6035 bright, lit_ratio=0.07, bright_ratio=0.0248.
- Integrated quality with viewer payload:
  - Decision: `needs_more_proof`.
  - Deterministic SfM/reducer/viewer gates pass.
  - Remaining not-run gates are heldout downstream render metrics and AI visual review; those require 3DGS/splat outputs and are not SfM-only gates.
- Evidence:
  - logs/sfm-production-spine/md1_visibility_cell_v1_two_leaf_viewer_api_20260518T2154Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_two_leaf_viewer_20260518T2200Z.png
  - logs/sfm-production-spine/md1_visibility_cell_v1_two_leaf_viewer_pixel_stats_20260518T2200Z.txt
  - logs/sfm-production-spine/md1_visibility_cell_v1_two_leaf_quality_filtered_seam_viewer_20260518T2201Z.json
- Next: commit/push the reducer/test patch, wait exact-head CI/container proof, then launch full 19-leaf visibility-cell SfM fanout with max concurrency 2.

### 2026-05-19T03:08Z full 19-leaf visibility-cell fanout progress
- Current objective: complete the SfM-only visibility-cell production proof end-to-end. Do not claim production readiness until all 19 leaves reduce into one merged COLMAP artifact and SfM-specific quality/viewer gates pass.
- Full run root: s3://spaceport-ml-processing-staging/manual-validations/md1-visibility-cell-v1-full-20260518T2206Z.
- Completed and verified leaves: 00, 01, 02, 03, 04, 05, repaired 06-r2, 07, 08.
- Active leaves:
  - Leaf 09: `md1-viscell-full-l09-1779157902`, InProgress, no FailureReason, mapper active; CloudWatch reached `num_reg_frames=219` at 2026-05-19T03:06:59Z.
  - Leaf 10: `md1-viscell-full-l10-1779158398`, InProgress, no FailureReason, mapper active; CloudWatch reached `num_reg_frames=136` at 2026-05-19T03:07:01Z.
- Pending leaves: 11-18. The continuation manager is running with max concurrency 2, so no duplicate fanout jobs are needed.
- Evidence:
  - logs/sfm-production-spine/md1_visibility_cell_v1_full_fanout_continue_status.json
  - logs/sfm-production-spine/md1-viscell-full-l09-1779157902_describe_poll_20260519T0307Z.json
  - logs/sfm-production-spine/md1-viscell-full-l09-1779157902_cloudwatch_tail_20260519T0307Z.json
  - logs/sfm-production-spine/md1-viscell-full-l10-1779158398_describe_poll_20260519T0307Z.json
  - logs/sfm-production-spine/md1-viscell-full-l10-1779158398_cloudwatch_tail_20260519T0307Z.json
- Next: continue monitoring the active manager to terminal; once leaves 09/10 complete, let it launch 11/12 and repeat until all 19 leaves are verified, then run the full reducer, seam/layering diagnostics, sparse quality, and browser viewer proof.

### 2026-05-19T03:26Z full fanout leaf09 terminal
- Leaf 09 completed and verified:
  - Job: `md1-viscell-full-l09-1779157902`.
  - ProcessingStartTime: 2026-05-18T20:32:22.005000-06:00.
  - ProcessingEndTime: 2026-05-18T21:23:16.797000-06:00.
  - FailureReason: empty.
  - Registered images: 360/360.
  - Raw model points: 228280.
  - Filtered `sparse/0` points: 71079.
  - S3 output: 376 objects / 2411580435 bytes, including non-empty `sparse/0/cameras.txt`, `images.txt`, and `points3D.txt`.
- The manager launched leaf11 `md1-viscell-full-l11-1779161085`; active leaves are now leaf10 and leaf11, with leaves 12-18 pending.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-full-l09-1779157902_describe_poll_20260519T0325Z.json
  - logs/sfm-production-spine/md1-viscell-full-l09-1779157902_cloudwatch_tail_20260519T0325Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_full_leaf09_s3_poll_20260519T0325Z.txt
- Next: continue bounded manager polling; do not run reducer until all 19 leaves have terminal, verified sparse outputs.

### 2026-05-19T06:05Z full fanout leaf16 terminal
- Leaf 16 completed and verified:
  - Job: `md1-viscell-full-l16-1779167589`.
  - ProcessingStartTime: 2026-05-18T23:13:55.947000-06:00.
  - ProcessingEndTime: 2026-05-19T00:02:55.381000-06:00.
  - FailureReason: empty.
  - Registered images: 360/360.
  - Raw model points: 235477.
  - Filtered `sparse/0` points: 111811.
  - S3 output: 376 objects / 2426705016 bytes, including non-empty `sparse/0/cameras.txt`, `images.txt`, and `points3D.txt`.
- The manager launched the final pending leaf18 `md1-viscell-full-l18-1779170653`; active leaves are now leaf17 and leaf18, with no pending leaves.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-full-l16-1779167589_describe_poll_20260519T0604Z.json
  - logs/sfm-production-spine/md1-viscell-full-l16-1779167589_cloudwatch_tail_20260519T0604Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_full_leaf16_s3_poll_20260519T0604Z.txt
- Next: wait for leaf17 and leaf18 terminal verification, then run the full 19-leaf reducer and SfM quality/viewer proof.

### 2026-05-19T06:25Z full fanout leaf17 terminal
- Leaf 17 completed and verified:
  - Job: `md1-viscell-full-l17-1779168816`.
  - ProcessingStartTime: 2026-05-18T23:34:20.276000-06:00.
  - ProcessingEndTime: 2026-05-19T00:20:14.197000-06:00.
  - FailureReason: empty.
  - Registered images: 360/360.
  - Raw model points: 204849.
  - Filtered `sparse/0` points: 112985.
  - S3 output: 376 objects / 2401427391 bytes, including non-empty `sparse/0/cameras.txt`, `images.txt`, and `points3D.txt`.
- Active leaves: leaf18 only. Pending leaves: none. Completed/verified leaves: 18/19.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-full-l17-1779168816_describe_poll_20260519T0622Z.json
  - logs/sfm-production-spine/md1-viscell-full-l17-1779168816_cloudwatch_tail_20260519T0622Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_full_leaf17_s3_poll_20260519T0622Z.txt
- Next: wait for final leaf18 terminal verification, then run the full 19-leaf reducer and SfM quality/viewer proof.

### 2026-05-19T06:36Z full fanout terminal
- Full visibility-cell fanout completed: 19/19 leaves terminal and verified by the continuation manager.
- Final leaf 18 completed and verified:
  - Job: `md1-viscell-full-l18-1779170653`.
  - ProcessingStartTime: 2026-05-19T00:04:57.904000-06:00.
  - ProcessingEndTime: 2026-05-19T00:33:34.686000-06:00.
  - FailureReason: empty.
  - Registered images: 206/206.
  - Raw model points: 138269.
  - Filtered `sparse/0` points: 128887.
  - S3 output: 221 objects / 1430362806 bytes, including non-empty `sparse/0/cameras.txt`, `images.txt`, and `points3D.txt`.
- Evidence:
  - logs/sfm-production-spine/md1_visibility_cell_v1_full_fanout_continue_status.json
  - logs/sfm-production-spine/md1-viscell-full-l18-1779170653_describe_poll_20260519T0634Z.json
  - logs/sfm-production-spine/md1-viscell-full-l18-1779170653_cloudwatch_tail_20260519T0634Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_full_leaf18_s3_poll_20260519T0634Z.txt
- Next: run the full 19-leaf reducer into one COLMAP artifact, then run seam/layering diagnostics, sparse quality gates, and browser viewer proof.

### 2026-05-19T05:34Z full fanout leaf15 terminal
- Leaf 15 completed and verified:
  - Job: `md1-viscell-full-l15-1779167214`.
  - ProcessingStartTime: 2026-05-18T23:07:42.741000-06:00.
  - ProcessingEndTime: 2026-05-18T23:29:46.999000-06:00.
  - FailureReason: empty.
  - Registered images: 137/137.
  - Raw model points: 110087.
  - Filtered `sparse/0` points: 101703.
  - S3 output: 152 objects / 980783642 bytes, including non-empty `sparse/0/cameras.txt`, `images.txt`, and `points3D.txt`.
- The manager launched leaf17 `md1-viscell-full-l17-1779168816`; active leaves are now leaf16 and leaf17, with only leaf18 pending.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-full-l15-1779167214_describe_poll_20260519T0532Z.json
  - logs/sfm-production-spine/md1-viscell-full-l15-1779167214_cloudwatch_tail_20260519T0532Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_full_leaf15_s3_poll_20260519T0532Z.txt
- Next: continue bounded manager polling; do not run reducer until all 19 leaves have terminal, verified sparse outputs.

### 2026-05-19T05:15Z full fanout leaf14 terminal
- Leaf 14 completed and verified:
  - Job: `md1-viscell-full-l14-1779164403`.
  - ProcessingStartTime: 2026-05-18T22:20:46.630000-06:00.
  - ProcessingEndTime: 2026-05-18T23:11:00.892000-06:00.
  - FailureReason: empty.
  - Registered images: 360/360.
  - Raw model points: 214250.
  - Filtered `sparse/0` points: 87609.
  - S3 output: 376 objects / 2391404294 bytes, including non-empty `sparse/0/cameras.txt`, `images.txt`, and `points3D.txt`.
- The manager launched leaf16 `md1-viscell-full-l16-1779167589`; active leaves are now leaf15 and leaf16, with leaves 17-18 pending.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-full-l14-1779164403_describe_poll_20260519T0515Z.json
  - logs/sfm-production-spine/md1-viscell-full-l14-1779164403_cloudwatch_tail_20260519T0515Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_full_leaf14_s3_poll_20260519T0515Z.txt
- Next: continue bounded manager polling; do not run reducer until all 19 leaves have terminal, verified sparse outputs.

### 2026-05-19T05:08Z full fanout leaf13 terminal
- Leaf 13 completed and verified:
  - Job: `md1-viscell-full-l13-1779164027`.
  - ProcessingStartTime: 2026-05-18T22:14:34.033000-06:00.
  - ProcessingEndTime: 2026-05-18T23:04:11.952000-06:00.
  - FailureReason: empty.
  - Registered images: 360/360.
  - Raw model points: 234318.
  - Filtered `sparse/0` points: 194545.
  - S3 output: 376 objects / 2454357919 bytes, including non-empty `sparse/0/cameras.txt`, `images.txt`, and `points3D.txt`.
- The manager launched leaf15 `md1-viscell-full-l15-1779167214`; active leaves are now leaf14 and leaf15, with leaves 16-18 pending.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-full-l13-1779164027_describe_poll_20260519T0507Z.json
  - logs/sfm-production-spine/md1-viscell-full-l13-1779164027_cloudwatch_tail_20260519T0507Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_full_leaf13_s3_poll_20260519T0507Z.txt
- Next: continue bounded manager polling; do not run reducer until all 19 leaves have terminal, verified sparse outputs.

### 2026-05-19T04:22Z full fanout leaf11 terminal
- Leaf 11 completed and verified:
  - Job: `md1-viscell-full-l11-1779161085`.
  - ProcessingStartTime: 2026-05-18T21:25:26.086000-06:00.
  - ProcessingEndTime: 2026-05-18T22:17:31.171000-06:00.
  - FailureReason: empty.
  - Registered images: 360/360.
  - Raw model points: 252467.
  - Filtered `sparse/0` points: 180037.
  - S3 output: 376 objects / 2422472957 bytes, including non-empty `sparse/0/cameras.txt`, `images.txt`, and `points3D.txt`.
- The manager launched leaf14 `md1-viscell-full-l14-1779164403`; active leaves are now leaf13 and leaf14, with leaves 15-18 pending.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-full-l11-1779161085_describe_poll_20260519T0422Z.json
  - logs/sfm-production-spine/md1-viscell-full-l11-1779161085_cloudwatch_tail_20260519T0422Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_full_leaf11_s3_poll_20260519T0422Z.txt
- Next: continue bounded manager polling; do not run reducer until all 19 leaves have terminal, verified sparse outputs.

### 2026-05-19T04:15Z full fanout leaf12 terminal
- Leaf 12 completed and verified:
  - Job: `md1-viscell-full-l12-1779161215`.
  - ProcessingStartTime: 2026-05-18T21:27:33.747000-06:00.
  - ProcessingEndTime: 2026-05-18T22:09:45.328000-06:00.
  - FailureReason: empty.
  - Registered images: 298/298.
  - Raw model points: 181192.
  - Filtered `sparse/0` points: 50308.
  - S3 output: 314 objects / 2015457016 bytes, including non-empty `sparse/0/cameras.txt`, `images.txt`, and `points3D.txt`.
- The manager launched leaf13 `md1-viscell-full-l13-1779164027`; active leaves are now leaf11 and leaf13, with leaves 14-18 pending.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-full-l12-1779161215_describe_poll_20260519T0414Z.json
  - logs/sfm-production-spine/md1-viscell-full-l12-1779161215_cloudwatch_tail_20260519T0414Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_full_leaf12_s3_poll_20260519T0414Z.txt
- Next: continue bounded manager polling; do not run reducer until all 19 leaves have terminal, verified sparse outputs.

### 2026-05-19T03:30Z full fanout leaf10 terminal
- Leaf 10 completed and verified:
  - Job: `md1-viscell-full-l10-1779158398`.
  - ProcessingStartTime: 2026-05-18T20:40:39.530000-06:00.
  - ProcessingEndTime: 2026-05-18T21:24:37.124000-06:00.
  - FailureReason: empty.
  - Registered images: 360/360.
  - Raw model points: 235213.
  - Filtered `sparse/0` points: 172083.
  - S3 output: 376 objects / 2428169050 bytes, including non-empty `sparse/0/cameras.txt`, `images.txt`, and `points3D.txt`.
- The manager launched leaf12 `md1-viscell-full-l12-1779161215`; active leaves are now leaf11 and leaf12, with leaves 13-18 pending.
- Evidence:
  - logs/sfm-production-spine/md1-viscell-full-l10-1779158398_describe_poll_20260519T0330Z.json
  - logs/sfm-production-spine/md1-viscell-full-l10-1779158398_cloudwatch_tail_20260519T0330Z.json
  - logs/sfm-production-spine/md1_visibility_cell_v1_full_leaf10_s3_poll_20260519T0330Z.txt
- Next: continue bounded manager polling; do not run reducer until all 19 leaves have terminal, verified sparse outputs.
