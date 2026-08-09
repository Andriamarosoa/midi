# H4 — isolation synthétique de l'état provisoire du décodeur

## Portée autorisée

Ce commit teste uniquement une architecture causale synthétique, opt-in et
injectable. Il ne définit pas la politique réelle qui déciderait
`HOLD/CONFIRM/REJECT` et n'utilise aucun audio, label, manifeste, checkpoint,
TensorFlow, modèle V1/V2, fit, calibration, validation ou test verrouillé.

## Architecture testée

Le décodeur distingue maintenant, seulement lorsqu'un resolver H4 est fourni :

```text
emitted_active     = NoteOn MIDI réellement émis et non encore terminé
provisional_active = sous-ensemble émis encore non confirmé
contextual_active  = emitted_active sans provisional_active
```

Le protocole MIDI reste honnête : une note provisoire a réellement produit un
`NoteOn`. Elle peut donc être tenue, confirmée sans second `NoteOn`, rejetée par
un `NoteOff`, ou préemptée par un `NoteOff` juste avant un nouveau `NoteOn`.
Le masque `contextual_active` est utilisé pour le support harmonique et le
budget de sélection. Le masque `emitted_active` reste utilisé pour garantir que
le nombre de notes MIDI tenues ne dépasse jamais `maximum_polyphony`.

## Reproduction exacte des deux mécanismes H3

### A — slot de polyphonie préemptible

Configuration : MIDI `60–61`, polyphonie maximale `1`.

```text
t0 A : aucun événement
t0 B : NoteOn 60 (provisoire)

t1 entrées A == entrées B
A : NoteOn 61
B : NoteOff 60 reason=provisional_preempt
    NoteOn 61 dans la même frame
```

Le candidat suivant n'est pas utilisé comme backfill : MIDI 61 est déjà le
candidat sélectionné par le budget contextuel. La préemption restaure ensuite
le budget MIDI émis avant son `NoteOn`. À aucun instant de sortie le maximum de
polyphonie n'est dépassé.

### B — base harmonique provisoire exclue

Configuration : MIDI `60–72`, polyphonie maximale `2`, H2 de MIDI 60.

```text
t0 A : aucun événement
t0 B : NoteOn 60 (provisoire)

t1 harmonic_support(72) : A=0.0, B=0.0
t1 A : NoteOn 72
t1 B : NoteOn 72

t2 B : REJECT 60
        NoteOff 60 reason=provisional_reject
```

Le faux MIDI 60 ne contamine donc plus le calcul harmonique futur. Le rejet
nettoie `active`, `provisional_active`, les compteurs d'activation/release,
`attack_activation_pending` et la grâce d'accord, sans couper MIDI 72.

## Confirmation et parité désactivée

Un test séparé confirme MIDI 60 après son premier `NoteOn`. Aucun second
`NoteOn` n'est émis; la note quitte seulement `provisional_active` et entre dans
`contextual_active`, où elle peut ensuite servir de base harmonique.

Sans resolver, `contextual_active` est exactement le masque historique
`active`. Les suites existantes couvrent les chemins legacy, audio-aware,
instrumentation et porte V2. La transition de release naturelle conserve
explicitement sa sémantique historique; seul le bit H4 additionnel est effacé.

## Verdict

```text
provisional_state_isolation_architecture_demonstrated
```

Ce verdict valide l'architecture de séparation et les transitions synthétiques,
pas une politique de confirmation réelle. La prochaine étape doit s'arrêter à
la définition/revue d'une politique causale de résolution; elle ne peut pas
charger les artefacts V1/V2 ni lancer un calcul réel sans autorisation séparée.
