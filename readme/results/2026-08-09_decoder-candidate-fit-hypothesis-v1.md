# Hypothèse V1 de fit du filtre causal de candidats

## Statut et périmètre

Ce document préenregistre une **première hypothèse de fit** à partir du corpus
V3 approuvé. Il ne lance aucun entraînement, aucune calibration, aucune
validation historique, aucun export, aucun live et aucun test verrouillé.

Le point de départ est le corpus train-only V3 : 90 prises, 3 139 candidats
causaux, 684 NoteOn confirmés (`cible=1`) et 2 455 faux NoteOn (`cible=0`). La
porte de représentation V3 est passée, mais `fit_authorized=false` est encore
effectif jusqu'à revue de cette hypothèse et du futur petit changement
d'implémentation.

L'hypothèse testable est la suivante :

> Un filtre logistique léger, alimenté uniquement par les observations
> pré-porte déjà disponibles au décodeur, peut séparer les NoteOn causaux des
> faux NoteOn mieux qu'une probabilité constante, sans ajouter de regard vers
> le futur ni dépendre de la validation historique.

Cette tête cible les **faux NoteOn réels du décodeur**, pas le label historique
`harmonic_only`. Elle ne réutilise donc ni ne promeut la précédente tête
`independent_note`, dont le résultat était négatif et saturé.

## Données, partitions et immutabilité

Le futur fit devra échouer fermé à moins d'employer exactement les artefacts V3
ci-dessous, rehachés avant la première lecture :

| Entrée | SHA-256 |
| --- | --- |
| `candidate_events.jsonl` | `fd852626f56b038837266b5336b318c8adf841c1aafbd01d36b362f7fe10150d` |
| `mining_report.json` | `e13a13be38710e7a15f9d6d222d0a7835aad204a1b7c821d8198d1ac9ccffe59` |
| Manifeste | `b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7` |
| Plan Policy A v2 | `a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4` |
| Registre d'actifs | `12dd74f2c868d884f9189e1c8d07c1e7e1cec4e984fda5a68ce434c05e586507` |
| Checkpoint de transcription ayant produit les candidats | `1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325` |
| Configuration d'inférence | `245285783eb395e1c16f9773cf9a15565510ba289467d63ad6a7d725bae19804` |
| Décodeur référence (`threshold=null`) | `c16be48271912c99c4237345e8406e39b88490b5565047757f6ca9e905615f96` |
| Politique audio causale LF | `45edbb712415c5b62f10a1405678fc28cee083891131108b2875ce8f71abcd3e` |
| Protocole V3 | `db55930a9faadc12fb7b08e52e0baac3543e3d5cb654844ea93e0d727a563683` |

Les partitions demeurent intangibles : `fit` apprend, `dev` choisit l'époque
du modèle et vérifie le signal, `calibration` choisit éventuellement le seuil.
La validation historique et le test verrouillé ne sont ni chargés ni lus. Toute
ligne hors de ces trois partitions, tout `event_id` dupliqué, toute absence de
provenance ou toute divergence d'empreinte rendra le fit inutilisable.

| Partition | Cible 0 | Cible 1 | Total |
| --- | ---: | ---: | ---: |
| `fit` | 694 | 244 | 938 |
| `dev` | 968 | 250 | 1 218 |
| `calibration` | 793 | 190 | 983 |

## Entrées autorisées et préparation

La projection d'entrée est **exactement** `CAUSAL_FEATURES`, dans cet ordre :

```text
frame_probability
onset_probability
candidate_score
candidate_reason
harmonic_support
audio_onset_available
audio_onset_recent
active_polyphony
```

Prétraitement figé :

1. `frame_probability`, `onset_probability`, `candidate_score`,
   `harmonic_support` et `log1p(active_polyphony)` sont normalisés par moyenne
   et écart-type calculés sur `fit` seulement. Un écart-type non fini ou nul
   provoque un échec fermé.
2. `audio_onset_available` et `audio_onset_recent` deviennent `0/1`.
3. `candidate_reason` est encodé one-hot dans l'ordre immuable :
   `model_onset`, `frame_attack`, `frame_fallback`, `legacy`,
   `chord_completion`.

La dimension finale est donc 12. Sont explicitement interdits comme entrées :
la cible, la latence, l'index de référence, `event_id`, pitch, frame, toutes les
provenances, l'état/score/rang post-porte et toute information future. Le
filtre reste ainsi causal et peut être évalué avant une décision d'émission.

## Architecture et optimisation figées

Le modèle V1 est une régression logistique régularisée :

```text
vecteur 12
→ Dense(1, sigmoid, GlorotUniform(seed=47), L2=1e-3)
→ probabilité p(NoteOn causal)
```

Il n'y a ni couche cachée, ni accès au backbone, ni audio brut, ni lookahead.
Cette simplicité est intentionnelle : elle isole la valeur prédictive des
features du décodeur avant d'introduire une capacité non linéaire plus difficile
à interpréter.

Le futur fit unique sera CPU forcé, seed `47`, batch `64`, Adam à `0,01`, au
plus 40 époques, une seule file et un seul worker. Il suivra la
cross-entropie binaire pondérée sur `dev`, avec arrêt anticipé
`patience=5`, `min_delta=1e-4`, restauration des meilleurs poids. La durée
murale est limitée à 15 minutes. Aucun deuxième essai ni recherche
d'hyperparamètres n'est autorisé par cette hypothèse.

## Pondération anti-dominance et anti-fuite

La pondération est calculée séparément dans chaque partition, sans jamais
utiliser dev ou calibration pour apprendre les statistiques de fit.

Les deux vues Guitar-TECHS (`directinput` et `micamp`) forment la même famille
`guitar_techs_paired`; elles ne reçoivent donc pas deux quotas de corpus pour
une même performance physique. Les familles sont : `gaps_poly_mix`,
`guitar_techs_paired` et `guitarset_poly_mix`.

Pour une ligne `i` de famille `f`, cible `y` et groupe de fuite `g`, le poids
de fit est :

```text
w_i = N_fit / (6 × G_(f,y) × n_(f,y,g))
```

où `G_(f,y)` est le nombre de groupes de fuite distincts présents dans la cellule
famille × cible et `n_(f,y,g)` le nombre de lignes de ce groupe dans cette
cellule. Les six cellules famille × cible contribuent donc également au loss,
et un joueur GAPS ou une performance Guitar-TECHS à deux vues ne peut pas
dominer simplement parce qu'il génère plus de candidats. Les poids ont une
moyenne égale à 1 sur `fit`. La même formule, calculée localement sur dev ou
calibration, est utilisée uniquement pour leurs métriques équilibrées.

## Critères préenregistrés

### Dev : choix de l'époque, pas du seuil

La meilleure époque est celle minimisant la cross-entropie binaire équilibrée
par groupe sur `dev`. Le modèle est considéré comme ayant un signal minimal
seulement si, sur dev :

- Brier équilibré par groupe `< 0,25` (meilleur qu'une constante à 0,5) ;
- AUC ROC équilibrée `≥ 0,55` dans chacune des trois familles ;
- les six cellules famille × cible sont présentes et finies.

Ces mesures sont diagnostiques et ne sélectionnent aucun seuil opérationnel.
Un échec conclut cette hypothèse négativement : aucune calibration, validation
historique ou relance ne sera effectuée automatiquement.

### Calibration : seuil interne au train uniquement

Si et seulement si dev passe, les seuils `0,01` à `0,99` par pas de `0,01` sont
évalués **une seule fois** sur calibration. Une candidate est conservée si
`p(NoteOn causal) ≥ seuil`. Le seuil publié est le plus petit seuil qui respecte
toutes les contraintes suivantes :

- rappel brut global des NoteOn causaux `≥ 0,98` ;
- rappel brut dans chacune des trois familles `≥ 0,90` ;
- retrait équilibré par groupe des faux NoteOn `≥ 0,05` ;
- Brier équilibré par groupe `< 0,25`.

S'il n'existe pas de seuil admissible, `threshold=null` est publié et la tête
ne peut pas être insérée dans le décodeur. Les résultats bruts et équilibrés,
globaux, par famille et par partition doivent être conservés pour la revue.

## Conditions de suite

Le futur rapport de fit devra inclure les empreintes, les poids par cellule,
l'architecture sérialisée, la parité sauvegarde/rechargement, les courbes
fit/dev, le tableau calibration complet et la mesure de coût par candidat ou
par frame. Une réussite de fit/calibration ne lance pas de validation : une
revue humaine devra d'abord autoriser une unique validation historique A/B,
sans test verrouillé.

Avant cette revue, il est interdit de lancer un fit, une calibration, une
validation, un export, du live, une sélection de seuil ou tout accès au test
verrouillé.

