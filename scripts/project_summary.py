"""Update the single human-readable project summary atomically.

Long-running jobs call this utility only when their phase changes. Progress
logs remain in ``tmp/``; completed, active, next and anomalous phases are
recorded in ``readme/README.md``.
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = ROOT / "readme/README.md"
CURRENT_START = "<!-- CURRENT_STATUS_START -->"
CURRENT_END = "<!-- CURRENT_STATUS_END -->"
JOURNAL_START = "<!-- JOURNAL_START -->"
JOURNAL_END = "<!-- JOURNAL_END -->"


def _replace_between(
    text: str, start: str, end: str, replacement: str
) -> str:
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f"Expected one marker pair: {start}, {end}")
    before, remainder = text.split(start, 1)
    _, after = remainder.split(end, 1)
    return before + start + "\n" + replacement.rstrip() + "\n" + end + after


def update_project_summary(
    *,
    phase: str,
    status: str,
    detail: str,
    next_steps: Sequence[str],
    summary_path: Path = DEFAULT_SUMMARY,
    timestamp: datetime | None = None,
) -> bool:
    """Update current status and append one deduplicated journal event."""
    summary_path = summary_path.resolve()
    text = summary_path.read_text(encoding="utf-8")
    moment = timestamp or datetime.now(timezone.utc)
    iso_time = moment.isoformat()
    current_lines = [
        "## État courant",
        "",
        f"- Mise à jour : `{iso_time}`",
        f"- Étape : `{phase}`",
        f"- Statut : `{status}`",
        f"- Détail : {detail}",
        "",
        "## Étapes suivantes",
        "",
    ]
    if next_steps:
        current_lines.extend(
            f"{index}. {step}"
            for index, step in enumerate(next_steps, start=1)
        )
    else:
        current_lines.append("Aucune étape automatique restante.")
    text = _replace_between(
        text, CURRENT_START, CURRENT_END, "\n".join(current_lines)
    )

    event_payload = "\0".join((phase, status, detail))
    event_id = hashlib.sha256(event_payload.encode("utf-8")).hexdigest()[:16]
    event_marker = f"<!-- project-event:{event_id} -->"
    appended = event_marker not in text
    if appended:
        date_text = moment.date().isoformat()
        journal_entry = (
            f"- {date_text} — **{status}** — `{phase}` : {detail}\n"
            f"  {event_marker}"
        )
        before, remainder = text.split(JOURNAL_START, 1)
        journal, after = remainder.split(JOURNAL_END, 1)
        journal = journal.rstrip() + "\n" + journal_entry + "\n"
        text = before + JOURNAL_START + journal + JOURNAL_END + after

    temporary = summary_path.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(summary_path)
    return appended


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--detail", required=True)
    parser.add_argument("--next", action="append", default=[])
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()
    appended = update_project_summary(
        phase=args.phase,
        status=args.status,
        detail=args.detail,
        next_steps=args.next,
        summary_path=args.summary,
    )
    print("journal_appended=" + str(appended).lower())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
