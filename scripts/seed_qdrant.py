"""
Seed Qdrant with 20 synthetic historical incidents.
Run BEFORE the demo to populate memory so SIREN shows instant recall quality.

Usage: python scripts/seed_qdrant.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timedelta, timezone
from siren.memory import get_qdrant_client, ensure_collection, upsert_incident
from siren.memory.schemas import IncidentVectorPayload
from siren.config import get_settings

SEED_INCIDENTS = [
    # OOM incidents — these match the demo scenario
    {
        "incident_id": "INC-20241001-SEED01",
        "severity": "P1",
        "affected_service": "payments-api",
        "alert_source": "prometheus",
        "incident_summary": "payments-api high latency spike, Redis connection errors, OOM kill observed",
        "root_cause": "Redis instance hit maxmemory limit due to session key accumulation without TTL",
        "root_cause_category": "oom",
        "symptoms": ["high_latency", "redis_errors", "connection_timeouts", "oom_kill", "payments_service"],
        "resolution_summary": "Flushed Redis session database (db=1), added 24h TTL to all session keys",
        "actions_taken": ["flush_redis_cache", "update_redis_config"],
        "resolved": True,
        "time_to_resolve_minutes": 23.0,
        "resolution_effective": True,
    },
    {
        "incident_id": "INC-20241015-SEED02",
        "severity": "P1",
        "affected_service": "checkout-service",
        "alert_source": "prometheus",
        "incident_summary": "checkout service degradation, cache layer unresponsive, error rate 67%",
        "root_cause": "Redis OOM caused by large sorted set accumulation in leaderboard feature without expiry",
        "root_cause_category": "oom",
        "symptoms": ["cache_miss_spike", "redis_oom", "checkout_errors", "error_rate_high"],
        "resolution_summary": "Restarted Redis container, implemented LRU eviction policy",
        "actions_taken": ["restart_docker_container", "update_redis_maxmemory_policy"],
        "resolved": True,
        "time_to_resolve_minutes": 31.0,
        "resolution_effective": True,
    },
    {
        "incident_id": "INC-20241020-SEED03",
        "severity": "P2",
        "affected_service": "payments-api",
        "alert_source": "cloudwatch",
        "incident_summary": "payments-api elevated error rate 22%, Redis READONLY errors in logs",
        "root_cause": "Redis replica promoted to master but maxmemory policy was set to noeviction, causing OOM on write",
        "root_cause_category": "oom",
        "symptoms": ["redis_readonly", "write_errors", "elevated_error_rate"],
        "resolution_summary": "Changed maxmemory-policy to allkeys-lru, flushed stale keys",
        "actions_taken": ["update_redis_config", "flush_redis_cache"],
        "resolved": True,
        "time_to_resolve_minutes": 18.0,
        "resolution_effective": True,
    },
    # Connection pool exhaustion
    {
        "incident_id": "INC-20241101-SEED04",
        "severity": "P1",
        "affected_service": "user-service",
        "alert_source": "prometheus",
        "incident_summary": "user-service complete outage, database connection pool exhausted",
        "root_cause": "Unclosed database connections in async task handler caused pool exhaustion under load",
        "root_cause_category": "connection_pool",
        "symptoms": ["db_timeout", "connection_pool_exhausted", "service_outage", "high_latency"],
        "resolution_summary": "Restarted user-service to reclaim connections, applied async context manager fix",
        "actions_taken": ["restart_docker_container", "deploy_hotfix"],
        "resolved": True,
        "time_to_resolve_minutes": 45.0,
        "resolution_effective": True,
    },
    {
        "incident_id": "INC-20241110-SEED05",
        "severity": "P2",
        "affected_service": "reporting-api",
        "alert_source": "prometheus",
        "incident_summary": "reporting-api timeouts, postgres connection wait time > 5s",
        "root_cause": "Long-running analytics query held connections for 8+ minutes, starving OLTP queries",
        "root_cause_category": "connection_pool",
        "symptoms": ["slow_queries", "connection_wait", "timeout_errors"],
        "resolution_summary": "Killed long-running query, set statement_timeout=30s for analytics role",
        "actions_taken": ["query_postgres_readonly", "update_pg_config"],
        "resolved": True,
        "time_to_resolve_minutes": 12.0,
        "resolution_effective": True,
    },
    # Deploy regressions
    {
        "incident_id": "INC-20241105-SEED06",
        "severity": "P1",
        "affected_service": "order-service",
        "alert_source": "pagerduty",
        "incident_summary": "order-service 500 errors started immediately after deploy v2.4.1",
        "root_cause": "Missing environment variable STRIPE_WEBHOOK_SECRET in new deployment caused panic on startup",
        "root_cause_category": "deploy_regression",
        "symptoms": ["500_errors", "deploy_correlation", "startup_panic", "missing_env_var"],
        "resolution_summary": "Rolled back to v2.4.0, added missing env var, redeployed",
        "actions_taken": ["scale_service", "deploy_rollback"],
        "resolved": True,
        "time_to_resolve_minutes": 8.0,
        "resolution_effective": True,
    },
    {
        "incident_id": "INC-20241112-SEED07",
        "severity": "P2",
        "affected_service": "payments-api",
        "alert_source": "prometheus",
        "incident_summary": "payments-api p99 latency increased 3x after deploy v3.1.0",
        "root_cause": "New synchronous external API call added in critical path without timeout, adding 800ms median latency",
        "root_cause_category": "deploy_regression",
        "symptoms": ["latency_increase", "deploy_correlation", "external_api_call", "p99_spike"],
        "resolution_summary": "Feature flagged off the new API call, hotfix deployed with async + timeout",
        "actions_taken": ["toggle_feature_flag", "deploy_hotfix"],
        "resolved": True,
        "time_to_resolve_minutes": 35.0,
        "resolution_effective": True,
    },
    # Disk saturation
    {
        "incident_id": "INC-20241108-SEED08",
        "severity": "P1",
        "affected_service": "log-aggregator",
        "alert_source": "cloudwatch",
        "incident_summary": "log-aggregator disk 98% full, failing to write logs, downstream services backing up",
        "root_cause": "Log rotation policy misconfigured — logs older than 7 days not being deleted due to cron job failure",
        "root_cause_category": "disk_saturation",
        "symptoms": ["disk_full", "log_write_failure", "backup_accumulation"],
        "resolution_summary": "Manually deleted 30-day old logs, fixed log rotation cron, added disk alert at 85%",
        "actions_taken": ["delete_old_logs", "fix_log_rotation"],
        "resolved": True,
        "time_to_resolve_minutes": 15.0,
        "resolution_effective": True,
    },
    # Network issues
    {
        "incident_id": "INC-20241115-SEED09",
        "severity": "P2",
        "affected_service": "api-gateway",
        "alert_source": "prometheus",
        "incident_summary": "api-gateway intermittent 502s, upstream timeout errors to auth-service",
        "root_cause": "auth-service health check endpoint was slow (600ms) causing ALB to drain it from rotation",
        "root_cause_category": "network",
        "symptoms": ["502_errors", "upstream_timeout", "health_check_failure", "alb_drain"],
        "resolution_summary": "Optimized health check endpoint, scaled auth-service to 3 replicas",
        "actions_taken": ["scale_service", "optimize_health_check"],
        "resolved": True,
        "time_to_resolve_minutes": 20.0,
        "resolution_effective": True,
    },
    # Config errors
    {
        "incident_id": "INC-20241118-SEED10",
        "severity": "P1",
        "affected_service": "notification-service",
        "alert_source": "custom",
        "incident_summary": "notification-service unable to send emails, SMTP authentication failures",
        "root_cause": "SMTP password rotated in secrets manager but notification-service was not restarted to pick up new secret",
        "root_cause_category": "config_error",
        "symptoms": ["smtp_auth_failure", "email_delivery_failure", "stale_credentials"],
        "resolution_summary": "Restarted notification-service to reload secrets from environment",
        "actions_taken": ["restart_docker_container"],
        "resolved": True,
        "time_to_resolve_minutes": 6.0,
        "resolution_effective": True,
    },
    # More OOM variants to improve recall quality for demo
    {
        "incident_id": "INC-20241120-SEED11",
        "severity": "P1",
        "affected_service": "session-service",
        "alert_source": "prometheus",
        "incident_summary": "session-service OOM, Redis memory at 99.9%, users being logged out",
        "root_cause": "User session tokens accumulating in Redis without TTL after auth provider change",
        "root_cause_category": "oom",
        "symptoms": ["redis_oom", "session_loss", "user_logout", "memory_full"],
        "resolution_summary": "Flushed Redis session DB, added 8h TTL to all session keys",
        "actions_taken": ["flush_redis_cache", "update_redis_config"],
        "resolved": True,
        "time_to_resolve_minutes": 19.0,
        "resolution_effective": True,
    },
    {
        "incident_id": "INC-20241122-SEED12",
        "severity": "P2",
        "affected_service": "cart-service",
        "alert_source": "prometheus",
        "incident_summary": "cart-service error rate 18%, Redis MISCONF errors, OOM killer active",
        "root_cause": "Cart item serialization bug causing bloated JSON payloads stored in Redis (50x normal size)",
        "root_cause_category": "oom",
        "symptoms": ["redis_misconf", "oom_killer", "elevated_error_rate", "large_payloads"],
        "resolution_summary": "Restarted Redis to clear memory, deployed fix for serialization bug",
        "actions_taken": ["restart_docker_container", "flush_redis_cache", "deploy_hotfix"],
        "resolved": True,
        "time_to_resolve_minutes": 28.0,
        "resolution_effective": True,
    },
]


def seed():
    settings = get_settings()
    qdrant = get_qdrant_client()
    ensure_collection(qdrant, settings.qdrant_collection)

    print(f"Seeding {len(SEED_INCIDENTS)} incidents into Qdrant collection '{settings.qdrant_collection}'...")

    base_date = datetime.now(timezone.utc) - timedelta(days=60)

    for i, inc_data in enumerate(SEED_INCIDENTS):
        created_at = base_date + timedelta(days=i * 3, hours=i % 24)
        resolved_at = created_at + timedelta(minutes=inc_data.get("time_to_resolve_minutes", 20))

        payload = IncidentVectorPayload(
            incident_id=inc_data["incident_id"],
            severity=inc_data["severity"],
            affected_service=inc_data["affected_service"],
            alert_source=inc_data["alert_source"],
            incident_summary=inc_data["incident_summary"],
            root_cause=inc_data["root_cause"],
            root_cause_category=inc_data["root_cause_category"],
            symptoms=inc_data["symptoms"],
            resolution_summary=inc_data["resolution_summary"],
            actions_taken=inc_data["actions_taken"],
            resolved=inc_data["resolved"],
            created_at=created_at,
            resolved_at=resolved_at,
            time_to_resolve_minutes=inc_data.get("time_to_resolve_minutes"),
            resolution_effective=inc_data.get("resolution_effective", True),
        )

        vector_id = upsert_incident(qdrant, payload)
        print(f"  [{i+1}/{len(SEED_INCIDENTS)}] {inc_data['incident_id']} → vector {vector_id[:8]}...")

    print(f"\nSeeding complete. Total incidents in Qdrant: {len(SEED_INCIDENTS)}")
    print("Run 'python scripts/trigger_demo.py' to fire the demo incident.")


if __name__ == "__main__":
    seed()
