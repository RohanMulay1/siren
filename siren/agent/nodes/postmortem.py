import json
import uuid
from datetime import datetime, timezone
from ..state import IncidentState
from ...config import get_settings
from ...memory import get_qdrant_client, ensure_collection, upsert_incident
from ...memory.schemas import IncidentVectorPayload
from ...llm import chat_complete
from ...integrations.slack.client import send_resolution

POSTMORTEM_SYSTEM = """You are SIREN's post-mortem writer. Generate a structured post-mortem.

Respond ONLY with JSON — no markdown, no code fences:
{
  "root_cause_category": "oom | connection_pool | deploy_regression | disk_saturation | network | config_error | dependency_failure | other",
  "symptoms": ["symptom1", "symptom2"],
  "timeline": ["HH:MM - event"],
  "contributing_factors": ["factor1"],
  "what_went_well": ["thing1"],
  "action_items": ["item1 — owner"],
  "resolution_effective": true,
  "postmortem_markdown": "# Post-Mortem\\n..."
}"""


async def run(state: IncidentState) -> dict:
    settings = get_settings()
    now = datetime.now(timezone.utc)

    actions_taken = [
        r["tool_name"]
        for r in state.get("execution_results", [])
        if r.get("status") == "success"
    ]
    resolution_summary = "; ".join(
        r.get("result", "")[:100]
        for r in state.get("execution_results", [])
        if r.get("status") == "success"
    ) or "No successful remediations recorded."

    prompt = (
        f"Incident ID: {state['incident_id']}\n"
        f"Service: {state['affected_service']}\n"
        f"Severity: {state['severity']}\n"
        f"Root cause: {state['root_cause']}\n"
        f"Actions taken: {', '.join(actions_taken) or 'none'}\n"
        f"Resolved: {state.get('remediation_verified', False)}\n"
        f"Investigation steps: {len(state.get('investigation_steps', []))}\n\n"
        "Generate the post-mortem."
    )

    resp = await chat_complete(
        model=settings.model_postmortem,
        system=POSTMORTEM_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
    )

    try:
        text = resp.choices[0].message.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)
    except Exception:
        data = {
            "root_cause_category": "other",
            "symptoms": [],
            "resolution_effective": state.get("remediation_verified", False),
            "postmortem_markdown": f"# Post-Mortem: {state['incident_id']}\nRoot cause: {state['root_cause']}",
        }

    # Embed and store in Qdrant
    qdrant = get_qdrant_client()
    ensure_collection(qdrant, settings.qdrant_collection)

    payload = IncidentVectorPayload(
        incident_id=state["incident_id"],
        severity=state["severity"],
        affected_service=state["affected_service"],
        affected_region=state.get("affected_region", "unknown"),
        alert_source=state["alert_source"],
        incident_summary=state["incident_summary"],
        root_cause=state["root_cause"] or "unknown",
        root_cause_category=data.get("root_cause_category", "other"),
        symptoms=data.get("symptoms", []),
        resolution_summary=resolution_summary,
        actions_taken=actions_taken,
        resolved=state.get("remediation_verified", False),
        created_at=now,
        resolved_at=now if state.get("remediation_verified") else None,
        resolution_effective=data.get("resolution_effective", True),
        postmortem_text=data.get("postmortem_markdown", ""),
    )

    vector_id = upsert_incident(qdrant, payload)
    postmortem_id = str(uuid.uuid4())[:8]
    status = "complete" if state.get("remediation_verified") else "escalated"

    # Send resolution notification to Slack
    try:
        created = state.get("created_at")
        mttr = 0.0
        if created:
            elapsed = (now - datetime.fromisoformat(created.replace("Z", "+00:00"))).total_seconds()
            mttr = round(elapsed / 60, 1)
        await send_resolution(
            incident_id=state["incident_id"],
            severity=state["severity"],
            service=state["affected_service"],
            root_cause=state["root_cause"] or "Unknown",
            mttr_minutes=mttr,
            postmortem_id=postmortem_id,
        )
    except Exception:
        pass

    return {
        "postmortem_id": postmortem_id,
        "qdrant_vector_id": vector_id,
        "workflow_status": status,
    }
