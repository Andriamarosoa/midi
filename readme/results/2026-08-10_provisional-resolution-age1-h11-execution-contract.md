# H11 — contrat d'exécution one-shot H7

## Verdict

```text
provisional_resolution_age1_persistence_h11_execution_contract_sealed
```

H11 prépare le futur chemin d'exécution, mais ne l'autorise ni ne l'invoque.
Aucun des 101 audio/labels H8 n'a été ouvert, aucun modèle chargé et aucune
inférence, cible, classe, AUC ou métrique réelle n'a été observée.

## Chaîne acceptée et contrat

- H7 : `e3e2be144282ecf0079ba22831abfb6439b16ac3` ;
- H8 : `8f50a8a083bbfd0b07330c338b64763199fdf894` ;
- cohorte H8 : `4dd76bd13c33ccb3946bfdbcf6f575d4550fb0c5588095e23da3b6e3f84bce1f` ;
- préparation H8 : `9bbe2b5558b6b5764415619260a6aba1e3daf1d3c22ce185f3b00a336f8e1639` ;
- H9 : `963cf72c8e60e2d669e659de037f910658637984` ;
- H10 : `bc878204451c45c3f5bb849bbf01de0de290f23a` ;
- contrat H10 brut : `533c5eb5062666181a98885cc588ef10a46bbf36c3618aed794ba3facd911e0f`.

Le contrat H11 fait `7635` octets et son SHA-256 brut est :

```text
ea6032e1e2cbd3da8a9bd2facb864df6eea5740692d00f952353d399b1facf8e
```

## Baseline historique unique

La provenance Policy A v3 fixe la seule baseline compatible :

```text
checkpoint Keras  5587783 octets
SHA               1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325
YAML              245285783eb395e1c16f9773cf9a15565510ba289467d63ad6a7d725bae19804
décodeur raw       c16be48271912c99c4237345e8406e39b88490b5565047757f6ca9e905615f96
décodeur canonique 7f6a93b566c2e042ec943821b5d35bdaa9151fe97711cd9463704aba20de178d
audio policy LF   45edbb712415c5b62f10a1405678fc28cee083891131108b2875ce8f71abcd3e
```

Le checkpoint et les trois configs ont été rehachés sur le Mac sans charger
Keras. Le baseline utilise 44100 Hz, hop 256, MIDI 40–76, fenêtre 8192,
fenêtre normale 4096, gain `1.4932045250002872`, batch 32, seed 0,
`shuffle=false`, un worker et les sorties `frame/onset/harmonic_amplitude`.

Le décodeur futur impose : collecteur passif age-1 actif, resolver nul, porte
causale nulle et `independent_note_threshold=null`. Aucune correction H4/H6
n'est active.

## Runtime figé

```text
Python      3.11.9
NumPy       1.26.4
TensorFlow  2.15.1
macOS       15.5 / Darwin 24.5.0
architecture arm64
device      CPU, MIDI_FORCE_CPU=1
```

Une mise à niveau exige une nouvelle revue avant exécution.

## Pipeline et consommation

Pour chaque prise : hashes avant ouverture, loaders historiques audio/labels,
une inférence acoustique, même séquence fournie une fois au décodeur et au
collecteur passif, flux MIDI complet, contrôle end-of-stream, cible H9,
jointure exacte `(frame_index,pitch)`, puis métadonnées H8 seulement.

La cohorte devient irrévocablement consommée juste avant que l'adapter puisse
ouvrir/parser le premier actif ou lancer l'inférence. Toute erreur ultérieure
interdit un verdict partiel et une relance automatique.

L'état futur est :

```text
prepared
→ external approval
→ authorization marker creation
→ atomic claim / running
→ completed OR failed
```

H11 ne crée pas le marqueur. La publication finale est un renommage atomique
après les 101 prises, 31 groupes, jointures et attritions réconciliés. Aucun
retry par prise n'existe.

## Tests synthétiques

Commande :

```powershell
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -m unittest `
  tests.test_provisional_resolution_age1_persistence_h7_contract `
  tests.test_provisional_resolution_age1_persistence_h8_preparation `
  tests.test_provisional_resolution_age1_h9_synthetic `
  tests.test_provisional_resolution_age1_h10_metrics `
  tests.test_provisional_resolution_age1_h11_orchestration
```

Résultat : `48 tests` réussis en `5,269 s`. Ils couvrent cohorte 101/31,
ordre d'une prise, inférence unique, même objet de prédiction, pending et
jointure invalides avant métrique, absence de retry, métrique appelée une fois,
marqueur absent/single-use, SHA invalide avant loader et publication atomique.
Les fixtures sont synthétiques et ne lisent aucun actif H8.

## Flags terminaux

```text
scientific_execution_authorized=false
execution_marker_created=false
runner_invoked=false
h8_scientific_assets_opened=false
h8_discovery_consumed=false
real_targets_extracted=false
real_signals_extracted=false
real_metrics_computed=false
locked_test_used=false
consumed_v2_cohort_used=false
```

Arrêt obligatoire pour revue externe avant toute création du marqueur ou
ouverture scientifique H8.
