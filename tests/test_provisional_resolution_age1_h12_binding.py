from __future__ import annotations

import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import src.polyphonic.provisional_resolution_age1_h12 as h12
from src.polyphonic.provisional_resolution_age1_h11 import H11Recording


ROOT = Path(__file__).resolve().parents[1]


def h11_recording(*, digest: str = "1" * 64) -> H11Recording:
    return H11Recording(
        recording_key="dataset|group|source|capture",
        corpus_category="dataset",
        leakage_group_key="group-00",
        partition="dev",
        audio_size_bytes=5,
        audio_sha256=digest,
        labels_size_bytes=6,
        labels_sha256="2" * 64,
        source_manifest_sha256=h12.MANIFEST_SHA256,
        source_partition_plan_sha256=h12.PLAN_SHA256,
    )


class H12BindingTests(unittest.TestCase):
    def test_actual_h11_raw_sha_is_hard_bound(self):
        path = ROOT / h12.H11_CONTRACT_RELATIVE
        self.assertEqual(h12.sha256_file(path), h12.H11_CONTRACT_SHA256)

    def test_h11_sha_mismatch_stops_before_other_preflight(self):
        paths = Mock()
        paths.h11_contract = Path("missing")
        with patch.object(h12, "sealed_h12_paths", return_value=paths), \
             patch.object(h12, "sha256_file", return_value="0" * 64), \
             patch.object(h12, "require_h12_source_bindings") as source:
            with self.assertRaisesRegex(RuntimeError, "H11 contract"):
                h12.run_h12_preflight(Path("repo"), Path("worker"))
            source.assert_not_called()

    def test_actual_h8_metadata_reconstructs_exact_101_and_31(self):
        records, forbidden = h12._load_h8_metadata(ROOT / h12.H8_COHORT_RELATIVE)
        self.assertEqual(len(records), 101)
        self.assertEqual(len({record.h11.leakage_group_key for record in records}), 31)
        self.assertFalse({record.h11.leakage_group_key for record in records}.intersection(forbidden))
        self.assertTrue(all(record.h11.partition == "dev" for record in records))

    def test_h8_sha_mismatch_fails_before_parse(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "cohort.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "selected-cohort"):
                h12._load_h8_metadata(path)

    def test_real_entrypoint_has_no_scientific_override_parameters(self):
        self.assertEqual(tuple(inspect.signature(h12.run_real_h7_discovery).parameters), ())
        source = inspect.getsource(h12.run_real_h7_discovery)
        self.assertIn("metric_callable=evaluate_h7_synthetic_metrics", source)
        for forbidden in (
            "cohort=", "forbidden_groups_override", "checkpoint_path=",
            "metric_callable_override", "bootstrap_seed=",
        ):
            self.assertNotIn(forbidden, source)

    def test_historical_and_instrumented_decoder_blobs_are_distinct_and_bound(self):
        self.assertEqual(h12.HISTORICAL_DECODER_BLOB, "4233186147c0946372ddb2e9e3dd3343daeb26eb")
        self.assertEqual(h12.INSTRUMENTED_DECODER_BLOB, "27026d368081fadc4fa282954428f0377020e723")
        self.assertNotEqual(h12.HISTORICAL_DECODER_BLOB, h12.INSTRUMENTED_DECODER_BLOB)
        h12.require_h12_source_bindings(ROOT)

    def test_each_source_blob_mismatch_fails_preflight(self):
        for bad_key in (
            "HEAD:src/polyphonic/decoder.py",
            "HEAD:src/polyphonic/provisional_resolution_age1.py",
            "HEAD:src/polyphonic/provisional_resolution_age1_metrics.py",
            "HEAD:src/polyphonic/provisional_resolution_age1_h11.py",
        ):
            with self.subTest(bad_key=bad_key), patch.object(
                h12, "_git_blob", side_effect=lambda _root, key, bad=bad_key: (
                    "0" * 40 if key == bad else {
                        "HEAD:src/polyphonic/decoder.py": h12.INSTRUMENTED_DECODER_BLOB,
                        "HEAD:src/polyphonic/provisional_resolution_age1.py": h12.H9_IMPLEMENTATION_BLOB,
                        "HEAD:src/polyphonic/provisional_resolution_age1_metrics.py": h12.H10_METRIC_BLOB,
                        "HEAD:src/polyphonic/provisional_resolution_age1_h11.py": h12.H11_ORCHESTRATOR_BLOB,
                        f"{h12.H7_COMMIT}:src/polyphonic/decoder.py": h12.HISTORICAL_DECODER_BLOB,
                    }[key]
                )
            ):
                with self.assertRaisesRegex(RuntimeError, "source binding"):
                    h12.require_h12_source_bindings(ROOT)

    def test_runtime_mismatch_fails_closed(self):
        expected = {
            "python": "3.11.9", "numpy": "1.26.4", "tensorflow": "2.15.1",
            "macos": "15.5", "darwin": "24.5.0", "architecture": "arm64", "device": "cpu",
        }
        h12.require_h12_runtime(expected)
        for name in expected:
            altered = dict(expected)
            altered[name] = "wrong"
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                h12.require_h12_runtime(altered)

    def test_actual_config_payloads_are_semantically_and_canonically_bound(self):
        paths = Mock()
        paths.model_config = ROOT / "configs" / "polyphonic_dual_stream_bass_independent_note.yaml"
        paths.decoder_config = ROOT / "configs" / "independent_note_decoder_reference.json"
        paths.audio_policy = ROOT / "configs" / "polyphonic_audio_evidence_adaptive_temporal.json"
        model, decoder, audio = h12.require_h12_config_payloads(paths)
        self.assertEqual(model["dataset"]["input_samples"], 8192)
        self.assertIsNone(decoder["independent_note_threshold"])
        self.assertEqual(audio, {"onset_adapt_temporal_background": True})

    def test_asset_mismatch_fails_without_scientific_open(self):
        with tempfile.TemporaryDirectory() as root:
            worker = Path(root)
            data = worker / "data"
            data.mkdir()
            (data / "audio.bin").write_bytes(b"audio")
            (data / "labels.bin").write_bytes(b"labels")
            record = h12.SealedH8Recording(
                h11=h11_recording(), dataset_id="dataset", source_id="source",
                group_id="group", capture_id="capture", audio_path_identity="audio.bin",
                audio_member_identity="", labels_path_identity="labels.bin", labels_member_identity="",
            )
            paths = h12.H12Paths(*([worker] * 13))
            adapter = Mock()
            with self.assertRaisesRegex(RuntimeError, "audio byte evidence"):
                h12.verify_h8_asset_bytes(paths, (record,))
            adapter.open_recording.assert_not_called()

    def test_zero_science_preflight_never_calls_adapter_or_metrics(self):
        records, forbidden = h12._load_h8_metadata(ROOT / h12.H8_COHORT_RELATIVE)
        fake_paths = Mock()
        fake_paths.h11_contract = ROOT / h12.H11_CONTRACT_RELATIVE
        fake_paths.h8_cohort = ROOT / h12.H8_COHORT_RELATIVE
        fake_paths.authorization_marker = ROOT / "never-created-authorization.json"
        fake_paths.result_destination = ROOT / "never-created-result"
        for name in ("manifest", "partition_plan", "asset_evidence", "checkpoint", "model_config", "decoder_config", "audio_policy"):
            setattr(fake_paths, name, ROOT / f"synthetic-{name}")
        runtime = {
            "python": "3.11.9", "numpy": "1.26.4", "tensorflow": "2.15.1",
            "macos": "15.5", "darwin": "24.5.0", "architecture": "arm64", "device": "cpu",
        }
        with patch.object(h12, "sealed_h12_paths", return_value=fake_paths), \
             patch.object(h12, "require_h12_source_bindings"), \
             patch.object(h12, "require_raw_sha256s"), \
             patch.object(h12, "require_h12_config_payloads"), \
             patch.object(h12, "_load_h8_metadata", return_value=(records, forbidden)), \
             patch.object(h12, "verify_h8_asset_bytes"), \
             patch.object(h12, "runtime_identity", return_value=runtime), \
             patch.object(h12.ConcreteH7ScientificAdapter, "open_recording") as opened, \
             patch.object(h12.ConcreteH7ScientificAdapter, "infer_once") as inferred, \
             patch.object(h12.ConcreteH7ScientificAdapter, "decode_once") as decoded, \
             patch.object(h12.ConcreteH7ScientificAdapter, "extract_targets") as targeted, \
             patch.object(h12, "evaluate_h7_synthetic_metrics") as metrics:
            result = h12.run_h12_preflight(ROOT, ROOT.parent)
        self.assertEqual(result["status"], "h7_real_execution_preflight_ready")
        self.assertFalse(result["h8_discovery_consumed"])
        self.assertFalse(result["scientific_execution_authorized"])
        for operation in (opened, inferred, decoded, targeted, metrics):
            operation.assert_not_called()
        self.assertFalse(fake_paths.authorization_marker.exists())

    def test_adapter_directly_names_h9_apis_and_baseline_gates(self):
        source = inspect.getsource(h12.ConcreteH7ScientificAdapter)
        for required in (
            "PassiveAge1SignalCollector", "require_no_pending_age1_at_end",
            "extract_exact_causal_age1_targets", "provisional_state_resolver=None",
            "causal_candidate_gate=None", "independent_note_threshold",
        ):
            self.assertIn(required, source)
        self.assertNotIn("retry", source.lower())

    def test_h12_contract_is_non_executing(self):
        payload = json.loads((ROOT / "configs" / "provisional_resolution_age1_persistence_h12_real_execution_binding.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "provisional_resolution_age1_persistence_h12_real_execution_binding_sealed")
        self.assertTrue(all(value is False for value in payload["terminal_flags"].values()))


if __name__ == "__main__":
    unittest.main()
