# H27 Review 5A — corrections après revue stricte

## Verdicts reçus

La première chaîne Review 5A a reçu `FAIL` avant activation. Aucune exécution
scientifique réelle n'a été tentée. Les corrections de ce lot restent locales,
synthétiques et non consommantes.

La chaîne de remplacement V2 a ensuite reçu un second `FAIL`, limité à quatre
écarts. Le correctif courant les ferme sans activation ni accès scientifique.

## Corrections

- Le moteur valide le schéma fermé d'un `H27SealedRecordBinding` slotté sans
  `vars()`. Un test traverse maintenant le vrai loader, le vrai moteur et le
  recomputer indépendant sur des octets synthétiques locaux.
- Une activation Review 5B séparée doit lier l'implémentation, l'identity
  binding, l'external seal, l'index exact, les deux runtimes, l'execution ID,
  le nonce et l'issuer. Elle est vérifiée avant le claim.
- Le contrat Review 5A reste désormais exclusivement dormant avec ses trois
  autorisations à `false`. Il n'existe plus de variante mutée autorisée : seule
  l'activation 5B vérifiée peut franchir le preflight, avant l'ACK et la création
  du répertoire de sortie.
- Le preflight relit le binding et le seal via `git show` depuis leurs commits
  déclarés, exige l'égalité byte-for-byte avec le checkout et vérifie le tuple
  Git blob/taille/SHA du binding inscrit dans le seal.
- La capability ne peut être issue que depuis une preuve process-local créée
  après publication `O_EXCL`, réouverture `O_NOFOLLOW` et comparaison canonique
  du claim durable. Le runtime secondaire répète la vérification de la même
  activation et du même claim.
- La preuve durable impose maintenant le schéma fermé du claim ainsi que
  l'égalité exacte `activation_sha256`, `execution_id` et `activation_nonce`.
  Le runtime secondaire fournit lui aussi ces trois valeurs vérifiées avant
  l'émission de sa capability process-local.
- Le répertoire vide est préparé et fsync avant la frontière irréversible. Le
  claim reste l'unique consommation; un répertoire exactement vide n'est pas
  considéré comme consommé.
- Les dix identifiants inverses déclarés possèdent une couverture exacte. Les
  corruptions sont maintenant instanciées une par une : retrait séparé de
  l'exclusivité/onset/résiduel; bound manquant/absence-only/target-derived/
  caller-supplied; égalité fréquence/amplitude/octets; endpoint futur/padding;
  les 12 catégories interdites et tous leurs alias; schéma recomputer avec
  champ oracle réellement ajouté. Les quatre variantes zéro utilisent une
  vraie mutation `2^-80` et les primitives de classification/spectre du moteur.
  P1 contrôle en outre rôles et masques fixture par fixture et réconcilie une
  fois exactement les 17 fixtures de P1-001 à P1-008.
- Chaque test terminé publie un reçu create-exclusive ordonné et chaîné au SHA
  précédent. Un premier FAIL arrête la séquence et aucun reçu ultérieur n'est
  produit.
- Le terminal est publié puis lié par un marker `COMPLETE.json` séparé. Un
  terminal sans marker valide reste inconclusif et n'est jamais écrasé.

## Validation locale

- `14` tests Review 5 ciblés : PASS.
- Suite complète Review 5 + moteur/recomputer + binding/seal : `27/27` PASS.
- `py_compile` : PASS.
- `git diff --check` : PASS.
- Aucun Mac/SSH, claim réel, P0/P1/P2 réel, locked-test, entraînement,
  calibration ou checkpoint.

## État

La chaîne V3 est complète : implementation `5ea555312f521afbe3f1c17bf38d163233bc3652`,
identity binding `576ba120c898ab8757cc22b0c7410dc02f7b11bc`, puis external
seal dans le commit courant. Elle attend une nouvelle revue externe. Toute
activation réelle reste interdite.
