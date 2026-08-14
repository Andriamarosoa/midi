# H27 — contrat de création one-shot du parent `control`

## Anomalie préflight

Après le PASS terminal de `c44cf938b04c9d2d3c023be12ab3a35186915c96`,
le préflight lecture seule du creator publié a confirmé ses bytes exacts, le
registry vide `0600`, l'absence du bundle final/staging et l'absence de creator
actif. Il a aussi établi que `/Users/amcarene/h27-admin/control` est absent.

Le creator écrit `reserved`, puis `consumed`, avant d'appeler
`_publish_bundle()`. Cette fonction exige immédiatement
`CONTROL_PARENT.resolve(strict=True)`. Une invocation dans cet état aurait
donc consommé l'autorité avant un échec terminal
`after_consumption_before_bundle_success`. Aucun checkout n'a été détaché et
le creator n'a pas été invoqué.

## Portée du lot

Le présent lot est exclusivement déclaratif :

- contrat :
  `configs/harmonic_censoring_h27_control_parent_creation_contract.json` ;
- external seal du contrat ;
- test mécanique ;
- README et présent rapport.

Identités exactes :

- contrat : `a9b37b3081ad79b773f3a7291a508665d623307a` / `5537` /
  `5d1d0474827e72708e4c1bcb5951e91425fcf95a00f3fc373266193c94653dc3` ;
- seal : `9edefaa15313be5d3a618b4b3ada012e14ef039b` / `1921` /
  `39f5b4ac64df47644a29597a497f280bdf7dbced02c3d5f549b17e918851f1b5`.

La première revue du commit `667e93e6b3d1797570e12ac1671f6a0083dd863f`
a conclu `FAIL` uniquement sur la fermeture mécanique du test : plusieurs
claims contractuels et champs non booléens du seal pouvaient dériver sans
échec. Le micro-correctif teste désormais exactement les métadonnées, l'état
terminal du root, les exigences du futur runner, l'état courant, les
`next_action` et le dictionnaire complet du seal. Les deux JSON ci-dessus ne
sont pas modifiés.

Le futur contrat lie le parent terminal `/Users/amcarene/h27-admin` au tuple
`device=16777233`, `inode=1445438`, puis fixe la seule cible
`/Users/amcarene/h27-admin/control`. La cible devra être absente, créée comme
répertoire réel mode `0700` par un `mkdir` relatif au dirfd vérifié, puis le
parent sera fsync et le nouveau fd sera confronté à l'entrée nommée, au type,
au mode et au même device/inode.

Toutes les identités et conditions statiques précèdent l'unique probe de
`control`. Le `mkdir` sera le premier et seul effet irréversible. Tout échec
postérieur sera terminal ; retry, cleanup, repair, recreation et `mkdir -p`
sont interdits.

## Frontière conservée

Aucun runner n'existe dans ce lot et aucune action Mac n'est effectuée. Le
registry n'est ni ouvert ni modifié ; aucune autorité n'est réservée ou
consommée ; le checkout n'est pas détaché ; le creator, le bundle, le
constructor/materializer, la science et le locked-test restent inexécutés.

État : `H27_CONTROL_PARENT_CREATION_CONTRACT_EXACT_TEST_MICROFIX_PENDING_EXTERNAL_REVIEW`.
La seule prochaine action est la revue externe du contrat et de son seal.

Validation locale : `3/3` tests ciblés, `477/477` tests H27 et
`git diff --check`.
