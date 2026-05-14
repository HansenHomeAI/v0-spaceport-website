reason: project-level continuation toward production-ready huge-scene tiled SfM; automation is active and must remain active until final proof has no unresolved caveats or owner explicitly stops it.
last_step: 2026-05-14T06:25Z promoted heldout-panel diagnostics into scripts/sfm/evaluate_sfm_quality.py via optional --panel-diagnostics-json. Added unit coverage in tests/unit/test_sfm_quality_eval.py and tests/unit/test_sfm_heldout_panel_diagnostics.py. py_compile passed for evaluate_sfm_quality.py and diagnose_heldout_panels.py; unittest passed for both quality-eval suites (9 tests). Re-ran r21 integrated quality with panel diagnostics at logs/sfm-production-spine/md1_fanout_reducer_with_r21_3dgs_quality_paneldiag_20260514T0620Z.json: heldout_render_metrics=pass, ai_visual_review=warning, heldout_panel_diagnostics=warning, decision=needs_more_proof.
next_unblocked_step: Commit and push the quality-gate diagnostics patch if not already pushed, then monitor exact-head GitHub workflows. No sample120 relaunch. After workflows are green, choose between full447 with r21 knobs or renderer/export-specific inspection based on the new deterministic fine-detail softness gate; avoid full-MD1 spend until this is reconciled.
owner_action_needed: none
active_jobs: []
active_workflows: []
active_codebuild: []
blocked_by_external_capacity: false
unrelated_active_jobs: []
branch: agent-73948216-sfm-production-spine
head: b97239e69498412f8391a4ba31216bf268f46385
updated: 2026-05-14T06:25:00Z
