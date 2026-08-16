# H27 Review 4 — arrêt préclaim sur métadonnées NumPy absentes

## Autorisation

La revue externe de `d89403a304d212e61c6dabbe429aea89b67bd390` a rendu
`PASS — nouvelle reprise autorisée`. Elle a autorisé un bloc SSH unique qui
devait revalider les six artefacts bootstrap existants, vérifier l'absence puis
créer exclusivement `authority`, `claims` et `population` en `0700`, exporter
l'ACK et lancer exactement une fois le runner scellé.

## Préparation administrative réussie

Le bloc a revalidé les six fichiers existants en `0400` par taille, Git blob et
SHA-256, sans remplacement ni réécriture. Il a ensuite vérifié l'absence des
trois parents, puis les a créés relativement au descripteur de
`/Users/amcarene/h27-admin` et vérifiés par type, owner, mode et device/inode,
avec `fsync(admin_fd)` après chaque création.

```text
REVALIDATED h27_review4_execute_once.py 26604 44f3bd75... 5f56026e...
REVALIDATED harmonic_censoring_h27_review4_materializer.py 33706 8cdafbd6... 2ecaabf1...
REVALIDATED harmonic_censoring_h27_review4_materializer_identity_binding.json 5269 9371d80c... 204f6130...
REVALIDATED harmonic_censoring_h27_review4_materializer_external_seal.json 1198 370eaf40... f396257c...
REVALIDATED harmonic_censoring_h27_review4_execution_composition_identity_binding.json 5955 7a1437c4... 56b06449...
REVALIDATED harmonic_censoring_h27_review4_execution_composition_external_seal.json 1640 7eb0f555... de9cc1c1...
CREATED_VERIFIED authority
CREATED_VERIFIED claims
CREATED_VERIFIED population
H27_REVIEW4_PARENTS_AND_BOOTSTRAP_VERIFIED_BEFORE_ACK
```

## Arrêt du runner

Après l'ACK, le runner exact a été invoqué une fois. Il a terminé `rc=1` dans
`preclaim()` pendant `verify_runtime()`, avant `consume_and_run()` :

```text
importlib.metadata.PackageNotFoundError: No package metadata was found for numpy
LOCAL_SSH_RC=1
```

Le Python utilisé était le chemin scellé :

```text
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11
```

## Frontière

Dans le runner scellé, `verify_runtime()` est appelé dans `preclaim()` avant le
retour vers `consume_and_run()`. Le fichier AUTHORITY n'a donc pas été créé,
CLAIM n'a pas été créé et la capability one-shot n'a pas été consommée. Aucun
plan, staging, population, terminal, P0/P1/P2, entraînement, locked-test ou
calcul scientifique n'a été exécuté.

Les répertoires administratifs `authority`, `claims` et `population` existent
désormais et ne doivent être ni supprimés, ni remplacés, ni modifiés pour un
retry automatique. Aucun nouveau SSH n'est lancé. Une revue externe doit
décider si et comment le runtime scellé peut retrouver exactement NumPy 1.26.4
sans changer l'identité Python ni franchir silencieusement la frontière.
