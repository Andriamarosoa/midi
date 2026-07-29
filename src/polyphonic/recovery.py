"""Crash-safe A/B recovery checkpoints for long Keras training runs.

The recovery directory contains two alternating native Keras archives and
their JSON state files.  A model archive is replaced before its state file.
Consequently, an interruption during a save can invalidate at most the slot
being written; the other slot remains available as a fallback.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = 1
SLOTS = ("a", "b")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class RecoveryError(RuntimeError):
    """Base class for recovery checkpoint failures."""


class RecoveryIntegrityError(RecoveryError):
    """Raised when recovery files exist but none can be trusted."""


class RecoverySignatureMismatch(RecoveryError):
    """Raised when a checkpoint belongs to a different training plan."""


@dataclass(frozen=True)
class RecoverySignatures:
    """Immutable identities required for an exact training resume."""

    plan_sha256: str
    config_sha256: str
    manifest_sha256: str
    commit: str

    def __post_init__(self) -> None:
        for name in ("plan_sha256", "config_sha256", "manifest_sha256"):
            value = str(getattr(self, name)).lower()
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
            object.__setattr__(self, name, value)
        if not str(self.commit).strip():
            raise ValueError("commit must not be empty.")
        object.__setattr__(self, "commit", str(self.commit).strip())

    def as_dict(self) -> dict[str, str]:
        return {
            "plan_sha256": self.plan_sha256,
            "config_sha256": self.config_sha256,
            "manifest_sha256": self.manifest_sha256,
            "commit": self.commit,
        }


@dataclass(frozen=True)
class RecoverySnapshot:
    """A saved or restored recovery generation."""

    model: Any
    state: dict[str, Any]
    model_path: Path
    state_path: Path
    slot: str


def file_sha256(path: str | Path, *, chunk_bytes: int = 1024 * 1024) -> str:
    """Return the SHA-256 digest of *path* without loading it all in memory."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_bytes):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    """Write JSON through a flushed sibling file followed by ``os.replace``."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(
                dict(payload),
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, destination)
        temporary_path = None
        _fsync_directory(destination.parent)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def save_recovery_checkpoint(
    directory: str | Path,
    model: Any,
    *,
    epoch: int,
    next_batch: int,
    signatures: RecoverySignatures,
    callback_state: Mapping[str, Any] | None = None,
) -> RecoverySnapshot:
    """Save a compiled model and exact resume state into the next A/B slot.

    Existing parseable state from another training identity is rejected.  The
    native ``.keras`` format persists model, optimizer, and optimizer slots.
    """

    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    epoch = _non_negative_integer("epoch", epoch)
    next_batch = _non_negative_integer("next_batch", next_batch)
    optimizer_iterations = _optimizer_iterations(model)
    learning_rate = _optimizer_learning_rate(model)
    normalized_callback_state = _json_mapping(
        "callback_state", callback_state or {}
    )

    existing_states = _parse_existing_states(root)
    for _, state, _ in existing_states:
        actual = _state_signatures(state)
        if actual != signatures:
            raise RecoverySignatureMismatch(
                "Recovery directory contains an incompatible training "
                f"identity: {_signature_difference(signatures, actual)}"
            )

    generation = max(
        (int(state["generation"]) for _, state, _ in existing_states),
        default=0,
    ) + 1
    slot = _next_save_slot(root, existing_states)
    model_path = _model_path(root, slot)
    state_path = _state_path(root, slot)

    _atomic_save_model(model, model_path)
    model_digest = file_sha256(model_path)
    state: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "slot": slot,
        "generation": generation,
        "epoch": epoch,
        "next_batch": next_batch,
        "optimizer_iterations": optimizer_iterations,
        "learning_rate": learning_rate,
        **signatures.as_dict(),
        "callback_state": normalized_callback_state,
        "locked_test_used": False,
        "model_filename": model_path.name,
        "model_sha256": model_digest,
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write_json(state_path, state)
    return RecoverySnapshot(
        model=model,
        state=state,
        model_path=model_path,
        state_path=state_path,
        slot=slot,
    )


def load_latest_recovery_checkpoint(
    directory: str | Path,
    *,
    signatures: RecoverySignatures,
    custom_objects: Mapping[str, Any] | None = None,
) -> RecoverySnapshot | None:
    """Load the newest intact compatible generation with ``compile=True``.

    Missing recovery files return ``None``.  Corrupt or incomplete newest
    generations fall back to the other slot.  A valid archive carrying an
    incompatible signature is refused instead of being silently skipped.
    """

    root = Path(directory)
    state_files = [_state_path(root, slot) for slot in SLOTS]
    if not any(path.exists() for path in state_files):
        return None

    parsed = _parse_existing_states(root)
    if not parsed:
        raise RecoveryIntegrityError(
            f"Recovery state exists in {root}, but no state file is valid."
        )
    generations = [int(state["generation"]) for _, state, _ in parsed]
    if len(generations) != len(set(generations)):
        raise RecoveryIntegrityError(
            "Recovery slots contain an ambiguous duplicate generation."
        )

    failures: list[str] = []
    for slot, state, state_path in sorted(
        parsed, key=lambda item: int(item[1]["generation"]), reverse=True
    ):
        model_path = _model_path(root, slot)
        if state["model_filename"] != model_path.name:
            failures.append(f"generation {state['generation']}: bad filename")
            continue
        if not model_path.is_file():
            failures.append(f"generation {state['generation']}: model missing")
            continue
        if file_sha256(model_path) != state["model_sha256"]:
            failures.append(
                f"generation {state['generation']}: SHA-256 mismatch"
            )
            continue

        actual = _state_signatures(state)
        if actual != signatures:
            raise RecoverySignatureMismatch(
                f"Newest intact recovery generation {state['generation']} "
                "has an incompatible training identity: "
                f"{_signature_difference(signatures, actual)}"
            )

        try:
            import tensorflow as tf

            model = tf.keras.models.load_model(
                model_path,
                custom_objects=(
                    None if custom_objects is None else dict(custom_objects)
                ),
                compile=True,
            )
            restored_iterations = _optimizer_iterations(model)
            restored_learning_rate = _optimizer_learning_rate(model)
        except Exception as error:  # A damaged archive must permit A/B fallback.
            failures.append(
                f"generation {state['generation']}: "
                f"{type(error).__name__}: {error}"
            )
            continue
        if restored_iterations != int(state["optimizer_iterations"]):
            failures.append(
                f"generation {state['generation']}: optimizer iterations "
                f"{restored_iterations} != {state['optimizer_iterations']}"
            )
            continue
        if not math.isclose(
            restored_learning_rate,
            float(state["learning_rate"]),
            rel_tol=1e-7,
            abs_tol=1e-12,
        ):
            failures.append(
                f"generation {state['generation']}: learning rate "
                f"{restored_learning_rate} != {state['learning_rate']}"
            )
            continue

        return RecoverySnapshot(
            model=model,
            state=state,
            model_path=model_path,
            state_path=state_path,
            slot=slot,
        )

    detail = "; ".join(failures) if failures else "no intact generation"
    raise RecoveryIntegrityError(
        f"No valid recovery checkpoint remains in {root}: {detail}"
    )


def _atomic_save_model(model: Any, destination: Path) -> None:
    if getattr(model, "optimizer", None) is None:
        raise ValueError("Recovery requires a compiled Keras model.")
    temporary = destination.with_name(
        f".{destination.stem}.{os.getpid()}.{os.urandom(8).hex()}.keras"
    )
    try:
        model.save(temporary)
        # Windows requires a writable descriptor for ``fsync``.
        with temporary.open("r+b") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        _fsync_directory(destination.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _parse_existing_states(
    root: Path,
) -> list[tuple[str, dict[str, Any], Path]]:
    parsed: list[tuple[str, dict[str, Any], Path]] = []
    for slot in SLOTS:
        state_path = _state_path(root, slot)
        if not state_path.is_file():
            continue
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            state = _validate_state(payload, expected_slot=slot)
        except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
            continue
        parsed.append((slot, state, state_path))
    return parsed


def _validate_state(payload: Any, *, expected_slot: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Recovery state must be a JSON object.")
    state = dict(payload)
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported recovery schema.")
    if state.get("slot") != expected_slot:
        raise ValueError("Recovery state slot mismatch.")
    for name in (
        "generation",
        "epoch",
        "next_batch",
        "optimizer_iterations",
    ):
        state[name] = _non_negative_integer(name, state.get(name))
    if state["generation"] < 1:
        raise ValueError("generation must be at least 1.")
    learning_rate = state.get("learning_rate")
    if isinstance(learning_rate, bool):
        raise ValueError("learning_rate must be finite.")
    try:
        state["learning_rate"] = float(learning_rate)
    except (TypeError, ValueError) as error:
        raise ValueError("learning_rate must be finite.") from error
    if not math.isfinite(state["learning_rate"]):
        raise ValueError("learning_rate must be finite.")
    _state_signatures(state)
    if not isinstance(state.get("callback_state"), dict):
        raise ValueError("callback_state must be a JSON object.")
    if state.get("locked_test_used") is not False:
        raise ValueError("A recovery state must exclude the locked test.")
    model_filename = state.get("model_filename")
    if model_filename != _model_path(Path("."), expected_slot).name:
        raise ValueError("Unexpected recovery model filename.")
    model_sha256 = str(state.get("model_sha256", "")).lower()
    if _SHA256_PATTERN.fullmatch(model_sha256) is None:
        raise ValueError("model_sha256 must be a SHA-256 digest.")
    state["model_sha256"] = model_sha256
    return state


def _state_signatures(state: Mapping[str, Any]) -> RecoverySignatures:
    return RecoverySignatures(
        plan_sha256=str(state.get("plan_sha256", "")),
        config_sha256=str(state.get("config_sha256", "")),
        manifest_sha256=str(state.get("manifest_sha256", "")),
        commit=str(state.get("commit", "")),
    )


def _signature_difference(
    expected: RecoverySignatures, actual: RecoverySignatures
) -> str:
    differences = [
        name
        for name in (
            "plan_sha256",
            "config_sha256",
            "manifest_sha256",
            "commit",
        )
        if getattr(expected, name) != getattr(actual, name)
    ]
    return ", ".join(differences) or "unknown mismatch"


def _optimizer_iterations(model: Any) -> int:
    optimizer = getattr(model, "optimizer", None)
    if optimizer is None:
        raise ValueError("Recovery requires a compiled Keras model.")
    value = getattr(optimizer, "iterations", None)
    if value is None:
        raise ValueError("The Keras optimizer has no iterations counter.")
    try:
        result = int(value.numpy())
    except (AttributeError, TypeError, ValueError):
        try:
            import tensorflow as tf

            result = int(tf.keras.backend.get_value(value))
        except Exception as error:
            raise ValueError(
                "Cannot read the Keras optimizer iterations counter."
            ) from error
    return _non_negative_integer("optimizer_iterations", result)


def _optimizer_learning_rate(model: Any) -> float:
    optimizer = getattr(model, "optimizer", None)
    if optimizer is None:
        raise ValueError("Recovery requires a compiled Keras model.")
    value = getattr(optimizer, "learning_rate", None)
    if value is None:
        raise ValueError("The Keras optimizer has no learning rate.")
    if callable(value):
        value = value(optimizer.iterations)
    try:
        value = value.numpy()
    except AttributeError:
        try:
            import tensorflow as tf

            value = tf.keras.backend.get_value(value)
        except Exception:
            pass
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("The optimizer learning rate must be finite.")
    return result


def _json_mapping(
    name: str, value: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping.")
    try:
        normalized = json.loads(
            json.dumps(dict(value), ensure_ascii=False, allow_nan=False)
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must contain only JSON values.") from error
    if not isinstance(normalized, dict):
        raise ValueError(f"{name} must be a JSON object.")
    return normalized


def _non_negative_integer(name: str, value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a non-negative integer.")
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{name} must be a non-negative integer."
        ) from error
    if result != value or result < 0:
        raise ValueError(f"{name} must be a non-negative integer.")
    return result


def _model_path(root: Path, slot: str) -> Path:
    return root / f"recovery-{slot}.keras"


def _state_path(root: Path, slot: str) -> Path:
    return root / f"recovery-{slot}.json"


def _next_save_slot(
    root: Path,
    existing_states: list[tuple[str, dict[str, Any], Path]],
) -> str:
    """Prefer an invalid slot, otherwise replace the oldest generation."""

    states_by_slot = {
        slot: state for slot, state, _ in existing_states
    }
    invalid_slots: list[str] = []
    for slot in SLOTS:
        state = states_by_slot.get(slot)
        model_path = _model_path(root, slot)
        if (
            state is None
            or not model_path.is_file()
            or file_sha256(model_path) != state["model_sha256"]
        ):
            invalid_slots.append(slot)
    if invalid_slots:
        return invalid_slots[0]
    return min(
        SLOTS, key=lambda slot: int(states_by_slot[slot]["generation"])
    )


def _fsync_directory(directory: Path) -> None:
    """Best-effort directory flush (not supported by every Windows runtime)."""

    descriptor: int | None = None
    try:
        descriptor = os.open(directory, os.O_RDONLY)
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        if descriptor is not None:
            os.close(descriptor)
