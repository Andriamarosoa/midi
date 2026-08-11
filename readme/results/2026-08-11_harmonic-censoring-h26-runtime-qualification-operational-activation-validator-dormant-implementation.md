# H26 dormant runtime qualification operational activation validator

Date: 2026-08-11

## Scope

This commit implements only the dormant, in-memory validator authorized after
the external review closure at
`f0f18f54439a643c4b49f77ee6126449290a02db`. It does not issue, persist, or
activate any capability and does not inspect an operational filesystem or
runtime.

## Reviewed bindings

- activation contract: `d8d71bad9aee560d3406e672e7ebc6c2cf11dbff`
- activation contract Git blob: `c6eac6ae2d05b99a1a5b88594dea473739904dd8`
- activation contract Git byte length: `16050`
- activation contract raw SHA-256: `ad3fd1a381022a8f0e79af2a2656daf327d3ef857a86a0cb55a611cb41e83c01`
- external seal: `ce4aa59f75d3ff3836bce91c6be9739a16448199`
- external seal Git blob: `685915e6e15a760fb439089752402ccb29c142f7`
- approved seal loader: `37f5f2d502b4eae9d878c5c0f47155a7b26c856b`
- approved seal loader module blob: `feacb3c10c269b5f574e8d7efab8211be145b5d8`
- seal-loader review closure: `f0f18f54439a643c4b49f77ee6126449290a02db`

The validator verifies those public bindings and the actual loader module
blob, then obligatorily calls the approved external-seal loader. It rereads the
same corrected contract and verifies its blob, length, and raw SHA-256 before
extracting the closed activation rules.

## In-memory validation

The caller-supplied artificial activation must contain exactly the 26 fields
and exact field types defined by the sealed contract. Every fixed value is
enforced, including the contract commit/raw-SHA pair. `administrative_root` is
checked syntactically only as a canonical absolute non-root POSIX path. No
existence, symlink, permission, or filesystem check occurs.

The validator applies no additional semantics to `issued_at` or
`issuer_identity`: the sealed contract currently requires only strings. It
derives `activation_id` over the canonical 25-field payload with the exact
`H26_RUNTIME_QUALIFICATION_OPERATIONAL_ACTIVATION_ID_V1` domain separator,
rejects an incorrect caller-supplied ID, serializes the complete validated
object with the approved canonical codec, and returns a frozen result carrying
the canonical bytes and their external SHA-256.

## Validation

Permitted commands executed:

```text
python -B -m py_compile src/polyphonic/harmonic_censoring_h26_runtime_qualification_operational_activation.py tests/test_harmonic_censoring_h26_runtime_qualification_operational_activation_dormant.py
python -B -m unittest tests.test_harmonic_censoring_h26_runtime_qualification_operational_activation_dormant
```

Result: `10 tests`, all successful. They cover a valid artificial object,
missing/extra/type/fixed/binding failures, bad ID, deterministic ID/bytes/SHA,
invalid POSIX roots, contract-only issuer/time strings, public binding
mutation, mandatory seal-loader invocation, immutability, and absence of any
writer/issuer/capability/operational-filesystem surface.

No real activation, root, issuer, capability, runtime, NumPy, BLAS, `otool`,
materializer, P0/P1/P2, scientific data, or locked test was used.

## State

The validator remains dormant and awaits external review. Runtime activation
and every scientific or materialization action remain unauthorized.
