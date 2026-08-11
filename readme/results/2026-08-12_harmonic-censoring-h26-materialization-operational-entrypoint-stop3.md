# H26 — operational materialization entrypoint after STOP 3

Status: `IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_MATERIALIZATION`.

This additive boundary binds the five qualified STOP 3 artifacts by exact path
and SHA-256, reconstructs their canonical runtime record, and requires the
approved proof validator to return `H26_MATERIALIZATION_RUNTIME_QUALIFIED`.
It has no caller-provided destination, authority, proof, materializer or
configuration.

The checked-in lifecycle is enforced rather than descriptive: while
`real_execution_authorized=false`, the entrypoint fails before runtime-artifact
access. A later separately reviewed authorization commit must switch the exact
status/authorization/next-action triple to its only accepted one-shot state.

The future no-argument macOS entrypoint fixes the destination to
`/Users/amcarene/h26-admin/population/h26-synthetic-v1`, issuer to
`h26-execution-codex-mac-primary`, and issued time to
`2026-08-12T13:00:00Z`. It requires acknowledgement, authorization commit equal
to clean HEAD, the exact qualified runtime environment, no worker lock, and
absent destination/staging/authority/seal slots.

The canonical 36-field materialization authority is derived exclusively from
the sealed fixed values and the single validated STOP 3 proof. Authority and
its distinct five-field seal are create-exclusive. Only after durable authority
publication can an identity-attested private boundary reach the unchanged
reviewed materializer. Its internal adapter is not caller injectable, accepts
one exact private capability, is process-locked, and is restored in `finally`.
The final staging rename uses Darwin `renameatx_np(RENAME_EXCL)` rather than an
overwriting rename.

Nine focused tests use temporary directories and a patched internal
materializer call. They cover canonical contract bytes, the pending-review
STOP, missing acknowledgement after a future authorization, exact fixed
publication, pre-existing-slot refusal before publication, forged boundary,
adapter restoration after failure, post-mint authority tamper refusal, and
runtime-artifact SHA mismatch. All 22 H26 test modules also pass when run in
their intended isolated processes. No real authority, seal, destination,
population, P0/P1/P2, locked test, training or calibration was created or
invoked.
