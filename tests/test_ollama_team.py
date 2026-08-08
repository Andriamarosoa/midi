from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "scripts" / "local" / "ollama_team.py"
CONFIG_PATH = ROOT / "configs" / "ollama_local_team.json"
POWERSHELL_SOURCE = (ROOT / "OLLAMA_TEAM.ps1").read_text(encoding="utf-8")
SPEC = importlib.util.spec_from_file_location("ollama_team", SOURCE_PATH)
assert SPEC is not None and SPEC.loader is not None
OLLAMA_TEAM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OLLAMA_TEAM)


class OllamaTeamConfigTests(unittest.TestCase):
    def test_role_routing_matches_mac_capacity_policy(self) -> None:
        config = OLLAMA_TEAM.load_config(CONFIG_PATH)
        roles = config["roles"]
        self.assertEqual(roles["batch_test"]["model"], "qwen3:8b")
        self.assertEqual(roles["implementation"]["model"], "qwen3:14b")
        self.assertEqual(roles["orchestration"]["model"], "qwen3:14b")
        self.assertEqual(roles["deep_review"]["model"], "qwen3.6:latest")
        self.assertEqual(roles["performance_judge"]["model"], "qwen3.6:latest")

    def test_endpoint_must_be_loopback(self) -> None:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        payload["endpoint"] = "http://100.89.128.87:11434"
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(OLLAMA_TEAM.TeamError, "loopback"):
                OLLAMA_TEAM.load_config(path)

    def test_base_system_prompt_is_advisory_and_locked_test_closed(self) -> None:
        config = OLLAMA_TEAM.load_config(CONFIG_PATH)
        messages = OLLAMA_TEAM.build_messages(
            config["roles"]["code_review"], "Review this diff.", ""
        )
        system = messages[0]["content"]
        self.assertIn("no execution authority", system)
        self.assertIn("locked test split", system)
        self.assertIn("Kaggle", system)
        self.assertIn("Do not edit files", config["roles"]["implementation"]["instruction"])


class OllamaTeamSafetyTests(unittest.TestCase):
    def test_context_rejects_external_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".txt") as handle:
            with self.assertRaisesRegex(OLLAMA_TEAM.TeamError, "repository file"):
                OLLAMA_TEAM.validate_context_path(pathlib.Path(handle.name))

    def test_context_rejects_sensitive_and_binary_paths(self) -> None:
        self.assertIn("data", OLLAMA_TEAM.FORBIDDEN_CONTEXT_PARTS)
        self.assertIn(".keras", OLLAMA_TEAM.FORBIDDEN_CONTEXT_SUFFIXES)
        self.assertIn("mac_worker.json", OLLAMA_TEAM.FORBIDDEN_CONTEXT_NAMES)

    def test_relative_context_is_resolved_from_repository_root(self) -> None:
        text, evidence = OLLAMA_TEAM.read_context_files(
            [pathlib.Path("configs/ollama_local_team.json")], 200_000
        )
        self.assertIn("CONTEXT FILE: configs/ollama_local_team.json", text)
        self.assertEqual(evidence[0]["path"], "configs/ollama_local_team.json")

    def test_shared_heavy_lock_refuses_concurrent_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            with OLLAMA_TEAM.HeavyWorkerLock(root, "first"):
                with self.assertRaisesRegex(OLLAMA_TEAM.TeamError, "already active"):
                    with OLLAMA_TEAM.HeavyWorkerLock(root, "second"):
                        self.fail("Second lock must never be acquired")
            self.assertFalse((root / "active.lock").exists())

    def test_report_metrics_are_objective_counts_and_rates(self) -> None:
        metrics = OLLAMA_TEAM.extract_metrics(
            {
                "load_duration": 2_000_000_000,
                "prompt_eval_count": 50,
                "prompt_eval_duration": 500_000_000,
                "eval_count": 100,
                "eval_duration": 5_000_000_000,
                "done_reason": "stop",
            },
            8.0,
        )
        self.assertEqual(metrics["load_seconds"], 2.0)
        self.assertEqual(metrics["prompt_tokens_per_second"], 100.0)
        self.assertEqual(metrics["generated_tokens_per_second"], 20.0)

    def test_powershell_wrapper_binds_exact_git_commit_and_base64_prompt(self) -> None:
        self.assertIn("Mac Git commit mismatch", POWERSHELL_SOURCE)
        self.assertIn("rev-parse HEAD", POWERSHELL_SOURCE)
        self.assertIn("--prompt-base64", POWERSHELL_SOURCE)
        self.assertIn("MIDI_MAC_WORKER_ROOT", POWERSHELL_SOURCE)


if __name__ == "__main__":
    unittest.main()
