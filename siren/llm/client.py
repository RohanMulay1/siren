"""
Unified LLM client using OpenAI-compatible API.
Supports OpenRouter (recommended) and Groq.
"""
from functools import lru_cache
from openai import OpenAI
from ..config import get_settings


@lru_cache(maxsize=1)
def get_llm_client() -> OpenAI:
    settings = get_settings()

    if settings.llm_provider == "groq":
        return OpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    else:
        # Default: OpenRouter
        return OpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/yourusername/siren",
                "X-Title": "SIREN Incident Response Engine",
            },
        )


def chat_complete(
    model: str,
    messages: list[dict],
    system: str | None = None,
    tools: list[dict] | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.1,
):
    """Single completion call — no tool loop."""
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

    return client.chat.completions.create(**kwargs)


def tool_loop(
    model: str,
    system: str,
    initial_messages: list[dict],
    tools: list[dict],
    tool_handler,           # async callable: (name, args) -> str
    max_iterations: int = 8,
    max_tokens: int = 4096,
):
    """
    Returns a generator that yields (tool_name, tool_args, tool_result) tuples
    as the model calls tools, and finally yields ("__done__", None, final_text).

    Callers iterate this to observe progress and collect findings.
    Uses a synchronous generator since OpenAI client is sync.
    """
    client = get_llm_client()
    messages = [{"role": "system", "content": system}] + initial_messages
    iterations = 0

    while iterations < max_iterations:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=max_tokens,
            temperature=0.1,
        )

        choice = resp.choices[0]
        msg = choice.message

        # Append assistant message to history
        messages.append(msg.model_dump(exclude_none=True))

        if choice.finish_reason == "tool_calls" and msg.tool_calls:
            tool_results = []
            for call in msg.tool_calls:
                import json
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                yield ("__tool_call__", name, args, call.id)

                # tool_handler is called by the caller after receiving this yield
                # We use a sentinel to signal the caller needs to provide the result
                # Since we can't do async here, we use a callback pattern via send()
                result = yield ("__awaiting_result__", name, args, call.id)

                tool_results.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": str(result),
                })

            messages.extend(tool_results)
            iterations += 1

        else:
            # Model is done
            final_text = msg.content or ""
            yield ("__done__", None, None, final_text)
            return

    yield ("__done__", None, None, "Max iterations reached.")
