# H26 activation issuance contract external seal

Date: 2026-08-11

This declarative seal binds the issuance contract at commit
`2f933536fb40603e8a4f2b7c6e9810ec0e0d366a`, Git blob
`05ec1c26edbd36cdf6d127f7e8361596f9a20958`, exact Git-blob length `5624`,
and raw SHA-256
`e15dcb79da60a5e22a9d0f76c30786b05b90fbefc7e0b71f32a3cbe74052dbe7`.

Length and SHA-256 were calculated over exactly the bytes returned by
`git cat-file blob 05ec1c26edbd36cdf6d127f7e8361596f9a20958`. Neither the seal nor the
issuance contract contains its own raw SHA-256.

Only the issuance contract exists. Issuer, activation, capability,
administrative root, authority, claim, runtime execution, materialization,
P0/P1/P2, science, and locked-test use remain absent, false, or null.
`creation_authorized_now=false`; this seal creates and authorizes nothing.
