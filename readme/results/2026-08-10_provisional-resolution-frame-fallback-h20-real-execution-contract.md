# H20 — Contrat de liaison d’une future exécution réelle H17

## Statut

`provisional_resolution_frame_fallback_h20_real_execution_contract_defined`

H20 est exclusivement contractuel et zéro-science. Il ne crée ni runner, ni
marqueur d’autorisation, ni commande worker. Il ne prépare et n’exécute pas
l’expérience H17.

## Chaîne scientifique liée

Le contrat lie H17, l’amendement H17a, l’audit H18a et la mécanique H19a, ainsi
que les blobs du décodeur, de l’extracteur causal, de l’univers de groupes et du
grouping. Le checkpoint reste fixé au SHA-256 `1ce8ac44…`. Toute divergence
future doit échouer avant le premier accès scientifique.

## Population prospective

La seule population autorisable ultérieurement est celle publiée par H18a :

```text
146 prises
51 groupes de fuite
fresh_discovery_only_not_independent_validation
scientifiquement ouverte = false
consommée = false
```

Aucune resélection, échantillonnage, équilibrage, filtrage de durée, raison,
target ou classe n’est permis. Les groupes H8, V2, test verrouillé, fit du
checkpoint et tous les groupes exclus par H18a restent interdits. Un actif
manquant ne peut jamais être remplacé.

## Règles scientifiques figées

La taxonomie amendée H17a, le target causal exact, `RD_false`, les cinq seuils
primaires et le bootstrap à 10 000 réplications / seed `721629268` sont figés.
L’univers futur contient exactement les 51 groupes H18a, y compris ceux qui ne
produiraient aucune ligne éligible. Les dix compteurs d’attrition sont
obligatoires et doivent se réconcilier sans suppression silencieuse.

## One-shot et consommation future

Une future exécution serait single-use, après approbation externe séparée et
marqueur lié au hash final du contrat d’exécution. La consommation devra être
persistée atomiquement juste avant la première ouverture scientifique, après
tous les préflights zéro-science. Un échec après cette limite laisse la
population consommée, interdit retry/rerun et rend le résultat inconclusif sauf
publication atomique complète déjà existante.

## Publication et éléments non résolus

La future publication devra être atomique et contenir lignes groupées,
attrition, métrique/verdict H17 et provenance. Le runtime, les chemins et hashes
des 146 audio/labels, la destination, le marqueur et le blob du futur runner
restent explicitement `null`. Ils nécessitent un contrat zéro-science séparé.

## Vérifications et interdictions

```text
7 tests structurels H20 réussis en 0,516 s
21 tests H17a/H19a/H20 réussis en 3,546 s
py_compile et git diff --check réussis
aucun fichier src/ modifié
aucun runner créé
aucun marqueur créé
```

Seuls les contrats/provenances et l’artefact JSON de métadonnées H18a ont été
lus. Aucun audio/label, checkpoint, TensorFlow, inférence, décodeur réel,
raison réelle, target réel, RD/bootstrap réel ou test verrouillé n’a été ouvert
ou calculé. H21 n’est pas autorisé automatiquement.
