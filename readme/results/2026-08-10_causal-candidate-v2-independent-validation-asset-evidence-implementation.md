# Implémentation synthétique — preuve d'actifs de validation V2 indépendante

## Portée

Ce commit prépare uniquement le registre de provenance requis avant la future
passe V2 indépendante. Il n'exécute aucune CLI et ne construit aucun registre
sur les données du projet. Les seuls fichiers lus par les tests sont des octets
factices créés dans des répertoires temporaires ; aucune forme d'onde, NPZ,
checkpoint, modèle ou prédiction réels n'a été ouvert.

Le contrat scellé est corrigé pour lever l'ambiguïté documentaire relevée
en revue : une ligne `train` peut rester visible dans le manifeste complet
pour prouver l'absence de chevauchement avec Policy A ; une ligne `test` ou
une ligne **sélectionnée** non-validation est en revanche refusée.

## Registre implémenté

`src/polyphonic/causal_candidate_v2_independent_asset_evidence.py` définit un
registre JSON canonique qui lie strictement :

- le SHA du protocole V2 indépendant ;
- le SHA du manifeste complet ;
- le SHA de la liste ordonnée des 30 clés et les 30 clés elles-mêmes ;
- les deux seuls types d'actifs, `audio` et `labels` ;
- pour chaque prise, l'identité, la clé de fuite, `audio_member`, les tailles
  et SHA-256 de l'audio et des labels.

Aucun chemin local, handle ou contenu d'actif n'est sérialisé. Le builder
accepte uniquement le snapshot chargé/attesté du manifeste et les 30 objets
exactement dérivés par la cohorte. Il refuse un SHA de manifeste divergent,
une ligne non-validation, une clé/groupe divergent ou un clone d'objet. Les
fichiers sont lus comme blocs d'octets pour calculer SHA-256 et taille ; ils ne
sont jamais interprétés comme audio ou labels.

L'écriture emploie un `.part` exclusif, `fsync`, une publication `link` sans
écrasement, JSON canonique et relecture. La lecture du registre ne charge pas
les actifs. Les deux fonctions de vérification
futures rehachent respectivement le label ou l'audio immédiatement avant une
ouverture future et échouent si les octets diffèrent.

## Vérifications

La commande ciblée suivante a réussi dans le worktree
`codex/independent-note-neural-v2` :

```text
python -m unittest \
  tests.test_causal_candidate_v2_independent_asset_evidence \
  tests.test_run_causal_candidate_v2_independent_validation \
  tests.test_decoder_candidate_asset_evidence \
  tests.test_decoder_candidate_snapshot_protocol \
  tests.test_decoder_candidate_provenance
```

Résultat : `41` tests réussis en `3,828 s`. `py_compile` est aussi passé.
La suite existante d'asset-evidence importe TensorFlow afin de construire son
corpus **synthétique**, mais aucun modèle, checkpoint, actif projet ni calcul
scientifique n'a été utilisé. Le nouveau module, importé seul dans un
processus neuf, ne charge ni TensorFlow ni CLI.

## Limite et prochaine action

Ce commit n'autorise aucune construction de preuve sur les 30 actifs réels.
Il n'ajoute pas le runner CPU et n'ouvre ni Mac, ni validation historique, ni
test verrouillé. La prochaine action autorisable est seulement une revue de
cette implémentation. Après une approbation distincte, la preuve réelle devra
être créée une fois, rehashée puis archivée avant toute passe CPU.
