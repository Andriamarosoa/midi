# H26 — unique runtime activation issued (STOP 2)

Status: `ACTIVATION_ISSUED_STOP_BEFORE_RUNTIME_AUTHORITY_OR_OBSERVER`.

STOP 1 was externally approved for exact execution commit
`dee520da5be1eee849618fbf918c4135c21d54dc`. On the clean Mac checkout, the
administrative directories `/Users/amcarene/h26-admin` and
`/Users/amcarene/h26-admin/activation` were created as non-symlink mode-0700
directories. Both activation final and staging slots were confirmed absent.

The reviewed entrypoint was invoked exactly once with the literal
acknowledgement, authorization commit equal to `HEAD`, and canonical 26-field
activation bytes on stdin. It returned:

- activation ID:
  `h26-runtime-activation-v1-61c06216bb264254573c6f13257b923fd34b31ca00693c59665f8d8bdbd43dde`;
- activation SHA-256:
  `f96a811b4d00e2a022c405d7e14b2b99d3af5028389536d03c0f7c9fce414fe2`;
- byte length: `1735`;
- final path: `/Users/amcarene/h26-admin/activation/activation.json`;
- final mode: `0600`;
- staging path after publication: absent;
- issuer: `h26-execution-codex-mac-primary`;
- issued at: `2026-08-12T12:00:00Z`;
- retry allowed: `false`;
- maximum observer invocations: `1`.

A separate read-only load revalidated the exact canonical bytes, ID and digest.
No `active.lock` or H24/H25/H26 execution process was present afterward.

This is the mandatory STOP 2. No runtime authority, claim, observer-entry
evidence, `observe_primary_runtime`, runtime record/receipt, materialization,
P0/P1/P2, locked-test, training or calibration was created or invoked.
