from .state import IncidentState
from ..config import get_settings


def route_after_triage(state: IncidentState) -> str:
    settings = get_settings()
    if state["severity"] == "P4" or state["triage_confidence"] < 0.3:
        return "escalate"
    return "recall"


def route_after_investigation(state: IncidentState) -> str:
    settings = get_settings()
    if state["root_cause_confidence"] >= settings.investigation_confidence_threshold:
        return "plan"
    if state["investigation_iterations"] >= settings.investigation_max_iterations:
        return "escalate"
    return "loop"


def route_after_guardrail(state: IncidentState) -> str:
    plan = state["action_plan"]
    idx = state["current_action_index"]

    if idx >= len(plan):
        return "skip"

    action = plan[idx]

    if action["classification"] == "DESTRUCTIVE":
        if action["approved"] is None:
            return "request_human"
        if action["approved"] is False:
            return "block"

    return "execute"


def route_after_execution(state: IncidentState) -> str:
    next_idx = state["current_action_index"] + 1
    if next_idx < len(state["action_plan"]):
        return "next_action"
    return "verify"


def route_after_verification(state: IncidentState) -> str:
    if state["remediation_verified"]:
        return "resolved"
    if state["investigation_iterations"] < 3:
        return "reinvestigate"
    return "escalate"
