# Résumé unique — Guitar MIDI AI

> Dernière mise à jour manuelle : 2026-08-10
>
> Branche active : `codex/independent-note-neural-v2`
>
> Règle : ce fichier est le résumé chronologique unique du projet. Chaque
> étape terminée, active, suivante ou en anomalie doit y être inscrite.
## Objectif

Produire sur desktop un moteur causal audio de guitare vers MIDI, monophonique
et polyphonique, avec peu de notes fantômes, une latence compatible avec le
live et des entraînements reproductibles exécutés localement. Kaggle et Colab
ne sont plus utilisés sauf nouvelle autorisation explicite de l’utilisateur.

<!-- CURRENT_STATUS_START -->
<!-- H26_CORRECTION_STATUS: H27 ODB-only exact-blob import contract PASS; dormant one-shot importer pending external review, no import. -->
## État courant

- Mise à jour : `2026-08-15`.
- État courant :
  `H27_ODB_ONLY_EXACT_BLOB_IMPORTER_PENDING_EXTERNAL_REVIEW_DORMANT_NO_IMPORT`.
- La revue externe de `dffce1f9a144be60968b7912e99c761ec058ee0f`
  conclut `PASS` sur le contrat ODB-only scellé et autorise uniquement son
  implémentation dormante. Le lot courant ajoute le one-shot importer exact,
  son identity binding, son external seal et des tests synthétiques. Les huit
  payloads proviennent exclusivement d'un ODB Git source externe réel, sont
  tous gardés en mémoire et prévalidés avant le premier effet. Backend `files`,
  HEAD, symbolic HEAD, worktree, refs régulières, root refs/pseudorefs, index,
  lock, ACK/processus et inventaire des objets sont contrôlés aux frontières
  prescrites. L'unique effet futur reste huit `hash-object -w --stdin` dans
  l'ordre déclaré ; échec partiel terminal, aucun retry ou cleanup. Le runner
  n'est pas exécuté et aucun accès Mac n'a lieu. Rapport :
  `readme/results/2026-08-15_harmonic-censoring-h27-odb-only-exact-blob-importer.md`.
  Prochaine action unique : revue externe du runner, de son binding et de son
  seal exacts ; aucun import avant un nouveau `PASS` explicite.
  La première revue de l'implémentation au commit `e17524d8...` a rendu `FAIL`
  uniquement parce que lecture et prévalidation étaient entrelacées payload
  par payload. La micro-correction courante sépare strictement les huit
  lectures complètes des huit prévalidations et verrouille cet ordre par test.
- La revue externe de `0c3a90776c48f3edd5a05f98653e253084637d4d`
  conclut `PASS` sur l'archive du préflight bloqué et autorise uniquement un
  contrat déclaratif one-shot d'apport ODB-only. Le lot courant lie les huit
  payloads par blob/taille/SHA-256, exige leur prévalidation intégrale en
  mémoire avant toute écriture future, scelle une unique opération
  `hash-object -w --stdin` par payload, et interdit tout changement de ref,
  HEAD, index ou worktree. Après le premier `FAIL` de revue, il capture
  d'abord un snapshot déterministe des refs régulières. Après le second `FAIL`
  signalant les pseudorefs omises par `for-each-ref`, la correction courante
  ajoute la capture byte-exacte de tous les fichiers root-ref/pseudoref présents
  au nom majuscule dans `.git`. Après le troisième `FAIL`, le contrat impose
  aussi `rev-parse --show-ref-format == files` avant la capture, avant le
  premier effet futur et au contrôle terminal ; `reftable` est refusé. Les deux
  snapshots sont comparés juste avant la
  première écriture future puis après les huit. Retry, cleanup et rollback
  implicite sont interdits ;
  un import partiel futur serait terminal consommé. Aucun accès Mac ni apport
  réel n'a lieu. Rapport :
  `readme/results/2026-08-15_harmonic-censoring-h27-odb-only-exact-blob-import-contract.md`.
  Prochaine action unique : revue externe du contrat et de son seal exacts.
- La revue externe de `5bfb382fbb72bdcb0a9a1b432361e64fc3030d36`
  conclut `PASS` sur le runner corrigé et autorise uniquement un préflight Mac
  strictement lecture seule. Ce préflight confirme Darwin, checkout/ODB réels,
  HEAD initial `75322bc6...`, worktree propre, cible `7ee0a897...` de type
  commit, ACK/lock/processus absents. Il s'arrête cependant avant invocation :
  runner, binding, seal et cinq prédécesseurs scellés sont tous absents de
  l'ODB Mac. Aucun fetch, synchronisation, ACK, runner ou detach n'a été
  exécuté. Rapport :
  `readme/results/2026-08-15_harmonic-censoring-h27-target-checkout-read-only-runner-preflight.md`.
  Cette preuve a depuis reçu `PASS`; le contrat déclaratif autorisé est l'entrée
  courante ci-dessus.
- La revue externe de `1c523581c866890c932268b54b66575871741acd`
  conclut `PASS` sur le binding corrigé et autorise uniquement le runner
  dormant one-shot, son binding, seal, tests et documentation. Le runner
  courant exige macOS, zéro argument et l'ACK exact
  `H27_TARGET_CHECKOUT_DETACH_EXECUTE=1`, rehash cinq identités après les
  realpaths et avant le HEAD, puis impose HEAD initial propre, cible de type
  commit, revalidation et une unique commande `git checkout --detach` vers
  `7ee0a897...`. Il vérifie ensuite HEAD exact, état detached et propreté,
  sans retry/reset/cleanup. Il n'est pas exécuté et aucune commande Mac n'a
  lieu. Rapport :
  `readme/results/2026-08-15_harmonic-censoring-h27-target-checkout-exact-detach-one-shot-runner.md`.
  Cette revue a depuis rendu `PASS` au commit `5bfb382f...`; le préflight
  lecture seule correspondant est archivé dans l'entrée courante ci-dessus.
- La première revue externe du runner au commit `f0bdb521...` conclut `FAIL`
  sur une seule dérive de nomenclature : le rehash administratif avait été
  inclus dans une nouvelle liste « normative » de douze étapes. La
  micro-correction conserve le runner `1ed1b57d...` byte-identique, sépare le
  rehash comme gate entre realpaths et HEAD, et restaure dans binding/seal les
  onze étapes exactement égales à `contract["future_fail_closed_order"]`.
- La seconde revue externe, sur `bdd5c90c...`, confirme cette correction mais
  conclut encore `FAIL` parce que les commandes Git déclarées en lecture seule,
  notamment les trois vérifications de propreté, pouvaient rafraîchir l'index.
  La micro-correction courante ajoute `git --no-optional-locks` à chaque
  `status`, `rev-parse`, `cat-file`, `symbolic-ref` et lecture de blob. La seule
  commande mutante `checkout --detach` reste byte-exactement inchangée. Un test
  verrouille les deux `status` pré-mutation et le `status` terminal ainsi que
  toutes les autres lectures. Le runner demeure dormant et aucune commande Mac
  n'a été exécutée.
- La revue externe de `36d9ee11fc800a7e57edff1a73858c47ccbdb947`
  conclut `PASS` sur le contrat de transition et autorise uniquement son
  identity binding administratif. Le lot courant lie byte-exactement le
  contrat `11fff096...`, son seal `24a8c14f...` et la preuve préflight
  `bda7e1fa...` au commit `b832f879...`. Checkout, ODB, HEAD initial
  `75322bc6...`, cible commit `7ee0a897...`, transition détachée explicite,
  règles one-shot/fail-closed et tous les downstream flags faux restent
  scellés. Aucun runner ni effet Mac. Rapport :
  `readme/results/2026-08-15_harmonic-censoring-h27-target-checkout-exact-detach-transition-contract-identity-binding.md`.
  Prochaine action unique : revue externe du binding et de son seal exacts ;
  aucun runner ou detach avant un nouveau `PASS` explicite.
- La première revue externe du binding au commit `669e2f04...` conclut `FAIL`
  sur un unique invariant : l'ordre normatif des onze étapes fail-closed était
  résumé mais pas lié comme liste ordonnée exacte. La micro-correction courante
  reproduit cette liste dans le binding et le seal, puis exige dans le test
  leur égalité directe avec `contract["future_fail_closed_order"]`. Les trois
  racines approuvées et tous les downstream flags restent inchangés.
- La revue externe de `b832f8797b557256dda85e40e8f952c59402fa3d`
  conclut `PASS` sur le préflight creator lecture seule et autorise uniquement
  la définition déclarative de la future transition du checkout. Le lot
  courant scelle le checkout exact
  `/Users/amcarene/midi-worker/repository`, son ODB `.git`, le HEAD initial
  `75322bc6...`, la cible commit `7ee0a897...`, et une future transition
  explicite détachée one-shot. Il interdit fetch, pull, merge, reset, rebase,
  modification de branche, ACK/invocation creator, ouverture/écriture du
  registre, réservation/consommation, bundle, matérialisation, science et
  locked test. Aucun runner de transition n'existe et aucun état Mac n'est
  modifié. Rapport :
  `readme/results/2026-08-15_harmonic-censoring-h27-target-checkout-exact-detach-transition-contract.md`.
  Prochaine action unique : revue externe du contrat et de son seal exacts ;
  aucune implémentation ou exécution avant un nouveau `PASS` explicite.
- La revue externe de `c9da0e5f1afccf9aa7af1f808e6ee4ea61fc116a`
  conclut `PASS` : le runner control-parent est terminalement consommé et ne
  doit jamais être rejoué. Le préflight creator lecture seule autorisé vérifie
  la source publiée, le manifest, le digest fermé, les `130` identités,
  l'autorité exacte, le parent `control`, l'absence du final/staging et le
  registre régulier vide `0600`. Le checkout est propre mais son HEAD
  `75322bc6...` ne correspond pas au HEAD creator exigé `7ee0a897...` : état
  `BLOCKED_HEAD_MISMATCH`, STOP sans checkout/detach, ACK, lock ou écriture.
  Rapport : `readme/results/2026-08-15_harmonic-censoring-h27-creator-read-only-preflight.md`.
  Prochaine action unique : revue externe du blocage avant toute modification
  du checkout.
- La revue externe du préflight documenté par
  `1b2043432bc29f9ab1d194e0f8611445fad6fec6` conclut `PASS` et autorise
  exactement une invocation réelle. Le blob Git exact `2b2bd6e5...` a été
  fourni depuis l'ODB au runner avec l'ACK exact et zéro argument. Résultat
  terminal : `H27_CONTROL_PARENT_CORRECTED_CREATED_TERMINAL_SUCCESS`, onze
  identités vérifiées, parent `16777234 / 1445438`, cible
  `/Users/amcarene/h27-admin/control` créée sur `16777234 / 1472478`. L'ancien
  runner reste non exécuté/non consommé. Registre, autorité, creator, bundle,
  constructeur, matérialisation, science et locked test restent faux. STOP
  immédiat, aucune seconde invocation. Prochaine action unique : revue externe
  de ce résultat one-shot.
- La revue externe de `421fd7d39ec429b149c265eadcdca7cd056568fd`
  conclut `PASS` et autorise uniquement un préflight Mac lecture seule. Ce
  préflight a fetché les objets sans checkout, vérifié l'ODB exact, le runner
  `2b2bd6e5...` (`blob`, `10126`, SHA-256 `37e40a4e...`), ses onze
  prédécesseurs, puis ouvert le parent avec `O_NOFOLLOW|O_DIRECTORY` : directory
  réel non-symlink, `16777234 / 1445438`. `control` est absent et aucun runner
  concerné n'est actif. ACK absent, runner non exécuté, `mkdir` non tenté.
  STOP respecté. Prochaine action unique : revue externe de ce préflight avant
  toute éventuelle exécution réelle one-shot.
- La revue externe de `2f0fb5c7cf0fd496f5a80a514b42081c00f87e74`
  conclut `FAIL` uniquement parce que le test ne comparait pas encore les
  dictionnaires complets du binding et du seal. La micro-correction autorisée
  ferme désormais exactement métadonnées, `execution_binding`, état stale,
  safeguards, `current_state`, `next_action` et le seal entier. Runner, binding
  et seal restent byte-identiques. Aucun effet Mac. Prochaine action unique :
  revue externe de cette fermeture mécanique.
- La revue externe de `da614f836e129df9a94534fae621e823ddef1d99`
  conclut `PASS`. Le nouveau runner one-shot corrigé est distinct du blob stale
  `96df0511...`, requiert le parent exact `16777234 / 1445438`, rehache onze
  identités avant toute observation du parent, puis impose une unique création
  `control` en mode `0700`. Son binding et son seal conservent explicitement
  l'ancien runner comme révoqué, jamais exécuté et jamais consommé. Le runner
  demeure dormant : aucune action Mac, aucun ACK, aucun `mkdir`, registre,
  autorité, creator, bundle, calcul scientifique ou locked test. Rapport :
  `readme/results/2026-08-15_harmonic-censoring-h27-control-parent-corrected-runner.md`.
  Prochaine action unique : revue externe du runner corrigé, de son binding et
  de son seal exacts; aucune exécution Mac avant un nouveau `PASS` explicite.
- La revue externe de `90fe6eec1a3c6eeb0e174c24b497280a39ee4668`
  conclut `PASS`. Le lot courant lie uniquement le contrat correctif, son seal
  et les sept objets historiques, soit neuf identités uniques. Le binding
  préserve l'ancien tuple `16777233 / 1445438`, l'observation read-only et la
  future frontière `16777234 / 1445438`, ainsi que le statut stale, révoqué,
  jamais exécuté/consommé du runner `96df0511...`. Aucun runner corrigé ni
  action Mac. Rapport :
  `readme/results/2026-08-15_harmonic-censoring-h27-control-parent-identity-drift-correction-binding.md`.
  Prochaine action unique : revue externe du binding et de son seal exacts.
- La revue externe de l'arrêt pré-effet conclut `PASS` : le parent réel
  `/Users/amcarene/h27-admin` conserve l'inode `1445438` mais son device
  observé en lecture seule est désormais `16777234`, contre `16777233` dans
  la chaîne scellée. Le runner `96df0511...` n'a jamais été exécuté, son ACK
  n'a pas été posé, il n'est pas consommé mais son autorisation est révoquée
  et il est stale. Le lot courant ajoute uniquement un contrat correctif
  déclaratif, son external seal, un test et la documentation. Les sept objets
  historiques restent byte-identiques. Aucun nouveau runner ni accès Mac.
  Rapport :
  `readme/results/2026-08-15_harmonic-censoring-h27-control-parent-identity-drift-correction-contract.md`.
  Prochaine action unique : revue externe du contrat correctif et de son seal.
- La revue externe de `a8662780533c9c613b22f709bd5da94d1526f314`
  conclut `PASS`. Le lot courant implémente uniquement le runner dormant
  one-shot `scripts/h27_create_control_parent_one_shot.py`, son identity
  binding, son external seal, ses tests et le présent journal. Le runner
  rehash sept identités Git avant toute observation du parent, impose macOS,
  ACK exact et zéro argument, ancre le parent à `16777233 / 1445438`, puis
  spécifie l’unique séquence `probe → revalidation → mkdir control 0700 →
  fsync → reopen/verify → revalidation → STOP`. Aucun accès Mac ni effet réel.
  Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-control-parent-one-shot-runner.md`.
  Prochaine action unique : revue externe du runner dormant et de ses seals.
- La revue externe de `a07522cbac45097acb53e24f06b61bb2a6060ce0`
  conclut `PASS`. Le lot courant lie exclusivement les cinq identités exactes
  du contrat control-parent PASS, de son seal et des trois prédécesseurs du
  root administratif, puis scelle ce binding. Parent `16777233 / 1445438`,
  cible `/Users/amcarene/h27-admin/control`, directory `0700`, ACK et compteurs
  `3 / 4 / 7 / 15 / 7` restent inchangés et dormants. Aucun runner, action
  Mac, registry, detach, creator, bundle, science ou locked-test. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-control-parent-creation-contract-identity-binding.md`.
  Prochaine action unique : revue externe du binding et de son seal exacts.
- La revue externe de `667e93e6b3d1797570e12ac1671f6a0083dd863f`
  conclut `FAIL` uniquement parce que le test ne verrouillait pas chaque claim
  du contrat et du seal. Le micro-correctif courant ajoute les égalités exactes
  complètes requises dans le test et la documentation. Les blobs contrat
  `a9b37b30...` et seal `9edefaa1...` restent byte-identiques ; aucun autre
  fichier ni état opérationnel n'est modifié.
- La revue externe du préflight post-`c44cf938b04c9d2d3c023be12ab3a35186915c96`
  confirme `PASS` pour le STOP avant réservation : le parent exact
  `/Users/amcarene/h27-admin/control` est absent et le creator consommerait
  l'autorité avant d'échouer terminalement. Le lot courant définit uniquement
  le futur contrat one-shot de ce parent réel, mode `0700`, sous le root
  terminal `/Users/amcarene/h27-admin` lié à `16777233 / 1445438`, avec probe
  unique, `mkdir` relatif comme premier/seul effet irréversible, fsync parent,
  vérification fd/entrée nommée et aucun retry. Aucun runner, accès Mac,
  registry, détachement checkout, creator, bundle, science ou locked-test.
  Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-control-parent-creation-contract.md`.
  Prochaine action unique : revue externe du contrat et de son seal exacts.
- La revue externe de `75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf`
  conclut `PASS` et autorise une seule exécution réelle du blob runner
  `bd8b42c4b6e047076f0cddaad3765899914900e2`. Le Mac a été synchronisé sur
  ce commit exact, worktree propre, cible absente et trois identités exactes.
  Le blob a été exécuté directement depuis l'ODB approuvé avec l'ACK exact et
  zéro argument. Résultat terminal :
  `H27_EMPTY_REGISTRY_FILE_CREATED_TERMINAL_SUCCESS`, huit identités vérifiées,
  parent `16777233 / 1448669`, cible régulière `16777233 / 1450301`, `nlink=1`,
  taille `0`, mode `0600`. Aucun processus runner ne reste actif. Aucun record,
  réservation/consommation bundle, creator, control bundle,
  constructor/materializer, science ou locked-test. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-empty-registry-file-terminal-execution.md`.
  Prochaine action unique : revue externe de cette exécution terminale avant
  toute définition ou exécution du writer de record/creator.
- La revue externe de `abf92acad5f2b6c93e6b718f9450b365a5ac12d6`
  conclut `FAIL` sur un unique ordre d'opérations : la vérification du fd créé
  précédait son `fsync`. Le micro-correctif courant place désormais
  strictement `fsync(created_fd)` avant la vérification du fd, puis
  `fsync(parent_fd)`, sans aucun autre changement de contrat. Le runner refusé
  n'a jamais été exécuté et ne doit pas l'être.
- La revue externe de `8c7152ccd5e50d8dbbb40c12ec582efadc58dd54`
  conclut `PASS`. Le lot courant implémente uniquement le runner dormant
  one-shot du futur fichier registry vide, son identity binding, son external
  seal, les tests et la documentation. Le runner rehash huit identités avant
  toute observation du parent, exige macOS, zéro argument et l'ACK exact, lie
  le parent au tuple terminal `16777233 / 1448669`, effectue un probe unique,
  puis réserve `O_CREAT|O_EXCL|O_NOFOLLOW` mode `0600` comme premier/seul effet
  irréversible. Le fichier créé est fsync avant la vérification du fd, puis le
  parent est fsync; fd créé, entrée nommée et fd rouvert doivent tous rester
  regular, `nlink=1`, taille `0`, mode réel `0600` et même device/inode. Le runner n'est pas exécuté; aucun accès Mac,
  record, autorité, creator, bundle, science ou locked-test. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-empty-registry-file-one-shot-creator.md`.
  Prochaine action unique : revue externe du runner, binding et seal exacts.
- La revue externe de `ef866d365b79455508f5d2d866bbf1dc043f0f70`
  conclut `PASS`. Le lot courant ajoute uniquement l'identity binding du
  contrat du futur fichier registry vide, son external seal, un test et la
  documentation. Il lie byte-exactement le contrat `943034b7...`, son seal
  `e697b7fe...` et les quatre identités terminales du registry-leaf. Parent
  `/Users/amcarene/h27-admin/registry`, tuple `16777233 / 1448669`, cible,
  taille `0`, `nlink=1`, mode `0600`, ACK et compteurs `4 / 9 / 18 / 7`
  restent fermés. Aucun runner, accès Mac, observation/création du JSONL,
  creator, bundle, science ou locked-test. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-empty-registry-file-contract-identity-binding.md`.
  Prochaine action unique : revue externe du binding et de son seal exacts.
- La revue externe de `366b778c86a0e00fb49be15bc122123f0db2fb56`
  confirme la frontiere principale mais rend `FAIL` sur deux fermetures : mode
  reel `0600` non revérifie et tests de contenu trop permissifs. La
  micro-correction du meme lot declaratif exige maintenant `0600` sur fd cree,
  fd rouvert et entree nommee, porte les regles a 18 et compare exactement les
  quatre preflights, neuf etapes, 18 regles, sept exigences runner et le seal
  complet. Toujours aucun runner, action Mac, JSONL, creator, bundle ou science.
  Prochaine action unique : nouvelle revue externe de ce lot corrige.
- La revue externe de `0ea166702f7573d894e487cb7d7f2551af769317`
  conclut `PASS`: le leaf registry est terminal, son autorite consommee et le
  runner `ca93c383...` non rejouable. Le lot courant definit uniquement le
  contrat declaratif + external seal + test + documentation de la future
  creation exclusive du fichier exact
  `/Users/amcarene/h27-admin/registry/h27-control-bundle-creation-authority-v1.jsonl`,
  initialement vide. Le parent est lie au tuple terminal `16777233 / 1448669`;
  le futur fichier doit etre regular, 0 octet, `nlink=1`, mode `0600`, cree
  exclusivement comme premier/seul effet puis fsync et reverifie. Aucun runner
  ni action Mac, aucune ligne JSONL, reservation/consommation, creator, bundle,
  constructor/materializer, science ou locked-test. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-empty-registry-file-creation-contract.md`.
  Prochaine action unique : revue externe du contrat et de son seal.
- La revue externe de `57e3f5be80ed12192776425799c58a7a4305ba6c`
  conclut `PASS` et autorise une seule execution du runner exact blob
  `ca93c383d8cc61a6f3869318f1e462ab82a1c92a`. Le Mac est synchronise propre
  sur ce commit, puis les bytes du blob sont executes depuis l'ODB avec l'ACK
  exact et zero argument. Resultat :
  `H27_REGISTRY_LEAF_CREATED_TERMINAL_SUCCESS`, sept identites verifiees,
  parent device `16777233` / inode `1445438`, leaf
  `/Users/amcarene/h27-admin/registry` device `16777233` / inode `1448669`.
  JSONL non observe/non ouvert, aucune reservation ou consommation d'autorite
  bundle, aucun creator entrypoint, bundle, constructor/materializer, science
  ou locked-test. STOP immediat, aucun retry/cleanup/repair. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-registry-leaf-terminal-execution.md`.
  L'autorite registry-leaf est terminalement consommee et le blob ne doit
  jamais etre rejoue. Prochaine action unique : revue externe de cette preuve.
- La revue externe de `78957b981fdf679e2ccca2ead0223e5310c1a909`
  juge le runner, son binding et son seal fonctionnellement conformes, mais
  rend `FAIL` uniquement parce que le test ne verrouillait pas plusieurs
  claims non booleens du seal. Le lot courant modifie seulement le test, ce
  README et le rapport : il compare desormais le dictionnaire complet du seal,
  notamment schema/id/status, commit, ACK, parent/path/device/inode, cible et
  next_action. Runner `ca93c383...`, binding `e2b18cf3...` et seal
  `c3b99549...` restent byte-identiques. Aucune execution ou action Mac.
  Prochaine action unique : revue externe de cette micro-correction.
- La revue externe de `c18ec0632e23edeca59816246c947a585f918af4`
  conclut `PASS`. Le lot courant implemente uniquement le runner dormant
  one-shot de creation du leaf exact `/Users/amcarene/h27-admin/registry`, son
  identity binding, son external seal, les tests et la documentation. Le
  runner rehash sept identites Git avant observation du parent, impose macOS,
  zero argument et l'ACK exact, puis applique `O_NOFOLLOW`, tuple terminal,
  probe unique, revalidation, unique `mkdir`, fsync et verification du leaf.
  Il n'est pas execute. JSONL registry, creator entrypoint, reservation,
  consommation, bundle, constructor/materializer, science et locked-test
  restent interdits. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-registry-leaf-one-shot-creator.md`.
  Prochaine action unique : revue externe du runner, binding et seal.
- La revue externe de `e07e26111bbcf0343a7b57f30c154ab667154fcf`
  conclut `PASS`. Le lot courant ajoute uniquement l'identity binding
  administratif du contrat registry-leaf PASS, son external seal, un test et
  la documentation. Il lie byte-exactement le contrat `ae1b6517...`, son seal
  `381b979b...` et les trois predecessor identities, tout en preservant parent
  `/Users/amcarene/h27-admin`, tuple terminal `16777233 / 1445438`, cible
  `/Users/amcarene/h27-admin/registry`, ACK futur et compteurs `4 / 7 / 14 /
  7`. Aucun runner, filesystem Mac, leaf registry, JSONL, creator entrypoint,
  bundle, constructor/materializer, science ou locked-test. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-registry-leaf-contract-identity-binding.md`.
  Prochaine action unique : revue externe du binding et de son seal.
- La revue externe de `9d8106135144c449e9d06a71269f61adf64457e8`
  conclut `PASS` : l'anomalie Windows/POSIX `795 -> 790` est fermee sans
  modifier ni rejouer le publisher terminalement consomme. Le lot courant est
  strictement declaratif : contrat + external seal + test + documentation de
  la future creation one-shot du leaf exact
  `/Users/amcarene/h27-admin/registry`. Le parent est lie au tuple terminal
  device `16777233` / inode `1445438`; le futur probe est unique et le futur
  `mkdir("registry", dir_fd=parent_fd)` doit etre le premier/seul effet
  irreversible. Aucun runner n'existe dans ce lot et aucune observation ou
  mutation du filesystem Mac, du JSONL registry, du bundle ou de la science
  n'a lieu. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-registry-leaf-creation-contract.md`.
  Prochaine action unique : revue externe de ce contrat et de son seal.
- La revue externe de `c5e2a8522502832223ef196900af70fb1fa31f4f`
  confirme que l'execution publisher est coherente et terminalement consommee,
  mais rend `FAIL` sur une contradiction du test : sous Windows,
  `Path` serialisait le root avec des backslashes et le test attendait `795`,
  tandis que le blob execute sur macOS produit canoniquement `790` octets. Le
  lot courant corrige uniquement le test pour imposer la semantique POSIX
  exacte et verrouille `790`, SHA `1d21fc85...` et digest ferme
  `bc0d75eb...`; README et rapport enregistrent cette correction. Publisher
  `60287a98...`, binding et seal restent byte-identiques ; aucune execution ou
  nouvelle observation Mac. Prochaine action unique : revue externe de cette
  correction administrative test-only.
- La revue externe de `242f7ae505763d69c6ffc14ea4454fded4a635f0`
  conclut `PASS` et autorise une seule execution du nouveau publisher exact
  blob `60287a98eb0a7ff227bfcff49e72935b4a40dafc`. Le Mac est synchronise propre
  sur ce commit puis les octets du blob sont executes une seule fois depuis
  l'ODB avec l'ACK exact et zero argument. Resultat terminal :
  `H27_REVIEWED_CREATOR_SOURCE_PUBLISHED_TERMINAL_SUCCESS`, 139 identites,
  entrypoint `2091028d...` / `44063` / `0f0dd586...`, manifest `790` /
  `1d21fc85...`, digest ferme `bc0d75eb...`. Le creator entrypoint n'est pas
  execute ; registre, bundle et science restent faux. Aucun retry, cleanup,
  repair ni autre phase ne suit. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-reviewed-creator-source-terminal-publication.md`.
  L'autorite publisher est desormais consommee et le blob `60287a98...` ne
  doit jamais etre rejoue. Prochaine action unique : revue externe de cette
  preuve terminale.
- La revue externe de `81acfa74ea9b6007bed3d02ce1ac7eec9d6a5ef9`
  conclut `PASS` : l'autorite creator-leaf est consommee terminalement et le
  runner `848c65d0...` ne doit jamais etre rejoue. Le lot courant durcit
  uniquement le publisher dormant existant : son parent exact
  `/Users/amcarene/h27-admin/creator` doit maintenant correspondre, pour le fd
  et l'entree nommee, au tuple terminal device `16777233` / inode `1447071`
  avant toute observation final/staging, immediatement avant le premier effet
  et avant succes. Un nouveau binding et son seal lient le publisher corrige,
  l'ancienne chaine publisher PASS et la preuve terminale creator-leaf. Aucun
  publisher n'a ete execute ; autorisation publisher, source, creator
  entrypoint, registre, bundle et science restent non consommes/faux. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-publisher-terminal-parent-microfix.md`.
  Le publisher PASS historique reste byte-identique sous son path d'origine ;
  le microfix est un nouveau publisher versionne. Identites : publisher
  `60287a98...` / `17187` / `c84a6476...`, binding `7ae682b7...` / `4380` /
  `9691a3aa...`, seal `c852b08c...` / `1857` / `57f0d4e3...`. Prochaine action
  unique : revue externe de ce lot dormant ;
  aucune publication reelle n'etait autorisee avant ce PASS.
- La revue externe de `406f04db0c3315b82ad91f02ffb71a425512f61b`
  conclut `PASS` et autorise une seule execution du runner exact blob
  `848c65d0039b0ef60a5752835ce4a9b84be47c73`. Le Mac est synchronise propre
  sur ce commit, puis les octets du blob sont executes une seule fois avec
  `H27_CREATOR_LEAF_CREATE_EXECUTE=1` et zero argument. Resultat terminal :
  `H27_CREATOR_LEAF_CREATED_TERMINAL_SUCCESS`, sept identites verifiees,
  parent `/Users/amcarene/h27-admin` device `16777233` / inode `1445438`, leaf
  `/Users/amcarene/h27-admin/creator` device `16777233` / inode `1447071`.
  Publisher, source, creator entrypoint, registre, bundle et science restent
  faux. Aucun retry, cleanup ni autre phase n'a suivi. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-creator-leaf-terminal-execution.md`.
  L'autorite creator-leaf est desormais consommee et le runner ne doit jamais
  etre rejoue.
- La revue externe de `c2b2fd7264966a183d20106004816149c1b0a3a9`
  conclut `FAIL` uniquement sur la fermeture mecanique du test : le runner est
  juge fonctionnellement conforme, mais `identity_graph`, les dix claims
  `creation_safeguards`, les quatre claims `authority_state` et plusieurs
  claims positifs du seal n'etaient pas compares comme valeurs exactes. Le lot
  courant modifie uniquement le test, ce README et le rapport pour fermer ces
  dictionnaires. Runner, binding et seal restent byte-identiques ; aucune
  execution reelle n'etait autorisee avant une nouvelle revue externe.
- La revue externe de `3021fa1dfe1bf3645ab3ae8d50927df3feaf1dfd`
  concluait `PASS`. Le lot precedent implementait uniquement le runner dormant
  one-shot de creation du leaf exact `/Users/amcarene/h27-admin/creator`, son
  identity binding et son seal. Il rehash sept identites depuis l'object
  database Git avant toute observation du parent, impose macOS, l'ACK exact et
  zero argument, puis lie le parent au tuple terminal device `16777233` / inode
  `1445438` par `O_NOFOLLOW` et dirfd. Le probe est unique ; `mkdir("creator")`
  reste le premier/seul effet irreversible, sans cleanup/retry/repair. Aucun
  runner n'a ete execute et aucun filesystem Mac n'a ete observe par ce lot.
  Publisher, source, creator entrypoint, registre, bundle et science restent
  faux. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-creator-leaf-one-shot-creator.md`.
  Identites : runner `848c65d0...` / `10474` / `04e5102e...`, binding
  `31b3dc73...` / `4968` / `58b3581e...`, seal `d79d8af6...` / `1812` /
  `dd7fd034...`. Prochaine action unique : revue externe de la micro-correction
  mecanique du test ;
  aucune creation reelle de `creator` n'est autorisee.
- L'unique execution one-shot du runner admin-root exact au commit
  `042974fde833d1ec13132520f003fba0b60ae044` aboutit au succes terminal :
  `/Users/amcarene/h27-admin`, device `16777233`, inode `1445438`, sept
  identites verifiees. Cette autorite est consommee et le runner ne doit jamais
  etre rejoue. Publisher, creator, registre, bundle et science restent faux ;
  l'autorisation du publisher reste non consommee. Le lot courant definit
  uniquement le contrat declaratif et le seal externe de la future creation
  one-shot du leaf exact `creator`. Parent `O_NOFOLLOW`/dirfd stable, probe
  unique, et identite parent liee exactement au device `16777233` / inode
  `1445438` terminal sont exiges pour le fd et l'entree nommee a chaque
  revalidation. `mkdir("creator")` reste premier/seul effet, fsync, verification
  inode/device, aucun retry/cleanup ni observation des roots publisher sont
  fermes. Aucun runner creator-leaf ni filesystem n'est execute. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-creator-leaf-creation-contract.md`.
  La micro-correction apres revue ferme ainsi le remplacement du parent au meme
  path. Identites : contrat `8a03300a...` / `5148` / `1c3412c4...`, seal
  `c86b6da6...` / `1652` / `af370f69...`. Prochaine action unique : revue
  externe de ce contrat et seal ; aucune creation de `creator` autorisee.
- La revue externe de `fba12da62f2271d574a9fb46c8a20260cf55a1f1`
  conclut `PASS`. Le lot courant implemente uniquement le runner one-shot
  dormant de creation du leaf exact `/Users/amcarene/h27-admin`, son identity
  binding et son seal. Le runner rehash sept predecessors depuis l'object
  database Git explicite avant toute observation de `/Users/amcarene`, ancre
  ce parent par `O_NOFOLLOW` + `dirfd`, effectue un probe unique, puis fixe
  `mkdir("h27-admin")` comme premier et seul effet irreversible. Il interdit
  cleanup, retry, creation parente, publisher, creator, registre, bundle et
  science. Aucun code n'a ete execute sur Mac. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-admin-root-one-shot-creator.md`.
  La micro-correction apres revue remet l'ordre scelle exact `rehash ->
  ACK/macOS/0 args -> open parent` et verrouille comme dictionnaires fermes
  `execution_binding`, les dix safeguards et les claims correspondants du
  seal. Identites : runner `4fd4c778...` / `9401` / `f29d33c5...`, binding
  `28331255...` / `4537` / `2bf1dc2e...`, seal `696ca0c0...` / `1432` /
  `b28c1e91...`. Prochaine action unique : revue externe de ce runner dormant,
  de son binding et de son seal exacts ; aucune creation reelle autorisee.
- La revue externe de `20f43758b6349ce7de9aa8503a3a6e81334cd36a`
  conclut `PASS`. Le lot courant ajoute uniquement l'identity binding
  administratif de ce contrat et son seal : contrat, seal et trois
  predecessors PASS forment cinq chemins uniques a rehasher. ACK, paths et
  sept exigences du futur runner sont preserves byte-exactement. Aucun runner,
  parent, target ou filesystem n'est ouvert. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-admin-root-creation-contract-identity-binding.md`.
  Identites : binding `4ecb86e7...` / `3541` / `1efcd187...`, seal
  `7c0c8ee6...` / `1282` / `d1d4c3f5...`. Prochaine action unique : revue
  externe de ce binding et seal exacts.
- Le lot courant definit uniquement le contrat declaratif et le seal externe de
  la future creation one-shot de `/Users/amcarene/h27-admin`. Il lie les trois
  identites PASS du publisher bloque, exige `/Users/amcarene` preexistant et
  stable par `dirfd`, fixe quatre preflights, sept etapes et quatorze regles.
  `mkdir("h27-admin")` serait le premier et seul effet ; `mkdir -p`, retry,
  cleanup et observation de `creator`/publisher roots sont interdits. La
  micro-correction apres revue fixe l'ACK futur exact
  `H27_ADMIN_ROOT_CREATE_EXECUTE=1`, ferme le dictionnaire des 14 regles et
  exige un futur runner distinct, PASS, identity-bound, scelle et execute
  uniquement depuis son blob Git exact. Aucun runner ou filesystem n'est
  ouvert. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-admin-root-creation-contract.md`.
  Identites : contrat `7ac98b37...` / `4505` / `82e4bbe7...`, seal
  `93597fd6...` / `1335` / `4bd891cd...`. Prochaine action unique : revue
  externe de ce contrat et seal exacts.
- La revue externe de `ddba2178028b385cb33f9a68455d724015e22814`
  conclut `PASS` et autorise uniquement la publication one-shot depuis le blob
  publisher exact `22fbc4ae...`. La premiere invocation Mac s'arrete avant
  effet car `/Users/amcarene/h27-admin/creator` est absent. La revue confirme
  que l'autorisation n'est pas consommee et autorise la creation bornee du leaf
  seulement si `/Users/amcarene/h27-admin` existe deja et est conforme. Ce
  parent est lui-meme absent ; la sequence s'arrete donc sans creation. Aucun
  final/staging n'est observe, aucun `mkdir(staging)`, registre, creator, bundle
  ou science n'est execute. La publication reste non consommee. Une nouvelle
  autorite explicite est requise avant toute creation de `h27-admin`.
- La premiere revue du publisher non versionne conclut `FAIL` sur trois
  surfaces : parent non ancre contre TOCTOU, rehash staging/final par chemins
  separes, et absence d'identite immuable du publisher. Le lot courant corrige
  uniquement ces trois points sans execution : toutes les operations sont
  relatives a un `dirfd` parent `O_NOFOLLOW` verifie, les fichiers sont lus et
  controles depuis le meme fd, et le publisher exact est versionne avec son
  identity binding et son seal. Les `139/139` identites sont verifiees en test,
  le manifest canonique mesure `795` octets, et les tests passent `3/3` puis
  `430/430`. Aucune racine administrative n'est observee ou creee. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-reviewed-creator-source-publisher.md`.
  Identites : publisher `22fbc4ae...` / `16875` / `80d46a6d...`, binding
  `11b68809...` / `2984` / `f700f00c...`, seal `cc627c22...` / `1317` /
  `256d24c...`. Prochaine action unique : revue externe de ce lot exact avant
  toute publication one-shot.
- La revue externe de `b93d6580ff19b7a514cefdae18a00c0f0c0457e6`
  conclut `PASS`. Le lot courant cree uniquement dans Git l'entrypoint dormant
  futur du creator, son identity binding et son seal. Il lie 139 paths uniques,
  un object database explicite, les 130 identites amont, les six fichiers du
  bundle et l'ordre registre/reservation/consommation/publication terminale.
  La premiere revue de `b8d0c9c7...` conclut `FAIL` sur le JSON canonique,
  la validation des records, les erreurs write/fsync et le TOCTOU registre.
  La micro-correction du meme stage ferme ces quatre surfaces sans execution.
  La deuxieme revue de `a9c60a43...` les confirme mais conclut `FAIL` sur le
  claim universel de fsync terminal du binding. La correction courante garde
  l'entrypoint byte-identique et remplace ce claim par quatre invariants exacts.
  La racine administrative n'est ni creee ni observee ; aucun filesystem,
  registre, reservation, consommation, bundle, invocation ou science n'est
  ouvert. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-reviewed-control-bundle-creator-implementation-source.md`.
  Identites : entrypoint `2091028d...` / `44063` / `0f0dd586...`, binding
  `3eea754a...` / `6091` / `0d084495...`, seal `aa3ebc70...` / `1649` /
  `1dd748ed...` ; tests `3/3` et `427/427`.
- La revue externe de `53607b623858b18064c23ab0a9772d4c36b48b90`
  conclut `PASS`. Le lot courant ajoute uniquement l'identity binding du
  contrat de source immutable et son seal : contrat + seal + 134 amont forment
  136 paths uniques rehashes. Les racines, deux fichiers fermes, schema du
  manifest, ordres 7/9 et douze regles sont preserves. Aucune source,
  implementation, filesystem, registre, reservation, consommation, bundle ou
  science n'est ouverte. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-reviewed-control-bundle-creator-implementation-source-contract-identity-binding.md`.
  Identites : binding `9da5ef44...` / `3751` / `4fe12fc4...`, seal
  `49de9d84...` / `1423` / `95a2e861...` ; tests `3/3` et `424/424`.
- La revue externe de `53335c83dffc7551e3f0e2f3236503ef92970599`
  conclut `PASS`. Le lot courant definit uniquement le contrat et le seal de la
  future source immutable du creator : racine exacte sous `h27-admin`, deux
  fichiers fermes, 134 identites a rehasher avant observation, sept controles
  statiques, neuf etapes atomiques et douze regles fail-closed. Aucune source,
  implementation, registre, reservation, consommation, bundle, operation
  filesystem ou science n'est ouverte. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-reviewed-control-bundle-creator-implementation-source-contract.md`.
  Identites : contrat `08a75b33...` / `7535` / `200242f8...`, seal
  `60830362...` / `1401` / `7632b7d0...` ; tests `3/3` et `421/421`.
  La premiere revue de `dd04b4d...` a conclu `FAIL` uniquement sur la couverture
  mecanique du test. La micro-correction garde contrat et seal byte-identiques
  et verrouille les dictionnaires source/manifest ainsi que les douze cles et
  valeurs fail-closed exactes.
- La revue externe de `4b58428db71de7a1810bd6c71b5bfc17d1277aed`
  conclut `PASS`. Le lot courant ajoute uniquement l'identity binding du
  contrat creator corrige et son seal : 132 paths uniques rehashes, sans
  implementation, registre, reservation, consommation, bundle, filesystem ou
  science. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-reviewed-control-bundle-creator-contract-identity-binding.md`.
  Identites : binding `b5ec9c1c...` / `3248` / `54a31600...`, seal
  `49240ffb...` / `1265` / `f99ccfde...` ; tests `3/3` et `418/418`.
- La revue externe de `817f4c8ab2d51674d17eef968a907e519ac2cccf`
  conclut `PASS`. Le lot courant definit uniquement le futur creator one-shot :
  130 identites rehashees avant registre, dix controles statiques, reservation
  puis consommation atomique et treize etapes exactes, avec terminalite sans
  retry. Aucune implementation, registre, consommation, bundle, filesystem ou
  science n'est ouvert. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-reviewed-control-bundle-creator-contract.md`.
  La premiere revue de `b9bb9ea...` a conclu `FAIL` sur le format du registre
  et la source du creator. La micro-correction ferme 11 champs JSONL, 11 regles
  de transition et la racine distincte `/Users/amcarene/h27-admin/creator/`.
  Identites : contrat `cee37fbe...` / `9920` / `8decca47...`, seal
  `530e2f57...` / `1283` / `b883b10d...` ; tests `3/3` et `415/415`.
- La revue externe de `f5f4b825b3103386ca3745c915beb20c05f78f0f`
  conclut `PASS`. Le lot courant ajoute uniquement l'identity binding de
  l'artefact non consomme et son seal : artefact + seal + 126 amont forment
  128 paths uniques rehashes. Aucun bundle, filesystem, registre, consommation
  ou science n'est ouvert. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-control-bundle-creation-authority-artifact-identity-binding.md`.
  Identites : binding `2c1d96a6...` / `3730` / `e39079c5...`, seal
  `47244bbd...` / `1400` / `13ef586b...` ; tests `3/3` et `412/412`.
- La revue externe de `7ee0a8977208bfa389e284b07207abc40a3517fd`
  conclut `PASS`. Le lot courant cree uniquement l'artefact administratif reel
  distinct et son seal, avec HEAD d'execution fixe au commit PASS `7ee0a897...`,
  ID canonique `4e107255...`, `single_use=true` et `consumed=false`. Aucun
  bundle, filesystem, registre, consommation ou science n'est ouvert. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-control-bundle-creation-authority-artifact.md`.
  Identites : artefact `9f8ebc7c...` / `920` / `da2718b4...`, seal
  `167e772f...` / `2003` / `40d742e3...` ; tests `3/3` et `409/409`.
- La revue externe de `2f078c1bdc0ca57559c6ff803f2847cf7b68fb68`
  conclut `PASS`. Le lot courant ajoute uniquement l'identity binding du
  contrat d'artefact d'autorite et son seal : contrat + seal + 124 amont
  forment 126 paths uniques rehashes. Aucun artefact reel, bundle, filesystem,
  registre, consommation ou science n'est ouvert. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-control-bundle-creation-authority-artifact-contract-identity-binding.md`.
  Identites : binding `30c07654...` / `4229` / `d4b76a2a...`, seal
  `8cf638d4...` / `1455` / `f0c31cee...` ; tests `3/3` et `406/406`.
- La revue externe de `c32c785cda2f8b23c3e788ee9cfffaa77d1745ec`
  conclut `PASS`. Le lot courant definit uniquement le schema ferme et le seal
  du futur artefact d'autorite distinct et single-use : les quatre identites
  du contrat de bundle et 120 amont forment 124 predecesseurs uniques. Aucun
  artefact reel, bundle, filesystem, registre, consommation ou science n'est
  ouvert. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-control-bundle-creation-authority-artifact-contract.md`.
  La premiere revue de `e2672ed...` a conclu `FAIL` sur trois verrouillages
  mecaniques. La micro-correction fixe les six valeurs exactes de chaine, la
  canonicalisation byte-exacte de l'ID et les gardes HEAD/bundle. Identites :
  contrat `12f7645d...` / `6121` / `dd030822...`, seal `870ef976...` /
  `1172` / `3f264fb3...` ; tests structurels `3/3` et suite H27 `403/403`.
- La revue externe de `e875d5831f45fdf2fa7c8f9c62d2206a98bd0d98`
  conclut `PASS`. Le lot courant ajoute uniquement l'identity binding du
  contrat de creation du bundle et son seal : contrat + seal + 120
  predecesseurs = 122 chemins uniques rehashes. Aucun bundle n'est observe ou
  cree; filesystem, registre, reservation, consommation, invocation et science
  restent fermes. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-control-bundle-creation-contract-identity-binding.md`.
  Validation locale : `3/3` tests administratifs et `400/400` tests H27.
- La revue externe de `5db5424d3cce72f8a1b9eee84cf4d1a8d9e09ace`
  conclut `PASS`. Le lot courant definit seulement le contrat declaratif et le
  seal de la future creation du bundle de controle immuable : manifeste ferme
  de six fichiers exacts et 120 identites amont rehashees avant toute
  observation du chemin. Les octets futurs proviendront uniquement des blobs
  Git exacts; overwrite, publication partielle et retry post-effet sont
  interdits. Aucun bundle, registre, reservation, consommation, invocation,
  filesystem ou science n'est ouvert. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-control-bundle-creation-contract.md`.
  Validation locale : `3/3` tests administratifs et `397/397` tests H27.
  La premiere revue de `29784a47ed283d1ae609780ce33087e2e2564264`
  conclut `FAIL` uniquement sur la couverture mecanique. La micro-correction
  garde contrat et seal byte-identiques et compare desormais l'ordre exact des
  13 etapes, les listes fermees de cles et les six identites completes.
- La revue externe de `6be05ef36794e4a42c133f9542fa2a30fa618496`
  conclut `PASS`. Le lot courant ajoute uniquement l'identity binding du
  contrat corrige du gate one-shot et son seal : contrat + seal + 116
  predecesseurs = 118 chemins uniques rehashes. Les deux sources runtime, le
  HEAD cible, l'autorite single-use non consommee et les huit edges fermes sont
  preserves. Aucun bundle administratif, registre, reservation, consommation,
  invocation, destination, filesystem ou science n'est ouvert. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-constructor-one-shot-execution-gate-contract-identity-binding.md`.
  Validation locale : `3/3` tests administratifs et `394/394` tests H27.
- La revue externe de `5a0b8d3d3f301ed4357bd1853af778bd6794f406`
  conclut `PASS`. Le lot courant definit seulement le contrat declaratif et le
  seal externe du futur gate one-shot : artefact, seal, binding, binding seal
  et 112 identites amont = 116 chemins uniques a rehasher avant registre.
  L'ordre futur est `artifact -> HEAD/clean -> rehash116 -> registre ->
  reservation -> consommation -> invocation`. Aucun registre, reservation,
  consommation, invocation, destination, filesystem ou science n'est ouvert.
  Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-constructor-one-shot-execution-gate-contract.md`.
  Validation locale : `3/3` tests administratifs et `391/391` tests H27.
  La premiere revue de `18ee84e2fd4edba39681effc315d9f5762f132fd`
  conclut `FAIL` : le HEAD cible `46a6bdf8...` ne contient pas encore les
  quatre fichiers de chaine d'autorite. La micro-correction separe le checkout
  cible exact `/Users/amcarene/midi-worker/repository` du bundle de controle
  immuable exact `/Users/amcarene/h27-admin/control/h27-constructor-execution-gate-v1`.
  Aucun fallback vers le checkout courant n'est permis et ce bundle n'est pas
  cree par le lot.
- La revue externe de `5e95219a517fb7206f4d54e5dc5e492dc868d80f`
  conclut `PASS`. Le lot courant ajoute uniquement l'identity binding de
  l'artefact d'autorite et son seal : artefact + seal + 112 identites amont =
  114 chemins uniques rehashes. Aucun registre, reservation, consommation,
  invocation ou science n'est ouvert. Rapport :
  `readme/results/2026-08-14_harmonic-censoring-h27-constructor-execution-authority-artifact-identity-binding.md`.
  Validation locale : `3/3` tests administratifs et `388/388` tests H27.
- La revue externe de `46a6bdf81a56a7a7a10524d4e55092301a452207`
  conclut `PASS`. Le lot courant cree uniquement l'artefact administratif
  d'autorite d'execution et son seal, avec `expected_git_head` explicitement
  fixe au commit PASS `46a6bdf81a56a7a7a10524d4e55092301a452207` et identite
  `45f4dc4ff73284f1355eb125dc36d8c8bad2372818bf5f80b85b758ea69ae64e`.
  Les 112 identites amont sont rehashees. Aucun registre, reservation,
  invocation ou science n'est ouvert. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-constructor-execution-authority-artifact.md`.
  Validation locale : `3/3` tests administratifs et `385/385` tests H27.
- La revue externe de `55bd7a533952d1ead5d7611580a066e7505698f4`
  conclut `PASS`. Le lot courant ajoute seulement l'identity binding
  administratif du contrat de l'artefact d'autorite d'execution et son seal :
  contrat + seal + 108 predecesseurs = 110 chemins uniques rehashes. Aucun
  artefact runtime, `expected_git_head` concret, registre, reservation,
  invocation ou science n'existe. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-constructor-execution-authority-artifact-contract-identity-binding.md`.
  Validation locale : `3/3` tests administratifs et `382/382` tests H27.
- La revue externe de `a786d5730b488694728088368a33e7584f8f13e7`
  conclut `PASS`. Le lot courant definit seulement le schema ferme et le seal
  externe du futur artefact d'autorite d'execution : 108 chemins uniques sont
  rehashes. Il exige un `expected_git_head` lowercase hex40 explicite dans un
  futur artefact distinct revu/scelle et interdit tout fallback vers le HEAD
  courant. Aucun artefact runtime, HEAD concret, registre, reservation,
  invocation ou science n'existe. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-constructor-execution-authority-artifact-contract.md`.
  Validation locale : `3/3` tests administratifs et `379/379` tests H27.
  La premiere revue de `d3b80971326c2cf810b8fe6cc9e90e72a80d23db`
  conclut `FAIL` sur la couverture mecanique incomplete des invariants deja
  declares. La micro-correction conserve contrat et seal byte-identiques et
  verrouille tous les types, constantes, rejets JSON, regles futures et
  semantiques du seal; nouvelle revue requise avant tout identity binding.
- La revue externe de `8382475d7a0d7bfb5e5ccb7f75dd3f874afd6cea`
  conclut `PASS`. Le lot courant ajoute seulement l'identity binding du contrat
  corrige et son seal : 106 chemins uniques rehashes. Aucun artefact runtime ni
  `expected_git_head` concret n'existe. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-constructor-real-invocation-authorization-binding.md`.
  Validation locale : `3/3` tests administratifs et `376/376` tests H27.
- La revue externe de `df0c4996fe3118197985ffb4aead9e0588681396`
  conclut `PASS`. Le lot courant ajoute seulement le contrat declaratif et le
  seal de la future autorisation d'invocation : 104 identites uniques rehashees,
  sans registre, reservation, invocation ou artefact reel. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-constructor-real-invocation-authorization-contract.md`.
  Validation locale : `3/3` tests administratifs et `373/373` tests H27.
  Le futur artefact d'autorite devra lier un `expected_git_head` hex40 exact;
  egalite HEAD et worktree propre seront verifies avant le rehash104.
- La revue externe de `6cbcf1c477770c0c5b05a6505146e20a0fcb137b`
  conclut `PASS`. Le lot courant scelle le module effect-free exact, ajoute son
  identity binding et le binding seal : 100 predecesseurs, 102 chemins uniques
  rehashes. Aucune invocation ni reservation n'est autorisee. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-authority-instance-artifact-constructor-seal-binding.md`.
  Validation locale : `3/3` tests administratifs et `370/370` tests H27.
- La revue externe de `1f46498d94949efe1a1c380a85fa046538fd8e94`
  conclut `PASS`. Le lot courant ajoute uniquement le module constructor
  dormant/effect-free et ses tests. Les 98 identites sont rehashees avant les
  entrees runtime; aucun registre, destination ou filesystem n'est modifie et
  aucun artefact reel n'est cree. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-authority-instance-artifact-constructor-effect-free-implementation.md`.
  Validation locale : `14/14` tests constructor/contrats et `366/366` tests H27.
- La revue externe de `c80a7c73264ece3354f1f8e03acecd0f061d99a0`
  conclut `PASS`. Le lot courant ajoute uniquement l'identity binding du
  contrat constructor et son seal : contrat + seal + 96 predecesseurs = 98
  chemins uniques rehashes. Le module futur reste absent et les huit edges
  restent fermes. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-authority-instance-artifact-constructor-implementation-contract-identity-binding.md`.
  Validation locale : `3/3` tests administratifs et `358/358` tests H27.
- La revue externe de `2233f17cd6ce2814f1a086398114cceceb4227ef`
  conclut `PASS`. Le lot courant ajoute uniquement le contrat declaratif et le
  seal du futur constructeur d'artefact. Il lie quatre artefacts PASS/scelles
  et 92 identites amont, soit 96 chemins uniques. Chemin/entrypoint futurs sont
  fixes mais le module reste absent; aucun artefact, instance, destination,
  filesystem, materializer ou science n'est ouvert. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-authority-instance-artifact-constructor-implementation-contract.md`.
  Validation locale : `3/3` tests administratifs et `355/355` tests H27.
  Apres la premiere revue, les six garde-fous du constructor boundary sont
  aussi testes explicitement contre les invariants exacts du contrat PASS amont.
- La revue externe de `0e3abcf37c4909cd0b6eebdb5f43a2f051868f24`
  conclut `PASS`. Le lot courant ajoute uniquement l'identity binding du
  contrat d'artefact d'instance d'autorite et son seal. Il lie le contrat, son
  seal et 92 predecesseurs, soit 94 chemins uniques, et preserve les ordres
  canoniques top-level/nested, derivation et unicite ID/nonce, registre,
  reservation terminale, ordre one-shot et no-retry. Aucun artefact ou
  instance reel n'existe; issuer, destination, filesystem, materializer et
  science restent fermes. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-one-shot-real-execution-authority-instance-artifact-contract-identity-binding.md`.
  Validation locale : `3/3` tests administratifs et `352/352` tests H27.
- La revue externe de `46944859860f8dc2b07b7e4fa0a34bd7150ef81c`
  conclut `PASS`. Le lot courant ajoute uniquement le contrat declaratif et le
  seal du futur artefact d'instance d'autorite one-shot. Il lie les quatre
  identites PASS/scellees du contrat d'autorite et leurs 88 identites amont,
  soit 92 chemins uniques. Il fixe le format exact, l'issuer, la destination et
  les bindings de la chaine scellee, tout en preservant single-use, ordre,
  terminalite et retry interdit. Aucune instance n'existe ou n'est consommee;
  issuer, destination, filesystem, materializer et science restent fermes.
  Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-one-shot-real-execution-authority-instance-artifact-contract.md`.
  Validation locale : `3/3` tests administratifs et `349/349` tests H27.
  La premiere revue de `517c590a0bdfbeb967a2cff12d4a661a4eef97e4`
  conclut `FAIL`: ordre de champs contradictoire avec `sorted_keys` et absence
  de derivation/unicite terminale de l'identite et du nonce. La correction du
  meme contrat conserve l'ordre exact, definit la derivation SHA-256 et exige
  un registre persistant avec reservation terminale avant publication.
  La deuxieme revue de `cc8749ce...` confirme ces corrections mais exige aussi
  l'ordre normatif exact des six cles du sous-objet `sealed_chain_identity`;
  celui-ci est maintenant ferme et une permutation est rejetee par test.
- La revue externe de `9dcd506e95c74f03c0efe4a7e8117bbf7b841d86`
  conclut `PASS`. Le lot courant ajoute uniquement l'identity binding du
  contrat de la future autorite d'execution reelle one-shot et son seal. Il
  recompose le contrat, son seal et 88 predecesseurs, soit 90 chemins uniques,
  et preserve le single-use, l'ordre `rehash -> consume -> observe absence ->
  create-exclusive`, la terminalite et l'interdiction de retry. Aucune instance
  d'autorite n'existe ou n'est consommee; issuer, destination, filesystem,
  materializer et science restent fermes. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-one-shot-real-execution-authority-contract-identity-binding.md`.
  Validation locale : `3/3` tests administratifs et `346/346` tests H27.
- La revue externe de `b29d90a18461cd05ed003ab4cab53f7f49e04c1b`
  conclut `PASS`. Le lot courant ajoute uniquement le contrat declaratif et le
  seal externe de la future autorite d'execution reelle one-shot. Il lie les
  quatre identites PASS/scellees de l'autorisation d'issuance et leurs 84
  identites amont, soit 88 chemins uniques a rehasher avant toute consommation.
  L'ordre futur reste `rehash -> consume -> observe absence ->
  create-exclusive`; succes et echec post-consommation sont terminaux sans
  retry. Aucune instance d'autorite n'existe ou n'est consommee; issuer,
  destination, filesystem, materializer et science restent fermes. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-one-shot-real-execution-authority-contract.md`.
  Validation locale : `3/3` tests administratifs et `343/343` tests H27.
- La revue externe de `4752b06d4e290b012c9c4e705cdac08011ee3446`
  conclut `PASS`. Le lot courant ajoute uniquement l'identity binding du
  contrat d'autorisation d'issuance et son seal. Il rehash le contrat, son seal
  et 84 predecesseurs, soit 86 chemins uniques, tout en preservant l'ordre
  `rehash -> consume -> observe absence -> create-exclusive`. Aucune authority
  reelle n'existe ou n'est consommee; issuer, destination, filesystem,
  materializer et science restent fermes. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-real-issuance-authorization-contract-identity-binding.md`.
- La revue externe de `962e169e25acb11758a70e87ada78ab4004acad2`
  conclut `PASS`. Le lot courant ajoute uniquement un contrat declaratif et son
  seal pour une future autorisation d'issuance reelle one-shot. Il lie et
  rehache 84 identites uniques de la chaine issuer PASS/scellee. Destination et
  invocation restent declaratives et interdites; les huit edges restent
  fermes. Aucune issuance, authority, claim, capability, operation filesystem,
  materializer, population ou science n'est ouverte. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-real-issuance-authorization-contract.md`.
- La premiere revue de `a2941ed9bd40ca436958ab7d96504c748d1be478`
  conclut `FAIL` sur une contradiction entre preuve d'absence et premiere
  observation. La correction du meme contrat impose explicitement l'ordre
  futur `rehash -> consommation one-shot -> premiere observation d'absence ->
  create-exclusive`, sans executer aucune de ces operations. Nouvelle revue
  requise; aucun identity binding du contrat n'est encore autorise.
- La revue externe de `485c35b4d8469e483b438915ddf20aba0194d800`
  conclut `PASS`. Le lot courant scelle uniquement ce module issuer effect-free
  exact, ajoute son identity binding administratif et le seal du binding. Il
  rehache 80 predecesseurs et lie 82 chemins uniques avec le module et son
  seal. Les huit edges restent fermes; aucune invocation, issuance, authority,
  claim, capability, destination, operation filesystem, materializer ou
  science n'est ouverte. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-one-shot-authority-issuer-identity-binding.md`.
- La revue externe de `cb581c7e989715b808a8334127dd1dd50ad816fd`
  conclut `PASS`. L'implementation courante rehache 78 identites puis construit
  uniquement les bytes canoniques en memoire via adapters fake/in-memory qui
  doivent declarer zero effet. Aucun artefact, authority, claim, capability,
  destination reelle, filesystem ou science n'est cree. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-one-shot-authority-issuer-effect-free-implementation.md`.
- La premiere revue de `f8daca6a138285a1946420071b6d4dd32ae94f3b`
  conclut `FAIL`: verification trop tardive de certaines dependances, callbacks
  arbitraires non attestables et nonce reutilisable. La correction du meme
  module impose verify-before-parse, une probe immutable sans callable et un
  registre one-shot in-memory verrouille. La deuxieme revue de `7d06d022...`
  confirme ces trois corrections mais refuse les annotations Python non
  imposees a l'execution. La micro-correction exige donc des types natifs exacts
  pour les quatre entrees et les quatre champs de probe avant toute operation;
  un objet personnalise adversarial est rejete sans methode magique executee ni
  consommation du nonce. Nouvelle revue requise.
- La revue externe de `108728b98311c6e5c3a8eaf2909670b3768b3f08`
  conclut `PASS`. Le binding administratif courant lie le contrat issuer PASS,
  son seal et 76 identites preexistantes, soit 78 chemins uniques rehashes.
  Le chemin et l'entrypoint futurs sont preserves, mais le module issuer reste
  inexistant et non autorise. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-one-shot-authority-issuer-implementation-contract-identity-binding.md`.
- La revue externe de `005c4e5eedfbb10b0452f9fa3e1939e589234f89`
  conclut `PASS`. Le contrat declaratif courant lie les quatre artefacts
  PASS/scelles du contrat d'artefact d'issuance et 72 identites transitives,
  soit 76 chemins uniques rehashes. Il definit seulement les exigences de la
  future implementation issuer; aucun module, artefact, pouvoir, destination,
  operation ou science n'est cree. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-one-shot-authority-issuer-implementation-contract.md`.
- La revue externe de `b39668e3cc777061f0004dbad6c22b94e47465aa`
  conclut `PASS`. Le binding administratif courant lie le contrat corrige, son
  seal et les 72 identites preexistantes, soit 74 chemins uniques rehashes.
  L'issuer H27 exact, le manifeste canonique 72 et les huit edges fermes sont
  preserves. Aucun artefact, pouvoir, destination, operation ou science n'est
  cree; nouvelle revue requise. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-one-shot-authority-issuance-artifact-contract-identity-binding.md`.
- La revue externe de `007614a466033b8000ef8e9d2b119c517e264a95`
  conclut `FAIL`: schema non ferme, identites/timestamp insuffisamment
  contraints et compteur 72 sans liaison cryptographique. La correction ferme
  et ordonne neuf champs, fixe leurs types, l'issuer exact, la derivation de
  l'artifact_id, le nonce hex64 unique, le timestamp UTC strict et le SHA-256
  du manifeste canonique des 72 identites. Des tests adversariaux sont ajoutes.
  Aucun artefact ou pouvoir reel n'est cree; nouvelle revue requise.
- La revue externe de `0d528cb9a734c23b9993ef06adde6e0791c97d68`
  conclut `FAIL` sur l'unique issuer `h26-...`, incompatible avec l'identite
  H27 scellee. La correction impose `h27-execution-codex-mac-primary`, le
  verifie directement dans `fixed_paths_and_counts.issuer_identity` du contrat
  de composition et rejette l'ancien issuer H26. Nouvelle revue requise.
- La revue externe de `630b81d1ad8f13b21e79778d512083201da2fc60`
  conclut `PASS`. Un contrat declaratif et son seal lient quatre artefacts
  one-shot et 68 identites amont, soit 72 chemins rehashes. Ils definissent le
  format du futur artefact d'issuance sans le creer; authority, claim,
  capability, destination et science restent fermes. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-one-shot-authority-issuance-artifact-contract.md`.
- La revue externe de `827cccead21986fc77046911d2f9321c3c11d39c`
  conclut `PASS`. Le binding administratif et son seal lient le contrat, son
  seal et 68 identites amont, soit 70 chemins rehashes. Aucune authority,
  claim, capability, destination, operation ou science n'est ouverte. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-real-publication-one-shot-authority-binding.md`.
- La revue externe de `b9438c9ca9a1be2e66c22afb978ea2b6e5acd8dc`
  conclut `PASS`. Un contrat declaratif et son seal definissent seulement les
  regles d'une future autorite one-shot. Ils lient quatre racines PASS et 64
  identites amont, soit 68 chemins rehashes. Aucune authority, claim,
  capability, observation destination, operation ou science n'est ouverte.
  Rapport : `readme/results/2026-08-13_harmonic-censoring-h27-real-publication-one-shot-authority-contract.md`.
- La revue externe de `4ee1bc40e439dd9e5d21580b6c139c2e07bd24fd`
  conclut `PASS`. Le binding administratif et son seal lient le contrat exact,
  son seal et 64 identites preexistantes, soit 66 chemins uniques rehashes.
  Destination non observee, huit edges fermes et tous les etats operationnels
  ou scientifiques faux. Rapport : `readme/results/2026-08-13_harmonic-censoring-h27-real-publication-execution-authorization-binding.md`.
- La revue externe de `e6a67a0a30ecf0b9999b26695eeb66db4ceed216`
  conclut `PASS`. Un contrat declaratif distinct et son seal definissent
  uniquement les preconditions fail-closed d'une future autorisation
  d'execution reelle. Ils lient le destination contract, son seal, son binding
  et le seal du binding puis rehashent les 60 transitifs, soit 64 identites
  uniques. La destination n'est pas observee; open, create-exclusive, write,
  fsync, rename et toute operation/science restent interdites. Les huit edges
  restent fermes. `3/3` tests administratifs et `301/301` tests H27 passent.
  Le lot attend une revue externe; `locked_test_used=false`.
  Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-real-publication-execution-authorization-contract.md`.
- La revue externe de `85fc9d33f58a20575727be76fa6bc3678f145956`
  conclut `PASS`. Un identity binding administratif et son seal lient le
  contrat de destination exact, son seal et les 60 identites transitives, soit
  62 chemins uniques rehashes. Le graphe reste acyclique, sans self-hash ni
  back-reference, et les huit edges restent fermes. La destination n'est ni
  observee, ni creee, ni ouverte ou ecrite; tous les etats operationnels et
  scientifiques restent faux. `3/3` tests administratifs et `298/298` tests
  H27 passent avec le venv du projet. Le lot attend une revue externe;
  `locked_test_used=false`. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-real-publication-destination-contract-identity-binding.md`.
- La revue externe de `4c8d56d844e7c21623af1cc381b61d0c56136477`
  conclut `PASS`. Un contrat declaratif fixe maintenant l'unique destination
  future `/Users/amcarene/h27-admin/activation/h27-materialization-v1.json`
  sans la creer ni l'autoriser. Il lie les quatre artefacts PASS/scelles de la
  frontiere dormante et rehash les 56 upstream, soit 60 identites exactes. Son
  seal et trois tests administratifs maintiennent huit edges fermes et tous les
  etats operationnels faux. Une revue externe est requise; locked-test=false.
  Rapport : `readme/results/2026-08-13_harmonic-censoring-h27-real-publication-destination-contract.md`.
- La revue externe de `b7282164d04b4e0d99ba1d0b663116ecf62b2b7c`
  conclut `PASS`. Le module dormant exact possede maintenant son seal de revue,
  un identity binding administratif et le seal de ce binding. Le test rehash
  les deux racines administratives et les 54 identites transitives, soit 56
  upstream uniques. Le graphe reste acyclique, les huit edges restent fermes et
  destination, artefact, write, connexions, authority, materializer et science
  restent faux. Le lot attend une revue externe; `locked_test_used=false`.
  Rapport : `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-activation-artifact-real-publication-dormant-identity-binding.md`.
- La revue externe de `285daa719a38884cca1dadb3571c6cb7bba2cacf`
  conclut `PASS`. Un module Python distinct implemente maintenant uniquement la
  frontiere dormante de future publication reelle. Il rehash le binding et son
  seal puis les 54 identites liees avant toute sonde, valide le payload et les
  exigences fail-closed, consomme le one-shot juste avant la premiere sonde
  create-exclusive, et exige que toutes les sondes restent sans effet. Le
  nouveau public edge est `().__getitem__`, soit huit edges fermes. Aucun API
  filesystem direct, destination reelle, artefact, write, connexion,
  materializer ou science n'est execute. `7/7` tests cibles et `289/289` tests
  H27 passent; une revue
  externe du code exact est requise. `locked_test_used=false`. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-activation-artifact-real-publication-dormant.md`.
- La revue externe de `1115d5cc841e41a3ecd51620f3122117c270b6ad`
  conclut `PASS`. Un identity binding administratif et son external seal lient
  maintenant le contrat PASS exact, son seal, les quatre artefacts du
  simulateur dormant et ses 48 entrees amont, soit 54 identites uniques
  rehashees. Le graphe reste acyclique sans self-hash/back-reference. Seuls les
  etats administratifs contract exists/reviewed/sealed et binding exists sont
  vrais; implementation, destination, artefact, write, connexions, authority,
  materializer, science, locked-test, training et calibration restent faux.
  Les sept edges restent `().__getitem__`. `7/7` tests administratifs et
  `282/282` tests H27 passent;
  le binding exact attend une revue externe. `locked_test_used=false`. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-activation-artifact-real-publication-implementation-contract-identity-binding.md`.
- La revue externe de `2f8562d23a1b167bf9cd22db3d347f2d4238e661`
  conclut `PASS`. Un contrat declaratif distinct et son seal definissent
  uniquement les exigences fail-closed d'une future implementation reelle de
  publication. Ils lient les quatre artefacts exacts du simulateur dormant
  revu/scelle et rehashent transitivement ses 48 entrees amont, soit 52
  identites uniques. L'implementation, le chemin de destination, l'artefact et
  le write restent absents et non autorises; les sept edges restent
  `().__getitem__`; connexions, authority, materializer, science, locked-test,
  training et calibration restent faux. `8/8` tests administratifs et
  `275/275` tests H27 passent. Une revue externe du contrat et du seal exacts
  est requise avant toute autre portee. `locked_test_used=false`. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-activation-artifact-real-publication-implementation-contract.md`.
- La revue externe de `6ad0232d460819962a89dc1f307b59f7d13b8f6c`
  conclut `PASS`. Le module dormant corrige exact (blob `6d254f43...`, 12600
  octets, SHA-256 `f4c35a76...`) possede maintenant un seal de revue externe,
  un identity binding acyclique et le seal de ce binding. Le binding rehash les
  48 entrees amont uniques (quatre publication, quatre dormant-module et
  quarante dependances) sans modifier aucun predecesseur. Seuls les etats
  administratifs exists/reviewed/sealed du module sont vrais; les sept edges
  restent `().__getitem__` et filesystem, artefact, connexions, authority,
  materializer et science restent faux. `8/8` tests administratifs et
  `267/267` tests H27 passent; `locked_test_used=false`. Le lot attend une revue externe.
  Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-activation-artifact-publication-dormant-identity-binding.md`.
- La revue externe de `84c46f1f834efd4a4fed579dd9f5dbd696d24135`
  conclut `FAIL` sur un seul ecart de schema : le simulateur acceptait des
  identites gate/materializer arbitraires bien formees et ne validait pas
  `invocation_nonce` en hex lowercase 64. La micro-correction locale exige les
  blobs gate/materializer et le SHA du binding gate exacts deja imposes par le
  schema activation-artifact PASS, valide le nonce, et ajoute quatre cas
  adversariaux. Les 48 rehash, 21 preconditions, sept barriers, one-shot et
  garanties sans effet restent inchanges. `9/9` tests cibles et `259/259` tests
  H27 passent. Une nouvelle revue externe est requise; aucun filesystem reel,
  artefact, connexion ou science n'est ouvert. `locked_test_used=false`.
- La revue externe de `c74ecdb808283a42fff55dad5f10aa87354182c9`
  conclut `PASS` et autorise uniquement un simulateur dormant distinct. Le
  nouveau module rehash exactement les quatre artefacts publication, les quatre
  artefacts du module dormant et les quarante dependances avant tout adapter.
  Son harness synthetique valide un payload canonique, l'absence de destination
  et l'unicite, puis consomme un droit local one-shot immediatement avant les
  simulations create-exclusive, flush/fsync, visibilite atomique, reopen/rehash
  et fsync parent. Toutes les simulations doivent rester false. Succes ou erreur
  post-consommation est terminal sans retry. Les sept public edges restent
  `().__getitem__`; artifact created/written, connexions, materializer et science
  restent faux. `8/8` tests ciblés passent. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-activation-artifact-publication-dormant.md`.
- La revue externe de `ab19acf97bd919dd17d9a8daf98925e0937c22f0`
  conclut `PASS`. Un identity binding administratif lie maintenant ce contrat
  exact (blob `d4026726...`, 22288 octets, SHA-256 `82b10aae...`) et son seal
  (blob `28a2e397...`, 3628 octets, SHA-256 `148829df...`), les quatre artefacts
  du module dormant et les quarante dependances existantes. Un external seal du
  binding est egalement present. Graphe acyclique, aucun self-hash/back-reference,
  six public edges fermes. `7/7` tests administratifs passent. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-activation-artifact-publication-identity-binding.md`.
- La revue externe de `309b93153ee4df7a17ae13a85b70532c0a426a69`
  conclut `PASS`. Un contrat declaratif distinct definit maintenant uniquement
  les preconditions fail-closed d'une future publication atomique/exclusive de
  l'artefact d'activation. Il lie les quatre artefacts exacts du module dormant
  scelle et rebind les quarante dependances existantes. Le contrat et son seal
  n'ajoutent aucun Python, path de destination, artefact, write/O_EXCL,
  connexion, authority/claim/capability, materializer ou science. La future
  implementation reste absente, non autorisee et exige un commit/review/seal
  separes. `9/9` tests administratifs passent. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-activation-artifact-publication-contract.md`.
- La revue externe du correctif exact
  `19af83ea7127e16c1abccc05315e5651f6074241` conclut `PASS`. Le lot
  administratif suivant scelle uniquement le module corrige (blob
  `277e8e56...`, 11226 octets, SHA-256 `c3ae1b3c...`), ajoute son identity
  binding acyclique et le seal de ce binding. Il rebind directement les quatre
  artefacts activation-artifact et les trente-six dependances historiques
  byte-identical. Seuls le contrat et le module dormant exacts sont
  exists/reviewed/sealed; implementation operationnelle, artefact, connexions,
  authority/claim/capability, materializer et science restent faux. Les six
  public edges restent `().__getitem__`. `8/8` tests administratifs passent.
  Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-activation-artifact-dormant-identity-binding.md`.
- La revue externe de `d18ed0ffb9a815ec349fb43c844fa25360e02449`
  a refuse uniquement deux ecarts au schema scelle : `created_at_utc` ne
  validait que le suffixe `Z` et l'unicite de `activation_id` n'etait pas
  attestee. La micro-correction exige maintenant une forme RFC3339 UTC valide
  parseable (fractions acceptees, dates impossibles et `garbageZ` refusees) et
  une attestation synthetique explicite d'unicite apres les quarante rehash et
  avant consommation. Aucun autre chemin n'est modifie. `9/9` tests ciblés et
  `226/226` tests H27 passent; artefact/write/connexions/science restent faux.
- La revue externe de `cdb30334d79f46d4661ad349fc6e3ca3b9f8c311`
  conclut `PASS` et autorise un constructeur strictement dormant en memoire. Le
  nouveau module revalide quarante entrees scellees avant tout mock, construit
  et valide les quatorze champs ordonnes du schema, exige les seize preconditions
  fail-closed et simule create-exclusive sans aucun appel filesystem. Son ticket
  local est immutable et one-shot; succes ou erreur post-consommation interdit
  tout retry. La trace termine avec artifact created/written=false, connexions
  false, materializer/science=0 et terminal=true. Le sixieme public edge est
  `().__getitem__`. Le rapport initial et sa section de correction archivent les
  nouvelles preuves. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-activation-artifact-dormant.md`.
- La revue externe de `b22e7e5f8f8c2d1032c719ed19ec5e956613ed8d`
  conclut `PASS`. Un identity binding administratif lie maintenant le contrat
  exact (blob `f7baf8c1...`, 17525 octets, SHA-256 `a84427a2...`) et son seal
  (blob `0e2f5558...`, 3296 octets, SHA-256 `9d2de175...`), puis rebind les
  trente-six dependances gate/activation/bridge/compatibility/predecesseurs.
  Seuls contract exists/reviewed/sealed sont vrais. Implementation, artefact,
  connexions, execution, materializer et science restent faux. Les cinq public
  edges restent `().__getitem__`. `8/8` tests administratifs et `217/217` tests
  H27 passent. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-activation-artifact-identity-binding.md`.
- La revue externe de `da5acf7026e89afec4155880d8e0cf7b1bf73f21`
  conclut `PASS`. Un contrat declaratif distinct fixe maintenant le schema ferme
  d'un futur artefact d'activation, ses quatorze champs ordonnes et seize
  preconditions fail-closed. Il lie exactement les quatre artefacts gate PASS,
  les douze artefacts activation/connection, bridge et compatibility, ainsi que
  les vingt predecesseurs. Aucun path, SHA d'artefact ou implementation future
  n'existe; creation et implementation restent non autorisees et devront etre
  distinctes, revues et scellees separement. Les deux connexions et les cinq
  public edges restent fermees. `9/9` tests administratifs et `209/209` tests H27
  passent. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-activation-artifact-contract.md`.
- La revue externe de `339e79d6e7f49606c0bfd05b269e7b4cb34faeb3`
  conclut `PASS`. Le gate dormant exact (blob `d6047037...`, 13835 octets,
  SHA-256 `7162a858...`) possede maintenant un seal externe, un identity binding
  acyclique et le seal du binding. Le lot rebind les quatre artefacts
  activation/connection, quatre bridge, quatre compatibility et vingt
  predecesseurs sans les modifier. Seuls gate exists/reviewed/sealed sont vrais;
  gate operational, activation, les deux connexions, materializer et science
  restent faux. Les cinq public edges restent `().__getitem__`. `8/8` tests
  administratifs et `200/200` tests H27 passent. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-operational-activation-connection-dormant-identity-binding.md`.
- La revue externe de `e0c51e9f2006aabfcc104f3bf63caa8885aac607`
  conclut `PASS` et autorise un module gate strictement dormant. Ce nouveau
  module revalide avant tout mock les quatre artefacts activation/connection
  PASS, les quatre bridge, les quatre compatibility et les vingt predecesseurs.
  Son harness synthetique exige le binding step-11 exact et terminal, les
  identites authority/claim/nonce/PID/code, le bridge terminal ainsi que le blob
  materializer et sa barriere fermee. Il refuse toute observation d'un edge
  connecte ou autorise, puis consomme un droit local one-shot sans creer
  d'activation. Le succes et toute erreur post-consommation rendent le ticket
  terminal. L'entree publique du nouveau module est `().__getitem__`; les quatre
  edges historiques sont inchanges. `10/10` tests ciblés et `192/192` tests H27
  passent. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-operational-activation-connection-dormant.md`.
- La revue externe de `4327484ec20e4331277112ec7b4606f0cba923b5`
  conclut `PASS`. Un identity binding administratif lie maintenant ce contrat
  exact (blob `d084467f...`, 13281 octets, SHA-256 `7565b0fa...`) et son seal
  (blob `a76af483...`, 4090 octets, SHA-256 `7d8b6933...`), rebind les quatre
  artefacts bridge PASS, les quatre artefacts compatibility et les vingt
  predecesseurs byte-identical. Seuls contract exists/reviewed/sealed sont vrais.
  Activation, les deux connexions, le chemin d'execution, materializer et science
  restent faux; les quatre public edges restent `().__getitem__`. `8/8` tests
  administratifs et `182/182` tests H27 passent. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-operational-activation-connection-identity-binding.md`.
- Un contrat declaratif distinct decrit maintenant les deux futures transitions
  `composition -> bridge` et `bridge -> materializer`, mais les conserve toutes
  deux `connected=false` et `connection_authorized=false`. Il lie exactement le
  module bridge revu et ses trois artefacts de seal/binding, les quatre artefacts
  de compatibilite et les vingt predecesseurs byte-identical. L'activation future
  reste absente, non autorisee, distincte et exige un commit, une revue et un seal
  separes. Les conditions futures fail-closed couvrent HEAD/worktree, identites
  code/contrat, binding step-11 exact, consommation terminale, authority/claim,
  nonce/PID/code identity, one-shot bridge, blob/barriere materializer et absence
  de retry. `9/9` tests administratifs et `174/174` tests H27 passent. Aucun code
  Python ni octet predecesseur n'est modifie. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-operational-activation-connection-contract.md`.
- La revue externe de `22f5b501d632b45fd7ef68c98ce007f5aacc8f35`
  conclut `PASS`. Le bridge dormant exact (blob `6cc65097...`, 10443 octets,
  SHA-256 `23e33bc4...`) possède maintenant un external-review seal, un binding
  acyclique et le seal du binding. Le lot lie les quatre artefacts de
  compatibilité et rebind les vingt prédécesseurs byte-identical. Seuls module
  exists/reviewed/sealed deviennent vrais; le bridge reste non opérationnel,
  déconnecté de composition et materializer, sans chemin d'exécution. Les quatre
  public edges restent `().__getitem__`. `8/8` tests administratifs et `165/165`
  tests H27 passent. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-identity-seal-binding.md`.
- La revue externe de `52dd2ec3f12219b09cafbb8dc6a22d9e5a531540`
  conclut `PASS` et autorise un module bridge strictement dormant. Le nouveau
  module distinct revalide byte-exactement les quatre artefacts bridge puis les
  vingt prédécesseurs avant les adapters. Son harness privé reçoit uniquement
  le binding step-11 exact par identité, revalide authority/claim, nonce, PID,
  code identity, materializer blob et barrière, consomme un droit local simulé
  one-shot attaché au binding lui-même et dérive une capability materializer
  simulée. Un succès ou une exception après consommation rend donc le même
  binding terminal pour tout nouvel appel complet, sans registre global mutable. Il termine avec
  `materializer_invocations=0`, `science_invocations=0`, `terminal=true`. Les
  24 corruptions, le second appel complet et le retry après exception sont
  testés. L'entrée publique du
  bridge est exactement `().__getitem__`; les trois modules PASS existants
  restent inchangés et fermés. `12/12` tests ciblés et `157/157` tests H27 passent.
  Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-dormant-implementation.md`.
- La revue externe de `b4be1566c571e8dee9719091bcb41d8cda218fd7`
  conclut `PASS`. Un identity binding administratif lie maintenant le contrat
  bridge exact (blob `c03e81b9...`, 12630 octets, SHA-256 `fa394ba1...`) et son
  seal (blob `c0a09c2e...`, 3661 octets, SHA-256 `952eae11...`), puis rebind les
  20 prédécesseurs composition/boundary/materializer/historiques sans les
  modifier. Le graphe reste acyclique, sans self-hash ni back-reference. Seuls
  contract exists/reviewed/sealed deviennent vrais; bridge, implémentation,
  chemin d'exécution et invocation materializer restent faux. `8/8` tests
  administratifs et `145/145` tests H27 passent. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-compatibility-identity-binding.md`.
- La portée cumulative `69c343374e1f4a9c555e12cc40a8d883ea7bec40`
  puis `9828ddf2ef89dd6cddb88a482c88c0f1ef6abdd6` conclut `PASS`.
  Un contrat purement déclaratif fixe maintenant la compatibilité du futur
  bridge après consommation réussie de step 11 : seul le binding exact par
  identité peut être transmis, avec authority/claim SHA, materializer blob,
  nonce, PID et code identity inchangés. La capability consommée est terminale
  et ne peut pas entrer dans la science. Le contrat lie 20 prédécesseurs exacts,
  interdit stale claim, drift, mauvais binding/blob/nonce/process, second appel
  et appel direct. Le bridge reste absent, non autorisé et fermé. Son contrat et
  son seal passent `9/9` tests ciblés et la suite H27 passe `137/137`; aucune
  opération ni science n'a été exécutée. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-future-bridge-compatibility-contract.md`.
- La revue externe de `b2e6a06ebe236eb9f192d85497753ee878617ec6`
  conclut `PASS`. Le module dormant exact (blob `c57dbd4...`, 7289 octets,
  SHA-256 `6e2ccf31...`) possède maintenant un seal externe, un identity binding
  acyclique et le seal de ce binding. Ces trois nouveaux artefacts relient le
  commit/parent/module exacts ainsi que les chaînes composition, boundary,
  materializer, activation et authority déjà scellées, sans self-hash ni
  back-reference. Tous les prédécesseurs restent byte-identical. L'entrée
  publique reste exactement `().__getitem__`; step 12 reste absent et tous les
  états opérationnels/scientifiques restent faux. `8/8` tests administratifs et
  `128/128` tests H27 passent; `locked_test_used=false`. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-dormant-one-shot-composition-identity-seal-binding.md`.
- La revue externe de `f66e6008aa1ea1eb27773f4e069a23b03273506c`
  conclut `PASS` et autorise un module de composition strictement dormant. Le
  nouveau module distinct execute d'abord l'etape 1, puis rehache aux etapes
  2-4 les quatre artefacts composition/binding, les quatre contrats/seals
  historiques et les huit artefacts boundary/materializer PASS. Son harness
  injecte uniquement des mocks et exerce dans l'ordre les etapes 1-11; chaque echec
  coupe les etapes suivantes. Claim simule, paire capability/binding exacte et
  retour du binding exact sont imposes. L'etape 12 ne possede aucun callback :
  `science_invocations=0`. L'entree publique reste exactement `().__getitem__`.
  Le source ne contient ni NumPy, materializer, chemin admin, ecriture, plan ni
  locked-test. Aucun vrai issuer/authority/claim/capability/activation/bridge/
  materialization/science/population n'existe. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-dormant-one-shot-composition-implementation.md`.
- La revue externe du module exact au commit
  `e47effd1ac10987242b537f5b54a9cfbed84faeb` conclut `PASS` et autorise
  uniquement son scellement externe et le rebinding contractuel de son identite.
  Le seal lie le blob `79f39935...` (32 243 octets, SHA-256 `02bf7e9a...`).
  Un overlay acyclique lie cette identite et son seal sans modifier les contrats
  historiques ni le module revu. Les constantes d'activation du module restent
  `None` et son entree publique reste la barriere dormante. Aucun issuer,
  authority, capability, claim, activation, materialization, population, index,
  calcul NumPy, entrainement, calibration ou locked-test n'existe. `72/72` tests
  H27 passent; `locked_test_used=false`. Le lot exact attend maintenant une revue
  externe avant toute nouvelle portee. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-activation-capable-materializer-identity-seal-binding.md`.
- La revue externe de `b8f6d904d3b0bdf6db5dbce939e6cdf09ee6ac55`
  conclut `PASS`. Le nouveau module activable est maintenant implemente mais
  reste strictement dormant et non scelle. Sa logique scientifique est
  mecaniquement identique au blob dormant revu `d3a903ac...`; seuls le type de
  capability et le plumbing de frontiere d'autorite sont ajoutes. Le correctif
  adversarial remplace le garde Python mutable par `().__getitem__`, barriere
  native sans import substituable ni `__code__`; l'entree et les onze helpers
  refusent avant tout argument, meme apres rebinding. Les validateurs suivent
  l'ordre fail-closed scelle : identite code/seal et module/callables,
  HEAD/worktree, runtime complet (NumPy/multiarray/OpenBLAS inclus),
  environnement, puis claim/staging/final. Le rebinding litteral de
  `sys.modules` est teste. Ces controles sont effectifs mais restent
  inemissibles faute de seal/HEAD futur. Aucun issuer, authority,
  capability utilisable, claim, activation, population ou calcul n'existe.
  `py_compile`, `git diff --check` et `64/64` tests H27 passent. Les familles
  exigeant un futur claim restent declarees differees, sans claim factice.
  Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-activation-capable-production-materializer-dormant.md`.
- La revue externe de `ece4b630e15a895daef9dafeca4955ee7b338573`
  conclut `PASS`. Le nouveau lot contractuel définit maintenant l'unique
  différence future autorisée — le plumbing d'autorité —, l'ordre fail-closed
  jusqu'à la claim `O_EXCL`, une capability process-local non forgeable et les
  tests adversariaux monkeypatch/rebinding/appels directs requis. Le correctif
  de revue lie maintenant explicitement le contrat d'activation approuve au
  blob `2df0e536...` et son seal au blob `0ef61aa7...`; runtime, environnement,
  cinq inputs, namespace, comptages et destinations doivent etre derives de
  ces octets exacts, sans override. Le futur
  module activable reste absent, non autorisé et sans path/blob/SHA/seal ; le
  code dormant `d3a903…` reste inchangé et non exécutable. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-activation-capable-authority-contract.md`.
- La revue externe de `4a0fcadcfd82530212a7f9bc381cb678ff275bb2`
  conclut `PASS` : les appels directs aux onze helpers production sont tous
  bloqués avant NumPy/plan/filesystem et les payloads futurs sont relus puis
  vérifiés en taille/SHA avant l'index. Un seal externe acyclique lie maintenant
  le blob dormant revu `d3a903ac…` et affirme explicitement qu'il n'est jamais
  une cible d'activation. Le contrat d'activation rebondi distingue ce code
  dormant d'un futur matérialiseur activation-capable, distinct et toujours
  `exists=false`/`implementation_authorized=false`. Aucun garde n'est relâché,
  aucun issuer/capability/claim n'est créé et aucune population n'est lue ou
  produite. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-production-materializer-review-seal.md`.
- Le futur matérialiseur H27 de production est maintenant implémenté dans un
  module distinct du matérialiseur dormant historique, qui reste au blob Git
  `394f25a5…` inchangé. La nouvelle entrée échoue inconditionnellement avant
  tout accès à NumPy, au plan ou au filesystem ; aucun issuer, registre ou
  capability constructible n'existe. Le correctif de revue impose le même
  refus en première instruction de chaque helper capable de synthétiser ou
  publier, empêchant tout contournement par appel direct de fonction privée.
  Sous cette frontière dormante, le code
  décrit les 124 records dans l'ordre canonique, les recettes et collisions
  indépendantes, les huit grilles P2, les masques role-major, l'index à dix
  champs et la publication Darwin create-exclusive/fsync/rename-no-replace.
  Les tests restent administratifs/toy/fail-closed : aucun waveform H27 de
  production, payload, index ou destination n'a été créé.
  Chaque payload futur devra aussi être relu et vérifié en taille/SHA avant
  l'écriture de l'index, puis rehaché après l'index. Le contrat d'activation et
  son seal ne sont pas modifiés : ils continuent donc à
  interdire ce nouveau target jusqu'à un futur lot de binding/seal séparément
  autorisé. `py_compile`, `git diff --check` et 37 tests H27 passent. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-production-materializer-dormant-implementation.md`.
- La revue externe de `43d160bc5c0c0d5fc5b199363d007e768eec1080`
  conclut `PASS` : les trois bloqueurs capability/binding/result-schema sont
  fermés. La portée suivante reste contract-only. Un nouveau contrat scelle
  donc le materializer dormant comme référence revue jamais exécutable par
  l'activation, les cinq blobs H27, le runtime primaire exact,
  la future activation/authority/capability one-shot, la publication atomique
  de `H27_SYNTHETIC_V1` et la dérivation exclusive de
  `H27SealedRecordBinding` depuis une ligne vérifiée du futur index. Le contrat
  et son seal externe existent, mais activation, authority, capability, claim,
  population, index, loader et exécution restent absents. Le futur materializer
  de production est lui aussi explicitement absent/non autorisé et exigera son
  propre commit et seal avant toute émission. Rapport :
  `readme/results/2026-08-13_harmonic-censoring-h27-materialization-activation-contract.md`.
- Le contrat H27 engine/recomputer est désormais implémenté de façon dormante : il lie les
  cinq blobs H27 revus, fige record/mask/role semantics/ordre fail-closed,
  distingue corruption terminale et résolution scientifique `AMBIGUOUS`,
  effectue l'exact-zero avant FFT et le plancher non nul après FFT, et impose un
  recomputer réellement indépendant. Le profil primaire CPython 3.11.9 scelle
  désormais aussi son exécutable résolu, ses 152 624 octets et son SHA-256,
  symétriquement au profil secondaire. L'engine et le recomputer indépendant
  n'importent pas NumPy au chargement et échouent avant tout accès : le garde
  capability est maintenant un refus inconditionnel sans registre mutable, et
  le descriptor libre est remplacé par un binding nominal inconstructible qui
  lie futur index, ligne canonique, chemin, topologie/SHA payload et paramètres
  P2. Le schéma de résultat contractuel couvre exactement les 17 champs des
  deux implémentations et du comparateur. Population, FFT/NNLS, P0/P1/P2 et
  exécution scientifique restent absents. `py_compile`, `git diff --check` et
  19 tests dormants/materializer passent. Rapport :
  `readme/results/2026-08-12_harmonic-censoring-h27-engine-recomputer-design.md`.
- Le loader et materializer H27 restent strictement dormants : les cinq blobs
  H27 revus sont contrôlés avant parsing, les 17/27/107/124 identités et le
  masque role-major sont réconciliés, et les frontières de synthèse/publication
  échouent avant allocation ou accès filesystem faute de capability émissible.
  Le correctif de revue interdit aussi aux helpers toy le domaine de production
  `16640/44100` et les rôles H27 avant tout accès NumPy. Huit tests
  structurels/toy passent ; aucun waveform H27, record, index,
  authority, claim, FFT, NNLS, P0/P1/P2 ou locked-test n'existe. Rapport :
  `readme/results/2026-08-12_harmonic-censoring-h27-dormant-materializer-implementation.md`.
- La revue externe du correctif fail-closed `b3153024ce4a90a2af6aa344e4ddc08d1408637f`
  est approuvée et clôturée. Les helpers toy sont structurellement disjoints
  du domaine H27 de production ; la capability reste inémettable et les deux
  frontières échouent avant synthèse ou filesystem. Cette clôture n'autorise
  toujours ni matérialisation ni science. Rapport :
  `readme/results/2026-08-12_harmonic-censoring-h27-dormant-materializer-review-closure.md`.
- Le package de conception H27 fixe exactement 17 fixtures (`4/4/2/7`), 27
  tests (`9/9/9`) et 107 cellules P2 futures, soit 124 records de population
  conçus mais non matérialisés. Il lie les deux blobs H27 approuvés, conserve
  les 11 obligations `R-ZERO`, distingue exact-zero, quasi-zero et support
  invalide, et interdit toute dépendance de synthèse vers H26. Les recettes,
  formules, enveloppes, collisions et bruits sont autonomes ; chaque cellule
  P2 possède un ID, un ordre et des opérandes canoniques, y compris deux
  runtimes exacts. Le masque est un payload role-major canonique de 66 560
  octets, ce qui permet d'invalider les vues précédentes sans contaminer les
  vues courantes superposées. Toutes les autorisations restent à `false`;
  aucun code, waveform, test exécutable, authority ou claim n'existe. Rapport :
  `readme/results/2026-08-12_harmonic-censoring-h27-fixture-test-population-design.md`.
- La préinscription successeur H27 fige séparément les quatre rôles de vue :
  seules les vues `previous_*` exactement silencieuses et entièrement supportées
  peuvent être des contextes valides avec `T=0`. Les vues `current_*` nulles ou
  sous le plancher restent invalides et ne peuvent atteindre ni NNLS ni
  certificats. Les seuils, outcomes, causalité et exclusions d'oracle de H26
  sont inchangés. Onze cas data-only sont repris ; la population et les
  autorités H27 n'existent pas encore. Rapport :
  `readme/results/2026-08-12_harmonic-censoring-h27-preregistration.md`.
- Le design contractuel de remédiation examine trois options et préfère une
  sémantique explicite de silence valide limitée aux vues précédentes. La vue
  courante reste soumise au plancher positif actuel ; aucun epsilon, bruit,
  oracle ou changement de seuil n'est admis. H26 demeure clos et consommé :
  cette sémantique devra être préenregistrée sous un successeur H27 avec de
  nouvelles identités, population et autorités avant toute implémentation.
  Onze cas synthétiques purement déclaratifs ferment les invariants, dont le
  rejet explicite de `current_long=0`. Rapport :
  `readme/results/2026-08-12_harmonic-censoring-h26-p0-remediation-design.md`.
- L'analyse forensique strictement read-only confirme que `H26-F-P01` possède
  une fenêtre `current_short` non nulle, mais une fenêtre `previous_short`
  exactement silencieuse. `extract_raw_operands()` appelle ces spectres dans
  cet ordre et `causal_spectrum()` refuse la puissance totale nulle :
  l'exception P0-002 provient donc d'une incompatibilité déterministe entre la
  fixture préenregistrée et le kernel, pas d'une corruption de population.
  L'état P0 reste inconclusif consommé, sans retry et sans conclusion
  scientifique H26. Rapport :
  `readme/results/2026-08-12_harmonic-censoring-h26-p0-forensic-zero-power-p01.md`.
- L'unique invocation P0 réelle au commit `eaed599a5a051685288f1f71b3cb057db64392c2`
  a consommé sa claim, puis s'est arrêtée pendant P0-002 sur
  `ValueError: H26 spectrum total power invalid`. P0-001 est la seule preuve
  publiée et a passé ; aucun transcript n'a été produit. Le receipt terminal
  est `H26_P0_INCONCLUSIVE_CONSUMED`, avec une invocation, aucun retry, aucun
  P1/P2 et aucun locked-test. Aucune conclusion P0 globale ou scientifique H26
  n'est autorisée. Rapport :
  `readme/results/2026-08-12_harmonic-censoring-h26-p0-inconclusive-consumed.md`.
- La frontière P0 réelle one-shot est implémentée dans un runner distinct du
  runner scientifique dormant fake-only. Elle lie le runtime STOP 3, les
  authority/seal/index STOP 4, les trois contrats scientifiques et les blobs
  engine/recomputer/materializer avant une future claim durable. Le lifecycle
  versionné reste `real_execution_authorized=false`; les tests utilisent
  seulement des fakes et des répertoires temporaires. Aucun P0 n'a été lancé.
  Rapport :
  `readme/results/2026-08-12_harmonic-censoring-h26-p0-operational-entrypoint-stop4.md`.
- L'unique matérialisation H26 autorisée a terminé avec `exit=0`, exactement un
  appel du materializer et aucun retry. La population finale contient 40
  records baseline et 153 records P2 ; son index a le SHA-256
  `b0045797b08ef2ebbfaf7e1dda0c10f213eec3d8b3a3daaa31c8153dd842b4a7`.
  Aucun P0/P1/P2 scientifique n'a été exécuté. Rapport STOP 4 :
  `readme/results/2026-08-12_harmonic-censoring-h26-materialization-stop4.md`.
- La frontière réelle de matérialisation one-shot a lié cinq preuves STOP 3,
  le processus live exact, une autorité canonique et la destination fixe avant
  l'unique appel réel. Rapport d'implémentation :
  `readme/results/2026-08-12_harmonic-censoring-h26-materialization-operational-entrypoint-stop3.md`.
- L'unique qualification runtime réémise après l'échec préflight pré-claim a
  produit un record qualifié et un receipt terminal : observer appelé une fois,
  aucun retry, runtime Darwin arm64/CPython 3.11.9/NumPy 1.26.4/OpenBLAS ILP64
  conforme. Aucun materializer ni test scientifique n'a été lancé. Rapport :
  `readme/results/2026-08-12_harmonic-censoring-h26-runtime-qualification-stop3.md`.
- La frontière opérationnelle runtime one-shot est implémentée additivement,
  liée à l'activation STOP 2 et limitée à authority -> claim -> evidence dans la
  boundary -> observer privé -> record -> receipt final. Les tests utilisent
  uniquement une observation synthétique et des répertoires temporaires ;
  l'activation réelle reste inutilisée. Rapport :
  `readme/results/2026-08-12_harmonic-censoring-h26-runtime-operational-entrypoint-stop2.md`.
- STOP 1 a été approuvé sur `dee520da...`. L'activation H26 unique a ensuite
  été publiée sur le Mac : 26 champs canoniques, 1 735 octets, mode `0600`,
  SHA-256 `f96a811b...`, staging absent. L'exécution s'est arrêtée avant toute
  authority, claim ou observation runtime. Rapport :
  `readme/results/2026-08-12_harmonic-censoring-h26-runtime-activation-issued-stop2.md`.
- L'ancien processus passif H24 `49567` a été arrêté proprement ; aucun processus
  H24/H26 ni `active.lock` ne subsiste. Les checkouts Mac `~/midi` et
  `~/midi-worker/repository` ont été resynchronisés au dernier HEAD de chaque
  point d'arrêt vérifié ; le SHA exact est archivé dans le rapport correspondant.
- La frontière opérationnelle one-shot de publication d'activation est
  implémentée avec racine `/Users/amcarene/h26-admin`, issuer
  `h26-execution-codex-mac-primary`, requête canonique sur stdin, acknowledgement
  littéral, `HEAD` propre lié et publication Darwin create-exclusive/fsync/
  `renameatx_np(RENAME_EXCL)`/directory-fsync. L'étape s'arrête avant toute
  création de racine ou activation pour revue externe. Rapport :
  `readme/results/2026-08-12_harmonic-censoring-h26-runtime-activation-operational-entrypoint.md`.
  L'adapter réel est privé et exige une capability attestée par identité,
  créée seulement après la frontière acknowledgement/commit/clean-HEAD/Darwin.
  Les `21/21` tests de frontière passent sur macOS, y compris la publication
  Darwin réelle dans un répertoire temporaire, et les `20/20` modules H26
  passent isolément sur Windows et macOS.
- Le seal externe dormant lie le contrat d'émission `2f933536...`, son blob
  `05ec1c26...`, ses 5 624 octets exacts et le SHA-256 `e15dcb79...`.
  Les self-SHA sont absents et toute création reste interdite. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-issuance-contract-external-seal.md`.
- Le contrat dormant d'émission de l'activation H26 ferme une activation
  maximum, l'activation comme unique capability single-use, les règles exactes
  d'issuer/time/root et une future publication create-once/no-replace. Aucun
  issuer, activation, capability, root ou fichier n'est créé. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-issuance-contract.md`.
- La revue externe du validateur dormant `686d86bc...` est close sans
  bloqueur. Elle confirme le module `e74231e8...`, le test `b240505d...`, les
  26 champs exacts, les bindings scellés, la racine POSIX purement syntaxique,
  l'ID redérivé et le résultat immutable en mémoire. Aucune portée
  opérationnelle n'est ouverte. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-validator-review-closure.md`.
- Le validateur dormant de l'objet d'activation opérationnelle H26 est
  implémenté entièrement en mémoire. Il appelle obligatoirement le loader du
  seal approuvé, impose les 26 champs et toutes les valeurs fixes, valide
  syntaxiquement la racine POSIX, redérive l'`activation_id`, puis retourne
  uniquement les bytes canoniques et leur SHA-256 externe. Il ne crée ni
  activation, issuer, capability, chemin, runtime ou science. Les 10 tests
  dormants réussissent. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-validator-dormant-implementation.md`.
- La revue externe du loader dormant `37f5f2d5...` est close sans bloqueur.
  Elle confirme le module `feacb3c1...`, le test `053c107b...`, la
  vérification fail-closed du seal avant parsing, puis les bindings exacts du
  contrat corrigé. Activation, issuer, capability, root, authority, claim,
  runtime, matérialisation, science et locked-test restent absents ou à
  `false`, `null` ou `0`. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-contract-external-seal-loader-review-closure.md`.
- Le loader dormant du seal externe d'activation runtime H26 vérifie le blob
  du seal `685915e6...` avant parsing, impose son contenu exact et relit le
  contrat corrigé `d8d71bad...` en octets Git LF. Il impose le blob
  `c6eac6ae...`, la longueur 16 050 et le SHA-256 `ad3fd1a3...`; il ne crée
  aucun objet, chemin, issuer, capability ou exécution. Les 8 tests dormants
  réussissent. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-contract-external-seal-loader-dormant-implementation.md`.
- Le seal externe dormant lie les 16 050 octets exacts du contrat d'activation
  corrige `d8d71bad...` / blob `c6eac6ae...` au SHA-256
  `ad3fd1a3...`. Le seal ne contient pas son propre SHA et tous les etats
  activation/runtime/science restent `false`, `null` ou zero. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-contract-external-seal.md`.
- Le contrat dormant d'activation operationnelle du runtime H26 definit un
  objet futur ferme de 26 champs, une racine POSIX future, les chemins derives
  authority/claim/evidence/record/receipt, leur publication create-exclusive
  et atomique, ainsi que les echecs pre-observer et post-entry sans retry. Il
  lie toute la pile runtime approuvee jusqu'au proof-validator aval. Aucun
  objet, chemin, runtime ou calcul n'est cree ou consulte. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-contract.md`.
  Le correctif suivant interdit explicitement l'`authority_id` brut dans tout
  chemin : le slot authority est derive uniquement du SHA-256 canonique externe
  de l'authority validee, exactement 64 caracteres hexadecimaux lowercase.
- La revue externe du validateur dormant `fee9b981...` est close sans
  bloqueur. Elle confirme le module `0e6fbe5f...`, le test `a4b1f52d...`, les
  bindings exacts du contrat, du seal-loader et du proof-validator, ainsi que
  l'absence de factory, issuer, writer, seal, destination ou execution. Cette
  cloture n'ouvre aucune portee operationnelle. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-materialization-authority-artifact-validator-review-closure.md`.
- Le validateur dormant du futur artefact d'autorite H26 est implemente en
  memoire pure. Il charge le contrat exact `dd24346e...` / `b6b98b4c...`, lie
  le loader du seal et le validateur de preuve approuves, impose le keyset de
  36 champs, les types, les 24 valeurs fixes, une unique projection runtime
  `QUALIFIED`, la syntaxe POSIX/UTC/issuer, puis rederive `authority_id` et les
  octets canoniques. Il ne construit, n'emet et n'ecrit aucun artefact et ne
  consulte pas la destination. Les 18 tests dormants reussissent. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-materialization-authority-artifact-validator-dormant-implementation.md`.
- Le futur artefact d'autorité de matérialisation possède maintenant un contrat
  déclaratif fermé : keyset exact de 36 champs, types exacts, octets JSON
  canoniques, `authority_id` dérivé par une préimage SHA-256 domain-separated,
  preuve runtime complète uniquement `QUALIFIED`, destination future unique et
  seal externe séparé. Les bindings du contrat corrigé `84d1a196…`, de son
  seal `eb058ed…`, du loader approuvé `88593f7f…` et de sa clôture
  `f51eac20…` sont exacts. Aucun issuer, validator, authority, claim,
  destination, runtime, materializer ou calcul n'est créé. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-materialization-authority-artifact-contract.md`.
- Le loader dormant du seal externe corrigé, implémenté au commit
  `88593f7f065e7492af566e2ca90577c09916923e`, est désormais relu et clos. Il vérifie le blob exact du seal avant
  interprétation, impose son schéma, ses bindings et tous ses états
  `false`/`null`, puis relit le contrat corrigé en bytes Git LF. Il vérifie le
  blob `94f255c5…`, la longueur 19 310, le SHA-256 `a82b00cf…` et le blob
  historique `fd5e40fb…` du validateur de preuve. Cette clôture ne crée aucun
  objet ou fichier opérationnel. Rapport de clôture :
  `readme/results/2026-08-11_harmonic-censoring-h26-materialization-authority-contract-external-seal-loader-review-closure.md`.
- Le seal externe déclaratif du contrat corrigé d'autorité de matérialisation
  lie maintenant son commit `84d1a196…`, son blob Git `94f255c5…` et le
  SHA-256 `a82b00cf…` calculé sur les 19 310 octets exacts de ce blob. Il lie
  aussi la clôture du validateur dormant `0ff5f5e4…` et le validateur approuvé
  `18b8d5a7…` / module `fd5e40fb…`. Le seal ne contient pas son propre SHA et
  tous ses états opérationnels restent `false` ou `null`. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-population-materialization-authority-contract-external-seal.md`.
- Le validateur dormant de la preuve complète, implémenté au commit
  `18b8d5a73e61ab9143b897cb68479ae571c62bca`, est désormais relu et clos. Il
  réutilise le validateur terminal approuvé, accepte uniquement une chaîne
  artificielle QUALIFIED exacte et retourne une projection immutable de neuf
  champs. Cette clôture ne crée ni authority, claim, receipt, runtime record,
  destination, population ou autorisation scientifique. Rapport de clôture :
  `readme/results/2026-08-11_harmonic-censoring-h26-materialization-runtime-execution-proof-validator-review-closure.md`.
- Le contrat dormant d'autorité de matérialisation exige maintenant la chaîne
  complète authority runtime → claim consommé → preuve d'entrée observer →
  receipt terminal → record runtime exact. Le record doit être
  `H26_MATERIALIZATION_RUNTIME_QUALIFIED`; son SHA seul, un receipt sans record
  ou un record sans receipt sont insuffisants. Cette correction ne crée aucun
  objet et n'autorise aucune exécution. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-population-materialization-authority-contract.md`.
- La pile dormante codec canonique → identités déterministes → validateurs
  artificiels authority/claim/observer-entry evidence/receipt terminal est
  désormais relue et close. Cette clôture ne crée et n'autorise aucun objet ou
  chemin opérationnel. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-runtime-execution-validation-stack-review-closure.md`.
- Étape : `harmonic_censoring_h26_runtime_qualification_execution_authority_contract`.
- Contrat dormant de la future chaîne authority → claim consommé → unique
  invocation → runtime record + receipt défini. Les objets restent distincts,
  single-use, sans retry et sans auto-SHA. Un runtime record isolé ne pourra
  jamais prouver une invocation autorisée; la matérialisation exigera aussi la
  preuve claim/receipt approuvée. Tous les états présents restent `false` ou
  `null`; aucune authority, claim, exécution, record ou science n'a été créé.
  Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-runtime-qualification-execution-authority-contract.md`.
- Durcissement one-shot du contrat : chaque authority possède exactement un
  slot de claim dérivé de son identité et SHA; la première tentative le
  consomme même si elle échoue partiellement. Un receipt avec compteur `1`
  exige désormais une preuve créée depuis l'intérieur de l'entrée observer.
  Une panne après claim mais avant observer laisse authority/claim consommés,
  sans record ni receipt prétendant une invocation et sans retry.
- La preuve d'entrée possède désormais dix champs exacts, une identité et un
  slot uniques dérivés de l'authority et du claim consommés. Sa première
  tentative create-exclusive consomme le slot; aucun ID/path/process alternatif
  n'est possible. Le receipt doit lier exactement son ID et son SHA externe.
- Authority, claim et receipt possèdent maintenant des keysets canoniques
  fermés, sans champ additionnel. Le claim hérite obligatoirement du commit et
  du SHA du contrat d'exécution portés par l'authority consommée, sans valeur
  indépendante, wildcard ou fallback.
- Les quatre artefacts administratifs futurs ont désormais des octets
  canoniques uniques (UTF-8/ASCII-safe, clés triées, aucun whitespace ou float,
  LF terminal) dont dérivent leurs SHA. `claim_id` et l'ID d'entrée observer
  suivent des préimages SHA-256 domain-separated exactes; leurs slots logiques
  sont ces IDs. UUID, random, autre algorithme et JSON byte-noncanonique sont
  refusés; aucune racine filesystem réelle n'est encore définie.
- L'échappement JSON est maintenant totalement déterministe : short escapes
  fixes pour les contrôles usuels, hex lowercase, `/` et ASCII imprimable
  littéraux, Unicode non-ASCII en `\u` canonique, paire surrogate ordonnée et
  surrogate isolé interdit. Les spellings équivalents mais byte-différents
  sont refusés au lieu d'être normalisés.
- Les primitives dormantes d'exécution administrative sont maintenant
  implémentées sans issuer ni effet : loader lié au contrat `e0e070b8…` / blob
  `5ab6ff43…`, codec JSON canonique manuel, validation byte-exacte, SHA externe,
  dérivation domain-separated des IDs/slots claim et observer-entry, et
  keysets fermés. Le loader du seal externe vérifie en plus son commit/blob,
  tous ses états `false`/`null` et le SHA brut du contrat sur les mêmes octets
  Git LF qui produisent `5ab6ff43…`. Des validateurs purement mémoire
  revalident désormais authority, claim et preuve d'entrée artificiels,
  recalculent leurs SHA canoniques et redérivent intégralement leurs IDs sans
  créer d'objet. Le validateur terminal revalide maintenant aussi un receipt
  artificiel : il sérialise tout record artificiel avec le serializer dormant
  approuvé, rehache ses octets et exige le statut redérivé; la branche sans
  record impose SHA `null` et inconclusive-consumed. Les 48 tests n'utilisent
  que des objets
  artificiels; aucune
  authority, claim, preuve d'entrée, receipt, invocation ou science n'existe.
  Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-runtime-execution-primitives-dormant-implementation.md`.
- Le seal externe déclaratif lie maintenant le contrat d'exécution approuvé
  `e0e070b8…` / blob `5ab6ff43…` au SHA-256 brut `c7f6da69…`, calculé sur les
  `24080` octets exacts du blob Git, ainsi qu'aux primitives approuvées
  `48d3e601…` / blob `9c347a6c…`. Il n'est pas auto-haché et tous les états
  opérationnels restent `false` ou `null`; aucune exécution n'est autorisée.
  Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-runtime-execution-contract-external-seal.md`.
- Étape : `harmonic_censoring_h26_materialization_runtime_qualification_contract`.
- Contrat dormant de qualification du runtime primaire H26 défini sans
  qualificateur ni exécution : identité exacte CPython 3.11.9 / Darwin 24.5.0
  arm64 / NumPy 1.26.4 / OpenBLAS ILP64, binaires et environnement de processus
  sont préassignés. Le futur record est non auto-référentiel, atomique et
  one-shot après nouvelle autorisation. Tous les états courants restent
  `false` ou `null`; aucun Python, NumPy, BLAS, record runtime, destination ou
  calcul H26 n'a été lancé. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-materialization-runtime-qualification-contract.md`.
- Correctif de revue : le futur record lie maintenant structurellement ses
  commits, blobs, runtime attendu et dix variables de contrôle exactes. Son
  `observed_runtime` exclut les preuves binaires dupliquées, et son statut est
  dérivé dans l'ordre preuve manquante → inconclusive, mismatch comparable →
  disqualified, toutes preuves et égalités exactes → qualified. Cette fermeture
  reste purement déclarative et ne qualifie aucun runtime.
- Qualificateur runtime primaire H26 implémenté en mode dormant : loader lié au
  commit `89cc0659…` et à son blob corrigé `c3a02187…`, classification pure des
  trois terminaux, record canonique sans statut fourni ni auto-SHA, serializer
  déterministe et writer atomique derrière une capability sans issuer. Le
  module n'importe pas NumPy au chargement et les 17 tests n'utilisent que des
  observations artificielles. Aucun vrai runtime/record n'a été qualifié ou
  créé. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-runtime-qualifier-dormant-implementation.md`.
- Correctif de revue du qualificateur : le SHA-256 contractuel est maintenant
  calculé sur les mêmes octets LF canoniques que le blob Git, donc indépendant
  d'un checkout CRLF. Avant sérialisation, tout record est revalidé contre le
  contrat, reconstruit en observation et son statut redérivé; un `_payload`
  forgé ne peut pas imposer `QUALIFIED`. Les 22 tests artificiels passent;
  aucune observation réelle n'a été effectuée.
- Durcissement BLAS et preuves : le provider futur est dérivé uniquement d'une
  dépendance BLAS unique effectivement liée à `_multiarray_umath`, jamais d'une
  constante ou d'un fichier seulement présent. Le serializer n'accepte qu'un
  triplet binaire complet et canonique ou trois `null`; toute forme partielle
  ou mal typée est refusée. Les 29 tests artificiels passent sans exécuter
  `otool`, NumPy ou une inspection runtime réelle.
- Contrat dormant d'autorité de matérialisation H26 défini, sans issuer ni
  objet opérationnel : les trois SHA scientifiques et les cinq blobs Git revus
  sont liés, la sémantique one-shot/fail-closed future est spécifiée et les
  onze booléens d'autorisation restent `false`. Aucun waveform, index, record
  P2, population, runtime ou calcul n'a été créé. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-population-materialization-authority-contract.md`.
- Le SHA d'une future authority est défini sans récursion : un seal externe
  séparé devra lier ses octets, le SHA brut du contrat et le commit approuvé,
  sans que l'authority ou le seal contienne son propre SHA. Les trois SHA
  scientifiques, le blob materializer et `authority_schema_version=1` sont
  des égalités structurelles ; runtime et destination restent sans valeur
  présente et aucune authority effective n'existe.
- Clôture de revue : `H26_DORMANT_STACK_REVIEWED_AND_CLOSED`. La
  préinscription et la pile logicielle dormante sont revues jusqu'au commit
  `60b8d90bcbb5fb6e3a82d839bae706a359ab310e`. Cette clôture ne constitue
  aucune observation scientifique et n'autorise ni matérialisation, waveform,
  population index, p2_record, capability, authority, claim, P0/P1/P2,
  runtime scientifique, donnée réelle, modèle, entraînement, calibration ou
  locked-test. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-dormant-stack-review-closure.md`.
- Statut : `préinscription et implémentation dormante H26 revues et clôturées au commit 60b8d90b; 40 fixtures et 27 tests préenregistrés inchangés, 0 waveform, aucune exécution/authority/capability/claim`.
- Implémentation dormante H26 revue et clôturée au commit `60b8d90b…` : loader strict lié aux
  trois SHA, synthèse future inaccessible, masques dérivés des recettes,
  mesures causales 4096/8192, NNLS fixe, resolver quatre issues, transforms P2,
  opérandes bruts et recomputer indépendant. Les deux capabilities restent
  sans issuer; aucune waveform H26, aucun P0/P1/P2 et aucun runtime scientifique
  n'ont été exécutés. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-dormant-stack-implementation.md`.
- Après le refus externe de `62c6ab70…`, le producer relit désormais l'index
  scellé au moment de consommer une observation et refuse toute dataclass dont
  les octets ou métadonnées divergent du record réel. Toutes les mesures audio
  restent ancrées au `target_hop_end=16383`; seule la résolution terminale a
  lieu un hop plus tard à `16639`. Le recomputer lie indépendamment chaque
  perturbation à son test, sa grille et sa cellule scellés, y compris les
  coordonnées décalées P2. Le câblage complet artificiel du producer est
  maintenant exercé; aucune science ni matérialisation H26 n'a été exécutée.
- Après le refus externe de `082a0db8…`, l'index futur sépare explicitement
  chaque observation baseline de chaque observation P2 par le tuple exact
  `fixture_id/test_id/grid_id/cell` et par les SHA waveform, masque et
  alternate éventuel. Le producer refuse donc une observation baseline avec
  une transformation P2, revalide la cellule canonique avant toute mesure et
  relit uniquement les octets P2 correspondants. Le recomputer exige aussi
  l'ordre brut `24..96` ou `96..24` prescrit par la cellule de permutation.
  Ces gardes sont couverts uniquement sur des tableaux artificiels; aucune
  waveform H26 réelle ni phase P0/P1/P2 n'a été matérialisée ou exécutée.
- Après le refus ciblé de `f6bb6f10…`, le masque consommé par le producer est
  désormais celui du record rebindé et déjà vérifié, jamais un masque P2
  recomparé à la baseline. Un hop-shift laisse all-valid les fixtures sans
  frontière déclarée (P09/P10) et déplace strictement la frontière existante
  pour A10/A12, sans clipping ni padding. Les coordonnées proposition,
  résolution et lecture maximale suivent le même décalage.
- La préinscription H26 sépare désormais un certificat positif de naissance et
  un certificat négatif falsifiant une proposition candidate d'amplitude
  minimale préenregistrée. L'absence d'évidence indépendante seule produit
  `AMBIGUOUS`, jamais `NO_BIRTH`. Toute équivalence observationnelle a priorité
  sur les scores et doit rester ambiguë. Les six collisions exactes futures
  exigent deux décompositions latentes réellement non nulles et byte-identiques;
  une source de gain zéro ne peut plus servir de collision. Le paquet contient
  `40` fixtures seulement spécifiées et `27` tests dormants, sans moteur,
  signal, runner ou calcul. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h26-scientific-preregistration.md`.
- L'unique exécution scientifique H25 autorisée a utilisé le point d'entrée
  public sur le commit `0baccdf7…`, puis a publié un terminal contrôlé avec
  `exit_code=0` et `scientific_status=H25_SYNTHETIC_HYPOTHESIS_KILLED`. Le claim
  `4632c23c…`, le terminal `dc37219d…` et le transcript `900df302…` sont
  préservés. P0-001 à P0-003 passent ; P0-004 échoue parce que A04/A05 donnent
  `NO_BIRTH` au lieu des six `AMBIGUOUS` exigés. Les 23 tests restants sont
  `NOT_RUN_BY_KILL_RULE`; aucune erreur opérationnelle, donnée réelle, modèle,
  entraînement ou test verrouillé n'a été utilisé.
- L'analyse forensique approuvée confirme un conflit de contrat, pas une
  corruption : la règle générique transforme « aucune évidence nouvelle et
  explication parfaite par l'ancienne source » en `NO_BIRTH`, tandis que
  P0-004 impose de conserver `AMBIGUOUS` lorsque les deux causes latentes sont
  observationnellement identiques. L'absence d'évidence indépendante n'est
  donc pas une preuve négative d'absence. H25 est consommé, définitivement
  clos et non rejouable. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h25-terminal-forensic-closure.md`.
- La revue externe de `7117d01…` conserve l'architecture centrale mais exige
  trois corrections. L'activation ne contient désormais aucun SHA de son
  propre futur commit : seul le binding OS externe doit égaler `HEAD`. Les 27
  records P2-007 sont produits par les vrais producteurs puis vérifiés par le
  recomputer, et tout placeholder `{status: PASS}` est refusé. Le processus
  secondaire doit présenter une identité scellée incluant exécutable, bytes,
  version, plateforme et hash de commande. Enfin, une fermeture primaire
  cassée publie sur un chemin forensique distinct sans effacer ni écraser le
  `.part` primaire. Ce correctif reste TEST-ONLY et attend une nouvelle revue.
- La revue externe de `de73a8f…` approuve la complétude des preuves H25 et
  autorise uniquement le contrat de capability et l'autorité one-shot
  dormants. Ce bloc lie exactement le commit approuvé, les blobs moteur,
  recomputer et runner, cinq contrats/manifests, les trois SHA de population,
  le runtime Mac et la qualification administrative. La capability est
  factory-only, process-local et non copiable ; le wrapper passe à
  `CONSUMED_BEFORE_DELEGATION` avant le runner. Le claim futur utilise
  `O_EXCL` et fsync, le transcript contient toujours 27 records en ordre
  P0/P1/P2, et les fermetures success/failure/inconclusive sont atomiques.
  P2-007 ne peut recevoir aucune observation manuelle : un sous-processus
  secondaire pré-déclaré et lié par une future activation devra produire les
  36 mesures et 27 records via stdout canonique. Le seal, l'activation et le
  binding OS requis n'existent pas ; l'issuer s'arrête donc avant contrats,
  population et NumPy. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h25-dormant-scientific-capability-authority.md`.
- La matérialisation one-shot approuvée a publié exactement `36` fixtures,
  `108` artefacts et `111` fichiers, puis une vérification indépendante hors
  TTY a recomputé les `36×3` artefacts avec des PCG64 frais et confirmé
  l'identité byte-for-byte. Les SHA exacts sont : index `814d8c36…`, provenance
  `cadc154a…`, receipt `dbab8591…`. Aucun P0/P1/P2 n'a été exécuté.
- Après le rejet externe de `c47b9ba`, le recomputer H25 a été refondu sans
  aucun import du moteur : il reconstruit indépendamment graphe, opérateur et
  catégories depuis les opérandes bruts. Les spectres/fréquences nécessaires
  sont persistés côté producteur, l'état actif est une trace causale rejouable
  bornée à `16383`, P0-007 vérifie bien `16383/16127`, P2-002 couvre exactement
  `0/1/2/4` hops et P2-007 exige les observations détaillées d'un second runtime
  au lieu d'un self-compare. Les inverses P1/P2 perturbent maintenant les inputs
  bruts. Le second durcissement impose aussi un état initial entièrement
  inactif, compare les explications latentes à l'intérieur de chaque fixture
  A01…A06, exige l'ensemble analytique complet, couvre réellement les
  permutations fixture/candidate/transform/graphe et redérive tout rejet de
  mutation brute. `66` tests H25 autorisés passent, dont `21` tests du moteur
  dormant. Rapport de correction :
  `readme/results/2026-08-11_harmonic-censoring-h25-dormant-scientific-recomputation-correction.md`.
- Le moteur H25 dormant implémente maintenant le graphe H1/H2..H20, la grille
  vectorisée `s=0..88`, les masques et le null géométrique, les vues causales
  4096/8192 au même hop, le résidu d'explication par état actif et la résolution
  `INACTIVE→PENDING_NEW→ACTIVE/INACTIVE` à exactement un hop. Le registre lie
  les `27` producteurs dans l'ordre P0/P1/P2 et le recomputer séparé refuse les
  verdicts auto-déclarés. Le runner reste fail-closed avant NumPy/population :
  aucune authority, capability, claim, seal ou activation scientifique
  n'existe. Le rapport historique du premier bloc est conservé, mais son
  affirmation initiale d'indépendance a été rejetée puis corrigée par l'étape
  ci-dessus. `66` tests H25 ciblés réussissent, dont `21` tests du moteur
  `TEST-ONLY`; rapport :
  `readme/results/2026-08-11_harmonic-censoring-h25-dormant-scientific-engine.md`.
- Le contrat de future matérialisation H25 lie exactement CPython `3.11.9`,
  NumPy `1.26.4`, macOS `15.5` / Darwin `24.5.0`, arm64 CPU, un processus,
  les variables de threads, locale, timezone et hash seed. L’extension NumPy
  charge OpenBLAS ILP64 scellé par taille/SHA et doit refuser Accelerate. Chaque
  waveform future serait un flux `<f8` little-endian de `16640` samples, soit
  `133120` octets, accompagné de deux JSON canoniques ; l’index contient
  exactement `36` lignes et `108` fichiers. Le préflight doit précéder tout
  import NumPy scientifique et une recomputation indépendante byte-for-byte
  doit précéder la publication atomique. Le contrat n’implémente et n’autorise
  aucune de ces opérations. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h25-population-materialization-runtime-contract.md`.
- La première revue du contrat runtime a relevé une faute bloquante `PC64`.
  La recomputation exige désormais explicitement un nouveau
  `numpy.random.Generator(numpy.random.PCG64(seed))` pour chaque fixture, sans
  clonage, réutilisation, advance, jump, spawn ou seed caller. Cette correction
  est contractuelle uniquement et n’a généré aucun tableau ni waveform.
- Le materializer H25 est maintenant implémenté sous forme dormante : aucun
  import NumPy au chargement, aucun CLI et aucun issuer de capability. Le
  préflight, les 11 familles de synthèse, le bruit PCG64 white/pink, l’encodage
  `<f8`, les JSON canoniques et le recomputer sont testables, mais l’entrée de
  publication refuse toute invocation. Les tests ne génèrent que des fixtures
  `TEST-ONLY-*` explicitement hors population H25. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h25-dormant-population-materializer.md`.
- Après revue, le préflight dormant compare aussi macOS, les chemins executable
  et venv, CPU/GPU=0 et l’absence de framework GPU importé. Avant rename, index,
  provenance et receipt sont reconstruits puis comparés par taille, SHA et
  octets canoniques ; un simple test « non vide » n’est plus accepté.
- L’autorité de matérialisation one-shot H25 est maintenant définie mais
  dormante : elle lie le materializer approuvé `0036853f…` et les cinq inputs,
  exige un futur seal et binding OS absents, et ne peut émettre aucune
  capability. Son wrapper consommerait l’autorité avant délégation et interdit
  copie/retry/réutilisation. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h25-materialization-authority-dormant.md`.
- Le futur issuer exige en plus un SHA-256 du seal transporté extérieurement
  par une seconde variable OS et le vérifie avant parsing. Il revalide aussi
  les cinq Git blobs et le blob materializer depuis `HEAD:<path>`.
- Le seal ne contient plus le SHA du futur commit d'activation : le binding
  d'activation est externe (`AUTHORIZATION_COMMIT == HEAD`) et évite toute
  auto-référence Git. Le blob de l'issuer au `HEAD` doit rester exactement le
  blob d'autorité revu et scellé.
- Le seal d'autorisation H25 à dix champs est maintenant versionné pour revue,
  sans activer l'issuer ni positionner ses deux bindings OS. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h25-materialization-authorization-seal.md`.
- Les manifests H25 définissent exactement `36` fixtures neuves, équilibrées
  `12 positive / 12 negative / 12 ambiguous`, et `27` tests ordonnés
  `9 P0 / 9 P1 / 9 P2`. P1 consomme chaque fixture exactement une fois ;
  chaque phase couvre les `36` IDs. Les paramètres déterministes incluent la
  timeline `16640` samples, les formules de sources/enveloppes, RNG PCG64,
  bruit blanc/pink, chirp/OOD, gains/phases/cents/inharmonicité, fenêtres
  `4096/8192`, catégories et bornes CPU/mémoire. Les manifests ne contiennent
  aucune donnée audio : `materialized=false`, `waveform_count=0`,
  `executed=false`. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h25-population-test-manifests.md`.
- La première revue de `d8184f57…` a refusé l'ambiguïté de normalisation du
  bruit. Le correctif définit désormais le support exact `A=8192..16639`
  (`8448` indices), utilise ce même `A` pour la moyenne/RMS bruit et le RMS
  clean, impose l'ordre des huit opérations et assigne directement `+0.0`
  hors support après normalisation. Les SHA dépendants sont rebondés ; aucune
  synthèse n'a été effectuée.
- H25 préenregistre une hypothèse limitée : une courbe de dilution vectorisée,
  normalisée par le support et combinée à deux fenêtres causales finissant au
  même hop (`4096` primaire, `8192` confirmation), peut aider à distinguer une
  nouvelle fondamentale lorsqu'une attaque ou structure harmonique indépendante
  existe. La transformation seule ne peut jamais séparer deux contributions
  exactement confondues ; le raw disappearance index est interdit et ces cas
  doivent rester `AMBIGUOUS`. La grille est figée à `0..88` demi-tons, calculée
  depuis un seul spectre et non par `89` inférences. P0/P1/P2, kill rules,
  lifecycle one-shot et namespaces neufs `H25_SYNTHETIC_V1/H25_TEST_V1` sont
  définis, mais aucun manifest, fixture, waveform, runner, claim ou calcul
  n'existe. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h25-scientific-hypothesis-execution-contract.md`.
- L'unique qualification administrative H25 autorisée a été exécutée sur le
  commit exact `b91374473e28b1bb4ad42a73f62af4171411588d` et a produit
  `H25_ADMIN_LIFECYCLE_QUALIFICATION_PASSED`. Les `13` probes real-OS et les
  `6` cas administratifs ont tous été enregistrés puis recomputés : `158`
  fichiers, `157` bindings exacts, `16` surrogate claims consommés/préservés,
  `3` arrêts pré-claim sans claim et `worker_alive_count=0`. Le record canonique
  a le SHA-256
  `54bd361a99223dd24d6e4f0883ace47572965604c406efe69e5564f675d14ee1`.
  Aucun retry ni usage scientifique n'a eu lieu. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h25-administrative-lifecycle-qualification-result.md`.
- Le premier seal H25 `e82874c5…` a été rejeté : son `runtime_id` pouvait
  différer uniquement par le script de transport alors que les deux processus
  utilisaient le même CPython, et son record P2-007 s'incluait récursivement via
  des records bootstrap incomplets. La correction définit une projection
  `H25_P2_007_NONRECURSIVE_SELF_CORE_V1` recomputable, sépare identité
  scientifique et transport, et prépare un runtime secondaire isolé CPython
  `3.9.6` + NumPy `1.26.4` face au primaire CPython `3.11.9`. Le seal rejeté
  est remplacé par un seal lié au commit correctif `a638aa99…`; activation,
  bindings OS, capability, claim, observer et `P0/P1/P2` restent
  absents/non exécutés. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h25-p2-007-nonrecursive-runtime-correction.md`.
- L'unique tentative de qualification autorisée sur `a2cbed8…` a échoué avant
  `main()` et avant tout namespace/claim : le driver placé sous `tmp/local`
  n'avait pas la racine du dépôt dans `sys.path`. Le pilote externe l'a classée
  `CONFIRMED_H25_ADMINISTRATIVE_QUALIFICATION_LAUNCH_PREENTRY_FAILURE — NON_CONSUMING`.
  Le nouvel entrypoint suivi doit être invoqué exclusivement comme module
  `python -m`, exige un acknowledgement littéral et le SHA complet du commit
  revu, et possède un contrôle d'import zéro-exécution. Aucun des `13+6` cas
  n'a encore été exécuté ou consommé. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h25-administrative-qualification-entrypoint.md`.
- Le harness H25 standard-library-only implémente un namespace `h25-admin-*`,
  un claim substitutif `O_EXCL`, un transcript chaîné, trois preuves de
  frontière, les fermetures success/failure/inconclusive et un reçu forensique
  pour les échecs de publication. Il ne peut émettre aucune capability ou
  claim scientifique, importer NumPy ou ouvrir une population.
- Après le refus de `3d755c9c…`, les inverses de transport ne sont plus de
  simples exceptions injectées. `13` probes lancent réellement le worker comme
  module, avec config séparée du stdin de contrôle : EOF avant/après claim,
  rupture du processus parent, `SIGINT` OS sur Mac, délais monotoniques et
  terminaison vérifiée du PID. `16` tests réussissent sur Windows en `6,394 s`;
  le probe OS complet, `SIGINT` inclus, réussit sur Mac arm64 en `1,764 s`.
  Aucune qualification enregistrée n'a été lancée. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h25-preclaim-administrative-lifecycle-harness.md`.
- Après approbation de la clôture H24, H25 réserve une première étape purement
  administrative : qualifier de bout en bout le cycle capability, claim,
  phases et fermetures dans un seul processus revu. Le futur contrôle devra
  fonctionner malgré EOF, déconnexion SSH, signal, timeout et erreurs de
  publication, sans injection post-claim ni fabrication manuelle.
- Les namespaces `H25_SYNTHETIC_V1` et `H25_TEST_V1` sont seulement réservés.
  Aucun manifest, population, runner, capability, claim ou test H25 n'existe.
  H24 ne peut fournir ni population, identifiant, claim ou verdict au
  successeur. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h25-successor-decision-contract.md`.
- Le claim H24 a été acquis sur le Mac après validation du commit d'activation
  exact `4d31fa333683f83f2a35117ab5597faf1a7784a6`, du runtime arm64 CPU
  mono-thread et des bindings de la population publiée. Le fichier
  `tmp/local/harmonic_censoring_h24_scientific_v1.consumed.json` est préservé :
  `1922` octets, mode `0600`, SHA-256
  `5e7bf0326e4bffeca12b2917d09f7814023877f54f876d0f8e295800e5b661d2`.
- Le processus claimed avait été maintenu vivant dans un sas passif qui ne
  disposait d'aucun chemin scellé pour poursuivre vers P0. Il a donc été arrêté
  sous autorisation forensique sans exécuter de test : `P0/P1/P2=0/0/0`.
  Staging, success, transcript et terminal scientifique sont absents. Aucun
  terminal synthétique n'a été fabriqué.
- Cette exécution est classée `H24_EXECUTION_INCONCLUSIVE_CONSUMED` : elle ne
  produit aucun verdict scientifique, n'a utilisé aucun waveform scientifique,
  aucune donnée réelle, H17, locked-test, modèle, checkpoint, calibration ou
  training, et ne peut jamais être relancée. Rapport :
  `readme/results/2026-08-11_harmonic-censoring-h24-final-forensic-inconclusive-closure.md`.
- Après le remplacement du seal/activation et leur binding OS au commit
  `06ce7075…`, l'invocation zéro-science autorisée a échoué avant capability
  avec `H24 population terminal SHA mismatch`. Le terminal publié de `591`
  octets a le SHA-256 réel
  `50ec58c81d1a0ae53359676536d141c7f98ac337686c1baf66517bc3e39c54eb` ;
  le contrat schéma `9` contenait encore une valeur impossible de `65`
  caractères. Aucun claim, decode ou test scientifique n'a eu lieu.
- La portée corrective remplace uniquement ce digest, passe le contrat au
  schéma `10` SHA-256
  `89311ecd7afdc9b26ce4e6b0c09b52da22f4cf77e57694973e27f3a0056dd95a`
  et rebascule immédiatement le validateur de seal sur la nouvelle topologie
  exacte de ce commit. Le futur seal devra lier ce nouveau commit et son blob
  capability ; aucun seal n'est créé ici. La suite administrative H24/H23/H20
  réussit avec `222` tests ; `py_compile` et `git diff --check` réussissent.
- La revue du commit `696a94ea…` a approuvé le SHA marker corrigé, puis a
  confirmé qu'un nouveau seal honnête à 8 fichiers aurait encore été rejeté
  par `_validate_seal()`, qui exigeait l'ancienne topologie à 6 fichiers.
  La portée
  `AUTHORIZED_TO_CORRECT_H24_REPLACEMENT_SEAL_TOPOLOGY_VALIDATION_AND_REBASE_DORMANT_AUTHORITY_BINDINGS_ONLY`
  rebascule le validateur sur la topologie exacte du présent commit candidat.
  Le contrat passe au schéma `9`, SHA-256
  `8049f8d613cb45eba80e5d10b0fcc440b25ac317ec4cdac1c02ffbba735ad1af`.
  Ce correctif modifie le blob capability ; le futur seal devra donc lier le
  commit exact produit ici, sa topologie et ce nouveau blob. Aucun seal n'est
  créé dans cette étape. La suite administrative H24/H23/H20 réussit avec
  `222` tests ; `py_compile` et `git diff --check` réussissent également.
- Le premier appel autorisé à
  `issue_h24_scientific_execution_capability()` s'est arrêté avant émission de
  capability avec `H24 population marker SHA mismatch`. Le marqueur publié de
  `1805` octets a le SHA-256 réel
  `3185adfdba761590062378d7a230d9b990913d3197c2e9d1b006abbc0e62b85d` ;
  le contrat schéma `7` contenait une valeur impossible de `65` caractères,
  avec un zéro supplémentaire. Aucun claim scientifique, décodage waveform,
  P0/P1/P2 ou autre calcul n'a eu lieu.
- Le contrat schéma `8` corrigeait uniquement ce binding et possédait le SHA-256
  `d587358ad1dfebf9e7d4ea3eaeb632b080e8bc68e14fe4caa331cd803048387b`.
  Les `72` producteurs, le runner, les `18` overrides, les manifests et la
  population sont inchangés. Le seal `818e53cd…`, l'activation `4082cf4e…` et
  le binding OS vers `8f23054e…` restent physiquement inchangés mais ne lient
  plus le contrat courant : ils ne peuvent donc plus autoriser l'issuer.
  Prochaine action : revue externe du micro-correctif topologique seulement.
- `H24_SYNTHETIC_V1` est publié sur le Mac avec `175` fixtures, `525`
  fichiers fixture, index `b45b63c4…`, receipt `8a8128dc…`, marker
  `3185adfd…` et terminal `50ec58c8…`; l'audit read-only confirme tous les
  hashes, l'ordre, les tailles waveform et l'absence d'extra. Le nouveau
  contrat initial SHA-256 `63355a01…` lie ces octets aux manifests, contrats et
  sources H24. La revue de `02bb76b2…` a validé sa dormance mais exigé une
  fermeture supplémentaire de la preuve persistée. Le correctif contract-only
  SHA-256 `00f67158…` impose désormais `72` records JSONL canoniques dans
  l'ordre scellé, une
  chaîne SHA-256 empêchant suppression/insertion/réordonnancement, le binding
  des preuves persistées et un finalizer indépendant qui recalcule verdict,
  premier échec et suffixes depuis les octets relus. Le terminal futur devra
  lier transcript, dernier maillon, preuves ordonnées, claim et population; les
  erreurs ordinaires post-claim deviennent inconclusives consommées, tandis
  qu'un crash brutal reste consommé sans retry même si le terminal est absent.
  Une future capability scientifique, un seal/activation séparés et un claim
  scientifique distinct restent obligatoires avant tout décodage waveform.
  Après approbation de cette fermeture, la capability process-local, le
  preflight des `525` fichiers, le claim `O_EXCL`, le writer hash-chain et le
  finalizer indépendant ont été implémentés avec mocks. Le contrat schéma `3`
  a le SHA-256 `426a80be…`. Il n'existe toujours aucun seal/activation et le
  registre des `72` producteurs reste explicitement dormant; le runner échoue
  donc avant claim. Aucune donnée scientifique n'a été lue ou calculée.
  La revue de `e705afe5…` a ensuite trouvé un bloqueur topologique : un futur
  seal pouvait placer une sortie scientifique dans le namespace immuable de
  la population, ou imbriquer dangereusement les chemins one-shot. Le
  correctif autorisé ferme désormais ce namespace avant claim et n'autorise
  que trois descendances canoniques : `success→transcript`,
  `success→evidence` et `staging→transcript.part`. Le contrat schéma `4` a
  le SHA-256 `4d33f80b…`; aucune voie scientifique n'a été activée.
  La revue externe a ensuite autorisé uniquement
  `AUTHORIZED_TO_DEFINE_AND_IMPLEMENT_H24_EXACT_72_EVIDENCE_PRODUCERS_ONLY`.
  Le registre ordonné couvre maintenant exactement les `72` tests. A01 produit
  indépendamment le graphe typé fermé et ses sept mutations inverses; les `71`
  successeurs restants adaptent les noyaux de mesure H23 déjà versionnés aux
  waveforms/targets H24 vérifiés, sans resynthèse et sans verdict producteur.
  L'import construit seulement les callables : aucun producteur n'est appelé.
  La revue de `4737e74c…` a refusé deux écarts : les blobs exécutables du
  producteur et de son prédécesseur H23 n'étaient pas tous liés au futur seal,
  et `18` évaluateurs H23 atteignaient encore une voie de resynthèse. Le
  correctif autorisé lie désormais le module producteur, le runner et harness
  H23 ainsi que le SHA du contrat scientifique H23. Les `18` producteurs
  concernés utilisent des overrides H24 fondés uniquement sur les waveforms
  H24 publiées, leurs specs scellées et des transformations numériques de ces
  octets; un garde AST prouve qu'aucun évaluateur H23 réutilisé n'atteint
  `_render_source`, `_synthesize_h23_fixture`, `_projected_harmonic_waveform`
  ou `_waveform_from_sources`. Le contrat schéma `6` a le SHA-256
  `9a814216…`.
  La suite administrative H24/H23/H20 complète réussit avec `209` tests;
  `py_compile` et `git diff --check` réussissent également.
  La revue de `ed087827…` a validé la suppression de la resynthèse mais a
  refusé l'autorité tant que les blobs étaient vérifiés seulement au commit
  d'implémentation. Le nouveau garde exige désormais que les cinq blobs
  exécutables soient identiques au commit d'implémentation revu **et** au HEAD
  d'activation OS-bound réellement exécuté. Le contrat H23 est également
  ancré au SHA scientifique H23 déjà scellé `719eba0a…` dans le seal, le
  checkout et le commit d'activation. Le contrat schéma `7` a le SHA-256
  `a0726827…`.
  La suite administrative complète réussit avec `211` tests; `py_compile` et
  `git diff --check` réussissent également.
  Après approbation de `22bf8783…`, le seal scientifique H24 dormant est
  maintenant défini. Il lie le commit d'implémentation, les cinq blobs, les
  contrats H24/H23, la topologie, le runtime Mac arm64 CPU mono-thread et les
  sept chemins one-shot. Son SHA-256 est `818e53cd…`. L'activation reste
  absente : le seal seul ne permet toujours aucune issuance, claim ou mesure.
  La suite administrative complète réussit avec `216` tests et
  `git diff --check` réussit.
  Après approbation de `db738d35…`, le fichier d'activation H24 dormant lie
  exactement ce seal et les mêmes huit bindings. Son SHA-256 est
  `4082cf4e…`. Le commit d'activation doit encore être relu et aucun
  `H24_SCIENTIFIC_EXECUTION_AUTHORIZATION_COMMIT` n'est défini : sa simple
  présence dans Git ne donne aucune autorité runtime.
  La suite administrative complète réussit avec `220` tests et
  `git diff --check` réussit.
  Le binding OS-bound reste absent, donc l'issuer public échoue toujours
  avant registre, population, NumPy ou claim.
  Aucun evaluator/oracle, P0/P1/P2, donnée réelle, H17, locked-test ou training
  n'est autorisé. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h24-scientific-execution-authorization-contract.md`.
- Mise à jour : `2026-08-10`.
- Étape : `harmonic_censoring_h24_population_materialization_activation_transition`.
- Statut : `seal rafraîchi et commit d'activation contractuel créé; revue externe obligatoire; aucune autorité runtime`.
- Le commit d'activation autorisé lie exactement le matérialiseur revu
  `c51d8eaf…`, son blob source `1f763915…`, le seal SHA-256 `a4f8e48e…`
  et le contrat d'activation SHA-256 `3c40e7d0…`. La topologie est fermée à
  six fichiers de contrat, tests et documentation. Aucun binding OS n'est
  stocké, aucune capability n'est émise, aucun claim/marker n'est créé,
  NumPy réel n'est pas importé et aucune population ni mesure P0/P1/P2 n'est
  produite. La prochaine action est uniquement la revue externe de ce commit
  exact; une autorisation séparée restera nécessaire avant d'injecter le SHA
  du commit depuis l'OS. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h24-population-materialization-activation-transition.md`.
- Mise à jour : `2026-08-10`.
- Étape : `harmonic_censoring_h24_dormant_operational_numpy_bridge`.
- Statut : `seal/contrat approuvés; bridge NumPy H24 implémenté mais rendu inexécutable par le seal source volontairement obsolète; aucun claim, import NumPy réel, marker, waveform, population ni exécution; en attente de revue externe`.
- La revue externe a approuvé `5864cc35…` puis autorisé uniquement
  `AUTHORIZED_TO_IMPLEMENT_H24_DORMANT_OPERATIONAL_NUMPY_BRIDGE_ONLY`. L'entrée
  publique vérifie désormais claim, activation distincte, HEAD/worktree,
  contrat/seal, blob source et runtime avant l'import exact de NumPy 1.26.4,
  puis appelle le corps privé. Les erreurs post-claim produisent le terminal
  négatif consommé. Le seal actuel lie toujours le blob antérieur `16210df0…` :
  le preflight refuse donc toute capability contre ce nouveau source. Un futur
  commit distinct devra rafraîchir le seal, être revu, puis être OS-bound avant
  que le bridge puisse devenir utilisable. Après revue de `3ea3eefd…`, la
  revalidation `require_claimed` a été déplacée dans l'enveloppe terminale :
  seule l'attestation de type/identité, nécessaire pour obtenir une autorité
  sûre, la précède. Une revalidation de marker déjà consommé qui échoue produit
  donc elle aussi le terminal négatif. `171` tests H24/H23/H20 réussissent en
  `2,185 s`. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h24-dormant-operational-numpy-bridge.md`.
- La revue externe a approuvé `101103e6…` puis autorisé uniquement
  `AUTHORIZED_TO_DEFINE_H24_POPULATION_MATERIALIZATION_AUTHORIZATION_SEAL_AND_ACTIVATION_CONTRACT_ONLY`.
  Le seal lie ce commit, son blob source `16210df0…`, le contrat `b48aa4f…` et
  ses quatre fichiers modifiés. Le contrat d'activation lie le SHA du seal,
  les chemins fixes, le runtime exact et une seule matérialisation future, mais
  reste `contract_only_pending_external_review_no_runtime_authority`. Aucun
  OS-binding, bridge NumPy, capability opérationnelle ou claim n'est créé.
  `167` tests H24/H23/H20 réussissent en `1,971 s`.
  Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h24-population-materialization-activation-contract.md`.
- La revue externe a approuvé `2cf2be8e…` et autorisé uniquement
  `AUTHORIZED_TO_IMPLEMENT_H24_DORMANT_MATERIALIZER_CLAIM_AND_ATOMIC_PUBLISHER_ONLY`.
  Le nouveau module lie le contrat `b48aa4f…`, réimplémente exactement la trace
  numérique scellée, ferme la capability à 18 champs par identité, prépare le
  preflight sans NumPy, le futur `O_EXCL`, le staging/index/receipt/rehash et les
  publications atomiques. Aucun seal d'activation n'existe et l'entrée publique
  refuse explicitement le bridge NumPy même après claim. Les tests du claim
  mockent l'écriture : aucun marker ni octet scientifique n'est créé. La revue
  de `3a5cf3e8…` a ensuite relevé deux écarts dormants : identifiant S5 abrégé
  et accumulation regroupée par source. Le correctif reconnaît exactement
  `H24-F-S5` et ajoute chaque harmonique directement au waveform global, avec
  adversariaux S5 et multi-source. `160` tests H24/H23/H20 réussissent en
  `2,029 s`. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h24-dormant-population-materializer.md`.
  Toute activation ou tentative one-shot reste interdite avant nouvelle revue.
- La revue externe de `10aa49a8…` a approuvé conceptuellement le one-shot et
  la séparation science/matérialisation, mais a refusé le contrat final pour
  quatre ambiguïtés : defaults source incomplets, ordre numérique/RNG non
  normatif, valeurs des lignes d'index et hash des IDs sous-spécifiés, puis
  schémas capability/marker/runtime non fermés. Le correctif contract-only
  impose tous les defaults optionnels, une trace exacte des primitives NumPy,
  l'ordre sources/harmoniques/additions et des deux tirages pink-noise, les
  treize valeurs de chaque ligne `i`, la sérialisation canonique des IDs, et
  les ensembles de champs immutables de la capability, du marker et du runtime.
  Des adversariaux refusent default manquant, RNG inversé, dtype ambigu, hash
  d'IDs alternatif, autorité marker manquante et champ runtime additionnel.
  Aucune capacité opérationnelle n'est créée.
- La revue externe a approuvé `1b6aa275…` comme harness H24 dormant
  sémantiquement fermé et autorisé uniquement la définition du contrat de
  matérialisation/consommation. Le nouveau contrat lie le commit approuvé, ses
  blobs source et les cinq JSON H24 par SHA; il ferme la dérivation ordonnée
  des `175` recettes, l'algorithme déterministe `H24_WAVEFORM_ALGORITHM_V1`,
  les octets `.f64le`, les specs/targets canoniques, l'index JSONL et le reçu
  final. Une future tentative devra créer un marker durable `O_EXCL` avant
  NumPy ou la première allocation, puis publier atomiquement la population.
  Toute interruption après claim consommera `H24_SYNTHETIC_V1` sans retry et
  les sorties partielles resteront non autoritatives. La matérialisation restera
  strictement séparée de P0/P1/P2. Aucun code `src/`, materializer, capability,
  claim, marker, waveform ou résultat scientifique n'est créé ici.
  La correction finale scelle aussi les points de grille de `linear_cents` et
  `linear_semitones`, la trajectoire `sinusoidal_cents` et les six branches OOD
  par primitives NumPy exactes; `np.linspace`, SciPy chirp et les réécritures
  algébriques alternatives sont interdites. `143` tests contractuels
  H24/H23/H20 réussissent en `2,121 s`. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h24-population-materialization-contract.md`.
  La prochaine action est uniquement la revue externe de ce contrat; toute
  implémentation ou synthèse reste interdite.
- La revue externe a approuvé `16e612ba…` comme fermeture complète des manifests
  et du plan H24, puis autorisé uniquement le harness dormant. Le nouveau
  contrat `harmonic_censoring_h24_dormant_harness_contract.json` lie les quatre
  artefacts approuvés par SHA et maintient toutes les capacités de production,
  synthèse, P0/P1/P2, données réelles, H17, modèle, entraînement et locked-test
  à `false`. Le loader résout strictement `175` spécifications et `72` tests,
  traduit chaque fixture en recette immutable sans waveform, enregistre un
  producteur dormant et un recomputer indépendant pour chaque test, implémente
  les `27` opérateurs et l’unique sentinelle, puis applique la non-vacuité et
  les cardinalités avant tout opérateur. Un plan remplacé ou construit hors
  factory est refusé. La revue de `77a7dcc3…` a confirmé ces propriétés mais a
  refusé la création de population car A01 acceptait sept payloads inverses
  arbitrairement invalides. Le correctif dormant vérifie désormais chaque
  inverse contre sa mutation unique : I1 H1 non-identité, I2 harmonique rendu
  identité, I3 unique injection descendante, I4 unique mauvais type H1, I5
  unique omission, I6 unique doublon et I7 unique `+0.25`. Toute modification
  supplémentaire échoue. `126` tests administratifs H24/H23/H20 réussissent en
  `1,997 s`; aucun evaluator scientifique, fixture, waveform ou donnée réelle
  n’a été exécuté. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h24-dormant-harness.md`.
  La prochaine action reste uniquement la revue sémantique externe de ce
  commit dormant; aucune création de population n’est autorisée.
- La revue externe de `4cfd4a60…` a validé cardinalités, namespaces, bindings,
  kill rules et scope zéro-science, mais a refusé l’implémentation pour trois
  ambiguïtés contractuelles. Le correctif ferme maintenant les `27` opérateurs
  et l’unique sentinelle par une sémantique normative exhaustive, persiste pour
  chacun des `72` tests une sélection exacte de fixtures H24 indépendante du
  texte libre, et décrit explicitement la transition entre le snapshot
  successeur historique (manifests alors absents) et l’état actuel (manifests
  définis mais population non matérialisée, aucun evaluator/oracle/test). Des
  adversariaux structurels couvrent registre incomplet/inconnu, sentinelle
  inconnue, fixture non liée, sélection vide inexpliquée et transition
  contradictoire. La seconde revue de `78effef6…` a validé ces trois fermetures
  puis détecté une vacuité possible des preuves universelles sur `[]`. Le
  correctif exige maintenant au moins un élément pour toute evidence array,
  sans exception vide, et fixe `H24-A02.analytic_pairs` à exactement `42`
  paires (`7` shifts × `6` cutoffs); les tableaux vides et cardinalités
  incorrectes échouent avant l’opérateur. `107` tests contractuels H24/H23/H20 réussissent en `1,382 s`
  sans evaluator scientifique ni donnée réelle. La prochaine action reste uniquement la revue externe de ce
  correctif JSON/tests/docs; aucune synthèse ni implémentation n’est autorisée.
- H24 possède maintenant deux manifests canoniques liés au contrat successeur :
  `175` spécifications de fixtures (`6+169`) sous `H24_SYNTHETIC_V1` et `72`
  tests redérivés (`1+71`) sous `H24_TEST_V1`, répartis `27/35/10` en
  P0/P1/P2. Les IDs et seeds sont nouveaux; aucun outcome H23 n’est repris.
  Chaque test persiste un evidence schema explicite et interdit le verdict du
  producteur. Les kill rules restent arrêt-au-premier-échec et un succès futur
  ne pourrait autoriser que la préparation d’un protocole train. Les manifests
  déclarent tous waveform/fixture/evaluator/exécution à `false`. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h24-manifests-full-test-plan.md`.
- Après approbation de la clôture H23, H24 définit prospectivement un graphe
  harmonique typé : `H1` est la relation réflexive `FUNDAMENTAL_IDENTITY`,
  tandis que `H2–H20` sont les seules arêtes `PROPER_HARMONIC_ASCENT`
  strictement ascendantes. Le nouveau test `H24-A01-GRAPH-DIRECTION` sépare les
  deux invariants. L’ensemble admissible `E` est défini par arithmétique entière
  exacte; le futur oracle devra imposer couverture, unicité, absence d’extra,
  recomputation de `q(p,h)`, typage dérivé du rang et sept inverses adversariales.
  Les namespaces futurs sont
  `H24_SYNTHETIC_V1` et `H24_TEST_V1`; aucun manifest, fixture, evaluator,
  oracle ou calcul H24 n’existe encore. H23 reste consommé et non relançable.
  Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h24-successor-contract.md`.
- L’unique passe synthétique H23 autorisée a créé son claim durable puis s’est
  arrêtée conformément à la règle P0 au premier test `A01`. Le résultat
  autoritatif est `H23_SYNTHETIC_HYPOTHESIS_KILLED` : `1/72` test exécuté,
  `0/1` réussi, `71` non exécutés et `0/175` fixture matérialisée. Aucune donnée
  réelle, population H17 ou locked-test n’a été utilisée. Le primaire A01
  échoue parce que le graphe préenregistré inclut `H1`, donc des arêtes identité
  `pitch → pitch`, alors que l’oracle scellé exige strictement
  `edge[1] > edge[0]`. L’inverse descendante passe. Le transcript, le marker et
  le rapport terminal sont persistés et hashés sur le Mac; aucun retry n’est
  autorisé. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h23-synthetic-one-shot-result.md`.
- La revue externe approuve `1025ac56…` et autorise uniquement la création du
  nouveau couple contractuel. Le seal lie ce commit d'implémentation, son vrai
  diff-tree de cinq fichiers, les blobs capability/runner, les trois contrats,
  les manifests et les quatre chemins one-shot. L'activation lie le SHA brut du
  seal et répète les bindings d'implémentation. Les SHA bruts sont
  `381d83e5…` pour le seal et `81d0f0d6…` pour l'activation. La variable OS
  `H23_AUTHORIZATION_ACTIVATION_COMMIT` n'est pas injectée : le loader reste
  dormant avant résolution du plan et aucune capability, claim ou exécution
  n'est possible. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h23-reviewed-activation-seal-refresh.md`.
- La revue externe approuve `a84f106a…` comme correction sémantique dormante
  des 72 procédures et autorise uniquement le commit TOCTOU séparé. Ce
  durcissement rehache désormais, juste avant le `O_EXCL` irréversible,
  l'activation, le seal, les trois contrats, le plan et ses deux manifests
  résolus, le harness, le runner, le recomputer pur et le runtime. Une dérive
  de contrat, manifest, source ou runtime échoue avant toute création du
  marker. La préparation du répertoire précède la revalidation; après celle-ci,
  l'opération filesystem suivante est le `os.open(O_CREAT|O_EXCL|O_WRONLY)`.
  Le correctif post-revue exige aussi `HEAD == activation_commit` au préclaim.
  Après claim, le loader du contrat scientifique lit ses octets une seule fois,
  vérifie leur SHA contre `claimed.contract_sha256`, puis parse exactement ce
  buffer. `81` tests contractuels H23/H20 réussissent sans appeler les evaluators.
  Aucun seal, activation, claim réel, marker, waveform ou P0/P1/P2 n'est créé.
  Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h23-preclaim-toctou-hardening.md`.
- La revue externe de `6e016783…` valide le registre 72/72 et la recomputation
  indépendante mais refuse encore le TOCTOU : plusieurs producteurs écrivaient
  une conclusion attendue. Le nouveau correctif exécute effectivement les
  procédures D04/D08/C02/C04, NNLS/cardinalités, variantes guitare/OOD,
  instrumentation P01/P02/P04/P05 et les trois grilles TS01. Les ensembles
  TS01 passés/échoués/sauvés/régressés et les transitions D08 sont persistés et
  recomputés. Les inverses citées sont désormais des mutations ou validators
  réellement exécutés. `76` tests contractuels réussissent sans appeler les
  evaluators. Aucun seal, activation, claim, marker, waveform ou P0/P1/P2 n'est
  créé. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h23-semantic-evaluator-fix.md`.
- La revue externe de `907bece…` a refusé le futur seal : certaines familles
  utilisaient encore des décisions génériques et le finalizer pouvait accepter
  des booléens produits par la même logique que l'oracle. La correction remplace
  ce chemin par deux registres fermés et exactement concordants de 72 IDs : un
  évaluateur dédié par test et un recomputer pur par test. Le recomputer impose
  les mesures, clés, types, opérateurs et tolérances, puis recalcule primaire,
  inverse et verdict depuis les mesures persistées. Des tests adversariaux
  refusent désormais `passed=true` avec mesures incompatibles et toute inverse
  falsifiée. `74` tests contractuels H23/H20 réussissent sans appeler les
  évaluateurs scientifiques. Aucun seal, activation, claim, marker, waveform ou
  P0/P1/P2 n'est créé. Le durcissement TOCTOU demandé restera un commit dormant
  séparé après approbation de celui-ci. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h23-exact-oracle-recomputation-fix.md`.
- Le commit courant implémente ensemble la claim durable `O_EXCL`, le snapshot
  complet d’autorité, le synthétiseur/exécuteur H23, le transcript JSONL
  canonique hash-chain et le finalizer autoritatif qui recalcule le verdict
  depuis les octets persistés. L’ancien couple activation/seal `31b116c…` est
  désormais rejeté structurellement car il ne lie ni le nouveau contrat
  `8126edc0…` ni le chemin du transcript. Aucun nouveau seal/activation n’est
  ajouté par cette étape : le code reste donc inexécutable en production.
  Les tests utilisent uniquement des répertoires temporaires et des événements
  administratifs synthétiques; aucune waveform, population H17, donnée réelle,
  modèle, checkpoint ou test verrouillé n’a été chargé. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h23-claim-executor-transcript-implementation.md`.
- La revue externe de `84179a1…` approuve la preuve administrative et autorise
  uniquement le contrat de la future chaîne autoritative. Le claim devra être
  `O_EXCL` puis `fsync(file)+fsync(directory)` avant la première waveform et
  restera consommé après toute erreur. L’exécuteur n’acceptera aucun résultat
  ou choix du caller; le transcript JSONL canonique hash-chain liera marker,
  seal, activation, sources, manifests, runtime, fixtures et tests. Le
  finalizer relira uniquement les octets persistés. Claim, exécuteur,
  transcript et finalizer devront être implémentés et revus ensemble, puis un
  nouveau seal/activation sera obligatoire : le couple `31b116c…` ne pourra
  pas autoriser leurs nouveaux blobs. La capability future snapshottera
  activation+seal avant claim; aucune autorité ne sera relue depuis l’env.
  Les quatre événements JSONL ont désormais un envelope et un jeu de clés
  exacts, sans champs supplémentaires, et leur hash inclut le LF terminal.
  Le SHA brut du présent contrat sera lui-même lié par le futur seal,
  l’activation, la capability, le marker, le header, la constante source et le
  finalizer. Les hashes des listes ordonnées utilisent un tableau JSON canonique
  UTF-8+LF exact; le hash du préfixe terminal couvre les octets persistés du
  header à la ligne préterminale, chaque LF inclus.
  Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h23-executor-claim-transcript-contract.md`.
- La revue externe de `31b116c…` approuve le couple activation+seal et autorise
  l’injection OS administrative du commit exact. Le worker Mac CPU a passé le
  preflight, émis une capability process-local attestée, puis s’est arrêté
  exactement sur le garde `PRODUCTION_H23_SCIENTIFIC_EXECUTOR_IMPLEMENTED=false`.
  Le job `h23-admin-capability-31b116c` termine `exited_nonzero/1`, sans marker,
  destination, terminal, waveform ni test P0/P1/P2. La population synthétique
  reste non consommée. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h23-administrative-capability-issuance.md`.
- La revue externe de `f384cea…` approuve la transition et autorise la
  définition séparée des deux artefacts. Le seal canonique lie le commit revu,
  son vrai `diff-tree`, les blobs capability/runner, les contrats et manifests,
  le runtime et les chemins one-shot. L’activation canonique lie son SHA et
  répète les trois bindings d’implémentation. Les sources capability/runner ne
  sont pas modifiées. `H23_AUTHORIZATION_ACTIVATION_COMMIT` n’est pas injecté :
  aucun loader autorisé, capability, claim ou calcul scientifique n’est donc
  possible avant la revue de ce nouveau commit. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h23-activation-and-seal-definition.md`.
- La revue externe de `1640d425…` approuve la dormance actuelle et confirme
  qu’aucun chemin vers `claimed`, `authoritative=true` ou `global_go_status`
  n’est accessible. Elle a toutefois interdit de créer le seal tant que son
  SHA devait être incorporé au source qu’il atteste. La transition retire
  cette circularité : un futur artefact d’activation séparé liera le SHA du
  seal et les blobs d’implémentation, tandis qu’un worker OS mono-usage devra
  injecter le commit d’activation complet déjà revu. `HEAD`, le worktree et le
  blob Git de l’activation seront vérifiés avant le seal et avant le plan H23.
  `exact_changed_files` reste le diff exact du commit revu; une source inchangée
  n’y est pas ajoutée artificiellement, car les blobs des deux sources sont
  vérifiés séparément au commit revu et dans le checkout courant.
  Aucun artefact d’activation ou seal n’existe encore. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h23-seal-activation-transition.md`.
- Après l'approbation finale du contrat `ee00bcf6…`, les modules de capability
  et de runner ont été ajoutés sans exécuteur scientifique. Le seal reste
  inexistant (`SHA=None`), la factory échoue avant le resolver et le runner ne
  référence pas le claim. Le claim public est désormais un refus inconditionnel
  (`H23_CONSUMPTION_CLAIM_IMPLEMENTED=false`). Les six droits futurs sont
  validés séparément; la capability est attestée par une closure sans
  token/registre exposé, dans un threat model explicitement non hostile et non
  réflexif qui exigera une frontière OS s'il est élargi. Les trois
  builders succès/kill/inconclusif ne produisent que des brouillons sans
  `global_go_status`; la finalisation autoritative refuse aussi tant que
  l'exécuteur scientifique et le claim restent absents. Les onze tests ajoutés
  sont purs et ne synthétisent rien. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h23-dormant-execution-implementation.md`.
- Le contrat séparé de future capability lie le harness approuvé `e97674cd…`,
  le contrat H23 `719eba0a…`, les manifests `175/72` et le runtime futur. Il
  impose une capability non constructible/copiable, un seal d'autorisation
  ultérieur encore inexistant avec les six droits explicites d'émission,
  d'exécution synthétique/scientifique et de phases P0/P1/P2,
  un claim one-shot avant la première waveform, l'ordre P0→P1→P2 et une
  publication atomique distincte pour succès complet, échec scientifique
  terminal et incident opérationnel inconclusif. Un échec scientifique publiera
  son préfixe exécuté et les IDs restants `NOT_RUN_BY_KILL_RULE`; l'exigence
  `175/72` ne s'applique qu'au succès. Tous les droits restent à `false`; la
  garde inconditionnelle du harness n'est pas modifiée. Les onze tests ajoutés
  sont contractuels uniquement. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h23-synthetic-execution-capability-contract.md`.
- La revue externe finale de `e97674cd1d1c3a12ff113f98789105941ab17030`
  conclut `APPROUVÉ`. Elle confirme le resolver/materializer, le test adversarial
  et la garde inconditionnelle : les dataclasses ne peuvent pas être forgées en
  capability. Cette approbation ne couvre aucune synthèse ni exécution.
- Le harness H23 dispose maintenant d'une frontière d'implémentation pure :
  le contrat canonique LF est lié à son SHA-256, les `175` spécifications de
  fixtures et les `72` contrats de tests sont résolus, ordonnés et hachés de
  manière déterministe, et le manifeste obtenu déclare explicitement
  `waveforms_synthesized=false` / `tests_executed=false`. Le module n'importe
  ni NumPy, ni TensorFlow, ni loader de données et ne contient aucun chemin de
  synthèse DSP. Une garde distincte refuse inconditionnellement toute exécution
  synthétique dans ce commit, même si un appelant forge les deux booléens du
  plan à `true`. Les tests ajoutés sont uniquement contractuels et n'ouvrent
  aucun actif scientifique.
  Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h23-harness-implementation.md`.
- La revue finale du commit `1e5075f5d9eb23bdab077bed3faeb6c58c61942e`
  conclut `APPROUVÉ` et ne relève plus aucun fail-open structurel. Le gate
  machine-readable autorise uniquement l'implémentation du harness synthétique.
  `synthetic_execution_authorized=false`, `scientific_execution_authorized=false`
  et `training_authorized=false` restent inchangés. Aucun P0 ne peut être lancé
  avant un contrat d'exécution séparé et relu.
- La seconde revue externe a confirmé les huit corrections H23a mais identifié
  sept blocages mathématiques. H23b les ferme sans calcul : domaine latent
  `24..76` séparé des `37` candidats MIDI et des `89` observations; cas
  produit MIDI `40+64`; vrai masque spectral appliqué à `P[k]`; null
  support-aware; summaries non constantes; factorisation NNLS, résidu,
  `K/K+1` et tuple causal de source-birth entièrement définis; matrice live
  exactement `37×6`; chacune des `169` variantes possède une transformation
  waveform/target explicite. L'univers reste `6+169=175`, les `72` tests et
  leur ordre restent inchangés. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h23b-mathematical-closure.md`.
- La première revue externe de H23 a confirmé les `72` tests et la couverture
  scientifique, mais a refusé l'exécution pour huit degrés de liberté. H23a
  les ferme sans calcul : `I01/I02` ont une phase P1 unique; formules
  `S_raw/S_norm/S_null/S_residual`, cutoffs, filtres, grilles de variantes,
  tolérances et oracles sont exacts; l'univers est figé à `175` fixtures avec
  égalité exhaustive des IDs; la polarité inverse-check est non ambiguë; les
  masks de normalisation/observation/émission sont explicites; la borne
  analytique passe à 128 pour couvrir H20 de MIDI 76 tout en gardant le
  firewall MIDI 76; runtime, RNG et SHA de provenance sont scellés. Aucun P0
  n'est autorisé avant nouvelle revue. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-h23-review-corrections.md`.
- H23 préenregistre sans code scientifique ni calcul le plan complet de
  falsification du censoring harmonique multiscale. Il remplace l'idée de
  dizaines de pitch-shifts par une représentation spectrale causale partagée
  et une matrice `pitch × cutoff relatif`, séparée en `S_raw`, `S_norm`,
  `S_null` et `S_residual`. Le plan impose les fixtures S1–S5, dont
  `S5=AMBIGUOUS`, un analogue physiquement réalisable à partir de MIDI 40,
  l'anti-auto-confirmation, le partage des partiels, la comparaison
  `K_latent_pitch/K_emit_pitch/K_source` et `K/K+1`, le firewall analytique
  40–128 vers la sortie
  MIDI 40–76, les variantes guitare, l'OOD, le déterminisme et la viabilité
  live à lookahead nul. P0 doit d'abord démontrer une information non triviale
  au-delà du pitch et du gain; sinon l'idée est tuée avant tout modèle. Le
  seul statut positif futur est `AUTHORIZED_TO_PREPARE_TRAIN_PROTOCOL`, jamais
  `TRAIN_AUTHORIZED`. `real_data_used=false`, `H17_population_used=false`,
  `locked_test_used=false`, `fit_performed=false`. Contrat :
  `configs/harmonic_censoring_pretrain_h23_contract.json`. Rapport :
  `readme/results/2026-08-10_harmonic-censoring-pretrain-h23-contract.md`.
- L'état terminal H17 reste inchangé : résultat atomique complet, population
  H21 définitivement consommée et aucun retry autorisé.
- H17 réel a traité exactement `146/146` prises et `51/51` groupes au commit
  `2794ac91…`, sur CPU, sans erreur et sans test verrouillé. Sur `29 317`
  NoteOn éligibles, le taux faux est `0,3825822651` pour `frame_fallback`
  (`2 895/7 567`) contre `0,5325057471` pour le comparateur
  (`11 582/21 750`). `RD_false=-0,1499234820`; son IC95 bootstrap groupé
  `10 000/10 000` est `[-0,1929047490 ; -0,0817464765]`. Le verdict
  préenregistré est
  `frame_fallback_false_risk_enrichment_not_demonstrated`. Les quatre corpus
  ont un RD négatif. État final : `fresh_population_consumed=true`,
  `complete_atomic_result`, `locked_test_used=false`. Rapport :
  `readme/results/2026-08-10_provisional-resolution-frame-fallback-h17-real-execution.md`.
- H22 scelle le runner sans arguments de la mesure réelle H17. Il vérifie tous
  les blobs H17a/H20/H21, les `146` prises / `51` groupes et leurs octets, le
  checkpoint, les configurations et le runtime avant de réclamer un marqueur
  lié au contrat/commit exact. Il persiste ensuite atomiquement
  `fresh_population_consumed=true` juste avant le premier accès scientifique,
  sans retry. La taxonomie, le target causal `250 ms`, `RD_false`, les seuils
  et le bootstrap `10 000`/seed `721629268` sont réutilisés directement et ne
  sont pas modifiables par le caller. La publication des lignes, attritions,
  métrique/verdict et provenance est atomique. Contrat :
  `configs/provisional_resolution_frame_fallback_h22_execution_contract.json`.
  Runner : `src/polyphonic/run_provisional_resolution_frame_fallback_h17.py`.
  Rapport d’implémentation :
  `readme/results/2026-08-10_provisional-resolution-frame-fallback-h22-runner.md`.
  H22a ajoute le scellement non auto-référentiel du snapshot d’exécution :
  parent exact `5810061e…`, un seul commit descendant et ensemble exact de cinq
  fichiers modifiés, en plus du SHA du contrat et du HEAD liés par le marqueur.
- H21 a scellé sur le worker Mac prévu, sans science, le runtime, le checkpoint
  brut et les actifs exacts des `146` prises / `51` groupes H18a. Chaque entrée
  conserve chemins logiques/résolus, `audio_member`, tailles et SHA-256 bruts;
  `87` chemins audio et `146` chemins labels uniques ont été attestés. Le
  checkpoint brut `1ce8ac44…` fait `5 587 783` octets. TensorFlow/Keras n’ont pas
  été importés; aucun audio n’a été décodé et aucun label parsé. La destination
  future, le marqueur, son claim et l’état de consommation restent absents; le
  blob du futur runner reste `null`. L’artefact canonique H21 a pour SHA-256
  `acb8ced104ec99afd7f6f966be17b84ce4d436e5582137b6ec6048a90dfe3331`.
  Aucun runner, autorisation ou consommation n’a été créé. Artefact :
  `configs/provisional_resolution_frame_fallback_h21_zero_science_preflight.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-frame-fallback-h21-zero-science-preflight.md`.
- H20 lie sans exécuter la future expérience H17 : chaîne H17/H17a/H18a/H19a,
  décodeur, target causal, univers de groupes, grouping et checkpoint. La seule
  population prospective reste exactement H18a (`146` prises / `51` groupes),
  non ouverte et non consommée, sans resélection ni remplacement possible. La
  taxonomie amendée, `RD_false`, les seuils, le bootstrap et les dix compteurs
  d’attrition sont figés. Une future consommation devra être atomique juste
  avant le premier accès scientifique et toute publication devra être atomique.
  Runtime, chemins/hashes des actifs, destination, marqueur et blob du runner
  restent `null` pour un futur contrat zéro-science séparé. Aucun runner ou
  marqueur n’existe. Contrat :
  `configs/provisional_resolution_frame_fallback_h20_real_execution_contract.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-frame-fallback-h20-real-execution-contract.md`.
- H17a formalise avant toute donnée l’amendement découvert par revue statique :
  le décodeur gelé peut émettre `harmonic_strong_frame`. Le contrat H17
  historique reste immuable; sa question, `F`, son comparateur, son target, son
  seuil RD et son bootstrap restent inchangés. La taxonomie de population et
  l’attrition sont explicitement amendées : `harmonic_strong_frame` rejoint
  `legacy` et `retrigger` comme raison exclue mais comptée, sans reconstruction
  de sa raison antérieure; toute autre raison échoue fermée. Contrat :
  `configs/provisional_resolution_frame_fallback_h17a_reason_taxonomy_amendment.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-frame-fallback-h17a-taxonomy-amendment.md`.
- H19 démontre uniquement sur objets synthétiques que la raison immuable déjà
  portée par chaque `PolyphonicMidiEvent` peut être observée après émission sans
  modifier événements ni état du décodeur. `frame_fallback` définit `F=1`;
  `model_onset`, `frame_attack` et `chord_completion` définissent le comparateur;
  `harmonic_strong_frame`, `legacy` et `retrigger` sont comptés mais exclus;
  toute autre raison échoue fermée. H19a ne reconstruit jamais la raison
  antérieure d'un `harmonic_strong_frame`. Le target causal H17 existant est
  réutilisé directement. La fonction
  pure `RD_false` et le bootstrap de 10 000 groupes, PCG64 seed `721629268`,
  univers immuable avec groupes vides et minimum 9 500 réplications valides
  passent leurs tests synthétiques. Le décodeur reste au blob `27026d36…` et la
  population H18a de 146 prises / 51 groupes n’est pas consommée. Contrat :
  `configs/provisional_resolution_frame_fallback_h19_synthetic_conformance.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-frame-fallback-h19-synthetic-conformance.md`.
- H18/H18a a effectué uniquement l'audit de métadonnées autorisé après H17. Le
  checkpoint `1ce8ac44…` est identifié par son fichier historique brut comme
  `epoch-07.keras`. Sa transaction lie le commit train `33251d7…`, le manifeste
  `b28cb17c…` et le plan d'époques `d039ac2c…`. Les colonnes d'indices des plans
  1 à 7 couvrent chacune les `572` prises train sans manque; elles représentent
  exactement `219` groupes de fit avec le grouping gelé `e43187b4…`. Le candidat
  métadonné contient `754` prises / `285` groupes avec chemins audio/labels
  déclarés présents, sans ouverture de leur contenu. Après soustraction exacte
  de H8 consommé (`31` groupes), V2 indépendant consommé (`20`), test verrouillé
  (`40`) et groupes de fit (`219`), il reste toutes les `146` prises de `51`
  groupes validation. Le minimum de `20` groupes est donc établi, mais cette
  population est classée uniquement `fresh_discovery_only_not_independent_validation`.
  Aucun audio/label/checkpoint n'a été ouvert, aucun modèle, TensorFlow,
  inférence, décodeur, raison, cible ou métrique scientifique n'a été utilisé,
  et la population n'est pas consommée. Audit :
  `configs/provisional_resolution_frame_fallback_h18_metadata_audit.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-frame-fallback-h18-metadata-audit.md`.
- H17 préenregistre sans données ni calcul une question distincte de H7 : les
  NoteOn audio-aware émis sous `frame_fallback` sont-ils enrichis d'au moins
  `0,10` en faux NoteOn causaux par rapport à `model_onset`, `frame_attack` et
  `chord_completion` ? Le seul signal primaire futur est l'indicateur
  catégoriel figé à l'émission. Le target causal existant, la latence maximale
  `250 ms`, le bootstrap de `10 000` réplications par groupes et le minimum de
  `20` groupes futurs réellement neufs sont scellés. Contrat :
  `configs/provisional_resolution_frame_fallback_risk_h17_hypothesis_contract.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-frame-fallback-risk-h17-hypothesis.md`.
- Infrastructure suivante : H16 durcit uniquement la provenance des futurs
  runners. Avant `opening`, `inference`, `decoder`, `target`, `reconciliation`,
  `metrics` et `publication`, une phase non scientifique est remplacée
  atomiquement. Sur échec futur, phase, type, message borné/redacté, pile bornée
  sans source/locals et index/clé d'enregistrement sont conservés. Aucune valeur
  S0/S1/D1, target, classe, probabilité, AUC ou bootstrap n'est journalisée.
  H16 ne rouvre pas H14/H8 et n'autorise aucune exécution. Contrat :
  `configs/provisional_resolution_age1_h16_operational_provenance_contract.json`.
  Les scellements H12/H13 historiques restent inchangés : leur liaison à
  l'ancien blob H11 n'est pas mise à jour. Tout futur runner nécessitera donc
  un nouveau contrat de liaison revu séparément.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-age1-h16-operational-provenance.md`.
- H14 est définitivement clos après un `RuntimeError` post-consommation. Le
  marqueur a été réclamé, le state persistant prouve
  `h8_discovery_consumed=true`, aucun répertoire final n'existe et la provenance
  d'échec ne conserve que `error_type=RuntimeError`. Le résultat scientifique
  H7 est donc `indeterminate`, le verdict exact est
  `inconclusive_fail_closed`, et ni une AUC produite ni son absence ne peuvent
  être prouvées. Aucun retry ou réemploi de H8 pour H7 n'est autorisé. L'audit
  H15 purement statique classe les sites candidats par phase mais ne peut pas
  identifier une cause unique :
  `h14_runtime_failure_root_cause_not_identified`. Les fichiers `.claimed`,
  `.state.json` et `.failure.json` restent intacts sur le Mac. Rapport :
  `readme/results/2026-08-10_provisional-resolution-age1-h14-permanent-closure.md`.
- H13 corrige avant toute consommation le seul écart découvert pendant la revue
  H12 : le bootstrap reçoit désormais explicitement l'univers immuable des `31`
  groupes H8, même lorsqu'un groupe ne produit aucune ligne scientifique
  éligible. Chaque réplication tire toujours exactement `G=31` groupes avec
  remise; un groupe vide contribue zéro ligne mais son tirage compte. Les lignes
  hors univers, groupes dupliqués ou identifiants non canoniques échouent
  fermés. Le runner final sans argument dérive lui-même cet univers depuis les
  métadonnées H8 et un futur marqueur devra lier les octets du contrat H13. Les
  tests sont uniquement synthétiques et le preflight reste zéro-science.
  Le preflight Mac sur `bd1858ad…` a confirmé `101` prises, l'univers scellé
  exact de `31` groupes, le runtime arm64 CPU attendu, l'absence des quatre
  chemins one-shot et tous les drapeaux science/consommation à `false`.
  Contrat :
  `configs/provisional_resolution_age1_persistence_h13_execution_seal.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-age1-h13-fixed-group-universe.md`.
- H12 supprime l'injection scientifique restante : le vrai point d'entrée n'a
  aucun argument de cohorte, groupes interdits, manifeste/plan, checkpoint,
  config, métrique, seed ou bootstrap. Il lie le contrat H11 `ea6032e1…`, la
  cohorte H8 `4dd76bd1…`, le blob historique du décodeur `42331861…`, le blob
  instrumenté neutre H9 `27026d36…`, les APIs H9 au blob `22b93d2b…` et le
  moteur H10 au blob `a343c505…`. Le seul adapter de production utilise les
  loaders historiques, une inférence, le collecteur passif direct et le moteur
  H10 direct. Le mode preflight vérifie octets, métadonnées, runtime et absence
  de marqueur sans ouvrir ni décoder de contenu scientifique. Le preflight Mac
  sur `d9154895…` a atteint `h7_real_execution_preflight_ready` avec `101`
  prises, `31` groupes, runtime exact et les quatre chemins one-shot absents;
  H8 reste non consommée. Contrat :
  `configs/provisional_resolution_age1_persistence_h12_real_execution_binding.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-age1-h12-real-execution-binding.md`.
- H11 scelle uniquement le futur runner one-shot H7. La provenance fixe le
  checkpoint `1ce8ac44…`, le YAML `24528578…`, le décodeur `c16be482…`, la
  politique audio LF `45edbb71…`, Python `3.11.9`, NumPy `1.26.4`, TensorFlow
  `2.15.1` et le Mac arm64 CPU. L'orchestrateur pur exige exactement `101`
  prises/`31` groupes H8, marque la cohorte consommée avant la première
  ouverture scientifique, n'appelle l'inférence qu'une fois par prise, refuse
  tout résultat partiel et ne publie atomiquement qu'après réconciliation
  complète. Le marqueur d'autorisation réel n'existe pas et le runner n'a pas
  été invoqué. Contrat :
  `configs/provisional_resolution_age1_persistence_h11_execution_contract.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-age1-h11-execution-contract.md`.
- H10 positif sur objets synthétiques uniquement : une fin d'enregistrement avec
  NoteOn encore pending échoue sous `age1_signal_execution_invalid` /
  `unresolved_age1_pending_at_end_of_recording`, sans synthèse de frame,
  suppression ou reclassification clock-skip. Le wrapper groupé garde
  `recording_key`, `corpus_category` et `leakage_group_key` hors du payload
  scientifique. L'AUC binaire average-rank attribue un demi-crédit exact aux
  égalités. Le bootstrap utilise exclusivement `10000` tirages de `G` groupes
  avec remise via `numpy.random.Generator(numpy.random.PCG64(721629268))`, toutes
  leurs lignes avec multiplicité, minimum `9500` réplications valides et
  percentiles linéaires `[2,5;97,5]`. La décision positive exige simultanément
  AUC S1 `>=0,60` et borne basse `>0,50`; S0/D1 et corpus restent descriptifs.
  Aucun actif H8, signal/target réel, modèle ou métrique réelle n'a été utilisé.
  Contrat :
  `configs/provisional_resolution_age1_persistence_h10_synthetic_metric_conformance.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-age1-h10-synthetic-metric-conformance.md`.
- H9 positif sur données synthétiques uniquement : un collecteur passif observe
  chaque vrai NoteOn du décodeur historique, retriggers compris, gèle
  `S0=frame_probability_at_noteon`, puis capture `S1` au même pitch exactement
  à `age_frames=1` avant les décisions de la frame suivante. Un saut d'horloge
  produit `age1_observation_unavailable`, sans interpolation ni substitution.
  Le collecteur est incompatible fail-closed avec le resolver H4/H6, la porte
  causale V1/V2 et le seuil independent-note. Une cible offline pure réutilise
  le matcher causal gelé : same-pitch, aucune référence future, one-to-one,
  dernière référence en attente, maximum `250 ms`. La jointure exige l'identité
  exacte `(frame_index,pitch)`. La parité MIDI et état interne du décodeur nu et
  instrumenté est démontrée sur les chemins legacy/audio-aware, harmoniques,
  polyphonie, release, retrigger, silence et sauts de hop. Aucun actif H8,
  modèle, target/signal réel, métrique, AUC ou bootstrap n'a été utilisé.
  Contrat :
  `configs/provisional_resolution_age1_persistence_h9_synthetic_conformance.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-age1-h9-synthetic-conformance.md`.
- Préparation H8 scellée sans modèle ni métrique : le SHA brut du contrat H7 a
  été vérifié, puis toutes les prises `dev` Policy A ont été considérées sans
  plafond, équilibrage ou sélection manuelle. Après exclusion entière des
  groupes de la cohorte V2 consommée et du test verrouillé, la cohorte contient
  `101` prises et `31` groupes; une seule prise `dev`, du groupe verrouillé
  `gaps:player:sanja_plohl`, est exclue. Les intersections finales V2/test
  valent zéro. Les 101 audio et 101 labels ont uniquement été hachés comme
  octets bruts et concordent avec le registre Policy A historique. L'artefact
  canonique de `112013` octets a le SHA-256
  `4dd76bd13c33ccb3946bfdbcf6f575d4550fb0c5588095e23da3b6e3f84bce1f`.
  H8 fige `10000` réplicats bootstrap group-safe, le seed `721629268`, au moins
  `9500` réplicats valides et au moins `200` observations age-1, sans exécuter
  bootstrap, AUC, cibles ou signaux. Contrats :
  `configs/provisional_resolution_age1_persistence_h8_preparation.json` et
  `configs/provisional_resolution_age1_persistence_h8_selected_cohort.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-age1-persistence-h8-preparation.md`.
- Hypothèse H7 préenregistrée sans données ni calcul : le seul signal primaire
  futur est `S1=current_frame_probability` du même pitch à `age_frames=1`;
  `S0=frame_probability_at_noteon` reste descriptif et `D1=S1-S0` uniquement
  mécanistique. Aucun autre champ H5, audio, onset, harmonique, polyphonie,
  score, raison, interaction ou modèle ne peut filtrer ou sauver H7. Le target
  réutilise le matcher causal one-to-one existant, same-pitch, sans référence
  future et à latence maximale `250 ms`, avec ses blobs Git figés. La future
  décision exige `ROC-AUC >= 0,60` et borne basse de l'IC 95 % bootstrap par
  groupes `> 0,50`. Le grouping doit provenir de `leakage_group_key`; bootstrap
  ligne/frame/NoteOn/recording interdit. Cohorte, actifs, nombre de réplicats,
  seed et minimums valides restent non résolus. La cohorte V2 consommée et le
  test verrouillé restent interdits. Contrat :
  `configs/provisional_resolution_age1_persistence_h7_hypothesis_contract.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-age1-persistence-h7-hypothesis-contract.md`.
- Conformance synthétique H6 positive : `ProvisionalObservation` est désormais
  une dataclass immuable contenant exactement les 15 champs H5. Les preuves
  `*_at_noteon` sont gelées à l'émission et toutes les observations d'une frame
  partagent les mêmes snapshots pré-résolution de contexte harmonique et de
  polyphonie. Le décodeur valide toutes les observations, calcule toutes les
  décisions, puis les valide toutes avant la première mutation. Un résultat
  invalide tardif, une exception tardive ou une valeur numérique non finie ne
  produit donc ni confirmation/rejet partiel ni événement MIDI de résolution.
  `audio_onset_available` décrit explicitement le hop courant, pas le latch
  historique. Les compositions avec la porte causale V1/V2 ou
  `independent_note_threshold` échouent au constructeur avec
  `unsupported_pending_separate_contract`. Les scénarios H3/H4 et le chemin
  désactivé restent conformes. Les 98 tests ciblés passent en `0,297 s`.
  Aucun resolver réel, seuil, durée, population, donnée, modèle, inférence ou
  validation n'a été utilisé. Rapport :
  `readme/results/2026-08-10_provisional-resolution-h5-h6-synthetic-conformance.md`.
- Contrat causal H5 défini sans calcul : le futur resolver ne pourra recevoir
  qu'une `ProvisionalObservation` immuable et construite par le décodeur au
  point causal courant. Quinze champs sont classés par provenance, disponibilité
  et temporalité; labels, vérité MIDI, futur, métriques, cohorte V2, accès au
  décodeur, fichiers, réseau, modèle externe et état caché sont interdits.
  `HOLD/CONFIRM/REJECT/PREEMPT`, les erreurs atomiques et l'ordre intra-frame
  sont formalisés. Les seuils, la durée maximale, la population éligible et la
  stratégie runtime d'erreur restent non résolus. H4 + causal gate V1/V2 et H4
  + `independent_note_threshold` sont explicitement
  `unsupported_pending_separate_contract`. Aucun code fonctionnel du décodeur,
  donnée, modèle ou calcul scientifique n'est inclus. Contrat :
  `configs/provisional_resolution_evidence_contract_h5.json`. Rapport :
  `readme/results/2026-08-10_provisional-resolution-evidence-h5-contract.md`.
- Prototype synthétique H4 positif et strictement opt-in : chaque nouveau
  `NoteOn` peut être conservé comme état émis provisoire, tandis que le contexte
  harmonique et le budget de sélection n'utilisent que les notes confirmées.
  Une résolution injectée `HOLD/CONFIRM/REJECT` permet de tester l'architecture
  sans modèle ni données. Dans le scénario de polyphonie H3, le faux MIDI 60
  est préempté par un `NoteOff` avant que MIDI 61 soit émis dans la même frame,
  sans backfill ni dépassement du maximum. Dans le scénario harmonique H3, le
  faux MIDI 60 provisoire ne devient plus une base H2 : A et B gardent un
  support `0.0` et émettent toutes deux MIDI 72. `CONFIRM` contextualise la note
  sans second `NoteOn`; `REJECT` émet un `NoteOff` et nettoie l'état. Lorsque
  H4 est absent, les chemins legacy et audio-aware conservent leur comportement
  historique. Aucun resolver réel, politique de confirmation, donnée, audio,
  TensorFlow, modèle V1/V2, fit ou validation n'a été utilisé. Rapport :
  `readme/results/2026-08-10_decoder-provisional-state-isolation-h4-synthetic-intervention.md`.
- Le diagnostic H3 précédent reste la preuve causale motivant H4 : deux
  décodeurs identiques reçoivent une perturbation normale uniquement à `t0`,
  puis des entrées strictement identiques dès `t1`. Le faux MIDI 60 persistant
  dans B consomme l'unique slot de polyphonie et devient une base harmonique H2.
  Verdict : `state_contamination_demonstrated`. Rapport :
  `readme/results/2026-08-10_decoder-state-contamination-h3-synthetic-diagnostic.md`.
- Clôture provenance-only Attempt4 : l'unique exécution autorisée au commit
  `df2a2a0641d7897195ee0712002bcc48e97858e6` a créé son marker persistant,
  acquis le lease et créé sa destination, puis a atteint le timeout externe
  exact de `900 s`. Le marker fait `628` octets, SHA-256
  `00c677be7d78771e1b8c82d6bdf394dc8c9af64441a7f12f99c02f832908f1b0`.
  La destination est vide, le lock vide reste présent, et aucun processus ne
  subsiste. Aucun rapport ni métrique A/B n'a été publié. Le point scientifique
  atteint reste indéterminable : une métrique a pu exister seulement en mémoire.
  Par conséquent, `ab_metrics_produced=unknown`, `ab_metrics_observed=false`,
  le verdict V2 indépendant est `inconclusive_fail_closed`, la cohorte n'est
  plus réutilisable comme validation indépendante et tout retry est interdit.
  Le marker, le lock et la destination ne doivent pas être supprimés. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-attempt4-post-claim-timeout.md`.
- Demande d'autorisation attempt3, sans exécution : attempt2 a consommé son
  approval et son marker, puis s'est arrêtée avant TensorFlow et avant tout
  actif scientifique parce que le registre d'evidence attendu était absent du
  checkout worker. Sa destination et le verrou sont restés absents; aucune
  métrique A/B n'a été produite ou observée et la cohorte scientifique reste
  non consommée. Le registre historique a ensuite été matérialisé au chemin
  exact du worker, avec SHA-256
  `10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee`.
  Une nouvelle demande canonique scelle le job
  `causal-candidate-v2-independent-cpu-20260810-attempt3`, sa destination, son
  futur approval et son marker, tous distincts des tentatives 1 et 2. Avant de
  créer le marker attempt3, le module TensorFlow-free exige désormais que ce
  registre existe au chemin exact et que ses octets correspondent au SHA
  scellé. Aucun approval, marker, worker ou calcul attempt3 n'existe encore.
  Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-attempt2-premetric-infrastructure-failure.md`.
- Incident pré-métrique du job indépendant V2 : l'unique autorisation du commit
  `78f46628f430b9cdbe0e2b9ea042f05d0b141762` a été revendiquée, puis le
  runner s'est arrêté avant TensorFlow et avant toute ouverture d'actif avec
  `Fail closed: independent validation asset-evidence read is not authorized`.
  Le marqueur persistant fait `370` octets, SHA-256
  `c0b544e2faed44df45985ccb9abfd13ed067966e907fe4f0f4c2bb83433225eb`;
  il ne sera jamais supprimé ni réutilisé. La destination et le verrou lourd
  sont absents, aucun rapport scientifique n'existe et la cohorte n'est pas
  consommée. L'autorisation, elle, est consommée. Le correctif en cours ajoute
  uniquement une capability d'évidence spécifique à l'exécution, tout en
  maintenant fermé le lecteur générique. Aucun retry, nouveau job, approval,
  marqueur, actif réel, TensorFlow, inférence ou métrique n'était autorisé par
  ce correctif. Le commit `c78b1e1c` est désormais approuvé; seule la demande
  distincte attempt2 ci-dessus est en revue, sans autoriser son exécution.
  Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-premetric-infrastructure-failure.md`.
- Jalon historique d'autorisation indépendante V2, désormais consommé : le runner gelé
  `6246ea18c49a6c3c3b8e2ce1303c9a6afffac6ee` est approuvé et reste
  byte-identique. Une demande canonique scelle CPU, `900 s`, job, destination,
  contrat et evidence; son module TensorFlow-free exige un futur fichier
  d'approbation externe lié au HEAD exact et un worktree propre. Ce fichier a
  ensuite été matérialisé et consommé par la tentative pré-métrique décrite
  ci-dessus. Le premier appel a créé avant attestation un marqueur persistant
  `O_EXCL`, jamais supprimé, empêchant tout retry cross-process. Aucun marqueur
  réel n'existait encore à ce jalon; il existe désormais et interdit toute
  réutilisation. Le test verrouillé reste fermé. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-one-job-authorization-request.md`.
- Jalon historique du correctif pre-science du runner indépendant : le manifeste attesté est
  désormais chargé directement par le lecteur sans TensorFlow; une primitive
  explicite prépare le runtime CPU seulement après contrat, Git, cohorte,
  preuve globale des 60 actifs, six SHA et lease atomique. La configuration
  CPU précède strictement les imports `data`/`evaluate_events`; chaque paire
  audio/labels est rehachée immédiatement avant l'ouverture du même objet et
  son corpus est fermé dans un `finally`. La capability one-job attestée sera
  revendiquée atomiquement dès la première invocation publique et ne pouvait
  jamais être réutilisée, même après un échec pre-lease. À ce jalon, aucune
  factory d'autorisation ni exécution réelle n'existait encore. `83` tests
  synthétiques passaient en `8,288 s`; la revue externe et l'autorisation ont
  ensuite mené à l'incident pré-métrique désormais en correction.
- Anomalie pré-métrique V2 vérifiée : le job unique
  `causal-candidate-v2-train-dev-cpu-20260809`, lancé au commit approuvé
  `ddd15be4fbf7e47205a0025f80821e2446ef9720` avec CPU et `900 s`, termine
  `exited_nonzero`/code `1` à l'horodatage brut worker
  `2026-08-10T01:02:26Z` (non réconcilié). L'accusé V2 et le
  préflight worker ont passé, mais le runner ne trouve pas
  `repository/tmp/local`, où il attend le plan Policy A et le registre
  d'actifs locaux scellés. Il échoue donc pendant `load_sealed_v2_diagnostic_contract`,
  avant TensorFlow, modèle, checkpoint, audio, labels, inférence ou métrique.
  La destination V2 et le verrou actif sont tous deux absents après l'arrêt;
  les 30 prises, les 12 validations historiques et le test verrouillé restent
  inutilisés. Aucune relance n'était alors autorisée : il fallait d'abord revoir
  la matérialisation contrôlée des artefacts locaux manquants. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-train-dev-preflight-missing-local-artifacts.md`.
- Suivi de matérialisation, sans écriture : les deux fichiers originaux requis
  (`decoder_candidate_partition_plan_v2.json` SHA
  `a8347e4e…3685f4` et `decoder_candidate_asset_evidence_v1.json` SHA
  `12dd74f2…e586507`) sont absents de tout `C:\Users\user\Desktop\midi` et
  de `/Users/amcarene/midi-worker`; ils ne sont pas versionnés et `tmp/` est
  ignoré par Git. Aucun SHA source n'est donc disponible à comparer ou copier.
  Aucun dossier Mac, transfert, Python ou relance n'a été effectué. Ils ne
  seront pas régénérés : fournir les deux originaux depuis une sauvegarde ou
  indiquer leur emplacement est nécessaire avant une nouvelle revue. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-artifact-materialization-blocked.md`.
- Récupération source, lecture seule : les deux originaux sont retrouvés dans
  l'ancien checkout Mac `/Users/amcarene/midi/tmp/local/decoder_candidate_policy_a_preregistration_20260809/`.
  Le plan fait `145 859` octets et son SHA-256 est exactement
  `a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4`; le
  registre fait `198 950` octets et son SHA-256 est exactement
  `12dd74f2c868d884f9189e1c8d07c1e7e1cec4e984fda5a68ce434c05e586507`.
  À ce jalon, aucun dossier destination, copie, reformatage ou lancement V2
  n'avait suivi. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-artifact-source-recovered.md`.
- Matérialisation binaire atomique V2 vérifiée : le worker Mac n'avait aucun
  job actif ni verrou, et le dossier destination était absent. Chaque original
  a été copié localement vers un fichier `.part` dans le dossier final
  `midi-worker/repository/tmp/local/decoder_candidate_policy_a_preregistration_20260809/`,
  contrôlé par taille et SHA-256, puis renommé atomiquement sur le même
  système de fichiers et recontrôlé. Le plan source/destination fait `145 859`
  octets, SHA-256
  `a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4`; le
  registre source/destination fait `198 950` octets, SHA-256
  `12dd74f2c868d884f9189e1c8d07c1e7e1cec4e984fda5a68ce434c05e586507`.
  Aucun `.part` résiduel ni verrou n'est présent après l'opération. Aucun JSON
  n'a été parsé ou réécrit; Python, TensorFlow, audio, labels, modèle,
  inférence et métrique restaient absents. La revue externe a ensuite autorisé
  l'unique passe décrite ci-dessous. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-artifact-materialization.md`.
- Résultat terminal de l'unique diagnostic V2 CPU train/dev : le nouveau job
  `causal-candidate-v2-train-dev-retry-cpu-20260810`, au commit exact
  `522acc1e71d8baeafcede67a3f14e71fece73f9b`, a terminé `exited_zero` à
  l'horodatage brut worker `2026-08-10T02:00:18Z`, après `720 s` et dans le
  timeout externe de `900 s`. Le rapport brut fait `793 812` octets, SHA-256
  `43e28b4ebfe33f5ad0f28be1c4b61704af8cebc08012458cbd645d3027b9acf9`;
  il confirme CPU, les 30 prises train/dev `6/6/6/12`, zéro validation
  historique et `locked_test_used=false`. La porte V2 gelée à `0,31`, placée
  `post_ranking_pre_noteon`, a traité `1 281` candidats et en a rejeté `61`
  (`4,76 %`). Elle retire `9` faux NoteOn standards (`14 031 → 14 022`),
  tandis que l'appariement onset baisse de `1` et que le rappel causal reste
  identique. Les faux NoteOn causaux passent de `13 285` à `13 275`, sans
  changement de retriggers, fragmentation ni MIDI `40–51`; p90 causal augmente
  de `0,265 ms`, bien sous un hop de `5,805 ms`. C'est une observation
  exploratoire train/dev non promotionnelle : ni fit, ni calibration, ni
  validation historique, ni export/live ni test verrouillé ne sont autorisés.
  Le verrou est libéré et le runner demande explicitement l'arrêt après son
  rapport. La seule prochaine action est la revue externe du résultat. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-train-dev-diagnostic-run.md`.
- Contrat et runner synthétique d'évaluation indépendante V2, sans calcul réel : le manifeste scellé et la
  sélection historique de 12 prises ont été audités par métadonnées uniquement.
  La prochaine cohorte est gelée à `30` prises validation inédites : `10` GAPS,
  `10` Guitar-TECHS direct input et `10` Guitar-TECHS mic/amp, avec exclusion
  stricte de toute clé et de tout groupe de fuite historique. GuitarSet est
  explicitement hors périmètre : ses `60` prises validation appartiennent toutes
  au joueur `04`, déjà exposé par la cohorte historique. Le modèle V1, le
  standardiseur, les 12 features, le seuil `0,31`, la politique audio et le
  placement `post_ranking_pre_noteon` restent gelés ; les seuils de faux NoteOn,
  rappel, F1, fragmentation et latence sont préenregistrés. Aucun audio, label,
  modèle, actif, inférence, fit, calibration, export, live ou test verrouillé
  n'a été ouvert. Le nouveau module pur recalcule ces 30 clés depuis le
  manifeste complet avant de comparer la liste gelée, vérifie l'exclusion des
  groupes historiques et Policy A, force le placement V2 et applique les règles
  de décision fail-closed sur un rapport synthétique. Il n'a ni CLI ni accès
  aux actifs : la construction/lecture d'asset evidence et toute passe CPU
  restent interdites. Rapports :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-contract.md`
  et
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-runner-implementation.md`.
- Preuve byte-level V2 indépendante, toujours synthétique : le nouveau
  registre canonique ne peut couvrir que les `30` clés validation et les `20`
  groupes de fuite dérivés, liés au SHA du protocole et du manifeste. Chaque
  entrée portable contient seulement l'identité, le membre audio, la taille
  et le SHA-256 des deux fichiers `audio`/`labels` ; elle ne contient aucun
  chemin. Sa création exige un snapshot exact du manifeste et ne peut lire que
  les octets des actifs sélectionnés. La lecture du JSON ne charge aucun actif
  et le futur runner devra rehacher chaque fichier juste avant son ouverture.
  Le registre est JSON canonique immuable, réouvert et attesté par identité ;
  une copie/altération ou un item clone échoue. `41` tests ciblés
  provenance/V2 passent sur fichiers factices uniquement. Aucun actif projet,
  modèle, inférence, job Mac, fit, calibration, export, live ou test verrouillé
  n'a été ouvert. La seule action suivante est la revue externe de cette
  implémentation ; toute construction de preuve réelle reste interdite.
  Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-asset-evidence-implementation.md`.
- Correctif de revue de cette preuve byte-level, toujours synthétique : la
  revue externe de `3d889f05` avait refusé l'ancienne API, car un cohort
  construit à la main et un registre JSON canonique aux digests inventés
  pouvaient encore franchir des étapes de provenance. La nouvelle API exige
  désormais un cohort et une demande d'évidence attestés par le chargeur
  scellé, bloque builder/reader tant que leurs flags versionnés sont `false`,
  rehache les 60 actifs entre build et publication, puis ne rend un registre
  utilisable qu'après rehash complet identité/métadonnées/octet. Une future
  étape de lecture devra aussi figer le SHA du registre et le SHA du protocole
  de construction; les deux autorisations sont mutuellement exclusives. Le
  lecteur de snapshot est maintenant sans TensorFlow. Les 14 tests nouveaux
  sans TensorFlow passent en `2,868 s`; la suite provenance élargie compte 44
  tests en `10,340 s`, sans actif projet, modèle, Mac, inférence ou calcul
  scientifique. Aucun registre réel n'est créé : la seule action suivante
  reste la revue externe de ce correctif. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-asset-evidence-review-fix.md`.
- Autorisation builder V2 indépendante, sans accès aux actifs : la seconde
  revue externe du correctif `5fd4fc8` est approuvée. Le nouveau protocole
  scellé (SHA-256 `d63655c3…9ba015`) autorise uniquement
  `independent_validation_asset_evidence_build` : le builder pourra, lors de
  l'étape distincte autorisée, hacher et publier atomiquement la preuve des
  `30` audio et `30` labels de la cohorte validation indépendante. Il garde
  `reader_authorized_now=false` et ne contient encore ni SHA source de preuve
  ni SHA attendu de registre. Le lecteur/validateur, tout chargement de modèle,
  décodage d'actif, évaluation, fit, calibration, export, live et test
  verrouillé restent interdits. Ce commit ne lance pas le builder et n'ouvre
  aucun actif projet. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-asset-evidence-builder-authorization.md`.
- Construction unique de la preuve d'actifs V2 indépendante : après préflight
  Mac propre au commit `e241bd8`, le builder byte-level autorisé a haché sans
  décodage les `30` audio et `30` labels de la cohorte scellée, puis publié le
  JSON canonique immuable à
  `/Users/amcarene/midi/tmp/local/causal_candidate_v2_independent_validation_asset_evidence_20260810.json`.
  Le registre fait `17 873` octets, SHA-256
  `10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee`,
  est lié au manifeste `b28cb17c…f1b8ed7` et au protocole builder
  `d63655c3…9ba015`; aucun fichier `.part` ne subsiste et le worktree Mac est
  propre. Le protocole courant est aussitôt refermé (SHA-256
  `79c11de0…5cd0e7`, builder/reader `false/false`) afin d'interdire toute
  seconde construction avant revue. Aucun JSON n'est lu/validé, aucun modèle,
  checkpoint, TensorFlow, inférence, évaluation, fit, calibration, export,
  live ou test verrouillé n'est utilisé. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-asset-evidence-build.md`.
- Contrat lecteur V2 indépendant, sans lecture : après la revue post-build, le
  protocole scellé (SHA-256 `6bf7619a…c8ab3e`) fixe enfin les deux valeurs que
  devra vérifier un lecteur futur : registre `10307a64…22aee` et protocole
  builder source `d63655c3…9ba015`. Il laisse le builder fermé, autorise
  uniquement l'opération lecteur/revalidateur future et interdit toujours
  décodage, modèle, évaluation, fit, calibration, export, live et test
  verrouillé. Cette étape ne relit pas le JSON et ne rehache aucun actif ; sa
  seule suite est une revue externe du contrat lecteur. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-asset-evidence-reader-authorization.md`.
- Revalidation unique de la preuve d'actifs V2 indépendante : après préflight
  Mac propre au commit `e667a5c`, le lecteur a vérifié le JSON canonique et son
  SHA `10307a64…22aee`, sa liaison au protocole builder `d63655c3…9ba015`, puis
  a rehaché avec succès les `30` audio et `30` labels de la cohorte scellée.
  Il retourne uniquement la capacité de preuve validée et s'arrête : aucun
  décodage, TensorFlow, modèle, checkpoint, inférence, métrique, évaluation,
  fit, calibration, export, live ou test verrouillé. Le protocole courant est
  aussitôt refermé (SHA-256 `def274de…a34119`, builder/reader `false/false`),
  donc aucune seconde revalidation ne peut démarrer avant revue. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-asset-evidence-revalidation.md`.
- Contrat d'exécution V2 indépendant, déclaratif uniquement : le nouveau
  protocole versionné SHA-256 `269efb65…ae63ed` lie le protocole indépendant
  fermé `def274de…a34119`, le registre revalidé `10307a64…22aee`, son
  protocole builder source `d63655c3…9ba015`, le manifeste, la sélection
  historique et le plan Policy A. Il gèle la cohorte validation indépendante
  `10/10/10/0` (`30` prises, `20` groupes), tous les artefacts V1/V2, le seuil
  `0,31`, les 12 features et le placement `post_ranking_pre_noteon`. Son seul
  état est `external_review` : builder, lecteur, runner, accès aux actifs,
  modèle, TensorFlow et tout calcul réel restent interdits. Il exige d'un futur
  runner revu qu'il rehache le registre et les `30` audio + `30` labels avant
  toute ouverture, exécute une seule passe CPU A/B puis s'arrête sans promotion
  ni retry. Compilation et `19` tests synthétiques/provenance passent en
  `1,650 s`, sans actif projet ni TensorFlow. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-execution-contract.md`.
- Correctif d'intégration V2 sans calcul : le worker Windows n'autorise
  désormais l'accusé dédié qu'au module exact
  `src.polyphonic.run_causal_candidate_v2_train_dev_diagnostic`, avec CPU,
  timeout externe exactement `900 s`, zéro argument et `ExpectedCommit` complet
  égal au HEAD local; le worker Mac revalide le même commit puis exige le
  littéral `DECODER_CANDIDATE_V2_DIAGNOSTIC_EXECUTE=1` avant TensorFlow. Le
  runner lit, hache et parse maintenant les mêmes octets de la politique audio
  scellée, exige `onset_adapt_temporal_background=true`, puis transmet cette
  unique métadonnée interne à l'évaluateur. Les masques sont donc calculés une
  fois et partagés par les deux décodeurs A/B ; toute surcharge audio appelant
  reste refusée. `py_compile`, `bash -n`, `git diff --check` et `46` tests
  ciblés (PowerShell/Bash, runner V2, A/B et décodeur) passent en `9,044 s`, sans
  synchronisation Mac, actif projet, inférence, fit, calibration, validation,
  export, live ni test verrouillé. Rapport :
  `readme/results/2026-08-09_causal-candidate-v2-runner-integration-fix.md`.
- Runner d'exécution réelle V2, sans exécution : la première mesure proposée
  est limitée aux `30` prises canoniques V3 dont la partition préassignée est
  `dev` (`6` GAPS, `6` Guitar-TECHS DI, `6` Guitar-TECHS mic/amp, `12`
  GuitarSet). Le plan Policy A, le registre d'actifs, les artefacts V1, le
  seuil `0,31`, les masques audio et le placement
  `post_ranking_pre_noteon` y sont gelés. Cette cohorte n'est pas indépendante,
  car elle a servi au choix de l'époque V1 : elle est explicitement
  **train-only exploratoire et non promotionnelle**, sans sélection de seuil ou
  de modèle. Les 12 prises validation restent exclues. Le nouveau module sans
  CLI fixe les chemins, l'accusé worker, CPU, la tête/standardiseur V1, le
  seuil `0,31` et le placement `post_ranking_pre_noteon`. Avant TensorFlow ou
  un actif, il rehash le protocole LF, les artefacts V1, la politique V3, le
  plan et le registre ; il dérive ensuite les 30 identités depuis le manifeste
  pur, puis exige que le contexte attesté reproduise exactement cette sélection
  avant tout chargement de modèle. Aucune exécution n'est autorisée avant revue
  externe du runner. Compilation, `git diff --check`, `52` tests
  A/B/V2/événements en `0,551 s` et `54` tests provenance/minage en `1,848 s`
  passent sans ouvrir les chemins Mac scellés. Rapport :
  `readme/results/2026-08-09_causal-candidate-v2-train-dev-diagnostic-runner-implementation.md`.
- Intégration A/B V2 sans actif réel : chaque chemin avec une porte causale doit
  désormais déclarer explicitement son placement avant toute inférence. Le
  runner scellé V1 passe explicitement `pre_ranking`, conservant son expérience
  historique. Le chemin candidat V2 transmet explicitement
  `post_ranking_pre_noteon` jusqu'à `PolyphonicDecoder`; une omission ou un
  placement inconnu échoue. Les preuves synthétiques vérifient une seule
  inférence, l'appel de la porte uniquement sur les deux candidats sélectionnés
  parmi trois, le rejet du premier et l'absence de backfill. `51` tests ciblés
  A/B/décodeur en `1,029 s` et `30` tests de provenance/minage en `0,846 s`
  passent. Rapport :
  `readme/results/2026-08-09_causal-candidate-v2-synthetic-integration.md`.
- Implémentation V2 sans actif réel : `PolyphonicDecoder` conserve le placement
  V1 `pre_ranking` par défaut et ajoute uniquement
  `post_ranking_pre_noteon`. Dans les chemins audio-aware et legacy, V2
  conserve un snapshot V1 figé après pré-ranking, classe puis sélectionne les
  candidats, applique la porte seulement aux sélectionnés, puis ne mute/émet
  que les acceptés. Un rejet conserve `activation_count` et
  `attack_activation_pending`, n'a aucune place active persistante, garde sa
  position de sélection sans backfill et n'entre pas dans `protected_chord`.
  Les tests synthétiques ciblés passent : `46` en `0,422 s` puis `30` en
  `0,769 s` (76 au total), sans
  modèle V1, standardiseur, actif projet, fit, calibration, validation,
  export, live ni test verrouillé. Aucune mesure de latence réelle n'est faite;
  V2 n'ajoute toutefois ni lookahead, buffer ni hop par construction. Rapport :
  `readme/results/2026-08-09_causal-candidate-v2-synthetic-implementation.md`.
- Contrat V2 préenregistré et désormais implémenté synthétiquement : la tête
  causale V1, son standardiseur, ses 12 features et le
  seuil gelé `0,31` restent inchangés. Seul le placement futur est défini :
  après ranking et sélection `maximum_polyphony`, juste avant les seules
  mutations liées à l'acceptation/émission d'un nouveau `NoteOn`. Les mises à
  jour causales pré-ranking déjà présentes (evidence d'activation, releases,
  retriggers et graces) restent identiques à la référence. Un candidat
  sélectionné puis rejeté ne devient pas actif; `activation_count` et
  `attack_activation_pending` restent exactement dans leur état post-pré-ranking
  sans reset V2. Il ne crée aucune place active persistante, mais sa position
  dans la sélection du hop reste consommée et n'est ni rouverte ni backfillée.
  Toutes les décisions de porte précèdent la protection d'accord, qui ne voit
  que les candidats acceptés. Les features restent celles de V1, figées après
  les mises à jour pré-ranking et avant ranking/sélection, sans information
  post-porte ni future. Les retriggers restent inchangés. Les 12 prises validation ayant
  déjà révélé le défaut V1, elles sont explicitement interdites dans ce contrat
  V2 et ne pourront être employées plus tard qu'avec une autorisation distincte
  et une interprétation exploratoire. Aucun modèle, actif, inférence, fit,
  recalibration, recherche de seuil, validation, export, live ou test verrouillé
  n'a été ouvert ou exécuté. Rapport :
  `readme/results/2026-08-09_causal-candidate-v2-post-ranking-hypothesis.md`.
- Résultat terminal vérifié : l'unique job CPU
  `causal-candidate-fit-v1-cpu-20260809` termine avec `exit_code=0`,
  `complete_non_authorizing`, 14 époques enregistrées et meilleure époque 9,
  au commit exact `578a9d6583b2e5a68a312bd8dccf8e19a77b58b7`. Le préflight
  scellé V3, les comptes `694/244`, `968/250`, `793/190`, la parité Keras
  `0,0`, les trois SHA d'artefacts et `locked_test_used=false` sont vérifiés.
  La calibration train-only retourne `0,31`, sans promouvoir ce seuil. Une
  anomalie non corrigée est archivée : le dossier de sortie porte un caractère
  CR final transmis par le transport SSH direct; les octets restent intègres,
  aucune copie, renommage ou reprise n'est faite. Seule la revue du rapport
  a approuvé le résultat interne sans promouvoir le seuil. Rapport :
  `readme/results/2026-08-09_decoder-candidate-fit-v1-run.md`.
- Correctif sans calcul : `MAC_WORKER.ps1` ne permet l'accusé
  `DECODER_CANDIDATE_FIT_EXECUTE=1` que pour le runner causal approuvé et le
  transporte par stdin via `Invoke-Ssh`; `mac_worker.sh` refuse tout argument
  contenant CR avant Git, TensorFlow ou écriture. Les artefacts V1 existants,
  y compris leur dossier anormal, restent inchangés. Une préinscription A/B
  versionnée fixe les 12 prises validation, la référence sans porte, le modèle
  `b9320cd0…`, le standardiseur `0600aa1a…`, le seuil non promu `0,31`, une
  seule inférence de transcription par prise et les critères de décision. Elle
  interdit encore fit, recalibration, recherche de seuil, export, live et test
  verrouillé. Aucun Mac job ni calcul validation n'a été lancé. Rapport :
  `readme/results/2026-08-09_causal-candidate-fit-v1-transport-and-validation-preregistration.md`.
- Révision de contrat sans calcul après revue externe de `64ccc768` : l'A/B ne
  prétend plus conserver les mêmes candidats après la première divergence. Il
  impose une seule inférence et les mêmes masques audio, puis deux états de
  décodeur causaux indépendants; les features de la branche candidate sont
  calculées juste avant sa porte depuis son état propre. Toute surcharge audio
  est interdite. Les deltas de latence causale `p50` et `p90` sont maintenant
  chacun limités à `+1` hop (`5,804988662 ms`). L'implémentation et l'exécution
  restent interdites jusqu'à la revue de cette révision.
- Implémentation A/B sans calcul : `causal_candidate_validation.py` vérifie les
  SHA de la policy, sélection, modèle, standardiseur, manifeste, checkpoint,
  YAML et décodeur avant chargement. Elle partage l'inférence et les masques
  audio, puis fourche uniquement deux états de décodeur; la tête candidate voit
  les features pré-porte, jamais la référence. 66 tests ciblés passent en
  `7,859 s`; aucun modèle ou actif réel, aucune validation, export, live ou
  test verrouillé n'a été exécuté. Rapport :
  `readme/results/2026-08-09_causal-candidate-validation-ab-implementation.md`.
- Correctif de revue A/B sans calcul : le verdict emploie désormais la métrique
  réellement émise `recall_within_max_latency`; le SHA-256 du `fit_report` est
  vérifié avant le modèle et les huit empreintes exigées sont archivées dans le
  résultat. Les agrégats `onset_offset` sont présents pour A et B. Le rejeu
  synthétique ciblé passe `66` tests en `8,147 s`; aucune prise validation ni
  actif réel n'a été ouvert. Une nouvelle revue externe reste obligatoire avant
  toute exécution Mac.
- Invocation Mac sans calcul : le module
  `src.polyphonic.run_causal_candidate_validation` ne possède aucun CLI et
  construit exclusivement en interne les huit chemins scellés, y compris le
  dossier historique à suffixe CR sans jamais le transmettre au shell. Le worker
  n'accepte cette seule exécution que via l'accusé dédié, sans argument de
  module, avec CPU, exactement `900` s et un commit Git complet égal au HEAD
  local. Son préflight spécifique ne charge pas TensorFlow : le runner vérifie
  d'abord les huit SHA puis impose CPU avant l'import. La destination est neuve
  par construction. `py_compile`, les parseurs PowerShell/Bash et 26 tests
  ciblés passent; aucun actif, checkpoint, prise validation, inférence,
  validation, export, live ou test verrouillé n'a été ouvert ou exécuté.
  La revue externe finale de cette invocation est la seule action préalable à
  une commande Mac. Rapport :
  `readme/results/2026-08-09_causal-candidate-validation-ab-invocation-contract.md`.
- Anomalie pré-métrique close de la première invocation A/B : le job CPU
  `causal-candidate-validation-ab-cpu-20260809`, au commit
  `4ab4f1ecâ€¦`, a terminé `exited_nonzero` à `2026-08-09T22:34:34Z` après le
  préflight worker, les huit SHA et le chargement du checkpoint, mais avant
  toute boucle/inférence sur les 12 prises. Cause : `evaluate_events` lisait
  inconditionnellement `thresholds["frame"]` alors que le décodeur scellé
  contient déjà les seuils et qu'aucun `thresholds.json` n'est autorisé dans la
  destination fraîche. Aucun rapport, audio/label, métrique, export, live ou
  test verrouillé n'a été produit; la destination A/B reste absente et le
  verrou est libéré. Correctif sans calcul : la configuration décodeur est
  maintenant résolue avant manifeste/checkpoint et ne lit les thresholds que
  si aucun décodeur explicite n'existe. `py_compile` et 54 tests ciblés passent
  en `8,912 s`. La revue externe a autorisé une seule relance. Rapport :
  `readme/results/2026-08-09_causal-candidate-validation-ab-threshold-contract-fix.md`.
- Résultat vérifié de cette unique relance CPU : le job Mac
  `causal-candidate-validation-ab-retry-cpu-20260809`, au commit exact
  `17d94580af0f293f66a05072388fa1df62f27a89`, termine `exited_zero` à
  `2026-08-09T22:53:39Z` en `complete_non_authorizing`. Le rapport brut
  (372 794 octets, SHA-256 `8f048ad173015c2a89d3cde5ca106cc45c6bad05f6023f36c92ba4e12c28d1c3`)
  confirme `split=validation`, 12 prises équilibrées, les huit SHA scellés,
  une inférence commune par prise, deux états de décodeur indépendants et
  `locked_test_used=false`. La porte causale V1 à `0,31` a rejeté 9 des 711
  candidats internes observés, mais n'a modifié aucun NoteOn final : faux
  positifs `3389 → 3389`, F1 onset `0,21760081 → 0,21760081`, rappel causal
  `0,59741687 → 0,59741687`, latences p50/p90 inchangées à `68,131/162,388 ms`.
  La règle préenregistrée exigeait au moins un faux positif en moins ; elle est
  seule en échec, donc `all_rules_passed=false`. Aucune promotion, nouveau fit,
  recalibration, recherche de seuil, export, live ou test verrouillé n'est
  autorisé. Rapport :
  `readme/results/2026-08-09_causal-candidate-validation-ab-v1-run.md`.
- Revue externe de `f893aa55…` : résultat approuvé et V1 formellement clôturée.
  Les 9 rejets internes sont réels, mais `0/4247` événement MIDI final a changé.
  Cette absence de transfert entre la population entraînée (NoteOn émis) et la
  population vue avant ranking est désormais une limite observée, non une raison
  de régler à nouveau le seuil. Une porte éventuelle après ranking/sélection,
  juste avant NoteOn, serait une nouvelle hypothèse architecturale à
  préenregistrer séparément ; aucune implémentation ni calcul ne suit cette
  revue.
- Résultat vérifié : le job Mac
  `decoder-candidate-guitarset-v3-cpu-20260809` a terminé avec `exit_code=0`
  et l'état `complete_non_authorizing` au commit
  `4ddc88666a1c55725c18a813c63ecd25a03bf298`. Les 90 prises train-only ont
  produit 3 139 candidats supervisés (684 positifs causaux, 2 455 faux NoteOn),
  0 perte et 3 139 `event_id` uniques. La porte de représentation passe, y
  compris GuitarSet positif `31/28/14` pour fit/dev/calibration, mais
  `fit_authorized=false` reste obligatoire. `locked_test_used=false`; aucun
  fit, calibration, validation, export, live, choix de seuil ou test verrouillé
  n'est autorisé. Les horodatages du worker Mac sont conservés dans le rapport
  sans réconciliation : début `2026-08-09T19:07:52Z`, fin
  `2026-08-09T19:41:24Z`. Rapport :
  `readme/results/2026-08-09_decoder-candidate-guitarset-v3-mining-run.md`.
- Revue externe : V3 est approuvé comme corpus train-only suffisamment
  représenté. Il n'autorise ni un quatrième minage, ni un fit automatique. La
  prochaine hypothèse, sans calcul, préenregistre une tête logistique causale,
  ses 12 entrées pré-porte, sa pondération group-safe, le choix dev et la
  calibration interne au train. Rapport :
  `readme/results/2026-08-09_decoder-candidate-fit-hypothesis-v1.md`.
- Implémentation vérifiée, sans exécution de fit :
  `src/polyphonic/causal_candidate_fit.py` scelle les deux artefacts V3 et le
  protocole V3 avant toute lecture de ligne, contrôle le statut non autorisant,
  les sept empreintes, le commit, le but et les comptes par partition. Il
  projette exclusivement les 12 features pré-porte, standardise sur `fit`,
  calcule les poids localement par partition et expose la BCE dev sans L2, la
  calibration déterministe et la parité sauvegarde/rechargement sans écrasement.
  Le budget figé utilise seed `47` et `shuffle=false`. Les 42 tests synthétiques
  ciblés passent en `2,015 s`; aucune ligne V3 réelle, aucun checkpoint réel,
  aucune gradient update, calibration, validation, export, live ni test
  verrouillé n'a été exécuté. La revue externe de cette implémentation est la
  seule action préalable à toute autorisation distincte de fit. Rapport :
  `readme/results/2026-08-09_decoder-candidate-fit-protocol-implementation.md`.
- Revue externe de `76ebf937` : l'implémentation V1 est approuvée, sans
  autoriser un job Mac. Le runner maintenant ajouté ne possède aucun réglage
  de spec ou de poids, exige un accusé d'exécution, CPU, Git exact et les
  artefacts V3 scellés. Il entraîne uniquement `fit`, observe `dev` hors
  gradients pour choisir l'époque par BCE hors L2, et n'ouvre calibration
  qu'après le verdict dev. Il persistera le standardiseur lié au modèle et
  appliquera un budget de 15 min ; les 47 tests synthétiques ciblés passent en
  `5,388 s`. Aucun fit, artefact V3 réel, calibration, validation, export,
  live ni test verrouillé n'a été exécuté. Une nouvelle revue externe du
  runner est obligatoire. Rapport :
  `readme/results/2026-08-09_decoder-candidate-fit-runner-implementation.md`.
- Résultat vérifié : le job Mac `decoder-candidate-extended-mining-cpu-20260809`
  a terminé sans erreur au commit `42a88b0d…`, avec `locked_test_used=false`,
  3 057 candidats supervisés (639 positifs, 2 418 négatifs), zéro perte et
  aucun `event_id` dupliqué. La porte échoue uniquement pour les positifs
  GuitarSet `dev=6` et `calibration=7`, sous le minimum préenregistré de 8.
  Aucun fit, calibration, validation, export, live, choix de seuil ou test
  verrouillé n'est donc autorisé. Rapport :
  `readme/results/2026-08-09_decoder-candidate-extended-mining-run.md`.
- Hypothèse suivante, sans calcul : le contrat v3 conserve les mêmes sept SHA,
  la porte à 8 et la Policy A, mais fixe une population unifiée de 90 prises
  (6 par cellule sauf GuitarSet à 12 par partition). Le correctif au blocage
  de revue lie de plus toute exécution du schéma 3 au seul fichier versionné
  `configs/decoder_candidate_guitarset_expansion_policy_a_v3.json` et à son
  SHA-256 LF `db55930a…5683`, avant Git, actifs ou TensorFlow. Les substitutions
  par chemin externe ou octets modifiés échouent fermées. Aucun calcul ne suit ;
  la revue externe du correctif est approuvée. L'unique replay CPU V3 est
  maintenant terminé ; aucun second lancement ni changement de contrat n'est
  autorisé avant la revue du rapport terminal. Rapports :
  `readme/results/2026-08-09_decoder-candidate-guitarset-expansion-hypothesis.md`
  et `readme/results/2026-08-09_decoder-candidate-guitarset-protocol-binding-fix.md`,
  puis `readme/results/2026-08-09_decoder-candidate-guitarset-v3-mining-run.md`.
- Résultat scientifique conservé : la tête `independent_note` précédente reste
  un résultat négatif, saturé près de 1, et ne doit promouvoir ni checkpoint ni
  seuil. Le test verrouillé reste fermé.
- Instrumentation candidat : `PolyphonicDecoder` accepte un collecteur optionnel
  `None` par défaut. Les features sont figées avant la porte; rang, sélection,
  émission et `event_id` ne sont ajoutés qu'après les décisions réelles. Le
  buffer est borné et drainable, tout débordement invalide le batch, et une
  erreur de collecte est mémorisée sans bloquer les événements MIDI. Une frame
  entière est remise en un seul batch après toutes ses décisions; une
  contention du collecteur échoue immédiatement sans attendre son verrou.
- Le snapshot manifeste lit et hache une fois les octets CSV puis construit les
  mêmes objets complets `ManifestItem` qui seront fournis à `PolyphonicCorpus`
  et au collecteur. Les chemins relatifs sont ancrés au manifeste. Les copies
  de snapshot/capacité validée, les chemins substitués et les wrappers de plan
  forgés échouent fermé avant toute collecte.
- Le plan canonique est persistant et immuable : écriture sans écrasement,
  relecture stricte, SHA du plan dans chaque batch, et re-vérification avant
  collecteur, ouverture ou agrégation. La politique A, désormais versionnée au
  schéma 2, conserve la validation historique et exclut automatiquement du
  futur minage toute capture train dont le groupe corpus-aware est déjà en
  validation. Les identités exclues sont elles-mêmes persistées et rematchées
  contre le manifeste complet; aucun sous-ensemble manuel ne peut passer.
- Preuve d'actifs : avant toute ouverture future, le contexte exigera un
  registre canonique, persistant et attesté des tailles/SHA-256 audio et labels
  de chaque capture train, lié au même manifeste, plan, `audio_member` et
  partition. Les labels sont rehachés juste avant leur lecture par le
  constructeur et l'audio juste avant son véritable chargement paresseux par
  `corpus.audio()`; le chemin `.npy` protégé ne conserve pas de `mmap` après
  cette vérification. Une couverture incomplète, un fichier modifié, un wrapper
  forgé ou des octets du registre modifiés échouent fermé. La preuve réelle
  Policy A de 541 actifs est enregistrée. Les trois replays train-only approuvés
  (12, 72 puis 90 prises) ont ouvert uniquement leurs actifs sélectionnés après
  revalidation du registre ; ce texte remplace l'ancienne assertion, devenue
  obsolète, qu'aucun actif n'avait encore été ouvert.
- Chaque ligne future porte la provenance immuable complète : `source_id`,
  `dataset_id`, `group_id`, `capture_id`, clé de fuite et partition. Les lots
  portant un autre manifeste/plan, une prise rejouée, un `event_id` dupliqué ou
  une couverture incomplète de partition seront refusés.
- Les codes de raisons existants du live sont centralisés sans changement. Les
  `event_id` v2 sont déterministes par identité physique/frame/pitch (la
  partition est volontairement exclue) et restent hors de
  `PolyphonicMidiEvent`.
- L'unité d'apprentissage est désormais définie : un vrai NoteOn
  `gate_eligible=True` et `emitted_noteon=True`. Le collapse temporel est
  supprimé; deux NoteOn réels restent distincts et un `event_id` dupliqué rend
  un futur artefact invalide.
- Infrastructure Ollama : le commit `af5437ee` conserve le verrou partagé
  jusqu'au déchargement vérifié, refuse les worktrees sales et les redirections,
  transporte le prompt par stdin, contrôle tous les composants des chemins et
  ne persiste plus le corps des réponses.
- Vérification instrumentation Windows : 86 tests ciblés réussis. Par rapport
  au décodeur approuvé `f9ed9d0`, 512 frames couvrant porte active/inactive et
  voie legacy/causale ont une parité exacte des événements et de tout l'état
  décisionnel, y compris reset et panic.
- Vérification Mac : checkout propre au commit
  `f7514228800d8ad15db7d047dcadfbf8640cf4ee`; les mêmes 86 tests réussissent
  en 0,604 s (`OK`, deux tests Windows-only ignorés) et la compilation des six
  fichiers Python touchés réussit.
- Microbenchmark borné dense : ancien décodeur 175,77 µs/frame, nouveau chemin
  désactivé 162,53 µs/frame (aucune régression mesurée), collecte activée
  260,64 µs/frame, soit +98,11 µs et 1,69 % du hop de 5,805 ms.
- Étiquettes futures : les seuls exemples de fit sont les NoteOn gate-éligibles
  et émis. Le matcher causal same-pitch une-à-une reçoit cependant tous les
  NoteOn valides du flux réel, retriggers inclus, à la fin du hop et à 250 ms
  inclusifs, avant projection vers le fit. Un retrigger same-pitch ne peut donc
  plus laisser une référence disponible pour rendre positif un candidat tardif.
  Les frames invalides ou hors audio ne consomment pas de référence; les
  retriggers restent comptés comme exclusion explicite; toute autre NoteOn sans
  trace ou erreur de collecteur invalide le lot. Les features de fit sont
  projetées strictement depuis `CAUSAL_FEATURES`.
- Vérification du protocole Windows : compilation Python, `git diff --check`
  et **128 tests ciblés réussis en 7,438 s** ont été archivés avant le commit
  précédent. Le détail et la commande exacte sont archivés dans le rapport.
- Vérification du correctif retrigger Windows : compilation Python,
  `git diff --check` et **131 tests ciblés réussis en 8,993 s**. Les deux
  ordres same-pitch retrigger/candidat, le retrigger invalide et l'intégrité du
  plan au `drain()` sont couverts dans le nouveau rapport.
- Revue externe du commit `9e666eb0f83d556a2b74809d0ffee47c51966fa1` :
  **approuvée**. Un rejeu Windows indépendant de la même suite ciblée obtient
  aussi **131 tests réussis en 9,336 s**. Cette seconde durée est une mesure
  d'exécution distincte; elle ne remplace pas l'évidence historique à 8,993 s.
- Vérification du correctif d'actifs Windows : compilation Python, `git diff
  --check` et **136 tests ciblés réussis en 9,718 s**, dont un parcours réel
  synthétique préinscription -> relecture -> ouverture, le rejet d'une mutation
  audio après construction mais avant `corpus.audio()`, et le cache de conteneur
  audio partagé. La vérification initiale du contrat à 134 tests en 9,429 s
  reste archivée dans son rapport propre.
- Vérification de la politique A Windows : compilation Python, `git diff
  --check` et **138 tests ciblés réussis en 8,696 s**. Les nouveaux fixtures
  GAPS synthétiques vérifient l'exclusion train déterministe, la persistance
  exacte des captures exclues, le refus d'un sous-ensemble manuel et
  l'impossibilité de construire leur collecteur.
- Vérification initiale du mineur borné Windows : les 39 tests ciblés passent en
  `1,044 s`; la suite générale passe ensuite à **458 tests en 38,309 s**
  (trois ignorés). Les éventuelles mini-époques visibles dans cette seconde
  suite sont uniquement des fixtures synthétiques historiques : aucun WAV,
  label, checkpoint ou artefact réel Policy A n'a été ouvert.
- Correctif de préflight du mineur borné Windows : la revue externe de
  `0e124352…` a relevé (a) la confusion entre SHA Git à 40 caractères et
  SHA-256, et (b) l'import de TensorFlow via `data.py` avant les empreintes.
  Le CLI charge désormais `data`/le contexte uniquement après les sept SHA,
  le lien YAML-manifeste et le préflight CPU; le SHA Git possède son validateur
  dédié. `py_compile`, `git diff --check` et **41 tests ciblés en 2,025 s**
  passent, dont un sous-processus vierge prouvant qu'un checkpoint substitué
  échoue avec `tensorflow` absent de `sys.modules`. Aucun actif Policy A,
  checkpoint réel, inférence, replay, collecteur ou artefact n'a été ouvert ou
  produit par ce correctif.
- Anomalie de préflight Mac après l'approbation de `9ed93e7` : six empreintes
  scellées concordent, mais la politique audio versionnée vaut `bf4c…` dans le
  checkout Windows CRLF et `45ed…` dans le blob Git / checkout macOS LF. Le
  job s'est arrêté avant TensorFlow, contexte, checkpoint, actif, replay ou
  écriture. Le correctif force LF pour les quatre configurations versionnées
  scellées et remplace l'empreinte audio par le SHA canonique Git `45ed…`.
  `py_compile`, `git diff --check` et **42 tests ciblés en 1,721 s** passent;
  une revue externe du correctif est obligatoire avant une nouvelle
  synchronisation et l'unique minage.
- Préinscription Policy A Mac terminée au commit `8190e3bf` : manifeste stable
  `b28cb17…` avant/après, validation historique inchangée (`182` lignes),
  `31` exclusions `gaps_poly_mix` couvrant les dix joueurs attendus, `541`
  prises planifiées et `541` entrées de registre. SHA plan v2
  `a8347e4e…` ; SHA registre `12dd74f2…`. Aucune exclusion n'est dans le
  registre, `locked_test_used=false`, et aucun replay/minage/entraînement ou
  autre calcul scientifique n'a démarré.
- Préinscription Mac de `d16b25f7` : le checkout est synchronisé et inactif,
  mais le garde group-safe a refusé le manifeste
  `b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7` avant
  toute écriture ou hachage. Dix joueurs `gaps_poly_mix` chevauchent train et
  validation (31 prises train, 11 validation au total). Le répertoire de sortie
  vide a été supprimé ; aucun plan, registre, actif ouvert, artefact candidat,
  minage ou test verrouillé n'existe. Le choix utilisateur A conserve cette
  validation; il ne modifie ni le manifeste ni les données et prépare seulement
  l'exclusion déterministe versionnée des prises train concernées.
- Autorisation externe de la préinscription Policy A (`8143f016…`) : le premier
  minage peut uniquement produire un corpus candidat et ses compteurs de
  provenance, sans fit ni validation. Le mineur versionné fige sept empreintes
  (manifeste, plan, registre, checkpoint de transcription, YAML, décodeur,
  politique audio), exige CPU et un commit Git propre exact, puis limite le
  rejeu à 12 prises canoniques train (`1 × corpus × fit/dev/calibration`). Il
  écrit atomiquement sous `data/processed`, refuse toute perte de collecte et
  marque `fit_authorized=false`. **Aucun minage réel n'a encore été lancé : la
  revue externe de cette implémentation est la porte suivante.**
- `locked_test_used=false`; aucun entraînement, minage, calcul validation,
  export ou live n'a été exécuté.
- Rapports :
  `readme/results/2026-08-05_decoder-candidate-mining-hypothesis.md`,
  `readme/results/2026-08-08_ollama-local-team.md` et
  `readme/results/2026-08-08_ollama-candidate-contract-hardening.md`, puis
  `readme/results/2026-08-08_decoder-candidate-instrumentation.md`,
  `readme/results/2026-08-08_decoder-candidate-instrumentation-review.md` et
  `readme/results/2026-08-08_decoder-candidate-provenance-contract.md`, puis
  `readme/results/2026-08-08_decoder-candidate-snapshot-label-protocol.md` et
  `readme/results/2026-08-08_decoder-candidate-retrigger-causal-matching-fix.md`,
  puis `readme/results/2026-08-08_decoder-candidate-retrigger-causal-matching-review.md`
  et `readme/results/2026-08-08_decoder-candidate-asset-evidence-contract.md`,
  puis `readme/results/2026-08-08_decoder-candidate-asset-evidence-lazy-audio-fix.md`
  et `readme/results/2026-08-08_decoder-candidate-preregistration-blocked-by-gaps-leakage.md`,
  puis `readme/results/2026-08-09_decoder-candidate-gaps-policy-a-contract.md`
  et `readme/results/2026-08-09_decoder-candidate-policy-a-preregistration.md`.

## Prochaine action réelle

1. Faire relire uniquement les trois nouveaux contrats H27 de fixtures, tests
   et population future, ce README et le rapport associé.
2. Ne pas implémenter de materializer, engine, recomputer ou test exécutable et
   ne matérialiser aucun record avant un nouveau verdict externe.
3. Ne créer aucune authority, claim ou capability et ne lancer aucun FFT,
   NNLS, P0/P1/P2, locked-test, entraînement ou calibration ; ne toucher à
   aucun artefact H26.

## État archivé — dual-stream du 30 juillet (remplacé)

- Mise à jour : `2026-07-30T08:13:17+04:00`
- Étape : `dual_stream_bass_local_train`
- Statut historique au 30 juillet : `en cours à cet instant`, désormais
  remplacé et non actif.
- Détail : décision permanente appliquée : aucun upload, appel API, kernel
  ou calcul Kaggle/Colab ne sera utilisé sans nouvelle autorisation explicite.
  Le desktop dispose d'un i7-1355U, de 15,64 Gio de RAM et de TensorFlow
  2.15.1 CPU sans GPU CUDA. Les 572 enregistrements train et 182 validation,
  soit 754 paires audio/labels, sont présents sous `data/processed`; les 114
  enregistrements test restent verrouillés. L'initialisation locale utilise
  `polyphonic_multisource_20260728_192326/epochs/epoch-08.keras`, 4 272 336
  octets, SHA-256
  `aaec718882bd1344461ecffa3475dceb10edcad5b2e265b1494977f6e1c9834c`.
  `model.summary()` est remplacé par `model_overview.json` et une seule ligne
  `MODEL_OVERVIEW` flushée. Les 308 tests de non-régression passent. Le smoke
  minimal 256/128 puis le smoke représentatif local 8 192/2 048 passent avec
  reprise A/B, `locked_test_used=false`, génération 6, 342 996 paramètres et transfert
  des 25 couches compatibles; les 7 nouvelles couches graves sont
  correctement initialisées. Le smoke représentatif entraîne à 169,89
  exemples/s sur 128 batches et valide en environ 4 s. La projection issue de
  ces mesures est d'environ 3 h 10 pour 8 époques, avec une marge pratique de
  4 à 6 h en cas de chauffe ou d'activité concurrente.
- Surveillance : train complet local démarré à `08:08:46+04:00`, run
  `polyphonic_dual_stream_bass_20260730_080855`, PID lanceur 11256 et PID
  TensorFlow 41032. Au batch 650/3 750 de l'époque 1/8, le débit réel est
  171,68 exemples/s et la projection restante est de 3 h 02. La génération
  recovery A est fraîche à `08:13:04+04:00`; aucune erreur n'est présente.
  L'automation `suivi-train-local-dual-stream` vérifie localement toutes les
  dix minutes et ne signale que les fins d'époque, pauses, anomalies ou la fin.
  Logs :
  `tmp/local/dual_stream_bass_train_20260730_080846.stdout.log` et
  `.stderr.log`. Le test verrouillé reste exclu.

## Étapes archivées — plan dual-stream du 30 juillet (non actif)

> Ces étapes appartiennent au plan dual-stream remplacé ci-dessus. Elles ne
> doivent ni être exécutées ni interprétées comme le plan actuel.

1. Capturer la même suite live sans puis avec capodastre, au même niveau et avec WAV/trace complète : cordes graves isolées, accords ouverts/barrés, strums lents/rapides, octaves et harmoniques. Comparer énergie fondamentale/partiels, probabilités par hauteur, erreurs d'octave et notes manquantes. Cette capture servira au diagnostic, pas au test verrouillé.
2. Conserver le remplacement par transposition +12/−12 uniquement comme diagnostic offline désactivé ; ne pas confondre ce test négatif avec la future architecture à deux flux.
3. Laisser achever l'unique train CPU local de 8 époques, avec un worker, logs
   flushés, reprise A/B toutes les 32 batches et arrêt récupérable à six heures.
4. Après achèvement seulement, classer et sélectionner sur validation, puis
   comparer les graves MIDI 40–51, les erreurs d'octave, les accords et chaque
   corpus.
5. Dans une expérience suivante seulement, corriger le contrat des masques harmoniques, sur-échantillonner les onsets/accords MIDI 40–51 sans réduire le reste et ajouter un objectif fondamentale/résonance fondé sur `note_id` et les colonnes harmoniques existantes.
6. Ouvrir le test verrouillé une seule fois après la sélection finale, puis produire le lanceur desktop stable et ses limites documentées.
<!-- CURRENT_STATUS_END -->

## État technique consolidé
### Produit monophonique

- Périmètre accepté : guitare propre monophonique, MIDI 40–76.
- Parité TFLite et ONNX validée.
- Inférence compatible avec le live.
- Limite : une sortie softmax unique ne transcrit pas les accords.
### Produit polyphonique V2.2
- Entrée causale : 4096 échantillons à 44,1 kHz, hop 256.
- Le V2.2 n'a pas trois branches de fenêtres explicites : contexte principal
  4096 et branche onset limitée aux 512 derniers échantillons seulement.
- Sorties : notes actives, onsets, amplitudes harmoniques et offsets en cents.
- Ancien train : 8 époques, 240 000 exemples par époque.
- Checkpoint sélectionné : époque 8.
- F1 frame validation : 0,5381.
- F1 onset événementiel pondéré : 0,2294.
- Limites : notes fantômes, fragmentation, offsets imprécis et domaine
  Guitar-TECHS plus faible.
- Le décodeur desktop a amélioré le F1 onset global de 0,1535 à 0,1751, au
  prix d’un rappel plus faible.
- TFLite float16 batch 1 : p95 de 2,17 ms, hors latence audio matérielle.
### Données reconstruites

- Toutes les données dérivées sont sous `data/processed`.
- 868 enregistrements : 572 train, 182 validation, 114 test verrouillé.
- Sources du manifest polyphonique : GuitarSet, GAPS et Guitar-TECHS
  direct/micro.
- IDMT-SMT-Guitar est conservé pour le diagnostic, mais n’entre pas dans le
  train polyphonique actuel.
- 62 476 notes disposent d’une supervision harmonique.
- Aucune fuite de groupe détectée entre les splits.
### Limite harmonique à corriger

`note_id` relie les notes aux mesures harmoniques. Cependant,
`note_harmonic_present` sert actuellement principalement de masque : les
harmoniques absentes ne constituent pas suffisamment d’exemples négatifs.
Le modèle ne possède donc pas encore de classification explicite
fondamentale contre harmonique/résonance. Lorsqu'une fréquence supérieure est
à la fois un partiel d'une fondamentale plus grave et une note volontairement
jouée, le décodeur ne peut l'identifier que partiellement : il la conserve si
elle possède un onset propre suffisamment fort, mais peut la supprimer lorsque
cet onset est faible. Une protection d'accord sans preuve indépendante serait
également dangereuse, car elle transformerait des résonances en notes fantômes.
## Journal des étapes
<!-- JOURNAL_START -->
- 2026-07-22 — **terminé** — entraînement polyphonique multi-source V2.2 sur
  GuitarSet, GAPS et Guitar-TECHS ; époque 8 sélectionnée, test verrouillé.
- 2026-07-22 — **terminé** — classement validation-only, sélection musicale,
  exports TFLite/ONNX et contrôles de parité.
- 2026-07-27 — **terminé** — validation du décodeur desktop ; diminution des
  notes fantômes et harmoniques parasites, mais rappel encore insuffisant.
- 2026-07-28 — **terminé** — suppression du périmètre Android, nettoyage des
  anciennes versions et adoption des branches Git.
- 2026-07-28 — **terminé** — reconstruction reproductible de
  `data/processed`, sans fuite entre train, validation et test.
- 2026-07-28 — **terminé** — préparation du pipeline Kaggle privé :
  packaging sans test, smoke/train P100, reprise, supervision et récupération.
<!-- PROJECT_TASK:kaggle_training_dataset_upload:START -->
- 2026-07-28 — **terminé** — `kaggle_training_dataset_upload` : pipeline Kaggle P100 validé avec succès sur le compte `miranacareneandrisoa`, commit `8bccadc6`, TensorFlow 2.20/Keras 3. Le smoke attache les 16 shards, charge les NPY tronqués, entraîne une époque de 256 exemples, valide sur 128 exemples et produit `best.keras`, `last.keras`, `final.keras`, l'archive et le rapport. Archive 17111040 octets, SHA-256 `830aa93d81d814a2f3109b9a62e26612348d90f53c3e4000078c6bcd95070117` conforme ; `locked_test_used=false`. Les quatre corpus sont présents dans les pools. Les métriques smoke (val_frame_micro_f1=0.061205, val_onset_micro_f1=0.002302) vérifient l'exécution, pas la qualité.
<!-- PROJECT_TASK:kaggle_training_dataset_upload:END -->
<!-- PROJECT_TASK:checkpoint_validation_selection:START -->
- 2026-07-28 — **terminé** — `checkpoint_validation_selection` : Sélection musicale Kaggle validation-only terminée et validée sur 12 enregistrements équilibrés (3 par corpus), candidate unique epoch-08. Archive 51548160 octets, SHA-256 ec9725179092a10d43af2dbbef9b61cc69f632c6038bc1b567041f3c120f7d28 conforme ; selection.json, selected.keras, thresholds.json et decoder_config.json présents ; selected.keras identique à epoch-08 ; locked_test_used=false. Métriques : F1 onset global 0,173294, F1 onset pondéré 0,233170, F1 onset+offset pondéré 0,127564. Limites réelles : 3160 faux positifs, 2994 notes manquantes, 71,44 faux NoteOn/min ; F1 onset Guitar-TECHS direct 0,039755 et micro 0,052980, contre GuitarSet 0,333844 et GAPS 0,212366. Latence causale NoteOn p50 65,63 ms, p90 164,74 ms.
<!-- PROJECT_TASK:checkpoint_validation_selection:END -->
<!-- PROJECT_TASK:skill_project_contract:START -->
- 2026-07-28 — **terminé** — `skill_project_contract` : skill
  guitar-audio-midi-researcher enrichi avec le contrat permanent du projet,
  puis rendu autonome : lecture complète obligatoire de `readme/README.md`,
  vérification Git/artifacts avant toute action, interrogation des compteurs
  réels à chaque demande de progression sans extrapolation, puis mise à jour
  de la même entrée de journal en fin d’étape ; validation réussie
<!-- PROJECT_TASK:skill_project_contract:END -->
<!-- PROJECT_TASK:desktop_candidate_validation:START -->
- 2026-07-29 — **terminé** — `desktop_candidate_validation` : Checkpoint Kaggle epoch-08 installé localement et exporté : parité TFLite/ONNX 100 % sur 96 exemples, ONNX p95 3,25 ms. Le TFLite est bit à bit identique au bundle stable (SHA-256 4a4df49d...), donc les poids sont reproduits ; seuls les seuils diffèrent. Deux benchmarks TFLite stricts restent instables malgré des p95 sous 5,80 ms. Après correction d’un WAV Guitar-TECHS temporaire écrêté, l’A/B donne F1 onset 0,0882 vers 0,0870 et faux positifs 33 vers 34 ; GuitarSet donne 0,2966 vers 0,3025 mais onset+offset 0,2542 vers 0,2437 et fragmentation 2 vers 4. Candidat non promu ; bundle v2_2_0 conservé. Runtime corrigé : fallback à 1 thread si la recommandation benchmark est absente. Test verrouillé non utilisé.
<!-- PROJECT_TASK:desktop_candidate_validation:END -->
<!-- PROJECT_TASK:adaptive_attack_validation:START -->
- 2026-07-29 — **terminé** — `adaptive_attack_validation` : Audit WAV Guitar-TECHS corrigé : l'ancien extrait était écrêté à 99,94 % par une conversion int16 incorrecte dans un script temporaire ; train et évaluations officielles non affectés. Ablation validation-only sur les 12 enregistrements exacts : faux NoteOn causaux 2118 vers 1389 (-34,4 %), erreurs d'octave 444 vers 310, F1 onset pondéré 0,2332 vers 0,2409 et Guitar-TECHS direct 0,0398 vers 0,0459. Régression : rappel causal 0,4636 vers 0,3968, F1 GAPS 0,2124 vers 0,1824 et F1 global 0,1733 vers 0,1604. Pipeline p95 3,30 à 4,17 ms sous le hop 5,80 ms, sans délai algorithmique. Candidat installé séparément, bundle stable inchangé, test verrouillé non utilisé.
<!-- PROJECT_TASK:adaptive_attack_validation:END -->
<!-- PROJECT_TASK:live_ab_adaptive_attack:START -->
- 2026-07-29 — **anomalie** — `live_ab_adaptive_attack` : L'audit du train annulé confirme un goulot d'étranglement I/O, pas une erreur CUDA. Le smoke P100 représentatif du snapshot `834b318a` est `COMPLETE` : staging 1 508 fichiers/8 643 963 647 octets en 208,70 s, entraînement-validation 8 192/2 048 en 29,85 s à 274,73 exemples/s, archive 17 745 920 octets et SHA-256 vérifié, `locked_test_used=false`; projection mesurée 2,00 h pour 8 époques avec staging. La reprise exacte et le transport inter-kernels sont poussés; le garde 16 shards du commit `5a5a2eff` porte le total à 305 tests. Le retry recovery P100 est `COMPLETE` : archive 26 685 440 octets et SHA-256 conformes, `locked_test_used=false`, roundtrip Keras 3 strict validé en génération 6/slot B avec Adam 128 et LR conservé. La phase 1 `guitar-midi-recovery-phase1-5a5a2eff` s'est figée à 170,3485 s pendant `model.summary()`, avant tout marqueur de reprise ou entraînement, puis a été supprimée manuellement le `2026-07-30`; aucun output terminal n'était publié et le quota final vérifié est 24,00/30 h. Les doublons du log sont un défaut de collecte Kaggle, pas la preuve de deux processus. Le correctif poussé `68084816` ajoute les jalons `RECOVERY_PREFLIGHT`, borne le processus entier à 10 minutes et rend `PROCESS_TIMEOUT` explicite. La provenance Kaggle est aussi corrigée en lisant `source_metadata.json` à la racine du dataset avant le fallback; 307 tests passent. Prochaine porte : supprimer l'affichage tabulaire de `model.summary()` dans le cloud, valider localement, publier le nouveau snapshot, puis lancer une seule phase 1 diagnostique; aucune phase 2 avant archive validée. MCP bloqué par HTTP 403 `oauthClients.use`. Test verrouillé exclu.
  - Surveillance `2026-07-30T07:52:29+04:00` : terminée; le slug est inaccessible et absent de la liste réelle des kernels. Aucune relance effectuée.
  - Mise à jour `2026-07-30T08:05:22+04:00` : la porte cloud
    précédente est annulée. Le contrat persistant interdit désormais Kaggle
    et Colab sans nouvelle autorisation explicite. `model.summary()` est
    remplacé par un aperçu compact; le smoke CPU local représentatif
    8 192/2 048 passe à 169,89 exemples/s, reprise A/B génération 6,
    `locked_test_used=false`. Le train complet sera local, unique et
    récupérable. Les 308 tests de non-régression passent.
  - Démarrage `2026-07-30T08:08:46+04:00` : run local
    `polyphonic_dual_stream_bass_20260730_080855`, PID TensorFlow 41032,
    époque 1/8, reprise A/B toutes les 32 batches et budget récupérable de
    six heures. Au batch 50/3 750, débit 151,25 exemples/s et projection
    dynamique 3 h 31. Test verrouillé exclu.
  - Surveillance `2026-07-30T08:13:17+04:00` : batch 650/3 750 de
    l'époque 1/8, 171,68 exemples/s, environ 3 h 02 restantes, recovery A/B
    valides et aucune erreur. L'automation locale
    `suivi-train-local-dual-stream` contrôle le run toutes les dix minutes
    sans utiliser Kaggle ni le test verrouillé.
<!-- PROJECT_TASK:live_ab_adaptive_attack:END -->
<!-- PROJECT_TASK:ollama_local_team:START -->
- 2026-08-08 — **terminé** — `ollama_local_team` : routeur local versionné
  pour `qwen3:8b`, `qwen3:14b` et `qwen3.6:latest`, appelé par SSH depuis
  Windows et partageant le verrou atomique du worker TensorFlow. Le correctif
  `af5437ee` maintient désormais ce verrou jusqu'au déchargement confirmé,
  refuse les worktrees sales, les proxies/redirections et tout composant de
  chemin test verrouillé, transporte les prompts par stdin et retire les corps
  de réponse des rapports persistants. Validation cumulée du correctif : 38
  tests Windows et 23 tests Mac, appel réel suivi de
  `active_lock=false/running_models=[]`, `locked_test_used=false`. La réponse
  générique du 14B n'est pas une revue valide. L'API directe réseau reste
  fermée sur `127.0.0.1:11434`; aucun modèle local ne possède l'autorité
  d'éditer, de commiter ou de remplacer les preuves réelles.
<!-- PROJECT_TASK:ollama_local_team:END -->
<!-- PROJECT_TASK:decoder_candidate_mining_contract:START -->
- 2026-08-08 — **terminé** — `decoder_candidate_mining_contract` : le
  contrat isolé corrige le découpage des épisodes avec `best_row` et
  `last_frame_index`, ajoute les features causales manquantes, sépare les
  métadonnées post-porte et impose des invariants JSON fail-closed. Les scores
  décroissants, les `event_id` distincts et les états incohérents sont testés.
  Les commits `af5437ee` et `88a66ce` sont approuvés par la revue externe et les
  38 tests ciblés Windows ont été rejoués avec succès. Aucun branchement dans
  `decoder.py`, minage, entraînement ou calcul validation n'a été effectué;
  test verrouillé fermé. La prochaine tâche distincte est une instrumentation
  désactivée par défaut, soumise à une nouvelle revue avant tout calcul.
<!-- PROJECT_TASK:decoder_candidate_mining_contract:END -->
<!-- PROJECT_TASK:decoder_candidate_instrumentation:START -->
- 2026-08-08 — **terminé** — `decoder_candidate_instrumentation` : collecteur
  optionnel désactivé par défaut ajouté aux voies legacy et causale. Snapshot
  pré-porte immuable, métadonnées post-décision, identifiants déterministes hors
  événement MIDI, encodage des raisons compatible avec le live, buffer borné,
  overflow fail-closed, remise par frame non bloquante et erreur de collecte
  fail-open. Les 86 tests Windows et Mac passent; le Mac ignore explicitement
  deux tests Windows-only. Les 512 frames sont identiques au décodeur `f9ed9d0`
  pour événements et état. Le chemin désactivé ne montre aucune régression
  mesurable; l'overhead activé est 98,11 µs/frame dans le benchmark dense. Mac
  propre au commit exact `f751422`. Revue de clôture de `f751422` et
  `d4492c3` approuvée : les 86 tests documentés sont rejoués localement avec
  succès (`86/86`, 6,895 s), l'arbre est propre et aucun processus scientifique
  n'est actif sur Windows ou Mac. La parité instrumentation désactivée/activée,
  les snapshots pré-porte, la remise non bloquante et les erreurs fail-open
  sont confirmés. Aucun minage, entraînement, validation, export, live ou test
  verrouillé n'est autorisé par cette clôture.
<!-- PROJECT_TASK:decoder_candidate_instrumentation:END -->
<!-- PROJECT_TASK:decoder_candidate_provenance_contract:START -->
- 2026-08-08 — **terminé** — `decoder_candidate_provenance_contract` : sans
  calcul scientifique, le protocole v1 est complété par le snapshot manifeste
  attesté, le plan canonique immuable, le contexte train-only et les labels
  causales. Les mêmes objets `ManifestItem` du CSV hashé alimentent le corpus
  et le collecteur; copies de snapshot/capacité/plan, chemins substitués,
  mélange de SHA, duplicats de prises/IDs et couverture de partition incomplète
  échouent fermé. Les labels utilisent un matcher same-pitch strictement causal
  (250 ms, fin de hop), excluent frames invalides et retriggers documentés, et
  refusent toute autre trace manquante ou erreur de collecteur. Les features
  sont projetées strictement hors cible/provenance/post-porte. Tests Windows :
  compilation, diff propre et suite ciblée complète OK; résultat exact archivé
  dans `2026-08-08_decoder-candidate-snapshot-label-protocol.md`. Aucun plan
  réel, artefact, minage, entraînement, validation, export, live ou test
  verrouillé n'a été produit. Les empreintes des actifs audio/labels restent à
  préenregistrer avant toute ouverture réelle. La revue de `a06e9641` a trouvé
  un faux positif de labels : un retrigger same-pitch exclu du fit ne consommait
  pas sa référence avant le matching d'un candidat ultérieur. Le correctif
  applique désormais le matcher à tous les NoteOn valides du flux avant de
  projeter uniquement les résultats entraînables, et sépare les matches complets
  des matches exclus du fit. Il exige aussi un plan réellement persistant pour
  construire la capacité collecteur et le revérifie au `drain()`. Compilation,
  `git diff --check` et 131 tests ciblés Windows passent en 8,993 s, puis un
  rejeu indépendant passe en 9,336 s. La revue externe du commit `9e666eb0`
  est approuvée. Aucune donnée projet n'a été ouverte; la prochaine étape est
  uniquement la préinscription réelle, soumise à une nouvelle revue avant tout
  minage.
<!-- PROJECT_TASK:decoder_candidate_provenance_contract:END -->
<!-- PROJECT_TASK:decoder_candidate_asset_evidence_contract:START -->
- 2026-08-08 — **terminé** — `decoder_candidate_asset_evidence_contract` :
  ajout sans calcul scientifique d'un registre canonique d'empreintes pour les
  actifs que le futur mineur pourrait ouvrir. Chaque entrée train lie identité
  physique, partition préassignée, `audio_member`, taille et SHA-256 du
  conteneur audio et des labels; aucun chemin hôte n'est persisté, le manifeste
  déjà hashé restant son ancre. Le registre est écrit sans écrasement, relu et
  attesté; le contexte refuse d'ouvrir tout corpus sans ce registre. La revue
  de `7440d093` approuve le format mais a relevé la fenêtre du chargement audio
  paresseux. Le correctif vérifie désormais les labels à l'entrée du
  constructeur et l'audio à l'entrée de `corpus.audio()`. Un parcours
  synthétique réel `pre_register -> reload -> open_recording` prouve le refus
  d'un audio muté après construction du corpus; le cache de conteneur partagé
  est aussi couvert. Compilation, `git diff --check` et 136 tests ciblés
  Windows passent en 9,718 s. La revue externe de `d16b25f7` est approuvée et
  a autorisé la seule préinscription Mac. Celle-ci s'est arrêtée avant toute
  écriture ou hachage : le manifeste `b28cb17...` comporte dix groupes GAPS
  chevauchant train/validation. Le répertoire de sortie vide a été supprimé;
  aucun plan, registre, actif projet, minage, entraînement, validation, export,
  live ou test verrouillé n'a été produit. La revue de `d4280e0` est approuvée
  et n'autorise qu'un futur commit de politique, sans données ni calcul : le
  choix entre préserver la validation actuelle (A) et créer une nouvelle
  validation group-safe (B) appartient à l'utilisateur avant toute tentative.
  Mise à jour du 2026-08-09 : l'utilisateur a choisi **A**. Le schéma 2 du plan
  persiste désormais chaque capture train exclue parce que son groupe
  corpus-aware est présent dans validation, puis rematche cette liste contre le
  manifeste complet. La validation elle-même reste inchangée, toute liste train
  fournie manuellement échoue, et les objets exposés au futur contexte ne
  couvrent que les prises planifiées. Tests synthétiques uniquement; aucun plan
  réel, registre, actif projet, minage, entraînement, validation, export, live
  ou test verrouillé n'a été exécuté. La revue externe de `8190e3b` a ensuite
  autorisé l'unique préinscription réelle. Elle a réussi sur le Mac au même
  commit : manifeste `b28cb17…` stable avant/après, `31` exclusions GAPS/10
  joueurs, `541` captures planifiées et `541` entrées d'actifs, plan v2 SHA
  `a8347e4e…`, registre SHA `12dd74f2…`, aucune exclusion dans le registre et
  `locked_test_used=false`. Les trois artefacts bruts locaux et leur SHA sont
  archivés dans le rapport du 2026-08-09. Aucun replay, collecteur, minage,
  entraînement, validation, export, live ou test verrouillé n'a démarré. La
  revue externe de cette préinscription est maintenant approuvée. Un mineur
  train-only borné est implémenté sans calcul réel : CPU obligatoire, commit
  Git exact/worktree propre, sept SHA avant TensorFlow, 12 prises
  préassignées, écriture atomique sous `data/processed`, aucune perte tolérée
  et `fit_authorized=false`. La revue externe de `0e124352…` a ensuite trouvé
  deux défauts avant le premier replay : le SHA Git à 40 caractères était
  vérifié comme un SHA-256, et `data.py` importait TensorFlow au chargement du
  CLI avant les empreintes. Le correctif diffère les imports runtime
  `data`/contexte/Keras après les sept empreintes, le lien YAML-manifeste et le
  préflight CPU; il ajoute une validation Git dédiée et un test frais qui
  confirme qu'un mauvais SHA de checkpoint échoue avec TensorFlow absent.
  `py_compile`, `git diff --check` et 41 tests ciblés passent en 2,025 s.
  Aucun actif Policy A, checkpoint réel, inférence, replay, collecteur, minage,
  entraînement, validation, export, live ou test verrouillé n'a été exécuté.
  Une dernière revue externe de ce correctif est obligatoire avant l'unique
  replay Mac. Après l'approbation de `9ed93e7`, le préflight Mac a trouvé une
  nouvelle divergence avant tout CLI ou import TensorFlow : la politique audio
  versionnée était hachée en CRLF sur Windows (`bf4c…`) mais en LF sur macOS,
  comme le blob Git (`45ed…`). Les six autres entrées sont conformes; aucun
  actif, checkpoint, contexte, replay ni sortie n'a été ouvert ou produit. Le
  correctif impose LF pour les quatre configurations versionnées scellées et
  adopte `45ed…` dans le protocole. `py_compile`, `git diff --check` et 42
  tests ciblés passent en 1,721 s. La revue externe de `f4eb87a` est approuvée.
  L'unique minage CPU train-only a donc été exécuté sur le Mac : préflight
  complet réussi (`7/7` SHA, worktree propre, CPU forcé, verrou absent), job
  `decoder-candidate-bounded-mining-cpu-20260809` terminé avec `exit_code=0`
  en 6 min 17 s et `locked_test_used=false`. Les artefacts Mac
  `candidate_events.jsonl` (`19cb073a…`) et `mining_report.json`
  (`3ad78ede…`) sont intègres. Ils contiennent 12 prises préinscrites, 429
  candidats supervisés (`94` positifs causaux, `335` faux NoteOn), zéro perte
  de collecte et aucun motif non instrumenté autre que 169 retriggers exclus.
  La revue externe de `83afcf34` approuve le pilote, mais confirme qu'il est
  insuffisant pour le fit : `fit` ne contient que 123 exemples, dont 23
  positifs, et certaines cellules GuitarSet n'ont qu'une classe. Le résultat
  reste **non autorisant** (`fit_authorized=false`). Le prochain contrat,
  également sans calcul, fixe six prises canoniques par corpus et partition
  (72 prises) et des seuils préenregistrés de représentation avant toute revue
  ultérieure, publiés automatiquement comme une porte non autorisante. Il
  complète aussi la réconciliation future du flux complet avec
  les compteurs `full_flow_invalid_frame` et `full_flow_outside_audio`. Les 45
  tests synthétiques ciblés, `py_compile` et `git diff --check` passent. La
  revue ChatGPT de ce nouveau contrat est obligatoire avant tout second minage.
  Aucun fit, calibration, validation, sélection de seuil, export, live ou test
  verrouillé n'est permis.
- Mise à jour du `2026-08-09T22:18:38+04:00` : le second minage CPU train-only
  autorisé a terminé au commit `42a88b0d…` sur les 72 prises canoniques, après
  préflight complet des sept SHA. Il produit 3 057 lignes supervisées
  (639 positives, 2 418 négatives), zéro tentative perdue, 3 057 `event_id`
  uniques, 54 groupes physiques sans croisement de partition et
  `locked_test_used=false`. Trois prises GuitarSet sélectionnées n'ont pas
  produit de candidat supervisé, ce qui est conservé comme constat de
  population. La porte préenregistrée échoue uniquement pour les positifs
  `guitarset_poly_mix` (`dev=6`, `calibration=7`, minimum 8) ;
  `fit_authorized=false` est maintenu. Aucun fit, calibration, validation,
  export, live, sélection de seuil ou test verrouillé ne suit. La seule étape
  suivante est la revue humaine du rapport
  `readme/results/2026-08-09_decoder-candidate-extended-mining-run.md` avant
  de définir une hypothèse distincte.
- Hypothèse v3 désormais implémentée, sans calcul :
  `configs/decoder_candidate_guitarset_expansion_policy_a_v3.json` scelle à
  nouveau les mêmes entrées et fixe 90 prises canoniques, soit 6 par
  corpus × partition sauf 12 pour GuitarSet. Les premiers six GuitarSet sont
  conservés et les six suivants par partition sont ajoutés dans le même corpus
  candidat futur ; la porte reste à 8 et `fit_authorized=false` reste
  inconditionnel. Les schémas précédents gardent leur sélection uniforme et le
  schéma 3 refuse une table de comptes incomplète. Compilation, `git diff
  --check` et 67 tests synthétiques ciblés passent en 2,157 s. Aucune donnée
  projet, inférence, minage, fit, calibration, validation, export, live ou test
  verrouillé n'a été exécuté. La revue externe de `8c92eb0` a relevé que le
  CLI pouvait encore recevoir un autre JSON v3 tout en gardant les sept SHA
  internes. Le correctif suivant exige donc, avant Git, actifs ou TensorFlow,
  le chemin exact du protocole v3 versionné et son SHA-256 LF
  `db55930a9faadc12fb7b08e52e0baac3543e3d5cb654844ea93e0d727a563683`.
  Les deux substitutions testées (`guitarset=13` par chemin externe, puis
  contenu canonique modifié) échouent avant TensorFlow. `py_compile`,
  `git diff --check` et 69 tests synthétiques ciblés passent en `2,120 s`.
  Aucun actif projet, inférence, minage, fit, calibration, validation, export,
  live ou test verrouillé n'avait été exécuté au moment de ce correctif. La
  revue externe l'a ensuite approuvé et l'unique job CPU V3
  `decoder-candidate-guitarset-v3-cpu-20260809` a démarré à
  `2026-08-09T19:07:52Z` au commit exact `4ddc886…`. CPU forcé, limite murale
  `3 600 s`, verrou actif. Le job termine ensuite avec `exit_code=0` et
  `complete_non_authorizing` : 3 139 candidats supervisés (684 positifs,
  2 455 négatifs), 0 perte et 3 139 `event_id` uniques. La porte à 8 passe,
  dont GuitarSet positif `31/28/14`, mais `fit_authorized=false` et
  `locked_test_used=false` restent obligatoires. Aucune autre action
  scientifique n'est autorisée avant la revue du rapport terminal.
  Rapports :
  `readme/results/2026-08-09_decoder-candidate-guitarset-expansion-hypothesis.md`
  et `readme/results/2026-08-09_decoder-candidate-guitarset-protocol-binding-fix.md`,
  puis `readme/results/2026-08-09_decoder-candidate-guitarset-v3-mining-run.md`.
- Revue externe de `9d360816` : **approuvée**. V3 clôt le minage avec une porte
  de représentation passée et sans autoriser un fit. L'hypothèse suivante est
  donc préenregistrée, sans calcul : une régression logistique causale de 12
  entrées strictement pré-porte, entraînée seulement sur les 938 lignes fit du
  corpus V3, pondérée par famille/cible/groupe de fuite pour ne pas doubler les
  vues Guitar-TECHS. Dev choisira l'époque, calibration choisira seule un seuil
  éventuel ; validation historique et test verrouillé restent fermés. La revue
  externe de cette hypothèse est requise avant toute implémentation, et une
  revue distincte avant tout fit. La revue `e90321a1` a autorisé ensuite la
  seule implémentation sans exécution : préflight V3 avec octets hachés une fois,
  projection pré-porte à 12 dimensions, pondération locale fit/dev/calibration,
  BCE dev hors L2, seed `47`, ordre canonique et `shuffle=false`, plus parité
  de sauvegarde/rechargement sans écrasement. Les 42 tests synthétiques ciblés
  passent en `2,015 s`; `rg` confirme l'absence de tout appel `fit(` dans ce
  module. Aucun artefact V3 réel, fit, calibration, validation, export, live ou
  test verrouillé n'a été utilisé. Une nouvelle revue externe est obligatoire
  avant toute décision de fit. La revue de `76ebf937` approuve le protocole V1
  et autorise seulement un runner sans exécution. Ce runner n'accepte aucun
  poids ni hyperparamètre externe, exige l'accusé `DECODER_CANDIDATE_FIT_EXECUTE=1`,
  Git propre exact, CPU, artefacts V3 hachés et destination fraîche ; il limite
  l'entraînement à `fit`, évalue dev par inférence/BCE hors L2, ne calibre
  qu'après dev et persiste le standardiseur lié au modèle. Compilation,
  `git diff --check` et 47 tests synthétiques ciblés passent en `5,388 s`.
  Aucun job Mac, fit, calibration, validation, export, live ou test verrouillé
  n'a été lancé. Une revue externe supplémentaire du runner est obligatoire.
  La revue de `5de7f7ef` a ensuite demandé un correctif préalable, sans donnée
  projet : le runner convertit maintenant explicitement les entrées Keras
  `fit` en tableaux NumPy `float32`, persiste la courbe fit/dev par époque,
  la décomposition des poids par partition/famille/cible/groupe et le coût
  d'inférence par candidat. Un test Keras synthétique traverse une époque
  réelle avec ce même chemin et les 48 tests ciblés passent. Aucun artefact V3,
  fit réel, calibration, validation, export, live ou test verrouillé n'a été
  ouvert. Le prochain lancement, seulement après revue externe, devra passer
  exclusivement par `scripts/remote/mac_worker.sh start` sur CPU avec timeout
  externe de 900 s; jamais directement par le module Python. Rapport :
  `readme/results/2026-08-09_decoder-candidate-fit-runner-evidence-correction.md`.
  Rapports :
  `readme/results/2026-08-09_decoder-candidate-fit-hypothesis-v1.md`, puis
  `readme/results/2026-08-09_decoder-candidate-fit-protocol-implementation.md`,
  puis `readme/results/2026-08-09_decoder-candidate-fit-runner-implementation.md`.
<!-- PROJECT_TASK:decoder_candidate_asset_evidence_contract:END -->
<!-- JOURNAL_END -->
## Rapports détaillés

- [2026-08-12 — contrat H27 des fixtures, tests et population future](results/2026-08-12_harmonic-censoring-h27-fixture-test-population-design.md)
- [2026-07-22 — entraînement polyphonique multi-source](results/2026-07-22_polyphonic-training.md)
- [2026-07-27 — validation du décodeur desktop polyphonique](results/2026-07-27_polyphonic-desktop-validation.md)
- [2026-07-28 — état du produit desktop monophonique](results/2026-07-28_mono-desktop-release.md)
- [2026-07-28 — reconstruction de `data/processed`](results/2026-07-28_processed-reconstruction.md)
- [2026-07-28 — incident de publication Kaggle](results/2026-07-28_kaggle-upload-incident.md)
- [2026-07-29 — validation du candidat desktop sélectionné](results/2026-07-29_desktop-candidate-validation.md)
- [2026-07-29 — validation de l’attaque causale adaptative](results/2026-07-29_adaptive-attack-validation.md)
- [2026-08-05 — hypothèse de minage des candidats du décodeur](results/2026-08-05_decoder-candidate-mining-hypothesis.md)
- [2026-08-08 — équipe Ollama locale](results/2026-08-08_ollama-local-team.md)
- [2026-08-08 — durcissement Ollama et contrat candidat](results/2026-08-08_ollama-candidate-contract-hardening.md)
- [2026-08-08 — instrumentation des candidats du décodeur](results/2026-08-08_decoder-candidate-instrumentation.md)
- [2026-08-08 — revue de clôture de l'instrumentation](results/2026-08-08_decoder-candidate-instrumentation-review.md)
- [2026-08-08 — contrat de provenance des candidats du décodeur](results/2026-08-08_decoder-candidate-provenance-contract.md)
- [2026-08-08 — protocole snapshot et labels causales des candidats](results/2026-08-08_decoder-candidate-snapshot-label-protocol.md)
- [2026-08-08 — correctif causal des retriggers candidats](results/2026-08-08_decoder-candidate-retrigger-causal-matching-fix.md)
- [2026-08-08 — revue du correctif causal des retriggers](results/2026-08-08_decoder-candidate-retrigger-causal-matching-review.md)
- [2026-08-08 — contrat d'empreintes des actifs candidats](results/2026-08-08_decoder-candidate-asset-evidence-contract.md)
- [2026-08-08 — correctif de lecture paresseuse des actifs candidats](results/2026-08-08_decoder-candidate-asset-evidence-lazy-audio-fix.md)
- [2026-08-08 — préinscription bloquée par le chevauchement GAPS](results/2026-08-08_decoder-candidate-preregistration-blocked-by-gaps-leakage.md)
- [2026-08-09 — contrat de politique A pour le chevauchement GAPS](results/2026-08-09_decoder-candidate-gaps-policy-a-contract.md)
- [2026-08-09 — préinscription réelle Policy A](results/2026-08-09_decoder-candidate-policy-a-preregistration.md)
- [2026-08-09 — mineur borné de candidats du décodeur](results/2026-08-09_decoder-candidate-bounded-miner.md)
- [2026-08-09 — correctif du préflight du mineur borné](results/2026-08-09_decoder-candidate-bounded-miner-preflight-fix.md)
- [2026-08-09 — correctif CRLF/LF du préflight du mineur borné](results/2026-08-09_decoder-candidate-bounded-miner-eol-preflight-fix.md)
- [2026-08-09 — passe CPU du mineur borné Policy A](results/2026-08-09_decoder-candidate-bounded-mining-run.md)
- [2026-08-09 — contrat d'extension Policy A à six prises par cellule](results/2026-08-09_decoder-candidate-expanded-policy-a-contract.md)
- [2026-08-09 — passe CPU étendue Policy A, porte refusée](results/2026-08-09_decoder-candidate-extended-mining-run.md)
- [2026-08-09 — hypothèse d'extension GuitarSet canonique](results/2026-08-09_decoder-candidate-guitarset-expansion-hypothesis.md)
- [2026-08-09 — correctif de scellement du protocole GuitarSet v3](results/2026-08-09_decoder-candidate-guitarset-protocol-binding-fix.md)
- [2026-08-09 — minage CPU V3 GuitarSet, porte passée mais non autorisant](results/2026-08-09_decoder-candidate-guitarset-v3-mining-run.md)
- [2026-08-09 — hypothèse V1 de fit du filtre causal de candidats](results/2026-08-09_decoder-candidate-fit-hypothesis-v1.md)
- [2026-08-09 — implémentation V1 du protocole de fit causal](results/2026-08-09_decoder-candidate-fit-protocol-implementation.md)
- [2026-08-09 — implémentation du runner V1 de fit causal](results/2026-08-09_decoder-candidate-fit-runner-implementation.md)
- [2026-08-09 — correctif de transport et préinscription A/B historique V1](results/2026-08-09_causal-candidate-fit-v1-transport-and-validation-preregistration.md)
- [2026-08-09 — implémentation A/B historique du filtre causal V1](results/2026-08-09_causal-candidate-validation-ab-implementation.md)
- [2026-08-09 — contrat d'invocation A/B historique du filtre causal V1](results/2026-08-09_causal-candidate-validation-ab-invocation-contract.md)
- [2026-08-09 — correctif pré-métrique du contrat A/B historique](results/2026-08-09_causal-candidate-validation-ab-threshold-contract-fix.md)
- [2026-08-09 — relance CPU A/B historique V1, résultat non autorisant](results/2026-08-09_causal-candidate-validation-ab-v1-run.md)
- [2026-08-09 — hypothèse V2 de porte causale post-ranking](results/2026-08-09_causal-candidate-v2-post-ranking-hypothesis.md)
- [2026-08-09 — implémentation synthétique de la porte causale V2](results/2026-08-09_causal-candidate-v2-synthetic-implementation.md)
- [2026-08-09 — intégration A/B synthétique explicite de la porte V2](results/2026-08-09_causal-candidate-v2-synthetic-integration.md)
- [2026-08-09 — protocole du diagnostic V2 train-only dev](results/2026-08-09_causal-candidate-v2-train-dev-diagnostic-protocol.md)
- [2026-08-09 — implémentation du runner V2 train-only dev](results/2026-08-09_causal-candidate-v2-train-dev-diagnostic-runner-implementation.md)
- [2026-08-10 — anomalie de préflight V2, artefacts locaux Mac absents](results/2026-08-10_causal-candidate-v2-train-dev-preflight-missing-local-artifacts.md)
- [2026-08-10 — matérialisation V2 bloquée, octets sources absents](results/2026-08-10_causal-candidate-v2-artifact-materialization-blocked.md)
- [2026-08-10 — sources exactes V2 retrouvées, copie encore interdite](results/2026-08-10_causal-candidate-v2-artifact-source-recovered.md)
- [2026-08-10 — matérialisation binaire contrôlée des artefacts V2 scellés](results/2026-08-10_causal-candidate-v2-artifact-materialization.md)
- [2026-08-10 — diagnostic V2 train/dev CPU, résultat exploratoire non promotionnel](results/2026-08-10_causal-candidate-v2-train-dev-diagnostic-run.md)
- [2026-08-10 — contrat d'évaluation V2 indépendante GAPS/Guitar-TECHS, sans calcul](results/2026-08-10_causal-candidate-v2-independent-validation-contract.md)
- [2026-08-10 — conformité synthétique H19 du risque `frame_fallback`](results/2026-08-10_provisional-resolution-frame-fallback-h19-synthetic-conformance.md)
- [2026-08-10 — amendement H17a pré-exécution de la taxonomie des raisons](results/2026-08-10_provisional-resolution-frame-fallback-h17a-taxonomy-amendment.md)
- [2026-08-10 — contrat H20 de liaison d'une future exécution réelle H17](results/2026-08-10_provisional-resolution-frame-fallback-h20-real-execution-contract.md)
- [2026-08-10 — exécution réelle H17, résultat atomique négatif pour l’enrichissement `frame_fallback`](results/2026-08-10_provisional-resolution-frame-fallback-h17-real-execution.md)
- [2026-08-10 — contrat pré-train H23 du censoring harmonique multiscale](results/2026-08-10_harmonic-censoring-pretrain-h23-contract.md)
- [2026-08-10 — corrections de revue H23a du contrat de censoring](results/2026-08-10_harmonic-censoring-h23-review-corrections.md)
- [2026-08-10 — fermeture mathématique H23b du contrat de censoring](results/2026-08-10_harmonic-censoring-h23b-mathematical-closure.md)
- [2026-08-10 — implémentation pure du resolver/materializer H23](results/2026-08-10_harmonic-censoring-h23-harness-implementation.md)
- [2026-08-10 — contrat de future capability d’exécution synthétique H23](results/2026-08-10_harmonic-censoring-h23-synthetic-execution-capability-contract.md)
- [2026-08-10 — transition d’activation du seal H23 sans circularité](results/2026-08-10_harmonic-censoring-h23-seal-activation-transition.md)
- [2026-08-10 — définition séparée de l’activation et du seal H23](results/2026-08-10_harmonic-censoring-h23-activation-and-seal-definition.md)
- [2026-08-10 — émission administrative de la capability H23 sur Mac](results/2026-08-10_harmonic-censoring-h23-administrative-capability-issuance.md)
- [2026-08-10 — contrat claim, exécuteur scientifique et transcript H23](results/2026-08-10_harmonic-censoring-h23-executor-claim-transcript-contract.md)
- [2026-08-10 — résultat terminal de l’unique passe synthétique H23](results/2026-08-10_harmonic-censoring-h23-synthetic-one-shot-result.md)
- [2026-08-10 — contrat successeur H24 après clôture H23](results/2026-08-10_harmonic-censoring-h24-successor-contract.md)
- [2026-08-10 — manifests et plan de test complet H24 sans synthèse](results/2026-08-10_harmonic-censoring-h24-manifests-full-test-plan.md)
- [2026-08-11 — clôture forensique H24 inconclusive, one-shot consommé sans P0](results/2026-08-11_harmonic-censoring-h24-final-forensic-inconclusive-closure.md)
- [2026-08-11 — contrat de décision successeur H25 après consommation H24](results/2026-08-11_harmonic-censoring-h25-successor-decision-contract.md)
- [2026-08-11 — implémentation du harness administratif pré-claim H25](results/2026-08-11_harmonic-censoring-h25-preclaim-administrative-lifecycle-harness.md)
- [2026-08-11 — correction de l'entrypoint de qualification administrative H25](results/2026-08-11_harmonic-censoring-h25-administrative-qualification-entrypoint.md)
- [2026-08-11 — résultat de la qualification administrative pré-claim H25](results/2026-08-11_harmonic-censoring-h25-administrative-lifecycle-qualification-result.md)
- [2026-08-11 — contrat scientifique H25 pitch-dilution et causal 4096/8192](results/2026-08-11_harmonic-censoring-h25-scientific-hypothesis-execution-contract.md)
- [2026-08-11 — manifests population/tests et spécifications de fixtures H25](results/2026-08-11_harmonic-censoring-h25-population-test-manifests.md)
- [2026-08-11 — contrat H25 de runtime, provenance et encodage de matérialisation](results/2026-08-11_harmonic-censoring-h25-population-materialization-runtime-contract.md)
- [2026-08-11 — implémentation dormante du materializer/recomputer H25](results/2026-08-11_harmonic-censoring-h25-dormant-population-materializer.md)
- [2026-08-11 — correction du moteur scientifique dormant et de la recomputation H25](results/2026-08-11_harmonic-censoring-h25-dormant-scientific-recomputation-correction.md)
- [2026-08-11 — capability scientifique et autorité one-shot dormantes H25](results/2026-08-11_harmonic-censoring-h25-dormant-scientific-capability-authority.md)
- [2026-08-11 — autorité one-shot dormante de matérialisation H25](results/2026-08-11_harmonic-censoring-h25-materialization-authority-dormant.md)
- [2026-08-11 — clôture terminale et analyse forensique H25 à P0-004](results/2026-08-11_harmonic-censoring-h25-terminal-forensic-closure.md)
- [2026-08-11 — préinscription scientifique H26 à certificats bornés](results/2026-08-11_harmonic-censoring-h26-scientific-preregistration.md)
- [2026-08-11 — contrat dormant de qualification du runtime de matérialisation H26](results/2026-08-11_harmonic-censoring-h26-materialization-runtime-qualification-contract.md)
- [2026-08-11 — implémentation dormante du qualificateur runtime H26](results/2026-08-11_harmonic-censoring-h26-runtime-qualifier-dormant-implementation.md)
- [2026-08-11 — primitives dormantes du codec et des identités d'exécution H26](results/2026-08-11_harmonic-censoring-h26-runtime-execution-primitives-dormant-implementation.md)
- [2026-08-11 — seal externe du contrat d'exécution runtime H26](results/2026-08-11_harmonic-censoring-h26-runtime-execution-contract-external-seal.md)
- [2026-08-11 — correction de liaison de preuve du contrat d'autorité de matérialisation H26](results/2026-08-11_harmonic-censoring-h26-population-materialization-authority-contract.md)
- [2026-08-11 — validateur dormant de preuve runtime pour la matérialisation H26](results/2026-08-11_harmonic-censoring-h26-materialization-runtime-execution-proof-validator-dormant-implementation.md)
- [2026-08-11 — contrat canonique du futur artefact d'autorité de matérialisation H26](results/2026-08-11_harmonic-censoring-h26-materialization-authority-artifact-contract.md)
- [2026-08-11 — implémentation dormante du validateur d'artefact d'autorité H26](results/2026-08-11_harmonic-censoring-h26-materialization-authority-artifact-validator-dormant-implementation.md)
- [2026-08-11 — clôture de revue du validateur dormant d'artefact d'autorité H26](results/2026-08-11_harmonic-censoring-h26-materialization-authority-artifact-validator-review-closure.md)
- [2026-08-11 — contrat dormant d'activation opérationnelle du runtime H26](results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-contract.md)
- [2026-08-11 — seal externe du contrat dormant d'activation runtime H26](results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-contract-external-seal.md)
- [2026-08-11 — implémentation dormante du loader du seal externe d'activation runtime H26](results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-contract-external-seal-loader-dormant-implementation.md)
- [2026-08-11 — clôture de revue du loader dormant du seal externe d'activation runtime H26](results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-contract-external-seal-loader-review-closure.md)
- [2026-08-11 — implémentation dormante du validateur de l'activation runtime H26](results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-validator-dormant-implementation.md)
- [2026-08-11 — clôture de revue du validateur dormant de l'activation runtime H26](results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-validator-review-closure.md)
- [2026-08-11 — contrat dormant d'émission de l'activation runtime H26](results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-issuance-contract.md)
- [2026-08-11 — seal externe du contrat dormant d'émission de l'activation runtime H26](results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-issuance-contract-external-seal.md)
- [2026-08-11 — loader dormant du seal du contrat d'émission H26, en attente de revue du lot](results/2026-08-11_harmonic-censoring-h26-runtime-qualification-operational-activation-issuance-contract-external-seal-loader-dormant-implementation.md)
- [2026-08-11 — contrat additif d'implémentation dormante de l'issuer H26](results/2026-08-11_harmonic-censoring-h26-activation-issuer-dormant-implementation-contract.md)
- [2026-08-11 — seal du contrat d'implémentation dormante de l'issuer H26](results/2026-08-11_harmonic-censoring-h26-activation-issuer-dormant-implementation-contract-external-seal.md)
- [2026-08-11 — loader dormant du seal d'implémentation de l'issuer H26](results/2026-08-11_harmonic-censoring-h26-activation-issuer-dormant-implementation-contract-seal-loader.md)
- [2026-08-11 — planner dormant d'émission de l'activation H26](results/2026-08-11_harmonic-censoring-h26-activation-issuance-planner-dormant.md)
- [2026-08-11 — issuer/publisher dormant de l'activation H26](results/2026-08-11_harmonic-censoring-h26-activation-issuer-dormant.md)
- [2026-08-11 — contrat dormant d'orchestration runtime one-shot H26](results/2026-08-11_harmonic-censoring-h26-runtime-one-shot-orchestration-dormant-contract.md)
- [2026-08-11 — seal du contrat dormant d'orchestration runtime H26](results/2026-08-11_harmonic-censoring-h26-runtime-one-shot-orchestration-contract-seal.md)
- [2026-08-11 — loader dormant du seal d'orchestration runtime H26](results/2026-08-11_harmonic-censoring-h26-runtime-one-shot-orchestration-contract-seal-loader.md)
- [2026-08-11 — orchestrateur runtime one-shot dormant H26](results/2026-08-11_harmonic-censoring-h26-runtime-one-shot-orchestrator-dormant.md)
- [2026-08-11 — contrat dormant d'opérationnalisation de la matérialisation H26](results/2026-08-11_harmonic-censoring-h26-materialization-operationalization-dormant-contract.md)
- [2026-08-11 — seal du contrat dormant de matérialisation H26](results/2026-08-11_harmonic-censoring-h26-materialization-operationalization-contract-seal.md)
- [2026-08-11 — loader dormant du seal de matérialisation H26](results/2026-08-11_harmonic-censoring-h26-materialization-operationalization-contract-seal-loader.md)
- [2026-08-11 — gate dormant de materialization authority H26](results/2026-08-11_harmonic-censoring-h26-materialization-authority-gate-dormant.md)
- [2026-08-11 — orchestrateur dormant de matérialisation H26](results/2026-08-11_harmonic-censoring-h26-materialization-orchestrator-dormant.md)
- [2026-08-11 — contrat dormant d'exécution scientifique H26](results/2026-08-11_harmonic-censoring-h26-scientific-execution-dormant-contract.md)
- [2026-08-11 — seal du contrat scientifique dormant H26](results/2026-08-11_harmonic-censoring-h26-scientific-execution-contract-seal.md)
- [2026-08-11 — loader dormant du seal scientifique H26](results/2026-08-11_harmonic-censoring-h26-scientific-execution-contract-seal-loader.md)
- [2026-08-11 — runner scientifique dormant H26 corrigé par frontière fake-only structurelle](results/2026-08-11_harmonic-censoring-h26-scientific-runner-dormant.md)
- [2026-08-11 — overlay correctif fake-only du runner scientifique dormant H26](results/2026-08-11_harmonic-censoring-h26-scientific-runner-fake-only-correction.md)
- [2026-08-11 — manifeste terminal du lot H26 pré-exécution dormant](results/2026-08-11_harmonic-censoring-h26-dormant-pre-execution-batch-manifest.md)
- [2026-08-11 — correction additive d'immutabilité profonde du lot dormant H26](results/2026-08-11_harmonic-censoring-h26-dormant-batch-deep-immutability-correction.md)
- [2026-08-11 — contrat correctif additif de l'ordre observer-entry H26](results/2026-08-11_harmonic-censoring-h26-runtime-observer-entry-order-correction-contract.md)
- [2026-08-11 — seal externe du correctif observer-entry H26](results/2026-08-11_harmonic-censoring-h26-runtime-observer-entry-order-correction-external-seal.md)
- [2026-08-11 — overlay correctif de l'ordre observer-entry H26](results/2026-08-11_harmonic-censoring-h26-runtime-observer-entry-order-correction-overlay.md)
- [2026-08-11 — correction du SHA documentaire R5 dans l'overlay H26](results/2026-08-11_harmonic-censoring-h26-runtime-observer-entry-order-overlay-sha-correction.md)
- [2026-08-11 — rejet des constantes non-JSON dans le loader runtime H26](results/2026-08-11_harmonic-censoring-h26-runtime-loader-non-json-constants-correction.md)
- [2026-08-11 — correction strict JSON du loader de materialisation H26](results/2026-08-11_harmonic-censoring-h26-materialization-loader-strict-json-correction.md)
- [2026-08-11 — correction strict JSON du loader scientifique H26](results/2026-08-11_harmonic-censoring-h26-scientific-loader-strict-json-correction.md)
- [2026-08-14 — contrat de création one-shot du leaf registry H27](results/2026-08-14_harmonic-censoring-h27-registry-leaf-creation-contract.md)
- [2026-08-14 — identity binding du contrat registry-leaf H27](results/2026-08-14_harmonic-censoring-h27-registry-leaf-contract-identity-binding.md)
- [2026-08-14 — runner dormant one-shot du leaf registry H27](results/2026-08-14_harmonic-censoring-h27-registry-leaf-one-shot-creator.md)
- [2026-08-14 — exécution terminale du creator registry-leaf H27](results/2026-08-14_harmonic-censoring-h27-registry-leaf-terminal-execution.md)
- [2026-08-14 — contrat du fichier registry H27 initialement vide](results/2026-08-14_harmonic-censoring-h27-empty-registry-file-creation-contract.md)
- [2026-08-14 — identity binding du contrat du fichier registry H27](results/2026-08-14_harmonic-censoring-h27-empty-registry-file-contract-identity-binding.md)
- [2026-08-14 — runner dormant one-shot du fichier registry H27](results/2026-08-14_harmonic-censoring-h27-empty-registry-file-one-shot-creator.md)
- [2026-08-10 — runner/provenance synthétique de l'évaluation V2 indépendante](results/2026-08-10_causal-candidate-v2-independent-validation-runner-implementation.md)
- [2026-08-10 — contrat d'exécution déclaratif de l'évaluation V2 indépendante](results/2026-08-10_causal-candidate-v2-independent-validation-execution-contract.md)
- [2026-08-10 — frontière d'exécution directe de l'évaluation V2 indépendante](results/2026-08-10_causal-candidate-v2-independent-validation-runner-contract-only.md)

Les rapports détaillés restent des preuves horodatées. Le présent fichier est
le seul résumé global et doit toujours refléter l’étape courante et la suite.
