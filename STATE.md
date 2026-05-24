reason: Montana time capsule monitor (SfM -> 3DGS -> compress -> viewer gates)
last_step: 2026-05-24T10:07:56Z Friday heartbeat evidence postpush GH snapshots recorded (cfb7c1e6; `[skip ci]`); evidence in logs/montana-time-capsule/STATE.md.
next_unblocked_step: continue no-spend monitoring until `friday-mtc-20260524T0001Z-3dgs` reaches `Completed`, then advance to pinned compression (one stage at a time).
[2026-05-22T15:36:42Z] heartbeat -> terminal reconfirmed (no spend) -> idle
[2026-05-22T15:37:51Z] heartbeat -> fresh reconfirmed (no spend) -> commit+push evidence
[2026-05-22T15:38:34Z] heartbeat -> fresh reconfirmed (no spend) -> commit+push evidence
[2026-05-22T15:47:04Z] heartbeat -> no-spend; no new jobs launched -> commit/push ledger
[2026-05-23T10:14:00Z] heartbeat -> terminal + S3 bundle + viewer/proxy HTTP200 + CI proof -> commit+push ledger
[2026-05-23T10:26:30Z] heartbeat -> terminal + S3 bundle + viewer/proxy HTTP200 -> commit+push ledger
[2026-05-23T10:31:23Z] post-heartbeat -> recorded git head + exact-head GH runs -> commit+push ledger
[2026-05-23T12:23:12Z] heartbeat -> boto3 aws/sm/s3 + viewer/proxy HTTP200 + GH REST snapshot -> commit+push ledger
[2026-05-23T13:04:40Z] heartbeat -> awscli sm/s3 + viewer/proxy HTTP200 + gh snapshot -> idle
[2026-05-23T13:06:43Z] postpush -> recorded gh runs for new head -> idle
[2026-05-23T14:04:11Z] heartbeat -> awscli sm/s3 + viewer/proxy HTTP200 + gh snapshot -> commit+push ledger
[2026-05-23T14:05:08Z] postpush -> recorded gh runs for new head -> idle
[2026-05-23T18:23:52Z] heartbeat -> awscli sm/s3 + viewer/proxy HTTP200 + gh snapshot -> commit+push ledger
[2026-05-23T18:25:50Z] postpush -> recorded gh runs for new head -> idle
[2026-05-24T10:05:12Z] heartbeat -> SfM Completed; 3DGS InProgress; S3+GH snapshots -> commit+push ledger
