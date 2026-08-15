# H27 — runner dormant one-shot de transition exacte du checkout

Date : 2026-08-15
Branche : `codex/independent-note-neural-v2`
Autorisation amont : PASS de `1c523581c866890c932268b54b66575871741acd`

## Portée

Implémentation dormante uniquement du runner one-shot de transition, identity
binding du runner, external seal, tests synthétiques et documentation. Aucune
commande Mac, aucun detach réel, registre, autorité, creator, bundle,
matérialisation, science ou locked test.

## Runner exact

```text
path       scripts/h27_detach_target_checkout_one_shot.py
git blob   d1cdf1562a814cef271d606da331e96565fcc79a
size       10428
sha256     e0fd3a4794cc2fdb266b9f3b89da25fa1260f6575e31dc3d95f761ed313b833f
```

Le runner exige :

- macOS, zéro argument et ACK
  `H27_TARGET_CHECKOUT_DETACH_EXECUTE=1` ;
- checkout `/Users/amcarene/midi-worker/repository` et ODB `.git` réels ;
- rehash de cinq identités approuvées avant observation du HEAD ;
- HEAD initial `75322bc6...`, worktree propre et cible `7ee0a897...` de type
  `commit` ;
- revalidation immédiate du HEAD initial et de la propreté ;
- unique mutation via la commande exacte :

```text
git -c core.hooksPath=/dev/null -c advice.detachedHead=false \
  -C /Users/amcarene/midi-worker/repository \
  checkout --detach --no-recurse-submodules \
  7ee0a8977208bfa389e284b07207abc40a3517fd
```

- vérification terminale HEAD cible, detached et worktree propre ;
- STOP terminal sans retry, reset, cleanup, réparation ou récupération.

Les variables d'environnement Git héritées sont retirées avant chaque
processus Git, les hooks sont désactivés et la récursion submodule interdite.
Toutes les commandes Git de lecture utilisent en plus
`git --no-optional-locks` afin que `status`, `rev-parse`, `cat-file`,
`symbolic-ref` et le rehash des blobs ne puissent pas rafraîchir l'index. La
commande de detach, seule mutation autorisée, reste strictement inchangée.

## Binding et seal

Le binding lie six chemins uniques : runner, contrat, seal du contrat, binding
du contrat, seal de ce binding et preuve préflight. Le runner rehash les cinq
prédécesseurs avant l'observation du HEAD.

```text
binding blob  d03385d842ca11631ba690d0a4bb70448c84480e
binding size  4927
binding sha   3db676881b0fca2265c09801be5fbb94d98bbf475429a7113deee872a68970df
```

Le seal reproduit le runner, son binding, les chemins/HEAD, l'ACK, la commande
de mutation et l'ordre normatif complet. Tous les downstream flags restent
faux.

## Micro-correction après première revue

La revue externe de `f0bdb521...` rend `FAIL` uniquement parce que le binding
et le seal appelaient « ordre normatif » une liste de douze éléments incluant
le rehash administratif. Le runner reste byte-identique. La correction sépare
désormais `verify_five_predecessor_identities` comme gate administratif après
realpaths et avant HEAD, tandis que l'ordre normatif publié contient exactement
les onze valeurs du contrat PASS. Le test charge ce contrat et impose
directement l'égalité des listes binding/seal avec
`contract["future_fail_closed_order"]`.

La seconde revue externe de `bdd5c90c...` confirme la nomenclature, mais rend
encore `FAIL` parce que `git status` pouvait prendre un verrou optionnel et
rafraîchir `.git/index` avant le detach. La correction courante désactive les
optional locks pour toutes les lectures Git seulement. Le test prouve
explicitement ce préfixe sur les deux contrôles de propreté pré-mutation, le
contrôle terminal, `rev-parse`, `cat-file`, `symbolic-ref` et la lecture de
blob. L'unique commande mutante reste celle déjà scellée.

## Validation locale

Les tests vérifient les six identités, le preflight réel des cinq blobs Git,
les dictionnaires complets, l'ordre statique et dynamique, l'unique mutation,
la commande POSIX exacte, les lectures Git sans optional locks et l'absence de
contrôles post-effet après échec.

- `py_compile` runner + test : réussi ;
- tests ciblés : `7/7` réussis en `0,243 s` ;
- suite H27 complète après micro-correction : `514/514` réussis en
  `61,272 s` avec le venv du projet ;
- `git diff --check` : réussi avant commit.

## STOP

Le runner reste dormant. Prochaine action unique : revue externe du runner,
de son binding et de son seal. Aucune exécution Mac n'est autorisée par ce lot.
