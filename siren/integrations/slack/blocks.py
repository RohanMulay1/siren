from ...agent.state import ActionPlan


RISK_EMOJI = {"READ": ":white_circle:", "REVERSIBLE": ":yellow_circle:", "DESTRUCTIVE": ":red_circle:"}
SEVERITY_EMOJI = {"P1": ":rotating_light:", "P2": ":orange_circle:", "P3": ":yellow_circle:", "P4": ":white_circle:"}


def build_approval_message(
    incident_id: str,
    severity: str,
    service: str,
    root_cause: str,
    action: ActionPlan,
    similar_context: str,
    investigation_summary: str,
    correlation_id: str,
) -> dict:
    sev_emoji = SEVERITY_EMOJI.get(severity, ":question:")
    risk_emoji = RISK_EMOJI.get(action["classification"], ":red_circle:")

    return {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{sev_emoji} SIREN Approval Required — {severity}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Incident:*\n`{incident_id}`"},
                    {"type": "mrkdwn", "text": f"*Service:*\n{service}"},
                    {"type": "mrkdwn", "text": f"*Proposed Action:*\n`{action['tool_name']}`"},
                    {"type": "mrkdwn", "text": f"*Risk Level:*\n{risk_emoji} {action['classification']}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Root Cause:*\n{root_cause}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Rationale:*\n{action['rationale']}"},
            },
            *(
                [{
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": f":brain: {similar_context}"}],
                }] if similar_context else []
            ),
            *(
                [{
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": f":mag: Evidence: {investigation_summary}"}],
                }] if investigation_summary else []
            ),
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "APPROVE"},
                        "style": "primary",
                        "action_id": "siren_approve",
                        "value": f"{correlation_id}:approve",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "REJECT"},
                        "style": "danger",
                        "action_id": "siren_reject",
                        "value": f"{correlation_id}:reject",
                    },
                ],
            },
        ]
    }


def build_incident_notification(
    incident_id: str,
    severity: str,
    service: str,
    summary: str,
) -> dict:
    sev_emoji = SEVERITY_EMOJI.get(severity, ":question:")
    return {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{sev_emoji} *New Incident: {incident_id}*\n*Service:* {service}\n*Summary:* {summary}",
                },
            }
        ]
    }
