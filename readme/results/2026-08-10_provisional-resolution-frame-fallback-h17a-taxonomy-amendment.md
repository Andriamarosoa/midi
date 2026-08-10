# H17a — Amendement pré-exécution de la taxonomie des raisons

## Statut

`provisional_resolution_frame_fallback_h17a_preregistration_amendment_recorded`

Cet amendement est effectué avant toute ouverture des 146 prises H18a et avant
tout comptage scientifique. Le contrat H17 historique reste inchangé au commit
`3a3e65ab…` et au blob Git `f8d8e71f…`.

## Motif

La revue statique externe du premier commit H19 a découvert qu’une raison déjà
présente dans le décodeur gelé avait été omise de la taxonomie H17 :
`harmonic_strong_frame`. H19 a donc été refusé, puis H19a a démontré sur le vrai
chemin synthétique du décodeur que cette raison peut être conservée et exclue
sans modifier le décodeur.

Chaîne archivée :

```text
H17 original       3a3e65ab532a4983fadae89c842b544228c3b028
H19 refusé         2361486241f6f58662ab483eb526d3b9bdeb68db
H19a corrigé       a28068a55d711ad4dd24e31736974bdf30533c00
```

## Taxonomie amendée

```text
F = 1
  frame_fallback

F = 0, comparateur
  model_onset
  frame_attack
  chord_completion

exclus et comptés seulement
  harmonic_strong_frame
  legacy
  retrigger

toute autre raison
  frame_fallback_execution_invalid
```

La raison antérieure d’un `harmonic_strong_frame` ne peut jamais être
reconstruite. Le compteur `excluded_harmonic_strong_frame_count` rejoint le
schéma d’attrition obligatoire.

## Portée scientifique

La question, le signal primaire, le comparateur, le target causal, le seuil RD
et le bootstrap sont inchangés. En revanche, le contrat déclare honnêtement :

```text
population_taxonomy_amended = true
attrition_schema_amended = true
amendment_occurred_before_real_data_access = true
```

## Vérifications

Le test structurel vérifie l’immuabilité du contrat H17 historique, les trois
commits de revue, la taxonomie exacte, les déclarations de changement, les dix
compteurs d’attrition, les seuils inchangés, le périmètre zéro-science et LF.

Aucun fichier `src/` n’est modifié. Aucun audio/label H18a, checkpoint,
TensorFlow, inférence, raison réelle, target réel, RD/bootstrap réel ou test
verrouillé n’a été ouvert ou calculé. Une revue externe reste obligatoire avant
toute préparation ou exécution scientifique.

```text
5 tests structurels H17a réussis
24 tests H17/H17a/H19a réussis en 4,150 s
py_compile réussi
git diff --check réussi
```
