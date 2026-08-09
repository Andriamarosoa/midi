# H6 — conformance synthétique à la frontière d'observation H5

## Verdict

```text
provisional_resolution_h5_synthetic_conformance_demonstrated
```

Ce verdict porte uniquement sur l'architecture synthétique. Il ne valide ni un
resolver, ni un signal, ni une politique, ni une performance, ni une V3.

## Frontière exacte

Le resolver reçoit exclusivement une dataclass `ProvisionalObservation`
immuable avec les 15 champs H5, dans cet ordre :

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

La frame d'émission et les quatre preuves candidat `*_at_noteon` sont stockées
lors du `NoteOn` et ne varient plus. Les probabilités `current_*`, l'audio, le support
harmonique et les polyphonies proviennent uniquement de la frame courante.
`age_frames` vaut exactement `current_frame - note_on_frame`.

`audio_onset_available` signifie qu'une observation audio-onset a été fournie
pour le hop courant (`audio_onset is not None`). Il ne reprend pas le latch
historique `decoder.audio_onset_available`. Le test causal distingue les deux :
après une onset disponible à `t0`, une frame `t1` sans observation expose
`false`, puis `t2` avec `audio_onset=false` expose `true`; le lookback causal
peut alors encore indiquer `audio_onset_recent=true`.

## Atomicité multi-notes

Pour chaque frame, H6 suit deux phases :

```text
Phase A
  copier contextual_active pré-résolution
  construire toutes les observations
  valider leur schéma et leurs nombres finis
  appeler le resolver pour toutes les notes
  valider toutes les décisions

frontière atomique

Phase B
  appliquer CONFIRM/REJECT
  produire les NoteOff de rejet
  continuer la frame historique
```

Dans le succès synthétique multi-notes, MIDI 60 reçoit `CONFIRM` et MIDI 64
reçoit `REJECT`. Les deux observations voient la même polyphonie pré-résolution
`emitted=2`, `contextual=0`; MIDI 60 devient contextuel sans second `NoteOn` et
MIDI 64 produit exactement un `NoteOff provisional_reject`.

Dans le test de résultat invalide, la première décision est valide et la
seconde vaut `INVALID`. L'appel échoue, mais les deux notes restent actives et
provisoires, sans confirmation, rejet, cleanup ni événement de résolution.

Dans le test d'exception, le resolver réussit pour MIDI 60 puis lève sur MIDI
64. Le même invariant atomique est conservé : aucune mutation ou émission
partielle.

Une probabilité courante `NaN` fait échouer la validation de l'observation avant
le premier appel au resolver; l'état provisoire reste inchangé. Le même garde
de finitude couvre `+inf` et `-inf`.

## Isolation intra-frame et composition

Quand MIDI 60 et MIDI 72 sont provisoires et que MIDI 60 reçoit `CONFIRM`, le
support H2 déjà construit pour MIDI 72 reste `0.0`, car il provient du snapshot
`contextual_active` antérieur à toute résolution. Les deux observations voient
aussi les mêmes compteurs de polyphonie. Après commit atomique seulement, MIDI
60 devient contextuel et son support H2 normal vaut `1.0`.

Le constructeur refuse avant toute frame :

```text
H6 resolver + causal candidate gate V1/V2
H6 resolver + independent_note_threshold
H6 resolver + les deux mécanismes
```

avec `unsupported_pending_separate_contract`. Aucune adaptation des anciennes
portes n'est effectuée.

`PREEMPT` reste extérieur au resolver. Les tests H4 conservent l'ordre
`NoteOff provisional_preempt` puis `NoteOn` de remplacement dans la même frame,
sans dépassement de `maximum_polyphony`. Les scénarios H3/H4, `CONFIRM` sans
second `NoteOn`, `REJECT` avec cleanup et le chemin sans H4 restent couverts.

## Vérification et limites

```text
py_compile : réussi
tests ciblés : 98 réussis en 0,297 s
git diff --check : réussi
```

Aucun dataset, manifeste, audio, label, TensorFlow, checkpoint, modèle,
inférence, fit, calibration, tuning, cohorte V2, validation, export, live ou
test verrouillé n'a été ouvert. Les seuils, l'âge maximal, la population de
production et la politique runtime d'erreur restent non définis. La prochaine
étape nécessite une nouvelle revue avant même de formuler un signal réel.
