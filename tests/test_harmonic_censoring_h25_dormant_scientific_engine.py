from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
import time
from types import MappingProxyType
import unittest

import numpy as np

from src.polyphonic.harmonic_censoring_h25_recomputer import (
    recompute_h25_persisted_evidence,
)
from src.polyphonic.harmonic_censoring_h25_scientific_engine import (
    ATOL,
    H25CandidateFeatures,
    H25CausalReplayTrace,
    H25EvidenceProducerContext,
    H25_EXACT_EVIDENCE_PRODUCER_REGISTRY,
    POPULATION_INDEX_SHA256,
    POPULATION_PROVENANCE_SHA256,
    POPULATION_RECEIPT_SHA256,
    build_typed_harmonic_graph,
    causal_power_spectrum,
    extract_causal_candidate_features,
    load_h25_dormant_scientific_plan,
    canonical_json_bytes,
    produce_h25_test_evidence,
    require_h25_scientific_execution_authorized,
    resolve_one_hop_candidate,
    scalar_support_normalized_dilution,
    support_normalized_dilution,
)
from src.polyphonic.run_harmonic_censoring_h25_scientific import (
    H25_DORMANT_SCIENTIFIC_RUNNER_IMPLEMENTED,
    load_h25_dormant_runner_plan,
    recompute_phase_prefix,
    run_h25_scientific_execution,
)


class H25DormantScientificEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.plan = load_h25_dormant_scientific_plan(cls.root)

    def test_plan_registry_and_population_bindings_are_exact(self) -> None:
        self.assertEqual(len(self.plan.fixture_ids), 36)
        self.assertEqual(len(self.plan.test_ids), 27)
        self.assertEqual(tuple(H25_EXACT_EVIDENCE_PRODUCER_REGISTRY), self.plan.test_ids)
        self.assertTrue(all(callable(item) for item in H25_EXACT_EVIDENCE_PRODUCER_REGISTRY.values()))
        self.assertEqual(
            dict(self.plan.population_bindings),
            {
                "population_index.jsonl": POPULATION_INDEX_SHA256,
                "runtime_provenance.json": POPULATION_PROVENANCE_SHA256,
                "population_receipt.json": POPULATION_RECEIPT_SHA256,
            },
        )
        runner = load_h25_dormant_runner_plan(self.root)
        self.assertEqual(runner.phase_order, ("P0", "P1", "P2"))
        self.assertEqual(runner.ordered_test_ids, self.plan.test_ids)

    def test_typed_graph_is_closed_exact_and_never_descends(self) -> None:
        graph = build_typed_harmonic_graph()
        expected = {
            (pitch, harmonic)
            for pitch in range(24, 77)
            for harmonic in range(1, 21)
            if pitch + 12.0 * math.log2(harmonic) <= 128.0
        }
        self.assertEqual(
            {(item["source_pitch"], item["harmonic_rank"]) for item in graph},
            expected,
        )
        self.assertEqual(len(graph), len(expected))
        for item in graph:
            if item["harmonic_rank"] == 1:
                self.assertEqual(item["relation_type"], "FUNDAMENTAL_IDENTITY")
                self.assertEqual(item["observation_coordinate"], float(item["source_pitch"]))
            else:
                self.assertEqual(item["relation_type"], "PROPER_HARMONIC_ASCENT")
                self.assertGreater(item["observation_coordinate"], item["source_pitch"])

    @staticmethod
    def _test_only_spectrum(window_samples: int = 4096) -> tuple[np.ndarray, np.ndarray]:
        n = np.arange(window_samples, dtype=np.float64)
        waveform = (
            np.sin(2.0 * np.pi * 261.625565 * n / 44100.0)
            + 0.4 * np.sin(2.0 * np.pi * 523.25113 * n / 44100.0)
            + 0.2 * np.sin(2.0 * np.pi * 784.876695 * n / 44100.0)
        )
        hann = 0.5 - 0.5 * np.cos(2.0 * np.pi * n / float(window_samples))
        power = np.abs(np.fft.rfft(waveform * hann)) ** 2
        frequencies = np.arange(power.size, dtype=np.float64) * 44100.0 / float(window_samples)
        return power, frequencies

    def _test_only_context(self, test, fixture_id="TEST-ONLY-H25-F-PRODUCER"):
        samples = np.arange(17664, dtype=np.float64)
        waveform = np.sin(2.0 * np.pi * 130.8127825 * samples / 44100.0)
        envelope = np.zeros(samples.shape, dtype=np.float64)
        elapsed = samples[16128:] - 16128.0
        envelope[16128:] = np.minimum(1.0, (elapsed + 1.0) / 64.0) * np.exp(-elapsed / 2048.0)
        waveform += envelope * np.sin(2.0 * np.pi * 261.625565 * samples / 44100.0)
        source = {
            "id": fixture_id,
            "order": 1,
            "category": "positive",
            "family": "IDENTIFIABLE_OVERLAP",
            "pitch_band": "mid",
            "candidate_pitch": 60,
            "parameters": {"old_pitch": 48, "new_onset": 16128},
        }
        test = replace(test, fixture_ids=(fixture_id,))
        plan = replace(self.plan, fixtures=(MappingProxyType(source),), tests=(test,))
        context = H25EvidenceProducerContext(
            np=np,
            plan=plan,
            waveforms=MappingProxyType({fixture_id: waveform}),
            fixture_records=MappingProxyType({fixture_id: {"source_fixture_record": source}}),
            causal_replay_traces=MappingProxyType({fixture_id: H25CausalReplayTrace(fixture_id, 16383, (48,), ())}),
            started_ns=time.perf_counter_ns(),
            peak_rss_bytes=1,
            operational_counters=MappingProxyType({
                "GPU_device_count": 0,
                "scientific_process_count": 1,
                "model_inference_call_count": 0,
                "hidden_repeated_pitch_shift_inference_count": 0,
            }),
            observed_fixture_ids=plan.fixture_ids,
            observed_test_ids=plan.test_ids,
        )
        return plan, test, context

    def test_vectorized_operator_matches_independent_scalar_reference(self) -> None:
        power, frequencies = self._test_only_spectrum()
        pitches = (40, 60, 76)
        vector = support_normalized_dilution(np, power, frequencies, candidate_pitches=pitches)
        self.assertEqual(vector.raw.shape, (3, 89))
        self.assertEqual(vector.harmonic_support.shape, (3, 89, 20))
        for row, pitch in enumerate(pitches):
            scalar = scalar_support_normalized_dilution(np, power, frequencies, candidate_pitch=pitch)
            self.assertEqual(vector.pair_support[row].tolist(), list(scalar["pair_support"]))
            self.assertEqual(bool(vector.baseline_valid[row]), scalar["baseline_valid"])
            for name in ("raw", "normalized", "geometric_null", "residual"):
                self.assertTrue(
                    np.allclose(
                        getattr(vector, name)[row],
                        np.asarray(scalar[name]),
                        rtol=1e-10,
                        atol=1e-12,
                        equal_nan=True,
                    ),
                    name,
                )

    def test_invalid_support_is_masked_and_candidate_order_is_invariant(self) -> None:
        power, frequencies = self._test_only_spectrum()
        forward = support_normalized_dilution(np, power, frequencies, candidate_pitches=(40, 76))
        reverse = support_normalized_dilution(np, power, frequencies, candidate_pitches=(76, 40))
        self.assertEqual(forward.pair_support.tolist(), reverse.pair_support[::-1].tolist())
        self.assertTrue(np.allclose(forward.raw, reverse.raw[::-1], equal_nan=True))
        self.assertTrue(np.all(np.isnan(forward.raw[~forward.pair_support])))
        valid = forward.pair_support & forward.baseline_valid[:, None]
        self.assertTrue(np.all(np.isnan(forward.residual[~valid])))
        self.assertFalse(np.any(np.isfinite(forward.residual[~valid])))

    def test_causal_windows_ignore_future_suffix_and_end_at_declared_sample(self) -> None:
        samples = np.arange(16640, dtype=np.float64)
        waveform = np.zeros(16640, dtype=np.float64)
        waveform[8192:] = np.sin(2.0 * np.pi * 261.625565 * samples[8192:] / 44100.0)
        changed = waveform.copy()
        changed[16384:] += 1000.0
        left_power, _ = causal_power_spectrum(np, waveform, end_sample=16383, window_samples=8192)
        right_power, _ = causal_power_spectrum(np, changed, end_sample=16383, window_samples=8192)
        self.assertEqual(left_power.tobytes(), right_power.tobytes())
        features = extract_causal_candidate_features(np, waveform, candidate_pitch=60, decision_hop_end=16639)
        self.assertEqual(features.maximum_sample_read, 16639)

    def test_state_machine_resolves_exactly_one_hop_without_backfill(self) -> None:
        base = dict(
            candidate_pitch=60,
            long_window_persistence_or_decay=0.0,
            dilution_residual_change_l1=0.0,
            short_valid=True,
            long_valid=True,
            maximum_sample_read=16639,
        )
        positive = H25CandidateFeatures(
            short_window_onset_rise=0.1,
            short_window_harmonic_novelty=0.2,
            short_window_new_energy=0.1,
            old_source_explanation_residual=0.5,
            **base,
        )
        absent = replace(
            positive,
            short_window_onset_rise=0.0,
            short_window_harmonic_novelty=0.0,
            short_window_new_energy=0.0,
            old_source_explanation_residual=0.0,
        )
        unresolved = replace(absent, old_source_explanation_residual=1.0)
        invalid = replace(positive, short_valid=False)
        self.assertEqual(resolve_one_hop_candidate(previous_state="PENDING_NEW", features=positive), ("ACTIVE", "BIRTH_SUPPORTED"))
        self.assertEqual(resolve_one_hop_candidate(previous_state="PENDING_NEW", features=absent), ("INACTIVE", "NO_BIRTH"))
        self.assertEqual(resolve_one_hop_candidate(previous_state="PENDING_NEW", features=unresolved), ("INACTIVE", "AMBIGUOUS"))
        self.assertEqual(resolve_one_hop_candidate(previous_state="PENDING_NEW", features=invalid), ("INACTIVE", "AMBIGUOUS"))
        self.assertEqual(resolve_one_hop_candidate(previous_state="ACTIVE", features=positive), ("ACTIVE", "ALREADY_ACTIVE_HISTORY"))
        with self.assertRaises(ValueError):
            resolve_one_hop_candidate(previous_state="INACTIVE", features=positive)

    def test_independent_recomputer_rejects_self_declared_verdict_and_kills_suffix(self) -> None:
        test = self.plan.tests[0]
        graph = list(build_typed_harmonic_graph())
        valid = {
            "schema_version": 1,
            "test_id": test.test_id,
            "phase": test.phase,
            "objective": test.objective,
            "fixture_measurements": [],
            "typed_harmonic_graph": graph,
            "inverse_measurement": {"mutated_typed_harmonic_graph": graph[1:]},
        }
        outcome = recompute_h25_persisted_evidence(self.plan, test.test_id, valid)
        self.assertTrue(outcome.final_pass)
        forged = dict(valid, verdict="PASS")
        with self.assertRaisesRegex(ValueError, "self-declared verdict"):
            recompute_h25_persisted_evidence(self.plan, test.test_id, forged)
        failed = dict(valid, typed_harmonic_graph=graph[1:])
        status, executed, not_run = recompute_phase_prefix(self.plan, {test.test_id: failed})
        self.assertEqual(status, "H25_SYNTHETIC_HYPOTHESIS_KILLED")
        self.assertEqual(executed, (test.test_id,))
        self.assertEqual(not_run, self.plan.test_ids[1:])

    def test_test_only_producer_serializes_operands_and_recomputes_independently(self) -> None:
        fixture_id = "TEST-ONLY-H25-F-PRODUCER"
        samples = np.arange(16640, dtype=np.float64)
        waveform = np.zeros(samples.shape, dtype=np.float64)
        waveform[8192:] = np.sin(2.0 * np.pi * 130.8127825 * samples[8192:] / 44100.0)
        envelope = np.zeros(samples.shape, dtype=np.float64)
        elapsed = samples[16128:] - 16128.0
        envelope[16128:] = np.minimum(1.0, (elapsed + 1.0) / 64.0) * np.exp(-elapsed / 2048.0)
        waveform += envelope * np.sin(2.0 * np.pi * 261.625565 * samples / 44100.0)
        source = {
            "id": fixture_id,
            "order": 1,
            "category": "positive",
            "family": "IDENTIFIABLE_OVERLAP",
            "pitch_band": "mid",
            "candidate_pitch": 60,
            "parameters": {"old_pitch": 48, "new_onset": 16128},
        }
        fixture_record = {"source_fixture_record": source}
        test = replace(self.plan.tests[4], fixture_ids=(fixture_id,))
        test_plan = replace(
            self.plan,
            fixtures=(MappingProxyType(source),),
            tests=(test,),
        )
        context = H25EvidenceProducerContext(
            np=np,
            plan=test_plan,
            waveforms=MappingProxyType({fixture_id: waveform}),
            fixture_records=MappingProxyType({fixture_id: fixture_record}),
            causal_replay_traces=MappingProxyType({
                fixture_id: H25CausalReplayTrace(
                    fixture_id=fixture_id,
                    observed_through_sample=16383,
                    initial_active_pitches=(48,),
                    transitions=(),
                )
            }),
            started_ns=time.perf_counter_ns(),
            peak_rss_bytes=1,
            operational_counters=MappingProxyType({
                "GPU_device_count": 0,
                "scientific_process_count": 1,
                "model_inference_call_count": 0,
                "hidden_repeated_pitch_shift_inference_count": 0,
            }),
            observed_fixture_ids=(fixture_id,),
            observed_test_ids=(test.test_id,),
        )
        evidence = produce_h25_test_evidence(context, test)
        canonical_json_bytes(evidence)
        self.assertNotIn("pass", evidence)
        self.assertNotIn("verdict", evidence)
        outcome = recompute_h25_persisted_evidence(test_plan, test.test_id, evidence)
        self.assertTrue(outcome.final_pass)

    def test_recomputer_has_no_engine_import_and_rederives_outcome(self) -> None:
        source = (self.root / "src/polyphonic/harmonic_censoring_h25_recomputer.py").read_text(encoding="utf-8")
        self.assertNotIn("harmonic_censoring_h25_scientific_engine", source)
        self.assertNotIn("build_typed_harmonic_graph", source)
        plan, test, context = self._test_only_context(self.plan.tests[9])
        evidence = produce_h25_test_evidence(context, test)
        forged = dict(evidence)
        forged_measurements = [dict(item) for item in evidence["fixture_measurements"]]
        forged_measurements[0]["outcome"] = "NO_BIRTH"
        forged["fixture_measurements"] = forged_measurements
        with self.assertRaisesRegex(ValueError, "independently derived"):
            recompute_h25_persisted_evidence(plan, test.test_id, forged)

    def test_p0_002_persists_raw_spectrum_and_recomputes_real_scaling_equivalence(self) -> None:
        plan, test, context = self._test_only_context(self.plan.tests[1])
        evidence = produce_h25_test_evidence(context, test)
        operator = evidence["operator_measurements"][0]
        self.assertEqual(set(operator["raw_operands"]), {"candidate_pitch", "power", "frequencies_hz"})
        self.assertNotIn("scalar_residual", operator)
        self.assertEqual(len(evidence["analytic_scaling_operands"]), 89 * 20)
        self.assertTrue(recompute_h25_persisted_evidence(plan, test.test_id, evidence).final_pass)

    def test_p0_007_uses_target_hop_not_resolution_hop(self) -> None:
        plan, test, context = self._test_only_context(self.plan.tests[6])
        evidence = produce_h25_test_evidence(context, test)
        self.assertEqual(evidence["causal_boundaries"], [{
            "fixture_id": context.plan.fixture_ids[0],
            "short_current_end": 16383,
            "long_current_end": 16383,
            "short_previous_end": 16127,
            "long_previous_end": 16127,
            "maximum_sample_read": 16383,
        }])
        self.assertTrue(recompute_h25_persisted_evidence(plan, test.test_id, evidence).final_pass)

    def test_p2_002_covers_exact_hop_translations(self) -> None:
        plan, test, context = self._test_only_context(self.plan.tests[19])
        evidence = produce_h25_test_evidence(context, test)
        translations = evidence["hop_translation_results"][0]["translations"]
        self.assertEqual([item["hop_translation"] for item in translations], [0, 1, 2, 4])
        self.assertEqual({item["resolution_delay_hops"] for item in translations}, {1})
        self.assertTrue(recompute_h25_persisted_evidence(plan, test.test_id, evidence).final_pass)

    def test_p2_007_requires_external_cross_runtime_observation(self) -> None:
        plan, test, context = self._test_only_context(self.plan.tests[24])
        evidence = produce_h25_test_evidence(context, test)
        self.assertFalse(recompute_h25_persisted_evidence(plan, test.test_id, evidence).primary_pass)
        completed = dict(evidence)
        completed["cross_runtime_observation"] = {
            "fixture_ids": list(test.fixture_ids),
            "categories_and_masks_exact": True,
            "maximum_float_error": 0.0,
        }
        self.assertTrue(recompute_h25_persisted_evidence(plan, test.test_id, completed).final_pass)

    def test_active_state_must_be_replayable_and_target_hop_bounded(self) -> None:
        plan, test, context = self._test_only_context(self.plan.tests[9])
        evidence = produce_h25_test_evidence(context, test)
        forged = dict(evidence)
        rows = [dict(item) for item in evidence["fixture_measurements"]]
        trace = dict(rows[0]["causal_replay_trace"])
        trace["derived_active_pitches"] = []
        rows[0]["causal_replay_trace"] = trace
        forged["fixture_measurements"] = rows
        with self.assertRaisesRegex(ValueError, "differs from independent replay"):
            recompute_h25_persisted_evidence(plan, test.test_id, forged)

    def test_runner_is_dormant_before_numpy_import_or_population_access(self) -> None:
        self.assertTrue(H25_DORMANT_SCIENTIFIC_RUNNER_IMPLEMENTED)
        source = (self.root / "src/polyphonic/run_harmonic_censoring_h25_scientific.py").read_text(encoding="utf-8")
        engine_source = (self.root / "src/polyphonic/harmonic_censoring_h25_scientific_engine.py").read_text(encoding="utf-8")
        for text in (source, engine_source):
            self.assertNotIn("import numpy", text)
            self.assertNotIn("import tensorflow", text)
            self.assertNotIn("if __name__ ==", text)
        with self.assertRaisesRegex(PermissionError, "dormant"):
            require_h25_scientific_execution_authorized()
        with self.assertRaisesRegex(PermissionError, "dormant"):
            run_h25_scientific_execution(self.root)


if __name__ == "__main__":
    unittest.main()
