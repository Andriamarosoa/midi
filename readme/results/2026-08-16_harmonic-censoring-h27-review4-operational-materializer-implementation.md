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

## Implémentation corrective

`src/polyphonic/harmonic_censoring_h27_review4_materializer.py` conserve
mécaniquement les quatorze fonctions scientifiques déterministes de rendu,
masques et descripteurs. La publication, volontairement durcie, n'est plus
considérée mécaniquement identique : elle opère par descripteurs détenus,
`O_DIRECTORY|O_NOFOLLOW`, créations `O_EXCL`, modes `0700/0600`, fsync et
`renameatx_np(..., RENAME_EXCL)` relatif au même parent.

Le token secret, `_ISSUED` et l'issuer public ont disparu. La capability n'a
aucun constructeur public. Le runner crée la paire exacte capability/binding
après écriture, fsync et relecture byte-exacte de l'authority puis du claim. Un
consumer generator one-shot réatteste PID, code gelé, authority et claim dans
la même étape; un objet forgé par `object.__new__` sans ces descripteurs échoue
avant publication.

Le runner gèle une seule fois les octets du contrat et du matérialiseur, puis
les exécute avec `compile`/`exec` dans des modules frais sans SourceFileLoader,
pyc ou seconde ouverture du chemin. Le plan et NumPy restent post-claim et
post-consommation. La réconciliation indépendante recalcule les identités
canoniques ordonnées, les métadonnées dérivées, les payloads, l'unique alternate,
les modes et l'arbre exhaustif. Le terminal marque explicitement P0/P1/P2 comme
non exécutés; seuls baseline/P2 population materialized et reconciliation sont
vrais. Les deux nouveaux JSON lient et scellent l'identité exacte du module.

Identités opérationnelles proposées à la revue :

```text
materializer  blob dab34b25b09e13aac2d46712e688aae2426fcd56
              28 901 octets
              SHA-256 8941ed24443aff54fd0ec331e74efb87b71b045e352e0a9ce19a379a31b9650a
binding       blob 14eb7ffa320ae99a1fd3f70c56afc73c75ee5adc
              1 512 octets
              SHA-256 1f495b010b86f9c47c3c95d56c1aa887ec9d22f8ab857b221a98be88f3e07cc6
seal          blob 28093a9511670f18fdb8b7aba7f6f57bb23ce69d
              1 118 octets
              SHA-256 3a330d160de20354670e1d9d849a38bd82dd5b3368790307a1533e94a9032347
```

## Validation locale

```text
python -m unittest tests.test_harmonic_censoring_h27_review4_materializer
8 tests réussis

python -m py_compile \
  src/polyphonic/harmonic_censoring_h27_review4_materializer.py \
  scripts/h27_review4_execute_once.py

git diff --check
```

Les tests prouvent l'équivalence AST des quatorze fonctions scientifiques, le
rejet constructeur/copy/deepcopy/pickle/object.__new__, l'absence de token,
issuer et registre mutable, la cohérence binding/seal et les frontières
post-claim/non-scientifiques du runner.

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
