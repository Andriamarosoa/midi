from __future__ import annotations

import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "MAC_WORKER.ps1").read_text(encoding="utf-8")


class MacWorkerTransportContractTests(unittest.TestCase):
    def test_uploads_use_initial_and_resumable_sftp(self) -> None:
        self.assertIn("function Invoke-SftpPut", SOURCE)
        self.assertIn("function Invoke-SftpReput", SOURCE)
        self.assertIn('"put -f "', SOURCE)
        self.assertIn('"reput -f "', SOURCE)
        self.assertNotRegex(SOURCE, r"&\s+scp[^\n]+\$archive")

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

    def test_transfer_has_bounded_sleep_assertion_and_single_sftp_guard(self) -> None:
        self.assertIn("caffeinate -ims -t 21600", SOURCE)
        self.assertIn("function Assert-NoActiveSftp", SOURCE)
        self.assertIn("Refusing a second SFTP upload", SOURCE)


if __name__ == "__main__":
    unittest.main()
