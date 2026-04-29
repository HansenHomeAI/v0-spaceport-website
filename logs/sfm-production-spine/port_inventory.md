# SfM Production Spine Port Inventory

| Required item | Decision |
|---|---|
| Base branch/head | `origin/agent-31459027-sfm-final-bridge-fallback` at `e42165e67ea6d8b635231105db1f216cdde1788d` |
| Dirty-state review | Existing local mature worktree has dirty `STATE.md` and `scripts/sfm/run_sfm_benchmark.py`; ignored for implementation. This branch was created from the clean remote mature head. |
| Files inspected | `infrastructure/containers/sfm/run_colmap_sfm.py`, `scripts/sfm/run_sfm_benchmark.py`, `tests/unit/test_colmap_gps_priors.py`, `docs/md1_phase1_footprint_graph_validation.md`, `.github/workflows/deploy-cloudflare-pages.yml`, `.github/workflows/cdk-deploy.yml`, `.github/workflows/build-containers.yml` |
| Logic to preserve | `footprint_graph_v1`, capped pair-list matching through `matches_importer`, bounded chunk recovery, adjacent/bridge recovery, seam-only balanced merge, standard `images/`, `database.db`, `sfm_metadata.json`, and `sparse/0/{cameras.txt,images.txt,points3D.txt}` export |
| Logic not to add in v1 | `hloc`, `LightGlue`, `MASt3R`, `DUSt3R`, `VGGSfM`, and full-scene `global_mapper` |
| First files to edit | `infrastructure/containers/sfm/run_colmap_sfm.py`, `scripts/sfm/run_sfm_benchmark.py`, `tests/unit/test_colmap_gps_priors.py`, `STATE.md`, `logs/sfm-production-spine/frontier.json`, `logs/agent-loop.log` |
| First local tests | `python3 scripts/sfm/run_sfm_benchmark.py --help`; `python3 -m unittest tests.unit.test_colmap_gps_priors`; planner-only tiny fixture run with `COLMAP_PIPELINE_MODE=distributed_chunked_v1` |

