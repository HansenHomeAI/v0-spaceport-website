reason: HMC Montana time capsule monitor (SfM -> 3DGS -> compress -> viewer gates)
last_step: 2026-05-23T22:24:45Z postpush verify: pushed heartbeat evidence commit (22ef8775; [skip ci]) and recorded branch + exact-head GitHub Actions snapshots (exact-head empty due to `[skip ci]`); evidence in logs/montana-time-capsule/STATE.md.
next_unblocked_step: idle; do not launch duplicate HMC jobs. Only proceed if a new explicit acceptance gate is requested (promotion/registry/public publish).
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
