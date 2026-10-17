# Architecture and implementation boundaries

## Target architecture
Mobile PWA (React/TypeScript) -> FastAPI -> Project Brain (PostgreSQL); authorized GitHub connector; sourced external research + evidence ledger; provider-neutral AI router; optional REA worker; queue -> disposable build/test workers; reviewable GitHub branch/PR with human approval. Video-specific layer later adds object storage and FFmpeg/render workers.

## Safety boundaries
- Never run arbitrary repository code in the API process.
- Worker containers need CPU, memory, time, filesystem and network limits.
- Treat repository content and external search results as untrusted input.
- Secrets remain server-side and must be redacted from logs.
- Never merge, deploy, purchase or delete without explicit approval.
- Store source URL, retrieval timestamp, version/ref, license evidence and confidence for research conclusions.

## Milestones
1. Mobile dashboard and planning API.
2. GitHub App/OAuth, repo inventory and explicit selection.
3. External research with source evidence and license checks.
4. PostgreSQL project brain, queue and provider adapters.
5. Sandboxed code generation/build/test loop.
6. Optional REA adapter after runtime dependencies are validated.
7. Video workflows: script/storyboard, media adapters, TTS/voice, assets, FFmpeg rendering and artifact storage.
8. Auth, monitoring, deployment and security review.

Evidence statuses: proposed -> generated -> testing -> tests_passed -> verified; use verification_pending when evidence is missing.
