# H27 Review 4 — matérialiseur opérationnel et runner one-shot

## Portée

Ce lot implémente uniquement le chemin exécutable de la Review 4. Il ne
consomme pas l'autorité publiée et ne matérialise aucune donnée.

## État vérifié avant modification

- branche isolée : `codex/h27-windows-transition-contract`;
- HEAD initial : `715d523be4a659ff2ba7a4accbd10e12d6546d2d`;
- checkout Mac détaché/propre : `46a6bdf81a56a7a7a10524d4e55092301a452207`;
- artefact publié : 882 octets, SHA-256
  `89d03ce3ea8f31a253b4e245e0357236e20860d409c27f0779a003d058fe91d2`;
- authority instance :
  `d44941a8c1c6674e5da89c40a7e3188c4e6318f7c5759ce490577d8bde81437a`;
- aucun processus H27, claim, authority materializer, staging, population ou
  terminal Review 4 observé.

## Revue externe du premier lot

La revue stricte de `859a4d848d1f2f625d2acadd728c489fd1f60038`
a rendu `NON APPROUVÉ`. Elle a identifié huit défauts : issuer/token et registre
mutable contournables, authority/claim sous-liés, double lecture TOCTOU du code,
chargement du plan avant claim, publication par chemins, faux marqueurs P0/P1/P2,
réconciliation insuffisante et absence de binding/seal opérationnel dédié.
Aucune exécution Mac n'a suivi ce verdict.

La seconde revue stricte de
`8861d7dccb6b088ab31e9b2ab16660444a11e566` a encore rendu
`NON APPROUVÉ`. Trois défauts restaient : allowlist globale réassignable,
session construisible par l'appelant et chaîne administrative incomplète, puis
absence de rehash exhaustif du staging après l'index mais avant le renommage
exclusif. Aucune exécution Mac n'a suivi ce second verdict.

## Implémentation corrective

`src/polyphonic/harmonic_censoring_h27_review4_materializer.py` conserve
mécaniquement les quatorze fonctions scientifiques déterministes de rendu,
masques et descripteurs. La publication, volontairement durcie, n'est plus
considérée mécaniquement identique : elle opère par descripteurs détenus,
`O_DIRECTORY|O_NOFOLLOW`, créations `O_EXCL`, modes `0700/0600`, fsync et
`renameatx_np(..., RENAME_EXCL)` relatif au même parent.

Le token secret, `_ISSUED`, l'issuer, `_ACTIVE_CAPABILITY` et la session publique
ont disparu. Sur import normal, l'entrypoint et tous les helpers opérationnels
sont des barrières natives. Le runner compile les octets exacts sans les
exécuter, crée la paire exacte capability/binding seulement après écriture,
fsync et réouverture byte-exacte de l'authority puis du claim, et injecte alors
une unique frontière privée. Un consumer generator one-shot réatteste PID,
code gelé, authority et claim dans la même étape.

Le runner gèle une seule fois les octets du contrat et du matérialiseur, vérifie
les seize identités administratives exactes du contrat de composition dormant,
et lie cette chaîne complète dans le binding et l'authority. Le plan et NumPy
restent post-claim et post-consommation. Après écriture et fsync de l'index, le
staging entier est relu par descripteurs, rehashé et réconcilié avec l'index
avant `RENAME_EXCL`; la réconciliation finale refait ensuite les contrôles.
Les écritures authority/claim conservent le fd créé ouvert à travers fsync du
parent et réouverture relative, puis comparent device/inode et octets. Le
terminal marque explicitement P0/P1/P2 comme
non exécutés; seuls baseline/P2 population materialized et reconciliation sont
vrais. Les deux nouveaux JSON lient et scellent l'identité exacte du module.

Identités opérationnelles proposées à la revue :

```text
materializer  blob 8cdafbd6a08ea893daa2d6f41cb62166bf9162cd
              33 706 octets
              SHA-256 2ecaabf1e1880688244b06ecb03a9b3eb7831d4659e209aa11e36b7b60948be3
binding       blob 9371d80c75c2cf08ebf2cc33177c05c123c13efa
              5 269 octets
              SHA-256 204f61303277b4a813d23a4a6a478d6d33a17893d30a72156e7a7d2574dfb4da
seal          blob 370eaf40be9863ec381061678451a58409264244
              1 198 octets
              SHA-256 f396257c040b7d0504336b98384308f76e45a32614efba129eba91c53b55f1de
```

## Validation locale

```text
python -m unittest tests.test_harmonic_censoring_h27_review4_materializer
10 tests découverts : 9 réussis, 1 skip POSIX-only sous Windows

python -m py_compile \
  src/polyphonic/harmonic_censoring_h27_review4_materializer.py \
  scripts/h27_review4_execute_once.py

git diff --check
```

Les tests prouvent l'équivalence AST des quatorze fonctions scientifiques,
l'absence d'allowlist/session publique, la barrière native sur import normal et
après rebinding des globals, la consommation exacte one-shot, le rejet de paire
forgée et de dérive post-claim, les seize identités administratives, la cohérence
binding/seal, l'ordre claim puis injection et la vérification staging avant
rename avec réouverture stable des fichiers durables.
Le test POSIX-only construit 124 répertoires/payloads, modifie un waveform
après l'index puis exige le rejet sur digest avant rename; il est versionné mais
non simulé sous Windows, où les invariants fd/mode Unix ne sont pas disponibles.

La découverte globale Windows a également été lancée sans être présentée comme
un PASS : `599` tests ont été découverts, avec `230` échecs et `44` erreurs dus
majoritairement aux représentations CRLF de ce worktree face aux contrats
historiques LF byte-exacts. Ce résultat non vert est archivé honnêtement; il ne
remplace pas le préflight Mac qui relit les blobs Git LF exacts.

## Frontière

- `materializer_authority_consumed=false`;
- `materializer_invoked=false`;
- `population_exists=false`;
- `science_executed=false`;
- `locked_test_used=false`;
- `training_executed=false`.

Le prochain geste est la revue du code exact, puis seulement son transfert
binaire et son préflight Mac avant l'unique consommation.
