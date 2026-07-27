# Résultat — validation du décodeur desktop polyphonique

> Date : 2026-07-27
> Statut : runtime fonctionnel, transcription musicale à améliorer
> Test verrouillé utilisé pour régler le décodeur : non

## Changement évalué

Le runtime applique un seuil `0,90` aux activations `frame` dépourvues
d’attaque physique récente. Une attaque audio récente ou un onset spécifique
au pitch conserve le chemin normal. Les poids du modèle n’ont pas changé.

## Résultats sur 12 enregistrements de validation

| Mesure | Avant | Après |
|---|---:|---:|
| Précision onset | 0,1102 | 0,1743 |
| Rappel onset | 0,2525 | 0,1759 |
| F1 onset global | 0,1535 | 0,1751 |
| Fausses notes supprimées | — | 4 387 |
| Faux intervalles harmoniques supprimés | — | 328 |
| Notes vraies appariées perdues | — | 279 |
| Fragments excédentaires supprimés | — | 495 |

Le compromis réduit fortement les notes fantômes et les harmoniques parasites,
mais manque davantage de vraies notes, notamment dans les accords denses.

## Runtime

| Mesure | Résultat |
|---|---:|
| TFLite float16 batch 1, p95 | 2,17 ms |
| Configuration recommandée | 3 threads |
| TFLite 3 threads, p95 inter-session | 2,60 ms |
| Budget d’un hop | 5,80 ms |
| Budget respecté | oui |

La latence d’inférence est donc compatible avec le live. Elle ne comprend pas
la latence matérielle complète entrée/sortie.

## Limites observées

- Le rendu est plus propre, mais trop parcimonieux.
- Abaisser le seuil de secours ajoute surtout des notes fantômes et récupère
  très peu de notes correctement appariées.
- La cause principale des notes manquantes se situe donc avant ou en dehors de
  ce seuil : détection d’attaque, domaine micro, sorties du modèle ou stratégie
  de décodage.
- Une chanson sans annotation fournit un audit spectral utile, mais ne permet
  pas de mesurer seule la justesse musicale.

## Preuves

- `artifacts/guitar_midi_polyphonic_v2_2_0/decoder_acceptance.json`
- `artifacts/guitar_midi_polyphonic_v2_2_0/latency_report.json`
- `artifacts/guitar_midi_polyphonic_v2_2_0/validation_decoder_unattacked_threshold.json`
- `artifacts/guitar_midi_polyphonic_v2_2_0/validation_runtime_events_fp16.json`
