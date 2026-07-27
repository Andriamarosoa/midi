# V6.0 - détection note active + pitch + harmoniques

V6.0 ajoute une sortie binaire `active` au modèle V5.3. Le pitch et les
harmoniques ne sont appris et évalués que lorsqu'une note est réellement
active. En inférence, le pitch est bloqué lorsque la probabilité `active` est
inférieure au seuil choisi uniquement sur la validation.

## Contrat des données

- Entrée : mix mono GuitarSet, identique à V5.3.
- Split : joueurs 00-03 train, 04 validation, 05 test.
- Positifs : les 83 533 fenêtres actives V5.3, identiques bit à bit.
- Négatifs : 16 703 fenêtres après relâchement et 10 244 fenêtres de silence.
- Plage pitch temporaire : MIDI 40-76.
- Fenêtres causales : 512, 1024, 2048 et 4096 échantillons dans un tenseur de
  4096 échantillons masqué à gauche.

Le rapport de validation est dans
`data/dataset/v6_0_active/validation_report.json`.

## Architecture et pertes

Le CNN + TCN + pooling reste commun. Quatre sorties partagent la même
représentation :

- `active` : sigmoid binaire ;
- `pitch` : softmax MIDI 40-76 ;
- `harmonic_amplitude` ;
- `harmonic_offset_cents`.

La tête `active` ajoute seulement 129 paramètres et aucun look-ahead. La perte
pitch et les pertes harmoniques sont masquées sur les exemples inactifs. Les
deux classes d'activité sont équilibrées par poids calculés sur le train.

## Construire les données

```powershell
python -m src.v5.external_data `
  --output-dir data\dataset\v6_0_active `
  --skip-idmt --skip-guitar-techs `
  --extract-harmonics --include-inactive `
  --silence-per-recording 32 `
  --release-offset-ms 20 50 `
  --overwrite
```

Puis vérifier que les exemples actifs n'ont pas changé :

```powershell
python -m src.v6.validate_dataset `
  --baseline-manifest data\dataset\v5_3_harmonics\manifest.csv `
  --candidate-manifest data\dataset\v6_0_active\manifest.csv `
  --output data\dataset\v6_0_active\validation_report.json
```

## Entraîner

```powershell
python -m src.v6.train --config configs\pitch_v6_0_guitarset_active.yaml
```

Chaque run conserve `last.keras` à chaque époque, `best.keras` selon l'AUC-PR
activité, `best_pitch.keras` selon le Top-1 pitch, `final.keras` et
`history.csv`. Un arrêt brutal peut perdre l'époque en cours, mais pas le
dernier checkpoint terminé.

## Évaluation

Le seuil actif maximise le F1 sur la validation, avec préférence pour la
précision en cas d'égalité. Il est ensuite figé pour le test. Les rapports
contiennent notamment :

- précision, rappel, F1 et faux positifs activité ;
- résultats par fenêtre, âge, relâchement, joueur et dataset ;
- Top-1/Top-3 pitch uniquement sur les vraies notes actives ;
- précision jointe après application du gate ;
- erreurs harmoniques uniquement sur les vraies notes actives.

Un checkpoint alternatif se réévalue avec un nouveau seuil choisi uniquement
sur la validation :

```powershell
python -m src.v6.evaluate_checkpoint `
  --run-dir runs\v6\NOM_DU_RUN `
  --checkpoint best_pitch.keras
```

## Limites connues

V6.0 apprend le silence et le relâchement, mais pas encore un événement onset
séparé ni la continuité temporelle d'un flux complet. Les tests live sur WAV
continus et la mesure de fausses notes par minute restent nécessaires avant de
conclure que les ghost notes sont résolues. IDMT, Guitar-TECHS et GAPS devront
être ajoutés ensuite avec le même contrat mono et des négatifs fiables, sans
modifier simultanément l'architecture de référence.
