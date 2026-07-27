from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import wave

from src.polyphonic.build_ab_listening_pack import build_ab_listening_pack
from src.product.midi_file import write_midi


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_wav(path: Path, *, frames: int = 800, rate: int = 8_000) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(b"\x00\x00" * frames)


def _write_note(path: Path, pitch: int, end_s: float) -> None:
    write_midi(
        path,
        [
            {"kind": "note_on", "time_s": 0.0, "pitch": pitch, "velocity": 90},
            {"kind": "note_off", "time_s": end_s, "pitch": pitch, "velocity": 0},
        ],
    )


class AbListeningPackTests(unittest.TestCase):
    def _inputs(self, root: Path) -> tuple[Path, Path, Path]:
        source = root / "input.wav"
        baseline = root / "meaningful-baseline-name.mid"
        candidate = root / "meaningful-candidate-name.mid"
        _write_wav(source)
        _write_note(baseline, 60, 0.5)
        _write_note(candidate, 64, 0.75)
        return source, baseline, candidate

    def test_no_render_builds_blind_self_contained_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, baseline, candidate = self._inputs(root)
            output = root / "pack"
            output.mkdir()
            # A stale render must not survive a --no-render rebuild.
            (output / "A.wav").write_bytes(b"stale")

            manifest = build_ab_listening_pack(
                source,
                baseline,
                candidate,
                output,
                no_render=True,
            )

            self.assertEqual((output / "source.wav").read_bytes(), source.read_bytes())
            self.assertFalse((output / "A.wav").exists())
            self.assertFalse((output / "B.wav").exists())
            self.assertFalse(manifest["rendering"]["performed"])
            self.assertEqual(manifest["rendering"]["commands"], [])
            self.assertAlmostEqual(manifest["source"]["duration_s"], 0.1)
            self.assertEqual(manifest["items"]["A"]["midi"]["note_count"], 1)
            self.assertIsNone(manifest["items"]["A"]["audio"])

            public_text = (output / "manifest.json").read_text(encoding="utf-8")
            self.assertNotIn("meaningful-baseline-name", public_text)
            self.assertNotIn("meaningful-candidate-name", public_text)
            self.assertNotIn('"role": "baseline"', public_text)
            self.assertNotIn('"role": "candidate"', public_text)
            self.assertNotIn("perceptual_score", public_text)

            protocol_path = output / "LISTENING_PROTOCOL.md"
            ratings_path = output / "ratings_template.json"
            protocol = protocol_path.read_text(encoding="utf-8")
            ratings = json.loads(ratings_path.read_text(encoding="utf-8"))
            self.assertIn("strictement constant", protocol)
            self.assertIn("source, B, A", protocol)
            for criterion in (
                "hauteurs",
                "fantômes",
                "Omissions",
                "Timing",
                "Fragmentation",
                "Préférence",
            ):
                self.assertIn(criterion, protocol)
            self.assertNotIn("baseline", protocol.lower())
            self.assertNotIn("candidate", protocol.lower())
            self.assertIsNone(ratings["playback"]["fixed_volume_confirmed"])
            self.assertIsNone(
                ratings["passages"][0]["ratings"]["A"][
                    "pitch_accuracy_1_to_5"
                ]
            )
            self.assertIsNone(
                ratings["passages"][0]["ratings"]["B"][
                    "ghost_notes_severity_0_to_4"
                ]
            )
            self.assertIsNone(ratings["passages"][0]["preference"])
            self.assertIsNone(ratings["overall"]["preference"])
            ratings_text = ratings_path.read_text(encoding="utf-8").lower()
            self.assertNotIn("baseline", ratings_text)
            self.assertNotIn("candidate", ratings_text)
            self.assertEqual(
                manifest["blind_listening"]["protocol"]["sha256"],
                _sha256(protocol_path),
            )
            self.assertEqual(
                manifest["blind_listening"]["ratings_template"]["sha256"],
                _sha256(ratings_path),
            )

            mapping_path = output / "mapping.json"
            mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
            roles = {
                item["role"]: label
                for label, item in mapping["assignments"].items()
            }
            self.assertEqual(set(roles), {"baseline", "candidate"})
            baseline_label = roles["baseline"]
            candidate_label = roles["candidate"]
            self.assertEqual(
                (output / f"{baseline_label}.mid").read_bytes(),
                baseline.read_bytes(),
            )
            self.assertEqual(
                (output / f"{candidate_label}.mid").read_bytes(),
                candidate.read_bytes(),
            )
            self.assertAlmostEqual(
                manifest["items"][baseline_label]["midi"]["duration_s"], 0.5
            )
            self.assertAlmostEqual(
                manifest["items"][candidate_label]["midi"]["duration_s"], 0.75
            )
            self.assertEqual(
                manifest["private_mapping"]["sha256"], _sha256(mapping_path)
            )

    def test_render_uses_deterministic_options_before_operands(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, baseline, candidate = self._inputs(root)
            soundfont = root / "piano.sf2"
            executable = root / "fluidsynth.exe"
            soundfont.write_bytes(b"soundfont")
            executable.write_bytes(b"executable")
            commands: list[list[str]] = []

            def fake_runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                commands.append(command)
                output = Path(command[command.index("-F") + 1])
                _write_wav(output, frames=4_410, rate=44_100)
                return subprocess.CompletedProcess(command, 0, "ok", "")

            output = root / "pack"
            output.mkdir()
            (output / "A.wav").write_bytes(b"stale")
            (output / "B.wav").write_bytes(b"stale")
            manifest = build_ab_listening_pack(
                source,
                baseline,
                candidate,
                output,
                soundfont=soundfont,
                fluidsynth=executable,
                runner=fake_runner,
            )

            self.assertEqual(len(commands), 2)
            for label, command in zip(("A", "B"), commands):
                soundfont_index = command.index(str(soundfont.resolve()))
                midi_index = command.index(str((output / f"{label}.mid").resolve()))
                self.assertEqual(soundfont_index, len(command) - 2)
                self.assertEqual(midi_index, len(command) - 1)
                for option in ("-n", "-i", "-q", "-C", "-R", "-r", "-g",
                               "-O", "-T", "-o", "-F"):
                    self.assertLess(command.index(option), soundfont_index)
                self.assertEqual(command[command.index("-C") + 1], "0")
                self.assertEqual(command[command.index("-R") + 1], "0")
                self.assertEqual(
                    command[command.index("-r") + 1], "44100"
                )
                self.assertEqual(command[command.index("-O") + 1], "s16")
                self.assertEqual(command[command.index("-T") + 1], "wav")

            self.assertTrue(manifest["rendering"]["performed"])
            self.assertEqual(manifest["rendering"]["commands"], commands)
            self.assertEqual(
                manifest["rendering"]["executable"]["sha256"],
                _sha256(executable),
            )
            self.assertEqual(
                manifest["rendering"]["soundfont"]["sha256"], _sha256(soundfont)
            )
            for label in ("A", "B"):
                rendered = output / f"{label}.wav"
                self.assertTrue(rendered.is_file())
                self.assertEqual(
                    manifest["items"][label]["audio"]["sha256"],
                    _sha256(rendered),
                )
                self.assertAlmostEqual(
                    manifest["items"][label]["audio"]["duration_s"], 0.1
                )

    def test_invalid_inputs_and_render_failure_do_not_publish_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, baseline, candidate = self._inputs(root)
            invalid_wav = root / "invalid.wav"
            invalid_wav.write_bytes(b"not-wave")
            invalid_midi = root / "invalid.mid"
            invalid_midi.write_bytes(b"not-midi")

            with self.assertRaisesRegex(ValueError, "WAV invalide"):
                build_ab_listening_pack(
                    invalid_wav, baseline, candidate, root / "bad-wav",
                    no_render=True,
                )
            with self.assertRaisesRegex(ValueError, "MIDI invalide"):
                build_ab_listening_pack(
                    source, invalid_midi, candidate, root / "bad-midi",
                    no_render=True,
                )
            with self.assertRaisesRegex(ValueError, "--soundfont"):
                build_ab_listening_pack(
                    source, baseline, candidate, root / "missing-sf",
                )

            soundfont = root / "piano.sf2"
            executable = root / "fluidsynth.exe"
            soundfont.write_bytes(b"soundfont")
            executable.write_bytes(b"executable")

            def failing_runner(
                command: list[str], **_: object
            ) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(command, 7, "", "render failed")

            output = root / "failed-render"
            with self.assertRaisesRegex(RuntimeError, "render failed"):
                build_ab_listening_pack(
                    source,
                    baseline,
                    candidate,
                    output,
                    soundfont=soundfont,
                    fluidsynth=executable,
                    runner=failing_runner,
                )
            self.assertFalse((output / "manifest.json").exists())
            self.assertFalse((output / "mapping.json").exists())


if __name__ == "__main__":
    unittest.main()
