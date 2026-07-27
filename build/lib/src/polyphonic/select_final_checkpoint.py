"""Select one deployable checkpoint using validation note events only."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict
from pathlib import Path

from src.polyphonic.decoder import default_decoder_config
from src.polyphonic.evaluate_events import evaluate_events


def event_selection_key(row: dict[str, object]) -> tuple[float, ...]:
    onset = row["onset"]
    onset_offset = row["onset_offset"]
    assert isinstance(onset, dict) and isinstance(onset_offset, dict)
    return (
        float(onset["f1"]),
        float(onset_offset["f1"]),
        float(onset["precision"]),
        float(onset["recall"]),
        -float(onset["onset_error_p95_absolute_ms"]),
    )


def _candidate_rows(ranking: dict[str, object]) -> list[dict[str, object]]:
    rows = ranking["checkpoints"]
    pareto = set(ranking["pareto_candidates"])
    if not isinstance(rows, list):
        raise ValueError("Invalid checkpoint ranking.")
    selected = [row for row in rows if str(row["checkpoint"]) in pareto]
    if not selected:
        raise ValueError("Checkpoint ranking contains no Pareto candidates.")
    return selected


def select(
    run_dir: Path,
    maximum_recordings: int | None = None,
    maximum_candidates: int | None = None,
) -> dict[str, object]:
    ranking_path = run_dir / "checkpoint_ranking.json"
    ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
    if ranking.get("split") != "validation" or ranking.get("locked_test_used") is not False:
        raise ValueError("Checkpoint ranking is not validation-only.")
    candidates = _candidate_rows(ranking)
    if maximum_candidates is not None and len(candidates) > maximum_candidates:
        # Keep diverse leaders rather than collapsing back to one metric.
        leaders: list[dict[str, object]] = []
        metrics = (
            ("frame_f1", True), ("onset_f1", True),
            ("harmonic_amplitude_mae", False),
            ("harmonic_offset_normalized_mae", False),
        )
        for metric, descending in metrics:
            row = sorted(
                candidates, key=lambda value: float(value[metric]),
                reverse=descending,
            )[0]
            if row not in leaders:
                leaders.append(row)
        candidates = leaders[:maximum_candidates]

    evaluated: list[dict[str, object]] = []
    for candidate in candidates:
        checkpoint = Path(str(candidate["checkpoint"]))
        thresholds_path = Path(str(candidate["thresholds"]))
        thresholds = json.loads(thresholds_path.read_text(encoding="utf-8"))
        decoder = default_decoder_config(
            float(thresholds["frame"]), float(thresholds["onset"])
        )
        decoder_path = thresholds_path.with_name(
            f"{checkpoint.stem}_decoder.json"
        )
        decoder_path.write_text(
            json.dumps(asdict(decoder), indent=2), encoding="utf-8"
        )
        report = evaluate_events(
            run_dir=run_dir,
            split="validation",
            maximum_recordings=maximum_recordings,
            checkpoint_path=checkpoint,
            thresholds_path=thresholds_path,
            decoder_config_path=decoder_path,
        )
        evaluated.append({
            "checkpoint": str(checkpoint),
            "thresholds": str(thresholds_path),
            "decoder_config": str(decoder_path),
            "recordings": report["recordings"],
            "onset": report["onset"],
            "onset_offset": report["onset_offset"],
            "retriggers": report["retriggers"],
        })

    chosen = max(evaluated, key=event_selection_key)
    selected_checkpoint = run_dir / "selected.keras"
    shutil.copy2(Path(str(chosen["checkpoint"])), selected_checkpoint)
    shutil.copy2(Path(str(chosen["thresholds"])), run_dir / "thresholds.json")
    shutil.copy2(
        Path(str(chosen["decoder_config"])), run_dir / "decoder_config.json"
    )
    selection = {
        "selected_on": "validation_note_events",
        "locked_test_used": False,
        "maximum_recordings": maximum_recordings,
        "candidate_count": len(evaluated),
        "selection_order": [
            "onset_f1", "onset_offset_f1", "onset_precision",
            "onset_recall", "onset_error_p95_absolute_ms",
        ],
        "selected_checkpoint": str(selected_checkpoint),
        "source_checkpoint": chosen["checkpoint"],
        "thresholds": str(run_dir / "thresholds.json"),
        "decoder_config": str(run_dir / "decoder_config.json"),
        "selected_metrics": chosen,
        "candidates": evaluated,
    }
    (run_dir / "selection.json").write_text(
        json.dumps(selection, indent=2), encoding="utf-8"
    )
    return selection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--maximum-recordings", type=int)
    parser.add_argument("--maximum-candidates", type=int)
    args = parser.parse_args()
    result = select(
        args.run_dir, args.maximum_recordings, args.maximum_candidates
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
