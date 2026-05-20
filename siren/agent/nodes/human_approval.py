from ..state import IncidentState
from ...integrations.slack.client import send_approval_request
from ...config import get_settings
import structlog

log = structlog.get_logger()


async def run(state: IncidentState) -> dict:
    """Send Slack approval message and pause. Graph resumes when approval_handler receives click."""
    settings = get_settings()
    plan = state["action_plan"]
    idx = state["current_action_index"]

    if idx >= len(plan):
        return {"workflow_status": "verifying"}

    action = plan[idx]

    similar_context = ""
    if state.get("similar_incidents"):
        top = state["similar_incidents"][0]
        similar_context = f"Based on {len(state['similar_incidents'])} similar past incidents. Best match: {top['similarity_score']:.0%} — previously resolved by: {top['resolution']}"

    investigation_summary = ""
    if state.get("investigation_steps"):
        steps = state["investigation_steps"][-3:]
        investigation_summary = " → ".join(s["tool_used"] + ": " + s["observation"][:80] for s in steps)

    try:
        await send_approval_request(
            incident_id=state["incident_id"],
            correlation_id=state["correlation_id"],
            severity=state["severity"],
            service=state["affected_service"],
            root_cause=state["root_cause"] or "Under investigation",
            action=action,
            similar_context=similar_context,
            investigation_summary=investigation_summary,
            action_index=idx,
            total_actions=len(plan),
        )
        log.info("slack_approval_sent", incident_id=state["incident_id"], action_id=action["action_id"])
    except Exception as e:
        log.error("slack_approval_failed", error=str(e))
        # If Slack fails, auto-block the action rather than proceeding blindly
        updated_plan = list(plan)
        updated_plan[idx] = {**action, "approved": False}
        return {
            "action_plan": updated_plan,
            "workflow_status": "awaiting_approval",
            "node_errors": [f"Slack notification failed: {e}"],
        }

    return {"workflow_status": "awaiting_approval"}
