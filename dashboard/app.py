"""
SIREN Dashboard — Live incident feed, MTTR trend (self-improvement proof), Qdrant memory stats.
Run: streamlit run dashboard/app.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import httpx
import time
from datetime import datetime

st.set_page_config(
    page_title="SIREN — Incident Response Engine",
    page_icon="🚨",
    layout="wide",
)

SIREN_URL = os.getenv("SIREN_API_URL", "http://localhost:8000")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

st.title("🚨 SIREN — Self-Improving Incident Response Engine")
st.caption("Autonomous AI agent for production incident response")

# --- Health bar ---
try:
    with httpx.Client(timeout=3) as client:
        health = client.get(f"{SIREN_URL}/health").json()
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", "🟢 Online")
    col2.metric("Memory (Qdrant)", f"{health.get('qdrant_incidents', 0)} incidents")
    col3.metric("Environment", health.get("environment", "unknown").upper())
except Exception:
    st.error("SIREN API unreachable. Start the server with: uvicorn siren.main:app --reload")
    st.stop()

st.divider()

# --- MTTR self-improvement chart ---
st.subheader("📉 MTTR Trend — Self-Improvement Signal")
st.caption("Average resolution time decreases as Qdrant memory grows. This is the proof of learning.")

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    import plotly.express as px
    import pandas as pd

    qdrant = QdrantClient(url=QDRANT_URL)
    collection = os.getenv("QDRANT_COLLECTION", "incidents")

    results = qdrant.scroll(
        collection_name=collection,
        scroll_filter=Filter(must=[FieldCondition(key="resolved", match=MatchValue(value=True))]),
        limit=500,
        with_payload=True,
    )[0]

    if results:
        rows = []
        for r in results:
            p = r.payload
            if p.get("time_to_resolve_minutes") and p.get("created_at"):
                rows.append({
                    "date": pd.to_datetime(p["created_at"]),
                    "mttr": float(p["time_to_resolve_minutes"]),
                    "service": p.get("affected_service", "unknown"),
                    "severity": p.get("severity", "P3"),
                    "root_cause_category": p.get("root_cause_category", "other"),
                })

        if rows:
            df = pd.DataFrame(rows).sort_values("date")
            df["incident_number"] = range(1, len(df) + 1)

            fig = px.line(
                df, x="incident_number", y="mttr",
                color="service",
                markers=True,
                title="MTTR by Incident Number — each point represents one resolved incident",
                labels={"incident_number": "Incident # (chronological)", "mttr": "MTTR (minutes)"},
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

            avg_first_half = df["mttr"].head(len(df) // 2).mean()
            avg_second_half = df["mttr"].tail(len(df) // 2).mean()
            if avg_first_half > 0:
                improvement = (1 - avg_second_half / avg_first_half) * 100
                if improvement > 0:
                    st.success(f"✅ MTTR improved by **{improvement:.0f}%** as Qdrant memory grew from {len(df)//2} → {len(df)} incidents")
        else:
            st.info("No resolved incidents yet. Run seed_qdrant.py and trigger_demo.py to populate.")
    else:
        st.info("Qdrant collection is empty. Run: python scripts/seed_qdrant.py")
except Exception as e:
    st.warning(f"Could not load MTTR data: {e}")

st.divider()

# --- Qdrant memory breakdown ---
st.subheader("🧠 Incident Memory (Qdrant)")
col1, col2 = st.columns(2)

try:
    from qdrant_client import QdrantClient
    import plotly.express as px
    import pandas as pd
    from collections import Counter

    qdrant = QdrantClient(url=QDRANT_URL)
    collection = os.getenv("QDRANT_COLLECTION", "incidents")
    results = qdrant.scroll(collection_name=collection, limit=500, with_payload=True)[0]

    if results:
        categories = Counter(r.payload.get("root_cause_category", "other") for r in results)
        services = Counter(r.payload.get("affected_service", "unknown") for r in results)

        with col1:
            fig1 = px.pie(
                values=list(categories.values()),
                names=list(categories.keys()),
                title="By Root Cause Category",
            )
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = px.bar(
                x=list(services.keys()),
                y=list(services.values()),
                title="By Affected Service",
                labels={"x": "Service", "y": "Incident Count"},
            )
            st.plotly_chart(fig2, use_container_width=True)
except Exception as e:
    st.warning(f"Could not load memory stats: {e}")

st.divider()

# --- Fire demo alert button ---
st.subheader("🔥 Demo Controls")
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("Fire Demo Incident", type="primary", use_container_width=True):
        try:
            with httpx.Client() as client:
                resp = client.post(f"{SIREN_URL}/webhook/alert", json={
                    "source": "prometheus",
                    "alert_name": "HighErrorRate",
                    "severity": "critical",
                    "service": "payments-api",
                    "description": "payments-api error rate exceeded 40%. Redis OOM errors observed.",
                    "labels": {"env": "production", "region": "us-east-1", "service": "payments-api"},
                })
                data = resp.json()
                st.success(f"Incident created: **{data['incident_id']}**")
                st.session_state["last_incident"] = data["incident_id"]
        except Exception as e:
            st.error(f"Failed to fire alert: {e}")

with col2:
    if "last_incident" in st.session_state:
        incident_id = st.session_state["last_incident"]
        try:
            with httpx.Client() as client:
                resp = client.get(f"{SIREN_URL}/api/incidents/{incident_id}", timeout=3)
                if resp.status_code == 200:
                    state = resp.json()
                    status = state.get("workflow_status", "unknown")
                    root_cause = state.get("root_cause", "Investigating...")
                    similar_count = len(state.get("similar_incidents", []))

                    st.metric("Workflow Status", status.upper().replace("_", " "))
                    st.metric("Similar Incidents Found", similar_count)
                    if root_cause and root_cause != "Investigating...":
                        st.info(f"**Root Cause:** {root_cause}")
        except Exception:
            pass

st.caption(f"Last refreshed: {datetime.utcnow().strftime('%H:%M:%S UTC')} | Auto-refreshes every 10s")

# Auto-refresh
time.sleep(0.1)
st.rerun() if st.checkbox("Auto-refresh", value=True) else None
