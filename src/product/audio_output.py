"""Optional in-process FluidSynth audio sink rendered through WASAPI."""

from __future__ import annotations

import queue
import time
from collections import deque
from pathlib import Path

import numpy as np

from src.product.audio_io import AudioStreamInfo, open_output_stream
from src.product.midi_output import MidiSink


class FluidSynthWasapiSink(MidiSink):
    """Render MIDI events locally without Microsoft GS Wavetable Synth.

    MIDI commands are queued and applied by the PortAudio callback, so the
    FluidSynth instance is touched by only one thread. This adds at most one
    render block of scheduling delay (about 2.9 ms at 128/44.1 kHz).
    """

    def __init__(
        self,
        soundfont: str | Path,
        sample_rate: int,
        block_size: int,
        *,
        output_device=None,
        midi_channel: int = 0,
        program: int = 0,
        gain: float = 0.65,
        _sd=None,
        _fluidsynth=None,
    ) -> None:
        self.soundfont = Path(soundfont).expanduser().resolve()
        if not self.soundfont.is_file():
            raise FileNotFoundError(self.soundfont)
        if not 0 <= int(midi_channel) <= 15:
            raise ValueError("Canal FluidSynth hors plage 0-15.")
        if not 0 <= int(program) <= 127:
            raise ValueError("Programme FluidSynth hors plage 0-127.")
        if not 0.0 < float(gain) <= 5.0:
            raise ValueError("Le gain FluidSynth doit etre dans ]0, 5].")

        if _fluidsynth is None:
            try:
                import fluidsynth as _fluidsynth
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "pyFluidSynth est requis pour --soundfont. "
                    "Installe-le avec: python -m pip install pyfluidsynth==1.3.6"
                ) from exc
            except (ImportError, OSError) as exc:
                raise RuntimeError(
                    "La bibliotheque native FluidSynth est introuvable. "
                    "Installe FluidSynth 2/3 et rends libfluidsynth-3.dll "
                    "accessible dans PATH."
                ) from exc

        self.sample_rate = int(sample_rate)
        self.block_size = int(block_size)
        self.midi_channel = int(midi_channel)
        self.program = int(program)
        self.gain = float(gain)
        self.active: set[int] = set()
        self.closed = False
        self.output_status_events = 0
        self.consecutive_output_status_events = 0
        self._recent_output_status = deque(maxlen=16)
        self.render_errors = 0
        self.consecutive_render_errors = 0
        self.last_render_error: str | None = None
        self._commands = queue.SimpleQueue()
        self._command_delay_ms: deque[float] = deque(maxlen=4096)
        self.stream = None
        self.audio_info: AudioStreamInfo | None = None
        self.synth = None

        try:
            self.synth = _fluidsynth.Synth(
                gain=self.gain,
                samplerate=self.sample_rate,
            )
            sfid = int(self.synth.sfload(str(self.soundfont)))
            if sfid < 0:
                raise RuntimeError(f"FluidSynth ne peut pas charger {self.soundfont}")
            self.synth.program_select(self.midi_channel, sfid, 0, self.program)

            def callback(outdata, frames, _time_info, status) -> None:
                self._recent_output_status.append(bool(status))
                if status:
                    self.output_status_events += 1
                    self.consecutive_output_status_events += 1
                else:
                    self.consecutive_output_status_events = 0
                try:
                    self._drain_commands()
                    samples = np.asarray(self.synth.get_samples(frames))
                    if np.issubdtype(samples.dtype, np.integer):
                        samples = samples.astype(np.float32) / 32768.0
                    else:
                        samples = samples.astype(np.float32, copy=False)
                    expected = int(frames) * 2
                    if samples.size != expected:
                        raise ValueError(
                            f"FluidSynth a rendu {samples.size} valeurs, {expected} attendues."
                        )
                    outdata[:] = samples.reshape(int(frames), 2)
                    self.consecutive_render_errors = 0
                except Exception as exc:
                    self.render_errors += 1
                    self.consecutive_render_errors += 1
                    self.last_render_error = repr(exc)
                    outdata.fill(0.0)

            self.stream, self.audio_info = open_output_stream(
                preferred_device=output_device,
                channels=2,
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                latency="low",
                dtype="float32",
                callback=callback,
                _sd=_sd,
            )
        except Exception:
            if self.stream is not None:
                try:
                    self.stream.close()
                except Exception:
                    pass
            if self.synth is not None:
                try:
                    self.synth.delete()
                except Exception:
                    pass
            raise

        self.label = (
            f"FluidSynth {self.soundfont.name} -> "
            f"{self.audio_info.host_api} [{self.audio_info.device_index}]"
        )

    def _drain_commands(self) -> None:
        while True:
            try:
                kind, first, second, queued_at = self._commands.get_nowait()
            except queue.Empty:
                return
            self._command_delay_ms.append(
                (time.perf_counter() - queued_at) * 1000.0
            )
            if kind == "on":
                self.synth.noteon(self.midi_channel, first, second)
            elif kind == "off":
                self.synth.noteoff(self.midi_channel, first)
            elif kind == "cc":
                self.synth.cc(self.midi_channel, first, second)

    def send(self, event) -> None:
        if self.closed:
            raise RuntimeError("Sortie FluidSynth fermee.")
        pitch = int(np.clip(event.pitch, 0, 127))
        if event.kind == "note_on":
            velocity = int(np.clip(event.velocity, 1, 127))
            self.active.add(pitch)
            self._commands.put(("on", pitch, velocity, time.perf_counter()))
        elif event.kind == "note_off":
            self.active.discard(pitch)
            self._commands.put(("off", pitch, 0, time.perf_counter()))
        else:
            raise ValueError(f"Evenement MIDI inconnu: {event.kind}")

    def panic(self) -> None:
        if self.closed:
            return
        for pitch in tuple(self.active):
            self._commands.put(("off", pitch, 0, time.perf_counter()))
        self.active.clear()
        self._commands.put(("cc", 64, 0, time.perf_counter()))
        self._commands.put(("cc", 123, 0, time.perf_counter()))

    def close(self) -> None:
        if self.closed:
            return
        self.active.clear()
        self.closed = True
        try:
            if self.stream is not None:
                try:
                    self.stream.stop()
                finally:
                    self.stream.close()
        finally:
            if self.synth is not None:
                self.synth.delete()

    def diagnostics(self) -> list[dict[str, object]]:
        report: dict[str, object] = {
            "backend": "fluidsynth",
            "soundfont": str(self.soundfont),
            "output_status_events": self.output_status_events,
            "consecutive_output_status_events": (
                self.consecutive_output_status_events
            ),
            "recent_output_status_events": int(sum(self._recent_output_status)),
            "recent_output_status_window": len(self._recent_output_status),
            "render_errors": self.render_errors,
            "consecutive_render_errors": self.consecutive_render_errors,
            "last_render_error": self.last_render_error,
        }
        delays = np.asarray(self._command_delay_ms, dtype=np.float64)
        report["command_delay_ms"] = {
            "count": int(delays.size),
            "p50": float(np.percentile(delays, 50.0)) if delays.size else None,
            "p95": float(np.percentile(delays, 95.0)) if delays.size else None,
            "max": float(np.max(delays)) if delays.size else None,
        }
        if self.audio_info is not None:
            report.update(self.audio_info.to_dict())
        return [report]

    def health_error(self) -> str | None:
        if self.stream is not None and not self.closed:
            try:
                stream_active = bool(getattr(self.stream, "active", True))
            except Exception as exc:
                return f"Etat du flux audio de sortie illisible: {exc!r}"
            if not stream_active:
                return "Le flux audio de sortie FluidSynth s'est arrete."
        if self.consecutive_output_status_events >= 3:
            return (
                "Le flux audio de sortie signale "
                f"{self.consecutive_output_status_events} incidents consecutifs."
            )
        if (
            len(self._recent_output_status) >= 8
            and sum(self._recent_output_status) >= 3
        ):
            return (
                "Le flux audio de sortie est instable: "
                f"{sum(self._recent_output_status)} incidents sur les "
                f"{len(self._recent_output_status)} derniers blocs."
            )
        if self.consecutive_render_errors < 3:
            return None
        return (
            "FluidSynth ne rend plus de son apres "
            f"{self.consecutive_render_errors} erreurs consecutives: "
            f"{self.last_render_error}"
        )
