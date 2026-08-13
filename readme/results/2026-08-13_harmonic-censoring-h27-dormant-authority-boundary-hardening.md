# H27 dormant authority-boundary adversarial hardening

Date: 2026-08-13

## Review input

External review of commit `38bba1111aea6b0669b56eec7ed3d3aaa16449fe`
returned `CHANGES REQUIRED`. The accepted mechanics were retained, while three
blocking issues were corrected:

1. capability bindings were adjacent fields rather than enforced attestation;
2. the returned Python `consume` closure exposed mutable `__code__` and closure
   cells;
3. nested `authority` or `claims` links could redirect writes outside the
   sandbox.

No operational or scientific scope was added.

## Corrected implementation identity

- path: `src/polyphonic/harmonic_censoring_h27_issuer_authority_claim_capability_dormant.py`
- Git blob before commit: `529eac42f89885254f431c859a7399cbba9091d2`
- size: `17333` bytes
- SHA-256: `f98fd0375a4e5645f4e6a211e144c89dfcba5ccfca372555a03e9e06fc06bb91`

## Binding hardening

The external capability attestation now returns one immutable binding that
contains and revalidates all required values:

- authority SHA-256;
- claim SHA-256;
- reviewed materializer Git blob;
- invocation nonce;
- process ID and pre-claim code identity SHA-256.

Changing any of the four contractual values in a copied/forged neighboring
structure no longer agrees with the immutable capability attestation.

## Native single-use boundary

The Python `consume` closure and its mutable `consumed` cell were removed.
Issuance now returns a read-only `MappingProxyType` containing only native
guards:

- `mappingproxy.__getitem__` for capability, process and code-identity
  attestation;
- one exact generator `__next__` method-wrapper for single-use consumption.

These callables expose neither `__code__` nor `__closure__`. The one-shot
iterator cannot be copied or pickled, its state cannot be reset, and concurrent
calls produce exactly one binding followed only by `StopIteration`.
`dataclasses.replace`, mapping assignment, capability forgery and forged
neighbor bindings are tested and rejected.

## Filesystem hardening

Before each open, the actual nested parent is checked with `lstat`, rejected if
it is a symlink or Windows reparse point, resolved strictly, and required to
remain below the already validated temporary sandbox root. Final-file symlinks
are rejected and `O_NOFOLLOW` is added when the platform provides it.

Real adversarial links are created for both `authority` and `claims`. On
Windows the test falls back to a real directory junction when ordinary symlink
creation is unavailable. Both cases fail before any file appears in the
outside destination; no test is skipped.

## Verification

- `15/15` focused dormant-boundary tests pass.
- `87/87` combined H27 tests pass in `2.807 s`.
- `py_compile` and `git diff --check` pass.
- No true H27 authority, claim, operational capability, activation,
  materializer call, NumPy science, plan, record, population/index, publication,
  training, calibration or locked-test exists.
- Runtime/live latency remains unchanged because no existing runtime imports
  this dormant module.

## State

`H27_DORMANT_AUTHORITY_BOUNDARY_HARDENED_PENDING_EXTERNAL_REVIEW`

The next action is review of this exact corrective commit and module identity.
Operational sealing, activation and science remain outside this scope.
