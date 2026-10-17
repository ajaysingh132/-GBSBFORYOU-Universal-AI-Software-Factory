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
