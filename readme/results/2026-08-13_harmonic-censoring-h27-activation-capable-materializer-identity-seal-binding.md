# H27 activation-capable materializer identity seal and binding

Date: 2026-08-13

## Scope

This change performs only the externally authorized sealing and contractual
identity binding of the already reviewed H27 activation-capable production
materializer. It does not modify the reviewed Python module, the dormant
scientific logic, the historical activation contract, or the historical
authority contract.

No issuer, authority artifact, capability, claim, activation, NumPy science,
population, population index, training, calibration, locked-test access, or
materialization is created or authorized.

## Externally reviewed implementation

- reviewed commit: `e47effd1ac10987242b537f5b54a9cfbed84faeb`
- reviewed parent: `c1871e67a9aac441ec1df9f654b1a1a3b28f17d3`
- verdict: `PASS`
- path: `src/polyphonic/harmonic_censoring_h27_activation_capable_production_materializer_dormant.py`
- Git blob: `79f399359e366781f9526098c98a93cca71b1b49`
- size: `32243` bytes
- SHA-256: `02bf7e9a8e7d0e8f292adb7b00742c83c19ab56eb89e35adc5da9c1c3144ff70`

## New sealed artifacts

### Materializer external-review seal

- path: `configs/harmonic_censoring_h27_activation_capable_production_materializer_external_review_seal.json`
- Git blob: `d5b852e63676b59a75b938ef17c51f9247dd5e68`
- size: `3057` bytes
- SHA-256: `68751aede0f11ce04763eb7398f4c071db91310c62c9a58c11667b908b58f95f`

### Identity-binding contract

- path: `configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding.json`
- Git blob: `a32721107c1ff65697661cfa7a2a235811884fc6`
- size: `4609` bytes
- SHA-256: `a752721a022433ac1d9fddccb29b9e56cbd5c1bc0566762ca50acd2f9b01a9fc`

### Identity-binding external seal

- path: `configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding_external_seal.json`
- Git blob: `be17bda1d7da5144758606ed4b4f1b56708ebf3d`
- size: `1760` bytes
- SHA-256: `a7aa1f6d844fb25e2f633db8bd2817f6741bfe194418985c8419bda64573b3be`

## Binding semantics

The binding is an acyclic overlay. The historical contracts remain
byte-identical. It replaces only the historical future-materializer identity
slots with the exact reviewed implementation and external-review seal. All
other activation, runtime, environment, input, count, destination, one-shot,
and scientific semantics are inherited unchanged.

The reviewed module constants remain `None`, and its public production entry
remains the dormant native barrier. Therefore the binding cannot itself be
used as an activation artifact or execution path.

## Verification

- `72/72` H27 tests passed in `2.287 s`, including `8` new identity-binding
  tests.
- The reviewed implementation was compared byte-for-byte with `git show` at
  commit `e47effd1...`.
- The new tests independently recompute Git blob IDs, byte sizes, and SHA-256
  values for every bound artifact.
- Canonical UTF-8/LF JSON, absence of BOM/CR, absence of self-hashes, dormant
  constants, and all false operational/scientific states are asserted.
- `locked_test_used=false`.

## State and next boundary

State:
`H27_REVIEWED_MATERIALIZER_IDENTITY_BOUND_AND_SEALED_DORMANT_PENDING_EXTERNAL_REVIEW`.

The next action is external review of this exact contract-only commit. No
issuer, authority, capability, claim, activation, materialization, or science
may be implemented or executed without a separate explicit authorization.
