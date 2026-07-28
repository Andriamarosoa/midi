"""Query the exact server-confirmed progress of a Kaggle resumable upload.

The Kaggle CLI stores resumable-upload metadata under the system temporary
directory. This tool sends the protocol's status request to that session and
reports acknowledged bytes without exposing the signed upload URL.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


RANGE_PATTERN = re.compile(r"^bytes=0-(\d+)$")


def upload_info_path(
    upload_path: Path, *, upload_info_dir: Path | None = None
) -> Path:
    """Return the sidecar path used by Kaggle's resumable uploader."""
    resolved = upload_path.resolve()
    directory = (
        upload_info_dir
        if upload_info_dir is not None
        else Path(tempfile.gettempdir()) / ".kaggle" / "uploads"
    )
    filename = str(resolved).replace(os.path.sep, "_").replace(":", "_")
    return directory / f"{filename}.json"


def uploaded_bytes_from_range(value: str | None) -> int:
    """Convert a resumable-upload Range header to an acknowledged byte count."""
    if value is None:
        return 0
    match = RANGE_PATTERN.fullmatch(value.strip())
    if match is None:
        raise ValueError("Unexpected resumable-upload Range header.")
    return int(match.group(1)) + 1


def _load_session(
    upload_path: Path, *, upload_info_dir: Path | None = None
) -> tuple[str, int]:
    resolved = upload_path.resolve()
    sidecar = upload_info_path(
        resolved, upload_info_dir=upload_info_dir
    )
    if not sidecar.is_file():
        raise FileNotFoundError(
            f"Kaggle resumable-upload sidecar not found: {sidecar}"
        )
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    recorded_path = Path(payload["path"]).resolve()
    if recorded_path != resolved:
        raise ValueError("Kaggle upload sidecar points to another file.")
    request = payload["start_blob_upload_request"]
    response = payload["start_blob_upload_response"]
    total_bytes = int(request["contentLength"])
    if total_bytes != resolved.stat().st_size:
        raise ValueError("Upload file size no longer matches its Kaggle sidecar.")
    create_url = str(response["createUrl"])
    if not create_url.startswith("https://"):
        raise ValueError("Kaggle resumable-upload URL is not HTTPS.")
    return create_url, total_bytes


def query_upload_progress(
    upload_path: Path,
    *,
    upload_info_dir: Path | None = None,
    opener: Callable[..., Any] = urlopen,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Return exact bytes acknowledged by the resumable-upload server."""
    create_url, total_bytes = _load_session(
        upload_path, upload_info_dir=upload_info_dir
    )
    request = Request(
        create_url,
        data=b"",
        method="PUT",
        headers={
            "Content-Length": "0",
            "Content-Range": f"bytes */{total_bytes}",
        },
    )
    try:
        response = opener(request, timeout=timeout_seconds)
    except HTTPError as error:
        response = error
    except URLError as error:
        raise RuntimeError(
            f"Cannot reach the Kaggle upload server: {error.reason}"
        ) from None

    try:
        status_code = int(response.code)
        if status_code in (200, 201):
            status = "complete"
            uploaded_bytes = total_bytes
        elif status_code == 308:
            status = "uploading"
            uploaded_bytes = uploaded_bytes_from_range(
                response.headers.get("Range")
            )
        elif status_code == 404:
            status = "expired"
            uploaded_bytes = 0
        else:
            raise RuntimeError(
                f"Unexpected Kaggle upload status: HTTP {status_code}"
            )
    finally:
        response.close()

    uploaded_bytes = min(uploaded_bytes, total_bytes)
    return {
        "status": status,
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "bytes_uploaded": uploaded_bytes,
        "total_bytes": total_bytes,
        "remaining_bytes": total_bytes - uploaded_bytes,
        "percent": round(100.0 * uploaded_bytes / total_bytes, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    args = parser.parse_args()
    try:
        progress = query_upload_progress(
            args.path, timeout_seconds=args.timeout_seconds
        )
    except (FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
        print(json.dumps({"status": "unavailable", "error": str(error)}))
        return 1
    print(json.dumps(progress, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
