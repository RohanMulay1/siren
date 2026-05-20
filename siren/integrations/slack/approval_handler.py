import json
import urllib.parse
import structlog
from ...agent.graph import get_graph

log = structlog.get_logger()


async def handle_slack_action(body: bytes, redis_client) -> dict:
    """
    Process a Slack interactive action (button click) and resume the paused graph.
    Called from POST /webhook/slack/action.
    Returns a Slack response_action dict.
    """
    # Slack sends payload as URL-encoded form data
    decoded = urllib.parse.unquote_plus(body.decode())
    if decoded.startswith("payload="):
        decoded = decoded[len("payload="):]
    payload = json.loads(decoded)

    actions = payload.get("actions", [])
    if not actions:
        return {"response_action": "clear"}

    action_value = actions[0].get("value", "")
    if ":" not in action_value:
        return {"response_action": "clear"}

    correlation_id, decision = action_value.rsplit(":", 1)
    approved = decision == "approve"
    approver = payload.get("user", {}).get("name", "unknown")

    log.info("slack_action_received", correlation_id=correlation_id, approved=approved, approver=approver)

    # Look up the incident_id from the correlation_id stored in Redis
    incident_id_bytes = await redis_client.get(f"siren:correlation:{correlation_id}")
    if not incident_id_bytes:
        log.warning("correlation_id_not_found", correlation_id=correlation_id)
        return {"response_action": "clear"}

    incident_id = incident_id_bytes.decode()

    # Load the graph and resume
    graph = get_graph()
    config = {"configurable": {"thread_id": incident_id}}

    try:
        current_state = graph.get_state(config)
        if current_state is None:
            log.warning("state_not_found", incident_id=incident_id)
            return {"response_action": "clear"}

        state_values = current_state.values
        plan = list(state_values.get("action_plan", []))
        idx = state_values.get("current_action_index", 0)

        if not plan:
            log.warning("empty_action_plan", incident_id=incident_id)
            return {"response_action": "clear"}

        # current_action_index points at the DESTRUCTIVE action awaiting approval
        target_idx = idx if idx < len(plan) else len(plan) - 1
        plan[target_idx] = {**plan[target_idx], "approved": approved}

        # Update checkpoint then resume
        await graph.aupdate_state(config, {"action_plan": plan})
        import asyncio
        asyncio.create_task(graph.ainvoke(None, config))

        log.info("graph_resumed", incident_id=incident_id, approved=approved, action_idx=target_idx)
    except Exception as e:
        log.error("graph_resume_failed", error=str(e), incident_id=incident_id)

    return {"response_action": "clear"}
