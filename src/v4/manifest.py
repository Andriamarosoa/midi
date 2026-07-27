from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv, re

@dataclass(frozen=True)
class ManifestItem:
    source_id: str
    npz_path: Path
    player_id: str

def player_from_source(source_id: str) -> str:
    match=re.match(r"^(\d{2})_",source_id)
    if not match:
        raise ValueError(f"Impossible d'extraire le joueur depuis: {source_id}")
    return match.group(1)

def load_manifest(path: str | Path) -> list[ManifestItem]:
    path=Path(path)
    items=[]
    with path.open('r',encoding='utf-8-sig',newline='') as handle:
        for row in csv.DictReader(handle):
            source=(row.get('source_id') or '').strip()
            raw=(row.get('npz_path') or '').strip()
            if not source or not raw: continue
            candidate=Path(raw)
            if not candidate.is_absolute():
                candidate=Path.cwd()/candidate
            if not candidate.is_file():
                fallback=path.parent/f"{source}.npz"
                if fallback.is_file(): candidate=fallback
                else: raise FileNotFoundError(f"NPZ absent pour {source}: {candidate}")
            items.append(ManifestItem(source,candidate,player_from_source(source)))
    unique={item.source_id:item for item in items}
    return [unique[key] for key in sorted(unique)]

def split_manifest(items, train_players, validation_players, test_players):
    groups={'train':[],'validation':[],'test':[]}
    mapping={p:'train' for p in train_players}
    mapping.update({p:'validation' for p in validation_players})
    mapping.update({p:'test' for p in test_players})
    for item in items:
        split=mapping.get(item.player_id)
        if split: groups[split].append(item)
    for name in groups:
        if not groups[name]: raise ValueError(f"Split vide: {name}")
    overlap=(set(train_players)&set(validation_players)) | (set(train_players)&set(test_players)) | (set(validation_players)&set(test_players))
    if overlap: raise ValueError(f"Joueurs présents dans plusieurs splits: {sorted(overlap)}")
    return groups
