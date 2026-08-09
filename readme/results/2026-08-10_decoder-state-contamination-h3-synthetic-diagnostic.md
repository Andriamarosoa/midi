# H3 — diagnostic synthétique de contamination de l'état du décodeur

## Hypothèse

Un faux `NoteOn` accepté à `t0` peut modifier l'état persistant du décodeur et
provoquer une décision MIDI différente à `t1`, alors que toutes les entrées
acoustiques fournies aux deux décodeurs sont strictement identiques à partir de
`t1`.

## Construction synthétique

Deux instances A et B partent de la même configuration et du même état. À `t0`,
B reçoit seule une entrée normale qui émet un faux `NoteOn`; aucun champ interne
n'est muté directement. À partir de `t1`, les tableaux frame, onset, harmonique
et les indicateurs audio sont identiques pour A et B.

Deux mécanismes indépendants sont isolés :

1. **Budget de polyphonie.** Le faux MIDI 60 de B occupe l'unique slot actif.
   À `t1`, A émet MIDI 61 tandis que B ne peut pas le sélectionner.
2. **Support harmonique.** Le faux MIDI 60 de B devient la base active de H2.
   Pour le même candidat MIDI 72 à `t1`, le support vaut `0.0` dans A et `1.0`
   dans B. A émet le candidat `frame_attack`; B le supprime sous la règle
   harmonique existante.

## Première divergence et état responsable

La première divergence reproductible survient à la frame `t1` dans les deux
scénarios, immédiatement après la perturbation unique de `t0` :

```text
polyphonie : active_B[60] = true → available = 0 → MIDI 61 absent
harmonique : active_B[60] = true → harmonic_support(H2) = 1.0 → MIDI 72 absent
contrôle   : faux MIDI 60 absent → MIDI 61/MIDI 72 émis
```

Les divergences concernent les événements futurs, le masque `active` et
`last_note_on`; les compteurs de release restent cohérents avec l'état actif.
Le mécanisme causal exact est donc la persistance du faux pitch dans `active`,
qui alimente ensuite à la fois le budget de polyphonie et le masque de base du
calcul harmonique.

## Verdict

```text
state_contamination_demonstrated
```

Ce résultat démontre uniquement le mécanisme. Il n'évalue aucune correction et
n'autorise pas encore une V3, une quarantaine provisoire ou une correction
causale différée. Aucun audio réel, dataset, manifeste, TensorFlow, checkpoint,
modèle, métrique V2 ou test verrouillé n'a été utilisé.
