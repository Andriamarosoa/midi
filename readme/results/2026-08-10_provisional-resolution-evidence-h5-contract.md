# H5 — contrat causal des preuves de résolution provisoire

## Statut

```text
provisional_resolution_evidence_contract_defined
```

H5 n'est ni une hypothèse de performance, ni une politique de résolution, ni
une V3. Il définit seulement la frontière d'information d'un futur resolver
`HOLD/CONFIRM/REJECT`. Aucun seuil, durée maximale ou population de NoteOn
éligible n'est choisi.

Le contrat machine-readable est :
`configs/provisional_resolution_evidence_contract_h5.json`.

## Horloge causale

À `t0`, un `NoteOn` est émis puis marqué provisoire. À une frame ultérieure
`t`, les sorties réseau et l'évidence audio strictement disponibles à `t` sont
validées. Le décodeur construit ensuite une `ProvisionalObservation` immuable,
calcule et valide atomiquement toutes les décisions de cette frame, puis
applique `HOLD`, `CONFIRM` ou `REJECT` avant les releases, retriggers, candidats,
contexte harmonique, ranking ou nouveaux `NoteOn` de la même frame.

Aucune frame ou audio postérieur à `t` n'est accessible. Une confirmation
devient contextuelle immédiatement après ce point causal. Un rejet produit son
unique `NoteOff` avant tout futur `NoteOn` de la frame.

## Observations autorisées

Les champs fermés du snapshot sont :

```text
pitch
note_on_frame
current_frame
age_frames
candidate_reason_at_noteon
candidate_score_at_noteon
frame_probability_at_noteon
onset_probability_at_noteon
current_frame_probability
current_onset_probability
audio_onset_available
audio_onset_recent
harmonic_support
emitted_polyphony
contextual_polyphony
```

Les identités, raisons, scores et probabilités `*_at_noteon` sont gelés à
l'émission. Les valeurs `current_*`, l'audio, le support harmonique et les deux
polyphonies décrivent seulement la frame de résolution. Le support harmonique
est obligatoirement calculé depuis `contextual_active`, jamais depuis une note
encore provisoire.

## Sources rejetées

Labels, MIDI de référence, matching vérité, targets, frames/audio/sorties réseau
futurs, métriques postérieures, validation, cohorte V2 indépendante, accès à
l'objet décodeur, fichiers, réseau, modèle externe, état mutable caché et état
post-résolution sont tous interdits.

Le resolver reçoit exclusivement le snapshot immuable construit par le
décodeur. Il ne reçoit aucune capability lui permettant de contourner ce
schéma.

## Résolution, erreurs et composition

- `HOLD` n'émet rien et garde la note émise, provisoire et non contextuelle.
- `CONFIRM` n'émet pas de second `NoteOn`; la note devient contextuelle.
- `REJECT` émet exactement un `NoteOff` et nettoie tout contexte futur.
- `PREEMPT` reste distinct de `REJECT` et conserve l'ordre `NoteOff` puis
  remplacement `NoteOn` sans dépasser `maximum_polyphony`.

Une exception, décision invalide, valeur non finie ou champ absent invalide
atomiquement toute la résolution de la frame. Aucun fallback implicite vers
`HOLD`, événement partiel ou mutation partielle n'est autorisé. La stratégie de
sûreté runtime du caller reste à définir dans un contrat séparé.

Les combinaisons H4 + causal gate V1/V2 et H4 +
`independent_note_threshold` sont `unsupported_pending_separate_contract`.
Elles ne peuvent pas être activées silencieusement, notamment parce que les
sémantiques `emitted_polyphony` et `contextual_polyphony` diffèrent.

## Limite

La durée maximale, les seuils, la population de NoteOn et la stratégie runtime
d'erreur restent tous `null`/non résolus. La prochaine étape, après revue, peut
formuler une hypothèse sur un signal causal de confirmation. Elle ne peut pas
implémenter une politique ni charger de données sans une autorisation distincte.
