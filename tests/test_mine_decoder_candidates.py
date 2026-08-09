"""Tests sans TensorFlow pour le mineur candidat borné train-only."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.polyphonic.decoder_candidate_labels import CausalCandidateLabelBatch
from src.polyphonic.mine_decoder_candidates import (
    BOUNDED_MINING_PURPOSE,
    EXTENDED_MINING_PURPOSE,
    BoundedMiningProtocol,
    _require_expected_git_commit,
    _representation_gate,
    _select_bounded_items,
    run_bounded_train_only_mining,
)


DATASETS = (
    "gaps_poly_mix",
    "guitar_techs_poly_directinput",
    "guitar_techs_poly_micamp",
    "guitarset_poly_mix",
)
PARTITIONS = ("fit", "dev", "calibration")


class _Item:
    def __init__(self, dataset_id: str, partition: str, ordinal: int = 0) -> None:
        self.dataset_id = dataset_id
        self.source_id = f"{partition}-{dataset_id}-{ordinal}-source"
        self.group_id = f"{partition}-{dataset_id}-{ordinal}-group"
        self.capture_id = f"{partition}-{dataset_id}-{ordinal}-capture"


class _Provenance:
    def __init__(self, partition: str) -> None:
        self.partition = partition


class _Snapshot:
    def provenance_for_snapshot_item(self, item: _Item) -> _Provenance:
        return _Provenance(item.source_id.split("-", 1)[0])


class _Context:
    def __init__(
        self,
        *,
        manifest_sha256: str,
        plan_sha256: str,
        evidence_sha256: str,
        items_per_dataset_partition: int = 1,
    ) -> None:
        self.snapshot = type("Snapshot", (), {"manifest_sha256": manifest_sha256})()
        self.persisted_plan = type("Plan", (), {"sha256": plan_sha256})()
        self.persisted_asset_evidence = type("Evidence", (), {"sha256": evidence_sha256})()
        self.validated_snapshot = _Snapshot()
        self._items = {
            partition: tuple(
                _Item(dataset, partition, ordinal)
                for dataset in DATASETS
                for ordinal in range(items_per_dataset_partition)
            )
            for partition in PARTITIONS
        }

    def items_for_partition(self, partition: str) -> tuple[_Item, ...]:
        return self._items[partition]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _batch(item: _Item, partition: str, *, manifest: str, plan: str) -> CausalCandidateLabelBatch:
    return CausalCandidateLabelBatch(
        manifest_sha256=manifest,
        partition_plan_sha256=plan,
        recording_identity=(item.dataset_id, item.source_id, item.capture_id),
        partition=partition,
        labels=(),
        total_attempts=0,
        retained_attempts=0,
        dropped_attempts=0,
        decoder_noteons=0,
        causal_matchable_decoder_noteons=0,
        full_flow_invalid_frame=0,
        full_flow_outside_audio=0,
        causal_false_decoder_noteons=0,
        instrumented_decoder_noteons=0,
        uninstrumented_decoder_noteons=0,
        uninstrumented_decoder_noteons_by_reason=(),
        gate_eligible_emitted_noteons=0,
        excluded_invalid_frame=0,
        excluded_outside_audio=0,
        reference_noteons=0,
        matched_reference_noteons=0,
        matched_reference_noteons_excluded_from_fit=0,
        missed_reference_noteons=0,
    )


class BoundedCandidateMiningTests(unittest.TestCase):
    @staticmethod
    def _initialize_clean_git_repository(root: Path) -> str:
        """Make a minimal clean repository while ignoring generated fixtures."""
        (root / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
        for command in (
            ("git", "init", "--quiet"),
            ("git", "add", ".gitignore"),
            ("git", "-c", "user.name=Bounded Test", "-c", "user.email=test@example.invalid", "commit", "--quiet", "-m", "fixture"),
        ):
            subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
        return subprocess.check_output(
            ("git", "rev-parse", "HEAD"), cwd=root, text=True
        ).strip()

    def _write_inputs(self, root: Path, *, checkpoint_contents: bytes = b"checkpoint") -> dict[str, Path]:
        manifest = root / "manifest.csv"
        manifest.write_text("placeholder\n", encoding="utf-8")
        plan = root / "plan.json"
        plan.write_text("plan\n", encoding="utf-8")
        evidence = root / "evidence.json"
        evidence.write_text("evidence\n", encoding="utf-8")
        checkpoint = root / "checkpoint.keras"
        checkpoint.write_bytes(checkpoint_contents)
        model = root / "model.yaml"
        model.write_text(
            "dataset:\n  manifest: " + str(manifest).replace("\\", "/") +
            "\n  input_samples: 16\ntrain:\n  batch_size: 1\n",
            encoding="utf-8",
        )
        decoder = root / "decoder.json"
        decoder.write_text(
            json.dumps({
                "midi_min": 40, "midi_max": 76, "frame_on_threshold": 0.6,
                "strong_frame_threshold": 0.85, "frame_off_threshold": 0.36,
                "onset_threshold": 0.615, "activation_frames": 2,
                "release_frames": 3, "minimum_retrigger_frames": 14,
                "silence_release_frames": 14, "maximum_polyphony": 6,
                "harmonic_suppression_strength": 0.25,
                "harmonic_tolerance_cents": 35.0, "audio_onset_lookback_frames": 10,
                "unattacked_frame_threshold": 0.9,
                "harmonic_support_threshold": 0.6,
                "recovery_release_grace_frames": 4,
                "chord_release_grace_frames": 6,
                "chord_formation_frames": 0,
                "independent_note_threshold": None,
            }, sort_keys=True),
            encoding="utf-8",
        )
        audio = root / "audio.json"
        audio.write_text("{}\n", encoding="utf-8")
        protocol = root / "protocol.json"
        payload = {
            "schema_version": 1,
            "purpose": BOUNDED_MINING_PURPOSE,
            "locked_test_used": False,
            "manifest_sha256": _sha256(manifest),
            "partition_plan_sha256": _sha256(plan),
            "asset_evidence_sha256": _sha256(evidence),
            "checkpoint_sha256": _sha256(checkpoint),
            "model_config_sha256": _sha256(model),
            "decoder_config_sha256": _sha256(decoder),
            "audio_evidence_config_sha256": _sha256(audio),
            "dataset_ids": list(DATASETS),
            "recordings_per_dataset_partition": 1,
            "maximum_attempts_per_recording": 8,
        }
        protocol.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return {
            "manifest": manifest, "plan": plan, "evidence": evidence,
            "checkpoint": checkpoint, "model": model, "decoder": decoder,
            "audio": audio, "protocol": protocol,
        }

    def test_protocol_requires_the_exact_closed_schema(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._write_inputs(root)
            protocol = BoundedMiningProtocol.from_path(paths["protocol"])
            self.assertEqual(protocol.dataset_ids, DATASETS)
            self.assertEqual(protocol.recordings_per_dataset_partition, 1)
            payload = json.loads(paths["protocol"].read_text(encoding="utf-8"))
            payload["locked_test_used"] = True
            paths["protocol"].write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PermissionError, "locked test"):
                BoundedMiningProtocol.from_path(paths["protocol"])

    def test_versioned_audio_policy_uses_a_cross_host_lf_digest(self) -> None:
        """The sealed versioned configs must not vary with CRLF/LF checkout."""
        repository = Path(__file__).resolve().parents[1]
        protocol = BoundedMiningProtocol.from_path(
            repository / "configs" / "decoder_candidate_bounded_mining_v1.json"
        )
        self.assertEqual(
            protocol.audio_evidence_config_sha256,
            "45edbb712415c5b62f10a1405678fc28cee083891131108b2875ce8f71abcd3e",
        )
        attributes = (repository / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn(
            "configs/polyphonic_audio_evidence_adaptive_temporal.json text eol=lf",
            attributes,
        )

    def test_extended_policy_a_protocol_is_six_deterministic_items_per_cell(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        baseline = BoundedMiningProtocol.from_path(
            repository / "configs" / "decoder_candidate_bounded_mining_v1.json"
        )
        extended = BoundedMiningProtocol.from_path(
            repository / "configs" / "decoder_candidate_extended_policy_a_6percell.json"
        )
        self.assertEqual(extended.recordings_per_dataset_partition, 6)
        self.assertEqual(extended.maximum_attempts_per_recording, 65536)
        self.assertEqual(extended.schema_version, 2)
        self.assertEqual(extended.purpose, EXTENDED_MINING_PURPOSE)
        self.assertEqual(extended.minimum_targets_per_dataset_partition_class, 8)
        self.assertEqual(extended.minimum_targets_per_partition_class, 75)
        self.assertEqual(extended.dataset_ids, baseline.dataset_ids)
        for field in (
            "manifest_sha256",
            "partition_plan_sha256",
            "asset_evidence_sha256",
            "checkpoint_sha256",
            "model_config_sha256",
            "decoder_config_sha256",
            "audio_evidence_config_sha256",
        ):
            self.assertEqual(getattr(extended, field), getattr(baseline, field))
        attributes = (repository / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn(
            "configs/decoder_candidate_extended_policy_a_6percell.json text eol=lf",
            attributes,
        )

    def test_extended_protocol_reports_coverage_shortfalls_without_authorizing_fit(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        protocol = BoundedMiningProtocol.from_path(
            repository / "configs" / "decoder_candidate_extended_policy_a_6percell.json"
        )
        balanced = SimpleNamespace(
            dataset_partition_target_counts=tuple(
                (dataset, partition, target, 75)
                for dataset in DATASETS
                for partition in PARTITIONS
                for target in (0, 1)
            )
        )
        self.assertEqual(_representation_gate(protocol, balanced), {
            "required": True,
            "passed": True,
            "minimum_targets_per_dataset_partition_class": 8,
            "minimum_targets_per_partition_class": 75,
            "shortfalls": [],
        })
        insufficient = SimpleNamespace(
            dataset_partition_target_counts=tuple(
                (dataset, partition, target, 8)
                for dataset in DATASETS
                for partition in PARTITIONS
                for target in (0, 1)
                if not (dataset == "guitarset_poly_mix" and partition == "fit" and target == 1)
            )
        )
        gate = _representation_gate(protocol, insufficient)
        self.assertTrue(gate["required"])
        self.assertFalse(gate["passed"])
        self.assertIn({
            "scope": "dataset_partition_target",
            "dataset_id": "guitarset_poly_mix",
            "partition": "fit",
            "target": 1,
            "actual": 0,
            "minimum": 8,
        }, gate["shortfalls"])

    def test_git_preflight_accepts_the_real_40_character_commit_shape(self) -> None:
        """Exercise the implementation, rather than mocking the preflight itself."""
        expected = "0e124352f52637d3a895b615c771ee14b0de09e5"

        def check_output(command, **_kwargs):
            if tuple(command[:3]) == ("git", "rev-parse", "HEAD"):
                return expected
            if tuple(command[:3]) == ("git", "ls-files", "--others"):
                return ""
            self.fail(f"unexpected Git command: {command!r}")

        with patch(
            "src.polyphonic.mine_decoder_candidates.subprocess.check_output",
            side_effect=check_output,
        ), patch(
            "src.polyphonic.mine_decoder_candidates.subprocess.run",
            return_value=SimpleNamespace(returncode=0),
        ):
            self.assertEqual(
                _require_expected_git_commit(expected, repository_root=Path(".")),
                expected,
            )

    def test_bad_digest_preflight_fails_before_tensorflow_is_imported(self) -> None:
        """Run a fresh interpreter through the real preflight without TensorFlow.

        The checkpoint is deliberately replaced after its protocol digest is
        recorded.  A correct pure-Python preflight rejects it before the CPU
        import boundary, proving that neither importing this CLI nor this
        provenance error loads TensorFlow.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data" / "processed").mkdir(parents=True)
            commit = self._initialize_clean_git_repository(root)
            paths = self._write_inputs(root)
            paths["checkpoint"].write_bytes(b"substituted checkpoint")
            output = root / "data" / "processed" / "bounded"
            script = """
import os
from pathlib import Path
import sys
from src.polyphonic.mine_decoder_candidates import run_bounded_train_only_mining

assert 'tensorflow' not in sys.modules
try:
    run_bounded_train_only_mining(
        manifest_path=Path(os.environ['MINER_MANIFEST']),
        partition_plan_path=Path(os.environ['MINER_PLAN']),
        asset_evidence_path=Path(os.environ['MINER_EVIDENCE']),
        checkpoint_path=Path(os.environ['MINER_CHECKPOINT']),
        model_config_path=Path(os.environ['MINER_MODEL']),
        decoder_config_path=Path(os.environ['MINER_DECODER']),
        audio_evidence_config_path=Path(os.environ['MINER_AUDIO']),
        protocol_path=Path(os.environ['MINER_PROTOCOL']),
        output_dir=Path(os.environ['MINER_OUTPUT']),
        expected_git_commit=os.environ['MINER_COMMIT'],
        repository_root=Path(os.environ['MINER_ROOT']),
    )
except RuntimeError as error:
    assert 'checkpoint_sha256' in str(error), repr(error)
else:
    raise AssertionError('substituted checkpoint unexpectedly passed preflight')
assert 'tensorflow' not in sys.modules
"""
            environment = dict(os.environ)
            environment.update({
                "MINER_ROOT": str(root),
                "MINER_MANIFEST": str(paths["manifest"]),
                "MINER_PLAN": str(paths["plan"]),
                "MINER_EVIDENCE": str(paths["evidence"]),
                "MINER_CHECKPOINT": str(paths["checkpoint"]),
                "MINER_MODEL": str(paths["model"]),
                "MINER_DECODER": str(paths["decoder"]),
                "MINER_AUDIO": str(paths["audio"]),
                "MINER_PROTOCOL": str(paths["protocol"]),
                "MINER_OUTPUT": str(output),
                "MINER_COMMIT": commit,
            })
            result = subprocess.run(
                (sys.executable, "-c", script),
                cwd=Path(__file__).resolve().parents[1],
                env=environment,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_selection_is_exactly_one_canonical_item_per_dataset_partition(self) -> None:
        protocol = BoundedMiningProtocol(
            manifest_sha256="a" * 64,
            partition_plan_sha256="b" * 64,
            asset_evidence_sha256="c" * 64,
            checkpoint_sha256="d" * 64,
            model_config_sha256="e" * 64,
            decoder_config_sha256="f" * 64,
            audio_evidence_config_sha256="1" * 64,
            dataset_ids=DATASETS,
            recordings_per_dataset_partition=1,
            maximum_attempts_per_recording=8,
        )
        context = _Context(
            manifest_sha256="a" * 64,
            plan_sha256="b" * 64,
            evidence_sha256="c" * 64,
        )
        selected = _select_bounded_items(context, protocol)
        self.assertEqual(len(selected), 12)
        self.assertEqual(
            [(item.source_id.split("-", 1)[0], item.dataset_id) for item in selected],
            [(partition, dataset) for partition in PARTITIONS for dataset in DATASETS],
        )

    def test_selection_scales_deterministically_to_each_protocol_cell(self) -> None:
        protocol = BoundedMiningProtocol(
            manifest_sha256="a" * 64,
            partition_plan_sha256="b" * 64,
            asset_evidence_sha256="c" * 64,
            checkpoint_sha256="d" * 64,
            model_config_sha256="e" * 64,
            decoder_config_sha256="f" * 64,
            audio_evidence_config_sha256="1" * 64,
            dataset_ids=DATASETS,
            recordings_per_dataset_partition=3,
            maximum_attempts_per_recording=8,
        )
        context = _Context(
            manifest_sha256="a" * 64,
            plan_sha256="b" * 64,
            evidence_sha256="c" * 64,
            items_per_dataset_partition=3,
        )
        selected = _select_bounded_items(context, protocol)
        self.assertEqual(len(selected), 36)
        for partition in PARTITIONS:
            for dataset in DATASETS:
                self.assertEqual(
                    [item.source_id for item in selected
                     if item.dataset_id == dataset and item.source_id.startswith(partition)],
                    [
                        f"{partition}-{dataset}-{ordinal}-source"
                        for ordinal in range(3)
                    ],
                )

    def test_sha_mismatch_fails_before_tensorflow_or_model_load(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data" / "processed").mkdir(parents=True)
            paths = self._write_inputs(root)
            paths["checkpoint"].write_bytes(b"substituted checkpoint")
            output = root / "data" / "processed" / "bounded"
            with patch(
                "src.polyphonic.mine_decoder_candidates._require_expected_git_commit",
                return_value="e" * 64,
            ), patch(
                "src.polyphonic.mine_decoder_candidates._require_cpu_tensorflow"
            ) as cpu, patch(
                "src.polyphonic.mine_decoder_candidates._load_inference_model"
            ) as model:
                with self.assertRaisesRegex(RuntimeError, "checkpoint_sha256"):
                    run_bounded_train_only_mining(
                        manifest_path=paths["manifest"],
                        partition_plan_path=paths["plan"],
                        asset_evidence_path=paths["evidence"],
                        checkpoint_path=paths["checkpoint"],
                        model_config_path=paths["model"],
                        decoder_config_path=paths["decoder"],
                        audio_evidence_config_path=paths["audio"],
                        protocol_path=paths["protocol"],
                        output_dir=output,
                        expected_git_commit="e" * 64,
                        repository_root=root,
                    )
            cpu.assert_not_called()
            model.assert_not_called()
            self.assertFalse(output.exists())

    def test_complete_bounded_run_writes_non_authorizing_artifact_only(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data" / "processed").mkdir(parents=True)
            paths = self._write_inputs(root)
            protocol = BoundedMiningProtocol.from_path(paths["protocol"])
            context = _Context(
                manifest_sha256=protocol.manifest_sha256,
                plan_sha256=protocol.partition_plan_sha256,
                evidence_sha256=protocol.asset_evidence_sha256,
            )
            output = root / "data" / "processed" / "bounded"

            def fake_predict(_model, _context, item, **_kwargs):
                partition = item.source_id.split("-", 1)[0]
                return (
                    _batch(
                        item, partition,
                        manifest=protocol.manifest_sha256,
                        plan=protocol.partition_plan_sha256,
                    ),
                    [],
                    {"source_id": item.source_id, "partition": partition},
                )

            with patch(
                "src.polyphonic.mine_decoder_candidates._require_expected_git_commit",
                return_value="e" * 64,
            ), patch(
                "src.polyphonic.mine_decoder_candidates._load_mining_context",
                return_value=context,
            ), patch(
                "src.polyphonic.mine_decoder_candidates._require_cpu_tensorflow",
                return_value=object(),
            ), patch(
                "src.polyphonic.mine_decoder_candidates._load_inference_model",
                return_value=object(),
            ) as model, patch(
                "src.polyphonic.mine_decoder_candidates._predict_recording",
                side_effect=fake_predict,
            ) as replay:
                report = run_bounded_train_only_mining(
                    manifest_path=paths["manifest"],
                    partition_plan_path=paths["plan"],
                    asset_evidence_path=paths["evidence"],
                    checkpoint_path=paths["checkpoint"],
                    model_config_path=paths["model"],
                    decoder_config_path=paths["decoder"],
                    audio_evidence_config_path=paths["audio"],
                    protocol_path=paths["protocol"],
                    output_dir=output,
                    expected_git_commit="e" * 64,
                    repository_root=root,
                )
            self.assertEqual(model.call_count, 1)
            self.assertEqual(replay.call_count, 12)
            self.assertEqual(report["status"], "complete_non_authorizing")
            self.assertIs(report["fit_authorized"], False)
            self.assertTrue((output / "candidate_events.jsonl").is_file())
            persisted = json.loads((output / "mining_report.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["counters"]["recordings"], 12)
            self.assertEqual(set(persisted["counters_by_partition"]), set(PARTITIONS))
            self.assertIs(persisted["locked_test_used"], False)


if __name__ == "__main__":
    unittest.main()
