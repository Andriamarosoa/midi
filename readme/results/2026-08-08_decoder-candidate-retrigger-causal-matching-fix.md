# Correctif causal des retriggers pour les labels candidats

## Portée

Cette correction répond à la revue du commit `a06e9641`. Elle ne lance aucun
minage, décodeur sur les données du projet, entraînement, validation officielle,
export, live ou test verrouillé. Les plans écrits par les tests restent
temporaires et synthétiques.

## Défaut corrigé

Le constructeur de labels envoyait auparavant au matcher causal uniquement les
NoteOn candidats entraînables. Un retrigger, explicitement exclu du fit faute de
décision pré-porte, ne consommait donc pas la même référence que dans le flux
réel du décodeur.

Exemple corrigé :

```text
référence MIDI 60 : 1,000 s
retrigger MIDI 60 : 1,100 s  (exclu du fit, mais réel)
candidat MIDI 60  : 1,200 s  (entraînable)
```

Le retrigger consomme la référence selon le matcher same-pitch, chronologique
et une-à-une. Le candidat ultérieur reçoit donc `causal_noteon_target=0`, au
lieu d'un faux positif de supervision. L'ordre inverse est aussi testé : si le
candidat est émis avant le retrigger, il conserve correctement la cible `1`.

## Contrat de matching maintenant appliqué

Le matcher reçoit une seule fois tous les NoteOn effectivement émis qui sont
valides dans le masque de labels et à l'intérieur de l'audio. Cela comprend les
retriggers et toute voie hors population de fit. Ensuite seulement, les
résultats sont projetés vers les candidats :

```text
tous les NoteOn valides du replay
  -> matcher causal same-pitch, une-à-une, 250 ms inclusifs
  -> consommation chronologique des références
  -> projection vers gate_eligible=True et emitted_noteon=True
```

Une frame invalide ou hors audio ne participe pas au matching et ne consomme
pas de référence : elle ne représente pas un événement supervisable fiable.
Les retriggers restent absents des features et des lignes de fit, mais leurs
matches sont explicitement comptés.

Les compteurs séparent désormais :

- `causal_matchable_decoder_noteons` : tous les NoteOn valides fournis au
  matcher ;
- `causal_false_decoder_noteons` : leurs prédictions sans référence causale ;
- `matched_reference_noteons` : références consommées par le flux complet ;
- `matched_reference_noteons_excluded_from_fit` : ces matches complets qui
  appartiennent à un retrigger ou à une autre voie non entraînable.

Les invariants imposent notamment :

```text
matchables = matches complets + faux NoteOn complets
matches complets = positifs de fit + matches exclus du fit
références = matches complets + références manquées
```

## Durcissement associé du plan persistant

La vérification interne a aussi fermé un raccourci d'API : une capacité
collecteur ne peut plus être créée à partir d'un plan uniquement en mémoire.
La validation snapshot exige maintenant un
`PersistedDecoderCandidatePartitionPlan` attesté, écrit puis relu depuis ses
octets canoniques. Le collecteur revérifie ces octets au moment du `drain()` ;
une modification ou suppression du plan pendant un futur replay refuse le lot
avant qu'il ne puisse devenir un artefact.

## Vérifications locales

La suite ciblée inclut les deux cas retrigger/candidat same-pitch, le cas
retrigger invalide, le refus d'un plan RAM ou d'un wrapper forgé, et le refus
d'un `drain()` après modification du JSON de plan. La vérification Windows a
exécuté `py_compile`, `git diff --check` et la même suite ciblée complète que
le rapport précédent : **131 tests réussis en 8,993 s**.

```text
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest \
  tests.test_decoder_candidate_snapshot_protocol \
  tests.test_decoder_candidate_labels \
  tests.test_decoder_candidate_provenance \
  tests.test_decoder_candidate_mining \
  tests.test_decoder_candidate_instrumentation \
  tests.test_polyphonic_decoder \
  tests.test_polyphonic_desktop_contract \
  tests.test_product_decoder \
  tests.test_polyphonic_validate_live_input_level \
  tests.test_ollama_team \
  tests.test_mac_worker_transport_contract \
  tests.test_polyphonic_smoke_neural_independent_note
```

Les mentions antérieures de `128` tests en `7,438 s` dans le rapport précédent
et de `7.421 s` dans le message de commit correspondent à deux exécutions
successives de la même suite avant cette correction. Elles ne sont pas une
différence de résultat scientifique.

`locked_test_used=false`. Aucun résultat antérieur, checkpoint ou seuil n'est
promu.

## Action suivante

Faire relire ce correctif. Après approbation explicite seulement, la prochaine
étape reste la préinscription du plan réel et des empreintes des actifs
audio/labels, suivie d'une revue distincte avant toute première collecte
train-only.
