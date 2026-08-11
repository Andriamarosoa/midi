"""Dormant H25 P2-007 observer for the sealed secondary Mac runtime.

The module is reviewable and command-ready, but the checked-in state has no
activation or OS authorization.  Direct invocation therefore fails before
NumPy import, claim consumption, or population access.
"""
from __future__ import annotations

from dataclasses import replace
import importlib
import json
from pathlib import Path
import sys
import time
from types import MappingProxyType
from typing import Mapping, Sequence


# The sealed command executes this file directly, so make the repository
# package importable without depending on an ambient PYTHONPATH.
_REPOSITORY_ROOT = Path(__file__).resolve(strict=True).parents[2]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))


from src.polyphonic.harmonic_censoring_h25_scientific_capability import (
    ACTIVATION_RECORD,
    AUTHORIZATION_SEAL,
    _object,
    _parse,
    _require_runtime_before_numpy,
    _sha256,
    _validate_dormant_contract,
    _validate_future_transition,
    _validate_secondary_runtime_identity,
)


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _claim_marker(
    root: Path,
    contract: Mapping[str, object],
    seal: Mapping[str, object],
    head: str,
    plan: object,
) -> Mapping[str, object]:
    claim_path = root / contract["one_shot_execution"]["claim_path"]
    if claim_path.is_symlink() or not claim_path.is_file():
        raise PermissionError("H25 secondary observer requires the durable parent claim.")
    marker = _parse(claim_path.read_bytes(), "secondary observer claim")
    required = {
        "schema_version", "purpose", "claim_state", "authorization_commit",
        "activation_sha256", "seal_sha256", "capability_contract_sha256",
        "authority_source_blob", "runner_source_blob", "engine_source_blob",
        "recomputer_source_blob", "population_index_sha256",
        "population_provenance_sha256", "population_receipt_sha256",
        "administrative_qualification_sha256", "ordered_fixture_ids",
        "ordered_test_ids", "real_data_used", "H17_H23_H24_population_used",
        "locked_test_used", "model_or_training_authorized",
    }
    if set(marker) != required:
        raise ValueError("H25 secondary observer claim schema mismatch.")
    if (
        marker["claim_state"] != "CLAIMED_BEFORE_FIRST_POPULATION_WAVEFORM"
        or marker["authorization_commit"] != head
        or marker["seal_sha256"] != _sha256((root / AUTHORIZATION_SEAL).read_bytes())
        or marker["activation_sha256"] != _sha256((root / ACTIVATION_RECORD).read_bytes())
        or marker["capability_contract_sha256"]
        != _sha256((root / "configs/harmonic_censoring_h25_scientific_execution_capability_contract.json").read_bytes())
        or marker["ordered_fixture_ids"] != list(getattr(plan, "fixture_ids"))
        or marker["ordered_test_ids"] != list(getattr(plan, "test_ids"))
        or marker["real_data_used"] is not False
        or marker["H17_H23_H24_population_used"] is not False
        or marker["locked_test_used"] is not False
        or marker["model_or_training_authorized"] is not False
    ):
        raise PermissionError("H25 secondary observer claim binding mismatch.")
    for field in (
        "authority_source_blob", "runner_source_blob", "engine_source_blob",
        "recomputer_source_blob", "population_index_sha256",
        "population_provenance_sha256", "population_receipt_sha256",
        "administrative_qualification_sha256",
    ):
        if marker[field] != seal[field]:
            raise PermissionError(f"H25 secondary observer claim differs at {field}.")
    return MappingProxyType(marker)


def _load_context_after_claim(
    np: object,
    root: Path,
    contract: Mapping[str, object],
    seal: Mapping[str, object],
    plan: object,
) -> object:
    from src.polyphonic.harmonic_censoring_h25_scientific_engine import (
        H25CausalReplayTrace,
        H25EvidenceProducerContext,
    )

    population = contract["published_population"]
    population_root = (root / population["directory"]).resolve(strict=True)
    bindings = {
        "population_index.jsonl": seal["population_index_sha256"],
        "runtime_provenance.json": seal["population_provenance_sha256"],
        "population_receipt.json": seal["population_receipt_sha256"],
    }
    bound_bytes: dict[str, bytes] = {}
    for name, expected in bindings.items():
        path = population_root / name
        raw = path.read_bytes()
        if path.is_symlink() or _sha256(raw) != expected:
            raise ValueError(f"H25 secondary observer population binding mismatch for {name}.")
        bound_bytes[name] = raw
    lines = bound_bytes["population_index.jsonl"].splitlines(keepends=True)
    if len(lines) != 36:
        raise ValueError("H25 secondary observer population count is not 36.")
    waveforms: dict[str, object] = {}
    fixture_records: dict[str, Mapping[str, object]] = {}
    traces: dict[str, object] = {}
    for ordinal, line in enumerate(lines):
        row = _parse(line, f"secondary population index {ordinal}")
        fixture_id = row["fixture_id"]
        if fixture_id != getattr(plan, "fixture_ids")[ordinal] or row["ordinal"] != ordinal:
            raise ValueError("H25 secondary observer population order mismatch.")
        artifacts: dict[str, bytes] = {}
        for stem in ("waveform", "fixture_record", "target_record"):
            candidate = population_root / row[f"{stem}_path"]
            if candidate.is_symlink():
                raise ValueError("H25 secondary observer forbids population symlinks.")
            path = candidate.resolve(strict=True)
            path.relative_to(population_root)
            raw = path.read_bytes()
            if len(raw) != row[f"{stem}_size_bytes"] or _sha256(raw) != row[f"{stem}_sha256"]:
                raise ValueError(f"H25 secondary observer {stem} bytes changed.")
            artifacts[stem] = raw
        waveform = np.frombuffer(artifacts["waveform"], dtype="<f8").astype(np.float64, copy=True)
        if waveform.shape != (16640,) or not bool(np.all(np.isfinite(waveform))):
            raise ValueError("H25 secondary observer waveform shape/finiteness mismatch.")
        record = _parse(artifacts["fixture_record"], f"secondary fixture {fixture_id}")
        parameters = record["source_fixture_record"].get("parameters", {})
        old_pitch = parameters.get("old_pitch")
        transitions: tuple[Mapping[str, object], ...] = ()
        if type(old_pitch) is int:
            transitions = (
                MappingProxyType({"sample_index": 8192, "kind": "note_on", "pitch": old_pitch}),
            )
        waveforms[fixture_id] = waveform
        fixture_records[fixture_id] = MappingProxyType(record)
        traces[fixture_id] = H25CausalReplayTrace(fixture_id, 16383, (), transitions)
    resource = importlib.import_module("resource")
    return H25EvidenceProducerContext(
        np=np,
        plan=plan,
        waveforms=MappingProxyType(waveforms),
        fixture_records=MappingProxyType(fixture_records),
        causal_replay_traces=MappingProxyType(traces),
        started_ns=time.perf_counter_ns(),
        peak_rss_bytes=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        operational_counters=MappingProxyType({
            "GPU_device_count": 0,
            "scientific_process_count": 1,
            "model_inference_call_count": 0,
            "hidden_repeated_pitch_shift_inference_count": 0,
        }),
        observed_fixture_ids=getattr(plan, "fixture_ids"),
        observed_test_ids=getattr(plan, "test_ids"),
        observed_test_records=None,
    )


def run_h25_secondary_runtime_observer(repository_root: Path) -> bytes:
    """Return the canonical P2-007 observation; dormant before all science."""

    root = Path(repository_root).resolve(strict=True)
    seal, _activation, head = _validate_future_transition(root)
    contract = _validate_dormant_contract(root)
    _require_runtime_before_numpy(root, contract)
    command = seal["secondary_runtime_command"]
    identity = _validate_secondary_runtime_identity(
        root, command, seal["secondary_runtime_identity"]
    )
    if (
        Path(__file__).resolve(strict=True) != Path(identity["observer_payload_path"])
        or Path(sys.executable).resolve(strict=True) != Path(identity["resolved_executable"])
        or sys.argv != [str(Path(__file__).resolve(strict=True))]
    ):
        raise PermissionError("H25 secondary observer invocation differs from sealed command.")
    from src.polyphonic.harmonic_censoring_h25_scientific_engine import (
        H25_EXACT_EVIDENCE_PRODUCER_REGISTRY,
        load_h25_dormant_scientific_plan,
    )

    plan = load_h25_dormant_scientific_plan(root)
    _claim_marker(root, contract, seal, head, plan)
    np = importlib.import_module("numpy")
    if getattr(np, "__version__", None) != "1.26.4":
        raise RuntimeError("H25 secondary observer requires exact NumPy 1.26.4.")
    context = _load_context_after_claim(np, root, contract, seal, plan)
    from src.polyphonic import run_harmonic_censoring_h25_scientific as runner

    records = runner._derive_recomputed_runtime_test_records(context, identity)
    context = replace(context, observed_test_records=records)
    test = next(item for item in plan.tests if item.test_id == "H25-T-P2-007")
    evidence = H25_EXACT_EVIDENCE_PRODUCER_REGISTRY[test.test_id](context, test)
    evidence = runner._attach_runtime_identity(evidence, identity)
    observation = evidence["current_runtime_observation"]
    return _canonical(observation)


def _main(argv: Sequence[str]) -> int:
    if list(argv) != [str(Path(__file__).resolve(strict=True))]:
        raise PermissionError("H25 secondary observer accepts no arguments.")
    root = Path(__file__).resolve(strict=True).parents[2]
    sys.stdout.buffer.write(run_h25_secondary_runtime_observer(root))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))


__all__ = ["run_h25_secondary_runtime_observer"]
