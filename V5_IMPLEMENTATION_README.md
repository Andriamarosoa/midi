# V5 Implementation

## Installation

Ensure these dependencies exist:

```toml
dependencies = [
  "numpy>=1.24",
  "tensorflow>=2.15,<2.16",
  "PyYAML>=6,<7",
]
```

## Syntax check

```powershell
python -m compileall src\v5
```

## Train

```powershell
python -m src.v5.train --config "configs\pitch_v5.yaml"
```

## Important RAM note

V5 loads the train, validation and test NPZ arrays into RAM. Check available
memory before a full run. If memory is insufficient, the next step is a
memory-mapped cache format rather than returning to per-batch NPZ loading.
