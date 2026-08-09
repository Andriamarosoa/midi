# Implémentation synthétique de la porte causale V2

Date : 2026-08-09

Portée : implémentation du décodeur et tests unitaires synthétiques seulement.
Aucun actif audio/label projet, checkpoint de transcription, modèle V1,
standardiseur V1, fit, calibration, recherche de seuil, validation historique,
export, live ou test verrouillé n'a été ouvert ou exécuté.

## Changement minimal

`PolyphonicDecoder` accepte désormais deux placements explicites de la porte
causale :

```text
pre_ranking                 # défaut V1, comportement existant
post_ranking_pre_noteon     # V2
```

Le défaut reste `pre_ranking`; V1 ne change donc pas. V2 fige un
`CausalCandidateGateInput` compatible V1 après les mises à jour causales
pré-ranking, mais avant ranking/sélection. Elle applique ensuite la même porte
uniquement aux candidats déjà sélectionnés par `maximum_polyphony`.

Dans le chemin audio-aware comme dans le chemin legacy, toutes les décisions
V2 des candidats sélectionnés sont terminées avant toute mutation liée à
l'émission. Les candidats acceptés seulement deviennent actifs et émettent un
`NoteOn`. Dans le chemin audio-aware, `protected_chord` est calculé après ces
décisions, uniquement à partir des candidats acceptés.

## Sémantique de rejet vérifiée

Un rejet V2 synthétique :

- n'émet aucun `NoteOn` et ne crée pas de note active persistante ;
- ne remet pas à zéro `activation_count` ni `attack_activation_pending` : ils
  restent dans l'état produit par la phase pré-ranking de ce hop ;
- conserve sa position déjà consommée dans la sélection du hop ; aucun
  reranking/backfill ne promeut un candidat suivant dans le même hop ;
- ne contribue pas à `protected_chord` ;
- ne modifie pas le chemin des retriggers, qui reste hors population V2.

Le snapshot passe explicitement les huit valeurs brutes V1 et exclut toujours
rang, sélection, émission, cible, provenance, futur et état post-mutation.

## Preuves synthétiques

Le nouveau module `tests/test_causal_candidate_v2.py` vérifie :

1. le refus fail-closed d'un placement inconnu ;
2. la parité stricte événements/état avec V2 désactivée, dans les chemins
   audio-aware et legacy ;
3. la conservation du placement V1 pré-ranking par défaut ;
4. dans le chemin audio-aware, ranking/selection avant porte, deux appels de
   porte pour deux candidats sélectionnés sur trois classés, conservation de
   l'évidence du rejet, absence de backfill et absence de protection d'accord
   indue ;
5. les mêmes invariants de sélection/rejet dans le chemin legacy.
6. la conservation d'un snapshot `frame_attack` et de son score/support V1
   lorsqu'un candidat devient ensuite `harmonic_strong_frame` pendant les
   contrôles précédant le ranking.

Les commandes locales suivantes passent sans ouvrir d'actif projet :

```text
python -m py_compile src/polyphonic/decoder.py tests/test_causal_candidate_v2.py
python -B -m unittest tests.test_causal_candidate_v2 \
  tests.test_causal_candidate_validation \
  tests.test_decoder_candidate_instrumentation \
  tests.test_polyphonic_events
# 46 tests, 0,422 s

python -B -m unittest tests.test_decoder_candidate_mining \
  tests.test_decoder_candidate_labels \
  tests.test_decoder_candidate_snapshot_protocol
# 30 tests, 0,769 s
```

`git diff --check` est propre. Aucun test ne charge les artefacts V1 ou des
enregistrements de validation. Les imports de runtime présents dans certains
tests restent ceux de l'environnement local ; aucun modèle Keras n'est chargé.

## Latence et limite

V2 n'ajoute ni lookahead, ni buffer, ni hop de décision. Cette affirmation est
une propriété du chemin de contrôle synthétique ; aucune mesure de latence
réelle ou live n'a été faite, et aucune ne l'est autorisée par ce commit.

## Étape suivante bloquée

Une revue externe du code et de ces preuves synthétiques est obligatoire avant
tout accès aux artefacts V1 ou tout calcul réel. La validation historique des
12 prises reste interdite, et `locked_test_used=false` demeure obligatoire.
