# Résultat — entraînement polyphonique multi-source

> Date : 2026-07-22
> Statut : entraînement terminé, qualité événementielle encore insuffisante
> Révision entraînée : `ada1f8ec06e1956f4ddbea804a0403b4357d70a8`

## Périmètre

- Python 3.9.13, TensorFlow 2.15.1, NumPy 1.26.4.
- Fenêtre causale : 4096 échantillons.
- Hop : 256 échantillons à 44,1 kHz.
- Sorties : `frame`, `onset`, amplitude harmonique et décalage harmonique.
- Sources : GuitarSet, GAPS et Guitar-TECHS direct/micro.
- Huit époques, 240 000 exemples échantillonnés par époque.
- Validation : 60 000 exemples, puis 12 enregistrements continus répartis
  également entre les quatre corpus.

## Résultats

L’époque 8 est la meilleure des huit pour les métriques calibrées :

| Mesure validation | Résultat |
|---|---:|
| F1 frame calibré | 0,5381 |
| F1 onset par frame calibré | 0,1038 |
| F1 onset par notes, pondéré par corpus | 0,2294 |
| F1 onset par notes, global | 0,1535 |
| F1 onset + offset, global | 0,0463 |
| Notes de référence sur les 12 fichiers | 3 639 |
| Notes estimées avant garde anti-fantômes | 8 333 |
| Notes appariées | 919 |

Le checkpoint retenu est `epoch-08.keras`. Le jeu de test est resté verrouillé
pendant le classement et la sélection.

## Analyse

- Le modèle apprend correctement la présence polyphonique par frame.
- Le passage des probabilités aux événements MIDI reste le principal point
  faible : trop de notes fantômes, offsets imprécis et fragmentation.
- Les performances Guitar-TECHS sont nettement inférieures à GuitarSet et
  GAPS ; une moyenne globale seule masquerait cette faiblesse.
- Aucun poids monophonique n’a été transféré pour cet entraînement.

## Preuves

- `runs/polyphonic/polyphonic_v2_2_guitarset_gaps_guitar_techs_20260722_024644/history.csv`
- `runs/polyphonic/polyphonic_v2_2_guitarset_gaps_guitar_techs_20260722_024644/checkpoint_ranking.json`
- `runs/polyphonic/polyphonic_v2_2_guitarset_gaps_guitar_techs_20260722_024644/selection.json`
- `runs/polyphonic/polyphonic_v2_2_guitarset_gaps_guitar_techs_20260722_024644/runtime.json`
