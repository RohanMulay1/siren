import pytest
from siren.agent.state import initial_state, IncidentState


def test_initial_state_has_required_fields():
    state = initial_state("INC-001", "corr-001", {"source": "prometheus", "description": "test"})
    assert state["incident_id"] == "INC-001"
    assert state["correlation_id"] == "corr-001"
    assert state["workflow_status"] == "ingesting"
    assert state["investigation_steps"] == []
    assert state["execution_results"] == []
    assert state["node_errors"] == []
    assert state["current_action_index"] == 0
    assert state["remediation_verified"] is False


def test_initial_state_preserves_alert():
    raw = {"source": "pagerduty", "description": "High latency", "service": "api"}
    state = initial_state("INC-002", "corr-002", raw)
    assert state["raw_alert"] == raw
    assert state["alert_source"] == "pagerduty"
