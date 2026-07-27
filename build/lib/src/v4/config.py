from __future__ import annotations
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import yaml

@dataclass(frozen=True)
class DataConfig:
    manifest: Path = Path("data/dataset/stream/manifest.csv")
    min_pitch: int = 40
    max_pitch: int = 88
    train_players: tuple[str, ...] = ("00", "01", "02", "03")
    validation_players: tuple[str, ...] = ("04",)
    test_players: tuple[str, ...] = ("05",)
    normalization_percentile: float = 99.5
    normalization_target: float = 0.90
    max_gain: float = 20.0
    cache_files: int = 4
    seed: int = 42

@dataclass(frozen=True)
class ModelConfig:
    input_samples: int = 4096
    channels: int = 32
    tcn_blocks: int = 4
    dropout: float = 0.20
    dense_units: int = 128
    pooling: str = "hybrid"

@dataclass(frozen=True)
class TrainConfig:
    output_root: Path = Path("runs/v4")
    run_name: str = "pitch_v4"
    batch_size: int = 64
    epochs: int = 40
    learning_rate: float = 1e-3
    min_learning_rate: float = 1e-6
    early_stopping_patience: int = 6
    reduce_lr_patience: int = 3
    steps_per_epoch: int | None = None

@dataclass(frozen=True)
class EvaluationConfig:
    make_plots: bool = True

@dataclass(frozen=True)
class V4Config:
    data: DataConfig = field(default_factory=DataConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)

    def to_dict(self) -> dict[str, Any]:
        def convert(value: Any) -> Any:
            if isinstance(value, Path): return str(value)
            if isinstance(value, tuple): return list(value)
            if isinstance(value, dict): return {k: convert(v) for k,v in value.items()}
            if isinstance(value, list): return [convert(v) for v in value]
            return value
        return convert(asdict(self))

def _section(cls, raw: dict[str, Any], name: str):
    values=dict(raw.get(name) or {})
    if cls is DataConfig:
        if 'manifest' in values: values['manifest']=Path(values['manifest'])
        for key in ('train_players','validation_players','test_players'):
            if key in values: values[key]=tuple(str(v) for v in values[key])
    if cls is TrainConfig and 'output_root' in values:
        values['output_root']=Path(values['output_root'])
    return cls(**values)

def load_config(path: str | Path) -> V4Config:
    with Path(path).open('r',encoding='utf-8') as handle:
        raw=yaml.safe_load(handle) or {}
    return V4Config(
        data=_section(DataConfig,raw,'data'),
        model=_section(ModelConfig,raw,'model'),
        train=_section(TrainConfig,raw,'train'),
        evaluation=_section(EvaluationConfig,raw,'evaluation'),
    )
