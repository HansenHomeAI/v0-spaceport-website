reason: Continuing SfM-only visibility-cell production proof. The two-leaf MD1 canary passed filtered reducer, seam-overlap, quality, API, and browser-viewer gates, but it is not production-ready until the full 19-leaf fanout/reducer/viewer proof passes as one merged COLMAP sparse artifact.
last_step: 2026-05-18T22:01Z: corrected reducer to prefer jurisdiction-filtered sparse/0 over sparse_raw/0 and added cross-leaf surface-overlap diagnostics. The repaired two-leaf canary merged chunks 1 and 8 into one COLMAP artifact with 626/626 registered images, 41,961 filtered points, 25 shared seam cameras, and 0/111 flagged cross-leaf overlap cells; local /pipeline-viewer API and browser canvas proof passed.
next_unblocked_step: Commit/push reducer seam hardening, wait for exact-head CI/container proof, then launch the full 19-leaf visibility_cell_v1 MD1 fanout with max concurrency 2. After all leaves finish, merge into one COLMAP artifact, run sparse cleanliness/double-surface/seam diagnostics, and verify in /pipeline-viewer before claiming production-ready.
owner_action_needed: none
active_jobs: []
completed_jobs: ["md1-tile00-ds1000-r30-1778869168", "md1-tile01-ds1000-r30-1778869169", "md1-tile02-ds1000-r30-1778869170", "md1-tile03-ds1000-r30-1778869171", "md1-tile04-ds1000-r30-1778869172", "md1-tile00-split-r32-1778899939", "md1-tile00-h1i1lod-r40-1778978757", "md1-tile01-h1i1lod-r41-1778982712", "md1-tile02-h1i1lod-r41-1778982713", "md1-tile03-h1i1lod-r41-1778982714", "md1-tile04-h1i1lod-r41-1778982715"]
failed_jobs: ["md1-tile00-split-r31-1778898254", "md1-tile00-sogs-r33-1778908626", "md1-tile00-sogs-r34-1778914593", "md1-tile00-lodonly-r38-1778950901", "md1-tile00-h0lod-r39-1778976307", "r41-remaining-tiles-viewer-visual-proof", "r41-viewer-unified-lod-false-idle"]
held_jobs: []
unrelated_active_jobs: []
branch: agent-73948216-sfm-production-spine
head: e2315457661b32e983d9e1317bd1aec1c300b774
current_rung: SFM_VISIBILITY_CELL_V1_TWO_LEAF_CANARY_PASSED_FULL_FANOUT_PENDING
project_final_decision: not_production_ready_sfm_full_fanout_pending
project_level_unresolved_caveats: ["SfM-only production proof still needs full 19-leaf fanout on the visibility_cell_v1 manifest", "two-leaf canary is bounded evidence only", "downstream 3DGS/SOGS proof is separate from this SfM-only gate"]
current_viewer_url: http://127.0.0.1:3000/pipeline-viewer?url=s3%3A%2F%2Fspaceport-ml-processing-staging%2Fmanual-validations%2Fmd1-visibility-cell-v1-canary-20260518T2025Z%2Fmerged-filtered-seam%2Fcolmap&maxPoints=160000
two_leaf_filtered_reducer: logs/sfm-production-spine/md1_visibility_cell_v1_two_leaf_reducer_filtered_seam_20260518T2146Z.json
two_leaf_quality: logs/sfm-production-spine/md1_visibility_cell_v1_two_leaf_quality_filtered_seam_viewer_20260518T2201Z.json
two_leaf_viewer_api: logs/sfm-production-spine/md1_visibility_cell_v1_two_leaf_viewer_api_20260518T2154Z.json
two_leaf_viewer_screenshot: logs/sfm-production-spine/md1_visibility_cell_v1_two_leaf_viewer_20260518T2200Z.png
active_processing_jobs_proof: logs/sfm-production-spine/active-md1-processing-jobs-current-20260518T2128Z.json
updated: 2026-05-18T22:01Z

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
