# H27 — runner dormant one-shot du fichier registry vide

La revue externe du commit
`8c7152ccd5e50d8dbbb40c12ec582efadc58dd54` conclut `PASS` et autorise
uniquement l'implémentation dormante du runner de création du JSONL vide, son
identity binding, son external seal, les tests et la documentation.

Le runner rehash exactement huit identités Git avant toute observation du
parent : binding PASS, son seal et les six objets transitifs. Il exige macOS,
zéro argument, l'ACK exact `H27_REGISTRY_FILE_CREATE_EXECUTE=1`, puis ouvre
`/Users/amcarene/h27-admin/registry` avec `O_NOFOLLOW` et exige le tuple
terminal `16777233 / 1448669` pour le fd et l'entrée nommée.

Après un unique probe d'absence et une revalidation du parent, le premier et
seul effet irréversible futur est `O_CREAT|O_EXCL|O_NOFOLLOW` sur
`h27-control-bundle-creation-authority-v1.jsonl`, mode `0600`. Le fd créé est
immédiatement vérifié regular, `nlink=1`, taille `0`, mode réel `0600`, puis le
fichier et le parent sont fsync. Une réouverture `O_NOFOLLOW` vérifie fd et
entrée nommée contre le même device/inode et répète tous les invariants avant
la dernière revalidation du parent. Aucun record, retry, cleanup, repair,
recreation, creator, bundle, constructor/materializer ou science.

Identités exactes :

- runner : `6f1ebfef57aeba640df44856906010ecf69bbb7f` / `11915` /
  `36a497cfeaf339bbeda0d885a16398f727f55df869af802b663e0a27e1a79a45` ;
- binding : `9dbcef0f2e083d8e8f9796be63218329bf71014a` / `5781` /
  `886c908dfe2b1fed1a76d72fdd2d2454ca9db55e68dfc4131dbac71d2364c4f3` ;
- seal : `f00acd08eaaaced2e0ed732ab0c621fd44b3d499` / `2191` /
  `c274ea79674f283c6f6d5e7e7188c84087e2da3f286bf57160a83693bc7b8c8a`.

Le lot reste dormant. Aucun accès Mac, aucune observation/création du JSONL,
aucune réservation/consommation d'autorité, aucun creator entrypoint, bundle,
science ou locked-test. La seule prochaine action est la revue externe du
runner, de son binding et de son seal exacts.

Validation locale avant commit : `5/5` tests ciblés, `474/474` tests H27 et
`git diff --check`.
