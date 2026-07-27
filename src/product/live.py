"""Low-latency microphone-to-MIDI PC application."""

from __future__ import annotations

import argparse
import csv
import json
import queue
import signal
import time
from collections import deque
from pathlib import Path

import numpy as np

from src.product.audio_io import audio_devices, managed_input_stream, parse_device
from src.product.audio_output import FluidSynthWasapiSink
from src.product.backpressure import LiveBackpressure
from src.product.engine import GuitarMidiEngine, InferenceRequest
from src.product.midi_output import (
    CompositeMidiSink,
    ConsoleMidiSink,
    NullMidiSink,
    WinMMMidiSink,
    list_midi_outputs,
)
from src.product.tflite_runtime import (
    ProductBundle,
    TFLitePitchModel,
    TFLiteTransitionGate,
)


def list_devices() -> int:
    print("Entrees audio:")
    for device in audio_devices("input"):
        marker = " [defaut]" if device["default"] else ""
        print(
            f"  {device['index']}: {device['name']} | {device['host_api']} | "
            f"{device['native_sample_rate']} Hz | "
            f"low={device['low_latency_ms']:.2f}ms{marker}"
        )
    print("Sorties audio:")
    for device in audio_devices("output"):
        marker = " [defaut]" if device["default"] else ""
        print(
            f"  {device['index']}: {device['name']} | {device['host_api']} | "
            f"{device['native_sample_rate']} Hz | "
            f"low={device['low_latency_ms']:.2f}ms{marker}"
        )
    print("Sorties MIDI:")
    midi = list_midi_outputs()
    if not midi:
        print("  aucune sortie WinMM")
    for index, name in midi:
        print(f"  {index}: {name}")
    return 0


def make_sink(args, sample_rate: int, block_size: int):
    sinks = []
    try:
        soundfont = getattr(args, "soundfont", None)
        if soundfont is not None:
            render_block_size = min(int(block_size), 128)
            sinks.append(FluidSynthWasapiSink(
                soundfont=soundfont,
                sample_rate=sample_rate,
                block_size=render_block_size,
                output_device=parse_device(
                    getattr(args, "audio_output_device", None)
                ),
                midi_channel=args.midi_channel - 1,
                program=args.program,
                gain=float(getattr(args, "synth_gain", 0.65)),
            ))

        outputs = list_midi_outputs()
        if not args.no_midi and not outputs:
            print("Aucune sortie MIDI WinMM; affichage console active.")
            if not sinks:
                sinks.append(ConsoleMidiSink())
        elif not args.no_midi:
            selected = (
                outputs[0][0]
                if args.midi_device is None else parse_device(args.midi_device)
            )
            sinks.append(
                WinMMMidiSink(selected, args.midi_channel - 1, args.program)
            )
        if args.console_midi:
            sinks.append(ConsoleMidiSink())
    except Exception:
        for sink in reversed(sinks):
            try:
                sink.close()
            except Exception:
                pass
        raise
    if not sinks:
        return NullMidiSink()
    if len(sinks) == 1:
        return sinks[0]
    return CompositeMidiSink(*sinks)


def debug_row(frame, queue_delay_ms: float, queue_depth: int) -> dict[str, object]:
    prediction = frame.prediction
    decoder = frame.decoder
    return {
        "frame": frame.frame_index,
        "time_s": frame.onset.time_s,
        "calibrated": int(frame.calibrated),
        "visible_window": frame.visible_window,
        "detected_onset": int(frame.onset.is_onset),
        "onset_confidence": frame.onset.confidence,
        "rms_dbfs": frame.onset.rms_dbfs,
        "active_probability": "" if prediction is None else prediction.active_probability,
        "raw_pitch": "" if decoder is None else decoder.raw_pitch,
        "stable_active": "" if decoder is None else int(decoder.active),
        "stable_pitch": "" if decoder is None else decoder.pitch,
        "transition_score": "" if decoder is None or decoder.transition_score is None else decoder.transition_score,
        "transition_veto": "" if decoder is None else int(decoder.transition_veto),
        "retrigger": "" if decoder is None else int(decoder.retrigger),
        "inference_ms": "" if prediction is None else prediction.inference_ms,
        "inference_skipped": int(frame.calibrated and prediction is None),
        "loop_ms": frame.loop_ms,
        "queue_delay_ms": queue_delay_ms,
        "queue_depth": queue_depth,
    }


def run(args) -> int:
    bundle = ProductBundle(args.artifacts)
    max_backlog_hops = (
        int(bundle.metadata["max_live_backlog_hops"])
        if args.max_backlog_hops is None
        else int(args.max_backlog_hops)
    )
    backpressure = LiveBackpressure(max_backlog_hops=max_backlog_hops)
    pitch_model = TFLitePitchModel(bundle, threads=args.threads)
    gate = TFLiteTransitionGate(bundle)
    warmup = np.zeros(4096, dtype=np.float32)
    for _ in range(20):
        pitch_model.infer(warmup, 4096)
    gate(np.zeros((1, 20), dtype=np.float32))
    engine = GuitarMidiEngine(
        bundle, pitch_model, gate,
        calibration_s=args.calibration_s,
        audio_gain=args.audio_gain,
    )
    hops: queue.Queue[tuple[np.ndarray, float]] = queue.Queue(maxsize=64)
    overflow = 0
    audio_status_events = 0
    invalid_audio_blocks = 0
    stop = False
    stop_reason = "unknown"
    output_health_error = None
    last_valid_audio_callback = time.monotonic()
    backlog_discarded_hops = 0
    recoveries = 0
    recovery_events: list[dict[str, float | int | str]] = []

    def callback(indata, frames, time_info, status) -> None:
        nonlocal overflow, audio_status_events, invalid_audio_blocks
        nonlocal last_valid_audio_callback
        if status:
            audio_status_events += 1
            overflow += 1
            return
        if frames != engine.hop_samples or indata.ndim != 2:
            invalid_audio_blocks += 1
            overflow += 1
            return
        last_valid_audio_callback = time.monotonic()
        value = np.asarray(indata[:, 0], dtype=np.float32).copy()
        try:
            hops.put_nowait((value, time.perf_counter()))
        except queue.Full:
            overflow += 1
            try:
                hops.get_nowait()
            except queue.Empty:
                pass
            try:
                hops.put_nowait((value, time.perf_counter()))
            except queue.Full:
                pass

    def request_stop(signum, frame) -> None:
        nonlocal stop, stop_reason
        stop = True
        stop_reason = "signal"

    def discard_queued_hops() -> int:
        removed = 0
        while True:
            try:
                hops.get_nowait()
                removed += 1
            except queue.Empty:
                return removed

    signal.signal(signal.SIGINT, request_stop)
    debug_handle = None
    writer = None
    if args.debug_csv:
        args.debug_csv.parent.mkdir(parents=True, exist_ok=True)
        debug_handle = args.debug_csv.open("w", encoding="utf-8", newline="")
    try:
        sink = make_sink(args, engine.sample_rate, engine.hop_samples)
    except Exception:
        if debug_handle is not None:
            debug_handle.close()
        raise
    audio_input_info = None
    budget_ms = engine.hop_samples / engine.sample_rate * 1000.0
    latencies: deque[float] = deque(maxlen=1000)
    measured_pipeline_ms: list[float] = []
    measured_loop_ms: list[float] = []
    measured_inference_ms: list[float] = []
    measured_queue_depth: list[int] = []
    overruns = 0
    skipped_inferences = 0
    processed_overflow = 0
    announced = False
    runtime_error = None
    cleanup_errors: list[str] = []
    last_status = time.monotonic()
    run_started = time.monotonic()
    print(
        f"Guitar MIDI {bundle.metadata['product_version']} | "
        f"{engine.sample_rate} Hz | hop {engine.hop_samples} ({budget_ms:.2f} ms)"
    )
    print("Reste silencieux pendant la calibration initiale. Ctrl+C pour arreter.")
    try:
        with managed_input_stream(
            preferred_device=parse_device(args.audio_device),
            channels=1,
            samplerate=engine.sample_rate,
            blocksize=engine.hop_samples,
            dtype="float32",
            latency="low",
            callback=callback,
        ) as (_input_stream, audio_input_info):
            while not stop:
                if args.duration_s is not None and time.monotonic() - run_started >= args.duration_s:
                    stop_reason = "duration"
                    break
                output_health_error = sink.health_error()
                if output_health_error is not None:
                    try:
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
                            sink.panic()
                        except Exception:
                            pass
                        stop_reason = "audio_input_stalled"
                        print(
                            "Le flux microphone ne fournit plus de blocs: "
                            "arret propre apres panic MIDI."
                        )
                        stop = True
                        break
                    if overflow != processed_overflow:
                        discarded = discard_queued_hops()
                        backlog_discarded_hops += discarded
                        processed_overflow = overflow
                        sink.panic()
                        engine.reset_continuity()
                        backpressure = LiveBackpressure(
                            max_backlog_hops=max_backlog_hops
                        )
                        recoveries += 1
                        recovery_events.append({
                            "time_s": time.monotonic() - run_started,
                            "reason": "audio_callback_stall",
                            "discarded_hops": discarded,
                            "total_dropped_hops": (
                                overflow + backlog_discarded_hops
                            ),
                        })
                        print(
                            "Incident audio recupere: contexte causal "
                            "reinitialise apres panic MIDI."
                        )
                    continue
                if overflow != processed_overflow:
                    discarded = 1 + discard_queued_hops()
                    backlog_discarded_hops += discarded
                    sink.panic()
                    processed_overflow = overflow
                    engine.reset_continuity()
                    backpressure = LiveBackpressure(
                        max_backlog_hops=max_backlog_hops
                    )
                    recoveries += 1
                    recovery_events.append({
                        "time_s": time.monotonic() - run_started,
                        "reason": "audio_callback",
                        "discarded_hops": discarded,
                        "total_dropped_hops": (
                            overflow + backlog_discarded_hops
                        ),
                    })
                    print(
                        "Surcharge audio recuperee: contexte causal "
                        f"reinitialise (dropped={overflow + backlog_discarded_hops})."
                    )
                    continue
                queue_delay_ms = (time.perf_counter() - captured_at) * 1000.0
                frontend = engine.process_frontend(hop)
                if isinstance(frontend, InferenceRequest):
                    try:
                        skip_inference = backpressure.decide(hops.qsize())
                    except RuntimeError as exc:
                        discarded = 1 + discard_queued_hops()
                        backlog_discarded_hops += discarded
                        sink.panic()
                        engine.reset_continuity()
                        backpressure = LiveBackpressure(
                            max_backlog_hops=max_backlog_hops
                        )
                        recoveries += 1
                        recovery_events.append({
                            "time_s": time.monotonic() - run_started,
                            "reason": "dangerous_backlog",
                            "discarded_hops": discarded,
                            "total_dropped_hops": (
                                overflow + backlog_discarded_hops
                            ),
                        })
                        print(
                            f"{exc} Contexte causal reinitialise; reprise "
                            "sur les nouveaux blocs."
                        )
                        continue
                    if skip_inference:
                        frame = engine.skip_inference(frontend)
                        skipped_inferences += 1
                    else:
                        frame = engine.process_inference(frontend)
                else:
                    frame = frontend
                pipeline_delay_ms = (time.perf_counter() - captured_at) * 1000.0
                latencies.append(pipeline_delay_ms)
                if frame.calibrated:
                    measured_pipeline_ms.append(pipeline_delay_ms)
                    measured_loop_ms.append(frame.loop_ms)
                    measured_queue_depth.append(hops.qsize())
                    if frame.prediction is not None:
                        measured_inference_ms.append(frame.prediction.inference_ms)
                overruns += int(pipeline_delay_ms > budget_ms)
                if frame.calibrated and not announced:
                    announced = True
                    print("Calibration terminee. Le moteur MIDI est actif.")
                if frame.decoder is not None:
                    for event in frame.decoder.events:
                        sink.send(event)
                if debug_handle is not None:
                    row = debug_row(frame, pipeline_delay_ms, hops.qsize())
                    if writer is None:
                        writer = csv.DictWriter(debug_handle, fieldnames=list(row))
                        writer.writeheader()
                    writer.writerow(row)
                    if frame.frame_index % 100 == 0:
                        debug_handle.flush()
                now = time.monotonic()
                if now - last_status >= 1.0 and latencies:
                    values = np.asarray(latencies, dtype=np.float64)
                    pitch = frame.decoder.pitch if frame.decoder is not None else -1
                    print(
                        f"pitch={pitch:3d} pipeline={pipeline_delay_ms:5.2f}ms "
                        f"p95={np.percentile(values, 95):5.2f}ms "
                        f"skipped={skipped_inferences} "
                        f"recent={backpressure.recent_skip_percent:4.1f}% "
                        f"dropped={overflow + backlog_discarded_hops}"
                    )
                    last_status = now
    except Exception as exc:
        runtime_error = repr(exc)
        if stop_reason == "unknown":
            stop_reason = "runtime_error"
        print(f"Erreur live: {runtime_error}")
    finally:
        try:
            sink.close()
        except Exception as exc:
            cleanup_errors.append(f"sortie MIDI/audio: {exc!r}")
        if debug_handle is not None:
            try:
                debug_handle.close()
            except Exception as exc:
                cleanup_errors.append(f"debug CSV: {exc!r}")
    if stop_reason == "unknown":
        stop_reason = "cleanup_error" if cleanup_errors else "completed"
    shutdown_label = (
        "Arret avec erreur" if runtime_error is not None or cleanup_errors
        else "Arret propre"
    )
    print(
        f"{shutdown_label}. overruns={overruns}, "
        f"inferences_sautees={skipped_inferences}, "
        f"hops_perdus={overflow + backlog_discarded_hops}, "
        f"recoveries={recoveries}"
    )
    if args.report_json:
        def statistics(values) -> dict[str, float | int | None]:
            data = np.asarray(values, dtype=np.float64)
            if data.size == 0:
                return {"count": 0, "mean": None, "p50": None, "p95": None,
                        "p99": None, "max": None}
            return {
                "count": int(data.size),
                "mean": float(np.mean(data)),
                "p50": float(np.percentile(data, 50.0)),
                "p95": float(np.percentile(data, 95.0)),
                "p99": float(np.percentile(data, 99.0)),
                "max": float(np.max(data)),
            }

        calibrated_frames = len(measured_pipeline_ms)
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
            "hop_budget_ms": budget_ms,
            "calibrated_frames": calibrated_frames,
            "inferences_skipped": skipped_inferences,
            "inference_skip_percent": (
                100.0 * skipped_inferences / calibrated_frames
                if calibrated_frames else 0.0
            ),
            "audio_hops_dropped": overflow + backlog_discarded_hops,
            "audio_status_events": audio_status_events,
            "invalid_audio_blocks": invalid_audio_blocks,
            "backlog_discarded_hops": backlog_discarded_hops,
            "overload_recoveries": recoveries,
            "overload_recovery_events": recovery_events,
            "soft_backlog_hops": max_backlog_hops,
            "pipeline_ms": statistics(measured_pipeline_ms),
            "loop_ms": statistics(measured_loop_ms),
            "inference_ms": statistics(measured_inference_ms),
            "queue_depth_hops": statistics(measured_queue_depth),
            "audio_input": (
                audio_input_info.to_dict() if audio_input_info is not None else None
            ),
            "audio_outputs": audio_outputs,
            "negotiated_audio_io_ms": negotiated_audio_io_ms,
            "stop_reason": stop_reason,
            "output_health_error": output_health_error,
            "runtime_error": runtime_error,
            "cleanup_errors": cleanup_errors,
        }
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if cleanup_errors:
        print("Erreurs de nettoyage: " + "; ".join(cleanup_errors))
    return 1 if runtime_error is not None or cleanup_errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Guitare mono live vers MIDI causal")
    parser.add_argument(
        "--artifacts", type=Path,
        default=Path("artifacts/guitar_midi_v1_0_0"),
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
    parser.add_argument("--audio-gain", type=float, default=1.0)
    parser.add_argument("--calibration-s", type=float, default=1.0)
    parser.add_argument("--threads", type=int, choices=(1, 2, 4))
    parser.add_argument(
        "--max-backlog-hops", type=int,
        help=(
            "Backlog tolere avant un saut borne a 2/32; utilise metadata.json "
            "par defaut."
        ),
    )
    parser.add_argument("--debug-csv", type=Path)
    parser.add_argument(
        "--report-json", type=Path,
        help="Rapport de latence agrege sans le cout d'un CSV par hop.",
    )
    parser.add_argument(
        "--duration-s", type=float,
        help="Arret automatique, utile pour les tests materiels.",
    )
    args = parser.parse_args()
    if args.list_devices:
        return list_devices()
    if not 1 <= args.midi_channel <= 16:
        parser.error("--midi-channel doit etre dans 1-16")
    if not 0 <= args.program <= 127:
        parser.error("--program doit etre dans 0-127")
    if args.audio_gain <= 0.0 or args.calibration_s <= 0.0:
        parser.error("gain et calibration doivent etre positifs")
    if not 0.0 < args.synth_gain <= 5.0:
        parser.error("--synth-gain doit etre dans ]0, 5]")
    if args.soundfont is not None and not args.soundfont.is_file():
        parser.error(f"SoundFont introuvable: {args.soundfont}")
    if args.audio_output_device is not None and args.soundfont is None:
        parser.error("--audio-output-device requiert --soundfont")
    if args.duration_s is not None and args.duration_s <= 0.0:
        parser.error("--duration-s doit etre positif")
    if args.max_backlog_hops is not None and args.max_backlog_hops < 0:
        parser.error("--max-backlog-hops doit etre positif ou nul")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
