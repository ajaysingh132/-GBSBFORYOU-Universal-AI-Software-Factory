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
