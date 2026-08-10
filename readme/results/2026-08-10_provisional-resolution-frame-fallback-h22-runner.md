# H22 — Runner one-shot de la mesure réelle H17

## Statut avant exécution

`provisional_resolution_frame_fallback_h22_execution_contract_sealed`

L’utilisateur a explicitement autorisé l’implémentation puis l’unique mesure
réelle H17. H22 ajoute le runner sans arguments et son contrat d’exécution. Au
moment de ce commit, aucun marqueur n’est créé, aucune donnée scientifique
n’est ouverte et la population H21 reste non consommée.

## Frontière one-shot

Le runner vérifie avant toute science : worktree propre, blobs H17/H17a/H18a/
H19a/H20/H21, son propre blob, SHA brut H21, 146 identités/51 groupes exacts,
chaque taille/SHA audio et label, checkpoint/configurations et runtime Mac CPU.
Il refuse toute destination, claim, state, phase ou provenance d’échec déjà
existante.

Le marqueur canonique doit lier le SHA-256 brut du contrat H22 et le commit
d’exécution exact. Il est réclamé par `os.replace`. Le state
`fresh_population_consumed=true` est ensuite écrit atomiquement avant la
première construction de corpus ou désérialisation du checkpoint. Il n’existe
aucune boucle de retry.

## Science inchangée

Le runner utilise directement :

- le checkpoint `1ce8ac44…` et les configurations historiques scellées ;
- le décodeur au blob `27026d36…`, sans resolver ou porte causale ;
- la raison immuable portée par les NoteOn et la taxonomie H17a ;
- l’extracteur causal exact à `250 ms` ;
- le moteur H19 pour `RD_false`, 10 000 tirages par 51 groupes, seed
  `721629268`, percentiles linéaires et verdict préenregistré.

La publication finale est un renommage atomique d’un staging contenant les
lignes groupées, les dix compteurs d’attrition globaux et par prise, le rapport
métrique/verdict et la provenance. Une erreur après consommation ne publie
aucun résultat partiel autoritatif et interdit tout retry.

## Vérifications synthétiques

```text
33 tests H17a/H19a/H20/H21/H22 réussis
py_compile réussi
git diff --check réussi
aucun actif réel ouvert par les tests
locked_test_used=false
```

Les tests démontrent notamment que l’état de consommation existe avant le
premier appel de l’adapter scientifique et qu’une erreur post-consommation est
persistée sans deuxième tentative.

## H22a — scellement du snapshot exact

La revue pré-consommation a approuvé la mécanique et la science mais a refusé
qu’un futur HEAD puisse être autorisé par un nouveau marqueur. H22a ferme ce
point sans auto-référence : le runner exige que son parent soit exactement le
commit H22 revu `5810061e…`, que HEAD soit son unique descendant direct et que
le diff contienne exactement les cinq fichiers H22a listés dans le contrat.
Le marqueur continue de lier simultanément le SHA brut du contrat et le HEAD
final. Un commit ultérieur échoue donc avant le premier hachage d’actif.
