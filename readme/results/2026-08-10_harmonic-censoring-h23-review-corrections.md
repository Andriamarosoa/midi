# H23a — corrections contractuelles après revue externe

## Verdict reçu

La revue externe du commit `dc587d147bb979e4d19a466dcfdd310ccfbee02c`
a classé H23 `NON APPROUVÉ` comme contrat exécutable, tout en confirmant la
couverture des idées, les `72` IDs uniques, S1C/S1P/S2–S5,
`S5=AMBIGUOUS`, l'anti-auto-confirmation, le partage des partiels,
`K_pitch/K_source`, `K/K+1`, la causalité, le firewall MIDI, l'atomicité et les
interdictions H17/test verrouillé/train.

Aucun P0, audio, label, modèle, fit ou calcul scientifique n'a été exécuté.

## B1 — phase unique de I01/I02

`I01` et `I02` sont déplacés dans `P1_integration`. Leur phase résolue et
`phase_order.P1` concordent désormais. P2 contient seulement déterminisme,
performance et teacher readiness.

## B2 — paramètres et oracles fermés

Le contrat fixe désormais :

- cutoffs exacts `[1,2,3,4,8,20]` ;
- masques hard et raised-cosine de `25 cents` ;
- phases, gains, cents, inharmonicité, bruit/SNR, âges, enveloppes, frontières
  et intervalles exacts ;
- tolérances float64 `rtol=1e-10`, `atol=1e-12` et tolérance catégorielle zéro ;
- contrôles D06/D07/D09/D10/C03/C05 et R03 sans branche ouverte ;
- budget P2 exact de streaming sur `60 s` et `10 336` hops.

Les anciens termes `machine tolerance`, `preregistered direction` et variantes
non bornées ne définissent plus le PASS/FAIL.

## B3 — mathématiques scellées

H23 définit maintenant le Hann périodique causal, RFFT puissance, fréquence
MIDI, noyau triangulaire de `35 cents`, énergies harmoniques, poids `1/h`,
`S_raw`, dénominateur `B`, validité de normalisation, `S_norm`, `S_null`, puis
les deux résidus :

```text
S_residual_norm = S_norm - S_null
S_residual_raw  = S_raw - B × S_null
```

Les définitions de `k90/k50/k10`, AUC, pente, courbure, roughness, changement
de régime et résidu final sont figées. Le rebond est explicitement retiré de
P0, car la somme cumulative non négative est monotone ; il ne pourra revenir
qu'avec un futur scorer non linéaire sous contrat séparé.

## B4 — polarité des inverse checks

Un inverse check correct produit :

```text
inverse_expected_failure_observed=true
inverse_unexpectedly_passes_primary_oracle=false
```

Seul l'inverse qui satisfait à tort l'oracle primaire fait échouer le test.

## B5 — univers fermé de fixtures

Le manifest futur contient exactement `6` bases et `169` variantes OFAT, soit
`175` IDs. Chaque axe, valeur, base concernée et count sont scellés. Les
trajectoires bend/slide/vibrato, accords, unisons, harmoniques naturelles,
résonances sympathiques et OOD ont des paramètres exacts.

Avant synthèse, un générateur zéro-science devra matérialiser le manifest et
son SHA. L'exécution future exigera :

```text
executed_fixture_ids == preregistered_fixture_ids
```

Ni omission ni ajout post-résultat ne sont permis.

## B6 — validité explicite

Les masques obligatoires ajoutent :

```text
normalization_valid
harmonic_observation_valid
emission_pitch_valid
```

Une énergie nulle ou trop faible rend `S_norm` invalide ; elle ne devient
jamais un négatif.

## B7 — borne analytique corrigée

H20 de MIDI 76 vaut :

```text
76 + 12 × log2(20) = 127,863137…
```

La grille analytique va donc jusqu'à la coordonnée `128`. Celle-ci reste
evidence-only et ne peut jamais produire un événement MIDI. La première
coordonnée interdite devient 129.

## B8 — reproductibilité

Le seal ajoute `fixture_spec_sha256`, `waveform_sha256`,
`cutoff_contract_sha256`, runtime, versions, architecture, device, threads et
RNG exact `numpy.random.Generator(numpy.random.PCG64(seed))`. La seed de chaque
fixture est dérivée de son ID par SHA-256. Le replay même runtime est
byte-identical ; la comparaison cross-runtime utilise les tolérances scellées.

## État

Ce correctif reste contract/doc-only. La seule prochaine action est une
nouvelle revue externe. Aucune implémentation ou exécution P0 n'est autorisée
automatiquement.
