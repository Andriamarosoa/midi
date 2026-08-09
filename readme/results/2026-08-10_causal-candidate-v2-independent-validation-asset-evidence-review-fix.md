# Correctif de revue synthétique — preuve d'actifs V2 indépendante

## Portée

Ce correctif répond à la revue externe négative de `3d889f05`. Il ne crée
aucun registre sur les données du projet, n'ouvre aucun audio/label du projet,
ne charge ni TensorFlow, ni modèle, ni checkpoint, et ne contacte pas le Mac.
Les seuls octets d'actifs hachés par les nouveaux tests sont de faux fichiers
créés dans un répertoire temporaire.

La politique versionnée reste explicitement fermée :

```text
builder_authorized_now = false
reader_authorized_now  = false
```

Ainsi aucune API de construction ou de lecture de registre ne peut démarrer
sur la cohorte réelle avant une autorisation et une revue ultérieures.

## Garde-fous ajoutés

1. `IndependentV2ValidationCohort` est désormais une capacité : seule
   `load_sealed_independent_v2_validation_cohort()` l'atteste par identité.
   Une dataclass construite directement ou clonée, même avec 30 clés et 20
   groupes valides, ne peut plus construire de preuve.
2. La demande d'évidence est elle aussi une capacité liée au cohort scellé.
   Elle impose les indicateurs d'autorisation du protocole avant toute lecture
   d'actif ou du JSON.
3. Le résultat du builder est une capacité distincte. L'écriture rehache les
   60 fichiers juste avant publication : une mutation entre `build` et `write`
   échoue, et le fichier destination n'est pas créé.
4. Un JSON chargé est seulement *analysé*, jamais utilisable directement.
   `validate` rehache les 30 audio et 30 labels, compare identité, groupe,
   `audio_member`, taille et SHA-256, puis délivre l'unique capacité employable
   par les vérifications d'ouverture. Un JSON canonique aux digests inventés
   est donc refusé.
5. Une future étape de lecture devra en outre fixer dans son protocole le SHA
   exact du registre et le SHA du protocole qui a autorisé sa construction.
   Le lecteur refuse les octets dont le SHA ne correspond pas à cette valeur
   scellée. Les flags `builder` et `reader` sont mutuellement exclus : la
   construction et l'exploitation nécessitent deux autorisations séparées.
6. Le lecteur de snapshot manifeste a été extrait dans
   `src/polyphonic/manifest_snapshot.py`, sans TensorFlow. Les tests de ce
   contrat importent ce module pur, pas `data.py`.

## Vérifications

Les tests strictement nouveaux, sans import TensorFlow, ont réussi :

```text
python -m unittest \
  tests.test_causal_candidate_v2_independent_asset_evidence \
  tests.test_run_causal_candidate_v2_independent_validation

14 tests réussis en 2,868 s
```

Ils couvrent notamment le refus avant hachage quand les flags sont faux, les
clones de cohort/demande, les digests forgés dans un JSON canonique, la
mutation build→write, le JSON sémantiquement identique mais non canonique, et
la mutation détectée à la frontière d'ouverture.

La suite provenance élargie a aussi réussi :

```text
44 tests réussis en 10,340 s
```

Cette dernière inclut des tests existants du corpus qui importent TensorFlow
pour leurs fixtures synthétiques; elle ne lit néanmoins aucun actif projet ni
ne produit de calcul scientifique. `py_compile` et `git diff --check` passent.

## État et suite

Le protocole réel demeure verrouillé à `false/false`; aucune construction de
preuve réelle, validation V2 indépendante, entraînement, export, live ou test
verrouillé n'est autorisé. La seule action suivante est une nouvelle revue
externe de ce correctif d'implémentation.
