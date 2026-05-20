from typing import TypedDict, Annotated, Literal
from datetime import datetime
import operator


class InvestigationFinding(TypedDict):
    timestamp: str
    tool_used: str
    observation: str


class ActionPlan(TypedDict):
    action_id: str
    tool_name: str
    tool_args: dict
    classification: Literal["READ", "REVERSIBLE", "DESTRUCTIVE"]
    rationale: str
    approved: bool | None  # None=pending, True=approved, False=rejected


class SimilarIncident(TypedDict):
    incident_id: str
    similarity_score: float
    description: str
    root_cause: str
    resolution: str
    time_to_resolve_minutes: float


class IncidentState(TypedDict):
    # Identity
    incident_id: str
    correlation_id: str  # ties Slack approval callbacks back to this graph run

    # Raw input
    raw_alert: dict
    alert_source: str  # "prometheus" | "pagerduty" | "cloudwatch" | "custom"

    # Triage output
    severity: Literal["P1", "P2", "P3", "P4"]
    affected_service: str
    affected_region: str
    incident_summary: str
    triage_confidence: float

    # Memory recall (Qdrant)
    similar_incidents: list[SimilarIncident]
    recalled_playbook: str | None

    # Investigation (Opus tool-use loop)
    # Annotated with operator.add so each node can append without overwriting
    investigation_steps: Annotated[list[InvestigationFinding], operator.add]
    root_cause: str | None
    root_cause_confidence: float
    investigation_iterations: int

    # Remediation
    action_plan: list[ActionPlan]
    current_action_index: int
    pending_approval_action_id: str | None

    # Execution
    execution_results: Annotated[list[dict], operator.add]
    remediation_verified: bool

    # Post-mortem
    postmortem_id: str | None
    qdrant_vector_id: str | None

    # Control flow
    node_errors: Annotated[list[str], operator.add]
    should_escalate: bool
    workflow_status: Literal[
        "ingesting", "triaging", "recalling", "investigating",
        "planning", "awaiting_approval", "executing",
        "verifying", "writing_postmortem", "complete", "escalated",
    ]


def initial_state(incident_id: str, correlation_id: str, raw_alert: dict) -> IncidentState:
    return IncidentState(
        incident_id=incident_id,
        correlation_id=correlation_id,
        raw_alert=raw_alert,
        alert_source=raw_alert.get("source", "custom"),
        severity="P3",
        affected_service="unknown",
        affected_region="unknown",
        incident_summary="",
        triage_confidence=0.0,
        similar_incidents=[],
        recalled_playbook=None,
        investigation_steps=[],
        root_cause=None,
        root_cause_confidence=0.0,
        investigation_iterations=0,
        action_plan=[],
        current_action_index=0,
        pending_approval_action_id=None,
        execution_results=[],
        remediation_verified=False,
        postmortem_id=None,
        qdrant_vector_id=None,
        node_errors=[],
        should_escalate=False,
        workflow_status="ingesting",
    )
