# SfM Production Spine Port Inventory

| Required item | Decision |
|---|---|
| Base branch/head | `origin/agent-31459027-sfm-final-bridge-fallback` at `e42165e67ea6d8b635231105db1f216cdde1788d`; feature branch/worktree is `agent-73948216-sfm-production-spine` at `/Users/gabrielhansen/worktrees/agent-73948216-sfm-production-spine`. |
| Dirty-state review | The root checkout was clean. The mature local worktree exists at `.agent-worktrees/agent-31459027-sfm-final-bridge-fallback`; it was treated as source context only and no dirty local files were copied. |
| Files inspected | `infrastructure/containers/sfm/run_colmap_sfm.py`, `scripts/sfm/run_sfm_benchmark.py`, `tests/unit/test_colmap_gps_priors.py`, `docs/md1_phase1_footprint_graph_validation.md`, `.github/workflows/deploy-cloudflare-pages.yml`, `.github/workflows/cdk-deploy.yml`, `.github/workflows/build-containers.yml`. |
| Logic to preserve | `footprint_graph_v1`, pair-list matching through `matches_importer`, bounded chunk recovery, adjacent/bridge recovery, balanced overlap-first merge, seam/local refinement, and the standard `images/`, `database.db`, `sfm_metadata.json`, `sparse/0/` COLMAP output contract. |
| Logic not to add in v1 | hloc, LightGlue, MASt3R, DUSt3R, VGGSfM, learned retrieval rescue, learned SfM rescue, and full-scene `global_mapper` as a primary method. |
| First files to edit | `infrastructure/containers/sfm/run_colmap_sfm.py`, `scripts/sfm/run_sfm_benchmark.py`, `tests/unit/test_colmap_gps_priors.py`, `STATE.md`, `logs/agent-loop.log`, `logs/sfm-production-spine/frontier.json`. |
| First local tests | `python3 scripts/sfm/run_sfm_benchmark.py --help`; `python3 -m unittest tests.unit.test_colmap_gps_priors`; targeted new unit tests for mode parsing, planner report generation, manifest stability, leaf metadata schema, reducer metadata schema, and default behavior unchanged when `COLMAP_PIPELINE_MODE` is unset. |
