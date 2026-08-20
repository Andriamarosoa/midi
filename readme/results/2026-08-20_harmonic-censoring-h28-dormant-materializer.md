# H28 — matérialiseur dormant des six snapshots causaux

## Résultat

Le matérialiseur H28 est implémenté sans être activable. Il ne possède aucun
issuer de capability, aucun chemin de destination et aucun code de publication.
Son entrée publique échoue avant NumPy, le contrat, le filesystem ou le rendu
d'un échantillon.

## Plan fermé

Le planner metadata-only dérive exactement :

```text
H27-F-P01/N          candidate 40, actifs []
H27-F-N01/N          candidate 52, actifs [40]
H27-F-P01/N_PLUS_1   candidate 40, actifs []
H27-F-N01/N_PLUS_1   candidate 52, actifs [40]
H27-F-P01/N_PLUS_2   candidate 40, actifs []
H27-F-N01/N_PLUS_2   candidate 52, actifs [40]
```

Les fins de proposition sont `16383`, `16639`, `16895`; les fins de
résolution correspondantes sont `16639`, `16895`, `17151`. Aucun état n'est
transporté entre les horizons.

## Rendu futur et preuve historique

Les recettes P01/N01 sont relues depuis le fichier H27 figé de `21241` octets,
SHA-256 `28707e95...`. Les primitives numériques, fréquence MIDI, enveloppe et
accumulation sont AST-identiques au matérialiseur H27; seul `SAMPLE_COUNT`
passe de `16640` à `17152`.

Une future activation devra vérifier avant de retourner chaque waveform que
ses `16640` premiers float64 ont exactement les SHA historiques :

```text
P01 173183bf0a8017e8d24591cbbdd4c8055838546775917a5534c894527fa70a7e
N01 657fb5dd2a0bac49b6d4a56911d861bcc194cc04f95de6c93d2731e3da0e0ebb
```

Pour l'horizon `N`, un masque legacy 16640 est aussi reconstruit et doit garder
le SHA `c38ec8da...`. Les nouveaux masques role-major mesurent `68608` octets et
marquent uniquement les quatre vues causales exigées par leur horizon.

## Validation locale

Les suites H28/H27 ciblées totalisent `40/40` tests réussis. Elles couvrent le
plan exact, la capability inconstructible/non copiable, l'arrêt avant toute
dépendance scientifique, la parité AST et l'absence de code de publication ou
d'import NumPy. `py_compile` et `git diff --check` passent.

Aucun waveform, masque, index, répertoire de population, FFT ou NNLS n'a été
créé ou exécuté.

Contrat du lot :

```text
configs/harmonic_censoring_h28_materializer_dormant_contract.json
SHA-256 09e704b1171b48fc64cb537149113d600322e52a3aac825c4b4cf1e87dff01ef
```

## Latence, risques et suite

Le lot ne touche pas le chemin live et n'ajoute donc aucune latence produit.
Le rendu futur est synthétique/offline. Le risque restant est opérationnel :
aucune autorité one-shot, aucun claim, aucun publisher atomique et aucun index
scellé n'existent encore.

La prochaine étape est uniquement leur implémentation dormante et leurs tests
fail-closed. Elle ne doit ni émettre de capability ni rendre/publier les six
records.
