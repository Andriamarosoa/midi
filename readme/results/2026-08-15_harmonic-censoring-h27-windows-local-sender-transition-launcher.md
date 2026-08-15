# H27 — launcher dormant de transition locale Windows

## Verdict local

Le launcher one-shot est implémenté uniquement dans le worktree auxiliaire de
revue. Il reste dormant : aucun ACK d'exécution, reset, sender, SSH, transport,
objet Git distant ou calcul scientifique n'a été exécuté.

État :
`H27_WINDOWS_LOCAL_HISTORICAL_SENDER_TRANSITION_LAUNCHER_DORMANT_PENDING_EXTERNAL_REVIEW`.

## Frontière exacte

Le launcher est destiné à être chargé ultérieurement depuis son blob Git revu
et exécuté par le Python exact via stdin, jamais depuis sa copie checkout. Il
exige Windows, zéro argument et
`H27_WINDOWS_LOCAL_SENDER_TRANSITION_EXECUTE=1`. Chaque commande Git utilise le
préfixe littéral scellé, supprime tous les `GIT_*` hérités, interdit les
opérations réseau et vérifie le worktree d'exécution exact à `61dc4b49...`.

Avant le premier effet, il capture puis revalide HEAD, arbre, branche, refs,
status, index brut, entrées d'index, inventaire ODB et octets bruts de tous les
fichiers suivis. Les dix blobs du graphe sender/receiver/contrats/bindings/seals
sont lus et rehachés depuis l'ODB avant le premier reset.

La future séquence autorisée est strictement :

1. reset historique unique vers `c0bb8d20...` ;
2. vérification complète de l'état historique ;
3. invocation unique des bytes sender prévalidés et exigence de
   `transport_executed=false` ;
4. reset de restauration unique vers `61dc4b49...` ;
5. restauration atomique/fsync des octets bruts suivis, puis de l'index brut ;
6. vérification byte/state-exacte et STOP avant SSH.

Après le premier reset, toute erreur consomme la transition. Le sender n'est
jamais retenté. Une seule restauration est tentée ; son échec exige une
intervention manuelle et interdit tout second cleanup/repair/rollback.

## Durcissement Windows CRLF

Le worktree auxiliaire utilise `core.autocrlf=true`. Un simple aller-retour
`reset --hard` pourrait donc restaurer le contenu logique tout en changeant les
octets LF/CRLF. Le contrat et son seal sont renforcés pour conserver en mémoire
les octets bruts suivis avant le premier effet et les restaurer par fichiers
temporaires frères exclusifs, `fsync` et renommage atomique avant de restaurer
l'index. La vérification terminale compare le snapshot brut complet.

## Identités

- contrat renforcé : `f1a394bb9c764e0d1942f10cf36711517dcb5f4b`, `10871` octets,
  SHA-256 `499fb31e73c5fc8b371d9c0a2f860e58dd614b58afa0cbca900755c19d3f1a70` ;
- seal du contrat : `eb5888e8f03b3c558dd3fcedc6d4bf44c898b911`, `5828` octets,
  SHA-256 `415b140882a981ee2dd0ab3ca0c4aeedf14eeeaeb1832d5eb9b92fef02371fd6` ;
- launcher : `25d06a49e5d4fffe0764de875dc83f937ac8d5c0`, `24083` octets,
  SHA-256 `4e764f3731c28a691bba2cf6844ff5b73e311d2e13baf898cdae1c2b14f089fd` ;
- binding launcher : `ee5e54aa27b099e04a24f930ee63ed6e5959b889`, `5298` octets,
  SHA-256 `f7c6e3c89c5060702b251a56c47dbc2bab66e0d3f2a1f5d56e6b9fcb0478071a`.

- seal launcher : `02e692e45b68478beb8f0c21d47a2761c5959a43`, `4993` octets,
  SHA-256 `75a7f7c4a122772b7b5a35d54df758671fec9a01b1c7bd58d98f59b7eabf5d4c`.

## Validation

Les tests sont synthétiques, structurels et read-only vis-à-vis du worktree
d'exécution. Ils ne lancent jamais le launcher réel. Ils couvrent les key sets,
identités, environnement Git fermé, graphe ODB exact, ordre succès, échec
pré-effet, échec sender consommé, échec de restauration terminal, rapport
sender strict, append exact des deux reflogs et absence d'exécution SSH.

- tests contrat + launcher : `15/15` en `1.336 s` ;
- `py_compile` : réussi ;
- `git diff --check` : réussi.

Le worktree d'exécution reste sur `61dc4b49...`, branche symbolique exacte et
propre. `locked_test_used=false`; impact live/scientifique nul.

## STOP

STOP avant toute exécution réelle. Prochaine action unique : revue externe du
launcher, de son identity binding, de son external seal, des tests et de ce
rapport. Aucun reset, sender, SSH, ACK distant ou transport avant un nouveau
`PASS` explicite.
