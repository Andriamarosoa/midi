# H25 — moteur scientifique, runner dormant et recomputer indépendant

## Verdict de phase

Cette phase implémente uniquement le bloc dormant autorisé après la validation
byte-for-byte de la population `H25_SYNTHETIC_V1`. Elle ne lance aucun des 27
tests scientifiques préenregistrés et n'ouvre pas la population Mac publiée.

```text
population H25 publiée et vérifiée       oui, preuve locale Mac approuvée
moteur scientifique                      implémenté, dormant
registre producteurs                     27/27, ordre P0 -> P1 -> P2
runner scientifique                      dormant, fail-closed
recomputer indépendant                   implémenté
P0 / P1 / P2 exécutés                    0 / 0 / 0
capability / claim / seal scientifique   absents
locked-test / données réelles            non utilisés
modèle / checkpoint / training           non utilisés
```

## Bindings de population

Le plan dormant lie les trois empreintes corrigées et vérifiées hors TTY :

```text
population_index.jsonl
814d8c368ac67ce65ed20c9e90e634ceffe706db1cc5e642cc3c61ff37ab5f53

runtime_provenance.json
cadc154a84674f6e58cf412d71f73407d0c07388f3bf470fa2368a1b810825db

population_receipt.json
dbab85910151ce25c186f478797c86604a94e6cf486dda7e0c4b7b8eeb4fddd9
```

Le loader versionné ne lit que les quatre contrats/manifests Git scellés. Il
n'ouvre aucun fichier sous `tmp/local`.

## Opérateur numérique

`H25_SUPPORT_NORMALIZED_DILUTION_V1` est calculé depuis un seul spectre de
puissance causal partagé :

```text
pitches candidats       MIDI 40..76
harmoniques              H1..H20
grille transform         s=0..88, pas 1 demi-ton
coordonnée               p + 12 log2(h)
support transformé       coordonnée + s <= 128 et support RFFT/Nyquist valide
sorties                   raw, normalisée, null géométrique, résiduelle
valeur invalide          masque + NaN, jamais zéro d'évidence
baseline                 B > max(1e-24, 1e-12 * puissance totale)
```

La version vectorisée et une référence scalaire indépendante utilisent des
boucles différentes. Les tests `TEST-ONLY-*` vérifient leur parité sur 89
positions, les masques, l'invariance à l'ordre candidat et l'absence de valeur
finie dans les cellules invalides. L'index brut de disparition n'est jamais
exposé comme feature.

## Graphe et causalité

Le graphe analytique est fermé sur :

```text
p=24..76
h=1..20
p + 12 log2(h) <= 128
```

H1 est typé `FUNDAMENTAL_IDENTITY`; H2..H20 sont uniquement
`PROPER_HARMONIC_ASCENT`. Les vues 4096 et 8192 terminent au même hop. Les vues
précédentes terminent exactement 256 samples plus tôt et la feature conserve
`maximum_sample_read` pour permettre au recomputer de refuser tout futur.

La vue 4096 porte onset, nouveauté harmonique et nouvelle énergie. La vue 8192
ne fournit que persistance/décroissance. Le résidu d'explication par les sources
déjà actives vient d'une factorisation causale non négative ; les sources
actives sont une entrée d'état du replay, pas déduites du target, de la famille
de fixture ou d'une identité de référence.

La machine d'état résout obligatoirement :

```text
INACTIVE -> PENDING_NEW -> ACTIVE / INACTIVE
```

après exactement un hop. Ses quatre sorties sont
`BIRTH_SUPPORTED`, `NO_BIRTH`, `ALREADY_ACTIVE_HISTORY` et `AMBIGUOUS`.
Un état non identifiable ou un support manquant reste ambigu ; aucun backfill,
retrigger ou NoteOn n'est produit par ce module.

## Producteurs, recomputation et kill rules

Le registre contient exactement les 27 IDs du manifest dans l'ordre. Les
producteurs persistent uniquement des opérandes, features, masques, compteurs
et mutations inverses. Les clés `pass`, `verdict`, `final_pass`,
`primary_pass` et `inverse_pass` sont refusées.

Le recomputer, dans un module séparé sans NumPy, dérive les catégories, la
parité scalaire/vectorisée, les inverses et les contraintes de phase. Le helper
de préfixe applique mécaniquement :

```text
échec P0 -> H25_SYNTHETIC_HYPOTHESIS_KILLED
échec P1 -> H25_IDENTIFIABILITY_NOT_DEMONSTRATED
échec P2 -> H25_PRETRAIN_READINESS_NOT_DEMONSTRATED
suffixe  -> NOT_RUN_BY_KILL_RULE
```

Le runner public recharge le plan et vérifie le registre, puis échoue toujours
à `require_h25_scientific_execution_authorized()` avant import NumPy ou accès
population. Il n'existe ni CLI, issuer, capability, claim, seal, activation ou
binding OS scientifique.

## Validation autorisée

```text
py_compile                                            réussi
9 tests du nouveau moteur dormant                     réussis en 0,088 s
54 tests H25 ciblés sans probes real-OS historiques   réussis en 0,284 s
git diff --check                                      réussi
```

Les nouveaux tests utilisent uniquement des tableaux synthétiques explicitement
`TEST-ONLY-H25-*`. Ils ne chargent aucun des 36 waveforms publiés et n'appellent
pas le runner de phase.

Une tentative plus large par wildcard a aussi inclus les probes administratifs
real-OS historiques. Sous le PTY Windows courant, 13 probes ont échoué sur
`worker exit marker differs from the process result`; le même test isolé
reproduit l'écart sans les nouveaux modules. Ce défaut de transport Windows
n'est pas masqué dans ce rapport, mais il n'affecte ni les 54 tests ciblés ni
la dormance scientifique. Aucune correction de ce harness déjà qualifié n'a
été faite dans ce commit.

## Portée restante

Toujours interdit : ouvrir/exécuter les 36 fixtures par le moteur, lancer P0,
P1 ou P2, créer une authority/capability/claim scientifique, accéder à une
donnée réelle ou au locked-test, charger un modèle/checkpoint, entraîner,
calibrer, exporter ou lancer le live.

La prochaine action est une revue externe du présent bloc dormant. Une future
transition d'autorité séparée devra précéder toute lecture scientifique de la
population et toute exécution P0.
