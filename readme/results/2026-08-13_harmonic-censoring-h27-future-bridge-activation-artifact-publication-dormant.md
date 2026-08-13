# H27 dormant activation-artifact publication simulator

Date: `2026-08-13`

## Scope

Distinct dormant Python module with a private synthetic harness only. It does
not expose a filesystem publication function: its public edge is a native
empty-tuple barrier. No destination, artifact, write, connection, authority,
claim, capability, materializer invocation or science exists.

## Reviewed authorization basis

The publication-contract identity binding at commit
`c74ecdb808283a42fff55dad5f10aa87354182c9` received external `PASS`.
That review authorized only this in-memory simulation module.

## Module identity before commit

- Git blob: `13af087b6a60d696430ff73d3fb41e111e55a8a3`
- size: `12031` bytes
- SHA-256: `48dbeb587cc514b5f6dafadbc049183650ae9b9a38dce497f3c6aac70cc72851`

## Synthetic lifecycle

Before any adapter/mock, the harness rehashes 48 unique sealed inputs:

- four publication contract/binding artifacts;
- four reviewed dormant activation-artifact module artifacts;
- four activation-artifact, four gate, four activation/connection, four
  bridge, four compatibility and twenty predecessor artifacts.

It then validates the exact 14-field canonical payload, 21 fail-closed
preconditions, RFC3339 UTC, activation-id uniqueness and destination absence.
The local right is consumed immediately before the first publication
simulation. Create-exclusive, file flush/fsync, same-filesystem atomic
visibility without replace, reopen/rehash and parent-directory fsync are
separate injected simulations and must all report that no real action occurred.

Success reports artifact_created/written=false, both connections=false,
materializer/science=0 and terminal=true. Any failure after consumption also
makes retry impossible.

## Validation

- `py_compile`: pass.
- `8/8` dedicated synthetic/adversarial tests pass.
- all 48 identities are counted uniquely and rehashed before adapters.
- invalid payload/time/digest, missing uniqueness, present destination and any
  simulated real effect fail closed.
- success second call and post-consumption failure retry are rejected.
- all seven public edges remain native `().__getitem__` barriers.
- source contains no `os.open`, `O_EXCL`, `write_bytes`, NumPy or locked-test.

The module awaits external review. It authorizes no real publication or later
phase.

## External-review correction

The external review of commit `84c46f1f834efd4a4fed579dd9f5dbd696d24135`
returned `FAIL` on one bounded schema mismatch: the publication simulator
accepted arbitrary syntactically valid gate/materializer identities and did
not validate `invocation_nonce` as lowercase 64-hex. The corrected harness now
requires the exact reviewed gate blob, exact gate identity-binding SHA-256 and
exact materializer blob already imposed by the sealed activation-artifact
schema. It also validates `invocation_nonce` as lowercase 64-hex.

Dedicated adversarial cases reject a substituted gate blob, gate binding,
materializer blob, and malformed nonce before the one-shot ticket is consumed.
The 48-input rehash order, 21 preconditions, seven closed public edges and all
no-effect/terminal guarantees are unchanged. This correction still performs no
filesystem operation or science and awaits a new external review.

Post-correction verification: `py_compile` passes, `git diff --check` passes,
the dedicated suite passes `9/9` in `0.431 s`, and the full H27 suite passes
`259/259` in `41.505 s`. `locked_test_used=false`.
