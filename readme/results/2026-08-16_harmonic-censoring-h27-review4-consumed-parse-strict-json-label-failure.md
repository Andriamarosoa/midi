# H27 Review 4 — échec consommé sur l'appel strict JSON

## Autorisation et bootstrap r2

La revue externe des commits A `245ff1436ec6ecfbeb23b7aa962016dc098482b1`
et B `e05f94cc0e0a3667579b38a0128f493633f5be7e` a rendu `PASS` pour
une reprise Mac immutable unique sous `review4-runner-r2`.

Le bloc SSH a passé tous les contrôles read-only requis : runtime exact via le
venv existant, HEAD cible détaché et propre, trois artefacts materializer
historiques byte-exacts, parents admin valides et cinq destinations absentes.
Il a ensuite créé exclusivement `review4-runner-r2` en `0700` et ses trois
artefacts en `0400` :

```text
R2_CREATED_VERIFIED h27_review4_execute_once.py 26857 6d7a4ade... ae7d5359...
R2_CREATED_VERIFIED harmonic_censoring_h27_review4_execution_composition_identity_binding.json 5955 cba1f35b... 816ce4f2...
R2_CREATED_VERIFIED harmonic_censoring_h27_review4_execution_composition_external_seal.json 1640 e7b1ce4c... 0874fcaf...
H27_REVIEW4_R2_BOOTSTRAP_AND_RUNTIME_PREFLIGHT_PASS_BEFORE_ACK
```

## Frontière consommée

Après ACK, le runner r2 a été invoqué exactement une fois. Contrairement aux
arrêts précédents, il a terminé `preclaim()`, puis `consume_and_run()` a créé le
fichier AUTHORITY via `O_CREAT|O_EXCL`, créé CLAIM de la même manière et consommé
la paire capability/binding avant d'appeler le matérialiseur. La frontière
one-shot est donc définitivement franchie.

## Erreur terminale

Le matérialiseur a consommé l'attestation, importé NumPy, puis appelé le loader
du plan. Le runner avait remplacé `_bound_json` par :

```python
return contract.parse_strict_json(frozen_inputs[path])
```

mais le contrat scellé définit :

```python
def parse_strict_json(raw: bytes, label: str) -> dict[str, object]:
```

L'exécution a donc terminé `rc=1` :

```text
TypeError: parse_strict_json() missing 1 required positional argument: 'label'
LOCAL_SSH_RC=1
```

## Portée

Le plan n'a pas été construit et `_publish()` n'a pas été atteint. Aucun rendu,
staging, population finale, index, terminal, P0/P1/P2, entraînement ou
locked-test n'a été exécuté. L'import NumPy a toutefois eu lieu après la
consommation administrative.

Conformément au contrat, aucun retry, suppression, remplacement, chmod,
réparation ou seconde invocation n'est effectué. AUTHORITY, CLAIM,
`review4-runner-r2` et tous les artefacts persistants doivent rester intacts.
La suite exige une revue externe de cet échec consommé; elle ne peut pas être
une nouvelle tentative H27 Review 4 sous la même activation.
