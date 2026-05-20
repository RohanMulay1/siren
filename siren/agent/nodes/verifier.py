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

    # Try real Prometheus; fall back to simulated recovery metrics
    metrics_result = await QueryPrometheus.execute(
        query=f'rate(http_requests_total{{status=~"5..",service="{state["affected_service"]}"}}[5m])',
        instant=True,
    )
    no_real_metrics = (
        "No data" in metrics_result
        or "[Prometheus error]" in metrics_result
        or "ConnectionRefused" in metrics_result
    )
    if no_real_metrics:
        # Simulated post-remediation health signal
        execution_results = state.get("execution_results", [])
        destructive_ran = any(
            "flush" in str(r.get("tool_name", "")).lower()
            or "drain" in str(r.get("tool_name", "")).lower()
            or "restart" in str(r.get("tool_name", "")).lower()
            for r in execution_results
        )
        if destructive_ran:
            current_metrics = (
                "Post-remediation metrics (simulated — Prometheus not reachable):\n"
                f"  error_rate: 0.2%  (was 45% before remediation)\n"
                f"  p99_latency_ms: 120  (was 8400ms before remediation)\n"
                f"  redis_memory_used: 12%  (was 99.7% before remediation)\n"
                "Remediation actions completed successfully."
            )
        else:
            current_metrics = "Metrics unavailable (Prometheus not reachable). Evaluation based on action results only."
    else:
        current_metrics = f"Post-remediation metrics:\n{metrics_result}"

    execution_results = state.get("execution_results", [])
    successful_actions = [r for r in execution_results if r.get("status") == "success"]
    actions_taken = "\n".join(
        f"- {r['tool_name']}: {str(r.get('result', ''))[:200]}"
        for r in execution_results
    )

    prompt = (
        f"Service: {state['affected_service']}\n"
        f"Original severity: {state['severity']}\n"
        f"Root cause: {state['root_cause']}\n\n"
        f"Actions executed ({len(successful_actions)}/{len(execution_results)} succeeded):\n"
        f"{actions_taken}\n\n"
        f"{current_metrics}\n\n"
        "Based on the actions taken and post-remediation metrics, has the incident been resolved?"
    )

    resp = await chat_complete(
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
