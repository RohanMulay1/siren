import uuid
from ..state import IncidentState


async def run(state: IncidentState) -> dict:
    """Normalize the raw webhook payload into a consistent structure."""
    raw = state["raw_alert"]
    source = raw.get("source", "custom")

    if source == "prometheus":
        summary = raw.get("description") or raw.get("annotations", {}).get("summary", "")
        service = (
            raw.get("service")
            or raw.get("labels", {}).get("service")
            or raw.get("labels", {}).get("job", "unknown")
        )
        region = raw.get("labels", {}).get("region", "unknown")
    elif source == "pagerduty":
        summary = raw.get("detail", {}).get("description", "")
        service = raw.get("detail", {}).get("service", {}).get("name", "unknown")
        region = "unknown"
    else:
        summary = raw.get("description", raw.get("message", "Unknown incident"))
        service = raw.get("service", "unknown")
        region = raw.get("region", "unknown")

    return {
        "incident_summary": summary,
        "affected_service": service,
        "affected_region": region,
        "workflow_status": "triaging",
    }
