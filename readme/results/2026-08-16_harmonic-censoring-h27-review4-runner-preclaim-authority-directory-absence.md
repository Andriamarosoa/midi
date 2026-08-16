# H27 Review 4 — arrêt runner préclaim sur parent authority absent

## Autorisation

Après l'arrêt pré-mutation précédent, la revue externe a rendu
`PASS — reprise pré-ACK autorisée`. Elle a autorisé un bloc SSH unique créant
`review4` relativement à l'admin root, matérialisant les six octets scellés,
les vérifiant avant ACK, puis lançant une fois le runner exact.

## Bootstrap réussi

Le bloc a créé `/Users/amcarene/h27-admin/review4` en `0700` avec `mkdir`
relatif, `O_DIRECTORY|O_NOFOLLOW`, owner/mode et device/inode vérifiés, puis
`fsync(admin_fd)`. Les six fichiers ont été créés en `0400` via
`O_CREAT|O_EXCL|O_NOFOLLOW`, gardés ouverts pendant fsync/réouverture relative,
et revérifiés par taille, Git blob et SHA-256.

```text
H27_REVIEW4_DIRECTORY_CREATED_VERIFIED
BOOTSTRAP_FILE_OK h27_review4_execute_once.py 26604 44f3bd75... 5f56026e...
BOOTSTRAP_FILE_OK harmonic_censoring_h27_review4_materializer.py 33706 8cdafbd6... 2ecaabf1...
BOOTSTRAP_FILE_OK harmonic_censoring_h27_review4_materializer_identity_binding.json 5269 9371d80c... 204f6130...
BOOTSTRAP_FILE_OK harmonic_censoring_h27_review4_materializer_external_seal.json 1198 370eaf40... f396257c...
BOOTSTRAP_FILE_OK harmonic_censoring_h27_review4_execution_composition_identity_binding.json 5955 7a1437c4... 56b06449...
BOOTSTRAP_FILE_OK harmonic_censoring_h27_review4_execution_composition_external_seal.json 1640 7eb0f555... de9cc1c1...
H27_REVIEW4_BOOTSTRAP_ALL_IDENTITIES_VERIFIED_BEFORE_ACK
```

## Arrêt du runner

Après l'ACK, l'unique invocation du runner a échoué dans `preclaim()` en tentant
d'ouvrir le parent administratif relatif `authority` :

```text
FileNotFoundError: [Errno 2] No such file or directory: 'authority'
LOCAL_SSH_RC=1
```

L'échec se situe avant `consume_and_run()`, avant `write_new_at(AUTHORITY)`, et
donc avant :

- authority et claim;
- consommation capability/binding;
- NumPy et chargement du plan;
- staging, population et terminal;
- P0/P1/P2, science, locked-test et entraînement.

## Frontière

Les six artefacts bootstrap et le répertoire `review4` existent désormais et ne
doivent être ni remplacés, ni supprimés, ni réparés. Aucun retry n'est lancé.
Une nouvelle décision externe doit définir si les parents administratifs
manquants `authority`, `claims` et éventuellement `population` peuvent être
créés exclusivement en `0700`, avec les mêmes contrôles dirfd/no-follow, puis si
une nouvelle invocation du runner est autorisée malgré l'ACK précédent. La
frontière durable `AUTHORITY O_EXCL` n'a pas été atteinte.
