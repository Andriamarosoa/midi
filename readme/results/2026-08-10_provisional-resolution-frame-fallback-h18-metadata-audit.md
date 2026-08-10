# H18 — audit métadonné de population fraîche pour `frame_fallback`

## Verdict

`fresh_discovery_population_established`

L'audit métadonné autorisé après H17 établit une population future de découverte
de `146` prises réparties dans `51` groupes de fuite. Le minimum préenregistré de
`20` groupes est satisfait. Cette population n'a pas été ouverte ni consommée et
ne constitue pas une validation indépendante.

## Périmètre appliqué

H18 a lu uniquement le manifeste CSV et les JSON/textes de provenance. Pour les
actifs candidats, il a vérifié l'existence des chemins audio et labels déclarés,
sans ouvrir les fichiers, archives ou membres. Aucun checkpoint n'a été chargé.

```text
scientific_execution_authorized = false
scientific_assets_opened        = false
model_loaded                    = false
tensorflow_imported             = false
inference_run                   = false
decoder_run                     = false
candidate_reasons_inspected     = false
targets_inspected               = false
scientific_metrics_computed     = false
fresh_population_consumed       = false
h8_opened                       = false
independent_v2_opened           = false
locked_test_opened              = false
```

## Provenance du checkpoint de transcription

Le checkpoint gelé est :

```text
SHA-256       1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325
run           polyphonic_dual_stream_bass_harmonic_presence_20260801_195145
fichier       epoch-07.keras
manifeste     b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7
fit           572 prises train / 219 groupes de fuite
```

Le parent H17 versionné relie ce checkpoint, ce run et le split train complet au
même manifeste brut. Les `219` groupes sont les valeurs exactes de
`leakage_group_key()` sur les `572` lignes train du manifeste, avec le blob de
grouping gelé `e43187b4e8ba0775a74114faf406703dd6c3187c`. Aucun groupe n'a été
approximé à partir d'un nom de fichier ou d'un échantillon.

## Sources métadonnées

```text
H17 commit
3a3e65ab532a4983fadae89c842b544228c3b028

H17 contract raw SHA-256
501ac2708cf9f7f1d226ff369bbd5476793af425331550ef54a3bf2cc80c2a8a

H17 contract Git blob
f8d8e71f8d2b98955c2e19fedf2f4019ab4cca2f

manifest
b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7
754 lignes : 572 train + 182 validation

cohorte H8 consommée
4dd76bd13c33ccb3946bfdbcf6f575d4550fb0c5588095e23da3b6e3f84bce1f

protocole V2 indépendant consommé
def274de1d1c738c7d4342f8f16ef2aaab99e9b2f87d6641d012d36ab6a34119
```

## Soustraction exacte des groupes

L'univers candidat est constitué de toutes les lignes du manifeste dont les
deux chemins déclarés audio et labels existent. Il contient `754` prises et
`285` groupes; aucun chemin déclaré n'est manquant.

```text
ensemble interdit                         groupes
H8 consommé                                  31
V2 indépendant consommé                      20
test verrouillé                              40
fit du checkpoint                            219

intersection candidat ∩ H8                   31
intersection candidat ∩ V2                   20
intersection candidat ∩ test verrouillé      12
intersection candidat ∩ fit                 219
intersection H8 ∩ V2                          0
intersection H8 ∩ test verrouillé             0
intersection V2 ∩ test verrouillé             2
```

Chaque groupe candidat porte dans le JSON une liste `exclusion_reasons`
construite uniquement par appartenance à ces quatre ensembles. Aucun résultat,
durée, équilibre ou contenu scientifique n'intervient.

Après soustraction, il reste :

```text
51 groupes
146 prises
split : validation uniquement
GAPS : 14 prises
Guitar-TECHS directinput : 36 prises
Guitar-TECHS micamp : 36 prises
GuitarSet : 60 prises
```

Le JSON archive pour chaque groupe frais sa catégorie de corpus, ses captures,
ses identités d'enregistrement et les relations multi-captures. Tous les groupes
admissibles sont conservés; il n'y a ni plafond, ni tirage, ni équilibrage.

## Limite méthodologique

Le mot « frais » signifie ici absent de H8, V2 consommé, test verrouillé et fit
du checkpoint. Les `146` prises appartiennent au split validation historique et
ont donc pu contribuer à des décisions historiques de sélection de modèle. H17
les classe explicitement comme population de **découverte seulement**, jamais
comme validation indépendante. Aucun résultat futur ne pourra être présenté
comme une nouvelle validation vierge.

## Artefact et suite

Artefact :
`configs/provisional_resolution_frame_fallback_h18_metadata_audit.json`.

Le prochain geste autorisé est uniquement la revue externe de H18. Aucun H19,
runner, ouverture d'actif, inférence, calcul de raisons/targets/métriques,
bootstrap, fit, calibration, export, live ou test verrouillé n'est autorisé par
ce commit.
