# H27 dormant issuer / authority / claim / capability boundary

Date: 2026-08-13

## Authorized scope

The external reviewer gave `PASS` to commit
`0a39763a9002b41df1750a0c2cb322033962b4fc` and authorized only a dormant,
adversarial implementation of the future issuer/authority/claim/capability
boundary. This lot implements that boundary without creating any operational
H27 artifact or connecting it to the production materializer.

## Implementation

- path: `src/polyphonic/harmonic_censoring_h27_issuer_authority_claim_capability_dormant.py`
- Git blob before commit: `2d42c457e9557a8b78cc8625501cd06038294478`
- size: `15977` bytes
- SHA-256: `7f26d58e63d867ced39d0b79eb5ababff519f120d07b23098b4ab2dd81e981f0`

The module loads and attests the exact reviewed identity binding, its seal, the
materializer seal, the materializer blob, and the historical activation and
authority contracts/seals. It then provides deterministic construction and
validation of a non-operational authority template.

The public operational entry is exactly the immutable native dormant barrier
`().__getitem__`. The only executable lifecycle is private and restricted to a
dedicated `h27-dormant*` directory below the system temporary directory. It
explicitly rejects the real `/Users/amcarene/h27-admin` boundary.

## Exercised mechanics

The sandbox lifecycle exercises, without production data:

- deterministic canonical UTF-8/LF authority bytes;
- fixed issuer, namespace, five inputs, runtime, environment, counts and
  destinations derived from the sealed activation contract;
- authority then claim creation with `O_CREAT | O_EXCL | O_WRONLY` and mode
  `0600`;
- file fsync and parent-directory fsync call boundaries;
- durable claim persistence after claim-file or parent-fsync interruption;
- exact invocation nonce binding;
- process-local identity attestation stored in a closure rather than a mutable
  module registry;
- nonconstructible, noncopyable and non-pickleable sandbox capability;
- atomic single-use consumption under concurrent callers;
- forged-object and wrong-process rejection;
- post-claim code identity drift as a terminal failure after consumption.

The sandbox capability is not an instance of
`H27ActivationCapableProductionMaterializationCapability`; it cannot open the
production materializer.

## Verification

- `13/13` focused dormant-boundary tests pass.
- `85/85` combined H27 tests pass in `2.553 s`.
- `py_compile` passes.
- `git diff --check` passes.
- No production administrative path, H27 population path, plan, NumPy
  scientific input, waveform, payload or locked-test was accessed.
- No latency-bearing inference or live path changed; latency impact is zero for
  the unchanged runtime because this new module is not imported by it.

## Current state

`H27_ISSUER_AUTHORITY_CLAIM_CAPABILITY_DORMANT_IMPLEMENTED_PENDING_EXTERNAL_REVIEW`

Still absent and forbidden: real authority, real claim, operational capability,
activation, materializer invocation, NumPy science, 124-record population,
index, staging/final publication, training, calibration and locked-test.

The next action is external review of this exact implementation identity. A
later seal or operational activation requires a new explicit authorization.
