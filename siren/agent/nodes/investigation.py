import json
from datetime import datetime
from ..state import IncidentState, InvestigationFinding
from ...config import get_settings
from ...tools import TOOL_REGISTRY, get_anthropic_tool_schemas
from ...guardrails.injection_detector import sanitize_tool_output
from ...llm.client import get_llm_client
from ...llm.tools import to_openai_tools, to_openai_finish_tool

INVESTIGATION_SYSTEM = """You are SIREN, an expert SRE agent investigating a production incident.
You have access to tools to read logs, query metrics, inspect git history, and check databases.

Investigation protocol:
1. Form a hypothesis based on the alert and any similar past incidents shown
2. Use tools to validate or refute your hypothesis — call multiple tools per turn
3. Iterate — refine based on evidence
4. When you have identified the root cause with >= 80% confidence, call finish_investigation
5. NEVER guess without tool evidence. Every claim must be grounded in tool output."""

FINISH_TOOL = {
    "name": "finish_investigation",
    "description": "Call this when you have identified the root cause with high confidence.",
    "input_schema": {
        "type": "object",
        "properties": {
            "root_cause": {"type": "string", "description": "Precise description of the root cause"},
            "root_cause_category": {
                "type": "string",
                "description": "Category: oom | connection_pool | deploy_regression | disk_saturation | network | config_error | dependency_failure | other",
            },
            "confidence": {"type": "number", "description": "Confidence score 0.0–1.0"},
            "evidence_summary": {"type": "string", "description": "2-3 sentences summarizing the evidence"},
        },
        "required": ["root_cause", "root_cause_category", "confidence", "evidence_summary"],
    },
}


def _build_context(state: IncidentState) -> str:
    lines = [
        f"Incident: {state['incident_id']}",
        f"Severity: {state['severity']}",
        f"Service: {state['affected_service']}",
        f"Region: {state.get('affected_region', 'unknown')}",
        f"Summary: {state['incident_summary']}",
    ]

    if state.get("recalled_playbook"):
        lines.append(f"\nPlaybook hint: {state['recalled_playbook']}")

    similar = state.get("similar_incidents", [])
    if similar:
        lines.append("\nSimilar past incidents from memory:")
        for s in similar[:3]:
            lines.append(
                f"  - [{s['similarity_score']:.0%} match] {s['description']}\n"
                f"    Root cause: {s['root_cause']}\n"
                f"    Resolution: {s['resolution']} ({s['time_to_resolve_minutes']:.0f} min)"
            )

    lines.append("\nBegin your investigation. Start with the most likely hypothesis.")
    return "\n".join(lines)


async def run(state: IncidentState) -> dict:
    settings = get_settings()
    client = get_llm_client()

    # READ-only tools + the finish sentinel
    read_schemas = get_anthropic_tool_schemas(classifications=["READ"])
    openai_tools = to_openai_tools(read_schemas)
    openai_tools.append(to_openai_finish_tool(FINISH_TOOL))

    messages = [
        {"role": "system", "content": INVESTIGATION_SYSTEM},
        {"role": "user", "content": _build_context(state)},
    ]

    findings: list[InvestigationFinding] = []
    root_cause = None
    root_cause_confidence = 0.0
    max_iters = settings.investigation_max_iterations

    for _ in range(max_iters):
        resp = client.chat.completions.create(
            model=settings.model_investigate,
            messages=messages,
            tools=openai_tools,
            tool_choice="auto",
            max_tokens=4096,
            temperature=0.1,
        )

        choice = resp.choices[0]
        msg = choice.message
        messages.append(msg.model_dump(exclude_none=True))

        if choice.finish_reason == "tool_calls" and msg.tool_calls:
            tool_results = []

            for call in msg.tool_calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                # Handle finish_investigation sentinel
                if name == "finish_investigation":
                    root_cause = args.get("root_cause")
                    root_cause_confidence = float(args.get("confidence", 0.8))
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": "Investigation concluded.",
                    })
                    break

                handler = TOOL_REGISTRY.get(name)
                if not handler:
                    raw_result = f"[Error] Unknown tool: {name}"
                else:
                    try:
                        raw_result = await handler.handler(**args)
                    except Exception as e:
                        raw_result = f"[Tool error] {type(e).__name__}: {e}"

                safe_result = sanitize_tool_output(str(raw_result), settings.tool_output_max_chars)

                findings.append(InvestigationFinding(
                    timestamp=datetime.utcnow().isoformat(),
                    tool_used=name,
                    observation=safe_result[:300],
                ))

                tool_results.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": safe_result,
                })

            messages.extend(tool_results)

            if root_cause:
                break
        else:
            # Model stopped without calling finish_investigation
            text = msg.content or ""
            root_cause = text[:500] or "Root cause could not be determined."
            root_cause_confidence = 0.5
            break

    return {
        "root_cause": root_cause,
        "root_cause_confidence": root_cause_confidence,
        "investigation_steps": findings,
        "investigation_iterations": state.get("investigation_iterations", 0) + 1,
        "workflow_status": "planning",
    }
