from datetime import datetime
from ..state import IncidentState
from ...tools import TOOL_REGISTRY
from ...guardrails.rate_limiter import DestructiveActionRateLimiter
from ...db.writer import write_action_audit
import redis.asyncio as aioredis
import structlog

log = structlog.get_logger()


async def run(state: IncidentState) -> dict:
    """Execute the current action in the plan after approval validation."""
    from ...config import get_settings
    settings = get_settings()

    plan = state["action_plan"]
    idx = state["current_action_index"]

    if idx >= len(plan):
        return {"workflow_status": "verifying"}

    action = plan[idx]

    # Final safety check for DESTRUCTIVE actions
    if action["classification"] == "DESTRUCTIVE":
        if not action.get("approved"):
            return {
                "execution_results": [{
                    "action_id": action["action_id"],
                    "tool_name": action["tool_name"],
                    "status": "blocked",
                    "reason": "DESTRUCTIVE action not approved",
                    "timestamp": datetime.utcnow().isoformat(),
                }],
                "current_action_index": idx + 1,
            }

        # Rate limiter check
        redis_client = aioredis.from_url(settings.redis_url)
        limiter = DestructiveActionRateLimiter(redis_client, settings.destructive_actions_per_hour)
        allowed, count = await limiter.check_and_consume()
        await redis_client.aclose()

        if not allowed:
            return {
                "execution_results": [{
                    "action_id": action["action_id"],
                    "tool_name": action["tool_name"],
                    "status": "rate_limited",
                    "reason": f"Destructive action rate limit exceeded ({count}/{settings.destructive_actions_per_hour}/hr)",
                    "timestamp": datetime.utcnow().isoformat(),
                }],
                "current_action_index": idx + 1,
                "node_errors": [f"Rate limit exceeded for destructive actions"],
            }

    handler = TOOL_REGISTRY.get(action["tool_name"])
    if not handler:
        result_entry = {
            "action_id": action["action_id"],
            "tool_name": action["tool_name"],
            "status": "error",
            "result": f"Unknown tool: {action['tool_name']}",
            "timestamp": datetime.utcnow().isoformat(),
        }
    else:
        try:
            result = await handler.handler(**action["tool_args"])
            result_entry = {
                "action_id": action["action_id"],
                "tool_name": action["tool_name"],
                "status": "success",
                "result": str(result)[:1000],
                "timestamp": datetime.utcnow().isoformat(),
            }
            log.info("action_executed", **result_entry)
        except Exception as e:
            result_entry = {
                "action_id": action["action_id"],
                "tool_name": action["tool_name"],
                "status": "error",
                "result": f"{type(e).__name__}: {e}",
                "timestamp": datetime.utcnow().isoformat(),
            }
            log.error("action_failed", error=str(e), tool=action["tool_name"])

    # Write audit trail to Postgres (best-effort)
    try:
        await write_action_audit(
            incident_id=state["incident_id"],
            action_id=action["action_id"],
            tool_name=action["tool_name"],
            tool_args=action["tool_args"],
            classification=action["classification"],
            approved=action.get("approved"),
            approved_by=None,
            result_status=result_entry.get("status", "unknown"),
            result_summary=result_entry.get("result", ""),
            database_url=settings.database_url,
        )
    except Exception as e:
        log.warning("audit_write_failed", error=str(e))

    return {
        "execution_results": [result_entry],
        "current_action_index": idx + 1,
        "workflow_status": "executing",
    }
