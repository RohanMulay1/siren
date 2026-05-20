import pytest
from siren.agent.state import initial_state
from siren.agent.routing import (
    route_after_triage,
    route_after_investigation,
    route_after_guardrail,
)


def make_state(**overrides):
    state = initial_state("INC-001", "corr-001", {"source": "custom"})
    state.update(overrides)
    return state


class TestRouteAfterTriage:
    def test_p1_with_high_confidence_recalls(self):
        state = make_state(severity="P1", triage_confidence=0.9)
        assert route_after_triage(state) == "recall"

    def test_p4_escalates(self):
        state = make_state(severity="P4", triage_confidence=0.9)
        assert route_after_triage(state) == "escalate"

    def test_low_confidence_escalates(self):
        state = make_state(severity="P1", triage_confidence=0.1)
        assert route_after_triage(state) == "escalate"


class TestRouteAfterInvestigation:
    def test_high_confidence_plans(self):
        state = make_state(root_cause_confidence=0.9, investigation_iterations=1)
        assert route_after_investigation(state) == "plan"

    def test_low_confidence_loops(self):
        state = make_state(root_cause_confidence=0.5, investigation_iterations=1)
        assert route_after_investigation(state) == "loop"

    def test_max_iterations_escalates(self):
        state = make_state(root_cause_confidence=0.3, investigation_iterations=5)
        assert route_after_investigation(state) == "escalate"


class TestRouteAfterGuardrail:
    def test_no_actions_skips(self):
        state = make_state(action_plan=[], current_action_index=0)
        assert route_after_guardrail(state) == "skip"

    def test_read_action_executes(self):
        state = make_state(
            action_plan=[{
                "action_id": "a1", "tool_name": "fetch_cloudwatch_logs",
                "tool_args": {}, "classification": "READ",
                "rationale": "check logs", "approved": None,
            }],
            current_action_index=0,
        )
        assert route_after_guardrail(state) == "execute"

    def test_destructive_unapproved_requests_human(self):
        state = make_state(
            action_plan=[{
                "action_id": "a1", "tool_name": "flush_redis_cache",
                "tool_args": {}, "classification": "DESTRUCTIVE",
                "rationale": "flush cache", "approved": None,
            }],
            current_action_index=0,
        )
        assert route_after_guardrail(state) == "request_human"

    def test_destructive_rejected_blocks(self):
        state = make_state(
            action_plan=[{
                "action_id": "a1", "tool_name": "flush_redis_cache",
                "tool_args": {}, "classification": "DESTRUCTIVE",
                "rationale": "flush cache", "approved": False,
            }],
            current_action_index=0,
        )
        assert route_after_guardrail(state) == "block"
