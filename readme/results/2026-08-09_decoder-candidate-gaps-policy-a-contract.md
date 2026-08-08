# Politique A GAPS — conserver la validation historique

## Décision utilisateur et périmètre

L'utilisateur a choisi explicitement la politique **A** : conserver sans
modification la validation historique et rendre inéligibles au futur minage
train-only les prises train dont la clé de fuite corpus-aware est déjà présente
en validation. Cette décision répond au refus fail-closed documenté le 8 août
pour les dix joueurs `gaps_poly_mix` (31 prises train et 11 prises validation).

Ce commit ne relit aucun actif du projet, ne crée aucun plan réel, ne hache ni
audio ni labels et n'exécute aucun replay, minage, entraînement, validation,
export ou live. `locked_test_used=false`.

## Contrat versionné

Le plan de partitions passe au schéma `2` et porte une politique explicite :

```text
preserve_historical_validation_exclude_train_validation_leakage_groups_
then_corpus_aware_hash_70_15_15_v1
```

À partir du **manifeste complet**, le protocole :

1. refuse toujours toute ligne `test` ;
2. calcule les clés de fuite corpus-aware des lignes validation existantes ;
3. exclut automatiquement chaque ligne train ayant l'une de ces clés ;
4. partitionne seulement les lignes train restantes par la règle hashée
   `fit/dev/calibration` ;
5. persiste dans le plan JSON les identités complètes et la clé de fuite de
   toutes les prises train exclues (`excluded_train_records`).

La validation n'est ni réécrite, ni filtrée, ni repartitionnée. Les exclusions
ne peuvent pas être injectées par une liste fournie par un appelant : elles sont
recalculées depuis le manifeste complet. À la relecture, le plan est rebâti
depuis ce manifeste et doit correspondre simultanément pour les prises
retenues **et** exclues. Une omission manuelle supplémentaire, une exclusion
retirée du JSON, une capture modifiée ou un manifeste différent échoue donc
avant qu'un collecteur ou un corpus puisse être créé.

Les objets `train_items` du snapshot validé et les méthodes
`items_for_partition()` n'exposent désormais que les prises réellement
couvertes par le plan. Une prise exclue reste une preuve immuable dans le
snapshot complet, mais est refusée lorsqu'elle est fournie au collecteur.

## Vérification locale synthétique

Les tests ajoutés ne touchent que des manifestes temporaires synthétiques :

- un joueur GAPS présent en train et validation garde sa ligne validation,
  retire exactement sa capture train, conserve une partition déterministe sous
  inversion de l'ordre du manifeste et sérialise l'exclusion ;
- retirer cette exclusion du JSON ou passer une liste train manuellement
  amputée est refusé au rematch du manifeste ;
- un contexte complet ne liste que les captures planifiées dans ses trois
  partitions et refuse explicitement le collecteur de la capture exclue.

Sous Windows, la vérification a exécuté :

```text
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m py_compile
  src/polyphonic/decoder_candidate_provenance.py
  src/polyphonic/decoder_candidate_miner.py
git diff --check
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest
  tests.test_decoder_candidate_snapshot_protocol
  tests.test_decoder_candidate_labels
  tests.test_decoder_candidate_provenance
  tests.test_decoder_candidate_mining
  tests.test_decoder_candidate_instrumentation
  tests.test_decoder_candidate_asset_evidence
  tests.test_polyphonic_decoder
  tests.test_polyphonic_desktop_contract
  tests.test_product_decoder
  tests.test_polyphonic_validate_live_input_level
  tests.test_ollama_team
  tests.test_mac_worker_transport_contract
  tests.test_polyphonic_smoke_neural_independent_note
```

Résultat : compilation et `git diff --check` réussis, puis **138 tests
réussis en 8,696 s**. La suite ne consulte que les fixtures synthétiques et
les contrats unitaires pour cette modification. Elle ne constitue pas une
nouvelle expérience scientifique ni une préinscription des données réelles.

## Limites et prochaine porte

Le futur plan réel, son SHA-256, sa liste effective des 31 exclusions et le
registre d'actifs restent **à produire une seule fois sur le Mac**, seulement
après revue externe de ce code. Cette future opération devra partir du
manifeste complet `b28cb17…`, conserver les 182 lignes validation inchangées,
et être suivie d'une revue de ses empreintes et de sa couverture avant toute
ouverture d'actif ou collecte.

Aucun seuil, checkpoint ou modèle n'est promu par cette décision de split.
