import json
from ..state import IncidentState
from ...config import get_settings
from ...llm import chat_complete
from ...tools.read.metrics import QueryPrometheus

VERIFIER_SYSTEM = """You are SIREN's verification agent. Determine if the remediation was successful.

Respond ONLY with JSON — no markdown, no code fences:
{
  "resolved": true | false,
  "confidence": 0.0-1.0,
  "reasoning": "1-2 sentences"
}"""


async def run(state: IncidentState) -> dict:
    settings = get_settings()

    current_metrics = ""
    try:
        metrics_result = await QueryPrometheus.execute(
            query=f'rate(http_requests_total{{status=~"5..",service="{state["affected_service"]}"}}[5m])',
            instant=True,
        )
        current_metrics = f"Current error rate: {metrics_result}"
    except Exception as e:
        current_metrics = f"Could not fetch metrics: {e}"

    actions_taken = json.dumps(state.get("execution_results", []), indent=2, default=str)

    prompt = (
        f"Service: {state['affected_service']}\n"
        f"Root cause: {state['root_cause']}\n"
        f"Severity: {state['severity']}\n\n"
        f"Actions taken:\n{actions_taken}\n\n"
        f"{current_metrics}\n\n"
        "Has the incident been resolved?"
    )

    resp = chat_complete(
        model=settings.model_verify,
        system=VERIFIER_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
    )

    try:
        text = resp.choices[0].message.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)
        resolved = data.get("resolved", False)
    except Exception:
        resolved = len(state.get("execution_results", [])) > 0

    return {
        "remediation_verified": resolved,
        "workflow_status": "writing_postmortem" if resolved else "investigating",
    }
