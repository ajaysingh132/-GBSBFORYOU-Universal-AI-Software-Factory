"""Read-only, deterministic manifest for AI code proposals.

No generated file is written, imported, executed, or committed by this module.
"""
import hashlib
from pathlib import PurePosixPath


def build_proposal_manifest(files: list[dict]) -> dict:
    if not isinstance(files, list) or not 1 <= len(files) <= 10:
        raise ValueError("Expected 1–10 proposed files.")
    seen = set()
    entries = []
    total_bytes = 0
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("content"), str):
            raise ValueError("Each proposed file must contain text path and content.")
        raw = item["path"]
        if "\\" in raw or "\x00" in raw or ":" in raw or raw.startswith(("/", "~")):
            raise ValueError("Unsafe file path.")
        parts = raw.split("/")
        if any(not part or part in {".", ".."} or part.startswith(".") for part in parts):
            raise ValueError("Hidden, empty, or traversal path segments are forbidden.")
        if PurePosixPath(raw).is_absolute() or raw.lower().endswith((".pem", ".key", ".p12", ".pfx")):
            raise ValueError("Absolute paths and key files are forbidden.")
        if raw in seen:
            raise ValueError("Duplicate proposed file path.")
        seen.add(raw)
        data = item["content"].encode("utf-8")
        if len(item["content"]) > 20000:
            raise ValueError("File content exceeds limit.")
        total_bytes += len(data)
        entries.append({
            "path": raw,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "lines": len(item["content"].splitlines()),
        })
    if sum(len(item["content"]) for item in files) > 60000:
        raise ValueError("Proposal content exceeds limit.")
    return {
        "files": entries,
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "status": "verification_pending",
        "checks": {
            "structure_and_paths": "passed",
            "source_review": "not_run",
            "isolated_build": "not_run",
            "automated_tests": "not_run",
            "security_scan": "not_run",
        },
        "evidence_note": "Hashes describe saved proposal text only; no files were written or tested.",
    }
