import json
import uuid
from ..state import IncidentState, ActionPlan
from ...config import get_settings
from ...tools import get_anthropic_tool_schemas
from ...llm import chat_complete

PLANNER_SYSTEM = """You are SIREN's remediation planning agent. Given an incident's root cause, generate an ordered remediation plan.

Rules:
- Order actions from least to most risky (READ first, then REVERSIBLE, then DESTRUCTIVE last)
- Each action must reference a real available tool by its exact name
- Provide clear rationale for each action
- Prefer REVERSIBLE fixes over DESTRUCTIVE ones
- Maximum 5 actions

Respond ONLY with a JSON array — no markdown, no code fences:
[
  {
    "tool_name": "exact_tool_name",
    "tool_args": {"arg1": "value1"},
    "rationale": "why this action will help"
  }
]"""


async def run(state: IncidentState) -> dict:
    settings = get_settings()

    all_tools = get_anthropic_tool_schemas()
    tool_catalog = "\n".join(
        f"- {t['name']}: {t['description'][:100]}"
        for t in all_tools
    )

    similar_context = ""
    if state.get("similar_incidents"):
        top = state["similar_incidents"][0]
        similar_context = (
            f"\nBest matching past resolution ({top['similarity_score']:.0%} match): "
            f"{top['resolution']}"
        )

    prompt = (
        f"Service: {state['affected_service']}\n"
        f"Root cause: {state['root_cause']}\n"
        f"Confidence: {state['root_cause_confidence']:.0%}\n"
        f"{similar_context}\n\n"
        f"Available tools:\n{tool_catalog}\n\n"
        "Generate the remediation plan."
    )

    resp = chat_complete(
        model=settings.model_plan,
        system=PLANNER_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )

    try:
        text = resp.choices[0].message.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        raw_plan = json.loads(text)
    except (json.JSONDecodeError, IndexError, AttributeError):
        raw_plan = []

    from ...guardrails.classifier import classify_action

    action_plan: list[ActionPlan] = []
    for item in raw_plan[:5]:
        tool_name = item.get("tool_name", "")
        tool_args = item.get("tool_args", {})
        action_id = str(uuid.uuid4())[:8]

        decision = classify_action(action_id, tool_name, tool_args)

        action_plan.append(ActionPlan(
            action_id=action_id,
            tool_name=tool_name,
            tool_args=tool_args,
            classification=decision.classification,
            rationale=item.get("rationale", ""),
            approved=None,
        ))

    return {
        "action_plan": action_plan,
        "current_action_index": 0,
        "workflow_status": "awaiting_approval",
    }
