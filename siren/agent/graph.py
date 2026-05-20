from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import IncidentState
from .nodes import (
    ingestion, triage, memory_recall, investigation,
    remediation_planner, guardrail_gate, human_approval,
    executor, verifier, postmortem,
)
from .routing import (
    route_after_triage,
    route_after_investigation,
    route_after_guardrail,
    route_after_execution,
    route_after_verification,
)


def build_graph(use_redis: bool = False, redis_url: str | None = None):
    """
    Build and compile the SIREN LangGraph state machine.

    use_redis=True: production mode with Redis checkpointer (required for human-in-the-loop)
    use_redis=False: in-memory checkpointer (for testing/dev)
    """
    builder = StateGraph(IncidentState)

    # Register all nodes
    builder.add_node("ingest",           ingestion.run)
    builder.add_node("triage",           triage.run)
    builder.add_node("memory_recall",    memory_recall.run)
    builder.add_node("investigate",      investigation.run)
    builder.add_node("plan_remediation", remediation_planner.run)
    builder.add_node("guardrail_gate",   guardrail_gate.run)
    builder.add_node("request_approval", human_approval.run)
    builder.add_node("execute_action",   executor.run)
    builder.add_node("verify",           verifier.run)
    builder.add_node("write_postmortem", postmortem.run)

    # Entry point
    builder.set_entry_point("ingest")

    # Linear edges
    builder.add_edge("ingest",           "triage")
    builder.add_edge("memory_recall",    "investigate")
    builder.add_edge("plan_remediation", "guardrail_gate")
    builder.add_edge("write_postmortem", END)

    # After Slack approval, re-enter guardrail_gate to re-evaluate
    builder.add_edge("request_approval", "guardrail_gate")

    # Conditional edges
    builder.add_conditional_edges(
        "triage",
        route_after_triage,
        {"recall": "memory_recall", "escalate": "write_postmortem"},
    )

    builder.add_conditional_edges(
        "investigate",
        route_after_investigation,
        {
            "plan": "plan_remediation",
            "loop": "investigate",
            "escalate": "write_postmortem",
        },
    )

    builder.add_conditional_edges(
        "guardrail_gate",
        route_after_guardrail,
        {
            "execute": "execute_action",
            "request_human": "request_approval",
            "skip": "verify",
            "block": "write_postmortem",
        },
    )

    builder.add_conditional_edges(
        "execute_action",
        route_after_execution,
        {
            "next_action": "guardrail_gate",
            "verify": "verify",
            "error": "write_postmortem",
        },
    )

    builder.add_conditional_edges(
        "verify",
        route_after_verification,
        {
            "resolved": "write_postmortem",
            "reinvestigate": "investigate",
            "escalate": "write_postmortem",
        },
    )

    # Checkpointer — Redis enables human-in-the-loop pause/resume
    if use_redis and redis_url:
        try:
            from langgraph.checkpoint.redis import RedisSaver
            checkpointer = RedisSaver.from_conn_string(redis_url)
        except ImportError:
            checkpointer = MemorySaver()
    else:
        checkpointer = MemorySaver()

    return builder.compile(
        checkpointer=checkpointer,
        # Pause before execution for safety inspection (useful in dev)
        # interrupt_before=["execute_action"],
    )


# Singleton for the FastAPI app
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        from ..config import get_settings
        settings = get_settings()
        _graph = build_graph(
            use_redis=True,
            redis_url=settings.redis_url,
        )
    return _graph
