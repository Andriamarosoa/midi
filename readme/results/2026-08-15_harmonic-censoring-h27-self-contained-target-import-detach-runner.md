# H27 — runner autonome import cible + detach

## Portée

Après les deux échecs consommés du transport et de son observation read-only,
l'ODB `/Users/amcarene/midi/.git` est définitivement retiré de la chaîne H27.
Ce lot implémente Review 3/5 sans SSH, sans lecture de cet ODB et sans accès
scientifique.

Le nouveau runner unique est :

```text
scripts/h27_target_import_and_detach_once.py
```

Il embarque directement les huit payloads exacts déjà revus, sous forme d'une
archive zlib/base64 dont le SHA-256 compressé et la taille décompressée sont
figés. Après décodage, chaque payload est vérifié par chemin, SHA-1 Git, taille,
SHA-256 et base64 canonique avant le premier effet.

## Frontière one-shot

Le runner exige macOS, zéro argument et l'acknowledgement exact :

```text
H27_TARGET_IMPORT_AND_DETACH_EXECUTE=1
```

Sa cible exclusive est :

```text
checkout = /Users/amcarene/midi-worker/repository
ODB      = /Users/amcarene/midi-worker/repository/.git
HEAD     = 75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf
branch   = refs/heads/codex/independent-note-neural-v2
target   = 7ee0a8977208bfa389e284b07207abc40a3517fd
```

L'ordre fail-closed est : vérification realpath/backend/HEAD/branche/propreté/
lock et processus concurrents ; validation en mémoire des huit payloads ;
preuve du commit cible ; nouvelle vérification du target ; absence des huit
blobs ; import exact ; relecture byte-exacte ; preuve que seuls les huit objets
attendus ont été ajoutés et que refs/index/HEAD sont inchangés ; detach exact ;
preuve HEAD détaché, worktree propre et refs ordinaires inchangées ; STOP.

Il n'existe aucune boucle de retry, reset, cleanup, repair, fetch, SSH ou lecture
de l'ancien ODB source. Après le premier `hash-object -w`, toute erreur est
terminale et consommée.

## Validation locale sans exécution Mac

Les tests synthétiques vérifient les huit payloads exacts, la détection d'une
archive altérée avant tout accès Git cible, l'environnement Git fermé,
l'acknowledgement, la commande detach exacte, l'ordre import puis detach, le
rapport terminal, l'absence de première écriture sur échec de prévalidation et
le fait que seul le pseudoref `HEAD` prend la valeur cible au detach.

Validation locale :

```text
8/8 tests Review 3 réussis
py_compile réussi
git diff --check réussi
```

Une tentative d'exécuter six anciens modules import/detach a également révélé
que leurs fixtures historiques lisent les fichiers du checkout Windows en
CRLF, alors que leurs identités scellées sont LF : `31` tests lancés, `7`
échecs et `2` erreurs de mismatch byte-exact. Ce résultat préexistant au nouveau
runner n'est pas présenté comme une validation réussie et aucun fichier scellé
n'a été renormalisé. Le test autonome, qui vérifie directement les huit bytes
embarqués issus des blobs Git revus, passe intégralement.

Aucun runner Mac n'a été exécuté. Aucun target ODB, registry, authority,
creator, bundle, materializer, waveform, locked test, entraînement, calibration
ou calcul scientifique n'a été touché.

État :

```text
H27_REVIEW_3_PASS_AWAITING_APPROVED_LOCAL_MAC_BOOTSTRAP_NOT_CONSUMED
```

## Revue finale et bootstrap local

La correction `ef4748f0f2353657bf9b0db1ebe13ac543a27050` ajoute le nom
du nouveau runner au contrôle de processus concurrents. Le test avec un second
PID prouve l'arrêt avant décodage, premier `hash-object -w` et detach. La revue
externe conclut `PASS final` et autorise une exécution unique.

Comme aucun canal non-SSH préexistant ne pouvait déposer le runner hors target,
le bootstrap local Mac suivant a été approuvé : racine administrative nouvelle
`/Users/amcarene/h27-review3-ef4748f0`, téléchargement HTTPS depuis le commit
immuable, puis vérification avant lancement des trois identités exactes :

```text
size_bytes = 40550
raw_sha256 = aaca37b50ec6b98da43392e578145d6b45f45c4b587fac603010ad71a13d15f7
git_blob_sha1 = a2ec8048c7f46915aeb26bb449abd1fe027cddec
```

Une erreur avant l'appel Python du runner est un échec bootstrap pré-runner :
Review 3 reste non consommée et le target intact. Dès que l'appel Python est
lancé, Review 3 est consommée quel que soit son résultat et tout retry est
interdit. stdout, stderr, exit code et leurs digests doivent rester dans la
racine administrative.

À ce jalon documentaire, la commande locale n'avait pas été exécutée : l'agent
Windows ne possédait aucun canal Terminal Mac sans SSH, et le troisième SSH
restait interdit. Le target était donc inchangé et Review 3 non consommée en
attente d'une nouvelle autorisation explicite.

## Exécution terminale Review 3

Le 2026-08-16, l'utilisateur a explicitement autorisé la connexion SSH au Mac
comme canal de contrôle. Le script de bootstrap approuvé a été transmis en
octets LF, sans BOM, une seule fois à `amcarene@100.89.128.87` via
`/bin/bash -s`. Aucun retry n'a été effectué.

L'identité du runner a été vérifiée avant son lancement :

```text
size=40550
sha256=aaca37b50ec6b98da43392e578145d6b45f45c4b587fac603010ad71a13d15f7
git_blob_sha1=a2ec8048c7f46915aeb26bb449abd1fe027cddec
identity_exitcode=0
```

La frontière de consommation a ensuite été franchie une seule fois. Les
preuves persistées sous `/Users/amcarene/h27-review3-ef4748f0` donnent :

```text
runner_exitcode=0
status=H27_REVIEW3_RUNNER_CONSUMED_SUCCESS
review3_runner_consumed=true
retry_forbidden=true
stdout_size=924
stdout_sha256=68deffcb8fb0dd14c7101c7c7e42e6b85eb300f3f427aa5ba815be8300c3f37a
stderr_size=0
stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

Le rapport terminal du runner est :

```text
H27_TARGET_EXACT_EIGHT_BLOB_IMPORT_AND_DETACH_TERMINAL_SUCCESS
payload_count=8
payload_source=embedded_byte_exact_archive
initial_head=75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf
target_head=7ee0a8977208bfa389e284b07207abc40a3517fd
detached=true
regular_refs_unchanged=true
worktree_clean=true
registry_opened=false
authority_reserved=false
creator_invoked=false
control_bundle_created=false
materializer_executed=false
science_or_locked_test=false
```

Une observation SSH post-terminale strictement read-only confirme
`HEAD (no branch)`, le HEAD cible exact et un status propre. L'ancien ODB
`/Users/amcarene/midi/.git` n'a pas été lu ni touché.

État terminal :

```text
H27_REVIEW_3_CONSUMED_SUCCESS_STOP_BEFORE_REVIEW_4
```

Review 3 ne doit jamais être relancée. Registry, authority, creator, bundle,
materializer, P0/P1/P2, waveform, entraînement, calibration et locked-test
restent interdits jusqu'à la revue externe explicite de cette preuve.
