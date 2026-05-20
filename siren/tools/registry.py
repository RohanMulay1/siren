from dataclasses import dataclass
from typing import Callable, Awaitable
from ..guardrails.classifier import Classification


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict
    handler: Callable[..., Awaitable[str]]
    classification: Classification


TOOL_REGISTRY: dict[str, ToolDefinition] = {}


def register_tool(classification: Classification):
    def decorator(cls):
        defn = ToolDefinition(
            name=cls.NAME,
            description=cls.DESCRIPTION,
            input_schema=cls.INPUT_SCHEMA,
            handler=cls.execute,
            classification=classification,
        )
        TOOL_REGISTRY[cls.NAME] = defn
        return cls
    return decorator


def get_anthropic_tool_schemas(classifications: list[Classification] | None = None) -> list[dict]:
    tools = []
    for defn in TOOL_REGISTRY.values():
        if classifications is None or defn.classification in classifications:
            tools.append({
                "name": defn.name,
                "description": defn.description,
                "input_schema": defn.input_schema,
            })
    return tools
