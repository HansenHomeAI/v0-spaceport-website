reason: unblock PlayCanvas SOGS viewer testing – CDN runtime missing
last_step: built the /sogs-viewer route and tried to run Playwright validations, but `@playcanvas/supersplat` CDN returns 404 (so `window.SuperSplatViewer` is undefined) and no public package exists; hosted tests + logs under `logs/sogs-viewer-*.log/png` demonstrate the missing dependency
next_unblocked_step: obtain an actual SuperSplat viewer bundle (or an approved alternative) that exposes `SuperSplatViewer.loadFromUrl` so we can finish wiring + testing against the S3 bundle
owner_action_needed: provide a valid script source (or green-light for another rendering approach) for the SuperSplat viewer
updated: 2025-11-20T16:25:00Z
