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

## Implémentation

`src/polyphonic/harmonic_censoring_h27_review4_materializer.py` conserve
mécaniquement les dix-huit fonctions de rendu, masques, descripteurs, payloads,
index et publication du matérialiseur production H27 revu. Le seul delta est
le plumbing d'autorité process-local et one-shot. Une capability est émise une
fois, devient active avant `_publish`, puis terminale dans un `finally`, y
compris après exception.

`scripts/h27_review4_execute_once.py` est Darwin-only, sans argument et exige
l'ACK littéral. Son préflight rehash les huit composants scellés depuis le
HEAD Git cible, contrôle l'artefact publié, le runtime CPython/NumPy/OpenBLAS,
l'environnement exact et l'absence de toutes les destinations. Après la future
consommation, il publiera 124 records et vérifiera chaque payload final avant
d'écrire le terminal.

## Validation locale

```text
python -m unittest tests.test_harmonic_censoring_h27_review4_materializer
5 tests réussis

python -m py_compile \
  src/polyphonic/harmonic_censoring_h27_review4_materializer.py \
  scripts/h27_review4_execute_once.py

git diff --check
```

Les tests prouvent l'équivalence AST des dix-huit fonctions, le rejet d'une
capability forgée, l'unicité d'émission, la terminalité succès/erreur et
l'absence d'appel engine/recomputer/locked-test. Les suites anciennes qui
rehashent directement le checkout échouent sous Windows à cause des CRLF de ce
worktree; ce n'est pas interprété comme un PASS et le runner rehash les blobs
LF réels du checkout Mac avant tout effet.

## Frontière

- `materializer_authority_consumed=false`;
- `materializer_invoked=false`;
- `population_exists=false`;
- `science_executed=false`;
- `locked_test_used=false`;
- `training_executed=false`.

Le prochain geste est la revue du code exact, puis seulement son transfert
binaire et son préflight Mac avant l'unique consommation.
