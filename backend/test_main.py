from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_health():
 r=client.get("/health"); assert r.status_code==200 and r.json()["status"]=="ok"
def test_capabilities_are_honest():
 d=client.get("/api/v1/capabilities").json(); assert "project-plan scaffold" in d["implemented"]; assert "REA runtime adapter" in d["planned"]
def test_project_plan():
 r=client.post("/api/v1/projects/plan",json={"name":"Video Studio","goal":"Build a mobile-first AI video creation application"}); assert r.status_code==200; d=r.json(); assert d["status"]=="proposed"; assert any(s["id"]=="verification" for s in d["steps"]); assert any(s["needs_approval"] for s in d["steps"])
def test_short_goal_rejected():
 assert client.post("/api/v1/projects/plan",json={"name":"Test","goal":"short"}).status_code==422


def test_repository_url_parser():
    from app.repository_intel import parse_github_repo
    assert parse_github_repo("https://github.com/owner/project.git") == ("owner", "project")

def test_repository_url_parser_rejects_other_hosts():
    import pytest
    from app.repository_intel import parse_github_repo, RepositoryAnalysisError
    with pytest.raises(RepositoryAnalysisError):
        parse_github_repo("https://example.com/owner/project")

def test_repository_endpoint_requires_url():
    response = client.post("/api/v1/repositories/analyze", json={})
    assert response.status_code == 422
    assert "URL" in response.json()["detail"]

def test_external_research_rejects_short_query():
    response = client.get("/api/v1/research/github", params={"q": "ai"})
    assert response.status_code == 422
    assert "3 characters" in response.json()["detail"]

def test_external_research_rejects_missing_query():
    response = client.get("/api/v1/research/github")
    assert response.status_code == 422

def test_project_brain_persists_and_reads_projects(tmp_path, monkeypatch):
    monkeypatch.setenv("FACTORY_DB_PATH", str(tmp_path / "factory-test.db"))
    payload = {
        "name": "Video Studio",
        "goal": "Build a mobile-first AI video creation application",
        "constraints": ["prefer free tools"],
        "repository_urls": [],
    }
    created = client.post("/api/v1/projects", json=payload)
    assert created.status_code == 200
    project = created.json()
    assert project["name"] == "Video Studio"
    assert project["status"] == "proposed"
    listed = client.get("/api/v1/projects")
    assert listed.status_code == 200
    assert any(item["id"] == project["id"] for item in listed.json()["projects"])
    detail = client.get(f"/api/v1/projects/{project['id']}")
    assert detail.status_code == 200
    assert detail.json()["goal"] == payload["goal"]

def test_project_brain_unknown_id_returns_404():
    response = client.get("/api/v1/projects/does-not-exist")
    assert response.status_code == 404

def test_project_brain_limit_validation():
    assert client.get("/api/v1/projects", params={"limit": 101}).status_code == 422

def test_ai_generate_rejects_unknown_provider():
    response = client.post("/api/v1/ai/generate", json={"provider": "unknown", "prompt": "hello"})
    assert response.status_code == 422

def test_ai_generate_rejects_empty_prompt():
    response = client.post("/api/v1/ai/generate", json={"provider": "openai", "prompt": "  "})
    assert response.status_code == 422

def test_ai_generate_reports_unconfigured_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/v1/ai/generate", json={"provider": "openai", "prompt": "Write a hello world app"})
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]

def test_ai_blueprint_validates_project_goal():
    response = client.post("/api/v1/projects/blueprint", json={
        "name": "Video Studio", "goal": "Build a mobile-first AI video tool",
        "provider": "openai", "constraints": []
    })
    assert response.status_code == 503 or response.status_code == 200

def test_ai_blueprint_uses_provider_and_marks_output_as_plan(monkeypatch, tmp_path):
    import app.main as main_module
    monkeypatch.setenv("FACTORY_DB_PATH", str(tmp_path / "blueprints.db"))
    async def fake_generate(provider, prompt):
        assert provider == "openai"
        assert "Do not claim repositories were inspected" in prompt
        return {"provider": provider, "model": "test-model", "text": "Milestone 1: build and test."}
    monkeypatch.setattr(main_module, "generate_text", fake_generate)
    response = client.post("/api/v1/projects/blueprint", json={
        "name": "Video Studio",
        "goal": "Build a mobile-first AI video creation application",
        "provider": "openai",
        "constraints": ["prefer free tools"]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "generated_and_saved"
    assert data["project_id"]
    assert data["blueprint_id"]
    assert data["provider"] == "openai"
    assert "not proof" in data["evidence_note"]

def test_ai_blueprint_rejects_unsupported_provider():
    response = client.post("/api/v1/projects/blueprint", json={
        "name": "Video Studio",
        "goal": "Build a mobile-first AI video creation application",
        "provider": "unsupported"
    })
    assert response.status_code == 422


def test_blueprint_history_requires_existing_project(tmp_path, monkeypatch):
    monkeypatch.setenv("FACTORY_DB_PATH", str(tmp_path / "history.db"))
    response = client.get("/api/v1/projects/missing-project/blueprints")
    assert response.status_code == 404


def test_project_store_saves_and_lists_blueprints(tmp_path, monkeypatch):
    from app.project_store import create_project, save_blueprint, list_blueprints
    monkeypatch.setenv("FACTORY_DB_PATH", str(tmp_path / "store-blueprints.db"))
    project = create_project("Studio", "Build a video tool", [], [])
    saved = save_blueprint(project["id"], "openai", "test-model", "Milestone plan", "Plan only")
    assert saved is not None
    history = list_blueprints(project["id"])
    assert len(history) == 1
    assert history[0]["content"] == "Milestone plan"
    assert history[0]["provider"] == "openai"


def test_research_blueprint_validates_repository_and_query_limits():
    response = client.post("/api/v1/projects/research-blueprint", json={
        "name": "Video Studio", "goal": "Build a mobile-first AI video creation application",
        "provider": "openai", "repository_urls": ["https://github.com/a/b"] * 11,
        "research_queries": []
    })
    assert response.status_code == 422


def test_research_blueprint_combines_evidence_and_persists(monkeypatch, tmp_path):
    import app.main as main_module
    monkeypatch.setenv("FACTORY_DB_PATH", str(tmp_path / "research-blueprint.db"))
    async def fake_repo(url):
        return {"repository": url, "license": "MIT", "files": ["README.md"], "status": "analyzed"}
    async def fake_search(query, limit=5):
        return {"query": query, "results": [{"name": "org/tool", "url": "https://github.com/org/tool", "license_spdx": "MIT"}]}
    async def fake_generate(provider, prompt):
        assert "org/tool" in prompt
        assert "https://github.com/a/repo" in prompt
        return {"provider": provider, "model": "test-model", "text": "Evidence-informed blueprint"}
    monkeypatch.setattr(main_module, "analyze_public_repository", fake_repo)
    monkeypatch.setattr(main_module, "search_github_repositories", fake_search)
    monkeypatch.setattr(main_module, "generate_text", fake_generate)
    response = client.post("/api/v1/projects/research-blueprint", json={
        "name": "Video Studio",
        "goal": "Build a mobile-first AI video creation application",
        "provider": "openai",
        "constraints": ["prefer free tools"],
        "repository_urls": ["https://github.com/a/repo"],
        "research_queries": ["AI video generation"]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "generated_and_saved"
    assert data["evidence"]["user_supplied_public_repository_reviews"][0]["status"] == "analyzed"
    assert data["evidence"]["public_github_searches"][0]["results"][0]["name"] == "org/tool"
    assert data["blueprint"] == "Evidence-informed blueprint"


def test_project_task_lifecycle_and_evidence_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("FACTORY_DB_PATH", str(tmp_path / "tasks.db"))
    created = client.post("/api/v1/projects", json={
        "name": "Task Project", "goal": "Build a mobile-first app",
        "constraints": [], "repository_urls": []
    })
    assert created.status_code == 200
    project_id = created.json()["id"]
    task_response = client.post(f"/api/v1/projects/{project_id}/tasks", json={
        "title": "Review repository license", "description": "Check the actual license file."
    })
    assert task_response.status_code == 200
    task = task_response.json()
    assert task["status"] == "proposed"
    blocked = client.patch(f"/api/v1/projects/{project_id}/tasks/{task['id']}", json={
        "status": "verified", "evidence": ""
    })
    assert blocked.status_code == 422
    verified = client.patch(f"/api/v1/projects/{project_id}/tasks/{task['id']}", json={
        "status": "verified", "evidence": "Reviewed LICENSE file at commit abc123"
    })
    assert verified.status_code == 200
    assert verified.json()["status"] == "verified"
    assert "LICENSE" in verified.json()["evidence"]
    listed = client.get(f"/api/v1/projects/{project_id}/tasks")
    assert listed.status_code == 200
    assert listed.json()["tasks"][0]["id"] == task["id"]


def test_project_task_rejects_unknown_status(tmp_path, monkeypatch):
    monkeypatch.setenv("FACTORY_DB_PATH", str(tmp_path / "task-status.db"))
    project = client.post("/api/v1/projects", json={
        "name": "Task Project", "goal": "Build a mobile-first app",
        "constraints": [], "repository_urls": []
    }).json()
    task = client.post(f"/api/v1/projects/{project['id']}/tasks", json={"title": "Inspect code"}).json()
    response = client.patch(f"/api/v1/projects/{project['id']}/tasks/{task['id']}", json={"status": "done"})
    assert response.status_code == 422


def test_generate_tasks_from_saved_blueprint(monkeypatch, tmp_path):
    import app.main as main_module
    from app.project_store import create_project, save_blueprint
    monkeypatch.setenv("FACTORY_DB_PATH", str(tmp_path / "generated-tasks.db"))
    project = create_project("Video Studio", "Build a mobile-first video tool", [], [])
    save_blueprint(project["id"], "openai", "test-model", "Architecture and test plan", "Plan only")

    async def fake_generate(provider, prompt):
        assert "Architecture and test plan" in prompt
        return {"provider": provider, "model": "test-model", "text": '[{"title":"Review licenses","description":"Check dependencies"},{"title":"Add API tests","description":"Test endpoints"}]'}

    monkeypatch.setattr(main_module, "generate_text", fake_generate)
    response = client.post(f"/api/v1/projects/{project['id']}/tasks/from-blueprint", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["created_count"] == 2
    assert all(task["status"] == "proposed" for task in data["tasks"])
    assert client.get(f"/api/v1/projects/{project['id']}/tasks").json()["tasks"][0]["title"] == "Review licenses"


def test_generate_tasks_requires_saved_blueprint(tmp_path, monkeypatch):
    from app.project_store import create_project
    monkeypatch.setenv("FACTORY_DB_PATH", str(tmp_path / "no-blueprint.db"))
    project = create_project("Video Studio", "Build a mobile-first video tool", [], [])
    response = client.post(f"/api/v1/projects/{project['id']}/tasks/from-blueprint", json={})
    assert response.status_code == 409



def test_task_patch_cors_preflight_allows_browser_updates():
    response = client.options(
        "/api/v1/projects/example/tasks/example",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert "PATCH" in response.headers["access-control-allow-methods"]


def test_capabilities_do_not_list_existing_provider_adapters_as_planned():
    data = client.get("/api/v1/capabilities").json()
    assert "server-side AI text generation adapters for five providers" in data["implemented"]
    assert "real LLM adapters" not in data["planned"]
    assert "persistent project brain" not in data["planned"]



def test_code_proposal_is_saved_as_review_only_artifact(monkeypatch, tmp_path):
    import app.main as main_module
    from app.project_store import create_project, create_task
    monkeypatch.setenv("FACTORY_DB_PATH", str(tmp_path / "code-proposals.db"))
    project = create_project("Factory", "Build a testable software factory", [], [])
    task = create_task(project["id"], "Add a health endpoint test", "Write a focused API test")

    async def fake_generate(provider, prompt):
        assert "review-only code proposal" in prompt
        return {
            "provider": provider, "model": "test-model",
            "text": '[{"path":"backend/test_health.py","content":"def test_health():\\n    assert True\\n"}]'
        }

    monkeypatch.setattr(main_module, "generate_text", fake_generate)
    response = client.post(
        f"/api/v1/projects/{project['id']}/tasks/{task['id']}/code-proposals",
        json={"provider": "openai"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "proposed"
    assert data["files"][0]["path"] == "backend/test_health.py"
    assert "not written" in data["evidence_note"]
    listed = client.get(f"/api/v1/projects/{project['id']}/code-proposals")
    assert listed.status_code == 200
    assert listed.json()["proposals"][0]["id"] == data["id"]


def test_code_proposal_rejects_path_traversal_without_saving(monkeypatch, tmp_path):
    import app.main as main_module
    from app.project_store import create_project, create_task
    monkeypatch.setenv("FACTORY_DB_PATH", str(tmp_path / "unsafe-proposal.db"))
    project = create_project("Factory", "Build a testable software factory", [], [])
    task = create_task(project["id"], "Add a test", "Create a test file")

    async def fake_generate(provider, prompt):
        return {"provider": provider, "model": "test-model", "text": '[{"path":"../outside.py","content":"unsafe"}]'}

    monkeypatch.setattr(main_module, "generate_text", fake_generate)
    response = client.post(
        f"/api/v1/projects/{project['id']}/tasks/{task['id']}/code-proposals",
        json={"provider": "openai"},
    )
    assert response.status_code == 502
    assert client.get(f"/api/v1/projects/{project['id']}/code-proposals").json()["proposals"] == []



def test_code_proposal_manifest_is_read_only_and_hashes_contents(monkeypatch, tmp_path):
    import hashlib
    import app.main as main_module
    from app.project_store import create_project, create_task
    monkeypatch.setenv("FACTORY_DB_PATH", str(tmp_path / "manifest.db"))
    project = create_project("Factory", "Build a testable software factory", [], [])
    task = create_task(project["id"], "Add health test")

    async def fake_generate(provider, prompt):
        return {"provider": provider, "model": "test-model", "text": '[{"path":"backend/test_ok.py","content":"assert True"}]'}

    monkeypatch.setattr(main_module, "generate_text", fake_generate)
    created = client.post(
        f"/api/v1/projects/{project['id']}/tasks/{task['id']}/code-proposals",
        json={"provider": "openai"},
    )
    assert created.status_code == 200
    proposal_id = created.json()["id"]
    response = client.get(f"/api/v1/projects/{project['id']}/code-proposals/{proposal_id}/manifest")
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["files"][0]["sha256"] == hashlib.sha256(b"assert True").hexdigest()
    assert manifest["checks"]["automated_tests"] == "not_run"
    assert manifest["checks"]["isolated_build"] == "not_run"
    assert manifest["status"] == "verification_pending"


def test_code_proposal_rejects_windows_drive_path(monkeypatch, tmp_path):
    import app.main as main_module
    from app.project_store import create_project, create_task
    monkeypatch.setenv("FACTORY_DB_PATH", str(tmp_path / "windows-path.db"))
    project = create_project("Factory", "Build a testable software factory", [], [])
    task = create_task(project["id"], "Add safe file")

    async def fake_generate(provider, prompt):
        return {"provider": provider, "model": "test-model", "text": '[{"path":"C:/secret.txt","content":"not allowed"}]'}

    monkeypatch.setattr(main_module, "generate_text", fake_generate)
    response = client.post(
        f"/api/v1/projects/{project['id']}/tasks/{task['id']}/code-proposals",
        json={"provider": "openai"},
    )
    assert response.status_code == 502
    assert client.get(f"/api/v1/projects/{project['id']}/code-proposals").json()["proposals"] == []
