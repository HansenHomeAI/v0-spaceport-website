STOPPED: company pivot halted CV-HR SfM-authority 3DGS work
reason: User pivoted company direction and requested no more compute spend for this feature. All known 3DGS watcher sessions have been killed and AWS was checked for active jobs.
last_step: R38 tile_00 no-training job `cvhr-r38-t00-edge2c035-1780082336` completed before the stop request took effect; no merge/review was launched for R38. Final checks showed no SageMaker Processing jobs in `InProgress`, no SageMaker Training jobs in `InProgress`, no queued/in-progress `spaceport-ml-containers` CodeBuild builds, and no `tmux` sessions.
next_unblocked_step: none unless the feature is revived. If revived, resume from `docs/3dgs-sfm-authority-pivot-handoff.md` and the latest blocker: `DJI_00809.JPG` horizon foreground alpha coverage remains barely over the hard gate while V18 non-regression promotes.
owner_action_needed: none currently
automations: all local `codex-3dgs-*` passive watcher sessions were killed; the aggressive `codex` watchdog had already been stopped earlier after duplicate canary risk.
updated: 2026-05-29T19:34:00Z
