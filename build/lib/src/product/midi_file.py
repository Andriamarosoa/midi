"""Small dependency-free Standard MIDI File writer."""

from __future__ import annotations

import struct
from pathlib import Path


def _variable_length(value: int) -> bytes:
    if value < 0:
        raise ValueError("Delta MIDI negatif.")
    output = [value & 0x7F]
    value >>= 7
    while value:
        output.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(output))


def write_midi(
    path: str | Path,
    events: list[dict[str, int | float | str]],
    channel: int = 0,
    program: int = 0,
    ticks_per_quarter: int = 480,
    tempo_us_per_quarter: int = 500_000,
) -> None:
    if not 0 <= channel <= 15 or not 0 <= program <= 127:
        raise ValueError("Canal ou programme MIDI invalide.")
    ticks_per_second = ticks_per_quarter * 1_000_000 / tempo_us_per_quarter
    track = bytearray(b"\x00\xff\x51\x03")
    track.extend(int(tempo_us_per_quarter).to_bytes(3, "big"))
    track.extend((0, 0xC0 | channel, program))
    previous_tick = 0
    ordered = sorted(
        events,
        key=lambda value: (
            float(value["time_s"]),
            0 if value["kind"] == "note_off" else 1,
        ),
    )
    for event in ordered:
        tick = max(previous_tick, int(round(float(event["time_s"]) * ticks_per_second)))
        pitch = int(event["pitch"])
        velocity = int(event["velocity"])
        if not 0 <= pitch <= 127 or not 0 <= velocity <= 127:
            raise ValueError("Evenement MIDI hors plage.")
        status = (0x80 if event["kind"] == "note_off" else 0x90) | channel
        track.extend(_variable_length(tick - previous_tick))
        track.extend((status, pitch, velocity))
        previous_tick = tick
    track.extend(b"\x00\xff\x2f\x00")
    payload = bytearray(b"MThd")
    payload.extend(struct.pack(">IHHH", 6, 0, 1, ticks_per_quarter))
    payload.extend(b"MTrk")
    payload.extend(struct.pack(">I", len(track)))
    payload.extend(track)
    Path(path).write_bytes(payload)
