# H26 — contrat dormant de qualification du runtime de matérialisation

## Portée fermée

Cette étape applique uniquement l'autorisation :

```text
AUTHORIZED_TO_DEFINE_AND_COMMIT_H26_DORMANT_MATERIALIZATION_RUNTIME_QUALIFICATION_CONTRACT_ONLY
```

Le parent direct est `236a84b4eb928b102bc1548fb2b32d1bffda2e63`.
Le changement est limité au contrat JSON déclaratif, au présent rapport et au
résumé global. Aucun qualificateur, claim, record runtime, authority, seal,
destination ou artefact scientifique n'est créé.

## Liaisons exactes

Le contrat lie `H26_BOUNDED_EVIDENCE_V1`, `H26_SYNTHETIC_V1` et
`H26_TEST_V1` au contrat d'autorité approuvé `236a84b4…`, dont le blob Git est
`dd5bcbff325e74f74e7bde4d425a11ac84aa264d`, et à l'implémentation dormante
revue `60b8d90b…`. Le materializer reste le blob
`2991c69db8a8816d0261c1fb6bb4e339e9408c11`.

Les trois liaisons scientifiques sont inchangées :

```text
scientific preregistration  8ecbb1da33e67e78bb76a2b0364d0d5c1697414a711418a030aafb000943b583
fixture specifications      c8e66f7f9d200451559bf538af5b6dd0b0e7131e042588b6f13ec8655804fc28
test manifest               f64b55a4b5dc21da0e2dc4bf9deb712073af59f3d67fd6e3d7d019ce8037e073
```

## Runtime primaire attendu

La qualification future vise uniquement
`H26_PRIMARY_MATERIALIZATION_RUNTIME` : CPython `3.11.9`, Darwin `24.5.0`
arm64, NumPy `1.26.4`, `_multiarray` de `3 164 400` octets au SHA-256
`6a88945a…`, et OpenBLAS ILP64 de `23 198 400` octets au SHA-256
`dde2b735…`. Toutes ces égalités seront exactes : aucun fallback, tolérance,
Accelerate de substitution ou remplacement Python/NumPy/BLAS n'est admis.

Le futur processus devra démarrer avec `MIDI_FORCE_CPU=1`, chacun des cinq
compteurs de threads à `1`, `PYTHONHASHSEED=0`, `LC_ALL=C`, `LANG=C` et
`TZ=UTC`. Ces valeurs devront être établies avant son démarrage, jamais
injectées après import.

Le runtime secondaire CPython `3.9.6` reste hors portée. Il n'est requis que
pour un éventuel test P2 cross-runtime ultérieur, séparément autorisé.

## Record futur sans auto-référence

Le schéma futur `H26_MATERIALIZATION_RUNTIME_QUALIFICATION_RECORD_V1` archive
les contrats et blobs liés, le rôle runtime, les valeurs attendues et
observées, l'environnement exact, ainsi que les chemins, tailles et SHA-256 de
l'exécutable, de `_multiarray` et de la bibliothèque BLAS.

Le contrat scientifique n'avait pas préenregistré le SHA de l'exécutable
primaire : aucune valeur attendue n'est inventée ici. Le chemin, la taille et
le SHA seront des observations futures. Le record ne contiendra jamais son
propre SHA ; son SHA brut sera calculé extérieurement après publication. Seul
un record `H26_MATERIALIZATION_RUNTIME_QUALIFIED`, puis revu séparément, pourra
être référencé par une future authority.

Les deux autres statuts définis sans être produits sont
`H26_MATERIALIZATION_RUNTIME_DISQUALIFIED` en cas de mismatch et
`H26_MATERIALIZATION_RUNTIME_QUALIFICATION_INCONCLUSIVE_CONSUMED` lorsqu'une
preuve requise ne peut être établie.

## Cycle futur fail-closed

Une qualification future nécessitera une nouvelle autorisation et un claim
distinct, consommé avant l'unique invocation de l'observer. Aucun retry avec
le même claim, correction automatique, installation, changement de runtime ou
publication partielle ne sera possible. Un record complet ne pourra être
publié que par opération atomique ; un record partiel restera non consommable.

Le futur observer pourra seulement constater plateforme, Python, exécutable,
NumPy, `_multiarray`, BLAS et environnement. Il ne devra importer aucun module
scientifique H26 ou materializer, générer aucun signal, exécuter aucun
FFT/NNLS ni calculer aucun outcome.

## Frontière actuelle

Les onze autorisations ou états courants sont tous `false` : il n'existe ni
qualifier, authority runtime, claim, exécution, record approuvé, authority de
matérialisation ou autorisation scientifique. Les valeurs du record courant,
de l'exécutable résolu et du statut terminal sont `null`.

Cette étape n'a lancé ni Python, NumPy, BLAS ni runtime secondaire. Elle n'a
créé aucun record, waveform, index, P2, population, destination, capability,
authority, claim, modèle, entraînement, calibration ou locked-test.

## Contrôles statiques autorisés

Les vérifications se limitent à `git diff --check`, à la liste exacte des trois
fichiers, aux SHA-256 bruts des trois configs scientifiques, aux blobs Git
liés, à la syntaxe JSON via `jq` seulement s'il est déjà installé, et à des
comparaisons textuelles des valeurs preregistrées. Aucun Python n'est lancé,
même pour valider le JSON.

Une revue externe de ce seul contrat est obligatoire. Son approbation ne
constituera aucune autorisation de qualification runtime ou de matérialisation.
