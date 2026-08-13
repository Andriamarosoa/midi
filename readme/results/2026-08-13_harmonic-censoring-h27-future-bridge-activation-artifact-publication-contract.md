# H27 future activation-artifact publication contract

Date: `2026-08-13`

## Scope

Declarative contract and external seal only for a future atomic, exclusive
publication of the already reviewed in-memory activation payload. No Python
implementation, destination, artifact, filesystem write, connection,
authority, claim, capability, materializer invocation or science exists.

## Reviewed predecessor

The externally reviewed administrative module lot is commit
`309b93153ee4df7a17ae13a85b70532c0a426a69`, with verdict `PASS`.

The new contract directly binds:

- the reviewed dormant activation-artifact module;
- its external-review seal;
- its acyclic identity binding;
- the external seal of that binding;
- the four prior activation-artifact artifacts;
- the thirty-six gate, activation/connection, bridge, compatibility and
  predecessor entries.

All forty inherited dependencies remain byte-exact.

## New identities

Publication contract:

- blob: `d402672653b9e532db0ea302e5e314dfa1e5c4e3`
- size: `22288` bytes
- SHA-256: `82b10aaed4161f189959b9ff85ed43ccabe5a1cf2b344b9ba7ec8909c1fa84f2`

Contract external seal:

- blob: `28a2e397c50f3f7eac79a652d0c786443295f01e`
- size: `3628` bytes
- SHA-256: `148829dfc1c9f8923a3ee0d3cd603476ae00bd10fbb191df2b166e8274f22db7`

## Fail-closed publication definition

The contract requires all identities and six closed public barriers to be
verified before any future write. It also requires unique activation identity,
valid RFC3339 UTC, absent destination, one-shot consumption immediately before
the first write, create-exclusive/no-overwrite semantics, full canonical byte
write and fsync, same-filesystem atomic visibility without replacement,
post-publication reopen/rehash, parent-directory fsync and terminal no-retry on
partial or failed publication.

These are declarative requirements only. No publication implementation or
destination is present or authorized.

## Validation

- JSON syntax validation passed for contract and seal.
- `9/9` dedicated administrative tests passed.
- The contract test rehashes four dormant-module artifacts plus forty inherited
  dependencies.
- The six public edges remain native empty-tuple `().__getitem__` barriers.
- `locked_test_used=false`.

## State

The contract awaits external review. Publication implementation, artifact,
write permission, both connections, execution path, materializer, science,
training and calibration remain false.
