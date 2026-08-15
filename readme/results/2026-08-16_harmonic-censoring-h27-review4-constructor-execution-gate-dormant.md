# H27 — Review 4 dormant constructor execution gate

Date : 2026-08-16

## Autorisation

La revue externe du résultat terminal archivé dans
`5e8a374d70ec1c06117d52f690c5f9bd5b5bf9b3` conclut `PASS`. Elle confirme la
transition consommée `7ee0a897... → 46a6bdf8...` et autorise uniquement
l'implémentation et les tests locaux d'un gate constructor dormant. Elle
n'autorise ni SSH ni ACK réel ni ouverture du registre Mac.

## Implémentation

Le nouveau runner est :

```text
scripts/h27_review4_constructor_execution_gate_once.py
ACK=H27_REAL_PUBLICATION_CONSTRUCTOR_ONE_SHOT_EXECUTION_GATE=1
arguments=0
target=/Users/amcarene/midi-worker/repository
required_head=46a6bdf81a56a7a7a10524d4e55092301a452207
control_bundle_digest=879d547c6fa4f1da36b83733bd658f10f48582fb6130470bb4657b70e55253fe
execution_authority=45f4dc4ff73284f1355eb125dc36d8c8bad2372818bf5f80b85b758ea69ae64e
constructor_blob=0c1a2aca42baa77edbd77ab42c0bd0cefaaa2b62
constructor_size=12599
constructor_sha256=0b8ad2a7efcd875b0102619eefe7ca9f015d9349693959803b9004bccf15b807
```

L'import du fichier est inert. Une future exécution n'est possible que sur
macOS, sans argument, avec l'ACK littéral. Le gate revalide le bundle fermé et
ses six fichiers avant tout accès au checkout, puis exige le HEAD exact,
détaché et propre, sans `index.lock`.

Le graphe normatif est développé et rehaché depuis les identités scellées :

```text
4 identités d'autorité dans le bundle
+ 112 identités exactes du checkout cible
= 116 identités vérifiées avant registre
```

Le contrôle est répété intégralement immédiatement avant la première frontière
persistante. Aucun chemin de destination n'est observé pendant le préflight.

## Frontières persistantes

L'ordre du futur chemin réel est explicite :

```text
préflight statique complet
→ os.open(registry, O_CREAT | O_EXCL | O_NOFOLLOW, 0600)
→ record reserved + fsync fichier + fsync parent
→ record consumed + fsync fichier
→ fermeture registre
→ chargement du constructor exact
→ invocation unique effect-free
→ vérification bytes/SHA/instance et zéro effet
→ STOP
```

L'ouverture exclusive du registre est la première tentative persistante. Toute
erreur à partir de cette frontière est terminale : aucun retry, reconstruction,
cleanup ou réparation automatique. Le constructor n'est appelé qu'après la
consommation durable de l'autorité. Il ne publie aucun artefact : son résultat
reste en mémoire, avec `filesystem_effects=0` et `science_invocations=0`.

Le runner ne contient ni matérialisation, ni population, ni P0/P1/P2, ni
science, ni locked-test. La destination activation reste une valeur canonique
passée au constructor; elle n'est ni sondée ni créée.

## Validation locale

Commandes exécutées uniquement dans le worktree auxiliaire Windows :

```text
python -B -m unittest tests.test_harmonic_censoring_h27_review4_constructor_execution_gate
.........
Ran 9 tests in 24.531s
OK

python -m py_compile \
  scripts/h27_review4_constructor_execution_gate_once.py \
  tests/test_harmonic_censoring_h27_review4_constructor_execution_gate.py
PASS

git diff --check
PASS
```

Les tests couvrent notamment l'inertie d'import, ACK/arguments fail-closed, la
construction canonique déterministe, les 112 identités normatives uniques,
l'exclusivité et l'ordre du registre, l'ordre préflight → réservation →
consommation → constructor, l'absence d'ouverture sur échec préflight et
l'absence de retry après une erreur constructor post-consommation.

## STOP

Aucun SSH, ACK réel, registre Mac, réservation, consommation, constructor,
destination, materializer, P0/P1/P2, waveform/data, science, locked-test,
training ou calibration n'a été exécuté. Prochaine action unique : revue
externe du commit complet. Toute exécution Mac requiert un nouveau `PASS`
explicite et une frontière séparée.
