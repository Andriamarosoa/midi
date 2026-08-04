from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "MAC_WORKER.ps1").read_text(encoding="utf-8")
RUNNER = (ROOT / "scripts" / "remote" / "mac_worker.sh").read_text(
    encoding="utf-8"
)
REMOTE_README = (ROOT / "scripts" / "remote" / "README.md").read_text(
    encoding="utf-8"
)
TRAIN_SOURCE = (ROOT / "src" / "polyphonic" / "train.py").read_text(
    encoding="utf-8"
)
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")


def _ps_quote(path: pathlib.Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def _load_functions_script(body: str) -> str:
    script_path = _ps_quote(ROOT / "MAC_WORKER.ps1")
    return (
        f"$source=Get-Content -Raw -LiteralPath {script_path}; "
        "$cut=$source.IndexOf('if ($Action -eq \"configure\")'); "
        ". ([scriptblock]::Create($source.Substring(0,$cut))) -Action probe; "
        + body
    )


class MacWorkerTransportContractTests(unittest.TestCase):
    def test_uploads_use_initial_and_resumable_sftp(self) -> None:
        self.assertIn("function Invoke-SftpPut", SOURCE)
        self.assertIn("function Invoke-SftpReput", SOURCE)
        self.assertIn('"put -f "', SOURCE)
        self.assertIn('"reput -f "', SOURCE)
        upload_actions = SOURCE.partition('if ($Action -eq "pull")')[0]
        self.assertNotIn("& scp", upload_actions)

    def test_partial_upload_requires_sha_and_size_sidecar(self) -> None:
        self.assertIn('"$remotePart.expected.env"', SOURCE)
        self.assertIn("Refusing orphan partial upload", SOURCE)
        self.assertIn('grep -Fxq "sha256=$expected_sha"', SOURCE)
        self.assertIn('grep -Fxq "size=$expected_size"', SOURCE)
        self.assertIn('stat -f %z "$part"', SOURCE)
        self.assertIn('shasum -a 256 "$part"', SOURCE)

    def test_remote_assignments_are_single_array_elements(self) -> None:
        self.assertNotRegex(
            SOURCE,
            re.compile(
                r'^\s+"(?:archive|part|sidecar|expected_sha|expected_size|'
                r'destination|staging|runner_source|runner_target|runner_tmp)="\s+\+',
                re.MULTILINE,
            ),
        )
        self.assertNotRegex(
            SOURCE,
            re.compile(
                r'^\s+(?!\()["\'][^\r\n]*\+\s+\(Quote-Posix',
                re.MULTILINE,
            ),
        )

    def test_failed_transfer_preserves_local_archive(self) -> None:
        self.assertGreaterEqual(
            SOURCE.count("Archive preserved for exact SFTP resume"),
            2,
        )
        self.assertIn('$buildingArchive = "$archive.building"', SOURCE)

    def test_data_archive_identity_is_bound_to_manifest(self) -> None:
        self.assertIn(
            '"mac-data-$manifestHash.tar"',
            SOURCE,
        )
        self.assertIn("splits=train,validation locked_test_used=false", SOURCE)

    def test_mac_training_preflight_uses_real_train_config(self) -> None:
        self.assertIn('training = config["train"]', RUNNER)
        self.assertNotIn('training = config["training"]', RUNNER)

    def test_representative_smoke_is_always_tiny_and_hard_bounded(self) -> None:
        self.assertIn('"--smoke-test"', REMOTE_README)
        self.assertIn('"--representative-smoke"', REMOTE_README)
        self.assertIn("smoke_test != representative_smoke", RUNNER)
        self.assertIn("must leave at least 60 seconds", RUNNER)
        self.assertIn("WallTimeoutSeconds", SOURCE)
        self.assertIn("wallclock_exec.py", RUNNER)
        self.assertIn("process_group_alive", RUNNER)
        self.assertIn("orphaned_group_alive", RUNNER)
        self.assertIn("Duplicate controlled option", RUNNER)
        self.assertIn("Duplicate controlled flag", RUNNER)
        self.assertIn("allow_abbrev=False", TRAIN_SOURCE)

    def test_remote_worker_exposes_owned_stop_contract(self) -> None:
        self.assertIn('"configure", "pair", "probe", "sync-code", "sync-data",', SOURCE)
        self.assertIn('"bootstrap", "start", "stop", "status", "tail", "pull"', SOURCE)
        self.assertIn('if ($Action -eq "stop")', SOURCE)
        self.assertIn("Refusing stop because process ownership does not match", RUNNER)
        self.assertIn("Refusing stop because supervisor identity cannot be proven", RUNNER)
        self.assertIn("kill -TERM \"$supervisor_pid\"", RUNNER)
        self.assertIn("Supervised process handshake failed", RUNNER)
        self.assertIn("lock preserved", RUNNER)
        self.assertIn("Handshake failed with an owned group", RUNNER)
        self.assertIn('ps -ww -p "$supervisor_pid"', RUNNER)
        self.assertIn("stale_owner_cleanup=true", RUNNER)
        self.assertIn('printf \'active_owner=%s', RUNNER)
        self.assertIn("final_status=orphaned_group", RUNNER)
        self.assertIn('final_status" != orphaned_group', RUNNER)
        self.assertIn("Owned runner survived stop; lock preserved", RUNNER)

    def test_transfer_has_bounded_sleep_assertion_and_single_sftp_guard(self) -> None:
        self.assertIn("caffeinate -ims -t 21600", SOURCE)
        self.assertIn("function Assert-NoActiveSftp", SOURCE)
        self.assertIn("Local\\MidiMacWorkerSftp", SOURCE)
        self.assertIn("WaitOne(0)", SOURCE)
        self.assertIn("Refusing a second SFTP upload", SOURCE)

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_atomic_mutex_rejects_concurrent_process(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ready = pathlib.Path(directory) / "ready.txt"
            holder_script = _load_functions_script(
                "$mutex=Enter-SftpMutex; "
                f"[IO.File]::WriteAllText({_ps_quote(ready)}, 'ready'); "
                "try { Start-Sleep -Seconds 5 } finally { Exit-SftpMutex $mutex }"
            )
            holder = subprocess.Popen(
                [POWERSHELL, "-NoProfile", "-Command", holder_script],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                deadline = time.monotonic() + 10.0
                while not ready.exists() and time.monotonic() < deadline:
                    if holder.poll() is not None:
                        break
                    time.sleep(0.05)
                self.assertTrue(ready.exists(), "mutex holder did not start")
                contender = subprocess.run(
                    [
                        POWERSHELL,
                        "-NoProfile",
                        "-Command",
                        _load_functions_script(
                            "try { $mutex=Enter-SftpMutex; "
                            "Exit-SftpMutex $mutex; exit 0 } "
                            "catch { Write-Error $_; exit 9 }"
                        ),
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
                self.assertNotEqual(contender.returncode, 0)
                self.assertIn(
                    "owns the atomic SFTP mutex",
                    contender.stdout + contender.stderr,
                )
            finally:
                try:
                    holder.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    holder.kill()
                    holder.wait(timeout=5)

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_dry_run_rejects_locked_test_split_behaviorally(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = pathlib.Path(directory)
            config = temporary / "worker.json"
            manifest = temporary / "manifest.csv"
            config.write_text(
                json.dumps(
                    {
                        "host": "invalid.local",
                        "user": "nobody",
                        "port": 22,
                        "remote_root": "/Users/nobody/midi-worker",
                        "identity_file": "",
                        "local_workspace_root": str(ROOT),
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            manifest.write_text(
                "split,audio_path,labels_path\ntest,,\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    POWERSHELL,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ROOT / "MAC_WORKER.ps1"),
                    "sync-data",
                    "-ConfigPath",
                    str(config),
                    "-Manifest",
                    str(manifest),
                    "-DryRun",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "Only an exact train+validation manifest is allowed",
                result.stdout + result.stderr,
            )


if __name__ == "__main__":
    unittest.main()
