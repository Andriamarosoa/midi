from __future__ import annotations

import csv
import tempfile
import unittest
import wave
import zipfile
from pathlib import Path

import numpy as np

from src.polyphonic.data import (
    PolyphonicCorpus,
    PolyphonicSequence,
    FramePools,
    build_frame_pools,
    class_counts,
    dataset_balanced_class_counts,
    load_manifest,
    sampler_effective_class_counts,
)
from src.polyphonic.keras_compat import predict_compat
from src.polyphonic.train import _fit_queue_options, _weights


class PolyphonicDataTests(unittest.TestCase):
    def test_predict_compat_omits_workers_for_keras3(self) -> None:
        calls = []

        class Legacy:
            def predict(self, inputs, verbose=0, workers=1):
                calls.append(("legacy", inputs, verbose, workers))
                return inputs

        class Keras3:
            def predict(self, inputs, verbose=0):
                calls.append(("keras3", inputs, verbose))
                return inputs

        self.assertEqual(
            predict_compat(Legacy(), "legacy-input", verbose=1, workers=4),
            "legacy-input",
        )
        self.assertEqual(
            predict_compat(Keras3(), "keras3-input", verbose=1, workers=4),
            "keras3-input",
        )
        self.assertEqual(
            calls,
            [
                ("legacy", "legacy-input", 1, 4),
                ("keras3", "keras3-input", 1),
            ],
        )

    def test_fit_queue_options_follow_installed_keras_signature(self) -> None:
        def legacy_fit(
            sequence,
            workers=1,
            use_multiprocessing=False,
            max_queue_size=10,
        ):
            return sequence

        def keras3_fit(sequence, epochs=1):
            return sequence, epochs

        self.assertEqual(
            _fit_queue_options(legacy_fit, workers=4),
            {
                "workers": 4,
                "use_multiprocessing": False,
                "max_queue_size": 2,
            },
        )
        self.assertEqual(_fit_queue_options(keras3_fit, workers=4), {})

    def test_extensionless_numpy_audio_is_loaded_by_magic_signature(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "audio.npy"
            waveform = np.linspace(-1.0, 1.0, 16, dtype=np.float32)
            np.save(original, waveform, allow_pickle=False)
            truncated = root / "audio_truncated"
            original.replace(truncated)

            labels_path = root / "labels.npz"
            np.savez_compressed(
                labels_path,
                active_bits=np.asarray([0], np.uint64),
                onset_bits=np.asarray([0], np.uint64),
                polyphony=np.asarray([0], np.uint8),
                valid=np.ones(1, np.uint8),
                slot_pitch=np.asarray([[-1]], np.int8),
                slot_note_id=np.asarray([[-1]], np.int32),
                note_harmonic_present=np.ones((1, 1), np.uint8),
                note_harmonic_amplitude=np.ones((1, 1), np.float16),
                note_harmonic_offset_cents=np.zeros((1, 1), np.float16),
                note_harmonic_valid=np.ones(1, np.uint8),
                sample_rate=np.int32(8),
                hop_size=np.int32(4),
                audio_frames=np.int64(len(waveform)),
                midi_min=np.int16(40),
                midi_max=np.int16(40),
            )
            manifest_path = root / "manifest.csv"
            fields = [
                "source_id", "dataset_id", "player_id", "group_id", "split",
                "audio_path", "audio_member", "labels_path", "capture_id",
                "license_id",
            ]
            with manifest_path.open(
                "w", newline="", encoding="utf-8"
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({
                    "source_id": "truncated",
                    "dataset_id": "unit",
                    "player_id": "p",
                    "group_id": "g",
                    "split": "train",
                    "audio_path": truncated,
                    "audio_member": "",
                    "labels_path": labels_path,
                    "capture_id": "clean",
                    "license_id": "unit",
                })

            with PolyphonicCorpus(load_manifest(manifest_path)) as corpus:
                loaded = corpus.audio(0).copy()

            np.testing.assert_array_equal(loaded, waveform)

    def test_manifest_paths_are_portable_between_windows_and_linux(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest_path = Path(temporary) / "manifest.csv"
            fields = [
                "source_id", "dataset_id", "player_id", "group_id", "split",
                "audio_path", "audio_member", "labels_path", "capture_id",
                "license_id",
            ]
            with manifest_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({
                    "source_id": "portable",
                    "dataset_id": "unit",
                    "player_id": "p",
                    "group_id": "g",
                    "split": "train",
                    "audio_path": r"data\processed\audio.npy",
                    "audio_member": "",
                    "labels_path": r"data\processed\labels.npz",
                    "capture_id": "clean",
                    "license_id": "unit",
                })

            item = load_manifest(manifest_path)[0]

        self.assertEqual(
            item.audio_path.as_posix(), "data/processed/audio.npy"
        )
        self.assertEqual(
            item.labels_path.as_posix(), "data/processed/labels.npz"
        )

    def test_softened_class_weights_preserve_rarity_without_saturation(self) -> None:
        positives = np.asarray([1.0, 4.0], np.float64)

        weights = _weights(
            positives, total=5, maximum=20.0, exponent=0.5,
        )

        np.testing.assert_allclose(weights, [2.0, 1.0])
        with self.assertRaisesRegex(ValueError, "exponent"):
            _weights(positives, total=5, maximum=20.0, exponent=0.0)

    def test_class_weights_follow_dataset_mixture_not_raw_size(self) -> None:
        class Item:
            def __init__(self, dataset_id: str):
                self.dataset_id = dataset_id

        class Cached:
            def __init__(self, dataset_id: str, bits: list[int]):
                self.item = Item(dataset_id)
                self.arrays = {
                    "valid": np.ones(len(bits), np.uint8),
                    "active_bits": np.asarray(bits, np.uint64),
                }

        class Corpus:
            pitch_classes = 2
            items = [Item("small"), Item("large")]
            labels = [
                Cached("small", [1, 1]),
                Cached("large", [0, 0, 0, 0, 0, 0, 0, 2]),
            ]

        positives, total = dataset_balanced_class_counts(
            Corpus(), "active_bits", {"small": 0.5, "large": 0.5},
            effective_total=800,
        )
        self.assertEqual(total, 800)
        self.assertEqual(positives.tolist(), [400.0, 50.0])

    def test_dataset_balancing_is_independent_from_dataset_size(self) -> None:
        class DummyCorpus:
            pass

        refs_a = np.asarray([[0, 0], [0, 1]], np.int32)
        refs_b = np.asarray([[1, 0], [1, 1]], np.int32)
        pools = {
            "a": FramePools(refs_a, refs_a, refs_a, refs_a),
            "b": FramePools(refs_b, refs_b, refs_b, refs_b),
        }
        sequence = PolyphonicSequence(
            DummyCorpus(), batch_size=4, input_samples=8,
            normalization_gain=1.0, seed=3,
            dataset_pools=pools, dataset_fractions={"a": 0.5, "b": 0.5},
            examples_per_epoch=20,
        )
        self.assertEqual(int(np.sum(sequence.order[:, 0] == 0)), 10)
        self.assertEqual(int(np.sum(sequence.order[:, 0] == 1)), 10)

    def test_class_counts_follow_effective_sampler_mixture(self) -> None:
        class Item:
            def __init__(self, dataset_id: str):
                self.dataset_id = dataset_id

        class Cached:
            def __init__(
                self,
                dataset_id: str,
                active_bits: list[int],
                onset_bits: list[int],
            ):
                self.item = Item(dataset_id)
                self.arrays = {
                    "active_bits": np.asarray(active_bits, np.uint64),
                    "onset_bits": np.asarray(onset_bits, np.uint64),
                }

        class Corpus:
            pitch_classes = 2
            labels = [
                Cached("a", [1, 1, 2, 1, 0], [1, 1, 0, 0, 0]),
                Cached("b", [2, 3, 1, 2, 0], [2, 0, 0, 0, 0]),
            ]

        def refs(recording_index: int, *frames: int) -> np.ndarray:
            return np.asarray(
                [[recording_index, frame] for frame in frames], np.int32
            )

        pools = {
            "a": FramePools(
                onset=refs(0, 0, 1),
                polyphonic=refs(0, 2),
                monophonic=refs(0, 3),
                silence=refs(0, 4),
            ),
            "b": FramePools(
                onset=refs(1, 0),
                polyphonic=refs(1, 1),
                monophonic=refs(1, 2, 3),
                silence=refs(1, 4),
            ),
        }
        dataset_fractions = {"a": 0.75, "b": 0.25}
        sampling_fractions = {
            "onset": 0.20,
            "polyphonic": 0.30,
            "monophonic": 0.40,
            "silence": 0.10,
        }

        onset_positive, total = sampler_effective_class_counts(
            Corpus(),
            "onset_bits",
            pools,
            dataset_fractions,
            sampling_fractions,
            effective_total=1_000,
        )
        frame_positive, _ = sampler_effective_class_counts(
            Corpus(),
            "active_bits",
            pools,
            dataset_fractions,
            sampling_fractions,
            effective_total=1_000,
        )

        self.assertEqual(total, 1_000)
        np.testing.assert_allclose(onset_positive, [150.0, 50.0])
        np.testing.assert_allclose(frame_positive, [575.0, 400.0])

    def test_effective_counts_reject_incomplete_sampling_mixture(self) -> None:
        class Corpus:
            pitch_classes = 1
            labels = []

        empty = np.empty((0, 2), np.int32)
        pools = {"all": FramePools(empty, empty, empty, empty)}
        with self.assertRaisesRegex(ValueError, "sampling fractions"):
            sampler_effective_class_counts(
                Corpus(),
                "onset_bits",
                pools,
                {"all": 1.0},
                {"onset": 1.0},
            )

    def test_compact_labels_are_materialized_as_causal_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wav = root / "audio.wav"
            samples = np.arange(32, dtype=np.int16)
            with wave.open(str(wav), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(8)
                handle.writeframes(samples.tobytes())
            archive_path = root / "audio.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.write(wav, "audio.wav")

            labels_path = root / "labels.npz"
            np.savez_compressed(
                labels_path,
                active_bits=np.asarray([0, 3, 3, 1, 0], np.uint64),
                onset_bits=np.asarray([0, 3, 0, 0, 0], np.uint64),
                polyphony=np.asarray([0, 2, 2, 1, 0], np.uint8),
                valid=np.ones(5, np.uint8),
                slot_pitch=np.asarray([
                    [-1, -1], [0, 1], [0, 1], [0, -1], [-1, -1],
                ], np.int8),
                slot_note_id=np.asarray([
                    [-1, -1], [0, 1], [0, 1], [0, -1], [-1, -1],
                ], np.int32),
                note_harmonic_present=np.ones((2, 2), np.uint8),
                note_harmonic_amplitude=np.ones((2, 2), np.float16),
                note_harmonic_offset_cents=np.zeros((2, 2), np.float16),
                note_harmonic_valid=np.ones(2, np.uint8),
                sample_rate=np.int32(8), hop_size=np.int32(4),
                audio_frames=np.int64(32), midi_min=np.int16(40),
                midi_max=np.int16(41), maximum_polyphony=np.int8(2),
                onset_width_hops=np.int8(1),
            )
            manifest_path = root / "manifest.csv"
            fields = [
                "source_id", "dataset_id", "player_id", "group_id", "split",
                "audio_path", "audio_member", "labels_path", "capture_id",
                "license_id",
            ]
            with manifest_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({
                    "source_id": "unit", "dataset_id": "unit",
                    "player_id": "p", "group_id": "g", "split": "train",
                    "audio_path": archive_path, "audio_member": "audio.wav",
                    "labels_path": labels_path, "capture_id": "clean",
                    "license_id": "unit",
                })

            corpus = PolyphonicCorpus(load_manifest(manifest_path))
            pools = build_frame_pools(corpus)
            sequence = PolyphonicSequence(
                corpus, batch_size=1, input_samples=8, normalization_gain=1.0,
                seed=1, refs=np.asarray([[0, 1]], np.int32),
            )
            inputs, targets = sequence[0]
            leveled_sequence = PolyphonicSequence(
                corpus,
                batch_size=1,
                input_samples=8,
                normalization_gain=1.0,
                seed=1,
                refs=np.asarray([[0, 1]], np.int32),
                input_gain_by_frame=[
                    np.full(5, 2.0, dtype=np.float32)
                ],
            )
            leveled_inputs, _ = leveled_sequence[0]
            partial_start = PolyphonicSequence(
                corpus,
                batch_size=1,
                input_samples=8,
                normalization_gain=1.0,
                seed=1,
                refs=np.asarray([[0, 0]], np.int32),
            )[0][0]
            full_start = PolyphonicSequence(
                corpus,
                batch_size=1,
                input_samples=8,
                normalization_gain=1.0,
                seed=1,
                refs=np.asarray([[0, 0]], np.int32),
                full_context_from_start=True,
            )[0][0]
            with self.assertRaisesRegex(ValueError, "one value per frame"):
                PolyphonicSequence(
                    corpus,
                    batch_size=1,
                    input_samples=8,
                    normalization_gain=1.0,
                    seed=1,
                    refs=np.asarray([[0, 0]], np.int32),
                    input_gain_by_frame=[
                        np.ones((5, 1), dtype=np.float32)
                    ],
                )
            positives, total = class_counts(corpus, "active_bits")
            corpus.close()

        self.assertEqual(pools.sizes, {
            "onset": 1, "polyphonic": 1, "monophonic": 1, "silence": 2,
        })
        self.assertEqual(targets["frame"].tolist(), [[1.0, 1.0]])
        self.assertEqual(targets["onset"].tolist(), [[1.0, 1.0]])
        self.assertEqual(inputs["audio"].shape, (1, 8, 1))
        self.assertEqual(inputs["time_mask"].sum(), 8.0)
        np.testing.assert_allclose(
            leveled_inputs["audio"],
            inputs["audio"] * 2.0,
        )
        self.assertEqual(partial_start["time_mask"].sum(), 4.0)
        self.assertEqual(full_start["time_mask"].sum(), 8.0)
        self.assertEqual(positives.tolist(), [3, 2])
        self.assertEqual(total, 5)


if __name__ == "__main__":
    unittest.main()
