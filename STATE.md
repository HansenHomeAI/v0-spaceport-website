reason: production-ready MD1 3DGS cost-reduction loop
current_rung: MD1_cost_reduction_retry1_presubmit_blocked_by_processing_e755
root_cause_classification: sentinel merge payload selected BACKGROUND_SOURCE_TILE_ID=tile_10 while the validated reuse merge plan contained only tile_04. CloudWatch failed closed with RuntimeError: requested background source tile tile_10 has no background_skybox.webp; available tiles: ['tile_04'].
current_branch_head: branch agent-90742618-md1-geometry-consistency is at e755dbc4f066fc554acee8ffaf8ef69a5eb63591 after corrected retry CodeBuild-hold evidence.
current_exact_head_gate_status: exact-head e755dbc4f066fc554acee8ffaf8ef69a5eb63591 green on CDK Deploy 26049681054.
current_live_compute_status: Fresh retry1 readiness against e755dbc4 is blocked because SageMaker processing is active: cvhr-mtc-20260518T1729Z-sfm InProgress (Component=SfM, Dataset=CV-HR, Profile=montana-time-capsule, SFM_BRANCH_NAME=agent-40136728-montana-time-capsule, SFM_GIT_HEAD=1b264bc2ac6be3bf34ca06582895f7f750e9a442). Training, Step Functions, and CodeBuild are idle. No paid retry/review/full14/LOD submitted.
latest_paid_steps: Failed sentinel merge md1-r0v5relax-merge-20260515 remains terminal Failed and debited. Failed job name must not be reused.
latest_no_spend_evidence: Corrected retry1 merge plan is materialized and uses suffixed job md1-r0v5relax-merge-retry1-8fdaa86f-20260518T170629Z with no BACKGROUND_SOURCE_TILE_ID. Fresh readiness against e755dbc4 blocks on processing_jobs_in_progress. Evidence: logs/md1-r0v5relax-merge-retry1-processing-hold-e755dbc4-20260518T175208Z-summary.json and logs/md1-r0v5relax-merge-retry1-processing-hold-e755dbc4-20260518T175208Z-cvhr-mtc-sfm-describe.json.
latest_testing: python3 -m unittest tests.unit.test_tiled_merge_processing_planner passed earlier. No new code changes after that.
latest_cost_control: No paid compute launched after failed sentinel merge. Budget remains debited at $0.075272, with $13.924728 remaining. Retry paid submit is blocked until SageMaker processing is idle and exact-head/AWS/CodeBuild/duplicate/readiness/budget checks are rerun.
blocked_promotion_reason: Retry1 is not submitted. Production promotion remains blocked until suffixed merge retry completes, preflight passes, then review/visual QA/full14/LOD/viewer gates pass.
next_unblocked_step: Wait for cvhr-mtc-20260518T1729Z-sfm to reach terminal state without stopping it, then rerun exact-head/AWS/CodeBuild/duplicate/readiness/budget checks against the latest committed head before any paid submit.
owner_action_needed: none
