# Contributing to SIREN

SIREN is open source and contributions are welcome. Here's how to get started.

## Setup

```bash
git clone https://github.com/yourusername/siren
cd siren
pip install -e ".[dev]"
pre-commit install
cp .env.example .env  # add your API keys
docker compose up -d
python scripts/seed_qdrant.py
```

## Project Structure

```
siren/agent/          — LangGraph nodes and state machine
siren/tools/          — Tools the agent can call (READ/REVERSIBLE/DESTRUCTIVE)
siren/guardrails/     — Safety layer (classifier, injection detector, rate limiter)
siren/memory/         — Qdrant vector store interface
siren/integrations/   — Slack, AWS, GitHub, Docker clients
siren/api/            — FastAPI webhook handlers
dashboard/            — Streamlit live dashboard
scripts/              — Demo and seed scripts
```

## Adding a New Tool

1. Create `siren/tools/{tier}/{tool_name}.py`
2. Decorate with `@register_tool("READ" | "REVERSIBLE" | "DESTRUCTIVE")`
3. Implement `NAME`, `DESCRIPTION`, `INPUT_SCHEMA`, and `async execute(**kwargs) -> str`
4. Import it in `siren/tools/__init__.py`
5. Add to `CLASSIFICATION_RULES` in `siren/guardrails/classifier.py`

```python
from ..registry import register_tool

@register_tool("READ")
class MyNewTool:
    NAME = "my_new_tool"
    DESCRIPTION = "What this tool does."
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "..."},
        },
        "required": ["param"],
    }

    @staticmethod
    async def execute(param: str) -> str:
        # implement
        return result
```

## Running Tests

```bash
pytest tests/unit/ -v                    # no external services needed
pytest tests/integration/ -v             # requires Docker Compose running
```

## Pull Requests

- Keep PRs focused on one thing
- Unit tests required for new guardrail logic
- Integration tests required for new tools
- No hardcoded credentials or API keys
