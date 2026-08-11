# H25 — manifests population/tests et spécifications de fixtures

## Autorisation

Le contrat scientifique `32a3c548…` a été approuvé sous :

```text
APPROVED_H25_SCIENTIFIC_HYPOTHESIS_AND_EXECUTION_CONTRACT
```

La portée autorisée est uniquement :

```text
AUTHORIZED_TO_DEFINE_AND_COMMIT_H25_POPULATION_TEST_MANIFESTS_AND_FIXTURE_SPECIFICATIONS_ONLY
```

Aucune fixture scientifique, waveform ou matrice NumPy n'a été créée.

## Fichiers et bindings

```text
configs/harmonic_censoring_h25_fixture_specifications.json
15988 octets
SHA-256 6e688fdadd128e78522c5efe7f40a3babf7b17d28464d81a71eeda8f5a84a880

configs/harmonic_censoring_h25_population_manifest.json
1658 octets
SHA-256 c1337e92b30bb6326e739bc8d3df618cc04342ba9034e58af49d8fca6c51a7ad

configs/harmonic_censoring_h25_test_manifest.json
17206 octets
SHA-256 60a15cc65d632f27824b2c15e123a667caf0585004e2d7e1a086d5b38c731313

tests/test_harmonic_censoring_h25_manifests.py
7230 octets
SHA-256 729796c4f747058c21e1b07c51b5394775c3022def9aed8db86f1071a7657dad
```

Les trois artefacts lient le contrat scientifique exact :

```text
ae837a647792c56c02a7d96a4328f62c1ecac03d0c0a839d59488c420cfff911
```

Le manifest population lie les spécifications ; le manifest tests lie les
spécifications et le manifest population par leurs SHA finaux.

## Population exacte

```text
namespace      H25_SYNTHETIC_V1
fixtures       36
waveforms       0
materialized   false

positive       12
negative       12
ambiguous      12

pitch low       4
pitch mid      10
pitch high     19
pitch none      3
```

Les IDs sont explicitement ordonnés :

```text
H25-F-P01..H25-F-P12
H25-F-N01..H25-F-N12
H25-F-A01..H25-F-A12
```

Ils sont tous neufs. Omission, duplication, ajout, tri filesystem/locale ou
réutilisation d'un ID/byte H17/H23/H24 sont interdits.

Familles positives :

- nouvelle fondamentale sur H2/H4/H8 d'une ancienne source ;
- fondamentale isolée low/mid/high ;
- deux sources à partiel partagé ;
- onsets aux offsets `0/128/255` du newest hop.

Familles négatives :

- ancienne harmonique H2/H4/H8 sans nouvelle source ;
- pitch déjà actif ;
- harmonique naturelle sans attaque indépendante ;
- décroissance sans nouvelle attaque.

Familles ambiguës :

- collision byte-identique avec deux explications latentes ;
- hypothèse de nouvelle source à gain waveform nul ;
- fondamentale manquante ;
- impulse, chirp et cloche inharmonique OOD.

## Timeline et génération déterministe

```text
sample rate              44100 Hz
hop                      256 samples
stream                   16640 samples, g=0..16639
premier long window      fin 8191, silence exact
old source onset         8192
target hop               fin 16383
resolution hop           fin 16639
target 4096              12288..16383
target 8192               8192..16383
previous 4096            12032..16127
previous 8192             7936..16127
padding                  interdit
```

Les spécifications fixent les formules float64 de fréquences MIDI, partiels,
enveloppes, phases, gains, cents et inharmonicité. Le seed de bruit dérive de
`SHA256("H25|" + fixture_id + "|noise")` et PCG64. Le pink noise est défini
par RFFT, DC nul et pondération `1/sqrt(k)`, puis IRFFT, centrage RMS et mise à
l'échelle SNR. Le bruit est nul avant `g=8192`, de sorte que le premier long
window reste un silence exact. Chirp, impulse et cloche OOD possèdent aussi des
formules fermées.

Le futur WAV/file encoding reste volontairement non défini : cette étape
spécifie les tableaux scientifiques float64 mais n'autorise pas leur création.

## Tests exacts

```text
namespace     H25_TEST_V1
P0             9
P1             9
P2             9
total         27
executed      false
```

Les IDs sont `H25-T-P0-001..009`, puis `P1-001..009`, puis `P2-001..009`.
Chaque test possède objectif, fixtures exactes en ordre population, oracle,
pass rule, kill status et inverse. P1 référence les `36` fixtures exactement
une fois et conserve le ratio `12/12/12`. P0 et P2 couvrent également l'union
exacte des `36` IDs.

Les neuf familles P0 verrouillent graphe typé, équivalence scaling/cutoff,
rejet du raw disappearance, collision ambiguë, parité vectoriel/scalar,
support/null, causalité 4096/8192, sécurité numérique et invariance d'ordre.

P1 verrouille toutes les catégories positives, négatives et ambiguës sans
compensation par moyenne. P2 verrouille futur causal, translation, gain/phase,
bruit/cents/inharmonicité, frontières, ordre, déterminisme, coût et attrition.

Bornes P2 figées :

```text
wall                 <= 600 s
peak RSS             <= 4 GiB
GPU devices             0
scientific processes    1
model inference calls   0
hidden pitch inferences 0
```

Ces bornes sont pass/fail et ne constituent pas des paramètres à ajuster.

## Validation structurelle

```text
python -m py_compile tests/test_harmonic_censoring_h25_manifests.py
python -m unittest tests.test_harmonic_censoring_h25_manifests -v

7 tests réussis en 0,007 s
JSON parse x3 réussi
git diff --check réussi
```

Les tests recomputent les SHA liés, comptes, catégories, familles, pitch bands,
IDs, ordres, schemas, références de fixtures, couverture exhaustive par phase
et P1 `12/12/12`.

## Interdictions

Aucune matérialisation/synthèse de waveform, aucun fichier fixture
scientifique, NumPy scientifique, operator/producer/runner/recomputer,
capability/claim/seal/activation/OS binding, P0/P1/P2, donnée réelle, H17,
locked-test, modèle, checkpoint, calibration ou training n'est autorisé.

La prochaine action est uniquement la revue externe des manifests et specs.
