# H27 — contrat de destination de publication réelle

Le commit `4c8d56d844e7c21623af1cc381b61d0c56136477` est revu `PASS`.
Cette étape fixe uniquement la destination future canonique :

`/Users/amcarene/h27-admin/activation/h27-materialization-v1.json`

Le chemin est unique et immuable mais n'est ni créé ni accédé. Création,
écriture, overwrite et replace restent non autorisés. Le contrat lie les quatre
artefacts de la frontière dormante et développe les 56 upstream en 60 identités
uniques, toutes rehashées par blob Git, taille et SHA-256.

Le graphe reste acyclique sans self-hash/back-reference; huit edges restent
fermés. Connexions, authority, materializer, science, locked-test, training et
calibration restent faux. Aucun calcul réel n'est exécuté.

Tests administratifs, suite H27, py_compile et diff-check sont requis avant le
commit. STOP après publication Git pour revue externe.
