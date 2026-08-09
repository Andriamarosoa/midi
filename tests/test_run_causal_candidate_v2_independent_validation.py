from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from src.polyphonic.decoder_candidate_provenance import load_decoder_candidate_manifest
from src.polyphonic import run_causal_candidate_v2_independent_validation as runner


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _row(
    dataset_id: str,
    source_id: str,
    group_id: str,
    capture_id: str,
    *,
    player_id: str = "",
    split: str = "validation",
) -> dict[str, str]:
    return {
        "source_id": source_id,
        "dataset_id": dataset_id,
        "player_id": player_id,
        "group_id": group_id,
        "capture_id": capture_id,
        "split": split,
    }


def _key(row: dict[str, str]) -> str:
    return "|".join((
        row["dataset_id"], row["group_id"], row["source_id"], row["capture_id"],
    ))


def _protocol(*, manifest_sha256: str, historical_sha256: str, recording_keys: list[str]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "purpose": "causal_candidate_fit_v2_post_ranking_independent_validation_contract",
        "status": runner.INDEPENDENT_V2_PROTOCOL_STATUS,
        "locked_test_used": False,
        "authorization_scope": {"allowed_now": list(runner.INDEPENDENT_V2_ALLOWED_NOW)},
        "frozen_v2_intervention": {
            **runner.INDEPENDENT_V2_FROZEN_ARTIFACT_SHA256,
            "threshold": 0.31,
            "candidate_gate_placement": "post_ranking_pre_noteon",
            "encoded_feature_count": 12,
        },
        "independence_boundary": {
            "manifest_sha256": manifest_sha256,
            "historical_v1_validation_selection_path": str(
                runner.HISTORICAL_V1_SELECTION_RELATIVE_PATH.as_posix()
            ),
            "historical_v1_validation_selection_sha256": historical_sha256,
            "policy_a_partition_plan_sha256": "c" * 64,
            "exclude_historical_recording_keys": True,
            "exclude_every_historical_leakage_group": True,
            "require_no_overlap_with_policy_a_eligible_train_groups": True,
            "forbid_manual_recording_selection": True,
            "forbid_metric_or_audio_or_label_based_selection": True,
        },
        "cohort_rule": {
            "recording_count": 30,
            "selection_seed": 47,
            "independent_group_count": 20,
            "canonical_recording_key": "dataset_id|group_id|source_id|capture_id",
            "recordings_per_dataset": {
                "gaps_poly_mix": 10,
                "guitar_techs_poly_directinput": 10,
                "guitar_techs_poly_micamp": 10,
                "guitarset_poly_mix": 0,
            },
            "recording_keys": recording_keys,
        },
        "validation_asset_evidence_contract": {
            "schema_version": 1,
            "purpose": "causal_candidate_v2_independent_validation_asset_evidence",
            "asset_types": ["audio", "labels"],
            "must_bind": [
                "independent_validation_protocol_sha256",
                "manifest_sha256",
                "ordered_recording_keys_sha256",
                "recording_keys",
            ],
            "builder_authorized_now": False,
            "reader_authorized_now": False,
        },
        "future_execution_contract": {
            "single_cpu_job": True,
            "wall_timeout_seconds": 900,
            "independent_group_count": 20,
            "report_recordings_and_independent_groups_separately": True,
            "single_transcription_inference_per_recording": True,
            "same_predictions_and_audio_evidence_masks_reused_across_ab": True,
            "reference_has_no_causal_candidate_gate": True,
            "candidate_uses_only_the_frozen_v2_intervention": True,
            "no_model_or_threshold_selection": True,
            "stop_after_report": True,
        },
        "pre_registered_interpretation_rules": {
            "all_rules_must_pass_for_positive_independent_evidence": True,
            "global_causal_false_noteon_relative_reduction_minimum": 0.01,
            "per_dataset_causal_false_noteons_must_not_increase": True,
            "retriggers_and_excess_fragments_must_not_increase": True,
            "guitarset_claim_forbidden": True,
            "automatic_promotion": False,
        },
    }


class IndependentV2ValidationRunnerTests(unittest.TestCase):
    def _write_manifest(self, root: Path, *, include_test: bool = False) -> tuple[Path, list[str]]:
        rows: list[dict[str, str]] = []
        historical: list[str] = []
        for index in range(3):
            row = _row(
                "gaps_poly_mix", f"historic-gaps-{index}", f"historic-gaps-{index}",
                "gaps_mixed_downmix", player_id=f"Historic {index}",
            )
            rows.append(row)
            historical.append(_key(row))
        for capture in ("directinput", "micamp"):
            for index in range(3):
                dataset = f"guitar_techs_poly_{capture}"
                group = f"historic-{capture}-{index}"
                row = _row(dataset, f"{group}-{capture}", group, capture)
                rows.append(row)
                historical.append(_key(row))
        for index in range(3):
            row = _row(
                "guitarset_poly_mix", f"historic-guitarset-{index}",
                f"historic-guitarset-{index}", "mono_pickup_mix", player_id="04",
            )
            rows.append(row)
            historical.append(_key(row))
        for index in range(12):
            rows.append(_row(
                "gaps_poly_mix", f"gaps-{index}", f"gaps-{index}",
                "gaps_mixed_downmix", player_id=f"Fresh {index}",
            ))
        for index in range(12):
            group = f"gtech-{index}"
            rows.append(_row(
                "guitar_techs_poly_directinput", f"{group}-direct", group, "directinput",
            ))
            rows.append(_row(
                "guitar_techs_poly_micamp", f"{group}-mic", group, "micamp",
            ))
        rows.append(_row(
            "guitarset_poly_mix", "fresh-guitarset", "fresh-guitarset", "mono_pickup_mix",
            player_id="04",
        ))
        # Train rows may appear in the full manifest, but their overlapping
        # leakage groups must never make a selected validation group Policy A eligible.
        rows.extend((
            _row("gaps_poly_mix", "train-gaps", "train-gaps", "gaps_mixed_downmix", player_id="Fresh 0", split="train"),
            _row("guitar_techs_poly_directinput", "train-gtech", "gtech-0", "directinput", split="train"),
            _row("gaps_poly_mix", "train-safe", "train-safe", "gaps_mixed_downmix", player_id="Train only", split="train"),
        ))
        if include_test:
            rows.append(_row(
                "gaps_poly_mix", "locked", "locked", "gaps_mixed_downmix",
                player_id="Locked", split="test",
            ))
        path = root / "manifest.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return path, historical

    def _derive(self, root: Path, *, include_test: bool = False):
        manifest_path, historical = self._write_manifest(root, include_test=include_test)
        items, manifest_sha = load_decoder_candidate_manifest(manifest_path)
        derived, _ = runner._derive_expected_recording_keys(
            items, historical_recording_keys=historical,
        )
        return (
            _protocol(
                manifest_sha256=manifest_sha,
                historical_sha256="a" * 64,
                recording_keys=list(derived),
            ),
            items,
            manifest_sha,
            historical,
            derived,
        )

    def test_derives_the_exact_metadata_only_30_recording_cohort(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol, items, manifest_sha, historical, derived = self._derive(root)
            cohort = runner.derive_independent_v2_validation_cohort(
                protocol,
                protocol_sha256="b" * 64,
                manifest_items=items,
                manifest_sha256=manifest_sha,
                historical_recording_keys=historical,
                historical_selection_sha256="a" * 64,
            )
        self.assertEqual(cohort.recording_keys, derived)
        self.assertEqual(cohort.independent_group_count, 20)
        self.assertEqual(dict(cohort.recordings_per_dataset), {
            "gaps_poly_mix": 10,
            "guitar_techs_poly_directinput": 10,
            "guitar_techs_poly_micamp": 10,
        })
        self.assertFalse(any(key.startswith("guitarset_poly_mix|") for key in cohort.recording_keys))
        with self.assertRaisesRegex(RuntimeError, "factory-attested"):
            runner.validation_asset_evidence_requirement(cohort)

    def test_rejects_any_locked_test_row_before_selecting_a_cohort(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, historical = self._write_manifest(root, include_test=True)
            items, manifest_sha = load_decoder_candidate_manifest(manifest_path)
            protocol = _protocol(
                manifest_sha256=manifest_sha,
                historical_sha256="a" * 64,
                recording_keys=["placeholder"] * 30,
            )
            with self.assertRaisesRegex(RuntimeError, "locked test rows"):
                runner.derive_independent_v2_validation_cohort(
                    protocol,
                    protocol_sha256="b" * 64,
                    manifest_items=items,
                    manifest_sha256=manifest_sha,
                    historical_recording_keys=historical,
                    historical_selection_sha256="a" * 64,
                )

    def test_rejects_a_configured_list_that_does_not_rederive_from_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol, items, manifest_sha, historical, derived = self._derive(root)
            protocol["cohort_rule"]["recording_keys"] = list(reversed(derived))  # type: ignore[index]
            with self.assertRaisesRegex(RuntimeError, "configured recording keys differ"):
                runner.derive_independent_v2_validation_cohort(
                    protocol,
                    protocol_sha256="b" * 64,
                    manifest_items=items,
                    manifest_sha256=manifest_sha,
                    historical_recording_keys=historical,
                    historical_selection_sha256="a" * 64,
                )

    def test_sealed_loader_rehashes_protocol_and_historical_selection_before_manifest_use(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, historical = self._write_manifest(root)
            items, manifest_sha = load_decoder_candidate_manifest(manifest_path)
            derived, _ = runner._derive_expected_recording_keys(
                items, historical_recording_keys=historical,
            )
            history_path = root / runner.HISTORICAL_V1_SELECTION_RELATIVE_PATH
            history_path.parent.mkdir(parents=True)
            history_path.write_text(json.dumps({
                "schema_version": 1,
                "locked_test_used": False,
                "recording_keys": historical,
            }) + "\n", encoding="utf-8")
            protocol = _protocol(
                manifest_sha256=manifest_sha,
                historical_sha256=_sha256(history_path),
                recording_keys=list(derived),
            )
            protocol_path = root / runner.INDEPENDENT_V2_PROTOCOL_RELATIVE_PATH
            protocol_path.parent.mkdir(parents=True, exist_ok=True)
            protocol_path.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
            with mock.patch.object(
                runner, "INDEPENDENT_V2_PROTOCOL_SHA256", _sha256(protocol_path)
            ):
                cohort = runner.load_sealed_independent_v2_validation_cohort(
                    root, manifest_path,
                )
        self.assertEqual(cohort.recording_keys, derived)
        self.assertEqual(cohort.independent_group_count, 20)

    def test_import_does_not_load_tensorflow_or_expose_a_cli(self) -> None:
        code = (
            "import sys; import src.polyphonic.run_causal_candidate_v2_independent_validation as module; "
            "raise SystemExit(int('tensorflow' in sys.modules or hasattr(module, 'main')))"
        )
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parents[1],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_decision_is_mechanical_and_fail_closed_on_non_finite_metrics(self) -> None:
        causal = {
            "false_noteons": 100,
            "recall_within_max_latency": 0.8,
            "latency_p50_ms": 20.0,
            "latency_p90_ms": 40.0,
        }
        per_dataset = {
            dataset: {"onset": {"f1": 0.6}}
            for dataset in (
                "gaps_poly_mix",
                "guitar_techs_poly_directinput",
                "guitar_techs_poly_micamp",
            )
        }
        by_corpus = {
            dataset: dict(causal)
            for dataset in per_dataset
        }
        reference = {
            "onset": {"f1": 0.6},
            "strictly_causal_noteon": {"global": causal, "by_corpus": by_corpus},
            "dataset_metrics": {"per_dataset": per_dataset},
            "retriggers": 2,
            "diagnostics": {"excess_fragments": 3},
        }
        candidate = {
            **reference,
            "strictly_causal_noteon": {
                "global": {**causal, "false_noteons": 99},
                "by_corpus": {
                    dataset: {**causal, "false_noteons": 99}
                    for dataset in per_dataset
                },
            },
        }
        rules = {
            "all_rules_must_pass_for_positive_independent_evidence": True,
            "global_causal_false_noteon_relative_reduction_minimum": 0.01,
            "per_dataset_causal_false_noteons_must_not_increase": True,
            "per_dataset_causal_recall_within_250ms_maximum_drop": 0.005,
            "global_causal_recall_within_250ms_maximum_drop": 0.002,
            "global_onset_f1_maximum_drop": 0.001,
            "per_dataset_onset_f1_maximum_drop": 0.002,
            "causal_latency_p50_and_p90_maximum_increase_ms": 5.804988662131519,
            "retriggers_and_excess_fragments_must_not_increase": True,
            "guitarset_claim_forbidden": True,
            "automatic_promotion": False,
        }
        decision = runner.evaluate_independent_v2_decision(
            reference=reference, candidate=candidate, rules=rules,
        )
        self.assertTrue(decision["all_rules_passed"])
        self.assertEqual(
            decision["classification"], "positive_independent_evidence_non_promotional",
        )
        candidate = {
            **candidate,
            "strictly_causal_noteon": {
                **candidate["strictly_causal_noteon"],
                "global": {**candidate["strictly_causal_noteon"]["global"], "latency_p50_ms": float("nan")},
            },
        }
        with self.assertRaisesRegex(ValueError, "non-finite metric"):
            runner.evaluate_independent_v2_decision(
                reference=reference, candidate=candidate, rules=rules,
            )

    def test_versioned_contract_seals_reader_after_builder_publication(self) -> None:
        root = Path(__file__).resolve().parents[1]
        protocol = json.loads((
            root / runner.INDEPENDENT_V2_PROTOCOL_RELATIVE_PATH
        ).read_text(encoding="utf-8"))
        self.assertEqual(
            _sha256(root / runner.INDEPENDENT_V2_PROTOCOL_RELATIVE_PATH),
            runner.INDEPENDENT_V2_PROTOCOL_SHA256,
        )
        self.assertEqual(protocol["status"], runner.INDEPENDENT_V2_PROTOCOL_STATUS)
        self.assertEqual(
            tuple(protocol["authorization_scope"]["allowed_now"]),
            runner.INDEPENDENT_V2_ALLOWED_NOW,
        )
        evidence_contract = protocol["validation_asset_evidence_contract"]
        self.assertFalse(evidence_contract["builder_authorized_now"])
        self.assertTrue(evidence_contract["reader_authorized_now"])
        self.assertEqual(
            evidence_contract["source_evidence_protocol_sha256"],
            "d63655c388991f3782a738e5bba58f0409ae79f297a3d5009dab7971349ba015",
        )
        self.assertEqual(
            evidence_contract["expected_evidence_sha256"],
            "10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee",
        )
        self.assertFalse(protocol["locked_test_used"])
        self.assertEqual(len(protocol["cohort_rule"]["recording_keys"]), 30)
        self.assertFalse(any(
            key.startswith("guitarset_poly_mix|")
            for key in protocol["cohort_rule"]["recording_keys"]
        ))
        self.assertEqual(
            protocol["future_execution_contract"]["independent_group_count"], 20,
        )


if __name__ == "__main__":
    unittest.main()
