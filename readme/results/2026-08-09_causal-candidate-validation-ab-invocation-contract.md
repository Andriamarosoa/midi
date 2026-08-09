# Contrat d'invocation A/B historique du filtre causal V1

Date : 2026-08-09
Portée : préparation opérationnelle uniquement, sans validation historique.

## Décision enregistrée

L'évaluateur A/B scellé approuvé au commit `463f93eba8434e05029d53dce14ec5b1c11e9960`
restait volontairement sans CLI. Cette étape ajoute le seul chemin d'invocation
possible, sans exécuter de job Mac. Une revue externe finale de cette invocation
reste obligatoire avant toute commande `start`.

## Chemin scellé

`src.polyphonic.run_causal_candidate_validation` n'accepte aucun argument et
n'expose aucun chemin, seuil, cohorte, configuration audio ou destination
contrôlable par l'appelant. Il construit les entrées suivantes depuis le
checkout Git du worker :

1. la policy A/B et la sélection historique de 12 prises ;
2. le `fit_report`, le modèle V1 et son standardiseur ;
3. le manifeste train/validation, le checkpoint de transcription, le YAML
   d'évaluation et le décodeur de référence ;
4. une destination unique sous `tmp/causal_candidate_validation_ab_v1_20260809`.

Le chemin du fit historique contient un caractère CR final. Ce caractère reste
une constante interne du module Python : il n'est jamais placé dans une
commande, un argument du worker ou le transport SSH. La destination A/B est
refusée si elle existe déjà.

Avant tout chargement Keras ou ouverture d'enregistrement, le runner vérifie
les huit SHA-256 préenregistrés : `fit_report`, modèle, standardiseur,
manifeste, sélection, checkpoint, YAML et décodeur de référence. Il exige aussi
`MIDI_FORCE_CPU=1`, masque les GPU TensorFlow et échoue si TensorFlow avait été
initialisé avant ce préflight.

## Contrat worker

`MAC_WORKER.ps1` n'autorise cette invocation que pour
`src.polyphonic.run_causal_candidate_validation`, avec :

- l'accusé dédié `DECODER_CANDIDATE_VALIDATION_EXECUTE=1` ;
- zéro argument de module ;
- `device=cpu` ;
- un timeout mur externe exactement égal à 900 secondes ;
- `ExpectedCommit` au format Git complet, identique au HEAD local demandé au
  worker.

Le préflight embarqué du worker vérifie ces quatre propriétés avant d'importer
TensorFlow. Seul le runner, après ses huit empreintes, peut ensuite importer
TensorFlow et lancer l'évaluation scellée. Les autres modules restent soumis à
leurs préflights historiques inchangés.

## Vérification locale sans calcul scientifique

Les contrôles réalisés dans le worktree Windows sont :

```text
py_compile : causal_candidate_validation.py,
             run_causal_candidate_validation.py et leurs trois modules de test
unittest  : 26 tests ciblés réussis en 9,606 s
parseurs  : PowerShell et Bash valides
```

Les tests couvrent notamment l'absence de l'accusé d'exécution, les chemins
internes, le caractère CR conservé uniquement dans le code, l'absence de CLI,
l'absence d'arguments libres, CPU/900 s, le commit exact et l'ordre du
préflight A/B avant TensorFlow. Aucun checkpoint réel, actif audio/label,
prise validation, inférence, entraînement, export, live ou test verrouillé n'a
été utilisé.

## Limites et prochaine action

Cette étape ne fournit aucune métrique musicale ni mesure de latence nouvelle :
elle ne modifie pas le décodeur décisionnel et n'exécute pas l'évaluation.
Après revue externe du commit qui la contient, la seule suite possible sera une
commande worker unique, CPU, avec le commit alors approuvé, suivie de la revue
du rapport A/B final. Toute validation historique, sélection, export, live et
test verrouillé restent interdits avant cette revue.
