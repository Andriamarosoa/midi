#!/usr/bin/env python3
"""Safe local Ollama role router for the Mac worker.

The tool is deliberately advisory: it cannot edit the repository, run tests,
open the locked test split, or publish Git state.  It serializes Ollama work
with the same atomic directory used by the heavyweight Mac worker.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPOSITORY_ROOT / "configs" / "ollama_local_team.json"
DEFAULT_LOG_ROOT = REPOSITORY_ROOT / "tmp" / "local" / "ollama_team"
DEFAULT_WORKER_ROOT = pathlib.Path.home() / "midi-worker"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
FORBIDDEN_CONTEXT_PARTS = {
    ".git",
    ".ssh",
    "checkpoints",
    "credentials",
    "data",
    "runs",
    "secrets",
}
FORBIDDEN_CONTEXT_NAMES = {
    ".env",
    "id_ed25519",
    "id_rsa",
    "mac_worker.json",
}
FORBIDDEN_CONTEXT_SUFFIXES = {
    ".aac",
    ".flac",
    ".keras",
    ".m4a",
    ".mp3",
    ".npz",
    ".onnx",
    ".tflite",
    ".wav",
}
BASE_SYSTEM_PROMPT = """You are an advisory local model for the Guitar MIDI AI repository.
You have no execution authority and must never claim that you edited files, ran commands,
validated a result, accessed the internet, or opened data that was not supplied. Never ask
for or expose credentials, raw datasets, model binaries, or the locked test split. Kaggle,
Colab, uploads, export, live deployment, threshold selection, and locked-test access remain
forbidden unless the user later authorizes them explicitly. Treat clean guitar, causality,
latency, leakage-safe splits, inverse validation, and source-specific regressions as first-
class constraints. Return a draft for Codex to verify with repository evidence and tests."""


class TeamError(RuntimeError):
    """Expected fail-closed error suitable for concise CLI reporting."""


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect so a loopback request cannot escape the Mac."""

    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Mapping[str, str],
        new_url: str,
    ) -> None:
        del request, file_pointer, code, message, headers, new_url
        return None


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_json(path: pathlib.Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TeamError(f"Cannot load JSON config {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise TeamError("The Ollama team config must be a JSON object.")
    return payload


def load_config(path: pathlib.Path) -> Dict[str, Any]:
    config = _load_json(path.resolve(strict=True))
    if config.get("schema_version") != 1:
        raise TeamError("Unsupported Ollama team schema_version.")
    endpoint = str(config.get("endpoint", ""))
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS:
        raise TeamError("Ollama endpoint must be loopback HTTP, never a LAN listener.")
    roles = config.get("roles")
    if not isinstance(roles, dict) or not roles:
        raise TeamError("At least one Ollama role is required.")
    for name, role in roles.items():
        if not isinstance(name, str) or not isinstance(role, dict):
            raise TeamError("Invalid role configuration.")
        if not role.get("model") or not role.get("instruction"):
            raise TeamError(f"Role {name!r} is missing model or instruction.")
    return config


def _is_relative_to(path: pathlib.Path, root: pathlib.Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_context_path(path: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve(strict=True)
    root = REPOSITORY_ROOT.resolve(strict=True)
    if not resolved.is_file() or not _is_relative_to(resolved, root):
        raise TeamError(f"Context must be a regular repository file: {path}")
    lowered_parts = {part.lower() for part in resolved.parts}
    if lowered_parts & FORBIDDEN_CONTEXT_PARTS:
        raise TeamError(f"Sensitive/generated context path is forbidden: {path}")
    lowered_name = resolved.name.lower()
    if lowered_name in FORBIDDEN_CONTEXT_NAMES:
        raise TeamError(f"Sensitive context file is forbidden: {path}")
    if any(
        "locked_test" in part.lower() or "locked-test" in part.lower()
        for part in resolved.parts
    ):
        raise TeamError(f"Locked-test context is forbidden: {path}")
    if resolved.suffix.lower() in FORBIDDEN_CONTEXT_SUFFIXES:
        raise TeamError(f"Binary/audio/model context is forbidden: {path}")
    return resolved


def read_context_files(
    paths: Iterable[pathlib.Path], maximum_bytes: int
) -> Tuple[str, List[Dict[str, Any]]]:
    blocks: List[str] = []
    evidence: List[Dict[str, Any]] = []
    consumed = 0
    for supplied in paths:
        if not supplied.is_absolute():
            supplied = REPOSITORY_ROOT / supplied
        path = validate_context_path(supplied)
        raw = path.read_bytes()
        consumed += len(raw)
        if consumed > maximum_bytes:
            raise TeamError(
                f"Context exceeds the configured {maximum_bytes}-byte limit."
            )
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise TeamError(f"Context is not UTF-8 text: {path}") from exc
        relative = path.relative_to(REPOSITORY_ROOT).as_posix()
        blocks.append(f"\n--- CONTEXT FILE: {relative} ---\n{text}")
        evidence.append(
            {"path": relative, "bytes": len(raw), "sha256": _sha256_bytes(raw)}
        )
    return "".join(blocks), evidence


def build_messages(
    role: Mapping[str, Any], prompt: str, context_text: str
) -> List[Dict[str, str]]:
    if not prompt.strip():
        raise TeamError("Prompt must not be empty.")
    system = BASE_SYSTEM_PROMPT + "\n\nROLE INSTRUCTION:\n" + str(role["instruction"])
    user = prompt.strip() + context_text
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


class OllamaClient:
    def __init__(self, endpoint: str, timeout_seconds: int = 1800) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.timeout_seconds = timeout_seconds
        parsed = urllib.parse.urlparse(self.endpoint)
        if parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS:
            raise TeamError("Ollama endpoint must remain loopback HTTP.")
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            NoRedirectHandler(),
        )

    def request(self, path: str, payload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        data = None
        headers: Dict[str, str] = {}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.endpoint + path, data=data, headers=headers)
        try:
            with self.opener.open(request, timeout=self.timeout_seconds) as reply:
                final_url = urllib.parse.urlparse(reply.geturl())
                if final_url.scheme != "http" or final_url.hostname not in LOOPBACK_HOSTS:
                    raise TeamError("Ollama response escaped the loopback endpoint.")
                response = json.load(reply)
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise TeamError(f"Ollama request failed for {path}: {exc}") from exc
        if not isinstance(response, dict):
            raise TeamError(f"Ollama returned an invalid response for {path}.")
        return response

    def installed_models(self) -> List[str]:
        result = self.request("/api/tags")
        return sorted(
            str(item.get("name"))
            for item in result.get("models", [])
            if isinstance(item, dict) and item.get("name")
        )

    def running_models(self) -> List[Dict[str, Any]]:
        result = self.request("/api/ps")
        return [item for item in result.get("models", []) if isinstance(item, dict)]

    def chat(
        self,
        model: str,
        messages: Sequence[Mapping[str, str]],
        *,
        context_tokens: int,
        maximum_output_tokens: int,
        temperature: float,
        seed: int = 42,
        keep_alive: Any = 0,
    ) -> Dict[str, Any]:
        return self.request(
            "/api/chat",
            {
                "model": model,
                "messages": list(messages),
                "stream": False,
                "think": False,
                "keep_alive": keep_alive,
                "options": {
                    "num_ctx": context_tokens,
                    "num_predict": maximum_output_tokens,
                    "temperature": temperature,
                    "seed": seed,
                },
            },
        )

    def generate_benchmark(
        self,
        model: str,
        prompt: str,
        benchmark: Mapping[str, Any],
    ) -> Dict[str, Any]:
        return self.request(
            "/api/generate",
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                # Keep the model resident only long enough to measure memory;
                # run_benchmark() unloads and verifies it in its finally block.
                "keep_alive": "30s",
                "options": {
                    "num_ctx": int(benchmark["context_tokens"]),
                    "num_predict": int(benchmark["maximum_output_tokens"]),
                    "temperature": float(benchmark["temperature"]),
                    "seed": int(benchmark["seed"]),
                },
            },
        )

    def unload(self, model: str) -> None:
        self.request("/api/generate", {"model": model, "keep_alive": 0})

    def unload_and_wait(
        self,
        model: str,
        *,
        timeout_seconds: float = 30.0,
        poll_seconds: float = 0.25,
    ) -> None:
        """Unload a model and prove that it is absent before releasing the lock."""
        self.unload(model)
        deadline = time.monotonic() + timeout_seconds
        while True:
            running_names = {
                str(item.get("name") or item.get("model") or "")
                for item in self.running_models()
            }
            if model not in running_names:
                return
            if time.monotonic() >= deadline:
                raise TeamError(
                    f"Ollama model {model!r} remained resident after unload; "
                    "the heavy-worker lock requires manual inspection."
                )
            time.sleep(poll_seconds)


class HeavyWorkerLock:
    """Share the Mac worker's atomic lock directory."""

    def __init__(self, worker_root: pathlib.Path, label: str) -> None:
        self.worker_root = worker_root.expanduser().resolve()
        self.path = self.worker_root / "active.lock"
        self.owner_path = self.path / "ollama-team-owner.json"
        self.label = label
        self.owned = False
        self.preserved = False

    def __enter__(self) -> "HeavyWorkerLock":
        self.worker_root.mkdir(parents=True, exist_ok=True)
        try:
            self.path.mkdir()
        except FileExistsError as exc:
            raise TeamError(
                f"Heavy work is already active or requires inspection: {self.path}"
            ) from exc
        self.owned = True
        owner = {
            "kind": "ollama_team",
            "label": self.label,
            "pid": os.getpid(),
            "started_utc": _utc_now(),
        }
        try:
            self.owner_path.write_text(
                json.dumps(owner, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except OSError:
            with contextlib.suppress(OSError):
                self.path.rmdir()
            self.owned = False
            raise
        return self

    def preserve(self, reason: str) -> None:
        """Keep the lock fail-closed when resource cleanup cannot be proven."""
        if not self.owned:
            return
        self.preserved = True
        owner = {
            "kind": "ollama_team_cleanup_failed",
            "label": self.label,
            "pid": os.getpid(),
            "requires_manual_inspection": True,
            "cleanup_error": reason,
            "updated_utc": _utc_now(),
        }
        with contextlib.suppress(OSError):
            self.owner_path.write_text(
                json.dumps(owner, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if not self.owned:
            return
        if self.preserved:
            self.owned = False
            return
        with contextlib.suppress(FileNotFoundError):
            self.owner_path.unlink()
        with contextlib.suppress(OSError):
            self.path.rmdir()
        self.owned = False


def _duration_seconds(payload: Mapping[str, Any], field: str) -> float:
    return round(int(payload.get(field) or 0) / 1_000_000_000, 3)


def _rate(count: int, duration_ns: int) -> Optional[float]:
    if not duration_ns:
        return None
    return round(count / (duration_ns / 1_000_000_000), 2)


def extract_metrics(payload: Mapping[str, Any], wall_seconds: float) -> Dict[str, Any]:
    prompt_count = int(payload.get("prompt_eval_count") or 0)
    prompt_duration = int(payload.get("prompt_eval_duration") or 0)
    eval_count = int(payload.get("eval_count") or 0)
    eval_duration = int(payload.get("eval_duration") or 0)
    return {
        "wall_seconds": round(wall_seconds, 3),
        "load_seconds": _duration_seconds(payload, "load_duration"),
        "prompt_tokens": prompt_count,
        "prompt_tokens_per_second": _rate(prompt_count, prompt_duration),
        "generated_tokens": eval_count,
        "generated_tokens_per_second": _rate(eval_count, eval_duration),
        "done_reason": payload.get("done_reason"),
    }


def _git_metadata() -> Dict[str, Optional[str]]:
    def run(*arguments: str) -> Optional[str]:
        try:
            return subprocess.check_output(
                ["git", "-C", str(REPOSITORY_ROOT), *arguments],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    return {"commit": run("rev-parse", "HEAD"), "branch": run("branch", "--show-current")}


def assert_clean_git_worktree() -> None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(REPOSITORY_ROOT),
                "status",
                "--porcelain",
                "--untracked-files=all",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise TeamError(f"Cannot inspect the Git worktree: {exc}") from exc
    if result.returncode != 0:
        raise TeamError("Cannot inspect the Git worktree cleanliness.")
    if result.stdout.strip():
        raise TeamError("Ollama advisory work requires a clean Git worktree.")


def _write_report(payload: Mapping[str, Any], prefix: str, log_root: pathlib.Path) -> pathlib.Path:
    log_root.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = log_root / f"{stamp}_{prefix}.json"
    temporary = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def _decode_prompt() -> str:
    return sys.stdin.read()


def run_role(args: argparse.Namespace, config: Mapping[str, Any]) -> int:
    assert_clean_git_worktree()
    roles = config["roles"]
    if args.role not in roles:
        raise TeamError(f"Unknown role {args.role!r}; choose from {', '.join(sorted(roles))}.")
    role = roles[args.role]
    prompt = _decode_prompt()
    context_text, context_evidence = read_context_files(
        [pathlib.Path(item) for item in args.context_file],
        int(config["maximum_context_bytes"]),
    )
    messages = build_messages(role, prompt, context_text)
    client = OllamaClient(str(config["endpoint"]), timeout_seconds=args.timeout_seconds)
    model = str(role["model"])
    installed = client.installed_models()
    if model not in installed:
        raise TeamError(f"Required model {model!r} is not installed; no automatic pull is allowed.")
    worker_root = pathlib.Path(os.environ.get("MIDI_MAC_WORKER_ROOT", str(DEFAULT_WORKER_ROOT)))
    with HeavyWorkerLock(worker_root, f"ollama:{args.role}:{model}") as lock:
        try:
            started = time.perf_counter()
            result = client.chat(
                model,
                messages,
                context_tokens=int(config["default_context_tokens"]),
                maximum_output_tokens=int(role["maximum_output_tokens"]),
                temperature=float(role["temperature"]),
                keep_alive=0,
            )
            wall_seconds = time.perf_counter() - started
        finally:
            try:
                client.unload_and_wait(model)
            except BaseException as cleanup_error:
                lock.preserve(str(cleanup_error))
                raise
    message = result.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise TeamError("Ollama chat response is missing message.content.")
    response = str(message["content"]).strip()
    report: Dict[str, Any] = {
        "schema_version": 1,
        "kind": "ollama_team_run",
        "created_utc": _utc_now(),
        "role": args.role,
        "model": model,
        "prompt_sha256": _sha256_bytes(prompt.encode("utf-8")),
        "context": context_evidence,
        "response": response,
        "response_sha256": _sha256_bytes(response.encode("utf-8")),
        "response_characters": len(response),
        "metrics": extract_metrics(result, wall_seconds),
        "git": _git_metadata(),
        "locked_test_used": False,
        "advisory_only": True,
    }
    if not args.no_log:
        persisted_report = dict(report)
        persisted_report.pop("response")
        report_path = _write_report(
            persisted_report,
            f"{args.role}_{model.replace(':', '-')}",
            args.log_root,
        )
        report["report_path"] = str(report_path)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(response)
        print(
            "OLLAMA_METRICS " + json.dumps(report["metrics"], sort_keys=True),
            file=sys.stderr,
        )
    return 0


BENCHMARK_PROMPT = (
    "In at most 80 words, propose a rigorous validation-only method to diagnose "
    "harmonic false NoteOn events in a causal guitar-to-MIDI decoder. Do not use "
    "the locked test split."
)


def run_benchmark(args: argparse.Namespace, config: Mapping[str, Any]) -> int:
    assert_clean_git_worktree()
    benchmark = config.get("benchmark")
    if not isinstance(benchmark, dict):
        raise TeamError("Benchmark configuration is missing.")
    models = list(args.model or benchmark.get("models", []))
    if not models:
        raise TeamError("No benchmark models configured.")
    client = OllamaClient(str(config["endpoint"]), timeout_seconds=args.timeout_seconds)
    installed = set(client.installed_models())
    missing = [model for model in models if model not in installed]
    if missing:
        raise TeamError("Missing models; automatic pull is forbidden: " + ", ".join(missing))
    records: List[Dict[str, Any]] = []
    worker_root = pathlib.Path(os.environ.get("MIDI_MAC_WORKER_ROOT", str(DEFAULT_WORKER_ROOT)))
    with HeavyWorkerLock(worker_root, "ollama:benchmark") as lock:
        for model in models:
            try:
                started = time.perf_counter()
                result = client.generate_benchmark(model, BENCHMARK_PROMPT, benchmark)
                wall_seconds = time.perf_counter() - started
                running = next(
                    (item for item in client.running_models() if item.get("name") == model),
                    {},
                )
                response = str(result.get("response") or "").strip()
                record = {
                    "model": model,
                    "metrics": extract_metrics(result, wall_seconds),
                    "resident_gb": round(int(running.get("size") or 0) / 1024**3, 2),
                    "vram_gb": round(int(running.get("size_vram") or 0) / 1024**3, 2),
                    "response_sha256": _sha256_bytes(response.encode("utf-8")),
                    "response_characters": len(response),
                }
                records.append(record)
            finally:
                try:
                    client.unload_and_wait(model)
                except BaseException as cleanup_error:
                    lock.preserve(str(cleanup_error))
                    raise
    report = {
        "schema_version": 1,
        "kind": "ollama_team_benchmark",
        "created_utc": _utc_now(),
        "prompt_sha256": _sha256_bytes(BENCHMARK_PROMPT.encode("utf-8")),
        "results": records,
        "git": _git_metadata(),
        "locked_test_used": False,
    }
    report_path = _write_report(report, "benchmark", args.log_root)
    report["report_path"] = str(report_path)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def show_models(args: argparse.Namespace, config: Mapping[str, Any]) -> int:
    client = OllamaClient(str(config["endpoint"]), timeout_seconds=args.timeout_seconds)
    print(json.dumps({"installed": client.installed_models()}, indent=2))
    return 0


def show_status(args: argparse.Namespace, config: Mapping[str, Any]) -> int:
    client = OllamaClient(str(config["endpoint"]), timeout_seconds=args.timeout_seconds)
    worker_root = pathlib.Path(os.environ.get("MIDI_MAC_WORKER_ROOT", str(DEFAULT_WORKER_ROOT))).expanduser()
    lock_path = worker_root / "active.lock"
    owner_path = lock_path / "ollama-team-owner.json"
    owner: Optional[Mapping[str, Any]] = None
    if owner_path.is_file():
        with contextlib.suppress(OSError, json.JSONDecodeError):
            owner = json.loads(owner_path.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "active_lock": lock_path.exists(),
                "ollama_owner": owner,
                "running_models": client.running_models(),
            },
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=pathlib.Path, default=DEFAULT_CONFIG)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--log-root", type=pathlib.Path, default=DEFAULT_LOG_ROOT)
    subparsers = parser.add_subparsers(dest="action", required=True)

    run_parser = subparsers.add_parser("run", help="Run one advisory role.")
    run_parser.add_argument("--role", required=True)
    run_parser.add_argument("--context-file", action="append", default=[])
    run_parser.add_argument("--json", action="store_true")
    run_parser.add_argument("--no-log", action="store_true")

    benchmark_parser = subparsers.add_parser(
        "benchmark", help="Benchmark configured models sequentially."
    )
    benchmark_parser.add_argument("--model", action="append")

    subparsers.add_parser("models", help="List installed Ollama models.")
    subparsers.add_parser("status", help="Show loaded models and shared lock state.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    def terminate(signum: int, frame: Any) -> None:
        del frame
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, terminate)
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.timeout_seconds < 1 or args.timeout_seconds > 7200:
        parser.error("--timeout-seconds must be between 1 and 7200.")
    config = load_config(args.config)
    action = {
        "run": run_role,
        "benchmark": run_benchmark,
        "models": show_models,
        "status": show_status,
    }[args.action]
    return action(args, config)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TeamError as error:
        print(f"OLLAMA_TEAM_ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
