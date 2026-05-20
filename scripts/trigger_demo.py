"""
Fire the SIREN Redis OOM demo end-to-end.

Usage:
  python scripts/trigger_demo.py           # fire + watch (default)
  python scripts/trigger_demo.py --quiet   # fire only, no polling
  python scripts/trigger_demo.py --repeat N  # fire N incidents to grow MTTR trend

What happens:
  1. Posts a synthetic Redis OOM alert to SIREN
  2. SIREN triages P1, recalls similar incidents from Qdrant
  3. Investigates root cause via tool-use loop (logs + metrics + docker inspect)
  4. Plans: restart_docker_container (auto) + flush_redis_cache (Slack approval)
  5. Sends Slack APPROVE/REJECT message — click APPROVE
  6. Executes flush, verifies recovery, writes post-mortem to Qdrant
  7. Prints final MTTR and Qdrant vector ID
"""
import sys, os, asyncio, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import httpx

SIREN_URL = os.getenv("SIREN_URL", "http://localhost:8000")

DEMO_ALERT = {
    "source": "custom",
    "alert_name": "RedisOOM",
    "severity": "P1",
    "service": "payments-api",
    "description": (
        "Redis out of memory — OOM command not allowed when used memory > maxmemory. "
        "payments-api error rate 45%, p99 latency 8.4s. Restart count: 3."
    ),
    "labels": {"env": "production", "region": "us-east-1", "team": "payments"},
}

STATUS_ICON = {
    "triaging": "🔍", "recalling": "🧠", "investigating": "🔬",
    "planning": "📋", "awaiting_approval": "⏳", "executing": "⚙️",
    "verifying": "✅", "writing_postmortem": "📝",
    "complete": "✅", "escalated": "⚠️",
}


async def fire_and_watch(label: str = "") -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{SIREN_URL}/webhook/alert", json=DEMO_ALERT)
        r.raise_for_status()
        data = r.json()

    incident_id = data["incident_id"]
    tag = f" [{label}]" if label else ""
    print(f"\n{'='*60}")
    print(f"Incident created{tag}: {incident_id}")
    print(f"Dashboard:  http://localhost:8501")
    print(f"API state:  {SIREN_URL}/api/incidents/{incident_id}")
    print(f"{'='*60}")

    last_status = None
    start = time.time()

    async with httpx.AsyncClient(timeout=5) as client:
        for _ in range(120):  # up to 10 minutes
            await asyncio.sleep(5)
            try:
                r = await client.get(f"{SIREN_URL}/api/incidents/{incident_id}")
                if r.status_code != 200:
                    continue
                state = r.json()
            except Exception:
                continue

            status = state.get("workflow_status", "unknown")
            if status != last_status:
                icon = STATUS_ICON.get(status, "⚪")
                elapsed = int(time.time() - start)
                print(f"  [{elapsed:3d}s] {icon}  {status.replace('_', ' ').upper()}", end="")
                if status == "investigating":
                    print(f"  (iter {state.get('investigation_iterations', 0)}/5)", end="")
                if status == "awaiting_approval":
                    plan = state.get("action_plan", [])
                    idx = state.get("current_action_index", 0)
                    if plan and idx < len(plan):
                        pending = plan[idx]["tool_name"]
                        print(f"\n\n  >>> CHECK SLACK — click APPROVE for [{pending}] <<<\n", end="")
                print()
                last_status = status

            if status in ("complete", "escalated"):
                elapsed = int(time.time() - start)
                print(f"\n{'='*60}")
                print(f"DONE in {elapsed}s ({elapsed/60:.1f} min)")
                print(f"Root cause:   {state.get('root_cause', 'N/A')}")
                print(f"Confidence:   {state.get('root_cause_confidence', 0):.0%}")
                print(f"Post-mortem:  {state.get('postmortem_id', 'N/A')}")
                print(f"Qdrant ID:    {state.get('qdrant_vector_id', 'N/A')}")
                print(f"{'='*60}")
                return {"incident_id": incident_id, "mttr_seconds": elapsed, "status": status}

    print("Timed out after 10 minutes.")
    return {"incident_id": incident_id, "status": "timeout"}


async def main():
    args = sys.argv[1:]
    quiet = "--quiet" in args
    repeat = 1
    for i, a in enumerate(args):
        if a == "--repeat" and i + 1 < len(args):
            repeat = int(args[i + 1])

    # Health check
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            h = (await client.get(f"{SIREN_URL}/health")).json()
        print(f"SIREN API: online | Qdrant: {h.get('qdrant_incidents', 0)} incidents in memory")
    except Exception:
        print(f"ERROR: SIREN API not reachable at {SIREN_URL}")
        print("Start with: uvicorn siren.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)

    results = []
    for i in range(repeat):
        label = f"run {i+1}/{repeat}" if repeat > 1 else ""
        if quiet:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(f"{SIREN_URL}/webhook/alert", json=DEMO_ALERT)
                data = r.json()
                print(f"Fired: {data['incident_id']}")
        else:
            result = await fire_and_watch(label)
            results.append(result)
            if repeat > 1 and i < repeat - 1:
                print("\nWaiting 10s before next run...")
                await asyncio.sleep(10)

    if len(results) > 1:
        print(f"\n{'='*60}")
        print("MTTR SUMMARY (self-improvement proof):")
        for i, r in enumerate(results):
            mins = r.get("mttr_seconds", 0) / 60
            print(f"  Run {i+1}: {mins:.1f} min  ({r['status']})")
        mttr_vals = [r["mttr_seconds"] for r in results if r.get("mttr_seconds")]
        if len(mttr_vals) >= 2:
            improvement = (mttr_vals[0] - mttr_vals[-1]) / mttr_vals[0] * 100
            print(f"\n  Improvement run 1 -> {len(results)}: {improvement:.0f}%")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
