# H13 — univers fixe des groupes de cohorte

## Décision externe à l'origine du correctif

La revue externe a approuvé H12 dans sa portée binding/preflight, puis a refusé
l'exécution réelle : H10 dérivait `G` uniquement des lignes scientifiques
éligibles. Un groupe H8 sans ligne éligible aurait donc disparu silencieusement
de l'univers bootstrap pourtant préenregistré comme les groupes indépendants de
la cohorte scellée.

## Correction synthétique

H10 exige maintenant `cohort_group_universe` explicitement. Cet univers est
validé, trié canoniquement et refuse doublons, texte vide/paddé et toute ligne
scientifique extérieure. Le bootstrap tire exactement `len(universe)` groupes
avec remise. Un groupe scellé sans ligne éligible reste tirable, contribue zéro
ligne et compte néanmoins dans les `G` tirages. Les réplications sans deux
classes restent invalides selon la règle H10 existante, sans retry.

La métrique globale reste calculée uniquement sur les lignes éligibles. Aucune
ligne, cible ou valeur S1 n'est créée pour un groupe vide. Les constantes restent
`10000` réplications, seed `721629268`, PCG64 et minimum `9500` réplications
valides. Les seuils, S1/S0/D1, cibles et verdict primaire sont inchangés.

## Binding réel final

Le runner H13 n'accepte aucun argument scientifique. Il reconstruit l'univers
comme les `31` valeurs uniques triées de `leakage_group_key` dans les
métadonnées H8 scellées, puis le transmet directement au moteur H10 corrigé.
Le point d'entrée H12 historique délègue à H13. Un futur marqueur one-shot devra
contenir le SHA brut du contrat H13 réellement revu, et non le SHA du contrat
H11.

Le contrat H13 scelle :

- contrat H12 brut : `d1f9e80227776c8d6c81fc91d7a2df8982425eaadf786b7406ca54f33fa41fce`;
- runner H12 précédemment revu : `4aba24acc1d3a435285e7260485f1bd4a358bf61`;
- cohorte H8 brute : `4dd76bd13c33ccb3946bfdbcf6f575d4550fb0c5588095e23da3b6e3f84bce1f`;
- univers : exactement `31` groupes, dérivés uniquement des métadonnées H8.

Empreintes du correctif :

- ancien moteur H10 : `a343c5057ec2a84f3e42c6be6e6e7b641c0f1a70`;
- moteur H10 corrigé : `5e40574dab4a53e0ce5b2288536d337f0da66fa9`;
- binding H12 corrigé : `1e5b54c365df82a6504068ab9a8385eef6d23ae5`;
- runner final H13 : `675e77e7182e5efbd91a1af35c86b9e242370a24`;
- contrat H13 brut : `76e40426921c3c972adc465a5197136d3ff675d15504816aa5f149878dd0bd0d`
  (`2616` octets).

La suite H7–H13 a exécuté `69` tests en `9,501 s`, avec `py_compile` et
`git diff --check`. Les nouveaux tests prouvent notamment un univers de trois
groupes avec lignes dans deux groupes seulement, la contribution vide du
troisième groupe, la conservation de `G=3`, la multiplicité, le déterminisme
sous inversion des entrées, les refus hors-univers/doublon/identifiant vide et
le statut inconclusif lorsque les groupes vides rendent trop de réplications
invalides.

## Portée

Cette étape n'a créé aucun marqueur et n'a pas invoqué le runner réel. Aucun
audio ou label H8 n'a été ouvert scientifiquement, aucun modèle chargé, aucune
inférence exécutée, aucun signal/target réel extrait et aucune métrique réelle
calculée. H8 reste non consommée. Une nouvelle revue externe est obligatoire
avant toute autorisation réelle.

## Preflight Mac zéro-science

Le Mac a été synchronisé exactement sur le commit
`bd1858addef75e64f771b884e7b1f91d3a5d0363`, puis seule la commande
`python -m src.polyphonic.provisional_resolution_age1_h13 --preflight-only`
a été exécutée avec `MIDI_FORCE_CPU=1` et le `MIDI_DATA_ROOT` canonique.

Résultat :

```text
status                                      h7_real_execution_preflight_ready
h13_status                                  provisional_resolution_age1_persistence_h13_execution_seal_ready
recordings                                  101
leakage_groups                              31
sealed_cohort_group_universe_count          31
forbidden_groups                            58
scientific_execution_authorized             false
execution_marker_created                    false
runner_invoked                              false
h8_scientific_assets_opened                 false
h8_discovery_consumed                       false
real_targets_extracted                      false
real_signals_extracted                      false
real_metrics_computed                       false
```

Runtime confirmé : Python `3.11.9`, NumPy `1.26.4`, métadonnée TensorFlow
`2.15.1`, macOS `15.5` / Darwin `24.5.0`, arm64, CPU.

Avant et après le preflight, les quatre chemins suivants étaient absents :

- marqueur d'autorisation ;
- marqueur `.claimed` ;
- répertoire final de résultat ;
- rapport d'échec.

Le worktree Mac est resté propre. Ce preflight n'autorise toujours pas le run
réel et n'a révélé aucun compte d'éligibilité scientifique par groupe.
