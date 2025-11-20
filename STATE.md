reason: sogs-test-1763664401 renders locally via the embedded SuperSplat build, but the `spaceport-ml-processing` S3 bucket still requires SigV4/KMS so remote loads fail without AWS credentials
last_step: mirrored the sogs-test-1763664401 supersplat_bundle into `web/public`, defaulted the `/sogs-viewer` UI to that copy, and ran chromium + webkit Playwright scenarios plus a fresh Next.js build to prove the viewer decompresses/renders the splat
next_unblocked_step: once the bucket either allows unsigned GETs or we get deployable AWS creds for the proxy, repoint the default bundle to the S3 URL and repeat the verification loop against the Cloudflare preview alias
owner_action_needed: relax the SSE-KMS policy on `s3://spaceport-ml-processing/compressed/sogs-test-1763664401/` (or share safe AWS credentials for Cloudflare) so `/api/sogs-proxy` can stream the remote assets
updated: 2025-11-20T20:10:27Z
