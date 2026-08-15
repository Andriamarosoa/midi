# H27 — receiver dormant exact des treize blobs de l'ODB source

Date : 2026-08-15
Branche : `codex/independent-note-neural-v2`
Autorisation amont : PASS du préflight `2211f1d6c4b95b93f19dce3c607d478b5697a153`

## Portée

Implémentation dormante dans le dépôt de revue uniquement : receiver Python
auto-contenu, identity binding, external seal, tests synthétiques et
documentation. Aucun SSH, accès Mac, ACK
`H27_SOURCE_ODB_EXACT_THIRTEEN_EXECUTE=1`, transport stdin, écriture ODB,
import cible, detach, downstream, science ou locked test.

## Receiver

Le receiver exact est :

```text
scripts/h27_receive_exact_thirteen_source_odb_blobs_one_shot.py
blob    9d32cac8ddb29e43975a6b82f5c1c39a91f93df4
size    119406
sha256  996c4539a357b13af65012de84ed836179389f111dd1849eb1ca165d15374000
```

Il contient les treize blobs du contrat, dans l'ordre déclaré, sous forme de
littéraux base64 RFC 4648 canoniques. Leur taille brute agrégée est `75730`
octets. La phase de décodage des treize objets est complète avant le début de
la phase de validation identité/taille/SHA-256/blob Git.

Le chemin dormant impose :

```text
Darwin + ACK exact + zéro argument
→ realpaths checkout/.git/objects/refs
→ preuve backend files Apple Git 2.39
→ décodage et prévalidation intégrale en mémoire
→ HEAD/symbolic HEAD/propreté/lock/processus
→ snapshots refs/root refs/index/ODB
→ revalidations + absence des 13 blobs
→ unique frontière de 13 hash-object -w --stdin ordonnés
→ relecture byte-exacte des 13 blobs
→ delta exact de 13 loose objects et invariants inchangés
→ succès terminal puis STOP
```

Chaque subprocess Git repart de l'environnement courant sans aucune variable
héritée `GIT_*`, puis réintroduit uniquement `GIT_TERMINAL_PROMPT=0` et
`GIT_NO_LAZY_FETCH=1`. ODB et worktree sont toujours sélectionnés par arguments
littéraux. Le receiver ne contient aucun client SSH, scp, sftp, rsync ni
création de fichier temporaire distant.

## Binding et seal

```text
binding
blob    676b04ce154b2210b714f87d20ae191017aa57c1
size    6625
sha256  47914c545457de3622d4c7aedf96cc5b457b2eb937f4ae95c970f5ff98bfe67b

seal
blob    60242774586277d9eccd8049d8d7c0062e08942b
size    6040
sha256  e9d30ee756843fc9475a08673ca0415e7aa88a4ff9928f409c5b2d1b160d5ec6
```

Le binding relie le receiver, le contrat et son seal PASS, ainsi que le rapport
du préflight lecture seule approuvé. Il reproduit l'ordre fail-closed du
contrat et les treize blob IDs. Le seal garde tous les états d'exécution faux.

## Validation locale

- `15/15` tests receiver + contrat en `1,175 s` ;
- `py_compile` receiver et test : réussi ;
- suite H27 complète avec le venv projet : `540/540` en `95,514 s` ;
- `git diff --check` : réussi.

Une première invocation de la suite avec le Python système a exécuté `533`
tests mais s'est terminée avec une unique erreur d'import
`ModuleNotFoundError: numpy`. Elle n'était pas un échec fonctionnel et a été
remplacée par la suite complète réussie avec
`C:\Users\user\Desktop\midi\.venv\Scripts\python.exe`.

Les tests restent structurels, synthétiques et mockés. Aucun waveform, modèle,
population H27, ODB Mac, locked test ou mesure scientifique n'a été utilisé.
La latence live et le chemin audio sont inchangés.

## STOP

État :
`H27_EXTERNAL_SOURCE_ODB_EXACT_THIRTEEN_RECEIVER_IMPLEMENTED_DORMANT_PENDING_EXTERNAL_REVIEW_NO_TRANSPORT_NO_DELIVERY`.

Prochaine action unique : revue externe du receiver, du binding et du seal
exacts. Aucun SSH, ACK, transport ou apport d'objet avant un nouveau `PASS`.
