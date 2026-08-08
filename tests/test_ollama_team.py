from __future__ import annotations

import argparse
import contextlib
import http.server
import importlib.util
import io
import json
import pathlib
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest import mock


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

    def test_context_rejects_locked_test_in_any_path_component(self) -> None:
        temporary_root = ROOT / "tmp"
        temporary_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="locked_test_parent_", dir=temporary_root
        ) as directory:
            path = pathlib.Path(directory) / "innocent.txt"
            path.write_text("not locked-test data", encoding="utf-8")
            with self.assertRaisesRegex(OLLAMA_TEAM.TeamError, "Locked-test"):
                OLLAMA_TEAM.validate_context_path(path)

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

    def test_preserved_lock_requires_manual_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            with OLLAMA_TEAM.HeavyWorkerLock(root, "cleanup") as lock:
                lock.preserve("model remained resident")
            lock_path = root / "active.lock"
            self.assertTrue(lock_path.is_dir())
            owner = json.loads(
                (lock_path / "ollama-team-owner.json").read_text(encoding="utf-8")
            )
            self.assertTrue(owner["requires_manual_inspection"])
            self.assertIn("remained resident", owner["cleanup_error"])
            (lock_path / "ollama-team-owner.json").unlink()
            lock_path.rmdir()

    def test_client_refuses_http_redirects(self) -> None:
        class RedirectHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(302)
                self.send_header("Location", "http://example.com/")
                self.end_headers()

            def log_message(self, format_string, *arguments) -> None:
                del format_string, arguments

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = OLLAMA_TEAM.OllamaClient(
                f"http://127.0.0.1:{server.server_port}", timeout_seconds=2
            )
            with self.assertRaisesRegex(OLLAMA_TEAM.TeamError, "request failed"):
                client.installed_models()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_unload_waits_until_model_is_absent(self) -> None:
        client = object.__new__(OLLAMA_TEAM.OllamaClient)
        calls = []
        states = iter([[{"name": "qwen3:8b"}], []])
        client.unload = lambda model: calls.append(("unload", model))
        client.running_models = lambda: next(states)
        client.unload_and_wait("qwen3:8b", timeout_seconds=1, poll_seconds=0)
        self.assertEqual(calls, [("unload", "qwen3:8b")])

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

    def test_run_unloads_before_releasing_lock_and_does_not_log_response(self) -> None:
        config = OLLAMA_TEAM.load_config(CONFIG_PATH)
        model = config["roles"]["brainstorming"]["model"]
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            log_root = root / "logs"
            events = []
            fake_client = SimpleNamespace(
                installed_models=lambda: [model],
                chat=lambda *args, **kwargs: {
                    "message": {"content": "private advisory response"},
                    "eval_count": 2,
                    "eval_duration": 1_000_000_000,
                },
            )

            def unload_and_wait(unloaded_model):
                self.assertEqual(unloaded_model, model)
                self.assertTrue((root / "active.lock").is_dir())
                events.append("unloaded")

            fake_client.unload_and_wait = unload_and_wait
            args = argparse.Namespace(
                role="brainstorming",
                context_file=[],
                timeout_seconds=10,
                no_log=False,
                json=False,
                log_root=log_root,
            )
            with mock.patch.object(OLLAMA_TEAM, "assert_clean_git_worktree"), mock.patch.object(
                OLLAMA_TEAM, "OllamaClient", return_value=fake_client
            ), mock.patch.dict(
                OLLAMA_TEAM.os.environ, {"MIDI_MAC_WORKER_ROOT": str(root)}
            ), mock.patch.object(
                OLLAMA_TEAM.sys, "stdin", io.StringIO("review prompt")
            ), contextlib.redirect_stdout(io.StringIO()):
                OLLAMA_TEAM.run_role(args, config)
            self.assertEqual(events, ["unloaded"])
            self.assertFalse((root / "active.lock").exists())
            reports = list(log_root.glob("*.json"))
            self.assertEqual(len(reports), 1)
            report = json.loads(reports[0].read_text(encoding="utf-8"))
            self.assertNotIn("response", report)
            self.assertEqual(report["response_characters"], 25)
            self.assertEqual(
                report["response_sha256"],
                OLLAMA_TEAM._sha256_bytes(b"private advisory response"),
            )

    def test_run_unloads_when_chat_fails(self) -> None:
        config = OLLAMA_TEAM.load_config(CONFIG_PATH)
        model = config["roles"]["brainstorming"]["model"]
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            events = []

            def fail_chat(*args, **kwargs):
                raise OLLAMA_TEAM.TeamError("chat failed")

            fake_client = SimpleNamespace(
                installed_models=lambda: [model],
                chat=fail_chat,
                unload_and_wait=lambda unloaded_model: events.append(
                    ("unloaded", unloaded_model)
                ),
            )
            args = argparse.Namespace(
                role="brainstorming",
                context_file=[],
                timeout_seconds=10,
                no_log=True,
                json=False,
                log_root=root / "logs",
            )
            with mock.patch.object(OLLAMA_TEAM, "assert_clean_git_worktree"), mock.patch.object(
                OLLAMA_TEAM, "OllamaClient", return_value=fake_client
            ), mock.patch.dict(
                OLLAMA_TEAM.os.environ, {"MIDI_MAC_WORKER_ROOT": str(root)}
            ), mock.patch.object(
                OLLAMA_TEAM.sys, "stdin", io.StringIO("review prompt")
            ):
                with self.assertRaisesRegex(OLLAMA_TEAM.TeamError, "chat failed"):
                    OLLAMA_TEAM.run_role(args, config)
            self.assertEqual(events, [("unloaded", model)])
            self.assertFalse((root / "active.lock").exists())

    def test_cleanup_failure_preserves_heavy_lock(self) -> None:
        config = OLLAMA_TEAM.load_config(CONFIG_PATH)
        model = config["roles"]["brainstorming"]["model"]
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)

            def fail_unload(unloaded_model):
                self.assertEqual(unloaded_model, model)
                raise OLLAMA_TEAM.TeamError("unload not confirmed")

            fake_client = SimpleNamespace(
                installed_models=lambda: [model],
                chat=lambda *args, **kwargs: {
                    "message": {"content": "response"},
                },
                unload_and_wait=fail_unload,
            )
            args = argparse.Namespace(
                role="brainstorming",
                context_file=[],
                timeout_seconds=10,
                no_log=True,
                json=False,
                log_root=root / "logs",
            )
            with mock.patch.object(OLLAMA_TEAM, "assert_clean_git_worktree"), mock.patch.object(
                OLLAMA_TEAM, "OllamaClient", return_value=fake_client
            ), mock.patch.dict(
                OLLAMA_TEAM.os.environ, {"MIDI_MAC_WORKER_ROOT": str(root)}
            ), mock.patch.object(
                OLLAMA_TEAM.sys, "stdin", io.StringIO("review prompt")
            ):
                with self.assertRaisesRegex(OLLAMA_TEAM.TeamError, "unload not confirmed"):
                    OLLAMA_TEAM.run_role(args, config)
            lock_path = root / "active.lock"
            self.assertTrue(lock_path.is_dir())
            owner = json.loads(
                (lock_path / "ollama-team-owner.json").read_text(encoding="utf-8")
            )
            self.assertTrue(owner["requires_manual_inspection"])
            (lock_path / "ollama-team-owner.json").unlink()
            lock_path.rmdir()

    def test_dirty_git_worktree_is_rejected(self) -> None:
        completed = SimpleNamespace(returncode=0, stdout=" M decoder.py\n")
        with mock.patch.object(OLLAMA_TEAM.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(OLLAMA_TEAM.TeamError, "clean Git"):
                OLLAMA_TEAM.assert_clean_git_worktree()

    def test_benchmark_unloads_when_generation_fails(self) -> None:
        config = OLLAMA_TEAM.load_config(CONFIG_PATH)
        model = config["benchmark"]["models"][0]
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            events = []

            def fail_generate(*args, **kwargs):
                raise OLLAMA_TEAM.TeamError("generation failed")

            fake_client = SimpleNamespace(
                installed_models=lambda: [model],
                generate_benchmark=fail_generate,
                unload_and_wait=lambda unloaded_model: events.append(
                    ("unloaded", unloaded_model)
                ),
            )
            args = argparse.Namespace(
                model=[model], timeout_seconds=10, log_root=root / "logs"
            )
            with mock.patch.object(OLLAMA_TEAM, "assert_clean_git_worktree"), mock.patch.object(
                OLLAMA_TEAM, "OllamaClient", return_value=fake_client
            ), mock.patch.dict(
                OLLAMA_TEAM.os.environ, {"MIDI_MAC_WORKER_ROOT": str(root)}
            ):
                with self.assertRaisesRegex(OLLAMA_TEAM.TeamError, "generation failed"):
                    OLLAMA_TEAM.run_benchmark(args, config)
            self.assertEqual(events, [("unloaded", model)])
            self.assertFalse((root / "active.lock").exists())

    def test_powershell_wrapper_binds_clean_exact_git_and_stdin_prompt(self) -> None:
        self.assertIn("Mac Git commit mismatch", POWERSHELL_SOURCE)
        self.assertIn("rev-parse HEAD", POWERSHELL_SOURCE)
        self.assertIn("status --porcelain --untracked-files=all", POWERSHELL_SOURCE)
        self.assertIn("$StandardInput | & ssh", POWERSHELL_SOURCE)
        self.assertNotIn("--prompt-base64", POWERSHELL_SOURCE)
        self.assertIn("MIDI_MAC_WORKER_ROOT", POWERSHELL_SOURCE)


if __name__ == "__main__":
    unittest.main()
