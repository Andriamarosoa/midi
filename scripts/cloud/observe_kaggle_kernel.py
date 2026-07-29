"""Observe one Kaggle kernel without ever submitting or restarting it.

The observer uses the official Kaggle CLI as a read-only control plane.  It
records the exact provider status and quota in an atomic JSON state file.
Execution logs and a small allow-list of output artifacts are downloaded only
after the kernel reaches a terminal COMPLETE or failure state.

Authentication remains entirely owned by the Kaggle CLI environment.  This
module never reads, prints, serializes, or passes credential values as command
line arguments.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
HANDLE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*/[A-Za-z0-9][A-Za-z0-9_-]*$")
STATUS_PATTERN = re.compile(r'has status\s+"([^"]+)"', re.IGNORECASE)
TOKEN_PATTERN = re.compile(r"\bKGAT[A-Za-z0-9._~-]+\b")

COMPLETE_STATUSES = {"complete", "completed", "success", "succeeded"}
FAILURE_STATUSES = {
    "error",
    "failed",
    "failure",
    "cancelled",
    "canceled",
    "cancelacknowledged",
}

DEFAULT_OUTPUT_PATTERNS = (
    r"(?:^|/)output_manifest\.json$",
    r"(?:^|/)(?:batch_progress|cloud_pipeline|recovery_state|"
    r"training_status)\.json$",
    r"(?:^|/)history\.csv$",
    r"\.(?:log|txt)$",
    r"\.(?:tar|tar\.gz|tgz|zip)$",
)


class KaggleCliError(RuntimeError):
    """A sanitized Kaggle CLI failure."""


@dataclass(frozen=True)
class KernelStatus:
    """Exact and normalized forms of a Kaggle kernel status."""

    raw: str
    canonical: str
    terminal: bool
    outcome: str | None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact_secrets(text: str) -> str:
    redacted = TOKEN_PATTERN.sub("<redacted>", text)
    for name in (
        "KAGGLE_API_TOKEN",
        "KAGGLE_KEY",
        "KAGGLE_MCP_TOKEN",
    ):
        value = os.environ.get(name)
        if value and len(value) >= 8:
            redacted = redacted.replace(value, "<redacted>")
    return redacted


def _validate_handle(handle: str) -> str:
    if not HANDLE_PATTERN.fullmatch(handle):
        raise ValueError(
            "Kernel handle must have the exact OWNER/SLUG form."
        )
    return handle


def _resolve_kaggle_cli(explicit: str | None = None) -> str:
    candidates: list[Path | str | None] = [
        explicit,
        os.environ.get("KAGGLE_CLI"),
        ROOT / ".venv-kaggle/Scripts/kaggle.exe",
        ROOT / ".venv-kaggle/bin/kaggle",
        Path(sys.executable).with_name("kaggle.exe"),
        Path(sys.executable).with_name("kaggle"),
        shutil.which("kaggle"),
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        path = Path(candidate).expanduser()
        if path.is_file():
            return str(path.resolve())
    raise FileNotFoundError(
        "Kaggle CLI introuvable. Installez-le dans .venv-kaggle ou "
        "utilisez --kaggle-cli."
    )


def _run_cli(
    cli: str,
    arguments: Sequence[str],
    *,
    timeout_seconds: float,
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    # The Kaggle CLI may emit Unicode notebook logs.  Force UTF-8 explicitly
    # because a redirected Windows process otherwise inherits a legacy code
    # page and can crash while printing a perfectly valid session log.
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [cli, *arguments],
        cwd=ROOT,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout_seconds,
    )
    if result.returncode:
        detail = _redact_secrets(
            "\n".join(part for part in (result.stdout, result.stderr) if part)
        ).strip()
        raise KaggleCliError(
            f"Kaggle CLI failed ({result.returncode}) for "
            f"{' '.join(arguments[:2])}: {detail or 'no diagnostic'}"
        )
    return result


def parse_kernel_status(output: str) -> KernelStatus:
    """Parse the exact CLI enum while exposing a stable terminal outcome."""

    match = STATUS_PATTERN.search(output)
    if match is None:
        raise ValueError(
            f"Unrecognized Kaggle kernel status: {_redact_secrets(output)!r}"
        )
    raw = match.group(1).strip()
    canonical = raw.rsplit(".", 1)[-1].strip().lower()
    if canonical in COMPLETE_STATUSES:
        return KernelStatus(raw, canonical, True, "complete")
    if canonical in FAILURE_STATUSES:
        return KernelStatus(raw, canonical, True, "error")
    return KernelStatus(raw, canonical, False, None)


def query_kernel_status(
    cli: str,
    handle: str,
    *,
    timeout_seconds: float,
) -> KernelStatus:
    result = _run_cli(
        cli,
        ("kernels", "status", handle),
        timeout_seconds=timeout_seconds,
    )
    return parse_kernel_status(result.stdout + "\n" + result.stderr)


def _decode_json_payload(output: str) -> Any:
    decoder = json.JSONDecoder()
    for index, character in enumerate(output):
        if character not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(output[index:])
        except json.JSONDecodeError:
            continue
        return value
    raise ValueError(
        f"Kaggle CLI returned no JSON payload: {_redact_secrets(output)!r}"
    )


def parse_quota(output: str) -> list[dict[str, Any]]:
    """Keep provider quota values verbatim instead of estimating them."""

    payload = _decode_json_payload(output)
    if isinstance(payload, dict):
        payload = payload.get("items", payload.get("resources"))
    if not isinstance(payload, list):
        raise ValueError("Kaggle quota JSON must be a list.")
    quota: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict) or not item.get("resource"):
            raise ValueError("Kaggle quota item is malformed.")
        quota.append({
            key: item.get(key)
            for key in ("resource", "used", "remaining", "total", "refreshAt")
        })
    return quota


def query_quota(
    cli: str,
    *,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    result = _run_cli(
        cli,
        ("quota", "--format", "json"),
        timeout_seconds=timeout_seconds,
    )
    return parse_quota(result.stdout)


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _load_state(path: Path, handle: str) -> dict[str, Any]:
    if not path.is_file():
        return {
            "schema_version": 1,
            "kernel": handle,
            "started_at_utc": _utc_now(),
            "no_automatic_relaunch": True,
            "poll_count": 0,
        }
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError(f"Observer state is not a JSON object: {path}")
    if state.get("kernel") != handle:
        raise ValueError(
            f"Observer state belongs to {state.get('kernel')!r}, not {handle!r}."
        )
    return state


def parse_output_listing(output: str) -> list[dict[str, Any]]:
    payload = _decode_json_payload(output)
    if isinstance(payload, dict):
        payload = payload.get("items", payload.get("files"))
    if not isinstance(payload, list):
        raise ValueError("Kaggle output listing JSON must be a list.")
    files: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name or Path(name).is_absolute():
            continue
        normalized = Path(name.replace("\\", "/"))
        if ".." in normalized.parts:
            continue
        files.append({
            "name": normalized.as_posix(),
            "size": item.get("size"),
            "creationDate": item.get("creationDate"),
        })
    return files


def list_kernel_outputs(
    cli: str,
    handle: str,
    *,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    result = _run_cli(
        cli,
        (
            "kernels",
            "files",
            handle,
            "--format",
            "json",
            "--page-size",
            "200",
        ),
        timeout_seconds=timeout_seconds,
    )
    return parse_output_listing(result.stdout)


def select_output_names(
    listing: Iterable[dict[str, Any]],
    patterns: Sequence[str],
) -> list[str]:
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    return sorted({
        str(item["name"])
        for item in listing
        if isinstance(item.get("name"), str)
        and any(pattern.search(str(item["name"])) for pattern in compiled)
    })


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def download_execution_log(
    cli: str,
    handle: str,
    destination: Path,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    if destination.is_file():
        return {
            "path": str(destination),
            "bytes": destination.stat().st_size,
            "sha256": _sha256(destination),
            "reused": True,
        }
    result = _run_cli(
        cli,
        ("kernels", "logs", handle),
        timeout_seconds=timeout_seconds,
    )
    text = result.stdout
    if result.stderr:
        text += "\n--- kaggle-cli stderr ---\n" + result.stderr
    _atomic_write_text(destination, _redact_secrets(text))
    return {
        "path": str(destination),
        "bytes": destination.stat().st_size,
        "sha256": _sha256(destination),
        "reused": False,
    }


def _merge_download_tree(
    staging: Path,
    destination: Path,
    expected_names: Sequence[str],
) -> list[dict[str, Any]]:
    downloaded: list[dict[str, Any]] = []
    for source in sorted(path for path in staging.rglob("*") if path.is_file()):
        relative = source.relative_to(staging)
        relative_name = relative.as_posix()
        if not any(
            relative_name == name or relative_name.endswith("/" + name)
            for name in expected_names
        ):
            # ``kaggle kernels output`` currently adds a session .log even
            # when --file-pattern excludes it.  The dedicated logs command
            # already captured that evidence, so do not retain this surprise
            # file as a selected output.
            source.unlink()
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        source_hash = _sha256(source)
        if target.is_file():
            if _sha256(target) != source_hash:
                raise FileExistsError(
                    f"Refusing to overwrite different output file: {target}"
                )
            source.unlink()
            reused = True
        else:
            os.replace(source, target)
            reused = False
        downloaded.append({
            "name": relative.as_posix(),
            "path": str(target),
            "bytes": target.stat().st_size,
            "sha256": source_hash,
            "reused": reused,
        })
    return downloaded


def download_selected_outputs(
    cli: str,
    handle: str,
    output_dir: Path,
    names: Sequence[str],
    *,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    if not names:
        return []
    output_dir.mkdir(parents=True, exist_ok=True)
    exact_pattern = (
        r"(?:^|/)(?:" + "|".join(re.escape(name) for name in names) + r")$"
    )
    staging = Path(tempfile.mkdtemp(prefix=".observer-download-", dir=output_dir))
    try:
        _run_cli(
            cli,
            (
                "kernels",
                "output",
                handle,
                "--path",
                str(staging),
                "--force",
                "--quiet",
                "--file-pattern",
                exact_pattern,
                "--page-size",
                "200",
            ),
            timeout_seconds=timeout_seconds,
        )
        return _merge_download_tree(staging, output_dir, names)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _terminal_artifacts(
    *,
    cli: str,
    handle: str,
    status: KernelStatus,
    output_dir: Path,
    patterns: Sequence[str],
    timeout_seconds: float,
) -> dict[str, Any]:
    if not status.terminal or status.outcome not in {"complete", "error"}:
        raise ValueError("Artifacts may only be fetched after terminal status.")
    log = download_execution_log(
        cli,
        handle,
        output_dir / "kernel_execution.log",
        timeout_seconds=timeout_seconds,
    )
    listing = list_kernel_outputs(
        cli,
        handle,
        timeout_seconds=timeout_seconds,
    )
    selected_names = select_output_names(listing, patterns)
    outputs = download_selected_outputs(
        cli,
        handle,
        output_dir,
        selected_names,
        timeout_seconds=timeout_seconds,
    )
    return {
        "completed_at_utc": _utc_now(),
        "execution_log": log,
        "available_outputs": listing,
        "selected_output_names": selected_names,
        "outputs": outputs,
    }


def observe_once(
    *,
    cli: str,
    handle: str,
    state_path: Path,
    output_dir: Path,
    patterns: Sequence[str] = DEFAULT_OUTPUT_PATTERNS,
    timeout_seconds: float = 120.0,
) -> tuple[dict[str, Any], KernelStatus]:
    """Poll one kernel and perform one idempotent terminal artifact fetch."""

    handle = _validate_handle(handle)
    state = _load_state(state_path, handle)
    status = query_kernel_status(
        cli,
        handle,
        timeout_seconds=timeout_seconds,
    )
    checked_at = _utc_now()
    try:
        quota = query_quota(cli, timeout_seconds=timeout_seconds)
        quota_error = None
    except (KaggleCliError, ValueError) as error:
        quota = state.get("quota")
        quota_error = _redact_secrets(str(error))

    previous_raw = state.get("status_raw")
    state.update({
        "updated_at_utc": checked_at,
        "last_poll_at_utc": checked_at,
        "poll_count": int(state.get("poll_count", 0)) + 1,
        "status_raw": status.raw,
        "status": status.canonical,
        "terminal": status.terminal,
        "outcome": status.outcome,
        "quota": quota,
        "quota_checked_at_utc": checked_at,
        "quota_error": quota_error,
    })
    if previous_raw != status.raw:
        state["previous_status_raw"] = previous_raw
        state["status_changed_at_utc"] = checked_at
    _atomic_write_json(state_path, state)

    if status.terminal and not state.get("terminal_artifacts"):
        state["artifact_download_started_at_utc"] = _utc_now()
        _atomic_write_json(state_path, state)
        try:
            artifacts = _terminal_artifacts(
                cli=cli,
                handle=handle,
                status=status,
                output_dir=output_dir,
                patterns=patterns,
                timeout_seconds=timeout_seconds,
            )
        except Exception as error:
            state["artifact_download_failed_at_utc"] = _utc_now()
            state["artifact_download_error"] = _redact_secrets(str(error))
            state["updated_at_utc"] = _utc_now()
            _atomic_write_json(state_path, state)
            raise
        state["terminal_artifacts"] = artifacts
        state["updated_at_utc"] = _utc_now()
        state.pop("artifact_download_error", None)
        state.pop("artifact_download_failed_at_utc", None)
        _atomic_write_json(state_path, state)
    return state, status


def _public_event(
    state: dict[str, Any],
    *,
    event: str,
    error: str | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "event": event,
        "checked_at_utc": state.get("last_poll_at_utc", _utc_now()),
        "kernel": state.get("kernel"),
        "status_raw": state.get("status_raw"),
        "status": state.get("status"),
        "terminal": state.get("terminal"),
        "quota": state.get("quota"),
    }
    if error:
        value["error"] = _redact_secrets(error)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", required=True, help="Exact OWNER/SLUG handle.")
    parser.add_argument("--kaggle-cli", help="Explicit Kaggle CLI executable.")
    parser.add_argument("--state", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--interval-seconds", type=float, default=300.0)
    parser.add_argument("--command-timeout-seconds", type=float, default=120.0)
    parser.add_argument(
        "--maximum-wait-seconds",
        type=float,
        default=0.0,
        help="Zero waits indefinitely; this never launches or restarts a kernel.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Perform exactly one status/quota poll.",
    )
    parser.add_argument(
        "--output-pattern",
        action="append",
        default=[],
        help="Additional regex selecting terminal output files.",
    )
    args = parser.parse_args()

    handle = _validate_handle(args.kernel)
    slug = handle.replace("/", "--")
    state_path = (
        args.state
        if args.state is not None
        else ROOT / "tmp/kaggle/observers" / f"{slug}.json"
    ).resolve()
    output_dir = (
        args.output_dir
        if args.output_dir is not None
        else ROOT / "tmp/kaggle/results" / slug
    ).resolve()
    cli = _resolve_kaggle_cli(args.kaggle_cli)
    patterns = (*DEFAULT_OUTPUT_PATTERNS, *args.output_pattern)
    started = time.monotonic()
    previous_raw: str | None = None

    while True:
        try:
            state, status = observe_once(
                cli=cli,
                handle=handle,
                state_path=state_path,
                output_dir=output_dir,
                patterns=patterns,
                timeout_seconds=args.command_timeout_seconds,
            )
        except KeyboardInterrupt:
            state = _load_state(state_path, handle)
            state["observer_interrupted_at_utc"] = _utc_now()
            _atomic_write_json(state_path, state)
            return 130
        except Exception as error:
            state = _load_state(state_path, handle)
            state["updated_at_utc"] = _utc_now()
            state["last_observer_error"] = _redact_secrets(str(error))
            _atomic_write_json(state_path, state)
            print(
                json.dumps(
                    _public_event(
                        state,
                        event="observer_error",
                        error=str(error),
                    ),
                    ensure_ascii=False,
                ),
                flush=True,
            )
            if args.once:
                return 2
        else:
            if previous_raw != status.raw or status.terminal or args.once:
                print(
                    json.dumps(
                        _public_event(state, event="kernel_observation"),
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
            previous_raw = status.raw
            if status.terminal:
                return 0 if status.outcome == "complete" else 2
            if args.once:
                return 0

        if (
            args.maximum_wait_seconds > 0
            and time.monotonic() - started >= args.maximum_wait_seconds
        ):
            state = _load_state(state_path, handle)
            state["observer_timeout_at_utc"] = _utc_now()
            _atomic_write_json(state_path, state)
            return 3
        time.sleep(max(1.0, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
