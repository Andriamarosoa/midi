# H26 dormant runtime activation external-seal loader

Date: 2026-08-11

## Scope

This change implements only the dormant loader authorized after external
approval of commit `ce4aa59f75d3ff3836bce91c6be9739a16448199`. It does not
create an activation, issuer, capability, authority path, runtime record,
receipt, materialization, or scientific execution.

## Exact bindings

- external seal commit: `ce4aa59f75d3ff3836bce91c6be9739a16448199`
- external seal Git blob: `685915e6e15a760fb439089752402ccb29c142f7`
- corrected activation contract commit: `d8d71bad9aee560d3406e672e7ebc6c2cf11dbff`
- corrected activation contract Git blob: `c6eac6ae2d05b99a1a5b88594dea473739904dd8`
- corrected activation contract Git byte length: `16050`
- corrected activation contract raw SHA-256: `ad3fd1a381022a8f0e79af2a2656daf327d3ef857a86a0cb55a611cb41e83c01`

The loader checks the seal Git blob before parsing. It then requires the exact
closed seal object, including the schema, status, two false self-SHA flags,
`creation_authorized_now=false`, and the complete dormant current state with
`observer_invocation_count=0`.

The bound contract is reread from disk. The only permitted checkout
normalization is CRLF to Git LF. Its Git blob, canonical length, and raw
SHA-256 must all match the reviewed values before the contract schema and
dormant runtime flag are inspected.

## Validation

The new dedicated test module covers:

- exact seal and contract acceptance;
- altered seal bytes rejected before JSON parsing;
- schema, version, status, current-state, self-SHA, and creation mutations;
- false contract blob, SHA, and byte-length bindings;
- altered contract bytes;
- CRLF checkout convergence to reviewed Git bytes;
- public binding mutation;
- immutable result, no file creation, and no operational API surface.

Commands executed:

```text
python -B -m py_compile src/polyphonic/harmonic_censoring_h26_runtime_qualification_operational_activation_contract_seal.py tests/test_harmonic_censoring_h26_runtime_qualification_operational_activation_contract_seal_dormant.py
python -B -m unittest tests.test_harmonic_censoring_h26_runtime_qualification_operational_activation_contract_seal_dormant
```

Result: `8 tests`, all successful. No scientific data, model, NumPy runtime,
BLAS inspection, `otool`, materializer, activation, or locked test was used.

## State

`creation_authorized_now=false`. External review of this dormant loader is the
only next action. Runtime execution and science remain unauthorized.
