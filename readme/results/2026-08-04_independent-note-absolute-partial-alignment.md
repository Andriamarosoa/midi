# Contrat de labels : alignement absolu des partiels

## Hypothèse

La classe active est un MIDI entier, tandis que le CSV harmonique est ancré à
l'annotation JAMS potentiellement fractionnaire. `note_fundamental_offset_cents`
relie ces deux repères; `note_harmonic_offset_cents` relie ensuite l'harmonique
annoté à sa fréquence mesurée. Les deux termes sont complémentaires.

## Correctif limité

Une première interprétation a temporairement supprimé le premier terme. La
revue l'a rejetée avant tout smoke. Le contrat final le restaure avec des noms
explicites : `annotation_offset_from_rounded_midi_cents` et
`partial_residual_from_annotated_harmonic_cents`. `note_id` continue de lier
chaque fondamental à ses propres partiels et une note annotée simultanée reste
positive, prioritaire sur toute cible négative.

Ce changement ne reconstruit aucune donnée et ne modifie pas le JSON de
validation précédent. Il ne réentraîne pas de modèle et ne sélectionne aucun
seuil.

## Vérification locale

- Compilation Python réussie.
- 24 tests ciblés réussis : cibles indépendantes, données polyphoniques et
  sidecar de décalage.
- Le test de contrat vérifie une annotation à +40 cents par rapport à la classe
  MIDI entière et un H2 à +30 cents par rapport à l'annotation : la cible est
  la classe supérieure, à +70 cents du H2 de la classe entière.

## Suite autorisée

Faire relire le contrat. Après revue seulement : smoke borné sur le Mac,
validation-only, sans entraînement complet, export, live ni test verrouillé.
