# H27 Review 5A — corrections après revue stricte

## Verdict reçu

La première chaîne Review 5A a reçu `FAIL` avant activation. Aucune exécution
scientifique réelle n'a été tentée. Les corrections de ce lot restent locales,
synthétiques et non consommantes.

## Corrections

- Le moteur valide le schéma fermé d'un `H27SealedRecordBinding` slotté sans
  `vars()`. Un test traverse maintenant le vrai loader, le vrai moteur et le
  recomputer indépendant sur des octets synthétiques locaux.
- Une activation Review 5B séparée doit lier l'implémentation, l'identity
  binding, l'external seal, l'index exact, les deux runtimes, l'execution ID,
  le nonce et l'issuer. Elle est vérifiée avant le claim.
- La capability ne peut être issue que depuis une preuve process-local créée
  après publication `O_EXCL`, réouverture `O_NOFOLLOW` et comparaison canonique
  du claim durable. Le runtime secondaire répète la vérification de la même
  activation et du même claim.
- Le répertoire vide est préparé et fsync avant la frontière irréversible. Le
  claim reste l'unique consommation; un répertoire exactement vide n'est pas
  considéré comme consommé.
- Les dix identifiants inverses déclarés possèdent une couverture exacte. Les
  corruptions positive, négative, collision, causalité et recomputation sont
  rejetées, et les quatre variantes zéro sont reliées aux fixtures dédiées.
  P1 contrôle désormais certificat, complétude, rôles, seuils, bornes, marges,
  raison causale et borne maximale de lecture.
- Chaque test terminé publie un reçu create-exclusive ordonné et chaîné au SHA
  précédent. Un premier FAIL arrête la séquence et aucun reçu ultérieur n'est
  produit.
- Le terminal est publié puis lié par un marker `COMPLETE.json` séparé. Un
  terminal sans marker valide reste inconclusif et n'est jamais écrasé.

## Validation locale

- `12` tests Review 5 ciblés : PASS.
- `py_compile` : PASS.
- `git diff --check` : PASS.
- Aucun Mac/SSH, claim réel, P0/P1/P2 réel, locked-test, entraînement,
  calibration ou checkpoint.

## État

Le lot attend une nouvelle chaîne implementation → identity binding → external
seal puis une nouvelle revue externe. Toute activation réelle reste interdite.
