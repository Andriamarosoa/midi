# H24 — bridge NumPy opérationnel dormant

Date : `2026-08-10`

## Autorisation

La revue externe a approuvé le seal et le contrat d'activation au commit
`5864cc35bef31dab8d99b710bd5250d3180c0b7e`, puis a autorisé uniquement :

```text
AUTHORIZED_TO_IMPLEMENT_H24_DORMANT_OPERATIONAL_NUMPY_BRIDGE_ONLY
```

Aucun OS-binding, claim, marker, import NumPy réel, waveform ou population
n'est autorisé par cette étape.

## Bridge implémenté

L'entrée publique conserve un unique argument capability. Son ordre fermé est :

```text
capability durablement claimed
→ revalidation du commit d'activation distinct
→ worktree propre et HEAD exact
→ rehash contrat + seal
→ blob materializer revu égal aux octets courants
→ runtime exact vérifié sans importer NumPy
→ importlib.import_module("numpy")
→ nom numpy et version 1.26.4 exacts
→ corps privé de matérialisation déjà revu
```

Toute erreur post-claim avant l'entrée dans le corps privé conserve la
consommation et tente d'écrire le terminal
`H24_POPULATION_MATERIALIZATION_INCONCLUSIVE_CONSUMED`. Le corps privé conserve
sa propre gestion terminale pour les erreurs pendant la matérialisation.

## Dormance opérationnelle

Le seal actuellement présent lie encore le materializer approuvé
`101103e63420de3703c045142291a9f231373f77` et son blob
`16210df0830eb62cc32f6900af51ad3d9e4972e5`.

Le bridge modifie le blob source courant. Le zero-science preflight exige que
le blob courant soit exactement celui nommé par le seal : aucune capability ne
peut donc être émise avec le seal actuel, même si quelqu'un tente de lier ce
commit par variable d'environnement.

Une activation future devra être un commit distinct, explicitement revu, qui
rafraîchit le seal pour lier le commit et le blob exacts de ce bridge avant tout
OS-binding. Sans cette transition, le chemin reste inexécutable.

## Tests sans science

Les tests utilisent uniquement mocks et inspection :

- le seal actuel ne correspond pas au nouveau blob source ;
- un échec de binding précède tout import NumPy ;
- l'ordre dynamique est claim → binding → import exact → corps privé ;
- une version NumPy autre que 1.26.4 est refusée avant matérialisation ;
- toute erreur post-claim appelle la mécanique terminale négative ;
- aucun NumPy réel n'est importé par le test du bridge.

P0/P1/P2, données réelles, H17, locked-test, training et preuve scientifique
restent interdits.

```text
170 tests H24/H23/H20 réussis en 2,202 s
py_compile réussi
git diff --check réussi
```

La prochaine action est uniquement la revue externe de ce bridge dormant.
