# Litchi Controller Send E2E Proof - 2026-05-28

Preview URL: https://agent-38642091-litchi-contro.v0-spaceport-website-preview2.pages.dev

Spaceport test user: codex-litchi-test+20260204T191111Z@spcprt.dev

Mission uploaded:

`litchi-e2e-20260529000156_flight-01-of-01_20260528-180205`

Proof summary:

- Signed into Spaceport test account and opened `/create`.
- Created a one-flight drone plan at `38.27371, -78.16950`, one battery, 10 minutes, altitude `120-160`.
- Clicked `Send to Controller` in the Spaceport modal.
- Spaceport API moved from `Uploading 1/1` to `Uploaded 1/1`.
- Step Functions execution `litchi-58a1f3f0-20260528-180205-1` finished `SUCCEEDED`.
- Litchi Mission Hub `Open...` list showed the uploaded mission row, ellipsized by Litchi as `litchi-e2e-20260529000156_flight-01...`.
- Mobile responsive check at `390x844` had `documentScrollWidth: 390` and no overflowing controls.

Key proof files:

- `spaceport-ui/events.json`
- `spaceport-ui/status-after-click.json`
- `spaceport-ui/status-summary.json`
- `spaceport-ui/mission-names.json`
- `spaceport-ui/mobile-metrics.json`
- `litchi-hub/verify.json`
- `litchi-hub/litchi-open-mission-list.png`
- `worker-test-58a-after-narrow-policy.json`
