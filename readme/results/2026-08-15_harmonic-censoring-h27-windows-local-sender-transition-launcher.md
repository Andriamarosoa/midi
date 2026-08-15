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
- launcher corrigé après consommation : `8249cb84e072afdfdd4420d650412dea6f1a3521`, `24190` octets,
  SHA-256 `c6a3444d04c660244c3f97535c1ab1115cefc7eebd43abacc04e7f7fc6c8f528` ;
- binding launcher : `4ae98cd08d47be174e75236b6bb6edd30d53bec4`, `5251` octets,
  SHA-256 `765a752ea77ac0039b27908db9a0a9751b7e46122a3a53e3d2554fe640f33b49`.

- seal launcher : `b02e86662499ca07ccf2833b67c14a104dff2a87`, `4922` octets,
  SHA-256 `4d2c2e0fe469f1e487f87e44e2917ba78fada13f2bb59407a9abaadbfe417113`.

## Validation

Les tests sont synthétiques, structurels et read-only vis-à-vis du worktree
d'exécution. Ils ne lancent jamais le launcher réel. Ils couvrent les key sets,
identités, environnement Git fermé, graphe ODB exact, ordre succès, échec
pré-effet, échec sender consommé, échec de restauration terminal, rapport
sender strict, append exact des deux reflogs et absence d'exécution SSH.

- tests contrat + launcher après correction : `16/16` en `1.544 s` ;
- `py_compile` : réussi ;
- `git diff --check` : réussi.

Le worktree d'exécution reste sur `61dc4b49...`, branche symbolique exacte et
propre. `locked_test_used=false`; impact live/scientifique nul.

## STOP

La revue externe du commit `c526aa14...` a rendu `PASS` et autorisé une unique
exécution. Elle a été consommée le 2026-08-15.

Le launcher a atteint le sender sans erreur primaire, puis a effectué le reset
de restauration. La vérification finale a échoué quand `git status` a refusé
l'index restauré : `unknown index entry format 0x735f0000`. L'index corrompu
mesure `169704` octets, SHA-256
`82367d517f483cbd03c90b8099dccdefdd29a18326e45b191bb957fc9b3c3879`.
L'index reconstruit depuis le HEAD mesure `169506` octets ; les `198` octets de
différence correspondent exactement aux `198` paires CRLF introduites par une
écriture Windows en mode texte. La cause est l'absence de `os.O_BINARY` sur les
descripteurs exclusifs utilisés pour les restaurations index et fichiers.

Conformément au contrat, aucune seconde invocation n'a eu lieu. L'index fautif
est préservé sous
`.git/worktrees/independent-note-neural-v2/index.h27-consumed-corrupt-20260815`.
Une intervention manuelle bornée a déplacé cet index puis exécuté uniquement
`git read-tree 61dc4b49...`. L'état final contrôlé est : HEAD et refs locales/
remote-tracking à `61dc4b49...`, branche symbolique exacte, status propre.

Le code historique est corrigé avec `O_BINARY` et un test Windows qui restaure
un payload contenant LF, CRLF, `0x1a` et `0xff` à l'identique. Cette correction
est archivale : la tentative reste consommée, son launcher ne doit jamais être
relancé. Aucun SSH, ACK distant, transport, import, detach, downstream, locked
test ou science n'a été exécuté.

Prochaine étape : review 2/5 consacrée à la livraison directe et contrôlée des
treize blobs vers le Mac. Aucun nouveau contrat/seal/micro-gate du bloc 1.
