#!/usr/bin/env bash
set -euo pipefail

action="${1:-}"
root_input="${2:-~/midi-worker}"
shift 2 || true

case "$root_input" in
  "~/"*) worker_root="$HOME/${root_input#\~/}" ;;
  /*) worker_root="$root_input" ;;
  *) echo "remote_root must be absolute or start with ~/" >&2; exit 2 ;;
esac
[[ "$worker_root" != "/" && "/$worker_root/" != *"/../"* && "/$worker_root/" != *"/./"* ]] || {
  echo "remote_root must not be / or contain dot segments" >&2
  exit 2
}

require_commit() {
  local commit="${1:-}"
  [[ "$commit" =~ ^[0-9a-f]{40}$ ]] || {
    echo "Invalid commit identifier: $commit" >&2
    exit 2
  }
  local workspace="$worker_root/workspaces/$commit"
  [[ -d "$workspace" ]] || {
    echo "Missing synchronized workspace: $workspace" >&2
    exit 3
  }
  [[ -f "$workspace/.source.env" ]] &&
    grep -Fxq "commit=$commit" "$workspace/.source.env" || {
      echo "Workspace provenance does not match commit $commit" >&2
      exit 3
    }
  printf '%s\n' "$workspace"
}

write_state() {
  local path="$1"
  shift
  local temporary="$path.tmp.$$"
  umask 077
  : > "$temporary"
  while (($#)); do
    printf '%s\n' "$1" >> "$temporary"
    shift
  done
  mv -f "$temporary" "$path"
}

read_state_field() {
  local path="$1"
  local key="$2"
  awk -F= -v key="$key" '$1 == key {sub(/^[^=]*=/, ""); print; exit}' "$path"
}

case "$action" in
  probe)
    printf 'hostname=%s\n' "$(hostname)"
    printf 'architecture=%s\n' "$(uname -m)"
    printf 'kernel=%s\n' "$(uname -s)"
    if command -v sw_vers >/dev/null 2>&1; then
      printf 'macos=%s\n' "$(sw_vers -productVersion)"
    fi
    if command -v sysctl >/dev/null 2>&1; then
      printf 'memory_bytes=%s\n' "$(sysctl -n hw.memsize)"
    fi
    df -Pk "$HOME" | tail -n 1 | awk '{print "home_available_kib=" $4}'
    if [[ -x "$worker_root/.venv/bin/python" ]]; then
      MIDI_DATA_ROOT="$worker_root/data" \
        "$worker_root/.venv/bin/python" - <<'PY'
import json
import platform
import tensorflow as tf

print("python=" + platform.python_version())
print("tensorflow=" + tf.__version__)
print("devices=" + json.dumps({
    "cpu": [item.name for item in tf.config.list_physical_devices("CPU")],
    "gpu": [item.name for item in tf.config.list_physical_devices("GPU")],
}, sort_keys=True))
PY
    else
      printf 'venv=missing\n'
    fi
    ;;

  bootstrap)
    commit="${1:-}"
    python_bin="${2:-python3.11}"
    workspace="$(require_commit "$commit")"
    [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]] || {
      echo "This worker profile requires macOS arm64." >&2
      exit 4
    }
    command -v "$python_bin" >/dev/null 2>&1 || {
      echo "$python_bin is missing. Install Python 3.11, then retry." >&2
      exit 5
    }
    "$python_bin" - <<'PY'
import sys
if sys.version_info[:2] != (3, 11):
    raise SystemExit("Python 3.11 is required for the TF 2.15 parity profile")
PY
    mkdir -p "$worker_root" "$worker_root/jobs" "$worker_root/logs"
    bootstrap_lock="$worker_root/active.lock"
    if ! mkdir "$bootstrap_lock" 2>/dev/null; then
      echo "A heavy job or maintenance operation owns $bootstrap_lock" >&2
      exit 6
    fi
    cleanup_bootstrap_lock() {
      rmdir "$bootstrap_lock" 2>/dev/null || true
    }
    trap cleanup_bootstrap_lock EXIT
    if [[ ! -x "$worker_root/.venv/bin/python" ]]; then
      "$python_bin" -m venv "$worker_root/.venv"
    fi
    "$worker_root/.venv/bin/python" -m pip install --upgrade \
      pip setuptools wheel
    "$worker_root/.venv/bin/python" -m pip install \
      "tensorflow==2.15.1" "tensorflow-metal==1.1.0"
    "$worker_root/.venv/bin/python" -m pip install -e "$workspace"
    MIDI_DATA_ROOT="$worker_root/data" \
      "$worker_root/.venv/bin/python" - "$worker_root" <<'PY'
import json
import pathlib
import platform
import sys
import tensorflow as tf

if not tf.__version__.startswith("2.15."):
    raise SystemExit(f"Expected TensorFlow 2.15.x, got {tf.__version__}")
gpus = tf.config.list_physical_devices("GPU")
if not gpus:
    raise SystemExit("tensorflow-metal did not expose an Apple GPU")
with tf.device("/GPU:0"):
    value = tf.reduce_sum(tf.matmul(tf.ones((64, 64)), tf.ones((64, 64))))
float(value.numpy())
report = {
    "architecture": platform.machine(),
    "python": platform.python_version(),
    "tensorflow": tf.__version__,
    "gpu_devices": [item.name for item in gpus],
    "status": "ready",
}
path = pathlib.Path(sys.argv[1]) / "environment.json"
path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(report, sort_keys=True))
PY
    "$worker_root/.venv/bin/python" -m pip freeze \
      > "$worker_root/environment.freeze.txt"
    cleanup_bootstrap_lock
    trap - EXIT
    ;;

  install-data)
    manifest_hash="${1:-}"
    archive_hash="${2:-}"
    expected_rows="${3:-}"
    [[ "$manifest_hash" =~ ^[0-9a-f]{64}$ ]] || {
      echo "Invalid manifest SHA-256" >&2; exit 2;
    }
    [[ "$archive_hash" =~ ^[0-9a-f]{64}$ ]] || {
      echo "Invalid archive SHA-256" >&2; exit 2;
    }
    [[ "$expected_rows" == "754" ]] || {
      echo "Expected exactly 754 train+validation rows" >&2; exit 2;
    }
    [[ -x "$worker_root/.venv/bin/python" ]] || {
      echo "Bootstrap the worker before installing data." >&2; exit 5;
    }
    mkdir -p "$worker_root/data"
    data_lock="$worker_root/active.lock"
    if ! mkdir "$data_lock" 2>/dev/null; then
      echo "A heavy job or maintenance operation owns $data_lock" >&2
      exit 6
    fi
    cleanup_data_lock() {
      rmdir "$data_lock" 2>/dev/null || true
    }
    trap cleanup_data_lock EXIT
    archive="$worker_root/inbox/mac-data-$manifest_hash.tar"
    evidence="$worker_root/data/.manifest-$manifest_hash.env"
    manifest="$worker_root/data/processed/polyphonic_harmonic_presence_v1/manifest_train_validation.csv"
    [[ -f "$archive" ]] || { echo "Missing uploaded data archive" >&2; exit 3; }
    actual_archive="$(shasum -a 256 "$archive" | awk '{print $1}')"
    [[ "$actual_archive" == "$archive_hash" ]] || {
      echo "Uploaded data archive SHA-256 mismatch" >&2; exit 3;
    }
    # Remove prior validity before touching any payload. A failed extraction
    # can therefore never leave a partial dataset accepted by start().
    rm -f "$evidence"
    tar -xf "$archive" -C "$worker_root"
    actual_manifest="$(shasum -a 256 "$manifest" | awk '{print $1}')"
    [[ "$actual_manifest" == "$manifest_hash" ]] || {
      echo "Extracted manifest SHA-256 mismatch" >&2; exit 3;
    }
    "$worker_root/.venv/bin/python" - "$manifest" <<'PY'
import csv
import pathlib
import sys

with pathlib.Path(sys.argv[1]).open(
    "r", encoding="utf-8-sig", newline=""
) as handle:
    rows = list(csv.DictReader(handle))
counts = {"train": 0, "validation": 0}
for row in rows:
    split = row.get("split", "")
    if split not in counts:
        raise SystemExit(f"Forbidden split after extraction: {split!r}")
    counts[split] += 1
if counts != {"train": 572, "validation": 182}:
    raise SystemExit(f"Unexpected extracted split contract: {counts}")
PY
    evidence_tmp="$evidence.tmp.$$"
    printf 'manifest_sha256=%s\narchive_sha256=%s\nrows=754\nsplits=train,validation\nlocked_test_used=false\n' \
      "$manifest_hash" "$archive_hash" > "$evidence_tmp"
    mv -f "$evidence_tmp" "$evidence"
    rm -f "$archive"
    cleanup_data_lock
    trap - EXIT
    ;;

  start)
    commit="${1:-}"
    job_id="${2:-}"
    device="${3:-}"
    wall_timeout_seconds="${4:-}"
    module="${5:-}"
    shift 5 || true
    workspace="$(require_commit "$commit")"
    [[ "$job_id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || {
      echo "Invalid job id" >&2; exit 2;
    }
    [[ "$module" =~ ^[A-Za-z_][A-Za-z0-9_.]*$ ]] || {
      echo "Invalid Python module" >&2; exit 2;
    }
    [[ "$device" == "cpu" || "$device" == "metal" ]] || {
      echo "Device must be cpu or metal" >&2; exit 2;
    }
    [[ "$wall_timeout_seconds" =~ ^[0-9]+$ ]] &&
      (( wall_timeout_seconds >= 1 && wall_timeout_seconds <= 22200 )) || {
        echo "Wall timeout must be between 1 and 22200 seconds" >&2; exit 2;
      }
    [[ -x "$worker_root/.venv/bin/python" ]] || {
      echo "Worker environment is not bootstrapped." >&2; exit 5;
    }
    mkdir -p "$worker_root/jobs" "$worker_root/logs"
    lock_path="$worker_root/active.lock"
    if ! mkdir "$lock_path" 2>/dev/null; then
      echo "Another job owns the atomic heavy-worker lock: $lock_path" >&2
      exit 6
    fi
    lock_owned=1
    release_start_lock() {
      if [[ "$lock_owned" == "1" ]]; then
        if [[ -n "${token:-}" && -f "$worker_root/active.token" ]] &&
           [[ "$(cat "$worker_root/active.token")" == "$token" ]]; then
          rm -f "$worker_root/active.pid" "$worker_root/active.job" \
            "$worker_root/active.token" "$worker_root/active.owner.env"
        fi
        rmdir "$lock_path" 2>/dev/null || true
      fi
    }
    trap release_start_lock EXIT
    active_pid_path="$worker_root/active.pid"
    if [[ -f "$active_pid_path" ]]; then
      active_pid="$(cat "$active_pid_path")"
      if kill -0 "$active_pid" 2>/dev/null; then
        echo "Another heavy job is active: PID $active_pid" >&2
        exit 6
      fi
    fi
    job_dir="$worker_root/jobs/$job_id"
    [[ ! -e "$job_dir" ]] || {
      echo "Job id already exists: $job_id" >&2; exit 7;
    }
    memory_bytes="$(sysctl -n hw.memsize)"
    available_kib="$(df -Pk "$worker_root" | tail -n 1 | awk '{print $4}')"
    (( memory_bytes >= 15000000000 )) || {
      echo "At least 15 GB physical memory is required." >&2; exit 9;
    }
    (( available_kib >= 10485760 )) || {
      echo "At least 10 GiB free disk is required before a heavy job." >&2
      exit 9
    }
    mkdir -p "$job_dir"
    preflight="$job_dir/preflight.py"
    cat > "$preflight" <<'PY'
import csv
import hashlib
import json
import pathlib
import sys
import yaml
import tensorflow as tf

device = sys.argv[1]
module = sys.argv[2]
workspace = pathlib.Path(sys.argv[3]).resolve(strict=True)
worker_root = pathlib.Path(sys.argv[4]).resolve(strict=True)
wall_timeout_seconds = int(sys.argv[5])
arguments = sys.argv[6:]
if tf.__version__ != "2.15.1":
    raise SystemExit(f"Expected TensorFlow 2.15.1, got {tf.__version__}")
if device == "metal" and not tf.config.list_physical_devices("GPU"):
    raise SystemExit("Apple Metal GPU is unavailable")
controlled_modules = {
    "src.polyphonic.train",
    "src.polyphonic.smoke_neural_independent_note",
}
if module not in controlled_modules:
    raise SystemExit(0)


def option_value(name: str, *, required: bool = False):
    matches = []
    for index, value in enumerate(arguments):
        if value == name:
            if index + 1 >= len(arguments):
                raise SystemExit(f"Missing value for {name}")
            matches.append(arguments[index + 1])
        prefix = name + "="
        if value.startswith(prefix):
            matches.append(value[len(prefix):])
    if len(matches) > 1:
        raise SystemExit(f"Duplicate controlled option: {name}")
    if required and not matches:
        raise SystemExit(f"Training jobs require an explicit {name}")
    if matches and not matches[0]:
        raise SystemExit(f"Empty value for {name}")
    return matches[0] if matches else None


def flag_value(name: str) -> bool:
    count = arguments.count(name)
    if count > 1:
        raise SystemExit(f"Duplicate controlled flag: {name}")
    return count == 1


config_argument = option_value("--config", required=True)
config_path = pathlib.Path(config_argument)
if not config_path.is_absolute():
    config_path = workspace / config_path
config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
training = config["train"]
queue_size = int(training.get("max_queue_size", 1))
if module == "src.polyphonic.train":
    workers = int(option_value("--workers") or training.get("workers", 1))
    recovery_chunks = int(
        option_value("--recovery-chunk-batches")
        or training.get("recovery_chunk_batches", 32)
    )
    runtime_minutes = float(
        option_value("--maximum-runtime-minutes")
        or training.get("maximum_runtime_minutes", 360)
    )
    smoke_test = flag_value("--smoke-test")
    representative_smoke = flag_value("--representative-smoke")
    if smoke_test != representative_smoke:
        raise SystemExit(
            "Representative Mac smokes require both --smoke-test and "
            "--representative-smoke"
        )
    if smoke_test:
        smoke_examples = int(option_value("--smoke-examples") or 8192)
        smoke_validation_examples = int(
            option_value("--smoke-validation-examples") or 2048
        )
        if (smoke_examples, smoke_validation_examples) != (8192, 2048):
            raise SystemExit(
                "Representative Mac smokes require exactly 8192 train and "
                "2048 validation examples"
            )
    if workers != 1 or queue_size != 1 or recovery_chunks != 32:
        raise SystemExit(
            "Mac M4 safety contract requires workers=1, max_queue_size=1 "
            "and recovery_chunk_batches=32"
        )
    if not 0 < runtime_minutes <= 360:
        raise SystemExit(
            "Mac M4 safety contract requires 0 < maximum_runtime_minutes <= 360"
        )
else:
    if device != "cpu":
        raise SystemExit("The independent-note train gate is CPU-only")
    if queue_size != 1:
        raise SystemExit("The independent-note train gate requires queue size 1")
    fit_examples = int(option_value("--fit-examples", required=True))
    dev_examples = int(option_value("--dev-examples", required=True))
    calibration_examples = int(
        option_value("--calibration-examples", required=True)
    )
    if (fit_examples, dev_examples, calibration_examples) != (8192, 2048, 4096):
        raise SystemExit(
            "The independent-note gate requires exactly 8192 fit, 2048 dev, "
            "and 4096 calibration examples"
        )
    epochs = int(option_value("--epochs", required=True))
    if epochs != int(training["epochs"]):
        raise SystemExit("The independent-note gate must use config train.epochs")
    runtime_minutes = float(
        option_value("--maximum-runtime-minutes", required=True)
    )
    if not 0 < runtime_minutes <= 60:
        raise SystemExit(
            "The independent-note train gate requires a runtime in (0, 60] minutes"
        )
    checkpoint = pathlib.Path(
        option_value("--initial-checkpoint", required=True)
    ).resolve(strict=True)
    checkpoint_root = (worker_root / "checkpoints").resolve(strict=True)
    if checkpoint.parent != checkpoint_root:
        raise SystemExit("Initial checkpoint is outside the immutable checkpoint store")
    expected_checkpoint = str(
        config.get("initialization", {}).get("required_checkpoint_sha256", "")
    )
    checkpoint_digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    if checkpoint_digest != expected_checkpoint:
        raise SystemExit("Initial checkpoint SHA-256 differs from the config")
    output_dir = pathlib.Path(option_value("--output-dir", required=True))
    if output_dir.is_absolute() or ".." in output_dir.parts or output_dir.parts[:1] != ("tmp",):
        raise SystemExit("Independent-note output must be a relative tmp/... path")
if runtime_minutes * 60 + 60 > wall_timeout_seconds:
    raise SystemExit(
        "maximum_runtime_minutes must leave at least 60 seconds before "
        "the hard wall timeout"
    )
manifest = pathlib.Path(config["dataset"]["manifest"])
if not manifest.is_absolute():
    manifest = workspace / manifest
manifest = manifest.resolve(strict=True)
digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
expected = "b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7"
if digest != expected:
    raise SystemExit(f"Unexpected remote manifest SHA-256: {digest}")
evidence = worker_root / "data" / f".manifest-{digest}.env"
if not evidence.is_file():
    raise SystemExit(f"Missing synchronized manifest evidence: {evidence}")
evidence_text = evidence.read_text(encoding="utf-8")
if "locked_test_used=false" not in evidence_text.splitlines():
    raise SystemExit("Manifest evidence does not preserve locked_test_used=false")
with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))
counts = {name: 0 for name in ("train", "validation")}
for row in rows:
    split = row.get("split", "")
    if split not in counts:
        raise SystemExit(f"Forbidden split in remote manifest: {split!r}")
    counts[split] += 1
if counts != {"train": 572, "validation": 182}:
    raise SystemExit(f"Unexpected remote split contract: {counts}")
if module == "src.polyphonic.smoke_neural_independent_note":
    sidecar_value = str(
        config["dataset"].get("independent_note_fundamental_offsets", "")
    )
    sidecar_expected = str(
        config["dataset"].get("independent_note_fundamental_offsets_sha256", "")
    )
    if not sidecar_value or len(sidecar_expected) != 64:
        raise SystemExit("Independent-note gate requires a signed offset sidecar")
    sidecar = pathlib.Path(sidecar_value)
    if not sidecar.is_absolute():
        sidecar = workspace / sidecar
    sidecar = sidecar.resolve(strict=True)
    if hashlib.sha256(sidecar.read_bytes()).hexdigest() != sidecar_expected:
        raise SystemExit("Independent-note offset sidecar SHA-256 mismatch")
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != 1
        or payload.get("locked_test_used") is not False
        or payload.get("manifest_sha256") != digest
    ):
        raise SystemExit("Independent-note offset sidecar provenance is invalid")
print("REMOTE_SPLIT_PREFLIGHT train=572 validation=182 test=0")
PY
    stdout_path="$worker_root/logs/$job_id.stdout.log"
    stderr_path="$worker_root/logs/$job_id.stderr.log"
    runner="$job_dir/run.sh"
    wallclock="$workspace/scripts/remote/wallclock_exec.py"
    [[ -f "$wallclock" ]] || {
      echo "Missing wall-clock supervisor: $wallclock" >&2; exit 11;
    }
    token="$($worker_root/.venv/bin/python - <<'PY'
import secrets
print(secrets.token_hex(16))
PY
)"
    command_line="$(printf '%q ' "$worker_root/.venv/bin/python" -u -m "$module" "$@")"
    preflight_line="$(printf '%q ' \
      "$worker_root/.venv/bin/python" "$preflight" "$device" "$module" \
      "$workspace" "$worker_root" "$wall_timeout_seconds" "$@")"
    job_command="$job_dir/job_command.sh"
    cat > "$job_command" <<EOF
#!/usr/bin/env bash
set -euo pipefail
requested_open_files=4096
current_open_files="\$(ulimit -Sn)"
if [[ "\$current_open_files" != "unlimited" ]] &&
   (( current_open_files < requested_open_files )); then
  ulimit -Sn "\$requested_open_files"
fi
current_open_files="\$(ulimit -Sn)"
if [[ "\$current_open_files" != "unlimited" ]] &&
   (( current_open_files < requested_open_files )); then
  echo "Open-file soft limit remains below \$requested_open_files: \$current_open_files" >&2
  exit 12
fi
printf 'OPEN_FILE_LIMIT soft=%s requested=%s\n' "\$current_open_files" "\$requested_open_files"
$preflight_line
exec $command_line
EOF
    chmod 700 "$job_command"
    job_command_line="$(printf '%q ' bash "$job_command")"
    supervisor_line="$(printf '%q ' \
      "$worker_root/.venv/bin/python" "$wallclock" \
      --timeout-seconds "$wall_timeout_seconds" --grace-seconds 15 \
      --job-id "$job_id" --token "$token" \
      --process-state "$job_dir/process.env" \
      --active-owner "$worker_root/active.owner.env" \
      --timeout-marker "$job_dir/timed_out.env" --)"
    write_state "$job_dir/status.env" \
      "status=launching" "job_id=$job_id" "commit=$commit" "device=$device" \
      "wall_timeout_seconds=$wall_timeout_seconds"
    write_state "$worker_root/active.job" "$job_id"
    write_state "$worker_root/active.token" "$token"
    cat > "$runner" <<EOF
#!/usr/bin/env bash
set +e
export MIDI_DATA_ROOT=$(printf '%q' "$worker_root/data")
export PYTHONPATH=$(printf '%q' "$workspace")
export PYTHONUNBUFFERED=1
export MIDI_FORCE_CPU=$(if [[ "$device" == "cpu" ]]; then printf 1; else printf 0; fi)
export GUITAR_MIDI_SOURCE_COMMIT=$(printf '%q' "$commit")
cd $(printf '%q' "$workspace")
active_pid_tmp=$(printf '%q' "$worker_root/active.pid.tmp.runner")
printf '%s\n' "\$\$" > "\$active_pid_tmp"
mv -f "\$active_pid_tmp" $(printf '%q' "$worker_root/active.pid")
runner_signal=0
supervisor_pid=""
forward_signal() {
  runner_signal=1
  if [[ "\$supervisor_pid" =~ ^[0-9]+$ ]]; then
    kill -TERM "\$supervisor_pid" 2>/dev/null || true
  fi
}
trap forward_signal HUP INT TERM
{
  date -u +started_utc=%Y-%m-%dT%H:%M:%SZ
  memory_pressure -Q 2>/dev/null || true
  sysctl vm.swapusage 2>/dev/null || true
  pmset -g therm 2>/dev/null || true
} > $(printf '%q' "$job_dir/system-start.txt")
status_tmp=$(printf '%q' "$job_dir/status.env.tmp.runner")
printf 'status=running\njob_id=%s\ncommit=%s\ndevice=%s\nwall_timeout_seconds=%s\nstarted_utc=%s\n' \\
  $(printf '%q' "$job_id") $(printf '%q' "$commit") $(printf '%q' "$device") \\
  $(printf '%q' "$wall_timeout_seconds") "\$(date -u +%Y-%m-%dT%H:%M:%SZ)" \\
  > "\$status_tmp"
mv -f "\$status_tmp" $(printf '%q' "$job_dir/status.env")
if command -v caffeinate >/dev/null 2>&1; then
  $supervisor_line caffeinate -dimsu $job_command_line > $(printf '%q' "$stdout_path") 2> $(printf '%q' "$stderr_path") &
else
  $supervisor_line $job_command_line > $(printf '%q' "$stdout_path") 2> $(printf '%q' "$stderr_path") &
fi
supervisor_pid=\$!
while true; do
  wait "\$supervisor_pid"
  code=\$?
  kill -0 "\$supervisor_pid" 2>/dev/null || break
done
{
  date -u +finished_utc=%Y-%m-%dT%H:%M:%SZ
  memory_pressure -Q 2>/dev/null || true
  sysctl vm.swapusage 2>/dev/null || true
  pmset -g therm 2>/dev/null || true
} > $(printf '%q' "$job_dir/system-finish.txt")
if [[ \$code -eq 125 ]]; then
  final_status=orphaned_group
elif [[ -f $(printf '%q' "$job_dir/timed_out.env") ]]; then
  final_status=timed_out
  code=124
elif [[ -f $(printf '%q' "$job_dir/stop_requested.env") || \$runner_signal -eq 1 ]]; then
  final_status=stopped
elif [[ \$code -eq 0 ]]; then
  final_status=exited_zero
else
  final_status=exited_nonzero
fi
status_tmp=$(printf '%q' "$job_dir/status.env.tmp.runner")
printf 'status=%s\njob_id=%s\ncommit=%s\ndevice=%s\nwall_timeout_seconds=%s\nexit_code=%s\nfinished_utc=%s\n' \\
  "\$final_status" $(printf '%q' "$job_id") $(printf '%q' "$commit") $(printf '%q' "$device") \\
  $(printf '%q' "$wall_timeout_seconds") "\$code" "\$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "\$status_tmp"
mv -f "\$status_tmp" $(printf '%q' "$job_dir/status.env")
if [[ "\$final_status" != orphaned_group ]] && \\
   [[ -f $(printf '%q' "$worker_root/active.job") ]] && \\
   [[ "\$(cat $(printf '%q' "$worker_root/active.job"))" == $(printf '%q' "$job_id") ]] && \\
   [[ -f $(printf '%q' "$worker_root/active.token") ]] && \\
   [[ "\$(cat $(printf '%q' "$worker_root/active.token"))" == $(printf '%q' "$token") ]]; then
  rm -f $(printf '%q' "$worker_root/active.pid") \\
    $(printf '%q' "$worker_root/active.job") \\
    $(printf '%q' "$worker_root/active.token") \\
    $(printf '%q' "$worker_root/active.owner.env")
  rmdir $(printf '%q' "$worker_root/active.lock") 2>/dev/null || true
fi
exit \$code
EOF
    chmod 700 "$runner"
    nohup bash "$runner" >/dev/null 2>&1 < /dev/null &
    pid=$!
    handshake=false
    for _ in $(seq 1 100); do
      if [[ -f "$job_dir/process.env" ]] &&
         [[ "$(read_state_field "$job_dir/process.env" token)" == "$token" ]]; then
        handshake=true
        break
      fi
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.1
    done
    if [[ "$handshake" != true ]]; then
      kill -TERM "$pid" 2>/dev/null || true
      for _ in $(seq 1 200); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.1
      done
      if kill -0 "$pid" 2>/dev/null; then
        # Preserve ownership if termination could not be proven; freeing the
        # lock here could overlap an untracked child with a second heavy job.
        lock_owned=0
        trap - EXIT
        echo "Runner did not stop after failed handshake; lock preserved" >&2
        exit 13
      fi
      failed_status="$(read_state_field "$job_dir/status.env" status 2>/dev/null || true)"
      failed_group_alive=false
      if [[ -f "$job_dir/process.env" ]] &&
         [[ "$(read_state_field "$job_dir/process.env" token)" == "$token" ]]; then
        failed_pgid="$(read_state_field "$job_dir/process.env" pgid)"
        if [[ "$failed_pgid" =~ ^[0-9]+$ ]] &&
           kill -0 -- "-$failed_pgid" 2>/dev/null; then
          failed_group_alive=true
        fi
      fi
      if [[ "$failed_status" == orphaned_group || "$failed_group_alive" == true ]]; then
        lock_owned=0
        trap - EXIT
        echo "Handshake failed with an owned group; lock preserved" >&2
        exit 13
      fi
      echo "Supervised process handshake failed for job $job_id" >&2
      exit 13
    fi
    lock_owned=0
    trap - EXIT
    printf 'job_id=%s\npid=%s\ncommit=%s\ndevice=%s\nwall_timeout_seconds=%s\nstdout=%s\nstderr=%s\n' \
      "$job_id" "$pid" "$commit" "$device" "$wall_timeout_seconds" "$stdout_path" "$stderr_path"
    ;;

  stop)
    job_id="${1:-}"
    [[ "$job_id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || {
      echo "Invalid job id" >&2; exit 2;
    }
    [[ -f "$worker_root/active.job" ]] &&
      [[ "$(cat "$worker_root/active.job")" == "$job_id" ]] || {
        echo "Job is not the active worker owner: $job_id" >&2; exit 12;
      }
    token="$(cat "$worker_root/active.token" 2>/dev/null || true)"
    [[ "$token" =~ ^[0-9a-f]{32}$ ]] || {
      echo "Active worker token is missing or invalid" >&2; exit 12;
    }
    process_state="$worker_root/jobs/$job_id/process.env"
    supervisor_pid=""
    pgid=""
    supervisor_alive=false
    process_group_alive=false
    if [[ -f "$process_state" ]]; then
      [[ "$(read_state_field "$process_state" job_id)" == "$job_id" ]] &&
        [[ "$(read_state_field "$process_state" token)" == "$token" ]] || {
          echo "Refusing stop because process ownership does not match" >&2; exit 12;
        }
      supervisor_pid="$(read_state_field "$process_state" supervisor_pid)"
      pgid="$(read_state_field "$process_state" pgid)"
      [[ "$supervisor_pid" =~ ^[0-9]+$ && "$pgid" =~ ^[0-9]+$ ]] || {
        echo "Invalid supervised process identifiers" >&2; exit 12;
      }
      kill -0 "$supervisor_pid" 2>/dev/null && supervisor_alive=true
      kill -0 -- "-$pgid" 2>/dev/null && process_group_alive=true
    else
      runner_pid="$(cat "$worker_root/active.pid" 2>/dev/null || true)"
      if [[ "$runner_pid" =~ ^[0-9]+$ ]] && kill -0 "$runner_pid" 2>/dev/null; then
        echo "Job has not completed the supervised-process handshake" >&2
        exit 12
      fi
    fi
    stop_marker="$worker_root/jobs/$job_id/stop_requested.env"
    if [[ "$supervisor_alive" == true ]]; then
      supervisor_command="$(ps -ww -p "$supervisor_pid" -o command= 2>/dev/null || true)"
      [[ "$supervisor_command" == *wallclock_exec.py* && "$supervisor_command" == *"$token"* ]] || {
        echo "Refusing stop because supervisor identity cannot be proven" >&2; exit 12;
      }
      write_state "$stop_marker" \
        "requested_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" "token=$token"
      if ! kill -TERM "$supervisor_pid"; then
        rm -f "$stop_marker"
        echo "Could not signal the proven owner supervisor" >&2
        exit 12
      fi
      for _ in $(seq 1 200); do
        if ! kill -0 "$supervisor_pid" 2>/dev/null &&
           ! kill -0 -- "-$pgid" 2>/dev/null; then
          break
        fi
        sleep 0.1
      done
      if kill -0 -- "-$pgid" 2>/dev/null; then
        kill -KILL -- "-$pgid" 2>/dev/null || true
      fi
    elif [[ "$process_group_alive" == true ]]; then
      echo "Refusing stop because the owner supervisor is gone while its group remains" >&2
      exit 12
    else
      write_state "$stop_marker" \
        "requested_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" "token=$token"
    fi
    if [[ "$pgid" =~ ^[0-9]+$ ]] && kill -0 -- "-$pgid" 2>/dev/null; then
      echo "Owned process group survived the stop escalation" >&2
      exit 14
    fi
    runner_pid="$(cat "$worker_root/active.pid" 2>/dev/null || true)"
    for _ in $(seq 1 100); do
      if [[ ! "$runner_pid" =~ ^[0-9]+$ ]] || ! kill -0 "$runner_pid" 2>/dev/null; then
        break
      fi
      sleep 0.1
    done
    if [[ "$runner_pid" =~ ^[0-9]+$ ]] && kill -0 "$runner_pid" 2>/dev/null; then
      runner_command="$(ps -ww -p "$runner_pid" -o command= 2>/dev/null || true)"
      expected_runner="$worker_root/jobs/$job_id/run.sh"
      [[ "$runner_command" == *"$expected_runner"* ]] || {
        echo "Refusing to signal a runner whose identity cannot be proven" >&2
        exit 15
      }
      kill -TERM "$runner_pid" 2>/dev/null || true
      for _ in $(seq 1 50); do
        kill -0 "$runner_pid" 2>/dev/null || break
        sleep 0.1
      done
      if kill -0 "$runner_pid" 2>/dev/null; then
        kill -KILL "$runner_pid" 2>/dev/null || true
      fi
    fi
    if [[ "$runner_pid" =~ ^[0-9]+$ ]] && kill -0 "$runner_pid" 2>/dev/null; then
      echo "Owned runner survived stop; lock preserved" >&2
      exit 15
    fi
    stale_cleaned=false
    if { [[ ! "$runner_pid" =~ ^[0-9]+$ ]] || ! kill -0 "$runner_pid" 2>/dev/null; } &&
       [[ -f "$worker_root/active.job" ]] &&
       [[ "$(cat "$worker_root/active.job")" == "$job_id" ]] &&
       [[ -f "$worker_root/active.token" ]] &&
       [[ "$(cat "$worker_root/active.token")" == "$token" ]]; then
      current_status="$worker_root/jobs/$job_id/status.env"
      commit_value="$(read_state_field "$current_status" commit 2>/dev/null || true)"
      device_value="$(read_state_field "$current_status" device 2>/dev/null || true)"
      timeout_value="$(read_state_field "$current_status" wall_timeout_seconds 2>/dev/null || true)"
      write_state "$current_status" \
        "status=stopped" "job_id=$job_id" "commit=$commit_value" \
        "device=$device_value" "wall_timeout_seconds=$timeout_value" \
        "exit_code=143" "finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        "stale_owner_cleanup=true"
      rm -f "$worker_root/active.pid" "$worker_root/active.job" \
        "$worker_root/active.token" "$worker_root/active.owner.env"
      rmdir "$worker_root/active.lock" 2>/dev/null || true
      stale_cleaned=true
    fi
    printf 'stop_requested=true\njob_id=%s\ntoken=%s\nstale_cleaned=%s\n' \
      "$job_id" "$token" "$stale_cleaned"
    ;;

  status)
    job_id="${1:-}"
    if [[ -z "$job_id" && -f "$worker_root/active.job" ]]; then
      job_id="$(cat "$worker_root/active.job")"
    fi
    [[ -n "$job_id" ]] || { echo "No active job."; exit 0; }
    [[ "$job_id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || {
      echo "Invalid job id" >&2; exit 2;
    }
    status_path="$worker_root/jobs/$job_id/status.env"
    [[ -f "$status_path" ]] || { echo "Unknown job: $job_id" >&2; exit 8; }
    cat "$status_path"
    memory_pressure -Q 2>/dev/null || true
    sysctl vm.swapusage 2>/dev/null || true
    runner_alive=false
    process_group_alive=false
    active_owner=false
    process_state="$worker_root/jobs/$job_id/process.env"
    active_token="$(cat "$worker_root/active.token" 2>/dev/null || true)"
    if [[ -f "$worker_root/active.job" ]] &&
       [[ "$(cat "$worker_root/active.job")" == "$job_id" ]] &&
       [[ "$active_token" =~ ^[0-9a-f]{32}$ ]] &&
       [[ -f "$process_state" ]] &&
       [[ "$(read_state_field "$process_state" job_id)" == "$job_id" ]] &&
       [[ "$(read_state_field "$process_state" token)" == "$active_token" ]]; then
      active_owner=true
    fi
    printf 'active_owner=%s\n' "$active_owner"
    if [[ "$active_owner" == true && -f "$worker_root/active.pid" ]]; then
      pid="$(cat "$worker_root/active.pid")"
      if kill -0 "$pid" 2>/dev/null; then
        runner_alive=true
      fi
      printf 'runner_pid=%s\nrunner_alive=%s\n' "$pid" "$runner_alive"
    fi
    if [[ "$active_owner" == true ]]; then
      supervisor_pid="$(read_state_field "$process_state" supervisor_pid)"
      pgid="$(read_state_field "$process_state" pgid)"
      supervisor_alive=false
      if [[ "$supervisor_pid" =~ ^[0-9]+$ ]] && kill -0 "$supervisor_pid" 2>/dev/null; then
        supervisor_alive=true
      fi
      if [[ "$pgid" =~ ^[0-9]+$ ]] && kill -0 -- "-$pgid" 2>/dev/null; then
        process_group_alive=true
      fi
      printf 'supervisor_pid=%s\nsupervisor_alive=%s\npgid=%s\nprocess_group_alive=%s\n' \
        "$supervisor_pid" "$supervisor_alive" "$pgid" "$process_group_alive"
    fi
    if [[ "$runner_alive" == false && "$process_group_alive" == true ]]; then
      printf 'orphaned_group_alive=true\n'
    elif [[ "$active_owner" == true && "$runner_alive" == false ]]; then
      printf 'stale=true\n'
    fi
    ;;

  tail)
    job_id="${1:-}"
    lines="${2:-80}"
    [[ "$job_id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo "Invalid job id" >&2; exit 2; }
    [[ "$lines" =~ ^[0-9]+$ ]] || { echo "Invalid line count" >&2; exit 2; }
    printf '%s\n' "--- stdout ---"
    tail -n "$lines" "$worker_root/logs/$job_id.stdout.log" 2>/dev/null || true
    printf '%s\n' "--- stderr ---"
    tail -n "$lines" "$worker_root/logs/$job_id.stderr.log" 2>/dev/null || true
    ;;

  *)
    echo "Usage: mac_worker.sh {probe|bootstrap|install-data|start|stop|status|tail} ROOT ..." >&2
    exit 2
    ;;
esac
