from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
import tensorflow as tf

from src.polyphonic import smoke_neural_independent_note as gate


def _item(
    source_id: str,
    dataset_id: str,
    player_id: str,
    group_id: str,
    split: str = "train",
):
    return SimpleNamespace(
        source_id=source_id,
        dataset_id=dataset_id,
        player_id=player_id,
        group_id=group_id,
        split=split,
    )


class TrainOnlyPartitionTest(unittest.TestCase):
    def test_train_items_refuses_test_and_returns_only_train(self) -> None:
        train = _item("train", "GAPS", "p", "g", "train")
        validation = _item("validation", "GAPS", "p", "v", "validation")
        self.assertEqual(gate.train_items_only([train, validation]), [train])
        with self.assertRaisesRegex(RuntimeError, "test rows"):
            gate.train_items_only([
                train,
                _item("locked", "GAPS", "p", "t", "test"),
            ])

    def test_corpus_aware_keys(self) -> None:
        self.assertEqual(
            gate.leakage_group_key(
                _item("gs-a", "GuitarSet", "Player 00", "recording-a")
            ),
            gate.leakage_group_key(
                _item("gs-b", "GuitarSet", "player-00", "recording-b")
            ),
        )
        self.assertEqual(
            gate.leakage_group_key(
                _item("gaps-a", "GAPS", "José Smith", "score-a")
            ),
            gate.leakage_group_key(
                _item("gaps-b", "GAPS", "Jose-Smith", "score-b")
            ),
        )
        self.assertEqual(
            gate.leakage_group_key(
                _item("direct", "Guitar-TECHS direct", "p", "song-a")
            ),
            gate.leakage_group_key(
                _item("mic", "Guitar-TECHS mic", "p", "song-a")
            ),
        )
        self.assertNotEqual(
            gate.leakage_group_key(
                _item("gaps-unknown-a", "GAPS", "gaps_unknown", "score-a")
            ),
            gate.leakage_group_key(
                _item("gaps-unknown-b", "GAPS", "gaps_unknown", "score-b")
            ),
        )

    def test_partition_is_deterministic_disjoint_and_keeps_paired_views(self) -> None:
        items = []
        for index in range(6):
            items.extend([
                _item(
                    f"gs-{index}-a", "GuitarSet", f"player-{index}",
                    f"guitarset-recording-{index}-a",
                ),
                _item(
                    f"gs-{index}-b", "GuitarSet", f"player-{index}",
                    f"guitarset-recording-{index}-b",
                ),
                _item(
                    f"gaps-{index}", "GAPS", f"performer-{index}",
                    f"score-{index}",
                ),
                _item(
                    f"direct-{index}", "Guitar-TECHS direct", "performer",
                    f"technique-{index}",
                ),
                _item(
                    f"mic-{index}", "Guitar-TECHS mic", "performer",
                    f"technique-{index}",
                ),
            ])
        first, first_report = gate.partition_train_groups(items, seed=47)
        second, second_report = gate.partition_train_groups(items, seed=47)
        self.assertEqual(first_report, second_report)
        self.assertEqual(
            {name: [item.source_id for item in rows] for name, rows in first.items()},
            {name: [item.source_id for item in rows] for name, rows in second.items()},
        )
        folds_by_key = {}
        for fold, rows in first.items():
            self.assertEqual(
                {item.dataset_id for item in rows},
                {"GuitarSet", "GAPS", "Guitar-TECHS direct", "Guitar-TECHS mic"},
            )
            for item in rows:
                key = gate.leakage_group_key(item)
                if key in folds_by_key:
                    self.assertEqual(folds_by_key[key], fold)
                else:
                    folds_by_key[key] = fold
        for index in range(6):
            direct = next(
                fold for fold, rows in first.items()
                if any(item.source_id == f"direct-{index}" for item in rows)
            )
            mic = next(
                fold for fold, rows in first.items()
                if any(item.source_id == f"mic-{index}" for item in rows)
            )
            self.assertEqual(direct, mic)


class CalibrationGateTest(unittest.TestCase):
    @staticmethod
    def _calibration_rows(gs_positive=50, gs_negative=20, gaps_positive=50):
        target = np.asarray(
            [1.0] * gs_positive
            + [0.0] * gs_negative
            + [1.0] * gaps_positive,
            dtype=np.float32,
        )
        weight = np.ones_like(target)
        corpus = np.asarray(
            ["GuitarSet"] * (gs_positive + gs_negative)
            + ["GAPS"] * gaps_positive,
            dtype=object,
        )
        return target, weight, corpus

    def test_calibration_minimums_pass_and_fail_closed(self) -> None:
        target, weight, corpus = self._calibration_rows()
        report = gate._class_report(
            target, weight, corpus, require_calibration_minimums=True
        )
        self.assertEqual(report["by_corpus"]["GuitarSet"]["independent_note"], 50)
        with self.assertRaisesRegex(RuntimeError, "50 positives"):
            gate._class_report(
                *self._calibration_rows(gs_positive=49),
                require_calibration_minimums=True,
            )
        with self.assertRaisesRegex(RuntimeError, "20 negatives"):
            gate._class_report(
                *self._calibration_rows(gs_negative=19),
                require_calibration_minimums=True,
            )

    def test_corpus_without_supervision_cannot_disappear(self) -> None:
        target = np.asarray([1.0, 0.0, 0.0], dtype=np.float32)
        weight = np.asarray([1.0, 1.0, 0.0], dtype=np.float32)
        corpus = np.asarray(
            ["GuitarSet", "GuitarSet", "GAPS"], dtype=object
        )
        with self.assertRaisesRegex(RuntimeError, "GAPS"):
            gate._class_report(target, weight, corpus)

    def test_least_aggressive_threshold_meets_fixed_gates(self) -> None:
        target, weight, corpus = self._calibration_rows()
        probability = np.asarray(
            [0.90] * 50 + [0.021] * 10 + [0.80] * 10 + [0.90] * 50,
            dtype=np.float32,
        )
        result = gate.select_least_aggressive_threshold(
            probability, target, weight, corpus
        )
        self.assertEqual(result["selected_threshold"], 0.03)
        self.assertTrue(result["brier_better_than_constant"])
        selected = next(
            row for row in result["grid"]
            if row["threshold"] == result["selected_threshold"]
        )
        self.assertGreaterEqual(selected["independent_recall"], 0.98)
        self.assertGreaterEqual(selected["harmonic_only_removed_recall"], 0.05)
        self.assertTrue(all(
            value >= 0.95
            for value in selected["independent_recall_by_corpus"].values()
        ))

    def test_brier_must_beat_constant(self) -> None:
        target = np.asarray([0.0, 1.0] * 50, dtype=np.float32)
        probability = np.full_like(target, 0.5)
        weight = np.ones_like(target)
        corpus = np.asarray(["GuitarSet"] * len(target), dtype=object)
        result = gate.select_least_aggressive_threshold(
            probability, target, weight, corpus
        )
        self.assertFalse(result["brier_better_than_constant"])
        self.assertIsNone(result["selected_threshold"])


class RuntimeContractTest(unittest.TestCase):
    def test_force_cpu_is_applied_during_module_initialization(self) -> None:
        source = Path(gate.__file__).read_text(encoding="utf-8")
        force_index = source.index(
            '_FORCE_CPU = os.environ.get("MIDI_FORCE_CPU") == "1"'
        )
        import_index = source.index("import tensorflow as tf")
        visibility_index = source.index(
            'tf.config.set_visible_devices([], "GPU")'
        )
        self.assertLess(force_index, import_index)
        self.assertLess(import_index, visibility_index)

    def test_only_independent_note_layers_remain_trainable(self) -> None:
        inputs = tf.keras.Input(shape=(3,), name="input")
        backbone = tf.keras.layers.Dense(4, name="backbone")(inputs)
        output = tf.keras.layers.Dense(2, name="independent_note")(backbone)
        model = tf.keras.Model(inputs, output)
        report = gate.freeze_independent_note_only(model)
        self.assertEqual(report["trainable_weight_layers"], ["independent_note"])
        self.assertFalse(model.get_layer("backbone").trainable)

    def test_fit_queue_options_follow_installed_keras_signature(self) -> None:
        def keras2_fit(
            *, workers=None, use_multiprocessing=None, max_queue_size=None
        ):
            return None

        def keras3_fit(*, epochs=None):
            return None

        self.assertEqual(
            gate._fit_queue_options(keras2_fit),
            {
                "workers": 1,
                "use_multiprocessing": False,
                "max_queue_size": 1,
            },
        )
        self.assertEqual(gate._fit_queue_options(keras3_fit), {})

    def test_source_snapshot_accepts_strict_archive_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit = "a" * 40
            archive = "b" * 64
            (root / ".source.env").write_text(
                f"commit={commit}\narchive_sha256={archive}\n", encoding="utf-8"
            )
            snapshot = gate.source_snapshot(root)
            self.assertEqual(snapshot["commit"], commit)
            self.assertEqual(snapshot["archive_sha256"], archive)
            self.assertTrue(snapshot["archive_snapshot"])
            self.assertFalse(snapshot["dirty"])
            (root / ".source.env").write_text(
                f"commit={commit}\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "Malformed"):
                gate.source_snapshot(root)

    def test_run_closes_registered_corpora_in_finally(self) -> None:
        corpus = mock.Mock()

        def fail(_args, registry):
            registry.extend([corpus, corpus])
            raise RuntimeError("planned")

        with mock.patch.object(gate, "_run_with_corpus_registry", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "planned"):
                gate.run(SimpleNamespace())
        corpus.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
