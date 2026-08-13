# H27 — contrat scellé de future activation de matérialisation

## Portée

Après le verdict externe `PASS` sur `43d160bc`, ce lot reste strictement
contractuel. Il définit et scelle la future activation one-shot qui serait
nécessaire pour matérialiser `H27_SYNTHETIC_V1`. Il n'ajoute aucun issuer,
loader, authority, capability, claim, activation, population, index ou runner.

Le contrat est acyclique : son seal externe lie ses octets exacts, mais le
contrat ne contient ni le SHA du seal ni un futur commit d'activation.

## Bindings fermés

Le contrat lie le materializer dormant existant, les cinq blobs H27 revus, le
contrat engine/recomputer qui porte le profil runtime primaire, puis recopie
exactement CPython 3.11.9, Darwin arm64, NumPy 1.26.4, OpenBLAS ILP64 et les dix
variables d'environnement mono-thread/CPU/locale.

La future activation est limitée à une émission, sous la racine
`/Users/amcarene/h27-admin`, avec commit d'activation égal au HEAD propre,
acknowledgement littéral et publication create-exclusive/fsync. Elle n'est pas
elle-même une capability scientifique.

La future authority doit lier contrat, seal, activation, runtime, materializer,
inputs et destination. Le claim durable `O_EXCL` précède NumPy ou la première
allocation scientifique et reste consommé après succès, erreur, interruption
ou timeout. Aucun retry n'est permis.

## Publication et index

Le staging et la destination finale sont fixes et absents. Les payloads doivent
être écrits et rehachés avant `population_index.json`, lui-même écrit en dernier
dans le staging. L'arbre est ensuite revalidé contre l'index avant un rename
atomique no-replace et un fsync du parent. Un staging partiel n'est jamais
autoritatif.

L'index futur contient exactement 124 records dans l'ordre canonique : 17
baseline et 107 P2. Chaque ligne ferme identité, répertoire, topologie et SHA
payload, pitches, coordonnées causales et `cents/B`. La future création d'un
`H27SealedRecordBinding` ne peut recevoir que `record_identity` comme sélecteur;
tous les autres champs doivent provenir d'une unique ligne vérifiée de l'index
dont le SHA est lié à l'authority. Le loader n'existe pas dans ce lot et les
gardes engine/recomputer restent inconditionnels.

## État et interdictions

Le contract et son seal existent. Tous les autres états restent faux : aucune
activation, authority, capability, claim, matérialisation, population, index,
lecture payload, FFT, NNLS, engine/recomputer, P0/P1/P2, locked-test,
entraînement ou calibration.

## Vérification

Les tests sont uniquement structurels : strict JSON LF, SHA/blob bindings,
profil runtime exact, one-shot, publication atomique, états faux et dérivation
exclusive du binding depuis l'index futur. Ils ne chargent aucun actif H27 et
n'appellent aucun kernel scientifique. `py_compile`, `git diff --check` et
`26/26` tests H27 contractuels/dormants passent en `2,293 s`.

## STOP

`H27_MATERIALIZATION_ACTIVATION_CONTRACT_SEALED_PENDING_EXTERNAL_REVIEW_NO_ACTIVATION_NO_EXECUTION`

La prochaine action est uniquement la revue externe du contrat et du seal.
