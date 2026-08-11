# H26 dormant operational activation issuance contract

Date: 2026-08-11

## Scope

This declarative contract closes the future issuance rule only. It creates no
issuer, activation, capability, administrative root, path, or scientific
execution.

The contract binds the approved activation contract and seal, the approved
seal loader, the approved in-memory activation validator, and its review
closure through `fe36943c57a4d7e088f95004308d742c49e82008`.

## Future rule

At most one complete 26-field activation may be presented to the approved
validator. The activation itself is the single-use capability; no separate
capability object exists. The caller-supplied ID is validated, never repaired
or regenerated. Only the canonical bytes returned by the validator may be
published, and their SHA-256 remains external to the activation.

The future issuer identity is a nonempty bounded ASCII token with an exact
regex, but no issuer is selected now. The future timestamp is canonical
Gregorian UTC at whole-second precision, but no clock is read now. The future
administrative root is a canonical absolute non-root POSIX string, but no
filesystem is consulted now.

Future publication is a single fixed slot beneath the validated root, using a
create-exclusive staging write, durability sync, and atomic no-replace rename.
A collision or partial write consumes that attempt and permits no suffix,
replacement, cleanup, fallback, or retry.

## Current state

Only `issuance_contract_exists` is true. Issuer, activation, capability, root,
authority, claim, observer invocation, runtime execution, materialization,
P0/P1/P2, science, and locked-test remain absent, false, or null.

No source or test file was added or changed, and no operational or scientific
command was executed for this contract-only step.
