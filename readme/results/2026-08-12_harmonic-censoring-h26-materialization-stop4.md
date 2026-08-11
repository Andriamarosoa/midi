# H26 — STOP 4 single real population materialization

Status: `H26_POPULATION_MATERIALIZED_STOP4_PENDING_EXTERNAL_REVIEW_BEFORE_P0`.

## Execution boundary

The single authorized invocation ran from clean HEAD
`182ae0c4f9c12729978e18056b2712d43aa4a151` on the exact qualified STOP 3
runtime. It used acknowledgement `H26_MATERIALIZATION_EXECUTE=1`, authorization
commit equal to HEAD, the ten exact controlled environment values, no worker
lock, the five unchanged STOP 3 artifacts and the fixed destination:

`/Users/amcarene/h26-admin/population/h26-synthetic-v1`

The invocation terminated with exit code `0`. Its terminal output reported:

- `materializer_invocations=1`;
- `retry_allowed=false`;
- authority ID
  `h26-materialization-authority-v1-1918eb0f2b74754fe79c50c994b9b038b5a27afcf80dd3ccf2d28825355a0be2`;
- authority raw SHA-256
  `ed0d55afe2923e4996f19e45be5aff99e2efab2f45ee6143c28f1a8ee6f2e805`.

The one-shot authorization is consumed. No retry is permitted.

## Published evidence

- Canonical authority: 2,977 bytes, mode `0600`, SHA-256
  `ed0d55afe2923e4996f19e45be5aff99e2efab2f45ee6143c28f1a8ee6f2e805`.
- External authority seal: 351 bytes, mode `0600`, SHA-256
  `f1118ccaae58bbbe90da3bcba1eab978ccd01b826f795fe163f409ae2e63bc42`.
- Population index: 108,072 bytes, mode `0600`, SHA-256
  `b0045797b08ef2ebbfaf7e1dda0c10f213eec3d8b3a3daaa31c8153dd842b4a7`.
- Baseline records: `40`.
- P2 grid records: `153`.
- Files at the population root: `87`.
- Final destination: real non-symlink directory, mode `0755`.

The P2 cardinality equals the sealed grid total
`9 + 20 + 36 + 36 + 32 + 8 + 12 = 153`. The two P2 tests without a grid add no
population record.

## Terminal checks and scope

After completion, the staging destination was absent, `active.lock` was absent,
PID `61293` was no longer running, and the Mac worktree remained clean at the
authorized HEAD. Authority and seal were each published once under their
SHA-derived filename.

These filesystem observations were performed locally on the Mac after the
runner stopped. They are archived as execution evidence, not as a scientific
result.

No P0, P1 or P2 scientific evaluation, locked test, training, calibration,
export or live operation was executed. The next action is external review of
this STOP 4 archive before any separate P0 authorization.
