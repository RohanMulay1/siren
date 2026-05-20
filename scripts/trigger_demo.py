"""
Fire the Redis OOM demo incident for competition demo.

Usage:
  python scripts/trigger_demo.py            # fire alert, run SIREN
  python scripts/trigger_demo.py --fill     # fill Redis until OOM first
  python scripts/trigger_demo.py --reset    # reset MTTR tracking

This fires a synthetic Prometheus alert simulating a payments-api Redis OOM.
SIREN will investigate, find 3 similar past incidents, plan a fix,
request Slack approval for FLUSHDB, and auto-verify resolution.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio
import httpx
import redis

SIREN_URL = os.getenv("SIREN_URL", "http://localhost:8000")

DEMO_ALERT = {
    "source": "prometheus",
    "alert_name": "HighErrorRate",
    "severity": "critical",
    "service": "payments-api",
    "description": (
        "payments-api error rate exceeded 40% for 5 minutes. "
        "Redis connection errors observed: OOM command not allowed when used memory > maxmemory."
    ),
    "labels": {
        "env": "production",
        "region": "us-east-1",
        "team": "payments",
        "service": "payments-api",
    },
    "annotations": {
        "runbook": "https://wiki.internal/runbooks/redis-oom",
        "dashboard": "https://grafana.internal/d/payments",
    },
}


def fill_redis_for_demo(redis_url: str = "redis://localhost:6380"):
    """Fill the demo Redis (memory-constrained to 64MB) until near-OOM."""
    print("Filling demo Redis to trigger OOM condition...")
    r = redis.from_url(redis_url)
    r.flushdb()

    # Write 1KB values until OOM
    value = "x" * 1024
    i = 0
    while True:
        try:
            r.set(f"session:{i}", value, ex=86400)
            i += 1
            if i % 1000 == 0:
                info = r.info("memory")
                used_mb = info["used_memory"] / 1024 / 1024
                print(f"  {i} keys written, {used_mb:.1f} MB used...")
        except Exception as e:
            print(f"  Redis OOM reached at {i} keys: {e}")
            break

    print(f"Demo Redis filled with {i} keys. Ready to fire alert.")


async def fire_alert():
    print(f"Firing demo incident to SIREN at {SIREN_URL}...")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{SIREN_URL}/webhook/alert", json=DEMO_ALERT)
        resp.raise_for_status()
        data = resp.json()

    incident_id = data["incident_id"]
    print(f"\nIncident created: {incident_id}")
    print(f"Status: {data['status']}")
    print(f"\nMonitor progress:")
    print(f"  API:       {SIREN_URL}/api/incidents/{incident_id}")
    print(f"  Dashboard: http://localhost:8501")
    print(f"\nSIREN is now investigating. Watch Slack for the APPROVE/REJECT message.")
    return incident_id


async def watch_incident(incident_id: str):
    """Poll incident status until complete."""
    print(f"\nWatching incident {incident_id}...")
    async with httpx.AsyncClient() as client:
        for _ in range(60):  # poll for up to 5 minutes
            await asyncio.sleep(5)
            try:
                resp = await client.get(f"{SIREN_URL}/api/incidents/{incident_id}")
                if resp.status_code == 200:
                    state = resp.json()
                    status = state.get("workflow_status", "unknown")
                    print(f"  Status: {status}")
                    if status in ("complete", "escalated"):
                        print(f"\nIncident resolved!")
                        print(f"  Root cause: {state.get('root_cause', 'N/A')}")
                        print(f"  Qdrant vector: {state.get('qdrant_vector_id', 'N/A')}")
                        return
            except Exception:
                pass


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--fill" in args:
        fill_redis_for_demo()

    async def main():
        incident_id = await fire_alert()
        if "--watch" in args:
            await watch_incident(incident_id)

    asyncio.run(main())
