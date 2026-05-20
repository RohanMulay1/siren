"""
SIREN Dashboard — Live incident feed, MTTR trend, Qdrant memory stats.
Run: streamlit run dashboard/app.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from collections import Counter
import time

st.set_page_config(
    page_title="SIREN — Incident Response Engine",
    page_icon="🚨",
    layout="wide",
)

SIREN_URL = os.getenv("SIREN_API_URL", "http://localhost:8000")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "incidents")

STATUS_COLOR = {
    "triaging": "🟡",
    "recalling": "🔵",
    "investigating": "🔵",
    "planning": "🟠",
    "awaiting_approval": "🔴",
    "executing": "🟠",
    "verifying": "🟡",
    "writing_postmortem": "🟢",
    "complete": "✅",
    "escalated": "⚠️",
}
SEV_COLOR = {"P1": "🔴", "P2": "🟠", "P3": "🟡", "P4": "⚪"}

NODE_ORDER = [
    "ingesting", "triaging", "recalling", "investigating",
    "planning", "awaiting_approval", "executing", "verifying",
    "writing_postmortem", "complete",
]


# ── helpers ──────────────────────────────────────────────────────────────────

def api(path, timeout=4):
    try:
        with httpx.Client(timeout=timeout) as c:
            r = c.get(f"{SIREN_URL}{path}")
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None


def qdrant_scroll():
    try:
        from qdrant_client import QdrantClient
        q = QdrantClient(url=QDRANT_URL)
        return q.scroll(collection_name=QDRANT_COLLECTION, limit=500, with_payload=True)[0]
    except Exception:
        return []


# ── header / health ──────────────────────────────────────────────────────────

st.title("🚨 SIREN — Self-Improving Incident Response Engine")
st.caption("Autonomous AI agent · multi-step tool-use · Slack human-in-the-loop · Qdrant memory")

health = api("/health")
if not health:
    st.error("SIREN API unreachable. Run: `uvicorn siren.main:app --host 0.0.0.0 --port 8000`")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("API", "🟢 Online")
c2.metric("Qdrant Memory", f"{health.get('qdrant_incidents', 0)} incidents")
c3.metric("Environment", health.get("environment", "dev").upper())
c4.metric("Version", health.get("version", "1.0.0"))

st.divider()

# ── fire demo button ──────────────────────────────────────────────────────────

st.subheader("🔥 Demo Controls")
col_btn, col_id = st.columns([1, 3])
with col_btn:
    if st.button("Fire Redis OOM Incident", type="primary", use_container_width=True):
        try:
            with httpx.Client(timeout=5) as c:
                r = c.post(f"{SIREN_URL}/webhook/alert", json={
                    "source": "custom",
                    "alert_name": "RedisOOM",
                    "severity": "P1",
                    "service": "payments-api",
                    "description": "Redis out of memory — OOM command not allowed. Error rate 45%. Payments service degraded.",
                    "labels": {"env": "production"},
                })
                data = r.json()
                st.session_state["active_incident"] = data["incident_id"]
                st.success(f"Created: **{data['incident_id']}**")
        except Exception as e:
            st.error(str(e))

with col_id:
    manual_id = st.text_input("Or poll an existing incident ID:", key="manual_id")
    if manual_id:
        st.session_state["active_incident"] = manual_id

st.divider()

# ── live incident tracker ─────────────────────────────────────────────────────

if "active_incident" in st.session_state:
    inc_id = st.session_state["active_incident"]
    st.subheader(f"🔎 Live: `{inc_id}`")

    state = api(f"/api/incidents/{inc_id}")
    if state:
        status = state.get("workflow_status", "unknown")
        icon = STATUS_COLOR.get(status, "⚪")
        sev = state.get("severity", "?")
        sev_icon = SEV_COLOR.get(sev, "⚪")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Status", f"{icon} {status.replace('_', ' ').upper()}")
        m2.metric("Severity", f"{sev_icon} {sev}")
        m3.metric("Investigation Iterations", state.get("investigation_iterations", 0))
        m4.metric("Actions Planned", len(state.get("action_plan", [])))

        # Node progress bar
        current_idx = NODE_ORDER.index(status) if status in NODE_ORDER else 0
        progress = (current_idx + 1) / len(NODE_ORDER)
        st.progress(progress, text=f"Node: {status.replace('_', ' ')}")

        # Root cause
        rc = state.get("root_cause")
        if rc:
            conf = state.get("root_cause_confidence", 0)
            st.info(f"**Root Cause** (confidence {conf:.0%}): {rc}")

        # Action plan
        plan = state.get("action_plan", [])
        if plan:
            st.markdown("**Action Plan:**")
            idx = state.get("current_action_index", 0)
            tier_icon = {"READ": "👁️", "REVERSIBLE": "🔄", "DESTRUCTIVE": "💥"}
            for i, a in enumerate(plan):
                approved = a.get("approved")
                if approved is True:
                    badge = "✅ approved"
                elif approved is False:
                    badge = "❌ rejected"
                elif i < idx:
                    badge = "✅ executed"
                elif i == idx and status == "awaiting_approval":
                    badge = "⏳ **awaiting your APPROVE in Slack**"
                else:
                    badge = "pending"
                icon_t = tier_icon.get(a["classification"], "❓")
                st.markdown(f"  {icon_t} `{a['tool_name']}` — {a['classification']} — {badge}")

        if status == "awaiting_approval":
            st.warning("⏳ Check Slack — click **APPROVE** or **REJECT** to continue")
    else:
        st.info("Incident initializing... (first 20-30s are investigation)")

st.divider()

# ── recent incidents feed ─────────────────────────────────────────────────────

st.subheader("📋 Recent Incidents")
incidents = api("/api/incidents") or []
if incidents:
    rows = []
    for inc in incidents:
        sev = inc.get("severity", "?")
        status = inc.get("workflow_status", "?")
        rows.append({
            "Severity": f"{SEV_COLOR.get(sev,'⚪')} {sev}",
            "Incident ID": inc.get("incident_id", ""),
            "Service": inc.get("affected_service", ""),
            "Status": f"{STATUS_COLOR.get(status,'⚪')} {status}",
            "Root Cause": (inc.get("root_cause") or "")[:80],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("No incidents yet — click 'Fire Redis OOM Incident' above.")

st.divider()

# ── MTTR self-improvement chart ───────────────────────────────────────────────

st.subheader("📉 MTTR Trend — Self-Improvement Signal")
st.caption("As Qdrant memory grows, recalled playbooks shorten investigation time. Watch MTTR fall.")

records = qdrant_scroll()
if records:
    rows = []
    for r in records:
        p = r.payload
        if p.get("time_to_resolve_minutes") and p.get("created_at"):
            rows.append({
                "date": pd.to_datetime(p["created_at"]),
                "mttr": float(p["time_to_resolve_minutes"]),
                "service": p.get("affected_service", "unknown"),
                "severity": p.get("severity", "P3"),
                "category": p.get("root_cause_category", "other"),
                "description": (p.get("description") or "")[:60],
            })

    if rows:
        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        df["Incident #"] = range(1, len(df) + 1)

        fig = px.scatter(
            df, x="Incident #", y="mttr",
            color="category", size_max=10,
            trendline="ols",
            hover_data=["service", "severity", "description"],
            title="MTTR per Incident (with LOWESS trend) — downward slope = self-improvement",
            labels={"mttr": "MTTR (minutes)", "Incident #": "Incident # (chronological)"},
        )
        fig.update_traces(marker=dict(size=10), selector=dict(mode="markers"))
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)

        n = len(df)
        if n >= 4:
            first_avg = df["mttr"].head(n // 2).mean()
            last_avg = df["mttr"].tail(n // 2).mean()
            delta = first_avg - last_avg
            pct = (delta / first_avg * 100) if first_avg > 0 else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("Avg MTTR (first half)", f"{first_avg:.1f} min")
            c2.metric("Avg MTTR (second half)", f"{last_avg:.1f} min", delta=f"-{delta:.1f} min", delta_color="normal")
            c3.metric("Improvement", f"{pct:.0f}%")
    else:
        st.info("No resolved incidents with MTTR data yet.")
else:
    st.info("Qdrant is empty. Run: `python scripts/seed_qdrant.py`")

st.divider()

# ── Qdrant memory breakdown ───────────────────────────────────────────────────

st.subheader("🧠 Incident Memory (Qdrant)")
if records:
    categories = Counter(r.payload.get("root_cause_category", "other") for r in records)
    services = Counter(r.payload.get("affected_service", "unknown") for r in records)
    severities = Counter(r.payload.get("severity", "P3") for r in records)

    c1, c2, c3 = st.columns(3)
    with c1:
        fig = px.pie(values=list(categories.values()), names=list(categories.keys()),
                     title=f"By Root Cause Category ({len(records)} total)")
        fig.update_layout(height=280)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(x=list(services.keys()), y=list(services.values()),
                     title="By Service", labels={"x": "Service", "y": "Count"})
        fig.update_layout(height=280)
        st.plotly_chart(fig, use_container_width=True)
    with c3:
        sev_order = ["P1", "P2", "P3", "P4"]
        sev_counts = [severities.get(s, 0) for s in sev_order]
        colors = ["#e74c3c", "#e67e22", "#f1c40f", "#95a5a6"]
        fig = go.Figure(go.Bar(x=sev_order, y=sev_counts, marker_color=colors))
        fig.update_layout(title="By Severity", height=280,
                          xaxis_title="Severity", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption(f"Refreshed at {datetime.utcnow().strftime('%H:%M:%S UTC')} · "
           f"[API Docs]({SIREN_URL}/docs) · "
           f"[GitHub](https://github.com/RohanMulay1/siren)")

# Auto-refresh toggle
if st.checkbox("Auto-refresh every 8s", value=True):
    time.sleep(8)
    st.rerun()
