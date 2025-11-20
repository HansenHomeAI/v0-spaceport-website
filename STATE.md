reason: sogs viewer now defaults to the remote sogs-test-1763664401 bundle and passes local + preview runs
last_step: re-uploaded the supersplat textures to S3 with SSE-S3, updated the viewer defaults/samples, and re-ran Next build plus chromium+webkit Playwright against localhost and the CF preview alias
next_unblocked_step: keep exercising new sogs outputs (drop them in S3 or public/), then rerun scripts/test-sogs-viewer.mjs with SOGS_BUNDLE_URL pointing to each dataset
owner_action_needed: optional – provide any additional bundles or viewer tweaks to verify
updated: $DATE
