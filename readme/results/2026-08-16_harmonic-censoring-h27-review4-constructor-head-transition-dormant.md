# H27 — Review 4 constructor HEAD transition runner dormant

Date : 2026-08-16

## Autorisation

La revue externe de `ace17e9f04ab1b47b6928fc45cddaf8b9d6cdc83`
rend `PASS` sur le préflight constructor-gate et autorise uniquement
l'implémentation et les tests d'un runner dormant de transition Git. Elle
n'autorise aucune exécution Mac.

## Runner

```text
scripts/h27_review4_constructor_head_transition_once.py
size_bytes=15975
git_blob_sha1=037703a9e710c3eebbd349e8801c6fc5913e7582
raw_sha256=665f2a878973a7e03bd24ea0fac06c583f889a993ff575da697a498969571d32
ACK=H27_REVIEW4_CONSTRUCTOR_HEAD_TRANSITION_EXECUTE=1
arguments=0
initial_head=7ee0a8977208bfa389e284b07207abc40a3517fd
target_head=46a6bdf81a56a7a7a10524d4e55092301a452207
```

L'ACK constructor `H27_REAL_PUBLICATION_CONSTRUCTOR_ONE_SHOT_EXECUTION_GATE`
doit rester absent. La future commande unique est exactement :

```text
git -c core.hooksPath=/dev/null -c advice.detachedHead=false \
  -C /Users/amcarene/midi-worker/repository \
  checkout --detach --no-recurse-submodules \
  46a6bdf81a56a7a7a10524d4e55092301a452207
```

Le runner nettoie toutes les variables `GIT_*`, puis réintroduit uniquement
`GIT_TERMINAL_PROMPT=0`, `GIT_NO_LAZY_FETCH=1` et
`GIT_OPTIONAL_LOCKS=0`.

## Préconditions fail-closed

Avant le premier effet, le runner impose :

- checkout et ODB réels aux chemins exacts ;
- bundle de six fichiers byte-exact et digest fermé `879d547c...` ;
- HEAD initial exact, détaché, worktree propre et `index.lock` absent ;
- cible commit exacte, ancêtre à une distance exacte de onze commits ;
- constructor cible blob `0c1a2aca...`, taille `12599`, SHA-256
  `0b8ad2a7...` ;
- snapshot des refs régulières ;
- registre constructor, final et staging tous absents ;
- aucun processus constructor, materializer ou science.

Après la première revue du commit `3c1b464...`, ce dernier garde-fou inclut
également toute autre instance du runner de transition lui-même. Le scan parse
les PID de `ps`, ignore uniquement `os.getpid()` et refuse un autre PID dont la
commande contient `h27_review4_constructor_head_transition_once.py` avant le
subprocess checkout.

Une revalidation complète est répétée immédiatement avant la mutation. Après
la mutation unique, HEAD cible, état détaché/propre, lock, refs, bundle,
constructor, chemins absents et processus sont revérifiés.

## Frontière de consommation

Avant le lancement du subprocess checkout, un échec reste pré-effet. Dès que
le subprocess est lancé, la tentative de transition est consommée quelle que
soit son issue. Toute erreur impose STOP sans retry, reset, cleanup, repair ou
récupération automatique.

Le runner ne peut ouvrir/écrire le registre, réserver/consommer l'autorité,
définir l'ACK constructor, invoquer constructor/materializer, créer staging ou
final, exécuter P0/P1/P2, générer des données, lancer science, locked-test,
training ou calibration.

## Validation locale

```text
py_compile=PASS
tests_dedies=10/10 PASS
test_file_size_bytes=13069
test_file_git_blob_sha1=f1eaf6b032dd8ee2abe98310fae194eb03943ce4
test_file_raw_sha256=bd1ff2006be864fa2a05d3a6e0b470d8def30cd7f2110dde532a959fea2d0b19
git_diff_check=PASS
```

Une tentative de suite historique H27 large (`585` tests) n'est pas une preuve
valide dans ce worktree Windows : `230` échecs et `50` erreurs proviennent
majoritairement des anciens fichiers scellés checkoutés en CRLF alors que ces
tests historiques exigent leurs octets Git LF. Aucun de ces fichiers n'a été
modifié par ce lot. Cette tentative locale n'a exécuté ni Mac, ni science, ni
locked-test.

STOP. Le runner n'a pas été exécuté; son ACK n'a pas été défini. Une nouvelle
revue externe du commit exact est obligatoire avant toute transition Mac.
