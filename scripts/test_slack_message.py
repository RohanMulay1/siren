"""Send a test Slack approval message to preview the new formatting."""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from siren.integrations.slack.client import send_approval_request, send_notification, send_resolution

TEST_ACTION = {
    "action_id": "test-001",
    "tool_name": "flush_redis_cache",
    "tool_args": {"redis_url": "redis://localhost:6379", "db_index": 0},
    "classification": "DESTRUCTIVE",
    "rationale": "Redis memory is at 99.8% utilisation. The OOM killer has triggered 3 times in the last hour. A cache flush will immediately free memory and restore payments-api to normal operation. Keyspace TTLs are short (< 60s) so data loss impact is minimal.",
    "approved": None,
}

async def main():
    print("Sending test incident notification…")
    await send_notification(
        incident_id="INC-20260520-TEST001",
        severity="P1",
        service="payments-api",
        summary="Redis out of memory — OOM command not allowed when used memory > maxmemory. payments-api error rate 45%, p99 latency 8.4s. Restart count: 3.",
    )
    print("OK Notification sent")

    await asyncio.sleep(1)

    print("Sending test approval request…")
    ts = await send_approval_request(
        incident_id="INC-20260520-TEST001",
        correlation_id="INC-20260520-TEST001",
        severity="P1",
        service="payments-api",
        root_cause="Redis has exceeded its maxmemory limit (configured: 512MB, used: 511.9MB). Caused by a spike in session token storage from a deploy at 14:32 UTC that removed TTL expiry from auth tokens. Memory has been growing at ~45MB/hour since the deploy.",
        action=TEST_ACTION,
        similar_context="Based on 3 similar past incidents. Best match: 92% — INC-20260418: Redis OOM on payments-api, previously resolved by FLUSHDB in 2.1 min.",
        investigation_summary="query_prometheus: error_rate=45.2% p99=8400ms → fetch_cloudwatch_logs: 'OOM command not allowed' x847 in last 10m → inspect_docker_container: memory_percent=99.8% restart_count=3",
        action_index=1,
        total_actions=2,
    )
    print(f"OK Approval request sent (ts={ts})")

    await asyncio.sleep(1)

    print("Sending test resolution notification…")
    await send_resolution(
        incident_id="INC-20260520-TEST001",
        severity="P1",
        service="payments-api",
        root_cause="Redis OOM caused by missing TTL on auth session tokens introduced in deploy d4f7a at 14:32 UTC. Cache flush restored service immediately.",
        mttr_minutes=2.4,
        postmortem_id="pm-a3f1",
    )
    print("OK Resolution sent")
    print("\nAll 3 messages sent — check your Slack channel!")

asyncio.run(main())
