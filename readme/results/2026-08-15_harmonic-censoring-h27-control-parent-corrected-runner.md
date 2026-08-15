# H27 — runner corrigé dormant du parent `control`

Date : 2026-08-15  
Branche : `codex/independent-note-neural-v2`  
Base approuvée : `da614f836e129df9a94534fae621e823ddef1d99`

## Portée

Ce lot implémente seulement le nouveau runner POSIX one-shot corrigé, son
binding d'identité, son seal externe, les tests structurels et la mise à jour
du journal. Aucun accès Mac, ACK, création de dossier, registre, réservation
d'autorité, creator, bundle, constructeur, matérialisation, calcul scientifique
ou locked test n'a été exécuté.

## Frontière corrigée

- parent exact : `/Users/amcarene/h27-admin` ;
- device exact : `16777234` ;
- inode exact : `1445438` ;
- cible exacte : `/Users/amcarene/h27-admin/control` ;
- type/mode exacts : directory `0700` ;
- ACK futur exact : `H27_CONTROL_PARENT_CREATE_EXECUTE=1` ;
- zéro argument ;
- exécution future uniquement depuis le blob Git revu.

Le runner rehache d'abord les deux racines correctives approuvées et les neuf
identités transitives qu'elles lient, soit onze identités uniques avant toute
observation du parent. Il ouvre ensuite le parent avec
`O_NOFOLLOW|O_DIRECTORY`, vérifie `device/inode`, effectue une unique sonde
d'absence de `control`, revalide le parent, puis réserve `mkdir(control, 0700)`
comme premier et unique effet irréversible. Après `fsync(parent)`, il rouvre la
cible sans suivre de lien et vérifie type, mode, device et inode par descripteur
et nom avant la revalidation finale du parent.

## Ancien runner

Le blob stale `96df05111a5e40a418e12fb2b3db4bd9516bcab3` reste :

- autorisation d'exécution révoquée ;
- non exécutable dans ce contrat ;
- jamais exécuté ;
- jamais consommé ;
- ACK non posé ;
- `mkdir` jamais tenté.

## Validation locale

- `py_compile` du runner corrigé et du test : réussi ;
- tests ciblés du runner, binding et seal : `6/6` réussis ;
- suite H27 complète avec le venv du projet : `500/500` réussis en
  `77,373 s` ;
- identités JSON exactes et absence de clés dupliquées vérifiées par les
  tests ;
- `git diff --check` : requis avant commit ;
- worktree propre : requis après commit/push.

## État et prochaine action

État :
`CORRECTED_RUNNER_TEST_CLOSURE_PENDING_EXTERNAL_REVIEW`.

La première revue externe du commit `2f0fb5c7...` a conclu `FAIL` sur un seul
point : le test ne verrouillait pas encore tous les dictionnaires du binding et
le seal complet. La micro-correction compare maintenant exactement les
métadonnées du binding, `execution_binding`, l'état stale, les safeguards,
`current_state`, `next_action` et le dictionnaire entier du seal. Le runner, le
binding et le seal restent byte-identiques aux blobs `2b2bd6e5...`,
`08366caf...` et `1052ff54...`.

Revalidation après micro-correction : `6/6` tests ciblés et `500/500` tests
H27 en `75,639 s`, avec `py_compile` et `git diff --check` réussis.

Prochaine action unique : revue externe de cette fermeture mécanique. Aucune
exécution Mac n'est autorisée par ce lot.

## Préflight Mac lecture seule après PASS

La revue externe de `421fd7d39ec429b149c265eadcdca7cd056568fd` a
conclu `PASS` et autorisé exclusivement le préflight lecture seule, suivi d'un
STOP.

Résultat vérifié :

- branche distante : `421fd7d39ec429b149c265eadcdca7cd056568fd` ;
- checkout Mac inchangé : `75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf` ;
- ODB réel : `/Users/amcarene/midi-worker/repository/.git` ;
- runner : type `blob`, `10126` octets, SHA-256
  `37e40a4ec03bdeef4d7a1ec8826c41b4b0b98bc76aeda252d1e2a6d834be8b4b` ;
- identités prédécesseures vérifiées : `11` ;
- parent : directory réel, non-symlink, device `16777234`, inode `1445438` ;
- `/Users/amcarene/h27-admin/control` : absent ;
- processus correspondant aux deux runners : `0` ;
- ACK : absent ;
- appel `create()` : non effectué ;
- runner exécuté : faux ;
- tentative `mkdir` : fausse.

Le premier essai de commande de préflight a fetché correctement la branche,
puis s'est arrêté avant l'ODB parce que PowerShell avait développé localement
une substitution de commande. Deux essais ultérieurs de vérification Python
ont échoué uniquement sur le quoting de `python3 -c`, avant tout appel au
runner ou accès au parent. La commande corrigée a ensuite effectué le contrôle
lecture seule ci-dessus. Ces anomalies de commande n'ont posé aucun ACK et
n'ont produit aucun effet filesystem Mac.

STOP respecté : aucune exécution du runner corrigé, aucun `mkdir`, registre,
autorité, creator, bundle, constructeur, matérialisation, science ou locked
test. La prochaine action reste une revue externe de cette preuve avant toute
éventuelle exécution réelle one-shot.
