# H26 — operational runtime qualification entrypoint (STOP 2)

Status: `IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_RUNTIME_CONSUMPTION`.

The unique activation from STOP 2 remains intact and unused. This change adds
the missing real one-shot boundary without creating authority, claim,
observer-entry evidence, runtime record or receipt.

The no-argument macOS entrypoint binds exactly:

- activation ID `h26-runtime-activation-v1-61c06216bb264254573c6f13257b923fd34b31ca00693c59665f8d8bdbd43dde`;
- activation SHA-256 `f96a811b4d00e2a022c405d7e14b2b99d3af5028389536d03c0f7c9fce414fe2`;
- root `/Users/amcarene/h26-admin`;
- authority ID `h26-runtime-authority-v1-61c06216bb264254573c6f13257b923fd34b31ca00693c59665f8d8bdbd43dde`;
- authority timestamp `2026-08-12T12:30:00Z`;
- issuer `h26-execution-codex-mac-primary`;
- exact CPU/thread/locale/timezone environment from the sealed runtime contract;
- acknowledgement and authorization commit equal to clean `HEAD`.

Before the first write it validates the activation, contracts, complete
authority/claim/evidence chain and absence of every final/staging path under
the five pre-existing non-symlink directories. Publication is create-exclusive,
mode 0600, fsynced and no-replace. The sole order is authority, claim,
observer-entry evidence created inside the boundary, private capability-gated
real observer, runtime record, and terminal receipt last. If observation or
record publication fails after observer entry, an inconclusive terminal receipt
is written and the original error is re-raised; no cleanup or retry exists.
Only the deterministic evidence ID/path is derived during preflight. The
evidence object itself cannot be constructed until the durable claim exists and
a distinct identity-attested observer-entry capability has been minted.

Tests cover missing boundary, forged capability, exact publication order,
qualified record/receipt and the observer-failure terminal receipt using only
temporary directories and a fake observation. A Darwin-only test exercises the
real publication primitives while still replacing the actual observer.

No real observer, runtime consumption, materialization, P0/P1/P2, locked-test,
training or calibration was invoked by this implementation step.
