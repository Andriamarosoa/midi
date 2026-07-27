# Decision V6.3

V6.3 est conserve comme artefact de recherche et rejete comme gate live.

- AUC-PR validation extraite : 55,83 %.
- F1 evenementiel continu corrige : 38,48 % sur joueur 04, 36,26 % sur joueur 05.
- Aucun seuil parmi 302 ne satisfaisait simultanement les contraintes V6.0
  lorsque le reseau produisait aussi les retriggers de meme MIDI.
- Les rapports suffixes `_corrected` sont les seuls rapports evenementiels
  valides ; voir `METRIC_CORRECTION.md`.

V6.0 reste la reference.
