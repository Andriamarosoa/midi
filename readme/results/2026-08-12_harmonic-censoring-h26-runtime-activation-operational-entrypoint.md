# H26 — operational activation entrypoint (STOP 1)

Status: `IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_ACTIVATION_CREATED`.

The reviewed dormant planner and publisher now have a narrow macOS boundary.
The fixed administrative root is `/Users/amcarene/h26-admin`, the issuer is
`h26-execution-codex-mac-primary`, and the pre-registered issuance timestamp is
`2026-08-12T12:00:00Z`. The command accepts no arguments and consumes only the
exact canonical 26-field activation bytes on stdin.

Before parsing the request it requires Darwin, a literal acknowledgement, an
external authorization commit equal to clean `HEAD`, and no caller-selected
paths. Publication uses an already-existing non-symlink root, an exclusive
0600 staging write, fsync, Darwin `renameatx_np(RENAME_EXCL)`, and directory
fsync. Collision or partial failure is terminal; cleanup and retry are absent.

This step stopped before root creation and before invocation. No activation,
runtime authority, claim, observer evidence, runtime record, materialization,
P0/P1/P2, locked-test, training, or calibration exists or ran.
