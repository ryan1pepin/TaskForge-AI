from openai import AsyncOpenAI
from app.config import settings

_client = None


def _get_client():
    global _client
    if _client is None and settings.OPENAI_API_KEY:
        _client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
    return _client


async def call_llm(system_prompt: str, context: dict, response_json=True) -> str:
    """Async LLM wrapper. Serializes context dict to readable key=value lines for the prompt."""
    client = _get_client()
    if not client:
        raise RuntimeError("OpenAI API key not configured — set OPENAI_API_KEY in .env")
    user_text = "\n".join(f"{k}: {v}" for k, v in context.items())
    resp = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        response_format={"type": "json_object"} if response_json else {"type": "text"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        max_tokens=getattr(settings, "OPENAI_MAX_TOKENS", 1024),
        timeout=15,
    )
    return (resp.choices[0].message.content or "{}").replace("```json", "").replace("```", "")
