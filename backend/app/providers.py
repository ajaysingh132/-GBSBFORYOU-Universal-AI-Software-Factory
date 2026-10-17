"""Provider-neutral interfaces. No provider is falsely reported as connected."""
import os
PROVIDER_ENV = {"openai":"OPENAI_API_KEY","anthropic":"ANTHROPIC_API_KEY","google_gemini":"GEMINI_API_KEY","deepseek":"DEEPSEEK_API_KEY","openrouter":"OPENROUTER_API_KEY"}
def configured_providers():
    return [{"id": p, "configured": bool(os.getenv(e)), "credential_env": e} for p,e in PROVIDER_ENV.items()]
class ProviderNotImplemented(RuntimeError):
    """Raised until a real server-side provider adapter is installed."""
async def generate_text(provider: str, prompt: str) -> str:
    if provider not in PROVIDER_ENV: raise ValueError(f"Unsupported provider: {provider}")
    if not os.getenv(PROVIDER_ENV[provider]): raise ProviderNotImplemented(f"{provider} is not configured. Set {PROVIDER_ENV[provider]} server-side.")
    raise ProviderNotImplemented(f"{provider} credentials exist, but its request adapter is not implemented yet.")
