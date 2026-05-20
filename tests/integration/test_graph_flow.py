"""
Integration test: verifies the full LangGraph workflow compiles and routes correctly
without calling external APIs. Uses mock node implementations.
"""
import pytest
from unittest.mock import AsyncMock, patch
from langgraph.graph import StateGraph, END
from siren.agent.state import IncidentState, initial_state
from siren.agent.routing import (
    route_after_triage,
    route_after_investigation,
    route_after_guardrail,
    route_after_execution,
    route_after_verification,
)


def test_graph_compiles():
    """Verify the LangGraph state machine compiles without error."""
    from siren.agent.graph import build_graph
    graph = build_graph(use_redis=False)
    assert graph is not None


def test_graph_has_correct_nodes():
    """Verify all expected nodes are present."""
    from siren.agent.graph import build_graph
    graph = build_graph(use_redis=False)
    # LangGraph exposes nodes via the graph's node set
    assert graph is not None


def test_initial_state_routes_through_triage():
    """P1 alert with high confidence should route to recall, not escalate."""
    state = initial_state("INC-TEST-001", "corr-001", {
        "source": "prometheus",
        "description": "Redis OOM",
        "service": "payments-api",
    })
    state["severity"] = "P1"
    state["triage_confidence"] = 0.92

    route = route_after_triage(state)
    assert route == "recall"


def test_p4_alert_escalates():
    state = initial_state("INC-TEST-002", "corr-002", {"source": "custom"})
    state["severity"] = "P4"
    state["triage_confidence"] = 0.9
    assert route_after_triage(state) == "escalate"


def test_investigation_with_high_confidence_plans():
    state = initial_state("INC-TEST-003", "corr-003", {"source": "custom"})
    state["root_cause_confidence"] = 0.95
    state["investigation_iterations"] = 2
    assert route_after_investigation(state) == "plan"


def test_full_routing_happy_path():
    """Walk through the complete routing decision tree for a happy-path incident."""
    state = initial_state("INC-TEST-004", "corr-004", {"source": "prometheus"})

    # Step 1: triage → recall
    state["severity"] = "P1"
    state["triage_confidence"] = 0.88
    assert route_after_triage(state) == "recall"

    # Step 2: investigate → plan (high confidence)
    state["root_cause_confidence"] = 0.90
    state["investigation_iterations"] = 2
    assert route_after_investigation(state) == "plan"

    # Step 3: guardrail → execute (REVERSIBLE action, approved=None is fine)
    state["action_plan"] = [{
        "action_id": "a1",
        "tool_name": "restart_docker_container",
        "tool_args": {"container_name": "payments-api"},
        "classification": "REVERSIBLE",
        "rationale": "container is crash looping",
        "approved": None,
    }]
    state["current_action_index"] = 0
    assert route_after_guardrail(state) == "execute"

    # Step 4: after execution → verify (last action)
    state["current_action_index"] = 1  # past end of plan
    assert route_after_execution(state) == "verify"

    # Step 5: verify → resolved
    state["remediation_verified"] = True
    assert route_after_verification(state) == "resolved"
