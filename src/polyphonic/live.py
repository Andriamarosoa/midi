"""Low-latency microphone-to-polyphonic-MIDI desktop application."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import asdict
import json
import queue
import signal
import time
from pathlib import Path
import wave

import numpy as np

from src.polyphonic.audio_gain import (
    apply_manual_audio_gain,
    validate_manual_audio_gain,
)
from src.polyphonic.audio_evidence import PolyphonicAudioEvidencePolicy
from src.polyphonic.decoder import PolyphonicDecoder, PolyphonicDecoderConfig
from src.polyphonic.input_level import CausalModelInputLeveler
from src.polyphonic.tflite_runtime import PolyphonicBundle, TFLitePolyphonicModel
from src.product.audio_io import managed_input_stream
from src.product.backpressure import LiveBackpressure
from src.product.live import list_devices, make_sink, parse_device
from src.stream.ring_buffer import MonoRingBuffer


NOTE_ON_REASON_CODES = {
    "model_onset": 1,
    "frame_attack": 2,
    "frame_fallback": 3,
    "harmonic_strong_frame": 4,
    "retrigger": 5,
    "legacy": 6,
    "chord_completion": 7,
}


def _decoder(bundle: PolyphonicBundle) -> PolyphonicDecoder:
    metadata = bundle.metadata
    if "decoder" in metadata:
        return PolyphonicDecoder(PolyphonicDecoderConfig(**metadata["decoder"]))
    frame_threshold = float(metadata["frame_threshold"])
    return PolyphonicDecoder(PolyphonicDecoderConfig(
        midi_min=int(metadata["min_pitch"]),
        midi_max=int(metadata["max_pitch"]),
        maximum_polyphony=int(metadata["maximum_polyphony"]),
        frame_on_threshold=frame_threshold,
        strong_frame_threshold=min(0.95, max(0.80, frame_threshold + 0.25)),
        frame_off_threshold=max(0.05, frame_threshold * 0.60),
        onset_threshold=float(metadata["onset_threshold"]),
    ))


def run(args) -> int:
    bundle = PolyphonicBundle(args.artifacts)
    level_metadata = bundle.metadata.get(
        "automatic_model_input_level",
        {},
    )
    configured_auto_level = (
        bool(level_metadata.get("enabled_by_default", False))
        if isinstance(level_metadata, dict)
        else False
    )
    auto_level_enabled = (
        configured_auto_level
        if args.auto_level is None
        else bool(args.auto_level)
    )
    runtime = TFLitePolyphonicModel(bundle, args.threads)
    decoder = _decoder(bundle)
    sample_rate = int(bundle.metadata["sample_rate"])
    hop_samples = int(bundle.metadata["hop_samples"])
    window_samples = int(bundle.metadata["max_window_samples"])
    ring = MonoRingBuffer(window_samples)
    window = np.zeros(window_samples, np.float32)
    audio_evidence_policy = PolyphonicAudioEvidencePolicy.from_metadata(
        sample_rate,
        hop_samples,
        bundle.metadata,
        calibration_s=args.calibration_s,
    )
    synthetic_priming_hops = (
        audio_evidence_policy.prime_silence()
        if args.synthetic_calibration
        else 0
    )
    input_leveler = CausalModelInputLeveler.from_metadata(
        sample_rate,
        hop_samples,
        float(bundle.metadata["normalization_gain"]),
        window_samples,
        bundle.metadata,
    )
    backpressure = LiveBackpressure(
        max_backlog_hops=int(bundle.metadata.get("max_live_backlog_hops", 3))
    )
    for _ in range(20):
        runtime.infer(window)

    hops: queue.Queue[tuple[np.ndarray, float]] = queue.Queue(maxsize=64)
    overflow = 0
    audio_status_events = 0
    invalid_audio_blocks = 0
    queue_overflow_drops = 0
    backlog_discarded_hops = 0
    stopped = False
    stop_reason = "unknown"
    output_health_error = None
    last_valid_audio_callback = time.monotonic()
    runtime_error = None
    cleanup_errors: list[str] = []

    def callback(indata, frames, time_info, status) -> None:
        nonlocal overflow, audio_status_events, invalid_audio_blocks
        nonlocal queue_overflow_drops, last_valid_audio_callback
        if status:
            audio_status_events += 1
            overflow += 1
            return
        if frames != hop_samples or indata.ndim != 2:
            invalid_audio_blocks += 1
            overflow += 1
            return
        last_valid_audio_callback = time.monotonic()
        hop = np.asarray(indata[:, 0], np.float32).copy()
        try:
            hops.put_nowait((hop, time.perf_counter()))
        except queue.Full:
            overflow += 1
            queue_overflow_drops += 1
            # Keep latency bounded: discard the oldest hop and retain the
            # newest microphone audio instead of terminating the session.
            try:
                hops.get_nowait()
            except queue.Empty:
                pass
            try:
                hops.put_nowait((hop, time.perf_counter()))
            except queue.Full:
                pass

    def request_stop(signum, frame) -> None:
        nonlocal stopped, stop_reason
        stopped = True
        stop_reason = "signal"

    def discard_queued_hops() -> int:
        """Discard every queued hop without reordering concurrent callbacks."""
        removed = 0
        while True:
            try:
                hops.get_nowait()
                removed += 1
            except queue.Empty:
                break
        return removed

    signal.signal(signal.SIGINT, request_stop)
    sink = None
    audio_input_info = None
    debug_handle = None
    debug_writer = None
    record_handle = None
    record_buffer = bytearray()
    recorded_samples = 0
    try:
        sink = make_sink(args, sample_rate, hop_samples)
        if args.debug_csv:
            args.debug_csv.parent.mkdir(parents=True, exist_ok=True)
            debug_handle = args.debug_csv.open(
                "w", encoding="utf-8", newline=""
            )
        if args.record_wav:
            args.record_wav.parent.mkdir(parents=True, exist_ok=True)
            record_handle = wave.open(str(args.record_wav), "wb")
            record_handle.setnchannels(1)
            record_handle.setsampwidth(2)
            record_handle.setframerate(sample_rate)
    except Exception:
        if debug_handle is not None:
            try:
                debug_handle.close()
            except Exception as cleanup_exc:
                cleanup_errors.append(f"debug CSV: {cleanup_exc!r}")
        if record_handle is not None:
            try:
                record_handle.close()
            except Exception as cleanup_exc:
                cleanup_errors.append(f"WAV: {cleanup_exc!r}")
        if sink is not None:
            try:
                sink.close()
            except Exception as cleanup_exc:
                cleanup_errors.append(
                    f"sortie MIDI/audio: {cleanup_exc!r}"
                )
        if cleanup_errors:
            print("Erreurs de nettoyage: " + "; ".join(cleanup_errors))
        raise
    trace = None
    if args.debug_npz:
        trace = {
            "frame_index": [],
            "time_s": [],
            "visible_samples": [],
            "decoder_reset_before": [],
            "audio_active": [],
            "audio_onset": [],
            "decoder_audio_onset_hop_index": [],
            "audio_onset_recent": [],
            "auto_level_gain_db": [],
            "projected_model_peak": [],
            "raw_rms_dbfs": [],
            "rms_dbfs": [],
            "activity_open_threshold_dbfs": [],
            "activity_close_threshold_dbfs": [],
            "onset_rms_threshold_dbfs": [],
            "onset_detector_score": [],
            "frame_probability": [],
            "onset_probability": [],
            "harmonic_amplitude": [],
            "harmonic_offset_cents": [],
            "active_mask": [],
            "note_on_mask": [],
            "note_off_mask": [],
            "note_on_velocity": [],
            "note_on_reason_code": [],
        }
    calibrated_announced = False
    last_status = time.monotonic()
    started = time.monotonic()
    calibrated_frames = 0
    skipped = 0
    inference_ms: list[float] = []
    pipeline_ms: list[float] = []
    raw_input_rms_dbfs: list[float] = []
    input_rms_dbfs: list[float] = []
    input_peak_absolute = 0.0
    capture_peak_absolute = 0.0
    clipped_input_samples = 0
    clipped_capture_samples = 0
    gain_induced_clipped_samples = 0
    projected_model_clipped_values = 0
    audio_active_frames = 0
    audio_active_with_notes_frames = 0
    audio_active_empty_frames = 0
    current_audio_active_empty_frames = 0
    longest_audio_active_empty_frames = 0
    audio_inactive_frames = 0
    current_inactive_frames = 0
    longest_inactive_frames = 0
    strong_predictions_vetoed_by_activity_gate = 0
    maximum_simultaneous_notes = 0
    processed_overflow = 0
    recoveries = 0
    recovery_events: list[
        dict[str, float | int | str | list[int]]
    ] = []
    decoder_reset_before = False
    pending_audio_onset_hop: int | None = None
    event_reason_counts: Counter[str] = Counter()
    note_on_reason_counts: Counter[str] = Counter()
    current_level_gain = 1.0
    current_level_gain_db = 0.0
    current_projected_model_peak = 0.0
    minimum_context_samples = min(
        window_samples,
        max(hop_samples, int(bundle.metadata.get("minimum_window_samples", 512))),
    )
    print(
        f"Guitar MIDI Poly {bundle.metadata['product_version']} | "
        f"hop={hop_samples / sample_rate * 1000.0:.2f} ms | "
        f"max_notes={bundle.metadata['maximum_polyphony']}"
    )
    if synthetic_priming_hops:
        print(
            "Calibration silencieuse deterministe terminee "
            f"({synthetic_priming_hops} hops)."
        )
    else:
        print("Reste silencieux pendant la calibration. Ctrl+C pour arreter.")
    try:
        with managed_input_stream(
            preferred_device=parse_device(args.audio_device),
            channels=1,
            samplerate=sample_rate,
            blocksize=hop_samples,
            dtype="float32",
            latency="low",
            callback=callback,
        ) as (_input_stream, audio_input_info):
            while not stopped:
                if args.duration_s and time.monotonic() - started >= args.duration_s:
                    stop_reason = "duration"
                    break
                output_health_error = sink.health_error()
                if output_health_error is not None:
                    try:
                        for event in decoder.panic():
                            sink.send(event)
                        sink.panic()
                    except Exception:
                        pass
                    stop_reason = "audio_output_error"
                    print(f"Sortie audio en erreur: {output_health_error}")
                    break
                try:
                    hop, captured_at = hops.get(timeout=0.25)
                except queue.Empty:
                    callback_stalled = (
                        not bool(getattr(_input_stream, "active", True))
                        or time.monotonic() - last_valid_audio_callback > 1.0
                    )
                    if callback_stalled:
                        try:
                            for event in decoder.panic():
                                sink.send(event)
                            sink.panic()
                        except Exception:
                            pass
                        stop_reason = "audio_input_stalled"
                        print(
                            "Le flux microphone ne fournit plus de blocs: "
                            "arret propre apres panic MIDI."
                        )
                        stopped = True
                        break
                    if overflow != processed_overflow:
                        discarded = discard_queued_hops()
                        backlog_discarded_hops += discarded
                        processed_overflow = overflow
                        preserved_notes = decoder.reset_observation_continuity()
                        ring.reset()
                        audio_evidence_policy.reset_continuity()
                        pending_audio_onset_hop = None
                        backpressure = LiveBackpressure(
                            max_backlog_hops=int(
                                bundle.metadata.get("max_live_backlog_hops", 3)
                            )
                        )
                        recoveries += 1
                        decoder_reset_before = True
                        recovery_events.append({
                            "time_s": time.monotonic() - started,
                            "reason": "audio_callback_stall",
                            "discarded_hops": discarded,
                            "total_dropped_hops": (
                                overflow + backlog_discarded_hops
                            ),
                            "preserved_active_notes": list(preserved_notes),
                        })
                        print(
                            "Incident audio sans nouveau bloc: contexte causal "
                            "reinitialise, notes actives conservees "
                            f"{list(preserved_notes)}."
                        )
                    continue
                if overflow != processed_overflow:
                    discarded = 1 + discard_queued_hops()
                    backlog_discarded_hops += discarded
                    processed_overflow = overflow
                    preserved_notes = decoder.reset_observation_continuity()
                    ring.reset()
                    audio_evidence_policy.reset_continuity()
                    pending_audio_onset_hop = None
                    backpressure = LiveBackpressure(
                        max_backlog_hops=int(
                            bundle.metadata.get("max_live_backlog_hops", 3)
                        )
                    )
                    recoveries += 1
                    decoder_reset_before = True
                    recovery_events.append({
                        "time_s": time.monotonic() - started,
                        "reason": "audio_callback",
                        "discarded_hops": discarded,
                        "total_dropped_hops": (
                            overflow + backlog_discarded_hops
                        ),
                        "preserved_active_notes": list(preserved_notes),
                    })
                    print(
                        "Surcharge audio recuperee: contexte causal reinitialise "
                        f"(dropped={overflow + backlog_discarded_hops}), "
                        f"notes actives conservees {list(preserved_notes)}."
                    )
                    continue
                input_peak_absolute = max(
                    input_peak_absolute,
                    float(np.max(np.abs(hop), initial=0.0)),
                )
                raw_rms = float(np.sqrt(
                    np.mean(np.asarray(hop, np.float64) ** 2)
                    + 1e-12
                ))
                raw_input_rms_dbfs.append(
                    PolyphonicAudioEvidencePolicy.rms_to_dbfs(raw_rms)
                )
                clipped_input_samples += int(
                    np.count_nonzero(np.abs(hop) >= 0.999)
                )
                capture_hop, induced_clipping = apply_manual_audio_gain(
                    hop,
                    args.audio_gain,
                )
                gain_induced_clipped_samples += induced_clipping
                capture_peak_absolute = max(
                    capture_peak_absolute,
                    float(np.max(np.abs(capture_hop), initial=0.0)),
                )
                clipped_capture_samples += int(
                    np.count_nonzero(np.abs(capture_hop) >= 0.999)
                )
                audio_evidence = audio_evidence_policy.process(capture_hop)
                onset_evidence = audio_evidence.onset
                activity_evidence = audio_evidence.activity
                if onset_evidence.is_onset:
                    pending_audio_onset_hop = audio_evidence.audio_hop_index
                if record_handle is not None:
                    # Keep the manual capture correction, but never bake the
                    # automatic model-only level into the evidence WAV.
                    pcm = np.clip(capture_hop, -1.0, 1.0)
                    record_buffer.extend(
                        np.rint(pcm * 32767.0).astype("<i2").tobytes()
                    )
                    recorded_samples += len(capture_hop)
                    if len(record_buffer) >= sample_rate * 2:
                        record_handle.writeframesraw(record_buffer)
                        record_buffer.clear()
                ring.write(capture_hop)
                level = input_leveler.process(
                    capture_hop,
                    audio_active=bool(
                        audio_evidence.calibrated
                        and activity_evidence.active
                    ),
                )
                if not audio_evidence.calibrated:
                    continue
                if not auto_level_enabled:
                    current_level_gain = 1.0
                    current_level_gain_db = 0.0
                    current_projected_model_peak = (
                        float(np.max(np.abs(capture_hop), initial=0.0))
                        * float(bundle.metadata["normalization_gain"])
                    )
                else:
                    current_level_gain = level.gain
                    current_level_gain_db = level.gain_db
                    current_projected_model_peak = level.projected_model_peak
                input_rms_dbfs.append(onset_evidence.rms_dbfs)
                if not calibrated_announced:
                    calibrated_announced = True
                    print("Calibration terminee. Le moteur polyphonique est actif.")
                    if not bool(activity_evidence.calibration_stable):
                        print(
                            "Calibration audio instable: le seuil de securite "
                            "a ete fige apres la duree maximale."
                        )
                    print(
                        "Gate audio fige: "
                        f"open={activity_evidence.open_threshold_dbfs:.1f}dBFS "
                        f"close={activity_evidence.close_threshold_dbfs:.1f}dBFS"
                    )
                calibrated_frames += 1
                if ring.available < minimum_context_samples:
                    continue
                ring.copy_latest_into(window)
                if not auto_level_enabled:
                    current_projected_model_peak = (
                        float(np.max(np.abs(window), initial=0.0))
                        * float(bundle.metadata["normalization_gain"])
                    )
                queue_depth = hops.qsize()
                try:
                    skip_inference = backpressure.decide(queue_depth)
                except RuntimeError:
                    # The queued audio is already too old for a live musical
                    # response. Discard it and resume from a clean context.
                    discarded = 1 + discard_queued_hops()
                    backlog_discarded_hops += discarded
                    preserved_notes = decoder.reset_observation_continuity()
                    ring.reset()
                    audio_evidence_policy.reset_continuity()
                    pending_audio_onset_hop = None
                    backpressure = LiveBackpressure(
                        max_backlog_hops=int(
                            bundle.metadata.get("max_live_backlog_hops", 3)
                        )
                    )
                    recoveries += 1
                    decoder_reset_before = True
                    recovery_events.append({
                        "time_s": time.monotonic() - started,
                        "reason": "dangerous_backlog",
                        "discarded_hops": discarded,
                        "total_dropped_hops": (
                            overflow + backlog_discarded_hops
                        ),
                        "preserved_active_notes": list(preserved_notes),
                    })
                    print(
                        "Backlog audio recupere: blocs perimes abandonnes "
                        f"(dropped={overflow + backlog_discarded_hops}), "
                        f"notes actives conservees {list(preserved_notes)}."
                    )
                    continue
                if skip_inference:
                    skipped += 1
                    continue
                if current_level_gain != 1.0:
                    window *= current_level_gain
                projected_model_clipped_values += int(np.count_nonzero(
                    np.abs(window)
                    * float(bundle.metadata["normalization_gain"])
                    >= 0.999
                ))
                prediction = runtime.infer(window, ring.available)
                audio_active = activity_evidence.active
                if audio_active:
                    audio_active_frames += 1
                    current_inactive_frames = 0
                else:
                    audio_inactive_frames += 1
                    current_inactive_frames += 1
                    longest_inactive_frames = max(
                        longest_inactive_frames, current_inactive_frames
                    )
                    if (
                        float(np.max(prediction.frame_probability))
                        >= decoder.config.strong_frame_threshold
                    ):
                        strong_predictions_vetoed_by_activity_gate += 1
                consumed_audio_onset_hop = pending_audio_onset_hop
                independent_note = getattr(
                    prediction, "independent_note_probability", None
                )
                decoder_gate_kwargs = (
                    {} if independent_note is None
                    else {"independent_note_probability": independent_note}
                )
                events = decoder.step(
                    prediction.frame_probability,
                    prediction.onset_probability,
                    prediction.harmonic_amplitude,
                    audio_active=audio_active,
                    # The shared audio clock advances for every captured hop,
                    # including hops whose model inference was skipped.
                    audio_hop_index=audio_evidence.audio_hop_index,
                    audio_onset=consumed_audio_onset_hop is not None,
                    audio_onset_hop_index=consumed_audio_onset_hop,
                    **decoder_gate_kwargs,
                )
                pending_audio_onset_hop = None
                for event in events:
                    sink.send(event)
                    event_reason_counts[event.reason or "unspecified"] += 1
                    if event.kind == "note_on":
                        note_on_reason_counts[event.reason or "unspecified"] += 1
                elapsed = (time.perf_counter() - captured_at) * 1000.0
                inference_ms.append(prediction.inference_ms)
                pipeline_ms.append(elapsed)
                active_notes = tuple(
                    bundle.metadata["min_pitch"] + int(index)
                    for index in np.flatnonzero(decoder.active)
                )
                maximum_simultaneous_notes = max(
                    maximum_simultaneous_notes, len(active_notes)
                )
                if audio_active:
                    if active_notes:
                        audio_active_with_notes_frames += 1
                        current_audio_active_empty_frames = 0
                    else:
                        audio_active_empty_frames += 1
                        current_audio_active_empty_frames += 1
                        longest_audio_active_empty_frames = max(
                            longest_audio_active_empty_frames,
                            current_audio_active_empty_frames,
                        )
                else:
                    current_audio_active_empty_frames = 0
                if trace is not None:
                    note_on_mask = np.zeros(decoder.classes, np.bool_)
                    note_off_mask = np.zeros(decoder.classes, np.bool_)
                    note_on_velocity = np.zeros(decoder.classes, np.uint8)
                    note_on_reason_code = np.zeros(decoder.classes, np.uint8)
                    for event in events:
                        class_index = event.pitch - decoder.config.midi_min
                        if event.kind == "note_on":
                            note_on_mask[class_index] = True
                            note_on_velocity[class_index] = event.velocity
                            note_on_reason_code[class_index] = (
                                NOTE_ON_REASON_CODES.get(event.reason, 255)
                            )
                        elif event.kind == "note_off":
                            note_off_mask[class_index] = True
                    trace["frame_index"].append(decoder.frame_index)
                    trace["time_s"].append(audio_evidence.time_s)
                    trace["visible_samples"].append(ring.available)
                    trace["decoder_reset_before"].append(decoder_reset_before)
                    trace["audio_active"].append(audio_active)
                    trace["audio_onset"].append(onset_evidence.is_onset)
                    trace["decoder_audio_onset_hop_index"].append(
                        -1
                        if consumed_audio_onset_hop is None
                        else consumed_audio_onset_hop
                    )
                    trace["audio_onset_recent"].append(
                        decoder.recent_audio_onset
                    )
                    trace["auto_level_gain_db"].append(
                        current_level_gain_db
                    )
                    trace["projected_model_peak"].append(
                        current_projected_model_peak
                    )
                    trace["raw_rms_dbfs"].append(
                        PolyphonicAudioEvidencePolicy.rms_to_dbfs(raw_rms)
                    )
                    trace["rms_dbfs"].append(onset_evidence.rms_dbfs)
                    trace["activity_open_threshold_dbfs"].append(
                        activity_evidence.open_threshold_dbfs
                    )
                    trace["activity_close_threshold_dbfs"].append(
                        activity_evidence.close_threshold_dbfs
                    )
                    trace["onset_rms_threshold_dbfs"].append(
                        PolyphonicAudioEvidencePolicy.rms_to_dbfs(
                            onset_evidence.rms_threshold
                        )
                    )
                    trace["onset_detector_score"].append(onset_evidence.score)
                    trace["frame_probability"].append(
                        prediction.frame_probability.copy()
                    )
                    trace["onset_probability"].append(
                        prediction.onset_probability.copy()
                    )
                    trace["harmonic_amplitude"].append(
                        prediction.harmonic_amplitude.copy()
                    )
                    trace["harmonic_offset_cents"].append(
                        prediction.harmonic_offset_cents.copy()
                    )
                    trace["active_mask"].append(decoder.active.copy())
                    trace["note_on_mask"].append(note_on_mask)
                    trace["note_off_mask"].append(note_off_mask)
                    trace["note_on_velocity"].append(note_on_velocity)
                    trace["note_on_reason_code"].append(note_on_reason_code)
                    decoder_reset_before = False
                if debug_handle is not None:
                    top_frame_indices = np.argsort(
                        prediction.frame_probability
                    )[-6:][::-1]
                    top_onset_indices = np.argsort(
                        prediction.onset_probability
                    )[-6:][::-1]
                    row = {
                        "frame": decoder.frame_index,
                        "time_s": audio_evidence.time_s,
                        "active_notes": " ".join(map(str, active_notes)),
                        "events": " ".join(
                            f"{event.kind}:{event.pitch}:{event.reason}"
                            for event in events
                        ),
                        "audio_active": int(audio_active),
                        "audio_onset": int(onset_evidence.is_onset),
                        "decoder_audio_onset_hop_index": (
                            consumed_audio_onset_hop
                        ),
                        "audio_onset_recent": int(decoder.recent_audio_onset),
                        "auto_level_gain_db": current_level_gain_db,
                        "projected_model_peak": current_projected_model_peak,
                        "raw_rms_dbfs": (
                            PolyphonicAudioEvidencePolicy.rms_to_dbfs(
                                raw_rms
                            )
                        ),
                        "onset_detector_confidence": onset_evidence.confidence,
                        "onset_detector_armed": int(onset_evidence.armed),
                        "rms_dbfs": onset_evidence.rms_dbfs,
                        "rms_threshold": onset_evidence.rms_threshold,
                        "onset_rms_threshold_dbfs": (
                            PolyphonicAudioEvidencePolicy.rms_to_dbfs(
                                onset_evidence.rms_threshold
                            )
                        ),
                        "activity_open_threshold_dbfs": (
                            activity_evidence.open_threshold_dbfs
                        ),
                        "activity_close_threshold_dbfs": (
                            activity_evidence.close_threshold_dbfs
                        ),
                        "growth_threshold": onset_evidence.growth_threshold,
                        "flux_threshold": onset_evidence.flux_threshold,
                        "rms_growth": onset_evidence.rms_growth,
                        "spectral_flux": onset_evidence.spectral_flux,
                        "onset_detector_score": onset_evidence.score,
                        "top_frame": " ".join(
                            f"{bundle.metadata['min_pitch'] + int(index)}:"
                            f"{float(prediction.frame_probability[index]):.5f}"
                            for index in top_frame_indices
                        ),
                        "top_onset": " ".join(
                            f"{bundle.metadata['min_pitch'] + int(index)}:"
                            f"{float(prediction.onset_probability[index]):.5f}"
                            for index in top_onset_indices
                        ),
                        "inference_ms": prediction.inference_ms,
                        "pipeline_ms": elapsed,
                        "queue_depth": queue_depth,
                        "strong_prediction_vetoed_by_activity_gate": int(
                            not audio_active
                            and float(np.max(prediction.frame_probability))
                            >= decoder.config.strong_frame_threshold
                        ),
                    }
                    if debug_writer is None:
                        debug_writer = csv.DictWriter(debug_handle, fieldnames=list(row))
                        debug_writer.writeheader()
                    debug_writer.writerow(row)
                now = time.monotonic()
                if now - last_status >= 1.0:
                    print(
                        f"notes={list(active_notes)} infer={prediction.inference_ms:.2f}ms "
                        f"pipeline={elapsed:.2f}ms skipped={skipped} "
                        f"dropped={overflow + backlog_discarded_hops} "
                        f"input={onset_evidence.rms_dbfs:.1f}dBFS "
                        f"level={current_level_gain_db:+.1f}dB "
                        f"gate={'on' if audio_active else 'off'}"
                    )
                    last_status = now
    except Exception as exc:
        runtime_error = repr(exc)
        if stop_reason == "unknown":
            stop_reason = "runtime_error"
        print(f"Erreur live polyphonique: {runtime_error}")
    finally:
        try:
            for event in decoder.panic():
                sink.send(event)
        except Exception as exc:
            cleanup_errors.append(f"panic decodeur: {exc!r}")
        try:
            sink.close()
        except Exception as exc:
            cleanup_errors.append(f"sortie MIDI/audio: {exc!r}")
        if debug_handle is not None:
            try:
                debug_handle.close()
            except Exception as exc:
                cleanup_errors.append(f"debug CSV: {exc!r}")
        if record_handle is not None:
            if record_buffer:
                try:
                    record_handle.writeframesraw(record_buffer)
                    record_buffer.clear()
                except Exception as exc:
                    cleanup_errors.append(f"ecriture WAV: {exc!r}")
            try:
                record_handle.close()
            except Exception as exc:
                cleanup_errors.append(f"fermeture WAV: {exc!r}")

    if stop_reason == "unknown":
        stop_reason = "cleanup_error" if cleanup_errors else "completed"

    if trace is not None:
        args.debug_npz.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            args.debug_npz,
            frame_index=np.asarray(trace["frame_index"], np.int64),
            time_s=np.asarray(trace["time_s"], np.float64),
            visible_samples=np.asarray(trace["visible_samples"], np.int32),
            decoder_reset_before=np.asarray(
                trace["decoder_reset_before"], np.bool_
            ),
            audio_active=np.asarray(trace["audio_active"], np.bool_),
            audio_onset=np.asarray(trace["audio_onset"], np.bool_),
            decoder_audio_onset_hop_index=np.asarray(
                trace["decoder_audio_onset_hop_index"], np.int64
            ),
            audio_onset_recent=np.asarray(
                trace["audio_onset_recent"], np.bool_
            ),
            auto_level_gain_db=np.asarray(
                trace["auto_level_gain_db"], np.float32
            ),
            projected_model_peak=np.asarray(
                trace["projected_model_peak"], np.float32
            ),
            raw_rms_dbfs=np.asarray(
                trace["raw_rms_dbfs"], np.float32
            ),
            rms_dbfs=np.asarray(trace["rms_dbfs"], np.float32),
            manual_audio_gain=np.asarray(args.audio_gain, np.float32),
            activity_open_threshold_dbfs=np.asarray(
                trace["activity_open_threshold_dbfs"], np.float32
            ),
            activity_close_threshold_dbfs=np.asarray(
                trace["activity_close_threshold_dbfs"], np.float32
            ),
            onset_rms_threshold_dbfs=np.asarray(
                trace["onset_rms_threshold_dbfs"], np.float32
            ),
            onset_detector_score=np.asarray(
                trace["onset_detector_score"], np.float32
            ),
            frame_probability=np.asarray(
                trace["frame_probability"], np.float32
            ),
            onset_probability=np.asarray(
                trace["onset_probability"], np.float32
            ),
            harmonic_amplitude=np.asarray(
                trace["harmonic_amplitude"], np.float32
            ),
            harmonic_offset_cents=np.asarray(
                trace["harmonic_offset_cents"], np.float32
            ),
            active_mask=np.asarray(trace["active_mask"], np.bool_),
            note_on_mask=np.asarray(trace["note_on_mask"], np.bool_),
            note_off_mask=np.asarray(trace["note_off_mask"], np.bool_),
            note_on_velocity=np.asarray(
                trace["note_on_velocity"], np.uint8
            ),
            note_on_reason_code=np.asarray(
                trace["note_on_reason_code"], np.uint8
            ),
            note_on_reason_labels=np.asarray(
                [
                    f"{code}:{reason}"
                    for reason, code in sorted(
                        NOTE_ON_REASON_CODES.items(), key=lambda item: item[1]
                    )
                ],
                dtype="<U32",
            ),
            midi_min=np.asarray(bundle.metadata["min_pitch"], np.int16),
            midi_max=np.asarray(bundle.metadata["max_pitch"], np.int16),
            sample_rate=np.asarray(sample_rate, np.int32),
            hop_samples=np.asarray(hop_samples, np.int32),
        )

    if args.report_json:
        def stats(values: list[float]) -> dict[str, float | int | None]:
            data = np.asarray(values, np.float64)
            return {
                "count": int(len(data)),
                "mean": float(np.mean(data)) if len(data) else None,
                "p95": float(np.percentile(data, 95)) if len(data) else None,
                "max": float(np.max(data)) if len(data) else None,
            }
        audio_outputs = sink.diagnostics()
        output_latencies = [
            float(item["latency_ms"])
            for item in audio_outputs
            if item.get("direction") == "output" and item.get("latency_ms") is not None
        ]
        negotiated_audio_io_ms = (
            audio_input_info.latency_ms + sum(output_latencies)
            if audio_input_info is not None and output_latencies else None
        )
        report = {
            "duration_requested_s": args.duration_s,
            "calibrated_frames": calibrated_frames,
            "skipped_inferences": skipped,
            "skip_percent": 100.0 * skipped / max(calibrated_frames, 1),
            "audio_hops_dropped": overflow + backlog_discarded_hops,
            "audio_status_events": audio_status_events,
            "invalid_audio_blocks": invalid_audio_blocks,
            "queue_overflow_drops": queue_overflow_drops,
            "backlog_discarded_hops": backlog_discarded_hops,
            "overload_recoveries": recoveries,
            "overload_recovery_events": recovery_events,
            "stop_reason": stop_reason,
            "inference_ms": stats(inference_ms),
            "pipeline_ms": stats(pipeline_ms),
            "raw_input_rms_dbfs": stats(raw_input_rms_dbfs),
            "input_rms_dbfs": stats(input_rms_dbfs),
            "input_peak_dbfs": PolyphonicAudioEvidencePolicy.rms_to_dbfs(
                input_peak_absolute
            ),
            "capture_peak_dbfs": (
                PolyphonicAudioEvidencePolicy.rms_to_dbfs(
                    capture_peak_absolute
                )
            ),
            "clipped_input_samples": clipped_input_samples,
            "clipped_capture_samples": clipped_capture_samples,
            "gain_induced_clipped_samples": (
                gain_induced_clipped_samples
            ),
            "projected_model_clipped_values": projected_model_clipped_values,
            "capture_gain": float(args.audio_gain),
            "automatic_model_input_level": (
                {"enabled": False}
                if not auto_level_enabled
                else input_leveler.diagnostics()
            ),
            "model_normalization_gain": float(
                bundle.metadata["normalization_gain"]
            ),
            "audio_activity_gate": (
                audio_evidence_policy.activity_diagnostics()
            ),
            "audio_evidence": audio_evidence_policy.diagnostics(),
            "synthetic_calibration": bool(args.synthetic_calibration),
            "audio_active_frames": audio_active_frames,
            "audio_active_note_coverage": {
                "with_active_notes_frames": audio_active_with_notes_frames,
                "empty_active_audio_frames": audio_active_empty_frames,
                "empty_active_audio_percent": (
                    100.0
                    * audio_active_empty_frames
                    / max(audio_active_frames, 1)
                ),
                "longest_empty_active_audio_frames": (
                    longest_audio_active_empty_frames
                ),
                "longest_empty_active_audio_ms": (
                    1000.0
                    * longest_audio_active_empty_frames
                    * hop_samples
                    / sample_rate
                ),
                "interpretation": (
                    "Audio-active frames without any emitted MIDI note; "
                    "coverage diagnostic, not missing-note ground truth."
                ),
            },
            "audio_inactive_frames": audio_inactive_frames,
            "audio_active_percent": (
                100.0 * audio_active_frames
                / max(audio_active_frames + audio_inactive_frames, 1)
            ),
            "longest_audio_inactive_frames": longest_inactive_frames,
            "strong_predictions_vetoed_by_activity_gate": (
                strong_predictions_vetoed_by_activity_gate
            ),
            "maximum_simultaneous_notes": maximum_simultaneous_notes,
            "effective_decoder": asdict(decoder.config),
            "event_reason_counts": dict(sorted(event_reason_counts.items())),
            "note_on_reason_counts": dict(
                sorted(note_on_reason_counts.items())
            ),
            "recorded_wav": str(args.record_wav) if args.record_wav else None,
            "recorded_samples": recorded_samples,
            "debug_npz": str(args.debug_npz) if args.debug_npz else None,
            "audio_input": (
                audio_input_info.to_dict() if audio_input_info is not None else None
            ),
            "audio_outputs": audio_outputs,
            "negotiated_audio_io_ms": negotiated_audio_io_ms,
            "output_health_error": output_health_error,
            "runtime_error": runtime_error,
            "cleanup_errors": cleanup_errors,
        }
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    shutdown_label = (
        "Arret avec erreur" if runtime_error is not None or cleanup_errors
        else "Arret propre"
    )
    print(
        f"{shutdown_label}. skipped={skipped}, "
        f"dropped={overflow + backlog_discarded_hops}, "
        f"recoveries={recoveries}"
    )
    if cleanup_errors:
        print("Erreurs de nettoyage: " + "; ".join(cleanup_errors))
    return 1 if runtime_error is not None or cleanup_errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Guitare polyphonique live vers MIDI")
    parser.add_argument(
        "--artifacts", type=Path,
        default=Path("artifacts/guitar_midi_polyphonic_v2_2_0"),
    )
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument(
        "--audio-device",
        help=(
            "Index/nom d'entree; auto MME/WASAPI si omis. "
            "Un pin WDM-KS d'entree doit etre choisi explicitement."
        ),
    )
    parser.add_argument("--midi-device")
    parser.add_argument("--midi-channel", type=int, default=1)
    parser.add_argument("--program", type=int, default=0)
    parser.add_argument("--console-midi", action="store_true")
    parser.add_argument("--no-midi", action="store_true")
    parser.add_argument(
        "--soundfont", type=Path,
        help="Active une sortie audio locale FluidSynth faible latence avec ce SF2.",
    )
    parser.add_argument(
        "--audio-output-device",
        help="Index/nom de sortie; auto WDM-KS/WASAPI si omis.",
    )
    parser.add_argument("--synth-gain", type=float, default=0.65)
    parser.add_argument(
        "--audio-gain",
        type=float,
        default=1.0,
        help=(
            "Gain numerique manuel applique une fois avant gate/onset, "
            "WAV et modele; une valeur trop forte peut ecreter."
        ),
    )
    level_group = parser.add_mutually_exclusive_group()
    level_group.add_argument(
        "--auto-level",
        dest="auto_level",
        action="store_true",
        default=None,
        help=(
            "Active explicitement l'amplification causale des entrees "
            "faibles; peut augmenter les notes fantomes."
        ),
    )
    level_group.add_argument(
        "--no-auto-level",
        dest="auto_level",
        action="store_false",
        help="Desactive le nivellement causal (comportement par defaut).",
    )
    parser.add_argument("--calibration-s", type=float, default=1.0)
    parser.add_argument(
        "--synthetic-calibration",
        action="store_true",
        help=(
            "Calibre causalement onset/gate sur un silence synthetique avant "
            "l'ouverture du jeu; candidat utile quand le bruit du rig "
            "contamine la calibration micro."
        ),
    )
    parser.add_argument("--threads", type=int, choices=(1, 2, 3, 4))
    parser.add_argument("--debug-csv", type=Path)
    parser.add_argument("--debug-npz", type=Path)
    parser.add_argument("--record-wav", type=Path)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--duration-s", type=float)
    args = parser.parse_args()
    if args.list_devices:
        return list_devices()
    if not 1 <= args.midi_channel <= 16 or not 0 <= args.program <= 127:
        parser.error("Invalid MIDI channel/program.")
    try:
        validate_manual_audio_gain(args.audio_gain)
    except ValueError as error:
        parser.error(str(error))
    if not np.isfinite(args.calibration_s) or args.calibration_s <= 0:
        parser.error("Calibration must be positive.")
    if not 0.0 < args.synth_gain <= 5.0:
        parser.error("--synth-gain doit etre dans ]0, 5]")
    if args.soundfont is not None and not args.soundfont.is_file():
        parser.error(f"SoundFont introuvable: {args.soundfont}")
    if args.audio_output_device is not None and args.soundfont is None:
        parser.error("--audio-output-device requiert --soundfont")
    if (
        args.duration_s is not None
        and (
            not np.isfinite(args.duration_s)
            or args.duration_s <= 0
        )
    ):
        parser.error("--duration-s doit etre positif.")
    if args.debug_npz and not args.duration_s:
        parser.error("--debug-npz requires --duration-s to bound memory use.")
    if args.debug_npz and args.duration_s > 300:
        parser.error("--debug-npz is limited to captures of at most 300 seconds.")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
