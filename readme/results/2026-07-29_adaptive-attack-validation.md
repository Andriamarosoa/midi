# Validation de l’attaque causale adaptative — 2026-07-29

## Périmètre

Cette ablation modifie un seul mécanisme du bundle desktop stable : les
statistiques causales de croissance RMS et de flux spectral apprennent
désormais sur les trames réarmées qui ont été rejetées comme attaque robuste.
Le plancher RMS, le modèle TFLite, les poids, les seuils MIDI et le décodeur
restent inchangés.

L’expérience utilise exclusivement la validation. Les 12 enregistrements sont
les mêmes 12 groupes équilibrés que lors de la sélection Kaggle : trois GAPS,
trois Guitar-TECHS direct, trois Guitar-TECHS micro et trois GuitarSet. Le test
verrouillé n’a pas été ouvert.

## Correction de l’audit WAV

Le premier WAV Guitar-TECHS de l’audit précédent avait été construit depuis
un tableau `int16` sans normalisation avant l’écriture PCM. Il contenait
99,94 % d’échantillons écrêtés, avec un RMS de 0,9997. Le tableau source est
valide : amplitude comprise entre -9616 et 9477, sans écrêtage.

Le WAV a été reconstruit après division par 32768 :

- minimum : -0,1800 ;
- maximum : 0,2283 ;
- RMS : 0,0310 ;
- échantillons écrêtés : 0 %.

Cette erreur concernait uniquement le script temporaire de création du WAV
d’écoute. Le train, `PolyphonicSequence`, les masques d’évidence audio et la
sélection validation-only normalisent déjà les sources entières.

## Attaques physiques sur les deux extraits déterministes

### Guitar-TECHS direct, 30 s

- F1 attaque : 0,2642 → 0,3000 ;
- attaques émises : 24 → 11 ;
- attaques appariées : 7 → 6 ;
- fausses attaques : 17 → 5.

### GuitarSet, 22,32 s

- F1 attaque : 0,5469 → 0,7835 ;
- attaques émises : 77 → 46 ;
- attaques appariées : 35 → 38 ;
- fausses attaques : 42 → 8.

L’adaptation supprime donc surtout les fluctuations de sustain prises pour de
nouvelles attaques.

## MIDI sur les deux extraits

Sur Guitar-TECHS :

- F1 onset : 0,0882 → 0,1111 ;
- faux positifs : 33 → 19 ;
- notes manquantes : 29 → 29 ;
- F1 onset+offset : 0,0294 → 0,0370.

Sur GuitarSet :

- F1 onset : 0,2966 → 0,4000 ;
- faux positifs : 74 → 49 ;
- notes manquantes : 92 → 83 ;
- F1 onset+offset : 0,2542 → 0,3182 ;
- références fragmentées : 2 → 1.

## Validation complète sur les 12 enregistrements

Métriques globales :

- NoteOn estimés : 3805 → 2833 ;
- faux positifs événementiels : 3160 → 2314 ;
- notes manquantes : 2994 → 3120 ;
- F1 onset global : 0,1733 → 0,1604 ;
- F1 onset+offset global : 0,0551 → 0,0581 ;
- F1 onset pondéré par corpus : 0,2332 → 0,2409 ;
- F1 onset+offset pondéré : 0,1276 → 0,1356.

Par corpus, F1 onset :

- GAPS : 0,2124 → 0,1824 ;
- Guitar-TECHS direct : 0,0398 → 0,0459 ;
- Guitar-TECHS micro : 0,0530 → 0,0550 ;
- GuitarSet : 0,3338 → 0,3721.

Mesure strictement causale :

- faux NoteOn : 2118 → 1389, soit -34,4 % ;
- faux NoteOn/min : 71,44 → 46,85 ;
- précision : 0,4434 → 0,5097 ;
- rappel à 250 ms : 0,4636 → 0,3968 ;
- erreurs d’octave : 444 → 310, soit -30,2 % ;
- latence NoteOn p50 : 65,63 → 71,14 ms ;
- latence NoteOn p90 : 164,74 → 156,69 ms.

La hausse du p50 événementiel reflète les appariements conservés après
suppression de candidats ; ce n’est pas un délai algorithmique ajouté.

## Coût live

Le mécanisme n’ajoute ni lookahead, ni vote, ni fenêtre supplémentaire. Il
réutilise les valeurs RMS/flux déjà calculées dans le même hop.

- Guitar-TECHS : pipeline p95 3,30 ms ;
- GuitarSet : pipeline p95 4,17 ms ;
- budget du hop : 5,80 ms.

Le changement reste donc compatible avec le live sur la machine mesurée.

## Décision

Le candidat réduit fortement les notes fantômes et les erreurs d’octave, et
améliore Guitar-TECHS ainsi que GuitarSet. Il n’est cependant pas promu par
défaut, car la baisse GAPS et la perte de rappel causal sont matérielles.

Un bundle opt-in est installé dans
`artifacts/guitar_midi_polyphonic_adaptive_attack_candidate`. La prochaine
étape est un test live A/B à niveau et périphérique identiques. Le bundle
stable `artifacts/guitar_midi_polyphonic_v2_2_0` reste inchangé.
