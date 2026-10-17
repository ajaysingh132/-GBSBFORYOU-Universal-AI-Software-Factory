"""Source-linked public GitHub search for external project research."""
import httpx

class ResearchError(ValueError):
    pass

async def search_github_repositories(query: str, limit: int = 8) -> dict:
    query = " ".join(query.split()).strip()
    if len(query) < 3:
        raise ResearchError("Search query must contain at least 3 characters.")
    if len(query) > 180:
        raise ResearchError("Search query must be 180 characters or fewer.")
    limit = max(1, min(int(limit), 10))
    url = "https://api.github.com/search/repositories"
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": limit}
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 403:
            raise ResearchError("GitHub search rate limit or permission restriction. Retry later.")
        response.raise_for_status()
        data = response.json()
    items = []
    for repo in data.get("items", []):
        lic = repo.get("license") or {}
        items.append({
            "name": repo.get("full_name"),
            "url": repo.get("html_url"),
            "description": repo.get("description"),
            "language": repo.get("language"),
            "license_spdx": lic.get("spdx_id"),
            "license_name": lic.get("name"),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "open_issues": repo.get("open_issues_count", 0),
            "pushed_at": repo.get("pushed_at"),
            "topics": repo.get("topics", []),
            "default_branch": repo.get("default_branch"),
            "evidence_url": repo.get("html_url"),
            "reuse_warning": "Metadata is not a license or security audit. Verify code, dependencies, model weights and commercial-use terms before reuse."
        })
    return {
        "query": query,
        "source": url,
        "source_url": "https://docs.github.com/en/rest/search/search#search-repositories",
        "total_count": data.get("total_count", 0),
        "results": items,
        "limitations": [
            "Search results are public GitHub metadata and may be incomplete or ranked by stars.",
            "Stars and recent activity do not prove quality, safety or suitability.",
            "A missing license must be treated as no explicit reuse permission.",
            "Private repositories are not searched by this endpoint."
        ]
    }
