"""Validation helpers for untrusted isolated-worker job manifests.

This module validates metadata only; it never executes code or shell commands.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

MAX_FILES = 100
MAX_FILE_BYTES = 200_000
MAX_TOTAL_BYTES = 1_000_000
CHECK_STATES = {"passed", "failed", "skipped", "not_run"}
JOB_STATES = {"queued", "running", "completed", "failed", "timed_out", "cancelled"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class WorkerProtocolError(ValueError):
    """Raised when a worker manifest or result violates the contract."""


def validate_relative_path(path: Any) -> str:
    """Reject absolute, traversal, drive-qualified, NUL, and empty paths."""
    if not isinstance(path, str) or not path or "\x00" in path:
        raise WorkerProtocolError("path must be a non-empty text path")
    if len(path) > 240 or "\\" in path:
        raise WorkerProtocolError("path is too long or uses unsupported separators")
    posix = PurePosixPath(path)
    windows = PureWindowsPath(path)
    if posix.is_absolute() or windows.is_absolute() or windows.drive:
        raise WorkerProtocolError("absolute or drive-qualified paths are not allowed")
    if any(part in {"", ".", ".."} for part in path.split("/")):
        raise WorkerProtocolError("path traversal or empty path segments are not allowed")
    if any(part.startswith(".") for part in posix.parts):
        raise WorkerProtocolError("hidden path segments are not allowed")
    return path


def validate_job_manifest(manifest: Any) -> dict:
    """Validate a JSON-like proposal manifest without extracting or executing it."""
    if not isinstance(manifest, dict):
        raise WorkerProtocolError("manifest must be an object")
    proposal_id = manifest.get("proposal_id")
    manifest_hash = manifest.get("manifest_sha256")
    files = manifest.get("files")
    if not isinstance(proposal_id, str) or not proposal_id.strip() or len(proposal_id) > 128:
        raise WorkerProtocolError("proposal_id is required")
    if not isinstance(manifest_hash, str) or not _SHA256.fullmatch(manifest_hash):
        raise WorkerProtocolError("manifest_sha256 must be a lowercase SHA-256 digest")
    if not isinstance(files, list) or not files or len(files) > MAX_FILES:
        raise WorkerProtocolError(f"files must contain 1 to {MAX_FILES} entries")
    seen: set[str] = set()
    total = 0
    normalized = []
    for item in files:
        if not isinstance(item, dict):
            raise WorkerProtocolError("each file entry must be an object")
        path = validate_relative_path(item.get("path"))
        content = item.get("content")
        if path in seen:
            raise WorkerProtocolError("duplicate file paths are not allowed")
        if not isinstance(content, str):
            raise WorkerProtocolError("file content must be text")
        size = len(content.encode("utf-8"))
        if size > MAX_FILE_BYTES:
            raise WorkerProtocolError(f"file exceeds {MAX_FILE_BYTES} bytes")
        total += size
        if total > MAX_TOTAL_BYTES:
            raise WorkerProtocolError(f"manifest exceeds {MAX_TOTAL_BYTES} bytes")
        seen.add(path)
        normalized.append({"path": path, "content": content, "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()})
    return {
        "proposal_id": proposal_id,
        "manifest_sha256": manifest_hash,
        "files": normalized,
        "total_bytes": total,
    }


def validate_worker_result(result: Any) -> dict:
    """Validate a worker's claimed result shape; callers must authenticate the sender."""
    if not isinstance(result, dict):
        raise WorkerProtocolError("worker result must be an object")
    job_id = result.get("job_id")
    state = result.get("state")
    manifest_hash = result.get("manifest_sha256")
    checks = result.get("checks")
    if not isinstance(job_id, str) or not job_id.strip() or len(job_id) > 128:
        raise WorkerProtocolError("job_id is required")
    if state not in JOB_STATES - {"queued", "running"}:
        raise WorkerProtocolError("state must be a terminal job state")
    if not isinstance(manifest_hash, str) or not _SHA256.fullmatch(manifest_hash):
        raise WorkerProtocolError("manifest_sha256 must be a lowercase SHA-256 digest")
    if not isinstance(checks, list) or len(checks) > 50:
        raise WorkerProtocolError("checks must be a list with at most 50 entries")
    for check in checks:
        if not isinstance(check, dict) or check.get("state") not in CHECK_STATES:
            raise WorkerProtocolError("each check must have a valid state")
        if not isinstance(check.get("name"), str) or not check["name"].strip():
            raise WorkerProtocolError("each check requires a name")
        if "command" in check:
            raise WorkerProtocolError("raw commands must not be accepted in worker results")
    return result
