from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.polyphonic.build_guitar_techs import discover_guitar_techs


class GuitarTechsBuilderTests(unittest.TestCase):
    def test_players_define_splits_and_captures_share_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for player in ("P1", "P2", "P3"):
                category = root / f"{player}_music"
                (category / "midi").mkdir(parents=True)
                (category / "audio" / "directinput").mkdir(parents=True)
                (category / "audio" / "micamp").mkdir(parents=True)
                (category / "midi" / "midi_song.mid").touch()
                (category / "audio" / "directinput" / "directinput_song.wav").touch()
                (category / "audio" / "micamp" / "micamp_song.wav").touch()
            recordings = discover_guitar_techs(root)
        self.assertEqual(len(recordings), 6)
        self.assertEqual(
            {row.player_id: row.split for row in recordings},
            {"gtech_p1": "train", "gtech_p2": "validation", "gtech_p3": "test"},
        )
        for player in ("gtech_p1", "gtech_p2", "gtech_p3"):
            captures = [row for row in recordings if row.player_id == player]
            self.assertEqual(len({row.group_id for row in captures}), 1)
            self.assertEqual({row.capture_id for row in captures}, {"directinput", "micamp"})


if __name__ == "__main__":
    unittest.main()
