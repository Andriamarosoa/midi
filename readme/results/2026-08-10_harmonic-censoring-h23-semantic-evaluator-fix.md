# H23 — correction dormante des producteurs sémantiques

## Origine

La revue externe de `6e016783826ea8e72150920f19b3f5e8b3b4a21b` a validé
l'architecture 72/72, le recomputer pur, l'égalité JSON typée et le refus des
booléens auto-certifiés. Elle n'a toutefois pas autorisé le passage au TOCTOU :
plusieurs `_measure_<ID>` produisaient encore une conclusion attendue au lieu
d'exécuter leur `exact_input`, leur procédure et leur inverse.

Cette étape est le correctif dormant limité aux evaluators autorisé par cette
revue. Elle ne touche ni au seal, ni à l'activation, ni au claim de production.

## Expériences corrigées

- `D04` synthétise réellement deux spectres au même pitch, applique les six
  masques et compare les courbes raw/normalisées/null/résiduelles à une
  référence scalaire indépendante.
- `D08` rejoue les six offsets hop par hop depuis `INACTIVE` et persiste toutes
  les transitions, ensuite recomputées depuis les offsets.
- `C02` rejoue quatre translations absolues et normalise seulement le trace
  après exécution ; `C04` dérive décision, retrigger et cardinalité de l'énergie
  des fenêtres observées.
- `F03/F04` exécutent NNLS, permutations, tie handling et stress partagé.
- `K01/K02` construisent les six cas depuis les sources des fixtures et dérivent
  séparément cardinalité latente, cardinalité émettable et identifiabilité des
  sources.
- `G01..G08` exploitent les sources, trajectoires pitch, énergies de fenêtres,
  enveloppes, naissance causale et hypothèses harmoniques ; ils ne sérialisent
  plus des catégories répétées écrites à l'avance.
- `O01/O02` classent réellement silence, quasi-silence, OOD et pile harmonique
  depuis RMS et résidus de factorisation.
- `P01/P02/P05` instrumentent réellement l'encodage partagé, les formes et les
  composantes de latence.
- `P04` construit le stream causal de `10 336` hops, chronomètre chaque fenêtre,
  calcule backlog et drain, puis exécute séparément le stress à douze cutoffs.
- `TS01` exécute les `175` fixtures sur les grilles 6, 16 et 32, et persiste les
  ensembles exacts passés, échoués, sauvés et régressés. Le recomputer vérifie
  leur partition et leur couverture du manifeste.
- Les inverses citées par la revue (`A02`, `A05`, `D12`, `F03`, `P04`) sont
  maintenant des transformations ou exécutions observées.

`I01` réutilise le même oracle local par fixture au lieu de déclarer zéro échec.
Les décisions sont dérivées sans consulter `expected_target`.

## Validation sans science

La suite contractuelle H23/H20 contient maintenant `76 tests`. Elle vérifie
notamment, par inspection statique, que les evaluators sémantiques appellent les
primitives scientifiques prescrites. Elle n'appelle aucun evaluator : aucune
waveform, aucun P0/P1/P2 et aucune population ne sont consommés pendant cette
validation administrative.

```text
76 tests réussis
py_compile réussi
git diff --check réussi
```

## État

```text
nouveau seal / activation       absent
claim / marker production       absent
waveform scientifique exécutée  non
P0 / P1 / P2 exécuté            non
population H17 / donnée réelle  non
modèle / checkpoint             non
locked-test                     non
```

Étape suivante : revue externe de ce correctif sémantique. Le durcissement
TOCTOU reste interdit jusqu'à son approbation, puis restera un commit dormant
séparé avant toute discussion d'un nouveau seal.
