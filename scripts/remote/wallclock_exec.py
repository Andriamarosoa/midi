#!/usr/bin/env python3
"""Run one command in an isolated POSIX process group with a hard deadline."""

from __future__ import annotations

import argparse
import os
import pathlib
import signal
import subprocess
import sys
import time


def _atomic_write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _terminate_group(
    process: subprocess.Popen[bytes], grace_seconds: int
) -> bool:
    pgid = process.pid
    if _group_alive(pgid):
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError:
            # Preserve a failure result below instead of turning a cleanup
            # problem into an unhandled supervisor exception.
            pass
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        # Reap the direct child as soon as it exits. On macOS an unreaped
        # group leader can make killpg(..., 0) report the group as present and
        # a subsequent SIGKILL fail with EPERM even though no runnable member
        # remains.
        process.poll()
        if not _group_alive(pgid):
            break
        time.sleep(0.1)
    process.poll()
    if _group_alive(pgid):
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError:
            # Do not claim success: the final group probe below remains true
            # and the caller returns the evidence-preserving status 125.
            pass
    try:
        process.wait(timeout=max(1, grace_seconds))
    except subprocess.TimeoutExpired:
        # The process group has already received SIGKILL. Returning a failure
        # lets the outer runner preserve evidence instead of claiming success.
        pass
    # Give orphaned descendants a short opportunity to be reaped after the
    # group-wide signal. The direct child has already been waited above.
    disappearance_deadline = time.monotonic() + max(1, grace_seconds)
    while _group_alive(pgid) and time.monotonic() < disappearance_deadline:
        time.sleep(0.05)
    return not _group_alive(pgid)


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=int, required=True)
    parser.add_argument("--grace-seconds", type=int, default=15)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--process-state", type=pathlib.Path, required=True)
    parser.add_argument("--active-owner", type=pathlib.Path, required=True)
    parser.add_argument("--timeout-marker", type=pathlib.Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    if arguments.command[:1] == ["--"]:
        arguments.command = arguments.command[1:]
    if not arguments.command:
        parser.error("a command is required after --")
    if not 1 <= arguments.timeout_seconds <= 22200:
        parser.error("timeout must be between 1 and 22200 seconds")
    if not 1 <= arguments.grace_seconds <= 60:
        parser.error("grace must be between 1 and 60 seconds")
    if not arguments.token or any(
        character not in "0123456789abcdef" for character in arguments.token
    ):
        parser.error("token must contain lowercase hexadecimal characters")
    return arguments


def main() -> int:
    arguments = _parse_arguments()
    received_signal = 0
    process: subprocess.Popen[bytes] | None = None

    def request_stop(signum: int, _frame: object) -> None:
        nonlocal received_signal
        received_signal = signum

    # Install handlers before spawning. The exec'd command receives the normal
    # unblocked/default signal disposition, while an immediate signal to this
    # supervisor is remembered even if Popen is still returning.
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGHUP, request_stop)
    try:
        process = subprocess.Popen(arguments.command, start_new_session=True)
        started_epoch = int(time.time())
        deadline_epoch = started_epoch + arguments.timeout_seconds
        state = (
            f"job_id={arguments.job_id}\n"
            f"token={arguments.token}\n"
            f"supervisor_pid={os.getpid()}\n"
            f"child_pid={process.pid}\n"
            f"pgid={process.pid}\n"
            f"started_epoch={started_epoch}\n"
            f"deadline_epoch={deadline_epoch}\n"
        )
        # Ownership becomes externally visible only after handlers and the
        # process group both exist.
        _atomic_write(arguments.process_state, state)
        _atomic_write(arguments.active_owner, state)

        deadline = time.monotonic() + arguments.timeout_seconds
        timed_out = False
        while process.poll() is None:
            if received_signal:
                _terminate_group(process, arguments.grace_seconds)
                break
            if time.monotonic() >= deadline:
                timed_out = True
                _atomic_write(
                    arguments.timeout_marker,
                    f"reason=wall_clock_timeout\n"
                    f"timeout_seconds={arguments.timeout_seconds}\n",
                )
                _terminate_group(process, arguments.grace_seconds)
                break
            time.sleep(0.2)

        return_code = process.poll()
        if return_code is None:
            _terminate_group(process, arguments.grace_seconds)
            return_code = process.poll()
        if _group_alive(process.pid):
            _terminate_group(process, arguments.grace_seconds)
            if _group_alive(process.pid):
                return 125
        if timed_out:
            return 124
        if received_signal:
            return 128 + received_signal
        if return_code is None:
            return 125
        if return_code < 0:
            return 128 - return_code
        return int(return_code)
    except BaseException:
        # Once Popen succeeds, every supervisor failure must terminate the
        # complete owned group before propagating the error.
        if process is not None and not _terminate_group(
            process, arguments.grace_seconds
        ):
            return 125
        raise


if __name__ == "__main__":
    raise SystemExit(main())
