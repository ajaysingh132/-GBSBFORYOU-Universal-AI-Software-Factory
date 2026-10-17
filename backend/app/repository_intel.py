"""Public GitHub repository metadata analyzer; private repos require OAuth integration."""
from urllib.parse import urlparse
import httpx

class RepositoryAnalysisError(ValueError):
    pass

def parse_github_repo(value: str) -> tuple[str, str]:
    parsed = urlparse(value)
    if parsed.hostname not in {"github.com", "www.github.com"}:
        raise RepositoryAnalysisError("Only canonical github.com repository URLs are accepted.")
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise RepositoryAnalysisError("URL must look like https://github.com/owner/repository.")
    owner, name = parts[0], parts[1]
    if owner in {".", ".."} or name in {".", ".."}:
        raise RepositoryAnalysisError("Invalid repository path.")
    return owner, name.removesuffix(".git")

async def analyze_public_repository(url: str) -> dict:
    owner, name = parse_github_repo(url)
    api = f"https://api.github.com/repos/{owner}/{name}"
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
        response = await client.get(api, headers=headers)
        if response.status_code == 404:
            raise RepositoryAnalysisError("Repository not found or not publicly accessible. Private repositories require an authorized GitHub App/OAuth connection.")
        if response.status_code == 403:
            raise RepositoryAnalysisError("GitHub API rate limit or permission restriction. Retry later or add a server-side GitHub App.")
        response.raise_for_status()
        data = response.json()
        if data.get("private"):
            raise RepositoryAnalysisError("Private repository access is not supported until OAuth is configured.")
        readme_response = await client.get(f"{api}/readme", headers=headers)
        readme_text = ""
        if readme_response.status_code == 200:
            import base64
            readme_data = readme_response.json()
            if readme_data.get("encoding") == "base64":
                try:
                    readme_text = base64.b64decode(readme_data.get("content", "")).decode("utf-8", errors="replace")
                except Exception:
                    readme_text = ""
        tree_response = await client.get(f"{api}/git/trees/{data.get('default_branch', 'main')}?recursive=1", headers=headers)
        files = []
        if tree_response.status_code == 200:
            files = [x.get("path", "") for x in tree_response.json().get("tree", []) if x.get("type") == "blob"][:500]
    manifests = [p for p in files if p.lower().split("/")[-1] in {"package.json","pyproject.toml","requirements.txt","cargo.toml","go.mod","pom.xml","build.gradle","dockerfile","compose.yaml","docker-compose.yml"}]
    test_files = [p for p in files if any(t in p.lower() for t in ("/test", "tests/", ".test.", ".spec."))][:80]
    license_info = data.get("license") or {}
    return {
        "repository": data.get("full_name"),
        "url": data.get("html_url"),
        "description": data.get("description"),
        "visibility": "public",
        "default_branch": data.get("default_branch"),
        "language": data.get("language"),
        "license": {"spdx_id": license_info.get("spdx_id"), "name": license_info.get("name")} if license_info else None,
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "pushed_at": data.get("pushed_at"),
        "topics": data.get("topics", []),
        "root_and_nested_file_count_sampled": len(files),
        "dependency_manifests": manifests,
        "test_file_candidates": test_files,
        "readme_excerpt": readme_text[:5000],
        "evidence_limitations": ["Metadata and a file-path sample are not a full code audit.", "A missing license field does not grant reuse permission.", "Private repositories need an explicitly authorized GitHub integration."]
    }
