# Correctif CR du worker et préinscription A/B historique du filtre causal V1

## Statut

Terminé sans calcul scientifique. Ce document enregistre le correctif du
transport SSH qui avait ajouté un retour-chariot au nom du dossier de sortie du
fit V1 et la seule hypothèse A/B historique qui pourra être étudiée après
revue. Aucun artefact V1 existant n'a été renommé, copié, rejoué ou modifié.
Cette étape ne lance ni fit, ni inférence, ni validation, ni export, ni live,
ni test verrouillé.

## Correction du transport

Le lancement direct par SSH avait laissé le `\r` de la terminaison PowerShell
dans le dernier argument `--output-dir`. Le correctif est volontairement
restreint :

- `MAC_WORKER.ps1` expose `-CausalCandidateFitExecute`; il l'accepte seulement
  pour `src.polyphonic.run_causal_candidate_fit` et transmet le seul littéral
  d'environnement autorisé, `DECODER_CANDIDATE_FIT_EXECUTE=1`;
- la commande est fournie à SSH sur stdin par `Invoke-Ssh`, qui ajoute une
  ligne commentaire distincte après la commande : le CRLF PowerShell ne peut
  donc plus devenir une partie du dernier argument;
- `scripts/remote/mac_worker.sh start` refuse tout argument qui contient un
  retour-chariot avant résolution Git, import TensorFlow, ouverture d'actif ou
  écriture de sortie.

Le test de régression exécute le worker shell avec un CR dans son dernier
argument et exige l'échec `2` avant lancement. Un second test verrouille le
chemin PowerShell et le caractère module-spécifique de l'accusé.

Le dossier Mac portant le CR final reste une anomalie historique de nom de
chemin. Les identités scientifiques du fit sont les SHA-256, pas ce chemin :

| Artefact | SHA-256 |
| --- | --- |
| Modèle Keras V1 | `b9320cd004ed686720e282e4338c4a6413c2ef3dd701d421de3533f710d8a59e` |
| Standardiseur V1 | `0600aa1aa75eb008f04e299de3ffe9d7b6b0a722b177750b42e0967740df5e3b` |
| Rapport de fit | `b8148fade0d72c6d20d64f31fbaf9983b748997ba16f5664c525bcc41ae9b759` |

## Hypothèse A/B préenregistrée

Les fichiers canoniques, normalisés LF par `.gitattributes`, sont :

| Fichier | SHA-256 |
| --- | --- |
| `configs/causal_candidate_fit_v1_validation_selection_12.json` | `8c3cf53c7f5dcf086b70767e28499c3164aa307059652a6d0a2fc87159f9dcbc` |
| `configs/causal_candidate_fit_v1_validation_ab_policy.json` | `53e8e26839ce7eadee0e4437ab1446c6a15370396862b09d9cf8964067e3029a` |

La cohorte est le split historique `validation`, exactement douze prises
fixées par identité `dataset|source|capture|audio_member`, sous le manifeste
`b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7`.
Elle conserve quatre corpus : GAPS, Guitar-TECHS direct, Guitar-TECHS mic et
GuitarSet. `locked_test_used=false` est inscrit dans les deux fichiers.

La référence applique le décodeur scellé historique sans porte causale. Le
candidat utilise **seulement** le modèle et standardiseur V1 listés ci-dessus,
avec le seuil interne train-only gelé à `0,31`. Le candidat ne peut voir que
les douze valeurs pré-porte gelées; il doit réutiliser les mêmes candidats
pré-porte et la même inférence de transcription que la référence.

L'évaluation future devra réaliser une seule inférence de transcription par
prise, puis deux décodages sur les mêmes prédictions :

```text
prédiction de transcription, une fois
├── référence : aucune porte causale V1
└── candidat : modèle V1 + standardiseur V1 + seuil 0,31
```

Elle rapportera les métriques globales, par corpus et par prise : onset,
onset+offset, NoteOn strictement causal, retriggers, diagnostics, MIDI 40–51
et deltas A/B appariés. Les SHA du modèle, standardiseur, rapport de fit,
manifeste, sélection, checkpoint, YAML et décodeur de référence seront
reproduits dans le rapport terminal.

## Règles décisionnelles fixées avant résultats

Le candidat ne sera considéré positivement que si **toutes** ces contraintes
passent sur les mêmes douze prises :

| Mesure candidat – référence | Limite |
| --- | --- |
| Faux NoteOn | au moins `-1` |
| Rappel onset global | au moins `-0,005` |
| F1 onset global | au moins `-0,002` |
| Rappel NoteOn strictement causal global | au moins `-0,005` |
| F1 onset de chaque corpus | au moins `-0,010` |
| F1 onset MIDI 40–51 | au moins `-0,010` |
| Retriggers | au plus `0` |
| Fragments excédentaires | au plus `0` |

Un verdict positif ne promeut pas automatiquement le modèle ni le seuil. Les
actions explicitement interdites restent : fit, recalibration, recherche de
seuil, export, live et test verrouillé.

## Vérifications locales

```text
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest \
  tests.test_mac_worker_transport_contract \
  tests.test_causal_candidate_validation_preregistration \
  tests.test_causal_candidate_fit \
  tests.test_run_causal_candidate_fit

Ran 36 tests in 14.587s — OK
```

`py_compile` des quatre modules de test et `bash -n` du worker ont également
réussi. `git diff --check` est vide. La mini-époque Keras visible dans la sortie
de `test_run_causal_candidate_fit` est une fixture synthétique existante; elle
n'ouvre aucun actif projet et ne constitue ni fit réel ni validation.

La prochaine action autorisée est uniquement la revue de ce commit. Une fois
approuvé, le lecteur/évaluateur A/B scellé pourra être implémenté sans
exécution; une nouvelle revue explicite restera nécessaire avant toute passe
CPU historique.
