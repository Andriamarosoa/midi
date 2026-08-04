# Hypothèse préenregistrée — porte note indépendante au décodeur

## Question

La tête entraînée avec l'alignement harmonique restauré peut-elle diminuer les faux NoteOn réellement produits par le décodeur, sans dégrader les vraies notes ni ajouter de latence de NoteOn ?

Le smoke train-only a démontré l'exécution technique et la cohérence de sauvegarde, mais pas cet effet final. Le seul seuil candidat de cette hypothèse est donc fixé **avant** la validation : `independent_note_threshold=0,01`. Il vient de la calibration interne train-only ; il n'est ni sélectionné ni optimisé sur validation.

## Expérience unique proposée

Une seule évaluation CPU, validation-only, sur les 12 enregistrements canoniques déjà utilisés par le diagnostic d'événements : mêmes WAV, mêmes références, même checkpoint de transcription, mêmes seuils frame/onset/offset, même décodeur causal et même ordre des prises.

Deux décodages seront produits à partir des mêmes prédictions de la tête :

1. **Référence** : porte `independent_note` désactivée.
2. **Candidat** : seule différence, porte active avec seuil gelé `0,01`.

Le modèle de tête est celui du smoke borné, SHA-256 `d4d2101ff6f7f4da9cee4eb9ee6b24e5c347cc0493039a1618a6d02e730a0adc`. Le checkpoint de transcription de base reste `1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325`.

## Mesures et décision

Mesures primaires, globales et par corpus : faux NoteOn, faux NoteOn/min, faux positifs à intervalle harmonique, erreurs d'octave, précision, rappel et F1 onset, notes manquantes, retriggers et fragmentation. Les graves MIDI 40–51 sont rapportés séparément. La latence causale est mesurée ; la porte ne doit ajouter aucun hop au NoteOn.

La variante n'est retenue comme candidat de recherche que si elle réduit les faux NoteOn et les faux positifs harmoniques sans régression matérielle de rappel ou F1 onset, sans dégradation sur un corpus, sans aggravation des erreurs d'octave graves et sans latence de NoteOn supplémentaire. Sinon elle est rejetée ; aucun seuil alternatif n'est essayé dans cette passe.

## Garde-fous

- Split officiel : validation uniquement ; `locked_test_used=false` obligatoire.
- CPU forcé, un seul job lourd, pas de nouvelle optimisation ni entraînement.
- Aucun export, live, sélection finale ou test verrouillé.
- Le rapport doit inclure commandes, SHA-256 des checkpoints/configurations, résultats A/B par prise et par corpus, ainsi que l'intégrité Keras/ZIP.

Cette hypothèse doit être revue avant son exécution. Elle permet de mesurer le comportement événementiel réel, sans transformer la calibration train-only en promotion automatique.
