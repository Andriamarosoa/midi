# H26 — frontière opérationnelle P0 après STOP 4

Date : 2026-08-12

## Portée

Cette étape implémente uniquement l'entrée opérationnelle de la future passe
P0. Elle part du commit STOP 4 approuvé
`4fd020c4689ded03698bb611068eccd2321ecf1e` et ne relance ni la
matérialisation ni un test scientifique.

État terminal de cette étape :

```text
H26_P0_OPERATIONAL_ENTRYPOINT_IMPLEMENTED_STOP4_PENDING_EXTERNAL_REVIEW_NO_P0
```

## Bindings immuables

- authority ID :
  `h26-materialization-authority-v1-1918eb0f2b74754fe79c50c994b9b038b5a27afcf80dd3ccf2d28825355a0be2` ;
- authority SHA-256 :
  `ed0d55afe2923e4996f19e45be5aff99e2efab2f45ee6143c28f1a8ee6f2e805` ;
- seal SHA-256 :
  `f1118ccaae58bbbe90da3bcba1eab978ccd01b826f795fe163f409ae2e63bc42` ;
- population index SHA-256 :
  `b0045797b08ef2ebbfaf7e1dda0c10f213eec3d8b3a3daaa31c8153dd842b4a7` ;
- population : `/Users/amcarene/h26-admin/population/h26-synthetic-v1`,
  exactement 40 records baseline et 153 records P2 ;
- blobs engine/recomputer/materializer inchangés : `729a989...`,
  `2e7fc04...`, `2991c69...`.

## Frontière implémentée

Le nouveau runner no-arg reste bloqué par son lifecycle par défaut. Une future
activation séparée devra être revue avant qu'il puisse :

1. revalider macOS, HEAD propre, acknowledgement, commit et les dix variables
   runtime ;
2. revalider les cinq preuves STOP 3, le runtime live, l'authority et le seal
   STOP 4 ;
3. rehacher l'index et tous les fichiers des 40+153 records, avec contrôle de
   namespace, ordre, cardinalité, doublons, containment et symlinks ;
4. revalider les trois JSON scientifiques et les trois blobs exécutables ;
5. exiger tous les slots P0 absents ;
6. publier `claim.json` en create-exclusive, point irréversible de
   consommation ;
7. exécuter uniquement P0-001 à P0-009 dans l'ordre, avec kill-rule ;
8. publier les preuves, le transcript validé puis le receipt terminal en
   dernier ;
9. s'arrêter pour revue externe, sans retry.

La capability P0 est privée, non constructible publiquement et attestée par
identité. Elle revalide HEAD, worktree, claim et population index à chaque
passage au moteur. L'adapter temporaire du moteur est restauré dans `finally`.

## Évaluateurs P0

Les neuf règles du manifeste sont implémentées explicitement : intégrité des
schémas et ordres, quatre outcomes, certificats positifs/négatifs et leurs
inverses, collisions non identifiables, fallback ambigu, causalité à un hop,
exclusion des oracles et recomputation indépendante avec cinq corruptions
préenregistrées. Aucune règle P1/P2 n'est accessible depuis ce runner.

## Validation locale sans science

Les tests utilisent uniquement une population artificielle minimale, des
fakes et des répertoires temporaires. Ils couvrent notamment le lifecycle
dormant, l'absence d'argument, la population scellée, le rejet d'une capability
forgée, les chemins all-pass/failure/inconclusive, la kill-rule, la restauration
de l'adapter et l'immutabilité des trois blobs scientifiques.

Validation exécutée : `52/52` tests ciblés réussis, puis les `23/23` modules
de test H26 réussis chacun dans un processus isolé, sans population réelle ni
calcul P0. Commandes archivées :

```text
python -m py_compile src/polyphonic/run_h26_p0_operational.py
python -m unittest tests.test_harmonic_censoring_h26_p0_operational tests.test_harmonic_censoring_h26_dormant_stack tests.test_harmonic_censoring_h26_materialization_operational -v
git diff --check
```

## Interdictions maintenues

- aucun P0/P1/P2 réel ;
- aucune lecture du locked-test ;
- aucun entraînement, modèle, checkpoint ou calibration ;
- aucune modification du moteur, recomputer, materializer, préinscription,
  fixture spec, manifeste ou population ;
- aucune activation, claim, preuve ou receipt réel ;
- aucun retry.

## Correctif après la première revue externe

La revue externe de `952e2cfbc75d713686013fef941f4556e9f3ecb5` a refusé
toute activation lifecycle et a autorisé uniquement un correctif borné de la
frontière. Le delta de correction :

- complète P0-005 avec les deux contributions non nulles, la fréquence de
  collision canonique, l'équation d'amplitude compensée, l'égalité byte-exacte
  des deux observations, le masque commun et l'état causal ambigu ;
- fixe P0-007 aux endpoints exacts `16383/16639`, aux vues précédentes finissant
  à `16127`, au hop `256` et à zéro lecture future ;
- étend P0-008 aux identités de fixture, labels latents, audio futur et état
  post-décision, en plus des champs oracle déjà interdits ;
- refuse les symlinks dans toute la chaîne de parents de sortie avant la claim ;
- limite chaque preuve JSON aux seules fixtures déclarées pour son test ;
- ajoute les cas négatifs STOP3/STOP4, runtime live, population, blobs source,
  slots, capability, publications et primitive Darwin no-replace demandés.

Le lifecycle et tous ses bindings immuables restent inchangés et dormants.
Aucun P0 réel, claim, evidence, transcript ou receipt n'a été produit par ce
correctif. Une nouvelle revue externe reste obligatoire avant toute activation.

Validation du correctif : `67` tests ciblés découverts sous Windows, `64`
réussis et les `3` contrôles dépendants de Darwin/symlinks ignorés ; les mêmes
`67/67` tests ont réussi sur le Mac. Les `23/23` modules H26 ont également
réussi séparément sous Windows puis sous macOS. Les deux checkouts Mac sont
propres et synchronisés au commit du correctif. Aucun de ces tests n'a ouvert
la population réelle ni publié de claim scientifique.
