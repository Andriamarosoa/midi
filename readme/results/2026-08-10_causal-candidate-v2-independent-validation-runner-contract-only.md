# Runner V2 indépendant — implémentation contract-only

Cette étape complète la frontière d'exécution directe prévue par le contrat
approuvé. L'entrée publique exige d'abord une capability one-job attestée,
puis construit elle-même les chemins de production, le probe système et
l'adaptateur scientifique. Aucune injection de chemin, probe ou adaptateur
n'est exposée au futur appelant.

Aucune factory d'autorisation n'est fournie ici. Un dataclass construit à la
main, un appel à `main()`, un booléen, un chemin ou une variable d'environnement
ne peuvent donc pas ouvrir d'actif, charger TensorFlow ou produire une
métrique.

L'orchestrateur vérifie le HEAD et le worktree Git, le CPU et le délai de
`900 s`, l'absence de verrou/destination, le manifeste et la cohorte scellée,
le registre d'actifs et les six artefacts gelés avant tout import TensorFlow.
Il exige exactement `30` objets du snapshot (`10/10/10`, `20` groupes, aucun
GuitarSet), valide globalement les `30` audio et `30` labels avant la première
ouverture, puis réserve atomiquement le verrou et la destination. Chaque paire
audio/labels est ensuite rehachée immédiatement avant l'ouverture du même objet.

Le snapshot est chargé directement par `manifest_snapshot.py`, sans importer
le module TensorFlow-backed `data.py`. Après tous les gates et l'acquisition
du lease, `prepare_runtime_after_all_gates()` impose `MIDI_FORCE_CPU=1`, appelle
le configurateur CPU alors que TensorFlow est encore absent, puis seulement
importe `data`, `evaluate_events` et les helpers Keras. Le corpus de chaque
prise est fermé dans un `finally`, y compris si l'inférence, les masques, le
décodage ou l'accumulation échouent.

L'adaptateur réel charge paresseusement le checkpoint de transcription, la
tête V1 et son standardiseur. Pour chaque prise, il produit une seule
inférence et un seul jeu de masques audio, réutilisés par deux décodages à
états indépendants : référence sans porte et candidat V2 au seuil `0,31`, avec
les 12 features gelées et le placement `post_ranking_pre_noteon`. Aucun
backfill n'est ajouté. Les métriques sont agrégées globalement, par corpus,
prise et groupe de fuite, y compris MIDI `40–51`, causalité, retriggers,
fragmentation et diagnostics de porte.

La machine one-shot passe à `SCIENTIFIC_ASSET_OPENED` avant l'ouverture,
`INFERENCE_STARTED` avant l'inférence et `AB_METRIC_PRODUCED` immédiatement
après le premier décodage A/B, avant son accumulation. Toute erreur suivante
conserve donc la cohorte comme consommée. Le runner construit lui-même la
provenance depuis les objets réellement vérifiés, valide toute la hiérarchie,
appelle l'évaluateur canonique préenregistré, force
`automatic_promotion=false`, puis publie atomiquement le rapport terminal.
La future capability attestée est revendiquée atomiquement comme toute
première opération de l'entrée publique. Le claim n'est jamais annulé : une
seconde invocation du même objet échoue même si la première s'arrête avant le
lease. Aucune factory permettant de créer cette capability n'existe encore.

Vérifications sans données projet : `py_compile` OK ; `83` tests ciblés A/B,
contrat, provenance, preuve d'actifs et événements réussis en `8,288 s` ;
`git diff --check` OK. Les anciens hooks factices de phases ont été supprimés
au profit de tests du véritable orchestrateur avec probe/adaptateur synthétiques.
Aucun audio/label/manifest/registre de projet, modèle, checkpoint, inférence,
métrique réelle, job Mac, fit, calibration, export, live ou test verrouillé
n'a été utilisé. La suite élargie importe l'environnement TensorFlow installé
pour ses tests synthétiques existants, sans charger d'artefact scientifique.

La prochaine étape reste soumise à une revue externe et à une autorisation
one-job distincte. Ce commit n'autorise aucune validation réelle.
