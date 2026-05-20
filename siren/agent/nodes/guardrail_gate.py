from ..state import IncidentState
from ...guardrails.classifier import classify_action
from ...config import get_settings


async def run(state: IncidentState) -> dict:
    """
    Re-classifies the current action and updates its approval state.
    The routing function (route_after_guardrail) reads the classification
    to decide whether to execute, request human approval, or block.
    """
    plan = state["action_plan"]
    idx = state["current_action_index"]

    if idx >= len(plan):
        return {}

    action = plan[idx]
    decision = classify_action(action["action_id"], action["tool_name"], action["tool_args"])

    # Update classification in place (in case args changed)
    updated_plan = list(plan)
    updated_plan[idx] = {**action, "classification": decision.classification}

    return {
        "action_plan": updated_plan,
        "pending_approval_action_id": action["action_id"] if decision.requires_human else None,
    }
