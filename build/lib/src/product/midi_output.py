"""Dependency-free MIDI output with stuck-note protection on Windows."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from src.product.decoder import MidiEvent


class MidiSink:
    def send(self, event: MidiEvent) -> None:
        raise NotImplementedError

    def panic(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        self.panic()

    def diagnostics(self) -> list[dict[str, object]]:
        return []

    def health_error(self) -> str | None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


class ConsoleMidiSink(MidiSink):
    def __init__(self) -> None:
        self.active: set[int] = set()

    def send(self, event: MidiEvent) -> None:
        if event.kind == "note_on":
            self.active.add(event.pitch)
        else:
            self.active.discard(event.pitch)
        print(f"MIDI {event.kind} pitch={event.pitch} velocity={event.velocity}")

    def panic(self) -> None:
        for pitch in sorted(self.active):
            print(f"MIDI note_off pitch={pitch} velocity=0")
        self.active.clear()


class NullMidiSink(MidiSink):
    def send(self, event: MidiEvent) -> None:
        pass

    def panic(self) -> None:
        pass


class CompositeMidiSink(MidiSink):
    """Fan out events to multiple sinks (for example WinMM + console)."""

    def __init__(self, *sinks: MidiSink) -> None:
        if not sinks:
            raise ValueError("Au moins une sortie MIDI est requise.")
        self.sinks = tuple(sinks)
        self.closed = False

    def send(self, event: MidiEvent) -> None:
        if self.closed:
            raise RuntimeError("Sortie MIDI fermee.")
        for sink in self.sinks:
            sink.send(event)

    def panic(self) -> None:
        if self.closed:
            return
        first_error = None
        for sink in self.sinks:
            try:
                sink.panic()
            except Exception as exc:
                if first_error is None:
                    first_error = exc
        if first_error is not None:
            raise first_error

    def close(self) -> None:
        if self.closed:
            return
        first_error = None
        try:
            for sink in reversed(self.sinks):
                try:
                    sink.close()
                except Exception as exc:
                    if first_error is None:
                        first_error = exc
        finally:
            self.closed = True
        if first_error is not None:
            raise first_error

    def diagnostics(self) -> list[dict[str, object]]:
        reports: list[dict[str, object]] = []
        for sink in self.sinks:
            reports.extend(sink.diagnostics())
        return reports

    def health_error(self) -> str | None:
        for sink in self.sinks:
            error = sink.health_error()
            if error is not None:
                return error
        return None


class _MidiOutCaps(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD),
        ("wPid", wintypes.WORD),
        ("vDriverVersion", wintypes.UINT),
        ("szPname", wintypes.WCHAR * 32),
        ("wTechnology", wintypes.WORD),
        ("wVoices", wintypes.WORD),
        ("wNotes", wintypes.WORD),
        ("wChannelMask", wintypes.WORD),
        ("dwSupport", wintypes.DWORD),
    ]


def _winmm():
    if sys.platform != "win32":
        raise RuntimeError("La sortie WinMM est disponible uniquement sous Windows.")
    return ctypes.WinDLL("winmm")


def list_midi_outputs() -> list[tuple[int, str]]:
    if sys.platform != "win32":
        return []
    library = _winmm()
    library.midiOutGetNumDevs.restype = wintypes.UINT
    devices = []
    for index in range(int(library.midiOutGetNumDevs())):
        caps = _MidiOutCaps()
        result = library.midiOutGetDevCapsW(
            index, ctypes.byref(caps), ctypes.sizeof(caps)
        )
        if result == 0:
            devices.append((index, str(caps.szPname)))
    return devices


class WinMMMidiSink(MidiSink):
    def __init__(self, device: int | str = 0, channel: int = 0, program: int = 0):
        if not 0 <= int(channel) <= 15:
            raise ValueError("Canal MIDI hors plage 0-15.")
        devices = list_midi_outputs()
        if isinstance(device, str) and not device.strip().lstrip("-").isdigit():
            matches = [item for item in devices if device.lower() in item[1].lower()]
            if len(matches) != 1:
                raise ValueError(f"Sortie MIDI ambigue ou absente: {device!r}")
            device_id = matches[0][0]
        else:
            device_id = int(device)
        if device_id not in {item[0] for item in devices}:
            raise ValueError(f"Sortie MIDI invalide: {device_id}; disponibles={devices}")
        self.library = _winmm()
        self.handle = wintypes.HANDLE()
        result = self.library.midiOutOpen(
            ctypes.byref(self.handle), device_id, 0, 0, 0
        )
        if result != 0:
            raise OSError(f"midiOutOpen a echoue: code={result}")
        self.channel = int(channel)
        self.active: set[int] = set()
        self.closed = False
        self._short(0xC0 | self.channel, int(np_clip(program, 0, 127)), 0)

    def _short(self, status: int, data1: int, data2: int) -> None:
        message = int(status) | (int(data1) << 8) | (int(data2) << 16)
        result = self.library.midiOutShortMsg(self.handle, message)
        if result != 0:
            raise OSError(f"midiOutShortMsg a echoue: code={result}")

    def send(self, event: MidiEvent) -> None:
        if self.closed:
            raise RuntimeError("Sortie MIDI fermee.")
        pitch = int(np_clip(event.pitch, 0, 127))
        if event.kind == "note_on":
            velocity = int(np_clip(event.velocity, 1, 127))
            self._short(0x90 | self.channel, pitch, velocity)
            self.active.add(pitch)
        elif event.kind == "note_off":
            self._short(0x80 | self.channel, pitch, 0)
            self.active.discard(pitch)
        else:
            raise ValueError(f"Evenement MIDI inconnu: {event.kind}")

    def panic(self) -> None:
        if self.closed:
            return
        for pitch in tuple(self.active):
            self._short(0x80 | self.channel, pitch, 0)
        self.active.clear()
        self._short(0xB0 | self.channel, 64, 0)
        self._short(0xB0 | self.channel, 123, 0)
        self.library.midiOutReset(self.handle)

    def close(self) -> None:
        if self.closed:
            return
        self.panic()
        self.library.midiOutClose(self.handle)
        self.closed = True


def np_clip(value: int, minimum: int, maximum: int) -> int:
    return min(maximum, max(minimum, int(value)))
