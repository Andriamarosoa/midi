# H26 — cause forensique de l'arrêt P0-002

Date : 2026-08-12

## Verdict forensique

```text
forensic_verdict = H26_P0_FORENSIC_ROOT_CAUSE_CONFIRMED_ZERO_POWER_PREVIOUS_SHORT_P01
p0_terminal_status = H26_P0_INCONCLUSIVE_CONSUMED
retry_allowed = false
population_index_sha256 = b0045797b08ef2ebbfaf7e1dda0c10f213eec3d8b3a3daaa31c8153dd842b4a7
```

L'investigation a été strictement read-only. Elle n'a appelé ni runner P0, ni
moteur H26, ni recomputer, ni FFT, ni NNLS. Elle n'a produit ou modifié aucun
artefact scientifique.

## Fixture responsable

```text
fixture = H26-F-P01
waveform_sha256 = 173183bf0a8017e8d24591cbbdd4c8055838546775917a5534c894527fa70a7e
waveform_size = 133120
finite_count = 16640
overall_nonzero_count = 512
first_nonzero_index = 16128
last_nonzero_index = 16639

current_short_range = 12288..16383
current_short_nonzero_count = 256
current_short_sum_x2 = 41.491130786397726
current_short_max_abs = 0.7175566355734877

previous_short_range = 12032..16127
previous_short_nonzero_count = 0
previous_short_sum_x2 = 0
previous_short_max_abs = 0

current_long_range = 8192..16383
current_long_nonzero_count = 256

previous_long_range = 7936..16127
previous_long_nonzero_count = 0
```

Le SHA de la waveform et celui du masque correspondent exactement au
`population_index.json`. La waveform contient 16 640 valeurs little-endian
`float64` finies ; le masque contient 16 640 octets 0/1 tous valides. Aucune
corruption de la population n'a été observée.

## Chaîne causale confirmée

P0-002 consomme ses représentants dans l'ordre `P01`, `N01`, `H01`, `A01`.
Pour P01, `extract_raw_operands()` appelle successivement :

```text
current_short
previous_short
current_long
previous_long
```

Le premier spectre est non nul. Le second porte sur une fenêtre exactement
silencieuse et produit une puissance totale nulle. `causal_spectrum()` exige
une puissance strictement supérieure au plancher et lève alors :

```text
failing_kernel = causal_spectrum
failing_stage = P0-002 / P01 / previous_short
error = H26 spectrum total power invalid
```

La fixture préenregistrée place l'onset unique à l'échantillon 16128, sans
source antérieure ni bruit. Sa fenêtre précédente, terminée à 16127, est donc
naturellement silencieuse. La cause est une incompatibilité déterministe entre
la fixture P01 et le contrat numérique du kernel.

## Contrôles d'exclusion

- `H26-F-N01` : waveform SHA
  `657fb5dd2a0bac49b6d4a56911d861bcc194cc04f95de6c93d2731e3da0e0ebb` ;
  les quatre fenêtres sont non nulles (`4096`, `4096`, `8192`, `7936`
  échantillons non nuls).
- `H26-F-H01` : waveform SHA
  `0c4f8dafe910c111d1bcd5e946e1f047d6289bc6ccd99371f76b67b6d8d20283` ;
  la convention `SILENT_STATE_ONLY` est cohérente et la branche
  `candidate_active` retourne avant tout spectre.
- `H26-F-A01` : waveform et alternate byte-identiques, SHA commun
  `beae562da7fb0e8ca710324fb30fb719f8120b2bbdb7cc4b5cdff57408a3849b` ;
  les quatre fenêtres sont non nulles et la branche
  `observation_equivalent` retourne avant tout spectre.

## Portée et arrêt

La population est intacte. L'incompatibilité fixture/kernel est confirmée.
P0 reste `H26_P0_INCONCLUSIVE_CONSUMED` : ce diagnostic ne constitue ni une
réussite ni un échec scientifique H26 et ne réouvre aucun retry.

```text
documentary_state = H26_P0_FORENSIC_ROOT_CAUSE_CONFIRMED_NO_RETRY_PENDING_REMEDIATION_DESIGN_REVIEW
locked_test_used = false
p1_executed = false
p2_executed = false
```

Toute décision entre correction du kernel, changement de sémantique d'une vue
silencieuse, modification de fixture ou abandon de H26 exige une autorisation
séparée. Aucun code, configuration, lifecycle, population ou artefact P0 n'est
modifié par cette archive.
