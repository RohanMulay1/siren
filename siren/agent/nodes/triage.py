import json
from ..state import IncidentState
from ...config import get_settings
from ...llm import chat_complete

TRIAGE_SYSTEM = """You are SIREN's triage agent. Classify the severity of the incoming incident and extract key metadata.

Respond ONLY with a JSON object — no markdown, no code fences:
{
  "severity": "P1" | "P2" | "P3" | "P4",
  "affected_service": "string",
  "affected_region": "string",
  "incident_summary": "string (1-2 sentences describing what is happening)",
  "confidence": 0.0-1.0,
  "is_noise": boolean
}

Severity guide:
- P1: Customer-facing outage, revenue impact, data loss risk
- P2: Significant degradation, partial outage
- P3: Minor degradation, no customer impact
- P4: Informational, no action needed"""


async def run(state: IncidentState) -> dict:
    settings = get_settings()
    raw = state["raw_alert"]

    prompt = (
        f"Alert source: {state['alert_source']}\n"
        f"Service: {state['affected_service']}\n"
        f"Region: {state['affected_region']}\n"
        f"Summary: {state['incident_summary']}\n"
        f"Raw alert: {json.dumps(raw, default=str)[:2000]}"
    )

    try:
        resp = await chat_complete(
            model=settings.model_triage,
            system=TRIAGE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
        )
        text = resp.choices[0].message.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)
    except Exception:
        data = {
            "severity": "P1",
            "affected_service": state["affected_service"],
            "affected_region": state["affected_region"],
            "incident_summary": state["incident_summary"],
            "confidence": 0.6,
            "is_noise": False,
        }

    return {
        "severity": data.get("severity", "P2"),
        "affected_service": data.get("affected_service", state["affected_service"]),
        "affected_region": data.get("affected_region", state["affected_region"]),
        "incident_summary": data.get("incident_summary", state["incident_summary"]),
        "triage_confidence": data.get("confidence", 0.5),
        "should_escalate": data.get("is_noise", False),
        "workflow_status": "recalling",
    }
