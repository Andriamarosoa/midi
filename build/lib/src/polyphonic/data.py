"""Compact corpus and Keras sequences for continuous polyphonic frames."""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence
from zipfile import ZipFile

import numpy as np
import soundfile as sf
import tensorflow as tf


@dataclass(frozen=True)
class ManifestItem:
    source_id: str
    dataset_id: str
    player_id: str
    group_id: str
    split: str
    audio_path: Path
    audio_member: str
    labels_path: Path
    capture_id: str
    license_id: str


@dataclass(frozen=True)
class CachedLabels:
    item: ManifestItem
    arrays: Mapping[str, np.ndarray]


def load_manifest(path: Path) -> list[ManifestItem]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "source_id", "dataset_id", "player_id", "group_id", "split",
        "audio_path", "audio_member", "labels_path", "capture_id",
        "license_id",
    }
    if not rows:
        raise ValueError(f"Empty polyphonic manifest: {path}")
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Manifest columns missing: {sorted(missing)}")
    return [ManifestItem(
        source_id=row["source_id"],
        dataset_id=row["dataset_id"],
        player_id=row["player_id"],
        group_id=row["group_id"],
        split=row["split"],
        audio_path=Path(row["audio_path"]),
        audio_member=row["audio_member"],
        labels_path=Path(row["labels_path"]),
        capture_id=row["capture_id"],
        license_id=row["license_id"],
    ) for row in rows]


class PolyphonicCorpus:
    """Keep compact labels in RAM and load each waveform at most once."""

    REQUIRED_LABELS = {
        "active_bits", "onset_bits", "polyphony", "valid", "slot_pitch",
        "slot_note_id", "note_harmonic_present", "note_harmonic_amplitude",
        "note_harmonic_offset_cents", "note_harmonic_valid", "sample_rate",
        "hop_size", "audio_frames", "midi_min", "midi_max",
    }

    def __init__(self, items: Sequence[ManifestItem]) -> None:
        if not items:
            raise ValueError("The corpus split is empty.")
        self.items = list(items)
        self.labels: list[CachedLabels] = []
        for item in self.items:
            with np.load(item.labels_path, allow_pickle=False) as source:
                missing = self.REQUIRED_LABELS - set(source.files)
                if missing:
                    raise ValueError(
                        f"{item.source_id}: label arrays missing {sorted(missing)}"
                    )
                arrays = {name: np.asarray(source[name]) for name in source.files}
            frame_count = len(arrays["active_bits"])
            for name in ("onset_bits", "polyphony", "valid"):
                if len(arrays[name]) != frame_count:
                    raise ValueError(f"{item.source_id}: inconsistent {name} length")
            if arrays["slot_pitch"].shape[0] != frame_count:
                raise ValueError(f"{item.source_id}: inconsistent slot arrays")
            self.labels.append(CachedLabels(item, arrays))

        first = self.labels[0].arrays
        self.sample_rate = int(first["sample_rate"])
        self.hop_size = int(first["hop_size"])
        self.midi_min = int(first["midi_min"])
        self.midi_max = int(first["midi_max"])
        self.pitch_classes = self.midi_max - self.midi_min + 1
        self.harmonic_count = int(first["note_harmonic_present"].shape[1])
        self._audio: dict[int, np.ndarray] = {}
        self._archives: dict[Path, ZipFile] = {}

        for cached in self.labels[1:]:
            arrays = cached.arrays
            contract = (
                int(arrays["sample_rate"]), int(arrays["hop_size"]),
                int(arrays["midi_min"]), int(arrays["midi_max"]),
                int(arrays["note_harmonic_present"].shape[1]),
            )
            expected = (
                self.sample_rate, self.hop_size, self.midi_min,
                self.midi_max, self.harmonic_count,
            )
            if contract != expected:
                raise ValueError(f"{cached.item.source_id}: mixed label contract")

    def close(self) -> None:
        for archive in self._archives.values():
            archive.close()
        self._archives.clear()

    def __enter__(self) -> "PolyphonicCorpus":
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    @property
    def audio_gib(self) -> float:
        return sum(value.nbytes for value in self._audio.values()) / 1024**3

    def audio(self, recording_index: int) -> np.ndarray:
        recording_index = int(recording_index)
        cached = self._audio.get(recording_index)
        if cached is not None:
            return cached
        item = self.items[recording_index]
        if item.audio_path.suffix.lower() == ".npy":
            waveform = np.load(item.audio_path, mmap_mode="r", allow_pickle=False)
            rate = self.sample_rate
            if waveform.ndim == 1:
                waveform = waveform[:, None]
        elif item.audio_member:
            archive = self._archives.get(item.audio_path)
            if archive is None:
                archive = ZipFile(item.audio_path)
                self._archives[item.audio_path] = archive
            source = io.BytesIO(archive.read(item.audio_member))
            waveform, rate = sf.read(source, dtype="float32", always_2d=True)
        else:
            waveform, rate = sf.read(
                item.audio_path, dtype="float32", always_2d=True
            )
        if int(rate) != self.sample_rate or waveform.shape[1] != 1:
            raise ValueError(
                f"{item.source_id}: expected mono {self.sample_rate} Hz audio"
            )
        mono = (
            waveform[:, 0]
            if isinstance(waveform, np.memmap)
            else np.ascontiguousarray(waveform[:, 0], dtype=np.float32)
        )
        expected_frames = int(self.labels[recording_index].arrays["audio_frames"])
        if len(mono) != expected_frames:
            raise ValueError(
                f"{item.source_id}: audio length {len(mono)} != {expected_frames}"
            )
        self._audio[recording_index] = mono
        return mono

    def preload_audio(self) -> None:
        for index in range(len(self.items)):
            self.audio(index)


@dataclass(frozen=True)
class FramePools:
    onset: np.ndarray
    polyphonic: np.ndarray
    monophonic: np.ndarray
    silence: np.ndarray

    @property
    def sizes(self) -> dict[str, int]:
        return {
            "onset": len(self.onset),
            "polyphonic": len(self.polyphonic),
            "monophonic": len(self.monophonic),
            "silence": len(self.silence),
        }


def _refs(recording_index: int, frame_indices: np.ndarray) -> np.ndarray:
    return np.column_stack((
        np.full(len(frame_indices), recording_index, dtype=np.int32),
        np.asarray(frame_indices, dtype=np.int32),
    ))


def build_frame_pools(corpus: PolyphonicCorpus) -> FramePools:
    return _build_frame_pools(corpus, range(len(corpus.labels)))


def _build_frame_pools(
    corpus: PolyphonicCorpus,
    recording_indices: Sequence[int],
) -> FramePools:
    categories: dict[str, list[np.ndarray]] = {
        "onset": [], "polyphonic": [], "monophonic": [], "silence": [],
    }
    for recording_index in recording_indices:
        cached = corpus.labels[int(recording_index)]
        arrays = cached.arrays
        valid = np.asarray(arrays["valid"] > 0)
        active = np.asarray(arrays["active_bits"] != 0)
        onset = np.asarray(arrays["onset_bits"] != 0)
        polyphonic = np.asarray(arrays["polyphony"] > 1)
        masks = {
            "onset": valid & onset,
            "polyphonic": valid & active & polyphonic & ~onset,
            "monophonic": valid & active & ~polyphonic & ~onset,
            "silence": valid & ~active,
        }
        for name, mask in masks.items():
            categories[name].append(_refs(recording_index, np.flatnonzero(mask)))
    pools = {
        name: np.concatenate(parts, axis=0)
        for name, parts in categories.items()
    }
    if any(len(pool) == 0 for pool in pools.values()):
        raise ValueError(f"One or more frame pools are empty: {pools.keys()}")
    return FramePools(**pools)


def build_dataset_frame_pools(
    corpus: PolyphonicCorpus,
) -> dict[str, FramePools]:
    indices: dict[str, list[int]] = {}
    for index, item in enumerate(corpus.items):
        indices.setdefault(item.dataset_id, []).append(index)
    return {
        dataset_id: _build_frame_pools(corpus, recording_indices)
        for dataset_id, recording_indices in sorted(indices.items())
    }


def natural_validation_refs(
    corpus: PolyphonicCorpus,
    maximum_examples: int | None,
    seed: int,
) -> np.ndarray:
    parts: list[np.ndarray] = []
    for recording_index, cached in enumerate(corpus.labels):
        valid = np.flatnonzero(cached.arrays["valid"] > 0)
        parts.append(_refs(recording_index, valid))
    refs = np.concatenate(parts, axis=0)
    if maximum_examples is not None and len(refs) > maximum_examples:
        rng = np.random.default_rng(seed)
        refs = refs[rng.choice(len(refs), size=maximum_examples, replace=False)]
    return refs


def dataset_balanced_validation_refs(
    corpus: PolyphonicCorpus,
    maximum_examples: int,
    dataset_fractions: Mapping[str, float],
    seed: int,
) -> np.ndarray:
    if set(dataset_fractions) != {item.dataset_id for item in corpus.items}:
        raise ValueError("Validation dataset fractions do not match the corpus.")
    if abs(sum(dataset_fractions.values()) - 1.0) > 1e-6:
        raise ValueError("Validation dataset fractions must sum to 1.0.")
    by_dataset: dict[str, list[np.ndarray]] = {
        dataset: [] for dataset in dataset_fractions
    }
    for recording_index, cached in enumerate(corpus.labels):
        valid = np.flatnonzero(cached.arrays["valid"] > 0)
        by_dataset[cached.item.dataset_id].append(_refs(recording_index, valid))
    rng = np.random.default_rng(seed)
    selected: list[np.ndarray] = []
    assigned = 0
    datasets = list(dataset_fractions)
    for index, dataset in enumerate(datasets):
        pool = np.concatenate(by_dataset[dataset], axis=0)
        count = (
            maximum_examples - assigned
            if index == len(datasets) - 1
            else int(round(maximum_examples * float(dataset_fractions[dataset])))
        )
        choices = rng.choice(len(pool), size=count, replace=count > len(pool))
        selected.append(pool[choices])
        assigned += count
    refs = np.concatenate(selected, axis=0)
    rng.shuffle(refs)
    return refs


def class_counts(
    corpus: PolyphonicCorpus,
    target: str,
) -> tuple[np.ndarray, int]:
    if target not in {"active_bits", "onset_bits"}:
        raise ValueError(target)
    positives = np.zeros(corpus.pitch_classes, dtype=np.int64)
    total = 0
    for cached in corpus.labels:
        arrays = cached.arrays
        valid = arrays["valid"] > 0
        bits = np.asarray(arrays[target][valid], dtype=np.uint64)
        total += len(bits)
        for class_index in range(corpus.pitch_classes):
            mask = np.uint64(1) << np.uint64(class_index)
            positives[class_index] += int(np.count_nonzero(bits & mask))
    return positives, total


def dataset_balanced_class_counts(
    corpus: PolyphonicCorpus,
    target: str,
    dataset_fractions: Mapping[str, float],
    effective_total: int = 1_000_000,
) -> tuple[np.ndarray, int]:
    """Estimate class counts under the configured dataset sampling mixture."""
    datasets = {item.dataset_id for item in corpus.items}
    if set(dataset_fractions) != datasets:
        raise ValueError("Class-weight dataset fractions do not match the corpus.")
    if abs(sum(dataset_fractions.values()) - 1.0) > 1e-6:
        raise ValueError("Class-weight dataset fractions must sum to 1.0.")
    if effective_total < 1:
        raise ValueError("effective_total must be positive.")
    positive_by_dataset = {
        dataset: np.zeros(corpus.pitch_classes, dtype=np.int64)
        for dataset in datasets
    }
    total_by_dataset = {dataset: 0 for dataset in datasets}
    for cached in corpus.labels:
        arrays = cached.arrays
        valid = arrays["valid"] > 0
        bits = np.asarray(arrays[target][valid], dtype=np.uint64)
        dataset = cached.item.dataset_id
        total_by_dataset[dataset] += len(bits)
        for class_index in range(corpus.pitch_classes):
            mask = np.uint64(1) << np.uint64(class_index)
            positive_by_dataset[dataset][class_index] += int(
                np.count_nonzero(bits & mask)
            )
    rate = np.zeros(corpus.pitch_classes, dtype=np.float64)
    for dataset, fraction in dataset_fractions.items():
        total = total_by_dataset[dataset]
        if total < 1:
            raise ValueError(f"Dataset {dataset!r} has no valid frames.")
        rate += (
            float(fraction)
            * positive_by_dataset[dataset].astype(np.float64)
            / float(total)
        )
    return rate * float(effective_total), int(effective_total)


class PolyphonicSequence(tf.keras.utils.Sequence):
    def __init__(
        self,
        corpus: PolyphonicCorpus,
        batch_size: int,
        input_samples: int,
        normalization_gain: float,
        seed: int,
        refs: np.ndarray | None = None,
        pools: FramePools | None = None,
        dataset_pools: Mapping[str, FramePools] | None = None,
        dataset_fractions: Mapping[str, float] | None = None,
        examples_per_epoch: int | None = None,
        sampling_fractions: Mapping[str, float] | None = None,
        augmentation_gain_db: float = 0.0,
        shuffle: bool = False,
    ) -> None:
        super().__init__()
        self.corpus = corpus
        self.batch_size = int(batch_size)
        self.input_samples = int(input_samples)
        self.normalization_gain = float(normalization_gain)
        self.rng = np.random.default_rng(seed)
        self.pools = pools
        self.dataset_pools = None if dataset_pools is None else dict(dataset_pools)
        self.dataset_fractions = None if dataset_fractions is None else dict(dataset_fractions)
        self.examples_per_epoch = examples_per_epoch
        self.sampling_fractions = dict(sampling_fractions or {
            "onset": 0.30,
            "polyphonic": 0.30,
            "monophonic": 0.25,
            "silence": 0.15,
        })
        self.shuffle = bool(shuffle)
        self.augmentation_gain_db = float(augmentation_gain_db)
        if self.batch_size < 1 or self.input_samples < 1:
            raise ValueError("Invalid sequence dimensions.")
        if pools is None and self.dataset_pools is None and refs is None:
            raise ValueError("Either fixed refs or balanced pools are required.")
        if (pools is not None or self.dataset_pools is not None) and examples_per_epoch is None:
            raise ValueError("examples_per_epoch is required with pools.")
        if self.dataset_pools is not None:
            if not self.dataset_fractions:
                raise ValueError("dataset_fractions are required with dataset_pools.")
            if set(self.dataset_fractions) != set(self.dataset_pools):
                raise ValueError("dataset_fractions must match dataset_pools.")
            if abs(sum(self.dataset_fractions.values()) - 1.0) > 1e-6:
                raise ValueError("dataset_fractions must sum to 1.0.")
        if abs(sum(self.sampling_fractions.values()) - 1.0) > 1e-6:
            raise ValueError("sampling_fractions must sum to 1.0.")
        self.fixed_refs = None if refs is None else np.asarray(refs, np.int32)
        self.order = self._next_order()

    def _next_order(self) -> np.ndarray:
        if self.pools is None and self.dataset_pools is None:
            assert self.fixed_refs is not None
            order = self.fixed_refs.copy()
            if self.shuffle:
                self.rng.shuffle(order)
            return order
        assert self.examples_per_epoch is not None
        if self.dataset_pools is not None:
            assert self.dataset_fractions is not None
            dataset_parts: list[np.ndarray] = []
            assigned = 0
            datasets = list(self.dataset_fractions)
            for index, dataset_id in enumerate(datasets):
                count = (
                    self.examples_per_epoch - assigned
                    if index == len(datasets) - 1
                    else int(round(
                        self.examples_per_epoch
                        * float(self.dataset_fractions[dataset_id])
                    ))
                )
                dataset_parts.append(self._sample_pools(
                    self.dataset_pools[dataset_id], count
                ))
                assigned += count
            order = np.concatenate(dataset_parts, axis=0)
            self.rng.shuffle(order)
            return order
        assert self.pools is not None
        order = self._sample_pools(self.pools, self.examples_per_epoch)
        self.rng.shuffle(order)
        return order

    def _sample_pools(self, pools: FramePools, total: int) -> np.ndarray:
        sampled: list[np.ndarray] = []
        assigned = 0
        names = list(self.sampling_fractions)
        for index, name in enumerate(names):
            fraction = float(self.sampling_fractions[name])
            count = (
                total - assigned
                if index == len(names) - 1
                else int(round(total * fraction))
            )
            pool = getattr(pools, name)
            selection = self.rng.choice(
                len(pool), size=count, replace=count > len(pool)
            )
            sampled.append(pool[selection])
            assigned += count
        return np.concatenate(sampled, axis=0)

    def __len__(self) -> int:
        return max(1, math.ceil(len(self.order) / self.batch_size))

    def __getitem__(self, batch_index: int):
        selected = self.order[
            batch_index * self.batch_size:(batch_index + 1) * self.batch_size
        ]
        if len(selected) == 0:
            raise IndexError(batch_index)
        size = len(selected)
        classes = self.corpus.pitch_classes
        harmonics = self.corpus.harmonic_count
        audio = np.zeros((size, self.input_samples, 1), dtype=np.float32)
        time_mask = np.zeros((size, self.input_samples), dtype=np.float32)
        frame_target = np.zeros((size, classes), dtype=np.float32)
        onset_target = np.zeros((size, classes), dtype=np.float32)
        harmonic_amplitude = np.zeros((size, classes, harmonics), np.float32)
        harmonic_offset = np.zeros((size, classes, harmonics), np.float32)
        harmonic_valid = np.zeros((size, classes, harmonics), np.float32)
        class_bits = np.arange(classes, dtype=np.uint64)

        for row, (recording_index, frame_index) in enumerate(selected):
            recording_index = int(recording_index)
            frame_index = int(frame_index)
            cached = self.corpus.labels[recording_index]
            arrays = cached.arrays
            waveform = self.corpus.audio(recording_index)
            end_sample = min(
                len(waveform), (frame_index + 1) * self.corpus.hop_size
            )
            start_sample = max(0, end_sample - self.input_samples)
            visible = end_sample - start_sample
            segment = np.asarray(
                waveform[start_sample:end_sample], dtype=np.float32
            )
            if np.issubdtype(waveform.dtype, np.integer):
                segment /= max(abs(np.iinfo(waveform.dtype).min), 1)
            audio[row, -visible:, 0] = segment
            gain = self.normalization_gain
            if self.augmentation_gain_db > 0.0:
                gain *= 10.0 ** (
                    self.rng.uniform(
                        -self.augmentation_gain_db, self.augmentation_gain_db
                    ) / 20.0
                )
            audio[row, :, 0] *= gain
            np.clip(audio[row, :, 0], -1.0, 1.0, out=audio[row, :, 0])
            time_mask[row, -visible:] = 1.0

            active_bits = np.uint64(arrays["active_bits"][frame_index])
            onset_bits = np.uint64(arrays["onset_bits"][frame_index])
            frame_target[row] = ((active_bits >> class_bits) & 1).astype(np.float32)
            onset_target[row] = ((onset_bits >> class_bits) & 1).astype(np.float32)

            for pitch_index, note_id in zip(
                arrays["slot_pitch"][frame_index],
                arrays["slot_note_id"][frame_index],
            ):
                pitch_index = int(pitch_index)
                note_id = int(note_id)
                if pitch_index < 0 or note_id < 0:
                    continue
                if not arrays["note_harmonic_valid"][note_id]:
                    continue
                valid = np.asarray(
                    arrays["note_harmonic_present"][note_id], np.float32
                )
                harmonic_valid[row, pitch_index] = valid
                harmonic_amplitude[row, pitch_index] = np.asarray(
                    arrays["note_harmonic_amplitude"][note_id], np.float32
                )
                harmonic_offset[row, pitch_index] = np.asarray(
                    arrays["note_harmonic_offset_cents"][note_id], np.float32
                )

        inputs = {"audio": audio, "time_mask": time_mask}
        targets = {
            "frame": frame_target,
            "onset": onset_target,
            "harmonic_amplitude": np.concatenate(
                [harmonic_amplitude, harmonic_valid], axis=-1
            ),
            "harmonic_offset_cents": np.concatenate(
                [harmonic_offset, harmonic_valid, harmonic_amplitude], axis=-1
            ),
        }
        return inputs, targets

    def on_epoch_end(self) -> None:
        self.order = self._next_order()
