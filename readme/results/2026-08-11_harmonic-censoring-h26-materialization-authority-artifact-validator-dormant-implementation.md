# H26 - implementation dormante du validateur d'artefact d'autorite

Date : 2026-08-11

## Portee

Cette etape implemente uniquement un validateur pur en memoire du futur
artefact d'autorite de materialisation H26. Elle ne cree aucun issuer,
authority, seal, claim, slot, destination, runtime record, population ou
execution scientifique.

Le parent contractuel exact est le commit
`dd24346e6bf6f50af13e10f8c5ca5d1281242088`; son contrat JSON est lie au blob
Git `b6b98b4cb205cb6c2f1c49e6f07b121e1e6b45f8`.

## Comportement implemente

Le module
`src/polyphonic/harmonic_censoring_h26_materialization_authority_artifact.py` :

- charge strictement le contrat dormant exact avant toute validation;
- reutilise le loader du seal approuve `88593f7f...` / `39316388...`;
- reutilise obligatoirement le validateur de preuve approuve
  `18b8d5a7...` / `fd5e40fb...`;
- exige exactement 36 champs, leurs types exacts et les 24 valeurs fixes;
- compare les neuf champs runtime a une seule projection artificielle
  completement validee et terminale `QUALIFIED`;
- valide uniquement la syntaxe de la destination POSIX, sans la consulter;
- valide la date UTC gregorienne et l'identite ASCII de l'issuer;
- rederive l'`authority_id` par la preimage domain-separated prescrite;
- produit les octets JSON canoniques et leur SHA-256 uniquement en memoire;
- retourne un resultat immutable.

Le module ne propose aucune factory d'autorite, aucun writer et aucun seal.

## Validation locale autorisee

Commandes executees :

```text
python -m py_compile src/polyphonic/harmonic_censoring_h26_materialization_authority_artifact.py tests/test_harmonic_censoring_h26_materialization_authority_artifact_dormant.py
python -m unittest tests.test_harmonic_censoring_h26_materialization_authority_artifact_dormant
```

Resultat : `18 tests` reussis. Les cas couvrent l'autorite valide, l'identite et
les octets deterministes, les champs absents/supplementaires, types et valeurs
fixes incorrects, ID forge, preuve mixte/forgee/non qualifiee, syntaxe de
destination, date gregorienne, issuer, SHA reproductible et absence d'effet
filesystem sur la destination.

`git diff --check` et le controle de portee restent requis avant commit.

## Etat terminal de cette etape

```text
validator_exists=true
authority_issuer_exists=false
materialization_authority_exists=false
external_authority_seal_exists=false
materialization_claim_exists=false
absolute_destination_bound=false
runtime_execution_authorized=false
materialization_authorized=false
materialization_executed=false
population_exists=false
scientific_execution_authorized=false
real_data_used=false
model_used=false
training_used=false
calibration_used=false
locked_test_used=false
```

La prochaine action autorisee est uniquement la revue externe de ce validateur
dormant. Toute emission, persistance ou execution requiert une autorisation
separee.
