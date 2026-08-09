# Fit causal candidat V1 — passe CPU train-only unique

## Verdict opérationnel

Le seul fit V1 autorisé a été lancé par le worker lourd Mac partagé et s'est
terminé avec `exit_code=0`. Il a produit un modèle, un standardiseur et un
rapport cohérents, mais n'autorise aucune étape ultérieure : ni validation
historique, ni export, ni live, ni test verrouillé. Une revue externe des
résultats est obligatoire.

Une anomalie de chemin est conservée telle quelle : le dossier de sortie créé
par ce lancement porte un caractère retour-chariot final (`U+000D`). Elle vient
du transport SSH direct de cette invocation unique, qui a transmis le dernier
argument avec une terminaison CRLF. Les trois artefacts eux-mêmes ont été
rehachés et le `.keras` a passé `unzip -t`; ils ne sont ni renommés ni recréés,
et aucun second fit n'est lancé. Toute décision sur une éventuelle normalisation
du chemin est reportée à la revue, sans modifier les octets de ce run.

## Exécution vérifiée

| Élément | Valeur |
| --- | --- |
| Job Mac | `causal-candidate-fit-v1-cpu-20260809` |
| Commit exécuté | `578a9d6583b2e5a68a312bd8dccf8e19a77b58b7` |
| Appareil | CPU forcé par le worker |
| Limite murale externe | `900 s` |
| Début / fin worker | `2026-08-09T21:07:06Z` / `2026-08-09T21:07:10Z` |
| Sortie worker | `0` — `exited_zero` |
| Statut interne | `complete_non_authorizing` |
| Époques demandées / enregistrées | `40` / `14` |
| Meilleure époque dev | `9` |
| Durée `Model.fit` | `0,188137334 s` |
| Test verrouillé / validation historique | `false` / `false` |

Le préflight, avant TensorFlow dans le runner, a confirmé le commit propre,
l'absence de verrou, une destination inexistante et les trois empreintes V3 :

- candidats `fd852626f56b038837266b5336b318c8adf841c1aafbd01d36b362f7fe10150d` ;
- rapport de minage `e13a13be38710e7a15f9d6d222d0a7835aad204a1b7c821d8198d1ac9ccffe59` ;
- protocole V3 `db55930a9faadc12fb7b08e52e0baac3543e3d5cb654844ea93e0d727a563683`.

Le seul stderr est l'avertissement générique Keras sur l'optimiseur Adam pour
M1/M2 ; le job est CPU sur M4 et aucun traceback ou échec n'est présent.

## Intégrité des artefacts Mac

| Fichier | SHA-256 | Contrôle |
| --- | --- | --- |
| `fit_report.json` | `b8148fade0d72c6d20d64f31fbaf9983b748997ba16f5664c525bcc41ae9b759` | JSON relu et contrat vérifié |
| `causal_candidate_fit_v1.keras` | `b9320cd004ed686720e282e4338c4a6413c2ef3dd701d421de3533f710d8a59e` | archive Keras : `unzip -t` réussi ; parité sauvegarde/rechargement `0,0` |
| `fit_standardizer.json` | `0600aa1aa75eb008f04e299de3ffe9d7b6b0a722b177750b42e0967740df5e3b` | lié au SHA du modèle et des candidats |

Les artefacts bruts restent sur le Mac et hors Git afin de ne pas versionner un
modèle généré. Le chemin brut est celui indiqué par le job, avec son suffixe
CR anormal, et non une copie recréée.

## Résultats train-only

La BCE dev minimale est obtenue à l'époque 9 :

- BCE dev pondérée : `0,640682169798129` ;
- Brier dev pondéré : `0,22471514998571712` ;
- AUC dev : GAPS `0,6119666209533043`, Guitar-TECHS pairé
  `0,7635533726365937`, GuitarSet `0,6542207792207789`.

La grille interne calibration trouve un seuil `0,31`, avec Brier pondéré
`0,23039975629334675`, rappel brut global `0,9894736842105263` et retrait
pondéré des faux NoteOn `0,0735288915290895`. C'est une mesure entièrement
issue du train-only ; elle ne sélectionne pas un seuil de produit et ne justifie
aucune validation A/B. Les 14 lignes `training_history`, les 18 cellules de
`weight_evidence` et les trois partitions V3 sont présentes dans le JSON.

Les comptes restent conformes au corpus V3 scellé : fit `694/244` (0/1), dev
`968/250`, calibration `793/190`, soit 3 139 candidats. Après restauration des
meilleurs poids, l'inférence de la petite tête seule sur ces 3 139 candidats
prend `0,001280834010685794 s`, soit `0,40803886928505706 µs` par candidat.
Cette mesure n'est pas une latence de transcription live : elle exclut l'audio,
le backbone, le décodeur et les E/S.

## Limites et prochaine porte

Le résultat démontre que le contrat de fit peut s'exécuter, mais il ne démontre
pas un bénéfice musical ni une réduction des faux NoteOn sur validation. Le
chemin de sortie CR est une anomalie de transport à décider explicitement. La
seule prochaine action autorisée est la revue externe de ce rapport et des
artefacts; aucun nouveau fit, recalibrage, validation historique, export, live
ou test verrouillé ne doit être lancé.

