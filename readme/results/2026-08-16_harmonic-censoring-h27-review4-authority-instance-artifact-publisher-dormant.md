# H27 Review 4 — publisher dormant de l'authority-instance

## Verdict interne

`ATOMIC_EXCLUSIVE_RENAME_CORRECTION_SUCCESS_STOP_PENDING_EXTERNAL_REVIEW`.

La preuve terminale du constructor gate archivée dans `6e792bf710595319d7ee85d28ee2d186463546c7`
a reçu un `PASS` externe. Le gate est consommé et n'est jamais rejoué. La seule
action autorisée ici est l'implémentation locale et dormante du publisher exact.

## Artefact figé

Le runner n'appelle ni horloge ni générateur aléatoire. Il reconstruit seulement
l'instance déjà consommée :

```text
authority_instance_id=d44941a8c1c6674e5da89c40a7e3188c4e6318f7c5759ce490577d8bde81437a
issuer_id=h27-execution-codex-mac-primary
issued_at_utc=2026-08-16T08:36:14Z
invocation_nonce=c8c7dc8162910a140bc1699b488478b8f9f343a855973453671f6cacdfcea165
destination=/Users/amcarene/h27-admin/activation/h27-materialization-v1.json
single_use=true
consumed=false
size=882
git_blob_sha1=dc85ee260763f9f9e65bbafbd776bf8611a67d9c
sha256=89d03ce3ea8f31a253b4e245e0357236e20860d409c27f0779a003d058fe91d2
```

## Runner dormant

```text
scripts/h27_review4_authority_instance_artifact_publish_once.py
ACK=H27_REVIEW4_AUTHORITY_INSTANCE_ARTIFACT_PUBLISH_EXECUTE
arguments=0
expected_platform=darwin
expected_detached_head=46a6bdf81a56a7a7a10524d4e55092301a452207
```

Avant toute consommation, le runner :

1. exige l'ACK exact, macOS et zéro argument ;
2. vérifie le checkout détaché/propre, le HEAD et l'absence d'`index.lock` ;
3. découvre le graphe normatif depuis les blobs immuables du HEAD ;
4. rehash les 92 identités correspondantes dans le checkout ;
5. exige les deux lignes exactes du registre constructor, `reserved` puis
   `consumed`, en mode `0600` ;
6. refuse un processus publisher/materializer/science concurrent ;
7. ouvre et ancre une fois les parents registry et activation avec
   `O_DIRECTORY|O_NOFOLLOW` ;
8. répète les validations immédiatement avant la frontière one-shot.

La première revue externe de `22aefd65098e0db089303b2c83b4ae0cb92ca912`
a rendu un `FAIL` limité : l'écriture directe du fichier final ne respectait
pas l'atomic rename transitivement scellé. Aucun Mac ni ACK réel n'avait été
utilisé.

La future frontière irréversible est la création exclusive du registre de
publication relatif au parent registry conservé. Le record `consumed` est écrit
et fsyncé avant toute observation de la destination. Ensuite seulement, la
destination finale est sondée relativement au parent activation conservé. Un
staging déterministe est créé dans ce même parent avec
`O_CREAT|O_EXCL|O_NOFOLLOW`, écrit avec les 882 octets exacts et fsyncé. Le
runner appelle ensuite exclusivement `renameatx_np(..., RENAME_EXCL)` vers le
nom final, sans fallback vers `rename` ou `replace`, fsync le parent, puis
rouvre le final par le même descripteur et le rehache. Le descripteur du staging
reste ouvert pendant le rename et son inode est comparé au final. Tout échec
post-consommation est terminal, sans retry, suppression, nettoyage ou
réparation automatique ; un staging éventuel est conservé comme preuve.

## Validation locale

```text
python -B -m unittest \
  tests.test_harmonic_censoring_h27_review4_authority_instance_artifact_publish \
  tests.test_harmonic_censoring_h27_review4_constructor_execution_gate

Ran 23 tests
OK
```

Les tests ajoutés interdisent l'ouverture directe du final avec `O_CREAT`,
prouvent l'ordre staging/write/fsync/exclusive-rename/parent-fsync/reopen et
simulent une destination apparue juste avant le rename : elle n'est jamais
écrasée. Un test séparé vérifie l'appel Darwin `renameatx_np` avec
`RENAME_EXCL` et l'absence de fallback si cette primitive est indisponible.

`py_compile` passe pour le runner et son test. Une exécution complémentaire de
quatre modules a rendu `24/26`; les deux échecs sont les contrôles LF de deux
anciens contrats checkoutés CRLF sous Windows. Aucun invariant fonctionnel du
nouveau runner n'a échoué et les blobs Git LF utilisés par celui-ci restent
byte-exacts. Cette limite d'environnement est archivée sans modifier les
anciens artefacts scellés.

## Frontières conservées

- aucun SSH ni accès Mac ;
- aucun ACK réel ;
- aucun registre de publication créé ;
- aucune observation ou création de la destination ;
- aucun materializer, P0/P1/P2 ou population ;
- aucune science, locked-test, training ou calibration ;
- aucune autorisation d'exécution implicite.

Prochaine action unique : revue externe du commit complet. Toute publication
réelle attend un `PASS` séparé sur les octets exacts du runner.
