from typing import Literal
from pydantic import BaseModel


Classification = Literal["READ", "REVERSIBLE", "DESTRUCTIVE"]

CLASSIFICATION_RULES: dict[Classification, list[str]] = {
    "READ": [
        "fetch_cloudwatch_logs",
        "query_prometheus",
        "query_postgres_readonly",
        "inspect_docker_container",
        "git_blame_file",
        "list_running_containers",
        "get_service_health",
    ],
    "REVERSIBLE": [
        "restart_docker_container",
        "scale_service",
        "toggle_feature_flag",
        "clear_application_cache",
    ],
    "DESTRUCTIVE": [
        "flush_redis_cache",
        "drain_lb_node",
        "execute_db_migration",
        "delete_stuck_jobs",
        "force_kill_process",
    ],
}

# Build reverse lookup once
_TOOL_TO_CLASS: dict[str, Classification] = {}
for cls, tools in CLASSIFICATION_RULES.items():
    for tool in tools:
        _TOOL_TO_CLASS[tool] = cls


class GuardRailDecision(BaseModel):
    action_id: str
    tool_name: str
    classification: Classification
    allowed: bool
    requires_human: bool
    block_reason: str | None
    risk_score: float  # 0.0–1.0


def classify_action(action_id: str, tool_name: str, tool_args: dict) -> GuardRailDecision:
    # Deterministic lookup — no LLM, no hallucination
    classification: Classification = _TOOL_TO_CLASS.get(tool_name, "DESTRUCTIVE")

    # Arg-level risk escalation
    if tool_name == "scale_service" and tool_args.get("replicas", 1) == 0:
        classification = "DESTRUCTIVE"
    if tool_name == "clear_application_cache" and tool_args.get("scope") == "global":
        classification = "DESTRUCTIVE"

    risk_map: dict[Classification, float] = {
        "READ": 0.0,
        "REVERSIBLE": 0.4,
        "DESTRUCTIVE": 0.9,
    }

    return GuardRailDecision(
        action_id=action_id,
        tool_name=tool_name,
        classification=classification,
        allowed=classification != "DESTRUCTIVE",
        requires_human=classification == "DESTRUCTIVE",
        block_reason=None,
        risk_score=risk_map[classification],
    )
