"""
Unified LLM client using OpenAI-compatible API.
Supports OpenRouter (recommended) and Groq.
"""
from functools import lru_cache
from openai import AsyncOpenAI
from ..config import get_settings


@lru_cache(maxsize=1)
def get_llm_client() -> AsyncOpenAI:
    settings = get_settings()

    if settings.llm_provider == "groq":
        return AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    else:
        return AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/RohanMulay1/siren",
                "X-Title": "SIREN Incident Response Engine",
            },
        )


async def chat_complete(
    model: str,
    messages: list[dict],
    system: str | None = None,
    tools: list[dict] | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.1,
):
    """Single async completion call — no tool loop."""
    client = get_llm_client()

    if system:
        messages = [{"role": "system", "content": system}] + messages

    kwargs: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    return await client.chat.completions.create(**kwargs)
