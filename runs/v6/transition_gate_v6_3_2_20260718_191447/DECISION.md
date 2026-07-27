# Decision V6.3.2

V6.3.2 n'est pas integree au live. V6.0 reste la reference.

Le classifieur causal de 481 parametres atteint 85,39 % AP sur player04 et
89,45 % sur player05. Le seuil decodeur 0,0131145, selectionne uniquement sur
quatre solos player04, respecte toutes les contraintes et retire cinq evenements
sur ces sources.

Sur les quatre solos player05 verrouilles, aucune transition n'est bloquee. Les
369 evenements, 52,764 fantomes/minute, cinq notes manquantes, 79,502 % de
precision conjointe et 84,873 % F1 active sont identiques a V6.0. Il n'existe
donc pas de gain test strict justifiant un changement de reference.

Le seuil zero reproduit exactement V6.0 sur les huit sources de validation
inverse. Aucun lookahead ni delai de stabilisation supplementaire n'a ete
introduit. La latence `tf.function` du gate est de 1,090 ms au percentile 95.

Rapport complet : `continuous_transition_gate_ablation/aggregate.json`.
