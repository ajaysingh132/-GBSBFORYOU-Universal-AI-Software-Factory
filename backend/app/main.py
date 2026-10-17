import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import ProjectPlanRequest, ProjectPlanResponse, PlanStep
from .providers import configured_providers, generate_text, ProviderNotImplemented
from .repository_intel import analyze_public_repository, RepositoryAnalysisError
from .external_research import search_github_repositories, ResearchError
from .project_store import create_project, list_projects, get_project, save_blueprint, list_blueprints, create_task, list_tasks, update_task

app = FastAPI(
    title="GBSBFORYOU Universal AI Software Factory API",
    version="0.1.0",
    description="Mobile-first, evidence-led software project planning API.",
)
origins = [
    item.strip()
    for item in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "app": "GBSBFORYOU Universal AI Software Factory",
        "version": "0.1.0",
    }


@app.post("/api/v1/ai/generate", tags=["ai"])
async def ai_generate(payload: dict):
    provider = payload.get("provider", "")
    prompt = payload.get("prompt", "")
    if not isinstance(provider, str) or provider not in {
        "openai", "anthropic", "google_gemini", "deepseek", "openrouter"
    }:
        raise HTTPException(status_code=422, detail="Unsupported provider.")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 30000:
        raise HTTPException(status_code=422, detail="prompt must contain 1–30000 characters.")
    try:
        return await generate_text(provider, prompt)
    except ProviderNotImplemented as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/projects/blueprint", tags=["projects"])
async def create_ai_blueprint(payload: dict):
    name = payload.get("name", "")
    goal = payload.get("goal", "")
    provider = payload.get("provider", "")
    constraints = payload.get("constraints", [])
    allowed = {"openai", "anthropic", "google_gemini", "deepseek", "openrouter"}
    if not isinstance(name, str) or not 2 <= len(name.strip()) <= 100:
        raise HTTPException(status_code=422, detail="name must contain 2–100 characters.")
    if not isinstance(goal, str) or not 10 <= len(goal.strip()) <= 5000:
        raise HTTPException(status_code=422, detail="goal must contain 10–5000 characters.")
    if provider not in allowed:
        raise HTTPException(status_code=422, detail="Unsupported provider.")
    if not isinstance(constraints, list) or any(not isinstance(x, str) for x in constraints[:30]):
        raise HTTPException(status_code=422, detail="constraints must be a list of text values.")
    instruction = (
        "You are the planning engine of GBSBFORYOU Universal AI Software Factory. "
        "Create a concrete, staged implementation blueprint for the user's software project. "
        "Use headings: Goal and acceptance criteria; Existing repositories to inspect; "
        "Recommended architecture; Reusable tools and libraries to research; "
        "Milestones; Test and security plan; Risks and unknowns. "
        "Prefer free/open-source options when suitable, but never claim a tool is free without evidence. "
        "Do not claim repositories were inspected, code was written, tests passed, or deployment occurred. "
        "Label assumptions and verification tasks explicitly. Do not include secrets or ask users to paste API keys.\n\n"
        f"Project name: {name.strip()}\nGoal: {goal.strip()}\n"
        f"Constraints: {', '.join(constraints[:30]) if constraints else 'None supplied'}"
    )
    try:
        result = await generate_text(provider, instruction)
        evidence_note = "This is an AI-generated plan, not proof that repositories were inspected, code was generated, tests passed, or deployment succeeded."
        project = create_project(
            name=name.strip(),
            goal=goal.strip(),
            constraints=constraints[:30],
            repository_urls=[],
        )
        saved = save_blueprint(
            project_id=project["id"],
            provider=result["provider"],
            model=result["model"],
            content=result["text"],
            evidence_note=evidence_note,
        )
        return {
            "project_id": project["id"],
            "blueprint_id": saved["id"] if saved else None,
            "project_name": name.strip(),
            "provider": result["provider"],
            "model": result["model"],
            "status": "generated_and_saved" if saved else "generated_not_saved",
            "blueprint": result["text"],
            "evidence_note": evidence_note,
        }
    except ProviderNotImplemented as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/projects/research-blueprint", tags=["projects"])
async def create_research_blueprint(payload: dict):
    """Create a blueprint informed by public repository evidence; no code is generated here."""
    name = payload.get("name", "")
    goal = payload.get("goal", "")
    provider = payload.get("provider", "")
    constraints = payload.get("constraints", [])
    repository_urls = payload.get("repository_urls", [])
    research_queries = payload.get("research_queries", [])
    allowed = {"openai", "anthropic", "google_gemini", "deepseek", "openrouter"}
    if not isinstance(name, str) or not 2 <= len(name.strip()) <= 100:
        raise HTTPException(status_code=422, detail="name must contain 2–100 characters.")
    if not isinstance(goal, str) or not 10 <= len(goal.strip()) <= 5000:
        raise HTTPException(status_code=422, detail="goal must contain 10–5000 characters.")
    if provider not in allowed:
        raise HTTPException(status_code=422, detail="Unsupported provider.")
    if not isinstance(constraints, list) or len(constraints) > 30 or any(not isinstance(x, str) for x in constraints):
        raise HTTPException(status_code=422, detail="constraints must contain at most 30 text values.")
    if not isinstance(repository_urls, list) or len(repository_urls) > 10 or any(not isinstance(x, str) for x in repository_urls):
        raise HTTPException(status_code=422, detail="repository_urls must contain at most 10 URL strings.")
    if not isinstance(research_queries, list) or len(research_queries) > 5 or any(not isinstance(x, str) for x in research_queries):
        raise HTTPException(status_code=422, detail="research_queries must contain at most 5 text values.")
    repository_evidence = []
    research_evidence = []
    for url in repository_urls:
        try:
            evidence = await analyze_public_repository(url)
            repository_evidence.append(evidence)
        except (RepositoryAnalysisError, ValueError) as exc:
            repository_evidence.append({"requested_url": url, "status": "not_verified", "reason": str(exc)})
        except Exception:
            repository_evidence.append({"requested_url": url, "status": "not_verified", "reason": "Unexpected repository analysis failure."})
    for query in research_queries:
        try:
            evidence = await search_github_repositories(query, limit=5)
            research_evidence.append(evidence)
        except (ResearchError, ValueError) as exc:
            research_evidence.append({"query": query, "status": "not_verified", "reason": str(exc)})
        except Exception:
            research_evidence.append({"query": query, "status": "not_verified", "reason": "Unexpected external research failure."})
    evidence_bundle = {
        "user_supplied_public_repository_reviews": repository_evidence,
        "public_github_searches": research_evidence,
        "scope_note": "Only returned public GitHub metadata and repository analyzer outputs are available. This is not a complete source-code, dependency, security, model-license or commercial-use audit."
    }
    instruction = (
        "You are the evidence-led planning engine of GBSBFORYOU Universal AI Software Factory. "
        "Create an implementation blueprint informed by the supplied evidence. Separate observed facts, "
        "inferences and items still requiring verification. Cite repository URLs in the text. "
        "Treat missing license as no explicit reuse permission. Do not say private repositories were accessed. "
        "Do not claim code was generated, tests passed or deployment occurred. "
        "Include sections: Requirements and acceptance criteria; Evidence reviewed; Candidate reuse options and license caveats; "
        "Architecture; Milestones; Test/security plan; Risks and unresolved checks. Prefer free/open-source options only when evidence supports it.\n\n"
        f"Project: {name.strip()}\nGoal: {goal.strip()}\n"
        f"Constraints: {', '.join(constraints) if constraints else 'None supplied'}\n"
        f"Evidence JSON: {__import__('json').dumps(evidence_bundle, ensure_ascii=False)[:22000]}"
    )
    try:
        result = await generate_text(provider, instruction)
    except ProviderNotImplemented as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    evidence_note = "AI-generated plan based on the public repository analysis/search results returned in this request. It is not a complete code/security/license audit and does not prove implementation or tests."
    project = create_project(
        name=name.strip(), goal=goal.strip(), constraints=constraints,
        repository_urls=repository_urls,
    )
    saved = save_blueprint(project_id=project["id"], provider=result["provider"],
        model=result["model"], content=result["text"], evidence_note=evidence_note)
    return {
        "project_id": project["id"], "blueprint_id": saved["id"] if saved else None,
        "project_name": name.strip(), "provider": result["provider"], "model": result["model"],
        "status": "generated_and_saved" if saved else "generated_not_saved",
        "blueprint": result["text"], "evidence_note": evidence_note,
        "evidence": evidence_bundle
    }


@app.get("/api/v1/capabilities", tags=["system"])
def capabilities():
    return {
        "providers": configured_providers(),
        "implemented": [
            "health",
            "capabilities",
            "project-plan scaffold",
            "SQLite persistent project brain",
            "public GitHub repository metadata analyzer",
            "source-linked public GitHub repository research",
            "server-side AI text generation adapters for five providers",
            "AI-generated project blueprint endpoint with persistence",
            "persistent project task tracking with evidence-gated verification",
        ],
        "planned": [
            "GitHub OAuth and private repository inventory",
            "source-cited external research",
            "REA runtime adapter",
            "isolated build/test workers",
            "video/media generation",
        ],
    }


@app.get("/api/v1/research/github", tags=["research"])
async def research_github(q: str, limit: int = 8):
    try:
        return await search_github_repositories(q, limit)
    except ResearchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="GitHub search failed; retry later.",
        ) from exc


@app.post("/api/v1/projects", tags=["projects"])
def save_project(payload: ProjectPlanRequest):
    return create_project(
        name=payload.name,
        goal=payload.goal,
        constraints=payload.constraints,
        repository_urls=[str(url) for url in payload.repository_urls],
    )


@app.get("/api/v1/projects", tags=["projects"])
def get_projects(limit: int = 50):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    return {"projects": list_projects(limit)}


@app.post("/api/v1/projects/{project_id}/tasks", tags=["tasks"])
def add_project_task(project_id: str, payload: dict):
    title = payload.get("title", "")
    description = payload.get("description", "")
    if not isinstance(title, str) or not 3 <= len(title.strip()) <= 160:
        raise HTTPException(status_code=422, detail="title must contain 3–160 characters.")
    if not isinstance(description, str) or len(description) > 2000:
        raise HTTPException(status_code=422, detail="description must be 2000 characters or fewer.")
    task = create_task(project_id, title, description)
    if task is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return task


@app.post("/api/v1/projects/{project_id}/tasks/from-blueprint", tags=["tasks"])
async def create_tasks_from_blueprint(project_id: str, payload: dict):
    """Ask a configured provider to convert the latest saved blueprint into actionable tasks."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    history = list_blueprints(project_id)
    if not history:
        raise HTTPException(status_code=409, detail="Create and save a blueprint before generating tasks.")
    provider = payload.get("provider", history[0]["provider"])
    allowed = {"openai", "anthropic", "google_gemini", "deepseek", "openrouter"}
    if provider not in allowed:
        raise HTTPException(status_code=422, detail="Unsupported provider.")
    blueprint = history[0]["content"]
    instruction = (
        "Convert this software project blueprint into 4 to 8 actionable implementation tasks. "
        "Return ONLY a JSON array, each item with string keys title and description. "
        "Titles must be concise, testable and distinct. Do not claim any task is completed or verified. "
        "Include research/license review, architecture, implementation, tests and deployment-readiness where relevant. "
        "Project goal: " + project["goal"] + "\nBlueprint: " + blueprint[:14000]
    )
    try:
        result = await generate_text(provider, instruction)
    except ProviderNotImplemented as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    import json
    try:
        text_value = result["text"].strip()
        if text_value.startswith("```"):
            text_value = text_value.split("\n", 1)[-1]
            if text_value.endswith("```"):
                text_value = text_value[:-3].strip()
        start, end = text_value.find("["), text_value.rfind("]")
        items = json.loads(text_value[start:end + 1]) if start >= 0 and end > start else None
        if not isinstance(items, list) or not 1 <= len(items) <= 12:
            raise ValueError("Expected a JSON array with 1–12 tasks.")
        tasks = []
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("title"), str) or not 3 <= len(item["title"].strip()) <= 160:
                raise ValueError("Each task must have a title of 3–160 characters.")
            description = item.get("description", "")
            if not isinstance(description, str) or len(description) > 2000:
                raise ValueError("Task descriptions must be text up to 2000 characters.")
            tasks.append((item["title"].strip(), description.strip()))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Provider did not return a valid task JSON array; no tasks were created.") from exc
    created = []
    for title, description in tasks:
        task = create_task(project_id, title, description)
        if task:
            created.append(task)
    return {"project_id": project_id, "provider": result["provider"], "model": result["model"], "created_count": len(created), "tasks": created, "status": "proposed", "evidence_note": "AI-proposed tasks only; each task requires implementation and evidence before verification."}


@app.get("/api/v1/projects/{project_id}/tasks", tags=["tasks"])
def get_project_tasks(project_id: str):
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project_id": project_id, "tasks": list_tasks(project_id)}


@app.patch("/api/v1/projects/{project_id}/tasks/{task_id}", tags=["tasks"])
def patch_project_task(project_id: str, task_id: str, payload: dict):
    status = payload.get("status", "")
    evidence = payload.get("evidence", "")
    if not isinstance(status, str) or not isinstance(evidence, str):
        raise HTTPException(status_code=422, detail="status and evidence must be text.")
    try:
        task = update_task(project_id, task_id, status, evidence)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if task is None:
        raise HTTPException(status_code=404, detail="Task or project not found")
    return task


@app.get("/api/v1/projects/{project_id}/blueprints", tags=["projects"])
def get_project_blueprints(project_id: str):
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project_id": project_id, "blueprints": list_blueprints(project_id)}


@app.get("/api/v1/projects/{project_id}", tags=["projects"])
def get_project_detail(project_id: str):
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.post("/api/v1/repositories/analyze", tags=["repositories"])
async def analyze_repository(payload: dict):
    url = payload.get("url", "")
    if not isinstance(url, str) or not url:
        raise HTTPException(
            status_code=422,
            detail="A public GitHub repository URL is required.",
        )
    try:
        return await analyze_public_repository(url)
    except RepositoryAnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="GitHub API request failed; retry later.",
        ) from exc


@app.post(
    "/api/v1/projects/plan",
    response_model=ProjectPlanResponse,
    tags=["projects"],
)
def create_project_plan(payload: ProjectPlanRequest):
    has_repos = bool(payload.repository_urls)
    steps = [
        PlanStep(
            id="requirements",
            title="Requirements and acceptance criteria",
            description="Convert the request into user stories, constraints and measurable acceptance criteria.",
        ),
        PlanStep(
            id="repo-scan",
            title="Authorized repository intelligence",
            description=(
                f"Review {len(payload.repository_urls)} supplied repository URL(s) for manifests, architecture, tests and licenses."
                if has_repos
                else "Connect GitHub and select authorized repositories before source inspection."
            ),
            status="ready" if has_repos else "blocked",
        ),
        PlanStep(
            id="research",
            title="External tools and open-source research",
            description="Compare source evidence, release activity, license, runtime needs, free-tier limits and costs.",
        ),
        PlanStep(
            id="architecture",
            title="Architecture and reuse plan",
            description="Map requirements to reusable components, new code, risks and unresolved decisions.",
        ),
        PlanStep(
            id="implementation",
            title="Generate code in an isolated workspace",
            description="Create incremental changes in a branch; do not execute untrusted code inside the API process.",
        ),
        PlanStep(
            id="verification",
            title="Build, tests and evidence report",
            description="Run named checks in a disposable worker and report actual logs, failures and unverified claims.",
        ),
        PlanStep(
            id="release",
            title="Reviewable release proposal",
            description="Prepare a pull request and changelog.",
            needs_approval=True,
        ),
    ]
    return ProjectPlanResponse(
        project_name=payload.name,
        summary=f"Planning scaffold for: {payload.goal}",
        assumptions=[
            "This endpoint generates a plan only; it does not inspect repositories or generate project code.",
            "GitHub access, external research, model credentials and worker infrastructure must be configured separately.",
            "A feature remains proposed or verification_pending until evidence is recorded.",
        ],
        steps=steps,
        evidence_policy="Never mark a feature verified from model output alone; attach source, version and test evidence.",
    )
