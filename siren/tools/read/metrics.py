import httpx
from datetime import datetime, timedelta
from ..registry import register_tool


@register_tool("READ")
class QueryPrometheus:
    NAME = "query_prometheus"
    DESCRIPTION = (
        "Execute a PromQL query against Prometheus. "
        "Use for CPU, memory, error rate, latency, and saturation metrics. "
        "Example queries: rate(http_requests_total{status=~'5..'}[5m]), "
        "process_resident_memory_bytes, redis_memory_used_bytes."
    )
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "PromQL expression"},
            "start": {"type": "string", "description": "ISO8601 start time, defaults to 30 minutes ago"},
            "end": {"type": "string", "description": "ISO8601 end time, defaults to now"},
            "step": {"type": "string", "description": "Resolution step, e.g. 30s, 5m", "default": "1m"},
            "instant": {"type": "boolean", "description": "If true, run instant query instead of range", "default": False},
        },
        "required": ["query"],
    }

    @staticmethod
    async def execute(
        query: str,
        start: str | None = None,
        end: str | None = None,
        step: str = "1m",
        instant: bool = False,
        prometheus_url: str = "http://localhost:9090",
    ) -> str:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                if instant:
                    resp = await client.get(
                        f"{prometheus_url}/api/v1/query",
                        params={"query": query},
                    )
                else:
                    end_dt = end or datetime.utcnow().isoformat() + "Z"
                    start_dt = start or (datetime.utcnow() - timedelta(minutes=30)).isoformat() + "Z"
                    resp = await client.get(
                        f"{prometheus_url}/api/v1/query_range",
                        params={"query": query, "start": start_dt, "end": end_dt, "step": step},
                    )

                resp.raise_for_status()
                data = resp.json()

                if data["status"] != "success":
                    return f"[Prometheus error] {data.get('error', 'unknown')}"

                result = data["data"]["result"]
                if not result:
                    return f"No data for query: {query}"

                lines = [f"Query: {query}"]
                for series in result[:10]:  # cap at 10 series
                    labels = series.get("metric", {})
                    label_str = ", ".join(f'{k}="{v}"' for k, v in labels.items())
                    if instant or "value" in series:
                        val = series["value"][1]
                        lines.append(f"  {{{label_str}}}: {val}")
                    else:
                        values = series.get("values", [])
                        if values:
                            latest = values[-1][1]
                            lines.append(f"  {{{label_str}}}: latest={latest} ({len(values)} points)")

                return "\n".join(lines)
        except Exception as e:
            return f"[Prometheus error] {type(e).__name__}: {e}"
