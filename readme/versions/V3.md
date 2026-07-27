# MIDI Pitch Research Pipeline V3

## Install

Add to `pyproject.toml`:

```toml
"PyYAML>=6,<7"
```

Then:

```powershell
python -m pip install -e .
```

## Train

```powershell
python -m src.v3.train --config configs\pitch_v3.yaml
```

Each run creates a timestamped directory under `runs\v3` containing:

```text
best.keras
final.keras
config.json
normalization.json
split_report.json
history.csv
reports/
  summary.md
  metrics.json
  pitch_age.csv
  pitch_window.csv
  pitch_note.csv
  confusion.csv
plots/
  loss.png
  top1.png
  top3.png
  confusion.png
```

## Generate grouped cross-validation folds

```powershell
python -m src.v3.cross_validation --config configs\pitch_v3.yaml --folds 5
```

## Important behavior

- Split is stratified by MIDI pitch and grouped by `note_id`.
- A pitch with only one unique `note_id` remains train-only; it is not used for validation.
- Validation pitches are guaranteed to exist in training.
- Sampling is softly balanced and capped to avoid excessive repetition.
- Normalization gain is computed only from training data.
