# H27 — runner dormant one-shot du fichier registry vide

La revue externe du commit
`8c7152ccd5e50d8dbbb40c12ec582efadc58dd54` conclut `PASS` et autorise
uniquement l'implémentation dormante du runner de création du JSONL vide, son
identity binding, son external seal, les tests et la documentation.

La première implémentation `abf92acad5f2b6c93e6b718f9450b365a5ac12d6`
a reçu `FAIL` sur un seul point : elle validait le fd créé avant son `fsync`.
Elle n'a jamais été exécutée et ses anciennes identités sont définitivement
supplantées. Le présent micro-correctif applique l'ordre contractuel exact :
`fsync(created_fd)`, validation du fd créé, puis `fsync(parent_fd)`.

Le runner rehash exactement huit identités Git avant toute observation du
parent : binding PASS, son seal et les six objets transitifs. Il exige macOS,
zéro argument, l'ACK exact `H27_REGISTRY_FILE_CREATE_EXECUTE=1`, puis ouvre
`/Users/amcarene/h27-admin/registry` avec `O_NOFOLLOW` et exige le tuple
terminal `16777233 / 1448669` pour le fd et l'entrée nommée.

Après un unique probe d'absence et une revalidation du parent, le premier et
seul effet irréversible futur est `O_CREAT|O_EXCL|O_NOFOLLOW` sur
`h27-control-bundle-creation-authority-v1.jsonl`, mode `0600`. Le fichier créé
est d'abord fsync, puis son fd est vérifié regular, `nlink=1`, taille `0`, mode
réel `0600`; le parent est ensuite fsync. Une réouverture `O_NOFOLLOW` vérifie fd et
entrée nommée contre le même device/inode et répète tous les invariants avant
la dernière revalidation du parent. Aucun record, retry, cleanup, repair,
recreation, creator, bundle, constructor/materializer ou science.

Identités exactes :

- runner : `bd8b42c4b6e047076f0cddaad3765899914900e2` / `11915` /
  `380c1012e0bdac0b42e5b531b26a178100115158f482f0b81e3c4ebac0485dd5` ;
- binding : `f9378878bc60ecf2128753bfa08d2193d5efe70d` / `5816` /
  `5521ac69fd021b79598f182e22f1ab9fc8a1894c7ed457e67ff320bd863bb38d` ;
- seal : `e02b8d9c6f1cf3ca29c95a52f2f90601f707a68d` / `2191` /
  `52b67c3a2096d115696e9dd7bd675dc270f4bd74c8e1fcafbf4adf79f6ca157b`.

Le lot reste dormant. Aucun accès Mac, aucune observation/création du JSONL,
aucune réservation/consommation d'autorité, aucun creator entrypoint, bundle,
science ou locked-test. La seule prochaine action est la revue externe du
runner, de son binding et de son seal exacts.

Validation locale avant commit : `5/5` tests ciblés, `474/474` tests H27 et
`git diff --check`.
