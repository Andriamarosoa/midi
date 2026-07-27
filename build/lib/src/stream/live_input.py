#!/usr/bin/env python3
"""Live mono input with progressive windows and adaptive onset detection.

Run from the project root:

    python -m src.stream.live_input

List input devices:

    python -m src.stream.live_input --list-devices

Select a device:

    python -m src.stream.live_input --device 3
"""

from __future__ import annotations

import argparse
import queue
import signal
import sys
from dataclasses import dataclass
from typing import Dict, Optional, Union

import numpy as np

from .onset_detector import AdaptiveOnsetDetector
from .ring_buffer import MonoRingBuffer


@dataclass(frozen=True)
class StreamConfig:
    sample_rate: int = 44_100
    hop_samples: int = 256
    max_window_samples: int = 4_096
    windows: tuple[int, ...] = (512, 1_024, 2_048, 4_096)
    queue_size: int = 32
    calibration_s: float = 1.0


class ProgressiveWindowStream:
    """Mono stream producing causal windows from one circular buffer."""

    def __init__(self, config: StreamConfig) -> None:
        if config.sample_rate <= 0:
            raise ValueError("sample_rate must be > 0")
        if config.hop_samples <= 0:
            raise ValueError("hop_samples must be > 0")
        if not config.windows:
            raise ValueError("windows must not be empty")
        if max(config.windows) > config.max_window_samples:
            raise ValueError(
                "max_window_samples must be >= the largest requested window"
            )

        self.config = config
        self.ring = MonoRingBuffer(config.max_window_samples)

        self.hop_queue: queue.Queue[np.ndarray] = queue.Queue(
            maxsize=config.queue_size
        )

        self.windows: Dict[int, np.ndarray] = {
            size: np.zeros(size, dtype=np.float32)
            for size in config.windows
        }

        self.tick_index = 0
        self.dropped_hops = 0

    def audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info,
        status,
    ) -> None:
        """Audio callback.

        Keep this callback very small. No inference, FFT or printing here.
        """
        if status:
            print(f"audio status: {status}", file=sys.stderr)

        if indata.ndim != 2 or indata.shape[1] < 1:
            return

        mono = np.asarray(indata[:, 0], dtype=np.float32).copy()

        try:
            self.hop_queue.put_nowait(mono)
        except queue.Full:
            self.dropped_hops += 1

    def process_next_hop(
        self,
        timeout: float = 1.0,
        gain: float = 1.0,
    ) -> tuple[np.ndarray, Dict[int, np.ndarray]]:
        """Read one hop, update the ring buffer and refresh all windows."""
        hop = self.hop_queue.get(timeout=timeout)
        if gain != 1.0:
            hop *= float(gain)
            np.clip(hop, -1.0, 1.0, out=hop)

        self.ring.write(hop)
        self.tick_index += 1

        for size, destination in self.windows.items():
            self.ring.copy_latest_into(destination)

        return hop, self.windows


def list_input_devices() -> int:
    try:
        import sounddevice as sd
    except ImportError:
        raise SystemExit(
            "sounddevice manquant : python -m pip install sounddevice"
        )

    devices = sd.query_devices()

    print("")
    print("Périphériques d'entrée disponibles")
    print("-" * 80)

    found = False

    for index, device in enumerate(devices):
        input_channels = int(device["max_input_channels"])

        if input_channels <= 0:
            continue

        found = True
        print(
            f"{index:>3} | "
            f"channels={input_channels:<2} | "
            f"default_sr={float(device['default_samplerate']):>8.0f} | "
            f"{device['name']}"
        )

    if not found:
        print("Aucun périphérique d'entrée trouvé.")

    return 0


def prediction_placeholder(
    windows: Dict[int, np.ndarray],
    sample_rate: int,
    hop_samples: int,
    tick_index: int,
) -> None:
    """Temporary diagnostic until the note-prediction model is connected."""
    short = windows[512]
    medium = windows[2_048]

    short_rms = float(
        np.sqrt(np.mean(short * short, dtype=np.float64) + 1e-12)
    )
    medium_rms = float(
        np.sqrt(np.mean(medium * medium, dtype=np.float64) + 1e-12)
    )

    ticks_per_print = max(
        1,
        round(sample_rate / hop_samples / 10),
    )

    if tick_index % ticks_per_print == 0:
        print(
            f"tick={tick_index:6d} "
            f"rms512={short_rms:.5f} "
            f"rms2048={medium_rms:.5f}"
        )


def print_stream_configuration(config: StreamConfig) -> None:
    print("Streaming mono")
    print(f"  sample rate : {config.sample_rate} Hz")
    print(
        f"  hop         : {config.hop_samples} samples "
        f"({config.hop_samples / config.sample_rate * 1000.0:.2f} ms)"
    )

    for size in config.windows:
        print(
            f"  window      : {size:4d} samples "
            f"({size / config.sample_rate * 1000.0:.2f} ms)"
        )

    print(
        f"  calibration : {config.calibration_s:.2f} s "
        f"(reste silencieux au début)"
    )
    print("  Ctrl+C pour arrêter")


def run_microphone(
    device: Optional[Union[int, str]],
    config: StreamConfig,
    show_rms: bool,
    input_gain: float,
) -> int:
    try:
        import sounddevice as sd
    except ImportError:
        raise SystemExit(
            "sounddevice manquant : python -m pip install sounddevice"
        )

    stream_input = ProgressiveWindowStream(config)

    detector = AdaptiveOnsetDetector(
        sample_rate=config.sample_rate,
        hop_samples=config.hop_samples,
        fft_size=512,
        calibration_s=config.calibration_s,
    )

    stop_requested = False
    calibration_announced = False

    def request_stop(signum, frame) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, request_stop)

    print_stream_configuration(config)

    with sd.InputStream(
        device=device,
        channels=1,
        samplerate=config.sample_rate,
        blocksize=config.hop_samples,
        dtype="float32",
        callback=stream_input.audio_callback,
    ):
        while not stop_requested:
            try:
                hop, windows = stream_input.process_next_hop(
                    timeout=0.5,
                    gain=input_gain,
                )
            except queue.Empty:
                continue

            onset = detector.process(hop)

            if onset.calibrated and not calibration_announced:
                calibration_announced = True
                print("")
                print("Calibration terminée. Tu peux jouer.")
                print("")

            if onset.is_onset:
                print(
                    f"ATTACK "
                    f"tick={onset.tick_index} "
                    f"time={onset.time_s:.3f}s "
                    f"rms={onset.rms:.6f} "
                    f"rms_dbfs={onset.rms_dbfs:.2f} "
                    f"growth={onset.rms_growth:.6f} "
                    f"flux={onset.spectral_flux:.4f} "
                    f"score={onset.score:.3f} "
                    f"confidence={onset.confidence:.3f}"
                )

                # Future model entry point:
                #
                # prediction = model.predict({
                #     "window_512": windows[512],
                #     "window_1024": windows[1024],
                #     "window_2048": windows[2048],
                #     "window_4096": windows[4096],
                # })
                #
                # print(prediction)

            if show_rms:
                prediction_placeholder(
                    windows=windows,
                    sample_rate=config.sample_rate,
                    hop_samples=config.hop_samples,
                    tick_index=stream_input.tick_index,
                )

    print("")
    print(f"Hops perdus : {stream_input.dropped_hops}")

    return 0


def parse_device(value: Optional[str]) -> Optional[Union[int, str]]:
    if value is None:
        return None

    stripped = value.strip()

    if stripped.lstrip("-").isdigit():
        return int(stripped)

    return stripped


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Capture mono avec ring buffer, fenêtres progressives "
            "et détection adaptative d'attaque."
        )
    )

    parser.add_argument(
        "--device",
        default=None,
        help="Index ou nom du périphérique d'entrée.",
    )

    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="Affiche les périphériques d'entrée puis quitte.",
    )

    parser.add_argument(
        "--sample-rate",
        type=int,
        default=44_100,
    )

    parser.add_argument(
        "--hop-samples",
        type=int,
        default=256,
    )

    parser.add_argument(
        "--max-window",
        type=int,
        default=4_096,
    )

    parser.add_argument(
        "--calibration-s",
        type=float,
        default=1.0,
        help="Durée initiale utilisée pour calibrer le bruit de fond.",
    )

    parser.add_argument(
        "--input-gain",
        type=float,
        default=1.0,
        help="Gain logiciel temporaire appliqué avant la détection.",
    )

    parser.add_argument(
        "--show-rms",
        action="store_true",
        help="Affiche périodiquement le RMS des fenêtres.",
    )

    args = parser.parse_args()

    if args.list_devices:
        return list_input_devices()

    if args.sample_rate <= 0:
        parser.error("--sample-rate doit être positif")

    if args.hop_samples <= 0:
        parser.error("--hop-samples doit être positif")

    if args.max_window < 4_096:
        parser.error("--max-window doit être >= 4096")

    if args.calibration_s <= 0:
        parser.error("--calibration-s doit être positif")

    if args.input_gain <= 0:
        parser.error("--input-gain doit être positif")

    config = StreamConfig(
        sample_rate=args.sample_rate,
        hop_samples=args.hop_samples,
        max_window_samples=args.max_window,
        windows=(512, 1_024, 2_048, 4_096),
        calibration_s=args.calibration_s,
    )

    device = parse_device(args.device)

    return run_microphone(
        device=device,
        config=config,
        show_rms=args.show_rms,
        input_gain=args.input_gain,
    )


if __name__ == "__main__":
    raise SystemExit(main())
