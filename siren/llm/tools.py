"""
Convert tool schemas between formats.
Registry stores Anthropic-style input_schema; OpenAI API expects parameters.
"""


def to_openai_tools(tool_defs: list[dict]) -> list[dict]:
    """Convert Anthropic tool schema list to OpenAI function calling format."""
    result = []
    for t in tool_defs:
        result.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        })
    return result


def to_openai_finish_tool(finish_tool: dict) -> dict:
    """Convert a single Anthropic-style tool to OpenAI format."""
    return {
        "type": "function",
        "function": {
            "name": finish_tool["name"],
            "description": finish_tool.get("description", ""),
            "parameters": finish_tool.get("input_schema", {"type": "object", "properties": {}}),
        },
    }
