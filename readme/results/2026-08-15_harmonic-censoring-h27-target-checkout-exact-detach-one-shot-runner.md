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
git blob   1ed1b57d6fb8ef9c8f27cb553278ba629e4d1e87
size       10382
sha256     491c5afe057a0aff364d522e28979ee2fa2d67e470f5cc61e8e8d2b1427cb7f9
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

## Binding et seal

Le binding lie six chemins uniques : runner, contrat, seal du contrat, binding
du contrat, seal de ce binding et preuve préflight. Le runner rehash les cinq
prédécesseurs avant l'observation du HEAD.

```text
binding blob  09e26933b8ea1ba8eadaeea8f9e116fe08a1953a
binding size  4649
binding sha   23b370fedc5fce032b3fa694230cfe555cd993f2a8cd41a7f7ac6b5f3f40ac16
```

Le seal reproduit le runner, son binding, les chemins/HEAD, l'ACK, la commande
de mutation et l'ordre normatif complet. Tous les downstream flags restent
faux.

## Validation locale

Les tests vérifient les six identités, le preflight réel des cinq blobs Git,
les dictionnaires complets, l'ordre statique et dynamique, l'unique mutation,
la commande POSIX exacte et l'absence de contrôles post-effet après échec.

- `py_compile` runner + test : réussi ;
- tests ciblés : `6/6` réussis ;
- suite H27 complète : `513/513` réussis en `61,483 s` ;
- `git diff --check` : requis avant commit.

## STOP

Le runner reste dormant. Prochaine action unique : revue externe du runner,
de son binding et de son seal. Aucune exécution Mac n'est autorisée par ce lot.
