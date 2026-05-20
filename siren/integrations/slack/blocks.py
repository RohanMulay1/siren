from ...agent.state import ActionPlan

RISK_EMOJI    = {"READ": "⚪", "REVERSIBLE": "🟡", "DESTRUCTIVE": "🔴"}
RISK_LABEL    = {"READ": "Read-only (safe)", "REVERSIBLE": "Reversible", "DESTRUCTIVE": "DESTRUCTIVE — irreversible"}
SEV_EMOJI     = {"P1": "🚨", "P2": "🟠", "P3": "🟡", "P4": "⚪"}
SEV_LABEL     = {"P1": "P1 CRITICAL", "P2": "P2 HIGH", "P3": "P3 MEDIUM", "P4": "P4 LOW"}
TIER_EXPLAIN  = {
    "READ":        "This action only *reads* data — no system state will change.",
    "REVERSIBLE":  "This action *modifies* system state but can be undone (e.g. restart, scale).",
    "DESTRUCTIVE": "⚠️ This action *cannot be undone* (e.g. cache flush, LB drain). Review carefully.",
}


def _divider():
    return {"type": "divider"}


def build_approval_message(
    incident_id: str,
    severity: str,
    service: str,
    root_cause: str,
    action: ActionPlan,
    similar_context: str,
    investigation_summary: str,
    correlation_id: str,
    action_index: int = 0,
    total_actions: int = 1,
) -> dict:
    sev_emoji   = SEV_EMOJI.get(severity, "❓")
    sev_label   = SEV_LABEL.get(severity, severity)
    risk_emoji  = RISK_EMOJI.get(action["classification"], "🔴")
    risk_label  = RISK_LABEL.get(action["classification"], action["classification"])
    tier_text   = TIER_EXPLAIN.get(action["classification"], "")

    # Truncate long fields
    root_cause_short = (root_cause or "Under investigation")[:200]
    rationale_short  = (action.get("rationale") or "No rationale provided")[:300]

    blocks = [
        # ── Header ─────────────────────────────────────────────────────────
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{sev_emoji}  SIREN — Human Approval Required",
                "emoji": True,
            },
        },

        # ── Incident snapshot ───────────────────────────────────────────────
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Incident ID*\n`{incident_id}`"},
                {"type": "mrkdwn", "text": f"*Severity*\n{sev_emoji} {sev_label}"},
                {"type": "mrkdwn", "text": f"*Service*\n`{service}`"},
                {"type": "mrkdwn", "text": f"*Step*\n{action_index + 1} of {total_actions} planned actions"},
            ],
        },

        _divider(),

        # ── What went wrong ─────────────────────────────────────────────────
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":mag: *Root Cause*\n>{root_cause_short}",
            },
        },

        # ── Evidence summary ─────────────────────────────────────────────────
        *(
            [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":microscope: *Evidence collected*\n{_format_evidence(investigation_summary)}",
                },
            }] if investigation_summary else []
        ),

        # ── Memory recall ────────────────────────────────────────────────────
        *(
            [{
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": f":brain: *Memory:* {similar_context}",
                }],
            }] if similar_context else []
        ),

        _divider(),

        # ── Proposed action ──────────────────────────────────────────────────
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"{risk_emoji} *Proposed Action*\n"
                    f"```{action['tool_name']}```\n"
                    f"*Risk:* {risk_label}\n"
                    f"_{tier_text}_"
                ),
            },
        },

        # ── Why this action ──────────────────────────────────────────────────
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":bulb: *Why this action?*\n{rationale_short}",
            },
        },

        # ── Tool args (if non-trivial) ────────────────────────────────────────
        *(
            [{
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": f":wrench: *Args:* `{_fmt_args(action.get('tool_args', {}))}`",
                }],
            }] if action.get("tool_args") else []
        ),

        _divider(),

        # ── CTA ──────────────────────────────────────────────────────────────
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    ":point_down: *Review and respond — SIREN is paused until you decide.*\n"
                    "Approve to execute immediately · Reject to skip this action and continue."
                ),
            },
        },

        # ── Buttons ───────────────────────────────────────────────────────────
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅  APPROVE", "emoji": True},
                    "style": "primary",
                    "action_id": "siren_approve",
                    "value": f"{correlation_id}:approve",
                    "confirm": {
                        "title": {"type": "plain_text", "text": "Confirm Approval"},
                        "text": {"type": "mrkdwn", "text": f"Execute `{action['tool_name']}` on *{service}*?"},
                        "confirm": {"type": "plain_text", "text": "Yes, execute"},
                        "deny": {"type": "plain_text", "text": "Cancel"},
                    } if action["classification"] == "DESTRUCTIVE" else None,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌  REJECT", "emoji": True},
                    "style": "danger",
                    "action_id": "siren_reject",
                    "value": f"{correlation_id}:reject",
                },
            ],
        },

        # ── Footer ────────────────────────────────────────────────────────────
        {
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"🤖 SIREN Autonomous Incident Response  |  `{correlation_id[:16]}…`",
            }],
        },
    ]

    # Strip None confirm fields from buttons
    for block in blocks:
        if block.get("type") == "actions":
            for el in block.get("elements", []):
                if el.get("confirm") is None:
                    el.pop("confirm", None)

    return {"text": f"{sev_emoji} SIREN approval needed for {service} ({severity})", "blocks": blocks}


def _format_evidence(raw: str) -> str:
    """Turn 'tool: obs → tool: obs' into a bulleted list."""
    parts = [p.strip() for p in raw.split("→") if p.strip()]
    if not parts:
        return raw
    return "\n".join(f"• {p}" for p in parts)


def _fmt_args(args: dict) -> str:
    if not args:
        return "{}"
    pairs = ", ".join(f"{k}={v}" for k, v in args.items())
    return pairs[:120] + ("…" if len(pairs) > 120 else "")


def build_incident_notification(
    incident_id: str,
    severity: str,
    service: str,
    summary: str,
) -> dict:
    sev_emoji = SEV_EMOJI.get(severity, "❓")
    sev_label = SEV_LABEL.get(severity, severity)
    return {
        "text": f"{sev_emoji} New incident: {service} ({severity})",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{sev_emoji}  New Incident Detected", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Incident ID*\n`{incident_id}`"},
                    {"type": "mrkdwn", "text": f"*Severity*\n{sev_emoji} {sev_label}"},
                    {"type": "mrkdwn", "text": f"*Service*\n`{service}`"},
                    {"type": "mrkdwn", "text": f"*Status*\n🔍 Investigating…"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Summary*\n>{summary[:300]}"},
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "🤖 SIREN is investigating autonomously. Approval request will follow if needed."}],
            },
        ],
    }


def build_resolution_notification(
    incident_id: str,
    severity: str,
    service: str,
    root_cause: str,
    mttr_minutes: float,
    postmortem_id: str | None,
) -> dict:
    sev_emoji = SEV_EMOJI.get(severity, "❓")
    return {
        "text": f"✅ Incident resolved: {service} ({severity}) in {mttr_minutes:.1f} min",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "✅  Incident Resolved", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Incident ID*\n`{incident_id}`"},
                    {"type": "mrkdwn", "text": f"*Service*\n`{service}`"},
                    {"type": "mrkdwn", "text": f"*Severity*\n{sev_emoji} {severity}"},
                    {"type": "mrkdwn", "text": f"*MTTR*\n⏱ {mttr_minutes:.1f} minutes"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f":mag: *Root Cause*\n>{root_cause[:200]}"},
            },
            *(
                [{
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": f":scroll: Post-mortem written · ID `{postmortem_id}`"}],
                }] if postmortem_id else []
            ),
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "🤖 SIREN · Resolution embedded in Qdrant memory for future recall"}],
            },
        ],
    }
