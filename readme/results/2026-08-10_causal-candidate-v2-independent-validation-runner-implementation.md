# Implémentation synthétique — runner/provenance de validation V2 indépendante

## Portée et statut

Cette implémentation est purement synthétique et reste en attente de revue
externe. Elle n'a pas ouvert d'audio, de labels, de checkpoint, de modèle,
d'asset evidence validation ou de runner Mac. Elle ne possède aucune CLI et ne
peut donc pas démarrer une passe CPU.

Le module ajouté est
`src/polyphonic/run_causal_candidate_v2_independent_validation.py`. Son unique
rôle actuel est de vérifier les JSON scellés et de reconstruire la cohorte à
partir des métadonnées du manifeste complet avant tout futur accès à un actif.
Il expose également l'enveloppe d'identité d'un futur registre validation :
SHA du protocole, SHA du manifeste, SHA ordonné des 30 clés et les deux types
d'actifs `audio`/`labels`. Cette enveloppe ne construit, ne lit et ne hache
aucun actif.

## Dérivation de cohorte fail-closed

Le préflight pur :

1. rehache le contrat V2 et la sélection historique V1 de 12 prises ;
2. lit le manifeste complet depuis les mêmes octets que son SHA-256, sans
   charger ses chemins audio ou labels ;
3. refuse toute ligne `test`, toute clé historique absente ou non-validation,
   tout doublon de clé canonique et toute divergence de SHA ;
4. applique `leakage_group_key()` — la règle corpus-aware réellement utilisée
   par Policy A — pour exclure toutes les fuites historiques ;
5. recalcule les 10 groupes GAPS et 10 groupes Guitar-TECHS par SHA-256 avec
   graine `47`, puis compare la liste ainsi dérivée aux 30 clés explicitement
   gelées dans le protocole ;
6. dérive aussi la population Policy A éligible depuis le manifeste complet et
   refuse toute intersection avec un groupe sélectionné.

La correction de ce commit aligne la règle GAPS sur les clés canoniques du
code (`gaps:player:<identifiant normalisé>`), plutôt que sur l'orthographe brute
des noms du CSV. Les dix clés GAPS gelées sont donc désormais exactement celles
que la dérivation future reproduira.

La cohorte contient 30 fichiers mais seulement 20 unités de fuite : 10 groupes
GAPS et 10 groupes physiques Guitar-TECHS, chacun vu en direct et mic/amp. Le
rapport futur devra toujours afficher les deux nombres. L'indépendance
Guitar-TECHS reste limitée au `group_id` préenregistré du projet, et ne prétend
pas prouver une indépendance de musicien, d'instrument ou de session.

## Intervention et décision mécanique

Le préflight contrôle que l'intervention demeure gelée : modèle V1,
standardiseur, 12 features, seuil `0,31`, checkpoint, politique audio,
décodeur référence et placement `post_ranking_pre_noteon`.

`evaluate_independent_v2_decision()` est une fonction sans I/O qui transforme
un futur rapport A/B déjà produit en décision mécanique. Elle exige les trois
corpus autorisés, refuse GuitarSet, les sections absentes et les valeurs non
finies. Elle applique les seuils préenregistrés : réduction causale globale
d'au moins 1 %, aucune hausse causale par corpus, limites de rappel/F1,
fragmentation et p50/p90. Une valeur manquante, un NaN ou une base de faux
NoteOn nulle échoue ; une réussite demeure
`positive_independent_evidence_non_promotional`, jamais une promotion.

## Vérifications effectuées

- `py_compile` du module ;
- 7 tests unitaires synthétiques : sélection de 30 prises / 20 groupes,
  refus du test verrouillé, refus d'une liste JSON non re-dérivable,
  rehash du protocole et de la sélection historique, import sans TensorFlow ni
  CLI, décision mécanique et non-finitude ;
- 47 tests ciblés V2/provenance au total, dont les 7 nouveaux ;
- préflight de métadonnées réel, sans audio ni label : le manifeste SHA
  `b28cb17…` redérive bien `30` prises et `20` groupes (`10/10/10`).

## Suite strictement interdite en attente de revue

La suite autorisée est seulement une revue de cette implémentation. Il reste
interdit de créer ou lire un registre d'actifs validation, de charger le modèle
V1, d'ouvrir audio ou labels, de faire une inférence, un fit, une calibration,
une passe Mac, un export, du live ou tout test verrouillé. Une étape distincte
devra d'abord sceller une preuve d'octets pour les seuls actifs validation
sélectionnés, puis être revue avant toute évaluation CPU.
