"""Server-side text-generation adapters. Secrets are read only from environment variables."""
import os
import httpx

PROVIDER_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google_gemini": "GEMINI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}
DEFAULT_MODELS = {
    "openai": "gpt-4.1-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "google_gemini": "gemini-2.5-flash",
    "deepseek": "deepseek-chat",
    "openrouter": "openai/gpt-4.1-mini",
}
DEFAULT_URLS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "google_gemini": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}
class ProviderNotImplemented(RuntimeError):
    """Provider is not configured or returned an unsupported response."""
def configured_providers():
    return [
        {"id": p, "configured": bool(os.getenv(e)), "credential_env": e,
         "model": os.getenv(f"{p.upper()}_MODEL", DEFAULT_MODELS[p])}
        for p, e in PROVIDER_ENV.items()
    ]
async def generate_text(provider: str, prompt: str) -> dict:
    if provider not in PROVIDER_ENV:
        raise ValueError(f"Unsupported provider: {provider}")
    key = os.getenv(PROVIDER_ENV[provider])
    if not key:
        raise ProviderNotImplemented(f"{provider} is not configured. Set {PROVIDER_ENV[provider]} server-side.")
    if not prompt.strip() or len(prompt) > 30000:
        raise ValueError("prompt must contain 1–30000 characters")
    model = os.getenv(f"{provider.upper()}_MODEL", DEFAULT_MODELS[provider])
    headers = {"Content-Type": "application/json"}
    if provider == "anthropic":
        headers.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
        url = os.getenv("ANTHROPIC_API_URL", DEFAULT_URLS[provider])
        body = {"model": model, "max_tokens": 2048, "messages": [{"role": "user", "content": prompt}]}
    elif provider == "google_gemini":
        url = os.getenv("GEMINI_API_URL", DEFAULT_URLS[provider]).format(model=model) + "?key=" + key
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 2048}}
    else:
        url = os.getenv(f"{provider.upper()}_API_URL", DEFAULT_URLS[provider])
        headers["Authorization"] = f"Bearer {key}"
        body = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2048}
        if provider == "openrouter":
            headers["HTTP-Referer"] = os.getenv("OPENROUTER_SITE_URL", "https://gbsbforyou.org")
            headers["X-Title"] = "GBSBFORYOU Universal AI Software Factory"
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
            response = await client.post(url, headers=headers, json=body)
        if response.status_code >= 400:
            # Do not return provider response bodies; they can contain request details.
            raise ProviderNotImplemented(f"{provider} returned HTTP {response.status_code}. Check model access, quota and server configuration.")
        data = response.json()
    except httpx.TimeoutException as exc:
        raise ProviderNotImplemented(f"{provider} request timed out.") from exc
    except httpx.HTTPError as exc:
        raise ProviderNotImplemented(f"{provider} network request failed.") from exc
    if provider == "anthropic":
        text = "\n".join(item.get("text", "") for item in data.get("content", []) if item.get("type") == "text")
    elif provider == "google_gemini":
        candidates = data.get("candidates", [])
        text = "\n".join(part.get("text", "") for part in (candidates[0].get("content", {}).get("parts", []) if candidates else []))
    else:
        choices = data.get("choices", [])
        text = choices[0].get("message", {}).get("content", "") if choices else ""
        if isinstance(text, list):
            text = "\n".join(part.get("text", "") for part in text if isinstance(part, dict))
    if not isinstance(text, str) or not text.strip():
        raise ProviderNotImplemented(f"{provider} returned no text; check model response format.")
    return {"provider": provider, "model": model, "text": text, "status": "generated"}
