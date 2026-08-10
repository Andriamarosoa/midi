# H19 — Conformité synthétique de l’exposition `frame_fallback`

## Verdict

`provisional_resolution_frame_fallback_h19_synthetic_conformance_demonstrated`

H19 démontre uniquement, sur données synthétiques, que le signal catégoriel
préenregistré par H17 peut être capturé passivement et évalué conformément au
contrat. La population fraîche H18a de 146 prises / 51 groupes reste intacte.

## Instrumentation passive

Le décodeur n’est pas modifié. Son blob reste :

```text
27026d368081fadc4fa282954428f0377020e723
```

Chaque `PolyphonicMidiEvent` immuable porte déjà `reason` au moment exact où
le `NoteOn` est émis. Le collecteur H19 observe uniquement la séquence
retournée et restitue les mêmes objets dans le même ordre. Les tests comparent
événements et état interne complet entre deux décodeurs identiques, avant et
après observation.

Taxonomie primaire exacte :

```text
frame_fallback                              F = 1
model_onset/frame_attack/chord_completion   F = 0
legacy/retrigger                            exclus, mais comptés
autre raison                                échec fermé
```

## Target causal inchangé

L’adaptateur synthétique appelle directement
`extract_exact_causal_age1_targets()`. Il ne définit aucun nouveau matching :
même pitch, causal, one-to-one, aucune référence future, maximum 250 ms. Pour
les lignes éligibles et matchables seulement :

```text
false_noteon = 1 - true_noteon
```

Les lignes invalides ou hors audio restent exclues, sans conversion en faux
NoteOn.

## Métrique et bootstrap

La fonction pure calcule exactement :

```text
RD_false = P(false_noteon=1 | F=1) - P(false_noteon=1 | F=0)
```

Le bootstrap tire exactement 10 000 fois `G` groupes avec remise depuis
l’univers immuable fourni. Les groupes sans ligne éligible restent dans cet
univers et contribuent zéro ligne lorsqu’ils sont tirés. Le générateur est
`numpy.random.Generator(numpy.random.PCG64(721629268))`; les percentiles 2,5 et
97,5 utilisent `method="linear"`; au moins 9 500 réplications valides sont
requises.

Le verdict synthétique positif exige simultanément : 200 lignes éligibles,
50 `frame_fallback`, 50 comparateurs, `RD_false >= 0,10` et borne basse
strictement positive. Les sorties secondaires ne peuvent pas modifier ce
verdict.

## Vérifications

```text
8 tests H19 synthétiques réussis en 3,047 s
48 tests H9/H10/H17/H18/H19 réussis en 12,559 s
py_compile réussi
git diff --check réussi
```

Les tests couvrent la neutralité événement/état, les six raisons connues,
l’échec sur raison inattendue ou identité dupliquée, la réutilisation du target
causal, l’exclusion descriptive de `legacy`/`retrigger`, la formule RD, les
seuils, le déterminisme, l’invariance d’ordre et les groupes vides.

## Provenance

```text
H17 accepté       3a3e65ab532a4983fadae89c842b544228c3b028
H18a accepté      3f9a15540d783c32486a9e0d50446efdb637ba60
audit H18a blob   c06459b5877526a515930561b15a5e9a08c3af31
audit H18a SHA    580ea2a77cd68798946c324d190082d5b960e5d1280fd93527b8ac47116fcff9
decoder blob      27026d368081fadc4fa282954428f0377020e723
```

## Interdictions maintenues

Aucun audio/label réel, checkpoint, TensorFlow, inférence, fréquence réelle de
raison, target réel, RD réel, bootstrap réel ou test verrouillé n’a été ouvert
ou calculé. H19 n’autorise pas automatiquement l’exécution scientifique H17.
La prochaine action est uniquement la revue externe de ce commit.
