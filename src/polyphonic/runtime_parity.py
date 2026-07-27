"""Shared numerical parity policy for deployable polyphonic runtimes."""

from __future__ import annotations

from collections.abc import Mapping


OUTPUT_MAX_ABSOLUTE_ERROR = {
    "frame": 0.002,
    "onset": 0.002,
    "harmonic_amplitude": 0.002,
    # This output is expressed in physical cents rather than probability units.
    "harmonic_offset_cents": 0.1,
}
MINIMUM_DECISION_AGREEMENT = 0.999


def parity_passes(metrics: Mapping[str, object]) -> bool:
    """Return whether runtime drift is negligible at the frozen thresholds."""
    for name, tolerance in OUTPUT_MAX_ABSOLUTE_ERROR.items():
        output = metrics.get(name)
        if not isinstance(output, Mapping):
            return False
        if float(output.get("maximum_absolute_error", float("inf"))) > tolerance:
            return False
    return bool(
        float(metrics.get("frame_decision_agreement", 0.0))
        >= MINIMUM_DECISION_AGREEMENT
        and float(metrics.get("onset_decision_agreement", 0.0))
        >= MINIMUM_DECISION_AGREEMENT
    )


def parity_policy_report() -> dict[str, object]:
    return {
        "maximum_absolute_error_by_output": dict(OUTPUT_MAX_ABSOLUTE_ERROR),
        "minimum_frame_decision_agreement": MINIMUM_DECISION_AGREEMENT,
        "minimum_onset_decision_agreement": MINIMUM_DECISION_AGREEMENT,
    }
