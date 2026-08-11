# H26 — validateur dormant de preuve runtime pour la matérialisation

Date : 2026-08-11

## Portée autorisée

```text
AUTHORIZED_TO_IMPLEMENT_H26_DORMANT_POPULATION_MATERIALIZATION_RUNTIME_EXECUTION_PROOF_VALIDATOR_ONLY
```

Parent exact :

```text
84d1a196635c6ace7f3ea5ec9b7e338f5da70300
```

Cette étape ajoute uniquement une primitive pure de validation et ses tests
artificiels. Elle ne crée ni issuer, authority, claim, evidence, receipt,
runtime record, capability, destination ou fichier opérationnel.

## Bindings fail-closed

Le nouveau module lie exactement :

```text
contrat de matérialisation corrigé       84d1a196635c6ace7f3ea5ec9b7e338f5da70300
blob du contrat corrigé                  94f255c583a52d660dc57f70df80b97173791296
validateur terminal receipt              09ef74cd537392d76eab1ed09082bf04e0214f16
blob du validateur terminal              9721a41eca9e3f2bfa1ef8150ff39bf34ccf5fce
qualificateur runtime                    25a08630d6ad99d5e3432a277b99b9603990458a
blob du qualificateur                    ef24d9ebdc4ae834b3b872175fb7e098330a68bf
clôture de validation                    b1b13048efeb73b468cb7fbb0f1ccff4c00ff0d0
blob du rapport de clôture               f26262b28e9d00e5d5c270461dd72c04e16bbaf9
```

Le loader relit le contrat corrigé, calcule son blob Git sur les octets texte
LF canoniques, refuse les clés JSON dupliquées et les nombres flottants, puis
vérifie les bindings de pile, les champs de preuve requis, les contraintes du
receipt et les onze frontières dormantes. Les blobs des sources du validateur
terminal, du qualificateur et du rapport de clôture sont également vérifiés.

## Primitive pure

```python
validate_artificial_materialization_runtime_execution_proof(...)
```

Elle reçoit exclusivement en mémoire une authority, un claim consommé, une
preuve d'entrée observer, un receipt terminal, leurs SHA externes et un runtime
record artificiel. Elle réutilise obligatoirement :

```python
validate_artificial_terminal_execution_receipt(...)
```

Après la revalidation terminale, elle exige en plus :

```text
receipt.runtime_record_exists = true
receipt.terminal_status = H26_MATERIALIZATION_RUNTIME_QUALIFIED
receipt.runtime_record_raw_sha256 = SHA du record resérialisé et revalidé
receipt_raw_sha256 = SHA des octets canoniques exacts du receipt
```

Le retour est une dataclass `frozen=True` contenant exactement les neuf champs
runtime-proof destinés à une éventuelle future authority de matérialisation.
Ce retour n'est pas une authority et ne porte aucune destination, capability ou
identité d'issuer.

## Validation synthétique autorisée

```text
py_compile                                     OK
nouveau test dormant                           9/9 OK
durée unittest                                 0,157 s
```

Les tests couvrent : preuve QUALIFIED exacte, projection immutable, appel
unique du validateur terminal, refus DISQUALIFIED/INCONCLUSIVE, receipt sans
record, faux SHA receipt/record, authority/claim/evidence falsifiés, contrats
ou blobs redirigés, octets alternatifs du contrat, absence de fichier créé et
absence d'import du materializer.

## Frontière inchangée

Aucun NumPy, BLAS, `otool`, observer, materializer, P0, P1, P2, waveform,
population, donnée réelle, modèle, entraînement, calibration ou locked-test n'a
été exécuté. Aucune qualification runtime réelle ni autorité réelle n'est
permise par cette implémentation dormante.

Une revue externe est obligatoire avant toute autre portée.
