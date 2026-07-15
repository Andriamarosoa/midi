from __future__ import annotations

import argparse
import queue
import signal
import sys
import time
from dataclasses import dataclass
from typing import Dict

import numpy as np

from .ring_buffer import MonoRingBuffer


@dataclass(frozen=True)
class StreamConfig:
    sample_rate: int = 44_100
    hop_samples: int = 256
    max_window_samples: int = 4_096
    windows: tuple[int, ...] = (512, 1_024, 2_048, 4_096)


class ProgressiveWindowStream:
    """Mono audio stream producing progressive causal windows.

    The audio callback only copies one hop into a queue. All model work is done
    outside the callback so inference cannot block the audio driver.
    """

    def __init__(self, config: StreamConfig) -> None:
        if config.max_window_samples < max(config.windows):
            raise ValueError("max_window_samples must cover every requested window")

        self.config = config
        self.ring = MonoRingBuffer(config.max_window_samples)
        self.hop_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=32)
        self.windows: Dict[int, np.ndarray] = {
            size: np.zeros(size, dtype=np.float32) for size in config.windows
        }
        self.dropped_hops = 0
        self.tick_index = 0

    def audio_callback(self, indata, frames, time_info, status) -> None:
        """sounddevice callback; keep this function extremely small."""
        if status:
            print("audio status:", status, file=sys.stderr)

        mono = np.asarray(indata[:, 0], dtype=np.float32).copy()
        try:
            self.hop_queue.put_nowait(mono)
        except queue.Full:
            self.dropped_hops += 1

    def process_next_hop(self, timeout: float = 1.0) -> Dict[int, np.ndarray]:
        hop = self.hop_queue.get(timeout=timeout)
        self.ring.write(hop)
        self.tick_index += 1

        for size, destination in self.windows.items():
            self.ring.copy_latest_into(destination)

        return self.windows


def prediction_placeholder(
    windows: Dict[int, np.ndarray],
    sample_rate: int,
    tick_index: int,
) -> None:
    """Replace this function with the neural-network inference call."""
    short = windows[512]
    medium = windows[2_048]

    short_rms = float(np.sqrt(np.mean(short * short) + 1e-12))
    medium_rms = float(np.sqrt(np.mean(medium * medium) + 1e-12))

    # Print roughly every 100 ms, not at every 5.8 ms tick.
    every = max(1, round(sample_rate / 256 / 10))
    if tick_index % every == 0:
        print(
            f"tick={tick_index:6d} "
            f"rms512={short_rms:.5f} "
            f"rms2048={medium_rms:.5f}"
        )


def run_microphone(device: int | str | None, config: StreamConfig) -> int:
    try:
        import sounddevice as sd
    except ImportError:
        raise SystemExit("sounddevice manquant : pip install sounddevice")

    stream_input = ProgressiveWindowStream(config)
    stop = False

    def request_stop(signum, frame) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, request_stop)

    print("Streaming mono")
    print(f"  sample rate : {config.sample_rate} Hz")
    print(
        f"  hop         : {config.hop_samples} samples "
        f"({config.hop_samples / config.sample_rate * 1000:.2f} ms)"
    )
    for size in config.windows:
        print(f"  window      : {size:4d} samples ({size / config.sample_rate * 1000:.2f} ms)")
    print("  Ctrl+C pour arrêter")

    with sd.InputStream(
        device=device,
        channels=1,
        samplerate=config.sample_rate,
        blocksize=config.hop_samples,
        dtype="float32",
        callback=stream_input.audio_callback,
    ):
        while not stop:
            try:
                windows = stream_input.process_next_hop(timeout=0.5)
            except queue.Empty:
                continue

            prediction_placeholder(
                windows=windows,
                sample_rate=config.sample_rate,
                tick_index=stream_input.tick_index,
            )

    print(f"Hops perdus : {stream_input.dropped_hops}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture mono + ring buffer + fenêtres progressives."
    )
    parser.add_argument("--device", default=None, help="Index ou nom du micro")
    parser.add_argument("--sample-rate", type=int, default=44_100)
    parser.add_argument("--hop-samples", type=int, default=256)
    parser.add_argument("--max-window", type=int, default=4_096)
    args = parser.parse_args()

    device = args.device
    if isinstance(device, str) and device.isdigit():
        device = int(device)

    config = StreamConfig(
        sample_rate=args.sample_rate,
        hop_samples=args.hop_samples,
        max_window_samples=args.max_window,
        windows=(512, 1_024, 2_048, 4_096),
    )
    return run_microphone(device, config)


if __name__ == "__main__":
    raise SystemExit(main())
