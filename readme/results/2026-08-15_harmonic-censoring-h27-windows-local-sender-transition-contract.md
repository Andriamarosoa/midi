# H27 — contrat de transition locale Windows vers le sender historique

## Verdict local

Le contrat déclaratif et son external seal ont été créés dans un worktree de
revue auxiliaire puis approuvés au commit `469b3f400358690af628f872b56696a8df368e64`.
Ils sont renforcés dans le lot launcher pour conserver et restaurer aussi les
octets bruts suivis malgré `core.autocrlf=true`. Aucune transition,
commande `reset`, exécution du sender, ACK, SSH ou livraison n'a eu lieu.

État :
`H27_WINDOWS_LOCAL_HISTORICAL_SENDER_TRANSITION_CONTRACT_ONLY_PENDING_EXTERNAL_REVIEW`.

## Topologie anti-récurrence

La branche et le worktree d'exécution sont préservés byte/state-exactement :

- branche : `codex/independent-note-neural-v2` ;
- chemin :
  `C:\Users\user\Desktop\midi\tmp\local\worktrees\independent-note-neural-v2` ;
- HEAD : `61dc4b496a454b596fca6ac361504f441e987aab` ;
- worktree : propre.

Le contrat évolue séparément sur :

- branche auxiliaire : `codex/h27-windows-transition-contract` ;
- base : `61dc4b496a454b596fca6ac361504f441e987aab` ;
- worktree auxiliaire :
  `C:\Users\user\Desktop\midi\tmp\local\worktrees\h27-windows-transition-contract`.

Le futur launcher devra être chargé depuis son blob Git scellé dans l'ODB
partagé et exécuté par bytes/stdin. Lire son fichier depuis le checkout
auxiliaire sera interdit. Ainsi, les futurs commits de revue ne déplacent pas
l'état initial exigé du worktree d'exécution.

## Transition future scellée

Après un ACK local distinct et avant le premier effet, le futur launcher devra
capturer HEAD, symbolic HEAD, ref locale, ref remote-tracking locale, status,
index brut, arbre index, lock et manifeste byte-exact des fichiers suivis. Il
chargera et rehachera en mémoire sender, receiver, contrats, bindings et seals.

L'unique séquence mutante future est :

1. un seul `reset --hard` local vers
   `c0bb8d20862f80cabc72ea64a5d437750b7c12e8` ;
2. vérification du HEAD, de la branche symbolique non détachée, de la ref, de
   la propreté et de l'absence de lock ;
3. une seule invocation du sender exact par
   `C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -`, depuis ses bytes
   prévalidés, qui doit rendre
   `H27_SOURCE_ODB_EXACT_THIRTEEN_SENDER_PREPARED_DORMANT_STOP` et
   `transport_executed=false` ;
4. une seule restauration par `reset --hard` vers `61dc4b49...` ;
5. restauration atomique des octets bruts originaux des fichiers suivis, puis
   restauration atomique des bytes originaux de l'index et vérification
   finale byte/state-exacte de HEAD, branche, refs, index, fichiers suivis et
   status ;
6. archivage et STOP avant SSH.

Aucun push/fetch/pull, aucune modification de ref remote-tracking et aucune
opération réseau Git ne sont permis. Les seuls deltas administratifs locaux
persistants attendus sont les deux entrées de reflog scellées et la conséquence
`ORIG_HEAD` des deux resets.

## Politique d'échec

- avant le premier effet : échec sûr, sans consommation ;
- après le premier reset : tentative consommée ; aucune seconde invocation du
  sender ;
- après tout résultat post-effet : exactement une tentative obligatoire de
  restauration ;
- restauration réussie après un échec : terminal consommé et restauré, aucun
  retry ;
- restauration échouée : terminal consommé nécessitant intervention manuelle,
  sans seconde restauration, cleanup, repair ou prétention de rollback.

## Identités

- contrat renforcé : blob `f1a394bb9c764e0d1942f10cf36711517dcb5f4b`, `10871` octets,
  SHA-256 `499fb31e73c5fc8b371d9c0a2f860e58dd614b58afa0cbca900755c19d3f1a70` ;
- external seal renforcé : blob `eb5888e8f03b3c558dd3fcedc6d4bf44c898b911`, `5828` octets,
  SHA-256 `415b140882a981ee2dd0ab3ca0c4aeedf14eeeaeb1832d5eb9b92fef02371fd6`.

## Validation et limites

Les tests sont strictement structurels/read-only. Ils ferment les dictionnaires,
vérifient l'identité du contrat, la topologie auxiliaire, les commandes exactes,
la politique d'échec et l'état dormant. Un contrôle live read-only confirme que
le worktree d'exécution est encore sur `61dc4b49...`, branche symbolique exacte
et propre.

- tests ciblés du nouveau contrat : `5/5` en `0.147 s` ;
- `git diff --check` : réussi.

Une tentative de suite H27 globale depuis le worktree auxiliaire fraîchement
créé a été arrêtée après l'apparition immédiate de nombreux échecs structurels
historiques : ces anciens tests rehachent les fichiers du checkout, que la
configuration Windows matérialise en CRLF, puis les comparent aux identités des
blobs Git LF. Un lot ciblé contrat/receiver/sender/transition a confirmé ce
diagnostic : `22/27` passent et les `5` échecs sont les assertions canoniques
LF/identité sur les copies checkout anciennes. Ce résultat n'est pas présenté
comme une suite réussie. Les blobs ODB approuvés restent inchangés et le contrat
interdit précisément au futur launcher de lire les copies checkout auxiliaires.
La dernière suite H27 complète sur le worktree d'exécution préservé à
`61dc4b49...` reste la preuve antérieure `547/547` en `99.830 s` ; elle n'a pas
été relancée car aucun fichier de ce worktree n'a changé.

Impact live/scientifique : nul. `locked_test_used=false`.

## Suite approuvée

La revue externe du commit `469b3f4...` autorise l'implémentation dormante du
launcher dans le worktree auxiliaire. Les `reset`, `switch`, `update-ref` dans
le worktree d'exécution, le sender, SSH, l'ACK Mac et le transport restent
interdits jusqu'à la revue séparée de ce launcher exact.
