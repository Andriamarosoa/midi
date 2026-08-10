# H24 — contrat de matérialisation et consommation one-shot

Date : `2026-08-10`

## Autorisation

La revue externe a approuvé le harness dormant corrigé au commit :

```text
1b6aa27536dd5bfceba62d6bc5c9a499b4c11f18
```

et a autorisé uniquement :

```text
AUTHORIZED_TO_DEFINE_H24_POPULATION_MATERIALIZATION_AND_ONE_SHOT_CONTRACT_ONLY
```

Cette étape n'autorise ni l'implémentation d'un materializer, ni la création
d'un claim/marker, ni la synthèse d'une waveform, ni P0/P1/P2.

## Artefact contractuel

Le fichier :

```text
configs/harmonic_censoring_h24_population_materialization_one_shot_contract.json
```

a pour SHA-256 :

```text
b48aa4f417a9857983c79809efe24137d6b82ad0984d20e906286477f05a14ca
```

Il lie les snapshots déjà approuvés :

```text
successor       184d3847a594ffaca263b45befe70d1f5aa63ade0a0ef599d969ba044f4e680a
population      52c88c74c837ad3c6109be466df38bac862e10d93c187fe60e8c5da30bd4b02b
tests           7f87e486ffc6fdc2bfa60a5c617eca9b1ce78c570c1d72910173193ad1f7b416
binding         242c00d4d5fd3b9e777676b563f28b94b724159bde81307aebbba9e46608a1b5
harness         72675c6dda2128aa0036b7f0f2379de535fd74445a029f020f24f3f6f15fff39
```

Le harness et les opérateurs approuvés sont liés au commit `1b6aa275…` et aux
blobs Git `1a8759d6…` et `7e72ed05…`.

## Spécifications vers population

La future population reste exactement `H24_SYNTHETIC_V1` :

```text
175 spécifications dans l'ordre du manifest
→ 175 recettes immutables dans le même ordre
→ 175 waveforms de 12 544 échantillons float64
→ 175 triples spec / target / waveform
→ index JSONL de 175 lignes
→ reçu de population
```

La sélection par l'appelant, l'omission, l'ajout, le doublon et le réordonnage
sont interdits. Chaque seed est recomputé par :

```text
uint64_le(first_8_bytes(SHA256(UTF8("H24|" + fixture_id))))
```

Le contrat ferme les `17` axes de variante, les enveloppes, trajectoires,
fréquences, phases, bruit PCG64, six OOD et les valeurs nommées nécessaires.
Il ne réutilise aucun seed, waveform, ID ou outcome H23.

### Correction après revue de `10aa49a8…`

La première revue a validé la structure one-shot, mais refusé le contrat final
car deux implémentations pouvaient encore produire des octets différents. Le
correctif impose désormais exactement :

```text
defaults source : gain=1, cents=0, B=0, fundamental_amplitude=1,
                  h1_phase=0, phase=0, old_source_age_hops=0,
                  onset=12032, attack=0, decay=8, technique=null,
                  instantaneous_pitch_offset=0

ordre : sources puis harmoniques dans l'ordre recette,
        une addition float64 à la fois, sans tri/réduction/FMA/fastmath

pink RNG : standard_normal(bins) pour real,
           puis standard_normal(bins) pour imag,
           jamais un tirage combiné/interleaved
```

La trace normative donne les appels exacts `np.power`, `math.pow`,
`math.sqrt`, `np.cumsum`, `np.exp`, `np.sin`, `np.mean`, `np.sqrt` et
`np.fft.irfft`, ainsi que l'ordre d'accumulation des OOD.

### Correction finale de la trace numérique

La seconde revue a confirmé les defaults, l'index et la provenance, mais a
refusé les descriptions encore mathématiques des trajectoires techniques et
des chirps. Le contrat ferme désormais aussi leur suite d'opérations exacte :

```text
linear_cents / linear_semitones
  elapsed = maximum(samples-onset, 0), float64
  duration = max(1, duration_hops*256)
  fraction = minimum(elapsed/duration, 1)
  première valeur end exactement à onset+duration
  np.linspace et dénominateur duration-1 interdits

sinusoidal_cents
  même elapsed float64
  appel np.sin exact avec depth/100, 2*pi, rate_hz et 44100

six OOD
  fill(0), slices, arange float64, phases, cumsum, boucles et additions
  explicités branche par branche dans l'ordre normatif
```

Les réécritures par `scipy.signal.chirp`, `logspace`, `geomspace`, une autre
interpolation ou une formule algébriquement équivalente sont interdites. Les
tests adversariaux remplacent volontairement la grille linéaire par
`np.linspace(..., endpoint=True)` et le log-chirp par une construction SciPy;
les deux contrats altérés sont refusés.

## Octets et hashes futurs

Chaque waveform sera publiée comme octets bruts :

```text
IEEE-754 binary64 little-endian
C order
aucun header
12 544 × 8 = 100 352 octets
extension .f64le
```

Les specs et targets utilisent du JSON canonique UTF-8/LF. Chaque hash est le
SHA-256 lowercase des octets exacts. Les hashes de waveform ne sont pas
fabriqués par ce contrat : ils seront calculés sur les octets effectivement
synthétisés pendant l'unique tentative, écrits dans l'index, puis tous les
fichiers seront rouverts et rehachés avant publication.

Les hashes prouvent l'identité des octets, pas la validité scientifique.

Pour chaque ligne `i`, les treize champs de l'index sont maintenant liés
explicitement au manifest, à la recette et aux fichiers rouverts. Le hash de
la liste ordonnée est exactement le SHA-256 du tableau JSON canonique des 175
IDs avec LF final; toute jointure alternative est interdite.

## Frontière de consommation

Le préflight futur devra vérifier tous les SHA, HEAD, worktree, runtime, blobs,
`175` recettes et seeds sans importer NumPy. La consommation commencera avec :

```text
os.open(marker, O_CREAT | O_EXCL | O_WRONLY, 0600)
→ écrire JSON canonique
→ fsync marker
→ close
→ fsync parent
→ seulement ensuite importer NumPy et allouer la première waveform
```

L'existence du marker suffit à déclarer `H24_SYNTHETIC_V1` consommé, même si
le marker est partiel ou corrompu. Après `O_EXCL`, erreur, crash ou timeout ne
permettent aucun retry, resume, repair ou seconde tentative.

La future capability est process-local, identity-attested, non sérialisable et
possède un ensemble fermé de 18 bindings. Le marker possède exactement ses
bindings d'autorité plus `schema_version`, `purpose` et
`population_consumed=true`. Il lie notamment contrat, commit/blob materializer,
blobs harness/opérateurs, cinq SHA H24, seal, chemins fixes et objet runtime.
Le runtime du marker et du reçu doit être exactement le même objet à huit
champs; hostname, PID, timestamp, nonce et metadata caller sont interdits.

## Atomicité et interruption

Les futurs chemins sont fixes sous :

```text
tmp/local/harmonic_censoring_h24_synthetic_v1/
```

La matérialisation se fera dans `population.materializing`. Les fichiers seront
fermés, fsync, rouverts et rehachés. Seule une population complète pourra être
renommée atomiquement en `population`. Toute sortie partielle reste privée,
non autoritative et interdite aux tests. Une erreur post-claim reçoit le statut
`H24_POPULATION_MATERIALIZATION_INCONCLUSIVE_CONSUMED` et ne porte aucun verdict
scientifique.

## Séparation scientifique

Le futur processus de matérialisation devra s'arrêter après reçu et rapport
terminal. Il lui sera interdit d'importer/appeler les evaluators H24. Même une
population complète n'autorisera pas P0/P1/P2 : une nouvelle capability, un
nouveau seal, une revue et une autorisation distincte resteront obligatoires.

## Validation administrative

Les tests spécifiques vérifient : bindings SHA, portée contract-only, `175`
recettes, fermeture des `17` axes, recomputation des `175` seeds, format exact
des fichiers, index/reçu, claim durable avant NumPy, non-retry et impossibilité
de promouvoir une sortie partielle.

```text
143 tests H24/H23/H20 réussis en 2,121 s
aucun fichier src/ modifié
aucune waveform synthétisée
aucune fixture matérialisée
aucun claim/marker créé
aucun P0/P1/P2 exécuté
aucune donnée réelle/H17/locked-test ouverte
```

La prochaine action est exclusivement la revue externe de ce contrat.
