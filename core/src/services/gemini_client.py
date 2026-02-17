"""
Minimal Gemini client using the REST API.
"""
import httpx

from config.settings import get_settings
from src.core.exceptions import ConfigurationError, LLMError


async def generate_text(prompt: str) -> str:
    settings = get_settings()

    if not settings.gemini_api_key:
        raise ConfigurationError("GEMINI_API_KEY is not set")

    model = settings.gemini_model.strip()
    if model.startswith("models/"):
        model = model.split("/", 1)[1]

    url = f"{settings.gemini_base_url}/v1beta/models/{model}:generateContent"
    params = {"key": settings.gemini_api_key}
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": settings.default_temperature,
            "maxOutputTokens": settings.default_max_tokens,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, params=params, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise LLMError("Gemini API call failed", {"error": str(exc)}) from exc

    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise LLMError("Gemini returned no candidates", {"response": data})

    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    if not parts or "text" not in parts[0]:
        raise LLMError("Gemini response missing text", {"response": data})

    return parts[0]["text"]
