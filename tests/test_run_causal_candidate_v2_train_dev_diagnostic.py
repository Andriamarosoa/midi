from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from src.polyphonic.mine_decoder_candidates import BoundedMiningProtocol
from src.polyphonic import run_causal_candidate_v2_train_dev_diagnostic as runner


@dataclass(frozen=True)
class _Item:
    dataset_id: str
    source_id: str
    capture_id: str
    group_id: str
    split: str = "train"


@dataclass(frozen=True)
class _Record:
    partition: str


class _Snapshot:
    def provenance_for_snapshot_item(self, item: _Item) -> _Record:
        return _Record(item.source_id.split("/", 1)[0])


class _Context:
    def __init__(self, values: dict[str, tuple[_Item, ...]]) -> None:
        self._values = values
        self.validated_snapshot = _Snapshot()

    def items_for_partition(self, partition: str) -> tuple[_Item, ...]:
        return self._values[partition]


class SealedV2TrainDevDiagnosticRunnerTests(unittest.TestCase):
    @staticmethod
    def _v3_policy() -> BoundedMiningProtocol:
        datasets = (
            "gaps_poly_mix",
            "guitar_techs_poly_directinput",
            "guitar_techs_poly_micamp",
            "guitarset_poly_mix",
        )
        return BoundedMiningProtocol(
            manifest_sha256="a" * 64,
            partition_plan_sha256="b" * 64,
            asset_evidence_sha256="c" * 64,
            checkpoint_sha256="d" * 64,
            model_config_sha256="e" * 64,
            decoder_config_sha256="f" * 64,
            audio_evidence_config_sha256="0" * 64,
            dataset_ids=datasets,
            recordings_per_dataset_partition=(
                ("gaps_poly_mix", 6),
                ("guitar_techs_poly_directinput", 6),
                ("guitar_techs_poly_micamp", 6),
                ("guitarset_poly_mix", 12),
            ),
            maximum_attempts_per_recording=64,
            schema_version=3,
            purpose="decoder_candidate_guitarset_expansion_train_only_mining_v3",
            minimum_targets_per_dataset_partition_class=8,
            minimum_targets_per_partition_class=75,
        )

    @staticmethod
    def _context(*, dev_split: str = "train") -> _Context:
        counts = {
            "gaps_poly_mix": 6,
            "guitar_techs_poly_directinput": 6,
            "guitar_techs_poly_micamp": 6,
            "guitarset_poly_mix": 12,
        }
        values: dict[str, tuple[_Item, ...]] = {}
        for partition in ("fit", "dev", "calibration"):
            rows: list[_Item] = []
            for dataset_id, count in counts.items():
                rows.extend(
                    _Item(
                        dataset_id=dataset_id,
                        source_id=f"{partition}/{dataset_id}-{index:02d}",
                        capture_id=f"{partition}-{dataset_id}-{index:02d}",
                        group_id=f"{partition}-{dataset_id}-{index:02d}",
                        split=dev_split if partition == "dev" else "train",
                    )
                    for index in range(count)
                )
            values[partition] = tuple(rows)
        return _Context(values)

    @staticmethod
    def _protocol() -> dict[str, object]:
        return {
            "cohort": {
                "selection_source": {
                    "recordings_per_dataset": {
                        "gaps_poly_mix": 6,
                        "guitar_techs_poly_directinput": 6,
                        "guitar_techs_poly_micamp": 6,
                        "guitarset_poly_mix": 12,
                    },
                },
            },
        }

    def test_execution_acknowledgement_precedes_paths_or_tensorflow(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                RuntimeError, "DECODER_CANDIDATE_V2_DIAGNOSTIC_EXECUTE=1"
            ):
                runner.run_sealed_v2_train_dev_diagnostic()

    def test_import_does_not_load_tensorflow_before_the_preflight(self) -> None:
        code = (
            "import sys; import src.polyphonic.run_causal_candidate_v2_train_dev_diagnostic; "
            "raise SystemExit(int('tensorflow' in sys.modules))"
        )
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parents[1],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_paths_are_internal_and_preserve_v1_cr_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            worker_root = Path(directory) / "midi-worker"
            repository_root = worker_root / "repository"
            repository_root.mkdir(parents=True)
            paths = runner.sealed_v2_diagnostic_paths(repository_root, worker_root)
        self.assertEqual(paths.run_dir.name, runner.V2_DIAGNOSTIC_RUN_DIRECTORY_NAME)
        self.assertEqual(paths.protocol_path.name, "causal_candidate_fit_v2_train_dev_diagnostic_protocol.json")
        self.assertEqual(paths.fit_report_path.parent.name, runner.FIT_ARTIFACT_DIRECTORY_NAME)
        self.assertTrue(paths.fit_report_path.parent.name.endswith("\r"))
        self.assertEqual(paths.partition_plan_path.name, runner.PARTITION_PLAN_FILENAME)
        self.assertEqual(paths.asset_evidence_path.name, runner.ASSET_EVIDENCE_FILENAME)

    def test_derives_exact_v3_dev_cohort_without_hard_coded_recording_keys(self) -> None:
        items = runner._derive_v3_dev_diagnostic_items(
            self._context(), self._v3_policy(), self._protocol(),
        )
        self.assertEqual(len(items), 30)
        self.assertEqual({item.source_id.split("/", 1)[0] for item in items}, {"dev"})
        self.assertEqual(
            {dataset: sum(item.dataset_id == dataset for item in items) for dataset in {
                "gaps_poly_mix", "guitar_techs_poly_directinput",
                "guitar_techs_poly_micamp", "guitarset_poly_mix",
            }},
            {
                "gaps_poly_mix": 6,
                "guitar_techs_poly_directinput": 6,
                "guitar_techs_poly_micamp": 6,
                "guitarset_poly_mix": 12,
            },
        )
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertNotIn("guitarset_04_BN1", source)

    def test_derivation_rejects_a_validation_item_before_model_loading(self) -> None:
        with self.assertRaisesRegex(PermissionError, "non-train item"):
            runner._derive_v3_dev_diagnostic_items(
                self._context(dev_split="validation"), self._v3_policy(), self._protocol(),
            )

    def test_runner_is_no_cli_and_forces_the_v2_placement(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertNotIn("argparse", source)
        self.assertIn('V2_DIAGNOSTIC_EXECUTE_ENV = "DECODER_CANDIDATE_V2_DIAGNOSTIC_EXECUTE"', source)
        self.assertIn("CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON", source)
        self.assertIn("sealed_train_only_corpus_opener=context.open_recording", source)
        self.assertIn(
            "sealed_audio_evidence_metadata=sealed.audio_evidence_metadata",
            source,
        )
        self.assertIn("write_report=False", source)

    def test_sealed_audio_policy_is_parsed_from_the_same_hashed_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audio-policy.json"
            payload = {"onset_adapt_temporal_background": True}
            raw = (json.dumps(payload) + "\n").encode("utf-8")
            path.write_bytes(raw)
            metadata, digest = runner._load_sealed_audio_evidence_metadata(
                path, hashlib.sha256(raw).hexdigest(),
            )
        self.assertEqual(digest, hashlib.sha256(raw).hexdigest())
        self.assertEqual(metadata, {"audio_evidence": payload})

    def test_sealed_audio_policy_rejects_the_non_adaptive_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audio-policy.json"
            raw = b'{"onset_adapt_temporal_background": false}\n'
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "must enable"):
                runner._load_sealed_audio_evidence_metadata(
                    path, hashlib.sha256(raw).hexdigest(),
                )


if __name__ == "__main__":
    unittest.main()
