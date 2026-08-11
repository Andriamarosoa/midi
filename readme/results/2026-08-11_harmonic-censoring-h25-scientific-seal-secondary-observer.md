# H25 — seal scientifique et observer secondaire dormants

## Portée

Ce commit applique uniquement l'autorisation externe :

```text
AUTHORIZED_TO_DEFINE_AND_COMMIT_H25_SCIENTIFIC_EXECUTION_AUTHORIZATION_SEAL_AND_DORMANT_SECONDARY_RUNTIME_OBSERVER_PAYLOAD_ONLY
```

Il ne crée aucune activation, aucun binding OS, aucune capability et aucun
claim. L'observer secondaire n'a pas été exécuté et la population publiée n'a
pas été ouverte pendant cette étape.

## Autorité scientifique liée

Le seal conserve exactement les blobs du commit d'autorité approuvé :

```text
reviewed authority commit  496331664023d505588a1bfcf0dd4a0c3ad01e77
authority blob             c907dcc4cd18289dccdd324570b51e797ee35d30
runner blob                2468d6ac73ce37a645d08d75441a9a08689a8b4c
engine blob                171602b54a8023e2c85c128aca14ec053da176ad
recomputer blob            25c6abaf220ff52913e233bdc21719e8e18bb637
```

Il lie aussi le contrat de capability courant, les trois SHA de la population
H25 publiée et la qualification administrative :

```text
population index       814d8c368ac67ce65ed20c9e90e634ceffe706db1cc5e642cc3c61ff37ab5f53
runtime provenance     cadc154a84674f6e58cf412d71f73407d0c07388f3bf470fa2368a1b810825db
population receipt     dbab85910151ce25c186f478797c86604a94e6cf486dda7e0c4b7b8eeb4fddd9
admin qualification    54bd361a99223dd24d6e4f0883ace47572965604c406efe69e5564f675d14ee1
```

## Observer secondaire

La commande future est fermée et sans argument :

```text
/Users/amcarene/midi-worker/.venv/bin/python
/Users/amcarene/midi-worker/repository/src/polyphonic/harmonic_censoring_h25_secondary_runtime_observer.py
timeout 120 s
```

Le seal enregistre CPython `3.11.9`, Darwin `24.5.0`, arm64, le chemin résolu
du binaire et ses octets :

```text
executable size  152624
executable SHA   4e28e811a89aeac6eed668ae641c7f85f5831e42e8dc6cd9a85a3bcc032ec46a
command SHA      93601a8cd24d6ae7869b8e7f8ace98ae17d80aa324f56954f244cba089379fb3
observer size    10330
observer SHA     fcc0c269e2c940aeaf0cc249fe5ad77a960d9f1324a3ba140d5601fceb69800d
```

Après une future activation séparément revue et après le claim durable du
processus parent, l'observer devra revalider le runtime et les bindings,
rehacher la population, produire les `36` mesures dans l'ordre, exécuter les
producteurs exacts des `27` tests, recomputer chaque preuve et rendre uniquement
l'observation P2-007 en JSON canonique sur stdout. Aucun record `PASS` préfabriqué
n'est construit.

## Dormance et limites

L'activation Git et les deux variables OS n'existent pas. Le premier appel du
payload s'arrête donc dans `_validate_future_transition()` avant contrat,
runtime, claim, import NumPy ou population. Les chemins one-shot claim, staging,
success, terminal et terminal forensique restent absents.

```text
capability / claim                 non / non
observer exécuté                  non
population ouverte                non
P0 / P1 / P2                      0 / 0 / 0
real data / locked test           non / non
model / training / calibration    non / non / non
```

La prochaine action est uniquement la revue externe de ce seal et de ce
payload. Elle ne peut pas être confondue avec une autorisation d'activation ou
d'exécution scientifique.
