from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class DatasetConfig:
    manifest: Path
    include_datasets: tuple[str, ...]
    min_pitch: int
    max_pitch: int
    train_players: tuple[str, ...]
    validation_players: tuple[str, ...]
    test_players: tuple[str, ...]
    seed: int
    sample_rate: int
    hop_size: int
    max_window: int
    normalization_percentile: float
    normalization_target: float
    max_gain: float


@dataclass(frozen=True)
class CacheConfig:
    mode: str
    validate_schema: bool


@dataclass(frozen=True)
class TrainConfig:
    run_name: str
    output_root: Path
    batch_size: int
    epochs: int
    learning_rate: float
    early_stopping_patience: int
    reduce_lr_patience: int
    min_learning_rate: float
    workers: int
    use_class_weights: bool
    max_class_weight: float


@dataclass(frozen=True)
class ModelConfig:
    channels: int
    tcn_blocks: int
    dropout: float
    dense_units: int
    pooling: str
    harmonic_auxiliary: bool
    harmonic_count: int
    harmonic_offset_scale_cents: float
    harmonic_amplitude_loss_weight: float
    harmonic_offset_loss_weight: float
    active_auxiliary: bool
    active_loss_weight: float
    onset_auxiliary: bool
    onset_loss_weight: float


@dataclass(frozen=True)
class EvaluationConfig:
    make_plots: bool
    save_predictions: bool


@dataclass(frozen=True)
class V5Config:
    dataset: DatasetConfig
    cache: CacheConfig
    train: TrainConfig
    model: ModelConfig
    evaluation: EvaluationConfig

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)

        def convert(value: Any) -> Any:
            if isinstance(value, Path):
                return str(value)
            if isinstance(value, tuple):
                return [convert(v) for v in value]
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            return value

        return convert(raw)


def load_config(path: str | Path) -> V5Config:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    dataset = raw["dataset"]
    cache = raw.get("cache", {})
    train = raw["train"]
    model = raw["model"]
    evaluation = raw.get("evaluation", {})

    return V5Config(
        dataset=DatasetConfig(
            manifest=Path(dataset["manifest"]),
            include_datasets=tuple(str(v) for v in dataset.get("include_datasets", [])),
            min_pitch=int(dataset.get("min_pitch", 40)),
            max_pitch=int(dataset.get("max_pitch", 88)),
            train_players=tuple(str(v) for v in dataset["train_players"]),
            validation_players=tuple(str(v) for v in dataset["validation_players"]),
            test_players=tuple(str(v) for v in dataset["test_players"]),
            seed=int(dataset.get("seed", 42)),
            sample_rate=int(dataset.get("sample_rate", 44100)),
            hop_size=int(dataset.get("hop_size", 256)),
            max_window=int(dataset.get("max_window", 4096)),
            normalization_percentile=float(dataset.get("normalization_percentile", 95.0)),
            normalization_target=float(dataset.get("normalization_target", 0.8)),
            max_gain=float(dataset.get("max_gain", 16.0)),
        ),
        cache=CacheConfig(
            mode=str(cache.get("mode", "ram")),
            validate_schema=bool(cache.get("validate_schema", True)),
        ),
        train=TrainConfig(
            run_name=str(train.get("run_name", "pitch_v5")),
            output_root=Path(train.get("output_root", "runs/v5")),
            batch_size=int(train.get("batch_size", 32)),
            epochs=int(train.get("epochs", 30)),
            learning_rate=float(train.get("learning_rate", 1e-3)),
            early_stopping_patience=int(train.get("early_stopping_patience", 6)),
            reduce_lr_patience=int(train.get("reduce_lr_patience", 3)),
            min_learning_rate=float(train.get("min_learning_rate", 1e-6)),
            workers=int(train.get("workers", 1)),
            use_class_weights=bool(train.get("use_class_weights", False)),
            max_class_weight=float(train.get("max_class_weight", 10.0)),
        ),
        model=ModelConfig(
            channels=int(model.get("channels", 32)),
            tcn_blocks=int(model.get("tcn_blocks", 4)),
            dropout=float(model.get("dropout", 0.1)),
            dense_units=int(model.get("dense_units", 128)),
            pooling=str(model.get("pooling", "hybrid")),
            harmonic_auxiliary=bool(model.get("harmonic_auxiliary", False)),
            harmonic_count=int(model.get("harmonic_count", 20)),
            harmonic_offset_scale_cents=float(
                model.get("harmonic_offset_scale_cents", 35.0)
            ),
            harmonic_amplitude_loss_weight=float(
                model.get("harmonic_amplitude_loss_weight", 0.2)
            ),
            harmonic_offset_loss_weight=float(
                model.get("harmonic_offset_loss_weight", 0.05)
            ),
            active_auxiliary=bool(model.get("active_auxiliary", False)),
            active_loss_weight=float(model.get("active_loss_weight", 0.2)),
            onset_auxiliary=bool(model.get("onset_auxiliary", False)),
            onset_loss_weight=float(model.get("onset_loss_weight", 0.2)),
        ),
        evaluation=EvaluationConfig(
            make_plots=bool(evaluation.get("make_plots", True)),
            save_predictions=bool(evaluation.get("save_predictions", False)),
        ),
    )
