# Contrat de labels : alignement absolu des partiels

## Hypothèse

`note_harmonic_offset_cents` est calculé depuis la fréquence mesurée du partiel
vers sa fréquence théorique (`fondamentale annotée × numéro harmonique`). Il
porte donc déjà le décalage de la fondamentale et celui du partiel. L'ancien
constructeur de cible ajoutait en plus `note_fundamental_offset_cents`, ce qui
pouvait déplacer deux fois la classe MIDI négative lorsqu'un décalage
fondamental non nul était fourni.

## Correctif limité

La cible `harmonic_only` emploie désormais uniquement le décalage harmonique
absolu pour convertir le partiel mesuré en classe MIDI. `note_id` continue de
lier chaque fondamental à ses propres partiels et une note annotée simultanée
reste positive, prioritaire sur toute cible négative.

Ce changement ne reconstruit aucune donnée et ne modifie pas le JSON de
validation précédent. Il ne réentraîne pas de modèle et ne sélectionne aucun
seuil.

## Vérification locale

- Compilation Python réussie.
- 24 tests ciblés réussis : cibles indépendantes, données polyphoniques et
  sidecar de décalage.
- Le nouveau test vérifie un fondamental à +40 cents et un partiel absolu à
  +30 cents : la cible reste la classe du second harmonique, au lieu d'être
  déplacée artificiellement d'un demi-ton par l'addition des deux valeurs.

## Suite autorisée

Faire relire le contrat. Après revue seulement : smoke borné sur le Mac,
validation-only, sans entraînement complet, export, live ni test verrouillé.
