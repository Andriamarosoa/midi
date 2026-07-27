from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict
import json


@dataclass
class DataConfig:
    npz: str = "data/processed/stream/00_BN1-129-Eb_comp_hex.npz"
    min_pitch: int = 40
    max_pitch: int = 88
    validation_ratio: float = 0.20
    seed: int = 42
    normalization_percentile: float = 99.0
    normalization_target: float = 0.90
    max_gain: float = 20.0


@dataclass
class SamplerConfig:
    enabled: bool = True
    balance_strength: float = 0.50
    max_class_multiplier: float = 2.0
    epoch_multiplier: float = 1.0


@dataclass
class ModelConfig:
    input_samples: int = 4096
    channels: int = 32
    tcn_blocks: int = 4
    dense_units: int = 128
    dropout: float = 0.15
    pooling: str = "hybrid"  # last, average, hybrid


@dataclass
class TrainConfig:
    output_root: str = "runs/v3"
    run_name: str = "pitch_v3"
    batch_size: int = 32
    epochs: int = 60
    learning_rate: float = 1e-3
    early_stopping_patience: int = 7
    reduce_lr_patience: int = 3
    min_learning_rate: float = 1e-6


@dataclass
class EvaluationConfig:
    top_k: int = 3
    make_plots: bool = True


@dataclass
class V3Config:
    data: DataConfig = field(default_factory=DataConfig)
    sampler: SamplerConfig = field(default_factory=SamplerConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _merge_dataclass(instance: Any, values: Dict[str, Any]) -> Any:
    for key, value in values.items():
        if hasattr(instance, key):
            setattr(instance, key, value)
    return instance


def load_config(path: str | Path) -> V3Config:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("PyYAML manquant: python -m pip install pyyaml") from exc
        raw = yaml.safe_load(text) or {}
    else:
        raw = json.loads(text)

    config = V3Config()
    _merge_dataclass(config.data, raw.get("data", {}))
    _merge_dataclass(config.sampler, raw.get("sampler", {}))
    _merge_dataclass(config.model, raw.get("model", {}))
    _merge_dataclass(config.train, raw.get("train", {}))
    _merge_dataclass(config.evaluation, raw.get("evaluation", {}))
    return config
