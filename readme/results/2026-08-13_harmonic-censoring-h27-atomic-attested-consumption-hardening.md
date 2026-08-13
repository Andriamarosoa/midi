# H27 atomic attested-consumption hardening

Date: 2026-08-13

## Review input

External review of commit `8812091656e2f5921f8bf51adcb0fcf1de8d7538`
returned `CHANGES REQUIRED`. The filesystem confinement and durable one-shot
mechanics remained valid, but two composition/reflection defects were found:

1. `consume_once()` could advance the one-shot state without invoking the
   separately exposed capability, process and code guards;
2. each `MappingProxyType.__getitem__` guard exposed a proxy whose backing
   dictionary could be recovered and modified through `gc.get_referents`.

No operational or scientific scope was added by this correction.

## Corrected implementation identity

- path: `src/polyphonic/harmonic_censoring_h27_issuer_authority_claim_capability_dormant.py`
- Git blob before commit: `ec61eef88dce7591fd411af230568b1e1d44d62e`
- size: `18915` bytes
- SHA-256: `d3d06f8c087845089094ff71f29d8745581d391784b9bbc40abeb57b0ba42f2f`

## Indivisible attestation and consumption

The four neighboring operations were removed. Issuance exposes one exact
native `generator.send` method-wrapper. Its single state transition requires:

- the exact process-local capability object by identity;
- the exact immutable `_CapabilityBinding` object by identity;
- the current PID to equal the PID sealed in that binding;
- a fresh SHA-256 of the issuer code bytes to equal the pre-claim code identity.

The generator captures only native `os.getpid/open/read/close` and SHA-256
callables plus immutable path/flag values. It does not retain a Python lambda or
other mutable identity-reader closure. The identity file is reopened with
`O_NOFOLLOW` where available during the atomic transition.

The binding itself contains authority SHA-256, claim SHA-256, reviewed
materializer Git blob, invocation nonce, PID and code identity SHA-256. Only
after every condition succeeds does the same transition yield that exact
binding. A wrong capability, neighboring forged binding, PID drift or code
drift terminates the generator and leaves no retry path. Successful concurrent
calls still produce exactly one winner.

## Reflection resistance

The issuance session is now an immutable native tuple, not a mapping proxy.
No capability/process/code allowlist dictionary exists. The exposed consumer
has neither `__code__` nor `__closure__`; its generator cannot be copied,
pickled or reset. Tests use `gc.get_referents` against the session, consumer and
generator and confirm that there is no authority dictionary to recover or
modify. A forged capability remains rejected after that real reflection
attempt, and the failed attempt is terminal.

## Preserved filesystem hardening

The existing `lstat`/reparse checks, strict parent resolution, sandbox
containment, final-target symlink refusal, `O_NOFOLLOW` where available,
`O_CREAT | O_EXCL | O_WRONLY`, mode `0600`, file and parent fsync, interruption
tests and real nested authority/claims symlink or junction escape tests remain
unchanged and passing.

## Verification

- `16/16` focused dormant-boundary tests pass.
- `88/88` combined H27 tests pass in `3.053 s` using the project virtualenv.
- The tests include atomic capability/binding/PID/code checks, terminal failure,
  `gc.get_referents`, forged session neighbors, copy/pickle/reflection,
  concurrency and both real nested filesystem redirects.
- No true H27 authority, claim, operational capability, activation,
  materializer call, NumPy science, plan, record, population/index, publication,
  training, calibration or locked-test exists.
- Runtime/live latency remains unchanged because no existing runtime imports
  this dormant module.

## State

`H27_DORMANT_ATOMIC_ATTESTED_CONSUMPTION_PENDING_EXTERNAL_REVIEW`

The next action is external review of this exact corrective commit and module
identity. Operational sealing, activation and science remain outside scope.
