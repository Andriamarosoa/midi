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
  : > "$path"
  while (($#)); do
    printf '%s\n' "$1" >> "$path"
    shift
  done
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
    module="${4:-}"
    shift 4 || true
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
      if [[ "$lock_owned" == "1" ]]; then rmdir "$lock_path" 2>/dev/null || true; fi
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
    "$worker_root/.venv/bin/python" - "$device" <<'PY'
import sys
import tensorflow as tf
if tf.__version__ != "2.15.1":
    raise SystemExit(f"Expected TensorFlow 2.15.1, got {tf.__version__}")
if sys.argv[1] == "metal" and not tf.config.list_physical_devices("GPU"):
    raise SystemExit("Apple Metal GPU is unavailable")
PY
    memory_bytes="$(sysctl -n hw.memsize)"
    available_kib="$(df -Pk "$worker_root" | tail -n 1 | awk '{print $4}')"
    (( memory_bytes >= 15000000000 )) || {
      echo "At least 15 GB physical memory is required." >&2; exit 9;
    }
    (( available_kib >= 10485760 )) || {
      echo "At least 10 GiB free disk is required before a heavy job." >&2
      exit 9
    }
    if [[ "$module" == "src.polyphonic.train" ]]; then
      config_path=""
      previous=""
      for argument in "$@"; do
        if [[ "$previous" == "--config" ]]; then config_path="$argument"; break; fi
        previous="$argument"
      done
      [[ -n "$config_path" ]] || {
        echo "Training jobs require an explicit --config." >&2; exit 10;
      }
      "$worker_root/.venv/bin/python" - \
        "$workspace" "$worker_root" "$config_path" "$@" <<'PY'
import csv
import hashlib
import pathlib
import sys
import yaml

workspace = pathlib.Path(sys.argv[1]).resolve(strict=True)
worker_root = pathlib.Path(sys.argv[2]).resolve(strict=True)
config_path = pathlib.Path(sys.argv[3])
if not config_path.is_absolute():
    config_path = workspace / config_path
config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
training = config["training"]
arguments = sys.argv[4:]


def option_value(name: str):
    for index, value in enumerate(arguments):
        if value == name:
            if index + 1 >= len(arguments):
                raise SystemExit(f"Missing value for {name}")
            return arguments[index + 1]
        prefix = name + "="
        if value.startswith(prefix):
            return value[len(prefix):]
    return None


workers = int(option_value("--workers") or training.get("workers", 1))
queue_size = int(training.get("max_queue_size", 1))
recovery_chunks = int(
    option_value("--recovery-chunk-batches")
    or training.get("recovery_chunk_batches", 32)
)
runtime_minutes = float(
    option_value("--maximum-runtime-minutes")
    or training.get("maximum_runtime_minutes", 360)
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
print("REMOTE_SPLIT_PREFLIGHT train=572 validation=182 test=0")
PY
    fi
    mkdir -p "$job_dir"
    stdout_path="$worker_root/logs/$job_id.stdout.log"
    stderr_path="$worker_root/logs/$job_id.stderr.log"
    runner="$job_dir/run.sh"
    command_line="$(printf '%q ' "$worker_root/.venv/bin/python" -u -m "$module" "$@")"
    write_state "$job_dir/status.env" \
      "status=launching" "job_id=$job_id" "commit=$commit" "device=$device"
    cat > "$runner" <<EOF
#!/usr/bin/env bash
set +e
export MIDI_DATA_ROOT=$(printf '%q' "$worker_root/data")
export PYTHONPATH=$(printf '%q' "$workspace")
export PYTHONUNBUFFERED=1
export MIDI_FORCE_CPU=$(if [[ "$device" == "cpu" ]]; then printf 1; else printf 0; fi)
export GUITAR_MIDI_SOURCE_COMMIT=$(printf '%q' "$commit")
cd $(printf '%q' "$workspace")
printf '%s\n' "\$\$" > $(printf '%q' "$worker_root/active.pid")
printf '%s\n' $(printf '%q' "$job_id") > $(printf '%q' "$worker_root/active.job")
{
  date -u +started_utc=%Y-%m-%dT%H:%M:%SZ
  memory_pressure -Q 2>/dev/null || true
  sysctl vm.swapusage 2>/dev/null || true
  pmset -g therm 2>/dev/null || true
} > $(printf '%q' "$job_dir/system-start.txt")
printf 'status=running\njob_id=%s\ncommit=%s\ndevice=%s\nstarted_utc=%s\n' \\
  $(printf '%q' "$job_id") $(printf '%q' "$commit") $(printf '%q' "$device") "\$(date -u +%Y-%m-%dT%H:%M:%SZ)" \\
  > $(printf '%q' "$job_dir/status.env")
if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu $command_line > $(printf '%q' "$stdout_path") 2> $(printf '%q' "$stderr_path")
else
  $command_line > $(printf '%q' "$stdout_path") 2> $(printf '%q' "$stderr_path")
fi
code=\$?
{
  date -u +finished_utc=%Y-%m-%dT%H:%M:%SZ
  memory_pressure -Q 2>/dev/null || true
  sysctl vm.swapusage 2>/dev/null || true
  pmset -g therm 2>/dev/null || true
} > $(printf '%q' "$job_dir/system-finish.txt")
if [[ \$code -eq 0 ]]; then final_status=exited_zero; else final_status=exited_nonzero; fi
printf 'status=%s\njob_id=%s\ncommit=%s\ndevice=%s\nexit_code=%s\nfinished_utc=%s\n' \\
  "\$final_status" $(printf '%q' "$job_id") $(printf '%q' "$commit") $(printf '%q' "$device") "\$code" \\
  "\$(date -u +%Y-%m-%dT%H:%M:%SZ)" > $(printf '%q' "$job_dir/status.env")
if [[ -f $(printf '%q' "$worker_root/active.job") ]] && \\
   [[ "\$(cat $(printf '%q' "$worker_root/active.job"))" == $(printf '%q' "$job_id") ]]; then
  rm -f $(printf '%q' "$worker_root/active.pid") $(printf '%q' "$worker_root/active.job")
  rmdir $(printf '%q' "$worker_root/active.lock") 2>/dev/null || true
fi
exit \$code
EOF
    chmod 700 "$runner"
    nohup bash "$runner" >/dev/null 2>&1 < /dev/null &
    pid=$!
    lock_owned=0
    trap - EXIT
    printf 'job_id=%s\npid=%s\ncommit=%s\ndevice=%s\nstdout=%s\nstderr=%s\n' \
      "$job_id" "$pid" "$commit" "$device" "$stdout_path" "$stderr_path"
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
    if [[ -f "$worker_root/active.pid" && -f "$worker_root/active.job" ]] &&
       [[ "$(cat "$worker_root/active.job")" == "$job_id" ]]; then
      pid="$(cat "$worker_root/active.pid")"
      if kill -0 "$pid" 2>/dev/null; then
        printf 'pid=%s\nalive=true\n' "$pid"
      else
        printf 'pid=%s\nalive=false\nstale=true\n' "$pid"
      fi
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
    echo "Usage: mac_worker.sh {probe|bootstrap|install-data|start|status|tail} ROOT ..." >&2
    exit 2
    ;;
esac
