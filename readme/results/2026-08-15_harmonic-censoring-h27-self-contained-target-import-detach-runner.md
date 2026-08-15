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
7/7 tests Review 3 réussis
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
H27_REVIEW_3_SELF_CONTAINED_TARGET_IMPORT_AND_DETACH_IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_MAC_EXECUTION
```
