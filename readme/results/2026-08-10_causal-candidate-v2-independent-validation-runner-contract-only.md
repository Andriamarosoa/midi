# Runner V2 indépendant — implémentation contract-only

Cette étape complète le shell fail-closed du runner prévu par le contrat
approuvé. Le runner expose les phases pures d'orchestration (préflight,
cohorte, evidence, artefacts, frontière scientifique lazy, A/B, rapport et
décision), puis refuse
toute exécution tant qu'une capability one-job séparée, factory-attestée et
liée au commit, au contrat, au CPU, au délai de 900 secondes et à l'identité
du job n'existe pas.

Aucune factory d'autorisation n'est fournie ici. Un dataclass construit à la
main, un appel à `main()`, un booléen, un chemin ou une variable d'environnement
ne peuvent donc pas ouvrir d'actif, charger TensorFlow ou produire une
métrique.

Vérifications contract-only : py_compile OK ; 28 tests ciblés OK ;
`git diff --check` OK. Mise à jour d'intégration : les hooks de production sont
construits dans le runner autour des APIs de cohorte et d'evidence déjà scellées,
mais restent inatteignables sans capability one-job. Le rapport hiérarchique
reference/candidate/delta est validé fail-closed lorsqu'il est fourni. Aucun audio, label, manifeste scientifique, registre,
modèle, checkpoint, TensorFlow, inférence, métrique, job Mac, fit, calibration,
export, live ou test verrouillé n'a été utilisé.

La prochaine étape reste soumise à une revue externe et à une autorisation
one-job distincte. Ce commit n'autorise aucune validation réelle.
