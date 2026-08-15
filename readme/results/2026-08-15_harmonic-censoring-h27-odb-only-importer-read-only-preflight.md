# H27 — préflight Mac lecture seule de l'importer ODB-only

Date : 2026-08-15
Branche : `codex/independent-note-neural-v2`
Importer revu PASS : `132e3da97180ce28c851b06e6a271430d7072292`

## Autorisation et portée

La revue externe autorisait uniquement un préflight Mac strictement lecture
seule de l'importer exact. Aucun ACK, `hash-object -w`, import ODB, fetch,
pull, sync, detach, registre, autorité, creator, bundle, matérialisation,
science ou locked test n'était autorisé.

Toutes les lectures Git ont utilisé `--no-optional-locks` et
`--no-replace-objects`. Aucun fichier Mac n'a été créé, modifié, copié ou
supprimé.

## État cible vérifié

```text
platform            Darwin
git                  2.39.5 (Apple Git-154)
checkout realpath   /Users/amcarene/midi-worker/repository
target ODB realpath /Users/amcarene/midi-worker/repository/.git
HEAD                 75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf
symbolic HEAD        refs/heads/codex/independent-note-neural-v2
worktree             clean
index.lock           absent
detach runner        absent
importer process     absent après le préflight
```

Snapshots lecture seule :

```text
regular refs sha256 d1e2a0579b854f5104d736e6e801ad60703938dbe25607bf7b14ee56b66442b9
index size          159298
index sha256        c92384509ec2f2f0c9d837aab0eb0bd32f8a78d2256ac421c9a12b2d97661907
object file count   1193
```

Root refs/pseudorefs présentes :

```text
FETCH_HEAD 125 627cbea355ed04a7e6354e2842ca9f799724894a1963de71c1aa8cfca26ee18a
HEAD        49 4560fdfefea5d5bfa81ecda627156750dab6821bfff1004d57b4a2d86cae3911
ORIG_HEAD   41 bfaa99996a57d274d3465d3c2f0210b805891ce82bf2226fd2898fb81c1e643a
```

Les huit payloads cibles sont tous absents de l'ODB cible, conformément à la
précondition de l'importer.

## Deux bloqueurs pré-effet

### 1. Format de refs non démontrable par la commande scellée

La commande exacte du contrat :

```text
git --no-optional-locks --no-replace-objects \
  --git-dir=/Users/amcarene/midi-worker/repository/.git \
  rev-parse --show-ref-format
```

retourne littéralement :

```text
--show-ref-format
```

et non `files`. Le Git Mac `2.39.5` ne fournit pas cette option sous la
sémantique attendue. L'importer échouerait donc fermé avant tout snapshot ou
effet.

### 2. ODB source sans les objets requis

L'ODB source candidat est réel et externe :

```text
/Users/amcarene/midi/.git
HEAD eaed599a5a051685288f1f71b3cb057db64392c2
branch refs/heads/codex/independent-note-neural-v2
```

Il ne contient aucun des treize objets contrôlés : contrat, seal, importer,
binding, binding seal et huit payloads. Aucun fetch/sync n'a été tenté.

## STOP

État terminal du préflight :
`H27_ODB_ONLY_IMPORTER_PREFLIGHT_BLOCKED_REF_FORMAT_COMMAND_UNSUPPORTED_AND_SOURCE_OBJECTS_ABSENT_NO_EFFECT`.

Aucun ACK ni import n'est consommé. Prochaine action unique : revue externe de
ce blocage avant toute correction de contrat, mise à niveau Git, apport des
objets source ou nouvelle commande Mac.
