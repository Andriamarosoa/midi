# H26 - seal externe du contrat dormant d'activation runtime

Date : 2026-08-11

## Portee

Ce commit ajoute uniquement un seal externe declaratif des octets exacts du
contrat d'activation operationnelle H26 corrige et sa documentation. Il ne cree
aucune activation, issuer, capability, racine, authority, claim, evidence,
record, receipt ou execution.

Parent exact : `d8d71bad9aee560d3406e672e7ebc6c2cf11dbff`.

## Octets scelles

Les valeurs ont ete calculees directement sur les octets retournes par :

```text
git cat-file blob c6eac6ae2d05b99a1a5b88594dea473739904dd8
```

Resultat exact :

```text
activation contract commit
d8d71bad9aee560d3406e672e7ebc6c2cf11dbff

activation contract Git blob
c6eac6ae2d05b99a1a5b88594dea473739904dd8

exact Git-blob byte length
16050

raw SHA-256 of those exact 16050 bytes
ad3fd1a381022a8f0e79af2a2656daf327d3ef857a86a0cb55a611cb41e83c01
```

Les octets se terminent par un unique LF. Le seal ne contient pas son propre
SHA et le contrat scelle ne contient pas davantage son propre SHA.

## Etat dormant

```text
activation_exists=false
issuer_exists=false
capability_exists=false
administrative_root=null
runtime_authority_exists=false
claim_exists=false
observer_entry_evidence_exists=false
observer_invoked=false
observer_invocation_count=0
runtime_record_exists=false
receipt_exists=false
runtime_execution_authorized=false
materialization_authorized=false
scientific_execution_authorized=false
locked_test_used=false
```

Aucun validateur d'activation, issuer, capability, filesystem, runtime,
NumPy/BLAS/otool, materializer ou calcul scientifique n'est autorise par ce
seal. La prochaine action est uniquement sa revue externe.
