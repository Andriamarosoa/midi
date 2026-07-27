from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ManifestItem:
    source_id: str
    npz_path: Path
    player_id: str
    dataset_id: str = "guitarset"
    group_id: str = ""
    capture_id: str = ""
    split: str | None = None


def player_from_source(source_id: str) -> str:
    match = re.match(r"^(\d{2})_", source_id)
    if not match:
        raise ValueError(f"Impossible d'extraire le joueur depuis: {source_id}")
    return match.group(1)


def load_manifest(path: str | Path) -> list[ManifestItem]:
    path = Path(path)
    items: list[ManifestItem] = []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            source_id = (row.get("source_id") or "").strip()
            raw_path = (row.get("npz_path") or "").strip()

            if not source_id:
                continue

            candidate = Path(raw_path) if raw_path else path.parent / f"{source_id}.npz"
            if not candidate.is_absolute():
                candidate = (Path.cwd() / candidate).resolve()

            if not candidate.is_file():
                fallback = (path.parent / f"{source_id}.npz").resolve()
                if fallback.is_file():
                    candidate = fallback
                else:
                    raise FileNotFoundError(f"NPZ absent pour {source_id}: {candidate}")

            explicit_player = (row.get("player_id") or "").strip()
            explicit_split = (row.get("split") or "").strip().lower() or None
            if explicit_split not in {None, "train", "validation", "test"}:
                raise ValueError(
                    f"Split invalide pour {source_id}: {explicit_split}"
                )

            items.append(
                ManifestItem(
                    source_id=source_id,
                    npz_path=candidate,
                    player_id=explicit_player or player_from_source(source_id),
                    dataset_id=(row.get("dataset_id") or "guitarset").strip(),
                    group_id=(row.get("group_id") or source_id).strip(),
                    capture_id=(row.get("capture_id") or "").strip(),
                    split=explicit_split,
                )
            )

    unique = {item.source_id: item for item in items}
    return [unique[key] for key in sorted(unique)]


def split_manifest(
    items: Iterable[ManifestItem],
    train_players: Iterable[str],
    validation_players: Iterable[str],
    test_players: Iterable[str],
) -> dict[str, list[ManifestItem]]:
    train_set = set(train_players)
    validation_set = set(validation_players)
    test_set = set(test_players)

    overlap = (
        (train_set & validation_set)
        | (train_set & test_set)
        | (validation_set & test_set)
    )
    if overlap:
        raise ValueError(f"Joueurs présents dans plusieurs splits: {sorted(overlap)}")

    groups = {"train": [], "validation": [], "test": []}
    mapping = {p: "train" for p in train_set}
    mapping.update({p: "validation" for p in validation_set})
    mapping.update({p: "test" for p in test_set})

    group_splits: dict[str, str] = {}
    for item in items:
        split_name = item.split or mapping.get(item.player_id)
        if split_name is not None:
            previous = group_splits.get(item.group_id)
            if previous is not None and previous != split_name:
                raise ValueError(
                    f"Groupe présent dans plusieurs splits: {item.group_id} "
                    f"({previous}, {split_name})"
                )
            group_splits[item.group_id] = split_name
            groups[split_name].append(item)

    for split_name, split_items in groups.items():
        if not split_items:
            raise ValueError(f"Split vide: {split_name}")

    return groups
