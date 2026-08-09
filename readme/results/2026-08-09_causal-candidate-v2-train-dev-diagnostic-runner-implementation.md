# Runner V2 scellé — diagnostic exploratoire train/dev

Date : 2026-08-09

Portée : implémentation et tests synthétiques uniquement. Aucun runner n'a été
exécuté, et cette modification n'ouvre ni modèle V1 réel, checkpoint, manifeste
réel, plan persistant, registre d'actifs, audio ni labels. Aucun fit,
calibration, recherche de seuil, validation historique, export, live ou test
verrouillé n'a été effectué.

## Runner ajouté

`src/polyphonic/run_causal_candidate_v2_train_dev_diagnostic.py` est un module
sans CLI et sans chemin, cohorte, poids, seuil ou placement fournis par
l'appelant. Une exécution future exigera l'accusé explicite
`DECODER_CANDIDATE_V2_DIAGNOSTIC_EXECUTE=1`, le worker Mac CPU, un worktree
propre et un répertoire de sortie inédit. Sa durée externe prévue est bornée à
`900` secondes ; elle sera imposée par le worker, pas par un appel direct au
module.

Avant TensorFlow, modèle ou actif, le runner :

1. vérifie les octets du protocole V2 au chemin versionné et son SHA-256 LF ;
2. vérifie les sept entrées V3, le rapport/standardiseur/modèle V1 et le lien
   standardiseur → modèle ;
3. recharge le plan Policy A et le registre d'actifs canoniques sans importer
   la pile `data`/TensorFlow ;
4. relit le manifeste en Python pur, réconcilie le plan et le registre, puis
   dérive les `30` identités V3 de partition `dev` (`6/6/6/12`) ;
5. refuse toute identité non `train`, toute répétition ou tout écart de quota.

Après l'isolation CPU de TensorFlow, le contexte complet est relu avec les
objets exacts du snapshot et la vérification des actifs. La sélection obtenue
doit être identique, dans le même ordre, aux trente identités du préflight pur
avant le chargement de la tête V1.

La branche de référence n'a pas de porte. La branche candidate utilise
obligatoirement le modèle/standardiseur V1 et le seuil `0,31` au placement
`post_ranking_pre_noteon`. La configuration audio alternative est absente ; le
contexte ouvre les mêmes actifs attestés et les masques sont réutilisés par les
deux décodeurs. La passe future produit seulement le rapport A/B global, par
corpus et par prise, avec causalité (dont p50/p90), graves MIDI 40–51,
retriggers, diagnostics, compteurs de porte et deltas d'événements. Elle se
termine ensuite sans règle de promotion.

## Intégration de l'évaluateur

`evaluate_events()` accepte maintenant une voie strictement dédiée aux items
train-only scellés : les objets `ManifestItem` et le context manager de corpus
doivent être fournis ensemble. Cette voie refuse tout split autre que `train`,
tout override de corpus/dataset ou de sélection et ne relit pas un second
manifeste sans registre d'actifs. Les appels A/B existants restent
validation-only et inchangés lorsqu'ils n'emploient pas cette capacité.

Le registre d'actifs est également devenu chargeable sans import de
`data`/TensorFlow : seule sa construction effective importe localement les
types du corpus. Ainsi la vérification du registre persistant reste réellement
pré-TensorFlow.

## Vérifications synthétiques

Les tests ajoutés couvrent l'accusé d'exécution, les chemins exclusivement
internes, le suffixe CR historique des artefacts V1, l'import du runner sans
TensorFlow, la dérivation dynamique des trente captures V3 et le refus d'une
prise validation avant toute charge de modèle. Ils confirment aussi l'absence
de CLI, le placement V2 explicite et l'utilisation du context manager
attesté.

La compilation Python, `git diff --check`, `52` tests A/B/V2/événements en
`0,551 s` et `54` tests provenance/minage en `1,848 s` passent sous
`C:\Users\user\Desktop\midi\.venv\Scripts\python.exe`. Ces tests restent
synthetiques : aucun des chemins Mac scellés n'a été ouvert.

La revue externe suivante doit examiner le commit et les tests avant toute
commande Mac. Une telle revue pourra autoriser, au plus, une unique passe CPU
exploratoire sur les 30 prises train/dev ; elle ne pourra toujours pas
autoriser fit, calibration, réutilisation des 12 validations, export, live ou
test verrouillé.
