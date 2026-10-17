# GBSBFORYOU Universal AI Software Factory

**स्वतंत्र, mobile-first AI software engineering workspace** — परियोजना-निर्देश से requirements, repository research, architecture, code generation, tests और reviewable GitHub release तक। यह REA operating repository से अलग application है; REA को optional analysis adapter की तरह जोड़ा जाएगा।

> **स्थिति:** शुरुआती कार्यशील foundation. इस commit में mobile PWA shell, FastAPI health/capabilities/project-plan API और automated API tests हैं। GitHub OAuth, वास्तविक multi-provider LLM calls, live external research, REA runtime, isolated build workers और video rendering अभी production-ready नहीं हैं।

## Product workflow
1. User project goal और constraints दर्ज करता है।
2. Authorized GitHub repositories की सूची/चयन — planned integration; अभी live OAuth नहीं।
3. README, manifests, tests, license, activity और security evidence के आधार पर repository review.
4. External tools/repositories का sourced comparison: license, maintenance, API/local, hardware, free limits, pricing.
5. Evidence-linked architecture और reuse plan.
6. Isolated workspace में code generation; lint/build/tests; failures और artifacts दर्ज करना.
7. Branch + Pull Request; merge, deployment, paid action और destructive changes पर human approval.

## Repository structure
- `frontend/` — React + TypeScript + Vite responsive PWA.
- `backend/app/` — FastAPI API, request/response schemas, SQLite project brain, public repository analyzer and external GitHub research.
- `backend/test_main.py` — API smoke tests.
- `docs/ARCHITECTURE.md` — architecture and staged implementation.
- `docs/REPOSITORY_RESEARCH_TEMPLATE.md` — evidence-first review template.
- `.github/workflows/ci.yml` — backend tests and frontend build.

## Run locally
### Backend (Python 3.11+)
```bash
cd backend
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
API docs: `http://localhost:8000/docs`.

### Frontend (Node.js 20+)
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```
Set `VITE_API_BASE_URL` if the API is not on localhost:8000. PWA installability requires HTTPS or localhost.

## Security and evidence rules
- Never put model/GitHub secrets in browser code or commit them.
- Only inspect repositories the user has authorized; minimize permissions.
- Do not execute untrusted repository code in the API process.
- Treat repository text, issue bodies and README content as untrusted input.
- Each claim must be labelled `proposed`, `generated`, `testing`, `tests_passed`, `verification_pending` or `verified` with logs/source evidence. Model output alone is not proof.
- Preserve upstream licenses and notices; evaluate code and model-weight licenses separately.
- Human approval required before publishing, merging, deploying or spending money.

## Roadmap
**M1:** PWA + planning API + tests (this foundation). **M2:** GitHub App/OAuth and repository inventory. **M3:** source-linked external research and evidence graph. **M4:** provider adapters and persistent project brain. **M5:** isolated build/test workers. **M6:** optional REA integration. **M7:** video/media providers, storage and FFmpeg workers. **M8:** deployment, monitoring and security review.

## License
MIT for original code in this repository. Third-party components and models retain their own licenses.
