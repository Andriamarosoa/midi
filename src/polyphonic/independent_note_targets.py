"""Deterministic labels for a causal independent-note head.

The target answers whether a MIDI pitch belongs to a real annotated note at
the current frame.  Inactive pitches are supervised as ``harmonic_only`` only
when an active lower note explicitly owns a measured, present partial at that
pitch.  Every other inactive pitch remains masked so unavailable supervision
cannot become a false negative.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

import numpy as np


@dataclass(frozen=True)
class IndependentNoteFrameTargets:
    """One frame of binary values and confidence/sample weights."""

    target: np.ndarray
    weight: np.ndarray


def _aligned_candidate_class(
    base_class: int,
    harmonic_number: int,
    *,
    annotation_offset_from_rounded_midi_cents: float,
    partial_residual_from_annotated_harmonic_cents: float,
    pitch_classes: int,
    tolerance_cents: float,
) -> int | None:
    if harmonic_number < 2:
        return None
    semitones = (
        12.0 * math.log2(float(harmonic_number))
        # The active class is rounded MIDI.  The fundamental table bridges it
        # to the fractional annotation, and the harmonic table then bridges
        # that annotation to the measured partial.  Both offsets are needed.
        + float(annotation_offset_from_rounded_midi_cents) / 100.0
        + float(partial_residual_from_annotated_harmonic_cents) / 100.0
    )
    rounded = int(round(semitones))
    if abs(100.0 * (semitones - rounded)) > tolerance_cents:
        return None
    candidate = int(base_class) + rounded
    return candidate if 0 <= candidate < pitch_classes else None


def build_independent_note_targets(
    arrays: Mapping[str, np.ndarray],
    frame_index: int,
    *,
    pitch_classes: int,
    harmonic_tolerance_cents: float = 35.0,
) -> IndependentNoteFrameTargets:
    """Build leakage-free labels from one compact annotation frame.

    Positive labels come directly from ``active_bits`` and always have full
    weight.  A negative receives weight only when an active fundamental's
    note-level table marks the aligned partial both explicitly supervised and
    present.  Its confidence is ``reliability * amplitude``.  Positives are
    installed first and can therefore never be overwritten by a coincident
    partial from another chord tone.
    """

    classes = int(pitch_classes)
    index = int(frame_index)
    tolerance = float(harmonic_tolerance_cents)
    if classes < 1 or classes > 64:
        raise ValueError("pitch_classes must be in [1, 64].")
    if index < 0:
        raise IndexError("frame_index cannot be negative.")
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("harmonic_tolerance_cents must be finite and non-negative.")

    active_bits = np.asarray(arrays["active_bits"])
    if active_bits.ndim != 1 or index >= len(active_bits):
        raise IndexError("frame_index is outside active_bits.")

    target = np.zeros(classes, dtype=np.float32)
    weight = np.zeros(classes, dtype=np.float32)
    valid = arrays.get("valid")
    if valid is not None:
        valid_array = np.asarray(valid)
        if valid_array.shape != active_bits.shape:
            raise ValueError("valid must align with active_bits.")
        if not bool(valid_array[index]):
            return IndependentNoteFrameTargets(target=target, weight=weight)

    bits = np.uint64(active_bits[index])
    class_bits = np.arange(classes, dtype=np.uint64)
    active = ((bits >> class_bits) & np.uint64(1)).astype(np.bool_)
    target[active] = 1.0
    weight[active] = 1.0

    optional_names = (
        "note_harmonic_supervised",
        "note_harmonic_present",
        "note_harmonic_amplitude",
        "note_harmonic_reliability",
        "note_harmonic_offset_cents",
        "note_fundamental_offset_cents",
        "slot_pitch",
        "slot_note_id",
    )
    if any(name not in arrays for name in optional_names):
        # Old/non-harmonic corpora still provide trustworthy positives, but
        # unavailable harmonic supervision must never create negatives.
        return IndependentNoteFrameTargets(target=target, weight=weight)

    supervised = np.asarray(arrays["note_harmonic_supervised"])
    present = np.asarray(arrays["note_harmonic_present"])
    amplitude = np.asarray(arrays["note_harmonic_amplitude"], dtype=np.float32)
    reliability = np.asarray(
        arrays["note_harmonic_reliability"], dtype=np.float32
    )
    offset_cents = np.asarray(
        arrays["note_harmonic_offset_cents"], dtype=np.float32
    )
    fundamental_offset_cents = np.asarray(
        arrays["note_fundamental_offset_cents"], dtype=np.float32
    )
    if supervised.ndim != 2 or supervised.shape != present.shape:
        raise ValueError("Harmonic supervised/present tables must align.")
    if (
        amplitude.shape != supervised.shape
        or reliability.shape != supervised.shape
        or offset_cents.shape != supervised.shape
    ):
        raise ValueError("Harmonic confidence tables must align with supervision.")
    if fundamental_offset_cents.shape != (supervised.shape[0],):
        raise ValueError("Fundamental offsets must align with harmonic note rows.")
    slot_pitch = np.asarray(arrays["slot_pitch"])
    slot_note_id = np.asarray(arrays["slot_note_id"])
    if slot_pitch.shape != slot_note_id.shape or slot_pitch.ndim != 2:
        raise ValueError("slot_pitch and slot_note_id must be aligned matrices.")
    if slot_pitch.shape[0] != len(active_bits):
        raise ValueError("Slot matrices must align with active_bits.")

    note_valid_source = arrays.get("note_harmonic_valid")
    if note_valid_source is None:
        note_valid = np.any(supervised > 0, axis=1)
    else:
        note_valid = np.asarray(note_valid_source) > 0
        if note_valid.shape != (supervised.shape[0],):
            raise ValueError("note_harmonic_valid must align with note rows.")

    for raw_base_class, raw_note_id in zip(
        slot_pitch[index], slot_note_id[index]
    ):
        base_class = int(raw_base_class)
        note_id = int(raw_note_id)
        if base_class < 0 and note_id < 0:
            continue
        if not (0 <= base_class < classes) or not (
            0 <= note_id < supervised.shape[0]
        ):
            raise ValueError("Active slot contains an invalid pitch or note_id.")
        if not active[base_class]:
            raise ValueError("Active slot pitch is absent from active_bits.")
        if not note_valid[note_id]:
            continue
        annotation_offset = float(fundamental_offset_cents[note_id])
        if not math.isfinite(annotation_offset):
            raise ValueError("Supervised fundamental offsets must be finite.")
        for harmonic_index in np.flatnonzero(
            (supervised[note_id] > 0) & (present[note_id] > 0)
        ):
            partial_offset = float(offset_cents[note_id, harmonic_index])
            if not math.isfinite(partial_offset):
                raise ValueError("Present harmonic offsets must be finite.")
            candidate = _aligned_candidate_class(
                base_class,
                int(harmonic_index) + 1,
                annotation_offset_from_rounded_midi_cents=annotation_offset,
                partial_residual_from_annotated_harmonic_cents=partial_offset,
                pitch_classes=classes,
                tolerance_cents=tolerance,
            )
            if candidate is None or active[candidate]:
                continue
            partial_amplitude = float(amplitude[note_id, harmonic_index])
            partial_reliability = float(reliability[note_id, harmonic_index])
            if not (
                math.isfinite(partial_amplitude)
                and math.isfinite(partial_reliability)
            ):
                raise ValueError("Harmonic confidence values must be finite.")
            confidence = float(
                np.clip(partial_amplitude, 0.0, 1.0)
                * np.clip(partial_reliability, 0.0, 1.0)
            )
            weight[candidate] = max(weight[candidate], confidence)

    return IndependentNoteFrameTargets(target=target, weight=weight)
