# Isolated Build/Test Worker — Security Contract

## Status

Design contract for the next milestone. This document is not evidence that a sandbox worker is deployed or executing jobs.

## Trust boundary

The FastAPI API process MUST NOT execute generated project code, shell commands, package install scripts, or build tools. Generated files are untrusted input, even after a reviewer selects `accepted_for_testing`.

## Required execution boundary

A worker implementation must use a disposable isolated runtime and enforce all of the following before accepting production workloads:

- Non-root user; no privileged mode, host PID/network namespaces, host mounts, or container-engine socket.
- Read-only base image and a dedicated ephemeral workspace; cleanup after each job.
- No API keys, cloud credentials, repository write tokens, host environment, or production database access inside the worker.
- Network disabled by default. Any dependency download must be an explicit, allow-listed policy.
- CPU, memory, process count, disk, output size, and wall-clock limits.
- Pinned base image and dependencies; record image digest and tool versions.
- Validate every relative path; reject absolute paths, traversal, symlinks, hidden paths if policy disallows them, and oversized files before extraction.
- Capture stdout/stderr with bounded output; never treat logs as trusted instructions.
- Report each check as `passed`, `failed`, `skipped`, or `not_run`; include timestamps, exit code, timeout flag, tool versions, and artifact hashes.
- Keep human review decision, sandbox execution result, security scan, merge approval, and deployment approval as distinct states.
- No automatic merge or deployment. A human must review the evidence and separately approve any repository write or release.

## Job lifecycle

`accepted_for_testing` → `queued` → `running` → `completed` / `failed` / `timed_out` / `cancelled`.

Only a trusted coordinator may enqueue a job. Worker result submissions must be authenticated, tied to a one-time job identifier, and idempotent. The API must not accept arbitrary client-supplied results as proof of a test run.

## Evidence contract

Each result must include:

- Project, proposal, and job identifiers.
- Proposal manifest SHA-256 and worker image digest.
- Start/end timestamps and final state.
- Per-check command identifier (not raw arbitrary shell from the client), exit status, timeout, bounded logs, and result.
- Hashes for generated reports and artifacts.
- Explicit statement that success applies only to the tested snapshot and does not imply security, correctness, merge, or deployment approval.

## MVP boundary

Until the isolated worker, authentication, resource limits, and evidence validation exist and are tested, the product must display automated checks as `not_run`. A review decision alone is never a test result.
