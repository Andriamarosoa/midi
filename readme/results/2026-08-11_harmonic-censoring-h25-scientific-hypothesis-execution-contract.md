# H25 — contrat scientifique pitch-dilution et causal 4096/8192

## Autorisation et portée

La clôture administrative `ebd5c0d8…` a été approuvée sous :

```text
APPROVED_H25_ADMINISTRATIVE_LIFECYCLE_QUALIFICATION_DOCUMENTARY_CLOSURE
```

La portée suivante autorise uniquement :

```text
AUTHORIZED_TO_DEFINE_AND_COMMIT_H25_SCIENTIFIC_HYPOTHESIS_AND_EXECUTION_CONTRACT_ONLY
```

Ce commit ne crée ni manifest, population, fixture, waveform, runner,
recomputer, capability, claim, seal, activation ou OS binding. Il n'importe
pas NumPy pour un calcul scientifique et n'exécute aucun P0/P1/P2.

## Artefacts contractuels

```text
configs/harmonic_censoring_h25_scientific_hypothesis_execution_contract.json
19629 octets
SHA-256 ae837a647792c56c02a7d96a4328f62c1ecac03d0c0a839d59488c420cfff911

tests/test_harmonic_censoring_h25_scientific_contract.py
7215 octets
SHA-256 4d62b02dbc4cb21475c09e49c913473ec29579c2796d1dcd26cd522fab10a26e
```

Le contrat lie obligatoirement la qualification administrative finale :

```text
H25_ADMIN_LIFECYCLE_QUALIFICATION_PASSED
record SHA-256
54bd361a99223dd24d6e4f0883ace47572965604c406efe69e5564f675d14ee1
```

## Hypothèse testable

La question H25 est volontairement plus étroite que l'idée brute de répéter
des transpositions :

> Une trajectoire de dilution calculée vectoriellement depuis un spectre causal
> partagé, après retrait de la géométrie de support et du gain, contient-elle
> une information utile lorsqu'elle est combinée à une preuve causale d'attaque
> ou d'harmoniques propres pour distinguer une nouvelle fondamentale d'une
> harmonique ancienne persistante ?

Le contrat contient aussi le null obligatoire : transformer tout le mélange
préserve une collision exacte. Une transformation seule ne peut pas attribuer
une fréquence à deux sources confondues. Deux explications produisant les mêmes
échantillons causaux et le même état doivent donc produire les mêmes features
et la catégorie `AMBIGUOUS`.

L'index brut auquel une composante disparaît hors support est une conséquence
de son pitch et des limites d'observation. Il est explicitement interdit comme
feature discriminative. H25 ne peut réussir en redécouvrant cette géométrie.

## Calcul de dilution préenregistré

```text
entrée       un spectre de puissance float64 partagé par fenêtre
grille       s = 0..88 demi-tons entiers, ordre ascendant
pas          1 demi-ton
valeurs      89
calcul       une opération vectorisée, jamais 89 inférences modèle
sortie       courbe normalisée - null géométrique support-aware
```

La grille `0..88` couvre la totalité de l'axe analytique déclaré de MIDI 40 à
la coordonnée 128. Toute paire candidat/shift hors support est masquée, jamais
remplacée par zéro. Le résultat vectorisé devra posséder une référence scalaire
et respecter `rtol=1e-10`, `atol=1e-12` en float64 ; catégories, masques,
entiers et booléens ont une tolérance nulle.

Le graphe harmonique est typé :

```text
H1       FUNDAMENTAL_IDENTITY
H2-H20   PROPER_HARMONIC_ASCENT
```

Le set attendu des relations est défini exactement et toute omission,
duplication, relation extra ou arête descendante devra échouer.

## Deux fenêtres, une seule frontière causale

Les deux vues terminent au même hop courant :

```text
4096 samples   preuve primaire d'onset, nouveauté et énergie
8192 samples   confirmation de persistance/décroissance et contexte ancien
hop            256 samples
lookahead      0
délai naissance nouvelle source   exactement 1 hop
```

Le contexte 8192 ne peut pas lire le futur, inventer une seconde décision
d'onset ou rendre identifiable un cas exactement confondu. La machine d'état
reste `INACTIVE -> PENDING_NEW -> ACTIVE`; un pending doit être résolu au hop
suivant en `BIRTH_SUPPORTED`, `NO_BIRTH` ou `AMBIGUOUS`.

## Nouvelle population exigée, mais absente

```text
population namespace   H25_SYNTHETIC_V1
test namespace         H25_TEST_V1
manifest population    absent
manifest tests         absent
waveforms              absentes
```

Tous les IDs devront être nouveaux. Aucun byte de fixture/test H23 ou H24 et
aucune ligne H17 ne peut être repris. Le futur plan devra couvrir au minimum
fondamentale isolée, harmonique ancienne, nouvelle fondamentale sur harmonique
partagée, collision exacte, fondamentales distinctes à partiel commun,
harmonique naturelle, inharmonicité/cents, gain/phase/bruit, frontières de
fenêtre/pitch/Nyquist, silence et OOD synthétique. Cardinalités, ordre et SHA
seront figés et revus avant toute synthèse.

## P0 / P1 / P2 et kill rules

```text
P0  opérateur analytique, graphe, null, causalité, non-identifiabilité
    premier échec -> H25_SYNTHETIC_HYPOTHESIS_KILLED

P1  naissance identifiable, rejet harmonique-only, collision ambiguë
    premier échec -> H25_IDENTIFIABILITY_NOT_DEMONSTRATED

P2  robustesse, déterminisme, limites, attrition, coût CPU/mémoire
    premier échec -> H25_PRETRAIN_READINESS_NOT_DEMONSTRATED

tout passe -> H25_SYNTHETIC_PRETRAIN_EVIDENCE_PASSED
```

P1 exige tous les P0 ; P2 exige tous les P1. Le premier échec arrête la phase
et marque la suite exacte `NOT_RUN_BY_KILL_RULE`. Aucun taux moyen ne peut
compenser l'échec d'une famille positive, négative ou ambiguë. Même un succès
total n'est ni une autorisation d'entraînement ni une validation réelle.

## Lifecycle scientifique futur

Le contrat reprend la forme qualifiée administrativement : un unique
entrypoint revu devra posséder préflight, capability, claim, P0/P1/P2 et
clôture dans le même processus, sans pause ou injection post-claim. Le claim
sera la dernière action irréversible avant P0 automatique. EOF stdin,
décrochage parent/SSH, signal, timeout et erreurs de publication devront avoir
des fermetures préenregistrées.

Les nouveaux chemins one-shot sont réservés sous :

```text
tmp/local/harmonic_censoring_h25_scientific_v1*
```

Ils ne chevauchent ni H17/H23/H24 ni le namespace de qualification
administrative. Avant toute future capability, il faudra encore définir,
implémenter et faire revoir séparément : manifestes, population matérialisée,
harness/runner/recomputer dormants, runtime exact, seal, activation et binding
OS.

## Tests structurels

```text
python -m py_compile \
  tests/test_harmonic_censoring_h25_scientific_contract.py

python -m unittest \
  tests.test_harmonic_censoring_h25_scientific_contract -v

7 tests réussis en 0,003 s
git diff --check réussi
```

Ces tests ne synthétisent aucun signal et ne lancent aucune phase scientifique.
Ils verrouillent le scope contract-only, le record administratif, le null
non-identifiable, la grille, les deux fenêtres causales, les phases/kill rules,
les namespaces neufs et le lifecycle one-shot.

## Interdictions maintenues

Aucun manifest/population H25, waveform, runner/executor, producer, capability,
claim, seal, activation, OS binding, NumPy scientifique, P0/P1/P2, donnée
réelle, H17, locked-test, modèle, checkpoint, calibration, entraînement, export
ou live n'est autorisé par ce contrat.

La prochaine action est uniquement sa revue externe.
